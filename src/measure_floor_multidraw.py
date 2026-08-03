#!/usr/bin/env python3
"""
The electrode-meshing floor, measured as a DISTRIBUTION instead of one
difference.

WHY THIS EXISTS

`measure_electrode_floor.py` reported 0.1310 dB from n = 2 -- a single
difference between two nominally-identical meshes, quoted to four significant
figures. One difference is not a spread, and that number now gates two
analyses (the cavity criterion (b), and the Fig 5 channel-redundancy
resolution floor). A quantity used as a threshold needs its own uncertainty.

THE DESIGN, AND WHY THE ROTATION IS THE WHOLE TRICK

A draw is one rigid rotation applied to BOTH the electrode array AND the
source points, solved on the SAME mesh file.

Rotating both is what makes the draws comparable. The relative geometry --
every source-to-electrode vector -- is identical in every draw, so the exact
answer is identical in every draw. The only thing that changes is how that
fixed geometry lands on a fixed discretisation: which surface triangles fall
under each electrode, and which tetrahedron contains each source. Any spread
in the measured error is therefore realisation noise and nothing else.

Rotating the electrodes ALONE would have been wrong. Sources would then sit
at different relative positions, the exact answer would genuinely differ
between draws, and real geometry change would be counted as noise.

WHAT THE ESTIMAND IS, STATED PRECISELY

This measures *mesh-realisation* noise at fixed physical geometry: electrode
contact triangulation AND source-point tetrahedron assignment. That is
slightly broader than electrode contact alone, so it is an UPPER BOUND on the
electrode-meshing term. It is also the quantity a resolution floor actually
needs, since both effects move a reported number without any physics moving.

TWO ESTIMATORS, BOTH REPORTED

  1. median MAG across sources -- the SAME estimator the n=2 floor used, so
     the new number is directly comparable to 0.1310 dB.
  2. per-electrode MAG -- the norm of each electrode's lead-field column
     against its analytic counterpart. This is the more defensible per-SITE
     quantity, because the floor is used per site: criterion (b) tests a
     per-electrode residual, and Fig 5 asks whether two SITES differ. The
     registered estimator is not silently replaced; both are printed.

Two phases, since simnibs and mne live in different interpreters:
    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/measure_floor_multidraw.py --phase simnibs
    .venv/bin/python                              src/measure_floor_multidraw.py --phase analytic
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402
import val_sphere_build as sph  # noqa: E402
import val_rdm_mag as vrm  # noqa: E402

N_DRAWS = 6                  # >= 5, per the queued follow-up
ANGLE_RANGE_DEG = (2.0, 8.0)  # big enough to re-triangulate, small enough to
#                               stay an obviously equivalent placement
SEED = 20260802


def rodrigues(axis, angle_rad):
    """Rotation matrix about a unit axis, written out rather than imported so
    the draw geometry is auditable from this file alone."""
    a = np.asarray(axis, dtype=float)
    a = a / np.linalg.norm(a)
    K = np.array([[0.0, -a[2], a[1]],
                  [a[2], 0.0, -a[0]],
                  [-a[1], a[0], 0.0]])
    return (np.eye(3) + np.sin(angle_rad) * K
            + (1.0 - np.cos(angle_rad)) * (K @ K))


def draw_rotations(n=N_DRAWS, seed=SEED):
    """Draw 0 is the identity, so this harness reproduces the committed
    single-placement measurement as one of its own draws."""
    rng = np.random.default_rng(seed)
    mats = [np.eye(3)]
    meta = [(0.0, np.array([0.0, 0.0, 1.0]))]
    lo, hi = np.deg2rad(ANGLE_RANGE_DEG[0]), np.deg2rad(ANGLE_RANGE_DEG[1])
    while len(mats) < n:
        ax = rng.normal(size=3)
        ax /= np.linalg.norm(ax)
        ang = rng.uniform(lo, hi)
        mats.append(rodrigues(ax, ang))
        meta.append((float(np.rad2deg(ang)), ax))
    return mats, meta


def phase_simnibs(mesh: Path, workdir: Path, npz: Path) -> int:
    from simnibs import sim_struct, run_simnibs, mesh_io

    if not mesh.exists():
        print(f"ERROR: no mesh at {mesh}", file=sys.stderr)
        return 1

    pts0, dirs0 = vrm.source_points()
    elecs0, ref0 = vrm.electrode_positions()
    mats, meta = draw_rotations()

    print(f"mesh      : {mesh.name}  (held FIXED across draws)")
    print(f"electrode : {config.ELECTRODE_DIAMETER_MM} mm (config)")
    print(f"draws     : {len(mats)}  (draw 0 = identity)")
    print(f"per draw  : {len(elecs0)} electrodes + 1 reference, "
          f"{len(pts0)} sources")
    print(f"total     : {len(mats) * len(elecs0)} solves\n")

    E_all = np.zeros((len(mats), len(elecs0), len(pts0), 3))
    P, D, EL, RF = [], [], [], []

    for r, (M, (ang, ax)) in enumerate(zip(mats, meta)):
        # Rotate EVERYTHING together: relative geometry is invariant, so the
        # exact answer is invariant, so any spread is realisation noise.
        pts, dirs = pts0 @ M.T, dirs0 @ M.T
        elecs, ref = elecs0 @ M.T, ref0 @ M.T
        P.append(pts); D.append(dirs); EL.append(elecs); RF.append(ref)
        print(f"draw {r}: rotation {ang:5.2f} deg about "
              f"[{ax[0]:+.3f} {ax[1]:+.3f} {ax[2]:+.3f}]", flush=True)

        for i, e in enumerate(elecs):
            out = workdir / f"draw{r:02d}" / f"e{i:02d}"
            out.parent.mkdir(parents=True, exist_ok=True)
            S = sim_struct.SESSION()
            S.fnamehead = str(mesh)
            S.pathfem = str(out)
            S.fields = "E"                 # uppercase: VECTOR field
            S.open_in_gmsh = False
            S.map_to_surf = False
            t = S.add_tdcslist()
            t.currents = [vrm.CURRENT_A, -vrm.CURRENT_A]
            for tag, sigma in zip(sph.TAGS, sph.SIGMAS):
                t.cond[tag - 1].value = sigma
                t.cond[tag - 1].name = f"shell{tag}"
            for j, c in enumerate((e, ref)):
                el = t.add_electrode()
                el.channelnr = j + 1
                el.centre = list(c)
                el.shape = "ellipse"
                el.dimensions = [config.ELECTRODE_DIAMETER_MM] * 2
                el.thickness = 2
            run_simnibs(S)
            res = sorted(out.glob("*_scalar.msh")) or sorted(out.glob("*.msh"))
            if not res:
                raise RuntimeError(f"no result mesh in {out}")
            m = mesh_io.read_msh(str(res[0]))
            if "E" not in m.field:
                raise RuntimeError(f"no vector E in {res[0]}")
            data = vrm.assert_vector_field(m.field["E"].value, "E")
            idx = m.find_closest_element(pts, return_index=True)[1] - 1
            E_all[r, i] = data[idx]
        print(f"  draw {r} done ({len(elecs)} solves)", flush=True)

    npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez(npz, pts=np.array(P), dirs=np.array(D), elecs=np.array(EL),
             ref=np.array(RF), E=E_all, current=vrm.CURRENT_A,
             angles=np.array([m[0] for m in meta]),
             mesh=str(mesh),
             env_simnibs=json.dumps(vrm.env_fingerprint()))
    print(f"\nwrote {npz}")
    return 0


def phase_analytic(npz: Path, out_txt: Path) -> int:
    import mne
    mne.set_log_level("ERROR")

    if not npz.exists():
        print(f"ERROR: {npz} missing; run --phase simnibs first",
              file=sys.stderr)
        return 1

    d = np.load(npz, allow_pickle=True)
    P, D, EL, RF, E = d["pts"], d["dirs"], d["elecs"], d["ref"], d["E"]
    cur = float(d["current"])
    angles = d["angles"]
    n_draws, n_el = E.shape[0], E.shape[1]

    radii = [r / 1000.0 for r in sph.shell_radii_mm()]
    head_r = radii[-1]
    bem = mne.make_sphere_model(r0=(0., 0., 0.), head_radius=head_r,
                                relative_radii=[r / head_r for r in radii],
                                sigmas=list(sph.SIGMAS), verbose=False)

    med_mag, med_rdm = [], []
    per_el_mag = np.zeros((n_draws, n_el))

    for r in range(n_draws):
        pts, dirs, elecs, ref = P[r], D[r], EL[r], RF[r]
        L_num = np.einsum("isk,sk->si", E[r], dirs) / cur

        allpos = np.vstack([elecs, ref[None, :]])
        names = [f"E{i}" for i in range(len(allpos))]
        info = mne.create_info(names, 1000.0, "eeg")
        info.set_montage(mne.channels.make_dig_montage(
            ch_pos={n: p / 1000.0 for n, p in zip(names, allpos)},
            coord_frame="head"))
        src = mne.setup_volume_source_space(
            pos={"rr": pts / 1000.0,
                 "nn": dirs / np.linalg.norm(dirs, axis=1, keepdims=True)},
            sphere_units="m", verbose=False)
        fwd = mne.make_forward_solution(info, trans=None, src=src, bem=bem,
                                        eeg=True, meg=False, verbose=False)
        fwd = mne.convert_forward_solution(fwd, force_fixed=True,
                                           use_cps=False, verbose=False)
        V = fwd["sol"]["data"].T
        L_ana = V[:, :n_el] - V[:, [n_el]]

        s = np.sign(np.sum(L_num * L_ana))
        A = s * L_num
        na = np.linalg.norm(A, axis=1)
        nb = np.linalg.norm(L_ana, axis=1)
        good = (na > 0) & (nb > 0)
        rdm = np.full(len(A), np.nan)
        mag = np.full(len(A), np.nan)
        rdm[good] = 50.0 * np.linalg.norm(
            A[good] / na[good, None] - L_ana[good] / nb[good, None], axis=1)
        mag[good] = 100.0 * (na[good] / nb[good] - 1.0)
        med_mag.append(float(np.nanmedian(mag)))
        med_rdm.append(float(np.nanmedian(rdm)))

        # estimator 2: per-ELECTRODE magnitude error, column norms over sources
        cn, ca = np.linalg.norm(A, axis=0), np.linalg.norm(L_ana, axis=0)
        per_el_mag[r] = 100.0 * (cn / ca - 1.0)

    med_mag = np.array(med_mag)
    med_rdm = np.array(med_rdm)

    def to_db(pp):
        return 20.0 * np.log10(1.0 + pp / 100.0)

    lines = []

    def say(s=""):
        print(s)
        lines.append(s)

    say("=" * 68)
    say("ELECTRODE-MESHING FLOOR, n = %d DRAWS" % n_draws)
    say("=" * 68)
    say(f"mesh held fixed : {Path(str(d['mesh'])).name}")
    say(f"electrode       : {config.ELECTRODE_DIAMETER_MM} mm")
    say("a draw          : one rigid rotation of electrodes AND sources")
    say("                  (relative geometry invariant -> exact answer")
    say("                   invariant -> all spread is realisation noise)")
    say("")
    say(f"{'draw':>5}{'rot deg':>10}{'median MAG %':>15}{'median RDM %':>15}")
    say("-" * 45)
    for r in range(n_draws):
        say(f"{r:>5}{angles[r]:>10.2f}{med_mag[r]:>+15.3f}{med_rdm[r]:>15.3f}")

    sd = float(np.std(med_mag, ddof=1))
    pair = np.abs(med_mag[:, None] - med_mag[None, :])
    iu = np.triu_indices(n_draws, k=1)
    mean_pair = float(pair[iu].mean())
    max_pair = float(pair[iu].max())

    say("")
    say("ESTIMATOR 1 -- median MAG across sources (the REGISTERED estimator,")
    say("               directly comparable to the n=2 figure)")
    say(f"  mean            : {med_mag.mean():+.3f} pp")
    say(f"  SD (n={n_draws})       : {sd:.3f} pp   -> {to_db(sd):.4f} dB")
    say(f"  mean |pairwise| : {mean_pair:.3f} pp   -> {to_db(mean_pair):.4f} dB")
    say(f"  max  |pairwise| : {max_pair:.3f} pp   -> {to_db(max_pair):.4f} dB")
    say("")
    say("  The n=2 measurement was ONE pairwise difference (1.5198 pp,")
    say("  0.1310 dB). Its expectation for normal data is 2*sd/sqrt(pi)")
    say(f"  = {2 * sd / np.sqrt(np.pi):.3f} pp, so a single difference estimates")
    say("  ~1.13 sd with enormous relative uncertainty. Quote the SD.")

    el_sd = per_el_mag.std(axis=0, ddof=1)
    say("")
    say("ESTIMATOR 2 -- per-ELECTRODE MAG (the per-SITE quantity the floor is")
    say("               actually USED as: criterion (b) tests a per-electrode")
    say("               residual, Fig 5 asks whether two SITES differ)")
    say(f"  per-electrode SD across draws, {n_el} electrodes:")
    say(f"    median : {np.median(el_sd):.3f} pp  -> {to_db(np.median(el_sd)):.4f} dB")
    say(f"    mean   : {el_sd.mean():.3f} pp  -> {to_db(el_sd.mean()):.4f} dB")
    say(f"    max    : {el_sd.max():.3f} pp  -> {to_db(el_sd.max()):.4f} dB")
    say("")
    say("RECOMMENDED REPORTING")
    say(f"  floor = {to_db(el_sd.mean()):.3f} dB  "
        f"(per-site, mean over {n_el} electrodes, n={n_draws} draws)")
    say(f"  spread across sites: {to_db(el_sd.min()):.3f} to "
        f"{to_db(el_sd.max()):.3f} dB")
    say("")
    say("  Report to TWO decimals, not four. The underlying spread does not")
    say("  support more, and the previous 0.1310 dB implied precision that")
    say("  a single difference cannot carry.")

    out_txt.parent.mkdir(parents=True, exist_ok=True)
    out_txt.write_text("\n".join(lines) + "\n")

    npz_out = out_txt.parent / "electrode_floor_draws.npz"
    np.savez(npz_out, med_mag=med_mag, med_rdm=med_rdm,
             per_el_mag=per_el_mag, angles=angles)
    print(f"\nWritten: {out_txt}")
    print(f"Written: {npz_out}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="measure_floor_multidraw.py")
    ap.add_argument("--phase", choices=("simnibs", "analytic"), required=True)
    ap.add_argument("--mesh", type=Path,
                    default=config.DATA / "val_sphere_medium.msh")
    ap.add_argument("--workdir", type=Path,
                    default=config.RESULTS / "floor_draws")
    ap.add_argument("--npz", type=Path,
                    default=config.RESULTS / "floor_draws_fields.npz")
    ap.add_argument("--out", type=Path,
                    default=config.RESULTS / "electrode_floor_multidraw.txt")
    a = ap.parse_args(argv)
    if a.phase == "simnibs":
        return phase_simnibs(a.mesh, a.workdir, a.npz)
    return phase_analytic(a.npz, a.out)


if __name__ == "__main__":
    sys.exit(main())
