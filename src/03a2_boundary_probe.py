#!/usr/bin/env python3
"""
Is the extended mesh's calibration failure LOCAL to the slab, or GLOBAL?

One solve, and it decides whether a 40-minute remesh is worth attempting.

The boundary run failed calibration at 100.49% and 95.84% on the extended
mesh while the truncated mesh was clean. Both failing solves injected at
`hyoid`, which sits 8 mm above the truncation plane, right where the slab's
coarse elements meet the head's fine ones.

    clean calibration at `above_ear` (~180 mm from the slab)
        -> the problem is LOCAL to the hyoid/slab region, the element-size
           jump is the live hypothesis, and a targeted refinement can fix it

    dirty calibration at `above_ear`
        -> the problem is GLOBAL to this mesh and refining the slab will NOT
           fix it. Stop and rethink the extrusion.

Injects between `above_ear` and the contralateral earlobe, both far from the
cut face, on the CURRENT extended mesh with no changes to it.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/03a2_boundary_probe.py
"""
from __future__ import annotations
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402

EXTENSION_LABEL = 200
SLAB_SIGMA = 0.355          # muscle-isotropic, the condition that gave 100.49%
INJECT_FROM = "above_ear"
INJECT_TO = "earlobe_contra"


def main() -> int:
    import importlib.util as iu
    spec = iu.spec_from_file_location("b", ROOT / "src" / "03a_boundary_run.py")
    b = iu.module_from_spec(spec)
    spec.loader.exec_module(b)
    import preflight

    pos = b.load_positions()
    sig = b.load_table1()
    mesh = config.DATA / "mida_neckext.msh"
    out = config.RESULTS / "boundary_probe" / "above_ear"

    if list(out.glob("simnibs_simulation*.mat")):
        print(f"ERROR: {out} already holds results; move it aside first",
              file=sys.stderr)
        return 1

    # Perpendicular distance to the derived cut plane, not a difference in S.
    cut_dist = config.clearance_to_cut(pos[INJECT_FROM][:3])
    print(f"probe: inject at {INJECT_FROM} (S = {pos[INJECT_FROM][2]:.1f} mm, "
          f"{cut_dist:.0f} mm from the cut plane)")
    print(f"       against {INJECT_TO}, on {mesh.name}")
    print(f"       hyoid, which FAILED, sits 8 mm from that plane\n")

    # The montage MUST be passed explicitly. The first run of this probe did
    # not pass it, so b.solve() fell back to 03a's module-level INJECT_FROM
    # ("hyoid") and re-solved the very montage this probe exists to differ
    # from. Assert it landed rather than trusting the call.
    msh, cal = b.solve(mesh, out, pos, sig, SLAB_SIGMA,
                       f"probe {INJECT_FROM}, slab {SLAB_SIGMA} S/m",
                       inject_from=INJECT_FROM, inject_to=INJECT_TO)
    _log = sorted(out.glob("simnibs_simulation*.log"))
    if _log:
        want = f"{pos[INJECT_FROM][0]:.2f}"
        if want not in _log[-1].read_text(errors="replace", encoding="utf-8"):
            raise RuntimeError(
                f"the solve did not use {INJECT_FROM}: its R coordinate "
                f"{want} does not appear in {_log[-1].name}. Refusing to "
                f"report a verdict from a montage that is not the one named.")

    print("\n" + "=" * 62)
    print("RESULT")
    print("=" * 62)
    print(f"  above_ear ({cut_dist:.0f} mm from slab): "
          f"{'CLEAN' if cal is None else f'WARNED {cal:.2f}%'}")
    print(f"  hyoid     (8 mm from slab, prior run): WARNED 100.49%")
    print(f"  truncated mesh, hyoid  (prior run)   : clean")
    print()
    if cal is None:
        print("  VERDICT: LOCAL. Calibration is clean far from the slab and")
        print("  dirty next to it, on the same mesh. The element-size jump at")
        print("  the interface survives as the hypothesis, and a TARGETED")
        print("  refinement of the slab is worth the remesh.")
    else:
        print("  VERDICT: GLOBAL. Calibration fails even 180 mm from the slab,")
        print("  so this is a property of the whole extended mesh and")
        print("  REFINING THE SLAB WILL NOT FIX IT. Do not spend the remesh.")
        print("  Rethink the extrusion, or reconsider whether the boundary")
        print("  question can be answered on this mesh at all.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
