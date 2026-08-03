# Paper 1 — Outline

**Working title:**
*Where can you hear the tongue from the ear? A volume-conductor model of articulator muscle sources at retroauricular electrode sites*

**Type:** Computational / modelling study
**Human subjects:** none (n = 0)
**IRB:** not required — no human subjects. State this explicitly in Methods.
**Target:** arXiv preprint first → *Journal of Neural Engineering* (rolling) or *Sensors* (rolling)

---

## The one-sentence claim

We compute, for the first time, how strongly each speech-articulator muscle couples to electrodes placed around the ear, and show which retroauricular positions carry the most silent-speech information.

---

## Why this is a real gap (verified)

Two literatures exist and they do not touch:

| Literature | Sources modelled | Geometry |
|---|---|---|
| Head volume conduction (EEG / MEG / tDCS) | **brain** dipoles, sometimes ocular | detailed head models — but tissue segmentation stops at brain/CSF/skull/scalp |
| Surface EMG volume conduction | **muscle** fibres | cylindrical or limb FEM geometries |

Nobody has published muscle-source dipoles in an anatomically detailed head model.

The gap is stated explicitly in the ear-EEG modelling literature: forward models exist for neural and **ocular** sources, but *"to date, there is no theoretical study of such artifacts in ear-EEG"* for muscle (Kappel et al., ear-EEG sensitivity modelling).

Meanwhile the empirical side has moved without theory:
- Retroauricular arrays demonstrably capture chewing and **speaking** EMG (Avramidou et al. 2024, *"From Ear-EEG to Ear-ExG: The Jaw Artifact is a Keeper"*)
- Ear-mounted electrodes classify jaw clench and chew at >90% (An et al. 2025, ID.EARS)
- AlterEgo's 2026 device moved from a jaw-wrapping band to an ear-mounted form factor

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

**Fig 1** — Head model with muscle compartments highlighted; electrode positions for all montages.

**Fig 2** — **The money figure.** Sensitivity matrix: muscles (rows) × electrode positions (columns), colour = lead-field magnitude in dB relative to the best jaw site, taken as the **median over source orientation**. Answers "what can you see from where." Every cell also carries the orientation envelope (min/max over n̂); render it as a companion panel or cell annotation rather than dropping it, since the envelope width is itself a finding.

**Fig 3** — Attenuation vs distance for each articulator muscle, jaw sites vs ear sites. Shows the cost of moving to the ear in dB.

**Fig 4** — Isotropic vs anisotropic muscle conductivity, same matrix. Quantifies the modelling error.

**Fig 5** — Rank ordering: the top-N retroauricular positions by total articulator sensitivity, **plus the channel-redundancy analysis that turns a ranking into a recommended subset**. **This is the design table earbud teams actually need.**

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
| 6 | **Electrode meshing** | contact area realised from incidental surface triangulation | yes | **yes — per-site, does not cancel** | **0.27 dB (n=6, per-site, common mode removed)** |
| 7 | **Single anatomy** | MIDA is one subject | yes | unknown | **not quantifiable from one head** |

**Row 6 was nearly mis-filed as a cancelling term and is the clearest case for the two-column split.** It would be natural to treat electrode modelling as a global scale factor that divides out. It does not: each electrode's contact area is realised independently from whatever surface triangles happen to fall under it, so it is per-site noise, not global scale.

**Measured properly at n = 6**, by rotating the electrode array and the source points together on a fixed mesh. Rotating both preserves every source-to-electrode vector (verified to 2.8 × 10⁻¹⁴ mm), so the exact answer is identical across draws and the whole spread is realisation noise. The term then splits, and the split is what row 6 is about:

| term | SD | dB | cancels in a site ratio? |
|---|---|---|---|
| common-mode | 4.93 pp | 0.42 | **yes** |
| electrode-specific residual | 3.18 pp | **0.27** | **no** |

**0.27 dB is the reported floor**, with a per-site spread of 0.12–0.49 dB. Only the residual survives into a site-to-site claim, which is exactly the distinction the two right-hand columns of this table exist to draw.

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
- Kappel et al. *Ear-EEG sensitivity modelling for neural and artifact sources.* — the gap statement
- Kappel et al. (2023). *High-density ear-EEG for understanding ear-centered EEG.* J. Neural Eng.
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
