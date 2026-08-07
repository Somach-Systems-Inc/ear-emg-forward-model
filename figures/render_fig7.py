#!/usr/bin/env python3
r"""
Fig 7 — What produces the jaw-versus-ear gap: geometry, or tissue?

WHY THIS FIGURE EXISTS

The paper's causal claim is that the retroauricular deficit is a DISTANCE
effect, not a tissue-conductivity effect. That claim was spread across three
places -- §4.3's prose, the per-muscle percentages, and the rho = -0.955
correlation -- leaving the reader to assemble the mechanism themselves.

This draws the decomposition directly. For each muscle the gap is split into the
part that survives when the adipose/muscle conductivity contrast is removed
(GEOMETRY: the same montage re-solved with both adipose compartments set to
muscle conductivity, geometry held exactly fixed) and the part that does not
(MATERIAL).

Two things become visible that the numbers alone do not carry:

  1. Geometry sets the gap everywhere. For the labial group the material term is
     a rounding error against a 9-21 dB geometric gap.
  2. The material term CHANGES SIGN. For temporalis it acts against the gap --
     removing the contrast makes the ear look better still -- while for
     sternocleidomastoid and lateral pterygoid it acts with it. A single
     "material share" percentage hides that, which is why §4.3 refuses to
     quote one.

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
                    default=Path("results/04e_fat_contrast_statisticA.csv"))
    ap.add_argument("--outdir", type=Path, default=rc.FIGDIR)
    a = ap.parse_args(argv)

    rc.use_print_style()
    import matplotlib.pyplot as plt

    d = pd.read_csv(a.csv)
    d["geometry"] = d.gap_without_contrast_A
    d["material"] = d.gap_with_contrast_A - d.gap_without_contrast_A
    d = d.sort_values("gap_with_contrast_A").reset_index(drop=True)

    fig, ax = plt.subplots(figsize=(6.6, 4.6))
    y = np.arange(len(d))

    ax.barh(y, d.geometry, height=0.62, color=rc.DEEMPH,
            edgecolor=rc.SURFACE, linewidth=0.6, zorder=3,
            label="geometry alone (tissue contrast removed)")
    ax.barh(y, d.material, left=d.geometry, height=0.62,
            color=[rc.JAW_ADVANTAGE if m > 0 else rc.EAR_ADVANTAGE
                   for m in d.material],
            edgecolor=rc.SURFACE, linewidth=0.6, zorder=4,
            label="tissue contrast: red adds to the jaw, blue to the ear")

    ax.axvline(0, color=rc.INK_PRIMARY, lw=0.9, zorder=5)
    ax.set_yticks(y)
    ax.set_yticklabels([rc.pretty(m) for m in d.muscle], fontsize=7)
    ax.set_xlabel("jaw-versus-ear gap (dB); positive favours the jaw montage",
                  fontsize=7.5)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", color=rc.INK_MUTED, alpha=0.15, lw=0.6)
    ax.set_axisbelow(True)
    leg = ax.legend(frameon=False, fontsize=6.6, loc="lower right")
    for t in leg.get_texts():
        t.set_color(rc.INK_SECONDARY)

    for i, r in d.iterrows():
        if abs(r.material) >= 0.9:
            ax.annotate(f"{r.material:+.1f} dB",
                        (r.geometry + r.material, i),
                        textcoords="offset points",
                        xytext=(7 if r.material > 0 else -7, -2.5),
                        ha="left" if r.material > 0 else "right",
                        fontsize=6.0, color=rc.INK_SECONDARY, zorder=6)

    if not rc.PAPER_MODE:
        ax.set_title("Fig 7 · Geometry sets the gap; tissue only trims it",
                     loc="left", fontsize=9.5, fontweight="bold", pad=22)

    fig.tight_layout()
    a.outdir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        out = a.outdir / f"fig7_gap_decomposition.{ext}"
        fig.savefig(out, dpi=300, bbox_inches="tight")
        print(f"  wrote {out}")
    print(f"  material term: {d.material.min():+.3f} to {d.material.max():+.3f} dB")
    print(f"  {(d.material > 0).sum()} muscles the contrast helps the jaw, "
          f"{(d.material < 0).sum()} it helps the ear")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
