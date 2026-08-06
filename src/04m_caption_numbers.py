#!/usr/bin/env python3
r"""
Stage 4m. CAPTION NUMBERS — every figure-caption quantity, emitted from source.

WHY THIS EXISTS
---------------
Figure 5's caption claimed the jaw's advantages "reach +21.9 dB while the ear's
reach only -3.80 dB". The figure's own source CSV gives +20.90 and -3.31. The
caption numbers had been typed from a report rather than read from the file the
figure was rendered from, and they had been wrong since before the corrections
of 2026-08-05 -- through several passes that regenerated the figure itself.

A caption is prose that makes numerical claims about a figure. Nothing
regenerates it when the figure is rebuilt, so it silently decays. This script
emits every number any caption cites, straight from the file the corresponding
figure reads, so a caption can be checked against source instead of trusted.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/04m_caption_numbers.py
    ... --check     # non-zero exit if the manuscript disagrees with source

Each entry is (key, value, source file, the figure that uses it). Add a row here
when a caption gains a number; do not type the number into the caption.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config                      # noqa: E402

OUT = config.RESULTS / "04m_caption_numbers.json"
MANUSCRIPT = ROOT / "paper" / "PAPER1_full_manuscript.md"


def collect() -> dict:
    v = {}

    # --- Figure 2: the sensitivity matrix's own extent -------------------
    mx = pd.read_csv(config.RESULTS / "04_sensitivity_matrix_dB.csv")
    # Muscle columns ONLY. `select_dtypes("number")` also catches
    # `clearance_to_cut_mm`, which made an earlier version of this script report
    # 11 muscles and a +133 dB maximum, and nearly "correct" two right captions.
    mcols = [n for n, _g, lab, _e in config.MUSCLES
             if lab is not None and n in mx.columns]
    cells = mx[mcols].to_numpy(dtype=float)
    cells = cells[np.isfinite(cells)]
    v["fig2_n_electrodes"] = (int(len(mx)), "04_sensitivity_matrix_dB.csv", "2")
    v["fig2_n_muscles"] = (len(mcols), "04_sensitivity_matrix_dB.csv", "2")
    v["fig2_min_dB"] = (round(float(cells.min()), 2),
                        "04_sensitivity_matrix_dB.csv", "2")
    v["fig2_max_dB"] = (round(float(cells.max()), 2),
                        "04_sensitivity_matrix_dB.csv", "2")

    # --- Figure 4 -------------------------------------------------------
    # NO SOURCE. The count of compartments carrying a fibre tensor is not
    # written to any results file -- 03e_build_tensor.py decides it at run time
    # and reports it only to stdout. The caption's "2 of 10" is therefore
    # UNVERIFIABLE from disk, and is flagged rather than silently trusted.
    # Fixing this means having 03e emit its accept/refuse decision per
    # compartment; until then the claim is not checked here.
    v["fig4_n_tensor"] = (None, "NOT EMITTED BY 03e_build_tensor.py", "4")

    # --- Figure 5: the arms of the distribution it plots -----------------
    # Read the SAME file render_fig5.py reads, so the caption and the figure
    # cannot disagree by construction.
    s = pd.read_csv(config.RESULTS / "04d_orientation_sign.csv")
    v["fig5_jaw_max_dB"] = (round(float(s.gap_median_dB.max()), 2),
                            "04d_orientation_sign.csv", "5")
    v["fig5_ear_max_dB"] = (round(float(s.gap_median_dB.min()), 2),
                            "04d_orientation_sign.csv", "5")
    v["fig5_n_muscles"] = (int(len(s)), "04d_orientation_sign.csv", "5")

    # --- the measured electrode-realisation floor ------------------------
    f = config.RESULTS / "electrode_meshing_floor.txt"
    if f.exists():
        txt = f.read_text()
        nums = [float(x) for x in re.findall(r"[-+]?\d*\.\d+|\d+", txt)]
        if nums:
            v["floor_dB"] = (round(nums[0], 2), f.name, "5")
        hi = re.search(r"(?:95|upper)[^\d]{0,24}(\d+\.\d+)", txt)
        if hi:
            v["floor_ci_hi_dB"] = (round(float(hi.group(1)), 2), f.name, "5")

    # --- Supplementary S1: air compartments ------------------------------
    # Air-assigned labels in Table 1, EXCLUDING `Background` (label 50), which
    # is the space around the head rather than a compartment within it.
    t1 = config.RESULTS / "01_table1_conductivities.csv"
    if t1.exists():
        a = pd.read_csv(t1)
        air = a[a.assigned_tissue.astype(str).str.lower().str.contains("air")]
        air = air[~air.mida_name.astype(str).str.lower().str.contains(
            "background")]
        v["s1_n_air"] = (int(len(air)), t1.name, "S1")
    return v


# --- AXIS (b): every anchored table IS the table it claims to be ------------
# A corrupted table can trace perfectly to source. On 2026-08-06 §3.3's
# fat-contrast table held Table 4's rows; every number in it was real and came
# from a real CSV. Provenance checking passes that. Schema checking does not.
TABLE_SCHEMA = {
    "fat_contrast": {
        "source": "04e_fat_contrast_statisticA.csv",
        "header": ["Muscle", "As modelled", "Without contrast", "Change",
                   "Contrast's role"],
        "n_rows": 10,
    },
    # Regenerated by 04q_table4_envelope.py. The source moved from 04j (one
    # chosen four-site jaw subset) to 04q (the envelope over all five), because
    # no rule selects the fourth jaw site once the corrected clearance admits
    # `submental_mid`. 04q refuses to write unless the published subset
    # reproduces 04j row for row, so the envelope is a superset of what 04j said.
    "two_axis_verdict": {
        "source": "04q_table4_envelope.csv",
        "header": ["Muscle", "Gap (dB), envelope over subsets", "Site-robust",
                   "Orientation agreement", "Verdict"],
        "n_rows": 10,
    },
}


def check_tables(text):
    """Schema + row-count + row-label-collision checks on anchored blocks."""
    import manuscript_blocks as MB
    bad, hazards = [], []
    for prob in MB.audit():
        bad.append(("anchors", prob, ""))
    labelsets = {}
    for name, spec in TABLE_SCHEMA.items():
        try:
            blk = MB.read_block(name)
        except Exception as e:                       # noqa: BLE001
            bad.append((name, "unreadable", str(e)[:70]))
            continue
        lines = [l for l in blk.splitlines() if l.strip().startswith("|")]
        if not lines:
            bad.append((name, "no table rows", ""))
            continue
        hdr = [c.strip() for c in lines[0].strip("|").split("|")]
        if hdr != spec["header"]:
            bad.append((name, "HEADER MISMATCH", f"{hdr} != {spec['header']}"))
        rows = [l for l in lines[2:] if l.strip().startswith("|")]
        if len(rows) != spec["n_rows"]:
            bad.append((name, "ROW COUNT",
                        f"{len(rows)} rows, source has {spec['n_rows']}"))
        labelsets[name] = frozenset(
            r.strip("|").split("|")[0].strip() for r in rows)
    # No two blocks may share a row-label set -- that ambiguity is what let a
    # row-label regex write Table 4's rows into the fat-contrast table.
    seen = {}
    for name, ls in labelsets.items():
        if ls and ls in seen:
            # HAZARD, not a defect. Both tables legitimately list all ten
            # muscles, so their row labels must coincide. It is reported every
            # run because it is the precondition for the 2026-08-06 corruption:
            # any edit addressed by row label is ambiguous between these two
            # blocks. The anchors are what makes it safe; this line is why they
            # exist. Do NOT "fix" it by renaming rows.
            hazards.append((name, "row labels identical to", seen[ls]))
        seen[ls] = name
    return bad, hazards


# Caption claims that must equal a collected value. Regex must capture the
# number in group 1. A claim listed here and absent from the manuscript is a
# FAIL, not a skip -- a caption that lost its number is as broken as one that
# has the wrong number.
CLAIMS = [
    ("fig5_jaw_max_dB", r"the jaw's advantages reach\s*\+?([\d.]+)\s*dB"),
    ("fig5_ear_max_dB", r"while the ear's reach only\s*[-−]([\d.]+)\s*dB"),
    ("fig2_n_electrodes", r"(\d+)\s*electrodes\s*×\s*\d+\s*muscles"),
    ("fig2_n_muscles", r"\d+\s*electrodes\s*×\s*(\d+)\s*muscles"),
    ("s1_n_air", r"all (\w+) air-filled compartments"),
    ("floor_dB", r"electrode-meshing floor \(([\d.]+)\s*dB"),
    ("floor_ci_hi_dB", r"upper bound of\s*([\d.]+)\s*dB"),
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="04m_caption_numbers.py")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)

    v = collect()
    OUT.write_text(json.dumps(
        {k: {"value": val, "source": src, "figure": fig}
         for k, (val, src, fig) in v.items()}, indent=2))
    print(f"{'key':<22}{'value':>12}   source")
    print("-" * 66)
    for k, (val, src, _f) in v.items():
        print(f"{k:<22}{str(val):>12}   {src}")
    print(f"\nwrote {OUT.name}")

    if not a.check:
        return 0

    text = MANUSCRIPT.read_text()
    bad = []
    for key, pat in CLAIMS:
        if key not in v or v[key][0] is None:
            continue
        m = re.search(pat, text)
        if not m:
            bad.append((key, "CLAIM NOT FOUND in manuscript", v[key][0]))
            continue
        WORDS = {"eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}
        raw = m.group(1)
        got = float(WORDS.get(raw.lower(), raw if raw.replace(".", "").isdigit()
                              else "nan"))
        want = float(v[key][0])
        if abs(got - abs(want)) > 0.051:
            bad.append((key, got, want))
    tbad, thaz = check_tables(text)
    for n, k, d in thaz:
        print(f"  HAZARD: {n} {k} {d} — anchors required, by design")
    print()
    if tbad:
        print("TABLE STRUCTURE PROBLEMS")
        for n, k, d in tbad:
            print(f"  {n:<20} {k}  {d}")
    else:
        print(f"all {len(TABLE_SCHEMA)} anchored tables match their source schema")

    print()
    if bad:
        print("CAPTION NUMBERS DISAGREE WITH SOURCE")
        for k, got, want in bad:
            print(f"  {k:<22} caption={got}   source={want}")
        return 1
    print(f"all {len(CLAIMS)} caption claims match source")
    return 1 if tbad else 0


if __name__ == "__main__":
    sys.exit(main())
