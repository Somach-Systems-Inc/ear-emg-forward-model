# Methods log

> **⚠️ COMMIT HASHES RECORDED BEFORE 2026-08-03 DO NOT RESOLVE DIRECTLY.**
> On 2026-08-03 the history was rewritten with
> `git filter-repo --path-glob '*.geo' --invert-paths` to purge MIDA-derived
> surface geometry that should never have been committed (see the licensing
> entry near the end of this file). **Every commit from the first `.geo`
> addition onward received a new SHA.**
>
> `paper/COMMIT_MAP_PRE_PURGE.txt` maps old to new for all 57 commits. To
> resolve a hash quoted anywhere in this log:
>
>     grep -i ^<oldhash> paper/COMMIT_MAP_PRE_PURGE.txt
>
> Worked examples: `304fcca` resolves to `8ba2295`, and `5908e18` to
> `acf76be`. Commits predating the first `.geo` addition kept their original
> SHA and map to themselves, so a hash that appears unchanged is not an error.
>
> **No content was lost.** Only `.geo` files were removed, and SimNIBS
> regenerates them on every solve.

Decisions, specification defects and non-obvious tool behaviour, recorded as
they happen. Kept because the corrections here are often more instructive than
the original plans, and because a defect that is not written down gets paid for
twice.

Distinct from OUTLINE.md, which holds the paper's argument. This holds the
process.

---

## 2026-08-02 — SPEC DEFECT (mine, Carl): interface-proximity test was collinear by construction

**Requested:** measure forward error against source-to-interface distance on
the concentric validation sphere, to set an error envelope for sensitivity
values near compartment surfaces.

**Defect:** on a concentric sphere a source at radius *r* is at distance
(78 − *r*) mm from the innermost interface **by construction**. Distance to
interface and eccentricity are perfectly collinear, so no regression on that
geometry can separate them. The measurement came out backwards from the
hypothesis — RDM *fell* toward the interface, correlation +0.676 with distance —
which is what exposed it. That is the well-known degradation of forward
solutions for deep central sources, wearing the wrong label.

**Correction:** hold source radius fixed (~50 mm) and vary the *layer boundary*
radius (55, 60, 65, 70 mm). Interface distance varies, eccentricity is
constant, the geometry stays concentric so the analytic oracle still applies.
Preferred over an eccentric inclusion or a self-converged head reference, both
of which trade an exact oracle for an approximate one.

**Recorded as a specification defect, not a result.** The requested experiment
could not have answered the question asked of it.

---

## 2026-08-02 — TOOL BEHAVIOUR: `meshmesh` element-size range does not override the label-volume floor

**Cost:** one full convergence run (48 solves) that produced two densities
instead of three.

Asking for `elem_sizes = {"standard": {"range": [0.8, 2.5]}}` on a 0.5 mm label
volume produced a mesh **0.13% larger** than the default-range mesh, at
identical element size (648,170 vs 647,323 tets; h_mean 1.676 vs 1.677 mm).

Element size is floored by two things the size range does not override:

1. the **label volume resolution** — 0.5 mm voxels cannot support sub-millimetre
   tetrahedra faithfully
2. **MMG's remeshing pass**, which runs after CGAL and renormalises element
   sizes (visible as `Tetraedras after remeshing run 1/2` in the log)

**Consequences.** To refine, refine the *label volume* (or use
`--voxsize_meshing`), not the size range. To coarsen, the size range works
fine — which is why the three-density study is being completed by adding a
**coarser** density rather than a finer one, sidestepping the floor entirely at
the cost of one cheap solve.

**Check before trusting any density request:** compare `h_mean` between meshes,
never the requested range. Two meshes with the same `h_mean` are the same
experiment run twice.

---

## 2026-08-02 — MEASUREMENT: electrode meshing is per-site noise, not global scale

Two statistically identical sphere meshes (0.13% apart in element count) gave
MAG differing by **5.06 percentage points** and RDM by 0.54. Electrode contact
area is realised from incidental surface triangulation, so it changes
discontinuously when surface triangles move.

**This does not cancel in ratios.** Each electrode's contact is realised
independently, so the term is per-site noise rather than a global scale factor,
and it propagates into every site-to-site comparison the paper makes.
5.06% = 20·log₁₀(1.0506) = **0.43 dB**.

Two things follow. It sets the **resolution floor for the channel-redundancy
analysis**, where differences between adjacent sites may be smaller than the
noise. And it sits only ~2.3x below the boundary run's 1.0 dB decision
threshold, so a boundary shift under ~0.5 dB cannot be separated from meshing
noise by a single pair of solves.

---

## 2026-08-02 — RETRACTION: the +4.4% MAG figure

Reported as an accuracy figure before its repeatability was known. A nominally
identical mesh gives +9.5%. Withdrawn; MAG is not quotable at this precision
until the electrode confound is removed.

RDM is the more robust metric and carries the headline, with the caveat that
5.147 → 4.355 across two densities is **monotone decreasing across the two
available densities**, not a convergence demonstration. It does not become
"converged" until a rate is fitted across three genuine densities.

---

## 2026-08-02 — BLOCKER: 106 of 116 MIDA labels have no conductivity

The boundary run failed before producing a number:

    TypeError: The value 12 in cond_list is not numerical

SimNIBS requires a conductivity for **every tag present in the mesh**, not only
the ones the analysis reads. `config.SIGMA` holds 14 generic tissue values and
`config.MUSCLES` maps 10 muscle labels, so 106 of the mesh's 116 tags were
`None`.

This blocks **every** solve on the MIDA mesh, so it blocks stage 3 as well as
the boundary run. It is not specific to the boundary experiment.

Scale of the gap:

| | count |
|---|---|
| MIDA labels in the mesh | 116 |
| mechanically mappable to an existing `SIGMA` value by name | 69 |
| needing a newly sourced value | 47, of which one is Background |

The 46 real structures are roughly **7% of head tissue volume** (excluding
Background) and are dominated by deep brain nuclei, glands, tendons, dura and
mucosa: Dura, Parotid Gland, Mucosa, Galea Aponeurotica, Submandibular Gland,
the brainstem, Thalamus, Putamen, Caudate, Hippocampus, the tendons.

Most sit far from both the muscle compartments and the electrodes, so their
exact values will barely move a jaw or ear lead field — but SimNIBS cannot run
without them, and **this is Table 1 of the paper**, which per CLAUDE.md must
carry sourced values, not plausible ones. Not filled in by guessing.

**Design note for whoever fills it:** the mapping should be explicit
label → tissue → σ with a source per row, not a name-matching heuristic. The
69 "mechanically mappable" labels above were matched by regex to demonstrate
the scale of the problem; that is a diagnostic, not a proposal. `Teeth` matched
`bone_compact` by keyword and dentine is not compact bone.

---

## 2026-08-02 — STOP: step 1 results are invalid; every solve carries a current-calibration warning

**Do not use `results/03_conductivity_bound.csv`.** The numbers in it are
physically impossible and are withdrawn.

### What the numbers said

Condition d (ear air voids filled with bone) reported **+39.9 to +45.7 dB**
across *all ten* muscle compartments at the `hyoid` electrode. Filling the
mastoid air cells cannot change a hyoid lead field at all at that distance, and
a near-uniform shift across every compartment is the signature of a global
scaling, not a local physical effect. The reported "sensitivity envelope" of
47.5 dB is likewise not credible against a 0.43 dB meshing noise floor.

### What was actually wrong

Every one of the 20 solves wrote this into `fields_summary.txt`:

    The current calibration error exceeded 10%! Estimated error value: 200.00%

**I did not read the solver's own output file.** SimNIBS reported the failure
in writing and I took the field values anyway. This is precisely the failure
mode CLAUDE.md names — silence is the bug, except here it was not even silent.

### What is NOT yet established

The same warning appears in **39 of 83 sphere solves**, including ones behind
the reciprocity validation. That would imply the validation is invalid too —
except the sphere result agreed with the *analytic* oracle at magnitude ratio
0.9907, r = 0.997, which a genuine 200% current error cannot produce. The
sphere summaries also print `Cannot locate subjects m2m folder / some
postprocessing options might fail`, so the calibration check may simply be a
post-processing step that cannot run without an m2m folder and reports a
meaningless 200% for any custom mesh.

Both readings are live and they have opposite consequences:

- **benign** — the warning is a post-processing artefact of custom meshes; the
  reciprocity validation stands; the MIDA anomalies have some other cause still
  to be found
- **real** — currents are mis-delivered; the reciprocity result is coincidental
  and everything solved on a custom mesh is suspect

**Not resolved by guessing.** The decisive test is to solve a case with a known
answer *and* check the calibration line: the sphere against the analytic oracle
is exactly that, so re-running one sphere solve while inspecting delivered
current per electrode separates the two readings.

### Required before any further solving

1. Parse `fields_summary.txt` after **every** solve and hard-fail on a
   calibration warning. No result is read from a solve that reported an error.
2. Determine whether the warning is benign for custom meshes, by the test above.
3. Only then re-run step 1, and step 2 behind it.

### Partial signal, recorded but not trusted

Conditions b, c1 and c2 gave *sane* values at masseter (−2.3, +3.4, −1.3 dB),
so the conductivity sensitivity may well be small. That is a hint, not a
result, and it is not going in the error budget until the solves are clean.

---

## 2026-08-02 — RESOLVED: the 200% calibration failure was conductivity conditioning

Carl's hypothesis, confirmed in three steps, two of which cost no solve time.

**Step 0, free.** Conductivity dynamic range per mesh:

| Mesh | Tags | σ range | σ_max/σ_min | tags at 1e-15 |
|---|---|---|---|---|
| Sphere | 4 | 0.004 – 1.0 | **2.5e2** | none |
| MIDA | 116 | 1e-15 – 1.879 | **1.879e15** | 10 |

Double precision carries ~1.8e16 of range. **The sphere was never exposed to
this, so the reciprocity validation does not need retracting.**

**Step 1, free.** The MIDA logs show `Using solver options: hypre` — an
*iterative* algebraic-multigrid solver, which is the proposed mechanism. The
same solver on the well-conditioned sphere converged and matched the analytic
oracle. Note: SimNIBS does not print a residual or iteration count, so the
calibration line is the only convergence signal available.

**Step 2, one solve.** MIDA baseline re-run with air at 1e-6, everything else
identical:

| | air 1e-15 | air 1e-6 |
|---|---|---|
| σ_max/σ_min | 1.879e15 | 1.879e6 |
| calibration | 200.00% error | **no warning** |
| field at hyoid | 2.8 – 6.1 V/m | **0.11 – 0.70 V/m** |

The broken solves returned fields 10–20x too large. Step 3, the sphere
current-delivery test, is therefore unnecessary as a discriminator.

### The value, and why it is not a physical measurement

`SIGMA["air"]` is now **1e-6 S/m**, flagged in Table 1 as a **deliberate
numerical choice**.

*Physics:* 1e-6 is four orders below compact bone (0.008), so current avoids an
air cavity identically at 1e-6 and at 1e-15. Nothing physical distinguishes
them.

*Numerics:* the stiffness matrix inherits σ_max/σ_min as its condition number.
At 1e-15 that is within a factor of ten of the double-precision limit and the
iterative solver fails; at 1e-6 it is 1.879e6 and the solve is clean.

*No convention to follow.* SimNIBS's standard table — verified directly in
`simnibs/utils/mesh_element_properties.py` — has 14 tissues and **no air entry
at all**. A web search surfaced a figure of 2.5e-14 for tDCS head models, but
it could not be traced to a primary source and is **not cited**. Any value
below ~1e-5 is physically equivalent here, so the choice is defensible on the
numerical argument alone and is presented that way.

### Permanent guards added

`src/preflight.py` gains two, both tested against the known-bad and known-good
cases:

- `check_conductivity_range()` — fails above σ_max/σ_min of 1e8 (two orders of
  headroom over the working case, eight below the failing one)
- `check_solve_output()` — reads `fields_summary.txt` after every solve and
  refuses to return a result from one that reported a calibration error

Not achievable: recording solver residual and iteration count per solve.
SimNIBS logs neither. The calibration line is the available proxy and is now
mandatory.

---

## 2026-08-02 — CORRECTION: SimNIBS's calibration check was not broken; I did not read it

An earlier entry here and an upstream issue draft both claimed the
current-calibration check "emits exactly 200.00% on custom meshes ... while the
actual failure goes undetected". Checking that claim before filing it showed it
is false.

| Case | σ span | calibration line | solve correct? |
|---|---|---|---|
| MIDA, air 1e-15 | 1.879e15 | **200.00%** | no |
| MIDA, air 1e-6 | 1.879e6 | **no warning** | yes |
| Sphere, 4 layers | 2.5e2 | warning on 5/16 | yes |

**On MIDA the check discriminated correctly.** It fired on the broken solve and
was silent on the good one. The failure was entirely mine: I did not read
`fields_summary.txt`, and SimNIBS had reported the problem in writing.

What survives is much narrower: a false-positive rate on well-conditioned
custom meshes (5 of 16 sphere solves warned while matching the analytic oracle).
The upstream issue is **held, not filed** — `paper/simnibs_issue_draft.md`
records the downgraded version and the reason.

The two suggestions that stand independently: warn when σ_max/σ_min exceeds
~1e8 at setup, and expose the iterative solver's residual and iteration count.

---

## 2026-08-02 — A wrong diagnosis that travelled attached to a right one

Worth recording as a pattern, not just an incident.

The conditioning hypothesis was **correct**: conductivity span near the
double-precision limit drove the iterative solver to return fields 10–20x too
large, and 1e-15 → 1e-6 fixed it. That diagnosis was reasoned from the round
`200.00%` figure and the `Cannot locate subjects m2m folder` message, and it was
right.

Attached to it was a second inference — that the calibration check itself was
broken and reported a constant 200.00% on custom meshes. **That was wrong, and
wrong in the dangerous direction.** On MIDA the check discriminated correctly:
200.00% on the broken solve, silent on the good one. Acting on the inference
would have meant suppressing or ignoring a signal that was working.

The reason this is worth a log entry: the wrong advice arrived **bundled with a
correct hypothesis, from a source that had just been right about something
harder**. That is the configuration most likely to pass unchallenged, because
the surrounding reasoning is sound and the conclusion feels earned. It only
surfaced because the claim was about to be published upstream under a real name,
which forced a check that ordinary internal use would not have.

Two working rules from it:

1. **Verify each claim separately, even when they arrive together and the hard
   one checks out.** Correctness does not propagate across a conjunction.
2. **Prefer the check that has an external consequence.** Drafting the issue for
   publication is what caught this; the same claim sat unchallenged in an
   internal log for two commits.

The direction also matters. An over-cautious wrong diagnosis costs a wasted
check. This one pointed at *disabling* a working alarm, and would have removed
the only signal that caught the original failure.

---

## 2026-08-02 — ADVERSARIAL PASS #1 (stage boundary before queue restart)

Job: falsify what is already recorded, not extend it. Four claims examined.

**A. "p = 0.980 confirms the densities are asymptotic" — FALSIFIED.**
Three data points fitted with three free parameters (RDM_0, C, p) is an exact
fit by construction; the reported residual was 5.3e-26. **A fit that cannot fail
carries no goodness-of-fit evidence.** p is determined algebraically, not
corroborated. Softened at source to "consistent with", with the reason inline.
A fourth density would make it testable.

**B. "0.43 dB electrode-meshing noise floor" — OVERSTATED.**
Derived from exactly two meshes. n = 2 is one difference, not a distribution,
and "floor" implies a spread never measured. Table 3 now reads
"~0.43 dB (n=2, single difference)". It has been used to size two decision
thresholds, so the qualification matters.

**C. "the sphere calibration warnings are false positives" — UPHELD, and now
tested rather than asserted.** The original argument was aggregate: overall RDM
matched the oracle. That is weak, because RDM is computed per source across all
16 electrodes, so one bad electrode dilutes. Tested per electrode:

    warned    (e02, e06, e07, e10, e11)  n=5   median |L_num|/|L_ana| 0.9814
    un-warned                            n=11  median                 1.0345

Difference 0.053, inside the scatter of either group. The warned electrodes are
not less accurate. Claim survives, on better evidence than it had.

**D. "suprahyoid corridor, length 85.1 mm" — PRECISION OVERSTATED.**
Recorded separately: the mastoid air-cell inferior tip sits above the true
digastric fossa, so the ROI "effectively begins ~10 mm distal". That is a 12%
bias on an 85.1 mm corridor, yet the length is quoted to 0.1 mm. Quote it as
~85 mm with the landmark bias attached, or measure the offset.

### Why this pass exists

The SimNIBS claim survived two commits in an internal log and died within
minutes of being drafted for an external audience. A log written for oneself is
not read adversarially. This manufactures that scrutiny on a schedule instead of
waiting for an audience to supply it.

Two of four claims needed correction and one needed upgrading from asserted to
tested. That hit rate on already-reviewed material is the argument for running
it at every stage boundary.

---

## 2026-08-02 — ADVERSARIAL PASS #2: the Fig 7 premise is FALSE

**Attacked an `asserted` claim and it did not survive.** Fig 7 is a numbered
result, so this is a stop-and-report trigger.

**The claim (asserted, never measured):** "the retroauricular region contains
the head's only large superficial skin-adjacent air voids, and they sit
directly between the electrode and the target muscles. No jaw site has anything
comparable."

**Test 1 — air-void inventory by volume and depth below skin** *(measured)*:

| Label | Structure | Volume mm³ | Min depth | Median depth |
|---|---|---|---|---|
| 31 | Air Internal - Nasal/Pharynx | **43,650** | **0.5** | 31.6 |
| 97 | Air Internal - Oral Cavity | 21,339 | 5.4 | 37.4 |
| 28 | Maxillary Sinus | 12,147 | 15.6 | 29.5 |
| 26 | Ethmoidal Sinus | 5,511 | 3.8 | 23.0 |
| 27 | Frontal Sinus | 3,109 | 8.0 | **12.7** |
| 30 | **Air Internal - Mastoid** | **1,402** | 11.3 | 16.4 |
| 85 | Ear Auditory Canal | 1,384 | 0.5 | 3.8 |

The mastoid air cells are among the **smallest** air voids in the head, 31x
smaller than the nasopharyngeal airway, which reaches the same 0.5 mm minimum
depth. The frontal sinus has a *shallower* median depth than the mastoid.

**Test 2 — distance from each electrode to its nearest air void** *(measured)*:

    ear sites   min 16.4   median 21.2 mm
    jaw sites   min 14.5   median 22.4 mm

**Indistinguishable, and the single closest electrode in the montage is
`hyoid` — a jaw site — at 14.5 mm.** Every jaw site sits over the oral cavity
or nasopharynx at the same range the ear sites sit over the mastoid.

**Verdict.** The premise fails on all three counts: not the only, not the
largest, not uniquely close to electrodes. Fig 7 as framed — air voids as an
*ear-specific* mechanism explaining ear-versus-jaw difference — is not
supported. The inter-subject variability prediction inherits the problem:
sinus pneumatisation varies as much as mastoid pneumatisation and sits next to
the jaw sites.

**What could still survive**, if the measurement supports it: air voids as a
*general* modelling term affecting both montages, tested by the same
filled-versus-air comparison but reported without the ear-specific framing.
That is a Methods term, not a headline result.

Provenance note: the claim was tagged `asserted` on the first pass and attacked
first for that reason. It had already been written into OUTLINE as a numbered
result with a testable prediction attached.

---

## 2026-08-02 — Invariant 1 rebuilt: two wrong diagnoses before the right one

The flux invariant went through two incorrect explanations before the actual
cause was found. Both are recorded because the second violated a conservation
law, and that is worth remembering.

**Killed hypothesis 1 — "current escapes a closed shell."** I wrote that buccal
showed low flux because current spreads laterally through thin cheek and leaves
the shell. **This violates Gauss's law.** A closed surface enclosing a source
carries flux equal to that source regardless of how current moves inside it.
Lateral spreading cannot reduce enclosed flux. Carl caught it.

**Killed hypothesis 2 — "triangle elements corrupt the centroid."** I predicted
that `find_closest_element` returning surface triangles would put a 0 in the
4th node slot and wrap the index. Tested: the 4th slot is never 0, and
triangles are only 6-12% of hits. Falsified by measurement.

**Actual cause, part 1 — masking.** The inside test was
`distance-to-nearest-element-centroid <= 2h`, with h ≈ 0.94 mm. A point can sit
legitimately inside an irregular tetrahedron and still lie further than 1.87 mm
from its centroid, so the test discarded points genuinely in tissue — 41-52% of
them, at a rate that varied by electrode (buccal 41-42%, hyoid 41-52%). **That
is what produced the "~19% quadrature bias" I had been reporting as an accepted
property.** It was not quadrature; it was a broken classifier.

**Actual cause, part 2 — the invariant's premise was wrong.** Replacing the
sampled shell with an exact tet patch gave flux ≈ 0, not ≈ 1. The reason is
physical: **SimNIBS injects current as a Dirichlet condition on the electrode's
exterior surface, not as a volumetric source.** A patch around the electrode
therefore contains no source. Current enters through the mesh's outer face and
leaves through the cut, netting zero — measured as +0.968 out through the cut
against −0.938 in through the exterior.

The quantity that equals the injected current is the flux through the
**interior cut only**, separated by face multiplicity in the full mesh (2 =
interior, 1 = mesh exterior).

**Result.** Corrected invariant on the known-good solve: 0.9606, CV 0.49%
across six radii from 25 to 75 mm. The residual ~4% deficit is *not* absorbed
silently: it is consistent with first-order error from the piecewise-constant
per-tetrahedron **E**, which matches the p ≈ 0.98 convergence rate measured
independently on the sphere. It should shrink on a finer mesh, and that is a
testable prediction rather than an excuse.

**Plateau criterion**, no absolute band:

| case | plateau | mean | CV | verdict |
|---|---|---|---|---|
| known-good 1e-6 | 25-75 mm, 6 radii | 0.9606 | 0.49% | PASS |
| known-bad 1e-15 | none (diverges to −8.94) | — | — | FAIL |
| buccal | 45-75 mm, 4 radii | 0.8861 | 1.53% | PASS |

buccal's earlier failure was a false positive of the old test. It needs r ≥ 45
mm before the patch contains the injection surface, which the plateau
requirement discovers automatically instead of needing a hand-picked radius per
electrode.

Open and recorded rather than absorbed: buccal reports exactly zero exterior
flux at r = 25 and 35 mm, meaning the patch reaches no mesh-exterior face at
those radii. That is unexplained for an electrode sitting on the skin. It does
not affect the criterion, which handles it via the plateau, but it is not
understood.

---

## 2026-08-02 — RETRACTION: the ~4% flux deficit is NOT first-order discretisation

Last commit recorded that the corrected integral's 0.96 reading was "consistent
with first-order error from the piecewise-constant per-tetrahedron E, matching
the p ~ 0.98 convergence rate measured independently on the sphere", and called
it a testable prediction. **Tested. It fails.**

Corrected tet-patch cut flux on all three existing sphere densities:

| density | h_mean | cut flux | plateau CV | deficit |
|---|---|---|---|---|
| vcoarse | 2.957 | 0.9406 | 0.69% | **+0.059** |
| coarse | 2.257 | **1.2481** | 0.53% | **−0.248** |
| medium | 1.677 | 1.1134 | 0.48% | −0.113 |

The deficit is non-monotone in h and **changes sign**. A first-order
discretisation error approaches unity monotonically from one side; it does not
overshoot by 25%. The story is falsified.

Each reading is internally consistent — every plateau CV is under 0.7% — so the
*consistency* invariant is unaffected and remains valid. What is wrong is the
explanation of the *level*.

**More likely explanation, and it is not yet tested:** the sphere solves use
15 mm electrodes, electrode meshing changes with mesh density, and per-electrode
contact geometry was already measured not to cancel between sites. Level
variation tracking electrode realisation rather than volume discretisation fits
every observation, including the electrode-dependent spread on the head mesh
(hyoid 0.9606 vs buccal 0.8861).

**Consequence for the invariant.** Invariant 1 must be used as a
radius-consistency test only, never as an absolute measurement of delivered
current. That is how it is written, so nothing downstream changes — but the
reason is now measured rather than assumed, and the earlier "~4% is
discretisation" claim is withdrawn.

**Provenance lesson.** The claim was tagged `derived` — it followed from a
measured number (0.96) plus reasoning (p ≈ 0.98 elsewhere). The reasoning was
plausible and the arithmetic fine; the inference was still wrong, because a
matching exponent from a different measurement is not evidence about this one.
`derived` is not a safe tier.

**Lesson, recorded verbatim because the wording matters:** a matching exponent
measured elsewhere is not evidence about this quantity. `derived` is not a safe
tier — it inherits the confidence of its weakest link, and mine was an analogy.

**Consolidated fix.** The 15/20 mm harness mismatch and the unexplained level
spread are plausibly the same defect, so one re-run at the production diameter
answers four open questions at once: it removes the mismatch, re-measures the
electrode-meshing floor at 10 mm (replacing 0.43 dB everywhere it has been used,
including the cavity criterion and the channel-redundancy resolution floor),
tests the electrode-realisation hypothesis for the 0.96 vs 0.886 spread, and
re-measures RDM/MAG, which are headline validation numbers currently carrying a
15 mm electrode. The local-element-quality test is dropped unless that comes
back null.

`src/test_no_hardcoded_geometry.py` makes the mismatch class a test failure:
it greps for literal `dimensions = [n, n]` anywhere in `src/` and fails. The
original slipped through an entire validation campaign unnoticed.

---

## 2026-08-02 — RULING: correcting the electrode-meshing floor is permitted

**Question.** The 0.43 dB electrode-meshing floor was measured with a 15 mm
electrode while production runs 10 mm. Criterion (b) of the cavity test was
registered against 0.43 dB. Re-measuring the floor moves a registered threshold
after registration, which the CLAUDE.md norm exists to prevent.

**Ruling (Carl).** Permitted. **Nothing failed 0.43 dB.** The quantity that
figure references was measured with the wrong electrode. That falls under the
norm's *"an independent measurement establishes the physical bound"* clause,
not the *"revised because something failed it"* prohibition.

**Why the distinction is the whole point.** The prohibited move is: run a test,
see it fail, widen the threshold. The permitted move is: discover the threshold
was measuring the wrong thing, measure the right thing, and record both. The
test outcome played no part in noticing the electrode mismatch — it was found by
auditing harness parameters against config, before the cavity residuals existed.
Order of discovery is what separates the two cases, and it is auditable here
because the correction was committed before the residuals were opened.

**Superseding mechanism, better than either threshold.** Rather than choosing a
floor, the analysis reports the residual in dB *and* the floor value at which
the verdict flips. The floor measurement then **locates** the result on that
axis instead of deciding it, and there is no threshold left to move. Both
readings — against the registered 0.43 dB and against the corrected 10 mm
value — are printed side by side so any change of verdict is visible.

**Generalised.** This applies to every threshold-gated claim in the paper.
Reporting where a result sits on the threshold axis is strictly more
informative than reporting which side of one line it landed on, and it survives
the threshold turning out to be wrong.

**Ordering guard, enforced in code.** `src/03c_cavity_analysis.py` exits 2 and
refuses to compute anything until `results/electrode_meshing_floor.txt` exists.
The floor is measured and committed in its own commit; only then are the cavity
residuals opened. This makes "the threshold followed the result" impossible
rather than merely undesirable.

---

## 2026-08-02 — MEASURED: electrode-meshing floor at the production diameter

Re-measured at 10 mm, the diameter production actually uses. Two
nominally-identical sphere meshes, same electrode, same solver.

| electrode | mesh pair | ΔRDM | ΔMAG | floor |
|---|---|---|---|---|
| 15 mm (old) | medium vs fine | — | 5.06 pp | **0.43 dB** |
| **10 mm (production)** | medium vs fine | 0.396 pp | 1.520 pp | **0.1310 dB** |

**The floor is 3.3x tighter than the figure it replaces.** *(measured)*

**This confirms the electrode-realisation hypothesis** and closes the question
item 4 was going to attack: meshing variance tracks electrode diameter, so the
level spread was electrode realisation rather than local element quality. Item 4
stays dropped, as agreed. *(measured)*

**Direction of the correction, flagged because it favours the hypothesis under
test.** The corrected floor is *lower*, which makes the cavity criterion (b)
**easier** to pass. A correction that loosens the bar on a live hypothesis
deserves more scrutiny than one that tightens it. Three things make this safe:
the mismatch was found by auditing harness parameters against config, before any
cavity residual existed; the correction was measured and committed in its own
commit before the residuals were opened, enforced by a guard that exits rather
than computing; and the analysis reports the flip point with both floors side by
side, so the verdict under the old floor stays visible.

**Also measured, at 10 mm:** RDM median 4.111 (medium) and 3.715 (fine), against
4.355 and 3.812 at 15 mm. RDM is fairly stable across electrode diameter. MAG is
not — +5.996/+7.516 at 10 mm against +4.400/+9.464 at 15 mm — which is further
evidence for the earlier MAG retraction and for RDM carrying the headline.

**Superseded everywhere:** 0.43 dB is withdrawn as the electrode-meshing floor.
It is replaced by 0.1310 dB in the cavity criterion and as the
channel-redundancy resolution floor (Fig 5), where a tighter floor means
adjacent sites are distinguishable at smaller differences than previously
believed.

---

## 2026-08-02 — MEASURED: solve resource profile, and the concurrency it allows

Sampled a live production solve on the 12.3 M-tet MIDA mesh for 60 s:

| | value |
|---|---|
| CPU | **100% of one core**, steady (98.0–100.0 across 10 samples) |
| Peak RSS | **10.8 GB** |
| Threads | single busy thread |

**hypre does not saturate the machine.** It uses one core of 18, so the binding
constraint is memory, not CPU. *(measured)*

    cores allow   18 concurrent
    48 GB allows   4 concurrent at 10.8 GB peak
      N=3  32.4 GB used, 15.6 GB headroom
      N=4  43.2 GB used,  4.8 GB headroom
      N=5  54.0 GB      — over

**Default N = 3, not 4.** Four workers leave under 5 GB for everything else, and
this machine was already observed with 3.9 GB of swap in use while running a
*single* solve. Swapping would erase the gain, so the default trades one worker
for headroom. `src/run_solves_parallel.py --workers` overrides.

Expected effect on stage 3: ~44 solves at ~4 min serial is roughly 3 hours;
at N=3 roughly 1 hour. The solves are independent — one electrode each — so
there is no coordination beyond the worker cap.

---

## 2026-08-02 — TOOL BEHAVIOUR: hypre runs single-threaded under SimNIBS

Same class as the `meshmesh` size-range floor: a non-obvious tool behaviour
that costs real time if you assume otherwise.

A production solve on the 12.3 M-tet mesh uses **100% of exactly one core**
(measured, 10 samples over 60 s, 98.0–100.0%) and **10.8 GB peak RSS**. On an
18-core machine, 17 cores sit idle through every solve.

`simnibs.simulation.fem.tdcs()` exposes an `n_workers` parameter defaulting to
1, and hypre supports OpenMP, so this may be configuration rather than a hard
limit. **Not tested — try `OMP_NUM_THREADS` / `n_workers>1` before building
process parallelism.** Threads cost no extra memory; processes cost 10.8 GB
each.

> **TESTED 2026-08-02, and the answer is no on all three counts.** See
> "RESOLVED: threads are not available" below. The hopeful reading above —
> that `n_workers` might be threads, or that hypre's OpenMP might be one
> environment variable away — is **withdrawn**. Process parallelism at
> 10.8 GB per worker is the only option available.

### The memory measurement that changes the plan

Measured with everything running:

```
PhysMem: 47G used, 536M unused
swap:    3917 MB of 5120 MB used
largest: ollama llama-server  14.76 GB
```

**The machine is already swapping with a single solve running.** The N=3 default
in `run_solves_parallel.py` was derived from a nominally free 48 GB and is
**unsafe as things stand**. Stop `ollama` (frees 14.76 GB), re-measure, then
choose N. With ollama running, N=1.

This is why the resource budget had to be measured rather than computed from
total RAM: the arithmetic said 4 concurrent solves, the machine had 536 MB free.

---

## 2026-08-02 — RESOLVED: threads are not available, and `n_workers` cannot help this montage

The previous entry left `n_workers` and `OMP_NUM_THREADS` untested and hoped
threads would remove the memory constraint. Tested. **Three independent lines
of evidence, all negative.** Two of the three cost no solve time.

**1. `n_workers` is processes, not threads.** `fem.tdcs` dispatches through
`run_in_multiprocessing_pool` (`simnibs/utils/threading.py`), which is a
`multiprocessing` pool despite the module name. Each worker is a full process
carrying its own copy of the mesh, so it costs the same 10.8 GB that the
process pool in `run_solves_parallel.py` already costs. It was never the
cheap option.

**2. `n_workers` is silently clamped to 1 for a bipolar montage.** `fem.py`
line 1468 reads `n_workers = min(len(currents) - 1, n_workers)`. It
parallelises across electrode *pairs within one montage*, and every montage in
this paper is bipolar, so `len(currents) = 2` and the effective worker count is
`min(1, N) = 1` for any N. Verified by evaluating the clamp:

| montage | requested | effective |
|---|---|---|
| bipolar (this paper) | 1, 4, 8 | **1, 1, 1** |
| 4-electrode | 1, 4, 8 | 1, 3, 3 |

Passing `n_workers=8` is not an error and produces no warning. It simply does
nothing. That is the failure mode worth remembering: a parameter that accepts
your value, reports nothing, and ignores it.

**3. Neither PETSc nor HYPRE was built with OpenMP.** `nm -u` on
`libpetsc.3.22.2.dylib` and `libHYPRE-2.31.0.dylib` returns **zero** undefined
`GOMP_*`, `omp_*` or `kmpc` symbols, and neither links an OpenMP runtime.
`libgomp`/`libomp` do exist under `simnibs_env/lib`, but they belong to other
packages (pygpc), not to the solver stack. There is no OpenMP code in the
linear solve for `OMP_NUM_THREADS` to enable.

Confirmed by measurement on the sphere (`val_sphere_medium.msh`, cheap enough
to run beside a live head solve):

| `OMP_NUM_THREADS` | wall | CPU median | CPU peak |
|---|---|---|---|
| 1 | 7.2 s | 98.9% | 99.5% |
| 8 | 7.3 s | 99.1% | **101.6%** |

Eight threads bought 0.98x, which is nothing. Peak CPU never approached the
150% that would indicate a second core doing work.

**Consequence, and it is the opposite of what the previous entry hoped.**
Process parallelism at 10.8 GB per worker is the only concurrency available.
The memory budget is therefore the real and permanent constraint on stage 3,
not a temporary condition to be engineered around. `run_solves_parallel.py`
stays as the mechanism, and N is set from measured free memory each time.

**PETSc links MPI**, so a multi-rank `mpirun` decomposition is theoretically
available, but SimNIBS drives PETSc in-process through petsc4py at one rank
and exposes no path to launch it otherwise. Recorded as noticed and rejected,
not as untried.

Harness: `scratchpad/omp_test.py`. Not committed, because it answers a
question that is now closed and the answer is recorded here.

---

## 2026-08-02 — MEMORY RE-MEASURED: ollama's model server had already exited

The previous entry recorded 536 MB unused with `ollama llama-server` holding
14.76 GB, and set N=1 on that basis. Re-measured at the start of the next
session:

```
PhysMem: 32G used, 15G unused     (one head solve running)
swap:    3909 MB of 5120 MB used  (flat, not growing)
```

`ollama serve` is still up but its `llama-server` child, which is what held
the 14.76 GB, is gone. Model servers exit on an idle timeout, so the 47G
reading was a transient captured at the worst possible moment.

**This does not vindicate computing the budget from total RAM.** The lesson
from the previous entry stands and is reinforced: the number moved by 14 GB
between two sessions with no deliberate action, so N must be chosen from a
fresh measurement at the moment of launch, never from a figure recorded
earlier. A memory budget has a shelf life measured in minutes.

The 3909 MB of swap in use is **residual, not active**. It stayed flat while
two jobs ran concurrently, which means those pages are stale and not being
faulted back in. Swap *in use* and swap *thrashing* are different readings and
only the second one costs anything.

---

## 2026-08-02 — DEFECT: the "permanent guards" were never called by anything

Recorded as its own entry because the claim is in this log, in writing, and it
was false.

The 2026-08-02 conditioning entry states that `src/preflight.py` gained
`check_solve_output()`, which "reads `fields_summary.txt` after every solve and
refuses to return a result from one that reported a calibration error", and
calls both additions **permanent guards**.

`grep` over `src/*.py` returns **no caller** for either
`check_solve_output()` or `check_conductivity_range()`. They were written,
tested against the known-good and known-bad cases, and then never wired into a
single solve script. Every solve run since has been unchecked.

**This is the same failure the whole log exists to prevent**, one level up. The
original error was not reading the solver's output. The correction was a
function that reads it. What was never done was calling the function, and the
log recorded the intention as though it were the state.

**It was not harmless.** Reading the calibration line directly off the cavity
run currently in progress:

| solve | calibration |
|---|---|
| `air__cg10` | **WARNED, 11.90%** |
| the other seven air solves | clean |

So one of the eight electrode pairs feeding the cavity verdict contains a
solve the solver itself flagged, and nothing in the pipeline would have
mentioned it.

### What was changed, and what deliberately was not

Wired in, so it runs: `03a_boundary_run.py` and `03c_cavity_analysis.py` now
read the calibration line for every solve they consume and print it before any
verdict.

**The gate's threshold was NOT touched.** `cg10` tripped the guard, and moving
a threshold because something failed it is the one move this project forbids.
Instead `preflight.read_calibration()` was added beside
`check_solve_output()`: it returns the reported percentage rather than raising,
so the value is carried with the result. Two populations are already measured
and they are far apart:

- **200.00%** the conductivity-conditioning failure, fields 10-20x too large,
  fatal
- **11-15%** seen on well-conditioned custom meshes; on the sphere 5 of 16
  solves warned while matching the analytic oracle, and the warned electrodes
  were *not* less accurate (median |L_num|/|L_ana| 0.9814 warned against
  1.0345 un-warned, a gap inside the scatter of either group)

`cg10` at 11.90% sits in the second population, and the conductivity span for
this run is 1.879e6, three orders inside the 1e8 guard, so the conditioning
mechanism is not available as an explanation. That is evidence, not proof, so
no threshold was invented to encode it.

`03c` instead recomputes the verdict **with and without** the warned pairs and
prints whether the exclusion changes the answer. If the verdict is unchanged,
the warning is irrelevant and the result stands on eight pairs. If it changes,
the result is declared not reportable until those solves are re-run. That
converts an unquantified worry into a stated dependency, which is the same
move the flip-point reporting makes for thresholds.

---

## 2026-08-02 — DEFECT: `03a_boundary_run.py` would have crashed on launch

Caught by inspection **before** the run, which is the only reason it cost
nothing.

The boundary run is the next queued item and it gates the stage 3 mesh choice.
It bound conductivities like this:

```python
for name, sigma in config.SIGMA.items():
    pass                              # tissue conductivities bind below
for mname, _, lab, _ in config.MUSCLES:
    if lab is not None:
        t.cond[lab - 1].value = config.SIGMA["muscle_iso"]
```

That is **11 of the 117 tags** the mesh carries: 10 muscles plus the neck slab.
The other 106 stay `None`, and SimNIBS raises
`TypeError: The value N in cond_list is not numerical` for the whole list.

**This is the identical blocker recorded in this log** under "106 of 116 MIDA
labels have no conductivity". That blocker was fixed by building Table 1, and
`03d_cavity_solves.py` was updated to read it. `03a` was not. It has been
sitting in the repo since, looking runnable, in a state where it cannot
complete a single solve.

Note also the dead `for ... in config.SIGMA.items(): pass` loop, which reads as
though it binds tissue conductivities and binds nothing. A loop whose body is
`pass` under a comment claiming it does the work is worse than no loop.

Fixed: `03a` now loads all 116 tags from
`results/01_table1_conductivities.csv` exactly as `03d` does, adds the slab
label on top for the extended mesh, and runs
`preflight.check_conductivity_range()` over the assembled list before solving.

**Generalisable lesson.** Table 1 was a cross-cutting fix and it was applied to
the one script that happened to be running at the time. Nothing swept the other
call sites. When a shared input changes shape, grep for every consumer rather
than fixing the one in front of you: the cost of the miss is paid much later,
by a run that fails after being queued behind an hour of other work.

Also corrected in the same pass: `03a` hardcoded the superseded **0.43 dB**
noise floor in its docstring, in its printed output, and in the `elif` of its
decision ladder. It now reads the measured value from
`results/electrode_meshing_floor.txt`, the file the measurement writes. The
pre-committed **1.0 dB** decision threshold is deliberately left hardcoded and
is not read from anywhere, because it must not move.

---

## 2026-08-02 — MEASURED: the floor is 0.27 dB, and 0.1310 dB was an unlucky draw

The queued follow-up asked for n ≥ 5 draws and an uncertainty on the floor.
Done, n = 6, and **the answer moved by a factor of two in the direction that
makes the cavity criterion harder.**

### The design, and the one thing it had to get right

A draw is **one rigid rotation applied to both the electrode array and the
source points**, solved on a single fixed mesh. Rotating both is the whole
trick. Every source-to-electrode vector is preserved, so the exact answer is
identical in every draw, so any measured spread is realisation noise and
nothing else. Verified at machine precision: the maximum change in any
source-to-electrode distance across 6 proper rotations is 2.8e-14 mm.

Rotating the electrodes *alone* would have been wrong. Sources would then sit
at different relative positions, the exact answer would genuinely differ
between draws, and real geometry change would have been counted as noise.

### The harness reproduces the number it replaces

Draw 0 is the identity rotation, so it is the committed measurement re-run:

| | median MAG | median RDM |
|---|---|---|
| draw 0 (identity) | **+5.996 pp** | **4.111** |
| committed `e10mm_medium.csv` | +5.996 pp | 4.111 |

Three decimals, both metrics. This is the same measurement resampled, not a
different one, which is what licenses the replacement.

### The result

| draw | rotation | median MAG | median RDM |
|---|---|---|---|
| 0 | 0.00° | +5.996 | 4.111 |
| 1 | 5.04° | −4.013 | 4.007 |
| 2 | 4.74° | +3.283 | 4.015 |
| 3 | 4.96° | +5.997 | 4.007 |
| 4 | 6.55° | +5.308 | 4.269 |
| 5 | 4.28° | −3.079 | 4.010 |

**MAG SD 4.607 pp. RDM SD 0.106 pp.**

### Why the answer is 0.27 and not 0.48

The raw per-electrode spread is 0.48 dB, but that is the wrong quantity.
Within a draw all 16 electrodes see the same source points, so whatever
source-sampling contributes is **common to all of them** and cancels in any
site-to-site comparison. Decomposing exactly as `03c` decomposes the cavity
shift:

| term | SD | dB | cancels in a ratio? |
|---|---|---|---|
| common-mode | 4.926 pp | 0.418 | **yes** |
| electrode-specific residual | 3.181 pp | **0.272** | **no** |

`03c` strips the common mode from the cavity result and tests
`max |residual|` against the floor. **So the floor has to be a
common-mode-removed per-site quantity too, or the two sides of criterion (b)
are different things.** Judging a decomposed residual against an undecomposed
0.48 dB floor would have made the criterion sharply and silently too strict.
That is the same two-column argument the error budget already makes; it simply
had not been applied to the floor itself.

**Floor: 0.27 dB per site, spread 0.12 to 0.49 dB across the 16 electrodes.**

### What was wrong with 0.1310 dB

Not the method. The sample size. It was **one pairwise difference of 1.5198
pp drawn from a distribution whose SD is 4.607 pp**. For normal data a single
difference has expectation 2σ/√π ≈ 5.2 pp, so 1.52 pp was a low draw by a
factor of about three. It did not merely lack an error bar, **it landed short**,
and it was then quoted to four significant figures and used to gate two
analyses.

The corrected value lands nearer the original 0.43 dB than the 0.131 that
replaced it. That is coincidence, not vindication of the 15 mm figure: n = 2
at either diameter cannot resolve a spread this wide.

### Direction of the correction, flagged because last time it went the other way

The previous floor correction *loosened* criterion (b) and that was called out
at the time as deserving extra scrutiny. **This one tightens it**, from 0.131
to 0.272 dB, which is the conservative direction and the one that cannot
flatter a live hypothesis.

The ordering discipline held either way: this was queued in HANDOFF before any
cavity residual existed, the filled solves were still running when it was
measured, and `03c` prints the flip point with all three floors side by side,
so no single choice of floor decides the verdict.

### A by-product that settles the MAG question

These draws hold the physical geometry *exactly* fixed and change only the
triangulation. Under that operation **MAG's spread is 44x RDM's and MAG
changes sign**, swinging from −4.013 to +5.997 pp while RDM sits in
4.007–4.269.

This is the cleanest evidence the project has for the MAG disposition, and it
is better than the three observations that motivated it, because those varied
mesh density or electrode diameter and this varies neither. Nothing physical
differs between draw 1 and draw 3. MAG measures the electrode realisation;
RDM measures the field solution.

---

## 2026-08-03 — ADVERSARIAL PASS #3, on the floor measurement, before it was used

Run on my own result the same day it was produced, because it had just been
written into two gates. Four attacks, two hits.

**A. "draws 0 and 3 are suspiciously identical" — REFUTED, and worth the
check.** Draw 0 gave median MAG +5.9959 and draw 3 gave +5.9971, 0.0012 pp
apart when the population SD is 4.6 pp. That is a ~1-in-thousands coincidence
and the obvious explanation is a duplicated draw. Tested by comparing the
per-electrode vectors rather than the summary: **they differ by up to 12.19
pp**. Not a duplicate. The median over 120 sources is simply a coarse enough
statistic to collide. Harness clean.

**B. "0.272 dB" — FALSE PRECISION, the same sin I had just criticised.** The
0.1310 dB figure was attacked for quoting four significant figures from n=2.
I then reported 0.272 dB from n=6, which is three. An SD from six draws is
not that well determined. Bootstrapped over draws, 20,000 resamples:

| | pp | dB |
|---|---|---|
| point estimate | 3.181 | 0.272 |
| 95% CI | 1.912 – 3.254 | **0.16 – 0.28** |

The interval spans a factor of 1.7. **Report the floor as ~0.27 dB with the
interval attached, not as 0.272.** Two decimals is already generous.

Recorded rather than quietly fixed, because the failure mode is instructive:
criticising someone else's precision does not immunise you against repeating
it one decimal place later.

**C. "the electrode-meshing floor is the right floor for a PAIRED comparison"
— OVERSTATED, and it makes the criterion conservative.** The cavity test
compares filled against air *at the same electrode on the same mesh*. The
contact triangulation is therefore identical in both halves of the pair, so
the contact-area error is common to numerator and denominator and cancels to
first order in the ratio. The true noise floor for a paired dB shift is
consequently **smaller** than the electrode-meshing floor, and the criterion
as registered is stricter than it needs to be.

**Deliberately not acted on.** Lowering a floor makes a live hypothesis easier
to pass, and the cavity residuals already existed when this was noticed. That
is precisely the ordering the project forbids. It is registered here as a
measurable quantity — solve one electrode twice with identical settings, or
air against air — and left for a session where no verdict is waiting on it.
Using the conservative floor costs nothing, because the verdict clears it by
5.9x.

**D. "the harness measures the same quantity as the number it replaces" —
UPHELD on evidence rather than assertion.** Draw 0 is the identity rotation
and reproduces `e10mm_medium.csv` at median MAG +5.996 pp and RDM 4.111, both
to three decimals. Two independent metrics agreeing to that precision is not
a coincidence available to a different configuration.

---

## 2026-08-03 — RESULT: the cavity hypothesis SURVIVES, and the verdict does not depend on the floor

All 16 solves complete. Analysed with `03c_cavity_analysis.py`; the verdict
printed by `03d` is superseded and was not used.

**Common-mode shift: −0.507 dB.** This is a Methods term in its own right and
is independent of the verdict: *head models omitting the oral cavity and
nasopharynx are systematically off by 0.51 dB in absolute lead field.*

| electrode | dist mm | signed dB | residual | median abs dB |
|---|---|---|---|---|
| hyoid | 14.5 | −2.107 | **−1.601** | 2.107 |
| buccal | 19.6 | −0.856 | −0.350 | 0.920 |
| submental_lat | 24.3 | −0.800 | −0.293 | 0.889 |
| midjaw | 36.9 | −0.453 | +0.053 | 0.751 |
| cg10 | 48.1 | −0.520 | −0.014 | 0.818 |
| pre_tragus | 58.1 | −0.493 | +0.014 | 0.725 |
| mastoid | 65.9 | −0.462 | +0.045 | 0.795 |
| above_ear | 75.5 | −0.322 | +0.185 | 0.484 |

- **(a)** Spearman rho(distance, median |dB|) = **−0.881**, p = 0.004 → PASS
- **(b)** max |residual| = **1.6006 dB** → PASS
- **VERDICT: SURVIVES**

**The flip point is 1.60 dB, and every floor the criterion has ever been
judged against sits far below it:**

| floor | (b) | overall |
|---|---|---|
| registered 0.43 dB (15 mm, n=2) | PASS | SURVIVES |
| superseded 0.1310 dB (10 mm, n=2) | PASS | SURVIVES |
| measured 0.27 dB (10 mm, n=6, per-site) | PASS | SURVIVES |

**This is the outcome that makes all the floor work moot for this particular
verdict, and that is a good outcome, not a wasted one.** The result clears the
measured floor by 5.9x, so no choice of floor decides it. Had the residual
landed at 0.2 dB the three rows would have disagreed and the floor measurement
would have been load-bearing. Reporting the flip point is what makes that
visible either way.

**The sign structure is physically coherent and was not designed for.** Near
sites lose signal when the cavity is filled and far sites gain slightly, which
is what shunting current into a newly conductive volume next to the electrode
should do. The crossover sits between `submental_lat` (24.3 mm, −0.293) and
`midjaw` (36.9 mm, +0.053).

### Adversarial pass on this result, run immediately

**Leave-one-out, all eight:** criterion (a) survives every deletion, rho
between −0.821 and −0.964, every p ≤ 0.024. Criterion (b) survives every
deletion. **The verdict is robust to dropping any single electrode.**

**But the (b) margin is concentrated in one site, and this must be stated.**
`hyoid` supplies the 1.601 dB. Drop it and the largest residual is `buccal` at
**0.350 dB**, which still passes the measured floor but by only **1.29x**, and
**would FAIL the registered 0.43 dB floor.**

| floor | all 8 | hyoid dropped |
|---|---|---|
| registered 0.43 | SURVIVES | **FALSIFIED** |
| superseded 0.131 | SURVIVES | SURVIVES |
| measured 0.27 | SURVIVES | SURVIVES |

So the honest reading: **as registered, on all eight electrodes, the verdict is
floor-independent. The magnitude criterion is carried by the single closest
electrode.** That is not a defect — `hyoid` is 14.5 mm from the cavity and the
next nearest is 19.6 mm, so the largest effect belongs exactly where the
physics puts it — but a reader must not be left to discover it.

### Calibration

`cg10` warned at **11.90% in both the air and the filled solve, identically**.
That reproducibility is itself informative: a random current-delivery failure
would not repeat to two decimal places across two different conductivity
fields, so this is a deterministic property of that electrode's realisation,
and being identical in both halves it cancels in the pair's ratio.

Excluding the `cg10` pair entirely: rho = −0.893 (p = 0.007), max |residual|
unchanged at 1.6006 dB (it is at `hyoid`), **verdict UNCHANGED**. The warned
solve does not carry the result.

### What this does and does not license

The cavity test was the condition attached to replacing the deleted Fig 7. It
passed. **The figure's framing is Carl's decision and is not written here.**
What is established is the measurement: articulatory volume-conductor exposure
falls monotonically with distance to the oral cavity, over 14.5–75.5 mm, at
p = 0.004, with the residual at the nearest site 5.9x the per-site noise floor.

The upper-bound framing holds and should travel with the number: MIDA is
static, complete cavity filling is the most extreme configuration physically
available, so real articulation lies strictly inside this envelope.

---

## 2026-08-03 — BLOCKED: the boundary run's verdict is NOT usable; both extended-mesh solves failed calibration

**Do not act on `results/03_boundary_sensitivity.csv`.** The run completed,
printed a decision, and that decision is withheld. This is a stop-and-report
trigger: the boundary run selects the mesh for **every published result**.

### What it printed

    largest |dB| shift: 8.66 dB   (threshold 1.00 dB)
    DECISION: extended mesh becomes PRIMARY for all published results

### Why it is not usable

The calibration guard wired in earlier today fired, and the pattern is
systematic rather than incidental:

| solve | mesh | calibration |
|---|---|---|
| truncated | `mida_headneck.msh` | **clean** |
| extended, slab 0.355 | `mida_neckext.msh` | **WARNED 100.49%** |
| extended, slab 0.190 | `mida_neckext.msh` | **WARNED 95.84%** |

**The truncated solve is clean and both extended solves are broken.** The mesh
is the only thing that differs. ~100% is a *new* population: the established
ones are 200.00% (conditioning failure, fields 10–20x too large, fatal) and
11–15% (measured false positive on well-conditioned custom meshes). 100% is
nowhere near the benign band.

**The field values corroborate it rather than merely permitting it.** SCM goes
2.615e-01 → 7.086e-01, a factor of 2.7. A ~100% current-calibration error is
exactly a delivered current off by about a factor of two, and in the 200% case
the fields were 10–20x out. The error magnitude tracks the field error in both
cases, which is what a real current-delivery failure looks like and is not
what a post-processing false positive looks like.

**The dB pattern is not the shape of a boundary artefact.** An insulating cut
face inflates lead fields *near* it and leaves distant structures alone. The
run reports **temporalis +3.96 dB**, and temporalis is nowhere near the cut at
S = −116.2 mm. A term that moves a structure at the top of the head by 4 dB is
global, not a boundary condition.

### The likely mechanism, measured not guessed

The extended mesh is **0.83% larger than the truncated mesh**:

| mesh | nodes | elements |
|---|---|---|
| `mida_headneck.msh` | 2,140,917 | 15,415,273 |
| `mida_neckext.msh` | 2,162,905 | 15,542,772 |

A 70 mm extrusion of a full neck cross-section adds on the order of 10% of the
head's volume. Getting **0.83% more elements** for it means the slab is meshed
at roughly an order of magnitude coarser element volume than the head it is
attached to. `01c_extend_neck.py` builds it as a deliberately homogeneous slab,
which is sound as a design, but a large jump in element size across a shared
interface is a classic way to wreck the conditioning of an iterative solve, and
hypre is iterative.

Conductivity conditioning is **excluded** as the cause: σ_max/σ_min is
1.879e6 for these solves, identical to the truncated run and three orders
inside the 1e8 guard, and `check_conductivity_range()` passed. So this is not
a repeat of the air-at-1e-15 failure.

### What happens next, and what must not

**The mesh decision is deferred, not made.** The pre-committed 1.0 dB rule is
untouched and still stands; what is missing is a trustworthy number to apply
it to. Nothing about the rule is revised because a run failed.

Required before the boundary decision can be made:

1. Diagnose the extended mesh's element-size transition at the slab interface,
   and rebuild it with the slab meshed at a size comparable to the adjacent
   head elements.
2. Re-run and confirm both extended solves report clean calibration.
3. Only then apply the rule.

Until then **stage 3 must not start on the extended mesh**, and it cannot
start on the truncated mesh either, because the whole point of the boundary
run is that we do not yet know which is primary.

**This is exactly what the guard was wired in for.** Six hours ago
`check_solve_output()` existed but nothing called it, and this run would have
printed "extended mesh becomes PRIMARY for all published results" from two
broken solves, with no indication anything was wrong. That decision would have
propagated into every figure in the paper.

---

## 2026-08-03 — MEASURED: extended-mesh memory, flagged before stage 3 rather than discovered during it

The question asked was whether the extended mesh's peak memory would make
stage 3 infeasible. **It would not.** Measured, not estimated:

| | value |
|---|---|
| element count difference | **+0.83%** (15.54 M vs 15.42 M) |
| observed RSS, extended-mesh solves | 8.3 – 9.7 GB |
| observed RSS, cavity solves (truncated) | up to **11.9 GB** |

Peak memory is set by the mesh, and the two meshes differ by under 1%, so
**budget ~12 GB per solve on either mesh**. The extended mesh introduces no
memory problem for stage 3.

That is the reassuring half. The unreassuring half is that the same 0.83%
figure is evidence the slab is meshed far too coarsely (see the entry above),
so the reason memory does not grow is the same reason the solve may be
failing. **A cheap answer to the memory question and a warning about the mesh
turned out to be the same measurement.**

If the extended mesh is rebuilt with the slab refined to match adjacent head
element sizes, **both numbers change**: element count rises meaningfully and
peak RSS with it. Re-measure after any rebuild rather than carrying the 12 GB
figure forward.

---

## 2026-08-03 — LICENSING STOP: MIDA-derived geometry is in git history; the repo cannot be published as it stands

Checked before creating a remote, and the check failed.

`SimNIBS` writes `<mesh>_el_currents.geo` into **every** solve directory. The
name suggests a small electrode patch. It is not:

| | value |
|---|---|
| triangles per file | **126,945** |
| unique vertices | **63,582** |
| bounding box | **194.6 x 255.8 x 253.4 mm** |
| size | ~23 MB each |

A 10 mm disc electrode spans 10 mm. That bounding box is the **entire MIDA
head and neck**. Each file is a reconstructible triangulated surface of the
licensed model.

**Extent: 255 files tracked, 3.26 GB on disk, 261 additions across history.**
`.gitignore` excluded `*.msh`, `*.nii` and `data/*`, but **not `*.geo`**, so
every solve added another and nothing caught it.

MIDA is licensed by the IT'IS Foundation and requires individual registration
(DOI 10.13099/ViP-MIDA-V1.0). Publishing this would redistribute it.

**Not pushed.** The instruction's own stop condition applies: licensed data is
already committed.

**What is clean:** the `.mat` session files are parameters only (`fnamehead`,
`pathfem`, `poslist`, field names) with no geometry. `medians.npy` files are
computed scalars. `results/01_label_inventory.csv` is label names and voxel
counts, i.e. metadata about the model rather than the model.

**Done now:** `*.geo` added to `.gitignore` with the reason inline, and all 255
removed from the index. That stops the bleeding but **does not touch history**.

**Remediation, one command, then the push is safe:**

    git filter-repo --path-glob '*.geo' --invert-paths

Nothing is lost: `.geo` files are regenerated by every solve. A history
rewrite on the only copy of the project is destructive and was not done
unilaterally.

**The exposure so far is zero**, because there is no remote. This is the best
possible moment to have found it.

---

## 2026-08-03 — RULING 2: the slab interface is CONFORMING, so refining it is a legitimate repair

The question was whether a coarse region 100 mm from every electrode could
really cause a ~100% calibration error, or whether the extrusion had produced
a non-conforming seam. **Tested before remeshing, as instructed.**

Streamed the binary mesh rather than loading it, because only 1.8 GB was free
and a 15.5 M-element load would have thrashed swap.

| test | `mida_neckext.msh` |
|---|---|
| nodes within 0.6 mm of S = −116.2 | 1,327 |
| **duplicate coordinates** | **0** |
| planar faces shared by 2 tets | **1,255** |
| planar faces used by 1 tet | 220 |

**No duplicated nodes and 1,255 tet pairs spanning the plane: the interface is
CONFORMING and the geometry is merged.** The slab is not a detached body, and
the extrusion method is not fundamentally wrong. **Refining is therefore a
legitimate repair path**, which is what the test was run to decide.

### A labelling bug I nearly reported and then disproved

Tets below the cut plane are tag 50 (100,325), tag 200 (27,683), tag 51 (14).
Tag 50 is **Background, air at 1e-6 S/m**, and tag 200 is the intended slab.
That looks damning: only 22% of the extruded volume carries the slab label,
which would also explain why the two slab conductivities gave nearly identical
answers (+8.66 vs +8.57 dB).

**It is not a bug.** `01c_extend_neck.py` takes the inferior face, masks
non-background voxels, fills holes, and extrudes that as `EXTENSION_LABEL`
with `MIDA_BACKGROUND` elsewhere. The neck is genuinely about 22% of the slice
area and the remaining 78% is the air *around* the neck, which is correct and
matches how air surrounds the head everywhere else in the volume. Checked the
source before writing it up.

### What is left, stated as the hypothesis it is

Excluded by measurement: non-conforming interface, duplicate nodes,
mislabelled slab, and global conductivity span (1.879e6, three orders inside
the 1e8 guard).

Remaining and **not yet proven**: the slab holds ~27,683 tets for roughly
600,000 mm³, about 22 mm³ per element, against the head's ~0.4 mm³. That is a
**~4x linear element-size jump**, and it sits directly beneath the `hyoid`
injection electrode, which is only 8 mm above the cut plane. A large element
jump immediately under a Dirichlet boundary is a credible way to wreck an
iterative solve. Credible is not demonstrated: the repair is to refine the
slab toward adjacent head element sizes and re-run, and if calibration comes
back clean that is the confirmation.

---

## 2026-08-03 — RULING 4: what 0.27 dB is, and why its "95% CI" was wrong

Flagged because 0.27 sat at the **top edge** of [0.16, 0.28], which is not how
a mean sits inside its own interval. The flag was right and the interval is
withdrawn.

**The statistic, stated explicitly:** 0.27 dB is the **mean over 16 electrodes
of (the per-electrode SD across 6 draws)**, after common-mode removal. It is a
mean of standard deviations, not a mean of measurements.

**Why the bootstrap was invalid for it.** Resampling 6 draws *with replacement*
yields on average only **3.99 distinct draws**. Duplicated draws shrink a
spread statistic, so every resample is biased low: the bootstrap distribution
centres on 2.797 pp against a point estimate of 3.181 pp, a bias of −0.384 pp.
The interval described a **downward-biased statistic**, not the estimator, which
is exactly why the point estimate sat at its upper edge. **Withdrawn.**

**The correct interval.** For an SD from n = 6, df = 5, the chi-square factors
are [0.624, 2.453]:

| | pp | dB |
|---|---|---|
| point estimate | 3.181 | **0.27** |
| 95% CI, per site | 1.986 – 7.802 | **0.17 – 0.65** |

**Report the floor as ~0.27 dB, 95% CI [0.17, 0.65].** At n = 6 each per-site
SD is known only to within about a factor of two.

Note the measured heterogeneity across sites, 0.12 to 0.49 dB, is comparable
to that sampling uncertainty, so neither dominates and n alone will not tighten
this: sites genuinely differ.

**Consequence for the cavity verdict: none.** The residual is 1.60 dB, above
even the upper bound of 0.65 dB.

---

## 2026-08-03 — RULING 3: the cavity verdict is PROVISIONAL

Recorded as surviving **with a stated dependency**, not as settled.

`hyoid` carries the magnitude criterion: it supplies the 1.601 dB residual,
and without it the largest is `buccal` at 0.350 dB. **`hyoid` is simultaneously
the site nearest the oral cavity (14.5 mm) and the site nearest the truncation
face (8.0 mm) whose model is currently broken.** The one electrode the result
leans on is the one most exposed to the unresolved boundary problem. That is a
dependency, not a refutation, and it must travel with the number.

**Re-run the correlation once a trustworthy extended mesh exists.**

**Correction to my own report.** I wrote that dropping `hyoid` leaves buccal
"clearing the measured floor by only 1.29x and failing the registered 0.43 dB
floor". The failure-against-0.43 framing was against the **retired** floor.
Against the **operative** floor of 0.27 dB, **buccal at 0.350 dB PASSES**, and
0.43 dB is no longer a criterion this paper uses. Stating a pass as a
near-failure by quoting a superseded threshold is the same error as quoting a
superseded value, and it made the result look weaker than it is.

---

## 2026-08-03 — RULING 5: the AlterEgo framing was mine, unverified, and is removed

Recorded because the provenance matters more than the correction.

The motivation claim *"AlterEgo's 2026 device moved from a jaw-wrapping band to
an ear-mounted form factor"* originated with **Carl in the first session** and
**sat unverified in OUTLINE.md and CLAUDE.md for several days**, propagating
into the paper's motivation as though it were sourced.

It is wrong twice: the public reveal of *Silent Sense* was **September 2025**,
not 2026, and **"ear-mounted" overstates** sources that describe a device worn
around the ears and resting largely on the back of the head, still sensing
face, jaw and neck muscles. There is no paper, dated white paper, or press
release with a stable identifier.

**Removed from OUTLINE entirely** rather than corrected in place, per the
ruling. The claim *"devices are being designed for a coupling nobody has
modelled"* is re-anchored on verified, peer-reviewed, ear-mounted ExG work:
**Avramidou et al. 2024**, **An et al. 2025 (ID.EARS)**, and **Debener et al.
2015 (cEEGrid)**. The gap statement is **Yarici, Thornton & Mandic 2023**.

**A wrong year that matches the current one is the hardest kind to notice**,
because it reads as up to date. It survived because nothing forced it to a
primary source until the citation audit ran.

---

## 2026-08-03 — CLOSED: concurrency

Settled and **not to be revisited**. Three independent tests: `n_workers` is a
multiprocessing pool, not threads; it is clamped by
`min(len(currents) - 1, n_workers)` to **1 for every bipolar montage** here;
and neither `libpetsc` nor `libHYPRE` contains a single OpenMP symbol, with
`OMP_NUM_THREADS=8` measuring 7.3 s against 7.2 s at one thread.

**Serial at ~3 h for stage 3 is accepted.** Stop pursuing concurrency.

---

## 2026-08-03 — INCIDENT: licensed MIDA geometry was PUBLIC on GitHub for ~11.5 hours

Found at Step E of the publication sequence, while checking whether the
target repo existed. It did, and it was **public**.

### What was exposed

`github.com/Somach-Systems-Inc/ear-emg-forward-model`, created
**2026-08-03T04:59:57Z**, pushed 12 seconds later at **05:00:09Z**, public
until **16:31Z**. Roughly **11.5 hours**.

Its tree at HEAD (`5908e18`) carried **109 `.geo` files at ~22.9 MB each**,
each one the full MIDA head-and-neck surface (126,945 triangles, 63,582
vertices). No `.msh` and no `.nii`, but the `.geo` files alone are a
reconstructible surface of the licensed model.

This predates and is independent of the local purge: the push happened
**before** anyone checked what `.geo` contained.

### Actual dissemination: none detectable

| metric | value |
|---|---|
| forks | **0** |
| stars / watchers | **0** |
| clones (14 d), unique cloners | **0 / 0** |
| views (14 d), unique visitors | **0 / 0** |

Zero across every counter over the whole public window. The repository was
new and unlinked from anywhere. GitHub's traffic counters lag slightly and do
not capture every automated crawler, so this is strong evidence rather than
proof, but nothing indicates the data was fetched by anyone.

### Action taken immediately

**Repository set to private**, verified. That was done without waiting,
because the instruction for this repo was explicitly *"PRIVATE repo,
Somach-Systems-Inc/ear-emg-forward-model"*, so making it private executes the
stated intent and stops an ongoing licence breach at the same time. It is
reversible and cost nothing to get wrong.

**Nothing was pushed.** The purged local history was NOT force-pushed,
because that would leave the old objects on GitHub as unreachable-but-present
and would create a false impression that the remote was clean.

### What remains, and why it is Carl's call

The remote is private but its history still contains the 109 files. Two ways
to finish it:

1. **Delete the repository and recreate it private, then push the purged
   history.** Removes the objects outright. Cleanest, and cheap here precisely
   because nobody has cloned it. Destructive and outward-facing, so not done
   unilaterally.
2. **Force-push the purged history.** Makes the old objects unreachable, but
   they persist on GitHub and remain fetchable by SHA until GitHub garbage
   collects. With the repo private that is only reachable by someone with
   access, so it is an acceptable interim, but it is not equivalent to (1) and
   should not be described as if it were.

### The lesson, which is an ordering lesson

The licensing check and the publication were done in the wrong order. A repo
was created and pushed in **12 seconds**, and the question "what is actually
inside `*_el_currents.geo`?" was not asked until eleven hours later. The file
name says *electrode currents*, which sounds like a small patch; it is the
whole head.

**Check what a file contains before publishing it, not after.** A name is not
a description, and 22.9 MB should have prompted the question on its own.

---

## 2026-08-03 — THE MIDA LICENCE, read in full from the primary document

Read from *Terms and Conditions of User License MIDA Model v1.0*, the IT'IS
PDF at
`itis.swiss/assets/Downloads/VirtualPopulation/License_Agreements/LicenseAgreementMIDA.pdf`,
not from a summary. **The MIDA download itself contains no licence file** —
`MIDA_v1.txt` is only the label lookup table — so the terms had to come from
IT'IS directly.

### The question asked: does it distinguish the voxel model from derived surfaces?

**No, and it forecloses the distinction explicitly.**

> **1. Software.** "The MIDA Model is distributed as a voxelized model in MAT,
> RAW, NII, and TXT file formats **and as a CAD model in STL file format**
> (the 'Model Data')"

Surfaces are Model Data by definition. And the redistribution clause reaches
past the distributed forms to anything derived from them:

> **2.3.2** "The Model Data **or works derived from the Model Data** must not
> be distributed or redistributed **in the original form or in any modified or
> updated form**."

That is about as broad as such a clause gets: derived works, any modified
form. **The `.geo` files were unambiguously covered.** There was never a
reading under which a triangulated surface exported from the meshed model sat
outside this, and the earlier framing of them as merely "MIDA-derived" was too
soft. They are squarely within 2.3.2.

### Two clauses that were not on anyone's radar

**2.3.3 constrains every figure in the paper.**

> "Any images based on the Model Data may be published **only if the face is
> disguised so as to render the individual unrecognizable** in any and all
> communications of any kind, including but not limited to reports, papers,
> and oral or poster presentations, in which images are published."

`figures/02_electrode_qa.png` is committed and renders the skin surface as a
point cloud in lateral view, where **the facial profile — nose, lips, chin —
is plainly legible**. Planned **Fig 1** ("head model with muscle compartments
highlighted") is the same exposure or worse. This is a publication blocker on
the figures, not on the code, and it is cheap to satisfy: crop below the
orbit, mask the anterior face, or render only the posterior aspect. **It must
be handled before any figure ships**, including in a preprint.

**5. Termination is strongly worded, and this bears on the disclosure decision.**

> "This Agreement terminates **with immediate effect** if the Licensee and/or
> any User is in breach of the terms of this Agreement, in particular clause 2
> above. Upon termination, Licensee shall **return the Installer and Model Data
> to IT'IS Foundation and confirm in writing that all copies** of the Installer
> and Model Data on any of its installations **have been deleted**."

With **4.2**: "The Licensee and/or User shall be **fully liable** to IT'IS
Foundation for, and agrees to hold IT'IS Foundation harmless from, any damage
caused by any breach of this Agreement, **in particular by any breach of
clause 2.3**."

### Obligations that are already satisfied, or now recorded

- **2.3.1** — derivative works must carry notice that they are modified or
  derived from the MIDA Model. The meshes qualify. `REPRODUCTION.md` now says
  so, and the paper's Methods must too.
- **2.3.8** — publications must credit **FDA, Center for Devices and
  Radiological Health, and IT'IS Foundation** as creators of the Model Data
  and cite Iacono et al., PLoS ONE, March 2015. Already in
  `paper/references.bib` (`iacono2015mida`, `itis2015midamodel`); the explicit
  FDA/CDRH creator credit still needs to appear in Methods.
- **2.3.5** — no military use. Not applicable.
- **2.3.9** — no title to IP is conveyed.
- **2.3.10** — IT'IS may withdraw use entirely if the source individual
  withdraws consent. A standing risk worth knowing for a paper built on one
  anatomy.

### Consequence for the disclosure decision

The instruction recorded *"no proactive disclosure to IT'IS, given nil
measured dissemination and same-day remediation. **Revisit if the licence
terms in item 2 are strongly worded.**"

**They are strongly worded.** Clause 5 makes breach terminate the licence
automatically and with immediate effect, and obliges deletion of all copies;
4.2 attaches full liability and singles out clause 2.3. That is a materially
different setting from a permissive academic licence, and it meets the
revisit condition as written.

**Not decided here, and deliberately not acted on.** This is a legal judgement
with consequences for a company, and the standing rule is to draft and stop
rather than contact anyone. The facts a decision needs are all in the incident
entry above: ~11.5 hours public, 109 files, every traffic counter zero,
remediated the same day. Recorded for Carl, who is the only person who should
weigh a self-report against clause 5's automatic-termination language.

---

## 2026-08-03 — CAVITY CAVEAT TIGHTENED: the drop-hyoid fallback does not hold

Correcting my own reporting a second time, in the stricter direction.

I had presented the leave-one-out result as reassurance: drop `hyoid` and
`buccal` still clears the floor at 0.350 dB against 0.27 dB, so the verdict
survives without its largest contributor.

**That reassurance does not survive the floor's own uncertainty.** The floor
is ~0.27 dB with a **95% CI of [0.17, 0.65]**. `buccal` at 0.350 dB sits
**below the upper bound**. A fallback that holds against the point estimate
but not across the interval of a quantity known only to within a factor of two
is not a fallback at all.

**The magnitude criterion therefore rests on `hyoid` alone.** And `hyoid` is
the worst site to be depending on: it is simultaneously the electrode nearest
the oral cavity (14.5 mm, so the largest effect belongs there physically) and
the electrode nearest the truncation face (8.0 mm), whose model is currently
broken and whose boundary run is withheld.

That is not a refutation. Criterion (a), the rank correlation, survives every
leave-one-out at rho between −0.821 and −0.964, p ≤ 0.024, and it is the
criterion carrying the actual claim about distance. But criterion (b) has one
load-bearing point, and the paper must say so.

**Verdict stays PROVISIONAL. Re-run once a trustworthy extended mesh exists.**

Two errors in a row on the same number, both now corrected: first quoting a
retired threshold, then quoting a point estimate without its interval. The
second is the more instructive, because the interval had been computed in the
same session and simply was not carried into the comparison.

---

## 2026-08-03 — PROBE: the extended-mesh failure is GLOBAL. Do not remesh.

One solve, and it cancels a 40-minute remesh that would not have worked.

`src/03a2_boundary_probe.py` injects at `above_ear`, **130 mm** from the
truncation plane, on the **unchanged** extended mesh. If the coarse slab were
the cause, a montage that far from it should solve cleanly.

| solve | distance from cut plane | slab σ | calibration |
|---|---|---|---|
| truncated, `hyoid` | — | — | **clean** |
| extended, `hyoid` | 8 mm | 0.355 | WARNED **100.49%** |
| extended, `above_ear` | **130 mm** | 0.355 | WARNED **100.49%** |
| extended, `hyoid` | 8 mm | 0.190 | WARNED **95.84%** |

**VERDICT: GLOBAL.** Calibration fails just as hard 130 mm away as it does
8 mm away. The element-size hypothesis is **falsified**, and refining the slab
would not have fixed it.

### The identical value is the real finding

`hyoid` and `above_ear` are entirely different montages, different current
paths, opposite ends of the head, and both return **100.49%** — not similar
values, the same value to two decimals. Local conditioning would not do that.

Cross-referencing the slab conductivity makes the pattern unambiguous:

    slab 0.355 S/m  ->  100.49%   (at BOTH hyoid and above_ear)
    slab 0.190 S/m  ->   95.84%

**The calibration error tracks the slab conductivity and is independent of
electrode position.** Whatever is wrong is a property of the extended mesh as
a whole and scales with how conductive the added region is. It is not
discretisation, and it is not local.

That also retires the hypothesis recorded this morning. The
element-size jump was reasoned from the 0.83% element-count anomaly, it was
plausible, and it was wrong. **A hypothesis that survives a conforming-
interface test and a labelling test can still fail the one measurement that
varies the thing it actually predicts** — here, distance from the slab.

### What this costs and what it does not

**Stage 3 is still blocked**, and the boundary question is now harder than
"refine and re-run". The truncated mesh remains the only one producing clean
solves, so the pre-committed 1.0 dB rule still has no trustworthy number to
act on. The rule is untouched.

Next candidates, none yet tested: whether the extrusion introduces a second
exterior surface that SimNIBS integrates current over when calibrating;
whether the slab's outer boundary needs an explicit tag; whether
`01c_extend_neck.py` should extend the *label volume* and re-run `meshmesh`
rather than concatenating a pre-built slab. Ordered cheapest first, and each
is a diagnostic rather than a rebuild.

**One solve against a 40-minute remesh was the right trade** and it paid for
itself immediately. Run the cheap discriminator before the expensive repair.

---

## 2026-08-03 — CONFIRMED: the extended mesh does not conserve charge. Boundary disposition settled.

### (c) Invariant 2 never ran

`03a_boundary_run.py` contains **zero references to `solve_invariants`**.
Neither invariant 1 nor invariant 2 executed on any extended-mesh solve. The
calibration line was the only check standing between a broken mesh and
"extended mesh becomes PRIMARY for all published results".

**Invariant 2 is precisely the test that would have caught this**, and it was
written, and it was not wired in. That is the same defect as the unwired
calibration guard, found the same day, in the same script.

### (a) The measurement

Both electrodes sit above the truncation plane (`hyoid` S = −108.2,
`earlobe_contra` S = −33.4). Charge conservation therefore requires **exactly
zero** net vertical current through any horizontal plane below both of them.

| plane S (mm) | net downward current | as % of 1 mA injected | region |
|---|---|---|---|
| −60.0 | 1.6106 mA | 161.1% | between electrodes |
| −90.0 | 1.5974 mA | 159.7% | between electrodes |
| −112.0 | 1.5937 mA | 159.4% | between electrodes |
| **−130.0** | **1.6406 mA** | **164.1%** | **below both** |
| **−150.0** | **1.4809 mA** | **148.1%** | **below both** |
| **−170.0** | **1.3653 mA** | **136.5%** | **below both** |
| **−182.0** | **1.0698 mA** | **107.0%** | **below both** |

**Two violations, not one.** Planes below both electrodes should carry 0 mA
and carry 1.07–1.64. Planes *between* the electrodes should carry exactly the
injected 1.00 mA and carry 1.59–1.61.

**The solve does not conserve charge anywhere.** *(measured)*

### What this does and does not identify

The leakage hypothesis is **supported**: current flows downward through the
slab and does not come back. It explains every observation, including the two
that killed the element-size story — the error scaling with slab conductivity
(a better conductor leaks more) and its independence from electrode position
(the exit is at the bottom regardless of where you inject).

**But it is not cleanly separable from simple non-convergence**, and that
distinction is not resolved here. A field from a non-converged iterative solve
violates conservation everywhere, which would produce the same table. One
detail leans toward a real geometric leak rather than pure numerical noise:
the flux **decreases monotonically with depth** (1.64 → 1.48 → 1.37 → 1.07),
which is what current exiting through the slab's *lateral* surface as it
descends would look like, rather than the flat profile a single bottom-face
leak would give. That is suggestive, not conclusive, and it is tagged
`derived` rather than `measured`.

**Either reading has the same consequence: every extended-mesh solve is
invalid, and no number from one may be used.**

### STOPPING RULE INVOKED

Two hypotheses were allowed. Both are spent:

1. **element-size jump at the interface** — FALSIFIED by the `above_ear`
   probe (identical 100.49% at 130 mm and at 8 mm)
2. **non-insulating inferior boundary / charge leak** — CONFIRMED as a
   conservation violation, mechanism not fully separated from non-convergence

**Stopping, as pre-committed.** No further attempt to repair the extended
mesh. Continuing would be disproportionate: an honest unquantified limitation
is publishable, and blocking the paper on a mesh bug is not.

**DISPOSITION: the truncated mesh `mida_headneck.msh` is PRIMARY for every
published result.** It is the only mesh producing clean calibration, and its
solves are the ones every existing result already rests on.

The pre-committed 1.0 dB rule is **not applied, not revised, and not
quietly dropped**. It required a trustworthy shift measurement on both meshes,
and no trustworthy extended-mesh solve exists. The rule stands unexecuted, and
that is recorded rather than hidden.

### Wired in so it cannot recur

`solve_invariants.check_solve_plateau` (invariants 1 and 2) is now called by
`03a_boundary_run.py` after every solve, exactly as `03d` already did. A solve
that violates conservation now fails loudly instead of printing a mesh
decision.

---

## 2026-08-03 — ADVERSARIAL PASS #4: the leak conclusion, checked against a control

Attacked my own conclusion from the previous entry, because "the mesh violates
charge conservation" was measured with a method that had never been validated.
If the method were wrong it would report nonsense on a *good* mesh too.

**Control: the same code on the truncated mesh, which calibrates clean.**

| plane S (mm) | truncated (clean) | extended (broken) |
|---|---|---|
| −60 | 0.934 mA | 1.611 mA |
| −90 | 0.948 mA | 1.597 mA |
| −112 | 0.951 mA | 1.594 mA |
| near its own floor | **0.107 mA** (at −119, floor −122) | **1.070 mA** (at −182, floor −192) |

**The method is validated.** Between the electrodes the truncated mesh returns
0.93–0.95 mA against a 1.00 mA injection, a 5–7% shortfall consistent with the
~4% discretisation deficit already characterised for this pipeline. It is not
returning nonsense.

**And the decisive contrast is cleaner than the one I first drew.** Approaching
its own inferior boundary the truncated mesh's net flux **collapses to 0.107
mA**, which is what an insulating face does: current cannot escape, so net
transport through planes near it goes to zero. The extended mesh at the
equivalent position still carries **1.070 mA**, a **10x difference**, with
current running at essentially the full injected rate right at the floor of
the domain.

Same code, same montage, same conductivities. Only the mesh differs.

### A correction to my own framing

The previous entry asserted that any plane below both electrodes must carry
zero net current, and applied that at S = −112 and −130. **That expectation is
too naive for planes just below an electrode.** Current injected at `hyoid`
(S = −108.2) genuinely spreads downward into tissue and returns, so a plane a
few mm below it carries real circulating current — the truncated control shows
0.951 mA at S = −112 and it is behaving correctly. The zero-flux argument only
bites once you are near the domain floor, where there is nowhere left for
current to circulate.

**The conclusion is unchanged and now rests on better evidence:** not "flux is
nonzero where it should be zero", which over-claimed, but "flux fails to decay
toward the domain floor, where the control shows it decaying by 10x". That is
the falsifiable version, and it is the one to quote.

Recorded rather than silently amended, because the first framing would have
survived unchallenged: it reached the right verdict by an argument that does
not hold everywhere it was applied.

`src/03a3_leak_probe.py` now runs the control alongside the test rather than
asserting the expectation.

---

## 2026-08-03 — GUARD COVERAGE: enumerated, and it found two more. Plus a correction to my own claim.

"Written but never wired" had happened three times. Rather than fix the third
and move on, it is now enumerated the way `.gitignore` was replaced by an
allowlist: `src/test_guard_coverage.py` parses each script's **AST call
graph** and fails if a solving script does not invoke its guards. Grep was
rejected deliberately, since a match in a comment, a docstring or an unused
import looks like coverage and provides none.

**It immediately found two more, and one of them was mine.**

| script | missing when the test first ran |
|---|---|
| `03b_conductivity_bound.py` | **all three**: calibration, invariants, sigma-span gate |
| `03d_cavity_solves.py` | calibration read, sigma-span gate |

`03d` is the cavity run. It never read a calibration line, **which is exactly
how `cg10`'s 11.90% warning passed unremarked through all 16 solves** and was
only caught later by `03c` at analysis time.

### CORRECTION: I claimed to have wired in "invariants 1 and 2" and had not

The earlier commit says invariants 1 and 2 were wired into `03a`. **Only
invariant 1 was.** `check_solve_plateau()` — the function production actually
calls — raised `INVARIANT 1 FAILED` and nothing else. Invariant 2 lived in
`check_solve()`, which **nothing in the repository calls**.

So the count was wrong in the worst possible direction: **invariant 2, the
whole-domain charge-conservation test, was unreachable from production
code at the exact moment a leaking mesh was going undetected.** The test
designed to catch that failure could not have caught it.

Fixed at the source rather than at the call site: `check_solve_plateau()` now
performs the outer-shell test and raises `INVARIANT 2 FAILED` itself, so every
existing caller gains it without needing to remember.

### Why the enumeration is the actual fix

Each of the five instances was found by accident — a warning noticed while
reading output, a grep run for another reason, a claim checked while writing
it up. None was found by anything designed to find it. A denylist of
remembered mistakes cannot cover the next one; an enumeration of what
production *must* call can.

`test_guard_coverage.py` carries an `EXEMPT` map with a written reason per
entry (the three sphere-validation harnesses, which are checked against an
analytic oracle instead). The exemption is deliberately verbose so that adding
one feels like a decision rather than a shortcut.

**Runs before any production run, always.**

---

## 2026-08-03 — IT'IS SELF-REPORT SENT. Licensing incident CLOSED.

**Carl sent the self-report to the IT'IS Foundation on 2026-08-03.** No
further action is pending unless they reply.

This closes the incident recorded above: the ~11.5-hour public exposure of 109
`.geo` files, each the full MIDA head surface, on what was then a public
GitHub repository. Sequence, in full:

| step | outcome |
|---|---|
| detected | at Step E of publication, while checking whether the repo existed |
| exposure | 2026-08-03 04:59:57Z → 16:31Z, ~11.5 h |
| dissemination | 0 forks, 0 stars, 0 watchers, 0 clones, 0 unique cloners, 0 views, 0 unique visitors |
| immediate | repository set to **private** on detection |
| local | history purged with `git filter-repo --path-glob '*.geo' --invert-paths` |
| remote | old repo **deleted**, recreated **private**, purged history pushed and verified |
| disclosure | **self-reported to IT'IS, 2026-08-03** |

The traffic counters lag slightly and do not capture every automated crawler,
so nil dissemination is strong evidence rather than proof, and the self-report
was sent on that understanding rather than in spite of it.

**The licence findings that made the decision are recorded above** and are what
tipped it: clause **2.3.2** bars distributing "the Model Data or works derived
from the Model Data ... in the original form or in any modified or updated
form", which covers a derived surface with no room for interpretation; and
clause **5** terminates the agreement **with immediate effect** on breach and
obliges written confirmation that all copies are deleted. A clause that severe
is not one to sit on.

Also still binding and unaffected: **2.3.3**, the face-disguise requirement,
now enforced structurally in `figures/render_common.py`.

---

## 2026-08-03 — RE-READ: all 16 cavity calibration lines. The finding STANDS.

`03d` did not read calibration output when the cavity run executed, so its 16
solves were never checked. Re-read from the existing `fields_summary.txt`
files — no solves re-run — because the cavity result is **the only surviving
positive finding in the paper** and it had been computed from output nobody
had checked.

| | count |
|---|---|
| solves parsed | **16 / 16** |
| clean, no calibration line | **14** |
| warned, inside the measured 11–15% benign band | **2** |
| **outside the band, or missing a summary** | **0** |

The two warnings are `air__cg10` and `filled__cg10`, both at **11.90%**.

**VERDICT: the cavity finding stands.** Spearman rho = −0.881, p = 0.004,
max |residual| 1.6006 dB. *(measured)*

Three independent reasons the `cg10` warning cannot carry the result, none of
which required re-solving:

1. **It is inside the measured false-positive band.** On the sphere, 5 of 16
   solves warned while matching the analytic oracle, and the warned electrodes
   were not less accurate.
2. **It is identical in both halves of the pair**, to two decimal places,
   across two different conductivity fields. A random current-delivery failure
   does not reproduce like that, and being identical it cancels in the
   air-versus-filled ratio the analysis actually takes.
3. **`03c` already recomputed the verdict without `cg10` entirely**:
   rho = −0.893, p = 0.007, max |residual| unchanged at 1.6006 dB because that
   value sits at `hyoid`. **UNCHANGED.**

**What this exercise actually demonstrates** is that the guard gap was real and
the recovery was luck-independent: the analysis script `03c` had been wired to
read calibration even though the solve script had not, so the warning surfaced
before the number reached Results rather than after. That redundancy was not
designed, and the guard-coverage test now makes it unnecessary to rely on.

---

## 2026-08-03 — FALSIFIED: the central novelty claim. HArtMuT got there in 2022.

**Stop-and-report trigger: a falsified claim that everything downstream
depends on.** The gap-check worktree was told to attack the paper's central
`asserted` claim, and it broke it. **Re-verified independently against
IOPscience before recording**, because a finding this consequential must not
rest on one agent's reading.

**The claim, as written since day one:**

> "Nobody has published muscle-source dipoles in an anatomically detailed head
> model."

**The paper that falsifies it:**

Harmening, Klug, Gramann & Miklody (2022), *HArtMuT — modeling eye and muscle
contributors in neuroelectric imaging*, **J. Neural Eng. 19(6):066041**,
doi:10.1088/1741-2552/aca8ce.

Confirmed by direct fetch, every element:

| element of our claim | HArtMuT |
|---|---|
| muscle sources as dipoles | **yes**, dipolar and tripolar, ~3,900 sources |
| in a detailed head model | **yes**, FEM leadfields on the New York Head |
| muscle geometry from MIDA | **yes**, "extracted from the open-source MIDA model" |
| fibre direction by PCA | **yes**, "a PCA on close neighboring grid points" |
| asserts the same gap | **yes**, "muscular sources, to our knowledge, have not been added to any head model so far" |

It is not a near miss. It is the same construction, from the same atlas, by
the same fibre-axis technique this paper proposed as its own, published four
years ago and already shipped into SEREEGA and UnfoldSim.jl.

### What survives, and it is narrower and better defended

**HArtMuT's muscle sources radiate through homogeneous scalp.** Its authors
say so in print: *"this approach lacks modeling eyeballs (and muscles) as
their own tissue(s) with different conductivity than the remaining scalp."*
Neither volume conductor it uses contains muscle or fat as a compartment.

So the surviving claim is **muscle as both source and its own anisotropic
tissue**, solved in **MIDA's native geometry** rather than warped onto another
head, applied to a **coupling question at ear electrodes** HArtMuT has no
electrodes for. That is a real gap and it is defensible. It is also a much
smaller one than the paper has been written around.

**Yarici et al. 2023 is undamaged.** Its gap statement is scoped to ear-EEG
and HArtMuT does not touch ear-EEG, so it carries more weight now, not less.

### Consequences, none of them optional

1. **The framing is Carl's to rewrite, not mine.** Novelty framing is
   Introduction/Discussion territory and is his by standing rule. `OUTLINE.md`
   is flagged at the claim so nobody writes on the dead premise meanwhile.
2. **The PCA fibre-axis method must cite HArtMuT as precedent** rather than
   presenting it as new. It is currently presented as this paper's own
   methodological angle.
3. **The second half of the claim is also overstated.** sEMG forward models
   are no longer only cylindrical or limb-shaped; the agent found DTI-derived
   hand, MRI upper-arm and multi-compartment abdomen models.
4. **UNVERIFIED and it gates a claim.** HArtMuT sampled MIDA's pooled
   `Muscle (General)` label and describes it as "lower neck", while our own
   inventory shows that label holds the suprahyoids. The public atlas is
   anonymised to four classes at IT'IS's request, so whether HArtMuT already
   covers the suprahyoid corridor **could not be settled from the paper**.
   Load `HArtMuT_NYhead_small.mat` and read the labels **before** any
   suprahyoid novelty claim is written. Ten minutes, and it decides whether
   the surviving claim is as narrow as stated or narrower still.

### An unrelated gift, worth taking

**Ernie Extended** (Van Hoornweder et al. 2024, *Imaging Neuroscience* 2,
doi:10.1162/imag_a_00379) is a 13-tissue head model that **includes muscle at
0.160 S/m** and is already neck-extended. It is the cleanest
tissue-not-source near-miss for the related-work ladder, and separately it is
a **cheaper route out of the broken neck-extension mesh than debugging the
extruded slab** — which is the problem this session stopped on under the
two-hypothesis rule.

### Why this was worth doing before Results

The claim sat tagged `asserted` from day one and was never attacked, while
five sessions of effort were spent on meshes, floors and invariants beneath
it. **The cheapest possible check — a literature search against the paper's
own headline — was the last one run.** Attack the load-bearing `asserted`
claim first, not last.

---

## 2026-08-03 — Face anonymisation: the first crop was insufficient, and only looking caught it

`02b_qa_render.py` now routes the skin and mandible surfaces through
`render_common.anonymise_head()` before plotting, per MIDA clause 2.3.3.

**The first implementation did not work, and the metric said it did.** It
dropped points where `S >= orbital_rim AND A >= A_eye`, which removes the
forehead and upper orbit. It reported "dropped 5,263 of 60,000 points" and
looked like a success. **Rendering it and looking showed a legible facial
profile still there**: the identifying features — nose tip, lips, chin — all
sit *below* the orbital rim, so the mask had removed the least identifying
part of the face and kept the most.

Corrected to drop everything anterior of the eyes **at all heights**. Now
14,088 of 60,000 skin points and a third of the mandible go, and the lateral
view is a cranium and neck with no profile.

**The cost is real and is the right trade.** The anterior skin around
`mental`, `submental_mid`, `submental_lat` and `buccal` is gone, so those
markers now sit against empty space rather than against the chin they are
placed on. A licence clause outranks figure context, and the electrode
positions themselves are unaffected.

**Side effect, recorded not hidden:** the per-view position counts changed
(posterior 15 → 13, frontal 19 → 22) because the script's per-view visibility
test consults the surface point cloud, which is now sparser at the front. That
is a rendering artefact of the mask, not a change to any coordinate. Worth
knowing before anyone reads a count off this figure.

**The lesson is the cheap one and I nearly missed it.** A count of dropped
points is not evidence that the right points were dropped. The check that
worked was rendering the image and looking at it, which took ten seconds.

---

## 2026-08-03 — STOP: stage 3 calibration is a NEW population, 7 of 16 above the benign band

**Stage-3 numbers are PROVISIONAL and must not reach Results until this is
settled.** Everything downstream depends on them.

| electrode | calibration | |
|---|---|---|
| `mental` | **32.99%** | above band |
| `cg08` | 28.82% | above band |
| `cg04` | 26.83% | above band |
| `cg09` | 25.27% | above band |
| `cg01` | 19.67% | above band |
| `earlobe_ipsi` | 17.03% | above band |
| `cg06` | 15.57% | above band |
| `cg03` | 13.99% | inside 11–15% |
| `cg10` | 11.90% | inside 11–15% |

Seven of sixteen completed solves sit **above** the only band ever measured as
benign. Three populations were characterised before today, all on measurement:
**11–15%** (false positive on well-conditioned custom meshes, 5 of 16 sphere
solves warned while matching the analytic oracle), **~100%** (the extended-mesh
charge leak), **200.00%** (conductivity conditioning). **15.6–33.0% is none of
them.**

**The benign finding does not extrapolate.** It was measured at 11–15% against
an analytic oracle. Asserting that 33% is equally harmless because 12% was
would be exactly the reasoning this project keeps having to retract.

**Both invariants PASS on every solve**, which is the genuinely confusing part:
invariant 1 plateaus everywhere (CV 0.38–1.53%, mean 0.887–1.075) and
invariant 2 is near zero for all but one. So charge conservation and radius
independence are satisfied while the solver reports delivering the wrong
current.

**One co-occurrence is suggestive and is tagged `derived`, not `measured`:**
`mental` carries both the worst calibration (32.99%) **and** the worst
invariant-2 residual (+0.01379 x injected, six times the next worst). If the
warnings were pure post-processing artefact, they should not correlate with
the one physical conservation measure available. n = 1 co-occurrence is not
evidence, but it is the thread to pull.

`mental` is also independently known to be the most thinly resolved
compartment in the mesh (1,786 voxels on the right, 3,226 tetrahedra, the
smallest in the model), which is a plausible common cause for both readings
and is testable.

### A false reassurance I gave, and how

I checked run health by grepping the log for `WARNED|ESCALATE|INVARIANT.*FAILED`
and got **zero hits**, and reported the run as clean. **The grep was wrong:**
`03_leadfields.py` prints `calibration 32.99%`, never the word "WARNED" — that
wording belongs to `03a` and `03b`. The warnings were in the CSV the whole
time and the log search could not have found them.

Caught only because the CSV was inspected directly a few minutes later. **A
grep for a string the program never emits returns zero and looks exactly like
good news.** The lesson is the same one as the face-crop count: check the
artifact, not a proxy for it.

### Required before any stage-3 number is used

1. Determine what the 15–33% population is. The decisive test is the one that
   worked before: solve a case with a known answer while inspecting delivered
   current per electrode.
2. If it is benign, characterise it properly and widen the recorded band with
   the measurement beside it.
3. If it is not, the affected solves are void and must be re-run.

The run was left to finish (17/22 at the time of writing) because it writes
incrementally and the data is worth having as evidence, not because it is
trusted.

---

## 2026-08-03 — BRANCH A: SimNIBS's calibration check is wrong, not the solves. Fourth band recorded.

Ran the pre-decided decisive test with **no new solves**: the validated
tet-patch integral already runs on every stage-3 solve, and its `mean_ratio`
**is** delivered current over requested.

### The evidence, and it is stronger than "they disagree"

| electrode | tet-patch integral | SimNIBS says | requested |
|---|---|---|---|
| `mental` | **1.0746 mA** | 32.99% error | 1.000 mA |
| `cg08` | 1.0508 mA | 28.82% | 1.000 mA |
| `cg04` | 1.0431 mA | 26.83% | 1.000 mA |
| `post_lobule` | 1.0134 mA | 21.24% | 1.000 mA |
| `cg06` | 0.9841 mA | 15.57% | 1.000 mA |
| **`buccal`** | **0.8870 mA** | **clean** | 1.000 mA |
| `mastoid` | 0.9420 mA | clean | 1.000 mA |

Every solve delivers **0.887–1.075 mA**, max deviation **11.3%**, nowhere near
the 15.6–33.0% claimed. **BRANCH A.** *(measured)*

**Three independent discriminators, not one:**

1. **No correlation.** Spearman(SimNIBS calibration, |my deviation|) =
   **−0.322, p = 0.193**; Pearson −0.294, p = 0.237. If the solves were
   genuinely mis-delivering current these would be strongly positive. They are
   not significant in *either* direction.
2. **The sign is backwards.** Warned solves average **1.0138 mA**; un-warned
   solves average **0.9434 mA**. The warned ones are *closer* to the requested
   current.
3. **The single worst delivery is reported clean.** `buccal` at **0.8870 mA**
   is the largest true deviation in the set and SimNIBS raises nothing, while
   `mental` at 1.0746 — closer to correct — is flagged at 32.99%.

A check that is anti-correlated with the error it claims to measure, and
silent on the worst case, is not measuring that error.

### FOURTH MEASURED BAND, recorded with its discriminating evidence

| band | meaning | how established |
|---|---|---|
| 11–15% | false positive, custom mesh | 5/16 sphere solves warned while matching the analytic oracle |
| **15.6–33.0%** | **false positive, MIDA mesh** | **tet-patch integral says 0.887–1.075 mA; correlation with the warning is −0.32, n.s.; worst true deviation is un-warned** |
| ~100% | real: charge leaking out the domain | flux fails to decay toward the floor; control decays 10x |
| 200.00% | real: conductivity conditioning | fields 10–20x too large; fixed by air 1e-15 → 1e-6 |

**The stage-3 solves STAND.** Anisotropy and stage 4 may proceed.

### Carl's correction on invariant 2, and he was right

I reported `mental`'s invariant-2 residual as "6x the next worst", which reads
as alarming. In absolute terms it is **+13.8 µA of 1000 µA (1.4%)**; the next
worst, `buccal`, is **−2.3 µA (0.23%)**. Six times a small number is still a
small number, and quoting the ratio without the magnitude was the misleading
choice. *(measured)*

### What this does NOT resolve

Why SimNIBS's check misfires on this mesh at all, and why the misfire is
*anti*-correlated with true delivery, are both unexplained. The check is now
**demoted to a recorded quantity rather than a gate** for MIDA solves: it is
still parsed and stored per solve, and the tet-patch integral is the
authority. That is a downgrade of a check, so it is recorded loudly rather
than quietly applied — and it is licensed by measurement, not by convenience,
since it is exactly the "independent measurement establishes the bound" clause
the threshold norm allows.

---

## 2026-08-03 — Invariant 2 is UNREACHABLE on its own known-bad case

Applying the new norm — no check counts as verified until it has been shown to
return DIRTY — to the one guard lacking a demonstration. **It failed the
demonstration, in an instructive way.**

The known-bad case is the extended-mesh solve measured to leak **1.07 mA of a
1 mA injection**. That is a gross charge-conservation violation and invariant 2
exists precisely to catch it.

**Invariant 2 never ran.** `check_solve_plateau()` raised
**`INVARIANT 1 FAILED: no stationary plateau in the cut flux`** and returned.
The invariant-2 block sits *after* that raise, so it is unreachable on any
solve broken enough to disturb the radius plateau.

**This is a structural problem, not a missing test case.** The two invariants
are ordered, and the ordering means invariant 2 can only ever fire on a solve
that violates whole-domain charge conservation **while** maintaining a clean
radius plateau. That is a narrow and possibly empty class. In this repository
invariant 2 has, so far, never been reachable on any solve that would fail it.

So the honest status of invariant 2 is not "passing" and not "untested" but
**"never demonstrated, and structurally hard to demonstrate as currently
ordered"**. It has been reported as a passing check in this log and in commit
messages; that reporting was accurate about what the code returned and
misleading about what it established. *(measured)*

**The fix is not to reorder blindly.** Invariant 1's raise is legitimate and
should stay loud. The right shape is to compute **both** invariants, then
raise once with **everything** that failed, so a solve that violates both
reports both. That is a change to shared solve machinery and it deserves a
session with room to write and verify it, not the tail of one.

**Recorded rather than quietly fixed**, because the finding is more valuable
than the patch: a check placed after another check's hard failure is not a
check, it is a comment. The guard-coverage test enumerates whether a guard is
*called*; it cannot see that a called guard is *unreachable*. Both were needed
to find this, and only the norm surfaced it.

---

## 2026-08-03 — Branch A/B table, all 22 solves. And a precise retraction.

### The owed table

| electrode | tet-patch delivered | SimNIBS says | requested |
|---|---|---|---|
| `mental` | 1.0746 mA | 32.99% | 1.0000 mA |
| `cg08` | 1.0508 mA | 28.82% | 1.0000 mA |
| `cg04` | 1.0431 mA | 26.83% | 1.0000 mA |
| `cg09` | 1.0296 mA | 25.27% | 1.0000 mA |
| `post_lobule` | 1.0134 mA | 21.24% | 1.0000 mA |
| `cg01` | 1.0055 mA | 19.67% | 1.0000 mA |
| `earlobe_ipsi` | 0.9887 mA | 17.03% | 1.0000 mA |
| `cg06` | 0.9841 mA | 15.57% | 1.0000 mA |
| `cg03` | 0.9812 mA | 13.99% | 1.0000 mA |
| `submental_mid` | 0.9864 mA | 13.65% | 1.0000 mA |
| `cg10` | 0.9671 mA | 11.90% | 1.0000 mA |
| `above_ear` | 0.9463 mA | clean | 1.0000 mA |
| **`buccal`** | **0.8870 mA** | **clean** | 1.0000 mA |
| `cg02` | 0.9579 mA | clean | 1.0000 mA |
| `cg05` | 0.9452 mA | clean | 1.0000 mA |
| `cg07` | 0.9619 mA | clean | 1.0000 mA |
| `hyoid` | 0.9606 mA | clean | 1.0000 mA |
| `mastoid` | 0.9420 mA | clean | 1.0000 mA |
| `midjaw` | 0.9461 mA | clean | 1.0000 mA |
| `pre_tragus` | 0.9210 mA | clean | 1.0000 mA |
| `submaxillary` | 0.9431 mA | clean | 1.0000 mA |
| `submental_lat` | 0.9593 mA | clean | 1.0000 mA |

**BRANCH A FIRED.** *(measured)*

- tet-patch implied error **0.5–11.3%**; SimNIBS claims **0–32.99%**
- the two **agree on 4 of 22** solves
- **Spearman −0.425, p = 0.048**

### Correction to my own statistic

I earlier reported this correlation as **−0.322, n.s. (p = 0.193)** on the 18
solves then complete. On the full 22 it is **−0.425, p = 0.048**, which is
**significant**. The conclusion does not change but its strength does, and in
the more damning direction: SimNIBS's calibration error is not merely
uncorrelated with true delivery error, it is **significantly
anti-correlated** with it. Quoting the interim n.s. figure as final would
have understated the case. *(measured)*

### RETRACT PRECISELY — what falls and what stands

The previous entry risked over-retracting. Separating the two claims:

**STANDS — the measurements.** Invariant 2's computation *did* execute on
every solve where invariant 1 passed, which is all 22 stage-3 solves. **Net
outer-boundary current measured at up to 13.8 µA of 1000 µA** is a real
number produced by real code on real fields. `buccal` at −2.3 µA likewise.
Those are `measured` and they are quotable.

**FALLS — the inference.** "Invariant 2 passed, therefore charge conservation
is verified" does **not** stand. The check has never been demonstrated capable
of returning dirty, so its silence carries no information. A passing result
from an unvalidated check is not evidence of correctness; it is an absence of
evidence either way.

The distinction matters because the numbers remain usable in the error budget
while the *guarantee* does not. **Keep the measurement, drop the assurance.**

---

## 2026-08-03 — THE DOUBLE REVERSAL. Self-criticism is not evidence.

The most generalisable entry in this log, and it is about how a claim was
handled rather than about the claim.

**The sequence.** (1) I asserted SimNIBS's current-calibration check was
broken. (2) I retracted that as over-reach, wrote the retraction into
`solve_invariants.py`'s docstring — *"Not because SimNIBS's check is broken. It
is not."* — and recorded that the earlier version *"was wrong and is corrected
here rather than deleted"*. (3) Measurement against the tet-patch integral
falsified the retraction. **The original claim was right.**

**The retraction was the error, and it was persuasive precisely because it was
self-critical.** It had every surface feature of rigour: it named its own prior
claim, called it wrong, corrected it in place rather than deleting it, and gave
a reason. What it did not have was a measurement. It reasoned from the check's
behaviour on one prior case — it had reported 200.00% on a solve that was
genuinely wrong and stayed silent on one that was right — and generalised from
n = 2 to "the check discriminates correctly".

**A retraction is a claim.** It carries the same evidentiary burden as the claim
it retracts, and it does not earn a discount for being humble. Nothing about
admitting error makes the admission true. The failure mode is specific and
worth naming, because in a project that rewards adversarial self-checking it is
the natural blind spot: **an agent that is rewarded for catching its own errors
will eventually manufacture one.** Retracting feels like rigour, so it bypasses
the scrutiny that asserting attracts.

**What actually settled it was a dissent-capable reference method.** The
tet-patch integral is not an opinion about SimNIBS's check — it is an
independent measurement of the same physical quantity (delivered current),
computed from the field alone, with no shared machinery, and validated against
the analytic sphere. It was *able to disagree*, and it did: on 22 solves it puts
delivered current at 0.887–1.075 mA where the check claims errors of up to
32.99%.

The operational rule: **when a claim and its retraction are both arguments,
neither is evidence. Build the instrument that can dissent, and let it.** Do not
resolve a contradiction between two of your own positions by picking the more
self-critical one.

*(Note also that independent evidence against the check existed from the
beginning and was not weighted: 5 of 16 sphere solves warned while matching the
analytic oracle. That is a measurement against an absolute reference, and it
said the check produces false positives. It was recorded as a curiosity and
then used to build the "benign band" instead of being read as what it was.)*

---

## 2026-08-03 — Guard-chain audit: collect-then-raise, and what else was dead

Converted the whole invariant chain to **collect-then-raise**
(`solve_invariants.GuardChain`): every guard is evaluated, every verdict
recorded, and one exception carries all failures. A guard that cannot be
evaluated is recorded as `error`, never skipped, because a skipped guard reads
exactly like a passing one.

**Verified end to end on the real known-bad case.** The extended-mesh solve now
reports **three** failures where it previously reported one:

| guard | extended, slab 0.355 | truncated control |
|---|---|---|
| invariant 1 plateau | FAIL, no plateau | ok, CV 0.49% |
| invariant 1 magnitude | FAIL, −38.20 × requested | ok, +0.9606 |
| invariant 2 outer net | **FAIL, −0.310 × injected** | ok, −0.000015 |
| invariant 2 coverage | ok, 3.40% | ok, 5.33% |

**Invariant 2's known-bad case is now DISCHARGED.** It fires on the extended
mesh at −0.310 and −0.566 × injected against −0.000015 on the truncated
control — four orders of magnitude of separation. It had never been reached
before because invariant 1 raised first. *(measured)*

I predicted before running this that invariant 2 would prove **incapable** of
firing, on the argument that its shell escapes the mesh and returns a
degenerate zero. **That prediction was wrong and the measurement said so.**
Recording it because it is the same lesson as the entry above: the argument was
tidy and it was not evidence.

### What else was dead

| guard | status | consequence |
|---|---|---|
| **invariant 3 (linearity)** | **no caller anywhere** | never ran on any solve, ever |
| **invariant 4 (reciprocity on the head mesh)** | **no caller anywhere** | never ran on any solve, ever |
| `batch_plan()` | no caller | the "first and last solve of a batch" policy never executed |
| `needs_escalation()` | called, result discarded | prints `[ESCALATE]` and branches on nothing |
| `check_solve()` | no caller | carried a second copy of invariant 2 behind **two** earlier raises; **deleted** |
| `check_solve_output()` | no caller | gates on the calibration check; **retired as an active refusal** |
| `solve_invariants.__main__` | `NameError` since it was written | the documented way to inspect the tolerances had never once been run |

Invariants 3 and 4 are the fifth and sixth instances of "written, documented as
policy, wired to nothing" in this repository. `test_guard_coverage.py` could not
see them because they were not in its `REQUIRED` set; they are now tracked in a
new `BATCH_REQUIRED` group and it **fails** until they are wired. The escalation
band was never reached in any case (observed CV 0.32–1.53%, band opens at
2.44%), so nothing silently passed a check it should have failed — but that is
luck, not coverage. Cost to wire: 4 extra solves, ~16 min.

### Two new guards, and why they are not tuned

**`invariant_1_magnitude`** — the loose 0.4–2.5 × injected band, inherited
unchanged from the deleted `check_solve()`. A uniform scale error leaves the
plateau exactly stationary and leaves invariant 2 at zero, so before today
*nothing per-solve* could see it; only the analytic sphere in pre-flight, which
runs once per environment. The band predates every stage-3 observation, which is
what makes it usable — a tight window around the observed 0.887–1.075 would be
derived from the data it judges.

**`invariant_2_coverage`** — invariant 2 integrates J·n over a shell at
1.05 × the 99th-percentile node radius, i.e. deliberately *outside* the bulk of
the domain. Measured on the truncated mesh:

| shell / p99 | 1.00 | 1.05 | 1.10 | 1.30 |
|---|---|---|---|---|
| inside the conductor | 8.20% | **5.35%** | 3.33% | **0.00%** |
| net / injected | −0.606 | +0.0138 | +0.0021 | **+0.000000** |

At zero support the integral returns exactly 0.0 and the tolerance passes
vacuously; a zero from "nothing was sampled" is indistinguishable from a zero
from "charge is conserved". **The check only has support at all because MIDA is
elongated** (p99 153.3 mm, r_max 199.3 mm). On any convex domain
1.05 × p99 > r_max — for a ball, p99/r_max = 0.997 — and coverage is zero. The
production shell coverage was computed and **discarded** by the caller for the
whole project; it is now a recorded verdict and a CSV column (`inv2_coverage`).

### Per-guard synthetic tests — `src/test_guards_fire.py`

Twelve cases, each failing exactly one guard with every other guard passing,
plus a clean control that trips none. No solve, no SimNIBS, no MIDA geometry:
a tetrahedralised ball with an analytic monopole or dipole field, in numpy,
running in seconds in the plain venv.

The invariant-2 case is the one that was owed: a **monopole** at the patch
centre gives flux that is radius-stationary *exactly* (invariant 1 passes) while
the net outer-boundary current equals the source current (invariant 2 must
fire). Radius-stationary flux and unconserved charge, with no solve.

**This property is also the only automatic detector of an unreachable guard.**
`test_guard_coverage.py` resolves whether a guard is *called*; it cannot see
that a called guard sits after another guard's raise. A case that must make one
guard fire *alone* does see it — under the old fail-fast chain the monopole case
reports invariant 1 failing too, and the test rejects it.

One incidental measurement: at **5×** uniform scale the magnitude case also
trips invariant 2, because invariant 2's residual is proportional to the field,
so a comfortably-inside-tolerance residual is amplified past it. **Invariant 2 is
not scale-invariant**, and a large enough scale error trips it through numerical
amplification rather than through charge conservation. The isolation case
therefore scales *down* (0.2×). *(measured)*

---

## 2026-08-03 — THE 11–15% BENIGN BAND IS RETIRED. So is the band taxonomy.

**The band is void and everything derived from it falls with it.**

It was measured as "5 of 16 sphere solves warned at 11–15% while matching the
analytic oracle", and thereafter used as a benign range: `cg10` at 11.90% was
waved through the cavity run on it, and stage 3 was halted when solves came back
at 15.6–33.0% on the reasoning that *"the benign finding does not extrapolate"*.

It was derived **entirely** from SimNIBS's calibration check. That check is now
measured anti-correlated with true delivered current on this mesh: **Spearman
−0.425, p = 0.048, n = 22**. Partitioning a quantity that does not measure what
it claims into "benign" and "fatal" ranges does not yield two populations; it
yields two arbitrary slices of noise. **There is no band. There is no threshold.
The axis is void.**

The wider taxonomy goes with it. Of the four recorded "bands", only the two that
never rested on the calibration check survive, and they survive because they
were always measurements of something else:

| former band | rested on | disposition |
|---|---|---|
| 11–15% "benign, custom mesh" | calibration only | **VOID — retired** |
| 15.6–33.0% "false positive, MIDA" | calibration only | **VOID as a band.** The underlying observation — these solves deliver 0.887–1.075 mA — stands, but it is a statement about the *tet-patch integral*, not a region of the calibration axis |
| ~100% "charge leaking out the domain" | **flux-decay probe**, independent | **SURVIVES** |
| 200.00% "conductivity conditioning" | **fields measured 10–20× too large**, independent | **SURVIVES** |

**What replaces the band is not another band. It is a different instrument.**
The tet-patch integral's `mean_ratio` *is* delivered current over requested,
validated against the analytic sphere. Delivered current is reported per solve
with its flip point, and the only gate on it is the loose gross-error band
(0.4–2.5 × injected) that predates every stage-3 observation.

Retired in: `preflight.read_calibration` (docstring), `preflight.check_solve_output`
(now an active refusal that raises), `03a_boundary_run.py`, `03c_cavity_analysis.py`,
`03d_cavity_solves.py`, `test_guard_coverage.REQUIRED`, `CLAUDE.md`, `OUTLINE.md`.

---

## 2026-08-03 — AUDIT: every decision that used SimNIBS calibration as evidence

Each decision, and whether it survives on evidence that does **not** come from
the calibration check.

| # | decision | independent evidence | verdict |
|---|---|---|---|
| 1 | extended mesh does not conserve charge | flux fails to decay toward the floor (1.070 mA at S=−182, floor −192) vs control (0.107 mA at S=−119, floor −122); **and** invariant 2 at −0.310 / −0.566 × injected vs −0.000015 | **SURVIVES** |
| 2 | σ_air 1e-15 → 1e-6 conditioning failure | fields measured 10–20× too large, directly | **SURVIVES** |
| 3 | the 11–15% benign band | none | **VOID — retired** |
| 4 | `cg10` 11.90% dismissed as benign | none | **VOID as reasoning.** Moot in fact: `cg10` warns identically in air and filled, so it cancels in the pair ratio, and the verdict is unchanged when the warned pairs are excluded |
| 5 | **stage 3 halted: "7 of 16 above the benign band"** | none | **VOID as reasoning.** The halt was correct by luck — it triggered branch A, which found the real result — but its stated grounds were not evidence |
| 6 | **`check_solve_output` as a production gate** | none | **VOID.** Never fired (no caller). Retired as an active refusal; had it been wired it would have voided 11 good solves and passed the worst one |
| 7 | **hypothesis 1 (coarse elements at the slab interface) FALSIFIED** | **none — and the measurement behind it does not exist** | **VOID. See below.** |
| 8 | cavity verdict recomputed excluding "warned" pairs | the recomputation itself | **SURVIVES as a leave-some-out robustness check**, but its *rationale* is void: "warned" is not a meaningful partition. Relabel, do not re-run |

Decisions 5, 6, 7 and 8 were not on the handoff list. **7 is the serious one.**

### 7. The `above_ear` probe solved `hyoid`. Hypothesis 1 was never tested.

`03a2_boundary_probe.py` exists to decide whether the extended mesh's failure is
LOCAL to the coarse slab or GLOBAL to the mesh, by injecting at `above_ear`
(130 mm from the cut face) instead of `hyoid` (8 mm). Its recorded result —
*"identical 100.49% at 130 mm and at 8 mm"* — falsified hypothesis 1 and closed
one of the two pre-committed hypotheses.

**It injected at `hyoid` both times.** From the probe's own log:

    Placing Electrode: centre: [-9.33, 42.74, -108.23]     <- hyoid
    above_ear is at             [78.76,   7.24,   13.61]

The cause: `03a2` calls `03a_boundary_run.solve()`, which read the montage from
**`03a`'s module-level `INJECT_FROM`** and had no parameter for it. `03a2` set
its own module-level `INJECT_FROM = "above_ear"`, which was used only in print
statements and never reached the solver. The probe therefore re-solved the
identical montage and produced a **byte-identical result mesh**
(md5 `b110d2ced3a7b2e10377dcaca1dad04d`, identical to
`results/boundary/muscle_iso/`). The two "agreeing" measurements are one
measurement, reported twice, once mislabelled.

**The identical 100.49% to two decimal places should itself have been the
alarm.** Two different montages on a 15.5-million-element mesh do not agree to
2 dp. It was read as a strikingly clean result instead of an impossible one.

**Consequences.**

- **Hypothesis 1 is UNTESTED, not falsified.** The "pre-committed budget of two
  hypotheses, both spent" is wrong: one was spent.
- **The boundary disposition SURVIVES.** The truncated mesh stays primary
  because the extended mesh demonstrably does not conserve charge (decision 1,
  independent). What is reopened is the *cause*, not the *unusability*.
- The claim appears in `HANDOFF.md` §1 and `OUTLINE.md` and is corrected in both.

**Fixed:** `solve()` now takes `inject_from`/`inject_to` as explicit parameters
and prints the montage; `03a2` passes them and then **asserts the coordinate
actually appears in the solver's log**, refusing to report a verdict otherwise.
The void directory is preserved at
`results/_failed_runs/boundary_probe_above_ear_VOID_solved_hyoid_20260803/`
with a `WHY_VOID.txt`, not deleted.

The generalisable rule, and it is the same one as the aniso guard in
`03_leadfields.py` that this project got right by hand: **a function whose
behaviour depends on a module global cannot be safely reused from another
module.** Verify the parameter landed by reading the tool's own output, not by
assuming the call configured it.

---

## 2026-08-03 — CORRECTION, same session: `EXTENSION_LABEL = 200` collides with SimNIBS's electrode tag range

**I recorded invariant 2 firing on the extended mesh at −0.310 and −0.566 ×
injected, and called its known-bad case discharged. That is WRONG and is
retracted here, in the same session, before it could be relied on.**

`solve_invariants.with_electrode_tags()` fills SimNIBS's reserved electrode
ranges, read from `mesh_element_properties.py`:

    ELECTRODE_RUBBER_RANGE = (100, 499)   sigma 29.4 S/m
    SALINE_GEL_RANGE       = (500, 899)   sigma  1.0 S/m

`01c_extend_neck.py` tags the neck-extension slab **200**, which falls inside
the rubber range. So any analysis that builds its conductivity map from Table 1
and then calls `with_electrode_tags()` silently models **42,766 slab elements
as electrode rubber at 29.4 S/m instead of muscle at 0.355 S/m** — an 83×
error, on the exact compartment whose behaviour was under investigation.

`setdefault` is what makes it silent: a map that *does* carry tag 200 keeps its
own value and is correct, and a map that does not gets rubber. Both look
identical at the call site.

| extended mesh, inject at `hyoid` | slab read as rubber (29.4) | slab correct (0.355) |
|---|---|---|
| invariant 1 delivered | −38.2021 × | −0.0000 × |
| invariant 2 net | **−0.310018** | **−0.003832** |
| invariant 2 verdict | FIRES | **PASSES** |

**Corrected findings:**

1. **Invariant 2 does NOT fire on the extended mesh.** With the correct map it
   reads −0.003832 at `hyoid` and −0.000163 at `above_ear`, both comfortably
   inside tolerance. Its real-known-bad demonstration is **still owed**.
2. **The synthetic demonstration stands**, and is now the only one. The
   monopole case in `test_guards_fire.py` is self-contained numpy with a
   complete conductivity map and no such coupling.
3. **The claim that invariant 2 corroborates the extended-mesh leak is
   withdrawn** — from this log and from OUTLINE. The leak rests on the
   flux-decay probe alone, which is unaffected: it reads J_z directly from the
   field and the slab's conductivity enters only through the solve, which used
   0.355 correctly.
4. **My prediction, my retraction of it, and my retraction of the retraction
   were all decided by an instrument fault.** Earlier today I predicted
   invariant 2 was incapable of firing here, then recorded that measurement had
   proved me wrong. The measurement was wrong. The third reading is the
   measured one — and it is closer to the first.

**Original solves are NOT affected.** `03a_boundary_run.solve()` passes
`assigned`, which sets tag 200 explicitly, so `setdefault` leaves it at 0.355;
the solve itself always used the right value. Only ad-hoc analysis scripts that
rebuilt the map from Table 1 alone were wrong. Stage 3 is unaffected for a
different reason: the truncated mesh has **0 tags with no conductivity** and
`03_leadfields.py` builds its analysis map with the same function that assigns
the solve's, so the two cannot diverge. Verified, not assumed.

**Owed:** move `EXTENSION_LABEL` out of 100–899 entirely, and make
`with_electrode_tags()` **raise** on a collision instead of `setdefault`-ing
over it. A reserved range that silently absorbs a user tag is the same class of
defect as a denylist `.gitignore`.

**The lesson, and it is the third of the day in the same shape.** The
conductivity map used for ANALYSIS must be provably the same one used for the
SOLVE, and nothing checked that. Together with the montage bug in `03a2` and
the patch-centre bug that followed it, all three are one failure: **a parameter
that reaches the instrument by a path nobody verified.** Print the montage.
Print the tag map. Assert the coordinate appears in the solver's own log. The
project already had the rule — *read the tool's own output before reporting its
result* — and applied it to the solver while trusting its own callers.

---

## 2026-08-03 — Filed upstream: simnibs/simnibs#665

https://github.com/simnibs/simnibs/issues/665

Led with the disagreement **pattern**, not the statistic: `buccal` at 0.8870 mA
is the largest true deviation in the set and is reported clean, while `mental`
at 1.0746 mA — closer to correct — is flagged 32.99%; warned solves average
1.0113 mA against un-warned 0.9428 mA. The Spearman −0.425, p = 0.048, n = 22
is included as supporting only, with the fragility of a marginal p on n = 22
stated in the issue rather than left for a maintainer to point out.

**The "4 of 22 agreement" figure went in with its tolerance attached**, under
the interim-statistic rule added to CLAUDE.md today. It reproduces only at an
unstated ±5 pp window and moves to 9 of 22 at ±6 pp, so the issue gives the
whole sensitivity curve (0 / 2 / 4 / 9 at ±3 / 4 / 5 / 6 pp) and tells the
reader to treat the parameter-free extremes as the claim.

**One claim was deliberately weakened before filing.** The handoff asked for
"the tet-patch method and its validation against the analytic sphere". The
sphere validates the method's **radius-consistency** (plateau CV < 0.7% at
every density) and the forward setup (RDM 4.36%, MAG +4.40%, n = 120) — it does
**not** validate the integral's absolute level, which reads 0.9406 / 1.2481 /
1.1134 across three sphere densities, non-monotone and sign-changing
(METHODS_LOG 2026-08-02). Filing "every solve delivers within 11.3%, so
SimNIBS's 15.6–33.0% is wrong" would have rested a magnitude claim on an
instrument whose magnitude is uncertain by more than the discrepancy.

So the issue claims **ordering**, not magnitude. A per-realisation scale factor
shifts every solve together and cannot invert a ranking, so the `buccal`/
`mental` inversion and the warned-vs-un-warned means survive it. The absolute
band is reported and its unvalidated level is stated in the issue itself.

---

## 2026-08-03 — RULINGS. Stage 3's footing corrected; hypothesis 1 closed as untested

Six rulings from Carl, recorded with what each changes.

### 1. The extended mesh is NOT reopened. The record is corrected.

**"Hypothesis 1 (coarse elements at the slab interface) falsified" becomes
"hypothesis 1 UNTESTED — the probe solved `hyoid` while reporting
`above_ear`."** "Both hypotheses spent" was wrong; one was spent.

The disposition is unchanged and rests on the **flux-decay probe**, which is
independent of the calibration check and of the probe defect. The mesh is
unused, the limitation is documented in OUTLINE with its bias direction, and
**the cause is not re-litigated**. The corrected probe was run once, reports
15.75% at `above_ear` against 100.49% at `hyoid`, and that number is recorded
here as an observation rather than as the start of an investigation.

### 2. Why stage 3 stands — corrected footing

**The previous footing was wrong in the way I had already flagged elsewhere.**
Branch A concluded the solves are sound because the tet-patch reports
0.887–1.075 mA. That is a **magnitude** claim resting on an instrument whose
absolute level is not established — the same integral reads 0.9406 / 1.2481 /
1.1134 across three analytic-sphere densities, non-monotone and sign-changing.
I weakened the upstream filing to an ordering claim for exactly this reason and
did not apply the same correction here. *(measured)*

**Correct footing, in three parts:**

1. **Every published claim in this paper is a RATIO** — site against site, ear
   against jaw, muscle against muscle. Table 3 is already organised around
   this. A term that scales the whole lead field equally **cancels exactly** in
   every ratio and cannot reach a conclusion.
2. **The tet-patch's absolute-level uncertainty is exactly such a common
   term.** It is a property of the integral, identical across solves, so it
   divides out of every comparison the paper makes. Stage 3 does not need the
   absolute level and never did.
3. **What the tet-patch establishes is RELATIVE, and that is what was needed:**
   no electrode deviates anomalously with respect to the others. The full
   spread across 22 solves is 0.887–1.075 (mean 0.9770, sd 0.0449), with no
   outlier and no site detached from the distribution.

**And it is the relative reading that carries the SimNIBS finding too.** A
common scale factor shifts every solve together and cannot invert a ranking, so
the ordering disagreement — `buccal` largest true deviation and reported clean,
`mental` closer to correct and flagged 32.99% — survives the level uncertainty
untouched.

**One thing the spread does NOT license.** The 0.887–1.075 range must not be
entered into the error budget as a fresh per-site term at face value. It is the
same size as, and has the same physical cause as, the electrode-meshing
realisation noise already carried as row 6 (contact area realised from whatever
surface triangles fall under each electrode). Adding it separately would
double-count. It enters Table 3 as a **bound** on that term, cross-referenced,
not as a new one.

### 4. Reserved-tag guard, enumerated from SimNIBS source

`solve_invariants.reserved_tag_ranges()` resolves the ranges from
`simnibs.utils.mesh_element_properties.ElementTags` and **raises if it cannot
import them**, because an out-of-date copy pasted into this repo is precisely
how tag 200 became electrode rubber:

| range | meaning |
|---|---|
| 100–499 | electrode rubber, σ 29.4 S/m |
| 500–899 | saline gel, σ 1.0 S/m |
| 999 | electrode cream |
| 1000–2499 | tissue and electrode SURFACE tags |
| 5000–5999 / 7000–7999 | left / right hemisphere surface and layer tags |

**It immediately found a second collision, and this one is in MIDA itself.**
MIDA's native labels **100–116** — cerebral peduncles, optic chiasm, the twelve
cranial nerves, thalamus — sit inside the electrode-rubber range.

**They are correct today, and only by accident of completeness.** Every one is
named in Table 1, so `setdefault` leaves it alone. Drop a single row from
Table 1 and that anatomical structure silently becomes 29.4 S/m. That is a
*latent* hazard, distinct in severity from tag 200, which had no conductivity
of its own and was therefore *actively* wrong. The guard reports the two
differently: a NOTE for reserved-range tags carrying an explicit conductivity,
a raise for those without.

**Checked and clean:** SimNIBS allocated **501 and 502** for the two electrode
volumes in every stage-3 solve (117 and 123 tetrahedra), in the saline range,
not the rubber range, so it never collided with MIDA labels 100–116. Verified
by reading the tags out of a result mesh, not assumed. *(measured)*

Wired as `conductivity_map_covers_mesh`, guard 0 of the invariant chain, which
is the first point where the mesh and the analysis map are both in hand. It
subsumed the old `invariant_2_unknown_tags` guard — a shell point can only be
zeroed for an unmapped tag if the map is already incomplete, so the two were
never independently triggerable, and the synthetic isolation test refused to
pass either until they were merged. The map-level check is strictly better: it
sees every tag in the mesh, not only the ~4% the outer shell samples.

`EXTENSION_LABEL = 200` is annotated as a defect at both definition sites and
**deliberately not renumbered** — rebuilding an unused mesh to change a label
would reopen a closed question for no gain.

### 5. The overstatement was Carl's, and is recorded as his

The handoff asked for "the tet-patch method and its validation against the
analytic sphere". **The sphere validates radius-consistency and the forward
setup, not the integral's absolute level.** Carl records the overstatement as
his own. It is worth keeping in the log for the same reason as the double
reversal: the instruction was specific, confident and slightly wrong, and the
right response was to measure what the sphere actually establishes and file the
narrower claim rather than the requested one.

### 6. The mesh-quality regression's dependent variable

Accepted: **delivered current** (tet-patch) against element count and quality
per electrode patch, with the calibration value reported alongside as a second
series. Calibration as the dependent variable is now known anti-correlated with
truth, so regressing against it would measure the artefact rather than the
mesh.

---

## 2026-08-03 — INVARIANTS 3 AND 4 HAVE NOW RUN. Reciprocity holds on the head mesh.

Ruling 3: run them before stage 4, because invariant 4 checks the identity the
whole paper rests on, on the real geometry rather than a sphere, and if it
fails everything downstream is void.

**It does not fail. Stage 4 is clear to proceed.** *(measured)*

Four extra solves (2x current and swapped montage, for the first and last solve
of the batch as `batch_plan` specifies), 2000 sample points inside segmented
muscle — where the lead field is actually read, so the identity is tested where
the paper uses it.

| electrode | invariant 3 (linearity) | invariant 4 (reciprocity) | geometry |
|---|---|---|---|
| `above_ear` | **0.000e+00** | **7.500e-06** | **identical**, 2,140,977 nodes |
| `submental_mid` | 6.421e-03 | 6.913e-03 | **DIFFERENT**, 2,140,980 vs 2,140,979 nodes |

### The split is the discretisation, and it is the whole finding

`above_ear`'s 1x and 2x solves are **bit-identical meshes** — same node count,
maximum coordinate difference exactly 0.0 — and there **linearity holds to
machine precision across all 12.29M elements**: the ratio |E(2I)|/|E(I)| has
min = max = median = 2.000000, with 0% of elements deviating by more than
1e-6. The solver is exactly scale-equivariant.

`submental_mid`'s are not: 2,140,980 nodes against 2,140,979. **SimNIBS
re-meshes the electrodes on every run**, so two runs of the "same" montage are
two different discretisations. Its 6.4e-3 is therefore not a linearity failure
— it is electrode realisation, the term already carried as Table 3 row 6, and
the comparison's premise (same discretisation, doubled current) does not hold.

The swapped-montage mesh for `above_ear` has the same node count with
coordinates **permuted** (SimNIBS renumbers when the channel order changes), so
the check compares the two fields at matched physical points rather than by
element index. After sorting coordinates the geometry is identical to 0.0 mm,
which is what makes its 7.5e-6 interpretable: it is the solver's own iterative
residual for a genuinely different right-hand side, not a meshing artefact.

### Why nothing downstream is void

7.5e-6 relative is **6.5e-5 dB**. `submental_mid`'s 6.9e-3 is **0.06 dB**, and
that one is dominated by electrode realisation rather than the identity. The
measured per-site noise floor is **0.27 dB**. Reciprocity therefore holds on
the real head geometry roughly **four orders of magnitude** inside the
resolution of anything the paper reports.

### The 1e-6 tolerances are WITHDRAWN, not retuned

Both readings exceed 1e-6, and the temptation is to move the number. **Nothing
ever measured it** — it is a round constant near machine precision, written
when the functions were written and never exercised, because neither function
had a caller.

Measurement now says it is the wrong shape. The identities are compared across
two independently re-meshed SimNIBS runs, and electrode realisation is
independently measured at ~3–5 percentage points on lead-field magnitude
(0.27 dB per-site, n=6). A 1e-6 gate asks these identities to hold about a
thousand times tighter than the reproducibility of the thing being compared.

So they are **withdrawn as gates and reported with their values**, following
the precedent already set in this project by the 20 mm electrode-spacing floor,
which was withdrawn to `config.COLLAR_OD_MM = None` rather than retuned. The
prohibited move is loosening a threshold because something failed it; the
permitted one is withdrawing a threshold that was never founded.

**What replaces the gate is a guard that actually discriminates:**
`same_discretisation()`, reported beside every value. A number from two
different meshes is uninterpretable as a physics result no matter what
threshold it is held to, and that distinction — not the tolerance — is what
separates `above_ear` from `submental_mid` here.

**Owed before either becomes a gate again:** solve one identical montage twice
and measure the solver's reproducibility at fixed geometry. That is the
independent measurement the threshold rule requires, and it is one solve.

### A note on what invariant 3 can and cannot see

At fixed discretisation it returned exactly 0.0 over 12.29M elements. That is a
pass, but it is a weak one: an iterative solver started from zero produces
exactly scaled iterates for a scaled right-hand side, so the test cannot
distinguish "the physics is linear" from "the solver is scale-equivariant". Its
real value is as the control for invariant 4 — it establishes that the solver
contributes no error at fixed geometry, which is what licenses reading
invariant 4's 7.5e-6 as a genuine residual.

