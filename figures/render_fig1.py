#!/usr/bin/env python3
r"""
Fig 1 — Head model, muscle compartments, and electrode positions.

Three orthogonal views of the MIDA skin surface with the ten segmented
articulator compartments coloured by muscle group, plus all 22 electrode
positions marked by montage. Establishes what the model contains and where the
electrodes sit, before any result is shown.

LICENCE. MIDA clause 2.3.3 requires the face be disguised in any published
image. Every point cloud here passes through
`render_common.anonymise_head(mode="crop")` and the figure is gated by
`assert_anonymised()`, exactly as the QA render is. The crop removes the
anterior skin, so the mandible and mentalis markers sit against empty space
rather than a profile; that is the intended trade and the electrode
coordinates are unaffected.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python figures/render_fig1.py \
        --label-volume data/MIDA_v1.0/MIDA_v1_voxels/MIDA_v1.nii
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "figures"))
import config          # noqa: E402
import render_common as rc  # noqa: E402

MIDA_SKIN, MIDA_BACKGROUND = 51, 50
GROUP_COLOUR = {}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="render_fig1.py")
    ap.add_argument("--label-volume", type=Path,
                    default=config.DATA / "MIDA_v1.0" / "MIDA_v1_voxels"
                    / "MIDA_v1.nii")
    ap.add_argument("--max-points", type=int, default=60000)
    ap.add_argument("--outdir", type=Path, default=rc.FIGDIR)
    a = ap.parse_args(argv)

    import nibabel as nib
    from scipy import ndimage
    rc.use_print_style()
    import matplotlib.pyplot as plt

    img = nib.load(str(a.label_volume))
    arr = np.asarray(img.dataobj)
    aff = img.affine
    rng = np.random.default_rng(0)

    def ras_of(label, n):
        idx = np.argwhere(arr == label)
        if len(idx) == 0:
            return np.empty((0, 3))
        if len(idx) > n:
            idx = idx[rng.choice(len(idx), n, replace=False)]
        return idx @ aff[:3, :3].T + aff[:3, 3]

    print("extracting skin surface ...", flush=True)
    skin_mask = arr == MIDA_SKIN
    bg = arr == MIDA_BACKGROUND
    surf = skin_mask & ndimage.binary_dilation(
        bg, ndimage.generate_binary_structure(3, 1))
    sidx = np.argwhere(surf)
    del skin_mask, bg, surf
    if len(sidx) > a.max_points:
        sidx = sidx[rng.choice(len(sidx), a.max_points, replace=False)]
    skin = sidx @ aff[:3, :3].T + aff[:3, 3]

    muscles = {}
    for name, group, lab, _e in config.MUSCLES:
        if lab is None:
            continue
        pts = ras_of(lab, 6000)
        if len(pts):
            muscles[name] = (group, pts)
    print(f"  {len(muscles)} segmented compartments")

    # LICENCE GATE — same path as the QA render
    n0 = len(skin)
    skin = skin[rc.anonymise_head(skin, mode="crop")]
    for k in list(muscles):
        g, p = muscles[k]
        muscles[k] = (g, p[rc.anonymise_head(p, mode="crop")])
    rc.assert_anonymised("fig1_head_model", True)
    print(f"  anonymised per licence 2.3.3: dropped {n0 - len(skin):,} of "
          f"{n0:,} skin points (orbital rim S = {rc.orbital_rim_S():.1f} mm)")

    # Muscle-group hues must avoid BOTH semantic electrode colours: the
    # cEEGrid markers are EAR_ADVANTAGE blue and the jaw markers are
    # JAW_ADVANTAGE red. The first render used tab10 from index 0, which put a
    # mastication blue directly under the blue cEEGrid squares in the lateral
    # view and made the markers hard to find. tab10 indices 1/2/4/5 are
    # orange, green, purple and brown -- no blue, no red.
    groups = list(dict.fromkeys(g for g, _ in muscles.values()))
    cmap = plt.get_cmap("tab10")
    SAFE = [1, 2, 4, 5, 8, 6]
    for i, g in enumerate(groups):
        GROUP_COLOUR[g] = cmap(SAFE[i % len(SAFE)])

    SOLVED = {r["electrode"] for r in csv.DictReader(
        (config.RESULTS / "03_leadfields.csv").open())}

    pos, montage = {}, {}
    for r in csv.DictReader(
            (config.RESULTS / "02_electrode_positions.csv").open()):
        # Plot exactly the electrodes that were SOLVED, read from the solve
        # table rather than inferred from a placement flag. Filtering on
        # `verified != "held"` let `earlobe_contra` through -- it has
        # coordinates but no solve -- so the figure showed 23 electrodes under a
        # caption claiming 22. The caption was right and the figure was wrong.
        #
        # `verified` is NOT a rejection flag: its values are no/accepted/held
        # and 16 of the 22 solved sites carry "no". An earlier version of this
        # fix filtered on it and would have plotted zero electrodes.
        if r["name"] not in SOLVED or not r["R"]:
            continue
        pos[r["name"]] = np.array([float(r["R"]), float(r["A"]),
                                   float(r["S"])])
        montage[r["name"]] = r.get("montage", "")

    MK = {"jaw": ("o", rc.JAW_ADVANTAGE), "ear": ("^", rc.EAR_ADVANTAGE),
          "ceegrid": ("s", rc.EAR_ADVANTAGE),
          "reference": ("X", rc.INK_MUTED)}
    views = [("Lateral (right)", 1, 2, "anterior  A (mm)", "superior  S (mm)"),
             ("Frontal", 0, 2, "right  R (mm)", "superior  S (mm)"),
             ("Axial", 0, 1, "right  R (mm)", "anterior  A (mm)")]

    fig, axes = plt.subplots(1, 3, figsize=(10.6, 4.3))
    for ax, (title, ix, iy, xl, yl) in zip(axes, views):
        # RASTERISED. 60k+ vector scatter points made a 3 MiB PDF and tripped
        # the repository's size guard. Point clouds carry no typographic
        # information, so rasterising them is the correct choice as well as the
        # small one; axes, text and electrode markers stay vector.
        ax.scatter(skin[:, ix], skin[:, iy], s=0.5, c="#d9d7d2",
                   linewidths=0, zorder=1, rasterized=True)
        for name, (g, p) in muscles.items():
            if not len(p):
                continue
            ax.scatter(p[:, ix], p[:, iy], s=1.1, color=GROUP_COLOUR[g],
                       alpha=0.55, linewidths=0, zorder=2, rasterized=True)
        for name, xyz in pos.items():
            mk, col = MK.get(montage[name], ("o", rc.INK_PRIMARY))
            ax.scatter(xyz[ix], xyz[iy], marker=mk, s=26, facecolor=col,
                       edgecolor=rc.SURFACE, linewidth=0.7, zorder=4)
        ax.set_title(title, fontsize=8)
        ax.set_xlabel(xl, fontsize=7)
        ax.set_ylabel(yl, fontsize=7)
        ax.set_aspect("equal")
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)

    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker="s", ls="", ms=5, color=GROUP_COLOUR[g],
                label=g) for g in groups]
    h += [Line2D([], [], marker=MK[k][0], ls="", ms=5.5,
                 color=MK[k][1], label=k) for k in
          ("jaw", "ear", "ceegrid", "reference") if k in set(montage.values())]
    leg = fig.legend(handles=h, loc="lower center", ncol=len(h), frameon=False,
                     fontsize=6.6, bbox_to_anchor=(0.5, -0.02))
    for t in leg.get_texts():
        t.set_color(rc.INK_SECONDARY)

    if not rc.PAPER_MODE:
        fig.suptitle("Fig 1 · Head model, segmented articulators and electrode "
                     "positions", x=0.012, ha="left", fontsize=9.5,
                     fontweight="bold")
        fig.text(0.012, 0.925,
                 f"MIDA v1.0, {len(muscles)} segmented articulator compartments "
                 f"coloured by group   ·   {len(pos)} electrode positions\n"
                 f"face cropped per MIDA licence clause 2.3.3: the anterior skin "
                 f"is removed, so the jaw electrodes sit against empty space "
                 f"rather than the chin they are placed on",
                 ha="left", fontsize=6.4, color=rc.INK_SECONDARY)
    fig.tight_layout(rect=[0, 0.04, 1, 0.90])

    import pandas as pd
    prov = pd.DataFrame({"x": [0]})
    prov.attrs["source"] = str(a.label_volume)
    prov.attrs["is_mock"] = False
    rc.save(fig, "fig1_head_model", prov, a.outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
