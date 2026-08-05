#!/usr/bin/env python3
r"""
Fig 3 — Attenuation against source-electrode distance, jaw versus ear.

Each point is one (electrode, muscle) pair: x is the straight-line distance
from the electrode to the nearest voxel of that muscle compartment, y is the
lead field in dB relative to that muscle's best jaw site. Jaw and retroauricular
sites are drawn as separate series so the reader can see whether the ear sits on
the same distance-attenuation curve as the jaw or on a different one.

Colour job: CATEGORICAL over two montages, using the project's semantic
constants so that "ear" is the same hue here as in Figs 2 and 5.

    simnibs_python figures/render_fig3.py
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
    ap.add_argument("--csv", type=Path, default=rc.DEFAULT_CSV)
    ap.add_argument("--dist", type=Path,
                    default=Path("results/04c_electrode_muscle_distance.csv"))
    ap.add_argument("--condition", default="iso", choices=["iso", "aniso"])
    ap.add_argument("--mesh", default="truncated")
    ap.add_argument("--outdir", type=Path, default=rc.FIGDIR)
    a = ap.parse_args(argv)

    rc.use_print_style()
    import matplotlib.pyplot as plt

    df = rc.load_sensitivity(a.csv)
    sl = rc.slice_condition_mesh(df, a.condition, a.mesh)
    sl = sl[sl["montage"] != "reference"]
    dist = pd.read_csv(a.dist)
    m = sl.merge(dist[["electrode", "muscle", "dist_mm"]],
                 on=["electrode", "muscle"], how="inner")
    if m.empty:
        raise SystemExit("no (electrode, muscle) pairs matched between the "
                         "sensitivity and distance tables")

    m["grp"] = np.where(m.montage == "jaw", "jaw", "retroauricular")
    fig, ax = plt.subplots(figsize=(6.4, 4.4))

    # THE OVERLAPPING RANGE. Fitting each montage over its own distance span
    # and then comparing slopes compares two different intervals: the jaw sites
    # reach 87 mm, the retroauricular ones 156 mm, and a slope quoted over a
    # longer lever arm is not comparable to one over a shorter. Both are
    # therefore fitted over the INTERSECTION, and the own-range fits are
    # reported alongside so the difference is visible rather than hidden.
    lo = max(m[m.grp == g].dist_mm.min() for g in ("jaw", "retroauricular"))
    hi = min(m[m.grp == g].dist_mm.max() for g in ("jaw", "retroauricular"))
    print(f"  overlapping range: {lo:.0f}-{hi:.0f} mm")
    fits = {}
    for grp, colour, mk in (("jaw", rc.JAW_ADVANTAGE, "o"),
                            ("retroauricular", rc.EAR_ADVANTAGE, "s")):
        g = m[m.grp == grp]
        ax.scatter(g.dist_mm, g.db_rel_best_jaw, s=14, marker=mk,
                   facecolor=colour, edgecolor=rc.SURFACE, linewidth=0.4,
                   alpha=0.85, label=f"{grp} (n={len(g)})", zorder=3)
        own = np.polyfit(g.dist_mm, g.db_rel_best_jaw, 1)[0]
        ov = g[(g.dist_mm >= lo) & (g.dist_mm <= hi)]
        b, c = np.polyfit(ov.dist_mm, ov.db_rel_best_jaw, 1)
        fits[grp] = b
        xs = np.linspace(lo, hi, 50)
        ax.plot(xs, b * xs + c, color=colour, lw=1.6, alpha=0.75, zorder=2)
        print(f"  {grp:<16} overlap-fit {b:+.3f} dB/mm   "
              f"own-range fit {own:+.3f} over "
              f"{g.dist_mm.min():.0f}-{g.dist_mm.max():.0f} mm  (n={len(ov)})")
    ratio = fits["retroauricular"] / fits["jaw"]
    print(f"  slope ratio over the overlap: {ratio:.2f}x")

    ax.axhline(0, color=rc.INK_PRIMARY, lw=0.9, zorder=4)
    ax.set_xlabel("distance from electrode to nearest voxel of the muscle (mm)",
                  fontsize=7.5)
    ax.set_ylabel("lead field (dB re each muscle's best jaw site)", fontsize=7.5)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(color=rc.INK_MUTED, alpha=0.15, lw=0.6)
    ax.set_axisbelow(True)
    leg = ax.legend(frameon=False, fontsize=6.8, loc="upper right")
    for t in leg.get_texts():
        t.set_color(rc.INK_SECONDARY)

    ax.set_title("Fig 3 · Attenuation against source distance", loc="left",
                 fontsize=9.5, fontweight="bold", pad=26)
    ax.text(0, 1.045,
            f"one point per (electrode, muscle) pair   ·   {a.condition}, "
            f"{a.mesh}   ·   0 dB = each muscle's best jaw site   ·   "
            f"lines are least-squares fits over the OVERLAPPING "
            f"{lo:.0f}-{hi:.0f} mm range",
            transform=ax.transAxes, va="bottom", ha="left",
            fontsize=6.3, color=rc.INK_SECONDARY)

    rc.save(fig, "fig3_attenuation_vs_distance", df, a.outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
