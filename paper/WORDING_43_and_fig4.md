# Approved wording — §4.3 opening, §3.2 / Fig 4 reframe

Written by Claude (the assistant), approved by Carl 2026-08-05. Third companion
file, after `WORDING_abstract_results.md` and `WORDING_33_43_limitations.md`.
Drop in verbatim.

---

## §4.3 — replacement for the opening paragraph

Replaces: *"The ear's deficit against the labial group is geometric. The
adipose–muscle conductivity contrast accounts for 0.6 to 13.3 per cent…"*

> For the labial group the ear's deficit is predominantly geometric, though the
> material contribution varies widely within the group: the adipose–muscle
> conductivity contrast accounts for 0.6 per cent of the gap for platysma and
> 13.3 per cent for orbicularis oris. The remainder in every case is
> source-to-electrode distance. The two regimes remain separated — 0.6 to 13.3
> per cent for the muscles the jaw wins, against 17 to 21 per cent for those the
> ear wins — but the separation is narrower than a single figure would suggest,
> and no muscle in either group is unaffected.
>
> Limb studies cannot make this separation, because adding a fat layer changes
> material properties and source-to-electrode distance together (Kuiken et al.
> 2003). A labelled head model can, because conductivity is changed with
> geometry held exactly fixed. This is a comparison the limb geometry
> structurally cannot support, and it is available here for the cost of one
> additional solve.

---

## §4.3 — new short paragraph, insert after the above

State the correlation reversal. It is honest, it pre-empts a reviewer who
computes the same thing, and it is the fourth appearance of the ratio-cancellation
argument the paper is organised around.

> The material share is not a dose response. Across the muscles for which a
> layer profile exists, it correlates *negatively* with the adipose fraction of
> the muscle-to-skin path (Spearman ρ = −0.955, p = 0.001, n = 7): platysma sits
> at 0.650 fat fraction and 0.6 per cent material share, while
> sternocleidomastoid sits at 0.225 and 21 per cent. The strength of that
> relationship shows the swap is measuring adipose path rather than something
> incidental, but its sign shows it does so through cancellation. The reported
> share is |Δgap| / |gap|, and a muscle embedded uniformly in fat has both the
> jaw and the ear route shifted together, so the change subtracts out of the
> ratio. The quantity that would track positively is the *difference* between
> how the two routes traverse fat, which this study does not form. This is the
> same cancellation that makes a uniform magnitude offset invisible in every
> ratio reported here, arriving in a place where it was not anticipated.

---

## §3.2 — replacement for the anisotropy paragraph

The current text describes a robustness check that survives. Under statistic A
the correct statement is stronger and simpler: there is no resolvable effect at
all.

> **The isotropy assumption does not measurably affect any site-to-site ratio.**
> Applying a fibre tensor changes the jaw-versus-ear gap by −0.085 dB for
> sternocleidomastoid, −0.010 dB for medial pterygoid, +0.137 dB for temporalis
> and +0.036 dB for lateral pterygoid. Every one of these lies below the 0.27 dB
> measured electrode-meshing floor, including for the two compartments that
> carry a tensor. Anisotropy raises the absolute lead field substantially — by
> roughly 5 dB in medial pterygoid — but it does so at the jaw and ear sites
> alike, so the effect subtracts out of every ratio this paper reports.
>
> This is a null with a bound rather than an absence of evidence, and it has a
> practical consequence: for coupling *ratios* between electrode sites, a
> muscle-fibre tensor is not worth the modelling effort in a head model of this
> resolution. Absolute lead-field values are a different matter and are affected.

**Fig 4's title and caption should follow.** The figure asks "is the ear
advantage robust to the isotropy assumption"; the answer is that the assumption
does not resolve at all. Retitle to state the null, and note in the caption that
the per-cell deltas shown are large while the *gap* deltas are below the floor —
that contrast is the point of the figure.

---

## Table 3 row 4 — reclassification, not just a value

Anisotropy moves from **affects site-to-site ratios: yes** to **no**, with
−0.085 dB as the largest observed change against a 0.27 dB floor. It joins the
cancelling terms. Note in the row that the absolute lead field *is* affected
(~5 dB in medial pterygoid), so the reclassification is specific to ratios.

---

## Notes for Claude Code

- The statistic-B anisotropy numbers (+1.448 SCM, +0.199 medial pterygoid) are
  **superseded and retracted**. B was wrong by 17× and flipped the sign. They
  belong in METHODS_LOG only, marked as such, alongside the fat-swap instance —
  two sign flips from the same cause is a pattern worth recording as one entry
  rather than two.
- Record that B is now retired for **all conductivity comparisons**, surviving
  only in Fig 2's matrix where no per-orientation form exists. State the reason
  in Methods: changing conductivity reshapes the current path, so per-site
  medians drift to different orientations and differencing them measures the
  drift.
- Verify every number in this file against source before it ships.
