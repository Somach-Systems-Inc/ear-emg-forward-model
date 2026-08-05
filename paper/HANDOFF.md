# HANDOFF — Paper 1, as of 2026-08-06

**Read in this order:** `CLAUDE.md` (standing rules — several were added this
session and they are the point), this file, `paper/METHODS_LOG.md` (last five
entries), `paper/REVIEW_TRIAGE.md`.

**Do not resume from memory.** Reconstruct state from files. This session made
several assertions that were wrong and had to be retracted; two of them were
"corrections" that damaged correct work. The files are right. Any narrative
summary of how the paper got here is not to be trusted.

---

## 1. Where the paper stands

**Headline: no muscle robustly favours the retroauricular montage.** Five
articulators favour the jaw montage on both robustness axes by 8.99–21.24 dB.

**This rests on ONE support, and §3.1/§4.1 say so explicitly.** The two
treatments of temporalis disagree:

| treatment | temporalis | verdict |
|---|---|---|
| uniform orientation sweep, matched counts (`04h`) | −2.571, [−3.308, −0.035] | favours the ear |
| derived per-voxel fibre field (`04k`) | −1.147, [−1.453, +5.458] | does not resolve |

The derived field governs: it removes an assumption rather than adding one, and
§2.8 pre-committed to that reading before the derivation ran. **Carl's standing
instruction: leave it that way. Do not look for a second support.** A paper that
names its most attackable point is stronger than one that props it up.

---

## 2. CURRENT HALT — the cut plane does not exist

`CUT_FACE_S = -116.2` is a **bare literal** at `02c_placement_acceptance.py:45`,
with copies in `01c_extend_neck.py` and `02_place_electrodes.py`. It governs the
10 mm near-cut exclusion set `{hyoid, submental_lat, submental_mid}` → the jaw
site set → every matched-count gap in Table 4 → the cluster basis the rest of the
audit is defined against.

**The mesh has no planar face at that coordinate or any other.** Node counts
taper smoothly: ~4,000/mm at S = −111, 1,402 at −116, 78 at the −122.17 minimum.
921 nodes lie within 0.25 mm of −116.2, unremarkable against its neighbours.
`clearance_to_cut_mm` is internally self-consistent with it, which is why nothing
caught it.

**Two attempts to replace it with a derived quantity both failed, both by
substituting a cheap proxy for a geometric quantity. Both are recorded in
METHODS_LOG as failures. Do not retry a third proxy.**

1. S-difference to the mesh minimum (−122.17). The minimum is a 78-node wisp,
   not a boundary, and is nowhere near the electrodes laterally.
2. 3D distance to triangles with `n_z < −0.5`. That filter spans S −122.07 to
   +115.99 — all downward-facing skin on the head. It measured distance to local
   skin (0.43–1.43 mm for all seven jaw electrodes), not to the inferior
   termination.

### FIRST ACTION, and only this one

Check whether the **extended** mesh has a planar face at S ≈ −182 that the base
mesh lacks.

- If the extension has a face and the base does not: "truncated" in this paper
  means MIDA's native anatomical extent, the extension is the cut object, and the
  language in §2 and §3.4 inverts.
- If neither is cut: the clearance concept dissolves and the exclusion set needs a
  different justification entirely.

Either answer makes a distance-to-boundary computation well-posed. Without it,
any distance computed is a third proxy. **Report the answer, change nothing,
then stop.**

### After that, only on Carl's ruling

- Correct §2's geometry description to what the mesh actually is. Carl's position:
  this is a strengthening, not a concession — a natural anatomical termination is
  a weaker artifact than a hard planar cut, and the extended-mesh charge-leak test
  stands independently of where anyone thought the boundary was.
- **Do not re-derive a threshold.** Report Table 4 both with and without the three
  most inferior jaw sites. If the verdict holds either way, the constant governs
  nothing and cannot be attacked. Pre-commit in METHODS_LOG first: *if any verdict
  differs between the two site sets, that is a finding change — halt and report,
  do not choose the set that agrees with the current text.*
- Then §3.4, then line 608 (both below).

---

## 3. Also open, blocked behind the halt

**§3.4 has no generating script.** Nothing in `results/` produces it. Its entire
numeric content — "no sign flips, 10 of 10, every |gap| clears the floor" — was
written from a run whose output was never saved. `+6.45` is an orphan. Carl has
ruled: regenerate from `04d` (a re-reduction over arrays already on disk, not a
solve), pre-committing first that any sign flip, any |gap| below the floor, or
fewer than 10 of 10 is a finding change and a halt.

**Line 608 / §3.5 basis mismatch.** The sentence pairs `04h`'s cluster gap
(−2.571) with a homogeneous value (−3.724) that exists in **no results file**.
`04i_homog_scalp.csv` gives −3.3145 → −4.3299, which are argmax-14 values. Carl's
ruling: compute the homogeneous gap at the **pre-registered cluster**, not
argmax-14, because differencing two independently-maximised quantities is the
statistic-B error again. **Guard passed** — `03_homog_scalp_per_direction.npz` has
all 22 electrodes including all four cluster sites, so this is a re-reduction, not
a re-solve. Restate all of §3.5 at cluster basis, not just the one sentence.
Approved wording is `paper/RULING_line608.md` §5; the line-608 block in
`WORDING_advantage_3sites.md` is **withdrawn**.

**`04i` must emit a `basis` column** (`argmax14` | `cluster`), both bases per
muscle in the same file, with the matching detailed-conductor gap in the same row
so nothing can pair across bases by accident. Mechanical, not yet done.

**Axis (a) of the audit** — `--check-body` with a manifest binding each claim to
(file, column, row selector), failing on drift **and** on any number in a covered
span with no manifest row. The second condition is what catches orphans. Spans:
Abstract, all table cells, finding-bearing Results sentences. Descriptive Methods
numbers are deferred. A manifest row resolving by value alone is not provenance,
and "unverified" is not a status the manifest may carry at submission.

**Then:** `03e_build_tensor.py` emits per-compartment tensor decisions to CSV
(Fig 4's "2 of 10" is unverifiable from disk); re-render Fig 1 (the 22-electrode
fix is committed, the figure is not rebuilt); item 23 (**no figure is cited
anywhere in the body text**); majors 11, 12, 14, 19, 21, 29; then 16, 17, 32 as
rewrites. Minors 30, 35–41, 43, 47 and editorial 44–49 are deferred to post-arXiv.

---

## 4. What exists to protect the work

- `src/manuscript_blocks.py` — anchored writes. `replace_block(name, content)`
  writes only between `<!-- TABLE:name -->` markers and raises if the anchor is
  missing or duplicated. **No fallback search, by design.**
- `src/04m_caption_numbers.py --check` — caption numbers from source (7/7 match),
  plus table header / row-count / row-label checks (2/2 match schema). Reports a
  standing HAZARD that the two tables share a row-label set by necessity. That is
  the precondition for this session's corruption; do not "fix" it by renaming.
- `src/04h_matched_counts.py` — reproduces the previously ad hoc tables exactly.
  **Carries a comment at the renormalisation site recording why it must NOT
  divide.** Read it before touching renormalisation anywhere.

---

## 5. What went wrong this session, so it is not repeated

Four retractions, all mine. They are in METHODS_LOG in full; the shapes matter
more than the instances:

1. **The 04h "renormalisation fix."** I verified 04h did not divide by delivered
   current and concluded the step was missing. `04d` already applied it upstream
   at line 123. Double-applied, moved ten gaps by up to 1.04 dB, flipped a
   verdict, and reached the Abstract and four sections before being caught.
   → *Verifying a step is absent HERE does not verify it is absent.*
2. **§3.3 overwritten with Table 4's rows, twice.** A row-label regex matched
   `| temporalis |` in both tables. There was never a second copy of Table 4.
   **Both times I reported it as a safeguard** ("rebuilt from CSV, not hand-edited").
   → *Never target a manuscript edit by content. Generating from source says
   nothing about where the output lands.*
3. **`04m`'s own first run** flagged three caption failures; one was real. It
   nearly "corrected" two correct captions — the same failure, inside the tool
   built to prevent it.
4. **Two bad proxies for the boundary distance** (§2 above).

Common thread: a check that confirmed a fact, where the fact did not support the
conclusion. In 1 and 2, the error was dressed as diligence.

**Carl's rules that follow, now in CLAUDE.md:** wording he supplies carries
placeholders keyed to a source file — never transcribe a number from prose, and
where a supplied number and source disagree, source wins and the discrepancy gets
reported even when the value is labelled approved. After correcting any computed
quantity, grep for the prose describing the old state. Any geometric quantity
entering a calculation must be derived, not asserted. Any scalar governing
inclusion or thresholding must be derived in code and emitted to a results file.

**Three times, deriving a constant from source overturned an assertion** — the
temporalis fibre axis, the 04h division, the cut plane. That is the method
working, not bad luck. Keep deriving.
