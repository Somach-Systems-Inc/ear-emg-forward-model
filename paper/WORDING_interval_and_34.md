# WORDING_interval_and_34.md

Status: **pending Carl.** Supervisor-approved only. Do not stamp Carl's name on
this file or record it as approved by him.

Covers four locations, all settled as of 85e453b:

1. §3.1 — the headline interval, its construction and its floor
2. §4.1 — the "not a correction of an error" sentence
3. §3.4 — boundary adequacy, regenerated
4. §4.7 — the sensitivity figure §3.4 feeds

**Placeholder rule.** Every `{{NAME}}` is filled from the source named below.
Where a source value disagrees with any number in my prose or in chat, **the
source wins**. Report the discrepancy in METHODS_LOG. Do not reconcile, do not
adjust the source, do not prefer the value that reads better.

---

## Placeholder table

| placeholder | source |
|---|---|
| `{{N_EAR_SITES}}` `{{N_DRAWN}}` | `04k` config |
| `{{HEADLINE_MEDIAN}}` | new interval script results file |
| `{{HEADLINE_LO}}` `{{HEADLINE_HI}}` | same |
| `{{HEADLINE_PCT_EAR}}` | same |
| `{{FLOOR_VALUE}}` | same, floor column |
| `{{FLOOR_ATTAIN_PCT}}` | same, floor attainment fraction |
| `{{DRAW_PREDICT_PCT}}` | computed, `{{N_DRAWN}}`/`{{N_EAR_SITES}}` |
| `{{ARGMAX14_GAP}}` | same results file |
| `{{SEED}}` | same |
| `{{T4_TEMP_MEDIAN}}` | `04h` Table 4 temporalis row |
| `{{T4_LO}}` `{{T4_HI}}` | same |
| `{{T4_FLOOR}}` `{{T4_FLOOR_PCT}}` | C8 output |
| `{{N_ORIENT_SAMPLES}}` | `04d_orientation_sign.npz` shape |
| `{{ALL_SEVEN_MEDIAN}}` | regenerated §3.4 source |
| `{{EXCL_NEARCUT_MEDIAN}}` | same |
| `{{NEARCUT_SHIFT}}` | same |
| `{{N_NEARCUT}}` | `results/02e_cut_clearance.csv` |
| `{{CLEAR_HYOID}}` `{{CLEAR_SUBLAT}}` `{{CLEAR_SUBMID}}` | same |
| `{{MIN_EAR_CLEARANCE}}` `{{MIN_EAR_SITE}}` | same, all ear sites incl. ceegrid |
| `{{N_SIGN_FLIPS}}` `{{N_MUSCLES}}` | regenerated §3.4 source |
| `{{MOVER_1}}` … `{{MOVER_3}}` and their dB | same |
| `{{ENVELOPE_LO}}` `{{ENVELOPE_HI}}` | subset envelope output |
| `{{N_SUBSETS}}` | same |
| `{{NEARCUT_WINDOW_LO}}` `{{NEARCUT_WINDOW_HI}}` `{{NEARCUT_WINDOW_WIDTH}}` | window verification log |

If a placeholder has no source, leave it unfilled and report it. Do not
substitute from prose, from chat, or from a run whose output was not saved.

---

## 1. §3.1 — construction and floor

Replaces the interval sentence at approximately lines 497–505. Keep the existing
statement of the inferential target at 477–480; it is correct and this text
depends on it.

> Electrode count is matched by drawing {{N_DRAWN}} of the {{N_EAR_SITES}} ear
> sites at random and taking the best, repeated over draws at seed {{SEED}}. For
> the derived fibre field the draw resamples electrodes alone, with the fibre
> orientation held fixed, so the resulting spread reflects site availability and
> nothing else. Temporalis gives a median gap of {{HEADLINE_MEDIAN}} dB with an
> interval of [{{HEADLINE_LO}}, {{HEADLINE_HI}}] dB, favouring the ear in
> {{HEADLINE_PCT_EAR}} of draws.

New sentence, immediately following. This is the floor disclosure and it is the
part that must not be dropped for length.

> The lower bound of this interval is not a tail quantile. The most ear-favouring
> outcome of any {{N_DRAWN}}-site draw is the best of all {{N_EAR_SITES}} sites,
> so {{FLOOR_VALUE}} dB is a floor fixed by the data rather than by sampling, and
> it is attained in {{FLOOR_ATTAIN_PCT}} of draws against the
> {{DRAW_PREDICT_PCT}} expected from draw size alone. It coincides with the
> argmax gap over all {{N_EAR_SITES}} sites, {{ARGMAX14_GAP}} dB, by
> construction; the two figures are one measurement, not two that agree. The
> corresponding bound under the uniform orientation sweep, {{T4_LO}} dB, is a
> genuine percentile lying strictly above its own floor of {{T4_FLOOR}} dB, which
> is attained in {{T4_FLOOR_PCT}} of draws. The two lower bounds are therefore
> not comparable quantities.

---

## 2. §4.1 — completing the fibre-model sentence

The existing sentence at line 675 is not wrong. It is silent on a consequence.
Keep it and append.

Existing, unchanged:

> "not a correction of an error; it is the difference between assuming source
> orientation is uniform over the sphere and deriving it."

Append:

> That difference also changes what the accompanying intervals measure. Under the
> uniform sweep, orientation is a sampled dimension and the interval averages over
> {{N_ORIENT_SAMPLES}} directions within each draw; under the derived field there
> is no orientation dimension to average over, and the interval reflects site
> selection alone. The two intervals answer different questions and should not be
> read as one quantity under two fibre models.

---

## 3. §3.4 — boundary adequacy, regenerated

Full replacement. The section's argument is unchanged: concede that the cut
inflates the jaw side, then show the finding survives its removal. Every number
is new and the conclusion is stronger than the published version, because the
sensitivity is smaller.

> The inferior truncation lies closer to the jaw montage than to the
> retroauricular montage, so the cut plane could in principle inflate the jaw
> side. Perpendicular clearance to the fitted plane places {{N_NEARCUT}} jaw
> sites within 10 mm of it ({{CLEAR_HYOID}} mm and {{CLEAR_SUBLAT}} mm); the next
> nearest is {{CLEAR_SUBMID}} mm. The closest ear site, {{MIN_EAR_SITE}}, is
> {{MIN_EAR_CLEARANCE}} mm away.
>
> Removing the near-cut sites moves the median gap from {{ALL_SEVEN_MEDIAN}} dB
> to {{EXCL_NEARCUT_MEDIAN}} dB, a shift of {{NEARCUT_SHIFT}} dB. No muscle
> changes sign ({{N_SIGN_FLIPS}} of {{N_MUSCLES}}). The largest individual
> movements are {{MOVER_1}}, {{MOVER_2}} and {{MOVER_3}} dB. The reported
> advantage is not an artefact of proximity to the truncation.

If the section carries a threshold-sensitivity sentence, use this. If it does
not, do not add one; it is optional.

> The 10 mm grouping above is descriptive. The reported subsets span every
> admissible site set for any near-cut threshold between {{NEARCUT_WINDOW_LO}} mm
> and {{NEARCUT_WINDOW_HI}} mm, a window of {{NEARCUT_WINDOW_WIDTH}} mm, so no
> conclusion here depends on where in that range the threshold is placed.

**Delete outright, do not rephrase:** the claim that every ear site is 80 mm or
more away. It is false under both metrics and the corrected minimum is above.

**Delete outright:** any occurrence of +6.45 or +5.91. They reproduce under
neither metric, so they are orphans from an unsaved run rather than values the
corrected clearance moved. Record that distinction in METHODS_LOG. Do not carry
them as superseded values.

---

## 4. §4.7 Limitations — the figure it inherits

Wherever §4.7 repeats the sensitivity, substitute the regenerated value. It is a
one-number edit and the surrounding argument is unaffected, except that the
smaller shift makes the limitation milder rather than more severe. Do not
strengthen the surrounding claim to match.

> …a shift of {{NEARCUT_SHIFT}} dB when the near-cut sites are excluded.

Check that §4.7 does not separately assert the 80 mm figure or the three-site
count. If it does, both correct here as well.

---

## Notes for the implementer

1. **The floor paragraph in §3.1 is the load-bearing addition.** If a length cut
   is needed, take it from §3.4's optional threshold sentence, never from the
   floor disclosure. The floor is the only place the manuscript tells a reader
   that the headline interval's lower bound is deterministic.

2. **Do not add the per-direction construction anywhere in the manuscript.** The
   standing instruction is that the claim rests on one support and the paper says
   so. Reporting a second construction that also spans zero converts one support
   into two, which is a scope change and not this file's business.

3. **`{{NEARCUT_SHIFT}}` is smaller than the published figure.** Report it as
   found. Do not add emphasis, do not describe the sensitivity as negligible, and
   do not claim the correction strengthens the result. State the number.

4. No text in this file introduces a scalar S, a threshold, or any constant not
   emitted to a results file. If filling a placeholder appears to require one,
   stop and report rather than choosing a value.
