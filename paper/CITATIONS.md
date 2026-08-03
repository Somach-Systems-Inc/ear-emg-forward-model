# CITATIONS.md — citation verification ledger

**Verified:** 2026-08-02. Every citation in `paper/OUTLINE.md` was checked against
a primary source, plus the additional sources the outline needs and did not yet
have. This file records status, the source consulted, and every correction. It
is the companion to `paper/references.bib`.

**Method.** Each record was resolved to a primary source: publisher page, DOI
content-negotiation via the Crossref REST API, PubMed, NCBI Bookshelf, the ACL
Anthology, or the authoritative software repository. "Independently re-fetched"
below means I pulled the primary record directly; the rest were verified in a
research pass against the same class of primary source and are flagged as such.

No year was guessed and no DOI was invented. Where a field could not be
confirmed, it is marked and the gap is stated.

---

## ⚠️ Load-bearing corrections to OUTLINE.md (read first)

I own only `references.bib` and `CITATIONS.md` and did not edit `OUTLINE.md`.
These three items in OUTLINE.md's prose and reference list are factually wrong
and are load-bearing for the gap claim. They must be fixed in OUTLINE.md by
whoever owns it.

1. **The gap statement is NOT a Kappel paper.** OUTLINE.md line 30 and line 363
   attribute *"to date, there is no theoretical study of such artifacts in
   ear-EEG"* to "Kappel et al., ear-EEG sensitivity modelling." That exact
   sentence is from **Yarici, Thornton & Mandic (2023)**, *Ear-EEG sensitivity
   modeling for neural sources and ocular artifacts*, Frontiers in Neuroscience
   16:997377, doi:10.3389/fnins.2022.997377. **Kappel is not an author.**
   Verified by independently re-fetching the Frontiers article page, which
   carries the sentence verbatim in its Introduction, plus the follow-on:
   *"In principle, the presented volume conductor modeling framework could be
   used to investigate the sensitivity of wearable EEG montages to muscle
   artifacts, for example by placing current sources in the locations from which
   EMG signals originate."* The paper's own title — "neural sources and ocular
   artifacts," with muscle conspicuously absent — is what makes it the right
   citation for the gap. → bib key `yarici2023earsens`.

2. **"Kappel et al. (2023), High-density ear-EEG..." is NOT Kappel and NOT 2023.**
   OUTLINE.md line 364. It is **Meiser, Knoll & Bleichner (2024)**, *High-density
   ear-EEG for understanding ear-centered EEG*, J. Neural Eng. 21(1):016001,
   doi:10.1088/1741-2552/ad1783. Verified by independently re-fetching the
   IOPscience page. → bib key `meiser2024hdeeg`.

3. **A genuine Kappel forward-model paper exists — cite it as such, not for the
   gap.** Kappel, Makeig & Kidmose (2019), *Ear-EEG Forward Models: Improved
   Head-Models for Ear-EEG*, Frontiers in Neuroscience 13:943,
   doi:10.3389/fnins.2019.00943. Independently re-fetched. It contains no
   muscle-gap statement. Included as `kappel2019forward` so the paper can cite a
   real Kappel forward model alongside the Yarici gap statement if desired.

Net effect on the gap argument: the gap is still real and still citable — it just
belongs to Yarici et al. 2023, not Kappel. The reference list needs the author,
year, and venue swapped, not the claim withdrawn.

---

## Status table — every OUTLINE citation

Legend: **V+** = verified, primary source independently re-fetched by me.
**V** = verified against a primary source (Crossref/PubMed/publisher/ACL) in the
research pass. **CORR** = a field in OUTLINE.md was wrong; correction in bib.
**UNVERIFIED** = could not confirm to a primary source; see notes.

| OUTLINE citation | Status | bib key | Correction / note |
|---|---|---|---|
| Iacono et al. 2015, MIDA, PLOS ONE | V+ | `iacono2015mida` | Confirmed. 17 authors, e0124126, doi:10.1371/journal.pone.0124126. |
| MIDA dataset DOI 10.13099/ViP-MIDA-V1.0 | V+ | `itis2015midamodel` | DOI resolves to the IT'IS MIDA V1.0 page. A **V1.1** also exists — cite the version actually downloaded. |
| Thielscher et al., SimNIBS | V+ | `thielscher2015simnibs` | Resolved to Thielscher, Antunes & Saturnino (2015), EMBC, pp. 222–225, doi:10.1109/EMBC.2015.7318340. See "solver citation" note below. |
| Kappel — gap statement | **CORR / UNVERIFIED as attributed** | `yarici2023earsens` | **Not Kappel.** Actual source Yarici, Thornton & Mandic 2023. See load-bearing correction 1. |
| Kappel et al. 2023, high-density ear-EEG, J. Neural Eng. | **CORR** | `meiser2024hdeeg` | **Not Kappel, not 2023.** Meiser, Knoll & Bleichner 2024. See correction 2. |
| Avramidou et al. 2024, Ear-ExG | V+ | `avramidou2024earexg` | Confirmed via Crossref. 6 authors, DSAI '24 (11th), pp. 384–393, doi:10.1145/3696593.3696601. Second author renders as "Ralph Peter Derleth" in Crossref; some listings show "Peter Derleth". |
| An et al. 2025, ID.EARS, CHI '25 | V+ | `an2025idears` | Confirmed via Crossref. Full title: "ID.EARS: One-Ear EEG Device with Biosignal Noise for Real-Time Gesture Recognition and Various Interactions." pp. 1–18, doi:10.1145/3706598.3714185. ACM article number not confirmable (ACM DL returns 403); Crossref gives the page range. |
| Debener et al. 2015, cEEGrid, Sci Rep 5:16743 | V | `debener2015ceegrid` | Confirmed. doi:10.1038/srep16743. |
| Kapur, Kapur & Maes 2018, AlterEgo, IUI '18 | V | `kapur2018alterego` | Confirmed via MIT Media Lab + ACM. pp. 43–53, doi:10.1145/3172944.3172977. |
| Gaddy & Klein 2020, Digital Voicing, EMNLP | V | `gaddy2020digital` | Confirmed via ACL Anthology 2020.emnlp-main.445. pp. 5521–5530, doi:10.18653/v1/2020.emnlp-main.445. |
| Wand & Schultz 2011, Session-Independent EMG | V | `wand2011session` | Confirmed via SciTePress. BIOSIGNALS 2011, pp. 295–300, doi:10.5220/0003169702950300. |
| Mesin 2020, crosstalk review | V | `mesin2020crosstalk` | **CORR:** full title is "Crosstalk in surface electromyogram: literature review **and some insights**." 43(2):481–492, doi:10.1007/s13246-020-00868-1. |
| Kuiken, Lowery & Stoykov 2003, fat | V | `kuiken2003fat` | Confirmed via PubMed 12812327. Findings confirmed (31.3/80.2/90.0% at 3/9/18 mm). See mechanism caveat below. |
| De Luca et al. 2011, inter-electrode spacing, J Biomech | V+ / **CORR** | `deluca2012spacing` | **Year is 2012, not 2011.** Issue-of-record 45(3):555–561, doi:10.1016/j.jbiomech.2011.11.010. Confirmed via Crossref. |
| Sato & Kochiyama 2023, facial EMG / ICA, Sensors | V | `sato2023facial` | Confirmed. 23(5):2720, doi:10.3390/s23052720. |
| Yao et al. 2019, EEG reference, Brain Topogr | V | `yao2019reference` | Confirmed via PubMed 31037477. 32(4):530–549, doi:10.1007/s10548-019-00707-x. |
| Goncharova et al. 2003, EMG contamination, Clin Neurophysiol | V | `goncharova2003emg` | Confirmed via PubMed 12948787. 114(9):1580–1593, doi:10.1016/S1388-2457(03)00093-2. |
| Kim & Loukas, Digastric, StatPearls | V+ / **CORR** | `tranchito2024digastric` | **Authors are Tranchito & Bordoni, not Kim & Loukas.** NBK544352, updated 2024-01-30. Independently re-fetched; no Kim/Loukas digastric chapter found. |
| Suprahyoid Muscle, StatPearls | V | `khan2025suprahyoid` | Khan, Fakoya & Bordoni. NBK546710, updated 2025-03-25. |
| Maksymenko, Deslauriers-Gauthier & Farina 2021, bioRxiv | V+ / **CORR** | `maksymenko2023digitaltwin` (+ `maksymenko2021biorxiv`) | The preprint was published, retitled, with two added authors: "A myoelectric digital twin for fast and realistic modelling in deep learning," Nature Communications 14:1600 (2023), doi:10.1038/s41467-023-37238-w. Confirmed via Crossref. Prefer the journal version. Preprint doi:10.1101/2021.06.07.447390 retained but superseded. |

---

## Additional sources the outline needs (found & verified)

**Subcutaneous adipose thickness → sEMG amplitude (limb/trunk).**
Nordander et al. (2003), *Influence of the subcutaneous fat layer, as measured by
ultrasound, skinfold calipers and BMI, on the EMG amplitude*, Eur. J. Appl.
Physiol. 89(6):514–519, doi:10.1007/s00421-003-0819-1. **V+** (Crossref). Measures
muscle-to-skin distance by ultrasound and relates it to EMG amplitude — a direct
empirical companion to Kuiken 2003's model. `nordander2003fat`.

**FEM modelling of fat-layer effects on crosstalk (limb).** Two verified records:
- Lowery, Stoykov, Taflove & Kuiken (2002), *A multiple-layer finite-element
  model of the surface EMG signal*, IEEE TBME 49(5):446–454, doi:10.1109/10.995683.
  **V** — the foundational multilayer FE model; treats the fat layer's insulating
  effect on the surface signal. `lowery2002fem`. (Note: the `10.1109/TBME.`
  DOI form does **not** resolve; the correct stem is `10.1109/10.995683`.)
- Lowery, Stoykov & Kuiken (2003), *A simulation study to examine the use of
  cross-correlation as an estimate of surface EMG cross talk*, J. Appl. Physiol.
  94(4):1324–1334, doi:10.1152/japplphysiol.00698.2002. **V** — FE-based study of
  crosstalk specifically. `lowery2003crosstalk`.

**Meijs et al. 1989 and the RDM / MAG definitions.**
Meijs, Weier, Peters & van Oosterom (1989), *On the numerical accuracy of the
boundary element method (EEG application)*, IEEE TBME 36(10):1038–1049,
doi:10.1109/10.40805. **V+** (Crossref) — primary source for the Relative
Difference Measure (RDM) and Magnitude (MAG) error metrics. `meijs1989bem`.
Crossref renders the parenthetical as "(EEG application)"; the IEEE print index
uses brackets "[EEG application]" — cosmetic only.
For the modern RDM / lnMAG definitions as commonly used in FEM head-model
accuracy work, also: Güllmar, Haueisen & Reichenbach (2010), NeuroImage
51(1):145–163, doi:10.1016/j.neuroimage.2010.02.014. **V+**. `gullmar2010anisotropy`.
(Vorwerk et al. 2014, "A guideline for head volume conductor modeling in EEG and
MEG," NeuroImage, is another standard definitional reference for RDM/lnMAG; not
independently verified here — add its record before citing.)

**Falla, Dahl & Merletti 2002, SCM and scalene innervation zones.**
**CORR:** the paper is Falla, **Dall'Alba**, Rainoldi, Merletti & Jull (2002),
*Location of innervation zones of sternocleidomastoid and scalene muscles — a
basis for clinical and research electromyography applications*, Clin.
Neurophysiol. 113(1):57–63, doi:10.1016/S1388-2457(01)00708-8. **V** (PubMed
11801425). Second author is Dall'Alba (not "Dahl"); five authors, not three.
`falla2002innervation`.

**Conductivity of internal air cavities — the 2.5e-14 S/m value: CONFIRMED and
traceable.** 2.5×10⁻¹⁴ S/m is the documented **default air conductivity in ROAST**.
Independently re-fetched from the ROAST repository README, which lists
`air (default 2.5e-14 S/m)` in its conductivities block (full default set: white
matter 0.126, gray matter 0.276, CSF 1.65, bone 0.01, skin 0.465, air 2.5e-14,
gel 0.3, electrode 5.9e7 S/m). Primary paper: Huang, Datta, Bikson & Parra
(2019), *Realistic volumetric-approach to simulate transcranial electric
stimulation — ROAST*, J. Neural Eng. 16(5):056006, doi:10.1088/1741-2552/ab208d
(**V+**, Crossref). `huang2019roast` for the paper, `roast_repo` for the exact
numeric value in the README. So the value is not fabricated — it is a small
non-zero "insulator" conductivity in the Parra-lab lineage (ROAST / New York
Head), used to keep the FEM stiffness matrix non-singular, and is within an order
of magnitude of the DC conductivity of dry air.

Competing published convention worth noting for Table 1: the most directly
analogous ear-region model, **Yarici et al. 2023** (`yarici2023earsens`), sets
internal **air = 0 S/m** exactly. Gabriel et al. (1996) dielectric tables and
McCann et al. (2019) "Variation in Reported Human Head Tissue Electrical
Conductivity Values" (Brain Topogr. 32(5):825–858, doi:10.1007/s10548-019-00646-7;
not independently re-fetched here) do **not** supply an air-cavity value — air is
outside their scope. SimNIBS's standard conductivity table has no default "air"
compartment, so 2.5e-14 does not originate from SimNIBS.

---

## UNVERIFIED — cannot be cited to a primary source

**"AlterEgo's 2026 device moved... to an ear-mounted form factor" (OUTLINE.md
line 35).** No citeable primary source supports this as framed, and the **year is
wrong**. The public reveal of AlterEgo's "Silent Sense" wearable was **September
2025**, not 2026 (demos on 8–9 Sept 2025; Axios AI+ Summit, 17 Sept 2025). The
form factor is described in secondary coverage as worn around the ears like
spectacles and resting largely on the back of the head, with sEMG still sensing
"face, jaw, and neck" muscles — so "ear-mounted" overstates the sources. There is
no paper, dated white paper, or press release with a stable identifier — only
conference demos and news articles (Tom's Hardware, UploadVR 2025-09-09, Axios).
**Recommendation:** in OUTLINE.md, either drop the specific-year form-factor
claim or reframe to "AlterEgo's 2025 'Silent Sense' prototype adopted a
head-worn form factor around the ears" and flag it as non-peer-reviewed news. The
2018 IUI paper (`kapur2018alterego`) remains the only peer-reviewed AlterEgo
primary source. Not added to `references.bib`.

---

## Notes for whoever finalizes the references

- **Solver citation.** `thielscher2015simnibs` (EMBC 2015) is the general "cite
  SimNIBS" reference. For the tDCS/FEM electric-field solver this study actually
  repurposes for reciprocity, the more precise citation is Saturnino, Madsen &
  Thielscher (2019), J. Neural Eng. 16(6):066032, doi:10.1088/1741-2552/ab41ba
  (**V+**, `saturnino2019fem`). Consider citing both — general software + solver.
- **Yarici year.** Frontiers lists publication year **2023**; the DOI stem and
  volume 16 carry a **2022** stamp (accepted Dec 2022, published Jan 2023).
  `references.bib` uses 2023 and records the nuance in the entry `note`. Pick one
  consistently in prose; both are defensible, neither is a guess.
- **Kuiken 2003 mechanism claim.** OUTLINE.md lines 250–252 correctly refuse to
  assert that fat's low conductivity (rather than added distance) drives the
  crosstalk increase. Verified: the Kuiken 2003 **abstract does not adjudicate**
  distance vs. adipose material properties. Do not cite it for that mechanism.
  Note the tension with Lowery et al. 2002, which reports a material-property
  (insulation) effect near the source — the mechanism is genuinely nuanced.
- **ID.EARS article number** and the **MIDA version actually downloaded** (V1.0
  vs V1.1) are the only two open bibliographic details; both are cosmetic and
  resolvable at submission from the ACM page and the local `data/` metadata.
