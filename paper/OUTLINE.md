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

⚠️ **Verify on download:** digastric, stylohyoid, mylohyoid, geniohyoid, genioglossus. These may sit inside a generic "muscles" catch-all. The suprahyoid group is central to the argument — if it is not individually segmented, sub-segment it manually from the label volume and document that as a methods limitation.

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

### Montages compared
1. **Canonical jaw** — the Gaddy/Kapur regions: mental, submental, submaxillary, hyoid, throat/SCM, buccal
2. **Retroauricular cluster** — above ear (temporalis), mastoid, behind/below earlobe (digastric + stylohyoid), anterior to tragus (masseter/TMJ)
3. **cEEGrid-like C-path** — 10 positions at 12–18 mm spacing, for comparability with the ear-EEG literature
4. Reference at contralateral earlobe; BIAS as in the physical rig

---

## Results (planned figures)

**Fig 1** — Head model with muscle compartments highlighted; electrode positions for all montages.

**Fig 2** — **The money figure.** Sensitivity matrix: muscles (rows) × electrode positions (columns), colour = lead-field magnitude in dB relative to the best jaw site. Answers "what can you see from where."

**Fig 3** — Attenuation vs distance for each articulator muscle, jaw sites vs ear sites. Shows the cost of moving to the ear in dB.

**Fig 4** — Isotropic vs anisotropic muscle conductivity, same matrix. Quantifies the modelling error.

**Fig 5** — Rank ordering: the top-N retroauricular positions by total articulator sensitivity. **This is the design table earbud teams actually need.**

**Table 1** — Tissue conductivities used, with sources.

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
4. **Limitations** — single anatomy (MIDA is one subject), static geometry (no articulation deformation), quasi-static assumption, fibre orientation approximated.

---

## Reference list (starting set, all verified)

- Iacono et al. (2015). *MIDA: A Multimodal Imaging-Based Detailed Anatomical Model of the Human Head and Neck.* PLOS ONE. doi:10.1371/journal.pone.0124126
- Kappel et al. *Ear-EEG sensitivity modelling for neural and artifact sources.* — the gap statement
- Kappel et al. (2023). *High-density ear-EEG for understanding ear-centered EEG.* J. Neural Eng.
- Thielscher et al. — SimNIBS
- Maksymenko, Deslauriers-Gauthier & Farina (2021). *Ultra fast and highly realistic numerical modelling of surface EMG.* bioRxiv — limb-geometry precedent
- Mesin (2020). *Crosstalk in surface electromyogram: literature review.* Phys Eng Sci Med. doi:10.1007/s13246-020-00868-1
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
