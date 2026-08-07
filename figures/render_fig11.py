#!/usr/bin/env python3
r"""
Fig 11 — Both robustness axes at once, and the one row where the basis decides.

Table 4 is the densest object in the paper: two robustness axes, an envelope
over five admissible jaw subsets, and a verdict, for ten muscles. Figure 3 shows
the ORIENTATION axis. Nothing showed the SITE axis, which is the axis that
decides the paper's title.

This draws Table 4. One bar per muscle, spanning the envelope over all five
admissible jaw subsets, coloured by verdict, against a zero line.

IT ALSO DRAWS THE THING TABLE 4 CANNOT SHOW. Table 4 is computed on statistic A,
the median over a uniform 200-direction orientation sweep. On that basis
temporalis is "ear, robust on both axes" -- its whole envelope sits on the ear
side. The paper's title says no articulator robustly favours the ear, and that
claim rests on a DIFFERENT basis: the per-voxel fibre field derived from the
label volume (§4.8), under which temporalis is -1.15 dB with an interval of
[-1.45, +5.46] that spans zero.

Both are true of their own basis, and a reader who only sees Table 4 will think
the title is contradicted by it. So the derived-fibre interval is drawn on the
temporalis row as a second rule, and it is the only row that carries one,
because it is the only muscle whose verdict depends on which basis is used.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python figures/render_fig11.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "figures"))
import config               # noqa: E402
import render_common as rc  # noqa: E402

BASIS_DEPENDENT = "temporalis"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="render_fig11.py")
    ap.add_argument("--envelope", type=Path,
                    default=config.RESULTS / "04q_table4_envelope.csv")
    ap.add_argument("--fibre", type=Path,
                    default=config.RESULTS / "04p_headline_interval.csv")
    ap.add_argument("--outdir", type=Path, default=rc.FIGDIR)
    a = ap.parse_args(argv)

    rc.use_print_style()
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    import pandas as pd

    d = pd.read_csv(a.envelope, comment="#") \
          .sort_values("gap_lo_dB").reset_index(drop=True)
    hl = pd.read_csv(a.fibre, comment="#")
    hl = hl[(hl.construction == "pervoxel_EXACT") & hl.is_published_basis].iloc[0]

    # GUARDS. Both halves of the figure's claim are checked against the data.
    ear_rows = d[d.verdict.str.startswith("ear")]
    if list(ear_rows.muscle) != [BASIS_DEPENDENT]:
        raise SystemExit(
            f"on the statistic-A basis the ear-robust set is "
            f"{list(ear_rows.muscle)}, not ['{BASIS_DEPENDENT}']. The figure "
            f"and §4.8 both assume exactly one basis-dependent row.")
    if not (hl.lo_dB < 0 < hl.hi_dB):
        raise SystemExit(
            f"the derived fibre interval [{hl.lo_dB}, {hl.hi_dB}] no longer "
            f"spans zero, so temporalis is NOT basis-dependent and the paper's "
            f"title claim needs rechecking before this figure is drawn.")

    n = len(d)
    fig, ax = plt.subplots(figsize=(7.3, 0.28 * n + 1.3))
    fig.subplots_adjust(left=0.225, right=0.775, bottom=0.245, top=0.875)

    for i, r in d.iterrows():
        v = r.verdict
        col = (rc.JAW_ADVANTAGE if v.startswith("jaw")
               else rc.EAR_ADVANTAGE if v.startswith("ear")
               else rc.NO_DIFFERENCE)
        ax.plot([r.gap_lo_dB, r.gap_hi_dB], [i, i], color=col, lw=7.0,
                alpha=0.9, zorder=3, solid_capstyle="butt")
        if v.startswith("unstable"):
            ax.plot(0, i, marker="o", ms=4.5, mfc=rc.SURFACE,
                    mec=rc.INK_PRIMARY, mew=1.0, ls="", zorder=6)

    # the one row whose verdict depends on the fibre basis
    j = int(d.index[d.muscle == BASIS_DEPENDENT][0])
    ax.plot([hl.lo_dB, hl.hi_dB], [j - 0.30, j - 0.30], color=rc.INK_PRIMARY,
            lw=1.4, zorder=5, solid_capstyle="butt")
    for b in (hl.lo_dB, hl.hi_dB):
        ax.plot([b, b], [j - 0.42, j - 0.18], color=rc.INK_PRIMARY, lw=1.4,
                zorder=5)
    ax.plot(hl.median_dB, j - 0.30, marker="o", ms=4.0, mfc=rc.INK_PRIMARY,
            mec=rc.SURFACE, mew=0.7, ls="", zorder=6)
    ax.annotate("same muscle, derived fibre field (§4.8): spans zero",
                (hl.hi_dB, j - 0.30), textcoords="offset points",
                xytext=(6, -2), ha="left", fontsize=6.4,
                color=rc.INK_PRIMARY, zorder=7)

    ax.axvline(0, color=rc.INK_PRIMARY, lw=1.0, zorder=4)
    ax.set_yticks(range(n))
    ax.set_yticklabels([rc.pretty(m) for m in d.muscle], fontsize=7.4)
    ax.set_ylim(-0.95, n - 0.35)
    ax.set_xlabel("jaw minus ear (dB), envelope over all five admissible "
                  "jaw subsets, electrode counts matched at four", fontsize=7.2)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=rc.INK_MUTED, alpha=0.15, lw=0.5)
    ax.set_axisbelow(True)

    ax.text(0.0, 1.012, "<-- ear side", transform=ax.transAxes, ha="left",
            va="bottom", fontsize=7, color=rc.EAR_ADVANTAGE)
    ax.text(1.0, 1.012, "jaw side -->", transform=ax.transAxes, ha="right",
            va="bottom", fontsize=7, color=rc.JAW_ADVANTAGE)

    # the other axis, as a column, so one row carries both
    ax.text(1.04, 1.012, "orientations agreeing", transform=ax.transAxes,
            ha="left", va="bottom", fontsize=6.4, color=rc.INK_SECONDARY)
    for i, r in d.iterrows():
        lo, hi = float(r.orient_lo_pct), float(r.orient_hi_pct)
        txt = f"{lo:.0f}%" if lo == hi else f"{lo:.0f}-{hi:.0f}%"
        ax.text(1.04, i, txt, transform=ax.get_yaxis_transform(), ha="left",
                va="center", fontsize=7,
                color=rc.INK_PRIMARY if lo == 100 else rc.INK_SECONDARY)
        ax.text(1.135, i, f"{int(r.site_robust_subsets)} of "
                          f"{int(r.n_subsets)} subsets",
                transform=ax.get_yaxis_transform(), ha="left", va="center",
                fontsize=6.2, color=rc.INK_MUTED)

    h = [Line2D([], [], color=rc.JAW_ADVANTAGE, lw=4, label="jaw"),
         Line2D([], [], color=rc.EAR_ADVANTAGE, lw=4,
                label="ear, on the statistic-A basis only"),
         Line2D([], [], color=rc.NO_DIFFERENCE, lw=4,
                label="unstable: verdict changes between jaw subsets"),
         Line2D([], [], color=rc.INK_PRIMARY, lw=1.4,
                label="derived per-voxel fibre field")]
    leg = ax.legend(handles=h, frameon=False, fontsize=6.4, ncol=2,
                    loc="upper center", bbox_to_anchor=(0.42, -0.185),
                    handlelength=2.0, columnspacing=1.6)
    for t in leg.get_texts():
        t.set_color(rc.INK_SECONDARY)

    if not rc.PAPER_MODE:
        ax.set_title("Fig 11 · Both robustness axes, and the one verdict that "
                     "depends on the fibre basis", loc="left", fontsize=9.5,
                     fontweight="bold", pad=26)

    prov = pd.DataFrame({"x": [0]})
    prov.attrs["source"] = str(a.envelope)
    prov.attrs["is_mock"] = False
    rc.save(fig, "fig11_two_axis_envelope", prov, a.outdir)

    njaw = int(d.verdict.str.startswith("jaw").sum())
    print(f"  {njaw} muscles jaw, 1 ear on statistic A, "
          f"{int(d.verdict.str.startswith('unstable').sum())} unstable")
    print(f"  temporalis: statistic A [{d.loc[j, 'gap_lo_dB']:+.4f}, "
          f"{d.loc[j, 'gap_hi_dB']:+.4f}] entirely on the ear side; "
          f"derived fibre [{hl.lo_dB:+.4f}, {hl.hi_dB:+.4f}] spans zero")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
