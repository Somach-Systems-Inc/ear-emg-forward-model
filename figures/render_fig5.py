#!/usr/bin/env python3
r"""
Fig 5 — Ranked retroauricular positions by total articulator sensitivity.

The design table an earbud team actually uses: every retroauricular site (the 4
ear positions + the 10 cEEGrid positions) ranked by the total lead field it picks
up, summed over all 18 articulator muscles. Horizontal bars, sorted; the top-N are
highlighted as a candidate montage and the rest greyed — EMPHASIS form, because
the reader's job is "which handful of sites do I place", not "tell 14 series apart".

Colour job: EMPHASIS (one accent hue + de-emphasis grey). Bar length is the only
measure — one axis. Values are labelled at the tips.

Note: total = Σ lead field (linear) across muscles, so louder muscles contribute
more; this is picked-up signal, not a per-muscle average. Which of the top sites
are mutually redundant (adjacent sites seeing the same thing) is the channel-
redundancy analysis in the paper — this figure ranks, it does not yet dedupe.

    simnibs_python figures/render_fig5.py --csv results/04_sensitivity_MOCK.csv --top 4
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

import render_common as rc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, default=rc.DEFAULT_CSV)
    ap.add_argument("--condition", default="iso", choices=["iso", "aniso"])
    ap.add_argument("--mesh", default="extended", choices=["truncated", "extended"])
    ap.add_argument("--top", type=int, default=4, help="highlight the top-N as a candidate subset")
    ap.add_argument("--outdir", type=Path, default=rc.FIGDIR)
    a = ap.parse_args(argv)

    rc.use_print_style()
    import matplotlib.pyplot as plt

    df = rc.load_sensitivity(a.csv)
    sl = rc.slice_condition_mesh(df, a.condition, a.mesh)
    sl = sl[sl["montage"].isin(["ear", "ceegrid"])]

    total = (sl.groupby("electrode")["lead_field"].sum()
             .sort_values(ascending=False))
    names = list(total.index)
    vals = total.to_numpy()
    n = len(names)
    top = min(a.top, n)
    colours = [rc.ACCENT if i < top else rc.DEEMPH for i in range(n)]

    fig, ax = plt.subplots(figsize=(4.2, 0.30 * n + 1.4))
    y = np.arange(n)[::-1]            # rank 1 at the top
    ax.barh(y, vals, height=0.62, color=colours, edgecolor=rc.SURFACE, linewidth=0.8,
            zorder=3)
    ax.grid(True, axis="x", zorder=0)

    pad = vals.max() * 0.012
    for yi, v in zip(y, vals):
        ax.text(v + pad, yi, f"{v:.2f}", va="center", ha="left",
                fontsize=6.4, color=rc.INK_SECONDARY)

    ax.set_yticks(y)
    ax.set_yticklabels([rc.pretty(nm) for nm in names])
    ax.set_xlim(0, vals.max() * 1.12)
    ax.set_xlabel("total articulator sensitivity  (Σ lead field, V/m per mA)")
    ax.set_title("Fig 5 · Retroauricular site ranking", loc="left",
                 fontsize=9.5, fontweight="bold", pad=16)
    ax.text(0, 1.02, f"summed over 18 articulator muscles · condition = {a.condition}"
            f", mesh = {a.mesh} · top {top} highlighted",
            transform=ax.transAxes, fontsize=6.8, color=rc.INK_SECONDARY)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(length=0)

    # two-entry legend for the emphasis split (identity never colour-alone)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(facecolor=rc.ACCENT, label=f"candidate subset (top {top})"),
                       Patch(facecolor=rc.DEEMPH, label="other sites")],
              loc="lower right", handlelength=1.0, handletextpad=0.4)

    rc.save(fig, "fig5_retroauricular_ranking", df, a.outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
