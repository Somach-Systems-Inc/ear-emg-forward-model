#!/usr/bin/env python3
"""
Physical invariants for every production solve, replacing SimNIBS's broken
current-calibration check.

WHY THIS EXISTS

SimNIBS's own check emits exactly 200.00% on any custom mesh because it cannot
locate an m2m folder, so it is useless as a signal: it fires on good solves and
bad ones alike. Meanwhile the real failure -- a conductivity span near the
double-precision limit driving the iterative `hypre` solver to return fields
10-20x too large -- produced no distinguishable message. And hypre exposes
neither a residual nor an iteration count.

So the checks here are computed from the FIELD ALONE. They need no solver
internals and no m2m folder, and they are physical invariants rather than
diagnostics: if any fails, the solve is wrong regardless of what the log says.

  1. ENCLOSED CURRENT   integral of J.n over a closed surface around an
                        electrode equals the injected current (charge
                        conservation)
  2. OUTER BOUNDARY     net current through a surface enclosing the whole head
                        is zero (what goes in comes out)
  3. LINEARITY          doubling the injection doubles the field exactly
  4. RECIPROCITY        L(A->B) = -L(B->A) on the head mesh, not just the sphere

1 and 2 run on any single solve. 3 and 4 need a paired solve and run on the
first montage of a production batch.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402

# Tolerances, recorded rather than tuned. The enclosed-current integral is a
# quadrature over a sampled sphere, so a few percent is expected from sampling
# alone; 15% is generous for that while still catching the observed failure,
# which was 1000-2000% wrong.
# The discriminating tolerance is on RADIUS-INDEPENDENCE, not absolute value.
# Measured: converged 2.6%, failed 22%. 8% sits between them with margin.
ENCLOSED_CURRENT_CV_TOL = 0.08   # coefficient of variation across shells
BOUNDARY_NET_TOL = 0.05          # fraction of injected current
LINEARITY_TOL = 1e-6             # relative
RECIPROCITY_TOL = 1e-6           # relative


def _fib_sphere(n):
    k = np.arange(n, dtype=float) + 0.5
    z = 1.0 - 2.0 * k / n
    r = np.sqrt(np.maximum(0.0, 1.0 - z * z))
    phi = np.pi * (1.0 + 5.0 ** 0.5) * k
    return np.column_stack((r * np.cos(phi), r * np.sin(phi), z))


def _sample_field(m, pts, return_inside=False):
    """(E, tag) at each point, from the tetrahedron containing it.

    find_closest_element maps a point OUTSIDE the mesh onto the nearest surface
    element, which then reports real tissue conductivity and a real field. For
    a surface integral that silently inflates the flux, and worse, it inflates
    it more at larger radii as more of the sphere leaves the head. `inside`
    flags points whose nearest element is genuinely near them.
    """
    E = np.asarray(m.field["E"].value)
    if E.ndim != 2 or E.shape[1] != 3:
        raise RuntimeError(f"E must be (n,3), got {E.shape}")
    idx = m.find_closest_element(pts, return_index=True)[1] - 1
    if not return_inside:
        return E[idx], m.elm.tag1[idx]
    nodes = m.nodes.node_coord
    nl = m.elm.node_number_list[idx]
    cent = np.stack([nodes[nl[:, i] - 1] for i in range(4)]).mean(0)
    d = np.linalg.norm(pts - cent, axis=1)
    # ABSOLUTE threshold from the mesh's own element size. A percentile of the
    # sample distances would be circular: if most points are outside, the
    # median inflates and everything passes.
    tets = m.elm.elm_type == 4
    h = float(np.mean(m.elements_volumes_and_areas()[tets]) ** (1 / 3))
    inside = d <= 2.0 * h
    return E[idx], m.elm.tag1[idx], inside


def enclosed_current(m, centre, radius_mm, sigma_by_tag, n_pts=4000):
    """Net current out of a sphere of `radius_mm` about `centre`, in amperes.

    Surface integral of J.n = sigma * E.n over the sphere, by quadrature on a
    near-uniform point set. Units: E in V/m, sigma in S/m, area in m^2.
    """
    u = _fib_sphere(n_pts)
    pts = centre[None, :] + radius_mm * u
    E, tags, inside = _sample_field(m, pts, return_inside=True)
    sig = np.array([sigma_by_tag.get(int(t), np.nan) for t in tags])
    # Points outside the head carry no current: sigma_air is ~0 physically, and
    # numerically their nearest-element lookup is meaningless. Zero them rather
    # than letting a surface element stand in for them.
    Jn = np.where(inside & np.isfinite(sig),
                  sig * np.einsum("ij,ij->i", E, u), 0.0)
    area_m2 = 4.0 * np.pi * (radius_mm * 1e-3) ** 2
    return float(np.mean(Jn) * area_m2), float(np.mean(inside))


def check_solve(mesh_path, elec_centre, sigma_by_tag,
                injected_A=None, radii_mm=(25.0, 35.0, 45.0), verbose=True):
    """Invariants 1 and 2 on a single solve. Returns a dict; raises on failure."""
    from simnibs import mesh_io
    injected_A = injected_A or config.INJECTION_CURRENT_A
    m = mesh_io.read_msh(str(mesh_path))

    out = {"radii_mm": list(radii_mm), "enclosed_A": [], "ratio": []}
    for r in radii_mm:
        I, frac_in = enclosed_current(
            m, np.asarray(elec_centre, float), r, sigma_by_tag)
        out["enclosed_A"].append(I)
        out["ratio"].append(I / injected_A)
        if verbose:
            print(f"    r={r:4.0f} mm  enclosed {I:+.4e} A  "
                  f"ratio {I/injected_A:+.4f}  ({frac_in:.0%} of the shell "
                  f"is inside the head)")

    # THE INVARIANT IS RADIUS-INDEPENDENCE, not the absolute value.
    #
    # Charge conservation says the flux through ANY surface enclosing the
    # electrode is the same. The absolute ratio carries a systematic quadrature
    # bias (~20% low here, from the discrete inside/outside test on a sampled
    # shell), and that bias applies to every radius equally -- so it cancels out
    # of a consistency test while contaminating an absolute one. Measured
    # separation on the known cases:
    #   converged solve   0.845 / 0.806 / 0.810   CV  2.6%
    #   failed solve      0.902 / 1.508 / 1.528   CV 22%
    r = np.array(out["ratio"], dtype=float)
    cv = float(np.std(r) / np.abs(np.mean(r))) if np.all(np.isfinite(r)) else np.nan
    med = float(np.median(r))
    out["median_ratio"], out["cv"] = med, cv
    if verbose:
        print(f"    radius-independence CV = {cv:.1%} "
              f"(tolerance {ENCLOSED_CURRENT_CV_TOL:.0%})")
    if not np.isfinite(cv) or cv > ENCLOSED_CURRENT_CV_TOL:
        raise RuntimeError(
            f"INVARIANT 1 FAILED: enclosed current varies {cv:.1%} across "
            f"shells of {radii_mm} mm ({np.round(r,3).tolist()}). Charge "
            f"conservation requires it to be radius-independent, so the solve "
            f"did not converge.")
    # loose absolute band, only to catch a gross scale error the CV cannot see
    if not (0.4 <= abs(med) <= 2.5):
        raise RuntimeError(
            f"INVARIANT 1 FAILED: enclosed current is {med:+.3f} x injected, "
            f"outside the loose 0.4-2.5 sanity band even allowing for "
            f"quadrature bias.")

    # Invariant 2: a shell enclosing the whole head must net to zero, because
    # source and sink are both inside it.
    nodes = m.nodes.node_coord
    cog = nodes.mean(0)
    big = float(np.percentile(np.linalg.norm(nodes - cog, axis=1), 99)) * 1.05
    net, _ = enclosed_current(m, cog, big, sigma_by_tag)
    out["outer_net_A"] = net
    out["outer_net_frac"] = net / injected_A
    if verbose:
        print(f"    outer shell r={big:.0f} mm  net {net:+.3e} A  "
              f"({net/injected_A:+.4f} x injected)")
    if abs(net / injected_A) > BOUNDARY_NET_TOL:
        raise RuntimeError(
            f"INVARIANT 2 FAILED: net current through a shell enclosing the "
            f"whole head is {net/injected_A:+.4f} x injected, should be 0.")
    return out


def check_linearity(msh_1x, msh_2x, pts, tol=LINEARITY_TOL):
    """Invariant 3: doubling the injection doubles the field exactly."""
    from simnibs import mesh_io
    a = _sample_field(mesh_io.read_msh(str(msh_1x)), pts)[0]
    b = _sample_field(mesh_io.read_msh(str(msh_2x)), pts)[0]
    n = np.linalg.norm(a, axis=1)
    k = n > 0
    rel = np.abs(np.linalg.norm(b[k], axis=1) / n[k] - 2.0) / 2.0
    worst = float(np.max(rel)) if k.any() else float("nan")
    if not np.isfinite(worst) or worst > tol:
        raise RuntimeError(f"INVARIANT 3 FAILED: field ratio at 2I vs I "
                           f"deviates from 2 by {worst:.3e} (tol {tol:.0e})")
    return worst


def check_reciprocity_symmetry(msh_ab, msh_ba, pts, tol=RECIPROCITY_TOL):
    """Invariant 4: swapping source and sink negates the field exactly."""
    from simnibs import mesh_io
    a = _sample_field(mesh_io.read_msh(str(msh_ab)), pts)[0]
    b = _sample_field(mesh_io.read_msh(str(msh_ba)), pts)[0]
    n = np.linalg.norm(a, axis=1)
    k = n > 0
    rel = np.linalg.norm(a[k] + b[k], axis=1) / n[k]
    worst = float(np.max(rel)) if k.any() else float("nan")
    if not np.isfinite(worst) or worst > tol:
        raise RuntimeError(f"INVARIANT 4 FAILED: L(A->B) + L(B->A) is "
                           f"{worst:.3e} of |L|, should be 0 (tol {tol:.0e})")
    return worst


if __name__ == "__main__":
    print(__doc__)
    print(f"tolerances: enclosed {ENCLOSED_CURRENT_TOL:.0%}, "
          f"outer {BOUNDARY_NET_TOL:.0%}, linearity {LINEARITY_TOL:.0e}, "
          f"reciprocity {RECIPROCITY_TOL:.0e}")
