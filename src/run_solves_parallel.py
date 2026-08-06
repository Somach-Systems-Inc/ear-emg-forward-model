#!/usr/bin/env python3
"""
Run independent SimNIBS solves concurrently.

MEASURED, not assumed: one production solve on the 12.3M-tet MIDA mesh uses
100% of ONE core (hypre is single-threaded here) and peaks at 10.8 GB resident.
So the machine's 18 cores are not the binding constraint -- memory is.

    cores allow   18 concurrent (1 core each)
    48 GB allows   4 concurrent at 10.8 GB peak

N defaults to 3 rather than 4. Four solves is 43.2 GB of 48, leaving under
5 GB for everything else, and this machine was already observed swapping
3.8 GB with a single solve running. Swapping would erase the gain, so the
default trades one worker for headroom. Override with --workers.

Solves are independent -- one electrode each -- so there is no coordination
beyond the worker cap.
"""
from __future__ import annotations
import argparse, os, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _find_simnibs_python():
    """Locate the SimNIBS interpreter. PATH first, install default second.

    Same resolution order as 01_build_mesh.py uses for `meshmesh`, and for the
    same reason: the installer puts its bin/ on PATH, but a non-login shell may
    not have read the profile that does it. On Windows the entry point is
    `simnibs_python.cmd`, which shutil.which() finds via PATHEXT.
    """
    found = shutil.which("simnibs_python")
    if found:
        return Path(found)
    for default in (Path.home() / "Applications/SimNIBS-4.6/bin/simnibs_python",
                    Path.home() / "SimNIBS-4.6/bin/simnibs_python.cmd"):
        if default.is_file():
            return default
    raise SystemExit(
        "SimNIBS `simnibs_python` is not on PATH and is not at either default\n"
        "install location. Install SimNIBS 4.6.0, then verify:\n"
        "  simnibs_python -c \"import simnibs; print(simnibs.__version__)\"")


SIMNIBS = _find_simnibs_python()
PEAK_RSS_GB = 10.8      # measured
TOTAL_RAM_GB = 48.0


def default_workers():
    return max(1, min(int(TOTAL_RAM_GB / PEAK_RSS_GB) - 1, os.cpu_count() or 1))


def run_one(script: Path, args: list[str], tag: str):
    t0 = time.time()
    p = subprocess.run([str(SIMNIBS), str(script), *args],
                       capture_output=True, text=True)
    return tag, p.returncode, time.time() - t0, p.stdout[-2000:], p.stderr[-2000:]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="run_solves_parallel.py")
    ap.add_argument("--script", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--arg", action="append", default=[],
                    help="repeat: one job per --arg, passed to the script")
    a = ap.parse_args(argv)

    n = a.workers or default_workers()
    print(f"measured: 1 core, {PEAK_RSS_GB} GB peak per solve")
    print(f"workers: {n}  ({n*PEAK_RSS_GB:.1f} GB of {TOTAL_RAM_GB:.0f} GB, "
          f"{TOTAL_RAM_GB-n*PEAK_RSS_GB:.1f} GB headroom)")
    print(f"jobs: {len(a.arg)}\n", flush=True)

    fails = 0
    with ThreadPoolExecutor(max_workers=n) as ex:
        futs = {ex.submit(run_one, a.script, arg.split(), arg): arg
                for arg in a.arg}
        for f in as_completed(futs):
            tag, rc, dt, out, err = f.result()
            status = "ok" if rc == 0 else f"FAILED rc={rc}"
            print(f"  [{status}] {tag}  {dt/60:.1f} min", flush=True)
            if rc != 0:
                fails += 1
                print("    " + (err.strip().splitlines() or ["(no stderr)"])[-1])
    print(f"\n{len(a.arg)-fails}/{len(a.arg)} succeeded")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
