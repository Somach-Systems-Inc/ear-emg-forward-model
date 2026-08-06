#!/usr/bin/env python3
r"""
Fig 7 — Material share against adipose path fraction, with leave-one-out.

WHY THIS FIGURE EXISTS

§4.3 reports Spearman rho = -0.955, p = 0.001, n = 7 between a muscle's adipose
path fraction and the material share of its jaw-versus-ear gap, and the paper
had no visualisation of it. #correlation asks for exactly that: "have you used
graphs (e.g., scatter plots) to visualize the correlation between the variables
under study?"

Seven points is few enough that a reader should see them rather than take the
coefficient on trust, and few enough that one outlier could carry the result.
The leave-one-out rho range is therefore drawn as an annotation rather than left
in the text alone.

The relationship is NEGATIVE and that is the interesting part: more fat on the
path means a SMALLER material share, because a muscle embedded uniformly in fat
has both the jaw and the ear route shifted together and the change cancels in
the ratio. The figure exists to make that counterintuitive sign visible.

    simnibs_python figures/render_fig7.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

import render_common as rc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path,
                    default=Path("results/04f_fat_path_vs_share.csv"))
    ap.add_argument("--loo", type=Path,
                    default=Path("results/04t_correlation_robustness.csv"))
    ap.add_argument("--outdir", type=Path, default=rc.FIGDIR)
    a = ap.parse_args(argv)

    rc.use_print_style()
    import matplotlib.pyplot as plt
    from scipy import stats

    d = pd.read_csv(a.csv).dropna(subset=["material_share_pct"])
    if len(d) < 3:
        raise SystemExit("fewer than 3 muscles carry a material share; "
                         "refusing to plot a correlation")
    rho, p = stats.spearmanr(d.fat_frac_of_path, d.material_share_pct)

    fig, ax = plt.subplots(figsize=(6.0, 4.2))

    # Colour by which montage the muscle favours, using the project's semantic
    # constants, so the reader can see that the high-share muscles are the ones
    # whose gap comes closest to zero rather than a random subset.
    ear_side = {"sternocleidomastoid", "lateral_pterygoid"}
    for lab, sel, colour, mk in (
            ("gap favours the jaw", ~d.muscle.isin(ear_side), rc.JAW_ADVANTAGE, "o"),
            ("no resolvable preference", d.muscle.isin(ear_side), rc.EAR_ADVANTAGE, "s")):
        g = d[sel]
        ax.scatter(g.fat_frac_of_path, g.material_share_pct, s=46, marker=mk,
                   facecolor=colour, edgecolor=rc.SURFACE, linewidth=0.6,
                   alpha=0.9, label=f"{lab} (n={len(g)})", zorder=3)

    for _, r in d.iterrows():
        ax.annotate(rc.pretty(r.muscle),
                    (r.fat_frac_of_path, r.material_share_pct),
                    textcoords="offset points", xytext=(6, 4),
                    fontsize=6.2, color=rc.INK_SECONDARY, zorder=4)

    # DELIBERATELY NO TREND LINE. These are seven independent muscles, not a
    # series: joining them implies a continuity between neighbouring points that
    # does not exist, and a least-squares line would imply a functional form
    # Spearman does not claim. The rank statistic is reported in the subtitle
    # and the reader can see the seven points. Adding a line here would be a
    # design choice that is not optimal for the data.

    ax.set_xlabel("adipose fraction of the muscle-to-skin path  (0–1)",
                  fontsize=7.5)
    ax.set_ylabel("material share of the jaw-versus-ear gap  (%)", fontsize=7.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(color=rc.INK_MUTED, alpha=0.15, lw=0.6)
    ax.set_axisbelow(True)
    leg = ax.legend(frameon=False, fontsize=6.8, loc="upper right")
    for t in leg.get_texts():
        t.set_color(rc.INK_SECONDARY)

    sub = (f"Spearman $\\rho$ = {rho:+.3f}, p = {p:.3f}, n = {len(d)}")
    if a.loo.exists():
        lo = pd.read_csv(a.loo, comment="#")
        sub += (f"   ·   leave-one-out $\\rho$ "
                f"{lo.rho.max():+.3f} to {lo.rho.min():+.3f}, "
                f"all p < {max(0.01, lo.p.max()):.2f}")

    ax.set_title("Fig 7 · Material share falls as the fat path grows",
                 loc="left", fontsize=9.5, fontweight="bold", pad=22)
    ax.text(0, 1.045, sub, transform=ax.transAxes, fontsize=6.8,
            color=rc.INK_SECONDARY, va="bottom")

    fig.tight_layout()
    a.outdir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = a.outdir / f"fig7_material_share_vs_fat.{ext}"
        fig.savefig(out, dpi=300, bbox_inches="tight")
        print(f"  wrote {out}")
    print(f"  rho {rho:+.4f}, p {p:.4f}, n {len(d)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
