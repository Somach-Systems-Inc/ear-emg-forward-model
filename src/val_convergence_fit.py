#!/usr/bin/env python3
"""
Fit RDM against characteristic element size and Richardson-extrapolate to h->0.

Three genuine densities are required. The first attempt at this had only two,
because meshmesh's element-size range cannot refine below the label-volume
floor -- so the third density is obtained by going COARSER, which the size
range does control, rather than by refining an 0.25 mm label volume.

Model:  RDM(h) = RDM_0 + C * h^p

RDM_0 is the discretisation-free residual: whatever error survives at h -> 0 is
NOT discretisation, and for this harness that is expected to be the electrode
model. p is the observed convergence rate. For linear tetrahedra on a smooth
problem p near 2 indicates the asymptotic regime; an erratic p means the
densities are not yet asymptotic and the extrapolation should not be trusted.

    python src/val_convergence_fit.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402

# (label, csv, h_mean mm, tets) -- h measured from the mesh, never the request
DENSITIES = [
    ("vcoarse", "vcoarse.csv", 2.957, 118_169),
    ("coarse",  "coarse.csv",  2.257, 265_620),
    ("medium",  "medium.csv",  1.677, 647_323),
]


def load(name):
    p = config.RESULTS / "convergence" / name
    if not p.exists():
        return None
    rows = list(csv.DictReader(p.open(encoding="utf-8")))
    rdm = np.array([float(r["RDM_pct"]) for r in rows])
    mag = np.array([float(r["MAG_pct"]) for r in rows])
    return float(np.nanmedian(rdm)), float(np.nanmedian(mag))


def main() -> int:
    from scipy.optimize import least_squares

    data = []
    for lbl, fn, h, n in DENSITIES:
        got = load(fn)
        if got is None:
            print(f"missing: {fn} (run the {lbl} density first)", file=sys.stderr)
            return 1
        data.append((lbl, h, n, got[0], got[1]))

    print(f"{'density':<9} {'tets':>10} {'h_mean':>8} {'RDM %':>8} {'MAG %':>9}")
    print("-" * 50)
    for lbl, h, n, rdm, mag in data:
        print(f"{lbl:<9} {n:>10,} {h:>8.3f} {rdm:>8.3f} {mag:>+9.3f}")

    h = np.array([d[1] for d in data])
    y = np.array([d[3] for d in data])          # RDM
    m = np.array([d[4] for d in data])          # MAG

    order = np.argsort(h)
    h, y, m = h[order], y[order], m[order]
    print(f"\nrefinement ratios: "
          + ", ".join(f"{h[i+1]/h[i]:.3f}" for i in range(len(h) - 1)))

    monotone = bool(np.all(np.diff(y) > 0))     # RDM rises with h
    print(f"RDM monotone in h: {monotone}")
    if not monotone:
        print("  RDM is NOT monotone in element size. The densities are not in "
              "the\n  asymptotic regime and the extrapolation below is not "
              "trustworthy.")

    def resid(theta):
        f0, c, p = theta
        return f0 + c * h ** p - y

    best, bestcost = None, np.inf
    for p0 in (0.5, 1.0, 1.5, 2.0, 3.0):
        try:
            r = least_squares(resid, [min(y) * 0.5, 1.0, p0],
                              bounds=([-np.inf, -np.inf, 0.1],
                                      [np.inf, np.inf, 6.0]))
            if r.cost < bestcost:
                best, bestcost = r, r.cost
        except Exception:
            continue
    if best is None:
        print("fit failed", file=sys.stderr)
        return 1

    f0, c, p = best.x
    print(f"\nRICHARDSON FIT   RDM(h) = RDM_0 + C h^p")
    print(f"  RDM_0 (h -> 0) : {f0:8.3f} %")
    print(f"  C              : {c:8.4g}")
    print(f"  p (rate)       : {p:8.3f}")
    print(f"  residual cost  : {bestcost:.3e}  (3 points, 3 params: exact fit)")

    print("\nINTERPRETATION")
    if not monotone:
        print("  Not asymptotic -- p is not meaningful. Escalate to the 0.25 mm")
        print("  label volume before quoting a discretisation term.")
    elif 0.7 <= p <= 1.4:
        print(f"  p = {p:.2f} is CONSISTENT WITH the expected rate. Linear tets")
        print("  converge at p ~ 2 for the potential and p ~ 1 for its GRADIENT,")
        print("  and RDM is computed on an E-derived quantity.")
        print("  NOT a confirmation: 3 points and 3 free parameters give an exact")
        print("  fit by construction (residual ~1e-26), so the fit cannot fail and")
        print("  carries no goodness-of-fit evidence. A 4th density would test it.")
    elif 1.4 < p <= 3.0:
        print(f"  p = {p:.2f} is between the gradient rate (~1) and the potential")
        print("  rate (~2). Plausible but worth noting which quantity dominates.")
    else:
        print(f"  p = {p:.2f} is outside the plausible band for linear tets.")
        print("  Report the fit but do not treat RDM_0 as a converged value.")

    print(f"\n  RDM_0 = {f0:.3f}% is the residual that does NOT shrink with mesh")
    print("  refinement. It is the discretisation-free floor of this harness,")
    print("  and given the measured electrode-meshing sensitivity it is most")
    print("  likely the electrode model rather than the solver. The")
    print("  point-electrode ablation tests exactly that.")
    disc = float(np.interp(1.677, h, y)) - f0
    print(f"\n  discretisation component at the production density "
          f"(h=1.677 mm): {disc:.3f} % RDM")

    out = config.RESULTS / "convergence" / "fit.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["density", "tets", "h_mean_mm", "RDM_pct", "MAG_pct"])
        for lbl, hh, n, r_, m_ in data:
            w.writerow([lbl, n, hh, round(r_, 4), round(m_, 4)])
        w.writerow([])
        w.writerow(["RDM_0_pct", "C", "p", "monotone"])
        w.writerow([round(f0, 4), round(c, 6), round(p, 4), monotone])
    print(f"\nWritten: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
