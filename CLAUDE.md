# CLAUDE.md — ear-emg-forward-model

Read this before doing anything. Then read `paper/OUTLINE.md`.

## What this is

A volume-conductor model answering one question: **which speech-articulator muscles are electrically visible at electrode sites around the ear, and how much signal is lost versus the canonical jaw montage?**

Output is a peer-reviewable paper plus a design table other people can use. Not a demo, not a library.

**No human subjects. No IRB. No hardware.** Nothing here is blocked on anything external.

## Why it exists

Two literatures exist and do not touch. Head volume-conduction modelling (EEG/MEG/tDCS) models **brain** sources in detailed head geometry. Surface-EMG volume-conduction modelling models **muscle** sources in limb geometry. Nobody has published muscle-source dipoles in an anatomically detailed head.

The ear-EEG modelling literature says this explicitly — forward models exist for neural and ocular sources, but there is no theoretical study of *muscle* artifacts in ear-EEG.

Meanwhile hardware has moved without theory: retroauricular arrays demonstrably pick up speaking EMG (Avramidou 2024), ear electrodes classify jaw gestures >90% (An 2025), and AlterEgo's *Silent Sense* prototype (demonstrated September 2025) adopted a head-worn form factor around the ears. Devices are being designed for a coupling nobody has modelled.

*(AlterEgo line corrected 2026-08-03 from "2026 device moved to an ear-mounted form factor". The year was wrong and "ear-mounted" overstated the sources, which describe a device resting largely on the back of the head. It has no citable primary source and must not carry weight in the motivation. See `paper/CITATIONS.md`.)*

## The method — do not get this wrong

**Use reciprocity. Do not solve the forward problem per source.**

Inject 1 mA at an electrode pair, solve for **E** throughout the head, read the field inside each muscle compartment. Lead field for a source at **r** with orientation **n̂** is `E(r) · n̂`.

SimNIBS's tDCS solver computes exactly this. Repurpose it. That is ~20 solves total instead of one per source.

If you find yourself writing a loop that places dipoles and solves, stop — you have taken the wrong branch.

## Hard constraints

- **SimNIBS 4.6**, native Apple Silicon. Custom tissue labels are a documented feature (`meshmesh` + per-label conductivity), not a hack.
- **MIDA head model** (IT'IS Foundation), 153 structures at 500 µm. Free, requires registration. Must be downloaded manually — do not attempt to script the download.
- All conductivities live in `src/config.py`. Do not hardcode them anywhere else. They go in Table 1 with sources.
- Muscle anisotropy (0.4 S/m long / 0.1 S/m transverse) is a **deliberate two-run design**, not an optional extra. Run isotropic and anisotropic, compare, report both.

## The fork in the road — resolve this first

```bash
python src/01_build_mesh.py --list-labels
```

Find the suprahyoid muscles in MIDA's label volume: **digastric (posterior belly especially), stylohyoid, mylohyoid, geniohyoid.**

- **Individually segmented** → proceed as designed.
- **Inside a generic "muscles" catch-all** → sub-segment manually from the label volume and document it as a methods limitation. Do not silently substitute a nearby label.

Confirmed present: masseter, temporalis, pterygoids, orbicularis oris, buccinator, zygomaticus, platysma, SCM.

Fill `mida_label` in `src/config.py` with real integers once known. Leave `None` until verified — a wrong label is worse than a missing one.

## Rules for you specifically

**A check may not report "clean" until it has been shown to fire.** No guard
counts as verified until it has returned DIRTY on a known-bad case, in the
same session, before you trust a clean result from it. A check that has never
failed has not been demonstrated capable of failing.

This norm was applied to the allowlist hook (tested against a staged `.geo`
and a 4.6 MB file before being trusted) and **not** applied to a log grep,
which searched for a string the program never prints, returned zero hits, and
was reported as "run is clean". Zero hits and working-correctly are
indistinguishable without a positive control.

Record the known-bad case beside each guard:

| guard | known-bad case it was shown to fire on |
|---|---|
| `.githooks/pre-commit` | staged 500-byte `.geo` (extension), staged 4.6 MB `.csv` (size) |
| `preflight.check_conductivity_range` | σ span 1.879e15, the air-at-1e-15 failure |
| `preflight.read_calibration` | `air__cg10`, returns 11.90 not the 10 threshold |
| `solve_invariants` invariant 1 | known-bad 1e-15 solve, diverges to −8.94, no plateau |
| `solve_invariants` invariant 2 | **NOT YET DEMONSTRATED — owed a known-bad case** |
| `test_guard_coverage` | found `03b` missing all three guards, `03d` missing two |
| `render_common.anonymise_head` | first crop left the profile legible; caught by rendering and looking |

**Never publish a recognisable face.** MIDA licence clause 2.3.3: *"Any images
based on the Model Data may be published only if the face is disguised so as to
render the individual unrecognizable in any and all communications of any kind,
including but not limited to reports, papers, and oral or poster
presentations."* This binds preprints, posters and slides, not just the journal
version. Every head rendering goes through `figures/render_common.anonymise_head()`
and is gated by `assert_anonymised()`; the orbital rim is **derived from MIDA's
own eye labels** (S = 13.8 mm), never hardcoded, and the helper raises rather
than guessing if it cannot derive it. Do not add a per-figure exception: one
forgotten figure is a licence breach that is only visible after publication.

**Never commit a file type that is not on the allowlist.** `.gitignore` is a
denylist and it failed open once already, letting 255 files of MIDA-derived
surface geometry into the history and 109 of them onto a public GitHub repo.
`.githooks/pre-commit` is the allowlist; enable it with
`git config core.hooksPath .githooks`. Adding a format is a deliberate edit,
not a `--no-verify`.

**Never fabricate a number.** If a solve hasn't run, the result is unknown. Write `TODO` or `None`, not a plausible-looking value. This is a paper; an invented figure is misconduct, not a placeholder.

**Flag uncertainty inline.** If a conductivity, label, or coordinate is assumed rather than verified, mark it `# UNVERIFIED:` in code and call it out in the commit message.

**Never move a threshold because something failed it.** A threshold may be revised only when an independent measurement establishes the physical bound, and the revision must be recorded inline next to that measurement. A test that is loosened until it passes is not a test.

Worked example, both directions. The hyoid depth band was specified 10–15 mm and the placement returned 19.7 mm. Revising it was legitimate *only* because a separate measurement — the hyoid's minimum distance to the skin surface taken over the entire surface, unconstrained, at 19.1 mm — established that 10–15 mm is physically unreachable in this anatomy; the band became 15–22 with that number written beside it. By contrast the 20 mm electrode-spacing floor was never revised, because nothing measured it: it was withdrawn as a gate and became a reported quantity awaiting a caliper reading (`config.COLLAR_OD_MM = None`). Withdraw an unfounded threshold; do not retune it to fit.

**A metric that stops early measures where it stopped.** The first tissue-composition table walked from electrode to the *nearest surface* of the target and reported percent-of-path, which made `midjaw` look like 3% masseter. Extending the same ray through the full compartment gave 16.5 mm of masseter, a 33x difference. Before a descriptive statistic becomes a claim, check that its integration limits are physical rather than incidental.

**Both outcomes publish.** The discussion is written so a large attenuation at the ear ("here is the dB budget, here is why it's hard") and a small one ("it should work, put contacts here") are both results. Do not tune the analysis toward either.

**Commit granularly with real messages.** This repo is public and is part of the company's credibility. `git commit -m "fix"` is not acceptable.

**Ask before restructuring.** The pipeline stages exist for a reason — 01 mesh, 02 electrodes, 03 leadfields, 04 analysis. Don't merge or reorder them without checking.

**When Carl's instructions conflict, the later one supersedes.** Flag the conflict explicitly, say which one you are following and why, then proceed. Do not block waiting for the contradiction to be resolved, and do not silently pick one. Worked example: one list said not to run the boundary experiment while a validation contradiction was open, a later list said to run it before any further validation. The right move was to follow the later ordering, state the technical reason the earlier caution mattered (the measured 0.43 dB noise floor sits close to the 1.0 dB decision threshold), and run it.

## Standing decision policy

Apply this yourself. Do not escalate anything it already covers.

### Thresholds
- A threshold may be revised **only** when an independent measurement
  establishes the physical bound, recorded inline with that measurement.
  **Never** because something failed it.
- For any threshold-gated claim, report the value **and** the threshold at which
  the verdict flips. Never report a bare binary.

### When something can't be sourced or segmented
- **Missing landmark** → bound the consequence with geometry derived from
  structures that *are* segmented. Never fabricate the landmark.
- **Unsourceable value** → measure its insensitivity across a plausible range.
  Never defend the value by argument alone.
- An annotation that enters no calculation may cite a literature mean. An
  operand may not.

### Claims
- Tag every claim `measured` | `derived` | `asserted`. Attack `asserted` first.
  `derived` inherits the confidence of its weakest link.
- Never assert a categorical claim about anatomy. Measure the gradient and let
  the category fall out.
- Both outcomes publish. Never tune toward the interesting one.
- Never fabricate a number.

### Code
- Identify by identity (labels); threshold by physics (values, with the
  derivation recorded). Every classification test asserts a non-empty set.
- Fail loudly. Never silently zero, skip, or clamp.
- Read the tool's own output before reporting its result.
- Verify an edit landed by parsing the file, not by assuming the replacement
  applied.
- Kill a run built on a bad input rather than let it finish.

### Instructions
- When Carl's instructions conflict, the later supersedes. Flag it and proceed.

### Escalation — the part that matters
Interrupt **immediately** only for:
- a decision no rule above covers
- a falsified claim that later work depends on
- an unphysical input
- a run over ~2h not already authorised

**Everything else accumulates and is reported once, at the next stage
boundary.** Do not ping for progress, for confirmations, or for decisions this
policy already answers.

## Pipeline

| Step | Script | Done when |
|---|---|---|
| 1 | `01_build_mesh.py` | tetrahedral mesh exists, muscle compartments present, labels verified against config |
| 2 | `02_place_electrodes.py` | coordinates for all 22 positions on the skin surface, written back to config |
| 3 | `03_leadfields.py` | one E-field volume per montage, both isotropy conditions |
| 4 | `04_analyze.py` | sensitivity matrix, dB tables, Figs 1–5 |

## Figures (see OUTLINE.md for full spec)

Fig 2 is the money figure: muscles × electrode positions, colour = lead field in dB relative to the best jaw site.
Fig 5 is the deliverable other people will cite: ranked retroauricular positions by total articulator sensitivity.

## Style

- Python, `numpy`/`scipy`/`nibabel`/`matplotlib`/`pandas`. No heavy frameworks.
- Figures: vector PDF for the paper, PNG for the repo README.
- Everything reproducible from a clean checkout given MIDA in `data/`. Document any manual step in the README rather than leaving it implicit.
- Prose in the paper: no bullet lists in Results or Discussion. Journals want paragraphs.

## Relationship to the rest of the programme

This paper **predicts** what Paper 2 measures. Paper 2 is a physical 8-channel rig running a jaw-vs-ear split montage on the same utterances. The model says which sites and which muscle groups should survive at the ear; the experiment confirms or refutes it.

That pairing is the point. Keep the electrode names here identical to the physical rig so the two papers share one vocabulary.
