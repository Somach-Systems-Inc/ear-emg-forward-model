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
    ("masseter",                "mastication",  None,  "STRONG - 1-2 cm anterior to tragus"),
    ("temporalis",              "mastication",  None,  "STRONG - directly above ear"),
    ("medial_pterygoid",        "mastication",  None,  "moderate - deep"),
    ("lateral_pterygoid",       "mastication",  None,  "moderate - deep"),
    ("orbicularis_oris",        "labial",       None,  "weak - far anterior"),
    ("buccinator",              "labial",       None,  "moderate"),
    ("mentalis",                "labial",       None,  "weak"),
    ("depressor_anguli_oris",   "labial",       None,  "weak"),
    ("platysma",                "cervical",     None,  "moderate - broad sheet"),
    ("sternocleidomastoid",     "cervical",     None,  "STRONG - mastoid attachment (but low speech activity)"),
]

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
