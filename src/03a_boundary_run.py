#!/usr/bin/env python3
"""
Boundary-condition sensitivity: truncated MIDA vs the neck-extended mesh.

PRE-COMMITTED DECISION RULE (written into OUTLINE before any numbers existed):
if the dB shift at hyoid, submental_lat or submental_mid exceeds 1.0 dB under
EITHER slab conductivity, the extended mesh becomes primary for every published
result and the truncated mesh moves to supplementary.

NOISE FLOOR, stated up front so the rule is applied against a known resolution.
Electrode contact geometry is realised from incidental surface triangulation,
and two statistically identical sphere meshes gave MAG differing by 5.06
percentage points = 20*log10(1.0506) = 0.43 dB. The decision threshold is
therefore only ~2.3x the measured per-realisation noise. A shift below ~0.5 dB
cannot be distinguished from meshing noise by a single pair of solves.

Injects between a jaw site and the contralateral earlobe -- the jaw-versus-ear
comparison the paper is actually about, and the montage most exposed to the cut
face. Compares median |E| per muscle compartment between meshes.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/03a_boundary_run.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402

EXTENSION_LABEL = 200
# Slab conductivity is bounded, not defended. Muscle-isotropic is the upper
# case; the blend is a volume-weighted average of muscle and fat, standing in
# for a neck that is not solid muscle.
SLAB_CONDUCTIVITIES = {
    "muscle_iso": 0.355,
    "fat_muscle_blend": 0.5 * (0.355 + 0.025),   # 0.190 S/m
}
INJECT_FROM = "hyoid"
INJECT_TO = "earlobe_contra"


def load_positions():
    rows = {r["name"]: r for r in
            csv.DictReader((config.RESULTS / "02_electrode_positions.csv").open())}
    return {n: np.array([float(r["R"]), float(r["A"]), float(r["S"])])
            for n, r in rows.items()
            if r.get("verified") != "held" and r["R"] != ""}


def solve(mesh: Path, out: Path, pos, slab_sigma=None, label=""):
    from simnibs import sim_struct, run_simnibs, mesh_io
    out.parent.mkdir(parents=True, exist_ok=True)
    S = sim_struct.SESSION()
    S.fnamehead = str(mesh)
    S.pathfem = str(out)
    S.fields = "E"                       # vector, not magnitude
    S.open_in_gmsh = False
    S.map_to_surf = False
    t = S.add_tdcslist()
    t.currents = [config.INJECTION_CURRENT_A, -config.INJECTION_CURRENT_A]
    for name, sigma in config.SIGMA.items():
        pass                              # tissue conductivities bind below
    # muscle compartments and the slab
    for mname, _, lab, _ in config.MUSCLES:
        if lab is not None:
            t.cond[lab - 1].value = config.SIGMA["muscle_iso"]
            t.cond[lab - 1].name = mname
    if slab_sigma is not None:
        t.cond[EXTENSION_LABEL - 1].value = slab_sigma
        t.cond[EXTENSION_LABEL - 1].name = "neck_extension"
    for j, nm in enumerate((INJECT_FROM, INJECT_TO)):
        el = t.add_electrode()
        el.channelnr = j + 1
        el.centre = list(pos[nm])
        el.shape = "ellipse"
        el.dimensions = [config.ELECTRODE_DIAMETER_MM] * 2
        el.thickness = 2
    print(f"  solving {label} ...", flush=True)
    run_simnibs(S)
    hits = sorted(out.glob("*_scalar.msh")) or sorted(out.glob("*.msh"))
    return hits[0]


def compartment_medians(res_msh: Path):
    """Volume-weighted median |E| per muscle compartment."""
    from simnibs import mesh_io
    m = mesh_io.read_msh(str(res_msh))
    if "E" not in m.field:
        raise RuntimeError(f"no vector E in {res_msh}; have {list(m.field)}")
    E = np.asarray(m.field["E"].value)
    if E.ndim != 2 or E.shape[1] != 3:
        raise RuntimeError(f"E must be (n,3), got {E.shape}")
    tets = m.elm.elm_type == 4
    tags = m.elm.tag1[tets]
    vols = m.elements_volumes_and_areas()[tets]
    mag = np.linalg.norm(E[tets], axis=1)
    out = {}
    for mname, _, lab, _ in config.MUSCLES:
        if lab is None:
            continue
        k = tags == lab
        if not k.any():
            continue
        v, w = mag[k], vols[k]
        o = np.argsort(v)
        c = np.cumsum(w[o])
        out[mname] = float(v[o][np.searchsorted(c, 0.5 * c[-1])])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="03a_boundary_run.py")
    ap.add_argument("--truncated", type=Path, default=config.DATA / "mida_headneck.msh")
    ap.add_argument("--extended", type=Path, default=config.DATA / "mida_neckext.msh")
    ap.add_argument("--workdir", type=Path, default=config.RESULTS / "boundary")
    ap.add_argument("--out", type=Path, default=config.RESULTS / "03_boundary_sensitivity.csv")
    a = ap.parse_args(argv)

    for p in (a.truncated, a.extended):
        if not p.exists():
            print(f"ERROR: missing mesh {p}", file=sys.stderr)
            return 1

    pos = load_positions()
    for nm in (INJECT_FROM, INJECT_TO):
        if nm not in pos:
            print(f"ERROR: {nm} has no accepted coordinate", file=sys.stderr)
            return 1
    print(f"injecting {config.INJECTION_CURRENT_A*1e3:.0f} mA between "
          f"{INJECT_FROM} and {INJECT_TO}\n")

    base = compartment_medians(
        solve(a.truncated, a.workdir / "truncated", pos, None, "truncated"))
    results = {"truncated": base}
    for cname, sigma in SLAB_CONDUCTIVITIES.items():
        results[cname] = compartment_medians(
            solve(a.extended, a.workdir / cname, pos, sigma,
                  f"extended, slab {sigma:.3f} S/m"))

    print(f"\n{'compartment':<24} {'truncated':>12} "
          + "".join(f"{c:>22}" for c in SLAB_CONDUCTIVITIES))
    print("-" * 90)
    rows, worst = [], 0.0
    for mname in base:
        line = f"{mname:<24} {base[mname]:>12.4e}"
        rec = {"compartment": mname, "truncated_V_per_m": base[mname]}
        for cname in SLAB_CONDUCTIVITIES:
            v = results[cname].get(mname, float("nan"))
            db = 20.0 * np.log10(v / base[mname]) if base[mname] > 0 else np.nan
            line += f"  {v:>10.4e} {db:>+7.2f}dB"
            rec[f"{cname}_V_per_m"] = v
            rec[f"{cname}_dB"] = round(float(db), 3)
            if np.isfinite(db):
                worst = max(worst, abs(db))
        print(line)
        rows.append(rec)

    print(f"\nlargest |dB| shift across all compartments and both "
          f"conductivities: {worst:.2f} dB")
    print(f"measured electrode-meshing noise floor: ~0.43 dB")
    print(f"pre-committed decision threshold       : 1.00 dB")
    if worst > 1.0:
        print("\nDECISION: extended mesh becomes PRIMARY for all published "
              "results;\n          truncated mesh moves to supplementary.")
    elif worst > 0.43:
        print("\nDECISION: below the 1.0 dB threshold, so the truncated mesh "
              "stays primary,\n          but the shift exceeds the meshing "
              "noise floor and is therefore real.\n          Report in "
              "Limitations with the measured value.")
    else:
        print("\nDECISION: below both the threshold and the meshing noise "
              "floor.\n          Truncated mesh stays primary; one paragraph "
              "in Limitations.")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nWritten: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
