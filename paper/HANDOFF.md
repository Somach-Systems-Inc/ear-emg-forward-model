# HANDOFF — Paper 1, ear-emg-forward-model

Rewritten 2026-08-03. Read `CLAUDE.md` (standing decision policy), then
`paper/METHODS_LOG.md` (what went wrong and why), then `paper/OUTLINE.md`.

Repo clean, all work committed, `main` at the Sculptor-review commit.

---

## 1. NOTHING IS RUNNING

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

**Next action:** rebuild `data/mida_neckext.msh` via `src/01c_extend_neck.py`
with the slab meshed comparably to adjacent head elements, re-run
`src/03a_boundary_run.py`, confirm both extended solves report clean
calibration, and only then apply the rule.

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
n=6, per-site, common mode removed. **95% CI [0.16, 0.28]** — quote it with
the interval, not as `0.272`. Written to
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
and **failing** the old registered 0.43 dB floor. `hyoid` is the closest site
at 14.5 mm, so the physics puts the largest effect there, but a reader must
not have to discover it.

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
