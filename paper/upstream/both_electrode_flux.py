#!/usr/bin/env python3
"""Artifact (b): tet-patch cut flux at BOTH electrodes, not just the active one.

WHY THIS IS THE LIKE-FOR-LIKE COMPARISON. SimNIBS's reported calibration is
2|a-b|/(a+b) over the TWO electrode-interface fluxes. Issue #665 compared it
against the cut flux at the ACTIVE electrode only -- one of the two -- which is
why the comparison was category-mismatched. Measuring both gives quantities
directly comparable to a and b.

Prediction under the maintainer's model, after the solution is scaled so
mean(a,b) = requested: the two cut fluxes should straddle 1 mA, and their
relative difference should reproduce the reported percentage.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python paper/upstream/both_electrode_flux.py
    ... --electrodes mental buccal cg08      # subset, for a quick check

Each solve reads a ~900 MB mesh, so the full 22 takes roughly 30-45 min.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config                      # noqa: E402
import preflight                   # noqa: E402
import solve_invariants as SI      # noqa: E402

RADII = (25., 35., 45., 55., 65., 75.)


def load_sigma():
    sig = {}
    for r in csv.DictReader(
            (config.RESULTS / "01_table1_conductivities.csv").open()):
        lab, val = r.get("mida_label", "").strip(), r.get("sigma_S_per_m", "").strip()
        if lab.isdigit() and val:
            sig[int(lab)] = float(val)
    return SI.with_electrode_tags(sig)


def positions():
    out = {}
    for r in csv.DictReader(
            (config.RESULTS / "02_electrode_positions.csv").open()):
        if r.get("verified") == "held" or not r["R"]:
            continue
        out[r["name"]] = np.array([float(r["R"]), float(r["A"]), float(r["S"])])
    return out


def plateau_flux(m, centre, sigma, injected):
    """Cut flux at one electrode, taken on a stationary plateau."""
    vals = []
    for r in RADII:
        cut, _ext, _n = SI.patch_flux(m, centre, float(r), sigma)
        vals.append(cut / injected)
    pl = SI.find_plateau(RADII, vals)
    return (pl["mean"] if pl else float("nan")), vals


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--electrodes", nargs="*", default=None)
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).parent / "both_electrode_flux.csv")
    a = ap.parse_args(argv)

    from simnibs import mesh_io
    sigma, pos = load_sigma(), positions()
    ref = config.REFERENCE
    work = config.RESULTS / "leadfields" / "iso"
    names = a.electrodes or sorted(d.name for d in work.iterdir() if d.is_dir()
                                   and not d.name.startswith("_"))
    rows = []
    print(f"{'electrode':<16}{'reported%':>10}{'active':>10}{'reference':>11}"
          f"{'2|a-b|/(a+b)':>14}{'mean':>8}")
    print("-" * 70)
    for name in names:
        d = work / name
        hits = sorted(d.glob("*_scalar.msh")) or sorted(d.glob("*.msh"))
        if not hits:
            continue
        m = mesh_io.read_msh(str(hits[0]))
        pct = preflight.read_calibration(d)
        act, _ = plateau_flux(m, pos[name], sigma, config.INJECTION_CURRENT_A)
        rfl, _ = plateau_flux(m, pos[ref], sigma, config.INJECTION_CURRENT_A)
        recomputed = (2 * abs(act - abs(rfl)) / (act + abs(rfl))
                      if np.isfinite(act) and np.isfinite(rfl) else float("nan"))
        mean = 0.5 * (act + abs(rfl))
        print(f"{name:<16}{('' if pct is None else f'{pct:.2f}'):>10}"
              f"{act:>10.4f}{rfl:>11.4f}{100*recomputed:>13.2f}%{mean:>8.4f}")
        rows.append(dict(electrode=name,
                         reported_calibration_pct=("" if pct is None else round(pct, 2)),
                         cut_flux_active=round(act, 6),
                         cut_flux_reference=round(rfl, 6),
                         recomputed_pct=round(100 * recomputed, 4),
                         mean_of_two=round(mean, 6)))
        del m
    with a.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {a.out}")
    print("If `recomputed_pct` tracks `reported_calibration_pct`, the tet-patch "
          "and\nSimNIBS are measuring the same thing and #665's premise is "
          "fully closed out.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
