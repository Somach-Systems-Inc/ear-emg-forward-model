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


def _tensor_rows(rows):
    """Which rows actually carry a fibre tensor, resolved from the builder.

    Read from 03e_build_tensor rather than from FIBRE_MODEL, because being
    PCA-defensible is necessary but not sufficient: the compartment must also
    be individually segmented in MIDA, and must pass the bilateral
    mirror-symmetry check.
    """
    import importlib.util
    from pathlib import Path as _P
    root = _P(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "bt", root / "src" / "03e_build_tensor.py")
    bt = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bt)
    seg = set(bt.TENSOR_MUSCLES)
    # mentalis is in TENSOR_MUSCLES but refused at build time; the refusal set
    # is only populated after a build, so exclude it explicitly here.
    refused = {"mentalis"}
    return [r in (seg - refused) for r in rows]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, default=rc.DEFAULT_CSV)
    ap.add_argument("--mesh", default="truncated",
                    choices=["truncated", "extended"])
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

    # NOT APPLIED, never 0 and never blank. A row whose muscle carries no
    # fibre tensor has not been measured to be unchanged -- it was never
    # varied. Rendering it as 0 dB in the same neutral the diverging scale
    # uses for "no change" asserts a null result that does not exist, and a
    # reader seeing eight neutral rows would conclude "anisotropy does not
    # matter" when the correct statement is "anisotropy was not applied here".
    #
    # Only 2 of 10 segmented muscles carry a tensor: SCM and medial pterygoid.
    # Of the nine PCA-defensible muscles six are pooled in MIDA's Muscle
    # (General) / Tongue labels, and mentalis is refused by the bilateral
    # mirror-symmetry check. See src/03e_build_tensor.py.
    applied = _tensor_rows(rows)
    D = np.where(np.array(applied)[:, None], D, np.nan)

    vmax = float(np.ceil(np.nanmax(np.abs(D)) * 10) / 10) or 1.0

    fig, ax = plt.subplots(figsize=(6.9, 5.3))
    cmap = rc.diverging_cmap()
    cmap.set_bad(rc.SURFACE)          # NOT APPLIED rows render as bare surface
    im = ax.imshow(D, aspect="auto", cmap=cmap, vmin=-vmax, vmax=vmax)

    row_labels = [rc.pretty(r) + (" †" if applied[i] else "")
                  for i, r in enumerate(rows)]
    rc.decorate_matrix(ax, rows, cols, row_labels=row_labels)

    # write NOT APPLIED across every row that carries no tensor, so the
    # absence is stated rather than left as empty space
    for i, ok in enumerate(applied):
        if not ok:
            ax.text(len(cols) / 2.0 - 0.5, i, "NOT APPLIED — no fibre tensor",
                    ha="center", va="center", fontsize=6.0,
                    color=rc.INK_MUTED, zorder=6)

    cbar = fig.colorbar(im, ax=ax, fraction=0.030, pad=0.02)
    cbar.set_label("Δ lead field, aniso − iso  (dB)", fontsize=7)
    cbar.ax.tick_params(labelsize=6, length=0)
    cbar.outline.set_visible(False)

    rc.matrix_titles(ax, "Fig 4 · Anisotropy modelling error",
                     f"20·log10(aniso / iso) per cell   ·   mesh = {a.mesh}   ·   "
                     f"† fibre tensor applied ({sum(applied)} of {len(rows)} "
                     f"muscles)   ·   unmarked rows are NOT APPLIED, not "
                     f"measured-as-zero")

    rc.save(fig, "fig4_anisotropy_delta", df, a.outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
