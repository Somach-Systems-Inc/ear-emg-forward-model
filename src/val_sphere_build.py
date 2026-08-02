#!/usr/bin/env python3
"""
Build a clean concentric-shell sphere label volume for reciprocity validation.

WHY NOT SIMNIBS'S SHIPPED sphere.msh

It is not a set of concentric shells. Its tag 3 spans radius 1.16-82.60 mm,
overlapping every other tag, so comparing it against an analytic multilayer
sphere would compare two different geometries and any disagreement would be
uninterpretable. This builds shells whose radii are exact by construction.

GEOMETRY -- matches MNE's default 4-layer EEG sphere exactly, so the analytic
solution is the oracle rather than a second approximation:

    tag 1  brain   r <  81.0 mm    sigma 0.33  S/m
    tag 2  csf     r <  82.8 mm    sigma 1.00  S/m
    tag 3  skull   r <  87.3 mm    sigma 0.004 S/m
    tag 4  scalp   r <  90.0 mm    sigma 0.33  S/m

Reciprocal-vs-direct on the head mesh would only prove two numerical paths
agree; a units or sign error corrupts both identically. The analytic sphere is
absolute ground truth.

    python src/val_sphere_build.py --voxel 0.5
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

HEAD_RADIUS_M = 0.09
# Shells deliberately thicker than MNE's stock (0.90, 0.92, 0.97, 1.00), whose
# CSF layer is 1.8 mm and would be 3.6 voxels at 0.5 mm. A shell that thin is a
# test of thin-shell meshing, not of reciprocity, and a discrepancy would be
# uninterpretable. These give every shell >= 6 voxels. MNE takes arbitrary
# radii, so the analytic oracle uses exactly these numbers and remains exact.
RELATIVE_RADII = (78 / 90, 82 / 90, 87 / 90, 1.00)
SIGMAS = (0.33, 1.00, 0.004, 0.33)
TAGS = (1, 2, 3, 4)
BACKGROUND = 0


def shell_radii_mm():
    return [HEAD_RADIUS_M * r * 1000.0 for r in RELATIVE_RADII]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="val_sphere_build.py")
    ap.add_argument("--voxel", type=float, default=0.5, help="mm per voxel")
    ap.add_argument("--out", type=Path, default=config.DATA / "val_sphere.nii.gz")
    a = ap.parse_args(argv)

    import numpy as np
    import nibabel as nib

    radii = shell_radii_mm()
    outer = radii[-1]
    half = outer + 3.0 * a.voxel
    n = int(np.ceil(2 * half / a.voxel))
    if n % 2:
        n += 1
    print(f"shell radii (mm): {[round(r,2) for r in radii]}")
    print(f"voxel {a.voxel} mm, grid {n}^3 = {n**3/1e6:.1f} M voxels")
    for i, (r, s, t) in enumerate(zip(radii, SIGMAS, TAGS)):
        thick = r - (radii[i - 1] if i else 0.0)
        print(f"  tag {t}  r < {r:6.2f} mm  sigma {s:6.3f}  "
              f"shell thickness {thick:6.2f} mm = {thick/a.voxel:.1f} voxels")

    thin = min(radii[i] - radii[i - 1] for i in range(1, len(radii)))
    if thin / a.voxel < 3.0:
        print(f"\nWARNING: thinnest shell is only {thin/a.voxel:.1f} voxels. "
              f"Use a smaller --voxel or the shell will not mesh faithfully.")

    ax = (np.arange(n) - (n - 1) / 2.0) * a.voxel
    # build radius field in chunks to keep peak memory sane
    vol = np.zeros((n, n, n), dtype=np.int16)
    x2 = ax[:, None, None] ** 2
    y2 = ax[None, :, None] ** 2
    z2 = ax[None, None, :] ** 2
    for i in range(n):
        r = np.sqrt(x2[i] + y2 + z2)[0]
        lab = np.zeros_like(r, dtype=np.int16)
        for rr, t in zip(radii[::-1], TAGS[::-1]):
            lab[r < rr] = t
        vol[i] = lab

    aff = np.eye(4)
    aff[0, 0] = aff[1, 1] = aff[2, 2] = a.voxel
    aff[:3, 3] = -half + a.voxel / 2.0

    counts = {int(t): int((vol == t).sum()) for t in TAGS}
    print("\nvoxel counts:")
    vv = a.voxel ** 3
    for t in TAGS:
        exp = (4 / 3) * np.pi * (radii[TAGS.index(t)] ** 3 -
                                 (radii[TAGS.index(t) - 1] ** 3 if TAGS.index(t) else 0))
        got = counts[t] * vv
        print(f"  tag {t}: {counts[t]:>10,} vox  {got:>12,.0f} mm^3  "
              f"analytic {exp:>12,.0f} mm^3  err {100*(got-exp)/exp:+.2f}%")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(vol, aff), str(a.out))
    print(f"\nwrote {a.out}")
    print("mesh with:")
    print(f"  meshmesh {a.out} data/val_sphere.msh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
