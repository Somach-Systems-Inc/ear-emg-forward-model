# CHI 2027 submission — build design

**One source, two outputs.** The CHI submission is rendered from
`paper/PAPER1_humanized.md` by `paper/build_chi.py` — the same text the arXiv
v3 bundle ships, so reviewers at both venues read the same words
(`--src` overrides for comparison builds). There is no CHI-specific
manuscript to keep in sync: the two venues differ only in what the build does
to the shared source.

Deadline: full papers due **2026-09-10 AoE** (verified on
chi2027.acm.org/authors/papers/, 2026-08-10; no abstract deadline; submission
site opens 2026-08-13; PCS, single-column review format, anonymized).
Word guidance: 5,000–8,000 encouraged; >12,000 desk-rejected. References,
figure/table captions and **appendices do not count**, which is why the cuts
below move text to appendices instead of deleting it.

## What the build does

1. **Cuts at paragraph granularity.** Each cut is addressed by section heading
   plus a verbatim prefix of the paragraph's first words. If the prefix no
   longer matches exactly one paragraph in that section, the build fails —
   never a silent no-op. Cut paragraphs are moved to Appendix A (methods),
   B (tables 2–3), or C (results/discussion detail), so nothing is destroyed
   and §-references keep resolving (every numbered section keeps its number
   and a condensed body in the main text).
2. **Replaces four blocks** with CHI-specific text from this directory:
   the abstract (shortened), the pre-registration paragraph and the data
   availability section (anonymized: repository URL and commit hashes withheld,
   dates kept), and one added positioning passage at the end of the
   Introduction (`intro_chi_positioning.md`).
3. **Anonymizes and proves it.** The build fails if the output contains the
   author's name, company, email, repository URL, or the pre-registration
   commit hashes. The `anonymous,review` options of `acmart` mask the author
   block; pdf metadata inherits that.
4. **Never retypes a number.** Every digit-bearing token in the generated
   markdown must appear verbatim in the source manuscript
   (`PAPER1_humanized.md` by default). Insert files are covered by the same
   check. A number that fails this check is a build error, not a warning.
5. **Renders with acmart** (`manuscript,review,anonymous` = the single-column
   review format), figures interleaved at first citation using the same
   anchor-then-insert-backwards algorithm as `build_submission.py`, unicode
   mapped through the same tables, Table 4/5 widths through the same fixer.
6. **Reports the countable word total** (abstract + body + tables 4–5,
   excluding references, captions, appendices) and warns above 8,000.

## What a human still owes before submission

- CCS concepts and keywords: placeholders marked TODO in the template.
- Subcommittee choice in PCS (opens 2026-08-13).
- Carl reviews all prose in this directory — it is draft, not approved wording.
- Final anonymization pass by eye on the built PDF, including figures.
