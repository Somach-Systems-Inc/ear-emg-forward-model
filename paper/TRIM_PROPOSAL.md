# TRIM PROPOSAL — CHI 2027 word count (PROPOSAL ONLY, nothing applied)

Drafted 2026-08-24 (UTC). The manuscript body has NOT been modified for this file; every cut below is a proposal for Carl to rule on.

## Baseline and what the counter counts

`build_chi.py` reports **9613 countable words** (2026-08-24 build, after Table 1 was inserted and routed to Appendix B). CHI's guidance is 5,000-8,000; the desk-reject line is 12,000. The build's counter is deliberately conservative: it counts Table 4/5 captions (287 words) and Table 4/5 pipe-table bodies (378 words) that CHI's stated rule ("references, figure/table captions and appendices do not count") excludes in part or in full. So the same manuscript reads:

- 9613 on the build's conservative counter
- 9326 with table captions excluded (CHI's stated rule, read literally)
- 8948 with table bodies excluded too (how word processors and PCS-style counts usually treat tables)

HANDOFF §9 names §4.3, §4.7 and §4.8 as the trim candidates that are Carl's call. Everything below stays inside those three sections.

## Mechanism: every cut is CHI-only

No proposed cut deletes text from `PAPER1_humanized.md`, so the arXiv v3 render is untouched (HANDOFF §9: do not let a CHI edit leak into the arXiv bundle). Two build mechanisms cover everything here, both already in `build_chi.py`:

- **Move**: add the paragraph's prefix to `SPEC[...]["appendix"]`; the paragraph moves whole to Appendix C, which CHI's count excludes. Nothing is destroyed.
- **Replace**: a condensed paragraph in `paper/chi/` substitutes the original in the CHI render only (`SPEC[...]["replace"]`). Used where a paragraph cannot move whole because it carries a figure's first citation.

Constraint respected throughout: a paragraph carrying a figure's FIRST citation cannot move to the appendix (the build refuses out-of-citation-order placement). That pins §4.3's Figure 5/6/7/8 paragraphs and §4.8's Figure 10/11 paragraphs to the main text; those are trimmed by replace, or kept.

## Tier 1 — whole-paragraph moves to Appendix C (net −850 words)

### §4.3 (173 words)

**Move (52 words).** Rationale: a literature aside; the decomposition itself already makes the point that limb geometry cannot separate the two terms.

> Limb studies cannot make this separation, because adding a fat layer changes
> material properties and source-to-electrode distance together (Kuiken et al.
> 2003). A labelled head model can, because conductivity is changed with geometry
> held exactly fixed. The limb geometry cannot support that comparison at all, and
> here it costs one additional solve.

**Move (28 words).** Rationale: a transitional sentence whose content is restated by the per-muscle numbers around it (and by Table 3 row 9 in Appendix B).

> Applied to the three muscles whose gaps come closest to zero, temporalis,
> sternocleidomastoid and lateral pterygoid, the same decomposition returns a
> modest term whose sign varies between them.

**Move (93 words).** Rationale: the per-muscle sign detail duplicates §3.3 and Table 3 row 9 (Appendix B), which report the same numbers with the same caveat.

> For temporalis the contrast acts against the gap, not for it: removing it
> would enlarge the gap from −3.801 to −4.923 dB. The direction is worth stating
> because it is the opposite of the intuitive reading, the tissue contrast is not
> what produces temporalis's proximity to zero; it is part of what holds it there.
> It does not change the verdict, which is set by the matched−count interval and
> not by this term. For sternocleidomastoid and lateral pterygoid the contrast acts
> with the gap, supplying 21.0 and 17.4 per cent of it respectively.

### §4.7 (441 words moved, +36 for three pointer sentences left behind)

Each move leaves a one-line pointer in the main text (the build's `insert_after`), e.g. "The magnitude, per-muscle envelopes and source files are given in Appendix C." — counted at ~12 words each below.

**Move (138 words).** Rationale: the mesh-realisation magnitudes duplicate Table 3 row 10 (already Appendix B) and the three named CSVs; the limitation survives as a pointer sentence.

> **Mesh realisation is wider than four of the reported margins.** Term 10 of the
> error budget is a rebuild of the same nominal mesh, and it moves per-muscle gaps
> by up to 1.554 dB. Four verdicts have envelopes comparable to that: masseter
> (+1.20 to +2.22), medial pterygoid (+0.86 to +1.33), sternocleidomastoid (−2.53
> to −0.97) and lateral pterygoid (−3.61 to −1.53). Medial pterygoid's envelope
> sits inside it entirely, so that verdict in particular should not be relied on
> until the term is characterised over several rebuilds. The five labial verdicts
> span 8.11 to 22.40 dB and are unaffected, so the study's headline result does
> not depend on this term. It is listed as unquantified rather than bounded
> because one realisation pair is not a distribution. The rebuild comparison is
> `results/04w_control_mesh_realisation.csv`, the refinement comparison
> `results/04w_mesh_convergence.csv`, and the estimator check
> `results/04x_estimator_stability.csv`.

**Move (126 words).** Rationale: single-subject transferability nuance; §4.2 and §4.3 carry the transfer argument in the main text.

> MIDA is a single subject, and between-subject variance in muscle geometry,
> adipose thickness and pinna position cannot be estimated from one head. The
> adipose decomposition narrows what that means, but unevenly, and the unevenness
> is itself informative. The labial group and temporalis are carried by geometry,
> which is comparatively conserved between individuals; sternocleidomastoid and
> lateral pterygoid draw 21.0 and 17.4 per cent of their gap from the conductivity
> contrast, so of the three muscles nearest zero they are the two whose position
> is most dependent on tissue properties, not on geometry, and the two whose gaps
> should be expected to move most with subject adiposity. This is a reason to
> expect differential generalisation, not a demonstration of any of it. Only a
> second anatomy demonstrates that.

**Move (91 words).** Rationale: the inferior-boundary detail is quantified in §3.4, which stays; this paragraph restates it with the direction argument.

> **The inferior boundary is an unquantified limitation whose bias runs against
> the ear.** A neck-extended mesh was built specifically to measure it and did not
> conserve charge, so the pre-committed decision rule was recorded unexecuted, not
> applied or revised. What can be said is §3.4: excluding the two near-cut jaw
> sites moves the median gap by only −0.17 dB and flips no signs, and seven of ten
> muscles are immune by construction. The magnitude of the residual bias is
> unknown, not estimated, and its direction flatters this paper's own headline
> comparison.

**Move (86 words).** Rationale: site-level disclosure whose placement detail already lives in the §2.3 appendix block; the verdict-level consequence (direction runs against the jaw advantage) fits in a pointer.

> **One jaw site is withheld, and its omission runs against the reported jaw
> advantage.** `throat_scm` carries no coordinate because MIDA's
> sternocleidomastoid is truncated by the inferior cut plane, which biases its
> centroid posteriorly, so no defensible automatic placement exists (§2.3). It is
> the jaw site nearest the ear montage, so a jaw montage carrying it would be
> compared from a position closer to the retroauricular sites than any jaw site
> actually used. The direction of that omission is toward a smaller jaw advantage
> than is reported.

### §4.8 (272 words)

**Move (78 words).** Rationale: the mechanics of the three corrections restate Methods machinery (§2.4, §2.5, §3.1) that is still in the main text.

> Three corrections, each motivated by a different defect, each moving the
> estimate the same way. Reporting the field magnitude instead of the lead field
> projected onto a source orientation overstates coupling, because the magnitude
> is the maximum over orientations. Comparing the best of fourteen candidate sites
> against the best of four rewards electrode density, not placement. And assuming
> a fibre direction rather than deriving one from the label volume permitted a
> claim the derived field does not support.

**Move (40 words).** Rationale: commentary on the corrections, not a result; safe in Appendix C.

> None of these is exotic. Each is the kind of simplification a forward-modelling
> study makes for defensible reasons, and each individually shifts the estimate by
> around a decibel. Their product is the difference between a 3.92 dB advantage and
> none.

**Move (94 words).** Rationale: the monotone-vs-probative epistemology aside; the load-bearing fact (the final step was pre-committed, §2.8) is stated in the sentence kept in [4] and in §2.8 itself.

> Two features of this sequence are worth separating, because only one of them is
> evidence. The **monotone** drift, every correction moving the same way, is
> suggestive but not probative; corrections that each remove an optimistic
> assumption will tend to move one way by construction. What is probative is that
> the **final** step, the one that crosses zero, removes an assumption instead of
> adding one, and was pre-committed (§2.8) before the derived field existed. We do
> not treat an effect as established when the assumption holding it up is one the
> anatomy itself can replace.

**Move (60 words).** Rationale: motivation for reporting the cascade; the cascade itself (table, Figure 10, Figure 11) stays.

> We report this because the intermediate results were not obviously wrong. Each
> was internally consistent, cleared its measurement floor, and reproduced an
> a-priori anatomical prediction, the three muscles that appeared to favour the
> ear are the three whose attachments sit at or near the temporal bone, which is
> what one would predict, and which is what made the result convincing.

## Tier 2 — sentence-level replaces in §4.3 (−142 words)

These two paragraphs carry Figure 6's and Figure 8's first citations and cannot move whole. A condensed replacement file in `paper/chi/` drops the sentences below and keeps everything else, including the figure citations. Carl approves the replacement wording before it is used.

**From §4.3 [the material-share paragraph], cut (35 words)** — the leave-one-out robustness mechanics; the CSV pointer preserves the audit trail, and the headline ρ stays:

> At n = 7 a single muscle could carry that
> relationship, so it was tested: dropping each muscle in turn leaves ρ between
> −0.928 and −0.986 and p below 0.01 in all seven cases
> [`results/04t_correlation_robustness.csv`];

**Same paragraph, cut (24 words)** — a second statement of the cancellation already explained two sentences earlier:

> The same cancellation makes a uniform magnitude
> offset invisible in every ratio reported here; it turned up here where we had
> not expected it.

**From §4.3 [the Figure 8 paragraph], cut (52 words)** — the worked distance example restates what Figure 8 draws:

> Orbicularis oris sits 45 mm from the jaw electrode and 141 mm from the ear
> electrode, and the jaw is 13.5 dB louder there; temporalis sits on the far side
> of the crossover, 116 mm from the ear electrode against 155 mm from the jaw, and
> the ear is 4.4 dB louder.

**Same paragraph, cut (31 words)** — scope guard also stated in Table 4's caption ("is not a montage recommendation"):

> The figure plots |E| for
> single electrodes, not the projected lead field for the full montages, so it
> carries the mechanism and not the verdicts, which remain those of Table 4.

## Tier 3 — further cuts if the conservative counter itself must read ≤8,000 (−304 words)

I recommend stopping after Tier 2 (see the ledger). If Carl wants the build's own conservative number at or under 8,000, these are the next cuts in order of least damage:

**§4.7 move (110 words)** — the suprahyoid-absence limitation; the strongest honest limitation in the paper — I would keep it in the main text, which is why it is Tier 3 and not Tier 1:

> **Ten of eighteen muscles are modelled, and the two carrying the strongest
> version of the anatomical argument are not among them.** MIDA does not
> individually segment the suprahyoid group or the tongue. Posterior digastric and
> stylohyoid, the two muscles that anchor at the mastoid notch and styloid
> process, and that motivated the retroauricular hypothesis in the first place,
> are therefore absent from the per-muscle comparison. The model is silent exactly
> where the a-priori argument was strongest, the muscles whose attachments most
> directly motivated a retroauricular montage are the ones it cannot test, and the
> spatial sensitivity field reported over the pooled compartments is a partial
> substitute, not an equivalent one.

**§4.7 move (56 words)** — static geometry:

> **Static geometry.** The model is solved on a single anatomical configuration.
> Articulation moves the tongue, opens and closes the oral cavity and alters the
> airway, all of which change the volume conductor during the task being measured.
> Nothing here quantifies that, and the jaw montage sits closer to the moving
> structures than the ear montage does.

**§4.7 move (30 words)** — fibre-orientation pointer; §2.5 states the same bound:

> Fibre orientation is bounded, not known (§2.5). A fibre tensor reaches two of
> ten segmented muscles, and rows without one are reported as not applied and not
> as zero change.

**§4.8 move (56 words)** — the stage table duplicates the cascade panel Figure 10 draws with intervals:

> | Stage | Temporalis gap |
> |---|---|
> | field magnitude, best of 14 ear sites | −3.92 dB |
> | projected onto source orientation | −3.31 dB |
> | matched electrode counts, four sites each | −2.57 dB, interval [−3.31, −0.03] |
> | derived per-voxel fibre field | **−1.15 dB, interval [−1.45, +5.46] spans zero** |

**§4.3 replace, cut (52 words)** — the masseter exception; a real finding, listed last for that reason:

> For nine of the ten muscles the closer electrode is the louder
> one; the exception is masseter, where the ear electrode is nearer by 1.9 mm and
> the jaw is nonetheless 4.1 dB louder, and it is the only muscle in the set whose
> ordering is decided by something other than distance.

## Ledger

| Step | Cut (words) | Conservative counter | Captions excluded (CHI's rule) | Captions + table bodies excluded |
|---|---|---|---|---|
| baseline (2026-08-24 build) | — | 9613 | 9326 | 8948 |
| after Tier 1 | −850 | 8763 | 8476 | 8098 |
| after Tier 2 | −142 | 8621 | 8334 | 7956 |
| after Tier 3 | −304 | 8317 | 8030 | 7652 |

**Recommendation: Tier 1 + Tier 2.** That lands at 8,621 on the conservative counter and 7,956 ≤ 8,000 under the reading that excludes table captions and bodies. Tier 3 additionally brings CHI's stated-rule reading (captions excluded, table bodies counted) to 8,030 — 30 words short of the line, and any one further Tier 2-style sentence cut closes it — at the cost of moving one limitation I would rather keep visible. Reaching 8,000 on the conservative counter using only these three sections would further require gutting §4.8's remaining spine (the cascade opener and the two figure paragraphs); I advise against, and note the desk-reject line (12,000) is not in play on any reading.
