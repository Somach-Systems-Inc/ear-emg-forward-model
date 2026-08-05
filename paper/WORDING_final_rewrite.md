# Approved wording — final rewrite

Written by Claude (the assistant), approved by Carl 2026-08-05. Supersedes the
Abstract and §3.1 in `WORDING_abstract_results.md` and Table 4 everywhere.
Incorporates: delivered-current renormalisation, matched site counts, the
interval criterion, and the homogeneous-scalp control.

**Do this rewrite BEFORE working PEER_REVIEW.md.** Many review items point at
the old seven-and-three framing and at numbers this replaces; rewriting first
closes them and stops you fixing text that is about to be deleted.

---

## The two-axis verdict — apply to all ten muscles

A single label was hiding information. Two independent robustness axes exist and
they do not agree, so both are reported:

- **Site robustness** — does the random-4 subsample interval exclude zero? If it
  crosses, the montage preference depends on which four electrodes you happen to
  have, which is not a montage property.
- **Orientation robustness** — what fraction of the 200 sampled source
  orientations agree with the median verdict?

| Muscle | Site-robust | Orientation | Verdict |
|---|---|---|---|
| mentalis | yes | 100 % | **jaw**, robust on both axes |
| depressor anguli oris | yes | 100 % | **jaw**, robust on both axes |
| buccinator | yes | 100 % | **jaw**, robust on both axes |
| orbicularis oris | yes | 100 % | **jaw**, robust on both axes |
| platysma | yes | 100 % | **jaw**, robust on both axes |
| masseter | yes, [+1.647, +5.793] | 64.0 % | **jaw**, site-robust but orientation-dependent |
| medial pterygoid | yes, [+1.141, +3.339] | 62.5 % | **jaw**, site-robust but orientation-dependent |
| sternocleidomastoid | no, [−1.40, +1.27] | 60.5 % | **no resolvable preference** |
| lateral pterygoid | no, [−1.59, +1.33] | 65.5 % | **no resolvable preference** |
| temporalis | yes, [−3.31, −0.03] | 92.0 % | **ear**, robust on both axes |

Fill exact intervals and fractions from source; those above are quoted from
reports and must be verified.

---

## Abstract — replacement

**Objective.** Ear-worn biopotential devices are being designed around a
coupling that has not been computed: how strongly each speech articulator
reaches electrodes on the jaw and around the ear. We compute it, and test the
answer against the three things that could produce it spuriously — source
orientation, electrode count, and the level of anatomical detail in the volume
conductor.

**Approach.** Articulator-to-electrode coupling is computed by reciprocity on
MIDA, a head model with 116 labelled compartments at 500 µm, treating muscle as
both the generator and its own conducting compartment. Twenty-two electrode
positions spanning the canonical jaw montage, a retroauricular cluster and a
cEEGrid C-path are compared against ten individually segmented articulators.
Each lead field is renormalised by its own measured delivered current. Source
orientation is swept over the hemisphere rather than assumed. Because the ear
montage offers fourteen candidate sites against the jaw's four, every comparison
is repeated at matched electrode counts by random subsampling. The pipeline is
validated against an analytic four-layer sphere (median RDM 4.36 % over 120
sources) and by four physical invariants computed on the head mesh.

**Main results.** The two montages see different muscles, but the effect is
narrower than an unmatched comparison suggests. Five articulators —
orbicularis oris, buccinator, mentalis, depressor anguli oris and platysma —
favour the jaw montage at every sampled orientation and at every electrode
subsample. One, temporalis, favours the retroauricular montage on both axes,
by 2.57 dB at a pre-registered four-site cluster, with 92 % of orientations
agreeing and a subsample interval excluding zero. Masseter and medial pterygoid
favour the jaw robustly across electrode selection but reverse in roughly a
third of orientations. Sternocleidomastoid and lateral pterygoid show no
preference that survives electrode subsampling: their intervals cross zero, so
the apparent advantage depends on which four sites are available. Electrode
placement chosen by anatomical target outperforms arbitrary placement around
the ear by up to 1.03 dB. A control in which every non-muscle soft tissue is
set to a single conductivity reproduces every montage assignment unchanged
while misstating gap magnitudes by up to 3.27 dB.

**Significance.** For device design the result is a per-muscle map rather than a
ranking: a retroauricular montage reads temporalis well, loses lip and chin
activity entirely, and offers no reliable advantage elsewhere. The
homogeneous-conductor control locates what anatomical detail is needed for —
montage assignment is recoverable without it, magnitudes are not.

---

## Introduction — replacement for the novelty paragraph

Replaces the paragraph asserting that no forward model treats muscle as its own
conducting compartment.

> Forward models of muscle sources in realistic head geometry exist. HArtMuT
> (Harmening et al. 2022) places roughly 3,900 muscle dipole and tripole sources
> derived from MIDA's muscle segmentation, with fibre directions estimated by
> principal component analysis, solved as finite-element lead fields. It is the
> methodological precedent for the fibre-axis treatment used here, and its
> muscle sources radiate through a homogeneous scalp compartment.
>
> **This study is an application of that class of model to an unanswered design
> question, not a methodological advance over it.** We tested the distinction
> directly rather than asserting it: setting every non-muscle soft tissue to a
> single conductivity, with geometry held fixed, reproduces every montage
> assignment reported here unchanged (§3.5). A homogeneous-scalp model would
> have reached the same qualitative conclusion. What the anatomically resolved
> conductor supplies is magnitude — gap sizes shift by up to 3.27 dB, and eight
> of ten by more than the measurement floor — which matters for a design table
> quoting decibels but not for deciding which montage sees which muscle.
>
> The open question is therefore not how to model muscle sources but where to
> put an electrode. That question is stated in the ear-EEG literature in the
> same terms (Yarici et al. 2023), while ear-worn arrays are already recording
> jaw and speech activity (Avramidou et al. 2024; An et al. 2025) on a widely
> replicated form factor (Debener et al. 2015). Devices are being designed
> around a coupling nobody has computed.

---

## §3.1 — replacement

> Reporting one gap per muscle presumes a fibre direction the model does not
> contain, and comparing the best of fourteen retroauricular sites against the
> best of four jaw sites rewards electrode count rather than placement. Both are
> controlled. Source orientation is swept over the hemisphere at 200 directions
> with the same orientation applied at both electrodes, since only a common
> orientation corresponds to a physical source. Electrode count is matched by
> drawing four of the fourteen ear sites at random, taking the best, and
> repeating; the resulting interval says whether a preference is a property of
> the montage or of which sites happen to be available.
>
> **The jaw's dominance over the labial group is robust on both axes.**
> Orbicularis oris, buccinator, mentalis, depressor anguli oris and platysma
> favour the jaw at all 200 sampled orientations and at every electrode
> subsample. No fibre direction and no four-site selection exists at which a
> retroauricular electrode competes for these muscles.
>
> **One articulator favours the ear on both axes.** Temporalis reaches −2.571 dB
> at the pre-registered four-site retroauricular cluster, with 92.0 per cent of
> orientations agreeing and a matched-count interval of [−3.31, −0.03] that
> excludes zero. It is the only muscle in the study for which a retroauricular
> montage is preferable independent of both fibre direction and site selection.
>
> **Two show no preference that survives electrode subsampling.**
> Sternocleidomastoid (−0.973 dB at the cluster, 60.5 per cent of orientations,
> interval [−1.40, +1.27]) and lateral pterygoid (−1.564 dB, 65.5 per cent,
> [−1.59, +1.33]) both have intervals crossing zero. Their apparent advantage
> depends on which four sites are available and is not a property of the
> montage. Reported at the unmatched argmax over fourteen sites they would read
> −1.402 and −1.679 dB, which is why the matched comparison is the one reported.
>
> **Two favour the jaw robustly across sites but not across orientation.**
> Masseter and medial pterygoid have subsample intervals entirely positive, but
> 36.0 and 37.5 per cent of sampled orientations reverse them. A single label
> would discard one axis or the other, so both are reported (Table 4).

---

## §3.5 — new section, the homogeneous-conductor control

> **A homogeneous soft-tissue conductor reproduces every montage assignment.**
> Setting skin, adipose and the non-muscle soft tissues to a single conductivity,
> with geometry, electrodes and sources held exactly fixed, changes no muscle's
> montage preference. Eight of ten gap magnitudes move by more than the 0.27 dB
> floor, with a median shift of 0.482 dB and a maximum of 3.271 dB (mentalis).
>
> The direction is not uniform. Temporalis's retroauricular advantage *grows*
> under the homogeneous conductor, from −3.315 to −4.330 dB, so the anatomically
> resolved model reports that result more conservatively than a simpler one
> would. Sternocleidomastoid and lateral pterygoid move the other way.
>
> This locates what the detailed conductor is required for. The question of
> which montage sees which muscle is answerable without it. The question of by
> how much is not, and a design table quoting decibels needs it.

---

## §3.6 — new section, placement method

> **Placement chosen by anatomical target outperforms arbitrary placement.** The
> four-site retroauricular cluster — above the ear, over the mastoid, behind and
> below the lobule, and anterior to the tragus — was specified by anatomical
> target in the project repository before any solve was run. Compared against
> the median of random four-site draws from the same fourteen candidates, it is
> 1.03 dB better for lateral pterygoid (−1.564 against −0.534) and equivalent
> for sternocleidomastoid (−0.973 against −0.979).
>
> Neither of the two sites that won the unmatched argmax for temporalis and
> sternocleidomastoid is in that cluster, which is the same point from the other
> direction: an argmax over fourteen densely spaced positions rewards density,
> while a four-site montage rewards placement. For a device constrained to a
> small number of contacts, where they go matters more than how many candidates
> were considered.

---

## Notes for Claude Code

- **Verify every number here against source before it ships.** Written from your
  reports, not from the CSVs.
- Table 4 replaces the single-verdict version everywhere it appears, including
  Fig 5's caption and the design-table discussion.
- §4.4's device-design paragraph must be rewritten to match: the ear reads
  temporalis, loses the labial group, and offers no reliable advantage
  elsewhere. Remove any claim resting on sternocleidomastoid or lateral
  pterygoid.
- §4.6's Paper 2 prediction narrows to temporalis-driven gestures. Remove
  lateral pterygoid from it.
- The title still holds — temporalis against the labial group is still "different
  articulators" — but check it reads honestly against a one-muscle result.
- Record in METHODS_LOG that the homogeneous control was pre-committed with both
  branches written before the solve, that the branch taken was the one costing
  the novelty claim, and that temporalis's advantage grows under the simpler
  model, so the reframe is not a self-serving read of an ambiguous result.
