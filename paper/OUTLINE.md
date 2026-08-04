# Paper 1 — Outline

**Working title:**
*Where can you hear the tongue from the ear? A volume-conductor model of articulator muscle sources at retroauricular electrode sites*

**Type:** Computational / modelling study
**Human subjects:** none (n = 0)
**IRB:** not required — no human subjects. State this explicitly in Methods.
**Target:** arXiv preprint first → *Journal of Neural Engineering* (rolling) or *Sensors* (rolling)

---

## The one-sentence claim

**The two montages do not see the same muscles.** We compute, for the first time, how strongly each speech-articulator muscle couples to electrodes placed around the ear, and find that jaw and retroauricular montages are **complementary rather than ranked**: jaw sites dominate for the anterior articulators, and retroauricular sites dominate for temporalis, sternocleidomastoid and lateral pterygoid.

*(Reframed 2026-08-03 on the stage-4 measurement. The previous framing was "the ear loses X dB versus the jaw, and quantifying that loss is the contribution", which presumes a single axis on which one montage is worse. The data has a **sign change**: three of ten muscles are picked up more strongly at the ear than at the best jaw site — temporalis **+3.92 dB**, sternocleidomastoid **+2.53 dB**, lateral pterygoid **+1.69 dB**, all clearing the 0.27 dB measured floor. A loss figure cannot express that, and averaging over muscles hides it.)*

---

## Why this is a real gap (verified)

Two literatures exist and they do not touch:

| Literature | Sources modelled | Geometry |
|---|---|---|
| Head volume conduction (EEG / MEG / tDCS) | **brain** dipoles, sometimes ocular | detailed head models — but tissue segmentation stops at brain/CSF/skull/scalp |
| Surface EMG volume conduction | **muscle** fibres | cylindrical or limb FEM geometries |

> ## 🛑 THIS CLAIM IS FALSIFIED — DO NOT WRITE ON IT
>
> **Harmening, Klug, Gramann & Miklody (2022), *HArtMuT*, J. Neural Eng.
> 19(6):066041, doi:10.1088/1741-2552/aca8ce** already published ~3,900 muscle
> dipole/tripole sources built from **MIDA's own** muscle segmentation, with
> fibre directions from **PCA on neighbouring grid points** (this paper's
> proposed method), solved as FEM leadfields on the New York Head. It asserts
> the same gap verbatim before closing it. Verified by direct fetch, not
> inferred.
>
> **What survives:** muscle as both source AND its own anisotropic tissue,
> in MIDA's native geometry, for a coupling question at ear electrodes.
> HArtMuT's muscle sources radiate through **homogeneous scalp** and its
> authors say so in print. Yarici et al. 2023 is undamaged.
>
> **Rewriting the novelty framing is Carl's call**, not an agent's. See
> `paper/GAP_CHECK.md` and METHODS_LOG. The PCA fibre-axis method must cite
> HArtMuT as precedent rather than claim it.

~~Nobody has published muscle-source dipoles in an anatomically detailed head model.~~

The gap is stated explicitly in the ear-EEG modelling literature: forward models exist for neural and **ocular** sources, but *"to date, there is no theoretical study of such artifacts in ear-EEG"* for muscle (**Yarici, Thornton & Mandic 2023**, *Ear-EEG sensitivity modeling for neural sources and ocular artifacts*, Front. Neurosci. 16:997377).

> **Attribution corrected 2026-08-03.** This sentence was previously attributed here to "Kappel et al." **Kappel is not an author of it.** Verified by fetching the Frontiers article directly: the sentence appears verbatim in Yarici, Thornton & Mandic (2023), and the paper's own title — neural sources and ocular artifacts, with muscle conspicuously absent — is what makes it the right citation for this gap. A genuine Kappel forward-model paper exists (Kappel, Makeig & Kidmose 2019, Front. Neurosci. 13:943) and may be cited alongside, but it carries no muscle-gap statement. **The gap changes owner, not validity.** See `paper/CITATIONS.md`.

Meanwhile the empirical side has moved without theory:
- Retroauricular arrays demonstrably capture chewing and **speaking** EMG (Avramidou et al. 2024, *"From Ear-EEG to Ear-ExG: The Jaw Artifact is a Keeper"*)
- Ear-mounted electrodes classify jaw clench and chew at >90% (An et al. 2025, ID.EARS)
- Ear-mounted electrode grids around the pinna (**cEEGrid**) are an established, widely replicated wearable form factor (Debener et al. 2015, Sci Rep 5:16743)

> **The AlterEgo line was REMOVED here on 2026-08-03, not corrected.** It read "AlterEgo's **2026** device moved from a jaw-wrapping band to an **ear-mounted** form factor." The year was wrong (the *Silent Sense* reveal was **September 2025**), "ear-mounted" overstated sources describing a device resting largely on the back of the head and still sensing face, jaw and neck, and no paper, white paper or press release with a stable identifier exists. It had **no citable primary source**.
>
> **Provenance, recorded because it matters more than the correction:** the claim was Carl's, written in the first session, and it sat unverified in this file and in `CLAUDE.md` for several days, propagating into the motivation as though it were sourced. A wrong year that happens to match the current one is the hardest kind to catch, because it reads as up to date.
>
> The motivation does not need it. The three citations above are peer-reviewed and carry "devices are being designed for a coupling nobody has modelled" on their own. Kapur, Kapur & Maes (2018, IUI) remains the only peer-reviewed AlterEgo source and may be cited for the *original* jaw-wrapping device.

**So: devices are being designed for a coupling nobody has modelled.** That is the paper.

---

## Method

### Head model
**MIDA** (IT'IS Foundation) — 153 anatomical structures at 500 µm isotropic, free, DOI 10.13099/ViP-MIDA-V1.0.
Confirmed segmented and relevant: masseter, temporalis, medial + lateral pterygoid, orbicularis oris, buccinator, zygomaticus major/minor, risorius, depressor anguli oris, mentalis, platysma, sternocleidomastoid, splenius capitis.

✅ **RESOLVED 2026-08-02** (was: "⚠️ verify on download — digastric, stylohyoid, mylohyoid, geniohyoid, genioglossus may sit inside a generic muscles catch-all").

They do. MIDA v1.0's voxel distribution carries **116 labelled structures**, and none of the suprahyoid or tongue muscles is among them. They are pooled into two compartments:

| Label | Name | Voxels | Volume |
|---|---|---|---|
| 38 | `Muscle (General)` | 1,975,307 | 246,872 mm³ |
| 42 | `Tongue` | 521,131 | 65,130 mm³ |

**The awkward branch applies.** Digastric posterior belly and stylohyoid — the two muscles that anchor at the mastoid and carry the strongest version of the argument — must be sub-segmented by hand from label 38, and the procedure reported as a methods limitation.

10 of the 18 muscles in `src/config.py` are individually segmented and verified: masseter (66), temporalis/temporoparietalis (63), medial pterygoid (81), lateral pterygoid (65), orbicularis oris (75), buccinator (84), mentalis (71), depressor anguli oris (72), platysma (60), sternocleidomastoid (68).

Note also that MIDA merges **temporalis with temporoparietalis** in label 63, and carries the temporalis tendon separately (98). Full inventory: `results/01_label_inventory.csv`.

> The 153-structure figure quoted from Iacono et al. (2015) describes the CAD/surface distribution. The voxel distribution actually used here has 116. Reconcile this in Methods before submission rather than quoting 153 for a model we mesh from 116 labels.

### Solver
**SimNIBS 4.6** — FEM, tetrahedral, native Apple Silicon. Custom tissue labels are a documented feature (`meshmesh` + per-label conductivity assignment), not a workaround.

### The reciprocity trick (this is the core method)

Do **not** place thousands of muscle-fibre sources and solve forward for each. Instead use reciprocity:

> Inject unit current at an electrode pair, solve for the electric field **E** throughout the head. The lead field for a source at position **r** with orientation **n̂** is then `L = E(r) · n̂`.

Practically: run SimNIBS's **tDCS solver** with 1 mA at each candidate montage, and read the resulting E-field inside each muscle compartment. One solve per montage instead of one per source. This turns an intractable problem into ~20 solves.

Cite the standard reciprocity formulation and note that SimNIBS's tDCS pipeline is being repurposed — that framing is itself a small methods contribution.

### Muscle anisotropy — the methodological angle
Muscle conductivity is anisotropic: roughly **0.4 S/m along fibres, 0.1 S/m across**. Nearly every head model treats tissue as isotropic because brain sources don't care much.

Run it **both ways**. If anisotropy materially changes the ear-site sensitivity estimate, that is a finding in itself: *isotropic head models systematically mis-estimate muscle coupling.*

### Bounding fibre-orientation uncertainty

Both anisotropy and source orientation depend on knowing which way muscle fibres run, and **MIDA does not contain that information** — its diffusion data covers brain water, not muscle. Rather than assume directions we cannot support, we bound them. Two effects are separated because they are different problems with different costs.

**1. Source orientation — bounded, no extra solves.** A fibre's current dipole runs along the fibre, and the lead field is `L = E(r) · n̂`. Since **E** is already solved, n̂ is swept over the hemisphere per muscle and reported as a median with a min/max envelope. Every sensitivity value in the paper therefore carries an orientation error bar rather than a point estimate that silently assumes a direction.

**2. Tissue anisotropy — two solves, not one per muscle.** Run A isotropic; Run B anisotropic, using a PCA principal axis as the fibre direction *only* for muscles where a principal axis is a meaningful object.

That restriction is the point. A principal axis describes a strap-like muscle well and is not merely imprecise but categorically wrong elsewhere:

| Treatment | Muscles | Why |
|---|---|---|
| PCA axis | digastric (both bellies), stylohyoid, geniohyoid, SCM, styloglossus, hyoglossus, medial pterygoid, mentalis | strap-like; fibres run along the long axis |
| Isotropic in both runs | orbicularis oris, temporalis, genioglossus, platysma, masseter, lateral pterygoid, mylohyoid, buccinator, depressor anguli oris | sphincter (ring), fan, sheet, or multiple layers at different angles |

Orbicularis oris is the clearest case: it is a sphincter whose fibres run in a ring, so a single axis is a category error, not an approximation. Temporalis is a fan whose anterior fibres are vertical and posterior fibres nearly horizontal; one axis describes neither.

**The muscles carrying the ear argument — digastric posterior belly, stylohyoid, SCM, and the styloid-origin tongue muscles — all fall in the PCA-defensible set.** The anisotropy treatment is therefore strongest exactly where the argument needs it, which is worth stating explicitly rather than leaving for a reviewer to notice.

**Why this is the stronger claim.** The question was never "what are the true fibre directions?" but "does fibre orientation materially change the ear sensitivity estimate?" That needs a bound, not ground truth. A narrow envelope shows fibre direction does not matter here, and every future head model can ignore it. A wide envelope quantifies how much it matters and motivates measuring it. Both outcomes publish, and the reviewer question "how do you know the fibre directions?" is answered with *we don't, so we bounded them* rather than *we assumed PCA*.

Reference points from the implementation's self-test: a perfectly aligned compartment yields a ~59 dB orientation envelope, a fully isotropic one ~0.3 dB. Real muscles fall between, and where they fall is a result.

### Reporting a field, not eighteen numbers

MIDA does not segment the suprahyoid group or the tongue muscles; they sit
pooled inside `Muscle (General)` (label 38, 1,975,307 voxels) and `Tongue`
(label 42, 521,131 voxels). We do **not** hand-segment them.

The reason is that reciprocity gives **E** everywhere in the volume.
Compartments are only how a result is *summarised*, never how it is computed,
so pooling is a reporting problem rather than a computational one. We therefore
report the field two ways:

1. **Per-compartment medians** for the 10 muscles MIDA actually segments (Fig 2).
2. **A spatial sensitivity field** over the pooled compartments, with
   anatomically-defined ROI corridors overlaid (Fig 6).

Each corridor is the subset of a pooled compartment lying inside a capsule
between two landmarks MIDA *does* segment: the **mastoid notch**, taken as the
inferior tip of `Air Internal - Mastoid` (30), and the **hyoid greater horn**,
taken as the ipsilateral half of `Hyoid Bone` (87). Both muscles central to the
argument run between these regions — digastric posterior belly from the mastoid
notch to its intermediate tendon at the hyoid, stylohyoid from the styloid to
the hyoid, nearly parallel and slightly anterior.

**The styloid process is not segmented in MIDA.** We searched `Skull` (40) for
an isolated process in every plausible box below and medial to the mastoid; the
skull is a single connected component and no separable spike exists at 500 µm.
So we build **one** corridor containing both muscles and report |E| as a
function of position along and across it, rather than inventing a styloid
coordinate. A reader with their own anatomical prior can read off the anterior
sub-band where stylohyoid lies; we do not bake that prior in.

Corridor geometry on the right side: length 85.1 mm; at the default 12 mm
radius the ROI holds 46,295 `Muscle (General)` voxels (5,786 mm³, 2.3% of the
pool). Radius is swept over 8–18 mm and the sensitivity reported, because the
radius is a choice. Occupancy is continuous along the corridor with no empty
bins, though the first 10% contains almost no muscle (6 voxels) — the mastoid
air cells' inferior tip sits somewhat superior to the true digastric fossa, so
the ROI effectively begins about 10 mm distal. That is a property of the
landmark proxy and is reported, not hidden.

**Why this is stronger than per-muscle numbers.** "We compute a spatial
sensitivity field and show the retroauricular montage's peak within the
suprahyoid corridor" is more falsifiable than "muscle X has sensitivity Y". It
hands readers a field they can re-analyse under their own anatomical priors
instead of eighteen numbers that bake in ours. And it retires the reviewer
question "how confident are you in that segmentation?" by never making one.

### The inferior boundary — a bias that runs one way

MIDA is cut at S = −116.2 mm and SimNIBS applies an insulating boundary there,
so current reflects at the cut face rather than continuing down the neck. The
error is not uniform across the montage: `hyoid` sits ~8 mm from that face,
`throat_scm` ~23 mm, and every ear site 80 mm or more. It therefore inflates
the lead field at the jaw sites and leaves the ear sites essentially untouched,
which biases this paper's headline jaw-versus-ear dB gap **in the flattering
direction**. That is the one direction of bias a reviewer should care about.

So it is measured, not argued about. `src/01c_extend_neck.py` extrudes the
inferior cross-section 70 mm downward as a homogeneous slab carrying its own
label. The slab's conductivity is not defended, it is **bounded**: the run is
repeated at **muscle-isotropic (0.355 S/m)** and at a **fat/muscle blend**, so
the reported shift spans the plausible range rather than resting on one
arbitrary value. The slab is homogeneous on purpose — the point is to move the
insulating boundary away from the electrodes, not to model neck anatomy MIDA
does not contain.

Three jaw sites sit within 10 mm of the cut face (`hyoid` 8.0 mm,
`submental_lat` 8.4 mm, `submental_mid` 9.7 mm) while every ear site is 80 mm
or more away, so the montage is exactly the wrong shape for this artefact to
cancel.

> **DECISION RULE, fixed before the numbers exist.** One representative montage
> is solved on both meshes. **If the dB shift at `hyoid`, `submental_lat` or
> `submental_mid` exceeds 1.0 dB under *either* slab conductivity, the extended
> mesh becomes primary for every published result and the truncated mesh moves
> to supplementary.** Otherwise the truncated mesh stays primary and this
> becomes one paragraph in Limitations. Written down in advance so the
> threshold cannot be chosen after seeing which answer is more convenient.
>
> ### ⚠️ THE RULE COULD NOT BE EXECUTED, and is recorded unexecuted
>
> **The neck-extended mesh is unusable.** Its solves do not conserve charge.
> Both electrodes sit above the truncation plane, so net vertical current
> through any plane below both of them must be exactly zero; it is measured at
> **1.07–1.64 mA against a 1 mA injection**, and planes *between* the
> electrodes carry 1.59–1.61 mA where they must carry exactly 1.00. The
> discriminating measurement is decay toward the domain floor, where there is
> nowhere left for current to circulate: the truncated control falls from
> 0.951 mA at S = −112 mm to 0.107 mA at S = −119 mm (floor −122), while the
> extended mesh holds 1.594 mA at S = −112 mm and is still at 1.070 mA at
> S = −182 mm (floor −192). Flux that fails to decay approaching an insulating
> floor means current is leaving the domain there.
>
> *(A claim that the whole-domain charge check corroborates this, at −0.310 and
> −0.566 × injected, was added and **withdrawn the same day**. Those readings
> came from an analysis map in which the neck slab — tagged 200, inside
> SimNIBS's reserved electrode-rubber range — was silently read as 29.4 S/m
> rubber instead of 0.355 S/m muscle. With the correct map the check reads
> −0.0038 and passes. **The leak rests on the flux-decay measurement alone**,
> which is unaffected. See METHODS_LOG.)*
>
> *(An earlier version of this paragraph also cited a current-calibration error
> near 100% reported by the solver on every extended-mesh solve. **That
> corroboration is withdrawn.** SimNIBS's calibration check is measured
> anti-correlated with true delivered current on this mesh and is no longer
> evidence of anything. The finding itself is unaffected: it rests on the
> flux-decay measurement above, which is independent of the solver's own
> diagnostics and was the discriminating test all along.)*
>
> Of the two pre-committed hypotheses, **one was tested**: a non-insulating
> inferior boundary, **confirmed as a conservation violation**, though not
> cleanly separated from simple non-convergence. The other — a coarse-element
> jump at the slab interface — is **untested**.
>
> *(Corrected 2026-08-03. This paragraph previously recorded that hypothesis as
> **falsified**, on the grounds that the failure was identical 130 mm from the
> cut face. The probe that produced that comparison solved the near montage
> both times: it called the boundary run's `solve()` without passing the
> montage, so the function fell back to that module's `INJECT_FROM = "hyoid"`,
> and the result mesh is byte-identical to the run it was meant to differ from.
> The "identical 100.49% at 130 mm and at 8 mm" is one measurement at 8 mm,
> reported twice. **This does not change the disposition** — the extended mesh
> is unusable either way, because it does not conserve charge — it changes only
> whether the cause is known. Detail in `METHODS_LOG.md`.)*
>
> **The 1.0 dB threshold is neither applied nor revised.** It required a
> trustworthy shift measured on both meshes and no trustworthy extended-mesh
> solve exists. **The truncated mesh is primary by default rather than by
> test**, and the difference between those two things is stated here rather
> than glossed.
>
> **This therefore remains an UNQUANTIFIED limitation, and the direction of
> its bias is against us.** MIDA is cut at S = −116.2 mm with an insulating
> face there, and three jaw sites sit within 10 mm of it — `hyoid` **8.0 mm**,
> `submental_lat` **8.4 mm**, `submental_mid` **9.7 mm** — while **every ear
> site is 80 mm or more away**. Reflection at the cut face therefore inflates
> the lead field at the jaw sites and leaves the ear sites essentially
> untouched. Since the paper's headline is a jaw-versus-ear comparison, the
> artefact **flatters that comparison**: it makes the jaw look better than it
> is, and so makes the ear's deficit look larger than it is. A reviewer should
> be told this plainly, in these terms, with the magnitude stated as unknown
> rather than estimated.

Either way the comparison is a supplementary figure.

### Montages compared
1. **Canonical jaw** — the Gaddy/Kapur regions: mental, submental, submaxillary, hyoid, throat/SCM, buccal
2. **Retroauricular cluster** — above ear (temporalis), mastoid, behind/below earlobe (digastric + stylohyoid), anterior to tragus (masseter/TMJ)
3. **cEEGrid-like C-path** — 10 positions at 12–18 mm spacing, for comparability with the ear-EEG literature
4. Reference at contralateral earlobe; BIAS as in the physical rig

**Placement rule.** Every jaw site is placed by *normal projection*: the target structure's centroid (or an anatomically-defined sub-region of it, where several sites share one structure) projected to the nearest point on the outer skin. No hand-tuned millimetre offsets. The reported distance is therefore the structure's **depth below the skin** and nothing else, which makes it a result rather than a residual: hyoid 28.2 mm, submaxillary 24.2 mm, midjaw 20.7 mm, buccal 19.6 mm, submental_mid 16.2 mm, submental_lat 15.3 mm, mental 13.2 mm. Depth predicts attenuation and pairs directly with each sensitivity number.

**`pre_tragus` sits 14 mm anterior to the tragus**, further forward than the 10–13 mm pre-auricular convention. That convention is for pre-auricular *EEG references*; our target is the posterior border of masseter, which lies further forward. Verified: the electrode is 7.8 mm from the masseter compartment with the connecting path inside the head. This is a choice, not an oversight.

**Midline is derived, not assumed.** MIDA's midline is not R = 0, and the estimates disagree: the mandibular symphysis gives R = −7.77, the pinna-pair midpoint R = −1.33, a **6.4 mm discrepancy**. The lower face is genuinely offset relative to the ear pair in this single subject. Midline sites (`mental`, `submental_mid`, `hyoid`) are pinned to the symphysis-derived midline. Report the discrepancy: it matters because the montage is run on one side.

---

## Results (planned figures)

### FIGURE CAPTIONS (drafted 2026-08-04 — Results only, no Discussion)

**Fig 2. Articulator sensitivity matrix.** Median lead field in each segmented
muscle compartment for each electrode site, in dB relative to that muscle's
best jaw site (0 dB, ringed). Isotropic condition, truncated MIDA mesh, 22
electrodes × 10 muscles. The colour scale is **diverging about 0 dB**: red is
attenuation relative to the best jaw site, blue is a site that exceeds it, and
boxed cells mark every (site, muscle) pair where a retroauricular electrode
beats every jaw electrode. **The two arms are not equally scaled** (−28 to 0 dB
against 0 to +4 dB), so colour saturation is not comparable across the
midpoint; the boxes carry the sign independently of colour. Values in
`results/04_sensitivity_matrix_dB.csv`.

**Fig 4. Anisotropy robustness check.** Change in lead field between the
isotropic and anisotropic conditions, 20·log₁₀(aniso/iso), per cell. The
anisotropic condition is solved **on the isotropic run's own mesh**, so the two
conditions differ in conductivity alone and carry no electrode-realisation
noise. A fibre tensor (σ = 0.4 S/m along fibre, 0.1 S/m across, per-side
principal axis from the MIDA label volume) is applied to **2 of 10** muscles —
`sternocleidomastoid` and `medial_pterygoid`. **Rows without a tensor are
labelled NOT APPLIED, not zero**: they were never varied, so no null result was
measured for them. Six of the nine PCA-defensible muscles are pooled inside
MIDA's `Muscle (General)` and `Tongue` labels; `mentalis` is excluded by a
bilateral mirror-symmetry test on its principal axes.

**Fig 5. Which montage sees which muscle.** For each articulator, the
difference between the best jaw site and the best retroauricular site, in dB.
Negative bars are muscles the ear sees more strongly. Jaw sites within 10 mm of
the truncation face are excluded. The shaded band is the measured
electrode-meshing floor (0.27 dB, with the lighter band extending to its 95% CI
upper bound of 0.65 dB). **The axis is linear in dB rather than a rank**,
because the asymmetry between the arms is itself a result: the jaw's advantages
reach **+22.78 dB** while the ear's reach only **−3.92 dB**. Fig 2's diverging
scale equalises those arms visually; this figure is where their true relative
size is readable.

---

### The complementarity result

**Jaw and retroauricular montages are complementary rather than ranked.** Of
the ten segmented articulators, seven are seen more strongly from the jaw and
**three from the ear**: temporalis (**−3.92 dB**, best site `cg01`),
sternocleidomastoid (**−3.41 dB**, `cg08`) and lateral pterygoid
(**−1.69 dB**, `pre_tragus`), where a negative gap denotes an ear advantage.
All three exceed the 0.27 dB measured floor.

**The two montages' advantages are asymmetric in size, and the asymmetry is a
result rather than an artefact of scaling.** The jaw's advantages are large and
broad — mentalis **+22.78 dB**, depressor anguli oris **+15.55**, buccinator
**+10.57**, orbicularis oris **+10.37**, platysma **+9.29** — and concentrate
on a single site, `mental`, which is the best jaw electrode for six of the
seven jaw-favouring muscles. The ear's advantages are **modest and specific**,
spanning only **1.69 to 3.92 dB**, and they distribute across three different
sites (`cg01`, `cg08`, `pre_tragus`). Stated as a ratio, the largest jaw
advantage is **5.8×** the largest ear advantage in dB terms. An ear montage
therefore does not trade signal evenly against a jaw montage: it gives up a
great deal on the labial group and gains a little, at specific sites, on three
muscles that attach at or near the temporal bone.

`medial_pterygoid` at **+0.62 dB** is **borderline** and is reported as such.
It clears the floor's 0.27 dB point estimate but falls below the 95% CI upper
bound of 0.65 dB, so it must not be counted as a clean jaw advantage.

### Material versus distance: the fat-conductivity swap

**The jaw-versus-ear difference is geometric, not material.** Holding the mesh,
the electrodes and the source compartments fixed and changing only the
conductivity of both adipose labels from 0.025 to 0.355 S/m — making fat
electrically indistinguishable from muscle — every site loses signal, by a
median of **−2.36 to −3.91 dB**. That shift is very nearly common to all sites
and therefore cancels in every ratio the paper reports.

What survives is the differential: jaw sites shift by a median **−3.17 dB** and
retroauricular sites by **−2.84 dB**, so the fat/muscle conductivity contrast
contributes **0.33 dB** to the jaw-versus-ear gap — 1.2× the measured 0.27 dB
floor. Against gaps reaching 22.78 dB, that is **1.5% of the effect** for the
labial group.

This separation is available here and not in the limb sEMG literature, where
adding subcutaneous fat necessarily also increases source-electrode distance;
holding geometry fixed removes distance from the comparison entirely.

**`medial_pterygoid` is the exception.** Its gap is +0.62 dB and the material
contribution is 0.33 dB, over half of it, so that borderline site must not be
given a mechanistic reading. Note also that the swap bounds the effect of the
fat/muscle *conductivity contrast*; it does not simulate a thinner subject.

### Anisotropy robustness

**The complementarity result does not depend on the isotropy assumption.**
Sternocleidomastoid carries a fibre tensor (σ = 0.4 S/m along fibre, 0.1 across,
per-side principal axis from MIDA's label volume), and its jaw-versus-ear gap
moves from **−3.41 dB to −2.77 dB** — still an ear advantage, and roughly ten
times the 0.27 dB measured floor. The other two ear-favouring muscles move by
**+0.11 dB** (temporalis) and **−0.06 dB** (lateral pterygoid); neither carries
a tensor, so those shifts are the small global redistribution caused by
changing conductivity elsewhere.

**`medial_pterygoid` carries a tensor and its gap moves by only −0.03 dB.**
Anisotropy raises its lead field by about 5 dB at the jaw and the ear sites
alike, so the effect cancels in the site-to-site ratio. This is a direct
demonstration of the argument Table 3 is organised around: a term that scales a
compartment roughly uniformly does not reach a published number.

**Scope, stated rather than implied.** A fibre tensor is applied to **2 of the
10** segmented muscles. Six of the nine PCA-defensible muscles are pooled inside
MIDA's `Muscle (General)` and `Tongue` labels and cannot carry a per-compartment
axis; `mentalis` is excluded by a bilateral mirror-symmetry test on its two
principal axes (|dot| = 0.215, right-side elongation 1.07, i.e. no long axis
exists). Those eight rows are reported **NOT APPLIED**, never as zero.

### Pre-registration of the anatomical prediction

**The prediction that the ear would favour temporal-bone muscles was recorded
before the model was solved, and the repository is the evidence.** The
`expected_at_ear` column of `src/config.MUSCLES` — carrying *"STRONG - directly
above ear"* for temporalis and *"STRONG - mastoid attachment"* for
sternocleidomastoid — entered the repository in commit **`fa583f6`
(2026-08-02)**. The lead-field results it predicts were committed the following
day, **2026-08-03**, in the commit that adds `results/03_leadfields.csv`. The
prediction therefore precedes the measurement by a day and by the entire solve
pipeline.

Cite both hashes in Methods. **The repository must be made public at
submission** for that citation to be checkable by a reader; it is currently
private. That is now safe: the `.geo` history was purged with `git filter-repo`,
the remote was deleted and recreated, and an allowlist pre-commit hook refuses
any file type not explicitly permitted (it fired during this session on a
stray `.bak`).

### Truncation sensitivity — the direct answer to the boundary limitation

**The jaw-versus-ear result does not depend on the truncation.** MIDA is cut at
S = −116.2 mm with an insulating face, and three jaw sites sit within 10 mm of
it (`hyoid` 8.0, `submental_lat` 8.4, `submental_mid` 9.7) while every ear site
is 80 mm or more away, so reflection at that face inflates the jaw side and
flatters the comparison. Reporting the gap twice, over all seven jaw sites and
again over the four clear of the cut:

- median gap **+6.45 dB → +5.91 dB**, a shift of **−0.54 dB**
- **no sign flips**: which montage wins is unchanged for **10 of 10** muscles
- every |gap| still clears the 0.27 dB measured floor

**The structural reason matters more than the number.** Only three muscles move
at all — `medial_pterygoid` (−1.33), `platysma` (−1.18), `sternocleidomastoid`
(−0.88). For the other seven the best jaw electrode was never one of the
near-cut sites, so excluding them cannot change the maximum: those muscles are
**immune by construction, not by luck**. The truncation can only inflate the
comparison where a near-cut site was already winning, and it was winning for
three muscles out of ten.

`medial_pterygoid` at **+0.62 dB** remains **borderline** and is reported as
such: it clears the floor's 0.27 dB point estimate but sits under the 95% CI
upper bound of 0.65 dB.



**Fig 1** — Head model with muscle compartments highlighted; electrode positions for all montages.

**Fig 2** — **The money figure.** Sensitivity matrix: muscles (rows) × electrode positions (columns), colour = lead-field magnitude in dB relative to the best jaw site, taken as the **median over source orientation**.

> **The colour scale MUST be diverging about 0 dB, with a neutral grey midpoint — never sequential.** 0 dB is each muscle's best jaw site, so the **sign is the result**. A one-hue ramp has no visual event at zero and renders the three ear-winning muscles as "slightly lighter blue", burying the finding the figure exists to carry. Arms are unequal (−22.8 .. 0 .. +3.9 dB), so saturation is not comparable across the midpoint; the colorbar states both arm ranges and **every cell where the ear wins is ringed**, so the sign is carried by geometry as well as colour. Answers "what can you see from where." Every cell also carries the orientation envelope (min/max over n̂); render it as a companion panel or cell annotation rather than dropping it, since the envelope width is itself a finding.

**Fig 3** — Attenuation vs distance for each articulator muscle, jaw sites vs ear sites. Shows the cost of moving to the ear in dB.

**Fig 4** — Isotropic vs anisotropic muscle conductivity, same matrix. Quantifies the modelling error.

**Fig 5** — **A per-muscle map, not a loss ranking.** For each articulator, which montage wins and by how much, with the best site named on each side. A single ranking of retroauricular sites by *total* sensitivity was the previous spec and it is now wrong for this data: summing over muscles collapses a sign change into a scalar, so the three muscles the ear is actually better at disappear into a total dominated by the anterior articulators, where the jaw wins by 10–23 dB.

The measured map, from `results/04_jaw_vs_ear_gap.csv` (near-cut jaw sites excluded):

| muscle | best jaw | best ear | gap | wins |
|---|---|---|---|---|
| mentalis | `mental` | `cg10` | +22.78 | jaw |
| depressor_anguli_oris | `mental` | `cg10` | +15.54 | jaw |
| buccinator | `mental` | `cg10` | +10.57 | jaw |
| orbicularis_oris | `mental` | `cg10` | +10.37 | jaw |
| platysma | `mental` | `cg10` | +9.29 | jaw |
| masseter | `mental` | `cg10` | +2.53 | jaw |
| medial_pterygoid | `submaxillary` | `cg09` | +0.62 | jaw, **borderline** |
| lateral_pterygoid | `midjaw` | `pre_tragus` | **−1.69** | **ear** |
| sternocleidomastoid | `midjaw` | `cg08` | **−3.41** | **ear** |
| temporalis | `midjaw` | `cg01` | **−3.92** | **ear** |

The channel-redundancy analysis still turns this into a recommended subset, and it is now a **per-muscle-group** subset: a montage chosen to cover temporalis and SCM is not the montage that covers the labial group. **This is the design table earbud teams actually need**, and it is more useful as a map than as a ranking.

`medial_pterygoid` at **+0.62 dB** is flagged **borderline** and stays flagged: it clears the 0.27 dB floor point estimate but sits below the floor's 95% CI upper bound of 0.65 dB. It must not be rounded into a clean jaw advantage.

### Channel redundancy — how many electrodes do you actually need?

A ranking says which sites are best individually. It does not say which are
*worth adding*, because two adjacent sites can rank highly and see the same
thing. Once the sensitivity matrix exists we compute the **pairwise Pearson
correlation between electrode column vectors across the muscle rows**. Two
columns that correlate at r ≈ 1 are one channel wearing two electrodes.

This is a contribution, not a diagnostic. Paper 2 records **4 jaw channels, not
8**, and the canonical Gaddy/Kapur montage has never been reduced on any
principled basis — people inherit all eight. The correlation matrix lets us
publish a defensible 4-site subset with the redundancy each dropped site
carried, and gives an earbud team the same tool for the retroauricular cluster.

It also settles a concrete question this model raised: `submental_mid` and
`submental_lat` are 11.9 mm apart, closer than any other pair. Whether that is
two channels or one is decided by their correlation, not by their spacing.

**Table 2 — the tissue layer stack beneath each canonical site.** Millimetres per MIDA tissue along the ray from each electrode through the **full thickness** of its target, for every jaw site plus `above_ear` and `pre_tragus`.

> **Correction, recorded rather than quietly fixed.** The first version walked from the electrode only as far as the *nearest surface* of the target and reported percent-of-path. That is truncation-limited by construction: the ray stopped on arrival, so `midjaw` looked like 3% masseter. Extending the same ray through the full compartment gives **16.5 mm of masseter**, a 33x difference; `submaxillary` changes by 109x. The earlier draft claim, "the canonical sites do not sit on the muscles they are named for", was an artefact of the integration limit and is **withdrawn**. Every site does sit over its named target with real thickness.

What survives is cleaner. Each site is separated from its named generator by a **subcutaneous fat layer of 1.5–14.0 mm**:

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

Fat sits at **0.025 S/m against muscle at 0.355 S/m, a 14x contrast**, and generates nothing itself. This connects directly to the limb literature: Kuiken, Lowery & Stoykov (2003) added fat layers of 3, 9 and 18 mm to a finite-element upper-arm model and measured surface RMS amplitude falling by **31.3%, 80.2% and 90.0%**, with crosstalk rising alongside. Our measured 1.5–14.0 mm spans most of that range, so their attenuation curve is the quantitative bridge. Framed correctly this is *"quantified in the head what was already established for limbs"*, not an isolated observation.

⚠️ **One mechanism claim is NOT yet supportable and must not be asserted.** It is tempting to write that fat's low conductivity forces current to fan laterally and so spatially low-passes the source. The limb literature does not clearly support that: several treatments attribute the crosstalk increase primarily to the added **source-to-electrode distance** rather than to adipose material properties, and the decisive sentence could not be verified from a primary source. Do not present the conductivity-contrast mechanism as established.

**This model can settle it, which beats asserting it.** Solve twice with geometry held exactly fixed: once with fat at 0.025 S/m, once with the fat compartment set to muscle conductivity. Any difference is attributable to material properties alone, because distance is identical by construction. Limb studies could not separate the two cleanly; a labelled head model can. If the solves agree, distance dominates and we say so; if they diverge, the conductivity mechanism is real and measured.

**Table 2b (stage 4) — the sensitivity-weighted successor.** Path thickness is a geometric proxy. The physical quantity is the **fraction of each electrode's total sensitivity contributed by each compartment**, free once **E** exists: integrate the lead field over each compartment and normalise. Table 2 is retained as the *a priori* geometric prediction and Table 2b as its confirmation, so the paper contains a prediction and its test rather than either alone.

**Fig 7 — DELETED.** Its premise ("the retroauricular region contains the head's only large superficial skin-adjacent air voids") was falsified by measurement, not argument: the mastoid air cells are among the *smallest* voids in the head at 1,402 mm³, the nasopharyngeal airway is 31x larger at the same 0.5 mm minimum depth, and electrode-to-nearest-void distance is indistinguishable between montages (ear median 21.2 mm, jaw 22.4 mm, with the closest electrode of all being the jaw site `hyoid` at 14.5 mm). Falsifying numbers are in `METHODS_LOG.md`. Nothing replaces it unless the articulatory non-stationarity test below survives its own falsification test.

**Supplementary — air-void inventory.** Volume and depth-below-skin for all nine air-filled compartments in MIDA. Retained because it is a useful anatomical fact in its own right and because it is what killed the original Fig 7. *(provenance: measured)*

**Air voids in Methods, not Results.** Air cavities are handled as a modelling term applying to **both** montages, with no ear-specific framing. The filled-versus-air comparison is reported as a sensitivity term in the error budget.

**Fig 6 — the suprahyoid sensitivity field. This is the figure the ear argument actually rests on.** Sagittal and coronal slices of |E| through the pooled `Muscle (General)` compartment, with the mastoid notch, hyoid and corridor overlaid, for the retroauricular montage. See "Reporting a field, not eighteen numbers" below.

**Table 1** — Tissue conductivities used, with sources.

---

## Table 3 — the error budget

**The headline jaw-versus-ear dB figure ships with a ± assembled from measured terms, not asserted ones.** Almost nobody in this literature attaches a measured uncertainty to a forward-model dB number; doing so is a differentiator independent of what the number turns out to be.

One row per term. Each is filled in only when its run completes, and any row still reading TODO at submission is either measured or explicitly declared unquantifiable — never guessed.

**Read the last two columns first.** Every published claim in this paper is a **ratio** — this site against that site, ear against jaw, muscle against muscle. A term that scales the whole lead field equally **cancels in every ratio** and never reaches a conclusion. A term that varies *between* sites survives into all of them. Sorting the budget this way is what makes it load-bearing rather than decorative.

| # | Term | What sets it | Affects absolute lead field | Affects site-to-site ratios | Value |
|---|---|---|---|---|---|
| 1 | **Discretisation** | finite element size | yes | partly | *TODO — see below* |
| 2 | **Interface proximity** | source near a conductivity boundary | yes | **yes** | *needs a different geometry* |
| 3 | **Inferior boundary** | MIDA's cut face at S = −116.2 mm | yes | **yes** — hits jaw sites, not ear sites | *TODO — run in progress* |
| 4 | **Muscle anisotropy** | σ tensor vs scalar | yes | **yes** | *TODO — stage 3* |
| 5 | **Fibre orientation** | n̂ unknown in MIDA | yes | **yes** | *partially measured, per-muscle envelope* |
| 6 | **Electrode meshing** | contact area realised from incidental surface triangulation | yes | **yes — per-site, does not cancel** | **~0.27 dB, 95% CI [0.17, 0.65] (n=6, per-site, common mode removed)** |
| 7 | **Single anatomy** | MIDA is one subject | yes | unknown | **not quantifiable from one head** |
| 8 | **Delivered current** | current actually injected per solve vs the 1 mA requested | yes | **bounded by row 6, not additive to it** | **0.887–1.075 × requested across 22 solves (mean 0.9770, sd 0.0449), no outlier** |

**Row 8 is a bound, not a new term, and that distinction is the point.** Measured per solve by the tet-patch integral (flux through the interior cut of a patch around the electrode, using the mesh's own faces as the quadrature). It splits the same way row 6 does:

- the **common** part — the integral's own absolute level, identical across solves — cancels exactly in every ratio. This matters because that level is *not* independently established: on the analytic sphere the same integral reads 0.9406 / 1.2481 / 1.1134 across three mesh densities, non-monotone and changing sign. None of that reaches a published number.
- the **per-site** part shares its physical cause with row 6 — contact area realised from whatever surface triangles fall under each electrode. Entering it separately would double-count. It is reported here as a **ceiling** on row 6's per-site term: whatever the per-electrode delivery variation is, it is under 11.3%, with no site detached from the distribution.

**What this row replaces.** SimNIBS's own current-calibration line reports 0% or 11.90–32.99% on these same solves. Taken at face value that would be a large per-site term. It is not usable: on this mesh it is measured **anti-correlated** with the tet-patch deviation (Spearman −0.425, p = 0.048, n = 22), the largest true deviation (`buccal`, 0.8870) is reported clean, and `mental` at 1.0746 — closer to correct — is flagged 32.99%. Filed upstream as [simnibs/simnibs#665](https://github.com/simnibs/simnibs/issues/665). The claim there is about **ordering**, not magnitude, precisely because a common scale factor cannot invert a ranking but can move a level.

**Row 6 was nearly mis-filed as a cancelling term and is the clearest case for the two-column split.** It would be natural to treat electrode modelling as a global scale factor that divides out. It does not: each electrode's contact area is realised independently from whatever surface triangles happen to fall under it, so it is per-site noise, not global scale.

**Measured properly at n = 6**, by rotating the electrode array and the source points together on a fixed mesh. Rotating both preserves every source-to-electrode vector (verified to 2.8 × 10⁻¹⁴ mm), so the exact answer is identical across draws and the whole spread is realisation noise. The term then splits, and the split is what row 6 is about:

| term | SD | dB | cancels in a site ratio? |
|---|---|---|---|
| common-mode | 4.93 pp | 0.42 | **yes** |
| electrode-specific residual | 3.18 pp | **0.27** | **no** |

**~0.27 dB is the reported floor, 95% CI [0.17, 0.65]**, with a per-site spread of 0.12–0.49 dB. The statistic is the **mean over 16 electrodes of the per-electrode SD across 6 draws**; the interval is chi-square on an SD at df = 5, so each per-site value is known only to within about a factor of two. An earlier bootstrap interval of [0.16, 0.28] is **withdrawn**: resampling 6 draws with replacement leaves only ~4 distinct draws, and duplicates shrink a spread statistic, so it described a downward-biased estimator rather than this one. Site-to-site heterogeneity (0.12–0.49 dB) is comparable to the sampling uncertainty, so more draws alone will not tighten it. Only the residual survives into a site-to-site claim, which is exactly the distinction the two right-hand columns of this table exist to draw.

That number matters twice over. It sets the **resolution floor for the channel-redundancy analysis** (Fig 5), where adjacent sites differing by less than 0.27 dB are indistinguishable rather than genuinely redundant. And it sits ~3.7x below the boundary run's 1.0 dB decision threshold, so that run has real resolution.

> **Two earlier values are superseded and both are recorded rather than quietly replaced.** 0.43 dB was measured with a 15 mm electrode while production runs 10 mm. Its replacement, 0.1310 dB, was measured at the right diameter but from **n = 2** — one pairwise difference of 1.52 pp drawn from a distribution whose SD is 4.61 pp, so it landed low by roughly a factor of three and was then quoted to four significant figures. The n = 6 harness reproduces that measurement's own input exactly (identity rotation gives median MAG +5.996 pp, RDM 4.111, matching `e10mm_medium.csv` to three decimals), so this is the same quantity resampled, not a different one. The correction **tightens** the criterion it gates, which is the direction that cannot flatter a live hypothesis.

**These draws also settle the MAG question, and settle it better than the observations that raised it.** Holding the physical geometry exactly fixed and changing only the triangulation, **MAG's spread is 44x RDM's and MAG changes sign** (−4.01 to +6.00 pp, against RDM's 4.01–4.27). Nothing physical differs between those draws. Earlier evidence varied mesh density or electrode diameter and so could always be argued to have moved something real; this varies neither.

**Worked cancellation, for the terms that do cancel.** A flat 4.4% magnitude offset is 20·log₁₀(1.044) = 0.37 dB on every site equally. In a ratio of site A to site B both numerator and denominator carry it, so it subtracts to exactly 0 dB. This is why the retracted MAG figure, though embarrassing as an accuracy claim, would not have moved a single published conclusion — and why RDM, which measures *topography*, is the metric that actually matters here.

Row 7 is deliberately left unquantified. A single-subject model cannot estimate its own between-subject variance, and producing a number for it would be exactly the hand-waving this table exists to avoid.

**Method validity is established separately and is not a budget term.** Reciprocity was verified against the analytic multilayer sphere at a median magnitude ratio of 0.9907 (least-squares scale factor 0.9935, magnitude correlation r = 0.99743, no systematic drift across source radii 20–75 mm). That is a correctness check on the identity `V_AB = E_recip(r)·p / I`, not an uncertainty on any published number, and conflating the two would inflate the budget with a term that does not belong in it.

**Row 1's first attempt failed and is recorded rather than re-run quietly.** Three densities were requested via `meshmesh --usesettings` element-size ranges. Two were produced:

| Mesh | Tets | h_mean | RDM (%) | MAG (%) |
|---|---|---|---|---|
| coarse | 265,620 | 2.257 mm | 5.147 | +22.018 |
| medium | 647,323 | 1.677 mm | 4.355 | +4.400 |
| "fine" | 648,170 | **1.676 mm** | 3.812 | +9.464 |

The "fine" mesh is **0.13% larger than medium with the same element size**. Requesting a 0.8–2.5 mm range produced nothing finer, because element size is floored by the 0.5 mm label volume and by MMG's remeshing pass, neither of which the size range overrides.

So the apparently non-monotonic MAG (+22.0 → +4.4 → +9.5) is not a convergence curve. It is two runs on statistically identical meshes disagreeing by **5.06 percentage points in MAG and 0.54 in RDM**. That variability is itself the informative result: at fixed element size, MAG moves by ±5 points under a 0.1% mesh perturbation, which means **MAG is dominated by how the 15 mm disc electrodes are meshed onto the surface, not by volume discretisation.** Electrode contact geometry changes discontinuously when surface triangles move.

Two consequences. A discretisation term cannot be extracted at this precision until the electrode confound is removed, and the earlier +4.4% MAG should not be quoted as an accuracy figure, since a nominally identical mesh gives +9.5%.

The redesign this calls for: refine the **label volume** to 0.25 mm rather than asking for smaller elements on a 0.5 mm volume; and either shrink the electrodes toward point contacts or average each density over several electrode montages, so electrode meshing is a controlled variable instead of an uncontrolled one. RDM is the more robust metric of the two and should carry the headline regardless.

### The disposition of MAG, settled

MAG is **kept and reported**, because RDM/MAG is the conventional validation
pair in this literature and dropping half of it invites the reviewer question
"what happened to the magnitude error?". But it is reported with an explicit
statement of what its variance actually measures, because three independent
observations now agree that it is not measuring solver accuracy:

| observation | MAG | RDM |
|---|---|---|
| two nominally identical meshes, 15 mm electrode | 5.06 pp apart | 0.54 pp |
| repeatability of the quoted accuracy figure | +4.4% vs +9.5% | stable |
| across electrode diameter (15 mm vs 10 mm) | +4.400/+9.464 vs +5.996/+7.516 | moved 0.4 pp |

The pattern is consistent: **MAG tracks electrode diameter and surface
triangulation, and RDM does not.** A metric whose spread is set by how a disc
contact happens to land on surface triangles is measuring the electrode model,
not the field solution.

So the paper states the small finding directly rather than burying it:
*MAG is not a useful solver-accuracy metric when the source of comparison is a
meshed surface electrode rather than a point sensor.* That is worth one
sentence in Methods and it is defensible from the table above. It also
explains, rather than excuses, why **RDM carries the headline validation
claim** everywhere in this paper.

This costs nothing. Per the error-budget split above, a flat magnitude offset
cancels exactly in every ratio the paper publishes, and every published claim
here is a ratio. MAG being unquotable at 5 pp precision does not move a single
conclusion; it only removes a number that was never load-bearing.

**Row 2 is blocked by a confound, not by effort.** The intent was to measure how forward error grows for sources near a conductivity boundary, which matters because in MIDA nearly every muscle is bounded by fat at a 14x contrast. On a concentric sphere this cannot be measured: a source at radius *r* is at distance (78 − *r*) mm from the innermost interface **by construction**, so distance-to-interface and eccentricity are perfectly collinear and no regression can separate them.

The measurement itself comes out backwards from the hypothesis, which is what exposed the confound. RDM *falls* as sources approach the interface:

| Distance to nearest interface | n | RDM median (%) | MAG median (%) |
|---|---|---|---|
| 0–5 mm | 24 | **2.54** | +3.62 |
| 5–10 mm | 24 | 3.08 | +4.22 |
| 10–20 mm | 24 | 4.47 | +5.21 |
| 20–40 mm | 24 | 7.46 | +5.16 |
| 40–100 mm | 24 | **8.96** | +5.10 |

Correlation of RDM with interface distance is **+0.676**. Read naively this says proximity to a conductivity jump *improves* accuracy, which is not plausible. Read correctly it is the well-known degradation of EEG forward solutions for **deep, central sources**, whose topographies are low-amplitude and poorly conditioned. In this geometry that is the same variable.

Getting a real number for row 2 needs a geometry where two sources at equal eccentricity sit at different distances from an interface — a sphere with an eccentric inclusion, or the head mesh itself with the analytic oracle replaced by a converged fine-mesh reference. Recorded as a designed experiment rather than quietly dropped.

This also disposes of the r = 40 mm anomaly from the earlier bipolar ratio (1.033 against 0.979–0.993 elsewhere). It was **not** interface proximity: r = 40 mm is 38 mm from the nearest boundary, the second-farthest sampled. MAG is essentially flat across radii (+3.6 to +5.2%), so the 1.033 was conditioning noise in a metric that has since been retired.

**Supplementary figure — boundary-condition sensitivity.** dB change at every electrode between the native mesh and the neck-extended mesh. See "The inferior boundary" below.

---

## Expected findings (to be confirmed, not assumed)

- Digastric posterior belly and stylohyoid should couple strongly to mastoid sites — they physically attach there.
- Masseter and temporalis should be visible anterior to and above the ear.
- Tongue muscles (genioglossus) should attenuate hard at the ear — they're deep and distant. If so, that predicts *which phonemes* degrade, which is a testable prediction for Paper 2.
- The ear should lose meaningful dB versus the jaw. **Quantifying that loss is the contribution**, whether it's 6 dB or 30 dB.

Write the discussion so that either direction is publishable. A large loss says "here is why ear-only silent speech is hard, and here is the exact budget." A small loss says "ear-mounted silent speech should work, here is where to put the contacts."

---

## Discussion angles

> **PREP NOTES ONLY — not prose, not to be pasted into a Discussion.**
> Framing decisions here are Carl's.
>
> **1. The complementarity result independently reproduces the a-priori
> anatomical argument.** The three muscles the ear wins on are exactly the
> three whose attachments sit at or near the temporal bone: **temporalis**
> (origin, temporal fossa — directly under the superior cEEGrid row, and its
> best site is `cg01`), **sternocleidomastoid** (insertion, mastoid process —
> best site `cg08`), and **lateral pterygoid** (insertion at the mandibular
> condyle and TMJ capsule, articulating with the temporal bone's mandibular
> fossa — best site `pre_tragus`, the most anterior ear position). The
> prediction was written into `config.MUSCLES`'s `expected_at_ear` column
> before any solve ran, and the volume-conductor model reproduces it without
> being told. That is a **prediction confirmed**, not a post-hoc
> rationalisation, and the ordering is **verified from the record, not from
> memory**: `expected_at_ear` — including *"STRONG - directly above ear"* for
> temporalis and *"STRONG - mastoid attachment"* for SCM — entered the repo in
> the first scaffold commit **fa583f6, 2026-08-02**, while `results/03_leadfields.csv`
> was not committed until **2026-08-03**. The prediction predates the
> measurement by a day and by the entire solve pipeline.
>
> **2. It sharpens the Paper 2 prediction.** Paper 1 predicts what Paper 2
> measures, and the prediction is now specific rather than a dB budget: an
> ear montage should retain gestures driven by **temporalis** (jaw elevation,
> clenching) and **lateral pterygoid** (protrusion, lateral excursion), and
> should lose gestures driven by the **labial group** — `mentalis`,
> `depressor_anguli_oris`, `buccinator`, `orbicularis_oris` — which sit
> 10–23 dB down at the ear. `sternocleidomastoid` is a caveat rather than a
> win: the model says the ear sees it well, and `config.MUSCLES` already
> records "STRONG - mastoid attachment (**but low speech activity**)", so it
> is a strong coupling to a muscle that may carry little speech information.
> Do not let the dB number imply otherwise.
>
> **3. What this does NOT license.** Ten of eighteen muscles are modelled;
> the suprahyoid and tongue groups are pooled in MIDA and are not in this
> result. The two muscles that carry the strongest version of the ear argument
> — digastric posterior and stylohyoid — are among the missing ones, so the
> complementarity map is currently silent exactly where the anatomical
> argument is strongest.



1. **Design guidance** — a lookup table for anyone building an ear-worn ExG device.
2. **Reframing artifact as signal** — the EEG field spent decades documenting mastoid EMG contamination as a nuisance (Yao et al. 2019; Goncharova et al. 2003). This model says what that contamination actually *is*, muscle by muscle.
3. **A testable prediction for Paper 2** — the model predicts which sites and which phoneme classes survive at the ear. Your physical 8-channel jaw-vs-ear rig tests it directly. Modelling paper predicts, empirical paper confirms or refutes. That pairing is much stronger than either alone.
4. **Limitations** — single anatomy (MIDA is one subject), static geometry (no articulation deformation), quasi-static assumption. Fibre orientation is *not* listed here any more: it moved out of limitations and into Methods as a bounded quantity ("Bounding fibre-orientation uncertainty"). Unknown-but-bounded is a result; unknown-and-assumed would have been a limitation. Three further items belong here explicitly:

   **Truncated cervical compartments.** MIDA's volume ends at S = −116.2 mm and two muscles run into it: sternocleidomastoid (lowest extent −116.0, a 0.1 mm gap) and platysma (−115.9, 0.3 mm). Every other segmented muscle clears by 13 mm or more. Absolute sensitivity for these two is computed over a *truncated* compartment and their PCA fibre axis is biased by the truncated shape, so **their numbers are lower bounds**. State plainly that this affects the **throat montage, not the ear argument**: SCM's mastoid end reaches S = −22 mm, well clear of the cut, and that is the end the retroauricular claim depends on.

   **`throat_scm` is hand-specified, not derived.** This paper's job is to predict what the physical rig measures, so the modelled electrode must sit where the physical electrode will sit. Deriving it from MIDA's truncated SCM centroid would place it by an artefact. Coordinate pending measurement on the rig.

   **`mentalis` is thinly resolved.** 1,786 voxels on the right versus 7,176 on the left, yielding 3,226 tetrahedra, the smallest compartment in the mesh. Its median is correspondingly noisy: report it with an explicitly wider uncertainty envelope than the others rather than dropping it.

---

## Reference list (starting set, all verified)

- Iacono et al. (2015). *MIDA: A Multimodal Imaging-Based Detailed Anatomical Model of the Human Head and Neck.* PLOS ONE. doi:10.1371/journal.pone.0124126
- **Yarici, Thornton & Mandic (2023).** *Ear-EEG sensitivity modeling for neural sources and ocular artifacts.* Front. Neurosci. 16:997377. doi:10.3389/fnins.2022.997377 — **the gap statement.** Verified by direct fetch; previously and wrongly attributed here to Kappel.
- **Kappel, Makeig & Kidmose (2019).** *Ear-EEG Forward Models: Improved Head-Models for Ear-EEG.* Front. Neurosci. 13:943. doi:10.3389/fnins.2019.00943 — a real Kappel forward model. Contains **no** muscle-gap statement; do not cite it for the gap.
- **Meiser, Knoll & Bleichner (2024).** *High-density ear-EEG for understanding ear-centered EEG.* J. Neural Eng. 21(1):016001. doi:10.1088/1741-2552/ad1783 — verified by direct fetch. Previously listed here as "Kappel et al. (2023)": wrong authors, wrong year.
- Thielscher et al. — SimNIBS
- Maksymenko, Deslauriers-Gauthier & Farina (2021). *Ultra fast and highly realistic numerical modelling of surface EMG.* bioRxiv — limb-geometry precedent
- Mesin (2020). *Crosstalk in surface electromyogram: literature review.* Phys Eng Sci Med. doi:10.1007/s13246-020-00868-1
- Kuiken, Lowery & Stoykov (2003). *The effect of subcutaneous fat on myoelectric signal amplitude and cross-talk.* Prosthet Orthot Int 27(1):48–54. doi:10.3109/03093640309167976 — **verified against PubMed 12812327.** FE upper-arm model; fat layers of 3/9/18 mm reduce surface RMS amplitude by 31.3/80.2/90.0% with crosstalk rising. This is the limb-geometry precedent Table 2 bridges to. Note: the abstract does **not** adjudicate distance versus adipose material properties as the cause; do not cite it for that.
- De Luca et al. (2011). *Inter-electrode spacing of surface EMG sensors.* J Biomech
- Sato & Kochiyama (2023). *Crosstalk in Facial EMG and Its Reduction Using ICA.* Sensors 23:2720
- Yao et al. (2019). *Which Reference Should We Use for EEG and ERP practice?* Brain Topogr. — mastoid picks up EMG
- Goncharova et al. (2003). *EMG contamination of EEG: spectral and topographical characteristics.* Clin Neurophysiol
- Avramidou et al. (2024). *From Ear-EEG to Ear-ExG: The Jaw Artifact is a Keeper.* DSAI '24
- An et al. (2025). *ID.EARS.* CHI '25
- Debener et al. (2015). *Unobtrusive ambulatory EEG using cEEGrid.* Sci Rep 5:16743
- Kapur, Kapur & Maes (2018). *AlterEgo.* IUI '18
- Gaddy & Klein (2020). *Digital Voicing of Silent Speech.* EMNLP
- Wand & Schultz (2011). *Session-Independent EMG-Based Speech Recognition.*
- Kim & Loukas. *Anatomy, Head and Neck, Digastric Muscle.* StatPearls
- *Anatomy, Head and Neck: Suprahyoid Muscle.* StatPearls

---

## Sequence

1. Download MIDA, verify the suprahyoid segmentation ← **the one thing that could change the design**
2. Install SimNIBS 4.6, run a stock example end to end
3. Build the mesh with muscle labels
4. Place electrodes, define montages
5. Run reciprocity solves
6. Sensitivity matrix + figures
7. Write it
8. arXiv

**Realistic: 4–8 weeks part-time.** The compute is minutes; the human hours are segmentation QA and electrode placement.
