#!/usr/bin/env python3
"""
Anatomical ROI corridors inside MIDA's pooled compartments.

THE IDEA

Reciprocity gives E everywhere in the volume. Compartments are only how a
result is SUMMARISED, not how it is computed. So MIDA pooling the suprahyoid
group into "Muscle (General)" is a reporting problem, not a computation
problem, and the fix is to report the field two ways:

  (a) per-compartment medians for the 10 muscles MIDA actually segments
  (b) a spatial sensitivity field over the pooled compartments, with
      anatomically-defined ROIs overlaid

This module builds (b)'s ROIs. Each is the subset of a pooled compartment lying
inside a capsule between two landmarks that MIDA *does* segment. That is
principled geometry from segmented structures, not freehand painting, and it
never requires claiming a segmentation we did not make.

WHICH LANDMARKS EXIST, AND WHICH DO NOT

  mastoid notch  -- from "Air Internal - Mastoid" (30), inferior tip. REAL.
  hyoid body     -- from "Hyoid Bone" (87), centroid. REAL.
  styloid process -- NOT SEGMENTED. Searched Skull (40) for an isolated
                    process in every plausible box below and medial to the
                    mastoid; the skull is one connected component of 122k+
                    voxels and no separable spike exists at 500 um.

Consequence, stated plainly: digastric posterior belly and stylohyoid run
nearly parallel and adjacent between the same two regions, and MIDA does not
let us separate them. So this builds ONE suprahyoid corridor containing both,
and reports the field as a function of position along and across it. A reader
with their own anatomical prior can read off the anterior sub-band where
stylohyoid lies; we do not bake that prior in. Inventing a styloid coordinate
would have quietly converted "we bounded it" back into "we assumed it".

    python src/roi_corridor.py --label-volume data/.../MIDA_v1.nii
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

MIDA_MASTOID_AIR = 30
MIDA_HYOID = 87
MIDA_MUSCLE_GENERAL = 38
MIDA_TONGUE = 42

# Default corridor radius. Reported with a sensitivity sweep, never as a single
# number -- the radius is a choice and the paper must show what it buys.
DEFAULT_RADIUS_MM = 12.0
RADIUS_SWEEP = (8.0, 10.0, 12.0, 15.0, 18.0)


def landmarks(arr, affine, side="right"):
    """Mastoid notch and hyoid body, both from segmented structures."""
    def ras(label):
        idx = np.argwhere(arr == label)
        return idx @ affine[:3, :3].T + affine[:3, 3]

    mast = ras(MIDA_MASTOID_AIR)
    if len(mast) == 0:
        raise RuntimeError(f"label {MIDA_MASTOID_AIR} (mastoid air cells) absent")
    m = mast[mast[:, 0] > 0] if side == "right" else mast[mast[:, 0] < 0]
    if len(m) == 0:
        raise RuntimeError(f"no mastoid air cells on the {side}")
    # The digastric fossa (mastoid notch) is on the inferior aspect of the
    # mastoid process; its air cells' inferior tip is the closest proxy MIDA
    # offers without inventing a landmark.
    notch = m[m[:, 2] <= np.percentile(m[:, 2], 8)].mean(0)

    hy = ras(MIDA_HYOID)
    if len(hy) == 0:
        raise RuntimeError(f"label {MIDA_HYOID} (hyoid bone) absent")
    # NOT the hyoid centroid. Digastric's intermediate tendon attaches near the
    # body/greater-horn junction on the SAME side, not at the midline body.
    # Using the centroid gave a 95 mm corridor -- more than twice the length of
    # a posterior digastric belly -- because it ran across the midline.
    ipsi = hy[hy[:, 0] > 0] if side == "right" else hy[hy[:, 0] < 0]
    horn = ipsi if len(ipsi) >= 50 else hy
    return notch, horn.mean(0)


def capsule_mask(points, a, b, radius):
    """Boolean mask: which `points` lie within `radius` of segment a->b."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ab = b - a
    L2 = float(ab @ ab)
    if L2 <= 0:
        return np.linalg.norm(points - a, axis=1) <= radius
    t = np.clip((points - a) @ ab / L2, 0.0, 1.0)
    closest = a[None, :] + t[:, None] * ab[None, :]
    return np.linalg.norm(points - closest, axis=1) <= radius, t


def corridor_roi(arr, affine, pooled_label, a, b, radius):
    """Voxels of `pooled_label` inside the capsule, with along-axis coordinate.

    Returns (ijk, ras, t) where t in [0,1] runs a->b, so the field can be
    reported as a profile along the corridor rather than one collapsed number.
    """
    idx = np.argwhere(arr == pooled_label)
    if len(idx) == 0:
        return idx, np.empty((0, 3)), np.empty(0)
    ras = idx @ affine[:3, :3].T + affine[:3, 3]
    inside, t = capsule_mask(ras, a, b, radius)
    return idx[inside], ras[inside], t[inside]


def _report(volume_path: Path, side: str, out_csv: Path | None) -> int:
    import nibabel as nib
    import csv as _csv

    if not volume_path.exists():
        print(f"ERROR: no label volume at {volume_path}", file=sys.stderr)
        return 1
    img = nib.load(str(volume_path))
    arr = np.asanyarray(img.dataobj)
    aff = img.affine
    voxel_mm3 = float(np.abs(np.linalg.det(aff[:3, :3])))

    notch, hyoid = landmarks(arr, aff, side)
    length = float(np.linalg.norm(hyoid - notch))
    print(f"Side: {side}")
    print(f"  mastoid notch (Air Internal - Mastoid 30, inferior tip): "
          f"[{notch[0]:7.1f} {notch[1]:7.1f} {notch[2]:7.1f}]")
    print(f"  hyoid body    (Hyoid Bone 87, centroid)                : "
          f"[{hyoid[0]:7.1f} {hyoid[1]:7.1f} {hyoid[2]:7.1f}]")
    print(f"  corridor length: {length:.1f} mm")
    print(f"\n  Digastric posterior belly runs mastoid notch -> intermediate")
    print(f"  tendon at the hyoid. Stylohyoid runs styloid -> hyoid, nearly")
    print(f"  parallel and slightly anterior. MIDA does not segment the")
    print(f"  styloid, so ONE corridor holds both; see module docstring.")

    print(f"\nRADIUS SENSITIVITY (the radius is a choice; here is what it buys)")
    print(f"{'radius':>7} {'MuscleGen vox':>14} {'volume mm3':>12} "
          f"{'Tongue vox':>11}  {'frac of pool':>12}")
    print("-" * 64)
    rows = []
    n_pool = int((arr == MIDA_MUSCLE_GENERAL).sum())
    for r in RADIUS_SWEEP:
        _, ras_m, t_m = corridor_roi(arr, aff, MIDA_MUSCLE_GENERAL, notch, hyoid, r)
        _, ras_t, _ = corridor_roi(arr, aff, MIDA_TONGUE, notch, hyoid, r)
        frac = len(ras_m) / n_pool if n_pool else 0.0
        mark = "  <- default" if abs(r - DEFAULT_RADIUS_MM) < 1e-6 else ""
        print(f"{r:>7.0f} {len(ras_m):>14,} {len(ras_m)*voxel_mm3:>12,.0f} "
              f"{len(ras_t):>11,}  {frac:>11.1%}{mark}")
        rows.append(dict(side=side, radius_mm=r, muscle_general_voxels=len(ras_m),
                         volume_mm3=round(len(ras_m) * voxel_mm3, 1),
                         tongue_voxels=len(ras_t), frac_of_pool=round(frac, 5),
                         corridor_length_mm=round(length, 2)))

    # profile along the default corridor, so the shape is visible not assumed
    _, ras_m, t_m = corridor_roi(arr, aff, MIDA_MUSCLE_GENERAL,
                                 notch, hyoid, DEFAULT_RADIUS_MM)
    if len(t_m):
        print(f"\nOCCUPANCY ALONG THE DEFAULT {DEFAULT_RADIUS_MM:.0f} mm CORRIDOR "
              f"(0 = mastoid notch, 1 = hyoid)")
        hist, edges = np.histogram(t_m, bins=10, range=(0, 1))
        for h, e0, e1 in zip(hist, edges[:-1], edges[1:]):
            bar = "#" * int(40 * h / max(hist.max(), 1))
            print(f"  {e0:.1f}-{e1:.1f}  {h:>7,}  {bar}")
        gaps = [i for i, h in enumerate(hist) if h == 0]
        if gaps:
            print(f"  WARNING: {len(gaps)} empty bin(s) -- the corridor leaves "
                  f"Muscle (General) somewhere along its length.")
        else:
            print("  No empty bins: the corridor stays inside muscle end to end.")

    if out_csv is not None:
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with out_csv.open("w", newline="") as fh:
            w = _csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
        print(f"\nWritten: {out_csv}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="roi_corridor.py")
    ap.add_argument("--label-volume", type=Path, required=True)
    ap.add_argument("--side", choices=("right", "left"), default="right")
    ap.add_argument("--out", type=Path,
                    default=config.RESULTS / "02_roi_corridor.csv")
    a = ap.parse_args(argv)
    return _report(a.label_volume, a.side, a.out)


if __name__ == "__main__":
    sys.exit(main())
