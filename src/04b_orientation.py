#!/usr/bin/env python3
r"""
Stage 4b. ORIENTATION: project the field onto source direction, per compartment.

WHY THIS EXISTS
---------------
Methods states the lead field for a source at r with unit orientation n-hat as
`E_recip(r) . n_hat`. Stage 3 reports the volume-weighted median of **|E|**,
which is the orientation-free magnitude -- i.e. the UPPER BOUND over all source
orientations, attained only when the fibre happens to lie along the field. The
projection onto n-hat was never computed, and `orientation.py`'s sweep
machinery was never wired to anything.

That is a stated-versus-done mismatch in the core method, and it is not
cosmetic: if the field is directionally concentrated at one site and diffuse at
another, the two sites' rank can change under projection. This computes the
missing quantity from the solves already on disk -- no new solving.

WHAT IT REPORTS, per (electrode, muscle)
----------------------------------------
    lf_absE      volume-weighted median |E|      -- what stage 3 reported
    lf_median    median over a uniform sweep of source orientations
    lf_min       worst orientation   ) the ENVELOPE. Its width is itself a
    lf_max       best orientation    ) finding and Fig 2's spec asks for it.
    lf_pca       projection onto the PCA fibre axis, where a principal axis is
                 a meaningful object for that muscle (config.FIBRE_MODEL);
                 blank otherwise, never silently substituted.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/04b_orientation.py
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
import config          # noqa: E402
import orientation     # noqa: E402

WORKDIR = config.RESULTS / "leadfields" / "iso"
OUT_CSV = config.RESULTS / "04b_orientation.csv"

MUSCLES = [(n, lab) for n, _g, lab, _e in config.MUSCLES if lab is not None]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="04b_orientation.py")
    ap.add_argument("--electrodes", nargs="*", default=None)
    ap.add_argument("--n-dirs", type=int, default=200)
    ap.add_argument("--out", type=Path, default=OUT_CSV)
    a = ap.parse_args(argv)

    from simnibs import mesh_io

    names = a.electrodes or sorted(
        d.name for d in WORKDIR.iterdir()
        if d.is_dir() and not d.name.startswith("_"))

    rows, t0 = [], time.time()
    for i, name in enumerate(names, 1):
        d = WORKDIR / name
        hits = sorted(d.glob("*_scalar.msh")) or sorted(d.glob("*.msh"))
        if not hits:
            continue
        print(f"[{i}/{len(names)}] {name}", flush=True)
        m = mesh_io.read_msh(str(hits[0]))
        E = np.asarray(m.field["E"].value)
        tets = m.elm.elm_type == 4
        tags = m.elm.tag1[tets]
        vols = m.elements_volumes_and_areas()[tets]
        Et = E[tets]
        nodes = m.nodes.node_coord
        nl = m.elm.node_number_list[tets][:, :4] - 1

        for mus, lab in MUSCLES:
            k = tags == lab
            if not k.any():
                continue
            Ek, wk = Et[k], vols[k]
            pts = nodes[nl[k]].mean(axis=1)
            s = orientation.summarise(mus, Ek, weights=wk, points=pts)
            # volume-weighted median |E|, the stage-3 quantity, recomputed here
            # so the two live in one file and can be compared directly
            mag = np.linalg.norm(Ek, axis=1)
            o = np.argsort(mag)
            c = np.cumsum(wk[o])
            absE = float(mag[o][np.searchsorted(c, 0.5 * c[-1])])
            rows.append(dict(
                electrode=name, muscle=mus,
                lf_absE=absE,
                lf_median=s["sens_median"], lf_min=s["sens_min"],
                lf_max=s["sens_max"], envelope_db=s["envelope_db"],
                lf_pca=s["sens_at_pca"], pca_dominance=s["pca_dominance"],
                fibre_model=s["fibre_model"], n_elements=s["n_elements"]))
        del m, E, Et
        gc.collect()

    if not rows:
        print("nothing computed", file=sys.stderr)
        return 1
    with a.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {a.out}  ({(time.time()-t0)/60:.1f} min, {len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
