#!/usr/bin/env python3
"""
Reciprocity validation reported as RDM and MAG, the conventional EEG
forward-model validation pair.

WHY THIS REPLACES THE RATIO AS THE HEADLINE

The bipolar ratio L_recip/L_analytic needed a conditioning restriction to be
readable: a source oriented nearly perpendicular to the reciprocal field makes
the denominator vanish, so the ratio explodes for reasons that have nothing to
do with solver accuracy. Reporting a headline number that depends on an
exclusion criterion is a bad habit. RDM and MAG are computed over the whole
electrode topography per source, are the standard in this literature, and need
no exclusions.

DEFINITIONS (Meijs et al. 1989; the pair used throughout the EEG forward
literature, e.g. Wolters and colleagues' FEM validation work):

    RDM(%) = 50 * || u_num/||u_num||  -  u_ana/||u_ana|| ||
    MAG(%) = 100 * ( ||u_num|| / ||u_ana||  -  1 )

RDM measures topography error, is bounded 0-100, optimum 0. MAG measures
magnitude error, optimum 0, unbounded above and bounded by -100 below.
u is the vector of electrode potentials for one source.

RDM is degenerate for a single bipolar pair -- with one number per source the
normalised "topography" is just a sign. So this builds a proper lead field
matrix: N electrodes, each solved against a common reference, giving
L[source, electrode].

Two phases, since simnibs and mne live in different interpreters:
    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/val_rdm_mag.py --phase simnibs
    .venv/bin/python                              src/val_rdm_mag.py --phase analytic
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402
import val_sphere_build as sph  # noqa: E402

N_ELECTRODES = 16
CURRENT_A = 1e-3
SOURCE_RADII_MM = (20.0, 40.0, 60.0, 70.0, 75.0)
N_POS_PER_RADIUS = 6


def electrode_positions(n=N_ELECTRODES):
    """n+1 points on the outer sphere; the last is the common reference."""
    r = sph.shell_radii_mm()[-1]
    k = np.arange(n, dtype=float) + 0.5
    z = 1.0 - 2.0 * k / n
    rho = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    phi = np.pi * (1.0 + 5.0 ** 0.5) * k
    pts = np.column_stack((rho * np.cos(phi), rho * np.sin(phi), z)) * r
    ref = np.array([0.0, 0.0, -r])
    return pts, ref


def source_points(seed=0):
    rng = np.random.default_rng(seed)
    pts, dirs = [], []
    for rad in SOURCE_RADII_MM:
        for _ in range(N_POS_PER_RADIUS):
            v = rng.normal(size=3)
            v /= np.linalg.norm(v)
            p = v * rad
            for n in (np.array([1.0, 0, 0]), np.array([0, 1.0, 0]),
                      np.array([0, 0, 1.0]), p / np.linalg.norm(p)):
                pts.append(p)
                dirs.append(n / np.linalg.norm(n))
    return np.array(pts), np.array(dirs)


def assert_vector_field(arr, name="E"):
    """Hard shape gate. SESSION.fields='e' silently writes |E|, and projecting
    a magnitude onto an orientation would corrupt every lead field with no
    error raised. This is the check that turns that into a loud failure."""
    a = np.asarray(arr)
    if a.ndim != 2 or a.shape[1] != 3:
        raise RuntimeError(
            f"{name} must be a vector field of shape (n, 3); got {a.shape}. "
            f"If this is (n,), SESSION.fields contained lowercase 'e' (which "
            f"writes |E|) instead of uppercase 'E'.")
    return a


def env_fingerprint():
    info = {"python": sys.version.split()[0], "platform": platform.platform()}
    try:
        import simnibs
        info["simnibs"] = simnibs.__version__
    except Exception:
        pass
    for mod in ("numpy", "scipy", "mne", "nibabel"):
        try:
            info[mod] = __import__(mod).__version__
        except Exception:
            pass
    return info


def phase_simnibs(mesh: Path, workdir: Path, npz: Path):
    from simnibs import sim_struct, run_simnibs, mesh_io

    pts, dirs = source_points()
    elecs, ref = electrode_positions()
    print(f"{len(pts)} sources, {len(elecs)} electrodes + 1 reference")
    print(f"{len(elecs)} reciprocal solves (each electrode against the "
          f"reference)\n")

    E_all = np.zeros((len(elecs), len(pts), 3))
    for i, e in enumerate(elecs):
        out = workdir / f"e{i:02d}"
        out.parent.mkdir(parents=True, exist_ok=True)
        S = sim_struct.SESSION()
        S.fnamehead = str(mesh)
        S.pathfem = str(out)
        S.fields = "E"                     # uppercase: VECTOR field
        S.open_in_gmsh = False
        S.map_to_surf = False
        t = S.add_tdcslist()
        t.currents = [CURRENT_A, -CURRENT_A]
        for tag, sigma in zip(sph.TAGS, sph.SIGMAS):
            t.cond[tag - 1].value = sigma
            t.cond[tag - 1].name = f"shell{tag}"
        for j, c in enumerate((e, ref)):
            el = t.add_electrode()
            el.channelnr = j + 1
            el.centre = list(c)
            el.shape = "ellipse"
            # geometry ALWAYS from config -- a hardcoded diameter here
            # is what left validation on a 15/20 mm electrode while
            # production ran 10 mm, silently invalidating the
            # electrode-meshing floor.
            el.dimensions = [config.ELECTRODE_DIAMETER_MM] * 2
            el.thickness = 2
        run_simnibs(S)
        res = sorted(out.glob("*_scalar.msh")) or sorted(out.glob("*.msh"))
        m = mesh_io.read_msh(str(res[0]))
        if "E" not in m.field:
            raise RuntimeError(f"no vector E in {res[0]}; have {list(m.field)}")
        data = m.field["E"].value
        assert_vector_field(data, "E")
        idx = m.find_closest_element(pts, return_index=True)[1] - 1
        E_all[i] = data[idx]
        print(f"  electrode {i:>2}/{len(elecs)} done", flush=True)

    npz.parent.mkdir(parents=True, exist_ok=True)
    np.savez(npz, pts=pts, dirs=dirs, elecs=elecs, ref=ref, E=E_all,
             current=CURRENT_A,
             env_simnibs=json.dumps(env_fingerprint()))
    print(f"\nwrote {npz}")


def phase_analytic(npz: Path, out_csv: Path):
    import mne
    mne.set_log_level("ERROR")

    d = np.load(npz, allow_pickle=True)
    pts, dirs, elecs, ref = d["pts"], d["dirs"], d["elecs"], d["ref"]
    E = d["E"]
    cur = float(d["current"])

    # numerical lead field: L[s, i] = E_i(r_s) . n_s / I
    L_num = np.einsum("isk,sk->si", E, dirs) / cur

    radii = [r / 1000.0 for r in sph.shell_radii_mm()]
    head_r = radii[-1]
    bem = mne.make_sphere_model(r0=(0., 0., 0.), head_radius=head_r,
                                relative_radii=[r / head_r for r in radii],
                                sigmas=list(sph.SIGMAS), verbose=False)
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
    fwd = mne.convert_forward_solution(fwd, force_fixed=True, use_cps=False,
                                       verbose=False)
    V = fwd["sol"]["data"].T                     # (n_sources, n_channels)
    L_ana = V[:, :len(elecs)] - V[:, [len(elecs)]]

    def rdm_mag(a, b):
        na = np.linalg.norm(a, axis=1)
        nb = np.linalg.norm(b, axis=1)
        good = (na > 0) & (nb > 0)
        rdm = np.full(len(a), np.nan)
        mag = np.full(len(a), np.nan)
        rdm[good] = 50.0 * np.linalg.norm(
            a[good] / na[good, None] - b[good] / nb[good, None], axis=1)
        mag[good] = 100.0 * (na[good] / nb[good] - 1.0)
        return rdm, mag

    # Sign convention: the reciprocal field and the analytic potential differ
    # by a fixed global polarity (which node is the anode, sign of E = -grad V).
    # Determined once from the aggregate, never per sample, so it cannot absorb
    # a real error.
    s = np.sign(np.sum(L_num * L_ana))
    RDM, MAG = rdm_mag(s * L_num, L_ana)

    print(f"global polarity convention factor: {s:+.0f} "
          f"(applied once, not per sample)\n")
    print(f"RDM (%)  topography error, 0 = perfect, over ALL {len(pts)} "
          f"sources, no exclusions")
    for lbl, v in (("median", np.nanmedian(RDM)), ("mean", np.nanmean(RDM)),
                   ("90th pct", np.nanpercentile(RDM, 90)),
                   ("max", np.nanmax(RDM))):
        print(f"  {lbl:<10}: {v:7.3f}")
    print(f"\nMAG (%)  magnitude error, 0 = perfect")
    for lbl, v in (("median", np.nanmedian(MAG)), ("mean", np.nanmean(MAG)),
                   ("10th pct", np.nanpercentile(MAG, 10)),
                   ("90th pct", np.nanpercentile(MAG, 90))):
        print(f"  {lbl:<10}: {v:+7.3f}")

    r_mm = np.linalg.norm(pts, axis=1)
    print("\nby source radius:")
    print(f"  {'r (mm)':>7} {'n':>4} {'RDM med':>9} {'MAG med':>9} "
          f"{'dist to interface':>18}")
    interfaces = sph.shell_radii_mm()
    for r in SOURCE_RADII_MM:
        k = np.abs(r_mm - r) < 1e-6
        dmin = min(abs(r - b) for b in interfaces)
        print(f"  {r:>7.1f} {int(k.sum()):>4} {np.nanmedian(RDM[k]):>9.3f} "
              f"{np.nanmedian(MAG[k]):>+9.3f} {dmin:>18.1f}")

    # ---- item 3: error vs distance to the nearest conductivity interface
    dist_if = np.array([min(abs(rr - b) for b in interfaces) for rr in r_mm])
    print("\nERROR vs DISTANCE TO NEAREST CONDUCTIVITY INTERFACE")
    edges = [0, 5, 10, 20, 40, 100]
    print(f"  {'band (mm)':>12} {'n':>4} {'RDM med':>9} {'MAG med':>9}")
    for lo, hi in zip(edges[:-1], edges[1:]):
        k = (dist_if >= lo) & (dist_if < hi)
        if k.any():
            print(f"  {f'{lo}-{hi}':>12} {int(k.sum()):>4} "
                  f"{np.nanmedian(RDM[k]):>9.3f} {np.nanmedian(MAG[k]):>+9.3f}")
    ok = np.isfinite(RDM)
    if ok.sum() > 3:
        cc = np.corrcoef(dist_if[ok], RDM[ok])[0, 1]
        print(f"\n  correlation(distance to interface, RDM) = {cc:+.3f}")

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["x_mm", "y_mm", "z_mm", "r_mm", "nx", "ny", "nz",
                    "dist_to_interface_mm", "RDM_pct", "MAG_pct"])
        for i in range(len(pts)):
            w.writerow([*np.round(pts[i], 3), round(float(r_mm[i]), 3),
                        *np.round(dirs[i], 4), round(float(dist_if[i]), 3),
                        round(float(RDM[i]), 5), round(float(MAG[i]), 5)])
    env = {"analytic_phase": env_fingerprint(),
           "simnibs_phase": json.loads(str(d["env_simnibs"]))}
    (out_csv.parent / "val_environments.json").write_text(
        json.dumps(env, indent=2), encoding="utf-8")
    print(f"\nWritten: {out_csv}")
    print(f"Written: {out_csv.parent / 'val_environments.json'}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="val_rdm_mag.py")
    ap.add_argument("--phase", choices=("simnibs", "analytic"), required=True)
    ap.add_argument("--mesh", type=Path, default=config.DATA / "val_sphere.msh")
    ap.add_argument("--workdir", type=Path,
                    default=config.RESULTS / "val_rdm_mag")
    ap.add_argument("--npz", type=Path,
                    default=config.RESULTS / "val_rdm_mag_fields.npz")
    ap.add_argument("--out", type=Path,
                    default=config.RESULTS / "val_rdm_mag.csv")
    a = ap.parse_args(argv)
    if a.phase == "simnibs":
        if not a.mesh.exists():
            print(f"ERROR: no mesh at {a.mesh}", file=sys.stderr)
            return 1
        phase_simnibs(a.mesh, a.workdir, a.npz)
    else:
        if not a.npz.exists():
            print(f"ERROR: {a.npz} missing; run --phase simnibs first",
                  file=sys.stderr)
            return 1
        phase_analytic(a.npz, a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
