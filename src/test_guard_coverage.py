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
import re
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
    # `check_solve_output` was REMOVED from this group on 2026-08-03. It raises
    # on any calibration line, i.e. it gates on SimNIBS's calibration check --
    # now measured anti-correlated with true delivered current (Spearman
    # -0.425, p = 0.048, n = 22). A script satisfying "calibration is wired" by
    # calling it would be gating on evidence known to be worthless. Only
    # `read_calibration`, which RECORDS rather than gates, counts.
    "calibration (records the solver's own fields_summary.txt value)":
        {"read_calibration"},
    # `check_solve` was REMOVED from this group and then deleted: it had no
    # caller, so a script could have satisfied this requirement by invoking a
    # dead function.
    "invariants 1 and 2 (radius plateau, magnitude, charge conservation)":
        {"check_solve_plateau"},
    "conductivity span gate (sigma_max/sigma_min)":
        {"check_conductivity_range"},
}

# Invariants 3 and 4 are tracked SEPARATELY from REQUIRED because they are a
# batch-level policy, not a per-solve call: they need paired solves, so they
# run on the first and last solve of a batch rather than on every one.
#
# THEY HAVE NEVER RUN. `check_linearity`, `check_reciprocity_symmetry` and
# `batch_plan` have no caller anywhere in this repository, and all 22 stage-3
# solves completed without them. `needs_escalation` IS called, but its result
# is printed and discarded, so the escalation branch is inert too.
#
# This is reported as a distinct, named gap rather than folded into the
# per-script failures above, because the fix is not "add a call to one script"
# -- it is extra solves, and the cost belongs in the open, not hidden inside a
# generic FAILED line.
BATCH_REQUIRED = {
    "invariant 3 (linearity: 2I gives exactly 2E)": "check_linearity",
    "invariant 4 (reciprocity: L(A->B) = -L(B->A))":
        "check_reciprocity_symmetry",
    "batch selection for invariants 3 and 4": "batch_plan",
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


def pipeline_scripts_exist():
    """The sibling failure: DOCUMENTED BUT NEVER WRITTEN.

    "Written but never wired" had a twin nobody was looking for.
    `03_leadfields.py` and `04_analyze.py` sit in CLAUDE.md's pipeline table,
    are referenced as the stage-3 and stage-4 entry points, and **do not exist
    on disk**. The table read as a description of the repository and was
    actually a description of an intention.

    Same class as an unwired guard, same fix: enumerate and assert.
    """
    md = ROOT / "CLAUDE.md"
    if not md.exists():
        return [f"{md} missing; cannot check the pipeline table"]
    missing = []
    for line in md.read_text().splitlines():
        # pipeline table rows look like: | 3 | `03_leadfields.py` | ... |
        if not line.strip().startswith("|"):
            continue
        for tok in re.findall(r"`([A-Za-z0-9_]+\.py)`", line):
            if not (SRC / tok).exists():
                missing.append(f"CLAUDE.md pipeline table references "
                               f"src/{tok}, which does not exist")
    return missing


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

    pipeline_missing = pipeline_scripts_exist()

    # Batch-level guards: is each one called by ANY script in src/?
    all_calls = set()
    for p in sorted(SRC.glob("*.py")):
        if p.name.startswith("test_"):
            continue
        try:
            all_calls |= calls_in(ast.parse(p.read_text()))
        except SyntaxError:
            pass
    batch_missing = [(label, fn) for label, fn in BATCH_REQUIRED.items()
                     if fn not in all_calls]

    print("GUARD COVERAGE")
    print("=" * 68)
    print(f"  solving scripts checked : {len(checked)}")
    for n in checked:
        print(f"      {n}")
    if exempted:
        print(f"  exempt ({len(exempted)}), each with a recorded reason:")
        for n, why in exempted:
            print(f"      {n}\n          {why}")

    if pipeline_missing:
        print()
        print(f"  PIPELINE TABLE — {len(pipeline_missing)} referenced "
              f"script(s) do not exist:")
        for m in pipeline_missing:
            print(f"      {m}")
        print("      A table that documents a script into existence is the")
        print("      same failure as a guard that is written but never")
        print("      called: it reads as done and is not.")

    if batch_missing:
        print()
        print(f"  BATCH POLICY — {len(batch_missing)} guard(s) documented as "
              f"policy and called by NOTHING:")
        for label, fn in batch_missing:
            print(f"      {fn}()  —  {label}")
        print("      All 22 stage-3 solves ran without these. The batch policy")
        print("      in solve_invariants.py describes them as running on the")
        print("      first and last solve of every batch; that has never")
        print("      executed. Wiring them costs 4 extra solves (~16 min), not")
        print("      a line of glue, which is why it is named separately here")
        print("      rather than buried in a generic failure.")

    print()
    if failures or pipeline_missing or batch_missing:
        print("  FAILED")
        if failures:
            print(f"    {len(failures)} script(s) solve without their guards:")
            for name, missing in failures:
                print(f"\n      {name}")
                for m in missing:
                    print(f"        MISSING: {m}")
            print()
            print("    A guard that is written but not invoked is not a guard.")
            print("    Wire it in, or add the script to EXEMPT with a reason")
            print("    that would survive a reviewer reading it.")
        if batch_missing:
            print(f"    {len(batch_missing)} batch-policy guard(s) have no "
                  f"caller (listed above).")
        if pipeline_missing:
            print(f"    {len(pipeline_missing)} pipeline-table script(s) do "
                  f"not exist (listed above).")
            print("    Write them, or correct the table. Do not leave a table")
            print("    describing an intention as though it described the repo.")
        print("=" * 68)
        return 1 if a.strict else 0

    print("  PASSED — every solving script invokes calibration reading, the")
    print("  invariants, and the conductivity-span gate, and every script the")
    print("  CLAUDE.md pipeline table references exists on disk.")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
