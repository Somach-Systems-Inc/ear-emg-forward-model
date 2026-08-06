#!/usr/bin/env python3
"""
Stage 2b -- QA renders of the electrode positions on the MIDA skin surface.

Three anatomical projections (lateral, frontal, posterior) with every position
labelled, plus pinna and mandible outlines so a position can be judged against
the landmark it claims to sit on. "mastoid" should sit behind the ear; you can
only see that if the ear is drawn.

2D projections rather than a 3D scatter on purpose: matplotlib's 3D depth
ordering is unreliable for dense point clouds, and a QA figure that might be
lying about occlusion is worse than no QA figure.

    python src/02b_qa_render.py --label-volume data/.../MIDA_v1.nii
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

# Categorical slots 1-3 of the validated palette, in fixed order. Verified with
# validate_palette.js --pairs all --mode light (scatter uses the all-pairs
# pairlist, which caps the palette at three slots):
#   CVD worst 9.2 dE, normal-vision worst 24.0 dE, all checks PASS.
# Reference electrodes deliberately do NOT take a fourth hue -- a fourth slot
# fails the all-pairs floors. They use neutral ink plus a distinct marker.
MONTAGE_STYLE = {
    "jaw":       ("#2a78d6", "o", "Jaw (canonical)"),
    "ear":       ("#eb6834", "^", "Retroauricular"),
    "ceegrid":   ("#1baf7a", "s", "cEEGrid C-path"),
    "reference": ("#52514e", "X", "Reference / BIAS"),
}
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
SURFACE = "#fcfcfb"
SKIN_TONE = "#dcdcd8"
PINNA_TONE = "#a8a8a0"
MANDIBLE_TONE = "#c2c2ba"

MIDA_BACKGROUND, MIDA_SKIN, MIDA_PINNA, MIDA_MANDIBLE = 50, 51, 35, 36


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="02b_qa_render.py")
    ap.add_argument("--label-volume", type=Path, required=True)
    ap.add_argument("--positions", type=Path,
                    default=config.RESULTS / "02_electrode_positions.csv")
    ap.add_argument("--out", type=Path, default=config.FIGURES / "02_electrode_qa")
    ap.add_argument("--max-points", type=int, default=60000)
    a = ap.parse_args(argv)

    import numpy as np
    import nibabel as nib
    from scipy import ndimage
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    if not a.positions.exists():
        print(f"ERROR: no positions file at {a.positions}. Run stage 2 first.",
              file=sys.stderr)
        return 1

    rows = list(csv.DictReader(a.positions.open(encoding="utf-8")))
    if not rows:
        print("ERROR: positions file is empty", file=sys.stderr)
        return 1

    img = nib.load(str(a.label_volume))
    arr = np.asanyarray(img.dataobj)
    aff = img.affine

    def ras_of(label, subsample=None):
        idx = np.argwhere(arr == label)
        if len(idx) == 0:
            return np.empty((0, 3))
        if subsample and len(idx) > subsample:
            rng = np.random.default_rng(0)
            idx = idx[rng.choice(len(idx), subsample, replace=False)]
        return idx @ aff[:3, :3].T + aff[:3, 3]

    print("extracting surfaces ...", flush=True)
    skin_mask = arr == MIDA_SKIN
    bg = arr == MIDA_BACKGROUND
    surf = skin_mask & ndimage.binary_dilation(
        bg, ndimage.generate_binary_structure(3, 1))
    sidx = np.argwhere(surf)
    del skin_mask, bg, surf
    rng = np.random.default_rng(0)
    if len(sidx) > a.max_points:
        sidx = sidx[rng.choice(len(sidx), a.max_points, replace=False)]
    skin = sidx @ aff[:3, :3].T + aff[:3, 3]
    pinna = ras_of(MIDA_PINNA, 20000)
    mand = ras_of(MIDA_MANDIBLE, 20000)

    # MIDA licence clause 2.3.3: any published image must have the face
    # disguised so the individual is unrecognizable. The lateral view of this
    # figure previously showed a legible facial profile (nose, lips, chin).
    # The rim is DERIVED from MIDA's own eye labels, never hardcoded.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "figures"))
    import render_common as rc
    n_before = len(skin)
    skin = skin[rc.anonymise_head(skin, mode="crop")]
    mand = mand[rc.anonymise_head(mand, mode="crop")]
    rc.assert_anonymised("02_electrode_qa", True)
    print(f"  anonymised per licence 2.3.3: dropped "
          f"{n_before - len(skin):,} of {n_before:,} skin points above the "
          f"orbital rim (S = {rc.orbital_rim_S():.1f} mm) and anterior of "
          f"the eyes")
    print(f"  skin {len(skin):,}  pinna {len(pinna):,}  mandible {len(mand):,}")

    # Held positions carry no coordinates by design (throat_scm awaits a
    # measurement from the physical rig). Skip them, and say so on the figure
    # rather than letting them vanish silently.
    held = [r["name"] for r in rows if r.get("verified") == "held"]
    E = {r["name"]: (float(r["R"]), float(r["A"]), float(r["S"]), r["montage"])
         for r in rows if r.get("verified") != "held" and r["R"] != ""}
    if held:
        print(f"  held, not drawn: {', '.join(held)}")

    # (title, half-space selector, projected axes, axis labels, x-inverted)
    # Two selectors per view: a tight one for the anatomy silhouette, and a
    # looser one for electrodes. Midline sites (mental, submental_mid, hyoid)
    # sit a few mm left of R=0 and a strict R>0 test drops them from the
    # lateral view entirely -- they are exactly the sites that most need
    # checking against the chin and jawline.
    a_mid = float(np.median(skin[:, 1]))
    views = [
        ("Lateral (right)", lambda p: p[:, 0] > 0, lambda p: p[:, 0] > -25,
         (1, 2), ("anterior  A (mm)", "superior  S (mm)"), False),
        ("Frontal", lambda p: p[:, 1] > a_mid, lambda p: p[:, 1] > a_mid - 20,
         (0, 2), ("right  R (mm)", "superior  S (mm)"), False),
        ("Posterior", lambda p: p[:, 1] < a_mid, lambda p: p[:, 1] < a_mid + 20,
         (0, 2), ("right  R (mm)", "superior  S (mm)"), True),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(19, 8), facecolor=SURFACE)
    all_texts = []
    for ax, (title, sel, esel, (ix, iy), (xl, yl), invert) in zip(axes, views):
        ax.set_facecolor(SURFACE)
        for cloud, tone, size in ((skin, SKIN_TONE, 1.0),
                                  (mand, MANDIBLE_TONE, 1.2),
                                  (pinna, PINNA_TONE, 1.6)):
            if len(cloud) == 0:
                continue
            k = sel(cloud)
            ax.scatter(cloud[k, ix], cloud[k, iy], s=size, c=tone,
                       linewidths=0, rasterized=True)

        drawn = {}
        for name, (R, A, S, mont) in E.items():
            p = np.array([[R, A, S]])
            if not esel(p)[0]:
                continue
            colour, marker, _ = MONTAGE_STYLE.get(mont, (INK_SECONDARY, "o", ""))
            x, y = p[0, ix], p[0, iy]
            # 2px surface ring so overlapping marks stay separable
            ax.scatter([x], [y], s=95, c=colour, marker=marker,
                       edgecolors=SURFACE, linewidths=1.6, zorder=5)
            drawn[name] = (x, y)

        texts = []
        for name, (x, y) in drawn.items():
            t = ax.annotate(name, (x, y), textcoords="offset points",
                            xytext=(8, 6), fontsize=7.5, color=INK_PRIMARY,
                            zorder=6,
                            bbox=dict(boxstyle="round,pad=0.16", fc=SURFACE,
                                      ec="none", alpha=0.85),
                            arrowprops=dict(arrowstyle="-", lw=0.5,
                                            color="#9a9a92", shrinkA=0,
                                            shrinkB=3))
            texts.append(t)
        all_texts.append((ax, texts))

        ax.set_title(f"{title}   ({len(drawn)} positions)", fontsize=11,
                     color=INK_PRIMARY, pad=10)
        ax.set_xlabel(xl, fontsize=9, color=INK_SECONDARY)
        ax.set_ylabel(yl, fontsize=9, color=INK_SECONDARY)
        ax.set_aspect("equal")
        if invert:
            ax.invert_xaxis()
        ax.tick_params(colors=INK_SECONDARY, labelsize=8)
        for s in ax.spines.values():
            s.set_color("#e2e2dd")

    handles = [plt.Line2D([], [], marker=m, color="none", markerfacecolor=c,
                          markeredgecolor=SURFACE, markersize=9, label=lab)
               for c, m, lab in MONTAGE_STYLE.values()]
    fig.legend(handles=handles, loc="lower center", ncol=4, frameon=False,
               fontsize=9.5, labelcolor=INK_PRIMARY, bbox_to_anchor=(0.5, 0.005))
    fig.suptitle("Electrode positions on the MIDA skin surface — "
                 "ALL POSITIONS UNVERIFIED, for visual QA",
                 fontsize=13, color=INK_PRIMARY, y=0.975)
    sub = ("grey = skin surface · mid grey = mandible · "
           "dark grey = pinna (auricular cartilage)")
    if held:
        sub += f"   ·   HELD, not shown: {', '.join(held)}"
    fig.text(0.5, 0.935, sub, ha="center", fontsize=9, color=INK_SECONDARY)
    fig.tight_layout(rect=[0, 0.05, 1, 0.92])

    # De-collide labels. The first render produced "above_ear" and "cg01"
    # overlapping into the unreadable string "above_cg01"; a QA figure whose
    # labels lie is worse than none. Leader lines keep each label tied to its
    # marker after it moves.
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    for ax, texts in all_texts:
        if len(texts) < 2:
            continue
        for _ in range(40):
            boxes = [t.get_window_extent(rend) for t in texts]
            moved = False
            for i in range(len(texts)):
                for j in range(i + 1, len(texts)):
                    if not boxes[i].overlaps(boxes[j]):
                        continue
                    hi, lo = (j, i) if boxes[j].y0 >= boxes[i].y0 else (i, j)
                    dx, dy = texts[hi].xyann
                    texts[hi].xyann = (dx, dy + 5.0)
                    dx, dy = texts[lo].xyann
                    texts[lo].xyann = (dx, dy - 5.0)
                    moved = True
                    break
                if moved:
                    break
            if not moved:
                break
            fig.canvas.draw()
        # give the moved labels room rather than letting them clip
        ax.margins(0.16)

    a.out.parent.mkdir(parents=True, exist_ok=True)
    png, pdf = a.out.with_suffix(".png"), a.out.with_suffix(".pdf")
    fig.savefig(png, dpi=170, facecolor=SURFACE)
    fig.savefig(pdf, facecolor=SURFACE)
    print(f"wrote {png}\nwrote {pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
