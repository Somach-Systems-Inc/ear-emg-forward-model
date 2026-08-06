#!/usr/bin/env python3
"""
Stage 2d -- tissue layer profile beneath each electrode.

WHY THIS SUPERSEDES THE PERCENT-OF-PATH TABLE

The first version walked from the electrode to the *nearest point of the target
compartment* and reported percent-of-path per tissue. That metric is
truncation-limited by construction: the ray stops at the target's near surface,
so the target itself contributes only the last sample or two. midjaw reported
3% masseter over an 11.0 mm path -- 0.33 mm -- not because the electrode sees
little masseter but because the ray ended the moment it arrived.

This walks the same direction but continues through the full thickness of the
target and out the far side, and reports **millimetres per tissue** plus the
ordered layer stack with entry and exit depths. Thickness is a physical
quantity; percent-of-path-to-an-interior-point is an artefact of where you
chose to stop.

    python src/02d_layer_profile.py --label-volume data/.../MIDA_v1.nii
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

MIDA_BACKGROUND = 50
STEP_MM = 0.25
MAX_MARCH_MM = 90.0


def layer_runs(labels, step_mm, start_mm=0.0):
    """Contiguous runs -> [(label, entry_mm, exit_mm, thickness_mm)]."""
    runs = []
    if len(labels) == 0:
        return runs
    cur, i0 = int(labels[0]), 0
    for i in range(1, len(labels) + 1):
        if i == len(labels) or int(labels[i]) != cur:
            entry = start_mm + i0 * step_mm
            exit_ = start_mm + i * step_mm
            runs.append((cur, entry, exit_, exit_ - entry))
            if i < len(labels):
                cur, i0 = int(labels[i]), i
    return runs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="02d_layer_profile.py")
    ap.add_argument("--label-volume", type=Path, required=True)
    ap.add_argument("--positions", type=Path,
                    default=config.RESULTS / "02_electrode_positions.csv")
    ap.add_argument("--side", choices=("right", "left"), default="right")
    ap.add_argument("--out", type=Path,
                    default=config.RESULTS / "02_layer_profile.csv")
    a = ap.parse_args(argv)

    import nibabel as nib
    from scipy.spatial import cKDTree

    img = nib.load(str(a.label_volume))
    arr = np.asanyarray(img.dataobj)
    aff = img.affine
    inv = np.linalg.inv(aff)

    lut = {}
    inv_csv = config.RESULTS / "01_label_inventory.csv"
    if inv_csv.exists():
        for r in csv.DictReader(inv_csv.open(encoding="utf-8")):
            lut[int(r["label"])] = r["name"]

    def nm(l):
        return lut.get(int(l), str(int(l)))

    rows = {r["name"]: r for r in csv.DictReader(a.positions.open(encoding="utf-8"))}
    targets = {n: s["label"] for n, s in place2.JAW_TARGETS.items()}
    for n, (lab, _) in place2.EAR_TISSUE_CHECK.items():
        targets[n] = lab

    print(f"Label volume : {a.label_volume}")
    print(f"Step         : {STEP_MM} mm, marching to {MAX_MARCH_MM:.0f} mm "
          f"or until the ray exits the head\n")

    out_rows, summary = [], []
    for name in sorted(targets):
        r = rows.get(name)
        if r is None or r.get("verified") == "held" or r["R"] == "":
            print(f"{name}: held / no coordinate, skipped\n")
            continue
        lab = targets[name]
        p0 = np.array([float(r["R"]), float(r["A"]), float(r["S"])])

        pts = np.argwhere(arr == lab) @ aff[:3, :3].T + aff[:3, 3]
        k = pts[:, 0] > 0 if a.side == "right" else pts[:, 0] < 0
        if k.any() and lab != 87:
            pts = pts[k]
        d_near, i = cKDTree(pts).query(p0)
        direction = pts[i] - p0
        direction = direction / np.linalg.norm(direction)

        t = np.arange(0.0, MAX_MARCH_MM, STEP_MM)
        seg = p0[None, :] + t[:, None] * direction[None, :]
        ijk = np.rint(seg @ inv[:3, :3].T + inv[:3, 3]).astype(int)
        ok = np.all((ijk >= 0) & (ijk < np.array(arr.shape)), axis=1)
        labs = np.full(len(t), MIDA_BACKGROUND, dtype=np.int32)
        labs[ok] = arr[ijk[ok, 0], ijk[ok, 1], ijk[ok, 2]]

        # stop once the ray leaves the head on the far side
        inside = labs != MIDA_BACKGROUND
        if inside.any():
            last = int(np.max(np.flatnonzero(inside)))
        else:
            last = 0
        labs, t = labs[:last + 1], t[:last + 1]

        runs = layer_runs(labs, STEP_MM)
        # thickness per tissue over the FULL traversal
        thick = {}
        for l, _, _, th in runs:
            thick[l] = thick.get(l, 0.0) + th
        tgt_full = thick.get(lab, 0.0)

        # what the truncated metric would have said
        n_trunc = int(round(d_near / STEP_MM)) + 1
        tgt_trunc = float(np.sum(labs[:n_trunc] == lab)) * STEP_MM
        pct_trunc = 100.0 * tgt_trunc / max(d_near, 1e-9)

        print(f"{name}  ->  target {lab} {nm(lab)}")
        print(f"  depth to target near-surface : {d_near:5.2f} mm")
        print(f"  target thickness, FULL ray   : {tgt_full:5.2f} mm")
        print(f"  target thickness, truncated  : {tgt_trunc:5.2f} mm "
              f"({pct_trunc:.0f}% of the old path)")
        print(f"  layer stack (entry -> exit, mm):")
        for l, e0, e1, th in runs:
            if th < 0.4:
                continue
            print(f"      {e0:6.2f} -> {e1:6.2f}  {th:5.2f}  {nm(l)}")
        print()

        for l, th in sorted(thick.items(), key=lambda kv: -kv[1]):
            if th < 0.2:
                continue
            out_rows.append(dict(site=name, target_label=lab,
                                 target_name=nm(lab),
                                 depth_to_target_mm=round(float(d_near), 2),
                                 tissue_label=int(l), tissue=nm(l),
                                 thickness_mm=round(float(th), 2)))
        # Fat encountered BEFORE first reaching the target, which is the layer
        # that actually stands between the generator and the electrode. Total
        # fat over the whole ray would include everything past the target and
        # is not the quantity of interest.
        fat_before = 0.0
        for l, e0, e1, th in runs:
            if int(l) == lab:
                break
            if int(l) in (43, 62):     # Adipose Tissue, Subcutaneous Adipose
                fat_before += th
        summary.append((name, lab, d_near, tgt_trunc, tgt_full, fat_before))

    print("=" * 96)
    print("TRUNCATION IMPACT -- target compartment thickness seen by each metric")
    print("=" * 96)
    print(f"{'site':<16} {'target':<24} {'truncated':>10} {'full':>8} "
          f"{'x':>7}  {'fat before target':>18}")
    print("-" * 96)
    for name, lab, dn, tt, tf, fat in summary:
        ratio = (tf / tt) if tt > 0.05 else float("inf")
        rs = "inf" if not np.isfinite(ratio) else f"{ratio:.1f}x"
        print(f"{name:<16} {nm(lab)[:23]:<24} {tt:>10.2f} {tf:>8.2f} "
              f"{rs:>7}  {fat:>17.2f}")

    print("\nThe truncated column is what the percent-of-path table reported.")
    print("Where the ratio is large the old metric was measuring where the ray")
    print("stopped, not what the electrode sees.")

    if out_rows:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        with a.out.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
            w.writeheader()
            w.writerows(out_rows)
        print(f"\nWritten: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
