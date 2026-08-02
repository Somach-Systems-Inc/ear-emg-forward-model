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
    P = np.asarray(points, dtype=np.float64)
    if P.ndim != 2 or P.shape[1] != 3 or len(P) < 3:
        raise ValueError(f"need (M>=3, 3) points, got {P.shape}")
    C = np.cov((P - P.mean(0)).T)
    vals, vecs = np.linalg.eigh(C)
    order = np.argsort(vals)[::-1]
    vals, vecs = vals[order], vecs[:, order]
    ratio = float(np.sqrt(vals[0] / vals[1])) if vals[1] > 0 else float("inf")
    return vecs[:, 0], ratio


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
    print(__doc__)
    print("Nothing to do without a solved E-field. Run --self-test to verify the maths.")
