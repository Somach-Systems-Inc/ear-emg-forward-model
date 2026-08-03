#!/usr/bin/env python3
r"""
Fig 3 — Attenuation vs distance, jaw sites vs ear sites.

Each point is one (electrode, muscle) pair: x = electrode-to-compartment distance
(mm), y = lead field in dB relative to that muscle's best jaw site. Jaw sites
(blue circles) sit near 0 dB at short range; ear sites (orange triangles) sit
farther out and lower — that vertical drop is the dB cost of moving to the ear. A
per-group linear trend makes the slope explicit; the muscles that stay loudest at
the ear are labelled because they are the ones the ear argument rests on.

Colour job: CATEGORICAL, two series (jaw / ear) — validated blue/orange pair
(CVD ΔE 96.7, contrast >=3:1). Marker shape is a redundant second channel.

    simnibs_python figures/render_fig3.py --csv results/04_sensitivity_MOCK.csv
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
    ap.add_argument("--outdir", type=Path, default=rc.FIGDIR)
    a = ap.parse_args(argv)

    rc.use_print_style()
    import matplotlib.pyplot as plt

    df = rc.load_sensitivity(a.csv)
    sl = rc.slice_condition_mesh(df, a.condition, a.mesh)
    sl = sl[sl["montage"].isin(["jaw", "ear"])]
    if "distance_mm" not in sl.columns:
        raise SystemExit("Fig 3 needs the distance_mm column (see the contract in "
                         "figures/mock_data.py); the CSV does not carry it.")

    fig, ax = plt.subplots(figsize=(4.3, 3.5))
    ax.grid(True, axis="both", zorder=0)
    ax.axhline(0, color=rc.BASELINE, lw=1.0, zorder=1)

    for montage in ("jaw", "ear"):
        g = sl[sl["montage"] == montage]
        colour, marker, label = rc.MONTAGE_STYLE[montage]
        ax.scatter(g["distance_mm"], g["db_rel_best_jaw"], s=18, marker=marker,
                   facecolor=colour, edgecolor=rc.SURFACE, linewidth=0.5,
                   alpha=0.85, zorder=4, label=label)
        # per-group linear trend (the "cost of distance")
        if len(g) >= 2:
            x = g["distance_mm"].to_numpy(); y = g["db_rel_best_jaw"].to_numpy()
            b, a0 = np.polyfit(x, y, 1)
            xs = np.array([x.min(), x.max()])
            ax.plot(xs, b * xs + a0, color=colour, lw=2.0, alpha=0.55, zorder=3)

    # label the muscles that stay loudest at the ear (the argument-carriers)
    ear = sl[sl["montage"] == "ear"]
    best_ear = ear.sort_values("db_rel_best_jaw", ascending=False) \
        .drop_duplicates("muscle").head(3)
    for row in best_ear.itertuples():
        ax.annotate(rc.pretty(row.muscle),
                    (row.distance_mm, row.db_rel_best_jaw),
                    xytext=(5, 3), textcoords="offset points",
                    fontsize=6.2, color=rc.INK_SECONDARY, zorder=6)

    ear_med = ear["db_rel_best_jaw"].median()
    ax.text(0.97, 0.05, f"ear median {ear_med:.1f} dB re best jaw",
            transform=ax.transAxes, ha="right", va="bottom",
            fontsize=6.4, color=rc.INK_MUTED)

    ax.set_xlabel("electrode-to-compartment distance (mm)")
    ax.set_ylabel("lead field (dB re best jaw site)")
    ax.set_title("Fig 3 · Cost of distance: jaw vs ear", loc="left",
                 fontsize=9.5, fontweight="bold", pad=16)
    ax.text(0, 1.02, f"condition = {a.condition}, mesh = {a.mesh}",
            transform=ax.transAxes, fontsize=6.8, color=rc.INK_SECONDARY)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(loc="lower left", handletextpad=0.3)

    rc.save(fig, "fig3_attenuation_vs_distance", df, a.outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
