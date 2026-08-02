# Stage 2 electrode QA notes

Generated 2026-08-02 against `data/mida_headneck.msh` (12,293,945 tets) and
MIDA v1.0. Figure: `figures/02_electrode_qa.png` / `.pdf`.

**Every position is still `verified=no` in `results/02_electrode_positions.csv`.**
Nothing below promotes a position to verified. These are the objective checks
that could be automated, plus the things that need a human eye.

---

## What passes

**All 24 positions lie on the outer skin surface.** Maximum distance to the
nearest skin voxel is 0.01 mm across the whole montage, so nothing is floating
in air or buried inside the head.

**All four retroauricular positions satisfy their anatomical definitions**,
tested against the right pinna (A −11.5..24.3, S −35.5..8.3, R 55.5..78.4):

| Position | Required relation | Result | Distance to pinna |
|---|---|---|---|
| `pre_tragus` | anterior to the pinna front edge | OK | 15.2 mm |
| `above_ear` | superior to the pinna top | OK | 5.6 mm |
| `mastoid` | posterior to pinna front, below mid-height | OK | 3.7 mm |
| `post_lobule` | inferior to the pinna centroid | OK | 10.1 mm |

**Every jaw site sits over the structure it claims**, and the straight segment
from electrode to that structure stays inside the head in all cases:

| Position | Claimed structure | Distance |
|---|---|---|
| `mental` | Mandible | 9.7 mm |
| `submental_mid` | Mandible | 12.6 mm |
| `submental_lat` | Mandible | 7.1 mm |
| `submaxillary` | Mandible | 8.9 mm |
| `hyoid` | Hyoid Bone | 25.2 mm |
| `throat_scm` | Muscle - Sternocleidomastoid | 3.2 mm |
| `buccal` | Muscle - Buccinator | 8.2 mm |
| `midjaw` | Muscle - Masseter | 10.6 mm |

**cEEGrid C-path spacing** is 11.9–18.0 mm consecutive, mean 15.1 mm, inside
the 12–18 mm band used by Debener et al. 2015.

---

## Needs your eyes

### 1. SCM and platysma are truncated by the model boundary — the real finding

MIDA's volume ends at **S = −116.2 mm**. Two compartments run into it:

| Muscle | Lowest extent | Gap to boundary |
|---|---|---|
| sternocleidomastoid | −116.0 mm | **0.1 mm** |
| platysma | −115.9 mm | **0.3 mm** |

Every other segmented muscle clears the boundary by 13 mm or more.

These two are cut off, not fully modelled. Three consequences:

- Their compartment volumes are partial, so absolute sensitivity is computed
  over an incomplete muscle.
- Their PCA fibre axis is biased by the truncated shape. This bites SCM
  specifically, since SCM is in the PCA-defensible set.
- `throat_scm` is placed from the SCM centroid, and truncation drags that
  centroid posteriorly and superiorly (A = −11.1, versus a head centre of
  A = +15.7). The electrode is correctly over the *modelled* SCM at 3.2 mm,
  but the modelled SCM is not the whole muscle.

I initially read `throat_scm` as misplaced on the postero-lateral neck. The
numeric check says the placement is right and the **model** is short. Worth
being clear about, because the fix is different: not a better offset, but a
documented limitation, and possibly a hand-chosen `throat_scm` matching where
the electrode goes on the physical rig.

Good news for the argument: SCM's mastoid end reaches S = −22, well clear of
the cut. The end that matters for the ear is intact.

### 2. Is `pre_tragus` too far forward?

It sits 15.2 mm from the pinna, from a 14 mm anterior offset off the tragus.
Pre-auricular electrodes are usually 10–13 mm anterior. It passes the "is it
anterior" test but the magnitude is my choice, not a measurement. If the
physical rig has a convention, use that number instead.

### 3. Side choice, and two thin compartments

Stage 2 uses `--side right`. Paired muscles are segmented very evenly
(masseter 3%, temporalis 1%, SCM 1%, platysma 3% left/right difference), so
the side choice is largely free. Two exceptions, both smaller on the right:

- `orbicularis_oris` 27,252 right vs 60,007 left (38%)
- `mentalis` 1,786 right vs 7,176 left (60%)

Both are midline structures where an R = 0 split is arbitrary, so the ratio is
not evidence of bad segmentation. But **mentalis is genuinely thin in absolute
terms** and yields only 3,226 tetrahedra in the mesh, the smallest of any
compartment. Expect a noisy median for it in stage 4.

### 4. `hyoid` is a 25 mm-deep target

Correct, not a bug: the hyoid bone genuinely sits ~25 mm below the skin. Worth
knowing when reading its sensitivity, since it is the deepest jaw target and
will attenuate accordingly.

### 5. The eight pooled muscles have no positions to check

`digastric_posterior`, `stylohyoid`, `mylohyoid`, `geniohyoid`,
`digastric_anterior`, `genioglossus`, `hyoglossus`, `styloglossus` remain
inside `Muscle (General)` (38) and `Tongue` (42). Nothing here validates them.

---

## Mesh validation (stage 1b)

`src/01b_validate_mesh.py`, run under `simnibs_python`:

- 2,140,917 nodes; 12,293,945 tetrahedra; 3,121,328 triangles
- **116 distinct tetra tags**, i.e. every MIDA label survived meshing
- total tet volume 10,078 cm³
- all 10 segmented muscles present; meshed volume agrees with voxel volume to
  within **1% for every one**
- element quality mean 0.681, **zero** negative-volume tets, 49 near-degenerate
  (<0.01) out of 12.3 M = 0.0004%

Smallest compartment is `mentalis` at 3,226 elements; largest is `temporalis`
at 249,240.

---

## Not done, deliberately

Stage 3 has not been started. Positions are unverified and lead-field solves
should not spend compute on coordinates that have not been looked at.

---

# Revision 2026-08-02 (after review)

Placement rewritten to normal projection; `throat_scm` held; midline derived;
ear tissue checks added; ROI corridor built. Earlier sections above describe
the superseded hand-offset placement and are kept for history.

## Item 1 — normal projection replaces hand offsets

Each jaw site is now the nearest outer-skin point to its target structure's
centroid (or an anatomically-defined sub-region, where sites share a
structure). Reported distance is now **depth**, not depth plus placement error.

| site | old R,A,S | new R,A,S | moved | old dist | new depth |
|---|---|---|---|---|---|
| `mental` | -7.2, 94.0, -105.0 | -6.7, 98.7, -99.6 | **7.1 mm** | 23.5 | 13.21 |
| `submental_mid` | -6.1, 69.5, -107.2 | -10.6, 81.8, -106.0 | **13.2 mm** | 3.5 | 16.15 |
| `submental_lat` | 16.7, 65.6, -105.3 | 19.7, 86.7, -92.6 | **24.8 mm** | 3.5 | 15.28 |
| `submaxillary` | 29.5, 53.4, -99.9 | 42.5, 68.7, -80.8 | **27.6 mm** | 4.5 | 24.19 |
| `hyoid` | -7.8, 36.1, -115.6 | -1.8, 42.1, -108.5 | **11.1 mm** | 25.5 | 28.23 |
| `buccal` | 33.4, 75.5, -86.7 | 38.7, 75.6, -78.4 | **9.9 mm** | 22.5 | 19.55 |
| `midjaw` | 60.3, 51.9, -67.8 | 65.2, 51.0, -54.9 | **13.8 mm** | 22.5 | 20.66 |
| `throat_scm` | 48.1, -15.1, -92.8 | **HELD** | - | - | - |

Target changes: `mental` now targets **Mentalis (71)**, not Mandible.
`hyoid` targets **Hyoid Bone (87)**. `submental_mid/lat` and `submaxillary`
target sub-regions of Mandible (symphysis midline, symphysis lateral,
body lateral).

Two bugs this surfaced. `buccal` first landed at R = -10.8, under the chin:
buccinator is bilateral, so an unrestricted centroid sits near midline and its
nearest skin point is submental, not buccal. Fixed with a side restriction
(same applies to masseter). And the old `hyoid` sat at S = -115.6, **0.6 mm**
from the volume floor — a direct instance of the boundary problem in item 3.

## Item 2 — tissue under the ear electrodes

| site | target tissue | distance | path |
|---|---|---|---|
| `above_ear` | Muscle - Temporalis/Temporoparietalis | 3.5 mm | inside |
| `pre_tragus` | Muscle - Masseter | 7.8 mm | inside |

`mastoid` and `post_lobule` sit over pooled `Muscle (General)` and are covered
by the ROI corridor instead.

## Item 3 — neck extension, running

`src/01c_extend_neck.py` extrudes the inferior cross-section 70 mm downward as
a homogeneous slab with its own label (200), so it cannot contaminate the
`Muscle (General)` pool used by the ROI analysis. Verified: superior axis
derived from the affine (voxel axis 1), origin shift exactly [0, 140, 0] so
original anatomy does not move, inferior limit -116.2 → -186.1 mm.
Mesh building; solve-both-ways comparison pending.

## Item 4 — midline derived

| estimate | R |
|---|---|
| mandibular symphysis (top 12% by A, n=42,298) | **-7.77** |
| hyoid bone centroid | -6.08 |
| whole mandible centroid | -5.68 |
| pinna pair midpoint | **-1.33** |

**Discrepancy 6.4 mm, exceeding the 3 mm flag.** The lower face is genuinely
offset relative to the ear pair in this subject; three independent lower-face
landmarks agree at about -6 to -8 while the ears say -1.3. Midline sites are
pinned to the symphysis value. This matters because the run is `--side right`
and `mentalis` is 4x larger on the left.

## Finding 5 — ROI corridor instead of hand segmentation

Right side: mastoid notch [51.1, -5.4, -16.8] → hyoid greater horn
[9.4, 21.3, -85.9], length **85.1 mm**.

| radius | Muscle(General) vox | volume | Tongue vox | frac of pool |
|---|---|---|---|---|
| 8 mm | 17,021 | 2,127 mm³ | 2,213 | 0.9% |
| 10 mm | 29,363 | 3,670 mm³ | 5,164 | 1.5% |
| **12 mm** | **46,295** | **5,786 mm³** | **9,184** | **2.3%** |
| 15 mm | 75,366 | 9,419 mm³ | 17,697 | 3.8% |
| 18 mm | 109,834 | 13,727 mm³ | 29,904 | 5.6% |

Using the hyoid **centroid** first gave a 95.1 mm corridor, more than twice a
posterior digastric belly, because it ran across the midline; the ipsilateral
greater horn fixes it and cuts Tongue contamination from 34,400 to 9,184
voxels at 12 mm.

Occupancy is continuous with no empty bins, but the first 10% holds only 6
voxels: the mastoid air-cell inferior tip sits superior to the true digastric
fossa, so the ROI effectively begins ~10 mm distal. Property of the landmark
proxy, reported not hidden.

**The styloid process is not segmented.** Searched Skull (40) across every
plausible box below and medial to the mastoid; it is one connected component
of 122,615 voxels with no separable spike at 500 µm. So one corridor holds both
digastric posterior and stylohyoid, and the field is reported along and across
it rather than assigning a styloid coordinate we cannot support.

## Approval status

Approved by Carl: all ear sites, cEEGrid, reference/BIAS.
Re-placed this revision and needing a fresh look: `mental`, `hyoid`,
`submental_mid`, `submental_lat`, `submaxillary`, `buccal`, `midjaw`.
**Held:** `throat_scm`, pending a measured coordinate.

---

# Placement acceptance (src/02c_placement_acceptance.py) — 2026-08-02

**RESULT: FAILED on B and C. Positions NOT written; sign-off not taken.**

## A. Centroid validity — 4 of 7 centroids are outside their own compartment

| site | target | label AT centroid | inside? | rule applied |
|---|---|---|---|---|
| `mental` | Mentalis (71) | 36 Mandible | **NO** | min-distance to compartment |
| `hyoid` | Hyoid Bone (87) | 37 Mucosa | **NO** | min-distance to compartment |
| `submental_mid` | Mandible (36) symphysis_mid | 36 | YES | centroid projection |
| `submental_lat` | Mandible (36) symphysis_lat | 41 Teeth | **NO** | min-distance to compartment |
| `submaxillary` | Mandible (36) body_lat | 43 Adipose | **NO** | min-distance to compartment |
| `buccal` | Buccinator (84) | 84 | YES | centroid projection |
| `midjaw` | Masseter (66) | 66 | YES | centroid projection |

The failures are all concave structures: a mandible and a hyoid are arches, so
the centroid sits in the soft tissue enclosed by the arch (mucosa, teeth, fat),
not in bone. Projecting from a point that is not in the target was the flaw.

Re-placed: `mental` 1.2, `hyoid` 7.6, `submental_mid` 2.6, `submental_lat`
23.4, `submaxillary` 29.4 mm.

**Implementation note:** the min-distance rule is applied *only* where the
centroid is invalid. Applying it uniformly moved `midjaw` 51.8 mm up to the
zygomatic arch (S = -17.7) — for a long muscle it migrates to the single
shallowest point of the whole compartment, which is not mid-ramus and came
within ~7 mm of `pre_tragus`.

## B. Depth — FAIL at hyoid

| site | depth | expected | verdict |
|---|---|---|---|
| `mental` | 5.1 | 3-8 | ok |
| `submental_lat` | 5.1 | 4-12 | ok |
| `submental_mid` | 6.5 | 4-12 | ok |
| `submaxillary` | 6.0 | 4-12 | ok |
| `buccal` | 10.8 | 8-15 | ok |
| `midjaw` | 11.0 | 5-12 | ok |
| `hyoid` | **19.7** | 10-15 | **FLAG** |

Diagnosed rather than smoothed. It is **not** the wrong aspect of the bone:
the hyoid's minimum distance to the skin surface is **19.1 mm taken over the
entire skin**, unconstrained. Midline band makes almost no difference
(±2 mm → 19.7, ±10 mm → 19.4, unconstrained → 19.1).

So MIDA's hyoid is simply ~19 mm deep in this subject; the 10-15 mm
expectation does not hold here. MIDA separates `Epidermis/Dermis` (51) from
`Subcutaneous Adipose Tissue` (62), so this depth spans skin, subcutaneous
fat, platysma and the infrahyoid muscles. Report the depth as measured.

## C. Inter-electrode spacing — FAIL, floor 20 mm

| site | nearest | mm |
|---|---|---|
| `submental_mid` | `submental_lat` | **11.9** |
| `mental` | `submental_mid` | **17.4** |
| `submaxillary` | `submental_lat` | 28.1 |
| `buccal` | `submaxillary` | 31.7 |
| `hyoid` | `submaxillary` | 38.5 |
| `midjaw` | `buccal` | 43.1 |

**Global minimum 11.9 mm against a 20 mm floor.** Closest jaw-to-other-montage
pair is `midjaw` ↔ `cg10` at 32.9 mm (ok).

This is a montage-definition problem, not a placement bug. `mental`,
`submental_mid` and `submental_lat` name three anatomically adjacent regions
of the chin, and once each is placed over its own structure they are 12-17 mm
apart. With 10 mm cups in adhesive collars the three cannot coexist. Needs a
decision, not a nudge — see the summary.

Held: `throat_scm`, so this is 7x7 rather than 8x8. Re-run when its measured
coordinate arrives.

## D. Side integrity — PASS

All three midline sites within 2 mm of the symphysis midline (-7.77):
`mental` 1.6, `hyoid` 1.6, `submental_mid` 0.4. All lateral sites on the
correct side (+11.2 to +73.0 mm).

## E. Boundary clearance (cut face S = -116.2)

| site | clearance |
|---|---|
| `hyoid` | **8.0 mm** |
| `submental_lat` | **8.4 mm** |
| `submental_mid` | **9.7 mm** |
| … | |
| `cg02` (largest) | 133.3 mm |

Three jaw sites sit within 10 mm of the insulating cut face while every ear
site is 80 mm or more away. This is exactly the asymmetry the boundary
sensitivity run is measuring.

## F. Displacement history

| site | original (hand-offset) | normal-projection | accepted | orig→acc |
|---|---|---|---|---|
| `mental` | -7.2, 94.0, -105.0 | -6.7, 98.7, -99.6 | -6.2, 98.2, -100.6 | 6.1 |
| `hyoid` | -7.8, 36.1, -115.6 | -1.8, 42.1, -108.5 | -9.3, 42.7, -108.2 | 10.0 |
| `submental_mid` | -6.1, 69.5, -107.2 | -10.6, 81.8, -106.0 | -8.1, 81.9, -106.5 | 12.6 |
| `submental_lat` | 16.7, 65.6, -105.3 | 19.7, 86.7, -92.6 | 3.5, 79.4, -107.8 | 19.3 |
| `submaxillary` | 29.5, 53.4, -99.9 | 42.5, 68.7, -80.8 | 24.1, 61.1, -102.4 | 9.8 |
| `buccal` | 33.4, 75.5, -86.7 | 38.7, 75.6, -78.4 | 38.7, 75.6, -78.4 | 9.9 |
| `midjaw` | 60.3, 51.9, -67.8 | 65.2, 51.0, -54.9 | 65.3, 51.0, -54.9 | 13.8 |

`mental` moved 6.1 mm from the original and sits at A = 98.2, S = -100.6, on
the chin pad over mentalis at 5.1 mm depth — it did not stay submental.
