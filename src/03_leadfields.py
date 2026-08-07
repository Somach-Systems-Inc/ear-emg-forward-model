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
# paired_invariants() had this inline. It has to be a module-level name like the
# others, or --workdir redirects the solve directories and the summary CSV while
# this one keeps overwriting the committed results/03_paired_invariants.csv --
# which is exactly what happened the first time --workdir was used.
PAIRED_CSV = config.RESULTS / "03_paired_invariants.csv"

# MIDA's inferior cut face. Reported per electrode so a reader can see
# truncation exposure per site instead of taking it on trust.
#
# There is deliberately NO scalar here. The face is a plane tilted 2.664 deg off
# the S axis, so it has no single S coordinate, and the literal that used to sit
# on this line (-116.2) was a bare constant in seven files that governed the
# near-cut exclusion set. Clearance is the perpendicular distance to the derived
# plane; see config.cut_plane() and 01d_derive_cut_plane.py.

CONDITIONS = ("iso", "aniso")


def load_positions():
    """Accepted coordinates only. `throat_scm` is verified='held' with blank
    coordinates pending a physical measurement on Carl's neck, and every
    consumer skips it rather than inventing a placement."""
    rows = list(csv.DictReader(
        (config.RESULTS / "02_electrode_positions.csv").open(encoding="utf-8")))
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
    for r in csv.DictReader(p.open(encoding="utf-8")):
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


def solve_one(elec, pos, sigma, condition, out: Path,
              current_scale=1.0, swap=False):
    """One solve.

    `current_scale` and `swap` exist for the paired invariants: 2x the current
    for linearity, source and sink exchanged for reciprocity. They are EXPLICIT
    PARAMETERS and the montage is printed, because the same function reading a
    montage from a module global is how `03a2_boundary_probe.py` solved `hyoid`
    while reporting `above_ear`.
    """
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
    I = config.INJECTION_CURRENT_A * current_scale
    t.currents = [I, -I]
    for lab, v in sigma.items():
        t.cond[lab - 1].value = v
        t.cond[lab - 1].name = f"tag{lab}"
    pair = (config.REFERENCE, elec) if swap else (elec, config.REFERENCE)
    print(f"    montage: {pair[0]} (+{I*1e3:.1f} mA) -> {pair[1]}", flush=True)
    for j, nm in enumerate(pair):
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


def sample_points(res_msh: Path, n=2000, seed=0):
    """Points inside segmented muscle, for the paired invariants.

    Muscle compartments rather than the whole head because those are where the
    lead field is actually read, so this tests the identity where the paper
    uses it.
    """
    from simnibs import mesh_io
    m = mesh_io.read_msh(str(res_msh))
    nodes = m.nodes.node_coord
    tets = m.elm.elm_type == 4
    tags = m.elm.tag1[tets]
    nl = m.elm.node_number_list[tets][:, :4] - 1
    labs = {lab for _, _, lab, _ in config.MUSCLES if lab is not None}
    k = np.isin(tags, list(labs))
    if not k.any():
        raise RuntimeError("no muscle-tagged tetrahedra to sample")
    cent = nodes[nl[k]].mean(axis=1)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(cent), size=min(n, len(cent)), replace=False)
    return cent[idx]


def paired_invariants(pos, sigma, targets, condition="iso"):
    """INVARIANTS 3 AND 4 — the batch policy that had never executed.

    `check_linearity` and `check_reciprocity_symmetry` had no caller anywhere
    in the repository; all 22 stage-3 solves ran without them. `batch_plan()`
    picks the first and last solve of the batch, which is the documented
    policy, so drift appearing partway through a run is caught rather than only
    a bad first solve.

    Invariant 4 is the one that matters most here: reciprocity is the identity
    the entire paper rests on, and until now it had only ever been checked on
    the analytic sphere, never on the real head geometry.
    """
    order = sorted(targets)
    picks = sorted(SI.batch_plan(len(order)))
    print(f"\nPAIRED INVARIANTS (3 and 4) on solve indices {picks} of "
          f"{len(order)}: {[order[i] for i in picks]}")
    rows = []
    for i in picks:
        elec = order[i]
        base = WORKDIR / condition / elec
        if not is_complete(base):
            raise RuntimeError(f"{elec}: no completed 1x solve to pair against")
        base_msh = (sorted(base.glob("*_scalar.msh"))
                    or sorted(base.glob("*.msh")))[0]
        pts = sample_points(base_msh)

        out2 = WORKDIR / condition / "_paired" / f"{elec}__2x"
        outs = WORKDIR / condition / "_paired" / f"{elec}__swap"
        for d, scale, swap, what in ((out2, 2.0, False, "2x current"),
                                     (outs, 1.0, True, "swapped montage")):
            if is_complete(d):
                print(f"  {elec}: {what} already complete, skipping")
                continue
            if d.is_dir():
                shutil.rmtree(d)
            print(f"  {elec}: solving {what} ...", flush=True)
            solve_one(elec, pos, sigma, condition, d, current_scale=scale,
                      swap=swap)

        m2 = (sorted(out2.glob("*_scalar.msh")) or sorted(out2.glob("*.msh")))[0]
        ms = (sorted(outs.glob("*_scalar.msh")) or sorted(outs.glob("*.msh")))[0]

        row = {"electrode": elec, "condition": condition,
               "n_points": len(pts)}

        # Called by name, not through a table of function objects. The AST
        # coverage test resolves Call nodes, so a guard invoked via a variable
        # is invisible to it -- which would reintroduce exactly the "written
        # but never wired" blindness this whole exercise exists to remove.
        def _record(name, fn):
            # REPORTED, not gated. The 1e-6 tolerances were never measured and
            # are withdrawn (see solve_invariants). What decides whether a
            # number here is interpretable at all is `same_mesh`: SimNIBS
            # re-meshes the electrodes every run, and a comparison across two
            # different discretisations measures electrode realisation, not the
            # identity under test.
            worst, same, note = fn()
            row[name] = worst
            row[name + "_same_mesh"] = bool(same)
            row[name + "_geometry"] = note
            print(f"    {name}: worst {worst:.3e}   "
                  f"[{'same discretisation' if same else 'DIFFERENT geometry'}"
                  f" — {note}]")

        _record("invariant_3_linearity",
                lambda: SI.check_linearity(base_msh, m2, pts))
        _record("invariant_4_reciprocity",
                lambda: SI.check_reciprocity_symmetry(base_msh, ms, pts))
        rows.append(row)

    out_csv = PAIRED_CSV
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {out_csv}")
    return rows


def append_row(path: Path, row: dict, fieldnames):
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        if new:
            w.writeheader()
        w.writerow(row)


def main(argv=None) -> int:
    # Declared up front because the --workdir/--out help strings interpolate
    # these names, and a `global` after any use of them is a SyntaxError.
    global WORKDIR, OUT_CSV, CALIB_LOG, PAIRED_CSV, MESH

    ap = argparse.ArgumentParser(prog="03_leadfields.py")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--conditions", nargs="+", default=["iso"],
                    choices=CONDITIONS)
    ap.add_argument("--paired-only", action="store_true",
                    help="skip the main batch and run invariants 3 and 4 "
                         "against the solves already on disk")
    ap.add_argument("--electrodes", nargs="+", metavar="NAME",
                    help="solve only these electrodes instead of all targets. "
                         "For re-running a single failed site, and for timing "
                         "or memory measurement without committing to the full "
                         "batch. Names must exist in 02_electrode_positions.csv "
                         "and must not be the reference. Does NOT change the "
                         "default: omit it and every target is solved.")
    ap.add_argument("--workdir", type=Path, default=None,
                    help=f"solve directory (default: {WORKDIR}). Every val_*.py "
                         f"harness already takes one; this did not, so a timing "
                         f"or re-measurement run had no way to avoid CLEARING "
                         f"the committed solves under results/leadfields/.")
    ap.add_argument("--cut-plane", type=Path, default=None,
                    help="cut-plane CSV matching --mesh (default: the committed "
                         "results/01_cut_plane.csv). The plane is FITTED to a "
                         "specific mesh and config.cut_plane() verifies its "
                         "sha256, so a second mesh needs its own plane file.")
    ap.add_argument("--mesh", type=Path, default=None,
                    help=f"head mesh to solve on (default: {MESH.name}). For "
                         f"the discretisation convergence study, which needs "
                         f"the SAME pipeline on a mesh built at a different "
                         f"resolution. Requires --workdir: see below.")
    ap.add_argument("--out", type=Path, default=None,
                    help=f"results CSV (default: {OUT_CSV})")
    ap.add_argument("--calib-log", type=Path, default=None,
                    help=f"calibration log (default: {CALIB_LOG})")
    a = ap.parse_args(argv)

    # A DIFFERENT MESH MUST WRITE SOMEWHERE ELSE. Solving a refined mesh into
    # results/leadfields/ would overwrite the production solves with fields
    # from a different discretisation, and nothing downstream would notice:
    # the CSVs have no mesh column. This is the same failure that overwrote a
    # committed 03_paired_invariants.csv on 2026-08-06, so --mesh refuses
    # rather than trusting the caller to remember.
    if a.cut_plane is not None:
        config.CUT_PLANE_CSV = a.cut_plane
    if a.mesh is not None:
        # A PLANE FITTED TO ANOTHER MESH IS NOT A PLANE FOR THIS ONE. The cut
        # plane is a total-least-squares fit to the truncation face of ONE
        # mesh, and config.cut_plane() verifies the mesh sha256 for exactly
        # that reason. --mesh without --cut-plane sends the guard a mesh it was
        # never fitted to, which is how this flag first failed: it ran one
        # electrode, then raised on the second machine's mesh hash.
        if a.cut_plane is None:
            print("ERROR: --mesh requires --cut-plane.\n"
                  "  The cut plane is fitted to one mesh and its hash is "
                  "checked. Derive one for the new mesh first:\n"
                  "    01d_derive_cut_plane.py --mesh <new.msh> --out <new_plane.csv>",
                  file=sys.stderr)
            return 2
        if a.workdir is None or a.out is None:
            print("ERROR: --mesh requires --workdir AND --out.\n"
                  "  Solving a different mesh into the production tree would "
                  "silently replace the committed solves with fields from a\n"
                  "  different discretisation, and no downstream file records "
                  "which mesh produced it.\n"
                  "  e.g. --mesh data/mida_fine.msh --workdir results/conv/leadfields "
                  "--out results/conv/03_leadfields.csv",
                  file=sys.stderr)
            return 2
        MESH = a.mesh

    # Rebind the module-level destinations so the helpers that read them write
    # to the redirected tree too. Redirecting only main() would leave
    # paired_invariants() still clearing the committed directories.
    if a.workdir is not None:
        WORKDIR = a.workdir
    if a.out is not None:
        OUT_CSV = a.out
    if a.calib_log is not None:
        CALIB_LOG = a.calib_log
    if a.out is not None:
        # keep the paired-invariant summary beside the redirected results,
        # never back in results/ where the committed copy lives
        PAIRED_CSV = OUT_CSV.parent / "03_paired_invariants.csv"
    if a.workdir is not None or a.out is not None or a.calib_log is not None:
        print(f"redirected: workdir={WORKDIR}  out={OUT_CSV}  calib={CALIB_LOG}\n"
              f"            paired={PAIRED_CSV}")

    if not MESH.exists():
        print(f"ERROR: missing mesh {MESH}", file=sys.stderr)
        return 1

    pos, held = load_positions()
    if config.REFERENCE not in pos:
        print(f"ERROR: reference {config.REFERENCE} has no coordinate",
              file=sys.stderr)
        return 1
    targets = [e for e in pos if e != config.REFERENCE]

    if a.electrodes:
        # Fail loudly on a name that is not a target. Silently solving a subset
        # because a name was misspelled would look exactly like a completed run
        # and the missing rows would only surface in stage 4.
        unknown = [e for e in a.electrodes if e not in pos]
        isref = [e for e in a.electrodes if e == config.REFERENCE]
        if unknown or isref:
            if unknown:
                print(f"ERROR: not in 02_electrode_positions.csv: "
                      f"{', '.join(sorted(unknown))}", file=sys.stderr)
            if isref:
                print(f"ERROR: {config.REFERENCE} is the reference, not a "
                      f"target; every solve is already against it.",
                      file=sys.stderr)
            print(f"  available: {', '.join(sorted(targets))}", file=sys.stderr)
            return 1
        targets = [e for e in targets if e in set(a.electrodes)]
        print(f"--electrodes: SUBSET of {len(targets)} "
              f"({', '.join(sorted(targets))}) -- this is NOT a full run")

    sigma_iso = load_sigma()

    muscles = [n for n, _, lab, _ in config.MUSCLES if lab is not None]
    fields = (["electrode", "condition", "montage", "side", "depth_mm",
               "clearance_to_cut_mm", "calibration_pct", "inv1_mean",
               "inv1_cv", "inv2_net_frac", "inv2_coverage"] + muscles)

    if a.paired_only:
        paired_invariants(pos, sigma_iso, targets, a.conditions[0])
        return 0

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
                       config.clearance_to_cut(pos[elec]["xyz"]), 2),
                   calibration_pct=("" if cal is None else round(cal, 2)),
                   inv1_mean=round(inv["mean_ratio"], 5),
                   inv1_cv=round(inv["cv"], 5),
                   inv2_net_frac=round(inv.get("outer_net_frac", float("nan")), 6),
                   # Recorded, not discarded. Invariant 2 integrates over
                   # whatever share of its shell lies inside the conductor, and
                   # at zero coverage it returns exactly 0.0 and passes. Without
                   # this column a vacuous pass and a real one look identical.
                   inv2_coverage=round(inv.get("outer_coverage", float("nan")), 4))
        for mname in muscles:
            row[mname] = med.get(mname, "")
        append_row(OUT_CSV, row, fields)          # incremental, per solve

        esc = SI.needs_escalation(inv["cv"])
        print(f"    calibration {'clean' if cal is None else f'{cal:.2f}%'}  "
              f"inv1 mean {inv['mean_ratio']:.4f} CV {inv['cv']*100:.2f}%"
              f"{'  [ESCALATE]' if esc else ''}  "
              f"inv2 net {inv.get('outer_net_frac', float('nan')):+.4f}",
              flush=True)

    # The batch policy, executed rather than described. It ran on nothing for
    # the whole project because nothing called it.
    paired_invariants(pos, sigma_iso, targets, a.conditions[0])

    dt = (time.time() - t0) / 60.0
    print(f"\nwrote {OUT_CSV}  ({dt:.1f} min this run)")
    print("Stage 4 reads this file. Truncation sensitivity (gap with and "
          "without\nhyoid/submental_lat/submental_mid) is computed there from "
          "the\nclearance_to_cut_mm column emitted here.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
