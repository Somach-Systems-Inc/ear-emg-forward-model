#!/usr/bin/env python3
r"""
Stage 4t. Leave-one-out robustness for §4.3's material-share correlation.

WHY THIS EXISTS

§4.3 reports Spearman rho = -0.955, p = 0.001, n = 7 between a muscle's adipose
path fraction and the material share of its jaw-versus-ear gap. **n = 7 is small
enough that one muscle could carry the result**, and the manuscript stated the n
without ever testing that.

This is the same question the jaw-subset envelope answers for Table 4: does the
conclusion depend on a choice nobody defended? There it was which electrode to
drop; here it is which muscle happens to have a layer profile.

The answer is that it does not, which makes the claim stronger rather than
weaker, and that is worth stating in the paper rather than leaving implicit.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/04t_correlation_robustness.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config                      # noqa: E402

SRC = config.RESULTS / "04f_fat_path_vs_share.csv"
OUT = config.RESULTS / "04t_correlation_robustness.csv"

X, Y = "fat_frac_of_path", "material_share_pct"
# The published pair, used as a refusal guard rather than as an input.
EXPECT_RHO, EXPECT_P = -0.955, 0.001


def main() -> int:
    d = pd.read_csv(SRC).dropna(subset=[Y])
    rho, p = stats.spearmanr(d[X], d[Y])
    print(f"full sample: n = {len(d)}, rho = {rho:+.4f}, p = {p:.4f}")

    if abs(rho - EXPECT_RHO) > 5e-4:
        raise RuntimeError(
            f"rho {rho:+.4f} does not reproduce the published {EXPECT_RHO}. "
            f"Refusing to report a robustness check on a statistic that does "
            f"not match the claim it is checking.")

    rows = []
    for i in range(len(d)):
        dd = d.drop(d.index[i])
        r2, p2 = stats.spearmanr(dd[X], dd[Y])
        rows.append(dict(dropped=d.iloc[i].muscle, n=len(dd),
                         rho=round(float(r2), 4), p=round(float(p2), 5),
                         still_p_below_05=bool(p2 < 0.05),
                         still_p_below_01=bool(p2 < 0.01)))

    rhos = [r["rho"] for r in rows]
    ps = [r["p"] for r in rows]
    print(f"\nleave-one-out over {len(rows)} muscles:")
    for r in rows:
        print(f"  drop {r['dropped']:<24} rho {r['rho']:+.4f}  p {r['p']:.4f}")
    print(f"\n  rho range : {min(rhos):+.4f} to {max(rhos):+.4f}")
    print(f"  worst p   : {max(ps):.4f}")
    print(f"  all p<0.05: {all(r['still_p_below_05'] for r in rows)}")
    print(f"  all p<0.01: {all(r['still_p_below_01'] for r in rows)}")

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        fh.write("# Leave-one-out robustness for the material-share correlation.\n")
        fh.write(f"# full sample: n={len(d)}, rho={rho:.4f}, p={p:.5f}\n")
        fh.write(f"# rho range under leave-one-out: {min(rhos):.4f} to {max(rhos):.4f}\n")
        fh.write(f"# worst p under leave-one-out: {max(ps):.5f}\n")
        fh.write("# n=7 is small; this tests whether one muscle carries the result.\n")
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
