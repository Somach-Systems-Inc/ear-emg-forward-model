#!/usr/bin/env python3
r"""
Stage 3b. The ANISOTROPIC condition, solved on the ISOTROPIC run's own mesh.

WHY IT REUSES THE ISO MESH INSTEAD OF RE-RUNNING THE SESSION
------------------------------------------------------------
SimNIBS re-meshes the electrodes on every `run_simnibs` call, and two runs of
the *same* montage are not guaranteed to produce the same discretisation --
measured directly on `submental_mid`, whose 1x and 2x solves have 2,140,980 and
2,140,979 nodes. Electrode realisation is independently measured at ~3-5
percentage points on lead-field magnitude (0.27 dB per-site).

Fig 4 asks whether the SCM retroauricular advantage (+2.53 dB at `cg08`)
survives relaxing the isotropy assumption. That advantage is a few dB. If the
anisotropic run were a fresh SESSION, the iso-vs-aniso difference would carry
electrode-realisation noise of the same order as the effect, and Fig 4 would be
uninterpretable.

So this loads each completed isotropic result mesh -- which already contains the
meshed electrodes, volume tags 501/502 and surface tags 2101/2102 -- swaps ONLY
the conductivity field, and re-solves with `fem.tdcs` on that identical
geometry. The comparison is then exactly one variable.

SCOPE: THREE COMPARTMENTS, AND ONLY TWO SURVIVE MEASUREMENT
-----------------------------------------------------------
Of the nine PCA-defensible muscles only three are individually segmented in
MIDA, and `mentalis` is then refused by the bilateral mirror-symmetry check
(its two "sides" are not mirror images; right-side elongation 1.07, i.e. no
long axis exists). **The tensor is applied to `sternocleidomastoid` and
`medial_pterygoid` only.** Every other muscle is NOT APPLIED, never blank.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/03f_aniso_solve.py
    ... --electrodes cg08 midjaw      # subset
"""
from __future__ import annotations

import argparse
import csv
import gc
import importlib.util
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config                      # noqa: E402
import orientation                 # noqa: E402
import solve_invariants as SI      # noqa: E402

WORKDIR = config.RESULTS / "leadfields"
OUT_CSV = config.RESULTS / "03_leadfields_aniso_projected.csv"
ELECTRODE_SURFACE_TAGS = [2101, 2102]

MUSCLE_NAMES = [n for n, _g, lab, _e in config.MUSCLES if lab is not None]
_LAB = {n: lab for n, _g, lab, _e in config.MUSCLES if lab is not None}


def _load_builder():
    """Import 03e_build_tensor.py, whose name is not a valid identifier."""
    spec = importlib.util.spec_from_file_location(
        "build_tensor", ROOT / "src" / "03e_build_tensor.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def compartment_medians(m, E, projected=True):
    """Per-compartment lead field.

    projected=True returns the ORIENTATION MEDIAN of |E.n_hat| over a uniform
    hemisphere sweep -- the quantity Methods defines. projected=False returns
    the volume-weighted median of |E|, the orientation-free norm, which is the
    upper bound over orientations and is NOT the lead field. Everything
    downstream of a lead-field value must use the projected quantity.
    """
    tets = m.elm.elm_type == 4
    tags = m.elm.tag1[tets]
    vols = m.elements_volumes_and_areas()[tets]
    Et = E[tets]
    out = {}
    for name in MUSCLE_NAMES:
        k = tags == _LAB[name]
        if not k.any():
            continue
        w = vols[k]
        if projected:
            out[name] = float(orientation.sweep(Et[k], weights=w)["median"])
        else:
            v = np.linalg.norm(Et[k], axis=1)
            o = np.argsort(v)
            c = np.cumsum(w[o])
            out[name] = float(v[o][np.searchsorted(c, 0.5 * c[-1])])
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="03f_aniso_solve.py")
    ap.add_argument("--electrodes", nargs="*", default=None)
    ap.add_argument("--out", type=Path, default=OUT_CSV)
    a = ap.parse_args(argv)

    from simnibs import mesh_io
    from simnibs.simulation import fem
    from simnibs.utils import cond_utils

    bt = _load_builder()
    print("Building and verifying the tensor before any solve ...")
    vol, affine, axes = bt.build_tensor_volume()
    applied = sorted(axes)
    print(f"\nTENSOR APPLIED: {applied}")
    print(f"NOT APPLIED   : "
          f"{sorted(set(MUSCLE_NAMES) - set(applied))}  (reported as NOT "
          f"APPLIED in Fig 4, never blank)\n")
    if not applied:
        print("no compartment survived verification; refusing to solve",
              file=sys.stderr)
        return 1

    sigma = bt.load_sigma()
    full = SI.with_electrode_tags(sigma)
    iso_dir = WORKDIR / "iso"
    names = a.electrodes or sorted(
        d.name for d in iso_dir.iterdir()
        if d.is_dir() and not d.name.startswith("_"))

    fields = (["electrode", "condition", "n_tensor_compartments"]
              + MUSCLE_NAMES)
    rows, t0 = [], time.time()
    for i, name in enumerate(names, 1):
        d = iso_dir / name
        hits = sorted(d.glob("*_scalar.msh")) or sorted(d.glob("*.msh"))
        if not hits:
            print(f"[{i}/{len(names)}] {name}: no iso solve, skipping")
            continue
        print(f"[{i}/{len(names)}] {name}: loading iso mesh ...", flush=True)
        m = mesh_io.read_msh(str(hits[0]))

        cond_list = [full.get(t + 1, 1e-6)
                     for t in range(int(m.elm.tag1.max()))]
        cond = cond_utils.cond2elmdata(
            m, cond_list, anisotropy_volume=vol, affine=affine,
            aniso_tissues=[_LAB[n] for n in applied],
            correct_FSL=bt.CORRECT_FSL, normalize=False,
            correct_intensity=bt.CORRECT_INTENSITY,
            max_ratio=bt.MAX_RATIO, max_cond=bt.MAX_COND)
        V = np.asarray(cond.value)
        if V.ndim != 2 or V.shape[1] != 9:
            raise RuntimeError(
                f"{name}: cond2elmdata returned a SCALAR field. Solving this "
                f"would reproduce the isotropic condition and make Fig 4 a "
                f"comparison against itself.")

        I = config.INJECTION_CURRENT_A
        print(f"    solving anisotropic ...", flush=True)
        v = fem.tdcs(m, cond, [I, -I], ELECTRODE_SURFACE_TAGS)
        # E = -grad(V). The mesh is in MILLIMETRES, so gradient() returns
        # V/mm and must be scaled by 1000 to match the isotropic run's V/m.
        # VERIFIED, not assumed: with this factor the eight NON-tensor
        # compartments come back at ratio 1.036 +/- 0.016 of their isotropic
        # values (0.996-1.050, i.e. within 0.4 dB of unchanged) while the two
        # tensor compartments move +3.92 and +5.02 dB. Without it every value
        # was ~600-1000x too small. A wrong constant here would have rescaled
        # the whole anisotropic column and made Fig 4 a units bug.
        E = np.asarray(v.gradient().value) * -1000.0   # V/m
        med = compartment_medians(m, E)
        row = dict(electrode=name, condition="aniso",
                   n_tensor_compartments=len(applied))
        for mn in MUSCLE_NAMES:
            row[mn] = med.get(mn, "")
        rows.append(row)
        print(f"    SCM {med.get('sternocleidomastoid', float('nan')):.6f} "
              f"V/m   medial_pterygoid "
              f"{med.get('medial_pterygoid', float('nan')):.6f}", flush=True)
        del m, cond, V, E
        gc.collect()

    if not rows:
        print("nothing solved", file=sys.stderr)
        return 1
    with a.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {a.out}  ({(time.time()-t0)/60:.1f} min)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
