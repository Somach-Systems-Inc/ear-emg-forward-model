#!/usr/bin/env python3
r"""
Stage 4p. THE HEADLINE INTERVAL. Generating script for the paper's single support.

WHY THIS EXISTS

`−1.147 dB` with `[−1.453, +5.458]` is the sole support for the paper's central
claim, and until now **nothing in the repository produced it**. It was computed
interactively and the output was never saved: the same defect as `04h`/`04j`
before they were scripted, and as §3.4. A published number with a real method and
no saved code is not a result.

Reproducing it required identifying the construction, which was also unrecorded.
Per-direction draws on the same data give `[−3.283, +3.997]`, not the published
interval.

THE CONSTRUCTION, AND WHY IT IS THE RIGHT ONE

**Per-voxel.** The draw resamples ELECTRODES only, with the derived fibre field
held fixed. §3.1 states the inferential target as site-selection uncertainty --
"whether a preference is a property of the montage or of which sites happen to be
available" -- and resampling electrodes alone is exactly that question.

The per-direction alternative takes a median over 200 sampled orientations inside
each draw. That reintroduces the uniform-orientation assumption which the derived
fibre field exists to remove, and answers a question §3.1 does not ask. It is not
a rival construction; it is the wrong treatment's construction applied to the
wrong object. It is emitted below **for robustness only** and is deliberately
NOT reported in the manuscript: the claim rests on one support and the paper says
so, and reporting a second construction that also spans zero would quietly
convert one support into two.

THE LOWER BOUND IS NOT A QUANTILE

The most ear-favouring outcome of any 4-site draw is the best of all 14 sites, so
the interval's lower bound is a floor fixed by the data, attained exactly whenever
a draw contains the single best ear site. It therefore coincides with the
argmax-14 gap by construction: those two figures are one measurement, not two
that agree. Both are emitted so the manuscript can disclose it. Table 4's
corresponding bound is a genuine percentile lying strictly above its own floor,
which is why the two lower bounds are not comparable quantities.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/04p_headline_interval.py
"""
from __future__ import annotations

import csv
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config                      # noqa: E402

PERVOX = config.RESULTS / "04k_temporalis_pervoxel.csv"
PERDIR = config.RESULTS / "04k_temporalis_perdirection.npz"
CLEAR = config.RESULTS / "02_cut_clearance.csv"
OUT = config.RESULTS / "04p_headline_interval.csv"

CLUSTER = ["above_ear", "mastoid", "post_lobule", "pre_tragus"]
NEAR_CUT_MM = 10.0
N_DRAWS = 10_000
SEED = 0

# The published basis. Frozen, not derived: the corrected clearance admits
# `submental_mid`, leaving five admissible jaw sites against a four-site
# pre-registered ear cluster, and no rule selects the fifth. See 04n.
PUBLISHED_JAW = ("buccal", "mental", "midjaw", "submaxillary")
PUBLISHED = dict(median=-1.147, lo=-1.453, hi=5.458, pct_ear=50.2)


def exact_pervoxel(pv, jaw, ear):
    """EXACT over every possible subset, not a sample of them.

    The ear pool is 14 sites and the draw is 4, so there are C(14,4) = 1001
    possible subsets -- small enough to enumerate. The published figures came
    from 10,000 random draws, which is a Monte Carlo approximation to a quantity
    that can simply be computed.

    This matters for two reasons beyond accuracy. It removes the seed, so the
    interval stops depending on a choice nobody defended. And it settles what
    the interval IS: a complete description of a finite, enumerable set of
    montage choices, not an inference from a sample to a population. That is why
    no multiple-comparison correction applies across the ten muscles -- there is
    no sampling distribution and no null hypothesis being rejected.
    """
    J = max(pv[e] for e in jaw)
    d = np.array([20 * np.log10(J / max(pv[e] for e in s))
                  for s in itertools.combinations(sorted(ear), len(CLUSTER))])
    floor = 20 * np.log10(J / max(pv[e] for e in ear))
    return d, float(floor)


def draws_pervoxel(pv, jaw, ear, seed=SEED, n=N_DRAWS):
    """Resample electrodes only. The fibre field is fixed and already integrated
    over voxels, so each site is one number. Retained to reproduce the published
    Monte Carlo figures; `exact_pervoxel` supersedes it."""
    J = max(pv[e] for e in jaw)
    rng = np.random.default_rng(seed)
    d = np.array([20 * np.log10(J / max(pv[e] for e in
                  rng.choice(ear, len(CLUSTER), replace=False)))
                  for _ in range(n)])
    floor = 20 * np.log10(J / max(pv[e] for e in ear))
    return d, float(floor)


def draws_perdirection(pd_, jaw, ear, seed=SEED, n=N_DRAWS):
    """ROBUSTNESS ONLY. Not reported in the manuscript -- see the docstring."""
    J = np.max(np.stack([pd_[e] for e in jaw]), axis=0)
    per = np.stack([pd_[e] for e in ear])
    rng = np.random.default_rng(seed)
    d = np.array([np.median(20 * np.log10(
        J / per[rng.choice(len(ear), len(CLUSTER), replace=False)].max(axis=0)))
        for _ in range(n)])
    floor = float(np.median(20 * np.log10(J / per.max(axis=0))))
    return d, floor


def summarise(d, floor):
    lo, hi = np.percentile(d, [2.5, 97.5])
    return dict(
        median_dB=round(float(np.median(d)), 4),
        lo_dB=round(float(lo), 4), hi_dB=round(float(hi), 4),
        spans_zero=bool(lo < 0 < hi),
        pct_favouring_ear=round(100 * float((d < 0).mean()), 1),
        floor_dB=round(floor, 4),
        floor_attained_pct=round(100 * float(np.isclose(d, floor).mean()), 1),
        lower_bound_is_floor=bool(np.isclose(lo, floor)),
    )


def main() -> int:
    pv = {r["electrode"]: float(r["lf_pervoxel_fan"])
          for r in csv.DictReader(open(PERVOX))}
    pd_ = np.load(PERDIR)
    lf = pd.read_csv(config.RESULTS / "03_leadfields.csv").set_index("electrode")
    mont = lf.montage.to_dict()
    clear = {r["electrode"]: float(r["clearance_perp_mm"]) for r in
             csv.DictReader(l for l in open(CLEAR) if not l.startswith("#"))}

    ear = sorted(e for e in pv if mont[e] in ("ear", "ceegrid"))
    jaw_all = [e for e in pv if mont[e] == "jaw"]
    admissible = sorted(e for e in jaw_all if clear[e] >= NEAR_CUT_MM)

    print("HEADLINE INTERVAL — temporalis over the derived fibre fan")
    print("=" * 78)
    print(f"  ear pool          : {len(ear)} sites")
    print(f"  drawn per subsample: {len(CLUSTER)}")
    print(f"  draws             : {N_DRAWS:,}   seed {SEED}")
    print(f"  admissible jaw    : {admissible}")
    print(f"  published basis   : {sorted(PUBLISHED_JAW)}\n")

    rows = []
    for sset in itertools.combinations(admissible, len(CLUSTER)):
        dropped = (set(admissible) - set(sset)).pop()
        is_pub = tuple(sorted(sset)) == tuple(sorted(PUBLISHED_JAW))
        for label, fn in (("pervoxel_EXACT", exact_pervoxel),
                          ("pervoxel_montecarlo", draws_pervoxel),
                          ("perdirection_ROBUSTNESS_ONLY", draws_perdirection)):
            src = pd_ if label.startswith("perdirection") else pv
            d, floor = fn(src, list(sset), ear)
            r = dict(construction=label, jaw_set="+".join(sorted(sset)),
                     dropped=dropped, is_published_basis=is_pub,
                     reported_in_manuscript=(label == "pervoxel_EXACT"),
                     **summarise(d, floor),
                     argmax14_gap_dB=round(floor, 4),
                     n_draws=N_DRAWS, seed=SEED, n_ear_sites=len(ear),
                     n_drawn=len(CLUSTER))
            rows.append(r)

    with open(OUT, "w", newline="") as fh:
        fh.write("# Temporalis matched-count interval over the derived fibre fan.\n")
        fh.write("# construction=pervoxel is THE REPORTED ONE: resamples electrodes\n")
        fh.write("#   only, fibre field fixed. Matches the inferential target §3.1\n")
        fh.write("#   states at lines 477-480 (site-selection uncertainty).\n")
        fh.write("# construction=perdirection_ROBUSTNESS_ONLY medians over 200\n")
        fh.write("#   orientations inside each draw, reintroducing the uniform-sweep\n")
        fh.write("#   assumption the derived field replaces. NOT reported in the\n")
        fh.write("#   manuscript; the claim rests on one support and says so.\n")
        fh.write("# floor_dB == argmax14_gap_dB BY CONSTRUCTION: the best draw is the\n")
        fh.write("#   best of all ear sites. lower_bound_is_floor=True means the\n")
        fh.write("#   interval's lower end is NOT a tail quantile.\n")
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)

    print(f"  {'construction':<30}{'drop':<15}{'median':>9}{'interval':>21}"
          f"{'ear %':>7}{'floor%':>8}")
    print("  " + "-" * 90)
    for r in rows:
        print(f"  {r['construction']:<30}{r['dropped']:<15}{r['median_dB']:>9.3f}"
              f" [{r['lo_dB']:+8.3f}, {r['hi_dB']:+8.3f}]"
              f"{r['pct_favouring_ear']:>6.1f}%{r['floor_attained_pct']:>7.1f}%"
              f"{'  <-- PUBLISHED' if r['is_published_basis'] and r['reported_in_manuscript'] else ''}")

    # ---- reproduction check against the published figures
    p = [r for r in rows if r["is_published_basis"]
         and r["construction"] == "pervoxel_montecarlo"][0]
    print(f"\n  REPRODUCTION CHECK against the published headline")
    ok = True
    for k, got, want in (("median", p["median_dB"], PUBLISHED["median"]),
                         ("lo", p["lo_dB"], PUBLISHED["lo"]),
                         ("hi", p["hi_dB"], PUBLISHED["hi"]),
                         ("pct ear", p["pct_favouring_ear"], PUBLISHED["pct_ear"])):
        hit = abs(got - want) < 5e-4
        ok &= hit
        print(f"    {k:<9} script {got:+9.4f}   published {want:+9.4f}   "
              f"{'MATCH' if hit else '*** DIFFERS ***'}")
    if not ok:
        raise RuntimeError(
            "this script does not reproduce the published headline interval. "
            "Do not report either number until that is resolved.")
    print(f"\n  All four reproduce exactly. The headline now has a generating "
          f"script.")
    print(f"  Lower bound is the floor, not a quantile: "
          f"{p['lower_bound_is_floor']}, attained in "
          f"{p['floor_attained_pct']}% of draws "
          f"(draw size alone predicts "
          f"{100*len(CLUSTER)/len(ear):.1f}%).")
    print(f"\nwrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
