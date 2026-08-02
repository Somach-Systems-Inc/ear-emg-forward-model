# CLAUDE.md — ear-emg-forward-model

Read this before doing anything. Then read `paper/OUTLINE.md`.

## What this is

A volume-conductor model answering one question: **which speech-articulator muscles are electrically visible at electrode sites around the ear, and how much signal is lost versus the canonical jaw montage?**

Output is a peer-reviewable paper plus a design table other people can use. Not a demo, not a library.

**No human subjects. No IRB. No hardware.** Nothing here is blocked on anything external.

## Why it exists

Two literatures exist and do not touch. Head volume-conduction modelling (EEG/MEG/tDCS) models **brain** sources in detailed head geometry. Surface-EMG volume-conduction modelling models **muscle** sources in limb geometry. Nobody has published muscle-source dipoles in an anatomically detailed head.

The ear-EEG modelling literature says this explicitly — forward models exist for neural and ocular sources, but there is no theoretical study of *muscle* artifacts in ear-EEG.

Meanwhile hardware has moved without theory: retroauricular arrays demonstrably pick up speaking EMG (Avramidou 2024), ear electrodes classify jaw gestures >90% (An 2025), and AlterEgo's 2026 device moved to an ear-mounted form factor. Devices are being designed for a coupling nobody has modelled.

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

**Never fabricate a number.** If a solve hasn't run, the result is unknown. Write `TODO` or `None`, not a plausible-looking value. This is a paper; an invented figure is misconduct, not a placeholder.

**Flag uncertainty inline.** If a conductivity, label, or coordinate is assumed rather than verified, mark it `# UNVERIFIED:` in code and call it out in the commit message.

**Never move a threshold because something failed it.** A threshold may be revised only when an independent measurement establishes the physical bound, and the revision must be recorded inline next to that measurement. A test that is loosened until it passes is not a test.

Worked example, both directions. The hyoid depth band was specified 10–15 mm and the placement returned 19.7 mm. Revising it was legitimate *only* because a separate measurement — the hyoid's minimum distance to the skin surface taken over the entire surface, unconstrained, at 19.1 mm — established that 10–15 mm is physically unreachable in this anatomy; the band became 15–22 with that number written beside it. By contrast the 20 mm electrode-spacing floor was never revised, because nothing measured it: it was withdrawn as a gate and became a reported quantity awaiting a caliper reading (`config.COLLAR_OD_MM = None`). Withdraw an unfounded threshold; do not retune it to fit.

**A metric that stops early measures where it stopped.** The first tissue-composition table walked from electrode to the *nearest surface* of the target and reported percent-of-path, which made `midjaw` look like 3% masseter. Extending the same ray through the full compartment gave 16.5 mm of masseter, a 33x difference. Before a descriptive statistic becomes a claim, check that its integration limits are physical rather than incidental.

**Both outcomes publish.** The discussion is written so a large attenuation at the ear ("here is the dB budget, here is why it's hard") and a small one ("it should work, put contacts here") are both results. Do not tune the analysis toward either.

**Commit granularly with real messages.** This repo is public and is part of the company's credibility. `git commit -m "fix"` is not acceptable.

**Ask before restructuring.** The pipeline stages exist for a reason — 01 mesh, 02 electrodes, 03 leadfields, 04 analysis. Don't merge or reorder them without checking.

**When Carl's instructions conflict, the later one supersedes.** Flag the conflict explicitly, say which one you are following and why, then proceed. Do not block waiting for the contradiction to be resolved, and do not silently pick one. Worked example: one list said not to run the boundary experiment while a validation contradiction was open, a later list said to run it before any further validation. The right move was to follow the later ordering, state the technical reason the earlier caution mattered (the measured 0.43 dB noise floor sits close to the 1.0 dB decision threshold), and run it.

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
