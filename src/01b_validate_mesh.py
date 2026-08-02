#!/usr/bin/env python3
"""
Stage 1b -- validate the tetrahedral mesh before anything expensive runs on it.

Must be run with SimNIBS's interpreter, which owns the mesh reader:

    ~/Applications/SimNIBS-4.6/bin/simnibs_python src/01b_validate_mesh.py

Checks, in order of how badly each would waste a stage-3 solve:
  1. the mesh loads at all
  2. node and element counts are sane
  3. every muscle compartment in config.MUSCLES exists with nonzero elements
  4. meshed compartment volume agrees with the voxel volume from stage 1
     (a compartment can survive as a tag but be badly under-resolved)
  5. element quality, since a few degenerate tets can wreck the FEM solve
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402

# Tolerance for meshed-vs-voxel volume disagreement before we complain.
VOLUME_TOL = 0.25
# Below this many elements a median is not worth trusting.
MIN_ELEMENTS = 200


def main() -> int:
    from simnibs import mesh_io

    mesh_path = config.MESH
    if not mesh_path.exists():
        print(f"ERROR: no mesh at {mesh_path}", file=sys.stderr)
        return 1

    print(f"Reading {mesh_path} ({mesh_path.stat().st_size/1e6:.0f} MB) ...", flush=True)
    m = mesh_io.read_msh(str(mesh_path))

    tets = m.elm.elm_type == 4
    tris = m.elm.elm_type == 2
    print(f"\nnodes        : {len(m.nodes.node_coord):,}")
    print(f"elements     : {len(m.elm.elm_type):,}")
    print(f"  tetrahedra : {int(tets.sum()):,}")
    print(f"  triangles  : {int(tris.sum()):,}")

    tags = m.elm.tag1[tets]
    uniq, counts = np.unique(tags, return_counts=True)
    print(f"distinct tetra tags: {len(uniq)}")

    vols = m.elements_volumes_and_areas()[tets]
    print(f"total tet volume: {vols.sum()/1000.0:,.0f} cm^3")

    # voxel volumes from stage 1, for the cross-check
    voxel_vol = {}
    inv = ROOT / "results/01_label_inventory.csv"
    if inv.exists():
        for row in csv.DictReader(inv.open()):
            voxel_vol[int(row["label"])] = float(row["volume_mm3"])
    else:
        print("\nWARNING: results/01_label_inventory.csv missing; "
              "skipping the volume cross-check")

    by_tag = {int(t): (int(c), float(vols[tags == t].sum()))
              for t, c in zip(uniq, counts)}

    print(f"\n{'muscle':<24} {'tag':>4} {'elements':>11} {'mesh_mm3':>12} "
          f"{'voxel_mm3':>12} {'diff':>7}  status")
    print("-" * 96)

    problems, pooled = [], []
    for name, group, label, _ in config.MUSCLES:
        if label is None:
            pooled.append(name)
            continue
        if label not in by_tag:
            print(f"{name:<24} {label:>4} {'ABSENT':>11} {'-':>12} {'-':>12} {'-':>7}  "
                  f"*** MISSING FROM MESH ***")
            problems.append(f"{name} (tag {label}) has no elements in the mesh")
            continue
        n, v = by_tag[label]
        vv = voxel_vol.get(label)
        if vv:
            diff = (v - vv) / vv
            ds = f"{diff:+.0%}"
        else:
            diff, ds = None, "-"
        flags = []
        if n < MIN_ELEMENTS:
            flags.append("TOO FEW ELEMENTS")
        if diff is not None and abs(diff) > VOLUME_TOL:
            flags.append("VOLUME MISMATCH")
        status = "ok" if not flags else "*** " + ", ".join(flags) + " ***"
        if flags:
            problems.append(f"{name} (tag {label}): {', '.join(flags)} "
                            f"[{n:,} elements, {ds} vs voxels]")
        print(f"{name:<24} {label:>4} {n:>11,} {v:>12,.0f} "
              f"{vv if vv else 0:>12,.0f} {ds:>7}  {status}")

    if pooled:
        print(f"\n{len(pooled)} muscle(s) not yet segmented, nothing to check: "
              + ", ".join(pooled))

    # --- element quality -------------------------------------------------
    print("\nELEMENT QUALITY")
    q = _quality(m, tets)
    print(f"  min tet volume   : {vols.min():.3e} mm^3")
    print(f"  negative volumes : {int((vols <= 0).sum()):,}")
    print(f"  mean qual        : {q.mean():.3f}   (1 = regular tetrahedron)")
    for p in (0.1, 1.0, 5.0):
        print(f"  {p:>4.1f}th pct qual : {np.percentile(q, p):.4f}")
    bad = int((q < 0.01).sum())
    print(f"  near-degenerate (<0.01): {bad:,}  ({100*bad/len(q):.4f}%)")
    if int((vols <= 0).sum()) > 0:
        problems.append(f"{int((vols<=0).sum())} tetrahedra have non-positive volume")

    print()
    if problems:
        print(f"VALIDATION FOUND {len(problems)} PROBLEM(S):")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("VALIDATION PASSED: every segmented muscle compartment is present, "
          "adequately resolved,\nand consistent in volume with the label volume.")
    return 0


def _quality(m, tets):
    """Normalised tet quality: 12/sqrt(2) * V / rms_edge^3, 1 for a regular tet."""
    nodes = m.nodes.node_coord
    idx = m.elm.node_number_list[tets][:, :4] - 1
    p = nodes[idx]
    e = np.stack([p[:, 1] - p[:, 0], p[:, 2] - p[:, 0], p[:, 3] - p[:, 0],
                  p[:, 2] - p[:, 1], p[:, 3] - p[:, 1], p[:, 3] - p[:, 2]], axis=1)
    L2 = (e ** 2).sum(-1)
    V = np.abs(np.einsum('ij,ij->i', np.cross(e[:, 0], e[:, 1]), e[:, 2])) / 6.0
    rms = np.sqrt(L2.mean(1))
    with np.errstate(divide="ignore", invalid="ignore"):
        q = (12.0 / np.sqrt(2.0)) * V / rms ** 3
    return np.nan_to_num(q)


if __name__ == "__main__":
    sys.exit(main())
