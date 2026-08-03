# HANDOFF — Paper 1, ear-emg-forward-model

Rewritten 2026-08-03. Read `CLAUDE.md` (standing decision policy), then
`paper/METHODS_LOG.md` (what went wrong and why), then `paper/OUTLINE.md`.

Repo clean, all work committed, `main` at the Sculptor-review commit.

---

## 0. 🛑 THE NOVELTY CLAIM IS FALSIFIED — read before writing anything

**HArtMuT** (Harmening, Klug, Gramann & Miklody 2022, *J. Neural Eng.*
19(6):066041, doi:10.1088/1741-2552/aca8ce) already published ~3,900 muscle
dipole/tripole sources built from **MIDA's own** muscle segmentation, fibre
directions by **PCA on neighbouring grid points** (this paper's proposed
method), as FEM leadfields on the New York Head. It asserts the same gap
verbatim before closing it. **Verified by direct fetch**, not taken from the
agent.

**What survives:** muscle as both source **and its own anisotropic tissue**,
in MIDA's native geometry, for an ear-electrode coupling question HArtMuT has
no electrodes for. HArtMuT's sources radiate through **homogeneous scalp** and
its authors say so in print. Yarici et al. 2023 is undamaged.

**Rewriting the novelty framing is Carl's**, not an agent's. The PCA
fibre-axis method must cite HArtMuT as precedent rather than claim it.
Full analysis in `paper/GAP_CHECK.md` (merged).

**One UNVERIFIED item gates a further claim.** HArtMuT sampled MIDA's pooled
`Muscle (General)` label and calls it "lower neck"; our inventory shows it
holds the suprahyoids. The public atlas is anonymised to four classes, so the
paper cannot settle it. **Load `HArtMuT_NYhead_small.mat` and read the labels
before writing any suprahyoid novelty claim.** Ten minutes.

**Useful by-catch:** Ernie Extended (Van Hoornweder et al. 2024, *Imaging
Neuroscience* 2, doi:10.1162/imag_a_00379, verified via Crossref, from
Thielscher's SimNIBS group) is neck-extended and includes muscle as a tissue.
Likely a cheaper route out of the broken neck-extension mesh than debugging
the extruded slab.

---

## 0. RUNNING RIGHT NOW — stage 3

`src/03_leadfields.py --conditions iso`, **22 solves**, background, started
2026-08-03. ~4 min each, so ~90 min. Writes `results/03_leadfields.csv`
**incrementally, one row per solve**, and is **resumable**: re-running skips
completed solves and clears partial ones. If it died, just run it again.

**Do NOT run anything memory-hungry beside it.** Free memory was 1.98 GB with
it running; a solve peaks near 12 GB.

**The anisotropic condition RAISES `NotImplementedError` by design.** It needs
a per-element conductivity tensor built from `orientation.principal_axis()`
for the `config.FIBRE_MODEL` "pca" compartments, and that is unwritten.
Falling through with the isotropic map would have produced a plausible, fake
"anisotropic" column and a Fig 4 comparing a condition against itself.
**Writing that tensor path is the next real task after stage 3.**

---

## 0a. IT'IS — CLOSED

**Carl sent the self-report on 2026-08-03.** Nothing pending unless they
reply. Repo is private and verified clean; history purged; old public repo
deleted. Do not contact anyone further.

**The cavity finding was re-checked and STANDS.** All 16 solves parsed:
14 clean, 2 warned (`cg10` air and filled, identical 11.90%, inside the
measured 11–15% benign band), **0 outside**. rho = −0.881, p = 0.004.

---

## 0. STATE — 2026-08-03, remote is LIVE

**Backed up off-machine at last.** `github.com/Somach-Systems-Inc/ear-emg-forward-model`,
**PRIVATE**, `main` pushed. Verified after push: **0** `.geo` in the remote
tree, **0** `.msh`/`.nii`, **no blob over 2 MB**, allowlist hook present.
Local history carries **0** `.geo` additions.

The licensing incident is closed operationally: the old public repo was
deleted, history purged with `git filter-repo`, and the repo recreated
private. Pre-purge commit hashes resolve via `paper/COMMIT_MAP_PRE_PURGE.txt`.
**Still open and Carl's alone:** whether to self-report to IT'IS. Licence
clause 5 terminates the agreement with immediate effect on breach, which meets
his own "revisit if strongly worded" condition. Do not contact anyone.

Local backups `/Users/carl/ear-emg-backup-20260803.tar.gz` and
`~/Documents/ear-emg-backups/` (md5 `85ef361856a9afb91a3f428f6f72fdee`) can be
retired now that the push is verified, but they bundle `.git` so they carry
licensed blobs: delete them or keep them local, never sync them.

**Two agents were running at handoff** in worktrees `../gap-check`
(`carl/gap-check`, owns only `paper/GAP_CHECK.md`) and `../bench-scripts`
(`carl/bench-scripts`, owns only `bench/`). Check their branches for
committed work; merge only if file ownership held and nothing was fabricated.

---

## 0b. ⚠️ STAGE 3 NEEDS A SCRIPT WRITTEN FIRST

**`src/03_leadfields.py` DOES NOT EXIST. Neither does `src/04_analyze.py`.**
CLAUDE.md's pipeline table lists both as though they do. Stage 3 is therefore
"write the production driver", not "run it". What exists is the machinery it
should compose: `run_solves_parallel.py`, `solve_invariants.py`,
`preflight.py`, `orientation.py`, `roi_corridor.py`, and the four `03a`–`03d`
one-off experiments.

Requirements for `03_leadfields.py`, all pre-committed elsewhere:

- 24 positions from `results/02_electrode_positions.csv`; `throat_scm` is
  `verified=held` with blank coordinates and every consumer must skip it
- **both** anisotropy conditions (isotropic, anisotropic per
  `config.FIBRE_MODEL`)
- the **truncated** mesh `mida_headneck.msh` (see section 1)
- invariants 1 and 2 on **every** solve; 3 and 4 on first and last, plus any
  solve whose invariant-1 CV is elevated (`solve_invariants.needs_escalation`)
- expect CV escalation to fire often. The band was calibrated on n=4 solves
  varying only σ_air, on one mesh and one montage. **Recalibrate from the
  first 10 stage-3 solves and record as calibration 2 with its own n,
  ALONGSIDE the first, never overwriting it.**
- `python src/test_guard_coverage.py --strict` must pass before it runs, and
  the new script must itself pass that test
- serial, ~3 h, authorised. Threads are settled and unavailable. Budget
  ~12 GB per solve and re-measure free memory at launch.

### Truncation sensitivity — costs nothing, do it in stage 4

Report the jaw-versus-ear gap **twice**: once with all jaw sites, once
**excluding `hyoid`, `submental_lat` and `submental_mid`**, the three within
10 mm of the cut face. Same solves, different subset.

If the gap survives the exclusion, that is a one-line answer to the obvious
reviewer objection that the truncation flatters the headline. If it does not
survive, **that must be known before any Discussion is written.**

Also emit **each electrode's clearance to the cut face as a column beside its
sensitivity**, so per-site exposure is visible rather than argued.

---

## 0. OPEN INCIDENT — licensed data was public; remote is private, awaiting Carl

**2026-08-03: `github.com/Somach-Systems-Inc/ear-emg-forward-model` was PUBLIC
for ~11.5 hours** (created 04:59:57Z, private 16:31Z) carrying **109 `.geo`
files at ~22.9 MB each**, each the full MIDA head surface.

**Dissemination appears nil:** 0 forks, 0 stars, 0 watchers, 0 clones, 0
unique cloners, 0 views, 0 unique visitors across the whole window.

**Done:** repo set to **private**, verified. Local history purged
(`git filter-repo --path-glob '*.geo' --invert-paths`); 0 `.geo` additions
remain in local history, `.git` went 23.11 → 10.64 MiB.

**NOT done, and it is Carl's call:** the remote is private but its history
still holds the 109 files. Either **delete and recreate the repo private,
then push the purged history** (removes the objects; cheap here because
nobody cloned it), or **force-push** (interim only: old objects persist
unreachable-but-fetchable-by-SHA until GitHub GCs). **Nothing was pushed**,
because a force-push would look clean while leaving the objects there.

Backups verified before any of this: `/Users/carl/ear-emg-backup-20260803.tar.gz`
and a copy in `~/Documents/ear-emg-backups/`, md5
`85ef361856a9afb91a3f428f6f72fdee`, 2,213 entries, zero `.geo`/`.msh`/`.nii`/`data`.
**Keep both until the remote is settled.** They bundle `.git`, so they carry
licensed blobs: keep them local, never in iCloud/Dropbox.

The external drive copy failed on macOS TCC, not permissions. Carl can run:
`cp /Users/carl/ear-emg-backup-20260803.tar.gz /Volumes/T7_MAC_BACKUP/`

Commit hashes recorded before the purge resolve via
`paper/COMMIT_MAP_PRE_PURGE.txt`; see the note atop METHODS_LOG.

**Still blocked behind this:** the `gap-check` and `bench-scripts` worktrees.

---

## 0b. ORIGINAL LICENSING FINDING (kept for context)

**MIDA-derived geometry is in git history.** SimNIBS writes
`<mesh>_el_currents.geo` into every solve directory, and each is **not** an
electrode patch: 126,945 triangles, 63,582 vertices, bounding box
194.6 x 255.8 x 253.4 mm — the **entire MIDA head and neck surface**, ~23 MB
each. **255 were tracked, 3.26 GB, 261 additions across history.**
`.gitignore` did not exclude `*.geo`.

MIDA is licensed by the IT'IS Foundation. Publishing this redistributes it.

Done: `*.geo` is now ignored (reason inline) and all 255 removed from the
index. That stops future commits carrying more. **It does NOT remove them
from history.**

**Remediation, then the push is safe:**

    git filter-repo --path-glob '*.geo' --invert-paths

Nothing is lost; `.geo` is regenerated by every solve. A history rewrite on
the only copy of the project is destructive and was NOT done unilaterally.

**Exposure so far is zero** — there is no remote. Best possible time to catch
it.

**Blocked behind this:** creating the private
`Somach-Systems-Inc/ear-emg-forward-model` remote, and the `gap-check` and
`bench-scripts` worktrees (explicitly gated on the remote existing so nothing
new is created on an unbacked-up repo).

Clean and not implicated: `.mat` session files (parameters only),
`medians.npy`, `results/01_label_inventory.csv` (metadata, not geometry).

---

## 1. BOUNDARY DISPOSITION — SETTLED, and stage 3 is UNBLOCKED

**The truncated mesh `mida_headneck.msh` is PRIMARY for every published
result.** Settled 2026-08-03 under the pre-committed two-hypothesis stopping
rule; both hypotheses are spent and no further repair will be attempted.

The extended mesh **does not conserve charge**. Both electrodes sit above the
cut, so any plane below both must carry zero net current; it carries
**1.07–1.64 mA against a 1 mA injection**, and planes *between* the electrodes
carry 1.59–1.61 mA where they must carry 1.00.

- hypothesis 1, coarse elements at the slab interface: **FALSIFIED** by the
  `above_ear` probe (identical 100.49% at 130 mm and at 8 mm)
- hypothesis 2, non-insulating inferior boundary: **CONFIRMED as a
  conservation violation**, not cleanly separated from plain non-convergence

**The 1.0 dB rule is recorded UNEXECUTED — not applied, not revised, not
dropped.** The truncated mesh is primary *by default, not by test*, and
OUTLINE says so. The inferior boundary is an **unquantified** limitation whose
bias direction is stated: it inflates `hyoid` (8.0 mm), `submental_lat`
(8.4 mm) and `submental_mid` (9.7 mm) while every ear site sits 80 mm+ away,
so it **flatters the paper's own jaw-versus-ear headline**.

Invariants 1 and 2 are now wired into `03a`. They had never run; invariant 2
is exactly the unconserved-current test that would have caught this.

---

## 1b. NOTHING IS RUNNING

No solves in flight. The cavity run (16 solves) and the boundary run (3) both
completed.

---

## 2. THE BLOCKER — read before starting anything

**Stage 3 cannot start.** The boundary run decides which mesh is primary for
every published result, and **its verdict is withheld**:

| solve | calibration |
|---|---|
| truncated | clean |
| extended, slab 0.355 | **WARNED 100.49%** |
| extended, slab 0.190 | **WARNED 95.84%** |

It printed "extended mesh becomes PRIMARY" from an 8.66 dB shift. Do not act
on that. ~100% is not the measured 11–15% false-positive band, the fields
corroborate it (SCM moves 2.7x), and the dB pattern is the wrong shape for a
boundary artefact (temporalis moves +3.96 dB and is nowhere near the cut).

**Measured cause candidate.** The extended mesh has only **0.83% more
elements** than the truncated one (15,542,772 vs 15,415,273) despite adding a
70 mm extrusion of a full neck cross-section. The slab is meshed roughly an
order of magnitude coarser than the head it attaches to, and a large
element-size jump across a shared interface wrecks an iterative solve.
Conductivity conditioning is excluded (σ span 1.879e6, identical to the clean
truncated run).

**Interface TESTED 2026-08-03 and it is CONFORMING** — zero duplicate
coordinates, 1,255 planar faces shared by two tets. The slab is merged and
the extrusion method is not wrong, so **refining is a legitimate repair**.
Also disproved: the sub-plane volume being 78% tag 50 (Background/air) looks
like a labelling bug but is correct, since the neck is only ~22% of the slice
and the rest is the air around it.

**Remaining hypothesis, NOT proven:** the slab holds ~27,683 tets for roughly
600,000 mm3, about 22 mm3 per element against the head's ~0.4 mm3 — a **~4x
linear element-size jump sitting directly beneath the `hyoid` injection
electrode**, which is only 8 mm above the cut plane.

**Next action:** rebuild `data/mida_neckext.msh` via `src/01c_extend_neck.py`
with the slab refined toward adjacent head element sizes, re-run
`src/03a_boundary_run.py`, and confirm both extended solves report clean
calibration. Clean calibration is the confirmation of the hypothesis. Only
then apply the rule.

**The 1.0 dB threshold is NOT revised.** Nothing failed it. What is missing is
a trustworthy number to apply it to.

---

## 3. SETTLED THIS SESSION — do not re-litigate

### Threads are not available. Process pool only.
Tested three ways, all negative. `fem.tdcs`'s `n_workers` is a
**multiprocessing** pool (10.8 GB per worker, not free), and it is clamped by
`n_workers = min(len(currents) - 1, n_workers)`, which is **1 for every
bipolar montage in this paper** regardless of what you pass. Neither
`libpetsc` nor `libHYPRE` has a single undefined OpenMP symbol, and
`OMP_NUM_THREADS=8` measured 7.3 s against 7.2 s at one thread. **Do not spend
time here again.**

### Memory
Budget **~12 GB per solve on either mesh** (observed peak 11.9 GB). The two
meshes differ by under 1%, so the extended mesh introduces no memory problem
— but if the slab is refined to fix the blocker above, **both element count
and peak RSS rise, so re-measure.**

Free memory swung 0.5 GB → 15 GB across sessions with no deliberate action
(ollama's model server exits on an idle timeout). **Measure at launch, choose
N from that, never from a figure recorded earlier.** Do not stop or modify
ollama or any other process; work inside whatever is free.

### The electrode-meshing floor is 0.27 dB
n=6, per-site, common mode removed. The statistic is the **mean over 16
electrodes of the per-electrode SD across 6 draws**. **95% CI [0.17, 0.65]**
(chi-square, df=5). An earlier bootstrap interval of [0.16, 0.28] is
**withdrawn**: resampling 6 draws with replacement leaves only ~4 distinct
draws and duplicates shrink a spread statistic, so it described a
downward-biased estimator, which is why the point estimate sat at its top
edge. Written to
`results/electrode_meshing_floor.txt`; every consumer reads it from there
(`03a`, `03b`, `03c`). `measure_electrode_floor.py` now refuses to overwrite
it and exits 3.

The old **0.1310 dB was not wrong in method, it was under-sampled**: one
pairwise difference of 1.52 pp drawn from a spread whose SD is 4.61 pp, so it
landed low by ~3x. The n=6 harness reproduces its exact input (identity
rotation gives median MAG +5.996, RDM 4.111, matching `e10mm_medium.csv`).

### MAG is disposed of
Under pure re-triangulation with geometry held exactly fixed, **MAG's spread
is 44x RDM's and MAG changes sign**. Keep reporting MAG (reviewers expect the
pair) but state what its variance measures. RDM carries the headline.

---

## 4. THE CAVITY RESULT — SURVIVES

All 16 solves done, analysed with `03c` (**not** `03d`'s printed verdict,
which is superseded and now says so in its own docstring).

    (a) Spearman rho = -0.881, p = 0.004    PASS
    (b) max |residual| = 1.6006 dB (hyoid)  PASS
    VERDICT: SURVIVES

**Flip point 1.60 dB.** All three floors ever used (0.43, 0.131, 0.27) agree,
so no choice of floor decides this. Residuals are monotone and physically
coherent: near sites lose signal when the cavity is filled, far sites gain
slightly, crossing over between `submental_lat` and `midjaw`.

**Methods term, independent of the verdict:** head models omitting the oral
cavity and nasopharynx are off by **0.507 dB** in absolute lead field.

**State this caveat with the result.** Leave-one-out survives all eight
deletions, but the (b) margin is carried by `hyoid`. Drop it and the largest
residual is `buccal` at 0.350 dB, clearing the measured floor by only 1.29x
**and the drop-hyoid fallback does NOT hold.** 0.350 dB clears the 0.27 dB
point estimate, but the floor's own 95% CI reaches **0.65 dB**, and 0.350
sits below that upper bound. A fallback that survives only against the point
estimate of a quantity known to within a factor of two is not a fallback.
(An earlier report additionally mis-stated this as failing the *retired*
0.43 dB floor; that comparison was against a threshold this paper no longer
uses.)

**So the magnitude criterion rests on `hyoid` alone** — and `hyoid` is the
site nearest the unresolved truncation face.

**The verdict is PROVISIONAL.** `hyoid` is simultaneously the site nearest the
oral cavity (14.5 mm) and nearest the truncation face (8.0 mm) whose model is
currently broken. **Re-run the correlation once a trustworthy extended mesh
exists.**

`cg10` warned at 11.90% in **both** air and filled, identically, so it cancels
in the pair ratio. Excluding it leaves the verdict unchanged.

**Fig 7's replacement is now licensed but NOT written.** The framing is
Carl's decision per `CLAUDE.md`.

---

## 5. QUEUED

- **3c. Fig 5 floor propagation.** Still blocked: needs the stage-4
  sensitivity matrix, which does not exist. Perturb each lead field by the
  measured per-site noise, recompute column correlations N times, report each
  correlation's uncertainty. `r = 0.95 ± 0.01` and `r = 0.95 ± 0.15` are
  different claims.
- **Paired noise floor.** Registered, deliberately not acted on. The cavity
  test compares filled against air *at the same electrode on the same mesh*,
  so contact realisation is identical in both halves and cancels to first
  order. The true floor for a paired dB shift is **smaller** than 0.27 dB,
  making the criterion conservative. Measure it (solve one electrode twice
  identically, or air against air) in a session where **no verdict is waiting
  on it** — lowering a floor while a hypothesis is live is the prohibited
  ordering.
- **Stage 3 config** unchanged: 24 positions (`throat_scm` still `held`, no
  coordinate, consumers skip it), both anisotropy conditions, invariants 1
  and 2 every solve, 3 and 4 first and last. Expect CV escalation to fire
  often; recalibrate from the first 10 solves and record as calibration 2
  **alongside** the first, not overwriting it.

---

## 6. TWO DECISIONS WAITING ON CARL

See `paper/SCULPTOR_REVIEW.md`.

1. **The figures workspace is held** because it modified `.gitignore`, outside
   its declared ownership. The change itself is sensible (it stops MOCK
   artifacts being tracked as real). One-line approval merges it.
2. **This repo has no git remote.** No `gh pr` path exists for held work, and
   nothing here is backed up off this machine. Creating and pushing a
   repository is outward-facing, so it was not done unilaterally.

Also flagged: `figures/mock_data.py` carries a synthetic placeholder
coordinate for `throat_scm`, the one electrode held blank pending Carl's own
neck measurement. Contained to mock data and clearly labelled, but it is the
only place in the repo where a number stands in for that measurement.

---

## 7. STANDING

Adversarial pass at every stage boundary. Pass #3 ran this session on the
floor measurement and hit twice: false precision in my own `0.272` (fixed with
a bootstrap CI), and the paired-cancellation issue above. Tag claims
`measured|derived|asserted` and attack `asserted` first.

Nothing in Discussion / Introduction / Abstract may be written. Those framing
decisions are Carl's.
