#!/usr/bin/env python3
r"""
Extend the derived per-voxel fibre fan beyond temporalis.

PRE-COMMITTED IN paper/PREREG_fibre_fan_extension.md, written before this ran.
Read it before reading any number out of here. The rules that matter:

  R1  every muscle attempted is reported, whichever way it moves
  R2  a verdict changes only if the exact C(14,4) interval changes side
  R3  where the derived field exists it governs, the uniform sweep is reported
      beside it
  R4  a fan spanning under 5 degrees is reported as "no fan", not reclassified
  R5  no change is itself a result and gets written into §4.7

WHAT THIS IS. §2.5.1 closes with "That intersection is available for temporalis
alone", and §4.7 names masseter and lateral pterygoid as muscles for which a
per-voxel fan toward a common attachment is the right treatment, untested. Both
insert on the mandible, the same bone temporalis inserts on, so the construction
is `04k_temporalis_fan.py` with the compartment label changed and nothing else:

    insertion    = centroid of mandible (36, right) voxels within 3.0 mm of the
                   muscle compartment
    n_hat(voxel) = normalise(insertion - voxel)

ONE PASS OVER THE MESHES. 04k reads all 22 solved meshes for its one muscle. Two
more muscles the same way would be 44 more reads of ~900 MB each. Every muscle
is extracted from each mesh while it is open instead, so the cost stays at 22
reads no matter how many muscles are added.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/04v_fibre_fan.py
"""
from __future__ import annotations

import argparse
import gc
import itertools
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402

MANDIBLE = 36
CONTACT_MM = 3.0          # inherited from 04k; the prereg forbids tuning it
DEGENERATE_FAN_DEG = 5.0   # R4: too narrow to be a fan
MAX_PATCH_FRACTION = 0.60  # R4b: patch this close to the compartment's own
COHERENCE_FLOOR = 0.60     #      extent, or directions this incoherent, means
                           #      the voxel-to-centroid construction is void.
                           #      See Amendment 1 of the prereg.
NEAR_CUT = {"hyoid", "submental_lat", "submental_mid"}
CLUSTER = ["above_ear", "mastoid", "post_lobule", "pre_tragus"]

# muscle -> (compartment label, insertion bone label). Fixed by the prereg.
TARGETS = {
    "masseter":          (66, MANDIBLE),
    "lateral_pterygoid": (65, MANDIBLE),
}


def exact_interval(pv, jaw, ear):
    """Median and 2.5/97.5 percentiles over all C(14,4) four-site ear montages.

    Same construction as 04p's exact_pervoxel, including the percentile bounds
    rather than min/max, so the number is comparable to the published
    temporalis interval and to nothing else.
    """
    J = max(pv[e] for e in jaw)
    d = np.array([20 * np.log10(J / max(pv[e] for e in s))
                  for s in itertools.combinations(sorted(ear), 4)])
    lo, hi = np.percentile(d, [2.5, 97.5])
    return d, float(np.median(d)), float(lo), float(hi)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="04v_fibre_fan.py")
    ap.add_argument("--muscles", nargs="*", default=sorted(TARGETS))
    a = ap.parse_args(argv)

    import nibabel as nib
    import pandas as pd
    from scipy.spatial import cKDTree
    from simnibs import mesh_io

    targets = {m: TARGETS[m] for m in a.muscles}

    # ---- insertions, from MIDA's own labels
    img = nib.load(str(config.DATA / "MIDA_v1.0" / "MIDA_v1_voxels" / "MIDA_v1.nii"))
    lab = np.asarray(img.dataobj)
    A = img.affine
    bone = {}
    centroid = {}
    print("INSERTIONS, derived from the label volume")
    for m, (mlab, blab) in targets.items():
        if blab not in bone:
            w = nib.affines.apply_affine(A, np.argwhere(lab == blab))
            bone[blab] = w[w[:, 0] > 0]
        mw = nib.affines.apply_affine(A, np.argwhere(lab == mlab))
        mw = mw[mw[:, 0] > 0]
        if len(mw) == 0:
            print(f"  {m}: EMPTY compartment on the right side, skipped")
            continue
        d, _ = cKDTree(mw).query(bone[blab])
        ins = bone[blab][d <= CONTACT_MM]
        if len(ins) < 20:
            print(f"  {m}: only {len(ins)} bone voxels within {CONTACT_MM} mm; "
                  f"the construction found no contact patch. Reported as a "
                  f"failure, NOT retried at a larger threshold (prereg).")
            continue
        c = ins.mean(0)
        centroid[m] = c
        print(f"  {m:<20}{len(ins):>6,} bone voxels in contact, centroid RAS "
              f"[{c[0]:7.2f} {c[1]:7.2f} {c[2]:7.2f}], "
              f"{len(mw):,} compartment voxels")
    if not centroid:
        print("no usable insertions; nothing to do", file=sys.stderr)
        return 1

    lf = pd.read_csv(config.RESULTS / "03_leadfields.csv").set_index("electrode")
    deliv, mont = lf["inv1_mean"], lf["montage"]
    work = config.RESULTS / "leadfields" / "iso"
    names = sorted(x.name for x in work.iterdir()
                   if x.is_dir() and not x.name.startswith("_"))

    pv = {m: {} for m in centroid}
    pdir = {m: {} for m in centroid}
    fan_reported = set()

    print(f"\nreading {len(names)} solved meshes once, "
          f"{len(centroid)} muscle(s) per mesh")
    for i, e in enumerate(names, 1):
        h = sorted((work / e).glob("*_scalar.msh"))
        if not h:
            continue
        msh = mesh_io.read_msh(str(h[0]))
        tets = msh.elm.elm_type == 4
        tags = msh.elm.tag1[tets]
        Eall = np.asarray(msh.field["E"].value)[tets]
        vall = msh.elements_volumes_and_areas()[tets]
        call = msh.nodes.node_coord[msh.elm.node_number_list[tets][:, :4] - 1] \
                 .mean(axis=1)
        for m, c in centroid.items():
            mlab = targets[m][0]
            k = np.flatnonzero(tags == mlab)
            E, vols, cent = Eall[k], vall[k], call[k]
            right = cent[:, 0] > 0
            E, vols, cent = E[right], vols[right], cent[right]
            if len(E) == 0:
                continue
            N = c[None, :] - cent
            N /= np.linalg.norm(N, axis=1)[:, None]

            if m not in fan_reported:
                fan_reported.add(m)
                axis = N.mean(0) / np.linalg.norm(N.mean(0))
                ang = np.degrees(np.arccos(np.clip(np.abs(N @ axis), -1, 1)))
                spread = float(ang.max())
                tag = ("NO FAN (R4): spans under "
                       f"{DEGENERATE_FAN_DEG} deg, a single axis"
                       if spread < DEGENERATE_FAN_DEG else "fan")
                print(f"  {m}: {len(N):,} tets, spread about the mean axis "
                      f"max {spread:.1f} deg, p95 "
                      f"{np.percentile(ang, 95):.1f} deg  [{tag}]")

            Lv = np.abs(np.einsum("ij,ij->i", E, N))
            o = np.argsort(Lv)
            cw = np.cumsum(vols[o])
            pv[m][e] = float(Lv[o][np.searchsorted(cw, 0.5 * cw[-1])]) / deliv[e]

            idx = np.linspace(0, len(N) - 1, 200).astype(int)
            P = np.abs(E @ N[idx].T)
            oo = np.argsort(P, axis=0)
            cw2 = np.cumsum(vols[oo], axis=0)
            j = (cw2 < 0.5 * cw2[-1, :]).sum(axis=0)
            pdir[m][e] = np.array([P[oo[j[q], q], q]
                                   for q in range(P.shape[1])]) / deliv[e]
        print(f"[{i}/{len(names)}] {e}", flush=True)
        del msh, Eall, vall, call
        gc.collect()

    # ---- report, unconditionally (R1)
    env = pd.read_csv(config.RESULTS / "04q_table4_envelope.csv", comment="#") \
            .set_index("muscle")
    rows = []
    print("\n=== DERIVED FAN vs THE PUBLISHED UNIFORM SWEEP (R3) ===")
    for m in pv:
        jaw = [e for e in pv[m] if mont[e] == "jaw" and e not in NEAR_CUT]
        ear = [e for e in pv[m] if mont[e] in ("ear", "ceegrid")]
        d, med, lo, hi = exact_interval(pv[m], jaw, ear)
        pub_lo = float(env.loc[m, "gap_lo_dB"])
        pub_hi = float(env.loc[m, "gap_hi_dB"])
        pub_spans = pub_lo < 0 < pub_hi
        new_spans = lo < 0 < hi
        flipped = pub_spans != new_spans          # R2
        rows.append(dict(
            muscle=m, construction="pervoxel_fan_EXACT",
            derived_median_dB=round(med, 4),
            derived_lo_dB=round(lo, 4), derived_hi_dB=round(hi, 4),
            derived_spans_zero=new_spans,
            published_uniform_lo_dB=round(pub_lo, 4),
            published_uniform_hi_dB=round(pub_hi, 4),
            published_spans_zero=pub_spans,
            verdict_changed_R2=flipped,
            pct_subsets_favouring_ear=round(100 * float((d < 0).mean()), 1),
            n_subsets=len(d),
            insertion_R=round(float(centroid[m][0]), 3),
            insertion_A=round(float(centroid[m][1]), 3),
            insertion_S=round(float(centroid[m][2]), 3),
        ))
        print(f"\n  {m}")
        print(f"    published, uniform sweep : [{pub_lo:+7.3f}, {pub_hi:+7.3f}]"
              f"  spans zero: {pub_spans}")
        print(f"    derived fan, per-voxel   : [{lo:+7.3f}, {hi:+7.3f}]"
              f"  spans zero: {new_spans}   median {med:+.3f}")
        print(f"    VERDICT CHANGED (R2): {flipped}")

    out = config.RESULTS / "04v_fibre_fan_extension.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    for m in pv:
        pd.DataFrame([{"electrode": e, "lf_pervoxel_fan": v}
                      for e, v in pv[m].items()]).to_csv(
            config.RESULTS / f"04v_{m}_pervoxel.csv", index=False)
    print(f"\nwrote {out} and {len(pv)} per-electrode file(s)")
    print("\nR5: whether or not a verdict moved, §4.7's 'untested here' is now "
          "false for these muscles and must be rewritten.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
