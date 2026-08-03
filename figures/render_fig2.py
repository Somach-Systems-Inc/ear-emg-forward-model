#!/usr/bin/env python3
r"""
Fig 2 — THE MONEY FIGURE. Articulator sensitivity matrix.

Muscles (rows, grouped) x electrode sites (columns, grouped by montage), colour =
lead-field magnitude in dB relative to each muscle's best jaw site (0 dB). Answers
"what can you see from where": the jaw block sits near 0 dB by construction; how
far the ear / cEEGrid columns fall below it is the cost of moving to the ear, and
any cell at or above 0 dB is a site that beats every jaw electrode for that muscle.

Colour job: SEQUENTIAL (one blue hue, light = attenuated, dark = sensitive) — the
data is magnitude, not identity or polarity. Reference electrodes are excluded
(they are not sensing channels). No per-cell numbers (that is the "number on every
point" anti-pattern for an 18x22 grid); exact values live in the CSV. A small ring
marks each row's 0 dB reference site so the reader sees what every row is measured
against.

    simnibs_python figures/render_fig2.py --csv results/04_sensitivity_MOCK.csv
    simnibs_python figures/render_fig2.py           # defaults to results/04_sensitivity.csv
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
    sl = sl[sl["montage"] != "reference"]

    M, rows, cols = rc.ordered_matrix(sl, "db_rel_best_jaw")
    vmin = float(np.floor(np.nanmin(M)))
    vmax = float(np.ceil(np.nanmax(M)))

    fig, ax = plt.subplots(figsize=(6.7, 5.3))
    im = ax.imshow(M, aspect="auto", cmap=rc.sequential_cmap(), vmin=vmin, vmax=vmax)

    col_montage, _ = rc.decorate_matrix(ax, rows, cols)

    # mark each row's 0 dB reference = its loudest jaw site. That may be quieter
    # than a near-ear site (temporalis, digastric posterior), so search the jaw
    # columns only — argmax over the whole row would miss the reference entirely.
    jaw_idx = [i for i, m in enumerate(col_montage) if m == "jaw"]
    for ri in range(len(rows)):
        ci = jaw_idx[int(np.nanargmax(M[ri, jaw_idx]))]
        ax.plot(ci, ri, marker="o", ms=3.4, mfc="none",
                mec=rc.INK_PRIMARY, mew=0.8, zorder=5)

    cbar = fig.colorbar(im, ax=ax, fraction=0.030, pad=0.02)
    cbar.set_label("lead field  (dB re best jaw site)", fontsize=7)
    cbar.ax.tick_params(labelsize=6, length=0)
    cbar.outline.set_visible(False)

    rc.matrix_titles(ax, "Fig 2 · Articulator sensitivity matrix",
                     f"median lead field per compartment, dB relative to each "
                     f"muscle's best jaw site   ·   condition = {a.condition}, "
                     f"mesh = {a.mesh}   ·   ring = 0 dB reference site")

    rc.save(fig, "fig2_sensitivity_matrix", df, a.outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
