#!/usr/bin/env python3
"""
Every production script must actually INVOKE its guards. Enumerated, not
trusted.

WHY THIS EXISTS

"Written but never wired" has now happened four times, and each one was found
by accident rather than by a check:

  1. `preflight.check_solve_output()` — written, documented in METHODS_LOG as
     a "permanent guard" that "reads fields_summary.txt after every solve",
     called by nothing. A cavity solve warned at 11.90% and nothing said so.
  2. `solve_invariants` — `03a_boundary_run.py` referenced it zero times, so
     no invariant ran on any boundary solve. It printed a mesh decision for
     the whole paper from solves that violate charge conservation.
  3. `preflight.check_conductivity_range()` — same, no caller.
  4. **Invariant 2 itself** — `check_solve_plateau()` is what production
     calls, and it only ever raised INVARIANT 1. Invariant 2 lived in
     `check_solve()`, which nothing calls. The one test designed to catch a
     leaking boundary was unreachable from production while a leaking
     boundary went undetected.

`.gitignore` failed the same way, as a denylist that only blocked what someone
had thought of. An allowlist fixed that. This is the same fix for guards:
enumerate what production MUST call and fail if it does not.

WHY IT PARSES THE AST AND NOT THE TEXT

Grepping for `check_solve_output` matches a mention in a comment, a docstring,
a disabled line, or an import that is never used — all of which look like
coverage and provide none. This resolves actual `ast.Call` nodes, so only a
real invocation counts.

    python src/test_guard_coverage.py
    python src/test_guard_coverage.py --strict     # non-zero exit blocks a run
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

# A script is PRODUCTION if it does either of these. Both are resolved from
# the AST, so a script cannot opt out by being renamed.
SOLVE_CALLS = {"run_simnibs", "tdcs"}

# Guards a solving script must invoke. Any one name in a group satisfies it,
# because the codebase has more than one legitimate entry point per guard.
REQUIRED = {
    "calibration (reads the solver's own fields_summary.txt)":
        {"check_solve_output", "read_calibration"},
    "invariants 1 and 2 (radius plateau, whole-domain charge conservation)":
        {"check_solve_plateau", "check_solve"},
    "conductivity span gate (sigma_max/sigma_min)":
        {"check_conductivity_range"},
}

# Scripts that solve deliberately WITHOUT the full guard set, each with a
# reason. Anything not listed here must comply. Keep this list short and
# justified; it is the escape hatch and it should feel expensive to use.
EXEMPT = {
    "val_reciprocity.py": "sphere validation against an analytic oracle; the "
                          "oracle IS the check, and it predates the guards",
    "val_rdm_mag.py": "sphere lead-field harness, validated against the "
                      "analytic solution rather than the invariants",
    "measure_floor_multidraw.py": "sphere realisation noise; every draw is "
                                  "compared against the analytic oracle",
    "03a2_boundary_probe.py": "single diagnostic probe whose entire purpose "
                              "is to READ a calibration value, not gate on it",
}


def calls_in(tree):
    """Every function name actually invoked, resolved from Call nodes."""
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute):
                out.add(f.attr)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="test_guard_coverage.py")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero on any gap, to block a production run")
    a = ap.parse_args(argv)

    failures, checked, exempted = [], [], []

    for p in sorted(SRC.glob("*.py")):
        if p.name.startswith("test_"):
            continue
        try:
            tree = ast.parse(p.read_text())
        except SyntaxError as e:
            failures.append((p.name, [f"does not parse: {e}"]))
            continue

        called = calls_in(tree)
        if not (called & SOLVE_CALLS):
            continue                      # not a solving script

        if p.name in EXEMPT:
            exempted.append((p.name, EXEMPT[p.name]))
            continue

        missing = [label for label, names in REQUIRED.items()
                   if not (called & names)]
        checked.append(p.name)
        if missing:
            failures.append((p.name, missing))

    print("GUARD COVERAGE")
    print("=" * 68)
    print(f"  solving scripts checked : {len(checked)}")
    for n in checked:
        print(f"      {n}")
    if exempted:
        print(f"  exempt ({len(exempted)}), each with a recorded reason:")
        for n, why in exempted:
            print(f"      {n}\n          {why}")

    print()
    if failures:
        print(f"  FAILED — {len(failures)} script(s) solve without their guards:")
        for name, missing in failures:
            print(f"\n    {name}")
            for m in missing:
                print(f"      MISSING: {m}")
        print()
        print("  A guard that is written but not invoked is not a guard. Wire")
        print("  it in, or add the script to EXEMPT with a reason that would")
        print("  survive a reviewer reading it.")
        print("=" * 68)
        return 1 if a.strict else 0

    print("  PASSED — every solving script invokes calibration reading, the")
    print("  invariants, and the conductivity-span gate.")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
