# UNVERIFIED wording — title, §4.4, §4.6, and the cascade paragraph

> **APPROVAL UNVERIFIED. DO NOT APPLY.** This file previously read "approved by
> Carl 2026-08-06". That date had not occurred when the file was committed, and
> Carl does not recall approving it. The attribution is stripped and deliberately
> NOT re-dated: re-dating would launder an invented date into a clean record of
> an approval nobody confirmed. Nothing here enters the manuscript until Carl
> re-reads it.
>
> **Measured against the current manuscript: 23 of 29 prose probes from this
> file's proposed text are already present (79%).** This is the most heavily
> applied of the four: the paper's TITLE, §4.4, §4.6 and the new §4.8 all came
> from here. Reverting is a live option only Carl can rule on.

Written by Claude (the assistant). Written after
the matched-count interval on the derived fan crossed zero and temporalis became
no resolvable preference. §4.4 and §4.6 are written from scratch rather than
reworded — neither survives in any form that mentions temporalis.

---

## Title — the current one is now false

*"Jaw and retroauricular electrode montages couple to different speech
articulators"* asserted complementarity. There is none: the jaw montage wins
every resolvable comparison. Replace with:

> **Canonical jaw electrode sites outperform retroauricular sites for every
> resolvable speech articulator: a volume-conductor model with orientation and
> electrode-count controls**

Declarative, states the finding, and the subtitle signals that the controls are
the methodological content.

---

## §4.4 — replacement, device design

> The design statement this supports is a negative one with a number attached.
> A retroauricular montage loses the labial group by 9.0 to 21.2 dB, and buys
> nothing reliable in return. No articulator in this study favours the
> retroauricular montage once source orientation and electrode count are
> controlled.
>
> That is more useful to a device team than a small positive margin would have
> been. An ear-worn form factor is chosen for wearability, not for signal, and
> the question a designer needs answered is what it costs. The answer is that it
> costs most of the anterior articulators outright and returns nothing
> measurable — not that it trades one muscle group for another.
>
> Three apparent advantages did not survive. Temporalis, sternocleidomastoid and
> lateral pterygoid each showed a retroauricular advantage at the unmatched
> comparison, and each dissolved: their gaps depend on which four electrodes a
> device carries rather than on the anatomy (§3.1). A device built around any of
> them would be built on a site-selection lottery. Anyone reading a
> retroauricular advantage off a model that does not match electrode counts
> between montages should expect the same.
>
> What does transfer is that placement method matters more than the marginal
> advantages did. A four-site cluster chosen by anatomical target outperforms an
> arbitrary four-site draw from the same candidates (§3.6). For a device
> constrained to a few contacts, where they go is the lever that remains.

---

## §4.6 — replacement, prediction for a companion experiment

> This model makes a falsifiable prediction for a physical experiment recording
> both montages simultaneously, and the prediction is a null.
>
> An eight-channel rig split four jaw and four retroauricular, recording
> identical utterances, should show **no articulator for which the
> retroauricular channels carry more information than the jaw channels**, and
> should show the labial group degrading sharply at the ear. A result finding a
> reliable retroauricular advantage for temporalis, sternocleidomastoid or
> lateral pterygoid would **falsify this model**, and would most likely indicate
> that a real muscle's fibre geometry differs from the field derived here, or
> that mechanical or acoustic coupling contributes signal this electrical model
> does not represent.
>
> Stating the direction in advance matters, because the alternative reading is
> available and would be unfalsifiable. Had the prediction been "the ear retains
> temporalis-driven gestures", an experiment finding no advantage could be
> explained as insufficient sensitivity rather than as evidence against the
> model. As stated, the null is the prediction and a positive finding is the
> refutation.

---

## §4.8 — new section: how the retroauricular advantage dissolved

Place at the end of the Discussion, before Limitations. This is the part of the
paper most likely to be read by people building similar models.

> An apparent retroauricular advantage was present at every intermediate stage
> of this analysis and survived to the point of being written into a draft.
> It did not survive the controls, and the way it disappeared is worth reporting
> because each control is individually standard and none was applied in response
> to the result.
>
> | Stage | Temporalis gap |
> |---|---|
> | field magnitude, best of 14 ear sites | −3.92 dB |
> | projected onto source orientation | −3.31 dB |
> | renormalised by measured delivered current | −2.57 dB |
> | derived per-voxel fibre field | −1.15 dB |
> | matched electrode counts | interval spans zero |
>
> Four corrections, each motivated by a different defect, each moving the
> estimate the same way. Reporting the field magnitude rather than the lead
> field projected onto a source orientation overstates coupling, because the
> magnitude is the maximum over orientations. Not renormalising by the current
> actually delivered leaves a per-site term that does not cancel in a ratio.
> Assuming a fibre direction rather than deriving one from the label volume
> permitted a claim the derived field does not support. And comparing the best
> of fourteen candidate sites against the best of four rewards electrode density
> rather than placement.
>
> None of these is exotic. Each is the kind of simplification a forward-modelling
> study makes for defensible reasons, and each individually shifts the estimate
> by around a decibel. Their product was an effect of roughly 4 dB that is not
> there. **A monotone drift toward the null under corrections adopted for
> independent reasons is the signature of an effect that was never present**, and
> it is visible only if the corrections are applied and reported rather than
> chosen.
>
> We report this because the intermediate results were not obviously wrong. Each
> was internally consistent, cleared its measurement floor, and reproduced an
> a-priori anatomical prediction — the three muscles that appeared to favour the
> ear are the three whose attachments sit at or near the temporal bone, which is
> exactly what one would predict and exactly what makes a spurious result
> convincing.

---

## Notes for Claude Code

- **Verify every number against source.** Written from your reports.
- The a-priori prediction (§2.8, commit `fa583f6`) now needs restating: it was
  recorded before the model and the model initially appeared to confirm it. That
  it did **not** survive the controls is a stronger use of a pre-registration
  than confirmation would have been, and §2.8 should say so rather than being
  quietly deleted. A pre-registration that catches you is doing its job.
- Check whether the Abstract's Significance paragraph still promises a
  "per-muscle map". There is no map, there is a one-sided result.
- §4.2, which argues the complementarity result reproduces the anatomical
  prediction, must be rewritten or removed — it argues for a result that no
  longer exists.
- The title change propagates to the repository README and to the SimNIBS thread
  if it references the paper.
