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
    ap.add_argument("--sign", type=Path,
                    default=Path("results/04d_orientation_sign.csv"))
    ap.add_argument("--npz", type=Path,
                    default=Path("results/04d_orientation_sign.npz"))
    ap.add_argument("--outdir", type=Path, default=rc.FIGDIR)
    a = ap.parse_args(argv)

    rc.use_print_style()
    import matplotlib.pyplot as plt
    import pandas as pd

    d = pd.read_csv(a.sign)
    z = np.load(a.npz)
    floor = _floor()
    d["pct_ear"] = (1 - d.frac_favouring_jaw) * 100
    d = d.sort_values("gap_median_dB")            # ear wins at the top

    n = len(d)
    fig, ax = plt.subplots(figsize=(7.4, 0.52 * n + 2.2))

    for i, (_, r) in enumerate(d.iterrows()):
        g = z[f"gap_{r.muscle}"]
        stable = bool(r.sign_stable)
        col = rc.EAR_ADVANTAGE if r.gap_median_dB < 0 else rc.JAW_ADVANTAGE
        # full min-max range as a thin rule
        ax.plot([g.min(), g.max()], [i, i], color=col,
                lw=1.2, alpha=0.45, zorder=2, solid_capstyle="round")
        # interquartile body, thicker
        q1, q3 = np.percentile(g, [25, 75])
        ax.plot([q1, q3], [i, i], color=col, lw=6.5, alpha=0.85,
                zorder=3, solid_capstyle="butt")
        # median marker: filled circle if sign-stable, open if graded
        ax.plot(r.gap_median_dB, i, marker="o", ms=7,
                mfc=(col if stable else rc.SURFACE), mec=col, mew=1.6,
                zorder=5)
        lbl = ("sign stable" if stable
               else f"{r.pct_ear:.0f}% of orientations favour ear")
        ax.text(g.max() + 0.03 * (z["gap_mentalis"].max()), i, lbl,
                va="center", ha="left", fontsize=6.0,
                color=(rc.INK_SECONDARY if stable else rc.INK_MUTED), zorder=5)

    ax.axvspan(-floor, floor, color=rc.INK_MUTED, alpha=0.15, zorder=1, lw=0)
    ax.axvline(0, color=rc.INK_PRIMARY, lw=1.0, zorder=4)
    ax.set_yticks(range(n))
    ax.set_yticklabels([rc.pretty(m) for m in d.muscle], fontsize=7)
    ax.set_xlabel("best jaw site  −  best ear site   (dB, linear)  ·  swept "
                  "over 200 source orientations", fontsize=7.5)
    ax.set_ylim(-0.8, n - 0.2)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.grid(axis="x", color=rc.INK_MUTED, alpha=0.16, lw=0.6, zorder=0)
    ax.set_axisbelow(True)

    ax.text(0.0, 1.012, "<-- ear wins", transform=ax.transAxes, ha="left",
            va="bottom", fontsize=6.8, color=rc.EAR_ADVANTAGE)
    ax.text(1.0, 1.012, "jaw wins -->", transform=ax.transAxes, ha="right",
            va="bottom", fontsize=6.8, color=rc.JAW_ADVANTAGE)

    n_stable = int(d.sign_stable.sum())
    if not rc.PAPER_MODE:
        ax.set_title("Fig 3 · Which montage sees which muscle, over all source "
                     "orientations", loc="left", fontsize=9.5,
                     fontweight="bold", pad=52)
        ax.text(0, 1.028,
                f"thin rule = full min-max over 200 orientations   ·   thick bar = "
                f"interquartile   ·   marker = median\n"
                f"FILLED marker = sign stable at every orientation "
                f"({n_stable} of {n} muscles)   ·   open marker = verdict depends "
                f"on fibre direction   ·   band = {floor:.2f} dB floor\n"
                f"VERDICTS ARE TWO-AXIS (Table 4): only temporalis is robust to BOTH "
                f"orientation and site sampling; SCM and lateral pterygoid fail the "
                f"matched-count test and are no resolvable preference",
                transform=ax.transAxes, va="bottom", ha="left",
                fontsize=6.2, color=rc.INK_SECONDARY)

    prov = pd.DataFrame({"x": [0]})
    prov.attrs["source"] = str(a.sign)
    prov.attrs["is_mock"] = False
    rc.save(fig, "fig3_complementarity_map", prov, a.outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
