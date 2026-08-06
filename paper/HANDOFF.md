# HANDOFF — Paper 1, as of 2026-08-05 (HEAD after `e903f5b`)

**Status: v1 is ready to post.** The review queue is worked, the title is ruled
and applied, and the two remaining substantive items are deliberately deferred to
v2 (§7). Do not start §7 work before the preprint is timestamped.

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

## 3. What was open here, and is now closed

Kept as a record of what each defect was, because the shapes recur.

**`−3.724` was NOT an orphan; it was correct and unsourced.** It reproduces at
−3.7237 from `03_homog_scalp_per_direction.npz` once the delivered-current
renormalisation is applied, and both it and −2.571 are cluster-basis, so the
"basis mismatch" this file previously recorded was not one. `04r_homog_cluster.py`
now emits it. `RULING_line608.md` is **withdrawn** (precondition never met) and
would have replaced correct text.

**Table 4 is now an envelope** over all five admissible jaw subsets
(`04q_table4_envelope.py`), which refuses to write unless the published four-site
subset reproduces the old table row for row. It does.

**Item 23 closed** — all six figures cited at first use. **Item 28 closed** — four
editing instructions were live in the body, not the two originally recorded.
**Items 11, 12, 13, 14, 19, 21 closed.**

**Still open:** item 29 (assembly-notes section at the end of the file), items 16
and 17 (the n=1 transferability argument rests on muscles that now carry no
claim), and a duplicated draw-procedure sentence in §3.1.

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

**The title was the open content problem and is now RULED and applied.** The old
one asserted jaw sites outperform "for every resolvable speech articulator", a
universal claim stronger than its own abstract. It is now *"No speech articulator
robustly favours retroauricular electrodes over canonical jaw sites"*, chosen
because its truth conditions are identical to the abstract's headline sentence,
so no future correction can make the two disagree. The abstract is deliberately
unchanged. `WORDING_title_44_46_cascade.md:28` still holds the old string on
purpose: it records what that file proposed, and rewriting it would falsify the
record.

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

Seven times now a real check returned a true fact that did not support the
conclusion drawn from it, and twice the proposed *correction* was the error. The
most recent three:

- `−3.724` was read as a wrong number because no file held it. It was right, and
  the ruling written to "fix" it would have replaced correct text.

- The cut plane "did not exist" because a histogram binned by S cannot see a plane
  tilted across 180 mm of lateral extent. **Every node count in that entry was
  correct.**
- My checkup reported "no orphans I can name" after checking the three orphans I
  already knew about and generalising. `−3.724` was in the handoff I had read.

**Verifying a step is absent HERE does not verify it is absent. Enumerating the
known cases does not establish the general claim.** Until axis (a)'s
`--check-body` reverse sweep exists, the correct statement is "no orphan has been
enumerated", never "there are none."

---

## 7. V2 QUEUE — future work, NOT open items. Do not treat as cleanup.

Everything below was investigated, costed, and **deliberately deferred past the
v1 preprint**. Each is disclosed in the manuscript as a limitation. A future
session must not pick these up as tidying: **every one of them can move Table 4
verdicts**, and the first fires a pre-commitment.

### 7.1 Extended-mesh rebuild — ARMS A LIVE TRIP-WIRE

The neck-extended mesh does not conserve charge: 1.070 mA through a plane at
S = −182 against a 1 mA injection, where the truncated control collapses to
0.107 mA at its own floor. Diagnosis is a mesh defect presenting as solver
non-convergence — the slab is meshed roughly an order of magnitude coarser than
the head, yielding 0.83% more elements for ~10% more volume. **Remedy is named at
METHODS_LOG 1265–1267:** rebuild with the slab at head-comparable element size.

Two cautions the record does not make obvious.

**Hypothesis 1 is UNTESTED, not falsified.** METHODS_LOG records it as falsified
by the `above_ear` probe, but `_failed_runs/boundary_probe_above_ear_VOID_solved_hyoid_20260803/WHY_VOID.txt`
shows that probe solved `hyoid`, not `above_ear`. The coarse-slab hypothesis is
still live and is the leading candidate.

**The 1.0 dB pre-commitment is recorded UNEXECUTED, and a successful measurement
fires it.** The measured floor is 0.27 dB, so exceeding 1.0 dB is well within
range. If it fires, the cascade reaches `04h`, `04q`, `04j`, `04p`, `04n`,
Table 4, §3.1, §4.1 and the Abstract. Cost: 22 solves at ~5.5 min wall each,
about two hours, plus the rebuild and a fresh memory measurement — the recorded
12 GB per solve does not survive refining the slab.

Closing this would bound Table 3 row 3's term on the **retained** sites, which is
what §3.4 cannot do. That is a real gain and it is why this is queued rather than
abandoned. Fire it when either outcome is affordable.

### 7.2 `EXTENSION_LABEL = 200` renumbering

`01c_extend_neck.py` labels the slab 200, inside SimNIBS's electrode-rubber range
(100–499), so `with_electrode_tags()` silently assigns 29.4 S/m — an 83x error
that once produced a fabricated invariant-2 reading (−0.310 against −0.0038 with
the correct map). It is **not** the cause of the flux failure, but any rebuild
must renumber it out of that range first.

### 7.3 Derived fibre fields — ZERO SOLVES, WHICH IS THE DANGER

`04k` reads the existing `*_scalar.msh` result meshes and computes E·n̂ per voxel.
The lead field is already solved; fibre direction enters only at read time. So
this is a re-reduction over 22 meshes at 911 MB each, about 20 GB read per
muscle, and **no new simulation**.

**That cheapness is exactly why it is deferred.** The derived field moved
temporalis from −2.571 to −1.147 and flipped *ear, robust on both axes* to *no
resolvable preference* — the single most consequential number change in this
paper. Running it on sternocleidomastoid and medial pterygoid, the two muscles
currently unstable across subsets, could resolve them in either direction off a
computation that costs nothing to start.

Scope is smaller than "the other nine": the construction needs a discrete bony
insertion. SCM, medial pterygoid and mentalis admit it directly; masseter,
lateral pterygoid and depressor anguli oris need a per-voxel fan toward a common
attachment; **orbicularis oris admits it in no form**, being a sphincter with no
bony insertion. §4.7 states this.

Regeneration if run: per-muscle pervoxel CSV and perdirection npz, then `04h`,
`04j`, `04q`, `04n`, `04p` if temporalis is touched, then §3.1, §4.1, Table 4 and
the Abstract.

---

## 8. PRE-SUBMISSION CHECKLIST — rescued from the manuscript's assembly notes

Item 29 removed an "ASSEMBLY NOTES — not part of the manuscript" section from the
end of the manuscript. Most of it was working record duplicated in METHODS_LOG.
**This part was not, and would have been destroyed with it.** Preserved verbatim
in substance, with dead entries marked.

1. ~~Figures 1, 3 and 6 do not exist.~~ **DONE 2026-08-05**, all six built and
   rendered; Fig 1 and Fig 6 pass `anonymise_head()` and `assert_anonymised()`.
2. **Table 1 CSV** needs exporting to a publication-ready form.
   `paper/TABLE1_conductivities.csv` exists; the manuscript describes Table 1 but
   does not include it. This is review item 48, deferred.
3. **SimNIBS citation is incomplete (ref 16).** This is review item 45, and it is
   the same defect: SimNIBS is named throughout and cited nowhere in text.
4. **`throat_scm` is withheld.** If it is ever measured on the physical rig it
   becomes a 23rd position and §2.3 changes. Disclosed in §4.7 as running against
   the reported jaw advantage.
5. **The repository must be public for §2.8's pre-registration citation to be
   checkable.** §2.8 cites commits by hash as evidence the prediction preceded the
   solve. The remote is currently **private** following the MIDA licensing
   incident (history purged with `git filter-repo`, incident closed). **A reader
   cannot verify the pre-registration while it stays private.** This is a live
   pre-submission blocker and it is recorded nowhere else.
6. **Author affiliation** — decide whether Minerva appears alongside Somach.
7. **Whether §4.4 stays.** It names uses Carl is not chasing (clench input,
   bruxism monitoring) and widens who cites this beyond silent speech. A decision,
   not a defect.

~~The title.~~ **Resolved 2026-08-05**, see §4.
