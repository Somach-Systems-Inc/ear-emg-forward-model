#!/usr/bin/env python3
"""
Is current leaving the extended mesh through the slab's inferior face?

THE HYPOTHESIS AND WHY IT FITS

The extended-mesh calibration error tracks the SLAB CONDUCTIVITY and not the
electrode position:

    slab 0.355 S/m -> 100.49%   at BOTH hyoid (8 mm from the cut) and
                                above_ear (130 mm from it)
    slab 0.190 S/m ->  95.84%

Error proportional to slab sigma, independent of where current is injected,
is the signature of current leaving the domain through the slab in proportion
to how well the slab conducts. MIDA's original cut face was the insulating
Neumann boundary; the extrusion moved the exterior surface down to
S = -186.2 mm, and the new bottom face may not carry that condition.

THE TEST, AND WHY IT IS DECISIVE

Both electrodes sit ABOVE the truncation plane (hyoid at S = -108.2,
earlobe_contra at S = -33.4). Charge conservation therefore requires that the
net vertical current through ANY horizontal plane below both of them be
**exactly zero** -- whatever flows down must come back up, because there is
nowhere else for it to go if the boundary is insulating.

    CORRECTED after the control run (adversarial pass #4). "Zero below both
    electrodes" is too naive for planes just BELOW an electrode: current
    injected at hyoid spreads downward into tissue and returns, so a plane a
    few mm under it legitimately carries circulating current. The truncated
    control shows 0.951 mA at S = -112 and is correct.

    The test that actually discriminates is DECAY TOWARD THE DOMAIN FLOOR,
    where there is nowhere left to circulate:

        truncated (clean)  0.951 mA at -112  ->  0.107 mA at -119 (floor -122)
        extended (broken)  1.594 mA at -112  ->  1.070 mA at -182 (floor -192)

    Flux that fails to decay approaching the floor means current is leaving
    the domain there.

Net vertical current through a plane is obtained as the volume integral of
J_z over a thin horizontal slab divided by its thickness, which converges to
the surface integral as the slab thins and avoids having to clip tetrahedra
against the plane.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/03a3_leak_probe.py
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
SLAB_SIGMA = 0.355
CUT_S = -116.2
PLANES = (-60.0, -90.0, -112.0, -130.0, -150.0, -170.0, -182.0)
HALF_T = 1.5          # mm; slab half-thickness for the volume integral
I_INJECTED = 1e-3     # A


def main() -> int:
    from simnibs import mesh_io

    res = sorted((config.RESULTS / "boundary" / "muscle_iso").glob("*_scalar.msh"))
    if not res:
        print("no extended-mesh solve found", file=sys.stderr)
        return 1
    print(f"reading {res[0].name} ...", flush=True)
    m = mesh_io.read_msh(str(res[0]))
    if "E" not in m.field:
        print(f"no vector E; have {list(m.field)}", file=sys.stderr)
        return 1

    E = np.asarray(m.field["E"].value)
    tets = m.elm.elm_type == 4
    tags = m.elm.tag1[tets]
    vols = m.elements_volumes_and_areas()[tets]          # mm^3
    Ez = E[tets][:, 2]                                   # V/m

    # centroid S of every tet
    nn = m.elm.node_number_list[tets] - 1
    zc = m.nodes.node_coord[nn][:, :, 2].mean(axis=1)     # mm

    sig = {}
    for r in csv.DictReader((config.RESULTS / "01_table1_conductivities.csv").open()):
        lab, val = r.get("mida_label", "").strip(), r.get("sigma_S_per_m", "").strip()
        if lab.isdigit() and val:
            sig[int(lab)] = float(val)
    sig[EXTENSION_LABEL] = SLAB_SIGMA
    # SimNIBS adds its own electrode rubber/gel tags (501, 502) to the result
    # mesh; they are not in Table 1 and would otherwise read as NaN.
    import solve_invariants as SI
    sig = SI.with_electrode_tags(sig)
    sigma = np.array([sig.get(int(t), np.nan) for t in tags])
    if np.isnan(sigma).any():
        bad = sorted({int(t) for t, s in zip(tags, sigma) if np.isnan(s)})
        print(f"tags with no conductivity: {bad}", file=sys.stderr)
        return 1

    # J_z in A/m^2; volumes mm^3 -> m^3 (1e-9); thickness mm -> m (1e-3)
    Jz = sigma * Ez
    print(f"\n{len(tags):,} tets, S range {zc.min():.1f} to {zc.max():.1f} mm")
    print(f"electrodes: hyoid S=-108.2, earlobe_contra S=-33.4 "
          f"(both ABOVE the cut at {CUT_S})")
    print(f"\nnet DOWNWARD current through horizontal planes")
    print(f"(slab +/-{HALF_T} mm, volume integral of Jz / thickness)\n")
    print(f"  {'S (mm)':>9}{'net I (mA)':>14}{'as % of 1 mA':>15}   region")
    print("  " + "-" * 58)

    for z0 in PLANES:
        k = np.abs(zc - z0) <= HALF_T
        if not k.any():
            print(f"  {z0:>9.1f}{'no tets':>14}")
            continue
        # integral of Jz dV over the slab, / thickness  ->  A
        I = float(np.sum(Jz[k] * vols[k] * 1e-9) / (2 * HALF_T * 1e-3))
        where = "between electrodes" if z0 > -116.2 else "BELOW both electrodes"
        print(f"  {z0:>9.1f}{I*1e3:>14.4f}{100*I/I_INJECTED:>14.1f}%   {where}")

    print()
    below = [z for z in PLANES if z < CUT_S]
    worst = 0.0
    for z0 in below:
        k = np.abs(zc - z0) <= HALF_T
        if k.any():
            I = abs(float(np.sum(Jz[k] * vols[k] * 1e-9) / (2 * HALF_T * 1e-3)))
            worst = max(worst, I)
    print("=" * 62)
    print("VERDICT")
    print("=" * 62)
    print(f"  largest |net current| below both electrodes: "
          f"{worst*1e3:.4f} mA ({100*worst/I_INJECTED:.1f}% of injected)")
    print()
    if worst > 0.05 * I_INJECTED:
        print("  LEAKAGE CONFIRMED. Charge conservation requires zero net")
        print("  current through any plane below both electrodes. It is not")
        print("  zero, so current is leaving through the slab's inferior")
        print("  face: that boundary is NOT insulating.")
        print("  The extrusion moved the exterior surface without carrying")
        print("  the Neumann condition with it.")
    else:
        print("  HYPOTHESIS FALSIFIED. Net current below the electrodes is")
        print("  within noise of zero, so the inferior face IS behaving as an")
        print("  insulating boundary and the leak is not there.")
        print("  This was hypothesis 2 of the 2 allowed. Per the stopping")
        print("  rule, proceed with the TRUNCATED mesh as primary and report")
        print("  the inferior boundary as an unquantified limitation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
