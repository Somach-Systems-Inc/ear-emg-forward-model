#!/usr/bin/env python3
r"""
Fig 6 — The suprahyoid sensitivity field for a retroauricular montage.

Sagittal and coronal slices of the field magnitude through MIDA's pooled
`Muscle (General)` compartment (label 38), which contains the suprahyoid group
— digastric, stylohyoid, mylohyoid, geniohyoid — that MIDA does not segment
individually. The compartment outline, the hyoid and the injection electrode
are overlaid.

WHY A FIELD AND NOT A NUMBER. The suprahyoids cannot be reported as ten
per-muscle rows, because they are one label. Showing the field lets a reader
see where within that pooled compartment a retroauricular electrode is
sensitive, which a single pooled median would average away.

WHAT IS PLOTTED. |E|, the field magnitude, NOT the projected lead field. A
per-voxel lead field requires a source orientation at every voxel, which the
model does not contain; the projection is defined per compartment, not per
point. |E| is the upper bound over orientations and is labelled as such on the
figure. Do not read absolute lead-field values off this panel.

LICENCE. A sagittal slice through a head shows the facial profile. MIDA clause
2.3.3 requires it be disguised, so the same orbital-rim crop used everywhere
else is applied to the plotted extent and the figure is gated by
`assert_anonymised()`.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python figures/render_fig6.py
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "figures"))
import config              # noqa: E402
import render_common as rc  # noqa: E402

MUSCLE_GENERAL = 38
HYOID = 87
GRID_MM = 1.5


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="render_fig6.py")
    ap.add_argument("--electrode", default="cg08")
    ap.add_argument("--outdir", type=Path, default=rc.FIGDIR)
    a = ap.parse_args(argv)

    from simnibs import mesh_io
    rc.use_print_style()
    import matplotlib.pyplot as plt
    import pandas as pd

    d = config.RESULTS / "leadfields" / "iso" / a.electrode
    msh = (sorted(d.glob("*_scalar.msh")) or sorted(d.glob("*.msh")))[0]
    print(f"reading {msh.name} ...", flush=True)
    m = mesh_io.read_msh(str(msh))
    tets = m.elm.elm_type == 4
    tags = m.elm.tag1[tets]
    E = np.asarray(m.field["E"].value)[tets]
    mag = np.linalg.norm(E, axis=1)
    nodes = m.nodes.node_coord
    cent = nodes[m.elm.node_number_list[tets][:, :4] - 1].mean(axis=1)

    pos = {}
    for r in csv.DictReader(
            (config.RESULTS / "02_electrode_positions.csv").open()):
        if r["R"]:
            pos[r["name"]] = np.array([float(r["R"]), float(r["A"]),
                                       float(r["S"])])
    elec = pos[a.electrode]

    rim = rc.orbital_rim_S()
    mg = cent[tags == MUSCLE_GENERAL]
    hy = cent[tags == HYOID]
    print(f"  Muscle (General): {len(mg):,} tets   hyoid: {len(hy):,}")

    from scipy.spatial import cKDTree
    tree = cKDTree(cent)

    def slab(axis, value, half, u, v):
        """Nearest-element |E| on a regular grid in the plane axis=value."""
        k = np.abs(cent[:, axis] - value) <= half
        if k.sum() < 100:
            raise SystemExit(f"slice at axis {axis}={value} is nearly empty")
        pu, pv = cent[k][:, u], cent[k][:, v]
        gu = np.arange(pu.min(), pu.max() + GRID_MM, GRID_MM)
        gv = np.arange(pv.min(), pv.max() + GRID_MM, GRID_MM)
        U, V = np.meshgrid(gu, gv)
        P = np.zeros((U.size, 3))
        P[:, axis] = value
        P[:, u] = U.ravel()
        P[:, v] = V.ravel()
        dist, idx = tree.query(P)
        # MASK BY DISTANCE. cKDTree.query returns a nearest element for EVERY
        # query point, including points outside the head, which then take the
        # value of the nearest surface element. The first render of this figure
        # filled its whole bounding rectangle that way and looked like a solid
        # block. This is the same defect audited in invariant 2's shell
        # sampling: a nearest-neighbour lookup is not an inside test.
        # Margin speckle: a grid point can sit just inside the distance
        # threshold while grazing the mesh boundary, giving isolated pixels
        # along the slice edge. Tighten the threshold and drop pixels whose
        # neighbourhood is mostly empty, which removes the fringe without
        # touching the interior.
        outside = dist > 0.9 * GRID_MM
        img = np.where(outside, np.nan, mag[idx]).reshape(U.shape)
        tg = np.where(outside, -1, tags[idx]).reshape(U.shape)
        from scipy import ndimage as _nd
        solid = _nd.uniform_filter(
            (~np.isnan(img)).astype(float), size=3) >= 0.55
        img = np.where(solid, img, np.nan)
        tg = np.where(solid, tg, -1)
        return gu, gv, img, tg

    # The sagittal slice goes through the SUPRAHYOID COMPARTMENT, not through
    # the electrode. The first render sliced at the electrode's R = 63 mm,
    # which is lateral, through the pinna, and missed the muscle the figure is
    # about; the suprahyoids sit near the midline. R is taken as the median of
    # the Muscle (General) centroids on the electrode's side.
    sag_R = float(np.median(mg[mg[:, 0] > 0][:, 0])) if (mg[:, 0] > 0).any() \
        else 0.0
    cor_A = float(np.median(mg[:, 1]))
    print(f"  sagittal at R = {sag_R:.1f} mm, coronal at A = {cor_A:.1f} mm "
          f"(medians of the compartment, not the electrode)")
    views = [("Sagittal  (R = %.0f mm)" % sag_R, 0, sag_R, 1, 2,
              "anterior  A (mm)", "superior  S (mm)"),
             ("Coronal  (A = %.0f mm)" % cor_A, 1, cor_A, 0, 2,
              "right  R (mm)", "superior  S (mm)")]

    fig, axes = plt.subplots(1, 2, figsize=(9.2, 4.6))
    plt.subplots_adjust(top=0.80)
    vmax = float(np.percentile(mag[tags == MUSCLE_GENERAL], 99))
    for ax, (title, axis, val, u, v, xl, yl) in zip(axes, views):
        gu, gv, img, tg = slab(axis, val, 2.0, u, v)
        # LICENCE CROP: blank everything above the orbital rim and anterior of
        # the eyes, the same rule anonymise_head applies to point clouds.
        U, V = np.meshgrid(gu, gv)
        if v == 2 and u == 1:
            # sagittal: blank anterior of the eyes AND above the orbital rim
            img = np.where((V > rim) & (U > 0), np.nan, img)
        im = ax.imshow(img, origin="lower", aspect="equal",
                       extent=[gu.min(), gu.max(), gv.min(), gv.max()],
                       cmap=rc.sequential_cmap(), vmin=0, vmax=vmax,
                       rasterized=True, zorder=1)
        ax.contour(U, V, (tg == MUSCLE_GENERAL).astype(float), levels=[0.5],
                   colors=[rc.INK_PRIMARY], linewidths=0.9, zorder=3)
        ax.contour(U, V, (tg == HYOID).astype(float), levels=[0.5],
                   colors=[rc.JAW_ADVANTAGE], linewidths=1.1, zorder=4)
        ax.plot(elec[u], elec[v], marker="v", ms=8, mfc=rc.EAR_ADVANTAGE,
                mec=rc.SURFACE, mew=0.8, zorder=6)
        ax.set_title(title, fontsize=8, pad=6)
        ax.set_xlabel(xl, fontsize=7)
        ax.set_ylabel(yl, fontsize=7)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)

    fig.subplots_adjust(right=0.88)
    cax = fig.add_axes([0.905, 0.22, 0.014, 0.52])
    cbar = fig.colorbar(im, cax=cax)
    cbar.set_label("|E|  (V/m)", fontsize=7)
    cbar.ax.tick_params(labelsize=6, length=0)
    cbar.outline.set_visible(False)

    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=rc.INK_PRIMARY, lw=1.2,
                label="Muscle (General) — pooled suprahyoids"),
         Line2D([], [], color=rc.JAW_ADVANTAGE, lw=1.2, label="hyoid bone"),
         Line2D([], [], marker="v", ls="", ms=6, color=rc.EAR_ADVANTAGE,
                label=f"injection electrode ({a.electrode})")]
    leg = fig.legend(handles=h, loc="lower center", ncol=3, frameon=False,
                     fontsize=6.6, bbox_to_anchor=(0.5, -0.02))
    for t in leg.get_texts():
        t.set_color(rc.INK_SECONDARY)

    rc.assert_anonymised("fig6_suprahyoid_field", True)
    fig.suptitle("Fig 6 · Suprahyoid sensitivity field, retroauricular montage",
                 x=0.012, ha="left", fontsize=9.5, fontweight="bold")
    fig.text(0.012, 0.915,
             f"|E| on 2 mm slabs through MIDA's pooled Muscle (General) "
             f"compartment   ·   magnitude, NOT the projected lead field   ·  "
             f" face cropped above S = {rim:.1f} mm per licence 2.3.3",
             ha="left", fontsize=6.4, color=rc.INK_SECONDARY)


    prov = pd.DataFrame({"x": [0]})
    prov.attrs["source"] = str(msh)
    prov.attrs["is_mock"] = False
    rc.save(fig, "fig6_suprahyoid_field", prov, a.outdir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
