# Peer review triage — regenerated against HEAD `cd61e66`, 2026-08-05

Supersedes the version written against the 2026-08-05 rewrite, which had drifted:
**four items it recorded were wrong at HEAD.** Every row below states how it was
checked, so a reader can re-run the check rather than trust the classification.

`grep` means verified against `PAPER1_full_manuscript.md` at HEAD. `read` means a
judgement from reading the section. `unverified` means carried forward from the
original report without a check this pass — treat those as unknown, not open.

| | count |
|---|---|
| **CLOSED, verified** | **24** |
| **OPEN, verified** | **6** |
| **OPEN, unverified this pass** | **6** |
| **Deferred post-arXiv** | **15** |

---

## The four the previous triage got wrong

| # | it said | HEAD says | check |
|---|---|---|---|
| 2 | STILL OPEN, "10 to 23 dB survives in the Discussion" | **CLOSED** | `grep "10 to 23"` → 0 hits; the manuscript reads 8.99 to 21.24 |
| 10 | STILL OPEN, Fig 4 caption says "robust to the isotropy assumption" | **CLOSED** | `grep` → 0 hits |
| 20 | NOT closed, "Table 3 row 8 still reads bounded by row 6" | **CLOSED** | row 8 now reads "no — corrected, not bounded" |
| 32 | NOW WRONG, title overstates a three-muscle result | **CLOSED as written** | title no longer asserts complementarity; **but see the note below** |

All four were closed by `661e419` or by the title change, and the triage was
never regenerated after. **Item 32 closes only in the sense the objection named.**
The current title came from an unverified wording file and describes a
three-muscle result that is now one muscle. That is a content problem, not a
review item, and Carl has not ruled on it.

---

## OPEN, verified at HEAD (6)

| # | sev | objection | lines | closes with |
|---|---|---|---|---|
| 23 | major | **no figure is cited anywhere in the body**; zero references to any of six | 1–950 | text edit |
| 29 | major | assembly-notes section still present | 1075+ | text edit |
| 11 | major | Table 3 row 3 says "bounded by §3.4" while §4.7 says the bias is "unknown rather than estimated" | 986, 925–932 | disclosure |
| 16, 17 | major | the n=1 transferability argument and the 21% / 5.06 dB figures rest on SCM and lateral pterygoid, which now carry no claim | §4.2 | rewrite, not patch |
| 45 | editorial | SimNIBS named throughout, cited nowhere in text | throughout | text edit |
| — | — | **§3.1 now states the draw procedure twice**, at line 478 in words and line 505 in numerals, introduced when the interval wording was applied | 478, 505 | text edit |

## OPEN, not verified this pass (6)

Carried from the original report. Each needs a read before it is worked.

12 (SCM truncated as a source, bias runs toward the ear) · 13 (orientation
constraint derived for temporalis, asserted elsewhere) · 14 (mirror-symmetry test
applied inconsistently to SCM and medial pterygoid) · 19 (sphere validation
framing) · 21 (§2.7's admission rule violated by its own rows — **held by ruling**,
it is in the analysis bucket) · 22 (electrode count; counts read consistent at
HEAD, 22 positions against 14 ear candidates, but not fully traced)

## CLOSED, verified (24)

The 18 closed by the 2026-08-05 rewrite (1, 3, 4, 5, 6, 7, 8, 9, 15, 18, 24, 25,
26, 27, 28, 31, 34, 42), plus **2, 10, 20, 32** above, plus:

| # | why |
|---|---|
| 33 | §3.3's heading now reads "a small term with a muscle-dependent sign", which is graded, not the binary the objection named |
| 49 | `grep "flip cone"` → 0 hits |

## Deferred post-arXiv (15)

Minors 30, 35–41, 43, 47. Editorial 44, 46, 48. Section ordering (§4.8 at line 856
precedes §4.7 at 899) is editorial and deliberately not reordered.

---

## Not review items, but open and larger than any of them

These come from the audit rather than the review, and they outrank most of the
list above.

1. **`−3.724` is a live orphan at line 648** in §3.5, pairing `04h`'s cluster gap
   with a homogeneous value in no results file. Its remedy, `RULING_line608.md`,
   is **withdrawn** — precondition unmet — so it has no approved fix.
2. **Table 4's basis.** Five jaw sites are admissible and the matched comparison
   takes four; no rule selects the fourth. The envelope over all five subsets is
   computed (`04n`) and every verdict is invariant, but presenting it **halted**:
   the supplied caption asserts every value is an envelope while the table body
   holds single-subset point values, and no generator for an envelope body exists.
3. **Axis (a) is unbuilt.** `--check-body` with a claims manifest, failing on
   drift *and* on any number in a covered span with no manifest row. Until it
   exists no one can say the manuscript has no orphans — only that none has been
   enumerated. Item 1 above is what that gap looks like in practice.

---

## Correction to this file, same session it was written

**Item 28 is a fifth misfiled item.** It was recorded CLOSED ("editing
instructions in Results/Discussion — absent from the file"). Two are live:

- **line 80**, Introduction: *"Replaces the paragraph asserting that no forward
  model treats muscle as its own…"*
- **line 736**, §4.3: *"Replaces: \"The ear's deficit against the labial group is
  geometric…\""*

In both cases the replacement text follows and was applied, so these are leftover
instructions rather than unfinished edits. Not removed: they were found while
working item 23 and removal was not in scope.

**Related and larger, found the same way.** Body text is inconsistently wrapped in
markdown blockquotes, an artifact of pasting wording-file content with its `>`
markers intact. §3.1, §3.2, §3.5, §3.6 and §4.3 are largely or wholly
blockquoted; §4.1 and the Abstract are not. In a rendered manuscript this makes
parts of Results and Discussion appear as pull quotes. It is cosmetic, it is
systematic, and it is not any numbered review item.

## Item 23: CLOSED this session

All six figures are now cited at first use in the body: Figure 1 in §2.1,
Figures 2 and 5 in §3.1, Figure 4 in §3.2, Figure 3 in §4.3, Figure 6 in §4.5.
Verified by grep over lines 1–1000, one citation each.
