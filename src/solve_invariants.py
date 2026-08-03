#!/usr/bin/env python3
"""
Physical invariants for every production solve, alongside SimNIBS's own
current-calibration check.

WHY THIS EXISTS

Not because SimNIBS's check is broken. It is not. On the MIDA mesh it
discriminated correctly: it reported 200.00% on the solve that was wrong and
stayed silent on the solve that was right. The failure was that nobody read
`fields_summary.txt`. (An earlier version of this docstring asserted the check
was useless. That was wrong and is corrected here rather than deleted.)

These invariants exist for three reasons that survive that correction:

  - the SimNIBS check is BINARY and gives no severity, and `hypre` exposes
    neither residual nor iteration count, so there is nothing to trend
  - it produces false positives on well-conditioned custom meshes (5 of 16
    sphere solves warned while matching the analytic oracle to RDM 4.36%)
  - it lives in a file that must be opened, whereas these raise

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

BATCH POLICY

1 and 2 run on EVERY solve; they need no extra work.

3 and 4 need a paired solve, so they run on the FIRST and LAST solve of a batch,
not the first alone. Four extra solves for a 44-solve production run instead of
forty-four, and unlike a first-solve check it catches drift that appears partway
through. They also run on any solve whose invariant-1 CV is elevated but still
under threshold, since that is the signature of a solve heading toward failure.

COVERAGE MAP, INCLUDING THE GAP

    invariant 1  (radius-independent flux) -> stalled / non-converged solve
    invariant 2  (outer boundary nets zero) -> unconserved current
    invariant 3  (linearity in I)           -> nonlinearity
    invariant 4  (L(A->B) = -L(B->A))       -> reciprocity broken on real geometry
    ANALYTIC SPHERE                         -> UNIFORM SCALE ERROR

The last row is the gap, and it is why the sphere stays in pre-flight
permanently rather than being retired as a one-off. **No head-mesh invariant can
detect a globally scaled field.** Multiply every E by a constant and the flux
stays radius-independent, the outer boundary still nets zero, linearity still
holds exactly, and reciprocity symmetry is untouched. Every check here passes.
Only comparison against an absolute external reference catches it, and the
analytic multilayer sphere is the only absolute reference available.

QUADRATURE BIAS, AND WHY IT IS TOLERATED

The flux integral runs ~19% low, from the discrete inside/outside test on a
sampled shell. It is used as a CONSISTENCY test only, never as an absolute
measurement, because a common-mode bias cancels from a radius-comparison while
contaminating an absolute one. That is worth stating generally: when a
measurement is biased but the bias is common to all conditions, compare
conditions rather than trying to remove the bias.
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
#
# CALIBRATED from a set of 4 known-good solves (the sigma_air sweep at 1e-6,
# 1e-5, 1e-4, 1e-3; all clean, none carrying a calibration warning), rather
# than picked as a round number between the good and bad cases:
#
#     CVs        2.144, 2.146, 2.167, 2.318 %      mean 2.194, sd 0.084
#     GATE       rule: max(known-good) x 3          -> 6.95 %
#     ESCALATE   rule: mean + 3sd .. gate           -> 2.44 .. 6.95 %
#
# The observed failure sat at 22.1%, i.e. 3.2x above the gate. The calibration
# set is n=4 and spans only sigma_air; it does not sample mesh or montage
# variation, so widen it if either changes materially.
ENCLOSED_CURRENT_CV_TOL = 0.0695   # calibrated, n=4 known-good
ENCLOSED_CURRENT_CV_ESCALATE = 0.0244  # mean + 3sd of the same set
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


# ----------------------------------------------------------------------
# Batch policy
# ----------------------------------------------------------------------
# Superseded by the calibrated band above; kept only as the fallback if no
# calibration set is available.
CV_ELEVATED_FRAC = 0.5


def batch_plan(n_solves):
    """Which solve indices get the paired invariants 3 and 4."""
    if n_solves <= 0:
        return set()
    if n_solves == 1:
        return {0}
    return {0, n_solves - 1}


def needs_escalation(cv, gate=None):
    """True if invariant-1 CV passed but is elevated enough to warrant 3 and 4.

    A solve drifting toward non-convergence shows a rising CV before it crosses
    the gate, so this catches the approach rather than only the arrival.
    """
    gate = ENCLOSED_CURRENT_CV_TOL if gate is None else gate
    lo = ENCLOSED_CURRENT_CV_ESCALATE
    return bool(np.isfinite(cv) and lo < cv <= gate)
