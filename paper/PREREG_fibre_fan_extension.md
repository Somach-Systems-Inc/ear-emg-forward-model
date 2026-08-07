# Pre-commitment: extending the derived fibre fan beyond temporalis

**Written before any value was computed.** Nothing in this file may be edited
after the first run of `src/04v_fibre_fan.py`. If a rule here turns out to be
wrong, add a dated amendment below it and say why; do not rewrite it. That is
the `CUT_FACE_S` rule and this file exists because the temporalis result is
exactly the kind of result that invites choosing the treatment after seeing it.

Recorded 2026-08-06, before the first solve was read.

---

## What is being done and why

§2.5.1 derives a per-voxel fibre field for temporalis by pointing each voxel at
its bony insertion, and §2.5.1 closes with "That intersection is available for
temporalis alone". §4.7 names the muscles for which the same construction is
appropriate but untested:

> Masseter, lateral pterygoid and depressor anguli oris are multi-part or
> converging ... and a per-voxel fan toward a common attachment is the
> appropriate treatment for them, untested here.

This extends the construction to **masseter (label 66)** and **lateral
pterygoid (label 65)**. Both insert on the mandible (label 36), the same bone
temporalis inserts on, so the insertion is found the same way and nothing new is
asserted about anatomy.

**Depressor anguli oris is excluded, in advance.** It converges on the modiolus,
which is soft tissue and carries no MIDA bone label, so the contact-with-bone
construction has nothing to find. Excluding it here, before any result, is the
point: it is excluded for an anatomical reason, not because of what it returned.

**Sternocleidomastoid, medial pterygoid and mentalis are also out of scope
here.** §4.7 calls them strap-like, and `config.FIBRE_MODEL` already assigns
them a PCA axis. They need the constrained sweep applied to an axis that already
exists, which is a different piece of work from deriving a fan, and mixing the
two in one run would make the outcome unattributable.

## Why these two muscles specifically

Both sit near the decision boundary on the orientation axis, which is the axis
this construction acts on. From Table 4:

| Muscle | Gap envelope (dB) | Orientation agreement | Current verdict |
|---|---|---|---|
| masseter | +1.20 to +2.22 | 56.0–68.5 % | jaw, site-robust but orientation-dependent |
| lateral pterygoid | -3.61 to -1.53 | 65.5–72.0 % | unstable across subsets |

Selecting them for being near the boundary is legitimate **because the selection
is by the pre-existing orientation-agreement column, not by any quantity this
run produces.** Both are already published as orientation-dependent, so both are
already flagged as the rows a fibre derivation would act on.

## The construction, fixed in advance

Identical to `04k_temporalis_fan.py`, with only the labels changed:

    insertion = centroid of label-36 (mandible, right side) voxels
                lying within 3.0 mm of the muscle compartment
    n_hat(voxel) = normalise(insertion - voxel)

The 3.0 mm contact threshold is inherited from the temporalis run and is **not**
to be tuned. If it yields a degenerate insertion for either muscle, that is
reported as a failure of the construction for that muscle, not as a reason to
try 4 mm.

Both evaluations from 04k are produced: PER-VOXEL (each tet uses its own
direction, giving the physically correct lead field) and PER-DIRECTION (each
derived direction applied uniformly, giving the reachable-orientation spread).
**PER-VOXEL is the reported one**, matching the ruling already made for
temporalis.

## Decision rules

Stated now, applied without further judgement.

**R1. Reporting is unconditional.** Every muscle attempted is reported with its
derived interval, whichever way it moves, including muscles whose verdict does
not change and muscles where the construction fails. A muscle may not be dropped
from the write-up after its number is seen.

**R2. A verdict changes only if the matched-count interval changes side.** As
for temporalis: the interval is the exact enumeration over all C(14,4) = 1001
four-site ear montages at the pre-registered cluster basis. A verdict flips only
if that interval moves from excluding zero to spanning it, or the reverse. A
shift in the point estimate alone changes nothing.

**R3. The derived field governs where it exists.** Same reasoning §4.8 gives for
temporalis: the derivation removes an assumption instead of adding one. If the
derived and uniform treatments disagree, the derived one is reported as the
result and the uniform one is reported beside it, as §4.8 already does. This is
fixed now precisely so it cannot be chosen later to suit the direction of the
change.

**R4. A degenerate fan is a null, not a discard.** If the derived directions for
a muscle span less than 5 degrees, the fan is not meaningfully different from a
single axis and the muscle is reported as "construction returns a single
direction, no fan", with the number. It is not silently reclassified as strap.

**R5. Failure to change anything is a result.** If neither muscle's verdict
moves, that is written into §4.7 as the limitation having been tested and
survived, replacing "untested here". The section does not simply keep its
current wording as though the work had not been done.

**R6. The title is not in scope.** Neither muscle currently favours the ear on
both axes, and both are jaw-side or unstable. If R2 fires for either, the
consequences for the abstract and title are worked out and shown to Carl before
any change is made to them. No agent edits the title off the back of this run.

## What would falsify the construction itself

The temporalis fan was validated by its angular spread being anatomically
plausible for a fan (reported in the 04k run output). The same check applies
here. If the derived insertion for a muscle sits outside that muscle's known
attachment region, the construction has found the wrong contact patch and the
result is void regardless of what it does to the gap. This is checked by
printing the insertion centroid in RAS and its distance to the compartment
before any gap is computed.

---

## Amendment 1, 2026-08-06, added AFTER the first run

**What happened.** The first run fired R2 for masseter: its interval moved from
[+1.201, +2.218], excluding zero, to [-1.987, +5.276], spanning it. Taken at
face value that retires masseter's jaw advantage.

**It is not taken at face value.** The geometry check this file already required
("if the derived insertion sits outside that muscle's known attachment region,
the construction has found the wrong contact patch and the result is void") was
written for an insertion in the wrong *place*. Masseter's insertion is in the
right place and still breaks the construction, for a reason the clause did not
anticipate: the contact patch is nearly coextensive with the muscle.

| muscle | insertion patch (mm) | compartment (mm) | \|mean(n̂)\| |
|---|---|---|---|
| temporalis (published) | 21 x 31 x 49 | 53 x 150 x 128 | 0.755 |
| lateral pterygoid | 18 x 19 x 21 | 44 x 34 x 36 | 0.710 |
| masseter | 31 x 43 x 68 | 35 x 65 x 73 | 0.555 |

Masseter's patch spans 66 to 89 per cent of the compartment's own extent on
every axis, so pointing each voxel at its centroid yields directions converging
inward from all sides, which is not a fibre model. Anatomy agrees: masseter runs
from the zygomatic arch to the ramus and lies along the ramus for its whole
length, so origin-to-insertion is the correct axis and voxel-to-insertion is
not. §4.7 predicted exactly this when it grouped masseter under "superficial and
deep layers at different angles".

**Amended rule R4b.** The construction is void for a muscle when the insertion
patch exceeds 60 per cent of the compartment extent on every axis, or when
\|mean(n̂)\| falls below 0.60. Both quantities come from the label volume alone
and are independent of any lead field, gap or interval, which is why adding this
after seeing a gap move is admissible. It is stated as a threshold on anatomy,
not on a result.

**Consequences, fixed now.** Masseter is reported as a construction failure and
its interval is NOT reported as a verdict change. Lateral pterygoid passes both
tests and its result stands. Under R1 both appear in the write-up, masseter as a
failure with its numbers shown and the reason given.

**What this cost and what it bought.** One spurious verdict change, caught
before it reached the manuscript. Had R4 been written to cover only the
too-narrow case, which is what it did cover, masseter would have entered §4.7 as
a retired jaw advantage.
