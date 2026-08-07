#!/usr/bin/env python3
r"""
Which single electrode serves each articulator best, and how fragile that is.

WHY THIS EXISTS

Reviewers and device teams both ask the same question the paper does not
answer: where should the electrodes go. §4.4 answers only the negative half,
that the ear is not a substitute for the jaw, and §3.6 shows that placement by
anatomical target beats an arbitrary draw. Neither names a site.

The obvious thing to compute is the argmax over all 22 positions for each
muscle. That is also exactly the operation §4.8 spends four paragraphs
discrediting, because an argmax over densely spaced candidates rewards density.
So the argmax alone must not be reported.

What makes it reportable is the MARGIN to the runner-up, checked against the
measured electrode-meshing floor. Two facts fall out, and the second is the one
worth having:

  1. Every margin is small, 0.03 to 1.02 dB. Several sit at or below the
     floor's 95 % CI upper bound of 0.65 dB, which means the identity of the
     single best electrode is not resolved by this model for those muscles.
     A table of "best sites" read without that column would be over-read.

  2. NO MUSCLE'S RUNNER-UP CROSSES MONTAGES. For all ten, the second-best site
     sits in the same montage as the best. So the site-level argmax is fragile
     and the montage-level assignment is not, which is the assumption the whole
     paper rests on and had not been tested directly.

Writes results/04u_best_site_per_muscle.csv and, with --emit, the Table 5 block.

    simnibs_python src/04u_best_site_per_muscle.py
    simnibs_python src/04u_best_site_per_muscle.py --emit
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config                # noqa: E402
import manuscript_blocks     # noqa: E402

BLOCK = "best_site"
PRETTY = {"post_lobule": "post-lobule", "pre_tragus": "pre-tragus",
          "submental_mid": "submental (mid)", "submental_lat": "submental (lat)",
          "above_ear": "above ear"}


def _floor_ci_hi() -> float:
    """Upper bound of the measured floor's 95 % CI, from the manuscript."""
    return 0.65


def build() -> pd.DataFrame:
    s = pd.read_csv(config.RESULTS / "04_sensitivity.csv")
    s = s[s.condition == "iso"]
    M = s.pivot_table(index="electrode", columns="muscle", values="lead_field")

    jaw = [e for e in config.MONTAGES["jaw"] if e in M.index]
    ear = [e for e in list(config.MONTAGES["ear"])
           + list(config.MONTAGES["ceegrid"]) if e in M.index]
    montage_of = {**{e: "jaw" for e in jaw}, **{e: "ear" for e in ear}}
    # RESTRICT TO THE TWO DEFINED MONTAGES. `earlobe_ipsi` is solved and sits
    # in the sensitivity table, but it belongs to neither MONTAGES["jaw"] nor
    # MONTAGES["ear"] nor the cEEGrid path, so it is not part of any montage
    # this paper compares. Leaving it in would let an unassigned site win an
    # argmax and be reported under a montage label it does not have.
    dropped = [e for e in M.index if e not in montage_of]
    if dropped:
        print(f"  excluded {len(dropped)} site(s) belonging to no montage: "
              f"{', '.join(sorted(dropped))}")
    M = M.loc[[e for e in M.index if e in montage_of]]

    rows = []
    for name, _grp, label, _exp in config.MUSCLES:
        if not label or name not in M.columns:
            continue
        v = M[name].sort_values(ascending=False)
        best, second = v.index[0], v.index[1]
        margin = 20 * np.log10(v.iloc[0] / v.iloc[1])
        m_best, m_second = montage_of[best], montage_of[second]
        other = [e for e in v.index if montage_of[e] != m_best][0]
        rows.append(dict(
            muscle=name,
            best_site=best, best_montage=m_best,
            second_site=second, second_montage=m_second,
            margin_dB=round(float(margin), 4),
            runner_up_crosses_montage=(m_best != m_second),
            resolved_above_floor=bool(margin > _floor_ci_hi()),
            best_other_montage_site=other,
            deficit_of_other_montage_dB=round(
                float(20 * np.log10(v[other] / v.iloc[0])), 4),
        ))
    return pd.DataFrame(rows)


def to_markdown(d: pd.DataFrame) -> str:
    def site(e):
        return PRETTY.get(e, e.replace("_", " "))
    out = ["| Articulator | Best single site | Montage | Runner-up | "
           "Margin (dB) | Runner-up crosses montage |",
           "|---|---|---|---|---|---|"]
    for _i, r in d.iterrows():
        mark = "" if r.resolved_above_floor else " *"
        out.append(
            f"| {r.muscle.replace('_', ' ')} | {site(r.best_site)} | "
            f"{r.best_montage} | {site(r.second_site)} | "
            f"{r.margin_dB:.2f}{mark} | "
            f"{'yes' if r.runner_up_crosses_montage else 'no'} |")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--emit", action="store_true",
                    help="write the Table 5 block into the manuscripts")
    a = ap.parse_args(argv)

    d = build()
    out = config.RESULTS / "04u_best_site_per_muscle.csv"
    d.to_csv(out, index=False)
    print(f"wrote {out}")

    n_cross = int(d.runner_up_crosses_montage.sum())
    n_unres = int((~d.resolved_above_floor).sum())
    print(f"  margins {d.margin_dB.min():.2f} to {d.margin_dB.max():.2f} dB")
    print(f"  {n_unres} of {len(d)} margins at or below the floor CI upper "
          f"bound ({_floor_ci_hi()} dB): identity of the best site unresolved")
    print(f"  {n_cross} of {len(d)} runner-ups cross montages")
    print(f"  best site is a jaw site for "
          f"{int((d.best_montage == 'jaw').sum())} of {len(d)} articulators")

    if n_cross:
        print("\n  NOTE: a runner-up now crosses montages. The claim in §4.4 "
              "that site-level fragility does not propagate to montage-level "
              "assignment no longer holds as written; fix the text.",
              file=sys.stderr)

    if a.emit:
        md = to_markdown(d)
        for p in (config.ROOT / "paper" / "PAPER1_full_manuscript.md",
                  config.ROOT / "paper" / "PAPER1_humanized.md"):
            manuscript_blocks.replace_block(BLOCK, md, path=p)
            print(f"  emitted TABLE:{BLOCK} into {p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
