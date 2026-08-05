# Methods

*Description only. No argument, no novelty claims — the Introduction and
Discussion are drafted separately.*

---

## 1. Head model

The volume conductor is **MIDA v1.0** (Multimodal Imaging-Based Detailed
Anatomical Model of the Human Head and Neck; Iacono et al. 2015, IT'IS
Foundation, DOI 10.13099/ViP-MIDA-V1.0), a whole-head model segmented at
**500 µm isotropic**.

**On the structure count.** MIDA is commonly cited as containing 153
structures. That figure describes the **CAD/surface distribution**. The
**voxel distribution used here carries 116 labelled structures**, and every
number in this paper derives from the voxel data. The full inventory is
`results/01_label_inventory.csv`. We report 116 rather than 153 throughout;
the discrepancy is a difference between two distributions of the same model,
not a subsetting choice on our part.

Ten of the eighteen articulator muscles in our target set are individually
segmented and were verified present by label: masseter (66), temporalis /
temporoparietalis (63), medial pterygoid (81), lateral pterygoid (65),
orbicularis oris (75), buccinator (84), mentalis (71), depressor anguli oris
(72), platysma (60), sternocleidomastoid (68).

**The suprahyoid and tongue muscles are not individually segmented.** Digastric
(both bellies), stylohyoid, mylohyoid, geniohyoid, genioglossus, hyoglossus and
styloglossus are pooled into two compartments — `Muscle (General)` (label 38;
1,975,307 voxels, 246,872 mm³) and `Tongue` (label 42; 521,131 voxels,
65,130 mm³). They are therefore absent from the per-muscle results, and this is
a limitation of the source segmentation rather than of the method. MIDA also
merges temporalis with temporoparietalis in a single label (63) and carries the
temporalis **tendon** separately (98); the tendon is excluded, since its
conductivity differs from muscle and it is not a source.

**Meshing.** The labelled volume was tetrahedralised with SimNIBS 4.6's
`meshmesh`, using per-label conductivity assignment (a documented feature, not
a workaround). The base mesh `mida_headneck.msh` contains **2,140,917 nodes and
15,415,273 elements**. SimNIBS meshes the two electrodes into it at solve time,
giving the solved mesh **15,415,668 elements, of which 12,294,182 are
tetrahedra** and the remainder surface triangles, and adding SimNIBS's own
electrode tags (volume 501 and 502, surface 2101 and 2102; 117 and 123
tetrahedra respectively). Element counts quoted for the solved mesh therefore
include the electrodes.

**Boundary.** MIDA terminates inferiorly at **S = −116.2 mm**, and that cut face
is treated as an insulating (homogeneous Neumann) boundary. A neck-extended
variant was constructed and **rejected**: it does not conserve charge, with flux
failing to decay toward the domain floor (1.070 mA at S = −182 mm against a
1 mA injection, where the truncated control falls to 0.107 mA at S = −119 mm).
All published results use the truncated mesh. The consequence for the
jaw-versus-ear comparison is quantified in Results (truncation sensitivity) and
carried in the error budget.

**Mesh validation.** Every tag present in the mesh carries an assigned
conductivity — verified by enumeration, **0 of 118 volume tags uncovered**. No
custom tag falls inside a SimNIBS reserved range without an explicit
conductivity; MIDA's own labels 100–116 (cerebral peduncles, optic chiasm, the
twelve cranial nerves, thalamus) do lie inside the reserved electrode-rubber
range 100–499, and are correct only because Table 1 names each of them
explicitly. This is checked at run time and is recorded as a fragility.

---

## 2. Conductivity assignment

All conductivities are listed in **Table 1** with their individual sources, and
live in a single file (`src/config.py`); no conductivity is hardcoded elsewhere.
All values are quoted at **100 Hz**, which brackets the surface-EMG band.

**Provenance is mixed, deliberately, and is stated per row in Table 1.**

- **SimNIBS 4.6 defaults** are used for the primary head tissues — skin, fat,
  compact and cancellous bone, grey and white matter, CSF, blood, eye, muscle,
  cartilage, air. These are the conventional head-modelling values, and using
  them keeps this model **comparable with the existing EEG/tDCS forward-model
  literature**, which is the point of the choice.
- **IT'IS Low Frequency database v4.2** (DOI 10.13099/VIP21000-04-2, released
  2024-06-04) supplies every tissue SimNIBS does not carry a default for —
  mandible, teeth, vertebrae, salivary glands, mucosa, dura, tendon, nerve,
  intervertebral disc, and the deep brain structures.
- A small number of assignments are **judgement**, marked as such in Table 1's
  `assignment` column, where MIDA segments a structure IT'IS does not list
  separately (e.g. deep grey nuclei mapped to Brain (Grey Matter); MIDA's split
  cerebellar grey and white both mapped to IT'IS's single Cerebellum entry).
  Each carries a note giving the reasoning.

**Air is a numerical choice, not a physical one.** True air conductivity is
zero, which makes the FEM system singular. Internal air cavities (nasal,
pharyngeal, sinuses, mastoid, auditory canal) are therefore assigned a small
finite value. The value matters because the stiffness matrix inherits
`σ_max/σ_min` as its condition number and SimNIBS solves iteratively:

- **σ_air = 1e-15 S/m fails.** The conductivity span reaches 1.879 × 10¹⁵, the
  iterative solve does not converge, and the returned fields are 10–20× too
  large while a result file is still written. The solver's own current-
  consistency check reports 200.00% on these solves.
- **σ_air = 1e-6 S/m is used throughout.** The span is 1.879 × 10⁶ and the
  solves are clean.
- A pre-flight gate refuses any assignment whose span exceeds **1 × 10⁸**, two
  orders above the working case and eight below the failing one.

**Insensitivity to the choice was measured, not assumed.** The model was solved
at σ_air = 1e-6, 1e-5, 1e-4 and 1e-3 S/m on **identical geometry**, and the
per-compartment lead field compared against the 1e-6 baseline:

| σ_air | largest \|Δ\| over the 10 muscle compartments |
|---|---|
| 1e-5 | **0.007 dB** |
| 1e-4 | **0.069 dB** |
| 1e-3 | **0.467 dB** |

**The result is insensitive across 1e-6 to 1e-4**, where the largest departure
(0.069 dB) sits roughly four times below the measured electrode-meshing noise
floor of 0.27 dB and is therefore unresolvable. **Departure begins at 1e-3**,
where the largest shift reaches 0.467 dB, about 1.7× the floor, and is
concentrated in the compartments nearest the oral and nasal cavities (mentalis
−0.467, orbicularis oris −0.433, depressor anguli oris −0.381) while the
compartments remote from air are essentially unmoved (temporalis −0.029,
lateral pterygoid −0.009). The operating value of 1e-6 therefore sits two
decades inside the insensitive range.

---

## 3. Electrode placement

All 22 positions are **derived from labelled anatomy and snapped to the outer
skin surface**, not hand-picked. An interactive picker was rejected because
clicked coordinates cannot be regenerated from a clean checkout, reviewed in a
diff, or defended in Methods. Positions are written to
`results/02_electrode_positions.csv`.

**Projection rule.** Each site is defined by an anatomical anchor plus an
offset in RAS millimetres, then projected to the **nearest outer-skin voxel**
along the surface normal. The sign of the R component is flipped automatically
for left-side placements.

**Target localisation uses a hybrid of centroid-interior and minimum-distance,
and the hybrid exists for a specific geometric reason.** For a compact
compartment, the centroid is a good interior representative and the electrode
is placed over it. For a **non-convex** compartment the centroid is not
necessarily inside the compartment at all — the mandible is the clear case: it
is an arch, and the centroid of an arch lies in the open space the arch encloses,
not in bone. Placing an electrode over that point would put it over the floor of
the mouth. So where a compartment's centroid does not lie within the
compartment, the site is instead defined by **minimum distance from the skin
surface to the compartment**, which is guaranteed to land on the structure.
Which rule applied to which site is recorded per row.

**The midline is derived, not assumed to be R = 0.** MIDA's head is not
perfectly centred in its own voxel grid, so the anatomical midline is computed
from the mandible label (36) rather than taken as the coordinate origin, and
midline sites (`mental`, `submental_mid`, `hyoid`) are placed relative to that
derived plane.

**Per-site depth** — the distance from the skin surface to the target
compartment along the placement ray — is reported for every site in
`results/02_electrode_positions.csv`, so that the geometric exposure of each
electrode is visible rather than argued.

**`pre_tragus`** is placed 14 mm anterior to the tragus, over the masseter and
the temporomandibular joint. It is included because it is the retroauricular
position with the shortest path to the mastication group, and therefore the
one most likely to carry jaw-gesture signal in a device that must sit around
the ear.

**One position is withheld.** `throat_scm` is recorded as `verified=held` with
blank coordinates: MIDA's sternocleidomastoid is truncated at the S = −116.2 mm
cut face, which biases its centroid posteriorly, so no defensible automatic
placement exists. Every consumer skips it rather than substituting a nearby
label, and it is absent from all results.

**Electrode model.** 10 mm diameter ellipse, 2 mm thickness, matching the gold
cup electrodes of the companion experiment.

---

## 4. Reciprocity

Lead fields are computed by **reciprocity**, not by forward-solving each source.

For a current dipole at position **r** with moment **p**, and a recording
electrode pair (A, B), the measured potential difference is

    V_AB(r, p)  =  E_recip(r) · p / I

where **E_recip** is the electric field produced throughout the head by
injecting a current *I* between A and B. The lead field for a source at **r**
with unit orientation **n̂** is therefore `E_recip(r) · n̂`.

**SimNIBS's tDCS solver computes exactly E_recip**, so it is repurposed here:
1 mA is injected between each electrode and a common reference
(`earlobe_contra`), and the resulting field is read inside every segmented
muscle compartment.

**The consequence is one solve per electrode instead of one per source.** A
forward formulation would require a separate solve for every dipole location
and orientation — on the order of 10⁵ solves at MIDA's resolution. The
reciprocal formulation requires **22**, one per electrode. The two formulations
are mathematically equivalent; only the cost differs.

Within each muscle compartment we report the **volume-weighted median |E|**,
which is robust to the small number of very high-field elements adjacent to
compartment boundaries.

---

## 5. Fibre orientation

Muscle is electrically anisotropic — conductivity along the fibre exceeds
conductivity across it — and MIDA carries no fibre-direction data. Orientation
is therefore **bounded rather than assumed**.

**Precedent.** Deriving muscle fibre directions by **principal component
analysis on neighbouring grid points of MIDA's own segmentation** is not novel
here: it was published by **HArtMuT** (Harmening, Klug, Gramann & Miklody 2022,
*J. Neural Eng.* 19(6):066041, doi:10.1088/1741-2552/aca8ce), which built
~3,900 muscle dipole and tripole sources from MIDA's muscle labels using that
method. We use the same approach and cite it as precedent.

**The isotropic condition is primary.** All 22 production solves assign muscle
a single isotropic conductivity (0.355 S/m). A second, anisotropic condition
assigns a per-element tensor with **σ = 0.4 S/m along the fibre and 0.1 S/m
across it**, aligned to a PCA-derived axis.

**PCA is applied only where it is a meaningful object.** A principal axis
describes a strap-like muscle; for a sphincter (orbicularis oris), a fan
(temporalis, genioglossus), a sheet (platysma, mylohyoid, buccinator) or a
multi-layered muscle (masseter, lateral pterygoid), a single axis is not merely
imprecise but the wrong kind of description. Those compartments remain isotropic
in **both** conditions. The classification and its reasoning are recorded per
muscle in `config.FIBRE_MODEL`.

**Two further restrictions apply, and both bite.** A compartment must also be
**individually segmented** to carry a per-compartment axis, which excludes the
six pooled suprahyoid and tongue muscles. And each axis must pass a
**bilateral mirror-symmetry test**: MIDA assigns one label to both sides of a
paired muscle, so PCA on the pooled voxel cloud returns the **left–right
separation between the two bellies**, not the fibre direction along either.
Axes are therefore computed **per side**, and the two must be mirror images in
x. Sternocleidomastoid passes at |dot| = 0.98 and medial pterygoid at 1.000;
**mentalis fails at 0.215** — its two fragments have a right-side elongation
ratio of 1.07, meaning no long axis exists to find — and receives no tensor.

**The anisotropic condition therefore applies a tensor to 2 of the 10
segmented muscles**: sternocleidomastoid and medial pterygoid. Every other
compartment is reported **NOT APPLIED** rather than as an unchanged or null
result, because it was never varied.

The anisotropic condition is solved on the **isotropic run's own mesh**, with
only the conductivity field replaced. SimNIBS re-meshes electrodes on each
session, and two sessions of the same montage can differ (2,140,980 against
2,140,979 nodes was observed); solving on the identical mesh removes electrode
realisation, which is comparable in size to the effect being measured, from the
comparison.

---

## 6. Validation

Validation is layered, and each layer tests something the others cannot.

**6.1 Analytic multilayer sphere.** The full pipeline is run against a
four-layer spherical head model with a closed-form solution. Over 120 source
positions spanning radii 20–75 mm, the median **RDM is 4.36%** and the median
**MAG is +4.40%**. This is the only layer that can detect a **uniform scale
error**, since no invariant computed on the head mesh can: multiplying every
field value by a constant leaves flux radius-independence, boundary
conservation, linearity and reciprocity symmetry all satisfied. The sphere is
therefore retained as a permanent pre-flight gate rather than a one-time
result, and it re-runs whenever the environment changes.

**6.2 Reciprocity on the head mesh.** The reciprocity identity is verified on
the real geometry, not only on the sphere, by solving a montage and its
polarity-swapped counterpart and requiring `L(A→B) = −L(B→A)`. On identical
discretisations the residual is **7.5 × 10⁻⁶** of |L|, i.e. **6.5 × 10⁻⁵ dB** —
four orders of magnitude below the measured per-site noise floor.

**6.3 Four physical invariants**, computed from the field alone and requiring
no solver internals:

| | invariant | detects |
|---|---|---|
| 1 | flux through a closed surface around an electrode is radius-independent, and its magnitude lies in a loose gross-error band | a stalled or non-converged solve; a uniform scale error |
| 2 | net current through a surface enclosing the whole domain is zero | current entering or leaving through the outer boundary |
| 3 | doubling the injected current doubles the field exactly | non-linearity |
| 4 | swapping source and sink negates the field | broken reciprocity on real geometry |

Invariant 1 uses an exact **tet-patch integral**: the flux is integrated over
the interior cut of a patch of tetrahedra using the mesh's own faces as the
quadrature, so enclosure and orientation are exact by construction (the patch
surface closes to 1.2 × 10⁻¹⁶ of its own area) and no inside/outside point test
is required. A stationary plateau across radii 25–75 mm is required before any
value is used. Invariants 1 and 2 run on every solve; 3 and 4 require paired
solves and run on the first and last of a batch.

All guards **collect and raise once with every failure**, rather than raising on
the first, so a solve that violates several invariants reports all of them.

**6.4 Convergence.** RDM against the analytic sphere was fitted across three
mesh densities, giving a convergence exponent **p = 0.980**, consistent with the
theoretical p ≈ 1 expected for a gradient quantity in a first-order FEM.
**This is stated as consistency, not as corroboration**: three data points
fitted with three free parameters (RDM₀, C, p) is an exact fit by construction,
so p is determined algebraically and the fit residual carries no
goodness-of-fit information. A fourth density would make it testable.

**6.5 Guard tests.** Two meta-tests protect the validation itself. A
**coverage** test resolves, from the abstract syntax tree, that every production
script actually invokes its guards — written-but-never-called has occurred
repeatedly in this codebase. A **synthetic-fire** test requires each guard to
fail on a purpose-built input that fails **that guard and nothing else**, with a
clean control that trips none; this is what detects a guard rendered
unreachable by an earlier guard's raise, which a coverage test cannot see.

---

## 6.6 Two gap statistics, and why one is retired for conductivity comparisons

A "gap" between two montages can be formed two ways, and they are not
interchangeable.

- **Statistic A — gap per orientation, then median over orientations.** For each
  sampled source orientation the same direction is applied at both electrodes,
  the gap is formed there, and the median is taken over the resulting
  distribution. **This is what the paper reports.**
- **Statistic B — orientation-median lead field per site, then differenced.**
  Two per-site medians are subtracted.

B is defective in principle because the two medians it differences need not
occur at the same orientation, and a physical source has a single orientation.
It was measured to be defective in practice, twice, on comparisons where a
**conductivity** was changed:

| comparison | statistic B | statistic A |
|---|---|---|
| adipose contrast, SCM | +1.361 dB | **+0.411 dB** |
| adipose contrast, lateral pterygoid | +0.815 dB | **+0.323 dB** |
| anisotropy, SCM | +1.448 dB | **−0.085 dB** |

The anisotropy case is wrong by a factor of 17 **and in the opposite
direction**. The shared cause is specific and predictable: changing a
conductivity **reshapes the current path** rather than scaling it, so the field
at each site peaks at a different orientation under the two conditions, and
differencing per-site medians measures that drift rather than the physics.

**Statistic B is therefore not used for any comparison in which a conductivity
differs between conditions.** It is retained in exactly one place — the
per-site sensitivity matrix (Figure 2) — because a matrix cell is a single
site's summary and a gap statistic has no per-cell form. That figure is
labelled accordingly.

## 7. Error budget

**Every published quantity in this paper is a ratio** — one site against
another, ear against jaw, muscle against muscle. That structure determines how
uncertainty is handled.

A term that scales the whole lead field equally **cancels exactly** in every
ratio and cannot reach a conclusion. A term that varies **between sites**
survives into all of them. The error budget (**Table 3**) is therefore split
into two columns on exactly that distinction — whether a term affects the
absolute lead field, and whether it affects site-to-site ratios — and terms are
admitted to the second column only when they are shown to vary per site.

The distinction is not cosmetic. Electrode contact area, for example, would
naturally be treated as a global scale factor; it is not, because each
electrode's contact is realised independently from whatever surface triangles
fall beneath it, making it per-site noise. Conversely a uniform magnitude
offset, however large, subtracts to exactly 0 dB in any site ratio.

Individual terms, their measured values, and the reasoning for each are in
Table 3 and are not restated here.

---

## 8. Reproducibility and pre-registration

Everything is reproducible from a clean checkout given MIDA in `data/`; the one
manual step (downloading MIDA, which requires registration) is documented in the
README rather than left implicit.

**The anatomical prediction was recorded before the model was solved, and the
repository is the evidence.** The `expected_at_ear` column of `config.MUSCLES` —
which predicts strong retroauricular coupling for temporalis ("directly above
ear") and sternocleidomastoid ("mastoid attachment") — entered the repository in
commit **`fa583f6`, dated 2026-08-02**. The lead-field results that test that
prediction were committed the following day, **2026-08-03**, in the commit
adding `results/03_leadfields.csv`. The prediction therefore precedes the
measurement by a day and by the entire solve pipeline, and both commits are
citable by hash in the public repository.

---

## 9. Ethics

**No human subjects were involved in this study.** It is a computational
modelling study performed on a publicly available anatomical model. No IRB
review was required or sought. No new imaging, recordings, or measurements from
living participants were acquired.
