# Methods log

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
