#!/usr/bin/env python3
"""
Conductivity sensitivity bound: do the unsourced values matter?

Table 1 assigns a conductivity to all 116 mesh tags. 17 of those are judgement
calls rather than lookups. This bounds their influence by solving one
representative montage under four conductivity conditions and reporting the dB
envelope per muscle compartment:

  a  baseline    every tag at its Table 1 value
  b  generic     the 17 judgement tags collapsed to one generic soft-tissue
                 value, testing whether the specific assignment mattered at all
  c1 all-low     every judgement tag at its sigma_low simultaneously
  c2 all-high    every judgement tag at its sigma_high simultaneously

c1 and c2 are both run because which end moves the result most is not known in
advance; asserting one would be guessing. The reported envelope is the worst
case across the set.

If the envelope is under ~0.1 dB, Methods carries one sentence and the 17
judgement calls stop being judgement calls in any way that affects a result.
Either way this produces a real error-budget row, "unsourced tissue
conductivity", classified by whether it survives into site-to-site ratios.

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/03b_conductivity_bound.py
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402

TABLE1 = config.RESULTS / "01_table1_conductivities.csv"
GENERIC_SOFT_TISSUE = 0.30      # S/m, a deliberately blunt stand-in
INJECT_FROM = "hyoid"
INJECT_TO = "earlobe_contra"


def load_table1():
    rows = list(csv.DictReader(TABLE1.open()))
    if not rows:
        raise RuntimeError(f"{TABLE1} is empty")
    return rows


def conductivity_sets(rows):
    """Four label -> sigma dicts, one per condition."""
    base = {int(r["mida_label"]): float(r["sigma_S_per_m"]) for r in rows}
    judge = [r for r in rows if r["assignment"] == "judgement"]

    generic = dict(base)
    for r in judge:
        generic[int(r["mida_label"])] = GENERIC_SOFT_TISSUE

    low, high = dict(base), dict(base)
    for r in judge:
        lab = int(r["mida_label"])
        if r["sigma_low"]:
            low[lab] = max(float(r["sigma_low"]), 1e-15)
        if r["sigma_high"]:
            high[lab] = max(float(r["sigma_high"]), 1e-15)

    return {"a_baseline": base, "b_generic": generic,
            "c1_all_low": low, "c2_all_high": high}, len(judge)


def solve(mesh: Path, out: Path, pos, sigmas, label):
    from simnibs import sim_struct, run_simnibs
    out.parent.mkdir(parents=True, exist_ok=True)
    S = sim_struct.SESSION()
    S.fnamehead = str(mesh)
    S.pathfem = str(out)
    S.fields = "E"
    S.open_in_gmsh = False
    S.map_to_surf = False
    t = S.add_tdcslist()
    t.currents = [config.INJECTION_CURRENT_A, -config.INJECTION_CURRENT_A]
    for lab, sig in sigmas.items():
        t.cond[lab - 1].value = float(sig)
        t.cond[lab - 1].name = f"tag{lab}"
    for j, nm in enumerate((INJECT_FROM, INJECT_TO)):
        el = t.add_electrode()
        el.channelnr = j + 1
        el.centre = list(pos[nm])
        el.shape = "ellipse"
        el.dimensions = [config.ELECTRODE_DIAMETER_MM] * 2
        el.thickness = 2
    print(f"  solving {label} ...", flush=True)
    run_simnibs(S)
    hits = sorted(out.glob("*_scalar.msh")) or sorted(out.glob("*.msh"))
    return hits[0]


def compartment_medians(res: Path):
    from simnibs import mesh_io
    m = mesh_io.read_msh(str(res))
    if "E" not in m.field:
        raise RuntimeError(f"no vector E in {res}; have {list(m.field)}")
    E = np.asarray(m.field["E"].value)
    if E.ndim != 2 or E.shape[1] != 3:
        raise RuntimeError(f"E must be (n,3), got {E.shape}")
    tets = m.elm.elm_type == 4
    tags = m.elm.tag1[tets]
    vols = m.elements_volumes_and_areas()[tets]
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="03b_conductivity_bound.py")
    ap.add_argument("--mesh", type=Path, default=config.DATA / "mida_headneck.msh")
    ap.add_argument("--workdir", type=Path, default=config.RESULTS / "cond_bound")
    ap.add_argument("--out", type=Path,
                    default=config.RESULTS / "03_conductivity_bound.csv")
    a = ap.parse_args(argv)

    if not a.mesh.exists():
        print(f"ERROR: no mesh at {a.mesh}", file=sys.stderr)
        return 1
    if not TABLE1.exists():
        print(f"ERROR: {TABLE1} missing; run src/build_table1.py", file=sys.stderr)
        return 1

    rows = load_table1()
    sets, n_judge = conductivity_sets(rows)
    print(f"Table 1: {len(rows)} tags, {n_judge} judgement calls")
    print(f"conditions: {', '.join(sets)}")
    print(f"generic soft-tissue stand-in: {GENERIC_SOFT_TISSUE} S/m\n")

    pos = {r["name"]: np.array([float(r["R"]), float(r["A"]), float(r["S"])])
           for r in csv.DictReader(
               (config.RESULTS / "02_electrode_positions.csv").open())
           if r.get("verified") != "held" and r["R"] != ""}
    for nm in (INJECT_FROM, INJECT_TO):
        if nm not in pos:
            print(f"ERROR: {nm} has no accepted coordinate", file=sys.stderr)
            return 1

    res = {}
    for cname, sig in sets.items():
        res[cname] = compartment_medians(
            solve(a.mesh, a.workdir / cname, pos, sig, cname))

    base = res["a_baseline"]
    others = [c for c in sets if c != "a_baseline"]
    print(f"\n{'compartment':<24} {'baseline':>11}" +
          "".join(f"{c:>14}" for c in others) + f"{'envelope':>11}")
    print("-" * 96)
    out_rows, worst = [], 0.0
    for name in base:
        line = f"{name:<24} {base[name]:>11.4e}"
        rec = {"compartment": name, "baseline_V_per_m": base[name]}
        dbs = []
        for c in others:
            v = res[c].get(name, float("nan"))
            db = 20 * np.log10(v / base[name]) if base[name] > 0 else np.nan
            dbs.append(db)
            line += f"{db:>+13.3f}dB"
            rec[f"{c}_dB"] = round(float(db), 4)
        env = float(np.nanmax(np.abs(dbs))) if dbs else float("nan")
        rec["envelope_dB"] = round(env, 4)
        worst = max(worst, env)
        line += f"{env:>10.3f}"
        print(line)
        out_rows.append(rec)

    print(f"\nworst-case envelope across all compartments: {worst:.3f} dB")
    print(f"electrode-meshing noise floor (measured)   : 0.430 dB")
    if worst < 0.1:
        print("\nVERDICT: under 0.1 dB. The 17 judgement calls do not affect any\n"
              "         result. Methods carries one sentence; the error-budget\n"
              "         row is bounded and negligible.")
    elif worst < 0.43:
        print("\nVERDICT: above 0.1 dB but below the electrode-meshing noise\n"
              "         floor, so it is real but not the limiting term.")
    else:
        print("\nVERDICT: exceeds the meshing noise floor. Unsourced conductivity\n"
              "         is a material error-budget term and the widest-range\n"
              "         judgement rows need sourced values.")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    print(f"\nWritten: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
