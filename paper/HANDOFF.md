# HANDOFF — Paper 1, ear-emg-forward-model

Written 2026-08-02 at ~99% context. Start here, then `CLAUDE.md` (standing
decision policy), then `paper/METHODS_LOG.md` (what went wrong and why), then
`paper/OUTLINE.md` (the paper's argument).

Repo: `~/CODELocalProjects/ear-emg-forward-model`, clean, all work committed.

---

## 1. RUNNING RIGHT NOW

**Cavity test, 16 solves, serial.** Background job, ~2/16 done, slow.
Script: `scratchpad/cavity_test.py` (in the session scratchpad, not the repo —
**copy it into `src/` if it matters**, it is the only uncommitted artefact).
Output lands in `results/cavity/{air,filled}__{electrode}/`.

It tests articulatory volume-conductor exposure vs distance to the oral cavity.
8 electrodes spanning 14.5–75.5 mm from the modified cavity. **Analysis is
NOT the script's own printed verdict** — that is superseded. Use
`src/03c_cavity_analysis.py`, which decomposes common-mode from residual and
reports the flip point.

**Do not compute the cavity verdict without reading `03c`'s ordering guard** —
it exits 2 until the floor file exists. That file now exists.

---

## 2. THE MEMORY SITUATION — READ BEFORE ANY PARALLEL RUN

Measured with everything running:

```
PhysMem: 47G used, 536M unused
swap:    3917 MB of 5120 MB used
largest consumer: ollama llama-server  14.76 GB
```

**The machine is memory-saturated and already swapping with ONE solve running.**

A production solve is **1 core at 100%, 10.8 GB peak RSS** (measured over 60 s,
10 samples). So:

- cores are NOT the constraint — 17 of 18 idle during every solve
- **memory is, and there currently is none free**

`src/run_solves_parallel.py` defaults to N=3 based on a *nominally* free 48 GB.
**That default is unsafe as things stand.** Before using it:

1. Stop `ollama` (frees 14.76 GB) or confirm it has exited.
2. Re-measure actual free memory.
3. Only then pick N. With ollama gone, N=3 is sound (32.4 GB, 15.6 GB headroom).
   With ollama running, **N=1**.

Swap thrash on a 1-hour run costs more than the parallelism gains.

### Untested, try this FIRST — threads before processes

`simnibs.simulation.fem.tdcs()` has an **`n_workers` parameter (default 1)**.
hypre supports OpenMP; SimNIBS may simply not enable it. **This was not
tested** — context ran out.

Run one solve with `OMP_NUM_THREADS=8` and/or `n_workers>1` and check whether
CPU exceeds 100%. Threads cost **no extra memory**; processes cost 10.8 GB each.
If threads work, the process pool is unnecessary and the memory problem
largely disappears. Report either way.

---

## 3. THREE QUEUED FOLLOW-UPS (Carl's, not yet done)

### 3a. The floor has false precision — do this before it gates Fig 5
`results/electrode_meshing_floor.txt` holds **0.1310 dB from n=2**. That is one
difference quoted to four significant figures, and it now gates two analyses
(cavity criterion b, Fig 5 resolution).

Report it as **~0.13 dB with n stated and its own uncertainty**. Get more draws
cheaply: **vary the electrode's angular placement slightly at the same
position**, which re-triangulates the contact without re-meshing the head.
Target **n ≥ 5**. These are sphere solves — seconds each, not minutes.

### 3b. MAG disposition
Three observations now show MAG's variance is dominated by **electrode
discretisation, not solver accuracy**:

| observation | value |
|---|---|
| two identical meshes, 15 mm | 5.06 pp |
| non-repeatability | +4.4% vs +9.5% |
| across diameter (RDM moved 0.4 pp) | +5.996/+7.516 vs +4.400/+9.464 |

**Keep reporting MAG** — reviewers expect the RDM/MAG pair — but state
explicitly what its variance measures. *"MAG is not a useful solver-accuracy
metric when the electrode is meshed rather than a point sensor"* is a
defensible small finding. **RDM carries the headline.**

### 3c. Fig 5 — propagate the floor, do not assume it transfers
A dB noise floor does **not** map onto a correlation threshold 1:1. Perturb each
lead field by the measured per-site noise, recompute the column correlations N
times, and report **each correlation's uncertainty**. Fig 5 is the design table
people would actually use, and `r = 0.95 ± 0.01` and `r = 0.95 ± 0.15` are
different claims.

---

## 4. STAGE 3 CONFIG

- **24 positions** including a provisional literature `throat_scm`.
  **`throat_scm` has no coordinate yet** — Carl is measuring it on his own neck.
  It is `verified=held` with blank coordinates in
  `results/02_electrode_positions.csv`, and every consumer skips held rows.
  A "provisional literature" placement was authorised but **not implemented**;
  SENIAM's SCM guidance (1/3 along sternal notch → mastoid) is the obvious
  source but was **never verified** — do not use it unsourced.
- **Both anisotropy conditions** (isotropic, anisotropic per `config.FIBRE_MODEL`).
- **Mesh:** whichever the boundary run selects. **The boundary run has not been
  done.** Rule is pre-committed in OUTLINE: >1.0 dB shift at `hyoid`,
  `submental_lat` or `submental_mid` under either slab conductivity ⇒ extended
  mesh (`data/mida_neckext.msh`) becomes primary.
- **Invariants:** 1 and 2 on every solve; 3 and 4 on **first and last** of the
  batch, plus any solve whose invariant-1 CV is elevated
  (`solve_invariants.needs_escalation`).
- **Expect escalation to fire often.** The CV band was calibrated on n=4 solves
  varying only σ_air, on one mesh and one montage, so it captures no mesh or
  montage variance. That is predicted, not drift. Recalibrate from the first 10
  stage-3 solves and record as **calibration 2 with its own n, alongside the
  first, not overwriting it**.

---

## 5. THINGS IN MY HEAD NOT YET WRITTEN DOWN ELSEWHERE

- **`scratchpad/cavity_test.py` is not in the repo.** It is the only script that
  exists solely in the session scratchpad. Everything else is committed.
- **The buccal exterior-flux anomaly is unexplained.** `buccal` reports
  *exactly* zero exterior flux at r=25 and 35 mm, meaning the patch touches no
  mesh-exterior face at those radii — odd for a skin-mounted electrode. It does
  not affect the plateau criterion, which handles it, but nobody understands it.
  `hyoid`'s exterior count is monotone, so it is not a general classification
  bug.
- **The ~4% flux deficit has no explanation.** My first-order-discretisation
  story was falsified (non-monotone in h, sign change, 25% overshoot at coarse).
  The electrode-realisation hypothesis is now *supported* by the floor
  measurement tracking diameter, but the deficit itself is still unexplained.
  **Invariant 1 is a consistency test only — never quote its absolute level.**
- **Fig 7 is deleted, not pending.** Its premise was falsified by measurement.
  The air-void inventory survives as a supplementary figure. Nothing replaces
  Fig 7 unless the cavity test survives.
- **8 of 18 muscles are still pooled** in `Muscle (General)` (38) and `Tongue`
  (42), including digastric posterior and stylohyoid — the two carrying the ear
  argument. `src/roi_corridor.py` handles them via a corridor ROI. The styloid
  process is **not segmentable** in MIDA (checked exhaustively), so one corridor
  holds both muscles.
- **Adversarial pass at every stage boundary** is standing policy. It has a
  ~50% hit rate on already-reviewed material. Tag claims
  `measured|derived|asserted` and attack `asserted` first.
- **Nothing in Discussion/Introduction/Abstract may be written.** Those framing
  decisions are Carl's.
