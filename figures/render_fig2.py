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

    # DIVERGING ABOUT 0 dB, NOT SEQUENTIAL. 0 dB is each muscle's best jaw
    # site, so the SIGN is the result: positive means a retroauricular site
    # BEATS the best jaw site for that muscle, which is measured for
    # temporalis (+3.92), sternocleidomastoid (+2.53) and lateral pterygoid
    # (+1.69). A one-hue sequential ramp has no visual event at zero and would
    # render the sign change as "slightly lighter blue" -- it would bury the
    # finding this figure now exists to show.
    #
    # TwoSlopeNorm pins 0 to the neutral gray midpoint while letting the arms
    # cover unequal data ranges (-22.8 .. +3.9). Symmetric limits at +/-22.8
    # would wash the entire positive arm to near-neutral, which is the same
    # burial by another route. The cost is that saturation is NOT comparable
    # across the midpoint, so two mitigations make the sign readable without
    # relying on colour intensity:
    #   - the colorbar states both arm ranges
    #   - every cell where the ear wins is RINGED, so the sign is carried by
    #     geometry as well as colour. Identity is never colour-alone.
    if vmin >= 0 or vmax <= 0:
        raise RuntimeError(
            f"matrix does not span 0 dB (vmin {vmin}, vmax {vmax}); a "
            f"diverging scale centred on 0 would imply a sign change that is "
            f"not in the data. Use the sequential ramp and say so.")
    from matplotlib.colors import TwoSlopeNorm
    norm = TwoSlopeNorm(vmin=vmin, vcenter=0.0, vmax=vmax)

    fig, ax = plt.subplots(figsize=(6.7, 5.3))
    im = ax.imshow(M, aspect="auto", cmap=rc.diverging_cmap(), norm=norm)

    # secondary encoding of the sign
    win_r, win_c = np.where(np.nan_to_num(M, nan=-1e9) > 0)
    for ri, ci in zip(win_r, win_c):
        ax.add_patch(plt.Rectangle((ci - 0.5, ri - 0.5), 1, 1, fill=False,
                                   ec=rc.INK_PRIMARY, lw=0.9, zorder=6))

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
    cbar.set_label(
        f"lead field  (dB re best jaw site)\n"
        f"0 = best jaw site  ·  ringed cells: ear beats jaw\n"
        f"arms are NOT equally scaled: {vmin:+.0f}..0 and 0..{vmax:+.0f} dB",
        fontsize=6.4)
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
