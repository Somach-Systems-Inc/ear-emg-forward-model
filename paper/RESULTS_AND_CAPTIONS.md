# Results and figure captions — Paper 1

Extracted verbatim from `paper/OUTLINE.md` on 2026-08-04 so it can be pasted
without hunting through the outline. **This file is a copy, not the source.**
Edit `OUTLINE.md` and re-extract, or fold edits back, so the two do not drift.

**No Discussion, Introduction or Abstract.** Those are Carl's, and the Abstract
comes last, after the Discussion, because it compresses what is actually argued
rather than what was planned.

---

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
