#!/usr/bin/env python3
r"""
Fig 4 — Isotropic vs anisotropic muscle conductivity, same matrix layout as Fig 2.

Quantifies the modelling error introduced by treating muscle as a scalar rather
than a tensor. Each cell is the change in that (electrode, muscle) lead field
between the two runs, 20*log10(lead_field_aniso / lead_field_iso), in dB. Rows for
muscles modelled isotropically in BOTH runs (sphincters, fans, sheets — see
src/config.py FIBRE_MODEL) are 0 by construction and read as neutral grey; the
strap-like muscles that carry a fibre tensor are where anisotropy actually moves
the estimate.

Colour job: DIVERGING (blue = anisotropy raises the lead field, red = lowers it,
neutral grey = no change) — the data is signed polarity about a true zero.

    simnibs_python figures/render_fig4.py --csv results/04_sensitivity_MOCK.csv
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
    ap.add_argument("--mesh", default="extended", choices=["truncated", "extended"])
    ap.add_argument("--outdir", type=Path, default=rc.FIGDIR)
    a = ap.parse_args(argv)

    rc.use_print_style()
    import matplotlib.pyplot as plt

    df = rc.load_sensitivity(a.csv)
    iso = rc.slice_condition_mesh(df, "iso", a.mesh)
    ani = rc.slice_condition_mesh(df, "aniso", a.mesh)
    iso = iso[iso["montage"] != "reference"]
    ani = ani[ani["montage"] != "reference"]

    I, rows, cols = rc.ordered_matrix(iso, "lead_field")
    A, rows2, cols2 = rc.ordered_matrix(ani, "lead_field")
    assert rows == rows2 and cols == cols2, "iso/aniso grids disagree"
    with np.errstate(divide="ignore", invalid="ignore"):
        D = 20.0 * np.log10(A / I)

    vmax = float(np.ceil(np.nanmax(np.abs(D)) * 10) / 10) or 1.0

    fig, ax = plt.subplots(figsize=(6.7, 5.3))
    im = ax.imshow(D, aspect="auto", cmap=rc.diverging_cmap(), vmin=-vmax, vmax=vmax)

    row_labels = [rc.pretty(r) + (" †" if r in rc.PCA_MUSCLES else "") for r in rows]
    rc.decorate_matrix(ax, rows, cols, row_labels=row_labels)

    cbar = fig.colorbar(im, ax=ax, fraction=0.030, pad=0.02)
    cbar.set_label("Δ lead field, aniso − iso  (dB)", fontsize=7)
    cbar.ax.tick_params(labelsize=6, length=0)
    cbar.outline.set_visible(False)

    rc.matrix_titles(ax, "Fig 4 · Anisotropy modelling error",
                     f"20·log10(aniso / iso) per cell   ·   mesh = {a.mesh}   ·   "
                     "† fibre tensor applied; unmarked rows isotropic in both "
                     "runs, 0 by construction")

    rc.save(fig, "fig4_anisotropy_delta", df, a.outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
