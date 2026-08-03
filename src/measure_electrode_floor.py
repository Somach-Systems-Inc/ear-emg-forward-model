#!/usr/bin/env python3
"""
Measure the electrode-meshing floor at the PRODUCTION electrode diameter.

Two nominally-identical sphere meshes (0.13% apart in element count) are solved
with the same electrode. Any difference between them is not physics: it is the
electrode's contact geometry being realised differently by incidental surface
triangulation. That difference is the resolution floor for every site-to-site
comparison, because contact area is realised per electrode and does NOT cancel.

The first measurement of this used a 15 mm electrode while production runs
10 mm, and it had already been used to size two decision thresholds. This
re-measures it at the diameter that actually ships.

Writes results/electrode_meshing_floor.txt, which the cavity analysis requires
before it will compute a verdict.

    python src/measure_electrode_floor.py
"""
from __future__ import annotations
import csv, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402

PAIR = ("e10mm_medium.csv", "e10mm_fine.csv")


def main() -> int:
    got = []
    for f in PAIR:
        p = config.RESULTS / f
        if not p.exists():
            print(f"missing {p} -- run the 10 mm sphere re-run first",
                  file=sys.stderr)
            return 1
        rows = list(csv.DictReader(p.open()))
        got.append((f, np.array([float(r["RDM_pct"]) for r in rows]),
                    np.array([float(r["MAG_pct"]) for r in rows])))

    (fa, rdm_a, mag_a), (fb, rdm_b, mag_b) = got
    d_rdm = abs(float(np.nanmedian(rdm_a)) - float(np.nanmedian(rdm_b)))
    d_mag = abs(float(np.nanmedian(mag_a)) - float(np.nanmedian(mag_b)))
    floor_db = 20.0 * np.log10(1.0 + d_mag / 100.0)

    print(f"electrode diameter: {config.ELECTRODE_DIAMETER_MM} mm (from config)")
    print(f"\n{'mesh':<20}{'RDM median %':>14}{'MAG median %':>14}")
    print("-" * 48)
    for f, r, m in got:
        print(f"{f.replace('.csv',''):<20}{np.nanmedian(r):>14.3f}"
              f"{np.nanmedian(m):>+14.3f}")
    print(f"\n  |dRDM| = {d_rdm:.3f} pp")
    print(f"  |dMAG| = {d_mag:.3f} pp  ->  floor = 20*log10(1+dMAG/100) "
          f"= {floor_db:.4f} dB")
    print(f"\n  previously (15 mm electrode): 5.06 pp -> 0.43 dB")
    print(f"  change: {floor_db - 0.43:+.4f} dB")

    out = config.RESULTS / "electrode_meshing_floor.txt"
    out.write_text(
        f"{floor_db:.6f}\n"
        f"# electrode-meshing floor, dB\n"
        f"# electrode diameter {config.ELECTRODE_DIAMETER_MM} mm (production)\n"
        f"# from |dMAG| = {d_mag:.4f} pp between two nominally-identical meshes\n"
        f"# n = 2 (one difference, not a distribution)\n"
        f"# supersedes the 0.43 dB figure measured with a 15 mm electrode\n")
    print(f"\nWritten: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
