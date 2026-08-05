#!/usr/bin/env python3
r"""
Stage 4h. MATCHED ELECTRODE COUNTS — statistic A.

WHY THIS EXISTS AS A SCRIPT
---------------------------
`04h_matched_counts.csv` and `04j_two_axis_verdict.csv` were produced ad hoc in
an interactive session and had no generating script. Two things followed from
that, both bad:

  1. They could not be regenerated from a clean checkout, which is the standard
     §2.3 applies to electrode coordinates and §2.5 now applies to fibre
     directions. A published table is a geometric-quantity-shaped object too.
  2. Nothing verified that they agreed with the pipeline. They did, as it turns
     out -- an attempt to "correct" them by renormalising here produced a
     DOUBLE renormalisation and moved published numbers by up to 1.04 dB before
     it was caught. See the note in `main()`.

This script is the reproducible replacement, and it reproduces the ad hoc
tables exactly.

WHAT IT COMPUTES
----------------
STATISTIC A, per Methods §2.6: the gap is formed PER SOURCE ORIENTATION and the
median is taken over gaps. A physical source has one orientation, seen by both
electrodes; taking medians per site first and differencing them (statistic B)
compares two orientations that need not coincide, and was measured to mislead by
up to 17x with a sign flip.

    cluster4_dB   gap at the four pre-registered retroauricular sites
    rand4_lo/hi   95% interval over 10,000 random four-site draws from the 14
                  ear candidates -- the SITE-robustness axis
    crosses_zero  whether that interval contains 0

Sign convention: POSITIVE = the jaw montage sees the muscle better.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/04h_matched_counts.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config                      # noqa: E402

PERDIR = config.RESULTS / "04d_orientation_sign.npz"
OUT_H = config.RESULTS / "04h_matched_counts.csv"
OUT_J = config.RESULTS / "04j_two_axis_verdict.csv"

# Pre-registered four-site retroauricular cluster, chosen by anatomical target
# before any gap was computed (§3.6). Matching the jaw montage's four sites is
# the whole point: best-of-14 against best-of-4 rewards electrode density.
CLUSTER = ["above_ear", "mastoid", "post_lobule", "pre_tragus"]

# Jaw sites within one mesh element of the inferior cut are excluded; the cut is
# an artificial insulating boundary and inflates the field beside it (§2.1).
NEAR_CUT = {"hyoid", "submental_lat", "submental_mid"}

N_DRAWS = 10_000
SEED = 0
FLOOR_DB = 0.27          # electrode-realisation floor, measured (§2.7)


def main() -> int:
    lf = pd.read_csv(config.RESULTS / "03_leadfields.csv").set_index("electrode")
    d = np.load(PERDIR)

    # DO NOT RENORMALISE HERE. `04d_orientation_sign.py` already divides each
    # site by its own measured delivered current at the point it builds these
    # arrays (line 123), and stores the RESULT under the `lf_<e>|<m>` keys. The
    # renormalisation specified in Methods 2.4 is therefore already applied to
    # everything this script reads. Dividing again double-applies it and shifts
    # published numbers by up to 1.04 dB.
    #
    # This was got wrong once, in the direction that looks careful: the absence
    # of a division was verified HERE without checking whether it had been
    # applied UPSTREAM. Confirming that a step is missing at one stage is not
    # the same as confirming it never ran.
    deliv = None

    present = {e for e in lf.index if f"lf_{e}|temporalis" in d}
    jaw = sorted(e for e in present
                 if lf.montage[e] == "jaw" and e not in NEAR_CUT)
    ear = sorted(e for e in present
                 if lf.montage[e] in ("ear", "ceegrid"))
    missing = [e for e in CLUSTER if e not in ear]
    if missing:
        raise RuntimeError(f"pre-registered cluster site(s) absent: {missing}")
    if len(jaw) != len(CLUSTER):
        raise RuntimeError(
            f"matched comparison requires equal counts: {len(jaw)} jaw sites "
            f"vs a {len(CLUSTER)}-site ear cluster. Refusing to report a gap "
            f"that rewards electrode density.")

    print("MATCHED ELECTRODE COUNTS — statistic A")
    print("=" * 68)
    print(f"  jaw sites   : {len(jaw)}  {jaw}")
    print(f"  ear cluster : {len(CLUSTER)}  {CLUSTER}")
    print(f"  ear pool    : {len(ear)} candidates for the random draw")
    print("  delivered-current renormalisation: ALREADY APPLIED upstream in "
          "04d (line 123)\n")

    muscles = [n for n, _g, lab, _e in config.MUSCLES if lab is not None]
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

        # ORIENTATION axis: fraction of sampled source orientations agreeing
        # with the cluster gap's sign. Independent of the site axis above.
        gaps = 20 * np.log10(J / best(CLUSTER))
        agree = float(100.0 * np.mean(np.sign(gaps) == np.sign(cluster)))

        crosses = bool(lo < 0 < hi)
        if crosses:
            verdict = "no resolvable preference"
        else:
            side = "jaw" if cluster > 0 else "ear"
            verdict = (f"{side}, robust on both axes" if agree >= 90.0
                       else f"{side}, site-robust but orientation-dependent")
        rows.append(dict(muscle=m, cluster4_dB=round(cluster, 4),
                         rand4_lo=round(lo, 4), rand4_hi=round(hi, 4),
                         crosses_zero=crosses,
                         orientation_agree_pct=round(agree, 1),
                         below_floor=abs(cluster) < FLOOR_DB,
                         verdict=verdict))

    t = pd.DataFrame(rows).sort_values("cluster4_dB", ascending=False)
    t[["muscle", "cluster4_dB", "rand4_lo", "rand4_hi", "crosses_zero",
       "verdict"]].to_csv(OUT_H, index=False)
    t[["muscle", "cluster4_dB", "rand4_lo", "rand4_hi", "crosses_zero",
       "orientation_agree_pct", "verdict"]].rename(
        columns={"cluster4_dB": "cluster_gap_dB"}).to_csv(OUT_J, index=False)
    print(t.to_string(index=False))
    print(f"\nwrote {OUT_H.name} and {OUT_J.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
