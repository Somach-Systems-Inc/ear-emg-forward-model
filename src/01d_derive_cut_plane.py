#!/usr/bin/env python3
"""
Stage 1d -- DERIVE the inferior cut plane from the mesh. Emit it to a results
file. Nothing downstream may hardcode it.

WHY THIS EXISTS

`CUT_FACE_S = -116.2` was a bare literal in seven files. It governed the 10 mm
near-cut exclusion set, which set the jaw site list, which set every matched-count
gap in Table 4. Every consumer agreed with every other consumer because all of
them inherited the same number, so internal consistency was evidence of nothing.

Two things were wrong with it, and they are separate:

  1. It was never derived. See CLAUDE.md, "asserted constant governing selection".
  2. **A tilted plane has no single S.** The face is tilted 2.664 deg off the S
     axis, so it spans S -122.07 to -110.18 across its own lateral extent. No
     scalar can represent it. Replacing -116.2 with a better scalar would
     reintroduce the identical defect, which is why this script emits a NORMAL
     and a POINT and never an S.

The face is real. An earlier session concluded it did not exist, from a histogram
of all 2.1M node S-coordinates that showed a smooth taper. That test cannot see
this object: it bins by RAS z, and a plane tilted 2.664 deg across a 180 mm
lateral extent is smeared over 11.9 mm of S by construction, while ~4,000 interior
nodes per mm bin swamp the ~12,000 that form the entire face. The taper it
recorded is exactly what a tilted plane produces under that test.

CHANNEL: correctness, with an independent expectation the fit never sees. If this
face is MIDA's own label-volume grid boundary, the fitted normal must equal the
voxel superior axis in RAS, which comes from the .nii affine and from no mesh.
Measured agreement: 0.0023 deg. That, not the residual, is the load-bearing
support.

    python src/01d_derive_cut_plane.py
    python src/01d_derive_cut_plane.py --self-test    # guard must fire
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

# Selection parameters. Both are swept in the METHODS_LOG entry of 2026-08-05 and
# neither is load-bearing: over |n_z| in 0.95..0.995 the fitted normal moves by
# 0.004 deg and the tilt by 0.004 deg.
#
# 0.999 and 0.9999 are NOT admissible and must not be used. They define cones of
# half-angle 2.56 and 0.81 deg, both narrower than the face's own 2.664 deg tilt,
# so they reject the bulk of the face by construction and fit a skewed remnant
# (18,818 triangles collapse to 2,927 and then 112).
NZ_THRESHOLD = 0.99          # 8.11 deg cone; face tilt is 2.664 deg
BAND_DEPTH_MM = 12.0         # inferior band the face is selected from

# PLANARITY GUARD. Derived from a control ladder, not chosen to pass.
# Synthetic fixtures through this same fit, in the same session:
#     flat cap ................. 0.0200 mm     tilted flat cap ... 0.0198 mm
#     0.5 mm voxel staircase ... 0.9777 mm     cone / taper ...... 9.2347 mm
# The real base mesh returns 0.0726 mm. 0.50 mm sits an order of magnitude above
# every planar fixture and an order of magnitude below the staircase, which is
# the nearest non-planar object this could be confused with.
MAX_PLANAR_RMS_MM = 0.50


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fit_plane(pts, w):
    """Area-weighted total-least-squares plane. Returns (unit normal oriented
    downward, point on the plane, residual RMS)."""
    import numpy as np
    w = w / w.sum()
    c = (pts * w[:, None]).sum(0)
    X = (pts - c) * np.sqrt(w)[:, None]
    _, _, vt = np.linalg.svd(X, full_matrices=False)
    n = vt[-1]
    if n[2] > 0:
        n = -n
    res = (pts - c) @ n
    return n, c, float(np.sqrt(np.average(res ** 2, weights=w)))


def inferior_face(mesh_path, nz_threshold=NZ_THRESHOLD, depth=BAND_DEPTH_MM):
    """Boundary triangles forming the inferior termination."""
    import numpy as np
    from simnibs import mesh_io
    m = mesh_io.read_msh(str(mesh_path))
    v = m.nodes.node_coord
    tri = m.elm.elm_type == 2
    tn = m.elm.node_number_list[tri][:, :3] - 1
    a, b, c = v[tn[:, 0]], v[tn[:, 1]], v[tn[:, 2]]
    cr = np.cross(b - a, c - a)
    twice = np.linalg.norm(cr, axis=1)
    ok = twice > 0
    n = np.zeros_like(cr)
    n[ok] = cr[ok] / twice[ok][:, None]
    area = 0.5 * twice
    cen = (a + b + c) / 3.0
    sel = (cen[:, 2] <= v[:, 2].min() + depth) & (np.abs(n[:, 2]) >= nz_threshold)
    if sel.sum() < 100:
        raise RuntimeError(
            f"only {int(sel.sum())} candidate face triangles in {mesh_path.name}; "
            f"refusing to fit a plane to that. Check the mesh, not the threshold.")
    return cen[sel], area[sel], v


def derive(mesh_path: Path, nz=NZ_THRESHOLD, depth=BAND_DEPTH_MM, verbose=True):
    import numpy as np
    pts, area, all_nodes = inferior_face(mesh_path, nz, depth)
    n, p, rms = fit_plane(pts, area)

    if rms > MAX_PLANAR_RMS_MM:
        raise RuntimeError(
            f"inferior boundary of {mesh_path.name} is NOT planar: residual RMS "
            f"{rms:.4f} mm exceeds {MAX_PLANAR_RMS_MM} mm. A 0.5 mm voxel "
            f"staircase reads 0.98 mm and a taper 9.23 mm through this same fit. "
            f"Do not relax this bound; the clearance concept does not apply to a "
            f"boundary that is not a plane.")

    # The plane must be the OUTER boundary, not an internal interface: essentially
    # no mesh may lie outside it. This is independent of the fit.
    d = (all_nodes - p) @ n
    outside = int((d > 0.5).sum())
    if outside:
        raise RuntimeError(
            f"{outside:,} nodes lie more than 0.5 mm outside the fitted plane, so "
            f"it is not the outer termination of {mesh_path.name}.")

    tilt = float(np.degrees(np.arccos(min(1.0, abs(n[2])))))

    # INDEPENDENT EXPECTATION. If this face is MIDA's own label-volume grid
    # boundary, the fitted normal must equal the voxel superior axis in RAS.
    # That axis comes from the NIfTI affine, which the fit never sees. This is
    # the correctness partner; the residual is only a fidelity statistic.
    mida = {}
    nii = config.DATA / "MIDA_v1.0/MIDA_v1_voxels/MIDA_v1.nii"
    if nii.exists():
        import nibabel as nib
        aff = nib.load(str(nii)).affine
        ax = int(np.argmax(np.abs(aff[2, :3])))
        v = aff[:3, ax]
        step = float(np.linalg.norm(v))
        v = v / step
        mida = dict(
            mida_axis_r=float(v[0]), mida_axis_a=float(v[1]), mida_axis_s=float(v[2]),
            mida_axis_angle_deg=float(np.degrees(np.arccos(min(1.0, abs(v[2]))))),
            mida_voxel_step_mm=step,
            fit_vs_mida_angle_deg=float(np.degrees(np.arccos(
                min(1.0, abs(float(np.dot(-n, v))))))),
        )

    if verbose:
        print(f"mesh            : {mesh_path}")
        print(f"sha256          : {sha256(mesh_path)}")
        print(f"face triangles  : {len(pts):,}   area {area.sum():,.1f} mm^2")
        print(f"unit normal     : [{n[0]:+.6f} {n[1]:+.6f} {n[2]:+.6f}]")
        print(f"point on plane  : [{p[0]:+.4f} {p[1]:+.4f} {p[2]:+.4f}]")
        print(f"tilt off S      : {tilt:.4f} deg")
        print(f"residual RMS    : {rms:.4f} mm   (guard {MAX_PLANAR_RMS_MM} mm)")
        print(f"max outside     : {float(d.max()):+.4f} mm")
        print(f"S span of face  : {pts[:,2].min():.3f} .. {pts[:,2].max():.3f}  "
              f"-- NOTE: no single S represents this plane")
    if verbose and mida:
        print(f"MIDA voxel axis : [{mida['mida_axis_r']:+.6f} "
              f"{mida['mida_axis_a']:+.6f} {mida['mida_axis_s']:+.6f}]  "
              f"step {mida['mida_voxel_step_mm']:.4f} mm")
        print(f"fit vs MIDA     : {mida['fit_vs_mida_angle_deg']:.4f} deg "
              f"-- the correctness partner, from the .nii the fit never sees")

    return dict(
        nx=n[0], ny=n[1], nz=n[2], px=p[0], py=p[1], pz=p[2],
        tilt_deg=tilt, residual_rms_mm=rms, n_triangles=len(pts),
        area_mm2=float(area.sum()), nz_threshold=nz, band_depth_mm=depth,
        max_node_outside_mm=float(d.max()),
        # A tilted plane has NO single S. These three record that fact in the
        # results file so no consumer can mistake one of them for "the cut".
        mesh_s_min=float(all_nodes[:, 2].min()),
        face_s_low=float(pts[:, 2].min()), face_s_high=float(pts[:, 2].max()),
        **mida,
        mesh=str(mesh_path.relative_to(config.ROOT)), mesh_sha256=sha256(mesh_path),
    )


def self_test():
    """The planarity guard must FIRE on a staircase and on a taper, and must NOT
    fire on a plane. Synthetic, no mesh, no solve."""
    import numpy as np
    rng = np.random.default_rng(0)
    th = np.linspace(0, 2 * np.pi, 200, endpoint=False)
    rr = np.linspace(1, 40, 40)
    R, T = np.meshgrid(rr, th)
    x, y = (R * np.cos(T)).ravel(), (R * np.sin(T)).ravel()
    w = np.ones(x.size)

    cases = [
        ("flat plane, tilted 2.7 deg (must PASS)",
         np.c_[x, y, -182.0 + np.tan(np.radians(2.7)) * x + 0.02 * rng.standard_normal(x.size)],
         False),
        ("0.5 mm voxel staircase (must FAIL)",
         np.c_[x, y, -182.0 + 0.5 * np.round(np.hypot(x, y) / 6.0)], True),
        ("cone / taper (must FAIL)",
         np.c_[x, y, -182.0 + 0.8 * np.hypot(x, y)], True),
    ]
    ok = True
    print(f"planarity guard, bound {MAX_PLANAR_RMS_MM} mm\n")
    for label, pts, must_fail in cases:
        _, _, rms = fit_plane(pts, w)
        fired = rms > MAX_PLANAR_RMS_MM
        verdict = "PASS" if fired == must_fail else "*** WRONG ***"
        print(f"  {label:<42} RMS {rms:8.4f} mm  guard "
              f"{'FIRES' if fired else 'silent':<6}  {verdict}")
        ok &= (fired == must_fail)
    print("\n" + ("all three behaved as specified" if ok else "GUARD IS BROKEN"))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="01d_derive_cut_plane.py")
    ap.add_argument("--mesh", type=Path, default=config.MESH)
    ap.add_argument("--out", type=Path, default=config.RESULTS / "01_cut_plane.csv")
    ap.add_argument("--extended", type=Path,
                    default=config.DATA / "mida_neckext.msh",
                    help="also fit the neck-extended mesh and emit the "
                         "PERPENDICULAR separation of the two planes")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)

    if a.self_test:
        return self_test()

    if not a.mesh.exists():
        print(f"ERROR: no mesh at {a.mesh}", file=sys.stderr)
        return 1

    row = derive(a.mesh)

    # Perpendicular separation of the base and extended planes. This MUST be
    # n.(p2-p1). The two fitted centroids sit at different lateral positions, so
    # the difference of their S coordinates is not the plane separation: it reads
    # 69.850 against a true 70.001, low by 0.151 mm. That is the same error class
    # as CUT_FACE_S itself, and it appeared once inside the check that confirmed
    # the fix. Do not "simplify" this back to a subtraction of pz values.
    ext = a.extended
    if ext and ext.exists():
        import numpy as np
        e = derive(ext, verbose=False)
        n = np.array([row["nx"], row["ny"], row["nz"]])
        d = np.array([e["px"] - row["px"], e["py"] - row["py"],
                      e["pz"] - row["pz"]])
        row["extrusion_perp_mm"] = float(abs(np.dot(n, d)))
        row["extrusion_s_difference_mm"] = float(abs(d[2]))
        row["extended_mesh"] = str(ext.relative_to(config.ROOT))
        print(f"\nextended plane  : perpendicular separation "
              f"{row['extrusion_perp_mm']:.4f} mm  "
              f"(S-difference alone would say {row['extrusion_s_difference_mm']:.4f})")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(row))
        wr.writeheader()
        wr.writerow({k: (f"{v:.10g}" if isinstance(v, float) else v)
                     for k, v in row.items()})
    print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
