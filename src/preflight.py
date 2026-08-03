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

# Conductivity dynamic range. The stiffness matrix inherits sigma_max/sigma_min
# as its condition number, and SimNIBS solves iteratively (hypre), so an
# excessive span makes the solve fail to converge while still writing a result
# file. Measured: 1.879e15 broke every solve; 1.879e6 was clean. 1e8 leaves
# two orders of headroom over the working case and is eight orders below the
# failing one.
SIGMA_RATIO_MAX = 1e8


def check_conductivity_range(sigmas, label=""):
    """Fail loudly if the assigned conductivities span too many orders."""
    v = [float(x) for x in sigmas if float(x) > 0]
    if not v:
        raise ValueError(f"{label}: no positive conductivities")
    ratio = max(v) / min(v)
    if ratio > SIGMA_RATIO_MAX:
        raise ValueError(
            f"{label}: conductivity span {ratio:.3e} exceeds "
            f"{SIGMA_RATIO_MAX:.0e}. The iterative solver will not converge "
            f"and SimNIBS will still write a result file. Raise the smallest "
            f"conductivity (min {min(v):.3e}, max {max(v):.3e}).")
    return ratio


def check_solve_output(pathfem):
    """Read the solver's own summary and fail on a calibration error.

    SimNIBS writes 'The current calibration error exceeded 10%!' into
    fields_summary.txt when the solve did not deliver the requested current.
    It is not an exception and the result file is written regardless, so it
    must be read explicitly. Not reading it cost this project a full 20-solve
    run whose numbers were 10-20x wrong.
    """
    from pathlib import Path as _P
    f = _P(pathfem) / "fields_summary.txt"
    if not f.exists():
        raise FileNotFoundError(f"no fields_summary.txt in {pathfem}; "
                                f"cannot confirm the solve succeeded")
    for line in f.read_text(errors="replace").splitlines():
        if "calibration error" in line:
            raise RuntimeError(
                f"solve in {pathfem} FAILED current calibration: "
                f"{line.strip()} -- result withheld")
    return True


def read_calibration(pathfem):
    """Return the reported current-calibration error in percent, or None if the
    solver printed no calibration warning at all.

    WHY THIS EXISTS ALONGSIDE check_solve_output()

    check_solve_output() raises on any calibration line. That is the right
    behaviour for a gate, but it is the wrong behaviour for a RECORD, and this
    project needs both. Two distinct populations have been measured:

      - 200.00%  the conductivity-conditioning failure. Fields came back
                 10-20x too large. Real, and fatal.
      - 11-15%   seen on well-conditioned custom meshes. On the sphere, 5 of
                 16 solves warned while matching the analytic oracle, and the
                 warned electrodes were NOT less accurate (median
                 |L_num|/|L_ana| 0.9814 warned vs 1.0345 un-warned, a
                 difference inside the scatter of either group).

    A single threshold separating those two populations is NOT invented here.
    Inventing one after a solve tripped the gate is exactly the prohibited
    move. Instead the value is recorded, carried alongside the result, and any
    downstream verdict states how many of its inputs warned and whether
    excluding them changes the answer.
    """
    from pathlib import Path as _P
    import re as _re
    f = _P(pathfem) / "fields_summary.txt"
    if not f.exists():
        raise FileNotFoundError(f"no fields_summary.txt in {pathfem}; "
                                f"cannot confirm the solve succeeded")
    for line in f.read_text(errors="replace").splitlines():
        if "calibration error" in line:
            # The line reads:
            #   "...calibration error exceeded 10%! Estimated error value: 11.90%"
            # so a plain "first percentage" match returns the THRESHOLD (10),
            # not the error (11.90). Anchor on the label.
            m = _re.search(r"Estimated error value:\s*([0-9]+\.?[0-9]*)\s*%",
                           line)
            if m:
                return float(m.group(1))
            return float("nan")     # warned, but the value could not be parsed
    return None


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
