# UNVERIFIED wording — three stale-framing sites

> **APPROVAL UNVERIFIED. DO NOT APPLY.** This file previously read "approved by
> Carl 2026-08-06". That date had not occurred when the file was committed, and
> Carl does not recall approving it. The attribution is stripped and deliberately
> NOT re-dated: re-dating would launder an invented date into a clean record of
> an approval nobody confirmed. Nothing here enters the manuscript until Carl
> re-reads it.
>
> **Measured against the current manuscript: 3 of 10 prose probes from this
> file's proposed text are already present (30%).** Text from an unverified file
> is already applied. That is a defect awaiting Carl's ruling, not a precedent.

Written by Claude (the assistant). All three quote
correct numbers while presuming a retroauricular advantage that no longer
resolves. The fix is the same in each: a **gap** is not an **advantage**, and
the win/lose framing has to go with it.

**Every number is a placeholder.** Fill from `04e_fat_contrast_statisticA.csv`
and `04h`, not from this file.

---

## 1. §4.3, line 699 — replace the two-regime sentence

Currently contrasts "muscles the jaw wins" against "those the ear wins." There
are none in the second category.

> The share is largest where the gap is smallest, and that is mostly a
> denominator effect rather than a difference in the tissue's role. The absolute
> contribution of the contrast is of comparable size across muscles —
> `[CONTRIB_MIN]` to `[CONTRIB_MAX]` dB — while the gaps it is measured against
> span an order of magnitude. Expressed as a share it therefore reaches
> `[SHARE_MAX]` per cent for the three muscles whose gaps come closest to zero
> and falls to `[SHARE_MIN]` per cent for the labial group, where the jaw's
> advantage is largest. Neither figure describes a different mechanism; they
> describe the same term divided by different quantities.

---

## 2. §4.3, line 730 — replace the temporalis sentence

Currently: *"suppressing an advantage that would otherwise be 4.92 dB rather
than 3.80."* Temporalis has no advantage that resolves.

> For temporalis the contrast acts against the gap rather than for it: removing
> it would enlarge the gap from `[TEMP_WITH]` to `[TEMP_WITHOUT]` dB. The
> direction is worth stating because it is the opposite of the intuitive
> reading — the tissue contrast is not what produces temporalis's proximity to
> zero, it is part of what holds it there. It does not change the verdict, which
> is set by the matched-count interval and not by this term.

---

## 3. Table 3 row 9 — replace the value cell

Currently reads *"the contrast SUPPRESSES its ear advantage"* and *"+0.41 dB
(21 % of its advantage)"* for sternocleidomastoid.

> per-muscle, sign varies: `[TEMP_DELTA]` dB for temporalis (acts against the
> gap), `[SCM_DELTA]` dB for sternocleidomastoid and `[LP_DELTA]` dB for lateral
> pterygoid (act with it), `[LABIAL_RANGE]` dB across the labial group. No
> single figure is admissible — the sign differs by muscle. Shares are not
> quoted here because they are dominated by the denominator; see §4.3.

Use **gap** throughout the row. The word *advantage* must not appear in
connection with any retroauricular result anywhere in the manuscript.

---

## Placeholder sources

| Placeholder | From |
|---|---|
| `[CONTRIB_MIN]`, `[CONTRIB_MAX]` | `04e`, min/max of \|change\| across all ten |
| `[SHARE_MIN]`, `[SHARE_MAX]` | `04e`, share column |
| `[TEMP_WITH]`, `[TEMP_WITHOUT]` | `04e`, temporalis with/without contrast |
| `[TEMP_DELTA]`, `[SCM_DELTA]`, `[LP_DELTA]` | `04e`, change column |
| `[LABIAL_RANGE]` | `04e`, change column across the five labial/platysma |

---

## Note for Claude Code

After applying these, **grep the whole manuscript for "advantage"** and check
every occurrence. The word is correct for the jaw montage and wrong for the
retroauricular one everywhere it appears. This is the same class as the six
stale sentences the grep-after-correction rule caught earlier — a framing that
propagated into consumers written before the framing changed. Report the count
and the sites before editing any that sit in Discussion prose.
