# Peer review triage against the 2026-08-05 rewrite

Classification only. Nothing fixed. Per the conflict rule: the rewrite
supersedes on **framing and numbers** because it postdates the review and
carries measurements the reviewer did not have; an item the rewrite did not
actually address is **still open** and is worked regardless of which section it
sits in.

| | count |
|---|---|
| **CLOSED by the rewrite** | **18** |
| **STILL OPEN** | **28** |
| **NOW WRONG** (objects to text that no longer exists, or in the opposite direction) | **3** |

---

## CLOSED by the rewrite (18)

Each names *which* change closed it, so a reader can check rather than trust.

| # | sev | why it is closed |
|---|---|---|
| 1 | major | Intro/Results mismatch — Abstract, Introduction novelty paragraph and §3.1 all replaced; the seven-and-three framing is gone from the file |
| 4 | major | Discussion per-site claims — §4.4 and §4.6 rewritten off the per-site argmax values |
| 5 | major | "No fibre direction exists" — that universal claim is absent; §3.1 now reports orientation agreement as a fraction |
| 6 | major | argmax 14 vs 4 — matched counts implemented; Table 4 uses the pre-registered 4-site cluster and reports the random-4 interval |
| 7 | major | novelty vs HArtMuT untested — **measured**, not argued: §3.5 is the homogeneous-conductor control, and the paper now concedes the application-study framing |
| 8 | major | anisotropy null scope — §3.2 and Table 3 row 4 state the tensor is applied to 2 of 10 compartments, others NOT APPLIED |
| 9 | major | §3.2 reported gap changes for non-tensor muscles — rewritten as a null with a bound |
| 15 | major | lateral pterygoid carrying §4.4/§4.6 — both rewritten off it; §4.6 states a null result there would agree with the model |
| 18 | major | §4.3 correlation uncheckable — the ρ = −0.955 paragraph and its cancellation explanation are in §4.3 |
| 24 | major | Fig 5 caption — figure rebuilt as a distribution; caption regenerated and points at the two-axis verdicts |
| 25 | major | Fig 6 caption promises overlays — figure built with the compartment, hyoid and electrode overlays it names |
| 26 | major | Fig 1 caption — figure built; the licence-crop consequence is stated in the caption |
| 27 | major | statistic A undefined — defined in Table 4's caption and in Methods §6.6 |
| 28 | major | editing instructions in Results/Discussion — absent from the file |
| 31 | major | pre-registration mechanism — §2.8 cites both commits by hash and date |
| 34 | minor | labial group membership — five members consistently |
| 42 | minor | Abstract lost its heading — structured headings restored |
| 3 | major | cross-reference pointing at a contradicting section — target text replaced; no `§3.3` cross-reference remains |

## NOW WRONG — objects in a direction the data no longer supports (3)

| # | sev | why |
|---|---|---|
| 16 | major | the n=1 transferability argument is still in the file, but it now rests on SCM and lateral pterygoid at "21 and 17 per cent" — both are now **no resolvable preference**, so the objection is right that the argument fails, but for a different and stronger reason than the reviewer gave. **Rewrite, do not patch.** |
| 17 | major | the 21 % / 5.06 dB site-set mismatch is real, but both numbers describe SCM, which no longer carries a claim. The fix is deletion, not reconciliation. |
| 32 | major | title vs conclusions — the reviewer objected that the title overstates a three-muscle result. It is now a **one-muscle** result, so the objection stands but is sharper than written. "Different articulators" still holds for temporalis against the labial group. |

## STILL OPEN (28)

The rewrite did not touch these. Severity from the report.

**Major (13):** 2 (stale 10–23 dB, confirmed present), 10 (Fig 4 caption in the
manuscript still says "robust to the isotropy assumption" — the *figure* was
retitled, the manuscript text was not), 11 (Table 3 truncation bounded vs §4.7
unknown), 12 (SCM truncated as a source, bias runs toward the ear electrodes),
13 (orientation constraint derived for temporalis, asserted elsewhere), 14
(mirror-symmetry test applied inconsistently to SCM and medial pterygoid), 19
(sphere validation framing), 20 (**Table 3 row 8 still reads "bounded by row 6"**
— the term was corrected in Methods §2.4 and in every downstream number, but the
row itself was never edited), 21 (§2.7 admission rule violated by its own rows),
22 (electrode count inconsistent), 23 (figure citation — figures exist and are
referenced, but check every one is cited at first use), 29 (assembly-notes
section still in the file), 33 (§3.3 heading asserts a binary its own section
refutes).

**Minor (10):** 35, 36, 37, 38, 39, 40, 41, 43, plus 30 (pre-registration
overstated in §4.2) and 47 (Table 2 caption).

**Editorial (5):** 44 (seven uncited references — Maksymenko and Mesin are
direct prior art the novelty claim must engage), 45 (SimNIBS named and never
cited in text — the bib entry exists, the citation does not), 46 (production
note at the top), 48 (Table 1 described but not included — the CSV exists at
`paper/TABLE1_conductivities.csv`), 49 ("flip cone" undefined — and the term no
longer appears in Table 4, so this is close to closed).

---

## The two that contradict expectation

**Item 20 is NOT closed.** The delivered-current term was corrected rather than
bounded, and every downstream number was regenerated — but **Table 3 row 8 still
literally reads "bounded by row 6"**. The fix landed in Methods §2.4 and in the
data; the table row was missed. This is exactly the failure the number audit
exists to catch, found by grep rather than by reading.

**Item 2 is NOT closed.** "10 to 23 dB" survives in the Discussion. The labial
gaps are now 8.99–21.24 dB at the cluster.
