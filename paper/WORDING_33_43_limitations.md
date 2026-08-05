# Approved wording — §3.3, §4.3, Limitations

Written by Claude (the assistant), approved by Carl 2026-08-05. Companion to
`WORDING_abstract_results.md`, which carries the Abstract, §3.1, Table 4 and the
Methods addition. Drop in verbatim once the two flagged recomputations land.

Written against the **statistic-A** fat-swap table, which supersedes the B
version reported earlier the same day.

---

## BEFORE APPLYING — two numbers must be recomputed under A

The across-sites differential (**−0.690 dB**, jaw −2.873 / ear −2.183) and the
labial group's **3–7 %** fraction were both computed under statistic B. You
demonstrated that B is unreliable for the fat condition specifically — a
conductivity change reshapes the current path rather than scaling it, so the two
conditions' per-site medians drift to different orientations. Those two numbers
inherit that defect.

Recompute both from the A data. No new solve required. Placeholders below are
marked `‹A›`. If the population differential cannot be defined cleanly under A,
**drop it and report the per-muscle table alone** — that is what every claim
rests on, and a population median that mixes muscles adds nothing the table does
not already say.

---

## §3.3 — replacement

Solving the full montage twice on identical geometry — once with adipose at
0.025 S/m and once with both adipose compartments set to muscle conductivity —
attributes any difference to material properties alone, since source-to-electrode
distance is unchanged by construction. The second condition is a counterfactual
used to decompose mechanism; the gaps reported throughout this paper are the
first, because real anatomy contains adipose tissue.

The contribution is not uniform in sign across muscles, because which electrode
is best differs by muscle and the shift is not uniform within a montage:

| Muscle | As modelled | Without contrast | Change | Share of gap |
|---|---|---|---|---|
| temporalis | −3.801 | −4.923 | **−1.121** | contrast *suppresses* the advantage |
| sternocleidomastoid | −1.958 | −1.547 | +0.411 | 21 % |
| lateral pterygoid | −1.855 | −1.532 | +0.323 | 17 % |

For the labial group, where the jaw wins by 8.2 to 21.9 dB, the contrast accounts
for ‹A› per cent of the gap. For the three muscles the ear wins it accounts for
17 to 21 per cent, and in opposite directions: it **suppresses** the temporalis
advantage by 1.12 dB, so that result is conservative as reported, and it
**contributes** 0.41 dB to sternocleidomastoid and 0.32 dB to lateral pterygoid.

Each ear advantage survives removal of the contrast — temporalis at −4.92 dB,
sternocleidomastoid at −1.55, lateral pterygoid at −1.53 — all clear of the
electrode-meshing floor and of its 95 % confidence upper bound of 0.65 dB.

---

## §4.3 — replacement

The ear's deficit against the labial group is geometric. The adipose–muscle
conductivity contrast accounts for ‹A› per cent of a gap reaching 21.9 dB; the
remainder is source-to-electrode distance. Limb studies cannot separate the two,
because adding a fat layer changes material properties and distance together
(Kuiken et al. 2003). A labelled head model can, because conductivity is changed
with geometry held exactly fixed. This is a comparison the limb geometry
structurally cannot support, and it is available here for the cost of one extra
solve.

The same decomposition applied to the ear's own advantages returns a modest and
sign-varying term. For temporalis the contrast works against the reported result,
suppressing an advantage that would otherwise be 4.92 dB rather than 3.80; the
figure in this paper is therefore conservative. For sternocleidomastoid and
lateral pterygoid it contributes 21 and 17 per cent of their advantage, so those
two are partly carried by tissue properties rather than by geometry alone. All
three survive its removal.

That distinction predicts which results should transfer between subjects. A
margin carried by skeletal attachment geometry inherits only anatomical variance;
a margin carried by a tissue-conductivity contrast also inherits variance in
adipose distribution, which is the larger and more variable of the two between
individuals. Temporalis and the labial group should therefore be expected to
transfer more readily than sternocleidomastoid and lateral pterygoid. The
prediction is a consequence of the decomposition rather than a separate claim,
and it is testable in any second anatomy.

---

## Limitations — replacement for the single-anatomy paragraph

MIDA is a single subject, and between-subject variance in muscle geometry,
adipose thickness and pinna position cannot be estimated from one head. The
adipose decomposition narrows what that means, but unevenly, and the unevenness
is itself informative. The labial group and temporalis are carried by geometry,
which is comparatively conserved between individuals; sternocleidomastoid and
lateral pterygoid draw 21 and 17 per cent of their advantage from the
conductivity contrast, so they should be expected to track subject adiposity and
are the results least likely to transfer unchanged. This is a reason to expect
differential generalisation, not a demonstration of any of it. Only a second
anatomy demonstrates that.

---

## Notes for Claude Code

- **Do not ship a single percentage for the adipose term without its sign.** The
  contrast suppresses temporalis and inflates the other two. One number hides a
  direction that differs by muscle. This applies to Table 3 row 9, §3.3, §4.3 and
  the Abstract if it mentions the term at all.
- **The B numbers (+1.361 / +0.815, 42 % / 65 %) are superseded and must not
  appear anywhere outside METHODS_LOG**, where they are already marked as such.
  The claim "lateral pterygoid falls below the floor's CI upper bound without the
  contrast" is retracted; under A it sits at −1.532 dB.
- Verify every number in this file against source before it ships, per the
  standing rule. It was written from your reports.
- After applying, re-verify all six figures against source as you offered, and
  report anything in the manuscript that still traces to a superseded value.
