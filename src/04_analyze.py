#!/usr/bin/env python3
"""
Stage 4. Sensitivity matrix and the jaw-versus-ear dB budget.

THE TRUNCATION SENSITIVITY IS THE POINT OF THIS SCRIPT, not an appendix to it.

MIDA is cut at S = -116.2 mm with an insulating face there. Three jaw sites sit
within 10 mm of it -- `hyoid` (8.0), `submental_lat` (8.4), `submental_mid`
(9.7) -- while every ear site is 80 mm or more away. Reflection at that face
inflates the near sites and leaves the far ones untouched, so the truncation
**flatters the paper's own jaw-versus-ear headline**.

The gap is therefore reported TWICE: once over all jaw sites, once excluding
those three. Same solves, different subset, no extra compute. If the gap does
not survive the exclusion, that must be known before any Discussion exists,
which is why this runs before figures rather than after.

Every published number here is a RATIO -- site against site, ear against jaw.
That is what makes the delivered-current uncertainty harmless: a term that
scales the whole lead field equally cancels exactly in every ratio (Table 3).

    .venv/bin/python src/04_analyze.py
    ... --csv results/03_leadfields.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402

# The three jaw sites within 10 mm of the cut face. Named here, not derived
# from a magic distance, so the exclusion set is auditable.
NEAR_CUT = ("hyoid", "submental_lat", "submental_mid")
NEAR_CUT_MM = 10.0

MUSCLE_NAMES = [n for n, _, lab, _ in config.MUSCLES if lab is not None]


def read_floor():
    """The electrode-meshing floor is MEASURED, never hardcoded."""
    f = config.RESULTS / "electrode_meshing_floor.txt"
    if not f.exists():
        raise FileNotFoundError(
            f"{f} missing. Every dB claim here is reported against the "
            f"measured per-site floor; run src/measure_electrode_floor.py.")
    for line in f.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return float(line.split()[0])
    raise RuntimeError(f"no numeric floor value in {f}")


def load(csv_path: Path):
    d = pd.read_csv(csv_path)
    missing = [m for m in MUSCLE_NAMES if m not in d.columns]
    if missing:
        raise RuntimeError(f"{csv_path} has no columns for {missing}")
    have = d[MUSCLE_NAMES]
    if not np.isfinite(have.to_numpy(dtype=float)).all():
        bad = d.loc[~np.isfinite(have.to_numpy(dtype=float)).all(axis=1),
                    "electrode"].tolist()
        raise RuntimeError(f"non-finite lead fields for {bad}; refusing to "
                           f"average over them")
    return d


def db_matrix(d):
    """Lead field in dB relative to the best JAW site, per muscle.

    Per-muscle reference, not a global one: the question is how much signal a
    site loses for a given muscle against the best jaw electrode for THAT
    muscle, which is the quantity a designer needs.
    """
    jaw = d[d.montage == "jaw"]
    if jaw.empty:
        raise RuntimeError("no jaw sites; the dB reference is undefined")
    ref = jaw[MUSCLE_NAMES].max()             # best jaw site per muscle
    if (ref <= 0).any():
        raise RuntimeError(f"non-positive jaw reference for "
                           f"{ref.index[ref <= 0].tolist()}")
    db = 20.0 * np.log10(d[MUSCLE_NAMES].to_numpy(dtype=float) /
                         ref.to_numpy(dtype=float)[None, :])
    out = pd.DataFrame(db, columns=MUSCLE_NAMES)
    out.insert(0, "electrode", d["electrode"].to_numpy())
    out.insert(1, "montage", d["montage"].to_numpy())
    out.insert(2, "clearance_to_cut_mm", d["clearance_to_cut_mm"].to_numpy())
    return out, ref


def gap(db, jaw_subset=None):
    """Jaw-versus-ear gap in dB: best jaw minus best ear, per muscle.

    'Best' is the maximum over sites in each group, because the design question
    is what the best available electrode achieves, not what the average does.
    """
    jaw = db[db.montage == "jaw"]
    if jaw_subset is not None:
        jaw = jaw[jaw.electrode.isin(jaw_subset)]
    ear = db[db.montage.isin(("ear", "ceegrid"))]
    if jaw.empty or ear.empty:
        raise RuntimeError("empty jaw or ear group")
    return (jaw[MUSCLE_NAMES].max() - ear[MUSCLE_NAMES].max()), \
        sorted(jaw.electrode), sorted(ear.electrode)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="04_analyze.py")
    ap.add_argument("--csv", type=Path,
                    default=config.RESULTS / "03_leadfields.csv")
    a = ap.parse_args(argv)

    d = load(a.csv)
    floor = read_floor()
    db, ref = db_matrix(d)

    print("STAGE 4 — sensitivity matrix and the jaw-versus-ear budget")
    print("=" * 74)
    print(f"  solves            : {len(d)}")
    print(f"  muscles           : {len(MUSCLE_NAMES)}")
    print(f"  measured per-site floor : {floor:.3f} dB "
          f"(95% CI [0.17, 0.65]; every claim below is read against it)")

    # ---- truncation exposure, stated per site rather than argued
    print("\nCLEARANCE TO THE CUT FACE (S = -116.2 mm), per site")
    print("-" * 74)
    ex = d[["electrode", "montage", "clearance_to_cut_mm"]].sort_values(
        "clearance_to_cut_mm")
    for _, r in ex.iterrows():
        flag = "  <-- within 10 mm" if r.clearance_to_cut_mm < NEAR_CUT_MM else ""
        print(f"  {r.electrode:<16} {r.montage:<10} "
              f"{r.clearance_to_cut_mm:>7.2f} mm{flag}")

    derived = tuple(ex.loc[ex.clearance_to_cut_mm < NEAR_CUT_MM, "electrode"])
    if set(derived) != set(NEAR_CUT):
        raise RuntimeError(
            f"the hardcoded near-cut set {NEAR_CUT} disagrees with what the "
            f"clearance column actually says ({derived}). One of them is "
            f"stale; do not report a subset that is not the measured one.")
    print(f"\n  the {len(NEAR_CUT)} sites within {NEAR_CUT_MM:.0f} mm are "
          f"exactly {list(NEAR_CUT)} — hardcoded set agrees with the measured "
          f"clearances")

    # ---- THE HEADLINE, TWICE
    all_jaw = sorted(d.loc[d.montage == "jaw", "electrode"])
    kept = [e for e in all_jaw if e not in NEAR_CUT]

    g_all, j_all, ears = gap(db)
    g_far, j_far, _ = gap(db, jaw_subset=kept)

    print("\nJAW-VERSUS-EAR GAP, reported twice")
    print("=" * 74)
    print(f"  all jaw sites          (n={len(j_all)}): {j_all}")
    print(f"  excluding near-cut     (n={len(j_far)}): {j_far}")
    print(f"  ear + cEEGrid          (n={len(ears)})")
    print()
    print(f"  {'muscle':<24}{'all jaw':>10}{'far jaw':>10}{'change':>10}"
          f"   survives?")
    print("  " + "-" * 70)
    rows = []
    for m in MUSCLE_NAMES:
        ga, gf = float(g_all[m]), float(g_far[m])
        delta = gf - ga
        # SURVIVES = the conclusion is unchanged by the exclusion. Two
        # conditions, and conflating them misreports the result:
        #   - the gap is still RESOLVABLE, i.e. |gap| exceeds the floor. The
        #     absolute value matters because a NEGATIVE gap is not a failed
        #     gap, it is the opposite finding: the ear beats the jaw for that
        #     muscle, which is a publishable result in its own right and is
        #     exactly the "both outcomes publish" case.
        #   - the SIGN is unchanged, so the exclusion did not flip which
        #     montage wins.
        resolvable = abs(gf) > floor
        same_sign = (ga >= 0) == (gf >= 0)
        surv = resolvable and same_sign
        note = ("yes" if surv else
                "sign FLIPPED" if not same_sign else
                "no — |gap| under the floor")
        who = "jaw" if gf >= 0 else "EAR wins"
        print(f"  {m:<24}{ga:>+9.2f} {gf:>+9.2f} {delta:>+9.2f}   "
              f"{note:<22}{who}")
        rows.append(dict(muscle=m, gap_all_jaw_dB=round(ga, 3),
                         gap_far_jaw_dB=round(gf, 3),
                         change_dB=round(delta, 3),
                         resolvable=bool(resolvable),
                         sign_preserved=bool(same_sign),
                         favours="jaw" if gf >= 0 else "ear",
                         survives_exclusion=bool(surv)))

    n_surv = sum(r["survives_exclusion"] for r in rows)
    n_ear = sum(r["favours"] == "ear" for r in rows)
    med_all = float(np.median([r["gap_all_jaw_dB"] for r in rows]))
    med_far = float(np.median([r["gap_far_jaw_dB"] for r in rows]))

    print("\n" + "=" * 74)
    print(f"  median gap, all jaw sites : {med_all:+.2f} dB")
    print(f"  median gap, near-cut sites excluded : {med_far:+.2f} dB")
    print(f"  shift from excluding them : {med_far - med_all:+.2f} dB")
    print(f"  conclusion unchanged by the exclusion : {n_surv} of "
          f"{len(rows)} muscles")
    print(f"  muscles where the EAR beats the jaw    : {n_ear} of "
          f"{len(rows)}  (a result, not a failure)")
    flipped = [r["muscle"] for r in rows if not r["sign_preserved"]]
    unres = [r["muscle"] for r in rows if not r["resolvable"]]
    print()
    if not flipped and not unres:
        print("  THE GAP SURVIVES THE EXCLUSION for every muscle: no sign")
        print("  flips, and every |gap| still clears the measured floor. The")
        print("  truncation is NOT what produces the jaw-versus-ear result.")
    else:
        if flipped:
            print(f"  SIGN FLIPPED for {flipped} — for these, which montage")
            print("  wins depends on sites the truncation inflates. STATE THIS")
            print("  BEFORE ANY DISCUSSION IS WRITTEN.")
        if unres:
            print(f"  UNRESOLVABLE (|gap| under the {floor:.2f} dB floor): "
                  f"{unres}.")
            print("  Report these as 'no resolvable difference', never as a")
            print("  jaw advantage.")

    # FLIP POINT, not a bare binary: the floor at which the verdict changes.
    mags = sorted(abs(r["gap_far_jaw_dB"]) for r in rows)
    print(f"\n  FLIP POINT, on the floor: with the near-cut sites excluded,")
    print(f"    smallest |gap| is {mags[0]:.2f} dB, so every muscle stays")
    print(f"    resolvable for any floor below that and the weakest drops out")
    print(f"    above it. Measured floor {floor:.2f} dB, 95% CI [0.17, 0.65];")
    print(f"    at the CI's upper bound {sum(m > 0.65 for m in mags)} of "
          f"{len(mags)} remain resolvable.")

    # ---- the FIGURE CONTRACT file, long format. Queue item (a): the figures
    # read this, so emitting it here is what retires 04_sensitivity_MOCK.csv.
    # Columns are render_common.CORE_COLUMNS exactly.
    long = []
    lf = d.set_index("electrode")[MUSCLE_NAMES]
    dbi = db.set_index("electrode")[MUSCLE_NAMES]
    for elec in d["electrode"]:
        for m in MUSCLE_NAMES:
            long.append(dict(electrode=elec, muscle=m, condition="iso",
                             mesh="truncated",
                             lead_field=float(lf.loc[elec, m]),
                             db_rel_best_jaw=round(float(dbi.loc[elec, m]), 4)))
    contract = config.RESULTS / "04_sensitivity.csv"
    pd.DataFrame(long).to_csv(contract, index=False)
    print(f"\nwrote {contract}  ({len(long)} rows, long format, "
          f"the figure contract)")

    out = config.RESULTS / "04_jaw_vs_ear_gap.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    db.round(3).to_csv(config.RESULTS / "04_sensitivity_matrix_dB.csv",
                       index=False)
    print(f"\nwrote {out}")
    print(f"wrote {config.RESULTS / '04_sensitivity_matrix_dB.csv'}")
    print("\nFig 2 reads the sensitivity matrix; Fig 5 ranks the "
          "retroauricular\nsites by total articulator sensitivity from it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
