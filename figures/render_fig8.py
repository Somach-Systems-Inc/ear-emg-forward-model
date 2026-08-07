#!/usr/bin/env python3
r"""
Fig 8 — The gap follows distance, drawn on the MIDA head itself.

The paper asserts that the retroauricular deficit is a DISTANCE effect. Until
now that assertion lived in a correlation coefficient and a table of dB values.
A reader had to take it on trust that nothing anatomically interesting was
happening -- that the ear is not blocked by bone, or shunted by fat, but simply
too far away.

This draws it. Three panels, all from the solved MIDA volume:

  A, B  |E| on ONE plane, from the jaw electrode and from the ear electrode.
        The plane is not sagittal. Sagittal cannot work here: the two
        electrodes are 76 mm apart in R and no sagittal slab contains both.
        Instead the plane is defined by three points -- the jaw electrode, the
        ear electrode, and the centroid of orbicularis oris -- so both sources
        AND the target sit in it exactly, at their true separations. Nothing is
        projected, nothing is foreshortened.

  C     |E| against straight-line distance from the injecting electrode, over
        every muscle tetrahedron in the head. The two montages fall on the SAME
        decay curve. That is the whole argument: the ear is not a worse
        electrode, it is a further one. The ten segmented muscles are marked at
        their own distance, so a reader can read off why temporalis survives
        the trip and orbicularis oris does not.

WHAT IS PLOTTED. |E|, field magnitude, from the reciprocity solve. This is the
upper bound over source orientations, not the projected lead field, which needs
a fibre direction at every point that the model does not carry. Same caveat as
the suprahyoid field figure; do not read absolute lead-field values off it.

LICENCE. An oblique cut through a head can show facial profile. MIDA clause
2.3.3 requires disguise, so the orbital-rim crop is applied to the plotted
extent by testing the true (R, A, S) of every grid point, and the figure is
gated by assert_anonymised().

    ~/Applications/SimNIBS-4.6/bin/simnibs_python figures/render_fig8.py
"""
from __future__ import annotations

import argparse
import csv
import gc
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "figures"))
import config               # noqa: E402
import render_common as rc  # noqa: E402

GRID_MM = 1.5
HALF_MM = 2.0               # slab half-thickness for the nearest-element lookup

# The labels drawn as outlines on the plane, when the plane crosses them.
OUTLINE = {
    75: "orbicularis oris",
    71: "mentalis",
    63: "temporalis",
    66: "masseter",
}
SEGMENTED = {lab: name for name, _g, lab, _e in config.MUSCLES if lab}


def _positions():
    pos = {}
    with (config.RESULTS / "02_electrode_positions.csv").open() as fh:
        for r in csv.DictReader(fh):
            if r["R"] and r["R"].replace(".", "").replace("-", "").isdigit():
                pos[r["name"]] = np.array([float(r["R"]), float(r["A"]),
                                           float(r["S"])])
    return pos


def _plane(p_jaw, p_ear, p_target):
    """Orthonormal in-plane basis (e1, e2) and origin for the three points."""
    o = p_target
    e1 = p_jaw - o
    e1 = e1 / np.linalg.norm(e1)
    w = p_ear - o
    e2 = w - (w @ e1) * e1
    e2 = e2 / np.linalg.norm(e2)
    return o, e1, e2


def _harvest(msh_path, elec_xyz, o, e1, e2, gu, gv):
    """One mesh, one pass. Returns the plane image, the tag image, the
    distance-decay curve, and per-muscle (distance, median |E|)."""
    from simnibs import mesh_io
    from scipy.spatial import cKDTree

    print(f"  reading {msh_path.name} ...", flush=True)
    m = mesh_io.read_msh(str(msh_path))
    tets = m.elm.elm_type == 4
    tags = m.elm.tag1[tets]
    mag = np.linalg.norm(np.asarray(m.field["E"].value)[tets], axis=1)
    cent = m.nodes.node_coord[m.elm.node_number_list[tets][:, :4] - 1] \
             .mean(axis=1)
    del m
    gc.collect()

    # --- the plane image
    U, V = np.meshgrid(gu, gv)
    P = o + U.ravel()[:, None] * e1 + V.ravel()[:, None] * e2
    tree = cKDTree(cent)
    dist, idx = tree.query(P)
    outside = dist > 0.9 * GRID_MM
    img = np.where(outside, np.nan, mag[idx]).reshape(U.shape)
    tg = np.where(outside, -1, tags[idx]).reshape(U.shape)
    from scipy import ndimage as _nd
    solid = _nd.uniform_filter((~np.isnan(img)).astype(float), size=3) >= 0.78
    # KEEP ONLY THE LARGEST CONNECTED REGION. The neighbourhood filter cleans
    # the interior but leaves detached islands where the oblique plane clips
    # the scalp tangentially -- a few pixels of shoulder or ear cartilage
    # floating above the head with nothing joining them to it. They are not
    # artefacts of the solve, they are real tissue caught edge-on, but they
    # read as noise and they made the head outline look broken.
    lab_, n_ = _nd.label(solid)
    if n_ > 1:
        big = 1 + int(np.argmax(_nd.sum(solid, lab_, range(1, n_ + 1))))
        solid = lab_ == big
    img = np.where(solid, img, np.nan)
    tg = np.where(solid, tg, -1)
    del tree, dist, idx
    gc.collect()

    # --- decay over every muscle tetrahedron in the head
    inmuscle = np.isin(tags, list(SEGMENTED) + [config.MIDA_MUSCLE_GENERAL,
                                                config.MIDA_TONGUE])
    r = np.linalg.norm(cent[inmuscle] - elec_xyz, axis=1)
    e = mag[inmuscle]
    keep = r > 1.0
    r, e = r[keep], e[keep]
    edges = np.logspace(np.log10(max(r.min(), 2.0)), np.log10(r.max()), 26)
    which = np.digitize(r, edges) - 1
    curve = []
    for b in range(len(edges) - 1):
        s = which == b
        if s.sum() >= 40:
            curve.append((np.sqrt(edges[b] * edges[b + 1]),
                          float(np.median(e[s]))))
    curve = np.array(curve)

    per_muscle = {}
    for lab, name in SEGMENTED.items():
        s = tags == lab
        if s.sum() < 10:
            continue
        d = np.linalg.norm(cent[s] - elec_xyz, axis=1)
        per_muscle[name] = (float(np.median(d)), float(np.median(mag[s])))

    # SCALE THE COLOURBAR ON MUSCLE, NOT ON THE WHOLE MESH. |E| at the
    # injection electrode exceeds 10^5 V/m -- a meshing singularity at the
    # current source, not a physical field. The first render normalised on the
    # global maximum and the entire head came out one flat pale blue, which
    # hides the only thing the panel is for. Muscle tissue is what the paper
    # measures, so muscle sets the range.
    hi = float(np.percentile(mag[inmuscle], 99.0))

    P3 = P.reshape(U.shape + (3,))
    del cent, mag, tags
    gc.collect()
    return img, tg, curve, per_muscle, P3, hi


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="render_fig8.py")
    ap.add_argument("--jaw", default="mental")
    ap.add_argument("--ear", default="mastoid")
    ap.add_argument("--target-label", type=int, default=75)  # orbicularis oris
    ap.add_argument("--stem", default="fig8_distance_mechanism")
    ap.add_argument("--outdir", type=Path, default=rc.FIGDIR)
    a = ap.parse_args(argv)

    rc.use_print_style()
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm
    from matplotlib.lines import Line2D
    import pandas as pd

    pos = _positions()
    p_jaw, p_ear = pos[a.jaw], pos[a.ear]

    # target centroid, read once from whichever mesh we open first
    from simnibs import mesh_io
    d0 = config.RESULTS / "leadfields" / "iso" / a.jaw
    msh0 = (sorted(d0.glob("*_scalar.msh")) or sorted(d0.glob("*.msh")))[0]
    print("locating the target compartment ...", flush=True)
    m = mesh_io.read_msh(str(msh0))
    tets = m.elm.elm_type == 4
    tg0 = m.elm.tag1[tets]
    c0 = m.nodes.node_coord[m.elm.node_number_list[tets][:, :4] - 1].mean(axis=1)
    p_target = c0[tg0 == a.target_label].mean(axis=0)
    del m, tg0, c0
    gc.collect()

    o, e1, e2 = _plane(p_jaw, p_ear, p_target)
    print(f"  plane through {a.jaw}, {a.ear}, and label {a.target_label}")
    print(f"  jaw is {np.linalg.norm(p_jaw - p_target):.1f} mm from the target, "
          f"ear is {np.linalg.norm(p_ear - p_target):.1f} mm")

    # in-plane extent: bound the two electrodes and the target, then pad
    proj = np.array([[(p - o) @ e1, (p - o) @ e2]
                     for p in (p_jaw, p_ear, p_target)])
    # PAD IS TIGHT ON PURPOSE. At \linewidth a 9.4 in figure is scaled to
    # 0.69 and 6.4 pt labels land at 4.4 pt on the page, which is below what
    # print can carry. Shrinking the figure and cropping the empty air around
    # the head buys the scale back.
    pad = 20.0
    gu = np.arange(proj[:, 0].min() - pad, proj[:, 0].max() + pad, GRID_MM)
    gv = np.arange(proj[:, 1].min() - pad, proj[:, 1].max() + pad, GRID_MM)

    panels = {}
    for key, name, xyz in (("jaw", a.jaw, p_jaw), ("ear", a.ear, p_ear)):
        d = config.RESULTS / "leadfields" / "iso" / name
        msh = (sorted(d.glob("*_scalar.msh")) or sorted(d.glob("*.msh")))[0]
        panels[key] = _harvest(msh, xyz, o, e1, e2, gu, gv)

    # ---- licence crop, applied on TRUE coordinates of each grid point
    rim = rc.orbital_rim_S()
    P3 = panels["jaw"][4]
    face = (P3[..., 2] > rim) & (P3[..., 1] > 0)
    for key in panels:
        img, tg, curve, pm, _p, hi = panels[key]
        panels[key] = (np.where(face, np.nan, img), np.where(face, -1, tg),
                       curve, pm, _p, hi)
    print(f"  licence crop blanked {face.sum():,} of {face.size:,} grid points "
          f"above S = {rim:.1f} mm")

    # ---- panel A: WHICH MONTAGE OWNS WHICH TERRITORY
    #
    # Two side-by-side |E| maps were tried first and failed. Both panels came
    # out the same overall shade, because the eye compares absolute darkness
    # badly across a log scale, and because tissue structure varies more within
    # one panel than the montage difference varies between them. The quantity
    # the paper is actually about is the RATIO, so plot the ratio: one panel,
    # one number per point, sign = which electrode is closer to owning it.
    img_j, tg, _c, _pm, _p, hi_j = panels["jaw"]
    img_e = panels["ear"][0]
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = 20.0 * np.log10(img_j / img_e)
    LIM = 30.0
    U, V = np.meshgrid(gu, gv)

    fig = plt.figure(figsize=(7.3, 4.05))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.06, 1.0],
                          wspace=0.20, left=0.035, right=0.975,
                          bottom=0.255, top=0.905)
    axes = [fig.add_subplot(gs[0, i]) for i in range(2)]

    ext = [gu.min(), gu.max(), gv.min(), gv.max()]
    ax = axes[0]
    im = ax.imshow(np.clip(ratio, -LIM, LIM), origin="lower", aspect="equal",
                   extent=ext, cmap=rc.diverging_cmap(ear_is_positive=False),
                   vmin=-LIM, vmax=LIM, rasterized=True, zorder=1)
    ax.contour(U, V, (tg >= 0).astype(float), levels=[0.5],
               colors=[rc.INK_MUTED], linewidths=0.7, zorder=2)
    # THE CROSSOVER. Everything on one side of this line is heard better at the
    # jaw, everything on the other side better at the ear. It is the single
    # most informative curve in the figure.
    #
    # SMOOTHED BEFORE CONTOURING, and the smoothing is cosmetic only -- the
    # colour field underneath is unfiltered. Contouring the raw ratio produced
    # a few dozen closed loops a millimetre across, wherever a conductivity
    # boundary flipped the sign locally. Those are real but they are not the
    # crossover; they buried the one line the panel exists to show. A 3 mm
    # nan-aware Gaussian removes them and moves the main line by well under a
    # voxel.
    from scipy import ndimage as _nd2
    good = np.isfinite(ratio)
    num = _nd2.gaussian_filter(np.where(good, ratio, 0.0), 2.0)
    den = _nd2.gaussian_filter(good.astype(float), 2.0)
    smooth = np.where((den > 0.30) & good, num / np.maximum(den, 1e-9), np.nan)
    ax.contour(U, V, smooth, levels=[0.0], colors=[rc.INK_PRIMARY],
               linewidths=1.6, zorder=4)
    for lab, lname in OUTLINE.items():
        if (tg == lab).sum() > 25:
            ax.contour(U, V, (tg == lab).astype(float), levels=[0.5],
                       colors=[rc.INK_PRIMARY], linewidths=0.8,
                       linestyles="dashed", zorder=3)
    for p, col, lab in ((p_jaw, rc.JAW_ADVANTAGE, a.jaw),
                        (p_ear, rc.EAR_ADVANTAGE, a.ear)):
        u_, v_ = (p - o) @ e1, (p - o) @ e2
        ax.plot(u_, v_, marker="v", ms=9, mfc=col, mec=rc.SURFACE, mew=1.0,
                ls="", zorder=7)
        ax.annotate(rc.pretty(lab), (u_, v_), textcoords="offset points",
                    xytext=(0, 11), ha="center", fontsize=6.6, color=col,
                    zorder=8, fontweight="bold",
                    bbox=dict(fc=rc.SURFACE, ec="none", alpha=0.82, pad=1.2))
    tu, tv = (p_target - o) @ e1, (p_target - o) @ e2
    ax.plot(tu, tv, marker="o", ms=6, mfc=rc.SURFACE, mec=rc.INK_PRIMARY,
            mew=1.4, ls="", zorder=7)
    ax.annotate("orbicularis oris", (tu, tv), textcoords="offset points",
                xytext=(-9, -12), ha="right", fontsize=6.4,
                color=rc.INK_PRIMARY, zorder=8,
                bbox=dict(fc=rc.SURFACE, ec="none", alpha=0.82, pad=1.2))
    for p, col in ((p_jaw, rc.JAW_ADVANTAGE), (p_ear, rc.EAR_ADVANTAGE)):
        ax.annotate("", xy=(tu, tv),
                    xytext=((p - o) @ e1, (p - o) @ e2),
                    arrowprops=dict(arrowstyle="-", color=col, lw=1.0,
                                    ls=(0, (3, 2)), alpha=0.9), zorder=5)
        mid = 0.5 * (p + p_target)
        ax.text((mid - o) @ e1, (mid - o) @ e2,
                f"{np.linalg.norm(p - p_target):.0f} mm",
                fontsize=6.6, color=col, ha="center", va="center", zorder=8,
                bbox=dict(fc=rc.SURFACE, ec="none", alpha=0.8, pad=1.0))
    ax.set_title("A   which electrode owns which tissue",
                 fontsize=8, pad=5, loc="left")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)

    cax = fig.add_axes([0.055, 0.135, 0.35, 0.024])
    cb = fig.colorbar(im, cax=cax, orientation="horizontal", extend="both")
    cb.set_label(f"|E| at {rc.pretty(a.jaw)} minus |E| at {rc.pretty(a.ear)} (dB)\n"
                 f"red = jaw louder, blue = ear louder", fontsize=5.6,
                 linespacing=1.6)
    cb.set_ticks([-LIM, -15, 0, 15, LIM])
    cb.ax.tick_params(labelsize=6, length=0)
    cb.outline.set_visible(False)

    # ---- panel B: the decay law
    ax = axes[1]
    for key, name, col in (("jaw", a.jaw, rc.JAW_ADVANTAGE),
                           ("ear", a.ear, rc.EAR_ADVANTAGE)):
        _i, _t, curve, pm, _p, _hi = panels[key]
        ax.plot(curve[:, 0], curve[:, 1], color=col, lw=1.7, zorder=3,
                label=f"{rc.pretty(name)} ({key})")
        for mus, (dd, ee) in pm.items():
            ax.plot(dd, ee, marker="o", ms=3.4, mfc=col, mec=rc.SURFACE,
                    mew=0.5, ls="", zorder=4)
    pm_jaw = panels["jaw"][3]
    pm_ear = panels["ear"][3]
    # The two muscles that carry the paper's verdict: one the ear reaches, one
    # it does not. Both are annotated on BOTH curves so the reader can see the
    # same muscle move along one decay law when the electrode moves.
    for mus, (dx, dy, ha) in (("orbicularis_oris", (-8, 9, "right")),
                              ("temporalis", (10, -12, "left"))):
        for pm, col in ((pm_jaw, rc.JAW_ADVANTAGE), (pm_ear, rc.EAR_ADVANTAGE)):
            if mus not in pm:
                continue
            dd, ee = pm[mus]
            ax.plot(dd, ee, marker="o", ms=6.0, mfc="none", mec=col, mew=1.3,
                    ls="", zorder=5)
        if mus in pm_jaw and mus in pm_ear:
            (d1, e1_), (d2, e2_) = pm_jaw[mus], pm_ear[mus]
            ax.annotate("", xy=(d2, e2_), xytext=(d1, e1_),
                        arrowprops=dict(arrowstyle="->", color=rc.INK_MUTED,
                                        lw=0.8, ls=(0, (2, 2))), zorder=4)
            ax.annotate(rc.pretty(mus), (np.sqrt(d1 * d2), np.sqrt(e1_ * e2_)),
                        textcoords="offset points", xytext=(dx, dy),
                        ha=ha, fontsize=6.4, color=rc.INK_SECONDARY, zorder=6,
                        bbox=dict(fc=rc.SURFACE, ec="none", alpha=0.85,
                                  pad=1.2))
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("straight-line distance from the injecting electrode (mm)",
                  fontsize=7)
    ax.set_ylabel("median |E|  (V/m)", fontsize=7)
    ax.set_title("B   one decay law, two starting distances", fontsize=8,
                 pad=5, loc="left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(color=rc.INK_MUTED, alpha=0.15, lw=0.5, which="both")
    ax.set_axisbelow(True)
    leg = ax.legend(frameon=False, fontsize=6.6, loc="upper right")
    for t in leg.get_texts():
        t.set_color(rc.INK_SECONDARY)

    h = [Line2D([], [], color=rc.INK_PRIMARY, lw=1.5,
                label="A: crossover, where the two montages are equally loud"),
         Line2D([], [], color=rc.INK_PRIMARY, lw=0.8, ls="--",
                label="A: muscle compartment crossed by the plane"),
         Line2D([], [], color=rc.INK_MUTED, lw=1.4,
                label="B: median in distance bins over all muscle tissue"),
         Line2D([], [], marker="o", ls="", ms=5, mfc="none",
                mec=rc.INK_MUTED, mew=1.2,
                label="B: one whole compartment, at its own median distance")]
    leg2 = fig.legend(handles=h, loc="lower right", ncol=1, frameon=False,
                      fontsize=6.4, bbox_to_anchor=(0.995, 0.004), labelspacing=0.62, handlelength=1.9)
    for t in leg2.get_texts():
        t.set_color(rc.INK_SECONDARY)

    rc.assert_anonymised(a.stem, True)
    if not rc.PAPER_MODE:
        fig.suptitle("Fig 8 · The ear is not a worse electrode, it is a "
                     "further one", x=0.012, ha="left", fontsize=8.5,
                     fontweight="bold")
        fig.text(0.012, 0.925,
                 "A and B share one oblique plane containing both electrodes "
                 "and the target, so the two distances are drawn true   ·   "
                 f"|E|, not the projected lead field   ·   face cropped above "
                 f"S = {rim:.1f} mm per licence 2.3.3",
                 ha="left", fontsize=6.3, color=rc.INK_SECONDARY)

    prov = pd.DataFrame({"x": [0]})
    prov.attrs["source"] = str(config.RESULTS / "leadfields" / "iso")
    prov.attrs["is_mock"] = False
    rc.save(fig, a.stem, prov, a.outdir)

    rows = []
    for key in ("jaw", "ear"):
        for mus, (dd, ee) in panels[key][3].items():
            rows.append({"montage": key, "muscle": mus,
                         "distance_mm": round(dd, 3), "median_E_Vpm": ee})
    out = config.RESULTS / "08_distance_mechanism.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"  wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
