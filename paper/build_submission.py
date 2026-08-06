#!/usr/bin/env python3
r"""
Build the arXiv submission from PAPER1_full_manuscript.md.

WHY THIS IS A SCRIPT

A published artifact with no generating script is not a result, and a submission
PDF is an artifact. This emits LaTeX source and a PDF, both regenerable.

WHAT IT HAS TO FIX, because the markdown is not submission-ready as written

  1. **No figures.** The manuscript carries six caption paragraphs and zero image
     includes. Rendered naively you get six captions and no figures. Each caption
     is matched to its vector PDF in `figures/` and turned into a float.
  2. **A production note** at the top recording which working files the draft was
     assembled from. That is internal provenance and must not ship. Removed here
     rather than in the manuscript, so the manuscript stays the working document
     and this stays the submission view. Review item 46.
  3. **Anchor comments** (`<!-- TABLE:name -->`) that `manuscript_blocks.py` needs
     and a reader does not.
  4. **Table 3 is six columns of prose** and overflows a portrait text block. It
     is set landscape.

arXiv prefers LaTeX source over PDF. Both are written; submit the `.tex`.

    python paper/build_submission.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "paper" / "PAPER1_full_manuscript.md"
STAGE = ROOT / "paper" / "_build"
# Self-contained arXiv bundle: the .tex and the figures it names, with BARE
# filenames. Absolute paths compile here and nowhere else, which is exactly the
# failure mode that reaches arXiv's build farm and not the author's laptop.
BUNDLE = ROOT / "paper" / "arxiv"
TEX = BUNDLE / "ms.tex"
PDF = ROOT / "paper" / "PAPER1_submission.pdf"

# Renumbered 2026-08-06 into FIRST-CITATION order, which is what a reader
# following the text expects and what interleaved placement requires.
FIGURES = {
    1: "fig1_head_model.pdf",
    2: "fig2_sensitivity_matrix.pdf",
    3: "fig3_complementarity_map.pdf",
    4: "fig4_anisotropy_delta.pdf",
    5: "fig5_attenuation_vs_distance.pdf",
    6: "fig6_material_share_vs_fat.pdf",
    7: "fig7_suprahyoid_field.pdf",
}

# Adapted from Carl's first arXiv submission (2601.06516), kept in
# md-capstonefall25_25TPE/.../022826_ARXIV_CleanSubmissions/paper1/main.tex,
# so the two papers look like they came from the same author.
ARXIV_PREAMBLE = r"""
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{amsmath, amssymb}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{etoolbox}
\usepackage{float}
\usepackage{placeins}
\usepackage{caption}
\usepackage{subcaption}
\usepackage{microtype}
\usepackage{url}
\captionsetup{font=small,labelfont=bf}
\setlength{\LTcapwidth}{\textwidth}
\AtBeginEnvironment{longtable}{\footnotesize}
\providecommand{\tightlist}{%
  \setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
"""

# NOTE: pandoc's default template already loads xcolor and graphicx. Loading
# xcolor again with options is an option clash and kills the build.
PREAMBLE = r"""
\usepackage{etoolbox}
\usepackage{graphicx}
\usepackage{booktabs}
\usepackage{longtable}
\usepackage{array}
\usepackage{pdflscape}
\usepackage{placeins}
\usepackage{caption}
\captionsetup{font=small,labelfont=bf}
\setlength{\LTcapwidth}{\textwidth}
% Table 3 is six columns of prose; without this it overflows the text block.
\AtBeginEnvironment{longtable}{\footnotesize}
\providecommand{\tightlist}{%
  \setlength{\itemsep}{0pt}\setlength{\parskip}{0pt}}
"""


# Latin Modern has no superscript/subscript glyphs. Left as Unicode they are
# silently DROPPED from the PDF -- "mm^3" would render as "mm". That is a
# content loss a reader cannot see, so map them to real LaTeX rather than
# hoping the font copes.
UNICODE_MAP = {
    # U+2212 MINUS SIGN is absent from T1 Latin Modern. Left as-is it is
    # DROPPED, turning -1.147 into 1.147 with no warning a reader could see.
    "−": "$-$",
    "–": "--", "—": "---",
    "⁻": "$^{-}$", "⁴": "$^{4}$", "⁵": "$^{5}$",
    "⁶": "$^{6}$", "⁸": "$^{8}$", "¹": "$^{1}$",
    "³": "$^{3}$", "₀": "$_{0}$", "₁": "$_{1}$",
    "σ": "$\\sigma$", "ρ": "$\\rho$", "Δ": "$\\Delta$",
    "×": "$\\times$", "≈": "$\\approx$", "→": "$\\rightarrow$",
    "°": "$^{\\circ}$", "µ": "$\\mu$", "·": "\\textperiodcentered{}",
    "̂": "",
}


def fix_unicode(md: str) -> tuple[str, int]:
    n = sum(md.count(k) for k in UNICODE_MAP)
    for k, v in UNICODE_MAP.items():
        md = md.replace(k, v)
    # collapse the artefacts of adjacent superscripts: $^{1}$$^{4}$ -> $^{14}$
    md = re.sub(r"\$\^\{([^}]*)\}\$\$\^\{([^}]*)\}\$", r"$^{\1\2}$", md)
    md = re.sub(r"\$\^\{([^}]*)\}\$\$\^\{([^}]*)\}\$", r"$^{\1\2}$", md)
    return md, n


def preprocess(md: str) -> tuple[str, list[str]]:
    notes = []
    md, n_uni = fix_unicode(md)
    if n_uni:
        notes.append(f"mapped {n_uni} unicode super/subscripts and symbols to "
                     f"LaTeX (they render as nothing otherwise)")

    # 1. production note -- internal provenance, must not ship
    prod = re.search(r"\*Draft manuscript assembled.*?METHODS_LOG\.md`\.\*\n",
                     md, re.S)
    if prod:
        md = md.replace(prod.group(0), "")
        notes.append("removed the production note at the top (review item 46)")

    # 2. anchor comments
    n_anchor = len(re.findall(r"<!-- /?TABLE:[A-Za-z0-9_]+ -->", md))
    md = re.sub(r"<!-- /?TABLE:[A-Za-z0-9_]+ -->\n?", "", md)
    if n_anchor:
        notes.append(f"stripped {n_anchor} manuscript_blocks anchor comments")

    # 3. author block -> metadata, so LaTeX gets a real \author
    lines = md.split("\n")
    title = lines[0].lstrip("# ").strip()
    body_start = next(i for i, l in enumerate(lines) if l.strip() == "---")
    author_block = [l for l in lines[1:body_start] if l.strip()]
    author_lines = [l.replace("**", "").strip() for l in author_block]
    author = "AUTHORBLOCK"
    md = "\n".join(lines[body_start + 1:])

    # 4. figures: caption paragraph -> float with the vector PDF
    placed = []
    for n, fname in FIGURES.items():
        path = ROOT / "figures" / fname
        if not path.exists():
            notes.append(f"MISSING figure file for Figure {n}: {fname}")
            continue
        # caption paragraph: starts **Figure N.** ... up to a blank line
        pat = re.compile(r"^\*\*Figure " + str(n) + r"[.:].*?(?=\n\n)",
                         re.S | re.M)
        m = pat.search(md)
        if not m:
            notes.append(f"NO CAPTION MATCHED for Figure {n}; figure not placed")
            continue
        cap = " ".join(m.group(0).split())
        cap = re.sub(r"^\*\*Figure \d+[.:]\*{0,2}\s*", "", cap)
        cap = cap.replace("**", "")
        block = (f"\n\\begin{{figure}}[htbp]\n\\centering\n"
                 f"\\includegraphics[width=\\linewidth,height=0.42\\textheight,"
                 f"keepaspectratio]{{{fname}}}\n"
                 f"\\caption{{{latex_escape(cap)}}}\n"
                 f"\\end{{figure}}\n")
        md = md[:m.start()] + f"@@FIG{n}@@" + md[m.end():]
        placed.append((f"@@FIG{n}@@", block, n))
    if INLINE[0]:
        # Move each float from the captions section to just after the paragraph
        # that first cites it. Floats cannot travel backwards, so a figure whose
        # caption sits at the end of the document can never appear beside the
        # text that discusses it.
        for tok, _blk, n in placed:
            md = md.replace(tok, "")
            cite = re.search(rf"Figure {n}\b", md)
            if not cite:
                notes.append(f"Figure {n}: no citation found, left at the end")
                md += f"\n{tok}\n"
                continue
            para = md.find("\n\n", cite.end())
            para = len(md) if para == -1 else para
            md = md[:para] + f"\n\n{tok}" + md[para:]
        notes.append("figures moved to their first citation (interleaved)")
        md = re.sub(r"^## Figure captions\s*$", "", md, flags=re.M)
    notes.append(f"placed {len(placed)} of {len(FIGURES)} figures")
    return md, (title, author_lines, placed, notes)


def latex_escape(s: str) -> str:
    """Escape caption text for LaTeX, LEAVING $...$ MATH ALONE.

    fix_unicode() has already turned characters like U+00D7 into `$\\times$`.
    Escaping that blindly produces `$\\textbackslash{}times$`, which renders as
    literal garbage inside a caption -- caught in Figure 2 as `$\\{}times$`.
    Math spans are therefore split out and passed through untouched.
    """
    def esc(chunk: str) -> str:
        for a, b in (("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
                     ("#", r"\#"), ("_", r"\_"),
                     ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}")):
            chunk = chunk.replace(a, b)
        return chunk.replace("`", "")

    parts = re.split(r"(\$[^$]*\$)", s)
    return "".join(p if p.startswith("$") and p.endswith("$") and len(p) > 1
                   else esc(p) for p in parts)


INLINE = [False]
STYLE = ["plain"]


def main() -> int:
    import shutil
    import argparse as _ap
    _p = _ap.ArgumentParser()
    _p.add_argument("--inline-figures", action="store_true")
    _p.add_argument("--style", default="plain", choices=["plain", "arxiv"])
    _p.add_argument("--out-stem", default="PAPER1_submission")
    _p.add_argument("--src", default=str(SRC))
    _a = _p.parse_args()
    INLINE[0] = _a.inline_figures
    STYLE[0] = _a.style
    globals()["SRC"] = Path(_a.src)
    globals()["PDF"] = ROOT / "paper" / f"{_a.out_stem}.pdf"
    globals()["BUNDLE"] = ROOT / "paper" / f"arxiv_{_a.out_stem}"
    globals()["TEX"] = BUNDLE / "ms.tex"
    STAGE.mkdir(exist_ok=True)
    BUNDLE.mkdir(exist_ok=True)
    for fn in FIGURES.values():
        src = ROOT / "figures" / fn
        if src.exists():
            shutil.copy2(src, BUNDLE / fn)
    md = SRC.read_text()
    md, (title, author_lines, placed, notes) = preprocess(md)

    stage_md = STAGE / "body.md"
    stage_md.write_text(md)
    pre = STAGE / "preamble.tex"
    pre.write_text(ARXIV_PREAMBLE if STYLE[0] == "arxiv" else PREAMBLE)

    cmd = ["pandoc", str(stage_md), "-f",
           "markdown+pipe_tables+implicit_figures+tex_math_dollars",
           "-t", "latex", "-s", "--wrap=preserve",
           # Without this every `##` becomes \subsection and the whole hierarchy
           # sits one level too deep. The manuscript numbers its own headings, so
           # sections stay unnumbered and no double numbering appears.
           "--top-level-division=section",
           "-V", "documentclass=article", "-V", "fontsize=11pt",
           "-V", ("papersize=a4" if STYLE[0] == "arxiv" else "papersize=letter"),
           "-V", "geometry:margin=1in", "-V", "colorlinks=true",
           "-M", f"title={title}", "-M", "author=AUTHORBLOCK",
           "-M", "date=", "-H", str(pre), "-o", str(TEX)]
    print("$ " + " ".join(cmd[:8]) + " ...")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        print(r.stderr[:2000], file=sys.stderr)
        return 1

    tex = TEX.read_text()
    # pandoc escapes metadata, so a literal backslash-backslash reaches the page
    # and the author line overruns the text block. Substitute a real multi-line
    # \author{}. A LaTeX line break is exactly two backslashes; re.sub also
    # interprets backslashes in the replacement, so pass a function to bypass
    # that rather than counting escapes.
    real = "\\author{" + " \\\\ ".join(author_lines) + "}"
    tex = re.sub(r"\\author\{[^}]*\}", lambda _m: real, tex, count=1)
    tex = re.sub(r"pdfauthor=\{[^}]*\}",
                 "pdfauthor={" + author_lines[0] + "}", tex, count=1)
    # splice the figure floats back in
    for token, block, n in placed:
        if token not in tex:
            notes.append(f"figure token for Figure {n} lost in conversion")
            continue
        tex = tex.replace(token, block)
    # Floats cannot move backwards. The caption paragraphs sit late in the
    # document, so without a barrier every figure drifts past the reference list
    # and the PDF ends with figures interleaved among the references.
    for heading in ("Data and code availability", "References"):
        m = re.search(r"\\(sub)*section\{" + re.escape(heading) + r"\}", tex)
        if m:
            tex = tex[:m.start()] + "\\FloatBarrier\n" + tex[m.start():]
            notes.append(f"flushed pending floats before '{heading}'")
        else:
            notes.append(f"NO BARRIER APPLIED: heading '{heading}' not matched")
    TEX.write_text(tex)
    print(f"wrote {TEX}")

    print("$ tectonic -X compile ...")
    r = subprocess.run(["tectonic", "-X", "compile", TEX.name,
                        "--outdir", str(BUNDLE)],
                       capture_output=True, text=True, cwd=str(BUNDLE))
    if r.returncode:
        tail = (r.stderr or r.stdout)[-3000:]
        print(tail, file=sys.stderr)
        return 1

    built = BUNDLE / (TEX.stem + ".pdf")
    if built.exists():
        shutil.copy2(built, PDF)
    print(f"\nwrote {PDF}")
    print(f"arXiv bundle: {BUNDLE}  ({len(list(BUNDLE.glob('*')))} files)")
    print("\nBUILD NOTES")
    for n in notes:
        print(f"  - {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
