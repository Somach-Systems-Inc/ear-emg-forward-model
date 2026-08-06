#!/usr/bin/env python3
r"""
Stage 4r. The homogeneous-conductor temporalis pair AT CLUSTER BASIS.

WHY THIS EXISTS

§3.5 states that temporalis's retroauricular advantage grows under a homogeneous
conductor, "from -2.571 to -3.724 dB at the pre-registered cluster". **Both
numbers are correct and neither was stored in any results file.**

`04i_homog_scalp.csv` does not supply the second one. It holds -3.3145 -> -4.3299,
which are **argmax-14** values, and pairing an argmax-14 homogeneous number with a
cluster-basis detailed number would be the statistic-B error in another costume.
`04i` also has no generating script.

THE ASYMMETRY THAT MAKES THIS EASY TO GET WRONG, AND HOW IT WAS CAUGHT

The two per-direction stores are NOT normalised the same way:

    04d_orientation_sign.npz          ALREADY divided by delivered current
                                      (04d line 123). Keys `lf_<e>|<m>`.
    03_homog_scalp_per_direction.npz  NOT divided. Keys `<e>|<m>`.

Reducing both the same way reproduces the detailed values exactly and BOTH
homogeneous values wrongly: argmax-14 comes out -4.8123 against 04i's -4.3299,
and the cluster value comes out -3.6722 against the manuscript's -3.724.

**-3.6722 is wrong by 0.05 dB, which reads as rounding.** It was not reported,
because a reduction that fails to reproduce two of four known values cannot be
trusted for the fifth. Applying the renormalisation reproduces 04i's -4.3299
exactly and gives -3.7237 for the unknown. That is why the control matters more
than the answer.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/04r_homog_cluster.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config                      # noqa: E402

DET = config.RESULTS / "04d_orientation_sign.npz"
HOM = config.RESULTS / "03_homog_scalp_per_direction.npz"
ENVELOPE = config.RESULTS / "04q_table4_envelope.csv"
OUT = config.RESULTS / "04r_homog_cluster.csv"

CLUSTER = ["above_ear", "mastoid", "post_lobule", "pre_tragus"]
PUBLISHED_JAW = ["buccal", "mental", "midjaw", "submaxillary"]
MUSCLE = "temporalis"
# Known-good targets. These are what the reduction must land on before anything
# is written; they are not inputs to it.
EXPECT_DETAILED = -2.5710
EXPECT_HOMOG = -3.7237
EXPECT_04I_ARGMAX14 = -4.3299


def gap(store, prefix, jaw, ear, muscle, deliv=None):
    """Statistic A: median over orientations of the per-orientation gap."""
    def arr(e):
        v = store[f"{prefix}{e}|{muscle}"]
        return v / deliv[e] if deliv else v
    J = np.max(np.stack([arr(e) for e in jaw]), axis=0)
    R = np.max(np.stack([arr(e) for e in ear]), axis=0)
    return float(np.median(20 * np.log10(J / R)))


def main() -> int:
    det, hom = np.load(DET), np.load(HOM)
    lf = pd.read_csv(config.RESULTS / "03_leadfields.csv")
    iso = lf[lf.condition == "iso"].set_index("electrode")
    mont, deliv = iso.montage.to_dict(), iso.inv1_mean.to_dict()
    ear14 = sorted(e for e in mont if mont[e] in ("ear", "ceegrid")
                   and f"{e}|{MUSCLE}" in hom)

    g_det = gap(det, "lf_", PUBLISHED_JAW, CLUSTER, MUSCLE)
    g_hom = gap(hom, "", PUBLISHED_JAW, CLUSTER, MUSCLE, deliv)
    g_hom_a14 = gap(hom, "", PUBLISHED_JAW, ear14, MUSCLE, deliv)
    g_hom_raw = gap(hom, "", PUBLISHED_JAW, CLUSTER, MUSCLE)

    print(f"TEMPORALIS, CLUSTER BASIS, detailed vs homogeneous conductor")
    print("=" * 74)
    print(f"  detailed  (04d, already renormalised) : {g_det:+.4f} dB")
    print(f"  homogeneous (03h, renormalised here)  : {g_hom:+.4f} dB")
    print(f"  change                                : {g_hom - g_det:+.4f} dB")
    print(f"\n  CONTROL, the reason this is trustworthy:")
    print(f"    homogeneous at argmax-14  : {g_hom_a14:+.4f}  "
          f"(04i says {EXPECT_04I_ARGMAX14:+.4f})")
    print(f"    same, WITHOUT renormalising: {g_hom_raw:+.4f}  "
          f"<- the 0.05 dB error that reads as rounding")

    # ---- refusal guards
    bad = []
    if abs(g_hom_a14 - EXPECT_04I_ARGMAX14) > 5e-4:
        bad.append(f"argmax-14 control {g_hom_a14:+.4f} != 04i's "
                   f"{EXPECT_04I_ARGMAX14:+.4f}; the renormalisation is wrong")
    env = pd.read_csv(ENVELOPE, comment="#").set_index("muscle")
    t4 = float(env.loc[MUSCLE, "published_gap_dB"])
    if abs(g_det - t4) > 5e-4:
        bad.append(f"detailed {g_det:+.4f} != Table 4's temporalis cell "
                   f"{t4:+.4f}")
    for label, got, want in (("detailed", g_det, EXPECT_DETAILED),
                             ("homogeneous", g_hom, EXPECT_HOMOG)):
        if abs(got - want) > 5e-4:
            bad.append(f"{label} {got:+.4f} != expected {want:+.4f}")
    if bad:
        for b in bad:
            print(f"  *** {b}")
        raise RuntimeError(
            "refusing to write: this reduction does not reproduce its known "
            "values. A reduction that fails its control cannot be trusted for "
            "the quantity it was written to produce.")
    print(f"\n  all guards pass; detailed matches Table 4's cell at {t4:+.4f}")

    row = dict(
        muscle=MUSCLE, basis="cluster",
        cluster_sites="+".join(CLUSTER), jaw_sites="+".join(PUBLISHED_JAW),
        gap_detailed_dB=round(g_det, 4), gap_homog_dB=round(g_hom, 4),
        change_dB=round(g_hom - g_det, 4),
        detailed_source="results/04d_orientation_sign.npz (already renormalised, 04d:123)",
        homog_source="results/03_homog_scalp_per_direction.npz",
        renormalisation="inv1_mean, condition=iso, results/03_leadfields.csv",
        statistic="A: median over orientations of the per-orientation gap",
    )
    with open(OUT, "w", newline="") as fh:
        fh.write("# Homogeneous-conductor control for temporalis at the\n")
        fh.write("# PRE-REGISTERED CLUSTER basis. This is the source for the\n")
        fh.write("# -2.571 -> -3.724 pair in section 3.5.\n")
        fh.write("# NOT interchangeable with 04i_homog_scalp.csv, which is\n")
        fh.write("#   argmax-14 basis. Differencing across bases is statistic B.\n")
        fh.write("# The two per-direction stores are normalised DIFFERENTLY:\n")
        fh.write("#   04d is already divided by delivered current; 03h is not.\n")
        wr = csv.DictWriter(fh, fieldnames=list(row))
        wr.writeheader()
        wr.writerow(row)
    print(f"\nwrote {OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
