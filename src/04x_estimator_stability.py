#!/usr/bin/env python3
r"""
Is the mesh-realisation noise physics, or is it the estimator?

WHAT 04w FOUND. Rebuilding the same nominal mesh moves the per-muscle
jaw-vs-ear gap by up to 1.554 dB, nearly as much as a 4.9 % refinement does
(1.850 dB). That leaves error budget row 1 unbounded and puts a ~1.5 dB term in
front of four of Table 4's verdicts.

THE HYPOTHESIS THIS TESTS. `03_leadfields.compartment_medians` reports a
volume-weighted MEDIAN of |E| over each compartment's tetrahedra. A median is a
single order statistic: it reads one element's value and throws the rest away.
Remeshing re-partitions the compartment, so which element sits at the 50 %
volume mark changes, and the reported number moves even where the field is
identical. A volume-weighted MEAN integrates over the whole compartment and
should be far less sensitive to how that volume is chopped up.

If the mean is stable where the median is not, the 1.5 dB is an artefact of the
estimator and not a physical uncertainty, and the paper needs a Methods
sentence rather than an error budget row.

NO NEW FEM. This re-reads solved meshes already on disk and recomputes both
statistics from the same fields, so the two estimators see byte-identical
input and nothing else can differ between them.

    simnibs_python src/04x_estimator_stability.py \
        --set mac_prod results/leadfields/iso \
        --set pc_prod  <path>/lf_prod/iso \
        --set pc_fine  <path>/lf_fine/iso
"""
from __future__ import annotations

import argparse
import gc
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

JAW = ["buccal", "mental", "midjaw", "submaxillary"]
EAR = ["above_ear", "mastoid", "post_lobule", "pre_tragus"]


def both_stats(res_msh: Path) -> dict:
    """Volume-weighted median AND mean of |E| per compartment, one pass."""
    from simnibs import mesh_io
    m = mesh_io.read_msh(str(res_msh))
    if "E" not in m.field:
        raise RuntimeError(f"no vector E in {res_msh}")
    tets = m.elm.elm_type == 4
    tags = m.elm.tag1[tets]
    vols = m.elements_volumes_and_areas()[tets]
    mag = np.linalg.norm(np.asarray(m.field["E"].value)[tets], axis=1)
    out = {}
    for name, _g, lab, _e in config.MUSCLES:
        if lab is None:
            continue
        k = tags == lab
        if not k.any():
            continue
        v, w = mag[k], vols[k]
        o = np.argsort(v)
        c = np.cumsum(w[o])
        med = float(v[o][np.searchsorted(c, 0.5 * c[-1])])   # exactly 03's
        mean = float(np.sum(v * w) / np.sum(w))              # the candidate
        out[name] = (med, mean)
    del m
    gc.collect()
    return out


def gaps(per_elec: dict, muscles, idx: int) -> dict:
    g = {}
    for mus in muscles:
        j = max(per_elec[e][mus][idx] for e in JAW if e in per_elec)
        r = max(per_elec[e][mus][idx] for e in EAR if e in per_elec)
        g[mus] = 20 * np.log10(j / r)
    return g


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="04x_estimator_stability.py")
    ap.add_argument("--set", nargs=2, action="append", metavar=("NAME", "DIR"),
                    required=True, help="label and a leadfields/iso directory")
    ap.add_argument("--out", type=Path,
                    default=config.RESULTS / "04x_estimator_stability.csv")
    a = ap.parse_args(argv)

    import pandas as pd

    sets = {}
    for name, d in a.set:
        d = Path(d)
        per = {}
        for elec in JAW + EAR:
            hits = sorted((d / elec).glob("*_scalar.msh"))
            if not hits:
                print(f"  {name}/{elec}: no solved mesh, skipped")
                continue
            per[elec] = both_stats(hits[0])
            print(f"  read {name}/{elec}", flush=True)
        missing = [e for e in JAW + EAR if e not in per]
        if missing:
            print(f"ERROR: set {name} is missing {missing}; the cluster gap "
                  f"cannot be formed from a partial set.", file=sys.stderr)
            return 1
        sets[name] = per

    muscles = sorted({m for p in sets.values() for mus in p.values() for m in mus})
    rows = []
    names = [n for n, _ in a.set]
    for i, stat in ((0, "median"), (1, "mean")):
        g = {n: gaps(sets[n], muscles, i) for n in names}
        # every consecutive pair of sets, labelled by the two set names, so
        # the script works with two sets or five and never mislabels a pair
        for base, other in zip(names, names[1:]):
            label = f"{base}->{other}"
            for mus in muscles:
                rows.append(dict(statistic=stat, comparison=label, muscle=mus,
                                 base_dB=round(g[base][mus], 4),
                                 other_dB=round(g[other][mus], 4),
                                 delta_dB=round(g[other][mus] - g[base][mus], 4)))
    d = pd.DataFrame(rows)
    d["abs_delta"] = d.delta_dB.abs()
    d.to_csv(a.out, index=False)

    print(f"\nwrote {a.out}\n")
    comps = list(dict.fromkeys(d.comparison))
    print(f"{'statistic':<10}{'comparison':<24}{'max |delta| dB':>16}"
          f"{'mean |delta| dB':>18}")
    summ = {}
    for stat in ("median", "mean"):
        for comp in comps:
            s = d[(d.statistic == stat) & (d.comparison == comp)]
            if s.empty:
                continue
            summ[(stat, comp)] = (s.abs_delta.max(), s.abs_delta.mean())
            print(f"{stat:<10}{comp:<24}{s.abs_delta.max():>16.4f}"
                  f"{s.abs_delta.mean():>18.4f}")

    print("\nVERDICT")
    key = comps[0]
    if ("median", key) in summ and ("mean", key) in summ:
        mrb = summ[("median", key)][0]
        arb = summ[("mean", key)][0]
        print(f"  {key}: median {mrb:.4f} dB -> mean {arb:.4f} dB "
              f"({mrb / arb:.1f}x smaller)" if arb > 0 else "")
        if arb < 0.272:
            print("  The MEAN puts rebuild noise UNDER the 0.272 dB electrode "
                  "floor.\n  The 1.5 dB is an ESTIMATOR ARTEFACT, not a physical "
                  "uncertainty.\n  Fix: switch compartment_medians to a "
                  "volume-weighted mean and re-run.\n  The paper then needs a "
                  "Methods sentence, NOT an error-budget row.")
        elif arb < 0.5 * mrb:
            print("  The mean roughly halves it but does not clear the floor. "
                  "Partly estimator,\n  partly real. Both a Methods change and a "
                  "budget row are warranted.")
        else:
            print("  The mean does NOT help. The movement is in the field, not "
                  "the statistic.\n  Mesh realisation is a real physical term "
                  "and belongs in the error budget.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
