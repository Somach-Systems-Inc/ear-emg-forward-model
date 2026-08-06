# WORDING_title_and_item11.md

Status: **pending Carl.** Supervisor-approved only. Do not stamp Carl's name on
this file.

Two locations:

1. The paper's title
2. Table 3 row 3, item 11

**Placeholder rule.** Every `{{NAME}}` is filled from the source named below.
Where a source disagrees with any number in my prose, **the source wins**. Report
the discrepancy in METHODS_LOG. Do not reconcile.

---

## Placeholder table

| placeholder | source |
|---|---|
| `{{N_JAW_FAVOURING}}` | `results/04q_table4_envelope.csv` — muscles favouring jaw on both axes in every subset |
| `{{N_MUSCLES}}` | same |
| `{{ENVELOPE_LO}}` `{{ENVELOPE_HI}}` | same |
| `{{N_SUBSETS}}` | same |
| `{{N_UNSTABLE}}` | same |

---

## 1. Title

### Why the current title fails

> Canonical jaw electrode sites outperform retroauricular sites for every
> resolvable speech articulator: a volume-conductor model with orientation and
> electrode-count controls

"For every resolvable speech articulator" is a universal claim. The result is
`{{N_JAW_FAVOURING}}` of `{{N_MUSCLES}}` favouring the jaw on both axes,
`{{N_UNSTABLE}}` unstable across subsets and reaching no verdict, and one
(temporalis) reading ear-on-both-axes under the uniform sweep. If "resolvable"
denotes the muscles that resolved to jaw, the claim is circular; if it denotes
anything reaching a verdict, temporalis is a counterexample in one treatment.

The abstract's headline sentence, "No muscle robustly favours the retroauricular
montage," is correct and stays. A title should not assert more than its abstract.

### Option A — the negative claim, matching the abstract

> No speech articulator robustly favours retroauricular electrodes over canonical
> jaw sites: a volume-conductor model with orientation and electrode-count
> controls

**Mechanism.** Promotes the abstract's own sentence, which survived every
correction. Negative claims do not inherit the counting problem: temporalis
failing to reach ear-on-both-axes under the derived field is consistent with it,
and the unstable muscles are consistent with it by reaching no verdict at all.
The title becomes true under every admissible subset for the same reason the
headline is.

**Cost.** Negative results read as weaker. The finding genuinely is a negative
one, so this is accurate rather than modest, but it will be read as modest.

### Option B — the counted claim

> Canonical jaw electrode sites outperform retroauricular sites for
> `{{N_JAW_FAVOURING}}` of `{{N_MUSCLES}}` speech articulators: a
> volume-conductor model with orientation and electrode-count controls

**Mechanism.** Replaces the universal with the count, which is what `04q`
actually supports. No "resolvable" to interpret, and a reader can check the
number against Table 4 directly.

**Cost.** A bare count invites "and the other five?" in the abstract's first
sentence — which is answerable, but the title has committed you to answering it.

### Option C — the method-forward framing

> A volume-conductor model of jaw versus retroauricular electrode sites for
> speech-articulator EMG: orientation, electrode-count and fibre-model controls

**Mechanism.** States the object rather than the finding, so no result claim can
go stale. The controls are the paper's actual contribution — the headline
survived six corrections precisely because they were applied, and they are what a
reader replicating this would want.

**Cost.** Method-forward titles attract fewer readers than claim-forward ones.
Given that the effect collapsed six times and the surviving claim is negative,
this may be the honest framing rather than a concession.

### Recommendation

**A**, with **C** as the fallback if the negative framing reads too weakly to
you. A is the only option whose truth conditions are identical to the abstract's,
which means no future correction can make the title and the abstract disagree.

Not B. Its count is stable today, but it is the one option that would need
revising if any muscle's verdict moved, and this paper's numbers have moved six
times.

---

## 2. Table 3 row 3, item 11

Ruled: §4.7 is correct, Table 3 row 3 is wrong. "Bounded by §3.4" claims a bound
§3.4 never established. §3.4 measures the shift from dropping the two most
exposed jaw sites; it does not bound the inferior-boundary artefact on the sites
that remain, and every site carries some exposure. The measurement that would
have bounded it directly, the neck-extended mesh, failed to conserve charge.

Replace row 3's final cell:

> unquantified; direction known, magnitude not bounded

Do not change §4.7. Its wording is the correct one.

If row 3 now needs the "directional, unquantified" label from item 21, apply it
for consistency with rows 1, 2 and 7.

**Optional sentence for §3.4**, if it currently implies it bounds this term:

> The sensitivity reported here measures the effect of excluding the most
> exposed sites. It does not bound the residual boundary artefact on the sites
> that remain, which is addressed in §4.7.

---

## Notes for the implementer

1. **The title change cascades.** Grep for the current title string in README.md,
   HANDOFF.md, any arXiv metadata file, and figure or caption headers. Report
   every location before editing.

2. **Do not adjust the abstract to match the new title.** The abstract sentence
   is correct as written and is the reason A works. If the title and the abstract
   appear to disagree after the change, report it rather than editing either.

3. Row 3's repair is a one-cell edit in a table with no anchor. Run the
   pipe-count check afterward, the same one that caught the doubled pipe in row 2.
