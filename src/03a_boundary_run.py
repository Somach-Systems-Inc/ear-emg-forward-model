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

# 200 IS INSIDE SIMNIBS'S ELECTRODE-RUBBER RANGE (100-499) AND IS A DEFECT.
# Any conductivity map built from Table 1 alone has this compartment filled in
# at 29.4 S/m electrode rubber by solve_invariants.with_electrode_tags(), an
# 83x error applied silently by setdefault. It produced a fabricated
# invariant-2 reading (-0.310 x injected, against -0.0038 with the correct
# map). See METHODS_LOG 2026-08-03.
#
# NOT renumbered here, deliberately: the extended mesh is unused, its
# disposition is settled on the flux-decay probe, and rebuilding it to change a
# label would reopen a closed question for no gain. The guard below makes the
# collision impossible to repeat in anything new.
EXTENSION_LABEL = 200   # DEFECT: see above
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


def solve(mesh: Path, out: Path, pos, base_sigma, slab_sigma=None, label="",
          inject_from=None, inject_to=None):
    """Solve one montage.

    `inject_from` / `inject_to` are EXPLICIT PARAMETERS, and that is a bug fix,
    not a tidy-up. They used to be read from this module's globals, so
    `03a2_boundary_probe.py` -- which imports this function and sets its OWN
    module-level INJECT_FROM = "above_ear" -- silently solved hyoid instead.
    It reported a probe 130 mm from the cut face and ran the identical montage
    8 mm from it, producing a bit-identical result mesh (md5 b110d2ce...) and
    the identical 100.49% calibration, which was then read as two independent
    measurements agreeing. See METHODS_LOG 2026-08-03.
    """
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
    pair = (inject_from or INJECT_FROM, inject_to or INJECT_TO)
    print(f"  montage: {pair[0]} -> {pair[1]}", flush=True)
    for j, nm in enumerate(pair):
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

    # Invariants 1 and 2. This script previously ran NEITHER, which is how a
    # mesh that leaks 1.6 mA of a 1 mA injection got as far as printing
    # "extended mesh becomes PRIMARY for all published results". Invariant 2
    # is exactly the unconserved-current test that would have caught it.
    # Centre the patch on the electrode THIS SOLVE actually injected at, not on
    # the module default. Same defect as the montage bug above and it survived
    # the first fix: a patch centred 130 mm from the injection contains no
    # source, so the cut flux is ~0 at every radius and invariant 1 fails for a
    # reason that has nothing to do with the solve.
    import solve_invariants as SI
    inv = SI.check_solve_plateau(hits[0], pos[pair[0]],
                                 SI.with_electrode_tags(assigned),
                                 verbose=False)
    print(f"    invariant 1: mean {inv['mean_ratio']:.4f} "
          f"CV {inv['cv']*100:.2f}% over "
          f"{inv['plateau']['radii'][0]:.0f}-{inv['plateau']['radii'][-1]:.0f} mm",
          flush=True)
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

    # SimNIBS refuses to write into a directory that already holds a
    # simnibs_simulation*.mat, but only AFTER loading the mesh. Check first, and
    # say what to do about it, rather than surfacing an OSError minutes in.
    # Do NOT auto-delete: a stale directory may hold a real earlier result.
    stale = [d for d in (a.workdir / "truncated",
                         *(a.workdir / c for c in SLAB_CONDUCTIVITIES))
             if list(d.glob("simnibs_simulation*.mat"))]
    if stale:
        print("ERROR: these output directories already hold simulation "
              "results:", file=sys.stderr)
        for d in stale:
            print(f"  {d}", file=sys.stderr)
        print("\nMove them aside (do not delete -- they may hold a real "
              "earlier result)\nand re-run, or pass --workdir with a fresh "
              "path.", file=sys.stderr)
        return 1

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

    print("\ncalibration reported by the solver, per solve "
          "(RECORDED, gates nothing):")
    for k, v in calib.items():
        print(f"  {k:<20} {'clean' if v is None else f'warned {v:.2f}%'}")
    if any(v is not None for v in calib.values()):
        print("  No verdict rests on these. SimNIBS's calibration check is")
        print("  measured anti-correlated with true delivered current on this")
        print("  mesh (Spearman -0.425, p = 0.048, n = 22), and the former")
        print("  11-15% 'benign band' is RETIRED: it partitioned a quantity")
        print("  that does not measure what it claims. Delivered current comes")
        print("  from the tet-patch integral in solve_invariants; judge by it.")

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
