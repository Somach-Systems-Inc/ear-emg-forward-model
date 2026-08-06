#!/usr/bin/env python3
"""
Stage 2 -- electrode positions on the MIDA skin surface.

Derives all 22 positions from labelled anatomy rather than hand-picking them,
then snaps each to the nearest outer-skin voxel. Writes
results/02_electrode_positions.csv plus a paste-ready config snippet.

WHY NOT AN INTERACTIVE PICKER
-----------------------------
README originally specified a GUI picker. That conflicts with CLAUDE.md's
"everything reproducible from a clean checkout given MIDA in data/": clicked
coordinates cannot be regenerated, reviewed in a diff, or defended in Methods.
Landmark-derived positions can. `--export-qa` writes a NIfTI with the
electrodes painted in so they can still be eyeballed in any viewer, and
config.ELECTRODE_OVERRIDES lets a position be pinned by hand if the automatic
one is wrong.

STATUS: every offset below is a first pass and is marked UNVERIFIED. CLAUDE.md
is explicit that electrode placement is where the human hours go. These are a
defensible starting point to be checked visually, not a finished answer.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402


class Stage2Error(RuntimeError):
    pass


# Offsets in mm from an anatomical anchor, in RAS.  (+R right, +A anterior, +S superior)
# UNVERIFIED: every number here is anatomical reasoning, not measurement.
# Sign of the R component is flipped automatically for the left side.
EAR_OFFSETS = {
    "pre_tragus":  (0.0,  14.0,   0.0),   # anterior to tragus, over masseter/TMJ
    "above_ear":   (0.0,   0.0,  30.0),   # superior to pinna, over temporalis
    "mastoid":     (0.0, -18.0, -10.0),   # posterior-inferior, on the mastoid
    "post_lobule": (0.0, -12.0, -30.0),   # behind/below the lobule
}

# Jaw sites: NORMAL PROJECTION, no hand-tuned RAS offsets.
#
# Each site names a target structure (and, where several sites share one
# structure, an anatomically-defined sub-region of it). The electrode is the
# nearest point on the OUTER SKIN to that sub-region's centroid. The reported
# distance is then depth of the structure below the skin, and nothing else --
# previously it was depth plus whatever error my hand-chosen offset introduced.
#
# `region` selects a sub-region so that three mandible-anchored sites do not
# collapse onto a single point. `skin` restricts which skin is eligible:
# "inferior" keeps submental/submaxillary under the jaw rather than letting
# them snap to the front of the chin, which is a different electrode.
JAW_TARGETS = {
    "mental":        dict(label=71, region=None,            skin=("midline",),
                          desc="over mentalis (chin)"),
    "submental_mid": dict(label=36, region="symphysis_mid", skin=("inferior", "midline"),
                          desc="under chin at midline, mandibular symphysis"),
    "submental_lat": dict(label=36, region="symphysis_lat", skin=("inferior",),
                          desc="under chin, lateral to the symphysis"),
    "submaxillary":  dict(label=36, region="body_lat",      skin=("inferior",),
                          desc="under the jawline, mandibular body"),
    "hyoid":         dict(label=87, region=None,            skin=("midline",),
                          desc="over the hyoid bone"),
    # region="side" matters: buccinator is bilateral, so an unrestricted
    # centroid lands near midline and its nearest skin point is under the chin,
    # not on the cheek. Same for masseter.
    "buccal":        dict(label=84, region="side",          skin=None,
                          desc="cheek, over buccinator"),
    "midjaw":        dict(label=66, region="side",          skin=None,
                          desc="over masseter"),
}

# HELD, not placed. Carl is measuring this on his own neck so the modelled
# electrode sits where the physical one will. Deriving it from MIDA's SCM
# centroid is wrong here: that compartment is truncated at the volume floor,
# which drags its centroid posteriorly. Stage 3 must not solve it.
HELD_POSITIONS = {
    "throat_scm": "awaiting measured coordinate from the physical rig; "
                  "MIDA's SCM is truncated by the inferior cut plane so its "
                  "centroid is biased",
}

# Tissue each ear site is supposed to sit over, for the same check the jaw
# sites get. mastoid and post_lobule are deliberately absent: they sit over the
# pooled Muscle (General) compartment and are handled by the ROI analysis.
EAR_TISSUE_CHECK = {
    "above_ear":  (63, "Muscle - Temporalis/Temporoparietalis"),
    "pre_tragus": (66, "Muscle - Masseter"),
}

MIDA_BACKGROUND = 50
MIDA_SKIN = 51
MIDA_PINNA = 35


def load(volume_path: Path):
    try:
        import numpy as np
        import nibabel as nib
        from scipy import ndimage
        from scipy.spatial import cKDTree
    except ImportError as exc:
        raise Stage2Error(
            f"Missing dependency: {exc.name}. Run: uv pip install -r requirements.txt"
        ) from exc

    if not volume_path.exists():
        raise Stage2Error(
            f"Label volume not found: {volume_path}\n"
            f"  Stage 2 reads the same MIDA volume stage 1 used. Pass --label-volume."
        )
    img = nib.load(str(volume_path))
    arr = np.asanyarray(img.dataobj)
    return np, nib, ndimage, cKDTree, img, arr


def outer_skin_points(np, ndimage, arr, affine):
    """RAS coordinates of skin voxels that touch background (the outer surface)."""
    skin = arr == MIDA_SKIN
    if not skin.any():
        raise Stage2Error(
            f"No voxels with label {MIDA_SKIN} (Epidermis/Dermis) in this volume.\n"
            f"  Stage 2 assumes MIDA's labelling. Check results/01_label_inventory.csv."
        )
    bg = arr == MIDA_BACKGROUND
    # a skin voxel on the outer surface has a background neighbour
    surface = skin & ndimage.binary_dilation(bg, ndimage.generate_binary_structure(3, 1))
    idx = np.argwhere(surface)
    del skin, bg, surface
    ras = nib_apply(np, affine, idx)
    return idx, ras


def nib_apply(np, affine, ijk):
    ijk = np.asarray(ijk, dtype=np.float64)
    return ijk @ affine[:3, :3].T + affine[:3, 3]


def derive_midline(np, arr, affine, mandible_label=36, pct=88.0):
    """Anatomical midline R, from the mandibular symphysis.

    Assuming R=0 is midline is wrong for MIDA: the symphysis sits at R=-7.8
    while the pinna-pair midpoint is at R=-1.3. Midline is derived, and the
    disagreement between the two estimates is reported rather than hidden --
    it is real facial asymmetry in a single-subject model.
    """
    idx = np.argwhere(arr == mandible_label)
    ras = idx @ affine[:3, :3].T + affine[:3, 3]
    symph = ras[ras[:, 1] >= np.percentile(ras[:, 1], pct)]
    return float(symph[:, 0].mean()), len(symph)


def region_points(np, ras, region, midline, sign):
    """Anatomically-defined sub-region of a structure's point cloud."""
    if region is None:
        return ras
    a = ras[:, 1]
    dr = (ras[:, 0] - midline) * sign          # +ve = chosen side
    if region == "symphysis_mid":
        return ras[(a >= np.percentile(a, 88)) & (np.abs(ras[:, 0] - midline) <= 10)]
    if region == "symphysis_lat":
        return ras[(a >= np.percentile(a, 82)) & (dr >= 12) & (dr <= 34)]
    if region == "body_lat":
        return ras[(a >= np.percentile(a, 45)) & (a <= np.percentile(a, 75)) & (dr >= 10)]
    if region == "side":
        return ras[dr > 0]
    raise ValueError(f"unknown region {region!r}")


def project_out_to_skin(np, arr, affine, inv_affine, start, head_centre,
                        max_mm=140.0, step_mm=0.5):
    """March outward from `start`, away from the head centre, and return the
    last non-background point: the skin directly OVER that structure.

    Nearest-neighbour snapping is wrong for deep anchors -- the hyoid sits
    ~20 mm below the skin, so its nearest skin voxel may be off to one side
    rather than the point an electrode over the hyoid would occupy.
    """
    d = np.asarray(start, float) - np.asarray(head_centre, float)
    n = np.linalg.norm(d)
    if n < 1e-6:
        return None, None
    d = d / n

    ts = np.arange(0.0, max_mm, step_mm)
    pts = np.asarray(start, float)[None, :] + ts[:, None] * d[None, :]
    ijk = np.rint(pts @ inv_affine[:3, :3].T + inv_affine[:3, 3]).astype(int)

    ok = np.all((ijk >= 0) & (ijk < np.array(arr.shape)), axis=1)
    labels = np.full(len(ts), MIDA_BACKGROUND, dtype=arr.dtype)
    labels[ok] = arr[ijk[ok, 0], ijk[ok, 1], ijk[ok, 2]]

    inside = (labels != MIDA_BACKGROUND) & ok
    if not inside.any():
        return None, None
    last = np.max(np.flatnonzero(inside))
    return pts[last], float(ts[last])


def centroid_ras(np, arr, affine, label):
    idx = np.argwhere(arr == label)
    if len(idx) == 0:
        return None
    return nib_apply(np, affine, idx.mean(0)[None, :])[0]


def side_split(np, arr, affine, label, side):
    """Voxels of `label` on one side, as RAS. side is 'right' (R>0) or 'left'."""
    idx = np.argwhere(arr == label)
    if len(idx) == 0:
        return None
    ras = nib_apply(np, affine, idx)
    keep = ras[:, 0] > 0 if side == "right" else ras[:, 0] < 0
    return ras[keep] if keep.any() else None


def place(volume_path: Path, side: str, out_csv: Path, qa_nifti: Path | None) -> int:
    np, nib, ndimage, cKDTree, img, arr = load(volume_path)
    affine = img.affine
    sign = 1.0 if side == "right" else -1.0

    print(f"Label volume : {volume_path}")
    print(f"Side         : {side} (ipsilateral)")
    print("Building outer skin surface ...", flush=True)
    skin_idx, skin_ras = outer_skin_points(np, ndimage, arr, affine)
    print(f"  {len(skin_ras):,} outer-skin voxels")
    tree = cKDTree(skin_ras)

    def snap(p):
        d, i = tree.query(np.asarray(p, float))
        return skin_ras[i], float(d)

    # --- ear anchor: the pinna on the chosen side -------------------------
    pinna = side_split(np, arr, affine, MIDA_PINNA, side)
    if pinna is None:
        raise Stage2Error(
            f"No pinna (label {MIDA_PINNA}) voxels found on the {side} side."
        )
    pinna_c = pinna.mean(0)
    # tragus ~ the most anterior pinna point (its anterior projection)
    tragus = pinna[np.argmax(pinna[:, 1])]
    print(f"  pinna centroid {fmt(pinna_c)}  n={len(pinna):,}")
    print(f"  tragus (most anterior pinna point) {fmt(tragus)}")

    # head centre, for the outward projection used by the deep jaw anchors
    inv_affine = np.linalg.inv(affine)
    head_idx = np.argwhere(arr != MIDA_BACKGROUND)
    head_centre = nib_apply(np, affine, head_idx.mean(0)[None, :])[0]
    del head_idx
    print(f"  head centre {fmt(head_centre)}")

    midline, n_symph = derive_midline(np, arr, affine)
    pin_l = side_split(np, arr, affine, MIDA_PINNA, "left")
    pinna_mid = (pinna.mean(0)[0] + pin_l.mean(0)[0]) / 2 if pin_l is not None else float("nan")
    print(f"  midline from mandibular symphysis: R = {midline:+.2f} "
          f"(n={n_symph:,})")
    print(f"  midline from pinna pair          : R = {pinna_mid:+.2f}")
    disagree = abs(midline - pinna_mid)
    print(f"  the two disagree by {disagree:.1f} mm"
          + ("   <-- EXCEEDS 3 mm, see notes" if disagree > 3 else ""))

    rows = []

    def add(name, montage, target, anchor_desc, depth=None):
        pos, dist = snap(target)
        rows.append(dict(
            name=name, montage=montage, side=side,
            R=round(float(pos[0]), 2), A=round(float(pos[1]), 2), S=round(float(pos[2]), 2),
            snap_mm=round(dist, 2),
            depth_mm=("" if depth is None else round(depth, 2)),
            anchor=anchor_desc, verified="no",
        ))

    for name, (dr, da, ds) in EAR_OFFSETS.items():
        anchor = tragus if name == "pre_tragus" else pinna_c
        add(name, "ear", anchor + np.array([sign * dr, da, ds]),
            f"pinna{'/tragus' if name=='pre_tragus' else ''} {dr:+.0f}R {da:+.0f}A {ds:+.0f}S")

    for name, spec in JAW_TARGETS.items():
        label, region, skinf, desc = (spec["label"], spec["region"],
                                      spec["skin"], spec["desc"])
        idx = np.argwhere(arr == label)
        if len(idx) == 0:
            print(f"  WARNING: label {label} absent, skipping {name}")
            continue
        ras = idx @ affine[:3, :3].T + affine[:3, 3]
        pts = region_points(np, ras, region, midline, sign)
        if len(pts) == 0:
            print(f"  WARNING: sub-region {region!r} empty for {name}, skipping")
            continue
        centre = pts.mean(0)

        # Eligible skin. "inferior" keeps submental/submaxillary under the jaw
        # instead of snapping to the front of the chin. "midline" pins the
        # genuinely midline sites to the DERIVED midline rather than letting
        # nearest-neighbour drift them a few mm off it.
        keep = np.ones(len(skin_ras), dtype=bool)
        for f in (skinf or ()):
            if f == "inferior":
                keep &= skin_ras[:, 2] <= centre[2] + 4.0
            elif f == "midline":
                keep &= np.abs(skin_ras[:, 0] - midline) <= 6.0
            else:
                raise ValueError(f"unknown skin filter {f!r}")
        if keep.all():
            cand, ctree = skin_ras, tree
        else:
            cand, ctree = skin_ras[keep], cKDTree(skin_ras[keep])
        d, i = ctree.query(centre)
        pos = cand[i]
        add(name, "jaw", pos,
            f"{desc} (label {label}"
            + (f", {region}" if region else "") + f"), normal projection",
            float(d))
        print(f"  {name:<16} target {label:>3} n={len(pts):>7,} "
              f"centroid {fmt(centre)} -> skin, depth {d:5.1f} mm")

    for name, why in HELD_POSITIONS.items():
        print(f"  {name:<16} HELD: {why}")
        rows.append(dict(name=name, montage="jaw", side=side, R="", A="", S="",
                         snap_mm="", depth_mm="",
                         anchor=f"HELD - {why}", verified="held"))

    # --- cEEGrid C-path ---------------------------------------------------
    # 10 positions sweeping around the pinna, anterior-superior -> posterior
    # -> inferior, at a fixed radius. UNVERIFIED: radius chosen so consecutive
    # spacing lands in the 12-18 mm band Debener 2015 uses; checked below.
    radius = 32.0
    angles = np.linspace(np.deg2rad(60), np.deg2rad(300), 10)
    for k, ang in enumerate(angles, start=1):
        target = pinna_c + np.array([0.0, radius * np.cos(ang), radius * np.sin(ang)])
        add(f"cg{k:02d}", "ceegrid", target, f"pinna + {radius:.0f}mm @ {np.rad2deg(ang):.0f}deg")

    # reference + bias on the lobule (most inferior pinna point), each side
    for nm, sd in ((config.REFERENCE, "left" if side == "right" else "right"),
                   (config.BIAS, side)):
        p = side_split(np, arr, affine, MIDA_PINNA, sd)
        if p is None:
            print(f"  WARNING: no pinna on {sd}, skipping {nm}")
            continue
        add(nm, "reference", p[np.argmin(p[:, 2])], f"most inferior pinna point, {sd}")

    # --- report -----------------------------------------------------------
    print(f"\n{'name':<16} {'montage':<10} {'R':>8} {'A':>8} {'S':>8} {'snap':>6} "
          f"{'depth':>6}  anchor")
    print("-" * 104)
    for r in rows:
        if r["verified"] == "held":
            print(f"{r['name']:<16} {r['montage']:<10} {'-':>8} {'-':>8} "
                  f"{'-':>8} {'-':>6} {'-':>6}  {r['anchor']}")
            continue
        dep = f"{r['depth_mm']:>6}" if r["depth_mm"] != "" else f"{'-':>6}"
        print(f"{r['name']:<16} {r['montage']:<10} {r['R']:>8.1f} {r['A']:>8.1f} "
              f"{r['S']:>8.1f} {r['snap_mm']:>6.1f} {dep}  {r['anchor']}")

    _tissue_check(np, arr, affine, rows, side)

    _sanity(np, rows)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nWritten: {out_csv}")

    if qa_nifti is not None:
        _write_qa(np, nib, img, arr, rows, qa_nifti)
        print(f"QA volume: {qa_nifti}")
        print("  Open alongside the label volume in any viewer; electrodes are label 999.")

    print("\nEVERY position above is verified=no. They are anatomically reasoned,")
    print("not measured. Check them visually before stage 3 -- CLAUDE.md is explicit")
    print("that electrode placement is where the human hours go.")
    return 0


def _tissue_check(np, arr, affine, rows, side):
    """Is each ear site actually over the muscle it targets?

    Same test the jaw sites get. mastoid and post_lobule are excluded on
    purpose: they sit over the pooled Muscle (General) compartment, which the
    ROI corridor analysis handles instead.
    """
    from scipy.spatial import cKDTree

    print("\nTISSUE UNDER THE EAR ELECTRODES")
    inv = np.linalg.inv(affine)
    pos = {r["name"]: np.array([float(r["R"]), float(r["A"]), float(r["S"])])
           for r in rows if r["verified"] != "held"}
    for name, (label, tissue) in EAR_TISSUE_CHECK.items():
        if name not in pos:
            continue
        idx = np.argwhere(arr == label)
        ras = idx @ affine[:3, :3].T + affine[:3, 3]
        keep = ras[:, 0] > 0 if side == "right" else ras[:, 0] < 0
        ras = ras[keep] if keep.any() else ras
        d, i = cKDTree(ras).query(pos[name])
        # does the straight segment to that tissue stay inside the head?
        seg = (pos[name][None, :] * (1 - np.linspace(0, 1, 80)[:, None])
               + ras[i][None, :] * np.linspace(0, 1, 80)[:, None])
        ijk = np.rint(seg @ inv[:3, :3].T + inv[:3, 3]).astype(int)
        ok = np.all((ijk >= 0) & (ijk < np.array(arr.shape)), axis=1)
        lab = np.full(len(seg), MIDA_BACKGROUND, dtype=arr.dtype)
        lab[ok] = arr[ijk[ok, 0], ijk[ok, 1], ijk[ok, 2]]
        outside = int(((lab == MIDA_BACKGROUND) | ~ok).sum())
        verdict = "ok" if (d < 35 and outside <= 1) else "*** CHECK ***"
        print(f"  {name:<12} -> {tissue:<40} {d:5.1f} mm  "
              f"path {'inside' if outside <= 1 else f'EXITS({outside})'}  {verdict}")
    print("  mastoid, post_lobule: over pooled Muscle (General); "
          "handled by the ROI corridor analysis")


def _sanity(np, rows):
    """Flag positions that are obviously wrong before they reach stage 3."""
    print()
    rows = [r for r in rows if r.get("verified") != "held"]
    problems = []
    # Jaw sites are projected onto the surface, so they should already sit on
    # skin; a large residual snap there means the projection missed.
    far = [r for r in rows if r["snap_mm"] > 15.0]
    if far:
        problems.append(
            f"{len(far)} position(s) snapped more than 15 mm to reach skin "
            f"({', '.join(r['name'] for r in far)}). For a projected site this "
            f"means the ray exited somewhere unexpected; for an offset site the "
            f"offset points into or away from the head."
        )
    deep = [r for r in rows if r["depth_mm"] not in ("", None) and float(r["depth_mm"]) > 45.0]
    if deep:
        problems.append(
            "structure(s) more than 45 mm below the skin: "
            + ", ".join(f"{r['name']} {r['depth_mm']}mm" for r in deep)
            + ". Plausible for pterygoids, suspicious for a surface jaw site."
        )
    cg = [r for r in rows if r["montage"] == "ceegrid"]
    if len(cg) > 1:
        d = [float(np.linalg.norm(np.array([b["R"], b["A"], b["S"]])
                                  - np.array([a["R"], a["A"], a["S"]])))
             for a, b in zip(cg, cg[1:])]
        print(f"cEEGrid consecutive spacing: min {min(d):.1f} mm, max {max(d):.1f} mm, "
              f"mean {sum(d)/len(d):.1f} mm  (Debener 2015 uses 12-18 mm)")
        if min(d) < 8 or max(d) > 25:
            problems.append(
                f"cEEGrid spacing {min(d):.1f}-{max(d):.1f} mm is outside a plausible "
                f"band; adjust the radius."
            )
    seen = {}
    for r in rows:
        key = (round(r["R"], 1), round(r["A"], 1), round(r["S"], 1))
        if key in seen:
            problems.append(f"{r['name']} and {seen[key]} snapped to the same point.")
        seen[key] = r["name"]

    if problems:
        print("\nSANITY CHECKS FAILED:")
        for p in problems:
            print(f"  - {p}")
    else:
        print("Sanity checks passed (snap distances, cEEGrid spacing, no duplicates).")


def _write_qa(np, nib, img, arr, rows, path):
    out = np.zeros(arr.shape, dtype=np.uint16)
    inv = np.linalg.inv(img.affine)
    zooms = np.array(img.header.get_zooms()[:3], dtype=float)
    rad_vox = np.ceil(4.0 / zooms).astype(int)
    for r in rows:
        ras = np.array([r["R"], r["A"], r["S"], 1.0])
        ijk = np.rint((inv @ ras)[:3]).astype(int)
        sl = tuple(slice(max(0, c - w), min(s, c + w + 1))
                   for c, w, s in zip(ijk, rad_vox, arr.shape))
        out[sl] = 999
    path.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(out, img.affine, img.header), str(path))


def fmt(p):
    return f"[{p[0]:7.1f} {p[1]:7.1f} {p[2]:7.1f}]"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        prog="02_place_electrodes.py",
        description="Stage 2: derive electrode positions on the MIDA skin surface.",
    )
    ap.add_argument("--label-volume", type=Path, required=True, metavar="NIFTI")
    ap.add_argument("--side", choices=("right", "left"), default="right",
                    help="ipsilateral side for the ear montage (default: right)")
    ap.add_argument("--out", type=Path,
                    default=config.RESULTS / "02_electrode_positions.csv")
    ap.add_argument("--export-qa", type=Path, nargs="?", const=config.RESULTS / "02_electrodes_qa.nii.gz",
                    help="write a NIfTI with electrodes painted as label 999")
    a = ap.parse_args(argv)
    try:
        return place(a.label_volume, a.side, a.out, a.export_qa)
    except Stage2Error as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
