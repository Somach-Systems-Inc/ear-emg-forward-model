# Approved wording — lines 608, 728, 869

Written by Claude (the assistant), approved by Carl 2026-08-06. Completes the
six-site "advantage" pass; `WORDING_stale_framing.md` covers 730, 732 and
Table 3 row 9.

**Numbers are placeholders.** Fill from source.

---

## Line 608, §3.5

Currently: *"Temporalis's retroauricular advantage grows under the homogeneous
conductor, from −3.315 to −4.330 dB."*

> Temporalis's gap grows more negative under the homogeneous conductor, from
> `[TEMP_DETAILED]` to `[TEMP_HOMOG]` dB, so the anatomically resolved model
> places it closer to zero than a simpler one would. Sternocleidomastoid and
> lateral pterygoid move the other way.

The point survives and is unchanged: the detailed conductor is not what produces
temporalis's proximity to zero. Only the word "advantage" was doing work the
result no longer supports.

---

## Line 728, §4.3

Currently: *"The same decomposition applied to the ear's own advantages returns
a modest and sign-varying term."*

> Applied to the three muscles whose gaps come closest to zero — temporalis,
> sternocleidomastoid and lateral pterygoid — the same decomposition returns a
> modest term whose sign varies between them.

---

## Line 869, §4.7

Currently: *"sternocleidomastoid and lateral pterygoid draw 21 and 17 per cent
of their advantage from the conductivity contrast."*

> sternocleidomastoid and lateral pterygoid draw `[SCM_SHARE]` and `[LP_SHARE]`
> per cent of their gap from the conductivity contrast, so of the three muscles
> nearest zero they are the two whose position is most dependent on tissue
> properties rather than on geometry.

Check the surrounding sentences in §4.7: this paragraph was written to rank
transferability between muscles that favoured different montages. With one
montage winning everywhere, the ranking is now about **which gaps are most
likely to move between subjects**, not about which results transfer. If the
paragraph still says "transfer", it needs the same correction.

---

## Placeholder sources

| Placeholder | From |
|---|---|
| `[TEMP_DETAILED]`, `[TEMP_HOMOG]` | §3.5's homogeneous-control comparison |
| `[SCM_SHARE]`, `[LP_SHARE]` | `04e_fat_contrast_statisticA.csv`, share column |

---

## Note

Apply these together with `WORDING_stale_framing.md` in one pass — all six sites
are the same defect and splitting them risks a seventh appearing between passes.

After applying, re-run the "advantage" grep and confirm the count drops from 23
to 18, with the 18 being exactly the lines your audit listed as correct.
