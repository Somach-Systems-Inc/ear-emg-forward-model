# Referee report

**Manuscript:** "Jaw and retroauricular electrode montages couple to different
speech articulators: a volume-conductor model in a detailed head anatomy"
**Journal:** Journal of Neural Engineering
**Recommendation:** Major revision. Not publishable in present form.

---

## Summary judgement

The underlying computation is probably sound and parts of the reporting
discipline are better than most submissions I see: the electrode-meshing floor is
measured rather than asserted, rows without a fibre tensor are marked NOT APPLIED
rather than zero, and the inferior-boundary problem is disclosed rather than
buried. I want to be clear that I am not questioning the arithmetic.

I am questioning whether this is one document. It is not. The Introduction
reports a result the Results section no longer contains. Five of six figures are
never cited. The inferential term the paper's two most important claims depend on
("statistic A") is never defined. Two sections still contain instructions
addressed to the author, and the file ends with a block of assembly notes listing
what is missing before submission. A referee cannot certify claims that the
document does not internally agree on.

Beneath the assembly problems there are four substantive challenges the authors
must answer: the novelty claim against HArtMuT is untested and partly refuted by
the paper's own §3.3; the orientation-conditioning procedure is applied
asymmetrically in the direction that saves results; the error budget contains a
row whose stated bound its own numbers contradict; and the truncation limitation
is disclosed for electrodes but not for the source that most depends on it.

---

## MAJOR

**1. The Introduction states a result the Results section contradicts.**

> "Seven of the ten articulators couple more strongly to the jaw montage and
> three couple more strongly to the ear" (§1)

Table 4 classifies masseter and medial pterygoid as "no resolvable preference",
so the Results support five, two and three, not seven and three. This is a
leftover from a point-estimate framing that §3.1 replaced. It is the last
paragraph of the Introduction and therefore the sentence most readers will carry
into the paper.

**2. Two more stale numbers from the same framing survive in the Discussion.**

> "the jaw wins by 10 to 23 dB" (§4.1)
> "the model says the ear costs 10 to 23 dB and no electrode position recovers
> it" (§4.4)

§3.1 and §3.3 both give the labial range as 8.2 to 21.9 dB. The Discussion is
quoting the withdrawn point estimates (10.37 and 22.78).

**3. A cross-reference points at a section that says the opposite.**

> "And `medial_pterygoid` remains borderline (§3.1)." (§4.4)

§3.1 does not describe medial pterygoid as borderline. It says the muscle shows
"no resolvable montage preference" and gives three independent reasons it
supports no directional claim. "Borderline" belonged to the withdrawn +0.62 dB
result.

**4. The Discussion asserts per-site results the Results section no longer
reports.**

> "its best site is the most superior one ... its best site is the
> posterior-inferior one ... its best site is the most anterior ear position"
> (§4.2)
> "contamination at `cg01` is not the same mixture as contamination at `cg08`"
> (§4.5)

Table 4 was rewritten to report a median gap and a percentage, dropping the
best-jaw and best-ear columns. The strings `cg01` and `cg08` appear nowhere in
§3. Two entire Discussion subsections rest on findings that have been deleted
from Results. Either restore the per-site columns or delete §4.2's second
paragraph and §4.5's second sentence.

**5. "No fibre direction exists" is a universal claim from a 200-point sample.**

> "no fibre direction exists at which a retroauricular electrode competes for
> them" (Abstract, repeated verbatim in §3.1)

Two hundred directions over a hemisphere gives roughly 11 degrees of
nearest-neighbour spacing. The paper's own temporalis analysis identifies a
reversal region occupying 8 of 200 samples, which establishes that reversal
regions at exactly the scale the sweep can barely resolve do exist in this model.
A narrower one in a labial muscle would be missed. The licensed statement is
"none of 200 sampled directions", and that is what the Abstract must say. This is
the single strongest sentence in the Abstract and it is not earned.

**6. "Best ear site" is an argmax over 14 positions against 4, and it is not a
montage.**

> "A retroauricular montage should read jaw-closing and head-stabilising
> activity well" (§4.4)

Table 4 excludes near-cut jaw sites, leaving four jaw positions against fourteen
ear positions (four retroauricular plus ten cEEGrid). A max over fourteen draws
beats a max over four under per-site noise of 0.27 dB by roughly 0.2 dB before
any physics, and the selection asymmetry is never addressed.

The deeper problem is that no physical device achieves the three reported ear
gaps at once. Figure 2 puts temporalis's best contact at cg01, sternocleidomastoid's
at the post-lobule and cg08 region, and lateral pterygoid's at pre-tragus. §4.5
concedes this ("their best positions differ"). §4.4 then issues a design
recommendation as if a single montage realised all three. Either report the gap
for a fixed, named electrode set, or restate §4.4 as a per-position statement.

**7. The novelty claim against HArtMuT is untested, and §3.3 argues against it.**

> "No published forward model treats facial and cervical muscle as both the
> generator and its own anatomically resolved conducting compartment, and none
> has been used to ask where a sensor should be placed rather than what a sensor
> is contaminated by." (§1)

This decomposes into two claims, and neither is a methodological contribution as
written.

The second half ("none has been used to ask where a sensor should be placed") is
a statement about research question, not about method. A lead field does not know
what it will be used for. For a methods journal this is an application, not a
novelty.

The first half is a conductivity assignment within one compartment, and the paper
never measures what it changes. This is conspicuous because the paper runs
exactly the right kind of experiment elsewhere: §3.3 re-solves with adipose set
to muscle conductivity on identical geometry to isolate a material effect. The
same design applied to the actual novelty claim (set muscle to scalp
conductivity, reproducing HArtMuT's stated simplification, and re-solve) is not
run. Without it the claim is asserted.

Worse, §3.3's result predicts the control would come out against the authors:

> "For the labial group, where the jaw wins by 8.2 to 21.9 dB, the contrast
> accounts for 0.6 to 13.3 per cent of the gap. For the three muscles the ear
> wins it accounts for 17 to 21 per cent" (§3.3)

If tissue-conductivity contrast contributes at most a fifth of any gap and the
remainder is geometry, then a model with correct geometry and a homogeneous
scalp, which is to say HArtMuT, should recover the qualitative complementarity
result. The paper's own mechanism decomposition undermines its own novelty claim.

Add to this that §2.5 concedes the fibre-axis method is HArtMuT's ("Deriving
fibre directions by principal component analysis on MIDA's own segmentation is
not novel here"), that the head model is the same, and that Harmening et al. 2022
appeared in this journal. The remaining novelty surface is thin. I would accept
either of two repairs: run the homogeneous-scalp control and quantify what the
muscle compartment buys, or reframe the contribution honestly as the first
application of an existing class of model to sensor placement, with the
electrode-placement methodology and the orientation sweep as the contribution.
The current framing will not survive review by the HArtMuT authors, who are the
obvious referees.

**8. The anisotropy null is stated over ten muscles and measured on two.**

> "**The isotropy assumption does not measurably affect any site-to-site
> ratio.**" (§3.2)

"Any" quantifies over all ten. Figure 4's caption explicitly refuses that
inference:

> "Rows without a tensor are labelled **not applied**, not zero: they were never
> varied, so no null result was measured for them." (Fig 4 caption)

§3.2 reports gap changes for four muscles. Six have no reported gap change at
all. For those six this is absence of evidence, and the figure caption says so
while the Results text denies it. The claim must be scoped to the muscles
actually varied.

**9. §3.2 reports gap changes for two muscles that carry no tensor, and never
explains how.**

> "changes the jaw-versus-ear gap by ... +0.137 dB for temporalis and +0.036 dB
> for lateral pterygoid" (§3.2)

§2.5 states the tensor reaches sternocleidomastoid and medial pterygoid only, and
Figure 4 renders temporalis and lateral pterygoid as NOT APPLIED. Presumably
these are second-order effects of altering neighbouring compartments'
conductivity on the global field, which would be a legitimate and interesting
observation, but the paper never says so. As written, the text reports
measurements for rows the figure declares unmeasured.

**10. Figure 4's own subtitle contradicts the Results text.**

> Fig 4 subtitle: "every jaw-vs-ear GAP moves less than 0.09 dB, under the
> 0.27 dB floor"
> §3.2: "+0.137 dB for temporalis"

0.137 is not less than 0.09. One of these is wrong and both are in the submitted
package.

**11. Table 3 says the truncation bias is bounded; §4.7 says it is unknown.**

> Table 3, row 3: "unquantified; bounded by §3.4"
> §4.7: "The magnitude of the residual bias is unknown rather than estimated"

These cannot both stand. Moreover §3.4 does not bound what row 3 claims. §3.4
measures the effect of *excluding three electrodes near the cut face*. The
insulating face itself is present in every solve, including the four jaw sites
declared "clear of the cut" and every ear site. Removing electrodes from a
neighbourhood is not the same operation as removing a boundary condition from a
domain. The honest statement is §4.7's.

**12. Sternocleidomastoid is truncated by the cut face, and it is one of the
three ear results.**

> "MIDA's sternocleidomastoid is truncated at the cut face, which biases its
> centroid posteriorly, so no defensible automatic placement exists." (§2.3)

The paper withholds the `throat_scm` electrode for precisely this reason, then
retains sternocleidomastoid as a source compartment without comment. A posterior
centroid bias moves the source toward the mastoid, which is toward the ear
electrodes, so the bias runs in favour of the reported SCM ear advantage. Neither
§3.4 nor §4.7 mentions this. Platysma, also truncated inferiorly in any head
model cut at S = −116 mm, is likewise reported without comment at +8.84 dB.

The truncation discussion currently covers electrode proximity only. It must
cover source truncation, and for SCM specifically it must state which direction
the bias runs.

**13. The orientation constraint is derived where it hurts and asserted where it
helps.**

§2.5 explicitly refuses temporalis an axis:

> "for a sphincter (orbicularis oris), a fan (temporalis), a sheet (platysma,
> buccinator) or a multi-layered muscle (masseter, lateral pterygoid), a single
> axis is the wrong kind of description rather than merely an imprecise one.
> Those compartments remain isotropic in both conditions." (§2.5)

§3.1 then evaluates temporalis over a fan whose geometry appears nowhere in
Methods:

> "Temporalis is a flat fan running from the temporal fossa to the coronoid
> process with negligible medio-lateral component, and that cone is therefore
> unreachable. Evaluated across the fan itself the gap is −2.70 dB at the
> anterior, near-vertical fibres, −3.54 dB at mid-fan, and −4.60 dB at the
> posterior" (§3.1)

Three named fibre positions require a specified fan. Where is it defined? How
were anterior, mid and posterior chosen? Was the fan extracted from MIDA's label
63, or taken from anatomical description? The text reads as the latter, which
puts it in direct conflict with the paper's own stated placement principle:

> "An interactive picker was rejected because clicked coordinates cannot be
> regenerated from a clean checkout, reviewed in a diff, or defended in Methods."
> (§2.3)

This matters because the fan is the entire mechanism converting an unconstrained
96 % into "effectively unconditional", which is what the Abstract claims. A
hand-specified constraint set that rescues a result must be held to the same
standard as a hand-picked electrode.

**14. Left-right disagreement disqualifies one muscle and is reported as a result
for another.**

> medial pterygoid: "its two sides disagree in sign at that axis (+4.21 dB right,
> −2.10 dB left), which is a third independent reason it supports no directional
> claim" (§3.1)
> sternocleidomastoid: "−5.06 dB on the right and −2.52 dB on the left"
> (Abstract and §3.1)

Medial pterygoid's axis passes the mirror-symmetry test at |dot| = 1.000, better
than sternocleidomastoid's 0.98. Its sides disagree in sign; SCM's disagree by a
factor of two. The paper treats the first as disqualifying and reports the second
in the Abstract without flagging that a 2.5 dB left-right spread on a 5 dB effect
is the same class of instability. State a single pre-specified rule for when
bilateral disagreement voids an at-axis estimate, and apply it to both.

**15. Lateral pterygoid cannot carry the weight §4.4 and §4.6 put on it.**

> "favours the ear in 69.0 % of directions (median −1.85 dB, range −7.70 to
> +6.78)" (§3.1)

The maximum jaw-favouring value over the sweep is +6.78 dB, which is 3.7 times
the magnitude of the median ear advantage. §3.1 correctly calls this "genuinely
conditional". §4.6 then makes it a falsifiable prediction for a physical
experiment, and the Abstract's Significance paragraph folds it into the design
claim. A result whose sign flips over a third of orientation space and whose
opposite-sign extreme dominates its own median is not a basis for a device
recommendation.

**16. The n = 1 generalisation argument is asserted and contradicted by Table 3.**

> "The labial group and temporalis are carried by geometry, which is
> comparatively conserved between individuals" (§4.7)

No citation, no data, and one head. Table 3 row 7 states the opposite posture:
"Single anatomy | MIDA is one subject | yes | unknown | not quantifiable from one
head". If the between-subject effect on ratios is unknown, transferability cannot
be ranked between muscle groups.

The argument also contains a non sequitur. That a margin arises from geometry
rather than tissue contrast says nothing about how variable that geometry is
between subjects. Pinna position, mastoid prominence, mandibular ramus height and
the temporalis-to-cEEGrid distance are exactly the quantities that vary most
across heads, and the ear margins are 2 to 5 dB. Either cite population data on
the relevant anatomical variances or reduce §4.7 to a hypothesis with no ranking.

The final sentence ("Only a second anatomy demonstrates that") is the correct
posture. The two paragraphs above it are not.

**17. The 21 % figure and the claimed 5.06 dB advantage use different
denominators.**

> "sternocleidomastoid and lateral pterygoid draw 21 and 17 per cent of their
> advantage from the conductivity contrast" (§4.7)

§3.3's table gives sternocleidomastoid "as modelled −1.958", which is the
unconstrained sweep median. 0.411/1.958 = 21 %. But the advantage the paper
claims for this muscle, in the Abstract and in §3.1, is −5.06 dB at the estimated
axis, against which the same 0.411 dB is 8 %. The generalisation argument in §4.7
and the "least likely to transfer" conclusion are both built on the larger
number. Decide which statistic is the muscle's advantage and compute the
decomposition against it. The same issue applies to temporalis, where the
decomposition is computed on the sweep median (−3.801) while §3.1 argues the
correct values are the at-fan ones (−2.70 to −4.60).

**18. §4.3's correlation cannot be checked against anything in the paper.**

> "it correlates *negatively* with the adipose fraction of the muscle-to-skin
> path (Spearman ρ = −0.955, p = 0.001, n = 7): platysma sits at 0.650 fat
> fraction and 0.6 per cent material share, while sternocleidomastoid sits at
> 0.225" (§4.3)

Table 2 contains neither platysma nor sternocleidomastoid. It lists nine
electrode sites whose targets are mandible, masseter, buccinator, hyoid bone,
temporalis and mentalis. The seven muscles "for which a layer profile exists" are
never named, the fat fractions appear in no table, and n = 7 out of 10 is a
selection whose rule is unstated. A reviewer is asked to accept a mechanistic
conclusion from a seven-point rank correlation whose seven points are not in the
manuscript.

**19. The sphere validation detected the error it exists to detect, and the paper
drops it.**

> "This is the only layer that can detect a uniform scale error, since no
> invariant computed on the head mesh can" (§2.6)
> "median RDM is 4.36 % and median MAG +4.40 %" (§2.6)

MAG +4.40 % is a uniform scale error of 4.4 %. The paper introduces the sphere as
the sole instrument capable of finding one, reports a positive finding, and says
nothing further about it. The ratio-cancellation argument may well dispose of it,
but that argument must be made where the number is reported, not left for the
reader to assume. RDM of 4.36 % is also on the high side for a four-layer sphere
and deserves comparison against published FEM pipelines.

Separately, state plainly what the sphere cannot validate: it has no muscle
compartment, no anisotropy, no electrode meshing and no truncation face, so it
tests none of the four features this paper's conclusions depend on.

**20. Table 3 row 8's stated bound is contradicted by its own numbers.**

> "| 8 | Delivered current | injected vs requested per solve | yes | bounded by
> row 6 | 0.887–1.075 × requested across 22 solves |"

0.887 to 1.075 is −1.04 dB to +0.63 dB, a spread of 1.67 dB. Row 6 is 0.27 dB.
The claimed bound is exceeded by a factor of six by the very range in the same
cell. §2.4 says "1 mA is injected between each electrode and a common reference"
and never states that fields are renormalised by delivered rather than requested
current. If they are renormalised, say so in §2.4 and the row becomes moot. If
they are not, this is a per-site, non-cancelling term larger than every ear
advantage except temporalis, and it invalidates the sternocleidomastoid and
lateral pterygoid results outright. This is the most serious single item in the
report and it must be resolved explicitly.

**21. §2.7's admission rule is violated by two rows of its own table.**

> "terms are admitted to the second column only when shown to vary per site"
> (§2.7)

Row 2 is marked "yes" for ratios with the value "requires a geometry decoupling
eccentricity from interface distance; not measured". Row 3 is marked "yes"
with "unquantified". Both were admitted by argument, not by demonstration. Either
restate the rule to permit argued admission, or mark these rows as suspected
rather than shown.

**22. The electrode count takes three different values across the submitted
package.**

> "Twenty-two electrode positions" (Abstract and §1); "All 22 positions" (§2.3);
> "22 solves" (§2.4); "all 22 production solves" (§2.5); "across 22 solves"
> (Table 3); "all 22 electrode positions shown" (Fig 1 caption)

Figures 2 and 4 render 21 columns: seven jaw, four retroauricular, ten cEEGrid.
Figure 3's legend gives n = 70 jaw and n = 140 retroauricular, which is 21 sites
across 10 muscles. Figure 1's own subtitle says "23 electrode positions". §3.4
says "all seven jaw sites", consistent with 21.

I can construct a reconciliation (21 recording sites, plus the contralateral
earlobe reference, plus the withheld `throat_scm`), but the manuscript never
offers one, and if the shared reference is one of the 22 then there were 21
solves, not 22. State the count once, define what is counted, and make the
figures agree.

**23. Five of the six figures are never cited in the body, and two tables are
not either.**

The only in-text figure mentions are "Figure 5" in §4.1 and "Fig 4" in §3.2, and
the latter is an editing instruction rather than a citation. Figures 1, 2, 3, 6
and Supplementary S1 have no in-text call-out anywhere. Tables 2 and 4 have none
either. JNE requires figures cited in sequential order. Figure 2 lost its
citation when §3.1 was rewritten (the sentence that carried it, naming the
site-by-muscle matrix, is gone). Figure 3 is not discussed anywhere at all, which
is notable given that its content, attenuation against distance for both arms, is
the direct evidence for §4.3's central claim that the mechanism is distance.

**24. Figure 5's caption describes a different figure.**

> "For each articulator, the difference between the best jaw site and the best
> retroauricular site, in dB. Negative bars are muscles the ear sees more
> strongly." (Fig 5 caption)

The figure is not bars. It is a min-max rule, an interquartile bar and a median
marker over 200 orientations, with a filled-versus-open marker distinction
carrying sign stability and per-muscle percentage annotations. None of that is in
the caption. The caption is the pre-sweep version and describes point estimates
the paper has withdrawn.

**25. Figure 6's caption promises overlays the figure does not contain.**

> "with the mastoid notch, hyoid greater horn and the corridor between them
> overlaid" (Fig 6 caption)

The figure's legend has three entries: Muscle (General) pooled suprahyoids, hyoid
bone, injection electrode (cg08). There is no mastoid notch and no corridor.
"The corridor between them" is a named anatomical structure introduced in a
caption, asserted as visible, absent from the figure and absent from Results. If
a mastoid-to-hyoid corridor is a finding, it belongs in §3 with a number attached.
If it is not, delete it.

The caption also says "for the retroauricular montage" while the figure shows a
single cEEGrid injection electrode, a distinction the paper maintains carefully
everywhere else (Figure 2 separates "Retroauricular" from "cEEGrid C-path").

**26. Figure 1's caption contradicts the figure, and the figure concedes a
rendering artefact.**

> "The face is masked above the orbital rim in accordance with the MIDA licence."
> (Fig 1 caption)
> "face cropped per MIDA licence clause 2.3.3: the anterior skin is removed, so
> the jaw electrodes sit against empty space rather than the chin they are placed
> on" (Fig 1 subtitle)
> "face cropped above S = 13.8 mm per licence 2.3.3" (Fig 6 subtitle)

Three incompatible descriptions of one mask. More importantly, the figure whose
job is to show where the electrodes are placed renders the jaw electrodes
detached from the anatomy, and says so. In the lateral panel the jaw markers
float in white space below and anterior to the model. This is the paper's only
placement figure and it cannot currently be used to verify placement. Mask the
skin texture rather than deleting the compartment, or add an unmasked inset
restricted to the mandible region.

**27. "Statistic A" is never defined, and two central claims depend on it.**

> "Under statistic A the correct statement is stronger and simpler" (§3.2)
> "statistic A: largest change to any gap is **−0.085 dB**" (Table 3, row 4)
> "a population differential across sites has no clean definition under
> statistic A" (Table 3, row 9)
> Fig 2 subtitle: "cells are the per-site orientation median (statistic B); a
> per-cell gap statistic does not exist, so Fig 5's per-orientation gap (A)
> cannot be shown here"

Neither A nor B appears in Methods. The A/B distinction is what licenses Figure 2
and Figure 5 to report apparently different quantities and what carries the entire
anisotropy null and the adipose decomposition. It has to be defined in §2, with
its formula, before §3 uses it.

**28. Two Results and Discussion subsections contain instructions addressed to
the author.**

> "**Fig 4's title and caption should follow.** The figure asks 'is the ear
> advantage robust to the isotropy assumption'; the answer is that the assumption
> does not resolve at all. Retitle to state the null, and note in the caption
> that the per-cell deltas shown are large" (§3.2)
> "Replaces: *'The ear's deficit against the labial group is geometric. The
> adipose–muscle conductivity contrast accounts for 0.6 to 13.3 per cent…'*"
> (§4.3)
> "State the correlation reversal. It is honest, it pre-empts a reviewer who
> computes the same thing, and it is the fourth appearance of the
> ratio-cancellation argument the paper is organised around." (§4.3)
> "The current text describes a robustness check that survives." (§3.2)

Roughly a third of §3.2 and §4.3 is editing scaffolding rather than manuscript
prose, and the actual claims sit inside block quotes with no antecedent. I am
being asked to review a draft that still contains its own revision notes,
including a note anticipating what I would do.

**29. The submitted file ends with a section titled "not part of the
manuscript".**

It lists withdrawn values, deleted sections, an incomplete SimNIBS citation,
"**Repo must be public** for §2.8's pre-registration citation to be checkable",
an undecided author affiliation, and an open question about whether §4.4 should
exist. It also states "**Figures 1, 3 and 6** do not exist yet", which is false;
all three are in the figure package I was given.

Two consequences beyond the obvious. First, §2.8's pre-registration claim and the
Data Availability statement both point at a repository the notes say is not
public, so neither is currently checkable. Second, the notes confirm that
material was removed rather than resolved, including the MAG discussion (item 19
above).

**30. The pre-registration is overstated in §4.2 and has a competing origin story
in §4.7.**

> §2.8 records the prediction as covering two muscles: "predicting strong
> retroauricular coupling for temporalis ('directly above ear') and
> sternocleidomastoid ('mastoid attachment')"
> §4.2 claims three: "The three muscles the ear wins on are the three whose
> attachments sit at or near the temporal bone. ... This was written down before
> the model was solved (§2.8)."

Lateral pterygoid was not pre-registered, and it is the weakest of the three.
§4.2 must say two of three were predicted.

Meanwhile §4.7 gives a third account of what motivated the hypothesis:

> "Posterior digastric and stylohyoid — the two muscles that anchor at the
> mastoid notch and styloid process, and that motivated the retroauricular
> hypothesis in the first place" (§4.7)

So the hypothesis was motivated by two muscles that are not modelled, registered
for two different muscles, and claimed in the Discussion for three. Pick one
account.

**31. The pre-registration mechanism does not support the weight placed on it.**

> "The prediction therefore precedes the measurement by a day and by the entire
> solve pipeline, and both commits are citable by hash." (§2.8)

A git commit date in a repository the sole author controls is author-settable and
is not a third-party timestamp. The interval is one day. The repository is not
yet public. §4.2 uses this to argue that the result "constrains how much of the
result can be an artifact of electrode placement choices", which is a strong
epistemic claim to rest on a self-attested commit date.

Either deposit the prediction with a third-party registry, or drop it to a plain
statement that the anatomical reasoning preceded the solve, without the
pre-registration framing. The anatomical argument is fine on its own merits and
does not need this.

**32. The paper's title and framing do not match its own conclusions.**

The title says "speech articulators". §4.4 concedes:

> "Sternocleidomastoid is a strong coupling to a muscle that may carry little
> speech information; the model says the ear sees it well, not that seeing it is
> useful." (§4.4)

Of the three muscles the ear wins, one is a masticatory muscle, one is a postural
muscle the paper itself says may carry no speech information, and one is
conditional. Nothing in the paper connects coupling magnitude to decodability, so
"reads ... well" and "loses ... almost entirely" are statements about lead-field
amplitude that the Introduction's silent-speech framing invites the reader to
interpret as statements about recoverable information.

The framing also drifts. The Introduction is about silent speech interfaces. §4.4
and §4.6 are about jaw-gesture detection, clench input and bruxism monitoring.
The assembly notes show the authors already know this and have not decided. It
needs deciding before review, because it changes what the contribution is.

**33. §3.3's heading asserts a binary its own section and §4.3 both refute.**

> Heading: "3.3 The gap is geometric, not a property of intervening tissue"
> §4.3: "the separation is narrower than a single figure would suggest, and no
> muscle in either group is unaffected"

§3.3 reports the contrast accounting for up to 13.3 % of a labial gap and 17 to
21 % of two ear gaps, and reversing sign for temporalis. That is not "not a
property of intervening tissue". §4.3's more careful wording is the correct one;
the heading is from the withdrawn 0.33 dB framing.

---

## MINOR

**34. "The labial group" has five members in Results and four in Discussion.**

> §3.1: "Orbicularis oris, buccinator, mentalis, depressor anguli oris and
> platysma"
> §4.6: "the labial group — mentalis, depressor anguli oris, buccinator,
> orbicularis oris"

Platysma is in one list and not the other. Figures 2 and 4 group platysma under
"cervical", not "labial", so the paper's own figures disagree with §3.1's
membership. Define the group once.

**35. RDM and MAG are never expanded, and RDM appears first in the Abstract.**

> "median RDM 4.36 % over 120 sources" (Abstract)

Standard in the forward-modelling literature, but a structured abstract should
not open an acronym it never defines, and MAG appears exactly once with no
definition and no interpretation.

**36. The 0.27 dB quantity has three names and is used before it is defined.**

> §2.2: "the measured noise floor of 0.27 dB"
> §3.2: "the 0.27 dB measured electrode-meshing floor"
> Fig 5 caption: "the measured electrode-meshing floor"

First use is in §2.2, five sections before §2.7 and Table 3 establish what it is
and that it is per-site rather than noise in the usual sense. Define it in §2.2 or
forward-reference it.

**37. The 18-muscle target set is never enumerated.**

> "Ten of the eighteen articulator muscles in our target set" (§2.1)

§2.1 names ten segmented and seven pooled, with "digastric (both bellies)"
ambiguous as to whether it counts once or twice. The reader cannot reconstruct
eighteen. List the set.

**38. The temporalis reversal cone is characterised below the sweep's resolution.**

> "The eight reversing directions form a cone of median half-width 12.1° about
> [−0.504, −0.555, +0.661], with a minimum |R| of 0.324, so every one lies at
> least 19° out of the sagittal plane." (§3.1)

Two hundred hemisphere samples give roughly 11 degrees of nearest-neighbour
spacing, so the cone's boundary is located to within about one sampling interval
and the claimed 19-degree clearance is under two. No dispersion is given for the
12.1 degrees. Either raise the sampling density around the reversal region or
state the resolution limit alongside the clearance.

**39. Convergence exponent is reported to a precision the paper says is
meaningless.**

> "giving a convergence exponent p = 0.980 ... three data points fitted with
> three free parameters is an exact fit by construction, so p is determined
> algebraically and the residual carries no goodness-of-fit information." (§2.6)

The candour is welcome; the three significant figures are not. Report p ≈ 1, or
add mesh densities so the fit is over-determined.

**40. Figure annotations round differently from the text.**

Figure 5 annotates 36 % and 72 % where §3.1 gives 35.5 % and 72.5 %. Figure 2's
subtitle gives the colour range as "-27..0" where its caption says "−28 to 0 dB".

**41. "Every reported quantity is a ratio" is not true.**

> "Every reported quantity is a ratio, and the uncertainty budget is assembled
> from measured terms." (Abstract)

Table 2 reports millimetres, §2.1 reports voxel counts and cubic millimetres, and
§2.6 reports RDM and MAG percentages against an external standard. The second
half is also overstated: Table 3 rows 2, 3 and 7 are explicitly not measured.

**42. The Abstract's results paragraph lost its heading.**

Objective, Approach and Significance carry bold heads. The paragraph beginning
"The two montages are complementary rather than ranked" does not. JNE's
structured-abstract format requires all four.

**43. The Abstract omits the adipose decomposition entirely.**

§3.3 and §4.3 together are among the longest passages in the paper, Table 3 row 9
is its longest cell, and the mechanism separation ("a comparison the limb geometry
structurally cannot support") is arguably the paper's most defensible original
contribution. None of it reaches the Abstract, which spends its results paragraph
on orientation conditioning instead.

---

## EDITORIAL

**44. Seven of nineteen references are never cited in the text.**

De Luca 2011, Kappel 2019, Maksymenko 2021, Meiser 2024, Mesin 2020, Sato and
Kochiyama 2023, and Wand and Schultz 2011 appear only in the reference list.
Maksymenko (numerical surface EMG modelling) and Mesin (surface EMG crosstalk
review) are direct prior art that the §1 novelty claim is obliged to engage with;
listing them uncited is worse than omitting them, because it demonstrates the
authors know they exist. Kappel 2019 is an ear-EEG forward-model paper and the §1
claim about the ear-EEG literature currently rests on Yarici 2023 alone.

**45. SimNIBS is named eight times and never cited.**

Reference 16 reads "Thielscher, A., et al. SimNIBS. *[complete citation before
submission]*". The solver is load-bearing for every number in the paper.

**46. The manuscript opens with a production note.**

> "*Draft manuscript assembled 2026-08-05. Methods from `paper/METHODS.md`;
> Introduction and Discussion from `paper/INTRO_AND_DISCUSSION_draft2.md`;
> Results from `paper/RESULTS_AND_CAPTIONS.md`. Working-record material
> (withdrawn values, in-session corrections) has been moved out; it remains in
> `paper/METHODS_LOG.md`.*"

The assembly date also postdates the figure render timestamps.

**47. Table 2's caption is a methods derivation and promises data the table does
not contain.**

> "Millimetres per MIDA tissue along the ray from each electrode through the full
> thickness of its target. *Target thickness traversed* is summed from
> `results/02_layer_profile.csv` over the target label."

The table has two numeric columns, not a per-tissue stack. The derivation and the
repository paths belong in §2. "Canonical site" is undefined. The table also
mixes `pre_tragus`, which §2.3 defines as a retroauricular position, into what
otherwise reads as a jaw-site table, with no other ear site present.

**48. Table 1 is described in the caption but not included in the manuscript.**

The caption points at `results/table1_conductivities.csv`. Table 1 is cited three
times in §2.1 and §2.2 as the authority for every conductivity in the model. A
referee cannot check any conductivity assignment.

**49. "Flip cone" appears in Table 4 without definition.**

> "temporalis | -3.80 | 96.0 | ear, effectively unconditional (flip cone
> unreachable)"

Defined only implicitly by §3.1's prose, and Table 4 is never cited from the body.

---

## Required before this can be reconsidered

In priority order. Items 1 through 4 are conditions of acceptance; the rest are
required revisions.

1. **Resolve Table 3 row 8** (item 20). Either state in §2.4 that lead fields are
   renormalised by delivered current, or quantify the per-site residual. As
   written, a 1.67 dB non-cancelling per-site term is larger than two of the three
   ear results. Nothing else in the paper matters until this is settled.

2. **Test the novelty claim or reframe it** (item 7). Run the homogeneous-scalp
   control and report what the muscle compartment changes, or restate the
   contribution as an application of an existing model class with the placement
   methodology and orientation sweep as the novelty. The current §1 wording will
   not survive.

3. **Put the temporalis fan in Methods, derived from MIDA** (item 13). The
   "effectively unconditional" claim in the Abstract depends entirely on a
   constraint set that appears for the first time in Results and is not derived
   from the model. Either extract it from label 63 and report how, or withdraw the
   claim to "96 % of sampled directions".

4. **Reconcile the Introduction, Results and Discussion** (items 1 to 4). The
   seven-and-three claim, the 10-to-23 dB range, the "borderline" medial
   pterygoid, and the best-site claims in §4.2 and §4.5 are all from a withdrawn
   framing. As it stands a reader cannot determine what the paper claims.

5. **Scope the anisotropy null to the muscles varied** (items 8 to 10), fix the
   Figure 4 subtitle, and explain how muscles with no tensor show gap changes.

6. **Extend the truncation discussion to truncated sources** (item 12), naming
   sternocleidomastoid explicitly and stating the direction of the bias.

7. **Define statistic A in Methods** (item 27) before anything in §3 uses it.

8. **Cite every figure and table in the body, in order** (item 23), fix the
   Figure 5 and Figure 6 captions to describe the figures that exist (items 24 and
   25), and re-render Figure 1 so electrode placement is verifiable (item 26).

9. **Settle the electrode count at one value** across text and figures (item 22).

10. **Remove the editing scaffolding and the assembly notes** (items 28 and 29),
    complete the SimNIBS citation, and either cite or remove the seven uncited
    references (items 44 and 45).

11. **Include Table 1** (item 48).

I would review a revised version. The mechanism decomposition in §3.3 and §4.3,
the measured electrode-meshing floor, and the NOT APPLIED discipline are real
contributions and I would like to see them in a document that supports them.
