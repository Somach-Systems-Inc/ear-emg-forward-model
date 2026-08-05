#!/usr/bin/env python3
r"""
Anchored writes into the manuscript. The ONLY sanctioned way to regenerate a
table or generated section.

WHY THIS EXISTS
---------------
On 2026-08-06 a table regenerator matched rows by their leading label --
`| temporalis |`, `| mentalis |`, and so on -- and rewrote every line in the
document that started that way. §3.3's fat-contrast table shares those row
labels with Table 4. It was overwritten twice, on the belief that the manuscript
held two copies of Table 4. It never did.

Both times the rewrite was reported as a SAFEGUARD: "rebuilt from the CSV rather
than edited by hand". Generating from source is the right instinct and it is not
sufficient, because it says nothing about *where* the generated text lands. The
corrupted table traced perfectly to a real source file; every number in it was
real; it was simply the wrong table's numbers in the right table's place. No
check keyed to provenance can see that.

So: a generator addresses a block by NAME, never by content. If the anchor is
missing, or appears more than once, this raises. It does not fall back to a
search, because a fallback search is exactly the failure being prevented.

    from manuscript_blocks import replace_block
    replace_block("fat_contrast", table_markdown)

Anchors look like:

    <!-- TABLE:fat_contrast -->
    ...generated content, never hand-edited...
    <!-- /TABLE:fat_contrast -->
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANUSCRIPT = ROOT / "paper" / "PAPER1_full_manuscript.md"


class AnchorError(RuntimeError):
    """Raised when a block cannot be addressed unambiguously by name."""


def _anchors(name: str) -> tuple[str, str]:
    return f"<!-- TABLE:{name} -->", f"<!-- /TABLE:{name} -->"


def block_names(path: Path | None = None) -> list[str]:
    text = (path or MANUSCRIPT).read_text()
    return re.findall(r"<!-- TABLE:([A-Za-z0-9_]+) -->", text)


def audit(path: Path | None = None) -> list[str]:
    """Structural problems with the anchor set itself. Empty list == clean."""
    p = path or MANUSCRIPT
    text = p.read_text()
    problems = []
    opens = re.findall(r"<!-- TABLE:([A-Za-z0-9_]+) -->", text)
    closes = re.findall(r"<!-- /TABLE:([A-Za-z0-9_]+) -->", text)
    for n in sorted(set(opens)):
        if opens.count(n) > 1:
            problems.append(f"{n}: opening anchor appears {opens.count(n)}x")
        if closes.count(n) != 1:
            problems.append(f"{n}: {closes.count(n)} closing anchors")
    for n in sorted(set(closes) - set(opens)):
        problems.append(f"{n}: closing anchor with no opening anchor")
    for n in sorted(set(opens)):
        o, c = _anchors(n)
        if o in text and c in text and text.index(o) > text.index(c):
            problems.append(f"{n}: closing anchor precedes opening anchor")
    return problems


def read_block(name: str, path: Path | None = None) -> str:
    p = path or MANUSCRIPT
    text = p.read_text()
    o, c = _anchors(name)
    if text.count(o) != 1 or text.count(c) != 1:
        raise AnchorError(
            f"block {name!r}: found {text.count(o)} opening and "
            f"{text.count(c)} closing anchors in {p.name}; need exactly 1 each. "
            f"Refusing to guess which block was meant.")
    return text[text.index(o) + len(o):text.index(c)].strip("\n")


def replace_block(name: str, content: str, path: Path | None = None) -> None:
    """Replace ONLY what lies between this block's anchors.

    Raises rather than falling back to a content search. A generator that
    cannot find its anchor has a bug in the manuscript's structure, and
    searching for something that looks like its table is how §3.3 was lost.
    """
    p = path or MANUSCRIPT
    text = p.read_text()
    o, c = _anchors(name)
    n_o, n_c = text.count(o), text.count(c)
    if n_o != 1 or n_c != 1:
        known = sorted(set(block_names(p)))
        raise AnchorError(
            f"block {name!r}: found {n_o} opening and {n_c} closing anchors in "
            f"{p.name}; need exactly 1 each.\n"
            f"  known blocks: {known}\n"
            f"  NOT falling back to a content search -- that is the bug this "
            f"module exists to prevent.")
    i = text.index(o) + len(o)
    j = text.index(c)
    if j < i:
        raise AnchorError(f"block {name!r}: closing anchor precedes opening")
    p.write_text(text[:i] + "\n" + content.strip("\n") + "\n" + text[j:])


if __name__ == "__main__":
    import sys
    bad = audit()
    for b in bad:
        print(f"  {b}")
    print(f"{len(block_names())} anchored blocks; "
          f"{len(bad)} structural problems")
    sys.exit(1 if bad else 0)
