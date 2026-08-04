# Follow-up artifacts for simnibs/simnibs discussions/666

**NOTHING HERE HAS BEEN POSTED. Carl posts, not an agent.**

The maintainer's correction is accepted in full. Reported calibration is
`e = 2|a−b|/(a+b)` over the two electrode-interface flux estimates, after which
the solution is scaled so `mean(a,b)` equals the requested current. Each
interface therefore sits `e/2` from the requested current. It is an
interface-consistency diagnostic, not a delivered-current error.

**Issue #665 needs correcting, not defending.** Its headline compares an
interface-consistency measure against a delivered-current measure. Our own data
confirms his model rather than ours (see below).

---

## The confirmation, which is the thing worth leading with

If `a = 1 + e/2`, the tet-patch integral around the **active** electrode should
track the reported error with a positive slope near 0.5. On all 22 solves:

| comparison | result |
|---|---|
| reported `e` vs **\|tet-patch − 1\|** (what #665 did) | Spearman **−0.425**, p = 0.048 |
| reported `e` vs **signed** (tet-patch − 1) | Spearman **+0.932**, p < 1e-5 |
| linear fit | slope **+0.359** (model predicts +0.5), R² = **0.860** |
| residual vs `a = 1 + e/2` | sd 0.0235, against 0.0449 for a flat 1.0 — the model removes **73%** of the variance |

The whole "anti-correlation" in #665 was `abs()`. Taking the absolute deviation
destroyed the sign and inverted the ranking. Slope 0.359 rather than 0.5 is
expected: the tet-patch integrates cut flux over r = 25–75 mm, not flux at the
interface, and carries its own realisation scatter.

The two algebraic landmarks check out exactly, and both match a real failure we
hit:

| reading | requires | our case |
|---|---|---|
| **200.00%** | one interface flux exactly zero | `sigma_air` = 1e-15, a non-conducting return path |
| **~100%** | `a/b = 3.000000` | neck-extended mesh leaking through its inferior face; measured 100.49% and 95.84% back-solve to **3.020** and **2.840** |

---

## Artifacts

| # | file | status |
|---|---|---|
| a | `interface_fluxes_derived.csv` | **DERIVED, not raw.** `fields_summary.txt` prints only the percentage, so `a` and `b` are reconstructed as `1 ± e/2` under the stated model. Raw values would need the solver to emit them — a small feature request worth making in the thread. |
| b | `both_electrode_flux.py` | **script written, NOT yet run on all 22.** Measures the tet-patch cut flux at BOTH electrodes, not just the active one, which is the like-for-like comparison against `a` and `b`. ~22 mesh reads. |
| c | `tet_patch_standalone.py` | standalone, runnable, no project imports |
| d | **the four-layer analytic sphere** | **highest value and fully shareable** — not MIDA-derived, so no licence constraint. `data/val_sphere.nii.gz`, `src/val_rdm_mag.py`, and `sphere_calibration_per_solve.csv`. **5 of 16 solves emit the warning while the lead fields match the closed form at RDM median 4.36%.** That is the case he can actually debug: a geometry with an exact answer, where the check fires and the solution is nonetheless right. |

**On (d), the interesting question under the corrected interpretation** is no
longer "why does it false-positive". It is: on a symmetric four-layer sphere
with identical electrodes, why do the two interface fluxes disagree by 11–15%
(each interface ~6–7.5% off) when the field itself matches the analytic
solution to 4.36% RDM? Either the interface-flux estimator is noisier than the
field it is computed from, or the two electrodes genuinely see different fluxes
for a reason worth knowing. The sphere is the right place to find out.
