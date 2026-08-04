# HANDOFF — Paper 1, ear-emg-forward-model

Rewritten 2026-08-03 (evening). Read `CLAUDE.md` (standing decision policy),
then `paper/METHODS_LOG.md` from "the double reversal" down, then
`paper/OUTLINE.md`.

Repo clean, all work committed.

---

## 0-NEXT. QUEUE — updated 2026-08-04

**Done since the last handoff:** the calibration reversal (see below), figures
wired to real stage-4 output, Fig 5 rebuilt as the complementarity map, Fig 2
diverging about 0 dB, **anisotropy tensor + Fig 4 complete (22/22 solves)**, QA
re-render with `anonymise_head()`, captions and Results.

1. **RUN `paper/upstream/both_electrode_flux.py`** — artifact (b) for the
   SimNIBS thread. It was launched and **killed part-way** because it and the
   anisotropy run together drove the machine into 6.5 GB of swap. Run it alone;
   ~30-45 min, reads only, no solves. It measures the tet-patch cut flux at
   BOTH electrodes, which is the like-for-like comparison against SimNIBS's
   `a` and `b` and the thing that closes out #665's premise.
2. **Post the upstream follow-up.** Everything is prepared in
   `paper/upstream/`. **CARL POSTS, NOT AN AGENT.** #665 needs correcting, not
   defending.
3. **Mesh-quality regression** — still owed, still demoted, may be
   supplementary. Dependent variable is **delivered current**, not calibration.
4. **The two owed measurements.** (a) Solver reproducibility at fixed geometry
   — one identical montage solved twice; needed before the withdrawn 1e-6
   tolerances on invariants 3 and 4 could be gates again. (b) A real known-bad
   case for invariant 2.
5. **Make the repo PUBLIC at submission** so the pre-registration citation
   (`fa583f6`, 2026-08-02 vs the 2026-08-03 leadfield commit) is checkable.
   Safe now: history purged, allowlist hook active.

**Settled, do not reopen:** the extended mesh. Hypothesis 1 is UNTESTED, not
falsified; the disposition stands on the flux-decay probe; the mesh is unused.

---

## 0. WHAT CHANGED THIS SESSION — three bugs, one shape

All three are **a parameter reaching the instrument by a path nobody
verified**, and each turned a self-comparison or a wrong constant into a
"measurement" that was then written down.

### 1. The `above_ear` probe solved `hyoid`. Hypothesis 1 is UNTESTED.

`03a2_boundary_probe.py` called `03a_boundary_run.solve()` without passing the
montage, so `solve()` used **03a's** module-level `INJECT_FROM = "hyoid"`. The
probe's own `INJECT_FROM = "above_ear"` only ever reached print statements. It
re-solved the identical montage and produced a **byte-identical result mesh**
(md5 `b110d2ce…`).

So *"hypothesis 1 FALSIFIED — identical 100.49% at 130 mm and at 8 mm"* is one
measurement at 8 mm, reported twice. **The identical 100.49% to two decimals
was the tell and it was read as a clean result instead of an impossible one.**

- **Hypothesis 1 (coarse elements at the slab interface) is untested, not
  falsified.** "Both hypotheses spent" was wrong; one was spent.
- **The boundary disposition SURVIVES and the extended mesh is NOT reopened**
  (ruling, 2026-08-03). The truncated mesh stays primary because the extended
  mesh does not conserve charge, on the flux-decay probe, which is
  independent. The mesh is unused, the limitation is documented in OUTLINE
  with its bias direction, and **the cause is not re-litigated.**
- Fixed: montage is now an explicit parameter, printed, and `03a2` asserts the
  coordinate appears in the solver's own log before reporting a verdict.
- Re-run with the fix: `above_ear` on the extended mesh reports calibration
  **15.75%**, not 100.49%. Void run preserved under
  `results/_failed_runs/boundary_probe_above_ear_VOID_solved_hyoid_20260803/`.

### 2. Tag 200 collides with SimNIBS's electrode-rubber range

`with_electrode_tags()` fills tags 100–499 with 29.4 S/m rubber by
`setdefault`. The neck slab is tagged **200**, so any analysis map built from
Table 1 alone read 42,766 slab elements as rubber — an **83× error** on the
compartment under investigation.

**This produced a false measurement that I recorded and have retracted:**
invariant 2 reading −0.310 / −0.566 × injected on the extended mesh. With the
correct map it reads **−0.0038 and passes**. Corrected in METHODS_LOG, OUTLINE
and CLAUDE.md the same session.

Stage 3 is unaffected and this was **verified, not assumed**: the truncated
mesh has **0 tags with no conductivity**, and `03_leadfields.py` builds its
analysis map with the same function that assigns the solve's.

### 3. The invariant patch was centred on the module default too

Same defect, survived the first fix: `03a.solve()` called
`check_solve_plateau(..., pos[INJECT_FROM], ...)`. A patch centred 130 mm from
the injection contains no source, so the cut flux is ~0 at every radius and
invariant 1 fails for a reason unrelated to the solve.

---

## 0. GUARD CHAIN — collect-then-raise, and what else was dead

`solve_invariants.GuardChain`: every guard evaluated, every verdict recorded,
one raise carrying all failures. A guard that cannot be evaluated is recorded
as ERROR, never skipped.

| guard | status found |
|---|---|
| **invariant 3 (linearity)** | **no caller anywhere — never ran, ever** |
| **invariant 4 (reciprocity)** | **no caller anywhere — never ran, ever** |
| `batch_plan()` | no caller; the first-and-last-solve policy never executed |
| `needs_escalation()` | called, result printed and discarded |
| `check_solve()` | no caller, second copy of invariant 2 behind two raises — **deleted** |
| `check_solve_output()` | no caller, gates on the calibration check — **retired, now raises** |
| `solve_invariants.__main__` | `NameError` since written — never once run |

Two guards added, neither tuned to this data:

- **`invariant_1_magnitude`** (0.4–2.5 × injected), inherited unchanged from the
  deleted `check_solve()`. A uniform scale error leaves the plateau stationary
  and invariant 2 at zero, so nothing per-solve could see it before.
- **`invariant_2_coverage`** (≥2% shell support). Invariant 2's shell sits at
  1.05 × p99 node radius; on MIDA only **5.35%** of it is inside the conductor,
  and on any convex domain it is **0%** — at which point the integral returns
  exactly 0.0 and passes vacuously. Coverage was computed and discarded for the
  whole project; it is now a verdict and a CSV column.

**`src/test_guards_fire.py`** — 12 synthetic cases, each failing exactly one
guard with the rest passing, plus a clean control. Seconds, plain venv, no
solve. Invariant 2's is a monopole: radius-stationary flux **and** nonzero net
outer-boundary current. **This is also the only automatic detector of an
unreachable guard** — `test_guard_coverage.py` sees whether a guard is called,
not whether it is reachable.

---

## 0. THE 11–15% BAND IS RETIRED — and so is the band taxonomy

Void: it was derived entirely from SimNIBS's calibration check, which is
measured anti-correlated with true delivered current (Spearman **−0.425,
p = 0.048, n = 22**). Slicing a quantity that does not measure what it claims
into "benign" and "fatal" ranges gives two slices of noise.

Of the four recorded bands, only those never resting on the check survive:
**~100%** (charge leak — flux-decay probe) and **200.00%** (conditioning —
fields measured 10–20× too large). **11–15%** and **15.6–33.0%** are void.

Replaced not by another band but by a different instrument: the tet-patch
integral, whose `mean_ratio` *is* delivered current over requested. Gated only
by the loose 0.4–2.5 gross-error band that predates every stage-3 observation.

Retired in `preflight.py`, `03a`, `03c`, `03d`, `test_guard_coverage.py`,
`CLAUDE.md`, `OUTLINE.md`.

---

## 0. DECISION AUDIT — what survived on independent evidence

| decision | verdict |
|---|---|
| extended mesh does not conserve charge | **SURVIVES** — flux-decay probe |
| σ_air conditioning failure | **SURVIVES** — fields 10–20× too large, measured |
| 11–15% benign band | **VOID — retired** |
| `cg10` 11.90% dismissal | **VOID as reasoning**; moot (cancels in the pair ratio) |
| stage-3 halt, "7 of 16 above the band" | **VOID as reasoning** — correct by luck; it triggered branch A |
| `check_solve_output` as a gate | **VOID** — would have voided 11 good solves and passed the worst |
| **hypothesis 1 falsified** | **VOID — the measurement does not exist** (see above) |
| cavity verdict excluding warned pairs | **SURVIVES as a leave-some-out check**; rationale void, relabel |

---

## 0. UPSTREAM: FILED — simnibs/simnibs#665

https://github.com/simnibs/simnibs/issues/665

Leads with the disagreement pattern: `buccal` at 0.8870 mA is the largest true
deviation and is reported **clean**; `mental` at 1.0746 mA is flagged
**32.99%**; warned solves average 1.0113 mA against un-warned 0.9428 mA.

**One claim was deliberately weakened before filing.** The sphere validates the
tet-patch integral's *radius-consistency* (plateau CV < 0.7%) and the forward
setup (RDM 4.36%, MAG +4.40%, n = 120) — it does **not** validate its absolute
level, which reads 0.9406 / 1.2481 / 1.1134 across three sphere densities,
non-monotone and sign-changing. So the issue claims **ordering**, not
magnitude: a common scale factor cannot invert a ranking.

"4 of 22 agreement" went in **with its ±5 pp tolerance and the full sensitivity
curve** (0 / 2 / 4 / 9 at ±3 / 4 / 5 / 6 pp), per the new interim-statistic
rule.

---

## 0. THE CALIBRATION CHECK WORKS — third reversal, and the last one

The SimNIBS maintainer (discussions/666) corrected the framing. Reported
calibration is `e = 2|a-b|/(a+b)` over the two electrode-interface fluxes,
after which the solution is scaled so `mean(a,b)` equals the requested current.
Each interface sits `e/2` from 1 mA. **It is an interface-consistency
diagnostic, not a delivered-current error**, and #665 compared two different
physical quantities.

**Our own data confirms his model, not ours:** reported `e` vs SIGNED
(tet-patch − 1) is **Spearman +0.932, p < 1e-5**, slope +0.359 against a
predicted +0.5, R² 0.860. The −0.425 "anti-correlation" was entirely `abs()`
destroying the sign.

Arithmetic verified: **200.00% requires one interface flux exactly zero** (the
sigma_air case); **100.00% requires a/b = 3.000000** exactly, and the
extended-mesh readings back-solve to 3.020 and 2.840. So calibration
**detected** both real failures rather than corroborating them.

`check_solve_output` is UN-RETIRED and gates per-interface deviation at 10%.
The 11–15% band is reinstated **with a meaning**. The m2m hypothesis is dead.

**The lesson: before concluding an instrument disagrees with the truth,
establish what the instrument measures.** Nobody read the source until the
maintainer quoted it.

---

## 0. THE PRINCIPAL FINDING — the two montages see different muscles

Three of ten articulators are stronger at the ear than at the best jaw site:
**temporalis +3.92 dB** (`cg01`), **sternocleidomastoid +2.53** (`cg08`),
**lateral pterygoid +1.69** (`pre_tragus`). All clear the 0.27 dB floor.

**Framing reversed in OUTLINE**: not "the ear loses X dB and quantifying the
loss is the contribution", but "jaw sites dominate the anterior articulators,
retroauricular sites dominate temporalis, SCM and lateral pterygoid". A loss
figure cannot express a sign change and a mean over muscles hides it.

The three are exactly those attaching at or near the temporal bone, and the
prediction is **verified a-priori from git**: `expected_at_ear` entered in
commit `fa583f6` (2026-08-02), leadfields committed 2026-08-03.

**It surfaced because a test encoded the assumption.** `gap > floor` has no
vocabulary for a sign flip, so it reported the three strongest counter-examples
as "under the floor" — disconfirming evidence filed as absence of evidence.
Criterion is now `|gap| > floor` AND sign preserved.

**Fig 2 must be DIVERGING about 0 dB** (done: `TwoSlopeNorm`, neutral grey
midpoint, ear-winning cells ringed since unequal arms make saturation
non-comparable). **Fig 5 becomes a per-muscle map, not a loss ranking** — spec
rewritten in OUTLINE; the code still ranks and needs rebuilding.

`medial_pterygoid` at +0.62 dB stays flagged **borderline** (under the floor's
0.65 dB CI upper bound). Do not round it away.

---

## 0. STAGE 4 — THE TRUNCATION SENSITIVITY SURVIVES

10 of 10 muscles keep their conclusion when the three jaw sites within 10 mm of
the cut face are excluded. Median gap **+6.45 -> +5.91 dB**, a shift of
**-0.54 dB**, and **no sign flips**. Only three muscles move at all, because
for the other seven the best jaw electrode was never a near-cut site.

**The ear beats the jaw for three muscles** — temporalis (-3.92 dB), SCM
(-3.41), lateral pterygoid (-1.69). That is a result, not a failure, and a
first version of the test that checked `gap > floor` was discarding it. The
criterion is now `|gap| > floor` AND sign preserved.

At the floor's CI upper bound (0.65 dB) nine of ten stay resolvable;
`medial_pterygoid` at 0.62 dB is borderline and must be reported as such.

---

## 0. INVARIANTS 3 AND 4 HAVE RUN — reciprocity holds on the head mesh

| electrode | linearity | reciprocity | geometry |
|---|---|---|---|
| `above_ear` | **0.000e+00** | **7.500e-06** | **identical**, 2,140,977 nodes |
| `submental_mid` | 6.421e-03 | 6.913e-03 | **DIFFERENT**, 2,140,980 vs 2,140,979 |

7.5e-06 is **6.5e-05 dB**, four orders of magnitude inside the 0.27 dB
per-site floor. **Nothing downstream is void; stage 4 was clear to proceed.**

`submental_mid`'s larger number is not a failure of the identity: SimNIBS
re-meshes electrodes every run, so its 1x and 2x solves are different
discretisations and the comparison measures electrode realisation.
`same_discretisation()` now reports this beside every value.

**The 1e-6 tolerances are WITHDRAWN as gates, not retuned** — nothing ever
measured them, and they ask these identities to hold ~1000x tighter than the
measured reproducibility of what is being compared. Precedent: `COLLAR_OD_MM`.

---

## 0. SETTLED, do not re-litigate

Branch A fired. **Stage 3 stands because the paper reports RATIOS** — a common
scale error in delivered current cancels exactly in every site-to-site
comparison, and the tet-patch's absolute-level uncertainty is exactly such a
common term. What the tet-patch establishes is *relative*: no electrode
deviates anomalously with respect to the others (0.887–1.075, sd 0.0449, no
outlier). It is **not** a magnitude claim; the earlier "the solves are sound
because delivered current is within 11.3%" footing was wrong for the same
reason the upstream filing was narrowed to ordering. Also verified: 0 unmapped
tags, analysis map provably identical to the solve map, invariant 1 CV
0.32–1.53%. Invariant 2's *measurements* stand (max 13.8 µA of 1000 µA);
its *assurance* does not, because it has no real known-bad demonstration.

Nothing in Discussion / Introduction / Abstract may be written. Those framing
decisions are Carl's.

---

## 0. STAGE 3 IS COMPLETE — 22/22, data is in `results/03_leadfields.csv`

All 22 electrodes solved against `earlobe_contra` on the truncated mesh,
**isotropic condition only**. `throat_scm` correctly skipped. Montages: 10
cEEGrid, 7 jaw, 4 ear, 1 reference. **220 lead-field values, all finite, all
positive.**

| | |
|---|---|
| delivered current | **0.887–1.075 mA** against 1 mA requested |
| invariant 1 CV | 0.32–1.53%, plateau on every solve |
| invariant 2 max net | 13.8 µA of 1000 µA |

**Next, in order:** invariant 2's known-bad case (owed under the new norm),
the mesh-quality regression (still owed), the anisotropy tensor, then
`04_analyze.py`.

**The anisotropy path still raises `NotImplementedError` deliberately.** It
needs a per-element tensor (0.4 along fibre, 0.1 across) from
`orientation.principal_axis()` for `config.FIBRE_MODEL` "pca" compartments
only. Never let it fall through to the isotropic map: that would fabricate
Fig 4 by comparing a condition against itself.

---

## 0b-was. STAGE 3 STANDS — SimNIBS's calibration check was the error

**BRANCH A fired.** The tet-patch integral, run on all 18 completed solves,
says every one delivers **0.887–1.075 mA** against a requested 1 mA (max
deviation 11.3%), not the 15.6–33.0% SimNIBS claims.

Three discriminators: correlation between the warning and true deviation is
**−0.322, p = 0.193** (not significant, and the wrong sign); warned solves
average **1.0138 mA** against un-warned **0.9434 mA**, so the warned ones are
*closer* to correct; and the single worst delivery, **`buccal` at 0.8870 mA**,
is reported **clean**.

**15.6–33.0% is recorded as a FOURTH measured band** (false positive on the
MIDA mesh) beside the three established ones. SimNIBS's calibration line is
**demoted from gate to recorded quantity** for MIDA solves; the tet-patch
integral is the authority. Still parsed and stored per solve.

`mental`'s invariant-2 residual in absolute terms: **+13.8 µA of 1000 µA**
(`buccal` −2.3 µA). Small, despite being 6x the next worst.

**Unresolved and worth knowing:** why the check misfires on this mesh, and why
the misfire is *anti*-correlated with true delivery.

**Stage 3 may proceed to anisotropy and stage 4.**

---

## 0-pre. BOTH AGENT BRANCHES ARE MERGED

`carl/gap-check` and `carl/bench-scripts` are both in `main` and pushed.
Ownership held mechanically on both. Their worktrees at
`../gap-check` and `../bench-scripts` can be removed with
`git worktree remove` whenever convenient.

**bench/** is the Cerelog ESP-EEG suite for hardware landing **Aug 6**: 19
files, `bench/selftest.py` passes **85/85**, verified by running it here
rather than trusting the report. The PGA gain guard is the point of it —
`config.PGA_GAIN` is the only host-side declaration, `counts_to_volts()`
cannot run without a verification, and `bench/00_gain_check.py` confirms the
scale factor physically off the ADS1299's internal test signal with no
external hardware. Carl will lower the board from gain 24 to ~8; the guard
exists so that cannot silently become a 3x voltage error.

Untested without hardware, documented in `bench/README.md`: serial port open,
OpenBCI command dialect, frame decoder, AD3 auto-detect, and the lower-gain
rows of the expected-noise table (modelled, labelled as estimates).
`vet --agentic` produced no output on that branch, so the selftest is what
stands behind it.

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
