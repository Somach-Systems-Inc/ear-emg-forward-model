#!/usr/bin/env python3
r"""
Derive the temporalis fibre fan from MIDA and re-evaluate its gap over it.

The paper's strongest surviving claim is that temporalis favours the
retroauricular montage "independent of fibre direction". That was argued from
textbook anatomy -- a fan from the temporal fossa to the coronoid process --
and an assertion is not a measurement. Every temporalis fibre converges on a
common insertion, so the fibre direction at each voxel is COMPUTABLE:

    n_hat(voxel) = normalise(insertion_centroid - voxel)

INSERTION, defined from MIDA's own labels and reproducible from a clean
checkout: mandible voxels (label 36, right side) lying within 3 mm of the
temporalis compartment (label 63). That contact region is the coronoid process
and the anterior border of the ramus, which is where temporalis inserts.

Two evaluations, because they answer different questions:
  PER-VOXEL   each tetrahedron uses its OWN fibre direction. This is the
              physically correct lead field for a fanned muscle and gives one
              number per electrode.
  PER-DIRECTION  each direction in the derived field is applied uniformly, so
              the gap can be checked at every anatomically reachable
              orientation. This is what the pre-committed reading asks for.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/04k_temporalis_fan.py
"""
from __future__ import annotations
import csv, gc, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402

TEMP, MAND = 63, 36
# HELD, NOT DERIVED -- same status as 04h's copy, and this one carries the
# HEADLINE. The paper's central claim rests on the temporalis interval computed
# below, so this set is load-bearing for it, which is why invariance had to be
# tested here separately: verifying it at 04h verifies a different object.
# Tested across all five admissible jaw subsets, the interval spans zero in every
# one. See 04n_site_set_sensitivity.py and METHODS_LOG 2026-08-05.
NEAR_CUT = {"hyoid", "submental_lat", "submental_mid"}
CLUSTER = ["above_ear", "mastoid", "post_lobule", "pre_tragus"]


def emit_fan_fractions(pv, pd_, mont, out=None):
    """Write the fan fractions this script previously only PRINTED.

    `8.5 %` reached §2.5.1 and was correct to the decimal, but existed in no
    results file. **A correct number with no file is invisible to a
    source-to-prose check in exactly the way an orphan is**, which is a distinct
    failure mode from -3.724 and -5.06 and is why this emitter exists.

    BASIS IS RECORDED EXPLICITLY. Reporting a cluster-basis fraction beside an
    argmax-14 one is the statistic-B pairing that produced the line-608 defect,
    and a basis question has now cost two halts. Do not drop the column.
    """
    import csv as _csv
    out = out or (config.RESULTS / "04k_fan_fractions.csv")
    jaw = [e for e in pv if mont[e] == "jaw" and e not in NEAR_CUT]
    ear14 = [e for e in pv if mont[e] in ("ear", "ceegrid")]
    rows = []
    for basis, ear in (("cluster", CLUSTER), ("argmax14", ear14)):
        J = np.max(np.stack([pd_[e] for e in jaw]), axis=0)
        R = np.max(np.stack([pd_[e] for e in ear]), axis=0)
        gd = 20 * np.log10(J / R)
        rows.append(dict(
            muscle="temporalis", basis=basis, n_fan_directions=len(gd),
            pct_fan_favouring_ear=round(100 * float((gd < 0).mean()), 1),
            pct_fan_conditional=round(100 * float((gd >= 0).mean()), 1),
            median_gap_dB=round(float(np.median(gd)), 4),
            ear_sites="+".join(sorted(ear)), jaw_sites="+".join(sorted(jaw)),
        ))
    with open(out, "w", newline="") as fh:
        fh.write("# Fraction of the DERIVED temporalis fibre fan favouring the ear.\n")
        fh.write("# basis=cluster is the reported one. The manuscript pairs this\n")
        fh.write("#   with the unconstrained orientation agreement from 04q, which\n")
        fh.write("#   is ALSO cluster basis. Pairing across bases is statistic B.\n")
        fh.write("# pct_fan_conditional is the complement: the share of the fan\n")
        fh.write("#   on which the montage preference is conditional.\n")
        w = _csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)
    print(f"\nwrote {out.name}")
    for r in rows:
        print(f"  {r['basis']:<9} {r['pct_fan_favouring_ear']:>5.1f} % favour the ear, "
              f"{r['pct_fan_conditional']:>4.1f} % conditional")
    return rows


def reduce_only() -> int:
    """Re-emit the fractions from the saved arrays. No mesh reads, no solve."""
    import pandas as pd
    pv = {r["electrode"]: float(r["lf_pervoxel_fan"]) for r in
          __import__("csv").DictReader(
              open(config.RESULTS / "04k_temporalis_pervoxel.csv"))}
    pd_ = np.load(config.RESULTS / "04k_temporalis_perdirection.npz")
    mont = pd.read_csv(config.RESULTS / "03_leadfields.csv").set_index(
        "electrode").montage.to_dict()
    emit_fan_fractions(pv, pd_, mont)
    return 0


def main() -> int:
    import sys as _sys
    if "--reduce-only" in _sys.argv:
        return reduce_only()
    import nibabel as nib, pandas as pd
    from scipy.spatial import cKDTree
    from simnibs import mesh_io

    img = nib.load(str(config.DATA / "MIDA_v1.0" / "MIDA_v1_voxels" / "MIDA_v1.nii"))
    lab = np.asarray(img.dataobj); A = img.affine
    tw = nib.affines.apply_affine(A, np.argwhere(lab == TEMP)); tw = tw[tw[:, 0] > 0]
    mw = nib.affines.apply_affine(A, np.argwhere(lab == MAND)); mw = mw[mw[:, 0] > 0]
    d, _ = cKDTree(tw).query(mw)
    ins = mw[d <= 3.0]
    cen = ins.mean(0)
    print(f"insertion: {len(ins):,} mandible voxels within 3 mm of temporalis")
    print(f"  centroid [{cen[0]:.2f} {cen[1]:.2f} {cen[2]:.2f}]")

    lf = pd.read_csv(config.RESULTS / "03_leadfields.csv").set_index("electrode")
    deliv, mont = lf["inv1_mean"], lf["montage"]
    work = config.RESULTS / "leadfields" / "iso"
    names = sorted(x.name for x in work.iterdir() if x.is_dir() and not x.name.startswith("_"))

    pv, pd_ = {}, {}
    dirs_ref = None
    for i, e in enumerate(names, 1):
        h = sorted((work / e).glob("*_scalar.msh"))
        if not h:
            continue
        m = mesh_io.read_msh(str(h[0]))
        tets = m.elm.elm_type == 4
        k = np.flatnonzero(m.elm.tag1[tets] == TEMP)
        E = np.asarray(m.field["E"].value)[tets][k]
        vols = m.elements_volumes_and_areas()[tets][k]
        nodes = m.nodes.node_coord
        cent = nodes[m.elm.node_number_list[tets][k][:, :4] - 1].mean(axis=1)
        right = cent[:, 0] > 0
        E, vols, cent = E[right], vols[right], cent[right]

        N = cen[None, :] - cent
        N /= np.linalg.norm(N, axis=1)[:, None]
        if dirs_ref is None:
            dirs_ref = N.copy()
            ang = np.degrees(np.arccos(np.clip(np.abs(N @ N.mean(0) / np.linalg.norm(N.mean(0))), -1, 1)))
            elev = np.degrees(np.arcsin(np.clip(np.abs(N[:, 2]), -1, 1)))
            print(f"  fan: {len(N):,} tets, angular spread about the mean axis "
                  f"max {ang.max():.1f} deg, p95 {np.percentile(ang,95):.1f}")
            print(f"  elevation from axial: min {elev.min():.1f} deg "
                  f"(near-horizontal) .. max {elev.max():.1f} deg (near-vertical)")
            print(f"  |R| component: median {np.median(np.abs(N[:,0])):.3f}, "
                  f"p95 {np.percentile(np.abs(N[:,0]),95):.3f}\n")

        # per-voxel: each tet with its own direction
        Lv = np.abs(np.einsum("ij,ij->i", E, N))
        o = np.argsort(Lv); c = np.cumsum(vols[o])
        pv[e] = float(Lv[o][np.searchsorted(c, 0.5 * c[-1])]) / deliv[e]

        # per-direction: a subsample of the derived directions applied uniformly
        idx = np.linspace(0, len(N) - 1, 200).astype(int)
        P = np.abs(E @ N[idx].T)
        oo = np.argsort(P, axis=0); cw = np.cumsum(vols[oo], axis=0)
        half = 0.5 * cw[-1, :]
        j = (cw < half).sum(axis=0)
        pd_[e] = np.array([P[oo[j[q], q], q] for q in range(P.shape[1])]) / deliv[e]
        print(f"[{i}/{len(names)}] {e}", flush=True)
        del m, E
        gc.collect()

    pd.DataFrame([{"electrode": e, "lf_pervoxel_fan": v} for e, v in pv.items()]
                 ).to_csv(config.RESULTS / "04k_temporalis_pervoxel.csv", index=False)
    np.savez(config.RESULTS / "04k_temporalis_perdirection.npz", **pd_)
    print(f"wrote 04k_temporalis_pervoxel.csv and _perdirection.npz")

    emit_fan_fractions(pv, pd_, mont)

    jaw = [e for e in pv if mont[e] == "jaw" and e not in NEAR_CUT]
    print("\n=== TEMPORALIS OVER THE DERIVED FAN ===")
    for label, ear in (("pre-registered cluster", CLUSTER),
                       ("all 14 ear sites", [e for e in pv if mont[e] in ("ear", "ceegrid")])):
        g = 20 * np.log10(max(pv[e] for e in jaw) / max(pv[e] for e in ear))
        J = np.max(np.stack([pd_[e] for e in jaw]), axis=0)
        R = np.max(np.stack([pd_[e] for e in ear]), axis=0)
        gd = 20 * np.log10(J / R)
        print(f"\n{label}:")
        print(f"  per-voxel fan gap      : {g:+.3f} dB")
        print(f"  per-direction over fan : median {np.median(gd):+.3f}, "
              f"min {gd.min():+.3f}, max {gd.max():+.3f}")
        print(f"  directions favouring the ear: {100*(gd<0).mean():.1f}% "
              f"({int((gd<0).sum())}/{len(gd)})")
        print(f"  ALL favour the ear: {bool((gd<0).all())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
