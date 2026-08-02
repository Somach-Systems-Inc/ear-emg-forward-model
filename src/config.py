"""
Paper 1 — shared configuration.
Volume-conductor model of articulator muscle sources at retroauricular sites.

Everything the pipeline needs to agree on lives here.
"""
from pathlib import Path

ROOT     = Path(__file__).resolve().parent.parent
DATA     = ROOT / "data"
RESULTS  = ROOT / "results"
FIGURES  = ROOT / "figures"
MESH     = DATA / "mida_headneck.msh"

# ----------------------------------------------------------------------
# TISSUE CONDUCTIVITIES  (S/m, quasi-static / low frequency)
# Source: IT'IS Foundation tissue property database v4.x
# Cite these in Table 1. Verify each against the current database version
# before submission — they update.
# ----------------------------------------------------------------------
SIGMA = {
    "skin":            0.465,
    "fat":             0.025,
    "muscle_iso":      0.355,   # isotropic average, for the baseline run
    "muscle_long":     0.400,   # along fibre  -- anisotropic run
    "muscle_trans":    0.100,   # across fibre -- anisotropic run
    "bone_compact":    0.008,
    "bone_cancellous": 0.025,
    "cartilage":       0.170,
    "blood":           0.700,
    "csf":             1.790,
    "grey_matter":     0.275,
    "white_matter":    0.126,
    "eye":             1.500,
    "air":             1e-15,   # not exactly zero -- keeps the solver happy
}

# Anisotropy ratio, quoted in the paper as a single number
ANISOTROPY_RATIO = SIGMA["muscle_long"] / SIGMA["muscle_trans"]   # = 4.0

# ----------------------------------------------------------------------
# ARTICULATOR MUSCLES  -- the rows of the sensitivity matrix
#
# `mida_label` MUST be filled in after downloading MIDA and inspecting the
# label volume. See 01_build_mesh.py --list-labels.
#
# `group` drives figure ordering and the discussion narrative.
# ----------------------------------------------------------------------
# Labels below are read from MIDA v1.0 MIDA_v1_voxels/MIDA_v1.txt (116 structures),
# verified 2026-08-02 via `01_build_mesh.py --list-labels`. Integers are exact.
#
# 10 of 18 are individually segmented. The 8 with mida_label = None are NOT
# absent from the model -- they are pooled inside a larger compartment (see
# MIDA_POOLED below) and must be sub-segmented by hand. Leaving them None is
# deliberate: CLAUDE.md, "a wrong label is worse than a missing one".
MUSCLES = [
    # name,                     group,          mida_label, expected_at_ear
    ("digastric_posterior",     "suprahyoid",   None,  "STRONG - attaches at mastoid notch"),
    ("stylohyoid",              "suprahyoid",   None,  "STRONG - styloid process, adjacent"),
    ("mylohyoid",               "suprahyoid",   None,  "moderate"),
    ("geniohyoid",              "suprahyoid",   None,  "weak - anterior, deep"),
    ("digastric_anterior",      "suprahyoid",   None,  "weak - anterior"),
    ("genioglossus",            "tongue",       None,  "WEAK - deep and distant; predicts phoneme loss"),
    ("hyoglossus",              "tongue",       None,  "weak"),
    ("styloglossus",            "tongue",       None,  "moderate - styloid origin"),
    ("masseter",                "mastication",    66,  "STRONG - 1-2 cm anterior to tragus"),
    # MIDA merges temporalis with temporoparietalis in one label. The temporalis
    # tendon is separate (98) and is NOT included here -- tendon conductivity
    # differs from muscle and it is not a source.
    ("temporalis",              "mastication",    63,  "STRONG - directly above ear"),
    ("medial_pterygoid",        "mastication",    81,  "moderate - deep"),
    ("lateral_pterygoid",       "mastication",    65,  "moderate - deep"),
    ("orbicularis_oris",        "labial",         75,  "weak - far anterior"),
    ("buccinator",              "labial",         84,  "moderate"),
    ("mentalis",                "labial",         71,  "weak"),
    ("depressor_anguli_oris",   "labial",         72,  "weak"),
    ("platysma",                "cervical",       60,  "moderate - broad sheet"),
    ("sternocleidomastoid",     "cervical",       68,  "STRONG - mastoid attachment (but low speech activity)"),
]

# ----------------------------------------------------------------------
# THE SUB-SEGMENTATION PROBLEM  (resolved 2026-08-02, methods limitation)
#
# MIDA v1.0 does not individually segment the suprahyoid group or the
# intrinsic/extrinsic tongue muscles. They are pooled into two compartments:
#
#   38  "Muscle (General)"  1,975,307 voxels  246,872 mm^3
#   42  "Tongue"              521,131 voxels   65,130 mm^3
#
# This hits the strongest part of the argument directly: digastric posterior
# belly and stylohyoid anchor at the mastoid, which is exactly why they were
# predicted to dominate the retroauricular signal. They must be sub-segmented
# from label 38 by hand and reported as a limitation.
# ----------------------------------------------------------------------
MIDA_MUSCLE_GENERAL = 38
MIDA_TONGUE         = 42

# muscle name -> the MIDA label it is currently pooled inside.
# UNVERIFIED: the assignment of each tongue muscle to 42 vs 38 is anatomical
# inference, not measurement. Styloglossus and hyoglossus originate outside the
# tongue body (styloid process, hyoid) so parts of them may sit in 38. Confirm
# against the volume before sub-segmenting; do not assume.
MIDA_POOLED = {
    "digastric_posterior": MIDA_MUSCLE_GENERAL,
    "digastric_anterior":  MIDA_MUSCLE_GENERAL,
    "stylohyoid":          MIDA_MUSCLE_GENERAL,
    "mylohyoid":           MIDA_MUSCLE_GENERAL,
    "geniohyoid":          MIDA_MUSCLE_GENERAL,
    "genioglossus":        MIDA_TONGUE,
    "hyoglossus":          MIDA_TONGUE,   # UNVERIFIED: may straddle 38
    "styloglossus":        MIDA_TONGUE,   # UNVERIFIED: may straddle 38
}

# ----------------------------------------------------------------------
# ELECTRODE MONTAGES
#
# Coordinates are placeholders. Fill them by picking points on the MIDA
# scalp/skin surface -- see 02_place_electrodes.py, which opens an
# interactive picker and writes the chosen coordinates back here.
#
# Keep the names identical to the physical rig so the modelling paper and
# the empirical paper share one vocabulary.
# ----------------------------------------------------------------------
MONTAGES = {
    # Gaddy / Kapur canonical sites -- the baseline everything is measured against
    "jaw": [
        "mental",            # chin, front
        "submental_mid",     # under chin, midline
        "submental_lat",     # under chin, lateral
        "submaxillary",      # under jawline
        "hyoid",
        "throat_scm",        # over sternocleidomastoid
        "buccal",            # cheek
        "midjaw",
    ],
    # The hypothesis under test
    "ear": [
        "above_ear",         # over temporalis
        "mastoid",           # on the bone behind the ear
        "post_lobule",       # behind / below the earlobe -- digastric + stylohyoid
        "pre_tragus",        # anterior to tragus -- masseter / TMJ
    ],
    # For comparability with the ear-EEG literature (Debener 2015)
    "ceegrid": [f"cg{i:02d}" for i in range(1, 11)],   # C-path, 12-18 mm spacing
}

REFERENCE = "earlobe_contra"
BIAS      = "earlobe_ipsi"

# Physical electrode geometry -- matches the real rig
ELECTRODE_DIAMETER_MM = 10.0    # gold cup
INJECTION_CURRENT_A   = 1e-3    # 1 mA, reciprocity solve

# ----------------------------------------------------------------------
# ANALYSIS
# ----------------------------------------------------------------------
# Reference for dB normalisation in Fig 2 -- the best jaw site per muscle
DB_REFERENCE = "best_jaw_site"

# Report sensitivity as the median |E| within each muscle compartment,
# plus IQR. Mean is skewed by boundary artefacts at compartment edges.
SENSITIVITY_STATISTIC = "median"
