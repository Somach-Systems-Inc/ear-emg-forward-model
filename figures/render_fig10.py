#!/usr/bin/env python3
r"""
Fig 10 — How the temporalis advantage dissolved, and what replaced it.

§4.8 tells this as a four-row table and three paragraphs. The table gives the
numbers but not the two things a sceptical reader wants: how large each
correction was relative to the others, and what the final interval is made of.

Panel A is the cascade. Four stages, each sourced from a different file, each
removing one optimistic assumption. The bar is the point estimate; the rule is
the matched-count interval where one exists. Only the last stage crosses zero.

Panel B is what that last interval actually is. It is not a confidence interval
and there is no sampling distribution behind it. The ear pool holds 14 candidate
sites and a montage takes 4, so there are exactly C(14,4) = 1001 possible
retroauricular montages, and every one of them is computed here. The histogram
IS the population. Half of those montages favour the ear and half favour the
jaw, which is the sense in which the advantage did not survive: it depends on
which four sites a device happens to carry.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python figures/render_fig10.py
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "figures"))
import config               # noqa: E402
import render_common as rc  # noqa: E402

CLUSTER = ["buccal", "mental", "midjaw", "submaxillary"]


def _stages(pd):
    """Each cascade stage, read from the file that reproduces it.

    Nothing here is transcribed from the manuscript. If a stage stops
    reproducing, this raises rather than drawing a stale number.
    """
    ear = list(config.MONTAGES["ear"]) + list(config.MONTAGES["ceegrid"])

    lf = pd.read_csv(config.RESULTS / "03_leadfields.csv").set_index("electrode")
    mag = 20 * np.log10(lf.loc[CLUSTER, "temporalis"].max()
                        / lf.loc[ear, "temporalis"].max())

    osign = pd.read_csv(config.RESULTS / "04d_orientation_sign.csv")
    proj = float(osign.loc[osign.muscle == "temporalis", "gap_median_dB"].iloc[0])

    site = pd.read_csv(config.RESULTS / "04n_site_set_sensitivity.csv")
    site = site[(site.muscle == "temporalis") & site.is_published_set].iloc[0]

    hl = pd.read_csv(config.RESULTS / "04p_headline_interval.csv", comment="#")
    hl = hl[(hl.construction == "pervoxel_EXACT") & hl.is_published_basis].iloc[0]

    return [
        ("field magnitude\nbest of 14 ear sites", float(mag), None, None,
         "the magnitude is the maximum over orientations"),
        ("projected onto\nsource orientation", proj, None, None,
         "median over a 200-direction sweep"),
        ("matched electrode counts\nfour sites each", float(site.cluster_gap_dB),
         float(site.rand4_lo), float(site.rand4_hi),
         "best of 14 against best of 4 rewards density"),
        ("derived per-voxel\nfibre field", float(hl.median_dB),
         float(hl.lo_dB), float(hl.hi_dB),
         "the sweep assumed a direction the anatomy supplies"),
    ]


def _exact_subsets(pd):
    """Every one of the C(14,4) = 1001 possible four-site ear montages."""
    pv = pd.read_csv(config.RESULTS / "04k_temporalis_pervoxel.csv") \
           .set_index("electrode")["lf_pervoxel_fan"].to_dict()
    ear = sorted(list(config.MONTAGES["ear"]) + list(config.MONTAGES["ceegrid"]))
    J = max(pv[e] for e in CLUSTER)
    d = np.array([20 * np.log10(J / max(pv[e] for e in s))
                  for s in itertools.combinations(ear, len(CLUSTER))])
    return d, 20 * np.log10(J / max(pv[e] for e in ear))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="render_fig10.py")
    ap.add_argument("--outdir", type=Path, default=rc.FIGDIR)
    a = ap.parse_args(argv)

    rc.use_print_style()
    import matplotlib.pyplot as plt
    import pandas as pd

    stages = _stages(pd)
    d, floor = _exact_subsets(pd)

    # GUARD. The figure must reproduce the interval the manuscript reports; a
    # figure that quietly disagrees with its own paper is worse than no figure.
    hl = pd.read_csv(config.RESULTS / "04p_headline_interval.csv", comment="#")
    hl = hl[(hl.construction == "pervoxel_EXACT") & hl.is_published_basis].iloc[0]
    # 04p's bounds are the 2.5 and 97.5 percentiles of the enumerated set, not
    # its min and max. The distinction is not cosmetic: 28.6 % of the 1001
    # montages attain the floor exactly, which is why the lower bound and the
    # floor coincide, while the upper tail runs on to 8.78 dB well past the
    # 97.5th percentile. Comparing against min/max here failed the guard, which
    # is what the guard is for.
    p_lo, p_hi = np.percentile(d, [2.5, 97.5])
    for got, want, what in ((np.median(d), hl.median_dB, "median"),
                            (p_lo, hl.lo_dB, "2.5th percentile"),
                            (p_hi, hl.hi_dB, "97.5th percentile"),
                            (floor, hl.floor_dB, "floor")):
        if abs(got - want) > 5e-4:
            raise SystemExit(f"enumeration disagrees with 04p on the {what}: "
                             f"{got:.4f} vs {want:.4f}")
    if len(d) != 1001:
        raise SystemExit(f"expected C(14,4) = 1001 subsets, enumerated {len(d)}")
    pct_ear = 100.0 * (d < 0).mean()

    fig = plt.figure(figsize=(7.3, 3.9))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.28, 1.0], wspace=0.42,
                          left=0.235, right=0.985, bottom=0.185, top=0.90)
    axA, axB = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1])

    # ---------- A: the cascade
    y = np.arange(len(stages))[::-1]
    for yy, (label, val, lo, hi, _why) in zip(y, stages):
        crosses = lo is not None and lo < 0 < hi
        col = rc.NO_DIFFERENCE if crosses else rc.EAR_ADVANTAGE
        axA.barh(yy, val, height=0.44, color=col,
                 edgecolor=rc.INK_MUTED if crosses else rc.SURFACE,
                 linewidth=0.6, zorder=3)
        if lo is not None:
            axA.plot([lo, hi], [yy, yy], color=rc.INK_PRIMARY, lw=1.1,
                     zorder=5, solid_capstyle="butt")
            for b in (lo, hi):
                axA.plot([b, b], [yy - 0.14, yy + 0.14], color=rc.INK_PRIMARY,
                         lw=1.1, zorder=5)
        # Labels sit OUTSIDE the bar. Inside-the-bar white text disappeared on
        # the last stage, whose bar is both short and pale because its interval
        # spans zero -- precisely the row a reader most needs to read.
        # lift the label clear of the whisker on the row whose interval is
        # wide enough to run underneath it
        axA.annotate(f"{val:.2f} dB", (0, yy), textcoords="offset points",
                     xytext=(5, 6 if crosses else -2.2), ha="left",
                     fontsize=6.2, color=rc.INK_PRIMARY, zorder=6)
    axA.axvline(0, color=rc.INK_PRIMARY, lw=1.0, zorder=4)
    axA.set_yticks(y)
    axA.set_yticklabels([s[0] for s in stages], fontsize=6.2, linespacing=1.35)
    axA.set_xlabel("temporalis gap (dB)   ·   negative favours the ear",
                   fontsize=6.8)
    axA.set_ylim(-0.62, len(stages) - 0.38)
    for s in ("top", "right", "left"):
        axA.spines[s].set_visible(False)
    axA.tick_params(axis="y", length=0)
    axA.grid(axis="x", color=rc.INK_MUTED, alpha=0.15, lw=0.5)
    axA.set_axisbelow(True)
    axA.set_title("A   three corrections, each standard, each the same way",
                  fontsize=7.2, pad=4, loc="left")
    axA.annotate("interval spans zero", (stages[-1][3], y[-1]),
                 textcoords="offset points", xytext=(-2, 11), ha="right",
                 fontsize=5.8, color=rc.INK_SECONDARY, zorder=6)

    # ---------- B: every possible four-site ear montage
    bins = np.linspace(d.min(), d.max(), 46)
    axB.hist(d[d < 0], bins=bins, color=rc.EAR_ADVANTAGE, zorder=3, lw=0)
    axB.hist(d[d >= 0], bins=bins, color=rc.JAW_ADVANTAGE, zorder=3, lw=0)
    axB.axvline(0, color=rc.INK_PRIMARY, lw=1.0, zorder=5)
    axB.axvline(float(np.median(d)), color=rc.INK_PRIMARY, lw=1.0, ls=(0, (3, 2)),
                zorder=5)
    axB.set_ylim(0, 330)
    axB.annotate(f"median {np.median(d):.2f} dB", (float(np.median(d)), 235),
                 textcoords="offset points", xytext=(7, 0), ha="left",
                 va="center", fontsize=5.8, color=rc.INK_SECONDARY, zorder=6)
    axB.annotate(f"{pct_ear:.1f}% favour the ear", (0.975, 0.94),
                 xycoords="axes fraction", ha="right", fontsize=6.2,
                 color=rc.EAR_ADVANTAGE, zorder=6)
    axB.annotate(f"{100 - pct_ear:.1f}% favour the jaw", (0.975, 0.86),
                 xycoords="axes fraction", ha="right", fontsize=6.2,
                 color=rc.JAW_ADVANTAGE, zorder=6)
    for q, lab in ((p_lo, "2.5%"), (p_hi, "97.5%")):
        axB.axvline(q, color=rc.INK_MUTED, lw=0.8, ls=(0, (1.5, 1.5)), zorder=4)
    axB.set_xlabel("temporalis gap (dB) for one four-site ear montage\n"
                   "dotted: the 2.5 and 97.5 percentiles",
                   fontsize=6.4, linespacing=1.5)
    axB.set_ylabel("number of montages", fontsize=6.8)
    axB.set_title("B   all C(14,4) = 1001 of them, enumerated",
                  fontsize=7.2, pad=4, loc="left")
    for s in ("top", "right"):
        axB.spines[s].set_visible(False)
    axB.grid(axis="y", color=rc.INK_MUTED, alpha=0.15, lw=0.5)
    axB.set_axisbelow(True)

    if not rc.PAPER_MODE:
        fig.suptitle("Fig 10 · How the retroauricular advantage dissolved",
                     x=0.012, ha="left", fontsize=9.5, fontweight="bold")

    prov = pd.DataFrame({"x": [0]})
    prov.attrs["source"] = str(config.RESULTS / "04p_headline_interval.csv")
    prov.attrs["is_mock"] = False
    rc.save(fig, "fig10_advantage_cascade", prov, a.outdir)
    print(f"  cascade: " + " -> ".join(f"{s[1]:.2f}" for s in stages))
    print(f"  1001 subsets: median {np.median(d):.4f}, "
          f"pct interval [{p_lo:.4f}, {p_hi:.4f}], full range "
          f"[{d.min():.4f}, {d.max():.4f}], {pct_ear:.1f}% favour the ear")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
