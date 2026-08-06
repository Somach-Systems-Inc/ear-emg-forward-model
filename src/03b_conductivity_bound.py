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
REFERENCE = "earlobe_contra"

# Per (compartment x electrode), not per compartment. A per-compartment
# marginal averages over electrodes and would hide a site-localised effect,
# which is the effect most likely to be present here.
#
# Four representative sites rather than all 23: two jaw, two ear, chosen to
# span the boundary-proximity and air-void gradients. At ~2m50s per solve on
# the 12.3M-tet mesh, all 23 would be 7+ hours per condition.
ELECTRODES = ["hyoid", "submental_mid", "mastoid", "above_ear"]

# Pneumatised temporal-bone structures. The retroauricular region holds the
# head's only large superficial skin-adjacent air voids, and they sit between
# the ear electrodes and the target muscles.
AIR_VOID_LABELS = {
    30: "Air Internal - Mastoid",
    85: "Ear Auditory Canal",
    86: "Ear Pharyngotympanic Tube",
}
AIR_VOID_FILL = "bone_compact"   # they are cavities within the temporal bone


def load_table1():
    rows = list(csv.DictReader(TABLE1.open()))
    if not rows:
        raise RuntimeError(f"{TABLE1} is empty")
    return rows


def conductivity_sets(rows):
    """Four label -> sigma dicts, one per condition."""
    base = {int(r["mida_label"]): float(r["sigma_S_per_m"]) for r in rows}
    judge = [r for r in rows if r["assignment"] == "judgement"]
    # Every classification test asserts its matched set is non-empty. A silent
    # empty match is how the air sweep ran four identical solves.
    assert judge, "no rows with assignment == 'judgement' in Table 1"

    generic = dict(base)
    for r in judge:
        generic[int(r["mida_label"])] = GENERIC_SOFT_TISSUE

    low, high = dict(base), dict(base)
    for r in judge:
        lab = int(r["mida_label"])
        if r["sigma_low"]:
            # Clamp to the CURRENT air value, never a literal. A hardcoded
            # 1e-15 here would silently reintroduce the conditioning failure
            # that voided a 20-solve run.
            low[lab] = max(float(r["sigma_low"]), config.SIGMA["air"])
        if r["sigma_high"]:
            high[lab] = max(float(r["sigma_high"]), config.SIGMA["air"])

    # Designed comparison, not a sensitivity variant: air voids filled with
    # the surrounding temporal bone. Tests whether the superficial air voids
    # at the ear are themselves a mechanism for ear-versus-jaw difference.
    filled = dict(base)
    missing = [l for l in AIR_VOID_LABELS if l not in base]
    assert not missing, f"air-void labels absent from Table 1: {missing}"
    for lab in AIR_VOID_LABELS:
        filled[lab] = config.SIGMA[AIR_VOID_FILL]

    return {"a_baseline": base, "b_generic": generic,
            "c1_all_low": low, "c2_all_high": high,
            "d_airvoids_filled": filled}, len(judge)


def solve(mesh: Path, out: Path, pos, sigmas, label, inject_from, inject_to):
    from simnibs import sim_struct, run_simnibs
    import preflight
    preflight.check_conductivity_range(sigmas.values(), label=label)
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
    for j, nm in enumerate((inject_from, inject_to)):
        el = t.add_electrode()
        el.channelnr = j + 1
        el.centre = list(pos[nm])
        el.shape = "ellipse"
        el.dimensions = [config.ELECTRODE_DIAMETER_MM] * 2
        el.thickness = 2
    print(f"  solving {label} ...", flush=True)
    run_simnibs(S)
    hits = sorted(out.glob("*_scalar.msh")) or sorted(out.glob("*.msh"))
    if not hits:
        raise RuntimeError(f"no result mesh in {out}")
    # Guards. This script solved without ANY of them until the guard-coverage
    # test enumerated it: no calibration read, no invariants, no sigma gate.
    import preflight
    import solve_invariants as SI
    cal = preflight.read_calibration(out)
    print(f"    calibration: "
          f"{'clean' if cal is None else f'WARNED {cal:.2f}%'}", flush=True)
    inv = SI.check_solve_plateau(hits[0], pos[inject_from],
                                 SI.with_electrode_tags(sigmas), verbose=False)
    print(f"    invariant 1: mean {inv['mean_ratio']:.4f} "
          f"CV {inv['cv']*100:.2f}%   invariant 2: "
          f"net {inv['outer_net_frac']:+.4f} x injected", flush=True)
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


def read_measured_floor():
    """The electrode-meshing floor is MEASURED and has moved twice: 0.43 dB
    (15 mm, n=2), 0.1310 dB (10 mm, n=2), now 0.272 dB (10 mm, n=6, per-site
    with common mode removed). Hardcoding it here is how a superseded number
    survives in a decision ladder, which is exactly what happened before."""
    f = config.RESULTS / "electrode_meshing_floor.txt"
    if not f.exists():
        raise FileNotFoundError(
            f"{f} missing. Run src/measure_floor_multidraw.py; this verdict is "
            f"reported against the measured floor.")
    for line in f.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return float(line.split()[0])
    raise RuntimeError(f"no numeric floor value in {f}")


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
    for nm in ELECTRODES + [REFERENCE]:
        if nm not in pos:
            print(f"ERROR: {nm} has no accepted coordinate", file=sys.stderr)
            return 1
    print(f"electrodes: {', '.join(ELECTRODES)}  (reference {REFERENCE})")
    print(f"{len(sets)} conditions x {len(ELECTRODES)} electrodes = "
          f"{len(sets)*len(ELECTRODES)} solves\n")

    res = {}
    for cname, sig in sets.items():
        for e in ELECTRODES:
            res[(cname, e)] = compartment_medians(
                solve(a.mesh, a.workdir / f"{cname}__{e}", pos, sig,
                      f"{cname} @ {e}", e, REFERENCE))

    others = [c for c in sets if c != "a_baseline"]
    comps = sorted(res[("a_baseline", ELECTRODES[0])])

    print(f"\n{'compartment':<22} {'electrode':<15}" +
          "".join(f"{c[:12]:>14}" for c in others) + f"{'envelope':>10}")
    print("-" * 110)
    out_rows, worst, worst_at = [], 0.0, None
    for name in comps:
        for e in ELECTRODES:
            b = res[("a_baseline", e)].get(name)
            if not b or b <= 0:
                continue
            line = f"{name[:21]:<22} {e:<15}"
            rec = {"compartment": name, "electrode": e, "baseline_V_per_m": b}
            dbs = []
            for c in others:
                v = res[(c, e)].get(name, float("nan"))
                db = 20 * np.log10(v / b)
                dbs.append((abs(db), c))
                line += f"{db:>+13.3f}dB"
                rec[f"{c}_dB"] = round(float(db), 4)
            env = max(d for d, _ in dbs)
            rec["envelope_dB"] = round(float(env), 4)
            if env > worst:
                worst, worst_at = env, (name, e, max(dbs)[1])
            line += f"{env:>9.3f}"
            print(line)
            out_rows.append(rec)

    # exclude the designed air-void comparison from the SENSITIVITY verdict --
    # it is a physical experiment, not an uncertainty on an unsourced value
    sens = [c for c in others if c != "d_airvoids_filled"]
    sens_worst, sens_at = 0.0, None
    for r in out_rows:
        for c in sens:
            if abs(r[f"{c}_dB"]) > sens_worst:
                sens_worst = abs(r[f"{c}_dB"])
                sens_at = (r["compartment"], r["electrode"], c)

    print(f"\nSENSITIVITY envelope (conditions b, c1, c2 only): "
          f"{sens_worst:.3f} dB")
    if sens_at:
        print(f"  worst at: {sens_at[0]} @ {sens_at[1]} under {sens_at[2]}")
    floor = read_measured_floor()
    print(f"electrode-meshing noise floor (measured)         : {floor:.3f} dB")
    print(f"  FLIP POINT: this verdict changes at {floor:.3f} dB; measured "
          f"{sens_worst:.3f} dB")

    if sens_worst < 0.1:
        print("\nVERDICT: under 0.1 dB. The 17 judgement calls do not affect any\n"
              "         result. Methods carries one sentence.")
    elif sens_worst < floor:
        print("\nVERDICT: above 0.1 dB but below the electrode-meshing noise\n"
              "         floor, so it is real but not the limiting term.")
    else:
        # Fourth branch: attribute the excess before blaming sourcing.
        ear = {"mastoid", "above_ear"}
        by_e = {}
        for r in out_rows:
            v = max(abs(r[f"{c}_dB"]) for c in sens)
            by_e[r["electrode"]] = max(by_e.get(r["electrode"], 0.0), v)
        ear_max = max((v for e, v in by_e.items() if e in ear), default=0.0)
        jaw_max = max((v for e, v in by_e.items() if e not in ear), default=0.0)
        print(f"\n  attribution by electrode: "
              + ", ".join(f"{e} {v:.3f}dB" for e, v in sorted(
                  by_e.items(), key=lambda kv: -kv[1])))
        print(f"  ear sites max {ear_max:.3f} dB vs jaw sites max "
              f"{jaw_max:.3f} dB")
        if ear_max > 2 * jaw_max:
            print("\nVERDICT: exceeds the noise floor but is LOCALISED TO EAR "
                  "SITES.\n         This is not a sourcing failure -- sigma_air "
                  f"is {config.SIGMA['air']:.0e} and correct.\n         It is a physical result "
                  "about superficial air voids; see the\n         air-void "
                  "comparison below.")
        else:
            print("\nVERDICT: exceeds the meshing noise floor and is not "
                  "localised to the\n         ear. Unsourced conductivity is a "
                  "material budget term and the\n         widest-range "
                  "judgement rows need sourced values.")

    # ---- designed comparison: superficial air voids at the ear -----------
    print(f"\n{'='*72}\nAIR VOIDS AT THE EAR (condition d: voids filled with "
          f"{AIR_VOID_FILL})\n{'='*72}")
    print("labels: " + ", ".join(f"{k} {v}" for k, v in AIR_VOID_LABELS.items()))
    print(f"\n{'compartment':<22} " + "".join(f"{e[:13]:>15}" for e in ELECTRODES))
    print("-" * 90)
    for name in comps:
        line = f"{name[:21]:<22} "
        for e in ELECTRODES:
            r = next((x for x in out_rows if x["compartment"] == name
                      and x["electrode"] == e), None)
            line += (f"{r['d_airvoids_filled_dB']:>+14.3f}dB" if r
                     else f"{'-':>15}")
        print(line)
    av = [(abs(r["d_airvoids_filled_dB"]), r["electrode"], r["compartment"])
          for r in out_rows]
    if av:
        m = max(av)
        print(f"\nlargest air-void effect: {m[0]:.3f} dB at {m[2]} @ {m[1]}")
        ear_av = max((v for v, e, _ in av if e in ("mastoid", "above_ear")),
                     default=0.0)
        jaw_av = max((v for v, e, _ in av if e not in ("mastoid", "above_ear")),
                     default=0.0)
        print(f"ear sites {ear_av:.3f} dB vs jaw sites {jaw_av:.3f} dB")
        signs = [r["d_airvoids_filled_dB"] for r in out_rows
                 if r["electrode"] in ("mastoid", "above_ear")]
        if signs:
            print(f"sign at ear sites: {sum(1 for s in signs if s>0)} positive, "
                  f"{sum(1 for s in signs if s<0)} negative "
                  f"(filling the voids RAISES sensitivity where positive)")

    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    print(f"\nWritten: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
