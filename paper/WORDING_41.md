# UNVERIFIED wording — §4.1

> **APPROVAL UNVERIFIED. DO NOT APPLY.** This file previously read "approved by
> Carl 2026-08-06". That date had not occurred when the file was committed, and
> Carl does not recall approving it. The attribution is stripped and deliberately
> NOT re-dated: re-dating would launder an invented date into a clean record of
> an approval nobody confirmed. Nothing here enters the manuscript until Carl
> re-reads it.
>
> **Measured against the current manuscript: 5 of 10 prose probes from this
> file's proposed text are already present (50%).** Text from an unverified file
> is already applied. That is a defect awaiting Carl's ruling, not a precedent.

Written by Claude (the assistant). Replaces §4.1
"What complementarity means" wholesale. The section currently asserts three ear
muscles and a 10–23 dB jaw range, both superseded.

**Every number is a placeholder.** Fill from source, not from anything in this
file or in the conversation.

---

## §4.1 — replacement

> ### 4.1 The montages are not complementary
>
> An earlier framing of this work treated jaw and retroauricular montages as
> complementary — each better for some articulators — and that framing does not
> survive its own controls. Every articulator this model can resolve favours the
> jaw montage. The three that appeared to favour the ear, all of them attaching
> at or near the temporal bone, are the three whose gaps come closest to zero,
> but none crosses it once source orientation and electrode count are controlled
> (§3.1, §4.8).
>
> The result is therefore one-sided rather than a trade. A retroauricular
> montage is not a repositioning of the jaw montage that exchanges one muscle
> group for another; it is a montage that loses the labial group by
> `[LABIAL_MIN]` to `[LABIAL_MAX]` dB and returns nothing measurable.
> Anatomical proximity to a bony attachment does predict which retroauricular
> sites are competitive, and in the right order, but competitive is not the same
> as better.
>
> Temporalis is the clearest case and the one that took longest to settle. It
> fails to resolve under two independent corrections that disagree with each
> other about magnitude: matched electrode counts alone give `[TEMP_MATCHED]` dB
> with an interval of `[TEMP_INTERVAL]`, while the derived per-voxel fibre field
> gives `[TEMP_FAN]` dB. The two differ by roughly a factor of two and agree
> that the advantage does not resolve. One is anatomy-specific and one is
> assumption-free, so their agreement on the verdict is stronger evidence than
> either would be alone.

---

## Placeholder sources

| Placeholder | Value from | Note |
|---|---|---|
| `[LABIAL_MIN]` | regenerated `04h`, min of the five labial/platysma gaps | ~8.59 |
| `[LABIAL_MAX]` | regenerated `04h`, max of the same five | ~20.20 |
| `[TEMP_MATCHED]` | regenerated `04h`, temporalis | ~−2.624 |
| `[TEMP_INTERVAL]` | regenerated `04h`, temporalis 95 % interval | ~[−2.855, +0.170] |
| `[TEMP_FAN]` | `04k`, temporalis per-voxel cluster gap | ~−1.147 |

Approximate values are shown only so you can detect a gross mismatch. **Fill
from the CSV.** If a filled value differs from the approximation by more than
rounding, report it rather than assuming the approximation is stale.

---

## Notes for Claude Code

- Check whether §4.1's old text is referenced elsewhere. "Complementarity"
  appears in the Abstract, §3.1 and possibly Fig 5's caption; the word should
  now appear only in the past tense, describing a framing that was tested and
  did not survive.
- The corollary you added — *a published table with no generating script is not
  a result yet* — should go in Methods, not only in CLAUDE.md. `04h` produced
  four published numbers, drifted out of step with §2.4, and the drift was
  invisible because every number in it was internally consistent. That is worth
  one sentence next to the reproducibility statement in §2.8.
