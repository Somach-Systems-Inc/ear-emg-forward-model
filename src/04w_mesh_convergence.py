#!/usr/bin/env python3
r"""
Bound the discretisation term by re-solving the cluster on a second mesh.

Error budget row 1 is the last term still "partly quantified, directional,
unquantified". Every other row has either a number or an explicit reason it
cannot have one. This measures it the only way it can be measured: run the same
pipeline on a mesh built at a different resolution and see how far the gaps
move.

WHAT IS COMPARED. The four-site cluster gap per muscle,

    gap = 20 log10( max over the jaw cluster / max over the ear cluster )

on the production mesh and on the refined mesh, using the SAME eight
electrodes. Not the matched-count interval: that needs all 14 ear sites and
would cost 14 more solves for a quantity whose site-sampling behaviour is not
what row 1 is about.

READ THE LEVER ARM BEFORE READING THE RESULT.

The refined mesh has 14,633,111 tets against production's 12,294,185. That is
19 % more elements, which is only 5.5 % smaller LINEARLY, because element size
goes as N^(-1/3). METHODS_LOG 2026-08-02 records why refinement saturates:
meshmesh's element size is floored by the label volume, and MIDA is 500 um, so
--voxsize_meshing 0.4 buys much less than the ratio suggests.

So a null here is WEAK EVIDENCE, and this script says so in its own output
rather than letting a small number be read as "discretisation does not matter".
Bounding row 1 properly wants a COARSER mesh as well, where the size range does
work and a 2x linear lever arm is available. That run is not this one.

    simnibs_python src/04w_mesh_convergence.py \
        --fine results/conv/03_leadfields_fine.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

JAW = ["buccal", "mental", "midjaw", "submaxillary"]
EAR = ["above_ear", "mastoid", "post_lobule", "pre_tragus"]
FLOOR = 0.272          # measured per-site electrode-meshing floor, dB
FLOOR_CI_HI = 0.65     # its 95 % CI upper bound
PROD_TETS = 12_294_185


def gaps(df: pd.DataFrame, muscles) -> dict:
    d = df.set_index("electrode")
    out = {}
    for m in muscles:
        j = d.loc[[e for e in JAW if e in d.index], m].max()
        e_ = d.loc[[e for e in EAR if e in d.index], m].max()
        out[m] = 20 * np.log10(j / e_)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="04w_mesh_convergence.py")
    ap.add_argument("--fine", type=Path, required=True,
                    help="03_leadfields.csv produced with --mesh on the second mesh")
    ap.add_argument("--fine-tets", type=int, default=14_633_111)
    ap.add_argument("--out", type=Path,
                    default=config.RESULTS / "04w_mesh_convergence.csv")
    a = ap.parse_args(argv)

    prod = pd.read_csv(config.RESULTS / "03_leadfields.csv")
    fine = pd.read_csv(a.fine)
    muscles = [m for m, _g, lab, _e in config.MUSCLES
               if lab and m in prod.columns and m in fine.columns]

    have = set(fine.electrode)
    missing = [e for e in JAW + EAR if e not in have]
    if missing:
        print(f"ERROR: the fine solve is missing {missing}. The cluster gap "
              f"cannot be formed from a partial set, and substituting a "
              f"different site would compare two different montages.",
              file=sys.stderr)
        return 1

    gp, gf = gaps(prod, muscles), gaps(fine, muscles)
    lin = (PROD_TETS / a.fine_tets) ** (1 / 3)

    rows = []
    for m in muscles:
        d = gf[m] - gp[m]
        rows.append(dict(muscle=m,
                         gap_production_dB=round(gp[m], 4),
                         gap_refined_dB=round(gf[m], 4),
                         delta_dB=round(d, 4),
                         abs_delta_dB=round(abs(d), 4),
                         under_floor=bool(abs(d) <= FLOOR),
                         under_floor_ci_hi=bool(abs(d) <= FLOOR_CI_HI),
                         sign_preserved=bool(np.sign(gf[m]) == np.sign(gp[m]))))
    out = pd.DataFrame(rows).sort_values("abs_delta_dB", ascending=False)
    out.to_csv(a.out, index=False)

    mx = out.abs_delta_dB.max()
    n_flip = int((~out.sign_preserved).sum())
    print(f"tets      : production {PROD_TETS:,}  refined {a.fine_tets:,}  "
          f"({a.fine_tets / PROD_TETS:.3f} x elements)")
    print(f"lever arm : element size {lin:.3f} x, i.e. "
          f"{100 * (1 - lin):.1f} % smaller LINEARLY")
    print()
    print(out[["muscle", "gap_production_dB", "gap_refined_dB",
               "delta_dB", "under_floor"]].to_string(index=False))
    print()
    print(f"largest movement : {mx:.4f} dB")
    print(f"vs floor         : {FLOOR} dB measured, {FLOOR_CI_HI} dB CI upper bound")
    print(f"sign flips       : {n_flip} of {len(out)}")
    print(f"wrote {a.out}")

    print("\nHOW TO READ THIS")
    if n_flip:
        print("  A SIGN FLIPPED. Discretisation changes a montage assignment, "
              "which is a result, not a bound. Row 1 is not a small term.")
    elif mx <= FLOOR:
        print(f"  Every gap moved less than the {FLOOR} dB floor. That bounds "
              f"row 1 BELOW THE FLOOR at this lever arm, and no further.")
        print(f"  THE LEVER ARM IS SHORT: {100 * (1 - lin):.1f} % in element "
              f"size. A null over so small a change is weak evidence, because")
        print("  it cannot distinguish 'discretisation does not matter' from "
              "'the mesh barely changed'. Quote it with the lever arm attached,")
        print("  and get a coarser mesh before claiming row 1 is bounded.")
    else:
        print(f"  Largest movement {mx:.4f} dB exceeds the {FLOOR} dB floor. "
              f"Row 1 is resolvable and now has a measured magnitude at this "
              f"lever arm.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
