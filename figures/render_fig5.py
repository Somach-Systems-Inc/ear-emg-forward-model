#!/usr/bin/env python3
r"""
Fig 5 — THE COMPLEMENTARITY MAP. Which montage wins each muscle, and by how much.

REBUILT 2026-08-04. This figure used to rank retroauricular sites by TOTAL
articulator sensitivity, summed over muscles. That spec is wrong for this data,
and the reason matters: summing over muscles collapses a SIGN CHANGE into a
scalar. Three muscles are picked up more strongly at the ear than at the best
jaw site -- temporalis, sternocleidomastoid, lateral pterygoid -- while a total
is dominated by the labial group, where the jaw wins by 10-23 dB. The three
muscles the ear is actually better at would vanish from the figure that is
supposed to be the design deliverable.

So: one row per muscle, a diverging bar about 0 dB, and the winning site named
on each side. A designer reads "which sites do I place for the gestures I care
about", instead of "which single site is loudest".

THE AXIS IS LINEAR IN dB, NOT A RANK, and that is the point. The asymmetry
between the two arms IS a result: the jaw's advantages are large and broad (up
to +22.8 dB), the ear's are modest and specific (+1.7 to +3.9 dB). Fig 2 uses
TwoSlopeNorm, which visually equalises those arms, so a reader could come away
believing the ear's advantage is comparable in size. Here it is readable by
POSITION at true relative scale -- the one place in the figure set where that
asymmetry is stated honestly.

Colour job: DIVERGING about 0 (two hues + neutral). Bar length is the measure —
one axis. Jaw sites within 10 mm of the truncation face are excluded by
default, since the cut inflates them.

    simnibs_python figures/render_fig5.py
    ... --include-near-cut     use all jaw sites, including the three within
                               10 mm of the cut face
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

import render_common as rc

NEAR_CUT = ("hyoid", "submental_lat", "submental_mid")
FLOOR_CI_HI = 0.65      # upper bound of the measured floor's 95% CI


def _floor():
    import config
    f = config.RESULTS / "electrode_meshing_floor.txt"
    for line in f.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return float(line.split()[0])
    raise RuntimeError(f"no numeric floor in {f}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, default=rc.DEFAULT_CSV)
    ap.add_argument("--condition", default="iso", choices=["iso", "aniso"])
    ap.add_argument("--mesh", default="truncated",
                    choices=["truncated", "extended"])
    ap.add_argument("--include-near-cut", action="store_true")
    ap.add_argument("--outdir", type=Path, default=rc.FIGDIR)
    a = ap.parse_args(argv)

    rc.use_print_style()
    import matplotlib.pyplot as plt

    df = rc.load_sensitivity(a.csv)
    sl = rc.slice_condition_mesh(df, a.condition, a.mesh)
    sl = sl[sl["montage"] != "reference"]
    floor = _floor()

    jaw = sl[sl.montage == "jaw"]
    if not a.include_near_cut:
        jaw = jaw[~jaw.electrode.isin(NEAR_CUT)]
    ear = sl[sl.montage.isin(("ear", "ceegrid"))]

    rows = []
    for m in rc.MUSCLE_ORDER:
        j, e = jaw[jaw.muscle == m], ear[ear.muscle == m]
        if j.empty or e.empty:
            continue
        bj = j.loc[j.db_rel_best_jaw.idxmax()]
        be = e.loc[e.db_rel_best_jaw.idxmax()]
        rows.append(dict(muscle=m,
                         gap=float(bj.db_rel_best_jaw - be.db_rel_best_jaw),
                         jaw_site=bj.electrode, ear_site=be.electrode))
    if not rows:
        raise SystemExit("no muscle had both a jaw and an ear site")
    rows.sort(key=lambda r: r["gap"])            # ear wins at the top

    n = len(rows)
    y = np.arange(n)
    gaps = np.array([r["gap"] for r in rows])

    fig, ax = plt.subplots(figsize=(7.1, 0.44 * n + 2.0))
    # Colours come from the SEMANTIC constants, not from picking positions on
    # a ramp. Reading poles off a colormap by index is what inverted this
    # figure the first time; rc.EAR_ADVANTAGE cannot be got backwards.
    EAR, JAW = rc.EAR_ADVANTAGE, rc.JAW_ADVANTAGE
    colours = [EAR if g < 0 else JAW for g in gaps]

    # resolution floor as a band, drawn under the bars
    ax.axvspan(-FLOOR_CI_HI, FLOOR_CI_HI, color=rc.INK_MUTED, alpha=0.13,
               zorder=1, lw=0)
    ax.axvspan(-floor, floor, color=rc.INK_MUTED, alpha=0.17, zorder=2, lw=0)
    ax.barh(y, gaps, height=0.62, color=colours,
            edgecolor=rc.SURFACE, linewidth=0.8, zorder=3)
    ax.axvline(0, color=rc.INK_PRIMARY, lw=1.0, zorder=4)

    span = gaps.max() - gaps.min()
    for i, r in enumerate(rows):
        g = r["gap"]
        site = r["ear_site"] if g < 0 else r["jaw_site"]
        off = -0.012 * span if g < 0 else 0.012 * span
        ax.text(g + off, i, f"{g:+.2f} dB · {rc.pretty(site)}",
                va="center", ha="right" if g < 0 else "left",
                fontsize=6.3, color=rc.INK_SECONDARY, zorder=5)

    ax.set_yticks(y)
    ax.set_yticklabels([rc.pretty(r["muscle"]) for r in rows], fontsize=7)
    ax.set_xlabel("best jaw site  −  best ear site   (dB, linear)", fontsize=7.5)
    ax.set_xlim(gaps.min() - 0.30 * span, gaps.max() + 0.30 * span)
    ax.set_ylim(-0.7, n - 0.3)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", color=rc.INK_MUTED, alpha=0.16, lw=0.6, zorder=0)
    ax.set_axisbelow(True)

    # ASCII arrows: the Helvetica/Arial print face has no glyph for U+2190/2192
    # and matplotlib renders them as tofu boxes. Caught by looking at the PNG.
    ax.text(0.0, 1.015, "<-- ear wins", transform=ax.transAxes, ha="left",
            va="bottom", fontsize=6.8, color=EAR)
    ax.text(1.0, 1.015, "jaw wins -->", transform=ax.transAxes, ha="right",
            va="bottom", fontsize=6.8, color=JAW)

    n_ear = int((gaps < 0).sum())
    sub = (f"best site per montage, per muscle   ·   {a.condition}, {a.mesh}   "
           f"·   {n_ear} of {n} muscles favour the ear   ·   band = measured "
           f"floor {floor:.2f} dB (95% CI to {FLOOR_CI_HI:.2f})")
    if not a.include_near_cut:
        sub += "   ·   jaw sites <10 mm from the cut face excluded"
    ax.set_title("Fig 5 · Which montage sees which muscle", loc="left",
                 fontsize=9.5, fontweight="bold", pad=30)
    ax.text(0, 1.055, sub, transform=ax.transAxes, va="bottom", ha="left",
            fontsize=6.2, color=rc.INK_SECONDARY)

    rc.save(fig, "fig5_complementarity_map", df, a.outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
