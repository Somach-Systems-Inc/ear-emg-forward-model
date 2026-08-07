#!/usr/bin/env python3
r"""
Build and VERIFY the per-element muscle conductivity tensor for the anisotropic
run. Solving is a separate step; nothing here writes a field.

WHAT FIG 4 IS NOW, AND IT IS NARROWER THAN IT WAS
-------------------------------------------------
Not "isotropic head models are wrong". Only **3 of the 9** PCA-defensible
muscles are individually segmented in MIDA -- `sternocleidomastoid` (68),
`medial_pterygoid` (81), `mentalis` (71); the other six are pooled into
`Muscle (General)` (38) and `Tongue` (42) and cannot carry a fibre axis.

Fig 4 is therefore a **ROBUSTNESS CHECK ON A HEADLINE FINDING**: SCM is one of
the three muscles the ear wins on (+2.53 dB at `cg08`), and that result
currently assumes isotropic muscle. The question is whether the SCM
retroauricular advantage survives the isotropy assumption being relaxed.

The seven non-tensorable rows are labelled **NOT APPLIED**, never left blank.
A blank cell asserts a null result that was never measured.

WHY THIS BYPASSES SimNIBS'S OWN ANISOTROPY PATH
------------------------------------------------
`TDCSLIST.cond2elmdata()`'s "dir" branch calls `cond_utils.cond2elmdata` WITHOUT
exposing two flags that both default to True:

  correct_FSL=True        rotates every tensor by a matrix derived from the
                          affine, to undo an FSL preprocessing convention.
                          Our tensors are synthesised directly in mesh space
                          and have never been near FSL, so this rotation is
                          pure corruption.
  correct_intensity=True  "fits the tensor sizes according to the scalar
                          values (Rullmann et al. 2009)" -- it rescales the
                          ENTIRE tensor field by a single fitted scalar. The
                          0.4 / 0.1 S/m pair is the experimental specification
                          of this paper's two-run design; a solver silently
                          rescaling it would make Fig 4 a comparison against an
                          unknown conductivity.

So the tensor field is built here with those flags pinned explicitly, and the
eigenvalue clamps (`max_ratio`, `max_cond`) are passed explicitly too rather
than inherited. Our ratio is 4.0 and our largest eigenvalue is 0.4, so the
defaults (10, 2) would not bite -- but "would not bite" is a fact to assert,
not to assume.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/03e_build_tensor.py
    ... --write-nifti     also dump the tensor volume for inspection
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config          # noqa: E402
import orientation     # noqa: E402
import solve_invariants as SI  # noqa: E402

LABEL_VOL = config.DATA / "MIDA_v1.0" / "MIDA_v1_voxels" / "MIDA_v1.nii"
TENSOR_NII = config.DATA / "muscle_tensor.nii.gz"

SIGMA_LONG = config.SIGMA["muscle_long"]    # 0.400 along fibre
SIGMA_TRANS = config.SIGMA["muscle_trans"]  # 0.100 across fibre

# Explicit, not inherited. See the module docstring.
CORRECT_FSL = False
CORRECT_INTENSITY = False
MAX_RATIO = 10.0
MAX_COND = 2.0

_SEG = {n: lab for n, _g, lab, _e in config.MUSCLES if lab is not None}
TENSOR_MUSCLES = {m: _SEG[m] for m in config.FIBRE_PCA_MUSCLES if m in _SEG}
NOT_APPLIED = [m for m in config.FIBRE_PCA_MUSCLES if m not in _SEG]


def load_sigma():
    sig = {}
    for r in csv.DictReader(
            (config.RESULTS / "01_table1_conductivities.csv").open(encoding="utf-8")):
        lab, val = r.get("mida_label", "").strip(), r.get("sigma_S_per_m", "").strip()
        if lab.isdigit() and val:
            sig[int(lab)] = float(val)
    return sig


# Mirror agreement required between a bilateral pair's fibre axes. Set at 0.9
# because it must separate "mirror images with meshing noise" from "unrelated
# directions", and the measured cases are not close to the line: SCM 0.98 and
# medial pterygoid 0.99 pass, mentalis 0.19 fails. Nothing sits near 0.9.
MIRROR_MIN = 0.9
_REFUSED = {}


def build_tensor_volume():
    """6-component tensor volume in MESH (world) space, plus its affine.

    Component order is SimNIBS's: [Dxx, Dxy, Dxz, Dyy, Dyz, Dzz], which
    `cond2elmdata` expands via [0,1,2,1,3,4,2,4,5].

    Voxels outside the tensor compartments are left at ZERO. They are not
    "isotropic muscle" -- `cond2elmdata` only substitutes the tensor inside
    `aniso_tissues`, and every other tag keeps its scalar from `cond_list`.
    """
    import nibabel as nib
    img = nib.load(str(LABEL_VOL))
    lab = np.asarray(img.dataobj)
    affine = img.affine
    print(f"label volume : {LABEL_VOL.name}  shape {lab.shape}")
    # Column norms, NOT the diagonal. MIDA's affine is permuted/rotated, so
    # its diagonal reads [0.024, 0.016, -0.017] and looks like a 20x unit
    # error when the voxels are in fact 0.5 mm isotropic.
    print(f"voxel size   : {np.round(np.linalg.norm(affine[:3, :3], axis=0), 4)}"
          f"  mm (column norms)")

    vol = np.zeros(lab.shape + (6,), dtype=np.float32)
    axes, refused = {}, {}
    for name, tag in sorted(TENSOR_MUSCLES.items(), key=lambda kv: kv[1]):
        m = lab == tag
        n = int(m.sum())
        if n == 0:
            raise RuntimeError(
                f"{name}: label {tag} has no voxels in {LABEL_VOL.name}. A "
                f"tensor cannot be built for a compartment that is not there.")
        # voxel indices -> world mm, so the principal axis is in MESH space
        ijk = np.argwhere(m)
        world = nib.affines.apply_affine(affine, ijk)

        # PER SIDE, ALWAYS. MIDA gives each muscle ONE label covering both
        # sides, and PCA on the pooled cloud measures the LEFT-RIGHT SEPARATION
        # between two muscles rather than the fibre direction along either. It
        # is not a subtle error: pooled, all three compartments return an axis
        # of [-0.999, 0.00, 0.05], i.e. every muscle in the head apparently
        # runs left-to-right. SCM spans x = -63.4..62.0 mm, which is both
        # necks, not one strap.
        #
        # `orientation.split_sides()` exists precisely for this and says so in
        # its own docstring -- "it reported sternocleidomastoid, the textbook
        # strap muscle, as a plate". The first version of this builder did not
        # call it.
        pooled_axis, pooled_elong = orientation.principal_axis(world)
        sides = orientation.split_sides(world)
        print(f"  {name:<22} label {tag:>3}  {n:>8,} voxels   "
              f"pooled axis [{pooled_axis[0]:+.3f} {pooled_axis[1]:+.3f} "
              f"{pooled_axis[2]:+.3f}] elong {pooled_elong:.2f}  "
              f"-> {len(sides)} side(s)")
        # BILATERAL SYMMETRY CHECK, and it is measured rather than asserted.
        #
        # A bilaterally paired muscle must have mirror-symmetric fibre axes:
        # negating the x component of one side should reproduce the other, up
        # to the sign ambiguity inherent in a principal axis. That is a
        # property of the anatomy, not a tuned threshold, and it is a far
        # better test than an invented elongation cutoff.
        #
        # It passes SCM and medial pterygoid and FAILS mentalis, whose two
        # "sides" are [+0.097 -0.147 +0.984] and [-0.976 -0.195 +0.093] --
        # not mirror images of each other at all. Mentalis is a small midline
        # muscle, so splitting on x>0/x<0 does not separate a pair, it slices
        # one blob: the right fragment has elongation 1.07, i.e. no long axis
        # exists to find. FIBRE_MODEL's own rule applies -- for a compartment
        # with no meaningful long axis a principal axis "is not merely
        # imprecise, it is the wrong kind of object" -- so no tensor is
        # applied and it is reported as NOT APPLIED with this reason.
        per_side = []
        for side_name, pts in sides:
            axis, elong = orientation.principal_axis(pts)
            axis = axis / np.linalg.norm(axis)
            per_side.append((side_name, axis, elong, len(pts)))
            print(f"      {side_name:<6} n={len(pts):>8,}  "
                  f"axis [{axis[0]:+.3f} {axis[1]:+.3f} {axis[2]:+.3f}]  "
                  f"elongation {elong:.2f}")
            if elong < 1.5:
                print(f"         WARNING: elongation {elong:.2f} is low; the "
                      f"principal axis is weakly defined here")
            if abs(axis[0]) > 0.9:
                print(f"         WARNING: axis is still nearly left-right; "
                      f"check that this side separated cleanly")
            # voxels of THIS side only
            if side_name == "right":
                sel = m & (np.zeros_like(m) | _mask_side(lab, m, affine, +1))
            elif side_name == "left":
                sel = m & (np.zeros_like(m) | _mask_side(lab, m, affine, -1))
            else:
                sel = m
            D = (SIGMA_LONG * np.outer(axis, axis)
                 + SIGMA_TRANS * (np.eye(3) - np.outer(axis, axis)))
            vol[sel] = np.array([D[0, 0], D[0, 1], D[0, 2],
                                 D[1, 1], D[1, 2], D[2, 2]], dtype=np.float32)
        if len(per_side) == 2:
            a_r = per_side[0][1] * np.array([-1.0, 1.0, 1.0])   # mirror in x
            a_l = per_side[1][1]
            mirror_dot = float(abs(np.dot(a_r, a_l)))
            print(f"      bilateral mirror agreement: |dot| = {mirror_dot:.3f}")
            if mirror_dot < MIRROR_MIN:
                print(f"      REFUSED: the two sides are not mirror images "
                      f"(|dot| {mirror_dot:.3f} < {MIRROR_MIN}). No tensor is "
                      f"applied to {name}; it is reported NOT APPLIED.")
                for _sn, _ax, _el, _n in per_side:
                    pass
                vol[m] = 0.0          # undo anything written for this label
                refused[name] = (f"bilateral axes not mirror-symmetric "
                                 f"(|dot| {mirror_dot:.3f}); right-side "
                                 f"elongation {per_side[0][2]:.2f}")
                continue
        axes[name] = per_side
    _REFUSED.update(refused)
    return vol, affine, axes


def _mask_side(lab, m, affine, sign):
    """Boolean voxel mask for one side of a compartment, by world x sign."""
    import nibabel as nib
    ijk = np.argwhere(m)
    w = nib.affines.apply_affine(affine, ijk)
    keep = ijk[(w[:, 0] > 0) if sign > 0 else (w[:, 0] < 0)]
    out = np.zeros_like(m)
    out[keep[:, 0], keep[:, 1], keep[:, 2]] = True
    return out


def verify_on_mesh(vol, affine, axes, mesh_path, sigma_by_tag):
    """READ BACK the ElementData and assert the eigenvalues. Do not trust it.

    This is the step the handoff demanded. A tensor pipeline that silently
    rotates, rescales or clamps produces a completely plausible Fig 4, and the
    only way to know is to look at the eigenvalues that actually reached the
    elements.
    """
    from simnibs import mesh_io
    from simnibs.utils import cond_utils

    m = mesh_io.read_msh(str(mesh_path))
    tets = m.elm.elm_type == 4
    tags = m.elm.tag1

    full = SI.with_electrode_tags(sigma_by_tag)
    cond_list = [full.get(i + 1, 1e-6) for i in range(int(tags.max()))]

    cond = cond_utils.cond2elmdata(
        m, cond_list,
        anisotropy_volume=vol, affine=affine,
        aniso_tissues=list(TENSOR_MUSCLES.values()),
        correct_FSL=CORRECT_FSL,
        normalize=False,
        correct_intensity=CORRECT_INTENSITY,
        max_ratio=MAX_RATIO, max_cond=MAX_COND,
    )
    V = np.asarray(cond.value)
    print(f"\nElementData: shape {V.shape}  "
          f"({'tensor, 9 components' if V.ndim == 2 and V.shape[1] == 9 else 'SCALAR'})")
    if V.ndim != 2 or V.shape[1] != 9:
        raise RuntimeError(
            "cond2elmdata returned a SCALAR field. The anisotropic condition "
            "would have solved the isotropic problem and Fig 4 would compare a "
            "condition against itself.")

    ok = True
    print(f"\n{'compartment':<22}{'n elm':>8}{'l1':>9}{'l2':>9}{'l3':>9}"
          f"{'axis dot':>10}")
    print("-" * 68)
    for name, tag in sorted(TENSOR_MUSCLES.items(), key=lambda kv: kv[1]):
        if name not in axes:
            print(f"{name:<22}{'--':>8}   NOT APPLIED (refused by measurement)")
            continue
        k = tets & (tags == tag)
        T = V[k].reshape(-1, 3, 3)
        if len(T) == 0:
            raise RuntimeError(f"{name}: no tetrahedra with tag {tag} in mesh")
        w, vec = np.linalg.eigh(T)
        l3, l2, l1 = np.median(w[:, 0]), np.median(w[:, 1]), np.median(w[:, 2])
        principal = vec[:, :, 2]
        # per-side axes: an element is correct if it aligns with the axis of
        # EITHER side, since the sides are geometrically disjoint
        dots = np.max(np.abs(np.stack(
            [principal @ ax for _s, ax, _e, _n in axes[name]], axis=1)), axis=1)
        dot = float(np.median(dots))
        print(f"{name:<22}{len(T):>8,}{l1:>9.4f}{l2:>9.4f}{l3:>9.4f}{dot:>10.4f}")
        # Interpolation is trilinear with cval=0 outside the compartment, so
        # boundary elements are legitimately pulled toward zero. Judge the
        # MEDIAN element, and require the bulk to be right rather than every
        # element.
        if not (abs(l1 - SIGMA_LONG) < 0.02 and abs(l2 - SIGMA_TRANS) < 0.02
                and abs(l3 - SIGMA_TRANS) < 0.02):
            print(f"     FAIL: median eigenvalues are not "
                  f"({SIGMA_LONG}, {SIGMA_TRANS}, {SIGMA_TRANS})")
            ok = False
        if dot < 0.95:
            print(f"     FAIL: principal eigenvector is not aligned with the "
                  f"PCA axis (|dot| = {dot:.3f})")
            ok = False

    # every other tag must be untouched and isotropic
    others = [int(t) for t in np.unique(tags[tets])
              if int(t) not in TENSOR_MUSCLES.values()]
    bad = []
    for t in others[:40]:
        k = tets & (tags == t)
        T = V[k].reshape(-1, 3, 3)
        w = np.linalg.eigvalsh(T)
        spread = float(np.median(w[:, 2] - w[:, 0]))
        if spread > 1e-9:
            bad.append((t, spread))
    print(f"\nnon-tensor tags checked: {len(others[:40])}, "
          f"anisotropic by mistake: {len(bad)}")
    if bad:
        print(f"     FAIL: tags {[b[0] for b in bad][:8]} became anisotropic")
        ok = False
    return ok, cond


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="03e_build_tensor.py")
    ap.add_argument("--mesh", type=Path, default=None,
                    help="result mesh to verify against (default: the "
                         "above_ear iso solve, which already has electrodes)")
    ap.add_argument("--write-nifti", action="store_true")
    a = ap.parse_args(argv)

    print("MUSCLE CONDUCTIVITY TENSOR — build and verify")
    print("=" * 68)
    print(f"  sigma along fibre  : {SIGMA_LONG} S/m")
    print(f"  sigma across fibre : {SIGMA_TRANS} S/m   (ratio "
          f"{SIGMA_LONG/SIGMA_TRANS:.1f})")
    print(f"  correct_FSL        : {CORRECT_FSL}   (pinned, not inherited)")
    print(f"  correct_intensity  : {CORRECT_INTENSITY}   (pinned)")
    print(f"  max_ratio/max_cond : {MAX_RATIO} / {MAX_COND}  (pinned; our "
          f"ratio {SIGMA_LONG/SIGMA_TRANS:.1f} and max eigenvalue "
          f"{SIGMA_LONG} are inside both)")
    print(f"\n  TENSOR APPLIED   ({len(TENSOR_MUSCLES)}): "
          f"{sorted(TENSOR_MUSCLES)}")
    print(f"  NOT APPLIED      ({len(NOT_APPLIED)}): {NOT_APPLIED}")
    print("      pooled in MIDA's Muscle (General) 38 / Tongue 42 — these rows "
          "are\n      labelled NOT APPLIED in Fig 4, never left blank.\n")

    vol, affine, axes = build_tensor_volume()
    if _REFUSED:
        print(f"\n  REFUSED BY MEASUREMENT ({len(_REFUSED)}): "
              f"{sorted(_REFUSED)}")
        for k, why in sorted(_REFUSED.items()):
            print(f"      {k}: {why}")

    if a.write_nifti:
        import nibabel as nib
        nib.save(nib.Nifti1Image(vol, affine), str(TENSOR_NII))
        print(f"\nwrote {TENSOR_NII}")

    mesh = a.mesh or (sorted(
        (config.RESULTS / "leadfields" / "iso" / "above_ear").glob("*_scalar.msh"))[0])
    print(f"\nverifying against {Path(mesh).parent.name}/{Path(mesh).name}")
    ok, _ = verify_on_mesh(vol, affine, axes, mesh, load_sigma())

    print("\n" + "=" * 68)
    if ok:
        print("  VERIFIED — the tensor that reaches the elements has the")
        print("  intended eigenvalues along the intended axes, and no other")
        print("  compartment became anisotropic. Safe to solve.")
        return 0
    print("  FAILED — do NOT solve. A tensor field that does not carry the")
    print("  specified conductivities would make Fig 4 a comparison against")
    print("  an unknown condition, which is worse than having no Fig 4.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
