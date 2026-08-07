#!/usr/bin/env python3
r"""
Stage 4q. TABLE 4 AS AN ENVELOPE over all five admissible jaw subsets.

WHY THIS EXISTS

The corrected perpendicular clearance admits `submental_mid` at 10.759 mm,
leaving FIVE admissible jaw sites against a four-site pre-registered ear cluster.
The matched comparison takes four. **No rule selects the fifth**, and choosing one
after seeing its effect on two verdicts would be `CUT_FACE_S` rebuilt with worse
provenance.

So no subset is selected. Every value is reported as the envelope over all
C(5,4) = 5 subsets, and the two muscles whose verdict differs between subsets are
marked unstable rather than resolved.

WHY THIS IS A GENERATOR AND NOT WORDING

An earlier attempt supplied a caption asserting every cell is an envelope while
the table body still held single-subset point values. That would have made the
caption false about its own table -- the §3.4 defect reproduced inside the file
written to prevent it. The body has to be generated before the caption can be
true, which is what this does.

THE ROW-LEVEL CHECK

The published four-site subset must reproduce the current Table 4 exactly. If it
does not, this script refuses to write, because an envelope whose own basis does
not reproduce is not a superset of the published result.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/04q_table4_envelope.py
    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/04q_table4_envelope.py --write-block
"""
from __future__ import annotations

import argparse
import csv
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
PUBLISHED = config.RESULTS / "04j_two_axis_verdict.csv"
OUT = config.RESULTS / "04q_table4_envelope.csv"

CLUSTER = ["above_ear", "mastoid", "post_lobule", "pre_tragus"]
PUBLISHED_JAW = ("buccal", "mental", "midjaw", "submaxillary")
NEAR_CUT_MM = 10.0
N_DRAWS, SEED = 10_000, 0
ORIENT_BAR = 90.0


def statistic_A(d, jaw, ear, muscles):
    """Verbatim the computation in 04h_matched_counts.py. Do NOT renormalise:
    04d already divided by delivered current at line 123."""
    out = {}
    for m in muscles:
        def best(sites):
            return np.max([d[f"lf_{e}|{m}"] for e in sites], axis=0)
        J = best(jaw)
        cluster = float(np.median(20 * np.log10(J / best(CLUSTER))))
        rng = np.random.default_rng(SEED)
        per = np.stack([d[f"lf_{e}|{m}"] for e in ear])
        draws = np.array([
            np.median(20 * np.log10(
                J / per[rng.choice(len(ear), len(CLUSTER),
                                   replace=False)].max(axis=0)))
            for _ in range(N_DRAWS)])
        lo, hi = np.percentile(draws, [2.5, 97.5])
        gaps = 20 * np.log10(J / best(CLUSTER))
        agree = float(100.0 * np.mean(np.sign(gaps) == np.sign(cluster)))
        crosses = bool(lo < 0 < hi)
        verdict = ("no resolvable preference" if crosses else
                   (("jaw" if cluster > 0 else "ear") +
                    (", robust on both axes" if agree >= ORIENT_BAR
                     else ", site-robust but orientation-dependent")))
        out[m] = dict(gap=cluster, lo=lo, hi=hi, crosses=crosses,
                      agree=agree, verdict=verdict)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(prog="04q_table4_envelope.py")
    ap.add_argument("--write-block", action="store_true",
                    help="regenerate the two_axis_verdict block in the manuscript")
    a = ap.parse_args(argv)

    lf = pd.read_csv(config.RESULTS / "03_leadfields.csv").set_index("electrode")
    d = np.load(PERDIR)
    clear = {r["electrode"]: float(r["clearance_perp_mm"]) for r in
             csv.DictReader(l for l in open(CLEAR, encoding="utf-8") if not l.startswith("#"))}

    present = {e for e in lf.index if f"lf_{e}|temporalis" in d}
    jaw_all = sorted(e for e in present if lf.montage[e] == "jaw")
    ear = sorted(e for e in present if lf.montage[e] in ("ear", "ceegrid"))
    admissible = sorted(e for e in jaw_all if clear[e] >= NEAR_CUT_MM)
    muscles = [n for n, _g, lab, _e in config.MUSCLES if lab is not None]

    subsets = list(itertools.combinations(admissible, len(CLUSTER)))
    print("TABLE 4 AS AN ENVELOPE")
    print("=" * 78)
    print(f"  admissible jaw sites : {len(admissible)}  {admissible}")
    print(f"  subsets of size {len(CLUSTER)}    : {len(subsets)}")
    print(f"  ear pool             : {len(ear)}\n")

    per_subset = {s: statistic_A(d, list(s), ear, muscles) for s in subsets}

    # ---- ROW-LEVEL CHECK: the published subset must reproduce Table 4 exactly
    pub = per_subset[tuple(sorted(PUBLISHED_JAW))]
    ref = pd.read_csv(PUBLISHED).set_index("muscle")
    print("  ROW-LEVEL CHECK against the published Table 4")
    bad = []
    for m in muscles:
        got, want = pub[m], ref.loc[m]
        for k, g, w in (("gap", got["gap"], float(want["cluster_gap_dB"])),
                        ("lo", got["lo"], float(want["rand4_lo"])),
                        ("hi", got["hi"], float(want["rand4_hi"]))):
            if abs(g - w) > 5e-4:
                bad.append(f"{m}.{k}: {g:+.4f} vs published {w:+.4f}")
        if got["verdict"] != want["verdict"]:
            bad.append(f"{m}.verdict: {got['verdict']!r} vs {want['verdict']!r}")
    if bad:
        for b in bad:
            print(f"    *** {b}")
        raise RuntimeError(
            "the published four-site subset does not reproduce Table 4. Refusing "
            "to write an envelope whose own basis does not reproduce.")
    print(f"    all {len(muscles)} rows reproduce exactly\n")

    rows = []
    for m in muscles:
        gs = [per_subset[s][m]["gap"] for s in subsets]
        ags = [per_subset[s][m]["agree"] for s in subsets]
        robust = sum(not per_subset[s][m]["crosses"] for s in subsets)
        verds = {per_subset[s][m]["verdict"] for s in subsets}
        stable = len(verds) == 1
        rows.append(dict(
            muscle=m,
            gap_lo_dB=round(min(gs), 4), gap_hi_dB=round(max(gs), 4),
            orient_lo_pct=round(min(ags), 1), orient_hi_pct=round(max(ags), 1),
            site_robust_subsets=robust, n_subsets=len(subsets),
            stable=stable,
            verdict=(sorted(verds)[0] if stable else "unstable across subsets"),
            all_verdicts=" | ".join(sorted(verds)),
            published_gap_dB=round(pub[m]["gap"], 4),
        ))
    rows.sort(key=lambda r: -r["published_gap_dB"])

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        fh.write("# Table 4 as an envelope over every admissible jaw subset.\n")
        fh.write(f"# {len(admissible)} jaw sites admissible, comparison takes "
                 f"{len(CLUSTER)}, so all {len(subsets)} subsets are reported.\n")
        fh.write("# NO SUBSET IS SELECTED. Choosing one after seeing its effect\n")
        fh.write("#   on a verdict is the CUT_FACE_S defect again.\n")
        fh.write(f"# seed {SEED}, {N_DRAWS} draws, orientation bar {ORIENT_BAR}%\n")
        wr = csv.DictWriter(fh, fieldnames=list(rows[0]))
        wr.writeheader()
        wr.writerows(rows)
    print(f"  wrote {OUT.name}")

    def fmt(r):
        gap = f"{r['gap_lo_dB']:+.2f} to {r['gap_hi_dB']:+.2f}"
        rob = ("yes, all %d" % r["n_subsets"] if r["site_robust_subsets"] == r["n_subsets"]
               else "%d of %d" % (r["site_robust_subsets"], r["n_subsets"]))
        ori = (f"{r['orient_lo_pct']:.1f} %" if r["orient_lo_pct"] == r["orient_hi_pct"]
               else f"{r['orient_lo_pct']:.1f}–{r['orient_hi_pct']:.1f} %")
        ver = (f"**{r['verdict']}**" if r["stable"]
               else f"**unstable across subsets**")
        return f"| {r['muscle'].replace('_',' ')} | {gap} | {rob} | {ori} | {ver} |"

    block = ["| Muscle | Gap (dB), envelope over subsets | Site-robust | "
             "Orientation agreement | Verdict |",
             "|---|---|---|---|---|"] + [fmt(r) for r in rows]
    print()
    for l in block:
        print("  " + l)

    if a.write_block:
        import manuscript_blocks as MB
        MB.replace_block("two_axis_verdict", "\n".join(block))
        print(f"\n  wrote the two_axis_verdict block via anchored write")
    else:
        print(f"\n  (dry run; pass --write-block to write it into the manuscript)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
