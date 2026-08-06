#!/usr/bin/env python3
r"""
Stage 4n. Does any Table 4 verdict depend on WHICH inferior jaw site is dropped?

WHY THIS EXISTS

The near-cut exclusion set was governed by `CUT_FACE_S = -116.2`, a bare literal
standing in for a plane tilted 2.664 deg. With the plane derived
(`01d_derive_cut_plane.py`) and clearance corrected to a perpendicular distance
(`02e_cut_clearance.py`), `submental_mid` moves from 9.660 mm to 10.759 mm and
crosses the 10 mm threshold. The near-cut set drops from three sites to two.

"Report Table 4 with and without the three most inferior jaw sites" is then not
computable as stated: seven jaw sites were solved, excluding two leaves five, and
`04h` raises unless the jaw count equals the pre-registered four-site ear cluster,
because best-of-5 against best-of-4 rewards electrode density.

So this enumerates all C(5,4) = 5 four-site subsets of the five admissible jaw
sites, each against the unchanged cluster, statistic A unchanged. Counts stay
matched and no new pre-registration is invented.

The halt condition was written into METHODS_LOG before this was run: if any
verdict differs across the subsets, halt and report, and do not select the subset
agreeing with the manuscript.

STATISTIC A is reproduced from `04h_matched_counts.py` without modification,
including its refusal to renormalise -- `04d_orientation_sign.py` already divides
each site by its own delivered current at line 123.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/04n_site_set_sensitivity.py
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config                      # noqa: E402

PERDIR = config.RESULTS / "04d_orientation_sign.npz"
CLEAR = config.RESULTS / "02_cut_clearance.csv"
OUT = config.RESULTS / "04n_site_set_sensitivity.csv"

CLUSTER = ["above_ear", "mastoid", "post_lobule", "pre_tragus"]
NEAR_CUT_MM = 10.0        # unchanged, and still undefended -- see METHODS_LOG
N_DRAWS = 10_000
SEED = 0
PUBLISHED_JAW = ("buccal", "mental", "midjaw", "submaxillary")


def statistic_A(d, jaw, ear, muscles):
    """Verbatim the computation in 04h_matched_counts.py."""
    rows = []
    for m in muscles:
        def best(sites):
            return np.max([d[f"lf_{e}|{m}"] for e in sites], axis=0)

        J = best(jaw)
        cluster = float(np.median(20 * np.log10(J / best(CLUSTER))))

        rng = np.random.default_rng(SEED)
        per_dir = np.stack([d[f"lf_{e}|{m}"] for e in ear])
        draws = np.array([
            np.median(20 * np.log10(
                J / per_dir[rng.choice(len(ear), len(CLUSTER),
                                       replace=False)].max(axis=0)))
            for _ in range(N_DRAWS)])
        lo, hi = np.percentile(draws, [2.5, 97.5])

        gaps = 20 * np.log10(J / best(CLUSTER))
        agree = float(100.0 * np.mean(np.sign(gaps) == np.sign(cluster)))
        crosses = bool(lo < 0 < hi)
        if crosses:
            verdict = "no resolvable preference"
        else:
            side = "jaw" if cluster > 0 else "ear"
            verdict = (f"{side}, robust on both axes" if agree >= 90.0
                       else f"{side}, site-robust but orientation-dependent")
        rows.append(dict(muscle=m, cluster_gap_dB=round(cluster, 4),
                         rand4_lo=round(lo, 4), rand4_hi=round(hi, 4),
                         crosses_zero=crosses,
                         orientation_agree_pct=round(agree, 1),
                         verdict=verdict))
    return rows


def main() -> int:
    lf = pd.read_csv(config.RESULTS / "03_leadfields.csv").set_index("electrode")
    d = np.load(PERDIR)

    clear = pd.read_csv(CLEAR, comment="#").set_index("electrode")
    present = {e for e in lf.index if f"lf_{e}|temporalis" in d}
    jaw_all = sorted(e for e in present if lf.montage[e] == "jaw")
    ear = sorted(e for e in present if lf.montage[e] in ("ear", "ceegrid"))

    excluded = sorted(e for e in jaw_all
                      if float(clear.clearance_perp_mm[e]) < NEAR_CUT_MM)
    admissible = sorted(e for e in jaw_all if e not in excluded)

    print("SITE-SET SENSITIVITY — statistic A, matched counts throughout")
    print("=" * 78)
    print(f"  jaw sites solved     : {len(jaw_all)}  {jaw_all}")
    print(f"  excluded, perp < {NEAR_CUT_MM:.0f} mm : {excluded}")
    print(f"  admissible           : {len(admissible)}  {admissible}")
    print(f"  ear cluster          : {CLUSTER}")
    print(f"  subsets of size {len(CLUSTER)}    : C({len(admissible)},{len(CLUSTER)}) = "
          f"{len(list(itertools.combinations(admissible, len(CLUSTER))))}")
    print()

    muscles = [n for n, _g, lab, _e in config.MUSCLES if lab is not None]
    all_rows, verdicts = [], {}
    for subset in itertools.combinations(admissible, len(CLUSTER)):
        tag = "+".join(subset)
        for r in statistic_A(d, list(subset), ear, muscles):
            r["jaw_set"] = tag
            r["is_published_set"] = (tuple(sorted(subset)) == tuple(sorted(PUBLISHED_JAW)))
            r["dropped"] = (set(admissible) - set(subset)).pop()
            all_rows.append(r)
            verdicts.setdefault(r["muscle"], {})[tag] = r["verdict"]

    t = pd.DataFrame(all_rows)
    t.to_csv(OUT, index=False)

    # ---- the halt check, applied without selecting
    print(f"{'muscle':<22} {'distinct verdicts':>17}  {'gap range dB':>16}  status")
    print("-" * 78)
    unstable = []
    for m in muscles:
        vs = set(verdicts[m].values())
        sub = t[t.muscle == m]
        rng = f"{sub.cluster_gap_dB.min():+.3f}..{sub.cluster_gap_dB.max():+.3f}"
        status = "stable" if len(vs) == 1 else "*** DIFFERS ***"
        if len(vs) > 1:
            unstable.append(m)
        print(f"{m:<22} {len(vs):>17}  {rng:>16}  {status}")

    print()
    if unstable:
        print("HALT CONDITION MET. Verdict differs across jaw subsets for: "
              f"{unstable}")
        print("Per the pre-commitment in METHODS_LOG, this is a finding change.")
        print("Reporting all subsets. NOT selecting the one matching the text.\n")
        for m in unstable:
            print(f"  {m}:")
            for tag, v in verdicts[m].items():
                pub = "  <-- currently published set" \
                    if tuple(sorted(tag.split("+"))) == tuple(sorted(PUBLISHED_JAW)) else ""
                g = float(t[(t.muscle == m) & (t.jaw_set == tag)].cluster_gap_dB.iloc[0])
                lo = float(t[(t.muscle == m) & (t.jaw_set == tag)].rand4_lo.iloc[0])
                hi = float(t[(t.muscle == m) & (t.jaw_set == tag)].rand4_hi.iloc[0])
                print(f"    drop {(set(admissible)-set(tag.split('+'))).pop():<14} "
                      f"{g:+8.3f} dB  [{lo:+7.3f}, {hi:+7.3f}]  {v}{pub}")
            print()
    else:
        print("Every verdict is identical across all five jaw subsets.")
        print("The exclusion threshold governs nothing: the finding does not "
              "depend on which inferior jaw site is dropped.")

    print(f"wrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
