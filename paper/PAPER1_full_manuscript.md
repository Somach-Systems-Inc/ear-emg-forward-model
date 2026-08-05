# Jaw and retroauricular electrode montages couple to different speech articulators: a volume-conductor model in a detailed head anatomy

**Carl Vincent Kho**
Somach Systems, Inc., San Francisco, CA, USA
carl@somach.life

*Draft manuscript assembled 2026-08-05. Methods from `paper/METHODS.md`;
Introduction and Discussion from `paper/INTRO_AND_DISCUSSION_draft2.md`; Results
from `paper/RESULTS_AND_CAPTIONS.md`. Working-record material (withdrawn values,
in-session corrections) has been moved out; it remains in `paper/METHODS_LOG.md`.*

---

## Abstract

**Objective.** Silent-speech interfaces and ear-worn biopotential devices are
being designed around a coupling that has not been computed: how strongly each
speech articulator muscle reaches electrodes placed on the jaw and around the
ear. Forward models of muscle sources exist, but they were built to remove
muscle activity from EEG rather than to record it, and they radiate muscle
sources through a homogeneous scalp.

**Approach.** We compute articulator-to-electrode coupling by reciprocity on
MIDA, a head model with 116 labelled compartments at 500 µm, treating muscle as
both the generator and its own anatomically resolved conducting compartment.
Twenty-two electrode positions spanning the canonical jaw montage, a
retroauricular cluster and a cEEGrid C-path are compared against ten
individually segmented articulators, under isotropic and anisotropic muscle
conductivity. The pipeline is validated against an analytic four-layer sphere
(median RDM 4.36 % over 120 sources) and by four physical invariants computed on
the head mesh itself. Every reported quantity is a ratio, and the uncertainty
budget is assembled from measured terms.

**Main results.** The two montages are complementary rather than ranked. Seven
of ten articulators couple more strongly to the best jaw electrode; three couple
more strongly to the best retroauricular electrode — temporalis by 3.92 dB,
sternocleidomastoid by 3.41 dB and lateral pterygoid by 1.69 dB — and all three
attach at or near the temporal bone. The advantages are asymmetric: the jaw's
reach 22.78 dB while the ear's do not exceed 3.92 dB. Setting adipose tissue to
muscle conductivity on identical geometry changes the jaw-versus-ear gap by only
0.33 dB, so the difference is geometric rather than a property of intervening
tissue. The anatomical prediction was recorded in the public repository one day
before the model was solved.

**Significance.** The result gives ear-worn device designers a per-muscle map
rather than a ranking: a retroauricular montage reads jaw-closing and
head-stabilising activity well and loses lip and chin activity almost entirely.
It also describes, muscle by muscle, what the retroauricular electromyographic
contamination long documented in the EEG literature actually consists of.

**Keywords:** volume conduction, surface electromyography, silent speech, ear-EEG, forward model, reciprocity

---

## 1. Introduction

Silent speech interfaces read articulator muscle activity from the surface of
the skin. When a word is articulated without voicing, the motor commands that
would drive the tongue, jaw, lips and hyoid still reach those muscles at
sub-threshold levels, and the resulting electrical activity is recoverable with
ordinary surface electrodes. The montage that dominates the literature places
those electrodes on the chin, under the jaw and along the throat [Kapur et al.
2018; Gaddy & Klein 2020], because that is where the anterior articulators are.

Ear-worn form factors have begun to appear alongside it. Retroauricular
electrode arrays demonstrably capture chewing and speaking electromyography
[Avramidou et al. 2024], ear-mounted electrodes classify jaw clench and chew
above 90 % accuracy [An et al. 2025], and the cEEGrid geometry around the pinna
is an established and widely replicated wearable configuration [Debener et al.
2015]. The appeal is not electrical. It is that an ear-worn device is socially
wearable in a way that a chin-mounted one is not.

What has not been computed is how strongly any given articulator couples to any
given position around the ear. Forward models of muscle sources in realistic
head geometry do exist: HArtMuT [Harmening et al. 2022] places roughly 3,900
muscle dipole and tripole sources derived from MIDA's muscle segmentation, with
fibre directions estimated by principal component analysis over neighbouring
grid points, solved as finite-element lead fields. That work is the
methodological precedent for the fibre-axis treatment used here.

It was built to answer the opposite question. HArtMuT's muscle sources exist so
that muscle activity can be identified and removed from scalp EEG, and they
radiate through a homogeneous scalp compartment — a simplification its authors
state explicitly, and an appropriate one for a model whose purpose is artifact
rejection. No published forward model treats facial and cervical muscle as both
the generator and its own anatomically resolved conducting compartment, and none
has been used to ask where a sensor should be placed rather than what a sensor
is contaminated by. The same absence is stated from the other direction in the
ear-EEG literature, where forward models exist for neural sources and ocular
artifacts and no theoretical treatment of muscle artifacts is available [Yarici
et al. 2023].

We compute that coupling. Using reciprocity, the electric field is solved once
per electrode on the MIDA head model with 116 anatomically labelled
compartments, and the lead field for a muscle source at any position follows by
projection. Twenty-two electrode positions spanning the canonical jaw montage, a
retroauricular cluster and a cEEGrid C-path are compared against ten
individually segmented articulators, under isotropic and anisotropic muscle
conductivity, with an uncertainty budget assembled from measured terms rather
than asserted ones.

The result is not a ranking. Seven of the ten articulators couple more strongly
to the jaw montage and three couple more strongly to the ear — temporalis,
sternocleidomastoid and lateral pterygoid, all of which attach at or near the
temporal bone. The two montages see different muscles. That prediction was
recorded in the repository a day before the model was solved, and both commits
are public and timestamped.

---

## 2. Methods

### 2.1 Head model

The volume conductor is MIDA v1.0 (Multimodal Imaging-Based Detailed Anatomical
Model of the Human Head and Neck; Iacono et al. 2015, IT'IS Foundation, DOI
10.13099/ViP-MIDA-V1.0), segmented at 500 µm isotropic.

MIDA is commonly cited as containing 153 structures. That figure describes the
CAD/surface distribution. The voxel distribution used here carries **116
labelled structures**, and every number in this paper derives from the voxel
data. We report 116 rather than 153 throughout; the discrepancy is a difference
between two distributions of the same model, not a subsetting choice.

Ten of the eighteen articulator muscles in our target set are individually
segmented and were verified present by label: masseter (66), temporalis /
temporoparietalis (63), medial pterygoid (81), lateral pterygoid (65),
orbicularis oris (75), buccinator (84), mentalis (71), depressor anguli oris
(72), platysma (60), sternocleidomastoid (68).

The suprahyoid and tongue muscles are not individually segmented. Digastric
(both bellies), stylohyoid, mylohyoid, geniohyoid, genioglossus, hyoglossus and
styloglossus are pooled into `Muscle (General)` (label 38; 1,975,307 voxels,
246,872 mm³) and `Tongue` (label 42; 521,131 voxels, 65,130 mm³). They are
therefore absent from the per-muscle results, which is a limitation of the
source segmentation rather than of the method. MIDA also merges temporalis with
temporoparietalis in a single label (63) and carries the temporalis tendon
separately (98); the tendon is excluded, since its conductivity differs from
muscle and it is not a source.

**Meshing.** The labelled volume was tetrahedralised with SimNIBS 4.6's
`meshmesh`, using per-label conductivity assignment. The base mesh contains
2,140,917 nodes and 15,415,273 elements. SimNIBS meshes the two electrodes into
it at solve time, giving 15,415,668 elements of which 12,294,182 are tetrahedra.

**Boundary.** MIDA terminates inferiorly at S = −116.2 mm, and that cut face is
treated as an insulating (homogeneous Neumann) boundary. A neck-extended variant
was constructed and rejected: it does not conserve charge, with flux failing to
decay toward the domain floor (1.070 mA at S = −182 mm against a 1 mA injection,
where the truncated control falls to 0.107 mA at S = −119 mm). All published
results use the truncated mesh; the consequence for the jaw-versus-ear
comparison is quantified in §3.4.

**Mesh validation.** Every tag present in the mesh carries an assigned
conductivity, verified by enumeration (0 of 118 volume tags uncovered). MIDA's
own labels 100–116 lie inside SimNIBS's reserved electrode-rubber range 100–499
and are correct only because Table 1 names each explicitly; this is checked at
run time.

### 2.2 Conductivity assignment

All conductivities are listed in Table 1 with individual sources and live in a
single file; none is hardcoded elsewhere. All values are quoted at 100 Hz, which
brackets the surface-EMG band.

Provenance is mixed, deliberately, and stated per row. SimNIBS 4.6 defaults are
used for the primary head tissues — skin, fat, compact and cancellous bone, grey
and white matter, CSF, blood, eye, muscle, cartilage, air — because these are
the conventional head-modelling values and using them keeps this model
comparable with the existing EEG and tDCS forward-model literature. The IT'IS
Low Frequency database v4.2 (DOI 10.13099/VIP21000-04-2) supplies every tissue
SimNIBS carries no default for. A small number of assignments are judgement,
marked as such in Table 1, where MIDA segments a structure IT'IS does not list
separately; each carries a note giving the reasoning.

**Air is a numerical choice, not a physical one.** True air conductivity is
zero, which makes the FEM system singular, so internal cavities are assigned a
small finite value. The value matters because the stiffness matrix inherits
σ_max/σ_min as its condition number and SimNIBS solves iteratively. At
σ_air = 1 × 10⁻¹⁵ S/m the span reaches 1.879 × 10¹⁵, the iterative solve does
not converge, and the returned fields are 10–20× too large while a result file
is still written. We use σ_air = 1 × 10⁻⁶ S/m throughout, giving a span of
1.879 × 10⁶. A pre-flight gate refuses any assignment whose span exceeds
1 × 10⁸.

Insensitivity to that choice was measured rather than assumed. Solving at
σ_air = 10⁻⁶, 10⁻⁵, 10⁻⁴ and 10⁻³ S/m on identical geometry, the largest
departure over the ten muscle compartments from the 10⁻⁶ baseline is 0.007 dB at
10⁻⁵, 0.069 dB at 10⁻⁴ and 0.467 dB at 10⁻³. The result is therefore
insensitive across 10⁻⁶ to 10⁻⁴, where the largest departure sits roughly four
times below the measured noise floor of 0.27 dB. Departure begins at 10⁻³, where
it reaches 1.7× the floor and concentrates in the compartments nearest the oral
and nasal cavities (mentalis −0.467, orbicularis oris −0.433) while remote
compartments are essentially unmoved (temporalis −0.029, lateral pterygoid
−0.009). The operating value sits two decades inside the insensitive range.

### 2.3 Electrode placement

All 22 positions are derived from labelled anatomy and snapped to the outer skin
surface, not hand-picked. An interactive picker was rejected because clicked
coordinates cannot be regenerated from a clean checkout, reviewed in a diff, or
defended in Methods.

Each site is defined by an anatomical anchor plus an offset in RAS millimetres,
then projected to the nearest outer-skin voxel along the surface normal.

Target localisation uses a hybrid of centroid-interior and minimum-distance, for
a geometric reason. For a compact compartment the centroid is a good interior
representative. For a non-convex compartment the centroid need not lie inside
the compartment at all — the mandible is the clear case, since it is an arch and
the centroid of an arch lies in the space the arch encloses, so an electrode
placed over that point would sit over the floor of the mouth. Where a
compartment's centroid does not lie within the compartment, the site is instead
defined by minimum distance from the skin surface to the compartment. Which rule
applied to which site is recorded per row.

The midline is derived, not assumed to be R = 0: MIDA's head is not perfectly
centred in its own voxel grid, so the anatomical midline is computed from the
mandible label and midline sites are placed relative to that plane. Per-site
depth — skin surface to target compartment along the placement ray — is reported
for every site.

`pre_tragus` is placed 14 mm anterior to the tragus, over the masseter and the
temporomandibular joint, as the retroauricular position with the shortest path
to the mastication group.

One position is withheld. `throat_scm` is recorded as held with blank
coordinates: MIDA's sternocleidomastoid is truncated at the cut face, which
biases its centroid posteriorly, so no defensible automatic placement exists.
Every consumer skips it rather than substituting a nearby label.

The electrode model is a 10 mm diameter ellipse of 2 mm thickness, matching the
gold cup electrodes of the companion experiment.

### 2.4 Reciprocity

Lead fields are computed by reciprocity rather than by forward-solving each
source. For a current dipole at position **r** with moment **p** and a recording
pair (A, B), the measured potential difference is

    V_AB(r, p) = E_recip(r) · p / I

where **E**_recip is the field produced throughout the head by injecting current
*I* between A and B. The lead field for a source at **r** with unit orientation
**n̂** is therefore E_recip(**r**) · **n̂**.

SimNIBS's tDCS solver computes exactly E_recip, so it is repurposed here: 1 mA
is injected between each electrode and a common reference (contralateral
earlobe), and the resulting field is read inside every segmented muscle
compartment. The consequence is one solve per electrode instead of one per
source — 22 solves against the order of 10⁵ a forward formulation would require
at MIDA's resolution. The formulations are mathematically equivalent; only cost
differs.

Within each compartment we report the volume-weighted median |E|, which is
robust to the small number of very high-field elements adjacent to compartment
boundaries.

### 2.5 Fibre orientation

Muscle is electrically anisotropic and MIDA carries no fibre-direction data, so
orientation is bounded rather than assumed.

Deriving fibre directions by principal component analysis on MIDA's own
segmentation is not novel here: it was published by HArtMuT [Harmening et al.
2022], which built ~3,900 muscle sources from MIDA's labels using that method.
We use the same approach and cite it as precedent.

The isotropic condition is primary: all 22 production solves assign muscle a
single isotropic conductivity of 0.355 S/m. A second, anisotropic condition
assigns a per-element tensor with σ = 0.4 S/m along the fibre and 0.1 S/m across
it, aligned to a PCA-derived axis.

PCA is applied only where a principal axis is a meaningful object. It describes
a strap-like muscle; for a sphincter (orbicularis oris), a fan (temporalis), a
sheet (platysma, buccinator) or a multi-layered muscle (masseter, lateral
pterygoid), a single axis is the wrong kind of description rather than merely an
imprecise one. Those compartments remain isotropic in both conditions.

Two further restrictions apply and both bite. A compartment must be individually
segmented to carry a per-compartment axis, which excludes the six pooled
suprahyoid and tongue muscles. And each axis must pass a bilateral
mirror-symmetry test: MIDA assigns one label to both sides of a paired muscle,
so PCA on the pooled voxel cloud returns the left–right separation between the
two bellies rather than the fibre direction along either. Axes are therefore
computed per side and required to be mirror images in x. Sternocleidomastoid
passes at |dot| = 0.98 and medial pterygoid at 1.000; mentalis fails at 0.215,
its two fragments having a right-side elongation ratio of 1.07, so no long axis
exists to find, and it receives no tensor.

The anisotropic condition therefore applies a tensor to 2 of the 10 segmented
muscles. Every other compartment is reported as **not applied** rather than as
an unchanged or null result, because it was never varied.

The anisotropic condition is solved on the isotropic run's own mesh with only
the conductivity field replaced. SimNIBS re-meshes electrodes on each session
and two sessions of the same montage can differ, so solving on the identical
mesh removes electrode realisation — comparable in size to the effect being
measured — from the comparison.

### 2.6 Validation

Validation is layered, and each layer tests something the others cannot.

**Analytic multilayer sphere.** The full pipeline is run against a four-layer
spherical head model with a closed-form solution. Over 120 source positions
spanning radii 20–75 mm, median RDM is 4.36 % and median MAG +4.40 %. This is
the only layer that can detect a uniform scale error, since no invariant
computed on the head mesh can: multiplying every field value by a constant
leaves flux radius-independence, boundary conservation, linearity and
reciprocity symmetry all satisfied. The sphere is therefore a permanent
pre-flight gate rather than a one-time result.

**Reciprocity on the head mesh.** The identity is verified on the real geometry
by solving a montage and its polarity-swapped counterpart and requiring
L(A→B) = −L(B→A). On identical discretisations the residual is 7.5 × 10⁻⁶ of
|L|, i.e. 6.5 × 10⁻⁵ dB — four orders of magnitude below the measured per-site
noise floor.

**Four physical invariants**, computed from the field alone and requiring no
solver internals: (1) flux through a closed surface around an electrode is
radius-independent; (2) net current through a surface enclosing the whole domain
is zero; (3) doubling the injected current doubles the field exactly; (4)
swapping source and sink negates the field. Invariant 1 uses an exact tet-patch
integral in which flux is integrated over the interior cut of a patch of
tetrahedra using the mesh's own faces as the quadrature, so enclosure and
orientation are exact by construction (the patch surface closes to 1.2 × 10⁻¹⁶
of its own area) and no inside/outside point test is required. A stationary
plateau across radii 25–75 mm is required before any value is used. Invariants 1
and 2 run on every solve; 3 and 4 require paired solves and run on the first and
last of a batch. All guards collect and raise once with every failure rather
than raising on the first.

**Convergence.** RDM against the analytic sphere was fitted across three mesh
densities, giving a convergence exponent p = 0.980, consistent with the
theoretical p ≈ 1 expected for a gradient quantity in a first-order FEM. This is
stated as consistency, not corroboration: three data points fitted with three
free parameters is an exact fit by construction, so p is determined
algebraically and the residual carries no goodness-of-fit information.

**Guard tests.** Two meta-tests protect the validation itself. A coverage test
resolves, from the abstract syntax tree, that every production script actually
invokes its guards. A synthetic-fire test requires each guard to fail on a
purpose-built input that fails that guard and nothing else, with a clean control
that trips none; this detects a guard rendered unreachable by an earlier guard's
raise, which a coverage test cannot see.

### 2.7 Error budget

Every published quantity in this paper is a ratio — one site against another,
ear against jaw, muscle against muscle — and that structure determines how
uncertainty is handled. A term that scales the whole lead field equally cancels
exactly in every ratio and cannot reach a conclusion. A term that varies between
sites survives into all of them. Table 3 is split into two columns on exactly
that distinction, and terms are admitted to the second column only when shown to
vary per site.

The distinction is not cosmetic. Electrode contact area would naturally be
treated as a global scale factor; it is not, because each electrode's contact is
realised independently from whatever surface triangles fall beneath it, making
it per-site noise. Conversely a uniform magnitude offset, however large,
subtracts to exactly 0 dB in any site ratio.

### 2.8 Reproducibility and pre-registration

Everything is reproducible from a clean checkout given MIDA in `data/`; the one
manual step, downloading MIDA, requires registration and is documented in the
repository README. MIDA itself cannot be redistributed under its licence and is
not included.

The anatomical prediction was recorded before the model was solved. The
`expected_at_ear` column of the muscle configuration — predicting strong
retroauricular coupling for temporalis ("directly above ear") and
sternocleidomastoid ("mastoid attachment") — entered the repository in commit
`fa583f6`, dated 2026-08-02. The lead-field results that test that prediction
were committed the following day, 2026-08-03. The prediction therefore precedes
the measurement by a day and by the entire solve pipeline, and both commits are
citable by hash.

### 2.9 Ethics

No human subjects were involved. This is a computational modelling study
performed on a licensed anatomical model. No IRB review was required or sought,
and no new imaging, recordings or measurements from living participants were
acquired.

---

## 3. Results

### 3.1 Jaw and retroauricular montages are complementary rather than ranked

Of the ten segmented articulators, seven are seen more strongly from the jaw and
three from the ear: temporalis (−3.92 dB, best site `cg01`), sternocleidomastoid
(−3.41 dB, `cg08`) and lateral pterygoid (−1.69 dB, `pre_tragus`), where a
negative gap denotes an ear advantage. All three exceed the 0.27 dB measured
electrode-meshing floor by roughly an order of magnitude. The full map is Table
4 and Figure 5; the site-by-muscle matrix is Figure 2.

The two montages' advantages are asymmetric in size, and the asymmetry is a
result rather than an artefact of scaling. The jaw's advantages are large and
broad — mentalis +22.78 dB, depressor anguli oris +15.55, buccinator +10.57,
orbicularis oris +10.37, platysma +9.29 — and concentrate on a single site,
`mental`, which is the best jaw electrode for six of the seven jaw-favouring
muscles. The ear's advantages are modest and specific, spanning 1.69 to 3.92 dB,
and distribute across three different sites. The largest jaw advantage is 5.8×
the largest ear advantage in dB.

`medial_pterygoid` at +0.62 dB is borderline and is reported as such: it clears
the floor's 0.27 dB point estimate but falls below the 95 % confidence upper
bound of 0.65 dB, so it is not counted as a clean jaw advantage.

### 3.2 The result does not depend on the isotropy assumption

Sternocleidomastoid carries a fibre tensor, and its jaw-versus-ear gap moves
from −3.41 dB to −2.77 dB — still an ear advantage, and roughly ten times the
measured floor. The other two ear-favouring muscles move by +0.11 dB
(temporalis) and −0.06 dB (lateral pterygoid); neither carries a tensor, so
those shifts are the small global redistribution caused by changing conductivity
elsewhere.

`medial_pterygoid` carries a tensor and its gap moves by only −0.03 dB.
Anisotropy raises its lead field by about 5 dB at the jaw and the ear sites
alike, so the effect cancels in the site-to-site ratio — a direct demonstration
of the argument Table 3 is organised around.

### 3.3 The gap is geometric, not a property of intervening tissue

Each canonical site is separated from its named target by 1.5–14.0 mm of
subcutaneous adipose tissue (Table 2), which sits at 0.025 S/m against muscle at
0.355 S/m. Solving the full montage twice on identical geometry — once with
adipose at 0.025 S/m and once with both adipose compartments set to muscle
conductivity — attributes any difference to material properties alone, since
source-to-electrode distance is unchanged by construction.

Every site loses signal when fat is made conductive, by a median of 2.36 to
3.91 dB, but that shift is very nearly common across sites and cancels in every
ratio reported here. What survives is the differential: jaw sites shift by a
median of −3.172 dB and retroauricular sites by −2.840 dB, so the conductivity
contrast contributes **0.33 dB** to the jaw-versus-ear gap. That is 1.2× the
measured floor and 1.5 % of an effect reaching 22.78 dB.

`medial_pterygoid` is the exception: its gap is +0.62 dB and the material
contribution is 0.33 dB of it, over half, so this already-borderline value
receives no mechanistic reading.

### 3.4 Truncation sensitivity

MIDA is cut at S = −116.2 mm with an insulating face, and three jaw sites sit
within 10 mm of it (`hyoid` 8.0, `submental_lat` 8.4, `submental_mid` 9.7) while
every ear site is 80 mm or more away, so reflection at that face inflates the
jaw side and flatters the comparison. Reporting the gap over all seven jaw sites
and again over the four clear of the cut:

- median gap **+6.45 dB → +5.91 dB**, a shift of **−0.54 dB**
- **no sign flips**: which montage wins is unchanged for **10 of 10** muscles
- every |gap| still clears the 0.27 dB measured floor

The structural reason matters more than the number. Only three muscles move at
all — `medial_pterygoid` (−1.33), `platysma` (−1.18), `sternocleidomastoid`
(−0.88). For the other seven the best jaw electrode was never a near-cut site,
so excluding them cannot change the maximum: those muscles are immune by
construction rather than by luck.

---

## 4. Discussion

### 4.1 What complementarity means

The result this model returns is not a loss figure. A single scalar cannot
express it: summing sensitivity over muscles — the natural way to rank electrode
positions, and the analysis this study originally planned — collapses a sign
change into an average dominated by the anterior articulators, where the jaw
wins by 10 to 23 dB. The three muscles the ear actually sees better disappear
into that total. The finding is only visible per muscle, which is why Figure 5
is a map rather than a ranking.

Complementarity should not be read as parity. An ear-mounted montage does not
trade evenly against a jaw montage: it gives up most of the labial group and
gains a little, at specific positions, on three muscles that attach at or near
the temporal bone. Any claim that ear-worn silent speech is simply a
repositioning of the jaw montage is not supported by this model.

### 4.2 The prediction preceded the measurement

The three muscles the ear wins on are the three whose attachments sit at or near
the temporal bone. Temporalis originates in the temporal fossa, directly beneath
the superior cEEGrid row, and its best site is the most superior one.
Sternocleidomastoid inserts on the mastoid process, and its best site is the
posterior-inferior one. Lateral pterygoid inserts at the mandibular condyle and
temporomandibular joint capsule, which articulates with the temporal bone's
mandibular fossa, and its best site is the most anterior ear position.

This was written down before the model was solved (§2.8). The anatomical
reasoning is not new; the attachments are in any textbook. What the model adds
is that a volume-conductor solution, given only tissue geometry and
conductivities, reproduces the prediction without being told it. That constrains
how much of the result can be an artifact of electrode placement choices, since
placements were derived by normal projection from anatomical landmarks rather
than tuned.

### 4.3 The mechanism is distance, not intervening tissue

It is tempting to attribute the ear's deficit to the adipose layer between each
electrode and its target, and the limb literature cannot settle the question,
since adding a fat layer to a model changes source-to-electrode distance and
material properties together [Kuiken et al. 2003]. A labelled head model can
separate them, because conductivity can be changed with geometry held exactly
fixed.

The measurement (§3.3) says the conductivity contrast contributes 0.33 dB to a
gap reaching 22.78 dB. **The labial group's attenuation at the ear is distance,
not intervening tissue.** The contrast is measurable and is not the mechanism.

The swap bounds the conductivity contrast, not subject adiposity — it does not
simulate a leaner subject. The contrast as it stands favours the jaw by 0.33 dB,
so erasing it would shrink the jaw's advantage rather than the ear's.

### 4.4 What this licenses for device design

The design statement this supports is narrower and more useful than "the ear
works." A retroauricular montage should read jaw-closing and head-stabilising
activity well and lose lip and chin activity almost entirely. For a device whose
target is jaw-gesture detection, clench-based input, or bruxism monitoring, the
ear is not a compromise position and may be the better one. For a device whose
target is labial articulation, the model says the ear costs 10 to 23 dB and no
electrode position recovers it.

Two qualifications belong with that statement. Sternocleidomastoid is a strong
coupling to a muscle that may carry little speech information; the model says
the ear sees it well, not that seeing it is useful. And `medial_pterygoid`
remains borderline (§3.1).

### 4.5 Contamination, described muscle by muscle

The EEG literature has documented mastoid and retroauricular electromyographic
contamination for decades as a nuisance to be suppressed [Goncharova et al.
2003; Yao et al. 2019]. This model says what that contamination consists of. The
three compartments a retroauricular electrode couples to most strongly, relative
to the canonical jaw montage, are temporalis, sternocleidomastoid and lateral
pterygoid — and their best positions differ, so contamination at `cg01` is not
the same mixture as contamination at `cg08`.

That is usable in the rejection direction as well as the sensing one. A spatial
filter informed by which muscle dominates at which contact is a different object
from one treating retroauricular electromyography as a single nuisance
component.

### 4.6 A specific prediction for a companion experiment

This model makes a falsifiable prediction for a physical experiment recording
both montages at once. The prediction is specific rather than a decibel budget:
gestures driven by temporalis (jaw elevation, clenching) and lateral pterygoid
(protrusion, lateral excursion) should be retained at a retroauricular montage,
while gestures driven by the labial group — mentalis, depressor anguli oris,
buccinator, orbicularis oris — should degrade sharply. An eight-channel rig
split four jaw and four ear, recording identical utterances, tests this
directly. If it shows the opposite pattern, this model is wrong in a way that
can be located.

### 4.7 Limitations

**Ten of eighteen muscles are modelled, and the two carrying the strongest
version of the anatomical argument are not among them.** MIDA does not
individually segment the suprahyoid group or the tongue. Posterior digastric and
stylohyoid — the two muscles that anchor at the mastoid notch and styloid
process, and that motivated the retroauricular hypothesis in the first place —
are therefore absent from the per-muscle map. The complementarity result is
silent exactly where the a-priori argument was strongest, and the spatial
sensitivity field reported over the pooled compartments is a partial substitute
rather than an equivalent one.

**One anatomy, with one component of that limitation bounded.** MIDA is a single
subject, and between-subject variance in muscle geometry, adipose thickness and
pinna position cannot be estimated from one head. The fat swap narrows what that
means in practice: the conductivity contrast contributes 0.33 dB to a gap
reaching 22.78 dB, so the result is driven by the geometric relationship between
muscle attachments and electrode positions rather than by tissue composition.
Skeletal attachment geometry is more conserved between individuals than adipose
distribution is, which is a reason to expect the complementarity pattern to hold
more widely than a single-subject model would otherwise support. It is a reason,
not a demonstration; only a second anatomy demonstrates it.

**The inferior boundary is an unquantified limitation whose bias runs against
the ear.** A neck-extended mesh was built specifically to measure it and did not
conserve charge, so the pre-committed decision rule was recorded unexecuted
rather than applied or revised. What can be said is §3.4: excluding the three
near-cut jaw sites moves the median gap by only −0.54 dB and flips no signs, and
seven of ten muscles are immune by construction. The magnitude of the residual
bias is unknown rather than estimated, and its direction flatters this paper's
own headline comparison.

**Static geometry.** The model is solved on a single anatomical configuration.
Articulation moves the tongue, opens and closes the oral cavity and alters the
airway, all of which change the volume conductor during the task being measured.
Nothing here quantifies that, and the jaw montage sits closer to the moving
structures than the ear montage does.

**Quasi-static assumption**, standard at surface electromyography frequencies
and stated for completeness.

**Fibre orientation is bounded, not known** (§2.5). A fibre tensor reaches two
of ten segmented muscles, and rows without one are reported as not applied
rather than as zero change.

---

## Tables

**Table 1 — Tissue conductivities.** All 116 MIDA labels with assigned
conductivity, source (SimNIBS 4.6 default / IT'IS LF v4.2 / judgement),
frequency, plausible range for judgement rows, volume fraction and minimum
distance to the nearest electrode. Sorted by volume fraction × proximity.
[`results/table1_conductivities.csv`]

**Table 2 — Tissue layer stack beneath each canonical site.** Millimetres per
MIDA tissue along the ray from each electrode through the full thickness of its
target.

| Site | Target | Target thickness traversed | Fat before target |
|---|---|---|---|
| `submaxillary` | Mandible | 27.25 mm | 2.75 mm |
| `pre_tragus` | Masseter | 17.25 mm | 5.50 mm |
| `midjaw` | Masseter | 16.50 mm | 9.00 mm |
| `submental_lat` | Mandible | 11.00 mm | 1.50 mm |
| `buccal` | Buccinator | 8.00 mm | 8.75 mm |
| `submental_mid` | Mandible | 7.25 mm | 7.25 mm |
| `hyoid` | Hyoid Bone | 6.25 mm | 14.00 mm |
| `above_ear` | Temporalis | 6.00 mm | 1.75 mm |
| `mental` | Mentalis | 2.75 mm | 5.00 mm |

**Table 3 — Error budget.** Read the last two columns first: every published
claim here is a ratio, so a term that scales the whole lead field equally
cancels and never reaches a conclusion, while a term varying between sites
survives into all of them.

| # | Term | What sets it | Affects absolute | Affects ratios | Value |
|---|---|---|---|---|---|
| 1 | Discretisation | finite element size | yes | partly | not separable from term 6 at current precision |
| 2 | Interface proximity | source near a conductivity boundary | yes | yes | requires a geometry decoupling eccentricity from interface distance; not measured |
| 3 | Inferior boundary | MIDA's cut face | yes | yes — jaw sites, not ear | unquantified; bounded by §3.4 |
| 4 | Muscle anisotropy | σ tensor vs scalar | yes | yes | SCM gap −3.41 → −2.77 dB; medial pterygoid −0.03 dB |
| 5 | Fibre orientation | n̂ unknown in MIDA | yes | yes | per-muscle min–max envelope |
| 6 | Electrode meshing | contact area from incidental surface triangulation | yes | **yes — per-site** | **0.27 dB, 95 % CI [0.17, 0.65], n = 6** |
| 7 | Single anatomy | MIDA is one subject | yes | unknown | not quantifiable from one head |
| 8 | Delivered current | injected vs requested per solve | yes | bounded by row 6 | 0.887–1.075 × requested across 22 solves |
| 9 | Adipose conductivity | fat at 0.025 vs muscle S/m | yes | yes | **0.33 dB on the jaw-vs-ear gap** |

Row 6 is measured by rotating the electrode array and the source points together
on a fixed mesh, which preserves every source-to-electrode vector (verified to
2.8 × 10⁻¹⁴ mm) so the exact answer is identical across draws and the whole
spread is realisation noise. The term splits into a common-mode part (SD
4.93 pp, 0.42 dB, cancels in a ratio) and an electrode-specific residual (SD
3.18 pp, 0.27 dB, does not). The reported statistic is the mean over 16
electrodes of the per-electrode SD across 6 draws, with a chi-square interval at
df = 5.

Row 7 is deliberately left unquantified. A single-subject model cannot estimate
its own between-subject variance.

**Table 4 — Which montage sees which muscle** (near-cut jaw sites excluded).

| Muscle | Best jaw | Best ear | Gap (dB) | Wins |
|---|---|---|---|---|
| mentalis | `mental` | `cg10` | +22.78 | jaw |
| depressor anguli oris | `mental` | `cg10` | +15.55 | jaw |
| buccinator | `mental` | `cg10` | +10.57 | jaw |
| orbicularis oris | `mental` | `cg10` | +10.37 | jaw |
| platysma | `mental` | `cg10` | +9.29 | jaw |
| masseter | `mental` | `cg10` | +2.53 | jaw |
| medial pterygoid | `submaxillary` | `cg09` | +0.62 | jaw, **borderline** |
| lateral pterygoid | `midjaw` | `pre_tragus` | **−1.69** | **ear** |
| sternocleidomastoid | `midjaw` | `cg08` | **−3.41** | **ear** |
| temporalis | `midjaw` | `cg01` | **−3.92** | **ear** |

---

## Figure captions

**Figure 1.** MIDA head model with the ten segmented articulator compartments
highlighted, and all 22 electrode positions shown in lateral, frontal and
posterior views. The face is masked above the orbital rim in accordance with the
MIDA licence.

**Figure 2. Articulator sensitivity matrix.** Median lead field in each
segmented muscle compartment for each electrode site, in dB relative to that
muscle's best jaw site (0 dB, ringed). Isotropic condition, truncated mesh, 22
electrodes × 10 muscles. The colour scale is diverging about 0 dB: red is
attenuation relative to the best jaw site, blue is a site that exceeds it, and
boxed cells mark every (site, muscle) pair where a retroauricular electrode
beats every jaw electrode. The two arms are not equally scaled (−28 to 0 dB
against 0 to +4 dB), so colour saturation is not comparable across the midpoint;
the boxes carry the sign independently of colour. **The 0 dB reference here
includes all jaw sites, whereas Figure 5 and Table 4 exclude those within 10 mm
of the truncation face, so the named best jaw site differs for some muscles.**

**Figure 3.** Attenuation against source depth for each articulator, jaw sites
against retroauricular sites.

**Figure 4. Anisotropy robustness check.** Change in lead field between the
isotropic and anisotropic conditions, 20·log₁₀(aniso/iso), per cell. The
anisotropic condition is solved on the isotropic run's own mesh, so the two
differ in conductivity alone and carry no electrode-realisation noise. A fibre
tensor is applied to 2 of 10 muscles — sternocleidomastoid and medial pterygoid.
Rows without a tensor are labelled **not applied**, not zero: they were never
varied, so no null result was measured for them.

**Figure 5. Which montage sees which muscle.** For each articulator, the
difference between the best jaw site and the best retroauricular site, in dB.
Negative bars are muscles the ear sees more strongly. Jaw sites within 10 mm of
the truncation face are excluded. The shaded band is the measured
electrode-meshing floor (0.27 dB, with the lighter band extending to its 95 % CI
upper bound of 0.65 dB). The axis is linear in dB rather than a rank, because
the asymmetry between the arms is itself a result: the jaw's advantages reach
+22.78 dB while the ear's reach only −3.92 dB.

**Figure 6. Suprahyoid sensitivity field.** Sagittal and coronal slices of |E|
through the pooled `Muscle (General)` compartment for the retroauricular
montage, with the mastoid notch, hyoid greater horn and the corridor between
them overlaid. Reported as a field rather than as per-muscle values because MIDA
does not segment the suprahyoid group.

**Supplementary Figure S1.** Air-void inventory: volume and depth below skin for
all nine air-filled compartments in MIDA.

---

## Data and code availability

All analysis code, electrode definitions, conductivity assignments and result
tables are available at `github.com/Somach-Systems-Inc/ear-emg-forward-model`.
The MIDA model itself cannot be redistributed under its licence and must be
obtained from the IT'IS Foundation; `REPRODUCTION.md` documents the one manual
step. Commits `fa583f6` (2026-08-02) and the lead-field commit (2026-08-03) are
cited in §2.8 as the pre-registration record.

---

## References

1. An, et al. (2025). ID.EARS. *CHI '25*.
2. Avramidou, et al. (2024). From Ear-EEG to Ear-ExG: The Jaw Artifact is a Keeper. *DSAI '24*.
3. Debener, S., et al. (2015). Unobtrusive ambulatory EEG using a smartphone and flexible printed electrodes around the ear. *Sci Rep* 5:16743.
4. De Luca, C. J., et al. (2011). Inter-electrode spacing of surface EMG sensors. *J Biomech*.
5. Gaddy, D., & Klein, D. (2020). Digital Voicing of Silent Speech. *EMNLP*.
6. Goncharova, I. I., et al. (2003). EMG contamination of EEG: spectral and topographical characteristics. *Clin Neurophysiol*.
7. Harmening, N., Klug, M., Gramann, K., & Miklody, D. (2022). HArtMuT — modeling eye and muscle contributors in neuroelectric imaging. *J Neural Eng* 19(6):066041. doi:10.1088/1741-2552/aca8ce
8. Iacono, M. I., et al. (2015). MIDA: A Multimodal Imaging-Based Detailed Anatomical Model of the Human Head and Neck. *PLOS ONE*. doi:10.1371/journal.pone.0124126
9. Kappel, S. L., Makeig, S., & Kidmose, P. (2019). Ear-EEG Forward Models: Improved Head-Models for Ear-EEG. *Front Neurosci* 13:943. doi:10.3389/fnins.2019.00943
10. Kapur, A., Kapur, S., & Maes, P. (2018). AlterEgo: A Personalized Wearable Silent Speech Interface. *IUI '18*.
11. Kuiken, T. A., Lowery, M. M., & Stoykov, N. S. (2003). The effect of subcutaneous fat on myoelectric signal amplitude and cross-talk. *Prosthet Orthot Int* 27(1):48–54. doi:10.3109/03093640309167976
12. Maksymenko, K., Deslauriers-Gauthier, S., & Farina, D. (2021). Ultra fast and highly realistic numerical modelling of surface EMG. *bioRxiv*.
13. Meiser, A., Knoll, J., & Bleichner, M. G. (2024). High-density ear-EEG for understanding ear-centered EEG. *J Neural Eng* 21(1):016001. doi:10.1088/1741-2552/ad1783
14. Mesin, L. (2020). Crosstalk in surface electromyogram: literature review. *Phys Eng Sci Med*. doi:10.1007/s13246-020-00868-1
15. Sato, W., & Kochiyama, T. (2023). Crosstalk in Facial EMG and Its Reduction Using ICA. *Sensors* 23:2720.
16. Thielscher, A., et al. SimNIBS. *[complete citation before submission]*
17. Wand, M., & Schultz, T. (2011). Session-Independent EMG-Based Speech Recognition.
18. Yao, D., et al. (2019). Which Reference Should We Use for EEG and ERP practice? *Brain Topogr*.
19. Yarici, M., Thornton, M., & Mandic, D. P. (2023). Ear-EEG sensitivity modeling for neural sources and ocular artifacts. *Front Neurosci* 16:997377. doi:10.3389/fnins.2022.997377

---

# ASSEMBLY NOTES — not part of the manuscript

## What I removed, and why

All of this is working record. It stays in `METHODS_LOG.md`; none of it belongs
in a paper.

- **Every "withdrawn / corrected / recorded rather than quietly fixed" note.**
  The bootstrap interval [0.16, 0.28], the 0.43 dB and 0.1310 dB floors, the
  Table 2 percent-of-path version, the anti-correlation claim about SimNIBS's
  calibration, the AlterEgo provenance note, the Kappel attribution correction.
  A paper states the current value and its derivation.
- **The MAG disposition section.** Three paragraphs on why MAG is unquotable.
  Reduced to reporting the value in §2.6 alongside RDM. Keep the longer version
  for the SimNIBS thread, where it is the point.
- **Row 2's failed interface-proximity measurement** and the r = 40 mm anomaly.
  Reduced to one Table 3 cell saying it needs a different geometry.
- **The neck-extension diagnostic history.** Reduced to "constructed and
  rejected, does not conserve charge," with the discriminating number.
- **Channel-redundancy section.** It describes an analysis that has not been
  run. Removed rather than promised — add it back when the correlation matrix
  exists.
- **Fig 7.** Deleted per the falsification; the air-void inventory survives as
  supplementary.
- **Table 2b.** Not computed. Removed rather than promised.

## What is still missing before submission

1. **Figures 1, 3 and 6** do not exist yet. Fig 1 needs `anonymise_head()`.
2. **Table 1 CSV** needs exporting to a publication-ready form.
3. **SimNIBS citation** is incomplete (ref 16).
4. **`throat_scm`** is withheld; if you measure it on the rig before submission,
   it becomes a 23rd position and §2.3 changes.
5. **Repo must be public** for §2.8's pre-registration citation to be checkable.
6. **Author affiliation** — decide whether Minerva appears alongside Somach.

## Two things you should decide

**The title.** The working title ("Where can you hear the tongue from the ear?")
is now wrong twice over: the tongue muscles are pooled and absent from the
result, and the finding is complementarity rather than a loss. I've replaced it
with a declarative one. If you want the question form back, make it about the
actual finding.

**Whether §4.4 stays.** It names uses you are not chasing — clench input,
bruxism monitoring. It widens who cites this beyond silent speech. Cut it if you
would rather keep the paper narrow.
