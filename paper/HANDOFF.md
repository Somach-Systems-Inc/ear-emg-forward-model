# HANDOFF — 2026-08-06, end of the review-queue session

## Read first
`paper/METHODS_LOG.md` (last three entries), `CLAUDE.md`, `paper/REVIEW_TRIAGE.md`.

## The state of the claim

**No muscle robustly favours the retroauricular montage.** Five favour the jaw
on both robustness axes by 8.99–21.24 dB.

**This rests on ONE support and the paper says so.** The two treatments of
temporalis disagree:

| treatment | temporalis | verdict |
|---|---|---|
| uniform orientation sweep, matched counts | −2.571, [−3.308, −0.035] | favours the ear |
| derived per-voxel fibre field (`04k`) | −1.147, [−1.453, +5.458] | does not resolve |

The derived field governs: it removes an assumption rather than adding one, and
§2.8 pre-committed to that reading. §3.1 and §4.1 name this as the paper's most
attackable point. **Carl's standing instruction: leave it that way, do not look
for a second support.**

## Two retractions today, both mine, both worth reading before trusting anything

1. **The 04h "renormalisation fix" was wrong and is fully reverted.**
   `04d_orientation_sign.py` already divides by delivered current at line 123
   and stores the divided arrays. Adding a division in 04h double-applied it,
   moved ten gaps by up to 1.04 dB, and flipped a verdict before being caught.
2. **`04m_caption_numbers.py`'s own first run flagged three failures; one was
   real.** It nearly "corrected" two right captions.

Both have the same shape: a check that confirmed a fact, where the fact did not
support the conclusion. New CLAUDE.md rule: *verifying a step is absent HERE
does not verify it is absent — check upstream, and name the file where it would
have been applied.*

## Done this session
- §4.1 replaced (montages are not complementary); §4.2 reframed as a FAILED
  pre-registration; §2.8 restates it plus the no-script corollary; new §4.8.
- New title; README retitled.
- `src/04h_matched_counts.py` — reproduces the ad hoc tables exactly.
- `src/04m_caption_numbers.py --check` — caption numbers from source, exits
  non-zero on drift. **All 7 claims currently match.**
- Fig 5 caption regenerated (+20.90 / −3.31, was +21.9 / −3.80).
- Review items **2, 20, 10** closed. **22** fixed in code (below).

## STOPPED, awaiting Carl

**Item 33 — §3.3's heading is a framing decision.** The heading reads *"The gap
is geometric, not a property of intervening tissue"*; the section's own body
says the adipose contribution "is not uniform in sign across muscles" and Table 3
row 9 records a sign spanning −2.86 to +1.09 dB. The heading asserts a binary its
content refutes. Rewriting it changes what the paper claims, so it waits.

## Open, mechanical, ready to run

- **Item 23 — NO figure is cited anywhere in the body.** All six are referenced
  only inside the captions block. Needs citations at first relevant point in
  Results.
- **Fig 1 must be re-rendered.** `figures/render_fig1.py` was fixed to plot the
  22 SOLVED electrodes (was 23 — it drew `earlobe_contra`, which has coordinates
  but no solve, under a caption saying 22). **The fix is committed but the
  figure has not been rebuilt.** Note `verified` is not a rejection flag: values
  are no/accepted/held and 16 of the 22 solved sites carry "no".
- **Fig 4's "tensor on 2 of 10" has no source on disk.** `03e_build_tensor.py`
  reports per-compartment decisions only to stdout. Believed correct, but fails
  §2.8. Fix = have 03e emit its decisions. **This is the third artifact found
  without a generating script; Carl's stop-rule names that as a halt condition.**
- Then: majors 11, 12, 14, 19, 21, 29; minors 30, 35–41, 43, 47; editorial 44–49.
- Items 16, 17, 32 are marked NOW WRONG in the triage — rewrite, do not patch,
  and all three touch Discussion prose.
