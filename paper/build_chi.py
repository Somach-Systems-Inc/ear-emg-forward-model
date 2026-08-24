#!/usr/bin/env python3
r"""
Build the CHI 2027 submission from PAPER1_humanized.md.

ONE SOURCE, TWO OUTPUTS. The arXiv build and this build read the same
manuscript; nothing here forks the prose. The CHI render differs in what the
build does: paragraph-level cuts routed to appendices (CHI's word count
excludes references, captions and appendices), four anonymization/condensation
replacements from paper/chi/, and the acmart review format.

THE THREE GUARDS, all of which fail the build rather than warn:

  1. **Prefix addressing.** Every cut, replacement and insertion is addressed
     by section heading plus a verbatim prefix of the paragraph's first words.
     A prefix that matches zero or two paragraphs is an error. No content
     regex, no positional index that drifts silently when the manuscript is
     edited upstream.
  2. **No retyped number.** Every digit-bearing token in the generated
     markdown must appear verbatim in the source manuscript (SRC, default
     PAPER1_humanized.md — the same text the arXiv submission ships). The insert
     files under paper/chi/ are covered by the same check, so a transcription
     error in a condensed abstract is a build failure, not a latent defect.
  3. **Anonymity.** The final LaTeX must not contain the author's name,
     company, email, repository host, or the pre-registration commit hashes.
     CHI desk-rejects anonymization violations, including in supplementary
     material.

Sections keep their numbers and a condensed body in the main text, so every
cross-reference of the form "(§2.6)" still resolves; the appendix subsection
that carries the moved detail names its origin section.

    python paper/build_chi.py
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPER = ROOT / "paper"
# The humanized variant is the text the arXiv submission ships, so it is what
# CHI reviewers should read too. --src overrides for comparison builds.
SRC = PAPER / "PAPER1_humanized.md"
CHI = PAPER / "chi"
BUILD = PAPER / "chi_build"
TEX = BUILD / "ms_chi.tex"
PDF = PAPER / "PAPER1_chi_submission.pdf"

sys.path.insert(0, str(PAPER))
from build_submission import FIGURES, fix_table_widths, fix_unicode_tex, latex_escape

# Each entry: section title (heading text without the hashes) -> operations.
#   replace_all:  file under paper/chi/ replacing the whole section body
#   replace:      {paragraph prefix: file} replacing one paragraph
#   appendix:     [paragraph prefix, ...] moved to the appendix, original order
#   insert_after: [(paragraph prefix, text-or-file), ...] new paragraph after
# Prefixes are verbatim from the manuscript; the build fails unless each
# matches exactly one paragraph in its section.
SPEC = {
    "Abstract": {"replace_all": "abstract.md"},
    "1. Introduction": {
        "insert_after": [("The result is not a ranking", "intro_chi_positioning.md")],
    },
    "2.1 Head model": {
        "appendix": [
            "**Boundary.** The MIDA head model is truncated",
            "The cut plane is not fitted to an assumed orientation",
            "**Mesh validation.** Every tag",
        ],
        "insert_after": [(
            "A neck-extended variant was constructed",
            "The fitted cut-plane geometry, its agreement with MIDA's own "
            "voxel axis, and the mesh-validation checks are given in full in "
            "Appendix A.",
        )],
    },
    "2.2 Conductivity assignment": {
        "appendix": [
            "Provenance is mixed, deliberately, and stated per row",
            "Insensitivity to that choice was measured",
        ],
        "insert_after": [(
            "Air is a numerical choice",
            "The measured insensitivity of every reported gap to that choice "
            "is given in Appendix A.",
        )],
    },
    "2.3 Electrode placement": {
        "appendix": [
            "Target localisation uses a hybrid",
            "The midline is derived, not assumed",
            "One position is withheld",
        ],
        "insert_after": [(
            "Each site is defined by an anatomical anchor",
            "The target-localisation rule, the derived anatomical midline, "
            "and per-site depths are specified in Appendix A.",
        )],
    },
    "2.5 Fibre orientation": {
        "appendix": [
            "Two further restrictions apply and both bite",
            "The anisotropic condition is solved on the isotropic run's own mesh",
        ],
        "insert_after": [(
            "The anisotropic condition therefore applies a tensor",
            "The bilateral mirror-symmetry test that gates each axis, and the "
            "identical-mesh construction that removes electrode realisation "
            "from the anisotropy comparison, are specified in Appendix A.",
        )],
    },
    "2.6 Validation": {
        "appendix": [
            "**Reciprocity on the head mesh.**",
            "**Four physical invariants**",
            "**Convergence.** RDM against the analytic sphere",
            "**Guard tests.**",
        ],
        "insert_after": [(
            "**Analytic multilayer sphere.**",
            "Three further validation layers (reciprocity verified on the "
            "head mesh itself, four physical invariants computed on every "
            "solve, a mesh-convergence fit, and two guard meta-tests that "
            "protect the validation machinery) are specified in full in "
            "Appendix A.",
        )],
    },
    "2.7 Error budget": {
        "insert_after": [(
            "Every published quantity in this paper is a ratio",
            "The full budget, with per-term magnitudes, is Table 3 in "
            "Appendix B.",
        )],
    },
    "2.8 Reproducibility and pre-registration": {
        "appendix": [
            "One qualification, because the claim is otherwise stronger",
            "A published table with no generating script",
        ],
        "replace": {
            "The anatomical prediction was recorded before the model was solved":
                "prereg_anonymized.md",
        },
        "insert_after": [(
            "Everything is reproducible from a clean checkout",
            "The mesh-realisation qualification to this claim, and a worked "
            "failure case for tables produced without a generating script, "
            "are given in Appendix A.",
        )],
    },
    "3.1 Which montage sees which muscle": {
        "appendix": [
            "The lower bound of this interval is not a tail quantile",
            "This also fixes what the interval means",
        ],
    },
    "3.3 The tissue-conductivity contrast is a small term with a muscle-dependent sign": {
        "appendix": ["Reported per muscle only"],
    },
    "4.3 The mechanism is distance, not intervening tissue": {
        "appendix": ["That distinction predicts which results should transfer"],
    },
    "4.7 Limitations": {
        "appendix": [
            "The construction requires a discrete bony insertion",
            "The limitation is therefore not that nine derivations",
        ],
        "insert_after": [(
            "**The orientation constraint is derived for one muscle",
            "Which compartments admit the derived-field treatment, which need "
            "a different construction, and which admit none are catalogued in "
            "Appendix C.",
        )],
    },
    "Tables": {
        "appendix": [
            "Table 1",
            "| # | MIDA structure",
            "Table 2",
            "| Site | Target | Target thickness",
            "Table 3",
            "| # | Term | What sets it",
            "Row 6 is measured by rotating",
            "Row 7 is deliberately left unquantified",
        ],
    },
    "Figure captions": {
        "appendix": ["**Supplementary Figure S1.**"],
    },
    "Data and code availability": {
        "replace_all": "data_availability_anonymized.md"
    },
}

# Build failure, not a warning: CHI desk-rejects anonymization violations.
# Commit hashes are withheld because a hash is a searchable token that leads
# straight to the public repository.
ANON_BANNED = ["Kho", "Somach", "somach", "Carl", "carl@", "fa583f6",
               "0492f57", "github.com"]

ACM_TEMPLATE = r"""\documentclass[manuscript,review,anonymous]{acmart}
%% CHI 2027 review submission: manuscript = single-column review format,
%% anonymous masks the author block and the pdf metadata.
\settopmatter{printacmref=false}
\setcopyright{none}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{calc}
\usepackage{pdflscape}
\usepackage{placeins}
\providecommand{\tightlist}{%%
  \setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
%% The manuscript numbers its own headings; stop acmart double-numbering them.
\setcounter{secnumdepth}{-1}
%% KNOWN-BAD CASE, DEMONSTRATED: without this counter the build halts at the
%% first longtable with "No counter 'none' defined" (a minimal acmart+longtable
%% document compiles, so the reference to a counter literally named `none`
%% arises only in the full document -- hyperref's longtable anchoring is the
%% suspect). Nothing displays this counter and no longtable here carries a
%% caption, so defining it is inert.
\newcounter{none}
%% DRAFT CCS concepts and keywords, not yet author-confirmed. The PCS form
%% must carry the same ones. Codes from dl.acm.org/ccs (2012 CCS).
\begin{CCSXML}
<ccs2012>
<concept>
<concept_id>10003120.10003138.10003139</concept_id>
<concept_desc>Human-centered computing~Interaction devices</concept_desc>
<concept_significance>500</concept_significance>
</concept>
<concept>
<concept_id>10003120.10003138.10003142</concept_id>
<concept_desc>Human-centered computing~Ubiquitous and mobile computing</concept_desc>
<concept_significance>300</concept_significance>
</concept>
<concept>
<concept_id>10010147.10010341</concept_id>
<concept_desc>Computing methodologies~Modeling and simulation</concept_desc>
<concept_significance>300</concept_significance>
</concept>
</ccs2012>
\end{CCSXML}
\ccsdesc[500]{Human-centered computing~Interaction devices}
\ccsdesc[300]{Human-centered computing~Ubiquitous and mobile computing}
\ccsdesc[300]{Computing methodologies~Modeling and simulation}
\keywords{silent speech interfaces, surface electromyography, ear-worn devices,
electrode placement, volume conductor modelling, forward models, cEEGrid}
\title{%(title)s}
\author{Anonymous Author(s)}
\affiliation{\institution{Anonymous}\country{Anonymous}}
\begin{document}
\begin{abstract}
%(abstract)s
\end{abstract}
\maketitle
%(body)s
\end{document}
"""


def die(msg: str) -> None:
    raise SystemExit(f"build_chi: {msg}")


def sections_of(md: str) -> list[dict]:
    parts = re.split(r"(?m)^(#{1,4} .+)$", md)
    secs = []
    for i in range(1, len(parts), 2):
        heading = parts[i].strip()
        secs.append({
            "level": len(heading) - len(heading.lstrip("#")),
            "title": heading.lstrip("#").strip(),
            "body": parts[i + 1],
        })
    return secs


def paras_of(body: str) -> list[str]:
    return [p for p in re.split(r"\n\s*\n", body)
            if p.strip() and p.strip() != "---"]


def find_one(ps: list[str], prefix: str, where: str) -> int:
    # Leading bold markers are normalised away: the humanized manuscript
    # strips some in-prose bold that the full manuscript carries, and a prefix
    # must address the same paragraph in either source.
    def norm(s: str) -> str:
        return s.lstrip().lstrip("*").lstrip()

    hits = [i for i, p in enumerate(ps) if norm(p).startswith(norm(prefix))]
    if len(hits) != 1:
        die(f"prefix {prefix!r} matched {len(hits)} paragraphs in {where!r}; "
            f"it must match exactly one. The manuscript has changed shape — "
            f"update SPEC deliberately, do not guess.")
    return hits[0]


def chi_text(name_or_text: str) -> str:
    if name_or_text.endswith(".md"):
        return (CHI / name_or_text).read_text().strip()
    return name_or_text


def apply_spec(secs: list[dict]) -> dict[str, list[str]]:
    """Mutates section bodies in place; returns {origin title: moved blocks}."""
    moved: dict[str, list[str]] = {}
    known = {s["title"] for s in secs}
    for key in SPEC:
        if key not in known:
            die(f"SPEC names a section that does not exist: {key!r}")
    for sec in secs:
        spec = SPEC.get(sec["title"])
        if not spec:
            continue
        where = sec["title"]
        if "replace_all" in spec:
            ps = paras_of(chi_text(spec["replace_all"]))
        else:
            ps = paras_of(sec["body"])
        for prefix, fname in spec.get("replace", {}).items():
            ps[find_one(ps, prefix, where)] = chi_text(fname)
        idxs = [find_one(ps, prefix, where)
                for prefix in spec.get("appendix", [])]
        if idxs:
            moved[where] = [ps[i] for i in sorted(idxs)]
            for i in sorted(idxs, reverse=True):
                ps.pop(i)
        for prefix, ins in spec.get("insert_after", []):
            ps.insert(find_one(ps, prefix, where) + 1, chi_text(ins))
        sec["body"] = "\n\n".join(ps)
    return moved


def appendix_md(secs: list[dict], moved: dict[str, list[str]]) -> str:
    """Appendices in source order: A methods, B tables, C results/discussion."""
    order = [s["title"] for s in secs if s["title"] in moved]
    groups = {"A": [], "B": [], "C": []}
    for title in order:
        g = ("A" if title.startswith("2.") else
             "B" if title == "Tables" else "C")
        groups[g].append(title)
    names = {"A": "Appendix A: Extended methods detail",
             "B": "Appendix B: Tables 1, 2 and 3",
             "C": "Appendix C: Extended results and discussion detail"}
    out = []
    for g in "ABC":
        if not groups[g]:
            continue
        out.append(f"## {names[g]}")
        if g == "B":
            for title in groups[g]:
                out.extend(moved[title])
            continue
        for n, title in enumerate(groups[g], 1):
            sub = ("Supplementary figure" if title == "Figure captions"
                   else f"Detail for §{title}")
            out.append(f"### {g}.{n} {sub}")
            out.extend(moved[title])
    return "\n\n".join(out)


def guard_numbers(generated: str, source: str) -> None:
    bad = sorted({t.rstrip(".,") for t in re.findall(r"\d[\d.,]*", generated)
                  if t.rstrip(".,") and t.rstrip(".,") not in source})
    if bad:
        die("digit tokens in the generated markdown that do not appear "
            f"verbatim in {SRC.name}: {bad}. A number is never retyped; fix "
            "the insert file to quote the source exactly.")


def guard_anonymity(tex: str) -> None:
    hits = [b for b in ANON_BANNED if b in tex]
    if hits:
        die(f"identifying strings in the output: {hits}. CHI desk-rejects "
            "anonymization violations; remove them at the source.")


def place_figures(md: str, notes: list[str]) -> tuple[str, list[tuple]]:
    """Caption paragraphs -> floats at first citation. Same algorithm as
    build_submission: resolve every anchor against one untouched string, then
    insert back to front, and refuse an out-of-citation-order result."""
    placed = []
    for n, fname in FIGURES.items():
        if not (ROOT / "figures" / fname).exists():
            die(f"missing figure file: {fname}")
        m = re.search(r"^\*\*Figure " + str(n) + r"[.:].*?(?=\n\n)",
                      md, re.S | re.M)
        if not m:
            die(f"no caption matched for Figure {n}")
        cap = " ".join(m.group(0).split())
        cap = re.sub(r"^\*\*Figure \d+[.:]\*{0,2}\s*", "", cap)
        cap = cap.replace("**", "")
        block = (f"\n\\begin{{figure}}[htbp]\n\\centering\n"
                 f"\\includegraphics[width=\\linewidth,height=0.42\\textheight,"
                 f"keepaspectratio]{{{fname}}}\n"
                 f"\\caption{{{latex_escape(cap)}}}\n"
                 f"\\end{{figure}}\n")
        md = md[:m.start()] + md[m.end():]
        placed.append((f"@@FIG{n}@@", block, n))
    anchors = []
    for tok, _blk, n in placed:
        cite = re.search(rf"Figure {n}\b", md)
        if not cite:
            die(f"Figure {n}: no citation found in the body")
        para = md.find("\n\n", cite.end())
        anchors.append((len(md) if para == -1 else para, n, tok))
    for pos, n, tok in sorted(anchors, reverse=True):
        md = md[:pos] + f"\n\n{tok}" + md[pos:]
    order = [n for _p, n, _t in sorted(anchors)]
    if order != sorted(order):
        die(f"figure placement out of citation order: {order}")
    md = re.sub(r"^## Figure captions\s*$", "", md, flags=re.M)
    notes.append(f"placed {len(placed)} figures at first citation")
    return md, placed


def pandoc(md: str, stage: Path) -> str:
    stage.write_text(md)
    cmd = ["pandoc", str(stage), "-f",
           "markdown+pipe_tables+tex_math_dollars",
           "-t", "latex", "--wrap=preserve", "--top-level-division=section"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        die("pandoc failed:\n" + r.stderr[:2000])
    return r.stdout


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(SRC))
    globals()["SRC"] = Path(ap.parse_args().src)
    notes: list[str] = []
    BUILD.mkdir(exist_ok=True)
    src_md = SRC.read_text()
    secs = sections_of(src_md)

    title = next(s["title"] for s in secs if s["level"] == 1)
    moved = apply_spec(secs)

    abstract_md = next(s["body"] for s in secs if s["title"] == "Abstract")

    body_secs = [s for s in secs
                 if s["level"] > 1 and s["title"] != "Abstract"]
    body_md = "\n\n".join(f"{'#' * s['level']} {s['title']}\n\n{s['body']}"
                          for s in body_secs)
    body_md = re.sub(r"<!-- /?TABLE:[A-Za-z0-9_]+ -->\n?", "", body_md)
    # The references are one flowing paragraph whose hard-wrapping happens to
    # put "2. " and "3. " at line starts; pandoc reads those as an ordered
    # list and swallows the neighbouring entries into two giant items.
    # Escaping the dot keeps them literal text.
    refs_at = body_md.index("## References")
    body_md = (body_md[:refs_at]
               + re.sub(r"(?m)^(\d+)\. ", r"\1\\. ", body_md[refs_at:]))
    body_md += "\n\n" + appendix_md(secs, moved)

    guard_numbers(abstract_md + "\n" + body_md, src_md)

    # Countable words: abstract + main text before References. Appendices sit
    # after References by construction; captions are lifted to floats below,
    # so they never enter this count. Table 4/5 bodies are counted, which is
    # the conservative reading of CHI's rule.
    body_md, placed = place_figures(body_md, notes)
    countable = body_md.split("## References")[0]
    n_words = len(abstract_md.split()) + len(countable.split())
    notes.append(f"countable words (abstract + body, excl. references, "
                 f"captions, appendices): {n_words}")
    if n_words > 8000:
        notes.append(f"OVER the 8000-word guidance by {n_words - 8000}; "
                     f"desk-reject threshold is 12000")

    abstract_tex = pandoc(abstract_md, BUILD / "abstract.md")
    body_tex = pandoc(body_md, BUILD / "body.md")

    for tok, block, n in placed:
        if tok not in body_tex:
            die(f"figure token for Figure {n} lost in conversion")
        body_tex = body_tex.replace(tok, block)
    for heading in ("Data and code availability", "References",
                    "Appendix A: Extended methods detail"):
        m = re.search(r"\\(sub)*section\{" + re.escape(heading), body_tex)
        if m:
            body_tex = (body_tex[:m.start()] + "\\FloatBarrier\n"
                        + body_tex[m.start():])

    tex = ACM_TEMPLATE % {"title": latex_escape(title),
                          "abstract": abstract_tex,
                          "body": body_tex}
    tex = fix_table_widths(tex, notes)
    # calc's `* \real{0.22}` column syntax dies inside acmart ("No counter
    # 'none' defined" at the first such spec, with calc loaded). eTeX
    # \dimexpr needs no package and cannot be broken by the class, so every
    # width becomes an integer-ratio \dimexpr instead.
    n_real = [0]

    def _dimexpr(m: re.Match) -> str:
        n_real[0] += 1
        return "p{\\dimexpr(%s)*%d/10000\\relax}" % (
            m.group(1), round(float(m.group(2)) * 10000))

    tex = re.sub(r"p\{\((\\linewidth - \d+\\tabcolsep)\) \* \\real\{([\d.]+)\}\}",
                 _dimexpr, tex)
    if n_real[0] == 0 or "\\real{" in tex:
        die("\\real{} column specs were not fully rewritten to \\dimexpr; "
            "pandoc's table emission has changed shape")
    notes.append(f"rewrote {n_real[0]} \\real column widths to \\dimexpr")
    tex, n_uni = fix_unicode_tex(tex)
    notes.append(f"mapped {n_uni} unicode symbols")
    # The " — " qualifier construction inside table cells ("yes — per-site")
    # is a documented AI-writing tell, and the manuscript's humanizer pass
    # ruled on prose but never touched table cells. Cells only: captions and
    # body keep whatever punctuation that pass kept deliberately.
    n_dash = [0]

    def _cells(m: re.Match) -> str:
        # pandoc's smart extension writes the em-dash as "---" in LaTeX, so
        # both spellings are covered; matching only \u2014 replaced nothing.
        body = m.group(0)
        n_dash[0] += body.count(" \u2014 ") + body.count(" --- ")
        return body.replace(" \u2014 ", "; ").replace(" --- ", "; ")

    tex = re.sub(r"\\begin\{longtable\}.*?\\end\{longtable\}", _cells, tex,
                 flags=re.S)
    if n_dash[0]:
        notes.append(f"replaced {n_dash[0]} em-dash separators inside table "
                     f"cells with semicolons")
    guard_anonymity(tex)
    TEX.write_text(tex)

    for fname in FIGURES.values():
        shutil.copy2(ROOT / "figures" / fname, BUILD / fname)

    r = subprocess.run(["tectonic", "-X", "compile", TEX.name,
                        "--outdir", str(BUILD)],
                       capture_output=True, text=True, cwd=str(BUILD))
    if r.returncode:
        print((r.stderr or r.stdout)[-3000:], file=sys.stderr)
        return 1
    shutil.copy2(BUILD / (TEX.stem + ".pdf"), PDF)
    print(f"wrote {PDF}")
    print("\nBUILD NOTES")
    for n in notes:
        print(f"  - {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
