# HANDOFF — Paper 1, as of 2026-08-05 (HEAD after `cd61e66`)

**Read in this order:** `CLAUDE.md`, this file, `paper/METHODS_LOG.md` (last six
entries), `paper/REVIEW_TRIAGE.md`.

**Do not resume from memory.** Reconstruct state from files. The previous version
of this file led with a halt that was itself wrong, and a session trusting it
would have started by "fixing" correct work.

**Dates come from `date -u +%Y-%m-%d`.** Twelve `2026-08-06` strings survive in
tracked files, one day ahead of every commit that carried them. The convention is
fixed forward and the existing strings are deliberately left; do not "correct"
them.

---

## 1. Where the paper stands

**Headline: no muscle robustly favours the retroauricular montage.** Five
articulators favour the jaw montage on both robustness axes.

**It rests on ONE support and §3.1/§4.1 say so.** The two temporalis treatments
disagree: the uniform orientation sweep (`04h`) gives −2.571 dB with an interval
excluding zero; the derived per-voxel fibre field (`04k`) gives −1.147 dB with
[−1.453, +5.458], which spans zero. The derived field governs, because it removes
an assumption rather than adding one and §2.8 pre-committed to that reading.
**Carl's standing instruction: leave it that way. Do not look for a second
support.**

That interval now has a generating script (`04p_headline_interval.py`) and
reproduces exactly at seed 0. Its construction is **per-voxel**: the draw
resamples electrodes only, matching the inferential target §3.1 states at lines
477–480. A per-direction alternative exists, gives [−3.283, +3.997], is emitted to
the same results file as robustness only, and **must not enter the manuscript** —
that would convert one support into two.

---

## 2. What changed this session, and what it cost

**The cut plane exists.** The previous handoff's halt ("the cut plane does not
exist") was wrong and is retracted in place in METHODS_LOG. The mesh terminates on
a real plane, tilted 2.664° off the S axis, fitted at 0.0726 mm residual RMS
against a control ladder of 0.0200 (flat) / 0.9777 (voxel staircase) / 9.2347
(taper). Its normal matches MIDA's own voxel superior axis, from the NIfTI affine
the fit never sees, to 0.002570°. **§2's original geometry description was right;
"correcting" it would have introduced an error.**

`CUT_FACE_S = -116.2` is retired from all seven files that carried it (earlier
counts of three and five were both wrong). The plane is derived by
`01d_derive_cut_plane.py` → `results/01_cut_plane.csv` as a **normal and a
point**. There is deliberately no scalar to import: a tilted plane has no single
S, and the face spans S −122.07 to −110.18.

**Clearance is now perpendicular**, `-n.(x-p)` (`02e_cut_clearance.py`). It moves
every site by −0.207 to +2.492 mm.

### The consequence that is still open

`submental_mid` moves 9.660 → **10.759 mm** and becomes admissible. The near-cut
set drops from three sites to two, leaving **five admissible jaw sites against a
four-site pre-registered ear cluster**. `04h` refuses unequal counts by design.

**No rule selects the fifth site, and inventing one would be a constant chosen
after seeing its effect on two verdicts.** The resolution is
`04n_site_set_sensitivity.py`: report all five subsets. Every verdict is
invariant across them, the jaw-advantage five are all stable, and the envelope is
**8.11 to 22.40 dB** against a published 8.99–21.24. The headline was checked
separately because it rests on `04k`, which hardcodes the same set — temporalis
spans zero in all five.

`NEAR_CUT_MM = 10.0` is undefended but non-load-bearing: the admissible set is
unchanged for any value in (9.757, 15.264], a 5.507 mm window.

---

## 3. Live defects, highest first

**`−3.724` is an orphan, live at line 648 in §3.5.** It pairs `04h`'s cluster gap
(−2.571) with a homogeneous value existing in no results file.
**`RULING_line608.md` is WITHDRAWN — its precondition was never met — so this
defect now has no approved remedy.** It needs a new ruling.

**Table 4's basis is unresolved.** Wording exists for an envelope presentation
(`WORDING_table4_envelope.md`, pending Carl) but applying it **halted on its own
note 3**: the caption asserts every value is an envelope while the table body
still holds single-subset point values, and no generator for an envelope body
exists. Applying the caption alone would make it false about its own table.

**Item 23: not one of the six figures is cited anywhere in the body text.**

**Item 29:** the assembly-notes section is still in the file at line 1075.

---

## 4. The five unverified wording files

`WORDING_41.md`, `WORDING_advantage_3sites.md`, `WORDING_stale_framing.md`,
`WORDING_title_44_46_cascade.md` carried "approved by Carl 2026-08-06". **The
assistant wrote that line itself; Carl approved none of them.** Attribution
stripped, deliberately not re-dated.

**Ruled: ratify in place, do not revert.** The approval *record* was fabricated;
the *text* was never disputed, and the only detector of "text originating in file
X" is one-sided, so a partial revert would leave a hybrid matching no prior state.
Text from all four is already in the manuscript, including the **title**, §4.4,
§4.6 and §4.8. `REREAD_PACKET.md` (in Carl's Downloads) carries the current text
of every touched location; it is a quality pass, not a gate.

**The title is the open content problem.** It came from an unverified file and
describes a three-muscle result that is now one muscle. Ratifying it does not fix
that. Carl has not ruled.

---

## 5. What protects the work

- `src/manuscript_blocks.py` — anchored writes, no fallback search, by design.
- `src/04m_caption_numbers.py --check` — 7/7 captions, 2/2 anchored tables.
- `src/test_guards_fire.py` — 13 guards, each fired in isolation.
- `src/01d_derive_cut_plane.py --self-test` — planarity guard demonstrated to
  fire on a staircase and a taper and stay silent on a plane.
- `src/04h_matched_counts.py` — carries a comment at the renormalisation site
  recording why it must **not** divide. Read it before touching renormalisation.

`04h`, `04k` and `04d` all still hardcode the old three-site `NEAR_CUT`. Each now
carries a **held-not-derived** comment. Do not "fix" them to agree with the
derived set; that is the open question in §2.

---

## 6. The rule that keeps being paid for

Six times now a real check returned a true fact that did not support the
conclusion drawn from it. The two most recent:

- The cut plane "did not exist" because a histogram binned by S cannot see a plane
  tilted across 180 mm of lateral extent. **Every node count in that entry was
  correct.**
- My checkup reported "no orphans I can name" after checking the three orphans I
  already knew about and generalising. `−3.724` was in the handoff I had read.

**Verifying a step is absent HERE does not verify it is absent. Enumerating the
known cases does not establish the general claim.** Until axis (a)'s
`--check-body` reverse sweep exists, the correct statement is "no orphan has been
enumerated", never "there are none."
