#!/usr/bin/env python3
r"""
Stage 3c. FAT CONDUCTIVITY SWAP — separating material properties from distance.

THE QUESTION THIS ANSWERS
--------------------------
Retroauricular sites sit behind more subcutaneous fat than jaw sites do, and
fat is ~14x less conductive than muscle (0.025 vs 0.355 S/m). Two mechanisms
are confounded in any observational comparison:

    (a) the ear is FURTHER from the anterior articulators
    (b) the ear is behind MORE INSULATING TISSUE

The limb sEMG literature cannot separate these cleanly, because in a limb
adding fat also moves the electrode further from the muscle -- thickness and
distance covary by construction.

Here they can be separated exactly, because the geometry is held FIXED and only
the material changes: every fat element is reassigned muscle conductivity, on
the identical mesh, with the identical electrodes. Distance is untouched. Any
change in the lead field is therefore attributable to the material alone.

If the effect is large, the Discussion may state the mechanism. If it is small,
the attenuation is geometric and the Discussion must say so instead. Either way
the answer is measured rather than argued -- and both outcomes publish.

Solved on the ISOTROPIC run's own mesh via `fem.tdcs`, for the same reason
03f_aniso_solve.py does: SimNIBS re-meshes electrodes on every SESSION call,
and electrode realisation (~0.27 dB per site) would otherwise be confounded
with the effect being measured.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/03g_fat_swap.py
    ... --electrodes cg08 midjaw      # subset
"""
from __future__ import annotations

import argparse
import csv
import gc
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config                      # noqa: E402
import solve_invariants as SI      # noqa: E402
import orientation                 # noqa: E402

WORKDIR = config.RESULTS / "leadfields"
OUT_CSV = config.RESULTS / "03_fat_swap_projected.csv"
ELECTRODE_SURFACE_TAGS = [2101, 2102]

# Both MIDA adipose labels, read from Table 1 rather than hardcoded by name.
FAT_TISSUE = "fat"
SWAP_TO = config.SIGMA["muscle_iso"]     # 0.355 S/m

MUSCLE_NAMES = [n for n, _g, lab, _e in config.MUSCLES if lab is not None]
_LAB = {n: lab for n, _g, lab, _e in config.MUSCLES if lab is not None}


def load_sigma_and_fat():
    """Table-1 map, plus the set of labels whose assigned tissue is fat."""
    sig, fat = {}, set()
    p = config.RESULTS / "01_table1_conductivities.csv"
    for r in csv.DictReader(p.open()):
        lab = r.get("mida_label", "").strip()
        val = r.get("sigma_S_per_m", "").strip()
        if not (lab.isdigit() and val):
            continue
        sig[int(lab)] = float(val)
        if r.get("assigned_tissue", "").strip() == FAT_TISSUE:
            fat.add(int(lab))
    if not fat:
        raise RuntimeError(
            f"no labels in {p.name} carry assigned_tissue='{FAT_TISSUE}'. "
            f"Refusing to run a swap that would change nothing and report a "
            f"null result.")
    return sig, fat


def compartment_medians(m, E):
    tets = m.elm.elm_type == 4
    tags = m.elm.tag1[tets]
    vols = m.elements_volumes_and_areas()[tets]
    # PROJECTED, not the norm. |E| is the upper bound over source orientations
    # and is not the lead field; anything downstream of a lead-field value must
    # be the projected quantity.
    Et = E[tets]
    out = {}
    for name in MUSCLE_NAMES:
        k = tags == _LAB[name]
        if not k.any():
            continue
        out[name] = float(orientation.sweep(Et[k], weights=vols[k])["median"])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="03g_fat_swap.py")
    ap.add_argument("--electrodes", nargs="*", default=None)
    ap.add_argument("--out", type=Path, default=OUT_CSV)
    a = ap.parse_args(argv)

    from simnibs import mesh_io
    from simnibs.simulation import fem
    from simnibs.utils import cond_utils

    sigma, fat_labels = load_sigma_and_fat()
    print("FAT CONDUCTIVITY SWAP")
    print("=" * 66)
    print(f"  fat labels        : {sorted(fat_labels)} "
          f"(from Table 1's assigned_tissue column)")
    print(f"  baseline sigma    : {config.SIGMA['fat']} S/m")
    print(f"  swapped to        : {SWAP_TO} S/m (muscle_iso), a "
          f"{SWAP_TO/config.SIGMA['fat']:.0f}x increase")
    print(f"  geometry          : IDENTICAL — same mesh, same electrodes, "
          f"only the material changes\n")

    swapped = dict(sigma)
    for lab in fat_labels:
        swapped[lab] = SWAP_TO
    full = SI.with_electrode_tags(swapped)

    iso_dir = WORKDIR / "iso"
    names = a.electrodes or sorted(
        d.name for d in iso_dir.iterdir()
        if d.is_dir() and not d.name.startswith("_"))

    fields = ["electrode", "condition"] + MUSCLE_NAMES
    rows, t0 = [], time.time()
    for i, name in enumerate(names, 1):
        d = iso_dir / name
        hits = sorted(d.glob("*_scalar.msh")) or sorted(d.glob("*.msh"))
        if not hits:
            continue
        print(f"[{i}/{len(names)}] {name}", flush=True)
        m = mesh_io.read_msh(str(hits[0]))
        cond_list = [full.get(t + 1, 1e-6)
                     for t in range(int(m.elm.tag1.max()))]
        cond = cond_utils.cond2elmdata(m, cond_list)
        I = config.INJECTION_CURRENT_A
        v = fem.tdcs(m, cond, [I, -I], ELECTRODE_SURFACE_TAGS)
        E = np.asarray(v.gradient().value) * -1000.0      # V/mm -> V/m
        med = compartment_medians(m, E)
        row = dict(electrode=name, condition="fat_as_muscle")
        for mn in MUSCLE_NAMES:
            row[mn] = med.get(mn, "")
        rows.append(row)
        del m, cond, E
        gc.collect()

    with a.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {a.out}  ({(time.time()-t0)/60:.1f} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
