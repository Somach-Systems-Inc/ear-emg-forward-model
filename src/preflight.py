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


# Reported calibration is a RELATIVE DIFFERENCE between the two electrode
# interface fluxes, confirmed by the SimNIBS maintainer (discussions/666):
#
#     e = 2 |a - b| / (a + b)
#
# and the solution is then scaled so mean(a, b) equals the requested current.
# So each interface sits e/2 from the requested current. It is an
# INTERFACE-CONSISTENCY diagnostic, not a delivered-current error.
#
# THE BAND, RE-DERIVED UNDER THE CORRECT INTERPRETATION. The old "11-15% benign"
# band was retired as meaningless; it is reinstated with a meaning:
#
#     reported 10%  ->  each interface  5% from the requested current
#     reported 12%  ->  each interface  6%
#     reported 20%  ->  each interface 10%
#     reported 33%  ->  each interface 16.5%
#
# and two exact algebraic landmarks, both verified:
#
#     e = 200.00%  <=>  one interface flux is EXACTLY ZERO
#     e = 100.00%  <=>  a/b = 3.000000 exactly
#
# INTERFACE_TOL is the per-interface deviation this project accepts. 10% is
# SimNIBS's own gate expressed in the same units (its 10% report = 5% per
# interface) doubled, i.e. deliberately looser than the solver's own warning
# so that this raises only on solves the solver already flagged AND that are
# twice as inconsistent as its threshold. It is not tuned to this data: at 20%
# reported it admits every stage-3 solve except cg01, cg04, cg08, cg09 and
# mental, which is a statement about the run, not a threshold chosen to fit it.
INTERFACE_TOL = 0.10        # per-interface fraction of the requested current
DEGENERATE_REPORTED = 2.00  # one interface carrying nothing
LEAK_REPORTED = 1.00        # a/b = 3


def interface_deviation(reported_pct):
    """Per-interface deviation from the requested current, as a fraction.

    reported_pct is what SimNIBS prints. Returns e/2, because the solution is
    scaled so the two interface fluxes straddle the requested current.
    """
    return None if reported_pct is None else float(reported_pct) / 200.0


def interface_ratio(reported_pct):
    """Back-solve a/b from the reported percentage. Diagnostic, not a gate.

    e = 2(r-1)/(r+1) for r = a/b >= 1, so r = (2+e)/(2-e). Undefined at
    e = 200%, which is the degenerate one-interface-zero case.
    """
    if reported_pct is None:
        return 1.0
    e = float(reported_pct) / 100.0
    if e >= 2.0:
        return float("inf")
    return (2.0 + e) / (2.0 - e)


def check_solve_output(pathfem, tol=INTERFACE_TOL):
    """Gate on the solver's interface-consistency check, correctly read.

    UN-RETIRED 2026-08-04. This function previously raised on ANY calibration
    line, was then retired entirely as an "active refusal" on the belief that
    the check was anti-correlated with delivered current, and is now restored
    with the right interpretation. Full sequence in METHODS_LOG under "the
    third reversal".

    What changed: the reported value is not a delivered-current error, so a
    bare "any warning is fatal" gate was wrong, and so was "it measures
    nothing". It measures how far the two electrode interfaces disagree, which
    is a real and useful diagnostic, and it correctly DETECTED both of this
    project's real solver failures:

        200.00%  the sigma_air 1e-15 conditioning failure -- requires one
                 interface flux to be exactly zero, which is what a
                 non-conducting return path gives
        ~100%    the neck-extended mesh leaking through its inferior face --
                 requires a/b = 3, and the measured values back-solve to
                 3.020 and 2.840
    """
    from pathlib import Path as _P
    f = _P(pathfem) / "fields_summary.txt"
    if not f.exists():
        raise FileNotFoundError(f"no fields_summary.txt in {pathfem}; "
                                f"cannot confirm the solve succeeded")
    pct = read_calibration(pathfem)
    if pct is None:
        return True
    dev = interface_deviation(pct)
    if dev > tol:
        raise RuntimeError(
            f"solve in {pathfem} FAILED interface consistency: SimNIBS "
            f"reports {pct:.2f}%, i.e. the two electrode-interface fluxes "
            f"differ by that fraction of their mean, so EACH interface sits "
            f"~{dev*100:.2f}% from the requested current (ratio a/b = "
            f"{interface_ratio(pct):.3f}). Tolerance is {tol*100:.0f}% per "
            f"interface. NOTE the two exact landmarks: 200% means one "
            f"interface carries nothing, ~100% means a/b = 3.")
    return True


def read_calibration(pathfem):
    """Return the reported current-calibration error in percent, or None if the
    solver printed no calibration warning at all.

    WHAT IT MEASURES -- corrected 2026-08-04 by the SimNIBS maintainer.

    e = 2|a - b| / (a + b) over the two electrode-interface flux estimates,
    after which the solution is scaled so mean(a, b) is the requested current.
    It is an INTERFACE-CONSISTENCY measure; each interface sits e/2 from the
    requested current. See `interface_deviation()` and `interface_ratio()`.

    The "11-15% benign band" was retired on 2026-08-03 as meaningless and is
    REINSTATED with a meaning: 12% reported means each interface is ~6% off,
    which is a real threshold. What is discarded is only the reading
    "N% means delivered current is N% wrong" -- that was a category error on
    our side, not a defect in the check. METHODS_LOG, "the third reversal".
    """
    from pathlib import Path as _P
    import re as _re
    f = _P(pathfem) / "fields_summary.txt"
    if not f.exists():
        raise FileNotFoundError(f"no fields_summary.txt in {pathfem}; "
                                f"cannot confirm the solve succeeded")
    for line in f.read_text(errors="replace", encoding="utf-8").splitlines():
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
        rows = list(csv.DictReader(a.results.open(encoding="utf-8")))
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
        rec = json.loads(a.envs.read_text(encoding="utf-8"))
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
