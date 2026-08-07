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
    7: "fig7_gap_decomposition.pdf",
    8: "fig8_distance_mechanism.pdf",
    9: "fig9_suprahyoid_field.pdf",
    10: "fig10_advantage_cascade.pdf",
    11: "fig11_two_axis_envelope.pdf",
}

# Adapted from Carl's first arXiv submission (2601.06516), kept in
# md-capstonefall25_25TPE/.../022826_ARXIV_CleanSubmissions/paper1/main.tex,
# so the two papers look like they came from the same author.
ARXIV_PREAMBLE = r"""
\usepackage{arxiv}
\usepackage[T1]{fontenc}
\usepackage{textcomp}
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
\usepackage{textcomp}
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



# Applied to the LATEX, not the markdown. Routing these through markdown lets
# pandoc re-parse "$-$" as inline math; with two of them in a sentence it pairs
# the wrong dollars and swallows every space between, turning
# "-1.15 dB with an interval of [-1.45" into one run-together math blob.
# Text-mode commands avoid math entirely and give the right glyphs.
TEX_UNICODE = {
    "\u2212": r"\textminus{}",
    "\u00d7": r"\texttimes{}",
    "\u00b0": r"\textdegree{}",
    "\u00b5": r"\textmu{}",
    "\u00b7": r"\textperiodcentered{}",
    "\u2248": r"$\approx$",
    "\u2192": r"$\rightarrow$",
    "\u03c3": r"$\sigma$",
    "\u03c1": r"$\rho$",
    "\u0394": r"$\Delta$",
    "\u207b": r"\textsuperscript{\textminus}",
    "\u00b9": r"\textsuperscript{1}",
    "\u00b3": r"\textsuperscript{3}",
    "\u2074": r"\textsuperscript{4}",
    "\u2075": r"\textsuperscript{5}",
    "\u2076": r"\textsuperscript{6}",
    "\u2078": r"\textsuperscript{8}",
    "\u2080": r"\textsubscript{0}",
    "\u2081": r"\textsubscript{1}",
    "\u0302": "",
}


def fix_unicode_tex(tex):
    n = sum(tex.count(k) for k in TEX_UNICODE)
    for k, v in TEX_UNICODE.items():
        tex = tex.replace(k, v)
    # merge adjacent superscripts: \textsuperscript{1}\textsuperscript{4}
    tex = re.sub(r"\\textsuperscript\{([^}]*)\}\\textsuperscript\{([^}]*)\}",
                 r"\\textsuperscript{\1\2}", tex)
    tex = re.sub(r"\\textsuperscript\{([^}]*)\}\\textsuperscript\{([^}]*)\}",
                 r"\\textsuperscript{\1\2}", tex)
    return tex, n


def preprocess(md: str) -> tuple[str, list[str]]:
    notes = []

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
        # ANCHORS ARE COMPUTED BEFORE ANY INSERTION, THEN APPLIED BACK TO FRONT.
        #
        # The first version inserted each token as it went. Figures 2 and 3 are
        # cited in one sentence -- "the sensitivity matrix is given in Figure 2,
        # and the per-muscle verdicts in Figure 3" -- so both resolved to the
        # same paragraph break. Inserting @@FIG2@@ there created a NEW "\n\n"
        # immediately after the paragraph, which Figure 3's search then found
        # first, so @@FIG3@@ landed in front of @@FIG2@@. LaTeX numbers floats
        # by order of appearance, so the complementarity map was printed as
        # "Figure 2" while the body told the reader Figure 2 was the sensitivity
        # matrix. The captions and images stayed together; only the numbering
        # was wrong, which is exactly the kind of defect that survives a
        # proofread.
        #
        # Resolving every anchor against the same untouched string, then
        # inserting from the end backwards, makes the result independent of
        # insertion order. Ties at one anchor are broken by figure number.
        for tok, _blk, n in placed:
            md = md.replace(tok, "")
        anchors = []
        for tok, _blk, n in placed:
            cite = re.search(rf"Figure {n}\b", md)
            if not cite:
                notes.append(f"Figure {n}: no citation found, left at the end")
                anchors.append((len(md), n, tok))
                continue
            para = md.find("\n\n", cite.end())
            anchors.append((len(md) if para == -1 else para, n, tok))
        for pos, n, tok in sorted(anchors, reverse=True):
            md = md[:pos] + f"\n\n{tok}" + md[pos:]
        order = [n for _p, n, _t in sorted(anchors)]
        if order != sorted(order):
            raise SystemExit(
                f"figure placement is out of citation order: {order}. "
                f"LaTeX numbers floats by appearance, so this would print "
                f"wrong figure numbers. Fix the citation order in the "
                f"manuscript, do not reorder FIGURES.")
        notes.append(f"figures moved to their first citation, in order {order}")
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
    out = "".join(p if p.startswith("$") and p.endswith("$") and len(p) > 1
                  else esc(p) for p in parts)
    # MARKDOWN EMPHASIS SURVIVES INTO THE CAPTION AND MUST BE CONVERTED.
    # Captions are lifted out of the markdown BEFORE pandoc runs, so pandoc
    # never sees them and never converts their `*italics*`. The bold markers
    # were already stripped by the caller, which made the omission of the
    # single-asterisk case easy to miss: Figure 6 shipped the literal string
    # "*smaller*" into the PDF. Done after escaping, which is safe because none
    # of the escapes above can introduce an asterisk.
    return re.sub(r"\*([^*\n]+)\*", r"\\emph{\1}", out)


INLINE = [False]
STYLE = ["plain"]



def fix_table_widths(tex, notes):
    """Give wide-prose columns the room they need.

    pandoc splits a five-column table 20/20/20/20/20 regardless of content, so
    Table 4's Verdict column ("jaw, site-robust but orientation-dependent")
    wrapped onto three lines and stranded the word "axes" on its own row. The
    widths below are allocated by what each column actually holds.
    """
    import re as _re
    WIDTHS = {
        # First column widened from 0.17 to 0.20 in Table 4 and set to 0.20 in
        # Table 5: "sternocleidomastoid" at 9 pt overflowed the muscle column
        # by 1.4 and 2.7 pt. Under a millimetre, and invisible in tectonic's
        # output, but pdflatex reports it as an overfull hbox and it is free
        # to fix.
        "Gap (dB), envelope": [0.20, 0.17, 0.12, 0.16, 0.35],   # Table 4
        "Best single site":   [0.20, 0.18, 0.10, 0.18, 0.13, 0.21],  # Table 5
        "As modelled":        [0.22, 0.16, 0.18, 0.14, 0.30],   # fat contrast
        "What sets it":       [0.04, 0.14, 0.19, 0.11, 0.17, 0.35],  # Table 3
    }
    for marker, w in WIDTHS.items():
        i = tex.find(marker)
        if i < 0:
            continue
        start = tex.rfind("\\begin{longtable}", 0, i)
        end = tex.find("@{}}", start)
        if start < 0 or end < 0:
            continue
        spec = "\\begin{longtable}[]{@{}\n" + "\n".join(
            "  >{\\raggedright\\arraybackslash}p{(\\linewidth - "
            f"{2*len(w)}\\tabcolsep) * \\real{{{x:.4f}}}}}" for x in w)
        tex = tex[:start] + spec + tex[end:]
        notes.append(f"re-allocated column widths for the '{marker}' table")
    return tex


# Extensions arXiv's AutoTeX will accept in a source package. Anything else in
# the bundle is either an accident or a licence problem, so the check is an
# allowlist, matching .githooks/pre-commit.
BUNDLE_EXT = {".tex", ".sty", ".pdf", ".bbl", ".bib", ".cls"}
# Files that live in the working bundle for convenience but must NOT be
# uploaded. ms.pdf is the compiled output; shipping it beside the source is
# dead weight at best and confuses AutoTeX at worst.
NOT_UPLOADED = {"ms.pdf"}


def harden_bundle(notes) -> int:
    """Make the bundle a faithful, self-contained arXiv source package.

    THE DEFECT THIS EXISTS FOR. The bundle directory was written but never
    cleaned, so it accumulated. After the figures were renumbered it still
    carried `fig7_suprahyoid_field.pdf` from the previous numbering: a
    licensed-geometry-derived render, orphaned from every caption, sitting in
    the directory that gets uploaded. Nothing referenced it and nothing
    complained. Stale files in an upload directory are the same class of
    failure as the *.geo leak, so this prunes by allowlist and says what it
    removed.
    """
    import shutil
    import tarfile
    import tempfile

    tex = TEX.read_text()
    referenced = set(re.findall(r"\\includegraphics\[[^]]*\]\{([^}]+)\}", tex))
    keep = referenced | {TEX.name} | ({"arxiv.sty"} if STYLE[0] == "arxiv" else set())

    # --- prune anything not referenced
    stale = [p for p in sorted(BUNDLE.iterdir())
             if p.is_file() and p.name not in keep and p.name not in NOT_UPLOADED]
    for p in stale:
        p.unlink()
    if stale:
        notes.append("PRUNED " + str(len(stale)) + " stale bundle file(s): "
                     + ", ".join(p.name for p in stale))

    # --- everything the tex names must actually be there
    missing = sorted(f for f in referenced if not (BUNDLE / f).exists())
    if missing:
        print(f"\nBUNDLE INCOMPLETE: ms.tex references {missing} which are not "
              f"in {BUNDLE}. arXiv would fail to build this.", file=sys.stderr)
        return 1

    # --- no absolute paths: they compile here and nowhere else
    abs_refs = [f for f in referenced if f.startswith("/")]
    abs_any = re.findall(r"(?:/Users/|/home/|[A-Z]:\\\\)\S*", tex)
    if abs_refs or abs_any:
        print(f"\nABSOLUTE PATHS IN ms.tex: {abs_refs or abs_any[:3]}. "
              f"This compiles on this laptop only.", file=sys.stderr)
        return 1

    # --- allowlist the extensions
    bad = [p.name for p in BUNDLE.iterdir()
           if p.is_file() and p.suffix.lower() not in BUNDLE_EXT]
    if bad:
        print(f"\nNOT UPLOADABLE: {bad} are not on the arXiv source allowlist "
              f"{sorted(BUNDLE_EXT)}.", file=sys.stderr)
        return 1

    # --- CLEAN-ROOM COMPILE. Copying to a directory outside the repo is the
    # only way to prove the bundle does not silently depend on a sibling file.
    # Building in place cannot detect that, which is the whole failure mode.
    upload = sorted(p for p in BUNDLE.iterdir()
                    if p.is_file() and p.name not in NOT_UPLOADED)
    with tempfile.TemporaryDirectory() as td:
        room = Path(td) / "cleanroom"
        room.mkdir()
        for p in upload:
            shutil.copy2(p, room / p.name)
        r = subprocess.run(["tectonic", "-X", "compile", TEX.name,
                            "--outdir", str(room)],
                           capture_output=True, text=True, cwd=str(room))
        if r.returncode:
            print("\nCLEAN-ROOM COMPILE FAILED. The bundle is not "
                  "self-contained.\n" + (r.stderr or r.stdout)[-2500:],
                  file=sys.stderr)
            return 1
        # PAGE COUNT VIA pdfinfo, NOT A REGEX. Counting /Type /Page in the
        # bytes returned 0 here, because tectonic writes object streams and
        # the page objects are compressed out of reach. A check that silently
        # reports 0 is worse than no check.
        room_pdf = room / (TEX.stem + ".pdf")

        def _pages(f):
            q = subprocess.run(["pdfinfo", str(f)], capture_output=True,
                               text=True)
            for line in q.stdout.splitlines():
                if line.startswith("Pages:"):
                    return int(line.split()[1])
            return None

        pages, repo_pages = _pages(room_pdf), _pages(PDF)
        if pages is None or repo_pages is None:
            notes.append("clean-room compile OK outside the repo "
                         f"({len(upload)} source files); page count not "
                         "checked, pdfinfo unavailable")
        elif pages != repo_pages:
            print(f"\nCLEAN-ROOM PDF DIFFERS: {pages} pages outside the repo "
                  f"against {repo_pages} inside it. Something in the build is "
                  f"reading a file that is not in the bundle.", file=sys.stderr)
            return 1
        else:
            notes.append(f"clean-room compile OK outside the repo, {pages} "
                         f"pages matching the in-repo build, {len(upload)} "
                         f"source files")

        # --- every font must be embedded or arXiv rejects the PDF
        q = subprocess.run(["pdffonts", str(room_pdf)], capture_output=True,
                           text=True)
        # PARSE FROM THE RIGHT. Two earlier versions of this check were
        # wrong and both reported healthy PDFs as broken.
        #   split()[3]      -- wrong, because type names contain spaces
        #                      ("Type 1C", "CID TrueType").
        #   fixed offsets   -- wrong, because a long font name overflows the
        #                      36-char name column and shifts every field
        #                      right. "CAFSZL+LatinModernMath-Regular-
        #                      Identity-H" does exactly that, and it was
        #                      reported as unembedded while pdffonts said yes.
        # The trailing five fields are always emb, sub, uni, object, ID
        # whatever the name and type widths do, so index from the end.
        loose, t3, n = [], [], 0
        for l in q.stdout.splitlines()[2:]:
            f = l.split()
            if len(f) < 6:
                continue
            n += 1
            if f[-5].lower() != "yes":
                loose.append(f[0])
            if " Type 3 " in l[len(f[0]):]:
                t3.append(f[0])
        if loose:
            print(f"\nFONTS NOT EMBEDDED: {loose}", file=sys.stderr)
            return 1
        if t3:
            print(f"\nTYPE 3 FONTS: {t3}. Regenerate the figure with "
                  f"pdf.fonttype 42.", file=sys.stderr)
            return 1
        if n:
            notes.append(f"all {n} fonts embedded, no Type 3")

        # --- SECOND ENGINE. tectonic is XeTeX; arXiv runs pdflatex. Verifying
        # one engine says nothing about the other, and the one that matters is
        # the one we do not use locally. A fresh copy is needed because the
        # tectonic run above left aux files in `room`.
        pdftex = shutil.which("pdflatex") or shutil.which(
            "pdflatex", path="/Library/TeX/texbin")
        if not pdftex:
            notes.append("pdflatex NOT FOUND, so the engine arXiv actually "
                         "uses is unverified; install basictex to close this")
        else:
            room2 = Path(td) / "pdflatex"
            room2.mkdir()
            for p_ in upload:
                shutil.copy2(p_, room2 / p_.name)
            for _pass in (1, 2):     # longtable needs two to settle widths
                r2 = subprocess.run(
                    [pdftex, "-interaction=nonstopmode", "-halt-on-error",
                     TEX.name], capture_output=True, text=True, cwd=str(room2))
                if r2.returncode:
                    log = (room2 / (TEX.stem + ".log"))
                    tail = log.read_text(errors="replace")[-2500:] \
                        if log.exists() else (r2.stdout or "")[-2500:]
                    print(f"\nPDFLATEX FAILED on pass {_pass}. arXiv builds "
                          f"with this engine, so this is a submission "
                          f"blocker.\n{tail}", file=sys.stderr)
                    return 1
            log = (room2 / (TEX.stem + ".log")).read_text(errors="replace")
            over = log.count("Overfull \\hbox")
            p2 = _pages(room2 / (TEX.stem + ".pdf"))
            notes.append(f"pdflatex compile OK, {p2} pages, {over} overfull "
                         f"hbox(es); page count may differ from tectonic's "
                         f"{pages} because the engines break floats "
                         f"differently, which is not an error")

    # --- the tarball arXiv actually wants
    tgz = ROOT / "paper" / f"{PDF.stem}_arxiv.tar.gz"
    with tarfile.open(tgz, "w:gz") as tf:
        for p in upload:
            tf.add(p, arcname=p.name)
    mb = tgz.stat().st_size / 1e6
    notes.append(f"wrote {tgz.name} ({mb:.2f} MB, {len(upload)} files); "
                 f"arXiv's limit is 50 MB")
    if mb > 50:
        print(f"\nTARBALL TOO LARGE: {mb:.1f} MB exceeds arXiv's 50 MB limit.",
              file=sys.stderr)
        return 1

    return 0


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
    sty = ROOT / "paper" / "arxiv.sty"
    if sty.exists() and STYLE[0] == "arxiv":
        shutil.copy2(sty, BUNDLE / "arxiv.sty")
    md = SRC.read_text()
    md, (title, author_lines, placed, notes) = preprocess(md)

    stage_md = STAGE / "body.md"
    stage_md.write_text(md)
    pre = STAGE / "preamble.tex"
    pre.write_text(ARXIV_PREAMBLE if STYLE[0] == "arxiv" else PREAMBLE)

    geom = [] if STYLE[0] == "arxiv" else ["-V", "geometry:margin=1in"]
    cmd = ["pandoc", str(stage_md), "-f",
           "markdown+pipe_tables+implicit_figures+tex_math_dollars",
           "-t", "latex", "-s", "--wrap=preserve",
           # Without this every `##` becomes \subsection and the whole hierarchy
           # sits one level too deep. The manuscript numbers its own headings, so
           # sections stay unnumbered and no double numbering appears.
           "--top-level-division=section",
           "-V", "documentclass=article", "-V", "fontsize=11pt",
           "-V", ("papersize=a4" if STYLE[0] == "arxiv" else "papersize=letter"),
 "-V", "colorlinks=true",
           *geom, "-M", f"title={title}", "-M", "author=AUTHORBLOCK",
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
    # Abstract as a real environment, matching the first arXiv paper, rather
    # than a numbered subsection.
    m = re.search(r"\\(sub)*section\{Abstract\}(\\label\{[^}]*\})?", tex)
    if m:
        nxt = re.search(r"\\(sub)*section\{", tex[m.end():])
        end = m.end() + (nxt.start() if nxt else 0)
        tex = (tex[:m.start()] + "\\begin{abstract}\n" + tex[m.end():end]
               + "\n\\end{abstract}\n\n" + tex[end:])
        notes.append("abstract set as a real abstract environment")

    tex = fix_table_widths(tex, notes)
    tex, n_uni = fix_unicode_tex(tex)
    notes.append(f"mapped {n_uni} unicode symbols to text-mode LaTeX "
                 f"(after every insertion, so the author block is covered too)")
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

    rc = harden_bundle(notes)
    print(f"arXiv bundle: {BUNDLE}  ({len(list(BUNDLE.glob('*')))} files)")
    print("\nBUILD NOTES")
    for n in notes:
        print(f"  - {n}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
