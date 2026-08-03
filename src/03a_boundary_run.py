#!/usr/bin/env python3
"""
Boundary-condition sensitivity: truncated MIDA vs the neck-extended mesh.

PRE-COMMITTED DECISION RULE (written into OUTLINE before any numbers existed):
if the dB shift at hyoid, submental_lat or submental_mid exceeds 1.0 dB under
EITHER slab conductivity, the extended mesh becomes primary for every published
result and the truncated mesh moves to supplementary.

NOISE FLOOR, stated up front so the rule is applied against a known resolution.
Electrode contact geometry is realised from incidental surface triangulation,
so nominally identical meshes disagree. That floor is READ FROM THE MEASUREMENT
FILE, never hardcoded here: it was 0.43 dB with a 15 mm electrode and 0.131 dB
re-measured at the 10 mm production diameter, and hardcoding it is how a
superseded number survives. At the corrected floor the 1.0 dB threshold sits
~7.6x above the noise rather than ~2.3x, so this run has more resolution than
was originally feared.

The 1.0 dB threshold itself is pre-committed in OUTLINE and does NOT move.

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


def read_measured_floor():
    """The electrode-meshing floor is a MEASURED quantity, not a constant.

    It was 0.43 dB (15 mm electrode), re-measured at 0.131 dB (10 mm, the
    production diameter). Hardcoding it here would silently keep using a
    superseded number, so it is read from the file the measurement writes.
    The 1.0 dB decision threshold is NOT read from anywhere: it is
    pre-committed in OUTLINE and must not move.
    """
    f = config.RESULTS / "electrode_meshing_floor.txt"
    if not f.exists():
        raise FileNotFoundError(
            f"{f} missing. Run src/measure_electrode_floor.py first; the "
            f"boundary shift is reported against the measured floor.")
    for line in f.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return float(line.split()[0])
    raise RuntimeError(f"no numeric floor value in {f}")


def load_table1():
    """Every tag in the mesh needs a conductivity, not just the ones the
    analysis reads.

    This script previously bound only the 10 muscle labels plus the slab: 11
    of the 117 tags present. SimNIBS raises
    `TypeError: The value N in cond_list is not numerical` for the other 106,
    which is the exact blocker recorded in METHODS_LOG that stopped the first
    attempt at this run. The script was never updated after Table 1 was built,
    so it would have crashed on launch.
    """
    p = config.RESULTS / "01_table1_conductivities.csv"
    if not p.exists():
        raise FileNotFoundError(
            f"{p} missing. Every mesh tag needs a sourced conductivity; "
            f"run src/build_table1.py first.")
    sig = {}
    for r in csv.DictReader(p.open()):
        lab = r.get("mida_label", "").strip()
        val = r.get("sigma_S_per_m", "").strip()
        if lab.isdigit() and val:
            sig[int(lab)] = float(val)
    if not sig:
        raise RuntimeError(f"{p} yielded no label->sigma pairs")
    return sig


def solve(mesh: Path, out: Path, pos, base_sigma, slab_sigma=None, label=""):
    from simnibs import sim_struct, run_simnibs, mesh_io
    import preflight
    out.parent.mkdir(parents=True, exist_ok=True)
    S = sim_struct.SESSION()
    S.fnamehead = str(mesh)
    S.pathfem = str(out)
    S.fields = "E"                       # vector, not magnitude
    S.open_in_gmsh = False
    S.map_to_surf = False
    t = S.add_tdcslist()
    t.currents = [config.INJECTION_CURRENT_A, -config.INJECTION_CURRENT_A]
    # EVERY tag in the mesh, from Table 1. Binding only the muscles leaves 106
    # tags at None and SimNIBS refuses the whole cond_list.
    assigned = dict(base_sigma)
    if slab_sigma is not None:
        assigned[EXTENSION_LABEL] = slab_sigma
    preflight.check_conductivity_range(assigned.values(), label=label)
    for lab, v in assigned.items():
        t.cond[lab - 1].value = v
        t.cond[lab - 1].name = f"tag{lab}"
    # muscle compartments keep their isotropic value and gain readable names
    for mname, _, lab, _ in config.MUSCLES:
        if lab is not None:
            t.cond[lab - 1].value = config.SIGMA["muscle_iso"]
            t.cond[lab - 1].name = mname
    if slab_sigma is not None:
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
    # Read the solver's own output. Not doing this cost a full 20-solve run.
    cal = preflight.read_calibration(out)
    print(f"    calibration: "
          f"{'clean' if cal is None else f'WARNED {cal:.2f}%'}", flush=True)
    hits = sorted(out.glob("*_scalar.msh")) or sorted(out.glob("*.msh"))
    if not hits:
        raise RuntimeError(f"no result mesh in {out}")
    return hits[0], cal


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

    sig = load_table1()
    print(f"conductivities: {len(sig)} tags from Table 1\n")

    calib = {}
    msh, calib["truncated"] = solve(a.truncated, a.workdir / "truncated",
                                    pos, sig, None, "truncated")
    base = compartment_medians(msh)
    results = {"truncated": base}
    for cname, sigma in SLAB_CONDUCTIVITIES.items():
        msh, calib[cname] = solve(a.extended, a.workdir / cname, pos, sig,
                                  sigma, f"extended, slab {sigma:.3f} S/m")
        results[cname] = compartment_medians(msh)

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

    floor = read_measured_floor()
    print(f"\nlargest |dB| shift across all compartments and both "
          f"conductivities: {worst:.2f} dB")
    print(f"measured electrode-meshing noise floor: {floor:.3f} dB")
    print(f"pre-committed decision threshold       : 1.00 dB  (NOT movable)")

    print("\ncalibration reported by the solver, per solve:")
    for k, v in calib.items():
        print(f"  {k:<20} {'clean' if v is None else f'WARNED {v:.2f}%'}")
    if any(v is not None for v in calib.values()):
        print("  At least one solve warned. The 200% conditioning failure is")
        print("  fatal; 11-15% on a well-conditioned custom mesh has been")
        print("  measured as a false positive. Judge by the value, and state")
        print("  it alongside the result rather than dropping it silently.")

    # Report where the verdict sits on the axis, not just which side it landed.
    print(f"\nFLIP POINT: the mesh decision changes at 1.00 dB; this run "
          f"measured {worst:.2f} dB,")
    print(f"            a factor of {worst / 1.0:.2f} of the threshold and "
          f"{worst / floor:.1f}x the noise floor.")

    if worst > 1.0:
        print("\nDECISION: extended mesh becomes PRIMARY for all published "
              "results;\n          truncated mesh moves to supplementary.")
    elif worst > floor:
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
