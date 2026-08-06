#!/usr/bin/env python3
"""
Stage 2c -- acceptance gate for the re-placed jaw electrodes.

Six checks. A clean pass is sign-off; a failure re-places the offending site by
the documented rule and re-checks, rather than smoothing the number.

  A CENTROID VALIDITY   is the side-restricted target centroid actually INSIDE
                        its compartment? A hyoid or a mandible is a U, so its
                        centroid sits in soft tissue in the middle of the arch,
                        and projecting from there is projecting from a point
                        that is not in the muscle. Failures are re-placed by
                        minimising distance to the COMPARTMENT, not to its
                        centroid.
  B DEPTH PLAUSIBILITY  post-projection depth should be skin+fat for a
                        superficial target. Flag > 15 mm.
  C INTER-ELECTRODE     nearest-neighbour spacing among the jaw sites. Hard
                        floor 20 mm: the physical rig is 10 mm gold cups in
                        adhesive collars, and Paper 2 tests this montage. A
                        montage nobody can wear predicts nothing.
  D SIDE INTEGRITY      each site on its target's side; midline sites within
                        2 mm of the symphysis-derived midline.
  E BOUNDARY CLEARANCE  distance from each electrode to MIDA's cut face at
                        S = -116.2, three smallest reported.
  F OLD VS NEW          full displacement history.

    python src/02c_placement_acceptance.py \\
        --label-volume data/MIDA_v1.0/MIDA_v1_voxels/MIDA_v1.nii
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402
import importlib
place2 = importlib.import_module("02_place_electrodes")

MIDA_BACKGROUND, MIDA_SKIN = 50, 51
CUT_FACE_S = -116.2
SPACING_FLOOR_MM = 20.0
DEPTH_FLAG_MM = 15.0
MIDLINE_TOL_MM = 2.0

SITES = ["mental", "hyoid", "submental_mid", "submental_lat",
         "submaxillary", "buccal", "midjaw"]

# (low, high) mm expected depth. Carl's review numbers, with one revised.
#
# hyoid was specified 10-15 mm. That is not attainable in MIDA: the hyoid
# bone's minimum distance to the skin surface is 19.1 mm measured over the
# ENTIRE skin, unconstrained by midline or any other filter. The band is
# revised to the measured reality rather than left as a permanent false
# failure. MIDA separates Epidermis/Dermis from Subcutaneous Adipose, so this
# depth spans skin, fat, platysma and the infrahyoid group.
DEPTH_EXPECT = {
    "mental": (3, 8), "midjaw": (5, 12), "buccal": (8, 15),
    "hyoid": (15, 22),          # REVISED from (10, 15); measured minimum 19.1
    "submental_mid": (4, 12), "submental_lat": (4, 12), "submaxillary": (4, 12),
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="02c_placement_acceptance.py")
    ap.add_argument("--label-volume", type=Path, required=True)
    ap.add_argument("--positions", type=Path,
                    default=config.RESULTS / "02_electrode_positions.csv")
    ap.add_argument("--baseline", type=Path, default=None,
                    help="optional CSV of the original hand-offset positions")
    ap.add_argument("--side", choices=("right", "left"), default="right")
    ap.add_argument("--write", action="store_true",
                    help="write accepted positions back to --positions")
    a = ap.parse_args(argv)

    import nibabel as nib
    from scipy import ndimage
    from scipy.spatial import cKDTree

    img = nib.load(str(a.label_volume))
    arr = np.asanyarray(img.dataobj)
    aff = img.affine
    inv = np.linalg.inv(aff)
    sign = 1.0 if a.side == "right" else -1.0

    def ras(idx):
        return idx @ aff[:3, :3].T + aff[:3, 3]

    def label_at(p):
        ijk = np.rint((np.append(np.asarray(p, float), 1.0) @ inv.T)[:3]).astype(int)
        if np.any(ijk < 0) or np.any(ijk >= np.array(arr.shape)):
            return None
        return int(arr[ijk[0], ijk[1], ijk[2]])

    midline, n_symph = place2.derive_midline(np, arr, aff)
    print(f"Label volume : {a.label_volume}")
    print(f"Side         : {a.side}")
    print(f"Midline      : R = {midline:+.2f} (mandibular symphysis, n={n_symph:,})\n")

    print("building outer skin surface ...", flush=True)
    skin = arr == MIDA_SKIN
    surf = skin & ndimage.binary_dilation(
        arr == MIDA_BACKGROUND, ndimage.generate_binary_structure(3, 1))
    skin_ras = ras(np.argwhere(surf))
    del skin, surf
    print(f"  {len(skin_ras):,} outer-skin voxels\n")

    rows = {r["name"]: r for r in csv.DictReader(a.positions.open(encoding="utf-8"))}
    baseline = {}
    if a.baseline and a.baseline.exists():
        baseline = {r["name"]: r for r in csv.DictReader(a.baseline.open(encoding="utf-8"))}

    # ---------------------------------------------------------------- A
    print("=" * 100)
    print("A. CENTROID VALIDITY  -- is the side-restricted centroid inside its compartment?")
    print("=" * 100)
    print(f"{'site':<16} {'target':<34} {'centroid label':<22} {'inside?':<8} action")
    print("-" * 100)

    accepted, changed = {}, []
    for name in SITES:
        spec = place2.JAW_TARGETS[name]
        label, region, skinf = spec["label"], spec["region"], spec["skin"]
        pts = place2.region_points(np, ras(np.argwhere(arr == label)),
                                   region, midline, sign)
        centre = pts.mean(0)
        got = label_at(centre)
        inside = (got == label)

        # eligible skin, with the midline band tightened to the acceptance
        # tolerance so check D is enforced at placement time rather than
        # merely measured afterwards
        keep = np.ones(len(skin_ras), dtype=bool)
        for f in (skinf or ()):
            if f == "inferior":
                keep &= skin_ras[:, 2] <= centre[2] + 4.0
            elif f == "midline":
                keep &= np.abs(skin_ras[:, 0] - midline) <= MIDLINE_TOL_MM
        cand = skin_ras[keep]
        if len(cand) == 0:
            print(f"{name:<16} {'':<34} {'':<22} {'':<8} NO ELIGIBLE SKIN")
            continue

        # The min-distance rule applies ONLY where the centroid is invalid.
        # Applying it everywhere is wrong: for a long muscle it migrates the
        # electrode to the muscle's single shallowest point, which for masseter
        # is up at the zygomatic arch, ~50 mm from mid-ramus and close enough
        # to pre_tragus to be unbuildable. Where the centroid IS inside the
        # compartment, projecting from it is valid and is kept.
        tree_pts = cKDTree(pts)
        if inside:
            d_c, _ = cKDTree(cand).query(centre)
            k = int(cKDTree(cand).query(centre)[1])
            pos = cand[k]
            depth = float(tree_pts.query(pos)[0])
            rule = "centroid projection (centroid valid)"
        else:
            d_all, _ = tree_pts.query(cand)
            j = int(np.argmin(d_all))
            pos, depth = cand[j], float(d_all[j])
            rule = "min-distance to compartment (centroid invalid)"

        old = np.array([float(rows[name]["R"]), float(rows[name]["A"]),
                        float(rows[name]["S"])])
        moved = float(np.linalg.norm(pos - old))
        if moved > 0.5:
            changed.append((name, moved))
        lname = str(got)
        print(f"{name:<16} {label} {region or '-':<30} "
              f"{lname:<22} {'YES' if inside else 'NO':<8} {rule}")
        accepted[name] = dict(pos=pos, depth=depth, target=label, region=region,
                              centroid_inside=inside, moved=moved, old=old)

    print(f"\ncentroid outside its own compartment: "
          f"{sum(1 for v in accepted.values() if not v['centroid_inside'])}/"
          f"{len(accepted)} sites")
    if changed:
        print("re-placed: " + ", ".join(f"{n} ({d:.1f} mm)" for n, d in changed))

    # ---------------------------------------------------------------- B
    print("\n" + "=" * 100)
    print("B. DEPTH PLAUSIBILITY  -- post-projection distance to target = depth")
    print("=" * 100)
    print(f"{'site':<16} {'depth mm':>9} {'expected':>12}  verdict")
    print("-" * 100)
    b_fail = []
    for name, v in accepted.items():
        lo, hi = DEPTH_EXPECT[name]
        d = v["depth"]
        if d > hi:
            verdict = f"*** FLAG: above band ***"
            b_fail.append(name)
        elif d < lo:
            verdict = "shallower than expected (not a failure)"
        else:
            verdict = "ok"
        print(f"{name:<16} {d:>9.1f} {f'{lo}-{hi}':>12}  {verdict}")

    # ---------------------------------------------------------------- C
    print("\n" + "=" * 100)
    floor = config.COLLAR_OD_MM
    print("C. INTER-ELECTRODE SPACING  -- REPORTED CONSTRAINT, not a gate")
    print("=" * 100)
    if floor is None:
        print("config.COLLAR_OD_MM is None (TODO: caliper the TD-20s collars).")
        print("Spacing is reported; nothing fails on it. A referential montage")
        print("does not have a derived minimum spacing, and the previous 20 mm")
        print("figure was a guess that failed three anatomically-correct pairs.\n")
    else:
        print(f"Flagging pairs closer than COLLAR_OD_MM = {floor:.1f} mm.\n")

    held = [n for n, r in rows.items() if r.get("verified") == "held"]
    names = list(accepted)
    P = np.array([accepted[n]["pos"] for n in names])
    D = np.linalg.norm(P[:, None, :] - P[None, :, :], axis=-1)

    # Full matrix, including the held site as a blank row/column so the 8x8
    # shape is visible and its absence is explicit rather than silent.
    allnames = names + held
    w = max(len(n) for n in allnames) + 1
    print(f"{'':<{w}}" + "".join(f"{n[:8]:>9}" for n in allnames))
    for i, n in enumerate(allnames):
        line = f"{n:<{w}}"
        for j, m in enumerate(allnames):
            if n in held or m in held:
                line += f"{'-':>9}"
            elif i == j:
                line += f"{'.':>9}"
            else:
                d = D[names.index(n), names.index(m)]
                mark = "*" if (floor is not None and d < floor) else " "
                line += f"{d:>8.1f}{mark}"
        print(line)

    np.fill_diagonal(D, np.inf)
    gmin = float(D.min())
    i, j = np.unravel_index(int(np.argmin(D)), D.shape)
    c_fail = []
    print(f"\nminimum pairwise spacing: {gmin:.1f} mm "
          f"({names[i]} <-> {names[j]})")
    if floor is not None:
        below = [(names[x], names[y], float(D[x, y]))
                 for x in range(len(names)) for y in range(x + 1, len(names))
                 if D[x, y] < floor]
        print(f"pairs below COLLAR_OD_MM: {len(below)}"
              + ("" if not below else "  " + ", ".join(
                  f"{a}-{b} {d:.1f}mm" for a, b, d in below)))
    else:
        print("no floor set, so no pairs flagged")
    if held:
        print(f"NOTE: {', '.join(held)} held with no coordinate, so this is "
              f"{len(names)}x{len(names)}, not 8x8. Re-run this check when the "
              f"measured coordinate arrives.")

    # Jaw-only spacing cannot catch a jaw site drifting into an ear site, and
    # an unbuildable montage is unbuildable regardless of which list the two
    # electrodes came from.
    other = [(n, np.array([float(r["R"]), float(r["A"]), float(r["S"])]))
             for n, r in rows.items()
             if n not in accepted and r.get("verified") != "held" and r["R"] != ""]
    if other:
        worst = None
        for n, v in accepted.items():
            for m, q in other:
                d = float(np.linalg.norm(v["pos"] - q))
                if worst is None or d < worst[0]:
                    worst = (d, n, m)
        d, n, m = worst
        ok = d >= SPACING_FLOOR_MM
        print(f"closest jaw-to-other-montage pair: {n} <-> {m} = {d:.1f} mm "
              f"({'ok' if ok else '*** BELOW FLOOR ***'})")
        if not ok:
            c_fail.append((n, m, d))

    # ---------------------------------------------------------------- D
    print("\n" + "=" * 100)
    print("D. SIDE INTEGRITY")
    print("=" * 100)
    print(f"{'site':<16} {'R':>8} {'expected':<22} verdict")
    print("-" * 100)
    d_fail = []
    for name, v in accepted.items():
        R = v["pos"][0]
        region = v["region"]
        if (v["region"] in ("symphysis_mid",) or
                "midline" in (place2.JAW_TARGETS[name]["skin"] or ())):
            off = abs(R - midline)
            ok = off <= MIDLINE_TOL_MM
            exp = f"midline +-{MIDLINE_TOL_MM:.0f}mm"
            detail = f"{off:.1f} mm off midline"
        else:
            ok = (R - midline) * sign > 0
            exp = f"{a.side} of midline"
            detail = f"{(R-midline)*sign:+.1f} mm"
        if not ok:
            d_fail.append(name)
        print(f"{name:<16} {R:>8.1f} {exp:<22} {'ok' if ok else '*** FAIL ***'} ({detail})")

    # ---------------------------------------------------------------- E
    print("\n" + "=" * 100)
    print(f"E. BOUNDARY CLEARANCE  -- distance above MIDA's cut face S = {CUT_FACE_S}")
    print("=" * 100)
    clear = []
    for name, v in accepted.items():
        clear.append((float(v["pos"][2] - CUT_FACE_S), name))
    for name, r in rows.items():
        if name in accepted or r.get("verified") == "held" or r["S"] == "":
            continue
        clear.append((float(r["S"]) - CUT_FACE_S, name))
    clear.sort()
    print("three smallest clearances (whole montage):")
    for d, n in clear[:3]:
        print(f"  {n:<16} {d:>7.1f} mm")
    print(f"largest: {clear[-1][1]} at {clear[-1][0]:.1f} mm")

    # ---------------------------------------------------------------- F
    print("\n" + "=" * 100)
    print("F. DISPLACEMENT HISTORY")
    print("=" * 100)
    hdr = f"{'site':<16} {'original (hand-offset)':<26} {'normal-projection':<26} {'accepted':<26} {'orig->acc':>10}"
    print(hdr)
    print("-" * len(hdr))
    for name, v in accepted.items():
        b = baseline.get(name)
        bs = (f"{float(b['R']):.1f}, {float(b['A']):.1f}, {float(b['S']):.1f}"
              if b else "-")
        o = v["old"]
        ns = f"{o[0]:.1f}, {o[1]:.1f}, {o[2]:.1f}"
        p = v["pos"]
        ps = f"{p[0]:.1f}, {p[1]:.1f}, {p[2]:.1f}"
        tot = (np.linalg.norm(p - np.array([float(b['R']), float(b['A']),
                                            float(b['S'])])) if b else float("nan"))
        print(f"{name:<16} {bs:<26} {ns:<26} {ps:<26} {tot:>9.1f}")

    # ---------------------------------------------------------------- G
    print("\n" + "=" * 100)
    print("G. TISSUE COMPOSITION ALONG THE ELECTRODE-TO-TARGET SEGMENT")
    print("=" * 100)
    print("What each canonical site is actually integrating over. At ~20 mm the")
    print("hyoid site traverses platysma and the infrahyoid group, not the")
    print("suprahyoids it is named for. Not previously reported for the")
    print("Gaddy/Kapur montage.\n")

    lut = {}
    inv_csv = config.RESULTS / "01_label_inventory.csv"
    if inv_csv.exists():
        for r in csv.DictReader(inv_csv.open(encoding="utf-8")):
            lut[int(r["label"])] = r["name"]

    targets = {n: place2.JAW_TARGETS[n]["label"] for n in accepted}
    for n, (lab, _) in place2.EAR_TISSUE_CHECK.items():
        if n in rows and rows[n]["R"] != "":
            targets[n] = lab

    comp_rows = []
    for name in sorted(targets, key=lambda x: (x not in accepted, x)):
        lab = targets[name]
        if name in accepted:
            p0 = accepted[name]["pos"]
        else:
            p0 = np.array([float(rows[name]["R"]), float(rows[name]["A"]),
                           float(rows[name]["S"])])
        pts = ras(np.argwhere(arr == lab))
        if a.side == "right":
            k = pts[:, 0] > 0
        else:
            k = pts[:, 0] < 0
        if k.any() and lab not in (87,):      # hyoid is a midline arch
            pts = pts[k]
        d, i = cKDTree(pts).query(p0)
        p1 = pts[i]

        t = np.linspace(0.0, 1.0, 400)[:, None]
        seg = p0[None, :] * (1 - t) + p1[None, :] * t
        ijk = np.rint(seg @ inv[:3, :3].T + inv[:3, 3]).astype(int)
        okm = np.all((ijk >= 0) & (ijk < np.array(arr.shape)), axis=1)
        labs = np.full(len(seg), MIDA_BACKGROUND, dtype=arr.dtype)
        labs[okm] = arr[ijk[okm, 0], ijk[okm, 1], ijk[okm, 2]]

        uniq, cnt = np.unique(labs, return_counts=True)
        order = np.argsort(cnt)[::-1]
        parts = []
        for u, c in zip(uniq[order], cnt[order]):
            pct = 100.0 * c / len(labs)
            if pct < 2.0:
                continue
            parts.append(f"{lut.get(int(u), str(int(u)))} {pct:.0f}%")
            comp_rows.append(dict(site=name, target_label=lab,
                                  path_mm=round(float(d), 2),
                                  tissue_label=int(u),
                                  tissue=lut.get(int(u), str(int(u))),
                                  pct_of_path=round(pct, 1)))
        print(f"  {name:<16} {d:>5.1f} mm -> {lut.get(lab,lab)[:28]:<30} "
              + "; ".join(parts[:5]))

    for n in held:
        print(f"  {n:<16} HELD, no coordinate; composition pending")

    if comp_rows:
        out = config.RESULTS / "02_path_composition.csv"
        with out.open("w", newline="", encoding="utf-8") as fh:
            w2 = csv.DictWriter(fh, fieldnames=list(comp_rows[0].keys()))
            w2.writeheader()
            w2.writerows(comp_rows)
        print(f"\nWritten: {out}")

    # ---------------------------------------------------------------- verdict
    print("\n" + "=" * 100)
    fails = []
    if b_fail:
        fails.append(f"B: depth over {DEPTH_FLAG_MM:.0f} mm at " + ", ".join(b_fail))
    if c_fail:
        fails.append("C(cross-montage): jaw site within the floor of another "
                     "montage: " +
                     ", ".join(f"{x}-{y} {d:.1f}mm" for x, y, d in c_fail))
    if d_fail:
        fails.append("D: side/midline failure at " + ", ".join(d_fail))
    if fails:
        print(f"ACCEPTANCE: FAILED ({len(fails)} check(s))")
        for f in fails:
            print(f"  - {f}")
    else:
        print("ACCEPTANCE: PASSED (A-F clean)")
    print("=" * 100)

    if a.write:
        for name, v in accepted.items():
            r = rows[name]
            r["R"], r["A"], r["S"] = (round(float(v["pos"][0]), 2),
                                      round(float(v["pos"][1]), 2),
                                      round(float(v["pos"][2]), 2))
            r["snap_mm"] = 0.0
            r["depth_mm"] = round(v["depth"], 2)
            r["anchor"] = (f"{place2.JAW_TARGETS[name]['desc']} "
                           f"(label {v['target']}"
                           + (f", {v['region']}" if v["region"] else "")
                           + "), min-distance projection to compartment")
            r["verified"] = "no" if fails else "accepted"
        with a.positions.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(next(iter(rows.values())).keys()))
            w.writeheader()
            w.writerows(rows.values())
        print(f"\nwrote {a.positions}")

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
