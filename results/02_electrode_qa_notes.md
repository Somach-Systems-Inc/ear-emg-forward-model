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
