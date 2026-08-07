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
# Reference S for splitting the sampling planes into above/below. NOT the cut
# face: the cut is a plane tilted 2.664 deg with no single S. This is the fitted
# plane's centroid S (results/01_cut_plane.csv, pz).
#
# TRAP, recorded before anyone falls into it. `deep` below selects from the
# discrete PLANES set, and that selection is invariant for ANY value in the open
# interval (-130, -112). The plane's centroid (-115.600) and the mesh S minimum
# (-122.070) both sit inside it; the face's UPPER extreme (-110.175) does NOT.
# Substituting the upper extreme flips deep[0] from -130 to -112 and changes the
# reported retained fraction. This is the third instance of a scalar summary of a
# tilted plane behaving differently by choice of summary. METHODS_LOG 2026-08-05.
CUT_S = -115.600
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
    for r in csv.DictReader((config.RESULTS / "01_table1_conductivities.csv").open(encoding="utf-8")):
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
        where = "between electrodes" if z0 > CUT_S else "BELOW both electrodes"
        print(f"  {z0:>9.1f}{I*1e3:>14.4f}{100*I/I_INJECTED:>14.1f}%   {where}")

    # DECAY TOWARD THE FLOOR is the discriminator, not "zero below the
    # electrodes" -- see the docstring correction. Compare the deepest plane
    # against the shallowest one below the cut.
    floor_S = float(zc.min())
    deep = [z for z in PLANES if z < CUT_S]
    def flux(z0):
        k = np.abs(zc - z0) <= HALF_T
        if not k.any():
            return None
        return float(np.sum(Jz[k] * vols[k] * 1e-9) / (2 * HALF_T * 1e-3))
    shallow_v, deep_v = flux(deep[0]), flux(deep[-1])
    print("=" * 62)
    print("VERDICT")
    print("=" * 62)
    print(f"  domain floor at S = {floor_S:.1f} mm")
    print(f"  flux at {deep[0]:.0f} mm : {shallow_v*1e3:.4f} mA")
    print(f"  flux at {deep[-1]:.0f} mm: {deep_v*1e3:.4f} mA  "
          f"({deep[-1]-floor_S:.0f} mm above the floor)")
    ratio = abs(deep_v) / abs(shallow_v) if shallow_v else float("nan")
    print(f"  retained fraction approaching the floor: {ratio:.2f}")
    print()
    print(f"  reference, truncated mesh (clean calibration, same code):")
    print(f"    0.951 mA at -112  ->  0.107 mA at -119   retained 0.11")
    print()
    if ratio > 0.5:
        print("  LEAKAGE CONFIRMED. Flux does NOT decay approaching the domain")
        print("  floor: current is still running at most of the injected rate")
        print("  where there is nowhere left for it to circulate. On the clean")
        print("  truncated mesh the same measurement decays by ~10x. Current is")
        print("  leaving the domain through the extension's inferior surface.")
    else:
        print("  HYPOTHESIS FALSIFIED. Flux decays toward the floor as it does")
        print("  on the clean mesh, so the inferior face IS insulating and the")
        print("  leak is not there. Per the stopping rule this was hypothesis")
        print("  2 of 2: proceed with the TRUNCATED mesh as primary.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
