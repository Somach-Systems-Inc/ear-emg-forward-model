#!/usr/bin/env python3
"""
Reciprocity validation against the analytic multilayer sphere.

THE CLAIM BEING TESTED

For a current dipole of moment p at position r, and electrodes A and B, the
measured potential difference is

    V_AB(r, p) = E_recip(r) . p / I

where E_recip is the field from injecting current I at A and withdrawing it at
B. That identity is the entire basis of this paper's method: it is why ~20
solves replace one solve per source. If it does not hold numerically, nothing
downstream means anything.

WHY A SPHERE AND NOT THE HEAD MESH

Comparing a reciprocal solve against a direct dipole solve on the head mesh
proves only that two numerical paths agree. A units error, a sign error or a
missing 1/sigma corrupts both identically and the check passes while being
wrong. The analytic multilayer sphere is absolute ground truth, so a systematic
error has nowhere to hide. MNE-Python supplies the series expansion; we do not
reimplement it.

Reported as a RATIO DISTRIBUTION across radii, depths and orientations, not a
pass/fail, because the interesting output is the size and structure of any
disagreement.

Two invariants are checked as well, both of which catch sign and scaling bugs
that a ratio near 1 can mask:
  - swapping source and sink flips the sign and preserves the magnitude
  - the lead field is linear in injection current

Run AFTER data/val_sphere.msh exists:
    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/val_reciprocity.py
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402
import val_sphere_build as sph  # noqa: E402

# electrode pair, on the outer surface, in mm
ELEC_A = np.array([0.0, 0.0, 90.0])
ELEC_B = np.array([0.0, 0.0, -90.0])
CURRENT_A = 1e-3

SOURCE_RADII_MM = (20.0, 40.0, 60.0, 70.0, 75.0)
N_DIR_PER_RADIUS = 6


def source_points(seed=0):
    """Sample source positions and orientations across radii and directions."""
    rng = np.random.default_rng(seed)
    pts, dirs = [], []
    for r in SOURCE_RADII_MM:
        for k in range(N_DIR_PER_RADIUS):
            v = rng.normal(size=3)
            v /= np.linalg.norm(v)
            p = v * r
            for n in (np.array([1.0, 0, 0]), np.array([0, 1.0, 0]),
                      np.array([0, 0, 1.0]),
                      p / np.linalg.norm(p)):          # radial
                pts.append(p)
                dirs.append(n / np.linalg.norm(n))
    return np.array(pts), np.array(dirs)


def analytic_leadfield(pts_mm, dirs, elec_mm):
    """V per unit dipole moment at each electrode, from MNE's sphere model.

    Returns (n_points, n_elec) in V / (A m).
    """
    import mne
    mne.set_log_level("ERROR")

    radii = [r / 1000.0 for r in sph.shell_radii_mm()]
    head_r = radii[-1]
    bem = mne.make_sphere_model(
        r0=(0.0, 0.0, 0.0), head_radius=head_r,
        relative_radii=[r / head_r for r in radii],
        sigmas=list(sph.SIGMAS), verbose=False)

    n_e = len(elec_mm)
    names = [f"E{i}" for i in range(n_e)]
    info = mne.create_info(names, 1000.0, "eeg")
    mont = mne.channels.make_dig_montage(
        ch_pos={nm: (p / 1000.0) for nm, p in zip(names, elec_mm)},
        coord_frame="head")
    info.set_montage(mont)

    rr = pts_mm / 1000.0
    nn = dirs / np.linalg.norm(dirs, axis=1, keepdims=True)
    src = mne.setup_volume_source_space(
        pos={"rr": rr, "nn": nn}, sphere_units="m", verbose=False)
    fwd = mne.make_forward_solution(
        info, trans=None, src=src, bem=bem, eeg=True, meg=False,
        verbose=False)
    fwd = mne.convert_forward_solution(
        fwd, force_fixed=True, use_cps=False, verbose=False)
    # (n_channels, n_sources) with the source orientations we supplied
    return fwd["sol"]["data"].T


def run_simnibs(mesh_path: Path, out_dir: Path, current: float,
                swap: bool = False):
    """Reciprocal solve: inject `current` at A, withdraw at B."""
    from simnibs import sim_struct, run_simnibs

    # SimNIBS calls os.mkdir, which will not create intermediate directories.
    out_dir.parent.mkdir(parents=True, exist_ok=True)

    S = sim_struct.SESSION()
    S.fnamehead = str(mesh_path)
    S.pathfem = str(out_dir)
    # Uppercase E is the VECTOR field. Lowercase e writes only |E|, which
    # cannot be projected onto a source orientation.
    S.fields = "E"
    S.open_in_gmsh = False
    S.map_to_surf = False

    t = S.add_tdcslist()
    t.currents = [current, -current] if not swap else [-current, current]
    for tag, sigma in zip(sph.TAGS, sph.SIGMAS):
        t.cond[tag - 1].value = sigma
        t.cond[tag - 1].name = f"shell{tag}"
    for centre in (ELEC_A, ELEC_B):
        el = t.add_electrode()
        el.channelnr = 1 if centre is ELEC_A else 2
        el.centre = list(centre)
        el.shape = "ellipse"
        # geometry ALWAYS from config -- a hardcoded diameter here is what
        # left the validation on a 15/20 mm electrode while production ran
        # 10 mm, silently invalidating the electrode-meshing floor.
        el.dimensions = [config.ELECTRODE_DIAMETER_MM] * 2
        el.thickness = 2
    run_simnibs(S)
    hits = sorted(out_dir.glob("*_scalar.msh")) or sorted(out_dir.glob("*.msh"))
    if not hits:
        raise RuntimeError(f"no result mesh in {out_dir}")
    return hits[0]


def sample_E(result_msh: Path, pts_mm):
    """E (V/m) at each point, from the element containing it."""
    from simnibs import mesh_io
    m = mesh_io.read_msh(str(result_msh))
    if "E" not in m.field:
        raise RuntimeError(
            f"no vector E in {result_msh}; have {list(m.field)}. "
            f"SESSION.fields must contain uppercase 'E' -- lowercase 'e' "
            f"writes only |E|, which cannot be projected onto an orientation.")
    fld = m.field["E"]
    data = fld.value if hasattr(fld, "value") else np.asarray(fld)
    if data.ndim != 2 or data.shape[1] != 3:
        raise RuntimeError(f"expected vector E, got shape {data.shape}")
    idx = m.find_closest_element(pts_mm, return_index=True)[1] - 1
    return data[idx]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="val_reciprocity.py",
        description="Two phases, because simnibs and mne live in different "
                    "interpreters. Run --phase simnibs under simnibs_python, "
                    "then --phase analytic under the project venv.")
    ap.add_argument("--phase", choices=("simnibs", "analytic"), required=True)
    ap.add_argument("--mesh", type=Path, default=config.DATA / "val_sphere.msh")
    ap.add_argument("--workdir", type=Path,
                    default=config.RESULTS / "val_reciprocity")
    ap.add_argument("--npz", type=Path,
                    default=config.RESULTS / "val_reciprocity_fields.npz")
    ap.add_argument("--out", type=Path,
                    default=config.RESULTS / "val_reciprocity.csv")
    a = ap.parse_args(argv)

    pts, dirs = source_points()

    # ---------------- phase 1: the numerical (reciprocal) side ----------
    if a.phase == "simnibs":
        if not a.mesh.exists():
            print(f"ERROR: sphere mesh not found at {a.mesh}\n"
                  f"  build it first:\n"
                  f"    python src/val_sphere_build.py --voxel 0.5\n"
                  f"    meshmesh data/val_sphere.nii.gz data/val_sphere.msh",
                  file=sys.stderr)
            return 1
        print(f"{len(pts)} source samples over radii "
              f"{list(SOURCE_RADII_MM)} mm\n")
        print("reciprocal solve, base ...", flush=True)
        E = sample_E(run_simnibs(a.mesh, a.workdir / "base", CURRENT_A), pts)
        print("reciprocal solve, swapped polarity ...", flush=True)
        E_s = sample_E(run_simnibs(a.mesh, a.workdir / "swap", CURRENT_A,
                                   swap=True), pts)
        print("reciprocal solve, doubled current ...", flush=True)
        E_2 = sample_E(run_simnibs(a.mesh, a.workdir / "double",
                                   2 * CURRENT_A), pts)
        a.npz.parent.mkdir(parents=True, exist_ok=True)
        np.savez(a.npz, pts=pts, dirs=dirs, E=E, E_swap=E_s, E_double=E_2,
                 current=CURRENT_A)
        print(f"\nwrote {a.npz}\nnow run --phase analytic under the venv")
        return 0

    # ---------------- phase 2: the analytic oracle + comparison ---------
    if not a.npz.exists():
        print(f"ERROR: {a.npz} missing. Run --phase simnibs first.",
              file=sys.stderr)
        return 1
    d = np.load(a.npz)
    pts, dirs = d["pts"], d["dirs"]
    E, E_s, E_2 = d["E"], d["E_swap"], d["E_double"]
    cur = float(d["current"])

    print(f"{len(pts)} source samples over radii "
          f"{list(SOURCE_RADII_MM)} mm\n")
    print("analytic sphere (MNE) ...", flush=True)
    V = analytic_leadfield(pts, dirs, np.array([ELEC_A, ELEC_B]))
    L_analytic = V[:, 0] - V[:, 1]          # V per unit dipole moment
    L_recip = np.einsum("ij,ij->i", E, dirs) / cur

    ok = np.isfinite(L_analytic) & np.isfinite(L_recip) & (np.abs(L_analytic) > 0)
    ratio = np.full(len(pts), np.nan)
    ratio[ok] = L_recip[ok] / L_analytic[ok]

    r_mm = np.linalg.norm(pts, axis=1)

    # Sign first. A uniform sign flip is a convention difference (which node is
    # the anode, and whether E is -grad V), not an error, and it must be
    # reported separately from magnitude or it contaminates every statistic.
    neg = float(np.mean(ratio[ok] < 0))
    absA_ = np.abs(L_analytic)
    thr_ = np.nanpercentile(absA_[ok], 50)
    strong = ok & (absA_ >= thr_)
    weak = ok & (absA_ < thr_)
    print("\nSIGN")
    print(f"  negative ratio, all samples          : {neg:.3f}")
    print(f"  negative ratio, well-conditioned half: "
          f"{float(np.mean(ratio[strong] < 0)):.3f}")
    print(f"  negative ratio, weakest half         : "
          f"{float(np.mean(ratio[weak] < 0)):.3f}")
    print("  A uniform flip is a polarity convention (which node is the anode,")
    print("  and the sign of E = -grad V), not an error. Exceptions confined to")
    print("  the weakest signals are conditioning noise; a sign flip among the")
    print("  well-conditioned samples would be a real defect.")

    mag = np.abs(ratio)
    print("\nMAGNITUDE  |L_reciprocal / L_analytic|   (1.0 = exact)")
    print(f"  n           : {int(ok.sum())}")
    print(f"  median      : {np.nanmedian(mag):.4f}")
    print(f"  IQR         : {np.nanpercentile(mag,25):.4f} .. "
          f"{np.nanpercentile(mag,75):.4f}")
    print(f"  5-95 pct    : {np.nanpercentile(mag,5):.4f} .. "
          f"{np.nanpercentile(mag,95):.4f}")

    # Conditioning. Where L_analytic is near zero the ratio is dominated by a
    # vanishing denominator, not by solver error -- a source whose orientation
    # is nearly perpendicular to the reciprocal field produces almost no signal
    # by construction. Report the well-conditioned subset separately.
    absA = np.abs(L_analytic)
    thr = np.nanpercentile(absA[ok], 50)
    well = ok & (absA >= thr)
    print(f"\n  restricted to the {int(well.sum())} best-conditioned samples "
          f"(|L_analytic| above its median):")
    print(f"    median   : {np.nanmedian(mag[well]):.4f}")
    print(f"    IQR      : {np.nanpercentile(mag[well],25):.4f} .. "
          f"{np.nanpercentile(mag[well],75):.4f}")
    print(f"    5-95 pct : {np.nanpercentile(mag[well],5):.4f} .. "
          f"{np.nanpercentile(mag[well],95):.4f}")

    print("\n  by source radius (magnitude, well-conditioned only):")
    for r in SOURCE_RADII_MM:
        k = well & (np.abs(r_mm - r) < 1e-6)
        if k.any():
            print(f"    r={r:5.1f} mm  n={int(k.sum()):>3}  "
                  f"median {np.nanmedian(mag[k]):.4f}  "
                  f"5-95 {np.nanpercentile(mag[k],5):.3f}-"
                  f"{np.nanpercentile(mag[k],95):.3f}")

    # Scale-free cross-check that does not divide at all.
    good_lin = ok
    num = float(np.sum(np.abs(L_recip[good_lin]) * np.abs(L_analytic[good_lin])))
    den = float(np.sum(L_analytic[good_lin] ** 2))
    print(f"\n  least-squares scale factor |L_recip| ~ k|L_analytic| : "
          f"k = {num/den:.4f}")
    cc = np.corrcoef(np.abs(L_recip[good_lin]), np.abs(L_analytic[good_lin]))[0, 1]
    print(f"  correlation of magnitudes                            : r = {cc:.5f}")

    # ---- invariant 1: swapping source and sink -------------------------
    print("\nINVARIANT 1  swap source and sink -> sign flips, magnitude preserved")
    L_s = np.einsum("ij,ij->i", E_s, dirs) / cur
    good = np.abs(L_recip) > 0
    rel = (L_s[good] + L_recip[good]) / np.abs(L_recip[good])
    print(f"  max |L_swap + L_base| / |L_base| : {np.nanmax(np.abs(rel)):.3e}"
          f"   (0 = perfect antisymmetry)")

    # ---- invariant 2: linearity in injection current -------------------
    print("\nINVARIANT 2  lead field is linear in injection current")
    L_2 = np.einsum("ij,ij->i", E_2, dirs) / (2 * cur)
    rel2 = (L_2[good] - L_recip[good]) / np.abs(L_recip[good])
    print(f"  max |L(2I) - L(I)| / |L(I)|      : {np.nanmax(np.abs(rel2)):.3e}"
          f"   (0 = perfectly linear)")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["x_mm", "y_mm", "z_mm", "r_mm", "nx", "ny", "nz",
                    "L_analytic", "L_reciprocal", "ratio"])
        for i in range(len(pts)):
            w.writerow([*np.round(pts[i], 3), round(float(r_mm[i]), 3),
                        *np.round(dirs[i], 4),
                        L_analytic[i], L_recip[i], ratio[i]])
    print(f"\nWritten: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
