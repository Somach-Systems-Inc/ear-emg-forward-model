#!/usr/bin/env python3
"""Assert no harness hardcodes electrode geometry. Run before any batch.

The 15/20 mm harness mismatch was invisible for the whole validation campaign
and silently invalidated the electrode-meshing floor, which had already been
used to size two decision thresholds. This makes that class of drift a test
failure rather than something found by reading code months later.
"""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATTERN = re.compile(r"\.dimensions\s*=\s*\[\s*[\d.]+\s*,")


def main() -> int:
    bad = []
    for f in sorted((ROOT / "src").glob("*.py")):
        if f.name == Path(__file__).name:
            continue
        for i, line in enumerate(f.read_text().splitlines(), 1):
            if PATTERN.search(line):
                bad.append(f"{f.relative_to(ROOT)}:{i}: {line.strip()}")
    if bad:
        print("FAIL: hardcoded electrode geometry found:")
        for b in bad:
            print("   " + b)
        print("\nUse config.ELECTRODE_DIAMETER_MM.")
        return 1
    print("PASS: every harness reads electrode geometry from config")
    return 0


if __name__ == "__main__":
    sys.exit(main())
