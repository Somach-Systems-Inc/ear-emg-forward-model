#!/usr/bin/env python3
"""
Articulatory volume-conductor exposure: common-mode vs distance-dependent.

Reads the completed air/filled solve pairs and DECOMPOSES the per-electrode
shift before testing, because the two components answer different questions:

    common-mode = median shift across all electrodes
    residual    = per-electrode shift minus common-mode

Filling 21,339 mm3 of oral cavity plus 43,650 mm3 of nasopharynx lowers total
head conductance and redistributes current at EVERY electrode, including ear
sites 76 mm away. A large global term with no distance dependence would pass a
raw-shift test while the hypothesis under test fails.

RE-REGISTERED CRITERION (criterion 2 amended before any number was seen):
  (a) Spearman rho(distance, median |dB|) NEGATIVE
      -- unaffected by the decomposition; rank order is invariant to a
         constant offset, so this is the criterion as originally written
  (b) max |RESIDUAL| exceeds 0.43 dB   <- was max |raw shift|
Both must hold. Failing either = FALSIFIED.

REPORTED SEPARATELY:
  common-mode -> a Methods term, now measured: "head models omitting the oral
                 cavity and nasopharynx are systematically off by X dB in
                 absolute lead field". This is the air-void term.
  residual    -> the hypothesis under test.

UPPER BOUND: MIDA is static. Complete cavity filling is the most extreme
configuration change physically available, so real articulation lies strictly
inside it. A residual below the noise floor at the extreme means real speech is
below it too -- which is a strong negative, not a null.
"""
from __future__ import annotations
import csv, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402

ELECS = ["hyoid", "buccal", "submental_lat", "midjaw", "cg10", "pre_tragus",
         "mastoid", "above_ear"]
CAVITY = (31, 97)
# The floor is a MEASURED quantity, not a constant. It was first measured with
# a 15 mm electrode while production runs 10 mm, so it is being re-measured.
# Until that lands this analysis refuses to run -- see the ordering guard.
REGISTERED_FLOOR_DB = 0.43           # what criterion (b) was registered against
FLOOR_FILE = "electrode_meshing_floor.txt"   # written by the 10 mm re-run


def medians(res_dir: Path):
    from simnibs import mesh_io
    m = mesh_io.read_msh(str(sorted(res_dir.glob("*_scalar.msh"))[0]))
    E = np.asarray(m.field["E"].value)
    if E.ndim != 2 or E.shape[1] != 3:
        raise RuntimeError(f"E must be (n,3), got {E.shape}")
    tets = m.elm.elm_type == 4
    tags, vols = m.elm.tag1[tets], m.elements_volumes_and_areas()[tets]
    mag = np.linalg.norm(E[tets], axis=1)
    out = {}
    for name, _, lab, _ in config.MUSCLES:
        if lab is None:
            continue
        k = tags == lab
        if not k.any():
            continue
        v, w = mag[k], vols[k]
        o = np.argsort(v)
        c = np.cumsum(w[o])
        out[name] = float(v[o][np.searchsorted(c, 0.5 * c[-1])])
    return out


def read_measured_floor():
    """Corrected floor, or None. Ordering guard: the cavity verdict must not be
    computed before the floor it is judged against has been measured and
    committed."""
    f = config.RESULTS / FLOOR_FILE
    if not f.exists():
        return None
    for line in f.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            try:
                return float(line.split()[0])
            except ValueError:
                continue
    return None


def main() -> int:
    from scipy.stats import spearmanr
    from scipy.spatial import cKDTree
    import nibabel as nib

    img = nib.load(str(config.DATA / "MIDA_v1.0/MIDA_v1_voxels/MIDA_v1.nii"))
    arr = np.asanyarray(img.dataobj)
    aff = img.affine.astype(np.float64)
    cav = np.vstack([np.argwhere(arr == l).astype(np.float64) @ aff[:3, :3].T
                     + aff[:3, 3] for l in CAVITY])
    tree = cKDTree(cav)
    pos = {r["name"]: np.array([float(r["R"]), float(r["A"]), float(r["S"])])
           for r in csv.DictReader(
               (config.RESULTS / "02_electrode_positions.csv").open())
           if r.get("verified") != "held" and r["R"] != ""}

    if read_measured_floor() is None:
        print("ORDERING GUARD: the 10 mm electrode-meshing floor has not been\n"
              "measured and committed yet. The cavity verdict is judged against\n"
              "that floor, so measuring it afterwards would let the threshold\n"
              f"follow the result. Write {config.RESULTS / FLOOR_FILE} first.\n",
              file=sys.stderr)
        return 2

    import preflight

    rows = []
    for e in ELECS:
        a = config.RESULTS / f"cavity/air__{e}"
        f = config.RESULTS / f"cavity/filled__{e}"
        if not (a.exists() and f.exists()):
            print(f"missing solve pair for {e}", file=sys.stderr)
            return 1
        # Read the solver's own calibration line for BOTH halves of the pair.
        # SimNIBS writes the result file whether or not the solve delivered the
        # requested current, so a verdict computed without reading this is a
        # verdict that has not checked its own inputs.
        cal_a = preflight.read_calibration(a)
        cal_f = preflight.read_calibration(f)
        A, F = medians(a), medians(f)
        db = [20 * np.log10(F[n] / A[n]) for n in sorted(A)]
        rows.append(dict(elec=e, dist=float(tree.query(pos[e])[0]),
                         signed=float(np.median(db)),
                         absmed=float(np.median(np.abs(db))),
                         absmax=float(np.max(np.abs(db))),
                         cal_air=cal_a, cal_filled=cal_f,
                         warned=(cal_a is not None or cal_f is not None)))

    common = float(np.median([r["signed"] for r in rows]))
    for r in rows:
        r["residual"] = r["signed"] - common

    rows.sort(key=lambda r: r["dist"])
    print(f"common-mode shift (median across {len(rows)} electrodes): "
          f"{common:+.3f} dB\n")
    print(f"{'electrode':<16}{'dist mm':>9}{'signed dB':>11}"
          f"{'residual':>10}{'med|dB|':>9}")
    print("-" * 56)
    for r in rows:
        print(f"{r['elec']:<16}{r['dist']:>9.1f}{r['signed']:>+11.3f}"
              f"{r['residual']:>+10.3f}{r['absmed']:>9.3f}")

    def criteria(subset):
        """(a) rank correlation, (b) max |residual|, on any subset of rows."""
        rr, pp = spearmanr([r["dist"] for r in subset],
                           [r["absmed"] for r in subset])
        return rr, pp, max(abs(r["residual"]) for r in subset)

    rho, p, max_res = criteria(rows)
    a_ok = rho < 0

    # ---- calibration status of every input solve, stated before the verdict
    warned = [r for r in rows if r["warned"]]
    print("\ncalibration reported by the solver, per input solve:")
    for r in rows:
        ca = "clean" if r["cal_air"] is None else f"{r['cal_air']:.2f}%"
        cf = "clean" if r["cal_filled"] is None else f"{r['cal_filled']:.2f}%"
        print(f"  {r['elec']:<16} air {ca:>8}   filled {cf:>8}")
    if warned:
        print(f"\n  {len(warned)} of {len(rows)} electrode pairs contain a "
              f"warned solve.")
        print("  Two populations have been measured: 200.00% is the")
        print("  conductivity-conditioning failure and is fatal; 11-15% on a")
        print("  well-conditioned custom mesh has been measured as a false")
        print("  positive (5 of 16 sphere solves warned while matching the")
        print("  analytic oracle, and were not less accurate).")
        print("  No threshold separating them is invented here. Instead the")
        print("  verdict is recomputed without the warned pairs, below, so")
        print("  their influence is visible rather than assumed away.")

    print(f"\n(a) Spearman rho(distance, median|dB|) = {rho:+.3f}  p = {p:.3f}"
          f"   -> {'PASS' if a_ok else 'FAIL'}")
    print(f"(b) max |residual| = {max_res:.4f} dB")
    print(f"    (max |raw shift| was {max(abs(r['signed']) for r in rows):.3f} dB"
          f" -- NOT the test)")

    # THE FLIP POINT, not a binary. Criterion (b) is "residual exceeds the
    # electrode-meshing floor", so the residual IS the floor value at which
    # the verdict changes. Reporting it locates the result on the axis and
    # removes the goalpost: the floor measurement then places the result
    # rather than deciding it.
    print(f"\n    FLIP POINT: criterion (b) passes for any floor below "
          f"{max_res:.4f} dB\n                and fails for any floor above it.")

    measured = read_measured_floor()
    verdicts = [("registered 0.43 dB (15 mm electrode)", REGISTERED_FLOOR_DB)]
    if measured is not None:
        verdicts.append((f"measured {measured:.4f} dB (10 mm, production)",
                         measured))
    print(f"\n    {'floor':<40}{'(b)':>6}   {'overall':>9}")
    for lbl, fl in verdicts:
        b = max_res > fl
        print(f"    {lbl:<40}{'PASS' if b else 'FAIL':>6}   "
              f"{'SURVIVES' if (a_ok and b) else 'FALSIFIED':>9}")

    b_ok = max_res > (measured if measured is not None else REGISTERED_FLOOR_DB)
    print("\nVERDICT:", "SURVIVES" if (a_ok and b_ok) else "FALSIFIED",
          f"(against the {'measured' if measured is not None else 'registered'}"
          f" floor)")

    # ---- does the verdict depend on the warned solves?
    if warned:
        keep = [r for r in rows if not r["warned"]]
        fl = measured if measured is not None else REGISTERED_FLOOR_DB
        if len(keep) < 3:
            print(f"\n  Only {len(keep)} clean pairs remain; too few for a rank"
                  f" correlation.\n  The verdict CANNOT be shown independent "
                  f"of the warned solves. Re-solve them.")
        else:
            rho2, p2, mr2 = criteria(keep)
            v2 = (rho2 < 0) and (mr2 > fl)
            print(f"\n  excluding {len(warned)} warned pair(s), n={len(keep)}:")
            print(f"    rho = {rho2:+.3f} (p = {p2:.3f}), "
                  f"max |residual| = {mr2:.4f} dB")
            print(f"    verdict {'SURVIVES' if v2 else 'FALSIFIED'}"
                  f"  ->  {'UNCHANGED' if v2 == (a_ok and b_ok) else 'CHANGED'}"
                  f" by the exclusion")
            if v2 != (a_ok and b_ok):
                print("    The verdict depends on solves the solver itself")
                print("    flagged. It is NOT reportable until those solves")
                print("    are re-run clean.")
    if not (a_ok and b_ok):
        print("\nThis is a STRONG NEGATIVE, not a null. Complete cavity filling")
        print("is the most extreme configuration change physically available,")
        print("so real articulation lies strictly inside it. A residual below")
        print("the noise floor at the extreme means real speech is below it too.")
    print(f"\nMETHODS TERM (measured, independent of the verdict): head models")
    print(f"omitting the oral cavity and nasopharynx are systematically off by")
    print(f"{abs(common):.3f} dB in absolute lead field.")

    out = config.RESULTS / "03_cavity_exposure.csv"
    with out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nWritten: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
