#!/usr/bin/env python3
"""
Stage 2e -- per-electrode PERPENDICULAR clearance above the derived cut plane.

Replaces the S-difference that `03_leadfields.py` wrote into
`clearance_to_cut_mm` as `xyz[2] - (-116.2)`.

WHY THE OLD COLUMN WAS WRONG, TWICE OVER

  1. -116.2 was a bare literal standing in for a plane that is tilted 2.664 deg,
     and a tilted plane has no single S.
  2. Even given a correct S, a difference in S is not a distance to a tilted
     plane. n_x = -0.0334 and n_y = -0.0324 act on each electrode's lateral
     offset, so the two quantities differ per site, and the sign of the
     difference varies by site. This is the same error class as the constant
     itself: a geometric quantity replaced by something cheaper to compute that
     does not mean what its name says.

The identical substitution appeared once more, in the check that CONFIRMED the
fix: the two meshes' planes were reported 69.851 mm apart, which is their
centroids' S-difference, when the centroids sit at different lateral positions.
The perpendicular separation is 70.0010 mm against a stated 70 mm extrusion.

This is a pure re-reduction. Clearance is a property of an electrode coordinate
and the mesh, not of any solve, so nothing here requires re-running the FEM.

    python src/02e_cut_clearance.py
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser(prog="02e_cut_clearance.py")
    ap.add_argument("--positions", type=Path,
                    default=config.RESULTS / "02_electrode_positions.csv")
    ap.add_argument("--out", type=Path,
                    default=config.RESULTS / "02_cut_clearance.csv")
    ap.add_argument("--near-cut-mm", type=float, default=10.0,
                    help="reporting threshold only; this script gates nothing")
    ap.add_argument("--refresh-leadfields", action="store_true",
                    help="rewrite clearance_to_cut_mm in 03_leadfields.csv from "
                         "the perpendicular distance. A RE-REDUCTION: clearance "
                         "is a property of an electrode coordinate and the mesh, "
                         "so no solve is re-run and no lead field changes.")
    a = ap.parse_args(argv)

    n, p, meta = config.cut_plane()
    print(f"plane      : n = [{n[0]:+.6f} {n[1]:+.6f} {n[2]:+.6f}]")
    print(f"             p = [{p[0]:+.4f} {p[1]:+.4f} {p[2]:+.4f}]")
    print(f"             tilt {float(meta['tilt_deg']):.4f} deg, "
          f"residual RMS {float(meta['residual_rms_mm']):.4f} mm, "
          f"{int(meta['n_triangles']):,} triangles")
    print(f"mesh       : {meta['mesh']}  {meta['mesh_sha256'][:16]}...")
    print()

    rows = []
    with open(a.positions) as fh:
        for r in csv.DictReader(fh):
            if not r.get("S"):
                continue
            xyz = (float(r["R"]), float(r["A"]), float(r["S"]))
            perp = config.clearance_to_cut(xyz, n, p)
            # what the old column said, kept so the change is auditable
            old = xyz[2] - (-116.2)
            rows.append(dict(
                electrode=r["name"], montage=r["montage"], side=r["side"],
                R=f"{xyz[0]:.2f}", A=f"{xyz[1]:.2f}", S=f"{xyz[2]:.2f}",
                clearance_perp_mm=f"{perp:.3f}",
                legacy_s_difference_mm=f"{old:.3f}",
                delta_mm=f"{perp - old:+.3f}",
            ))

    rows.sort(key=lambda r: float(r["clearance_perp_mm"]))

    print(f"{'electrode':<16} {'montage':<9} {'perp mm':>9} {'old S-diff':>11} "
          f"{'delta':>8}")
    print("-" * 60)
    for r in rows:
        flag = "  <-- within %.0f mm" % a.near_cut_mm \
            if float(r["clearance_perp_mm"]) < a.near_cut_mm else ""
        print(f"{r['electrode']:<16} {r['montage']:<9} "
              f"{float(r['clearance_perp_mm']):>9.3f} "
              f"{float(r['legacy_s_difference_mm']):>11.3f} "
              f"{float(r['delta_mm']):>+8.3f}{flag}")

    near_new = [r["electrode"] for r in rows
                if float(r["clearance_perp_mm"]) < a.near_cut_mm]
    near_old = [r["electrode"] for r in rows
                if float(r["legacy_s_difference_mm"]) < a.near_cut_mm]
    print(f"\nwithin {a.near_cut_mm:.0f} mm, perpendicular : {sorted(near_new)}")
    print(f"within {a.near_cut_mm:.0f} mm, old S-difference: {sorted(near_old)}")
    if set(near_new) != set(near_old):
        print("\n*** THE EXCLUSION SET CHANGES UNDER THE CORRECTED METRIC. ***")
        print("    That is a finding change. Halt and report; do not proceed to")
        print("    Table 4 on either set until Carl rules.")
    else:
        print("\nSame membership under both metrics. The correction moves the "
              "numbers, not the set.")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", newline="") as fh:
        fh.write(f"# cut plane, derived by 01d_derive_cut_plane.py\n")
        fh.write(f"# normal,{n[0]:.10g},{n[1]:.10g},{n[2]:.10g}\n")
        fh.write(f"# point,{p[0]:.10g},{p[1]:.10g},{p[2]:.10g}\n")
        fh.write(f"# tilt_deg,{float(meta['tilt_deg']):.6g}\n")
        fh.write(f"# residual_rms_mm,{float(meta['residual_rms_mm']):.6g}\n")
        fh.write(f"# n_triangles,{meta['n_triangles']}\n")
        fh.write(f"# mesh,{meta['mesh']}\n")
        fh.write(f"# mesh_sha256,{meta['mesh_sha256']}\n")
        fh.write(f"# clearance_perp_mm = -n.(x-p), positive is above the face\n")
        fh.write(f"# legacy_s_difference_mm = S - (-116.2), the retired quantity\n")
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    print(f"\nwrote {a.out}  ({len(rows)} electrodes)")

    if a.refresh_leadfields:
        lf_path = config.RESULTS / "03_leadfields.csv"
        perp = {r["electrode"]: r["clearance_perp_mm"] for r in rows}
        with open(lf_path) as fh:
            rd = list(csv.DictReader(fh))
            cols = rd[0].keys()
        n = 0
        for r in rd:
            if r["electrode"] in perp:
                r["clearance_to_cut_mm"] = f"{float(perp[r['electrode']]):.2f}"
                n += 1
        with open(lf_path, "w", newline="") as fh:
            wr = csv.DictWriter(fh, fieldnames=list(cols))
            wr.writeheader()
            wr.writerows(rd)
        print(f"refreshed clearance_to_cut_mm on {n} rows of {lf_path.name} "
              f"(re-reduction; no solve re-run, no lead field touched)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
