# GAP_CHECK.md — adversarial test of the central novelty claim

**Run:** 2026-08-03. **Brief:** break the claim, do not support it.
**Method:** every source resolved to a primary record (Crossref REST, PubMed
E-utilities, publisher page, arXiv API, or the authors' own release
repository). No year, DOI, author list, or venue was inferred. Fields that
could not be confirmed are marked UNVERIFIED and say what is missing.

---

## VERDICT: THE CLAIM FAILS

> "Nobody has published muscle-source dipoles in an anatomically detailed head
> model."

This is false, and it has been false since December 2022. The counterexample is
peer-reviewed, in the paper's own target journal, uses the paper's own head
atlas, uses the paper's own fibre-orientation technique, and ships as a
downloadable `.mat` file that is already wired into two EEG simulation
toolboxes.

**The citation that breaks it:**

> Harmening, N., Klug, M., Gramann, K., & Miklody, D. (2022).
> *HArtMuT — modeling eye and muscle contributors in neuroelectric imaging.*
> **Journal of Neural Engineering 19(6): 066041.**
> doi:[10.1088/1741-2552/aca8ce](https://doi.org/10.1088/1741-2552/aca8ce)
> Preprint: bioRxiv doi:10.1101/2022.08.19.504507 (posted 2022-08-22; Crossref
> records the preprint as `is-preprint-of` the JNE article).

Crossref record independently re-fetched: four authors as listed, *Journal of
Neural Engineering*, volume 19, issue 6, page 066041, published-print
2022-12-01, published-online 2022-12-20.

Worse than a collision on the result: **HArtMuT asserts the same gap this paper
asserts, in almost the same words, and then closes it.** From the published
article, quoted verbatim:

> "While modeling ocular contributors to the EEG have already been discussed
> among researchers, muscular sources, to our knowledge, have not been added to
> any head model so far."

> "However, to our knowledge, no head model actually provides leadfields that
> incorporate the eyes and face and neck muscles in the forward solution."

A reviewer who knows this literature will find HArtMuT in one search. The claim
must be rewritten before submission, not defended.

---

## 1. Why this is a real break and not a technicality

Every element of the claim is met individually, and they are met in the same
artifact.

| Element of the claim | What HArtMuT did | Evidence |
|---|---|---|
| muscle sources | ~3,900 source positions built on 1 mm grids inside segmented face and neck muscle surfaces; modelled as dipoles, tripoles, and symmetric dipoles | Methods, "Artefact sourcemodel creation" |
| dipoles specifically | the FEM ground-truth run used "only the common dipolar source model type, because no FEM solution for tripoles was available" | Methods, "Simulated Data" |
| anatomically detailed head model | FEM leadfields for 3,540 artefact sources computed on the **New York Head**, a 0.5 mm, six-tissue, neck-extended FEM, solved with SimBio | Methods, "Simulated Data" |
| published | J. Neural Eng. 19(6):066041, peer reviewed | Crossref |
| head anatomy source | **MIDA** (Iacono et al. 2015), the same atlas this paper meshes | Methods, "MIDA open-source Atlas" |

Two further points that make it harder, not easier, to distinguish this work:

**The fibre-orientation method is the same one.** OUTLINE.md, "Bounding
fibre-orientation uncertainty," proposes a PCA principal axis as the fibre
direction for strap-like muscles. HArtMuT already did this: "The fiber
directions were approximated by using a Principal Component Analysis (PCA) on
close neighboring grid points of a muscles grid point cloud, where the closeness
criteria have been varied depending on the underlying muscle shape." This is
prior art for the technique and must be cited as such rather than presented as
new. It does not weaken the paper (the paper's contribution there is the
*orientation envelope*, which HArtMuT does not compute), but presenting PCA-on-
MIDA-muscle as novel would be an unforced error.

**It is not a paper-only result.** The release at
`github.com/harmening/HArtMuT` ships `HArtMuT_NYhead_small.mat` (36 MB),
`HArtMuT_mix_Colin27_small.mat` (49 MB), boundary meshes, and an artefact
parcellation atlas, and the README states HArtMuT "is already part of SEREEGA
and UnfoldSim.jl, where it can be used to simulate artefacts in synthetic EEG
data." Muscle-source leadfields in a head model are now off-the-shelf tooling.

---

## 2. Where HArtMuT actually stops

This is the useful part. HArtMuT closes the broad claim and leaves a narrower
one wide open. Each limit below is sourced, and several are stated by the
HArtMuT authors themselves.

**L1. Muscle is never a conductivity compartment. It is scalp.**
This is the single biggest surviving difference and HArtMuT says it outright:

> "Moreover, this approach lacks modeling eyeballs (and muscles) as their own
> tissue(s) with different conductivity than the remaining scalp."

Confirmed against both volume conductors used:
- The inverse-fit model is a **4-shell BEM** of Colin27 with a neck-extended
  scalp mesh: cortex (grey + white), CSF, skull, scalp. Conductivities fixed at
  scalp 0.465, skull 0.01, CSF 1.65, cortex 0.201 S/m. No muscle, no fat.
- The FEM ground truth is the **New York Head** (Huang, Parra & Haufe 2016,
  NeuroImage 140:150–162, doi:10.1016/j.neuroimage.2015.12.019), verified from
  the PMC full text as six tissues: "scalp, skull, CSF, gray matter, white
  matter, air cavities," at 0.5 mm³. Muscle and fat are **not** among them.

So HArtMuT's muscle sources radiate through homogeneous scalp. There is no
muscle/fat conductivity contrast anywhere in the model. The 14x fat-to-muscle
contrast that OUTLINE Table 2 is built on does not exist in any published
head-model muscle-source leadfield.

**L2. Isotropic everywhere.** No muscle conductivity tensor, no anisotropy
treatment, in either the BEM or the NY Head FEM. Anisotropy enters the head
volume-conduction literature only for white matter and skull.

**L3. MIDA supplies positions, never the volume conductor.** The source model
was warped out of MIDA: "A warping procedure for transferring the artefact
sourcemodel from MIDA into MNI space was developed." The fields were then solved
in Colin27 (BEM) and NYhead (FEM). The authors list this as an error term:
"different anatomies (NYhead vs. Colin27), and needed transformations of
electrode and source positions." **No published work has solved a muscle-source
forward problem in MIDA's own geometry.**

**L4. The question is inverse, not forward-sensitivity.** HArtMuT's output is
localization error and residual variance for ICA components. It reports no
source-to-electrode coupling, no dB attenuation, no montage comparison, no
per-muscle sensitivity, and no uncertainty budget on a forward number. It is a
tool for *identifying* muscle artifacts, not for *predicting how well a given
electrode sees a given muscle*.

**L5. The electrodes are a 129-channel whole-scalp cap.** No ear, mastoid,
retroauricular, cEEGrid, or jaw montage appears anywhere in it.

**L6. The muscles are the wrong ones, probably.** HArtMuT's own hit list from
real data is temporalis/temporoparietalis (21.6%), MIDA's `Muscle generalis`
class (18.1%), splenius capitis (4.2%), sternocleidomastoid (4.1%), plus
occipitofrontalis and levator labii superioris named in figures, "All other
muscles (26 in total) were below 4%." The framing throughout is facial
expression and **dorsal neck** muscles for mobile EEG. Critically, HArtMuT
describes MIDA's pooled label as "a collection of muscular tissue in the lower
neck," whereas this paper's own inventory finds label 38 (`Muscle (General)`,
1,975,307 voxels) is where the **suprahyoid group and the styloid-origin tongue
muscles** live. **See §4: this must be checked, not assumed.**

---

## 3. The narrowest claim that is still true and still interesting

Ranked from safest to most exposed. Tier A is defensible today on the evidence
in this document. Tier B becomes defensible after the ten-minute check in §4.
Tier C must not be written.

### Tier A — safe, verified, still novel

> **A1.** No published head volume-conductor model treats muscle as a
> *conductivity compartment* while also placing sources inside it. Existing
> muscle-source head models (HArtMuT) place sources in homogeneous scalp;
> existing head models that do segment muscle (Ernie Extended, SimNIBS charm)
> use it only as a passive conductor for stimulation. **This paper is the first
> to make muscle simultaneously the source and its own tissue.**

> **A2.** Muscle conductivity anisotropy has never been carried into a head
> model. Head models are anisotropic for white matter and skull only; the
> anisotropic-muscle literature is entirely limb and trunk.

> **A3.** No muscle-source forward solution has been computed in MIDA's native
> geometry. HArtMuT warped MIDA muscle positions into Colin27 and NYhead and
> paid a stated anatomy-mismatch penalty for it.

> **A4.** No published work reports source-to-electrode *sensitivity* for
> articulator muscles at retroauricular sites, or any jaw-versus-ear coupling
> comparison. Ear-EEG forward modelling covers neural and ocular sources only
> (Yarici et al. 2023; Kappel et al. 2019), and this remains true after
> HArtMuT because HArtMuT has no ear electrodes.

**A4 is the paper's real headline and it is untouched.** The contribution is the
*answer to a design question*, not the mere existence of a muscle dipole in a
head mesh. Reframe around that.

### Tier B — true only if the §4 check comes back clean

> **B1.** The suprahyoid group and the styloid-origin tongue muscles have never
> been modelled as sources in any head model.

HArtMuT sampled MIDA's pooled `Muscle (General)` label. If its 3.9k grid
included points in the submandibular part of that label, B1 is false too.
Do not write B1 until this is resolved.

### Tier C — retire these

- "Nobody has published muscle-source dipoles in an anatomically detailed head
  model." False. HArtMuT.
- "The two literatures do not meet." They met in J. Neural Eng. in 2022.
- Any framing that presents PCA-on-MIDA-muscle fibre axes as new.
- "Surface-EMG volume conduction models muscle fibres in cylindrical or limb
  geometry." Overstated; see §6.

### Suggested replacement text for OUTLINE.md §"Why this is a real gap"

> Muscle sources have been added to head models once, for artifact
> identification: HArtMuT (Harmening et al., 2022) places dipolar and tripolar
> sources inside MIDA-segmented face and dorsal-neck muscles and computes
> leadfields on a 4-shell BEM and on the New York Head FEM. In that model,
> however, muscle is not its own tissue. The authors state it directly: the
> approach "lacks modeling eyeballs (and muscles) as their own tissue(s) with
> different conductivity than the remaining scalp." The volume conductors
> involved (4-shell Colin27; the six-tissue New York Head) contain neither
> muscle nor fat, and are isotropic apart from the usual white-matter and skull
> treatments. HArtMuT's purpose is inverse: it improves source localization and
> component labelling for whole-scalp EEG caps. It reports no source-to-
> electrode sensitivity, no montage comparison, and includes no ear or jaw
> electrode. What has not been done, and what we do here, is to make muscle both
> the source and its own anisotropic conducting tissue in the head, in MIDA's
> native geometry, and to use it to answer a design question: how much of each
> speech articulator survives the move from the jaw to the ear.

---

## 4. The one check that must be run before submission

**Cost: about ten minutes. Payoff: converts Tier B into a claim or kills it.**

Download `HArtMuTmodels/HArtMuT_NYhead_small.mat` and
`HArtMuT_mix_Colin27_small.mat` from `github.com/harmening/HArtMuT`, read the
source positions and labels, and answer:

1. Do any HArtMuT sources lie in the submandibular / suprahyoid region, or does
   its `Muscle_neck` class stop at the dorsal neck as the prose implies?
2. Are any tongue-region sources present?
3. What is the full per-muscle label list?

Note that the public `artefactatlas` is deliberately anonymised to four classes
(`Empty_Space`, `Eye_left`, `Eye_right`, `Muscle_face`, `Muscle_neck`), because,
per the repo README, "the IT'IS Foundation owns the rights to object against
publishing the full HArtMuT atlas here with all the detailed tissue
information." The full list is said to be in a TU Berlin bachelor's thesis
(Moritz Steffin, 2022, "Creation of an Anatomical Artefact Atlas Based on
HArtMuT"), which I did not read. **The per-muscle inventory of HArtMuT is
therefore UNVERIFIED in this document.** The model files themselves carry
labels and will settle it.

---

## 5. Related work: the near-miss ladder

Ordered by how close each comes. This is the related-work paragraph.

| # | Work | Verified record | What it does | Precisely how it falls short |
|---|---|---|---|---|
| 1 | **HArtMuT** — Harmening, Klug, Gramann & Miklody (2022) | J. Neural Eng. 19(6):066041, doi:10.1088/1741-2552/aca8ce (Crossref, re-fetched) | Dipole/tripole muscle and eye sources from MIDA segmentation, PCA fibre axes, leadfields on 4-shell Colin27 BEM and New York Head FEM | **Does not fall short of the claim as written; it breaks it.** Falls short only of the narrowed claim: muscle is scalp-conductivity, not its own tissue; isotropic; MIDA is warped away, never meshed; inverse-localization purpose; no ear/jaw electrodes; no sensitivity or coupling result |
| 2 | **Yarici, Thornton & Mandic (2023)** | Front. Neurosci. 16:997377, doi:10.3389/fnins.2022.997377 (Crossref); arXiv:2207.08497 title "Ear-EEG Sensitivity Modelling for Neural and Artifact Sources" | The one ear-EEG sensitivity model with an artifact source class | Sources are neural and **ocular** only. Muscle absent by the paper's own title and Introduction. Still the correct citation for the ear-EEG-specific gap; HArtMuT does not touch it, since HArtMuT has no ear electrodes |
| 3 | **Kappel, Makeig & Kidmose (2019)** | Front. Neurosci. 13:943, doi:10.3389/fnins.2019.00943 (Crossref) | Improved ear-EEG forward head models | Brain sources only. No artifact class at all |
| 4 | **New York Head** — Huang, Parra & Haufe (2016) | NeuroImage 140:150–162, doi:10.1016/j.neuroimage.2015.12.019 (Crossref; tissue list from PMC5778879) | 0.5 mm, six-tissue, neck-extended FEM; the volume conductor HArtMuT borrowed | Six tissues: scalp, skull, CSF, grey, white, air cavities. **No muscle, no fat.** Its own leadfields are for 10,004 cortical grey-matter points. Detailed head geometry, brain sources: the exact half of the split the paper describes |
| 5 | **Ernie Extended** — Van Hoornweder, Cappozzo, De Herde, Puonti, Siebner, Meesen & Thielscher (2024) | Imaging Neuroscience 2, doi:10.1162/imag_a_00379 (Crossref) | Head-and-shoulders model, **13 tissues including muscle** at 0.160 S/m | The cleanest **tissue-not-source** case in the literature. Muscle is a segmented conducting compartment, and is used purely to route tES current toward brain targets. Never a generator. Also the best available answer to this paper's own inferior-boundary problem |
| 6 | **MIDA** — Iacono et al. (2015) | PLOS ONE 10(4):e0124126, doi:10.1371/journal.pone.0124126 (Crossref, 17 authors) | The atlas; 153 structures at 500 µm including named facial and masticatory muscles | Demonstration application is a tACS electric-field study. Muscle is anatomy and conductor, never source |
| 7 | **Carl, Açık, König, Engel & Hipp (2012)** | NeuroImage 59(2):1657–1667, doi:10.1016/j.neuroimage.2011.09.020 (Crossref + PubMed 21963912) | Characterises the saccadic spike **field** in MEG and, by distributed source analysis, "identified the sources of the SF in the extraocular muscles" | **Inverse, not forward.** No muscle-source forward model was constructed, no muscle conductivity compartment, and the muscles are extraocular rather than articulatory. This is the strongest "ocular artifact is really muscle" prior art and it still does not build a forward model |
| 8 | **Richer, Downey, Hairston, Ferris & Nordin (2020)** | IEEE TNSRE 28(8):1825–1835, doi:10.1109/TNSRE.2020.3000971 (Crossref + PubMed 32746290) | **Physical** electrical head phantom broadcasting four brain and four muscle sources, including at sternocleidomastoid and semispinalis capitis | A hardware phantom, not a volume-conductor solve. No conductivity model, no leadfield, no anatomy beyond the phantom shell |
| 9 | **Lowery, Stoykov, Taflove & Kuiken (2002)** | IEEE TBME 49(5):446–454, doi:10.1109/10.995683 (Crossref) | Foundational multilayer FE surface-EMG model with fat as an insulating layer | Upper limb, layered geometry. The physics this paper wants, in the wrong body part |
| 10 | **Pereira Botelho, Curran & Lowery (2019)** | PLOS Comput. Biol. 15(8):e1007267, doi:10.1371/journal.pcbi.1007267 (Crossref) | Anatomically accurate, DTI-derived FE model of EMG during index-finger flexion/abduction | Genuinely non-cylindrical, MRI+DTI realistic geometry, with real fibre directions. Still a **hand**. Proves the sEMG field can do realistic anatomy when it wants to, and simply has not done the head |
| 11 | **Maksymenko, Clarke, Mendez Guerra, Deslauriers-Gauthier & Farina (2023)** | Nat. Commun. 14:1600, doi:10.1038/s41467-023-37238-w (Crossref) | Fast, realistic numerical sEMG "digital twin" | Forearm geometry. Note for `references.bib`: the published version has **five** authors and a different title from the 2021 preprint OUTLINE.md still cites |
| 12 | **La Rosa, Eswaran, Preissl & Nehorai (2012)** | BMC Med. Phys. 12:4, doi:10.1186/1756-6649-12-4 (Crossref) | Multiscale forward electromagnetic model of uterine contractions in a realistic multi-compartment abdomen | Non-limb, anatomically realistic, muscle-source volume conduction. Kills the word "cylindrical" in the claim's second half, though not the head part |

**Deliberately excluded after checking, with reasons:**

- **TMS-evoked cranial muscle artifact work** (Mutanen et al. and successors).
  Artifacts are removed using empirically measured topographies via SSP/SSP-SIR.
  No forward muscle-source model in a head volume conductor.
- **Facial/masticatory FE modelling.** A PubMed query for
  `electromyograph* AND (finite element OR boundary element) AND (facial OR
  mastication OR jaw OR swallow*)` returns 12 records, all of them **mechanical**
  biomechanics (mandible strain, lip movement, facial-expression animation), not
  bioelectric volume conduction. This branch is empty.
- **Glossokinetic potential.** The tongue artifact literature is empirical and
  the modern reading (intracranial EEG work) argues against a simple dipole
  entirely. No forward model.
- **Submental/swallowing sEMG.** Empirical crosstalk and muscle-contribution
  studies only.
- **Gowda & Miller (2025)**, arXiv:2502.05762, "Non-invasive electromyographic
  speech neuroprosthesis: a geometric perspective." Signal representation and
  EMG-to-text, no volume conductor. Verified via the arXiv API (two authors,
  submitted 2025-02-09).

**Search coverage, so the negative results carry weight.** PubMed E-utilities
across head-model + muscle + forward/leadfield, volume conduction + facial
muscle/masseter/temporalis/digastric, surface EMG + finite element + head/face/
neck/tongue, EMG + head model + simulation, MIDA + muscle/EMG, ear-EEG +
model; OpenAlex full-citation graph of HArtMuT (10 citing works, none extending
it toward muscle-as-tissue); OpenAlex keyword sweeps on muscle lead fields,
facial muscle forward models, and ear-EEG muscle artifacts; Crossref
bibliographic search; plus targeted web search on ocular and saccadic-spike
forward models, TMS muscle artifacts, glossokinetic potentials, swallowing EMG,
and uterine/abdominal EMG forward models. HArtMuT was the only hit that lands
on the claim.

---

## 6. The claim's second half is also overstated

> "surface-EMG volume-conduction literature models MUSCLE fibres in cylindrical
> or limb geometry"

"Cylindrical" is wrong as a blanket statement. Row 10 above is an MRI+DTI hand
model with real fibre architecture; row 9 is an MRI-derived multilayer upper
arm; row 12 is a multi-compartment pregnant abdomen. The field left cylinders
behind some time ago.

Correct wording, which is still true and is a sharper statement:

> Surface-EMG forward models have moved from cylindrical layered geometry to
> subject-specific, DTI-informed anatomy, but exclusively in the limbs and
> trunk. None has been built for the head or neck.

---

## 7. Verification ledger

**Independently re-fetched to a primary record by me:** Crossref works API for
HArtMuT (both preprint and JNE versions, including the `is-preprint-of`
relation), New York Head, Ernie Extended, MIDA, Yarici 2023, Kappel 2019,
Lowery 2002, Botelho 2019, Maksymenko 2023, La Rosa 2012, Carl 2012, Richer
2020. PubMed E-utilities esummary/efetch for Carl 2012 (PMID 21963912) and
Richer 2020 (PMID 32746290). arXiv API for 2207.08497 and 2502.05762. PMC full
text for the New York Head tissue list. IOPscience full text for the three
load-bearing HArtMuT quotes. bioRxiv PDF (CC-BY) for the HArtMuT methods
detail, cross-checked against the IOP version.

**Quote provenance.** The three quotes doing real work in this document (the
"not been added to any head model so far" novelty claim, the "own tissue(s) with
different conductivity than the remaining scalp" admission, and the NYhead/
SimBio ground-truth description) were confirmed present in the **published**
IOPscience article, not only in the preprint. Methods detail quoted at greater
length (PCA fibre directions, 1 mm grids, the 4-shell conductivity values) comes
from the CC-BY bioRxiv PDF, which Crossref links as the preprint of record.

**UNVERIFIED, stated as such:**
- HArtMuT's **full per-muscle label list**. The public atlas is anonymised to
  four classes at IT'IS's request. Resolvable from the released `.mat` files;
  see §4. Until then, whether HArtMuT covers the suprahyoid corridor is an open
  question and Tier B claims must not be written.
- Whether the released `HArtMuT_NYhead_small.mat` contains muscle leadfields for
  the full source set or only the 3,540-source validation subset. Not stated in
  the README.
- The Steffin (2022) TU Berlin bachelor's thesis on the artefact atlas. Not
  read; cited here only because the repo README points to it.

---

## 8. Required edits to OUTLINE.md

1. **Delete line 28** ("Nobody has published muscle-source dipoles in an
   anatomically detailed head model") and the two-literature table's implication
   that they never meet. Replace with the §3 paragraph.
2. **Add HArtMuT to the reference list and to `references.bib`**, and cite it in
   three places: the gap paragraph, the fibre-orientation section (PCA
   precedent), and the discussion of muscle-as-artifact.
3. **Keep Yarici et al. 2023 exactly where it is.** Its claim is scoped to
   ear-EEG and survives HArtMuT intact. It is now doing more work than before,
   not less.
4. **Rewrite the one-sentence claim (line 15)** so the novelty rests on the
   coupling question and the muscle-as-its-own-anisotropic-tissue treatment,
   not on the existence of a muscle dipole in a head mesh.
5. **Fix the sEMG half of the claim** per §6.
6. **Consider Ernie Extended (row 5) for the truncated-neck problem.** The
   inferior-boundary limitation in OUTLINE.md is currently unquantified because
   the hand-built neck extension fails charge conservation. A published,
   validated head-and-shoulders model with a muscle compartment already exists.
   That is a cheaper route than debugging the extruded slab.
7. **Run the §4 check** before writing any suprahyoid novelty claim.

---

## 9. Bottom line for the author

The broad claim is gone and it was never necessary. What the paper actually does
that nobody has done is narrower and more defensible: it makes muscle its own
anisotropic conducting tissue rather than undifferentiated scalp, it solves in
MIDA rather than warping out of it, and it answers a question about electrode
placement that no forward model has been pointed at. The error budget in Table 3
has no counterpart anywhere in the near-miss ladder either.

A gap claim that survives a hostile search is worth more than one that sounds
bigger. This one now has a named competitor, a stated difference from it, and a
citation to prove the difference is the competitor's own admission.
