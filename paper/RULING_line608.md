# UNVERIFIED ruling — line 608, and what it implies for §3.5 and axis (a)

> **PROVENANCE UNVERIFIED. DO NOT APPLY.** This file is the fifth member of the
> 2026-08-06 set: it is stamped with a date that had not occurred when it was
> written, by the generator that also produced four false "approved by Carl"
> attributions. The date line is left in place rather than re-dated, for the same
> reason the other four were not re-dated.
>
> It was also, until 2026-08-05, **absent from the repository entirely** while
> HANDOFF §3 cited `paper/RULING_line608.md` §5 as the approved wording for line
> 608. It existed only as an untracked file in Carl's Downloads, so it was in no
> commit and no history. Copied in unmodified; byte-identical to his copy.
>
> Nothing here enters the manuscript until Carl re-reads it. The §3.5 text it
> governs is in `~/Downloads/REREAD_PACKET.md`.

Written by Claude (the assistant), 2026-08-06. Supersedes the line-608 block in
`WORDING_advantage_3sites.md`, which was written against `04i` before the basis
mismatch was visible and is now **withdrawn**.

**Every number below is a placeholder.** Fill from source. Source wins over any
value quoted here; report the discrepancy rather than reconciling it.

---

## 1. The ruling

**Take the second option: compute the homogeneous gap at the pre-registered
cluster.** Do not adopt 04i's argmax-14 pair.

Causal reason, so the rule generalises rather than settling one line:

§3.5's sentence is a **difference of two gaps**. A difference is only
interpretable when everything except the variable under test is held fixed. Here
the variable under test is conductor detail — anatomical σ map versus
homogeneous scalp. Pairing `04h`'s cluster gap with `04i`'s argmax-14 gap varies
two things at once: the conductor **and** the site-selection rule. Argmax-14
maximises over sites, so it carries a selection bias whose size depends on how
the field is shaped, which is exactly what changing the conductor alters. The
resulting difference is part conductor effect, part selection-bias drift, in
unknown proportion. That is the same failure as statistic B: differencing two
quantities each of which was independently maximised over a nuisance axis.

Cluster basis also matches the rest of the paper. Table 4, the matched-count
intervals and every headline magnitude are cluster-based. A §3.5 stated at
argmax-14 would be the only place in Results using a basis the paper retired for
its own claims, and a reviewer would reasonably read that as basis-shopping.

---

## 2. Pre-commitment, before you look at the number

State this in `METHODS_LOG.md` **before running**, so the reading is not chosen
after seeing the result:

- The claim §3.5 currently makes is *directional*: the detailed conductor places
  temporalis **closer to zero** than a homogeneous one does.
- If the cluster-basis homogeneous gap is **more negative** than the cluster-basis
  detailed gap, the claim survives and the wording below applies as written.
- If it is **less negative**, or the two straddle, the claim inverts or dissolves.
  That is a finding change, not a wording change: **halt and report, do not
  rewrite §3.5 yourself.**

Either outcome is publishable. §3.5 is a control, not a support of the headline
result, and the headline verdict is set by the matched-count interval.

---

## 3. Guard before running

If the homogeneous-scalp solve stored only argmax-reduced outputs and the
per-site fields needed for a cluster restriction are **not on disk**, then this
is a re-solve, not a re-reduction. In that case **halt and report** rather than
re-solving — a solve is a memory- and time-bearing operation and there are
outside processes running on that machine that must not be disturbed. Say which
arrays are missing and what the solve would cost.

If the fields are present, the computation is a re-reduction of existing data.
Run it.

---

## 4. What 04i must emit

The mismatch happened because a CSV carried numbers whose basis was recorded
nowhere. Fix the class, not the instance:

1. `04i_homog_scalp.csv` gains an explicit **`basis`** column with values
   `argmax14` or `cluster`, and emits **both** bases for every muscle in the same
   file. Both are legitimate; only the silent mixing is not.
2. The matching detailed-conductor gap goes in the same row, from the same basis,
   so a consumer cannot pair across bases by accident.
3. Add the basis to the column headers of any table derived from it.
4. Any homogeneous number quoted in prose **names its basis in the sentence.**

Then extend `04m_caption_numbers.py --check` to fail if a homogeneous value
appears in prose or a caption without a basis word adjacent to it.

---

## 5. Wording for line 608 — apply only if the pre-commitment in §2 holds

> Temporalis's gap grows more negative under the homogeneous conductor, from
> `[TEMP_CLUSTER_DETAILED]` to `[TEMP_CLUSTER_HOMOG]` dB at the pre-registered
> cluster, so the anatomically resolved model is not what places temporalis close
> to zero. Sternocleidomastoid and lateral pterygoid move the other way. Both
> figures are cluster-basis; the argmax-14 equivalents are
> `[TEMP_ARGMAX_DETAILED]` and `[TEMP_ARGMAX_HOMOG]` dB and are reported in
> Table `[N]` for comparison.

The word **advantage** does not appear. The point survives unchanged: the
detailed conductor is not the cause of temporalis's proximity to zero.

### The rest of §3.5

Restate the whole homogeneous-control comparison at cluster basis, not just this
sentence. A section with one cluster sentence and the rest at argmax-14 is the
same defect at smaller scale. Where a §3.5 quantity can only exist at argmax-14 —
if any does — keep it and label it in the sentence.

### Placeholder sources

| Placeholder | From |
|---|---|
| `[TEMP_CLUSTER_DETAILED]` | `04h`, temporalis, matched-count cluster gap |
| `[TEMP_CLUSTER_HOMOG]` | `04i` after §4's change, `basis == cluster` |
| `[TEMP_ARGMAX_DETAILED]`, `[TEMP_ARGMAX_HOMOG]` | `04i`, `basis == argmax14` |
| `[N]` | whichever table carries the homogeneous control |

---

## 6. The orphan number is the finding here, not a side note

**−3.724 exists in no results file.** That is worse than a stale number. A stale
number was once correct and drifted; an orphan number was never generated by
anything. It cannot be traced, cannot be regenerated, and passed every check the
project has because every existing check compares source-to-prose for numbers it
already knows about, never prose-to-source for numbers it does not.

Add to `CLAUDE.md` as a named class:

> **Orphan number.** A magnitude in prose or a caption that matches no cell in
> any results file. Checks that verify known claims against source cannot detect
> one, because the claim is not in the manifest. Detection requires the reverse
> sweep: enumerate every number in the prose and require each to name a source.
> Finding one invalidates the assumption that the surrounding paragraph was ever
> generated from data.

Grep §3.5 and its neighbours for further orphans **before** editing line 608 —
an orphan usually has siblings, because it enters when a paragraph is written
from memory rather than from a file. Report what you find before changing
anything.

---

## 7. Axis (a) — make it a check, not a reading

Line 608 justifies the axis-(a) pass and also shows a manual pass is the wrong
instrument: a human read would have accepted −3.724 as plausible, because it sits
between the two real numbers.

`04m_caption_numbers.py` already does claim-against-source for 7 caption claims.
Extend it rather than writing a second tool:

1. A manifest CSV: one row per numeric claim — anchor, quoted value, source file,
   column, row selector, tolerance.
2. `--check-body` walks the manifest, fails on drift, and **fails on any number
   in the covered spans that has no manifest row.** The second condition is what
   catches orphans; without it the extension inherits the blind spot.
3. Covered spans, in order: Abstract, then all table cells, then finding-bearing
   Results sentences. Descriptive Methods numbers stay deferred.
4. Prove it fires: perturb one manifest value and one prose number in a scratch
   copy, confirm both conditions trip, revert. No check reports clean until it has
   been shown to fire on a known-bad case in the same session.

This is more work than reading 40–60 claims once, and it is worth it because the
numbers have moved six times already and will move again if any correction
lands before submission.

---

## 8. Ordering

Confirmed, with the manifest folded in:

1. §3, §4, §5, §6 of this file — the 608 fix and the 04i basis change.
2. Axis (a) as `--check-body`, spans in the order above.
3. `03e_build_tensor.py` emits per-compartment tensor decisions to CSV.
4. Re-render Fig 1 (22-electrode fix is committed, figure is not rebuilt).
5. Item 23 — figure citations in Results.
6. Majors 11, 12, 14, 19, 21, 29; then 16, 17, 32 as rewrites.

Minors 30, 35–41, 43, 47 and editorial 44–49 stay deferred to post-arXiv.
