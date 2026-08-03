#!/usr/bin/env python3
"""
Stage 3. One reciprocity solve per electrode, both anisotropy conditions.

Injects 1 mA between each electrode and the common reference, solves for E
throughout the head, and records the volume-weighted median |E| in every
segmented muscle compartment. That is the lead field, by reciprocity: one
solve per montage instead of one per source.

Runs on the TRUNCATED mesh `mida_headneck.msh`, which is primary. The
neck-extended mesh does not conserve charge and every solve on it is void; see
METHODS_LOG and OUTLINE. The pre-committed 1.0 dB boundary rule is recorded
UNEXECUTED, not satisfied.

RESUMABLE BY DESIGN, and this is not decoration
-----------------------------------------------
44 solves at ~4 min is ~3 hours serial. A run that dies at solve 40 must
resume at 40, not at 1. Two things make a naive re-run worse than useless:

  - SimNIBS REFUSES to write into a directory that already holds a
    `simnibs_simulation*.mat`, so re-running crashes on the work that already
    succeeded rather than skipping it
  - a solve killed midway leaves a directory that LOOKS started but has no
    result mesh, and would be skipped as if complete if "directory exists"
    were the test

So completeness is judged by the result mesh plus a readable summary, never by
the directory existing. Incomplete directories are cleared and re-solved;
complete ones are skipped without loading anything.

Results are appended PER SOLVE. Nothing is held until the end, so a crash
costs one solve rather than the whole run.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/03_leadfields.py
    ... --dry-run          plan only, no solving
    ... --conditions iso   one condition instead of both
"""
from __future__ import annotations

import argparse
import csv
import shutil
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402
import preflight  # noqa: E402
import solve_invariants as SI  # noqa: E402

MESH = config.DATA / "mida_headneck.msh"
OUT_CSV = config.RESULTS / "03_leadfields.csv"
WORKDIR = config.RESULTS / "leadfields"
CALIB_LOG = config.RESULTS / "03_leadfield_calibration.csv"

# MIDA's inferior cut face. Reported per electrode so a reader can see
# truncation exposure per site instead of taking it on trust.
CUT_FACE_S = -116.2

CONDITIONS = ("iso", "aniso")


def load_positions():
    """Accepted coordinates only. `throat_scm` is verified='held' with blank
    coordinates pending a physical measurement on Carl's neck, and every
    consumer skips it rather than inventing a placement."""
    rows = list(csv.DictReader(
        (config.RESULTS / "02_electrode_positions.csv").open()))
    pos, held = {}, []
    for r in rows:
        if r.get("verified") == "held" or not r["R"]:
            held.append(r["name"])
            continue
        pos[r["name"]] = dict(
            xyz=np.array([float(r["R"]), float(r["A"]), float(r["S"])]),
            montage=r.get("montage", ""), side=r.get("side", ""),
            depth_mm=r.get("depth_mm", ""))
    return pos, held


def load_sigma():
    p = config.RESULTS / "01_table1_conductivities.csv"
    sig = {}
    for r in csv.DictReader(p.open()):
        lab, val = r.get("mida_label", "").strip(), r.get("sigma_S_per_m", "").strip()
        if lab.isdigit() and val:
            sig[int(lab)] = float(val)
    if not sig:
        raise RuntimeError(f"{p} yielded no label->sigma pairs")
    return sig


def is_complete(d: Path) -> bool:
    """Complete means a RESULT exists, not that the directory does.

    A killed solve leaves a directory with a .mat and logs and no result mesh.
    Testing for the directory would skip it forever and silently drop an
    electrode from the matrix.
    """
    if not d.is_dir():
        return False
    if not (list(d.glob("*_scalar.msh")) or list(d.glob("*.msh"))):
        return False
    return (d / "fields_summary.txt").exists()


def compartment_medians(res_msh: Path):
    """Volume-weighted median |E| per segmented muscle compartment."""
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
    for name, _, lab, _ in config.MUSCLES:
        if lab is None:
            continue
        k = tags == lab
        if not k.any():
            continue
        v, w = mag[k], vols[k]
        o = np.argsort(v)
        c = np.cumsum(w[o])
        out[name] = float(v[o][np.searchsorted(c, 0.5 * c[-1])])
    return out


def solve_one(elec, pos, sigma, condition, out: Path):
    from simnibs import sim_struct, run_simnibs
    out.parent.mkdir(parents=True, exist_ok=True)
    preflight.check_conductivity_range(sigma.values(),
                                       label=f"{condition}__{elec}")
    S = sim_struct.SESSION()
    S.fnamehead = str(MESH)
    S.pathfem = str(out)
    S.fields = "E"                       # uppercase: VECTOR field
    S.open_in_gmsh = False
    S.map_to_surf = False
    t = S.add_tdcslist()
    t.currents = [config.INJECTION_CURRENT_A, -config.INJECTION_CURRENT_A]
    for lab, v in sigma.items():
        t.cond[lab - 1].value = v
        t.cond[lab - 1].name = f"tag{lab}"
    for j, nm in enumerate((elec, config.REFERENCE)):
        el = t.add_electrode()
        el.channelnr = j + 1
        el.centre = list(pos[nm]["xyz"])
        el.shape = "ellipse"
        el.dimensions = [config.ELECTRODE_DIAMETER_MM] * 2
        el.thickness = 2
    run_simnibs(S)
    hits = sorted(out.glob("*_scalar.msh")) or sorted(out.glob("*.msh"))
    if not hits:
        raise RuntimeError(f"no result mesh in {out}")
    return hits[0]


def append_row(path: Path, row: dict, fieldnames):
    new = not path.exists()
    with path.open("a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        if new:
            w.writeheader()
        w.writerow(row)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="03_leadfields.py")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--conditions", nargs="+", default=["iso"],
                    choices=CONDITIONS)
    a = ap.parse_args(argv)

    if not MESH.exists():
        print(f"ERROR: missing mesh {MESH}", file=sys.stderr)
        return 1

    pos, held = load_positions()
    if config.REFERENCE not in pos:
        print(f"ERROR: reference {config.REFERENCE} has no coordinate",
              file=sys.stderr)
        return 1
    targets = [e for e in pos if e != config.REFERENCE]
    sigma_iso = load_sigma()

    muscles = [n for n, _, lab, _ in config.MUSCLES if lab is not None]
    fields = (["electrode", "condition", "montage", "side", "depth_mm",
               "clearance_to_cut_mm", "calibration_pct", "inv1_mean",
               "inv1_cv", "inv2_net_frac"] + muscles)

    plan = [(e, c) for c in a.conditions for e in sorted(targets)]
    done = [(e, c) for e, c in plan if is_complete(WORKDIR / c / e)]
    partial = [(e, c) for e, c in plan
               if (WORKDIR / c / e).is_dir() and not is_complete(WORKDIR / c / e)]

    print(f"mesh        : {MESH.name}  (truncated, PRIMARY)")
    print(f"electrodes  : {len(targets)} against {config.REFERENCE}")
    print(f"held/skipped: {held or 'none'}")
    print(f"conditions  : {', '.join(a.conditions)}")
    print(f"planned     : {len(plan)} solves")
    print(f"  complete, will SKIP   : {len(done)}")
    print(f"  partial, will CLEAR   : {len(partial)}")
    print(f"  to run                : {len(plan) - len(done)}")
    if partial:
        for e, c in partial:
            print(f"      partial: {c}/{e}")
    if a.dry_run:
        print("\n--dry-run: nothing solved.")
        return 0

    t0 = time.time()
    for i, (elec, cond) in enumerate(plan, 1):
        out = WORKDIR / cond / elec
        if is_complete(out):
            print(f"[{i}/{len(plan)}] {cond}/{elec}: complete, skipping",
                  flush=True)
            continue
        if out.is_dir():
            # Partial. SimNIBS will refuse to write here, and the directory is
            # worthless without a result mesh, so clear it rather than fail.
            print(f"[{i}/{len(plan)}] {cond}/{elec}: partial, clearing",
                  flush=True)
            shutil.rmtree(out)

        sigma = dict(sigma_iso)
        if cond == "aniso":
            # NOT IMPLEMENTED, and it RAISES rather than quietly solving the
            # isotropic case twice.
            #
            # Anisotropy needs a per-element conductivity TENSOR, not a scalar
            # per tag: sigma_long = 0.4, sigma_trans = 0.1 aligned to a fibre
            # direction, applied only to the compartments config.FIBRE_MODEL
            # marks "pca" (the strap muscles), with the "isotropic" ones left
            # scalar in BOTH runs by design. orientation.principal_axis()
            # supplies the axis; what is missing is writing the tensor field
            # into the SimNIBS session.
            #
            # Falling through with the isotropic map would produce a complete,
            # plausible, entirely fake "anisotropic" column and a Fig 4 that
            # compares a condition against itself. That is precisely the
            # silent-success failure this project keeps finding, so it is a
            # hard stop instead.
            raise NotImplementedError(
                "anisotropic condition is not implemented: it requires a "
                "per-element conductivity tensor built from "
                "orientation.principal_axis() for the config.FIBRE_MODEL "
                "'pca' compartments. Run with --conditions iso until it is "
                "written. Silently reusing the isotropic map would fabricate "
                "Fig 4.")

        print(f"[{i}/{len(plan)}] {cond}/{elec}: solving ...", flush=True)
        res = solve_one(elec, pos, sigma, cond, out)

        cal = preflight.read_calibration(out)
        inv = SI.check_solve_plateau(res, pos[elec]["xyz"],
                                     SI.with_electrode_tags(sigma),
                                     verbose=False)
        med = compartment_medians(res)

        row = dict(electrode=elec, condition=cond,
                   montage=pos[elec]["montage"], side=pos[elec]["side"],
                   depth_mm=pos[elec]["depth_mm"],
                   clearance_to_cut_mm=round(
                       float(pos[elec]["xyz"][2]) - CUT_FACE_S, 2),
                   calibration_pct=("" if cal is None else round(cal, 2)),
                   inv1_mean=round(inv["mean_ratio"], 5),
                   inv1_cv=round(inv["cv"], 5),
                   inv2_net_frac=round(inv.get("outer_net_frac", float("nan")), 6))
        for mname in muscles:
            row[mname] = med.get(mname, "")
        append_row(OUT_CSV, row, fields)          # incremental, per solve

        esc = SI.needs_escalation(inv["cv"])
        print(f"    calibration {'clean' if cal is None else f'{cal:.2f}%'}  "
              f"inv1 mean {inv['mean_ratio']:.4f} CV {inv['cv']*100:.2f}%"
              f"{'  [ESCALATE]' if esc else ''}  "
              f"inv2 net {inv.get('outer_net_frac', float('nan')):+.4f}",
              flush=True)

    dt = (time.time() - t0) / 60.0
    print(f"\nwrote {OUT_CSV}  ({dt:.1f} min this run)")
    print("Stage 4 reads this file. Truncation sensitivity (gap with and "
          "without\nhyoid/submental_lat/submental_mid) is computed there from "
          "the\nclearance_to_cut_mm column emitted here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
