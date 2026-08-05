#!/usr/bin/env python3
r"""
Stage 4d. THE DECIDING QUESTION: does the sign of the jaw-vs-ear gap survive
every possible source orientation?

WHY THIS IS THE RIGHT TEST
--------------------------
The orientation envelope on the ABSOLUTE lead field is ~14 dB, roughly four
times the jaw-vs-ear effect. Taken alone that looks fatal. It is not, and the
reason is the same cancellation the error budget is built on:

    a source has ONE orientation, and BOTH electrodes see that same source at
    that same orientation.

So the honest test is not "how wide is the envelope at each electrode
separately" -- that is what 04b reported, and min_jaw and min_ear generally
occur at DIFFERENT directions, so differencing them is meaningless. The test is:
sweep a common n-hat over the hemisphere, and at EACH direction compute the gap
using that same direction at both electrodes. Then ask whether the SIGN of the
gap is stable across the entire sweep.

If the sign never flips, the finding is robust to the one thing MIDA cannot
tell us -- fibre direction -- which is a stronger statement than any point
estimate. If it flips, the claim must be conditioned on fibre direction.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/04d_orientation_sign.py
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
NEAR_CUT = ("hyoid", "submental_lat", "submental_mid")
MUSCLES = [(n, lab) for n, _g, lab, _e in config.MUSCLES if lab is not None]
MAX_ELEM = 200_000


def wmedian(v, w):
    o = np.argsort(v)
    c = np.cumsum(w[o])
    return v[o][np.searchsorted(c, 0.5 * c[-1])]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="04d_orientation_sign.py")
    ap.add_argument("--n-dirs", type=int, default=200)
    ap.add_argument("--out", type=Path,
                    default=config.RESULTS / "04d_orientation_sign.csv")
    a = ap.parse_args(argv)

    from simnibs import mesh_io

    # ONE fixed direction set, shared by every electrode and every muscle, so
    # that column j always means the same physical orientation everywhere.
    N = orientation.fibonacci_hemisphere(a.n_dirs)
    print(f"common hemisphere sweep: {len(N)} directions\n")

    mont = {}
    for r in csv.DictReader(
            (config.RESULTS / "02_electrode_positions.csv").open()):
        if r.get("verified") == "held" or not r["R"]:
            continue
        mont[r["name"]] = r.get("montage", "")

    names = sorted(d.name for d in WORKDIR.iterdir()
                   if d.is_dir() and not d.name.startswith("_"))
    # per muscle: {electrode: array over directions}
    L = {m: {} for m, _ in MUSCLES}
    rng = np.random.default_rng(0)

    t0 = time.time()
    for i, name in enumerate(names, 1):
        hits = sorted((WORKDIR / name).glob("*_scalar.msh"))
        if not hits:
            continue
        print(f"[{i}/{len(names)}] {name}", flush=True)
        m = mesh_io.read_msh(str(hits[0]))
        tets = m.elm.elm_type == 4
        tags = m.elm.tag1[tets]
        vols = m.elements_volumes_and_areas()[tets]
        E = np.asarray(m.field["E"].value)[tets]
        for mus, lab in MUSCLES:
            k = np.flatnonzero(tags == lab)
            if k.size == 0:
                continue
            if k.size > MAX_ELEM:
                k = rng.choice(k, MAX_ELEM, replace=False)
            Ek, wk = E[k], vols[k]
            # (n_elem, n_dirs) projection, then a volume-weighted median per dir
            P = np.abs(Ek @ N.T)
            L[mus][name] = np.array(
                [wmedian(P[:, j], wk) for j in range(P.shape[1])])
            del P
        del m, E
        gc.collect()

    rows = []
    print(f"\n{'muscle':<24}{'gap@min':>10}{'gap@max':>10}{'median':>10}"
          f"{'  sign stable?':>16}")
    print("-" * 72)
    for mus, _ in MUSCLES:
        d = L[mus]
        jaw = [e for e in d if mont.get(e) == "jaw" and e not in NEAR_CUT]
        ear = [e for e in d if mont.get(e) in ("ear", "ceegrid")]
        if not jaw or not ear:
            continue
        J = np.max(np.stack([d[e] for e in jaw]), axis=0)   # best jaw per dir
        R = np.max(np.stack([d[e] for e in ear]), axis=0)   # best ear per dir
        gap = 20 * np.log10(J / R)
        stable = bool(np.all(gap > 0) or np.all(gap < 0))
        rows.append(dict(muscle=mus, gap_min_dB=round(float(gap.min()), 4),
                         gap_max_dB=round(float(gap.max()), 4),
                         gap_median_dB=round(float(np.median(gap)), 4),
                         gap_range_dB=round(float(gap.max() - gap.min()), 4),
                         favours=("jaw" if np.median(gap) > 0 else "ear"),
                         sign_stable=stable,
                         frac_favouring_jaw=round(float((gap > 0).mean()), 4),
                         n_dirs=len(gap)))
        print(f"{mus:<24}{gap.min():>+10.2f}{gap.max():>+10.2f}"
              f"{np.median(gap):>+10.2f}"
              f"{('  YES' if stable else '  ** FLIPS **'):>16}")

    with a.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\nwrote {a.out}  ({(time.time()-t0)/60:.1f} min)")
    flips = [r["muscle"] for r in rows if not r["sign_stable"]]
    print(f"\nSIGN FLIPS ACROSS THE FULL SWEEP: "
          f"{flips if flips else 'NONE'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
