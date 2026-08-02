#!/usr/bin/env python3
"""
Fibre-orientation uncertainty, bounded rather than assumed.

MIDA ships no muscle fibre directions. Instead of inventing them, sweep the
source orientation n_hat over the sphere and report an envelope.

A muscle fibre's current dipole runs along the fibre, and the lead field for a
source at r with orientation n_hat is L = E(r) . n_hat. E is already solved, so
the sweep costs no extra FEM solve -- it is a post-processing step on a field
that exists. Every sensitivity number then carries a min/max band instead of a
point estimate that quietly assumes a direction nobody measured.

Read this as the answer to the reviewer question "how do you know the fibre
directions?". The answer is that we do not, so we bounded them.

Self-test:  python src/orientation.py --self-test
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402


def fibonacci_hemisphere(n: int) -> np.ndarray:
    """`n` near-uniform unit vectors on the upper hemisphere.

    |E . n_hat| is invariant under n_hat -> -n_hat, so a hemisphere covers
    every distinguishable source orientation and halves the work.
    """
    if n < 1:
        raise ValueError("n must be >= 1")
    k = np.arange(n, dtype=np.float64) + 0.5
    z = k / n                                  # (0, 1] -> upper hemisphere
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    phi = np.pi * (1.0 + 5.0 ** 0.5) * k       # golden angle
    return np.column_stack((r * np.cos(phi), r * np.sin(phi), z))


def _weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    order = np.argsort(values)
    v, w = values[order], weights[order]
    c = np.cumsum(w)
    if c[-1] <= 0:
        return float("nan")
    return float(v[np.searchsorted(c, 0.5 * c[-1])])


def sweep(E: np.ndarray,
          weights: np.ndarray | None = None,
          n_dirs: int | None = None,
          max_elements: int | None = 200_000,
          seed: int = 0,
          chunk: int = 64) -> dict:
    """Sweep source orientation over the hemisphere for one muscle compartment.

    E        : (M, 3) electric field vectors, one per element in the compartment
    weights  : (M,) element volumes. Without them every element counts equally,
               which biases the median toward wherever the mesh is finest.
    returns  : dict with the per-direction statistic and its envelope
    """
    E = np.asarray(E, dtype=np.float64)
    if E.ndim != 2 or E.shape[1] != 3:
        raise ValueError(f"E must be (M, 3), got {E.shape}")
    if len(E) == 0:
        raise ValueError("empty compartment: no elements to sweep")

    if weights is not None:
        weights = np.asarray(weights, dtype=np.float64)
        if weights.shape != (len(E),):
            raise ValueError(f"weights must be ({len(E)},), got {weights.shape}")

    # Subsample large compartments. A median over 200k elements is already far
    # past the point where more samples move it.
    if max_elements is not None and len(E) > max_elements:
        rng = np.random.default_rng(seed)
        pick = rng.choice(len(E), max_elements, replace=False)
        E = E[pick]
        weights = None if weights is None else weights[pick]
        subsampled = True
    else:
        subsampled = False

    dirs = fibonacci_hemisphere(n_dirs or config.ORIENTATION_SWEEP_N)
    stat = np.empty(len(dirs), dtype=np.float64)

    # Chunk over directions: the (M, N) product is what blows up memory.
    for a in range(0, len(dirs), chunk):
        block = dirs[a:a + chunk]
        L = np.abs(E @ block.T)                # (M, chunk)
        if weights is None:
            stat[a:a + len(block)] = np.median(L, axis=0)
        else:
            for j in range(L.shape[1]):
                stat[a + j] = _weighted_median(L[:, j], weights)
        del L

    lo, hi = int(np.argmin(stat)), int(np.argmax(stat))
    smin, smax = float(stat[lo]), float(stat[hi])
    return {
        "n_elements": int(len(E)),
        "subsampled": subsampled,
        "n_dirs": int(len(dirs)),
        "median": float(np.median(stat)),   # across orientations
        "min": smin,
        "max": smax,
        "dir_min": dirs[lo],
        "dir_max": dirs[hi],
        # Envelope width in dB. This is the number that decides whether fibre
        # orientation matters at all: narrow means future head models can
        # ignore it, wide means someone needs to go and measure it.
        "envelope_db": (20.0 * np.log10(smax / smin)
                        if smin > 0 and np.isfinite(smin) else float("inf")),
        "stat": stat,
    }


def principal_axis(points: np.ndarray) -> tuple[np.ndarray, float]:
    """First principal component of a point cloud, and how dominant it is.

    Returns (axis, anisotropy_ratio) where the ratio is sqrt(l1/l2) of the top
    two eigenvalues. A ratio near 1 means the cloud has no meaningful long
    axis, which is the quantitative form of "PCA is the wrong object here".
    """
    axis, _, elong, _ = shape_descriptors(points)
    return axis, elong


def shape_descriptors(points: np.ndarray):
    """Classify a compartment's shape from its scatter matrix.

    Returns (axis, eigenvalues, elongation, flatness) where
      elongation = sqrt(l1/l2)  -- rod-ness. High for a strap muscle.
      flatness   = sqrt(l2/l3)  -- plate-ness. High for a sheet or a ring.

    This is what makes the FIBRE_MODEL table testable rather than asserted.
    A muscle labelled "pca" should be a rod: elongation clearly above 1 and
    larger than its flatness. A sheet, fan or sphincter is a plate: flatness
    dominates and the "long axis" is an artefact of outline, not fibres.
    """
    P = np.asarray(points, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] != 3 or len(P) < 3:
        raise ValueError(f"need (M>=3, 3) points, got {P.shape}")
    C = np.cov((P - P.mean(0)).T)
    vals, vecs = np.linalg.eigh(C)
    order = np.argsort(vals)[::-1]
    vals, vecs = vals[order], vecs[:, order]
    elong = float(np.sqrt(vals[0] / vals[1])) if vals[1] > 0 else float("inf")
    flat = float(np.sqrt(vals[1] / vals[2])) if vals[2] > 0 else float("inf")
    return vecs[:, 0], vals, elong, flat


def split_sides(ras: np.ndarray, min_frac: float = 0.15):
    """Split a compartment into left/right halves if it is bilateral.

    MIDA gives each muscle ONE label covering both sides. Running PCA on that
    directly measures the left-right separation between two muscles, not the
    fibre direction along either -- it reported sternocleidomastoid, the
    textbook strap muscle, as a plate. Any fibre axis must be computed per
    side. Returns a list of (side_name, points).
    """
    right, left = ras[ras[:, 0] > 0], ras[ras[:, 0] < 0]
    n = len(ras)
    if len(right) >= min_frac * n and len(left) >= min_frac * n:
        return [("right", right), ("left", left)]
    return [("both", ras)]


def _pca_check(volume_path: Path) -> int:
    """Test FIBRE_MODEL against MIDA's real geometry.

    Only the muscles with a verified mida_label can be checked; the pooled
    ones have no compartment to measure yet.
    """
    import nibabel as nib

    if not volume_path.exists():
        print(f"ERROR: label volume not found: {volume_path}", file=sys.stderr)
        return 1

    img = nib.load(str(volume_path))
    arr = np.asanyarray(img.dataobj)
    aff = img.affine

    print(f"Label volume: {volume_path}")
    print("elongation = sqrt(l1/l2), rod-ness.  flatness = sqrt(l2/l3), plate-ness.")
    print("A 'pca' muscle should be a rod: elongation > flatness.\n")
    print(f"{'muscle':<24} {'model':<10} {'lab':>4} {'voxels':>10} "
          f"{'elong':>7} {'flat':>7}  {'shape':<8} verdict")
    print("-" * 100)

    disagree = []
    for name, group, label, _ in config.MUSCLES:
        kind = config.FIBRE_MODEL.get(name, ("?", ""))[0]
        if label is None:
            print(f"{name:<24} {kind:<10} {'-':>4} {'pooled':>10} "
                  f"{'-':>7} {'-':>7}  {'-':<8} not yet segmented")
            continue
        idx = np.argwhere(arr == label)
        if len(idx) < 3:
            print(f"{name:<24} {kind:<10} {label:>4} {len(idx):>10} "
                  f"{'-':>7} {'-':>7}  {'-':<8} TOO FEW VOXELS")
            continue
        ras = idx @ aff[:3, :3].T + aff[:3, 3]
        for side, pts in split_sides(ras):
            if len(pts) < 3:
                continue
            _, _, elong, flat = shape_descriptors(pts)
            # Neutral band. platysma-left came out elongation 2.82, flatness
            # 2.82 and a bare >= silently called it a rod. Forcing a coin-flip
            # into a category is the same error as asserting a fibre axis for
            # a sphincter, just smaller.
            ratio = elong / flat if flat > 0 else float("inf")
            if 0.8 < ratio < 1.25:
                shape = "ambiguous"
            else:
                shape = "rod" if ratio >= 1.0 else "plate"
            agree = (shape == "ambiguous") or ((kind == "pca") == (shape == "rod"))
            verdict = ("consistent" if agree else "*** DISAGREES WITH FIBRE_MODEL ***")
            if shape == "ambiguous":
                verdict = "ambiguous, no evidence either way"
            if not agree:
                disagree.append((f"{name} ({side})", kind, shape, elong, flat))
            tag = f"{name} [{side}]" if side != "both" else name
            print(f"{tag:<24} {kind:<10} {label:>4} {len(pts):>10,} "
                  f"{elong:>7.2f} {flat:>7.2f}  {shape:<8} {verdict}")

    # Left/right volume asymmetry. MIDA is one subject segmented by hand, so a
    # large imbalance is a segmentation artefact rather than anatomy -- and it
    # matters, because stage 2 places the montage on one nominated side.
    print("\nLEFT/RIGHT VOLUME SYMMETRY")
    print(f"{'muscle':<24} {'right':>10} {'left':>10} {'asym':>7}")
    print("-" * 56)
    asym_flagged = []
    for name, _, label, _ in config.MUSCLES:
        if label is None:
            continue
        idx = np.argwhere(arr == label)
        if len(idx) < 3:
            continue
        ras = idx @ aff[:3, :3].T + aff[:3, 3]
        nr, nl = int((ras[:, 0] > 0).sum()), int((ras[:, 0] < 0).sum())
        if nr + nl == 0:
            continue
        a = abs(nr - nl) / (nr + nl)
        flag = "  <-- asymmetric" if a > 0.25 else ""
        if a > 0.25:
            asym_flagged.append((name, nr, nl, a))
        print(f"{name:<24} {nr:>10,} {nl:>10,} {a:>7.2f}{flag}")
    if asym_flagged:
        print("\nAsymmetry above 0.25 in: "
              + ", ".join(f"{n} ({a:.0%})" for n, _, _, a in asym_flagged))
        smaller_right = [n for n, nr, nl, _ in asym_flagged if nr < nl]
        if smaller_right:
            print("These are SMALLER on the right: " + ", ".join(smaller_right))
            print("Stage 2 currently places the montage on the right (--side right).")
        print("\nCAVEAT: a left/right split at R=0 is only meaningful for PAIRED")
        print("muscles. For midline structures -- orbicularis oris is a single ring")
        print("crossing the midline, mentalis sits on the chin -- the split is")
        print("arbitrary and 'asymmetry' is largely an artefact of where the plane")
        print("falls. Judge those two on absolute element count, not on this ratio.")

    print()
    if disagree:
        print("Geometry disagrees with the anatomical classification for "
              f"{len(disagree)} muscle(s):")
        for n, k, s, e, f in disagree:
            print(f"  {n}: labelled '{k}' but the compartment is a {s} "
                  f"(elongation {e:.2f}, flatness {f:.2f})")
        print("\nGeometry is evidence, not a verdict. A fan can have an elongated")
        print("outline while its fibres diverge, so a 'plate' shape does not by")
        print("itself justify flipping a muscle to pca. Treat these as prompts to")
        print("re-read the anatomy, not as an automatic reclassification.")
    else:
        print("Every segmented muscle's shape is consistent with its FIBRE_MODEL entry.")
    return 0


def evaluate_at(E: np.ndarray, n_hat: np.ndarray,
                weights: np.ndarray | None = None) -> float:
    """Sensitivity for one specific source orientation (e.g. the PCA axis)."""
    n_hat = np.asarray(n_hat, dtype=np.float64)
    n_hat = n_hat / np.linalg.norm(n_hat)
    L = np.abs(np.asarray(E, dtype=np.float64) @ n_hat)
    if weights is None:
        return float(np.median(L))
    return _weighted_median(L, np.asarray(weights, dtype=np.float64))


def summarise(muscle: str, E, weights=None, points=None) -> dict:
    """Full per-muscle record: envelope, plus the PCA point estimate when the
    muscle is one where a principal axis means anything."""
    s = sweep(E, weights=weights)
    kind, reason = config.FIBRE_MODEL.get(muscle, ("isotropic", "not in FIBRE_MODEL"))
    rec = {
        "muscle": muscle,
        "fibre_model": kind,
        "fibre_model_reason": reason,
        "n_elements": s["n_elements"],
        "sens_median": s["median"],
        "sens_min": s["min"],
        "sens_max": s["max"],
        "envelope_db": s["envelope_db"],
        "pca_axis": "",
        "pca_dominance": "",
        "sens_at_pca": "",
    }
    if kind == "pca" and points is not None:
        axis, dom = principal_axis(points)
        rec["pca_axis"] = " ".join(f"{v:.4f}" for v in axis)
        rec["pca_dominance"] = round(dom, 3)
        rec["sens_at_pca"] = evaluate_at(E, axis, weights)
    return rec


# ----------------------------------------------------------------------
def _self_test() -> int:
    """Check the sweep against cases whose answer is known analytically."""
    rng = np.random.default_rng(0)
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'}  {name}   {detail}")
        ok &= bool(cond)

    print("fibonacci_hemisphere")
    d = fibonacci_hemisphere(512)
    check("all unit length", np.allclose(np.linalg.norm(d, axis=1), 1.0))
    check("all in upper hemisphere", (d[:, 2] >= 0).all())
    check("reasonably spread", d[:, 2].min() < 0.05 and d[:, 2].max() > 0.95,
          f"z range {d[:,2].min():.3f}..{d[:,2].max():.3f}")

    print("\nperfectly aligned field (all E along +x, |E|=2)")
    E = np.tile([2.0, 0.0, 0.0], (5000, 1))
    s = sweep(E)
    check("max ~= |E|", abs(s["max"] - 2.0) < 0.02, f"max={s['max']:.4f}")
    check("min ~= 0", s["min"] < 0.02, f"min={s['min']:.4f}")
    check("envelope is huge", s["envelope_db"] > 30, f"{s['envelope_db']:.1f} dB")
    check("argmax points along x", abs(abs(s["dir_max"][0]) - 1.0) < 0.05,
          f"dir_max={np.round(s['dir_max'],3)}")

    print("\nisotropic random field")
    E = rng.normal(size=(20000, 3))
    s = sweep(E)
    check("envelope is narrow", s["envelope_db"] < 3.0, f"{s['envelope_db']:.2f} dB")

    print("\nprincipal_axis")
    P = rng.normal(size=(5000, 3)) * np.array([10.0, 1.0, 1.0])
    ax, dom = principal_axis(P)
    check("axis recovers the long direction", abs(abs(ax[0]) - 1.0) < 0.05,
          f"axis={np.round(ax,3)}")
    check("dominance is large", dom > 5, f"ratio={dom:.2f}")
    P = rng.normal(size=(5000, 3))
    _, dom = principal_axis(P)
    check("isotropic cloud has no long axis", dom < 1.15, f"ratio={dom:.3f}")

    print("\nweighted vs unweighted median")
    E = np.vstack([np.tile([1.0, 0, 0], (100, 1)), np.tile([5.0, 0, 0], (100, 1))])
    w = np.concatenate([np.full(100, 1.0), np.full(100, 100.0)])
    unw = evaluate_at(E, [1, 0, 0])
    wtd = evaluate_at(E, [1, 0, 0], w)
    check("weights shift the median toward the heavy elements",
          wtd > unw, f"unweighted={unw:.2f} weighted={wtd:.2f}")

    print("\nguards")
    for bad, desc in ((np.zeros((0, 3)), "empty compartment"),
                      (np.zeros((10, 2)), "wrong shape")):
        try:
            sweep(bad)
            check(f"rejects {desc}", False)
        except ValueError:
            check(f"rejects {desc}", True)

    print("\nSELF-TEST", "PASSED" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    if "--pca-check" in sys.argv:
        i = sys.argv.index("--pca-check")
        if i + 1 >= len(sys.argv):
            print("usage: --pca-check <label-volume.nii>", file=sys.stderr)
            sys.exit(2)
        sys.exit(_pca_check(Path(sys.argv[i + 1])))
    print(__doc__)
    print("Nothing to do without a solved E-field.")
    print("  --self-test              verify the maths on synthetic fields")
    print("  --pca-check <nifti>      test FIBRE_MODEL against MIDA geometry")
