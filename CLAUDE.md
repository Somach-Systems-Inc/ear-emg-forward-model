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

**A guard is not validated until a SYNTHETIC input has made it fire in
isolation, with every other guard in the chain passing.** A real known-bad case
is not sufficient and this was proved the expensive way: invariant 2 had one —
the extended mesh leaking 1.07 mA of a 1 mA injection — and was still never
demonstrated, because that mesh also destroys the radius plateau, so invariant
1 raised first and invariant 2 never executed. An end-to-end case that trips
several guards lets the first mask the rest, and no amount of running it
reveals which ones work. `src/test_guards_fire.py` holds one synthetic case per
guard, each failing that guard and nothing else, plus a clean control that must
trip none. It runs in seconds in the plain venv, with no solve and no MIDA
geometry. Run it before any production run.

This property is also the only automatic detector of an *unreachable* guard.
`test_guard_coverage.py` resolves whether a guard is CALLED; it cannot see that
a called guard sits after another guard's raise. A synthetic case that must
make one guard fire alone does see it.

**Verifying that a step is absent HERE does not verify that it is absent.**
Check upstream before concluding a specification was not applied. A pipeline
stage is a property of the pipeline, not of the file you happen to be reading.

This is the mirror of the rule above and it cost a full retraction on
2026-08-06. I checked whether `04h_matched_counts.py` divided by measured
delivered current, found it did not, and reported that the renormalisation had
been skipped. `04d_orientation_sign.py` had already applied it at line 123 and
stored the divided arrays under the keys 04h reads. The "fix" double-applied it,
moved ten muscle gaps by up to 1.04 dB and the placement advantage by 0.67 dB,
flipped a montage verdict, and reached the Abstract, four Results and Discussion
sections, both copies of Table 4 and the README before it was caught.

**Carl instructed the fix, and that is not what made it wrong.** He approved a
diagnosis I supplied, from a summary, without either of us asking where else the
step could have run. An instruction that inherits a bad diagnosis carries the
bad diagnosis. Approval settles what to do; it does not certify the finding that
motivated it, and "you told me to" is not a defence for a check I did not run.

Two things should have raised suspicion and did not. The errors were ~1 dB,
exactly the size the renormalisation genuinely is, so they looked plausible. And
the result was tidier than the truth — a headline failing on two independent
axes that agreed. **A correction that makes the story neater is the one to check
hardest, not the one to ship fastest.**

Before reporting that a specification was not applied, name the file where it
WOULD have been applied and show it is not there either.

**Never target an edit to the manuscript by its content.** No regex on row
labels, no "replace the line that starts with `| temporalis |`", no search for
text that looks like the table you mean. Address a block by NAME through
`src/manuscript_blocks.py`, which writes only between that block's
`<!-- TABLE:name -->` anchors and raises if the anchor is missing or duplicated.
It deliberately has no fallback search.

A content-addressed edit lands in every block that shares the pattern. On
2026-08-06 a row-label regex overwrote §3.3's fat-contrast table with Table 4's
rows, twice, because both tables have a `| temporalis |` row and I believed the
document held two copies of Table 4. It never did.

**Both times I reported it as a safeguard** — "rebuilt from the CSV rather than
edited by hand". Generating from source is right and says nothing about where
the output lands. The corrupted table traced perfectly to a real source file and
every number in it was real; they were the wrong table's numbers in the right
table's place. **Provenance checking cannot see this class of error, so it must
be made structurally impossible instead.**

**Orphan number.** A magnitude in prose or a caption that matches no cell in any
results file. Checks that verify known claims against source cannot detect one,
because the claim is not in the manifest. Detection requires the reverse sweep:
enumerate every number in the prose and require each to name a source. Finding
one invalidates the assumption that the surrounding paragraph was ever generated
from data.

**Section with no generating script.** §3.4 is the fourth artifact found this
way. The first three were single artifacts; this is a whole section, and its
numeric content was never retained. The stop-rule was written for artifacts and
did not trigger on a section, because nothing checked whether Results *prose* had
a source at all -- only whether named tables did. **The sweep is per-section, not
per-table.**

**Asserted constant governing selection.** Worse than a reported orphan. A
constant that sets a filter or threshold, appears in prose or as a bare literal,
and is not derived from the data silently determines which data enters every
downstream result. All consumers agree with each other because all inherit the
same value, so internal consistency is evidence of nothing. **Any scalar that
governs inclusion, exclusion, or thresholding must be derived in code and emitted
to a results file, or it is not admissible.**

`CUT_FACE_S = -116.2` in `02c_placement_acceptance.py` is the worked example. It
sets the near-cut exclusion set, which sets the jaw site list, which sets every
matched-count gap in Table 4. It is a bare literal. The mesh has **no planar face
at that coordinate or any other** -- node counts taper smoothly from ~4000/mm at
S = -111 to 78 at the -122.17 minimum, with nothing distinguishing -116.2 from
its neighbours. Being in code made it look derived, which is why the first grep
for it (`config.py` only) reported it absent from the codebase entirely.

**A verification check confirms a specification was APPLIED. It cannot confirm
the specification was CORRECT.** Fidelity and correctness are separate channels
and need separate tests. Passing one says nothing about the other.

The case that established this: the anisotropy tensor was verified by reading
the `ElementData` back off the mesh and asserting the eigenvalues were
0.4/0.1/0.1 along the intended axis. It passed at |dot| = 1.0000 — **on a PCA
axis that was the bilateral left-right separation between the paired muscles,
not the fibre direction along either.** The check was working perfectly. It
confirmed that the tensor SimNIBS received was the tensor requested, and it had
no way to know the request was anatomically backwards. What caught it was
reading the numbers and knowing that sternocleidomastoid does not run
ear-to-ear.

So for every check, ask which channel it covers, and say so in its docstring:

- **fidelity** — "the value I asked for is the value that arrived". Cheap,
  mechanical, and blind to the value being wrong.
- **correctness** — "the value I asked for is the right value". Needs an
  independent expectation: an analytic solution, a symmetry the answer must
  obey, a control condition, or a physical fact about the world.

A fidelity check without a correctness partner is not wrong, but it must be
**labelled fidelity-only** so nobody reads its green tick as validation.

**Audit, 2026-08-04.** Every verification in this repo, by channel:

| check | channel | correctness partner |
|---|---|---|
| tensor eigenvalue readback | fidelity | **bilateral mirror-symmetry test** (paired axes must mirror in x) — added after the failure above |
| `03e` per-side PCA axis | correctness | mirror symmetry + elongation; refuses `mentalis` at \|dot\| 0.215 |
| aniso solve units (×1000) | correctness | the eight **non-tensor compartments as a control** — they must return at ratio ~1.0 |
| `test_guards_fire.py` | correctness | each guard must fire in isolation AND a clean control must trip none |
| `test_guard_coverage.py` | **fidelity-only** | it resolves that a guard is *called*; `test_guards_fire` is its correctness partner |
| `same_discretisation()` | correctness | compares sorted coordinate sets, not counts |
| invariant 1 plateau | correctness | radius-independence is a physical requirement |
| invariant 2 outer net | correctness | charge conservation; **support** is a separate fidelity check (`invariant_2_coverage`) |
| `conductivity_map_covers_mesh` | fidelity | reserved-range collision check is its correctness partner |
| analytic sphere (pre-flight) | correctness | closed-form solution |
| `anonymise_head()` + `assert_anonymised()` | **fidelity-only** | correctness partner is **rendering the figure and looking at it** — the first crop passed its own point count and left the profile legible |
| allowlist pre-commit hook | correctness | it is an allowlist, so unknown formats fail closed |

**And read the docstring of the thing you are about to reuse.**
`orientation.split_sides()` carried a warning about this exact failure —
*"Running PCA on that directly measures the left-right separation between two
muscles, not the fibre direction along either — it reported sternocleidomastoid,
the textbook strap muscle, as a plate"* — and the new tensor builder did not
call it. That is the same shape as the SimNIBS calibration reversal, where three
sessions of statistics ran against a quantity whose definition was one function
away and nobody opened the source. **Both cost days. Both were one file away.**

**Evaluate every guard, then raise once with all failures.** Fail-fast is right
for a cheap precondition (the conductivity-span gate, which runs before a
4-minute solve) and wrong for a diagnostic. `solve_invariants.GuardChain` is
the shape: collect verdicts, record a guard that could not be evaluated as
ERROR rather than skipping it, raise once. A skipped guard reads exactly like a
passing one.

Record the known-bad case beside each guard:

| guard | known-bad case it was shown to fire on |
|---|---|
| `.githooks/pre-commit` | staged 500-byte `.geo` (extension), staged 4.6 MB `.csv` (size) |
| `preflight.check_conductivity_range` | σ span 1.879e15, the air-at-1e-15 failure; synthetic, and passes on the 1.879e6 span that worked |
| `preflight.read_calibration` | synthetic `fields_summary.txt`, returns 11.90 not the 10 threshold, and `None` (not 0.0) when clean |
| invariant 1 plateau | synthetic dipole scaled by radius: flux rises instead of holding |
| invariant 1 magnitude | synthetic dipole at 0.2x: plateau exact, delivered current a fifth of requested |
| invariant 2 outer net | **DEMONSTRATED SYNTHETICALLY 2026-08-03** — monopole: radius-stationary flux *and* nonzero net outer-boundary current, no solve. **A REAL known-bad case is still owed:** with the correct conductivity map it does NOT fire on the extended mesh (−0.0038 × injected). An earlier claim that it fired there at −0.310 came from the neck slab being read as electrode rubber; retracted |
| invariant 2 coverage | shell pushed to 1.6 × p99 on a clean solve: 0% support, net exactly 0.0, which the net test alone reads as "charge conserved" |
| invariant 2 unknown tags | synthetic tag with no conductivity outside every patch radius |
| invariant 3 linearity | synthetic 2.5x pair |
| invariant 4 reciprocity | synthetic −1.01x pair |
| `test_guard_coverage` | found `03b` missing all three guards, `03d` missing two, and invariants 3/4 called by nothing |
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

**A geometric quantity that cannot be regenerated from a clean checkout cannot
be defended in Methods — and that includes fibre directions, not just electrode
coordinates.** §2.3 applied this standard to electrode placement and rejected an
interactive picker for it. It was never applied to the other class of geometric
input, and it cost two retractions.

Both were assertions about temporalis geometry, both were mine, and both
flattered the result:

1. "The flip cone is anatomically unreachable, because temporalis fibres run in
   the sagittal plane with negligible medio-lateral component." **Derived from
   MIDA: median |R| = 0.331**, against a cone requiring |R| ≥ 0.324. Reachable.
2. "Temporalis favours the ear independent of fibre direction." **Derived: 91.5%
   of the fan, not all**, and the physically correct per-voxel gap is −1.15 dB
   against the −2.57 dB the uniform sweep gave.

The second retraction then failed the matched-count test and cost the paper its
last ear result. **Deriving the quantity took one script and seven minutes.**
The assertion had stood for two days and was load-bearing for the headline.

So: if a direction, an axis, a landmark or a distance enters a calculation,
derive it from the labelled volume and record the derivation. "It is a fan from
the temporal fossa to the coronoid process" is a textbook fact and not a
measurement of *this* anatomy.

**After correcting any computed quantity, GREP for the prose that described the
old state.** Data corrections propagate through the pipeline automatically; the
sentences describing them never do. Review item 20 is the worked example: the
delivered-current term was corrected in Methods, regenerated through every
downstream number, and left Table 3 row 8 still reading "bounded by row 6" —
with every number in that row correct. The audit found it by grep, not by
reading.

**Wording supplied by Carl carries placeholders for every number, keyed to a
source file. Do not transcribe numbers out of prose — fill them from source.**
Where a supplied number and its source disagree, **source wins, and you report
the discrepancy rather than applying the supplied value.** "Approved" means the
wording is approved; it does not certify the arithmetic, because the prose was
written from an agent's report and inherits whatever that report got wrong.

Three errors in supplied wording have been caught this way — a mislabelled
cascade row, a duplicated pipeline stage, and a labial range read off a table
that had silently skipped renormalisation. Each was approved. Each was wrong.
A fourth will not be caught if numbers are copied rather than derived.

The same applies to any table with no generating script: `04h_matched_counts.csv`
was produced interactively, could not be regenerated from a clean checkout, and
drifted out of step with Methods until it reached three published numbers. **If a
published table has no script, it is not a result yet.**

**Never fabricate a number.** If a solve hasn't run, the result is unknown. Write `TODO` or `None`, not a plausible-looking value. This is a paper; an invented figure is misconduct, not a placeholder.

**Never stamp a date from your own sense of the date. Read it from `date -u +%Y-%m-%d`.** Every date in a log entry, a commit message, or a wording file comes from that command, in UTC.

On 2026-08-05 twelve occurrences of `2026-08-06` were found across nine tracked files, one day ahead of every commit that carried them and ahead of both UTC and local time. Four read "approved by Carl 2026-08-06" and attributed an approval to a date that had not yet happened; Carl did not recall giving it, and all four are now marked UNVERIFIED. The batch that was *correct* — the `2026-08-05` files, committed late evening Pacific on 08-04 — was correct precisely because those stamps were UTC. A date is a measurement. Take it from the instrument.

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

### Interim statistics
- **Any statistic quoted before its data set is complete must carry its `n` and
  an explicit `INTERIM` label.** Not "the correlation is −0.322, n.s." but
  "INTERIM, n=18 of 22: −0.322, p = 0.193". A statistic without its n reads as
  final, and a reader cannot tell that it is still moving.
- Worked example, and it moved in the direction that mattered. The correlation
  between SimNIBS's calibration warning and true delivered-current error was
  quoted as **−0.322, p = 0.193, not significant** on the 18 solves then
  complete. On the full 22 it is **−0.425, p = 0.048** — significant, and more
  damning: the check is not merely uncorrelated with the error it claims to
  measure, it is significantly *anti*-correlated. Quoting the interim figure as
  final would have understated the case against it.
- A statistic with a free parameter must state the parameter, not just the
  number. "The two agree on 4 of 22 solves" reproduces only at an unstated ±5
  percentage-point tolerance, and becomes 9 of 22 at ±6 pp. Numbers that sit on
  a cliff of an undeclared choice do not go in front of a reviewer without the
  choice attached.

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
