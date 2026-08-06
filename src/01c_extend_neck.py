#!/usr/bin/env python3
"""
Stage 1c -- extrude the neck below MIDA's inferior cut face.

WHY THIS EXISTS

MIDA ends on a planar cut, tilted 2.664 deg off the S axis and therefore having
no single S coordinate (see 01d_derive_cut_plane.py; the face spans S -122.07 to
-110.18). SimNIBS applies an insulating (zero-flux) boundary condition on the
outer surface, so at that cut face current is reflected rather than continuing
down the neck. The error is not uniform across the montage, in PERPENDICULAR
distance to that plane:

    hyoid          ~0 mm from the cut face
    throat_scm    ~23 mm
    every ear site 80+ mm

So the artefact inflates the lead field at the jaw sites and leaves the ear
sites essentially untouched -- it biases this paper's headline jaw-versus-ear dB
gap in the flattering direction. That is the one direction of bias a reviewer
should care about, so it gets measured rather than argued about.

WHAT IT DOES

Takes the inferior cross-section, and extrudes it downward as a homogeneous
slab carrying its own label (EXTENSION_LABEL), so it never contaminates the
Muscle (General) compartment used for the suprahyoid ROI analysis. The slab is
assigned muscle-isotropic conductivity in stage 3.

A homogeneous slab is deliberate: the point is to move the insulating boundary
away from the electrodes, not to model neck anatomy that MIDA does not contain.
Inventing vertebrae and vessels down there would be fiction.

    python src/01c_extend_neck.py --mm 70
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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
MIDA_BACKGROUND = 50


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="01c_extend_neck.py")
    ap.add_argument("--label-volume", type=Path,
                    default=config.DATA / "MIDA_v1.0/MIDA_v1_voxels/MIDA_v1.nii")
    ap.add_argument("--out", type=Path, default=config.DATA / "mida_neckext.nii.gz")
    ap.add_argument("--mm", type=float, default=70.0,
                    help="extrusion length in mm (default 70)")
    a = ap.parse_args(argv)

    import numpy as np
    import nibabel as nib
    from scipy import ndimage

    if not a.label_volume.exists():
        print(f"ERROR: no label volume at {a.label_volume}", file=sys.stderr)
        return 1

    img = nib.load(str(a.label_volume))
    arr = np.asanyarray(img.dataobj)
    aff = img.affine

    # Which voxel axis is superior, and which way does it point? The affine is
    # oblique, so this must be derived, never assumed.
    sup_axis = int(np.argmax(np.abs(aff[2, :3])))
    sup_sign = float(np.sign(aff[2, sup_axis]))
    step_mm = float(np.linalg.norm(aff[:3, sup_axis]))
    n_slices = int(round(a.mm / step_mm))
    print(f"superior axis: voxel {sup_axis} (sign {sup_sign:+.0f}), "
          f"{step_mm:.4f} mm/slice")
    print(f"extruding {a.mm:.0f} mm = {n_slices} slices")

    # inferior face = index 0 if S increases with the axis, else the last index
    face_idx = 0 if sup_sign > 0 else arr.shape[sup_axis] - 1
    face = np.take(arr, face_idx, axis=sup_axis)
    mask = face != MIDA_BACKGROUND
    print(f"inferior face: {int(mask.sum()):,} non-background voxels "
          f"({100*mask.mean():.1f}% of the slice)")
    if mask.sum() < 1000:
        print("ERROR: inferior face looks empty; wrong axis?", file=sys.stderr)
        return 1

    # Close small holes so the slab is a solid neck cross-section rather than
    # inheriting airways and vessel lumens as through-holes.
    mask = ndimage.binary_fill_holes(mask)
    print(f"after hole-fill: {int(mask.sum()):,} voxels")

    slab_slice = np.where(mask, EXTENSION_LABEL, MIDA_BACKGROUND).astype(arr.dtype)
    slab = np.repeat(np.expand_dims(slab_slice, sup_axis), n_slices, axis=sup_axis)

    parts = [slab, arr] if sup_sign > 0 else [arr, slab]
    out = np.concatenate(parts, axis=sup_axis)

    # Shift the origin so world coordinates of the ORIGINAL voxels are unchanged.
    new_aff = aff.copy()
    if sup_sign > 0:
        new_aff[:3, 3] = aff[:3, 3] - n_slices * aff[:3, sup_axis]

    print(f"shape {arr.shape} -> {out.shape}")
    nib.save(nib.Nifti1Image(out, new_aff), str(a.out))
    print(f"wrote {a.out}")

    # verify the original anatomy did not move
    chk = np.array([100.0, 100.0, 100.0, 1.0])
    old_ijk = np.linalg.inv(aff) @ chk
    new_ijk = np.linalg.inv(new_aff) @ chk
    shift = new_ijk[:3] - old_ijk[:3]
    print(f"world->voxel shift for the same RAS point: {shift.round(2)} "
          f"(expect {n_slices} on axis {sup_axis}, 0 elsewhere)")
    lo = np.argwhere(out != MIDA_BACKGROUND)
    ras = lo @ new_aff[:3, :3].T + new_aff[:3, 3]
    # The extruded mesh's face is PARALLEL to the base one and displaced by the
    # extrusion along the plane normal. Its S minimum is a corner of that face,
    # not the cut location, so this is a sanity print and not a measurement of
    # the plane. 01d_derive_cut_plane.py --extended emits the real separation.
    print(f"new inferior limit: S = {ras[:,2].min():.1f} mm "
          f"(base mesh S min -122.2, so expect about {-122.167 - a.mm:.1f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
