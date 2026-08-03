# Sculptor workspace review — 2026-08-03

Three workspaces were to be reviewed against declared file ownership, vetted,
and merged one at a time. Result: **one merged, one held, one had no work.**

A PR could not be opened for the held workspace: **this repo has no git remote
configured** (`git remote -v` is empty), so `gh pr create` has nothing to push
to. Creating a GitHub repository is outward-facing and was not done
unilaterally. The findings are recorded here instead. See "What I need from
you" at the bottom.

---

## Identification

Branch names are auto-generated, so workspaces were identified by content.

| workspace branch | identified as | state |
|---|---|---|
| `carl/organic-echidna` | **citations** | **MERGED** |
| `carl/arrogant-spoonbill` | **figures** | **HELD** |
| `carl/mustard-sparrow` | github-org (presumed) | **no work** |
| `carl/sloppy-giraffe` | unassigned, 4th workspace | **no work** |

All four branches sit at commit `88b51da` with **zero commits** of their own.
All work is uncommitted in the worktrees. The Sculptor app is running, so the
worktrees were treated as **read-only** and were not modified: the merge was
performed by copying files into `main`, leaving their workspaces untouched.

---

## 1. citations — MERGED (commit `8579c29`)

**Ownership: PASS.** Touched `paper/references.bib` and `paper/CITATIONS.md`
and nothing else.

**Vet: PASS, and it is the strongest artefact of the three.** It grades every
entry `V+` (primary source independently re-fetched), `V`, `CORR` or
`UNVERIFIED`, and it refuses to invent what it cannot confirm. The AlterEgo
form-factor claim is left **out of the bib entirely** rather than given a
plausible-looking citation, which is the correct call.

**Two of its load-bearing corrections were re-verified here independently
before merging**, because a citation ledger that is wrong is worse than none:

- The gap statement *"to date, there is no theoretical study of such artifacts
  in ear-EEG"* is **Yarici, Thornton & Mandic (2023)**, Front. Neurosci.
  16:997377. Fetched the Frontiers page: title, all three authors, volume and
  article number confirmed, sentence present verbatim. **Kappel is not an
  author.** `OUTLINE.md` attributed it to Kappel in two places, and this is the
  sentence the paper's entire gap argument rests on.
- *"Kappel et al. (2023), High-density ear-EEG"* is **Meiser, Knoll &
  Bleichner (2024)**, J. Neural Eng. 21(1):016001. Fetched IOPscience:
  confirmed. Wrong authors, wrong year.

The gap survives both corrections. It changes owner, not validity.

`OUTLINE.md` and `CLAUDE.md` were corrected in commit `c684ced`. The citations
workspace correctly declined to edit files it did not own and wrote the
corrections where the owner would find them, which is exactly right.

---

## 2. figures — HELD

**Ownership: FAIL.** Declared ownership is `figures/render_*.py` and
`figures/mock_data.py` only.

| file | within ownership? |
|---|---|
| `figures/mock_data.py` | yes |
| `figures/render_common.py` | yes |
| `figures/render_fig2.py` … `render_fig5.py` | yes |
| **`.gitignore` (modified)** | **NO** |

That is the whole reason it is held. The rule was applied mechanically, as
specified.

**In fairness to the work, the `.gitignore` change is defensible in content.**
It adds:

    results/04_sensitivity_MOCK.csv
    figures/MOCK_*.pdf
    figures/MOCK_*.png

so synthetic fixtures are never tracked as if they were real solve output.
That is a *good* instinct and it protects exactly the property this project
cares most about. It is still outside the declared ownership, and the
ownership rule is what keeps parallel workspaces safe to merge unattended.
**Your call, not mine** — it is a one-line approval if you want it.

**Vet: no correctness or fabrication findings.** The safeguards are genuinely
strong:

- every number stamped `SYNTHETIC`; output file carries `_MOCK` in its name
- `# SYNTHETIC MOCK DATA` banner written as the file's first line
- every rendered figure carries a diagonal `SYNTHETIC — MOCK DATA` watermark
- missing electrode coordinates `raise SystemExit` rather than being invented
- renderers default to the real contract path `results/04_sensitivity.csv`, so
  they switch from mock to real without edits once stage 4 emits that schema

**One item for your eye, not a blocker.** `mock_data.py` carries a synthetic
placeholder coordinate for `throat_scm`:

    "throat_scm": (52.0, -2.0, -95.0),   # over SCM, lower neck — SYNTHETIC placeholder

`throat_scm` is the one electrode held with blank coordinates because **you
are measuring it on your own neck**, and the project rule is never to fabricate
a landmark. This is contained to mock data and is explicitly labelled, so it
does not violate the rule as written. But it is the single place in the
repository where a number stands in for that measurement, and it is worth
knowing that before the real placement lands.

---

## 3. github-org — NO WORK

`carl/mustard-sparrow` and `carl/sloppy-giraffe` both have **clean working
trees and zero commits**. No `.github/` directory was created in either. There
is nothing to merge, review, or hold. If a github-org task was dispatched, it
produced no output.

---

## What I need from you

1. **The `.gitignore` question.** Approve the figures workspace's `.gitignore`
   addition and I will merge it, or tell me to have the workspace drop that
   file and re-do it within ownership.
2. **Whether to create a git remote.** There is none. Without one there is no
   `gh pr` path for held work, and nothing in this repo is backed up off this
   machine. Creating and pushing a repository is outward-facing, so it is
   waiting on you.
