# Reproduction

**This repository ships code, not data.** The MIDA head model is licensed by
the IT'IS Foundation and cannot be redistributed here, so nothing in `data/`
is tracked and every mesh must be rebuilt locally from your own copy.

---

## 1. Obtain MIDA yourself

**MIDA v1.0**, DOI [10.13099/ViP-MIDA-V1.0](https://doi.org/10.13099/ViP-MIDA-V1.0),
from the IT'IS Foundation Virtual Population. It is free apart from a handling
fee (CHF 5) and requires individual registration. Download it manually; do not
attempt to script the download.

Place the voxel distribution so that this path exists:

    data/MIDA_v1.0/MIDA_v1_voxels/MIDA_v1.nii

The pipeline reads the label volume from there. `data/` is git-ignored in
full.

### What the licence requires of you

Read *Terms and Conditions of User License MIDA Model v1.0* yourself; the
download does not include it. The clauses that shape how this repository is
built:

- **2.3.2** — the Model Data *or works derived from it* must not be
  distributed in original, modified or updated form. **This covers meshes and
  exported surfaces, not just the voxel volume.** It is why `data/`, `*.msh`,
  `*.nii` and `*.geo` are all excluded, and why the pre-commit hook below is
  an allowlist.
- **2.3.3** — any published image based on the Model Data must have **the face
  disguised so the individual is unrecognizable**. This applies to papers,
  preprints, posters and talks. Crop or mask before publishing any render of
  the skin surface.
- **2.3.1** — derivative works must carry notice that they are derived from
  the MIDA Model. The meshes this pipeline builds are derivative works.
- **2.3.8** — publications must credit the **FDA, Center for Devices and
  Radiological Health, and the IT'IS Foundation** as creators, and cite
  Iacono et al., *PLoS ONE*, March 2015.

## 2. Enable the pre-commit hook

Git does not clone hooks, so this is required once per clone:

    git config core.hooksPath .githooks

It is an **allowlist**: it rejects any file extension not explicitly
permitted, and any file over 2 MiB. It exists because a denylist (`.gitignore`)
already failed open once and let 255 files of MIDA-derived surface geometry
into the history. Adding a new file type is a deliberate edit to
`.githooks/pre-commit`.

## 3. Environment

- **SimNIBS 4.6**, native Apple Silicon build, at
  `~/Applications/SimNIBS-4.6/`. Run solver scripts with its bundled
  interpreter: `~/Applications/SimNIBS-4.6/bin/simnibs_python`.
- A separate `.venv` for analysis that needs `mne` (the two interpreters are
  deliberately split; `val_rdm_mag.py` and `measure_floor_multidraw.py` each
  run in two phases because of it).

Verify the environment before trusting any solve:

    python src/preflight.py --strict

## 4. Run the stages in order

| stage | command | produces |
|---|---|---|
| 1 | `simnibs_python src/01_build_mesh.py` | tetrahedral mesh with muscle compartments |
| 1b | `simnibs_python src/01b_validate_mesh.py` | label verification against `config.py` |
| 1c | `simnibs_python src/01c_extend_neck.py` | neck-extended mesh for the boundary test |
| 2 | `simnibs_python src/02_place_electrodes.py` | electrode coordinates on the skin surface |
| 3 | `simnibs_python src/03_leadfields.py` | one E-field volume per montage, both isotropy conditions |
| 4 | `simnibs_python src/04_analyze.py` | sensitivity matrix, dB tables, figures |

Validation and error-budget scripts (`val_*.py`, `measure_floor_multidraw.py`,
`03a`–`03d`) are documented in their own docstrings and in
`paper/METHODS_LOG.md`.

## 5. What is not reproducible from this repository

- **The MIDA model itself.** Licensed; obtain it as above.
- **Meshes and E-field volumes.** Large and regenerable; rebuild them.
- **`*_el_currents.geo`.** SimNIBS writes one per solve. Each is the full head
  surface at ~23 MB and is **licensed derived geometry**. They are ignored and
  must never be committed.

Everything else — every number, table and figure in the paper — follows from
the tracked code plus your own copy of MIDA.
