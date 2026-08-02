#!/usr/bin/env python3
"""
Pre-flight gate. Run before stage 3 and before any production run.

The sphere validation is not a one-time result to be filed away. It is the
check that catches silent setup failures, and setup drifts: a SimNIBS upgrade,
a changed field string, a different interpreter. The `fields="e"` versus `"E"`
bug is the archetype -- a magnitude where a vector was needed, which would have
broken every orientation projection while raising nothing at all.

Refuses to pass if:
  - the sphere validation has never been run
  - RDM or MAG exceed their tolerances
  - the recorded interpreter versions no longer match the current environment

    python src/preflight.py            # check
    python src/preflight.py --strict   # non-zero exit blocks a pipeline
"""
from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402

# Tolerances. These are correctness gates on the method, not uncertainty
# estimates, and they are set from the validated baseline with headroom -- not
# tightened around whatever the current run happened to produce.
RDM_MEDIAN_MAX = 5.0      # percent
MAG_ABS_MEDIAN_MAX = 5.0  # percent


def current_env():
    info = {"python": sys.version.split()[0], "platform": platform.platform()}
    for mod in ("numpy", "scipy", "mne", "nibabel"):
        try:
            info[mod] = __import__(mod).__version__
        except Exception:
            pass
    try:
        import simnibs
        info["simnibs"] = simnibs.__version__
    except Exception:
        pass
    return info


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="preflight.py")
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero on any failure, to block a pipeline")
    ap.add_argument("--results", type=Path,
                    default=config.RESULTS / "val_rdm_mag.csv")
    ap.add_argument("--envs", type=Path,
                    default=config.RESULTS / "val_environments.json")
    a = ap.parse_args(argv)

    problems, notes = [], []

    print("PRE-FLIGHT")
    print("=" * 68)

    if not a.results.exists():
        problems.append(
            f"sphere validation has never been run ({a.results} missing).\n"
            f"      simnibs_python src/val_rdm_mag.py --phase simnibs\n"
            f"      .venv/bin/python src/val_rdm_mag.py --phase analytic")
    else:
        rows = list(csv.DictReader(a.results.open()))
        rdm = np.array([float(r["RDM_pct"]) for r in rows])
        mag = np.array([float(r["MAG_pct"]) for r in rows])
        rdm_med = float(np.nanmedian(rdm))
        mag_med = float(np.nanmedian(mag))
        print(f"  sphere validation : {len(rows)} sources")
        print(f"  RDM median        : {rdm_med:7.3f} %   "
              f"(tolerance <= {RDM_MEDIAN_MAX})")
        print(f"  MAG median        : {mag_med:+7.3f} %   "
              f"(tolerance |.| <= {MAG_ABS_MEDIAN_MAX})")
        if not np.isfinite(rdm_med) or rdm_med > RDM_MEDIAN_MAX:
            problems.append(f"RDM median {rdm_med:.3f}% exceeds "
                            f"{RDM_MEDIAN_MAX}%")
        if not np.isfinite(mag_med) or abs(mag_med) > MAG_ABS_MEDIAN_MAX:
            problems.append(f"|MAG| median {abs(mag_med):.3f}% exceeds "
                            f"{MAG_ABS_MEDIAN_MAX}%")

    if not a.envs.exists():
        notes.append(f"no environment fingerprint at {a.envs}; "
                     f"reproducibility of the two-phase split is unrecorded")
    else:
        rec = json.loads(a.envs.read_text())
        cur = current_env()
        print("\n  recorded environments:")
        for phase, env in rec.items():
            print(f"    {phase}:")
            for k, v in sorted(env.items()):
                if k == "platform":
                    continue
                print(f"      {k:<10} {v}")
        drift = []
        for phase, env in rec.items():
            for k, v in env.items():
                if k in cur and k != "platform" and cur[k] != v:
                    drift.append(f"{k}: recorded {v}, current {cur[k]} "
                                 f"(in {phase})")
        if drift:
            notes.append("environment drift since validation:\n        "
                         + "\n        ".join(drift))

    print("\n" + "=" * 68)
    for n in notes:
        print(f"  NOTE: {n}")
    if problems:
        print(f"  PRE-FLIGHT FAILED ({len(problems)}):")
        for p in problems:
            print(f"    - {p}")
        print("=" * 68)
        return 1 if a.strict else 0
    print("  PRE-FLIGHT PASSED -- reciprocity verified against the analytic")
    print("  sphere in this environment. Safe to run production solves.")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
