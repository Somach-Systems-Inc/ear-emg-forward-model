#!/usr/bin/env python3
"""
Two checks against the failure that put a corrupted tissue name in Table 1.

WHY THIS EXISTS

`parse_lut()` read MIDA's latin-1 lookup table with
`path.read_text(errors="replace")`: no encoding, so the platform default, and
`errors="replace"` substitutes U+FFFD instead of raising. On a UTF-8 platform
the `0xEB` of "Skull Diploë" is an invalid start byte and became U+FFFD. On a
cp1252 platform it decoded correctly. The corruption then propagated into
`results/01_table1_conductivities.csv` and `paper/TABLE1_conductivities.csv`.

Nothing in the repository could have caught that. A tissue name is an IDENTITY,
and an identity that depends on which machine read it is not one.

CHANNEL, per the audit table in CLAUDE.md:

  check_no_mojibake   CORRECTNESS. Its independent expectation is that
                      U+FFFD never legitimately appears in this repository's
                      artifacts: it is not a character any of this data
                      contains, it is only ever the residue of a failed decode.
                      Its known-bad case is real and current, not synthetic --
                      the two Table 1 files above still carry it.

  check_io_pinned     FIDELITY-ONLY. It proves every text write declares an
                      encoding; it cannot tell you the declared encoding is the
                      right one. Its correctness partner is check_no_mojibake,
                      which reads what actually landed on disk.

KNOWN-BAD CASES THIS HAS BEEN SHOWN TO FIRE ON

  check_no_mojibake   results/01_table1_conductivities.csv (EF BF BD at the
                      "Skull Diplo-e-umlaut" of label 52), and a synthetic
                      file written for the purpose. A clean control passes.
  check_io_pinned     a synthetic source file containing
                      `open(p, "w")` with no encoding. A clean control passes.

    python src/test_encoding_integrity.py            # report
    python src/test_encoding_integrity.py --strict   # non-zero exit blocks a run
"""
from __future__ import annotations

import argparse
import ast
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REPLACEMENT = b"\xef\xbf\xbd"          # U+FFFD encoded as UTF-8
TEXT_SUFFIXES = {".csv", ".md", ".txt", ".json", ".ini", ".bib", ".py", ".yml",
                 ".yaml", ".toml"}
SCAN_DIRS = ("src", "figures")


def tracked_text_files():
    """Only tracked files. An untracked scratch file is not an artifact."""
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, check=True,
                             capture_output=True, text=True).stdout
    except Exception as e:                       # not a checkout, or no git
        raise RuntimeError(f"cannot enumerate tracked files: {e}")
    for rel in out.splitlines():
        p = ROOT / rel
        if p.suffix.lower() in TEXT_SUFFIXES and p.is_file():
            yield rel, p


def check_no_mojibake(paths=None):
    """Return [(path, offset)] for every U+FFFD found in a tracked text file.

    U+FFFD is never legitimate here. It is what a decoder emits when it was
    handed bytes it could not interpret and was told not to raise.
    """
    hits = []
    src = paths if paths is not None else tracked_text_files()
    for rel, p in src:
        raw = p.read_bytes()
        off = raw.find(REPLACEMENT)
        while off != -1:
            hits.append((rel, off))
            off = raw.find(REPLACEMENT, off + 1)
    return hits


def check_io_pinned(dirs=SCAN_DIRS, root=None):
    """Return [(path, line, call)] for text I/O that declares no encoding.

    READS matter as much as writes, and pinning writes alone is actively worse
    than pinning neither. Once results/01_label_inventory.csv is written utf-8,
    a bare open() reads it back as cp1252 on Windows and silently yields
    'Skull DiploA-tilde-guillemet' -- a NEW corruption created by the half-fix.
    Both directions or neither.

    Binary modes are skipped: they carry no encoding, correctly. write_text()
    is always text -- its first positional argument is CONTENT, not a mode,
    which is exactly how seven writes were missed on the first sweep.

    build_table1.py's IT'IS read is intentionally exempt and does not appear
    here: it decodes bytes with a utf-8-then-latin-1 fallback because that file
    is an external export whose encoding is not ours to assume.
    """
    base = Path(root) if root else ROOT
    bad = []
    for d in dirs:
        for f in sorted((base / d).glob("*.py")):
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for n in ast.walk(tree):
                if not isinstance(n, ast.Call):
                    continue
                if isinstance(n.func, ast.Name):
                    name = n.func.id
                elif isinstance(n.func, ast.Attribute):
                    name = n.func.attr
                else:
                    continue
                if name not in ("open", "write_text", "read_text"):
                    continue
                if any(k.arg == "encoding" for k in n.keywords):
                    continue
                if name in ("write_text", "read_text"):
                    bad.append((str(f.relative_to(base)), n.lineno, name))
                    continue
                mode = next((a.value for a in n.args
                             if isinstance(a, ast.Constant)
                             and isinstance(a.value, str)), None)
                for k in n.keywords:
                    if k.arg == "mode" and isinstance(k.value, ast.Constant):
                        mode = k.value.value
                if mode and "b" in mode:
                    continue
                bad.append((str(f.relative_to(base)), n.lineno,
                            f"open({mode!r})" if mode else "open() [text read]"))
    return bad


def _self_test():
    """Both checks must FIRE on a known-bad input and PASS on a clean control.

    A check that has never failed has not been demonstrated capable of failing.
    This runs in a temp directory, touches nothing in the repository, and takes
    milliseconds -- so there is no excuse for trusting a green result without it.
    """
    ok = True
    with tempfile.TemporaryDirectory() as d:
        t = Path(d)

        dirty = t / "dirty.csv"
        dirty.write_bytes(b"label,name\n52,Skull Diplo" + REPLACEMENT + b"\n")
        clean = t / "clean.csv"
        clean.write_bytes(b"label,name\n52,Skull Diplo\xc3\xab\n")

        fired = check_no_mojibake([("dirty.csv", dirty)])
        passed = check_no_mojibake([("clean.csv", clean)])
        print(f"  {'PASS' if fired else 'FAIL'}  mojibake check fires on a "
              f"synthetic U+FFFD")
        print(f"  {'PASS' if not passed else 'FAIL'}  ...and passes on the same "
              f"name encoded correctly")
        ok &= bool(fired) and not passed

        (t / "src").mkdir()
        (t / "src" / "bad.py").write_text(
            'from pathlib import Path\n'
            'def f(p):\n'
            '    with open(p, "w") as fh:\n'
            '        fh.write("x")\n'
            '    Path(p).write_text("y")\n'
            '    return Path(p).read_text()\n', encoding="utf-8")
        (t / "src" / "good.py").write_text(
            'from pathlib import Path\n'
            'def f(p):\n'
            '    with open(p, "w", encoding="utf-8") as fh:\n'
            '        fh.write("x")\n'
            '    Path(p).write_text("y", encoding="utf-8")\n'
            '    Path(p).read_text(encoding="utf-8")\n'
            '    with open(p, "rb") as fh:\n'
            '        fh.read()\n', encoding="utf-8")

        b = check_io_pinned(dirs=("src",), root=t)
        bad_hits = [x for x in b if "bad.py" in x[0]]
        good_hits = [x for x in b if "good.py" in x[0]]
        print(f"  {'PASS' if len(bad_hits) == 3 else 'FAIL'}  io-pinning check "
              f"fires on open('w'), write_text() AND a bare read "
              f"(found {len(bad_hits)}/3)")
        print(f"  {'PASS' if not good_hits else 'FAIL'}  ...and passes on pinned "
              f"I/O, ignoring binary reads")
        ok &= len(bad_hits) == 3 and not good_hits
    return ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="test_encoding_integrity.py")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero on any failure, to block a pipeline")
    ap.add_argument("--self-test-only", action="store_true")
    a = ap.parse_args(argv)

    print("ENCODING INTEGRITY")
    print("=" * 68)
    print("\n  self-test -- each check must fire before its verdict is trusted:")
    if not _self_test():
        print("\n  SELF-TEST FAILED. The checks below cannot be trusted.")
        print("=" * 68)
        return 1
    if a.self_test_only:
        print("=" * 68)
        return 0

    problems = []

    moji = check_no_mojibake()
    print(f"\n  U+FFFD in tracked text artifacts : "
          f"{len(moji)} occurrence(s)")
    if moji:
        for rel, off in moji:
            print(f"      {rel}  at byte {off}")
        problems.append(
            f"{len(moji)} U+FFFD occurrence(s) in tracked artifacts. This is "
            f"not a character this data contains; it is the residue of a "
            f"failed decode.")

    unpinned = check_io_pinned()
    print(f"  text I/O with no encoding=        : {len(unpinned)} site(s)")
    for rel, line, call in unpinned:
        print(f"      {rel}:{line}  {call}")
    if unpinned:
        problems.append(
            f"{len(unpinned)} text I/O site(s) declare no encoding, so the "
            f"bytes they produce or consume depend on the machine.")

    print("\n" + "=" * 68)
    if problems:
        print(f"  FAILED ({len(problems)}):")
        for p in problems:
            print(f"    - {p}")
        print("\n    Known outstanding: results/01_table1_conductivities.csv and")
        print("    paper/TABLE1_conductivities.csv carry U+FFFD where MIDA's LUT")
        print("    says 'Skull Diplo' + U+00EB. The read path is fixed; those two")
        print("    artifacts cannot be regenerated without")
        print("    data/itis/itis_lf_v4.2_conductivity.csv, which is not in the")
        print("    repo. This check stays RED until they are rebuilt.")
        print("=" * 68)
        return 1 if a.strict else 0

    print("  PASSED -- no U+FFFD in any tracked text artifact, and every text")
    print("  I/O site declares an encoding.")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
