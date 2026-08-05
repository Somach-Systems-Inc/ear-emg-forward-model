# Approved wording — Abstract, §3.1, Table 4

Written by Claude (the assistant), approved by Carl 2026-08-05. Drop in
verbatim. Every number traces to the 200-direction orientation sweep, the
anatomical-constraint analysis, and the PCA-axis evaluation.

---

## STATISTIC DEFINITION — read before using any number below

Two "gap" statistics exist and they are not interchangeable:

- **A. Gap-per-orientation, then median over orientations.** temporalis −3.80,
  SCM −1.96, lateral pterygoid −1.85. **This is the one used throughout the
  wording below.**
- **B. Orientation-median lead field per site, then differenced.** temporalis
  −3.31, SCM −3.21, lateral pterygoid −1.26.

**Use A.** A physical source has a single orientation, so the meaningful
quantity is the gap evaluated at that orientation, and its distribution over the
sweep is what Figure 5 plots. B differences two medians that need not occur at
the same orientation — the same defect already identified in 04b for min/max,
weaker for the median but not eliminated. If B is retained anywhere, it must be
labelled as a different statistic and its construction stated.

---

## Abstract — replacement paragraph

The two montages are complementary rather than ranked, and the complementarity
is orientation-dependent in a way a point estimate conceals. Sweeping source
orientation over the hemisphere with the same orientation applied at both
electrodes, five articulators — orbicularis oris, buccinator, mentalis,
depressor anguli oris and platysma — favour the jaw montage at every orientation
tested, by medians of 8.2 to 21.9 dB; no fibre direction exists at which a
retroauricular electrode competes for them. Temporalis favours the
retroauricular montage at every anatomically reachable orientation: the 4 % of
directions that reverse it lie at least 19° out of the sagittal plane, outside
the fan temporalis occupies, and the gap across that fan runs −2.70 dB at the
anterior fibres to −4.60 dB at the posterior. Sternocleidomastoid favours the
ear at its own estimated fibre axis, by −5.06 dB on the right and −2.52 dB on
the left. Lateral pterygoid, which has no estimable axis, favours the ear in
69 % of directions and is reported as conditional.

---

## §3.1 — replacement section

Reporting one gap per muscle presumes a fibre direction the model does not
contain. We therefore sweep source orientation over the hemisphere at 200
directions, applying the same orientation at both electrodes, since only a
common orientation corresponds to a physical source. Where anatomy constrains
the fibre direction, we then evaluate the gap over that constrained set rather
than over the full hemisphere.

**The jaw's dominance over the labial group is orientation-independent.**
Orbicularis oris, buccinator, mentalis, depressor anguli oris and platysma
favour the jaw montage at all 200 sampled orientations, with median gaps of 8.2
to 21.9 dB. No fibre direction exists at which a retroauricular electrode
competes for these muscles, which is a stronger statement than any point
estimate.

**Temporalis favours the retroauricular montage at every orientation it can
physically take.** Over the full hemisphere the ear wins in 96.0 % of directions
(median −3.80 dB, range −10.99 to +1.93). The eight reversing directions form a
cone of median half-width 12.1° about [−0.504, −0.555, +0.661], with a minimum
|R| of 0.324, so every one lies at least 19° out of the sagittal plane.
Temporalis is a flat fan running from the temporal fossa to the coronoid process
with negligible medio-lateral component, and that cone is therefore unreachable.
Evaluated across the fan itself the gap is −2.70 dB at the anterior,
near-vertical fibres, −3.54 dB at mid-fan, and −4.60 dB at the posterior,
near-horizontal fibres. The advantage is effectively unconditional.

**Sternocleidomastoid favours the ear at its estimated fibre axis, more strongly
than the unconstrained sweep suggests.** Its principal axis passes the bilateral
mirror-symmetry test at |dot| = 0.98, and the gap evaluated there is −5.06 dB on
the right and −2.52 dB on the left, against a sweep median of −1.96 dB. The
72.5 % hemisphere fraction understates the case, because the jaw-favouring
directions are not ones this muscle occupies.

**Lateral pterygoid is genuinely conditional.** It has no estimable principal
axis, favours the ear in 69.0 % of directions (median −1.85 dB, range −7.70 to
+6.78), and is reported as depending on fibre direction.

**Masseter and medial pterygoid show no resolvable montage preference**, at
35.5 % and 37.0 % of directions favouring the ear respectively. Medial pterygoid
carries an estimated axis, but its two sides disagree in sign at that axis
(+4.21 dB right, −2.10 dB left), which is a third independent reason it supports
no directional claim.

---

## Table 4 — replacement structure

Caption: **Which montage sees which muscle, with orientation dependence stated.**
Gap is computed per orientation and the median taken over 200 hemisphere
directions; positive favours the jaw. "% ear" is the fraction of sampled
directions favouring the retroauricular montage. Jaw sites within 10 mm of the
truncation face are excluded.

| Muscle | Median gap (dB) | % ear | Status |
|---|---|---|---|
| mentalis | *from CSV* | 0.0 | jaw, orientation-independent |
| depressor anguli oris | *from CSV* | 0.0 | jaw, orientation-independent |
| buccinator | *from CSV* | 0.0 | jaw, orientation-independent |
| orbicularis oris | *from CSV* | 0.0 | jaw, orientation-independent |
| platysma | *from CSV* | 0.0 | jaw, orientation-independent |
| masseter | +1.70 | 35.5 | no resolvable preference |
| medial pterygoid | +1.15 | 37.0 | no resolvable preference; sides disagree at axis |
| lateral pterygoid | −1.85 | 69.0 | ear, conditional on fibre direction |
| sternocleidomastoid | −1.96 | 72.5 | ear at estimated axis (−5.06 R, −2.52 L) |
| temporalis | −3.80 | 96.0 | ear, effectively unconditional (flip cone unreachable) |

Fill the five jaw medians from `results/04d_*.csv` rather than from the 8.2–21.9
range quoted in prose. Sort as shown: jaw-stable first, then graded, then the
strongest ear result last, so the reading order matches the argument.

---

## Methods addition — the anatomically-constrained sweep

Insert into §2.5, or as a short §2.5.1.

An unconstrained orientation fraction is conservative to the point of being
misleading, because orientation space is not uniformly reachable. Two muscles
demonstrate this in opposite directions. For temporalis, the directions that
reverse the montage preference lie outside the anatomical fan entirely, so an
unconstrained 96 % understates a result that is effectively unconditional. For
sternocleidomastoid, the jaw-favouring directions are not ones the muscle
occupies, so an unconstrained 72.5 % understates a gap that is −5.06 dB at the
estimated axis. We therefore sweep the hemisphere first and intersect with the
anatomically permitted set wherever one can be established, reporting the
unconstrained fraction alongside so the constraint is visible rather than
implicit.

---

## Notes for Claude Code

- The five jaw-stable muscles' individual medians are not in this file. Read
  them from the results CSV; do not use the 8.2–21.9 range as a per-muscle
  number.
- Every other number here is quoted from your own reports. Verify each against
  source before it ships, per the standing number-audit rule.
- The fat-swap differential (−0.332 dB) is currently an |E| number and is
  therefore not yet quotable. Table 3 row 9 and §3.3 stay pending until the
  re-solve lands.
