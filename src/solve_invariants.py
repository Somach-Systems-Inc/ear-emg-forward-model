#!/usr/bin/env python3
"""
Physical invariants for every production solve, alongside SimNIBS's own
current-calibration check.

WHY THIS EXISTS

**SimNIBS's current-calibration check is measured ANTI-CORRELATED with true
delivered current on this mesh and is no longer evidence of anything.** On the
22 stage-3 solves, Spearman(reported calibration error, true |deviation|) =
-0.425, p = 0.048, n = 22; the largest true deviation (`buccal`, 0.8870 mA of
1 mA requested) is reported CLEAN while `mental` at 1.0746 mA is flagged
32.99%. It is parsed and recorded per solve, and it gates nothing.

*(This docstring has now been wrong in both directions. It first asserted the
check was useless; that was retracted as over-reach; the retraction was then
falsified by measurement against the tet-patch integral. The original claim
was right. See METHODS_LOG, "the double reversal". Only the measurement
settled it -- neither version of the argument did.)*

So these invariants are not a supplement to the solver's own check. They are
the only per-solve evidence there is:

  - they are computed from the FIELD ALONE, needing no solver internals and no
    m2m folder, so they cannot inherit the solver's own blind spots
  - they give severity, not a binary, and `hypre` exposes neither residual nor
    iteration count, so there is nothing else to trend
  - the solver's check lives in a file that must be opened, whereas these raise

They are physical invariants rather than diagnostics: if any fails, the solve
is wrong regardless of what the log says.

  1. ENCLOSED CURRENT   integral of J.n over a closed surface around an
                        electrode equals the injected current (charge
                        conservation)
  2. OUTER BOUNDARY     net current through a surface enclosing the whole head
                        is zero (what goes in comes out)
  3. LINEARITY          doubling the injection doubles the field exactly
  4. RECIPROCITY        L(A->B) = -L(B->A) on the head mesh, not just the sphere

BATCH POLICY -- AND THE PART OF IT THAT WAS NEVER TRUE

1 and 2 run on EVERY solve; they need no extra work.

3 and 4 need a paired solve, so the policy is that they run on the FIRST and
LAST solve of a batch, plus any solve whose invariant-1 CV is elevated but
still under the gate.

**THAT POLICY HAS NEVER EXECUTED.** `check_linearity` and
`check_reciprocity_symmetry` have no caller anywhere in the repository, and
neither does `batch_plan`. All 22 stage-3 solves ran with invariants 1 and 2
only. `needs_escalation` IS called by `03_leadfields.py`, but its result is
printed as a `[ESCALATE]` tag and then discarded, so the escalation branch is
inert too. Audited 2026-08-03.

This is the fifth and sixth instance of "written, documented as policy, wired
to nothing" in this repository. `test_guard_coverage.py` could not see it
because invariants 3 and 4 were not in its REQUIRED set; they are now, and it
fails until they are wired. The escalation band was never reached in any case
(observed CV 0.32-1.53%, band opens at 2.44%), so nothing silently passed a
check it should have failed -- but that is luck, not coverage.

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
import traceback
from contextlib import contextmanager
from dataclasses import dataclass, field as _dc_field
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402


# ----------------------------------------------------------------------
# COLLECT-THEN-RAISE
# ----------------------------------------------------------------------
# Fail-fast is right for a cheap precondition and wrong for a diagnostic,
# because the first failure hides every later one. That is not a hypothetical:
# invariant 2 sat after invariant 1's raise and was therefore unreachable on
# any solve broken enough to disturb the radius plateau -- which is every solve
# it existed to catch. It was reported as "passing" for the whole project.
#
# The rule this encodes: a guard chain evaluates EVERY guard, records each
# verdict, and raises ONCE with all of them. A guard that cannot be evaluated
# is recorded as ERROR, never skipped silently, because a skipped guard reads
# exactly like a passing one.

GUARD_STATUS = ("pass", "fail", "error")


@dataclass
class Verdict:
    name: str
    status: str
    message: str
    value: float | None = None
    threshold: str | None = None
    detail: dict = _dc_field(default_factory=dict)

    def __str__(self):
        mark = {"pass": "ok  ", "fail": "FAIL", "error": "ERR "}[self.status]
        v = "" if self.value is None else f"  [{self.value:+.6g}]"
        t = "" if self.threshold is None else f"  (limit {self.threshold})"
        return f"    {mark}  {self.name}{v}{t}\n           {self.message}"


class GuardsFailed(RuntimeError):
    """Raised once, carrying every guard that failed rather than the first."""

    def __init__(self, label, verdicts):
        self.verdicts = list(verdicts)
        self.failures = [v for v in self.verdicts if v.status != "pass"]
        body = "\n".join(str(v) for v in self.verdicts)
        super().__init__(
            f"{len(self.failures)} of {len(self.verdicts)} guards failed on "
            f"{label}:\n{body}")


class GuardChain:
    """Accumulates guard verdicts and raises once, with all of them.

    Every guard runs. `guard()` is a context manager so that a guard which
    THROWS (rather than returning a verdict) is recorded as an error and the
    chain continues, instead of aborting the remaining guards -- an exception
    escaping mid-chain would reintroduce exactly the masking this exists to
    remove.
    """

    def __init__(self, label):
        self.label = label
        self.verdicts = []

    def record(self, name, ok, message, value=None, threshold=None, **detail):
        self.verdicts.append(Verdict(name, "pass" if ok else "fail", message,
                                     value, threshold, detail))
        return ok

    @contextmanager
    def guard(self, name):
        try:
            yield
        except Exception as e:                     # noqa: BLE001 - deliberate
            self.verdicts.append(Verdict(
                name, "error",
                f"guard could not be evaluated: {type(e).__name__}: {e}",
                detail={"traceback": traceback.format_exc()}))

    @property
    def failures(self):
        return [v for v in self.verdicts if v.status != "pass"]

    def report(self):
        return "\n".join(str(v) for v in self.verdicts)

    def raise_if_failed(self):
        if self.failures:
            raise GuardsFailed(self.label, self.verdicts)

    def as_dict(self):
        return {v.name: v.status for v in self.verdicts}

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
# The observed failure sat at 22.1%, i.e. 3.2x above the gate.
#
# CALIBRATION 1 (n=4): varies ONLY sigma_air, on one mesh and one montage, so
# sd = 0.084 pp captures none of the mesh or montage variance that a production
# batch contains. EXPECT ESCALATION TO FIRE ON MOST STAGE-3 SOLVES. That is the
# predicted behaviour of a band calibrated on an unrepresentative set, not a
# sign of trouble, and it should not be read as evidence of drift.
#
# CALIBRATION 2 (pending): recalibrate the escalation band from the first 10
# stage-3 solves, once real mesh and montage variance is represented. Record it
# as a SECOND calibration with its own n beside the first, rather than
# overwriting -- the two answer different questions and the first stays the
# reference for sigma_air sensitivity.
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

    Returns (net_current_A, frac_inside, frac_unknown_tag).

    frac_inside is the share of the sampled shell that actually lies within the
    meshed conductor, and IT IS PART OF THE RESULT, not diagnostics. The
    estimator has no support outside the mesh, so as frac_inside -> 0 the
    integral tends to exactly 0.0 and any tolerance on it passes trivially.
    Measured on the truncated MIDA mesh: at 1.30 x the 99th-percentile node
    radius the shell is 0% inside and the net is exactly +0.000000e+00. A
    caller that discards frac_inside cannot tell that verdict apart from
    conservation actually holding. `check_solve_plateau` discarded it for the
    whole project.

    frac_unknown_tag is the share zeroed because their tag carries no
    conductivity. That is a SILENT ZERO -- the project's own rule forbids it --
    so it is returned and gated by the caller rather than absorbed here.
    """
    u = _fib_sphere(n_pts)
    pts = centre[None, :] + radius_mm * u
    E, tags, inside = _sample_field(m, pts, return_inside=True)
    sig = np.array([sigma_by_tag.get(int(t), np.nan) for t in tags])
    # Points outside the head carry no current: sigma_air is ~0 physically, and
    # numerically their nearest-element lookup is meaningless. Zero them rather
    # than letting a surface element stand in for them.
    known = np.isfinite(sig)
    Jn = np.where(inside & known, sig * np.einsum("ij,ij->i", E, u), 0.0)
    area_m2 = 4.0 * np.pi * (radius_mm * 1e-3) ** 2
    unknown = float(np.mean(inside & ~known))
    return float(np.mean(Jn) * area_m2), float(np.mean(inside)), unknown


def _enclosed_net(m, centre, radius_mm, sigma_by_tag, n_pts=4000):
    """Back-compatible 2-tuple wrapper for callers that predate frac_unknown."""
    net, frac_in, _ = enclosed_current(m, centre, radius_mm, sigma_by_tag,
                                       n_pts)
    return net, frac_in


# ----------------------------------------------------------------------
# `check_solve()` -- REMOVED 2026-08-03, and why it is not merely deprecated
# ----------------------------------------------------------------------
# It computed invariant 1 from the SHELL quadrature (`enclosed_current`), which
# `check_solve_plateau` superseded with the exact tet-patch integral. Nothing
# called it. It mattered anyway, for two reasons:
#
#   - it was named in `test_guard_coverage.REQUIRED`, so a solving script could
#     have satisfied the "invariants are wired" requirement by calling a dead
#     function. A coverage test that accepts a dead callee measures nothing.
#   - it carried its own copy of invariant 2, behind TWO earlier raises, so it
#     was the original site of the masking defect.
#
# Its one surviving idea is the loose absolute band (0.4-2.5 x injected), which
# catches a gross uniform scale error that a radius-consistency test cannot
# see. That band is not deleted -- it moves to `check_solve_plateau` as
# INVARIANT_1_MAGNITUDE, unchanged in value. It predates every stage-3
# observation, so moving it is not tuning it.


# Invariants 3 and 4 are split into a mesh-loading wrapper and a field-level
# core. The split is not cosmetic: the core is what the synthetic per-guard
# tests can drive without a solve, and a guard that can only be exercised by
# running two 4-minute solves is a guard that never gets exercised.

def _check_linearity_fields(m_1x, m_2x, pts, tol=LINEARITY_TOL):
    """Invariant 3 on two already-loaded meshes."""
    a = _sample_field(m_1x, pts)[0]
    b = _sample_field(m_2x, pts)[0]
    n = np.linalg.norm(a, axis=1)
    k = n > 0
    rel = np.abs(np.linalg.norm(b[k], axis=1) / n[k] - 2.0) / 2.0
    worst = float(np.max(rel)) if k.any() else float("nan")
    if not np.isfinite(worst) or worst > tol:
        raise RuntimeError(f"INVARIANT 3 FAILED: field ratio at 2I vs I "
                           f"deviates from 2 by {worst:.3e} (tol {tol:.0e})")
    return worst


def check_linearity(msh_1x, msh_2x, pts, tol=LINEARITY_TOL):
    """Invariant 3: doubling the injection doubles the field exactly."""
    from simnibs import mesh_io
    return _check_linearity_fields(mesh_io.read_msh(str(msh_1x)),
                                   mesh_io.read_msh(str(msh_2x)), pts, tol)


def _check_reciprocity_fields(m_ab, m_ba, pts, tol=RECIPROCITY_TOL):
    """Invariant 4 on two already-loaded meshes."""
    a = _sample_field(m_ab, pts)[0]
    b = _sample_field(m_ba, pts)[0]
    n = np.linalg.norm(a, axis=1)
    k = n > 0
    rel = np.linalg.norm(a[k] + b[k], axis=1) / n[k]
    worst = float(np.max(rel)) if k.any() else float("nan")
    if not np.isfinite(worst) or worst > tol:
        raise RuntimeError(f"INVARIANT 4 FAILED: L(A->B) + L(B->A) is "
                           f"{worst:.3e} of |L|, should be 0 (tol {tol:.0e})")
    return worst


def check_reciprocity_symmetry(msh_ab, msh_ba, pts, tol=RECIPROCITY_TOL):
    """Invariant 4: swapping source and sink negates the field exactly."""
    from simnibs import mesh_io
    return _check_reciprocity_fields(mesh_io.read_msh(str(msh_ab)),
                                     mesh_io.read_msh(str(msh_ba)), pts, tol)


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


# ----------------------------------------------------------------------
# Tet-patch flux: exact enclosure, mesh's own faces as the quadrature
# ----------------------------------------------------------------------
# SimNIBS adds electrode volumes to the mesh with its own tag ranges, and they
# ARE part of the conductor -- a surface enclosing the electrode necessarily
# cuts through them. Values read from
# simnibs/utils/mesh_element_properties.py, not assumed.
ELECTRODE_RUBBER_RANGE = (100, 499)    # sigma 29.4 S/m
SALINE_GEL_RANGE = (500, 899)          # sigma 1.0 S/m
ELECTRODE_RUBBER_SIGMA = 29.4
SALINE_GEL_SIGMA = 1.0


def with_electrode_tags(sigma_by_tag, mesh_tags=None):
    """Extend a Table-1 conductivity map with SimNIBS's electrode tags.

    `mesh_tags`, when given, is the set of tags actually present in the mesh.
    Any of them that fall in a reserved electrode range WITHOUT being in
    `sigma_by_tag` raise, because that is a silent 83x error waiting to happen.

    THE COLLISION THIS EXISTS TO STOP. `01c_extend_neck.py` tags the
    neck-extension slab **200**, which sits inside ELECTRODE_RUBBER_RANGE
    (100-499). A map built from Table 1 alone therefore had its 42,766 slab
    elements filled in at 29.4 S/m electrode rubber instead of 0.355 S/m
    muscle. `setdefault` made it silent: a map that already carried tag 200 was
    correct, a map that did not got rubber, and both look identical at the call
    site. It moved invariant 2's reading on the extended mesh from -0.0038
    (passes) to -0.310 (fires), which was then written into METHODS_LOG as a
    measurement. See METHODS_LOG 2026-08-03.
    """
    out = dict(sigma_by_tag)
    reserved = [(ELECTRODE_RUBBER_RANGE, ELECTRODE_RUBBER_SIGMA, "electrode rubber"),
                (SALINE_GEL_RANGE, SALINE_GEL_SIGMA, "saline gel")]
    if mesh_tags is not None:
        clashes = [(int(t), name)
                   for t in sorted(set(int(x) for x in mesh_tags))
                   for (lo, hi), _, name in reserved
                   if lo <= t <= hi and t not in sigma_by_tag]
        if clashes:
            raise RuntimeError(
                "tags present in the mesh fall inside SimNIBS's reserved "
                "electrode ranges but carry no conductivity of their own, so "
                "they would be silently filled in as electrode material: "
                + ", ".join(f"tag {t} (would become {name})"
                            for t, name in clashes)
                + ". Give them an explicit conductivity, or retag the "
                  "compartment outside 100-899.")
    for (lo, hi), sig, _ in reserved:
        for t in range(lo, hi + 1):
            out.setdefault(t, sig)
    return out


def patch_flux(m, centre, radius_mm, sigma_by_tag):
    """Current crossing OUT of the tet patch through its INTERIOR cut, in A.

    THE PREMISE THAT HAD TO BE FIXED. SimNIBS injects current as a Dirichlet
    condition on the electrode's EXTERIOR surface, not as a volumetric source.
    A patch around the electrode therefore contains no source at all: current
    enters through the mesh's outer face and leaves through the cut, and the
    NET flux is exactly zero. Measured: +0.968 out through the cut, -0.938 in
    through the exterior, total +0.030.

    So the quantity that equals the injected current is the flux through the
    interior cut ONLY. Boundary faces are split by their multiplicity in the
    FULL mesh: 2 means an interior face (part of the cut), 1 means it lies on
    the mesh exterior (where the current is imposed).

    Enclosure and orientation are exact by construction -- the patch surface
    closes to 1.2e-16 of its own area -- and there is no inside/outside test.

    Returns (cut_flux_A, exterior_flux_A, n_cut_faces).
    """
    centre = np.asarray(centre, dtype=np.float64)
    nodes = m.nodes.node_coord.astype(np.float64)
    tets = m.elm.elm_type == 4
    nl = m.elm.node_number_list[tets][:, :4] - 1
    tags = m.elm.tag1[tets]
    E = np.asarray(m.field["E"].value)
    if E.ndim != 2 or E.shape[1] != 3:
        raise RuntimeError(f"E must be (n,3), got {E.shape}")
    E = E[tets]

    FACES = ((0, 1, 2, 3), (0, 1, 3, 2), (0, 2, 3, 1), (1, 2, 3, 0))
    n_t = len(nl)
    all_faces = np.sort(np.concatenate(
        [nl[:, list(f[:3])] for f in FACES]), axis=1)
    _, inv_all, cnt_all = np.unique(all_faces, axis=0,
                                    return_inverse=True, return_counts=True)

    sel = np.linalg.norm(nodes[nl].mean(axis=1) - centre, axis=1) <= radius_mm
    if not sel.any():
        raise RuntimeError(f"no tetrahedra within {radius_mm} mm of {centre}")
    idx = np.flatnonzero(sel)
    own = np.tile(idx, 4)
    slot = np.concatenate([idx + k * n_t for k in range(4)])
    tri = np.concatenate([nl[sel][:, list(f[:3])] for f in FACES])
    opp = np.concatenate([nl[sel][:, f[3]] for f in FACES])

    _, iv, cv = np.unique(np.sort(tri, axis=1), axis=0,
                          return_inverse=True, return_counts=True)
    bnd = cv[iv] == 1

    a = nodes[tri[bnd][:, 0]]
    b = nodes[tri[bnd][:, 1]]
    c = nodes[tri[bnd][:, 2]]
    nrm = np.cross(b - a, c - a)
    two_area = np.linalg.norm(nrm, axis=1)
    nhat = nrm / np.maximum(two_area, 1e-30)[:, None]
    nhat[np.einsum("ij,ij->i", nhat, nodes[opp[bnd]] - a) > 0] *= -1.0
    area_m2 = 0.5 * two_area * 1e-6

    sig = np.array([sigma_by_tag.get(int(t), np.nan) for t in tags[own[bnd]]])
    if not np.isfinite(sig).all():
        missing = sorted({int(t) for t, s in zip(tags[own[bnd]], sig)
                          if not np.isfinite(s)})
        raise RuntimeError(f"tags on the patch boundary have no conductivity: "
                           f"{missing}")
    Jn = sig * np.einsum("ij,ij->i", E[own[bnd]], nhat) * area_m2
    is_cut = cnt_all[inv_all[slot[bnd]]] == 2
    return (float(Jn[is_cut].sum()), float(Jn[~is_cut].sum()),
            int(is_cut.sum()))


# ----------------------------------------------------------------------
# Plateau criterion on the corrected (cut-faces-only) flux
# ----------------------------------------------------------------------
PLATEAU_MIN_RADII = 3        # stationary across at least this many radii
PLATEAU_MIN_SPAN_MM = 20.0   # ...spanning at least this range
PLATEAU_CV_TOL = 0.03        # CV within the plateau

RADIUS_SCAN_MM = (25., 35., 45., 55., 65., 75.)

# INVARIANT 1, MAGNITUDE. Inherited unchanged from the deleted `check_solve()`;
# NOT derived from any stage-3 observation, which is what makes it usable.
#
# The plateau test is a CONSISTENCY test and is blind to a uniform scale error:
# multiply every E by a constant and the cut flux stays radius-stationary at
# the wrong value. Invariant 2 is blind to it too, since a scaled zero is still
# zero. Before today nothing per-solve caught it -- only the analytic sphere in
# pre-flight, which runs once per environment and not per solve.
#
# This band is deliberately LOOSE. It is a gross-error gate for the 10-20x
# conditioning failure, not an accuracy claim. A tight window around the
# observed 0.887-1.075 would be derived from the data it judges, which is the
# circularity the plateau design exists to avoid, and it is exactly the move
# that produced the retired "11-15% benign band". The delivered current is
# REPORTED per solve instead, and the flip point is reported with it.
PLATEAU_MEAN_MIN = 0.4
PLATEAU_MEAN_MAX = 2.5

# INVARIANT 2, SUPPORT. Measured 2026-08-03 and this is why it exists.
#
# Invariant 2 integrates J.n over a shell at 1.05 x the 99th-percentile node
# radius. On the truncated MIDA mesh only 5.35% of that shell lies inside the
# conductor, and the mesh carries no air box (Background tag 50 has volume
# fraction 0.0), so the shell is mostly in empty space. As the shell escapes
# the mesh entirely the estimator loses all support and returns exactly 0.0:
#
#     r / p99     1.00     1.05     1.10     1.30
#     inside      8.20%    5.35%    3.33%    0.00%
#     net/inj    -0.606   +0.0138  +0.0021  +0.000000
#
# A tolerance on the net alone therefore passes trivially in the limit, and a
# zero from no-support is indistinguishable from a zero from conservation. The
# guard still discriminates at the coverage it actually has -- on the known-bad
# extended mesh it reports -0.310 and -0.566 x injected against -0.000015 on
# the truncated control -- but that is a property of this geometry, not of the
# check, and it must not be left implicit.
#
# 2% is set BELOW every observed working value (3.33% is the lowest coverage at
# which the estimator was still demonstrated to discriminate) and above the
# degenerate zero. It fires on absence of evidence, not on a bad result.
BOUNDARY_MIN_COVERAGE = 0.02

# The shell multiplier, promoted from a literal buried in the function body to
# a named constant, because it is the whole reason the support problem exists:
# 1.05 places the shell OUTSIDE the 99th-percentile node radius by design. On a
# CONVEX domain that puts it outside the conductor altogether -- for a ball,
# p99/r_max = 0.997, so 1.05 x p99 > r_max and coverage is zero. MIDA gives it
# support only by being elongated (p99 153.3, r_max 199.3). The check is
# therefore geometry-dependent in a way its name does not admit.
OUTER_SHELL_FACTOR = 1.05


def find_plateau(radii, vals, cv_tol=PLATEAU_CV_TOL,
                 min_n=PLATEAU_MIN_RADII, min_span=PLATEAU_MIN_SPAN_MM):
    """Longest run of consecutive radii that is stationary. None if none is.

    A patch must be large enough to contain the whole injection surface before
    the cut flux means anything -- buccal sits on thin cheek and does not
    stabilise until r >= 45 mm. Requiring a plateau makes that automatic
    instead of requiring a hand-picked radius per electrode.
    """
    r = np.asarray(radii, float)
    v = np.asarray(vals, float)
    best = None
    for i in range(len(r)):
        for j in range(len(r), i, -1):
            if j - i < min_n or (r[j - 1] - r[i]) < min_span:
                continue
            seg = v[i:j]
            if not np.all(np.isfinite(seg)) or abs(seg.mean()) < 1e-12:
                continue
            cv = float(np.std(seg) / abs(np.mean(seg)))
            if cv <= cv_tol and (best is None or (j - i) > best[2] - best[1]):
                best = (cv, i, j)
        if best is not None and best[1] == i:
            break
    if best is None:
        return None
    cv, i, j = best
    return dict(cv=cv, i=i, j=j, radii=list(r[i:j]), vals=list(v[i:j]),
                mean=float(v[i:j].mean()))


def check_solve_plateau(mesh_path, elec_centre, sigma_by_tag,
                        injected_A=None, radii=RADIUS_SCAN_MM, verbose=True,
                        mesh=None, shell_factor=None):
    """Invariants 1 and 2 on one solve, COLLECT-THEN-RAISE.

    Every guard is evaluated and every verdict recorded before anything is
    raised, so a solve that violates two invariants reports two. The previous
    shape raised on invariant 1 and returned, which made invariant 2
    unreachable on precisely the solves it existed to catch.

    Guards, all four always evaluated:

        invariant_1_plateau     cut flux is radius-stationary
        invariant_1_magnitude   plateau mean within the loose gross-error band
        invariant_2_coverage    the outer shell has support to integrate over
        invariant_2_outer_net   net current through that shell is zero

    Raises GuardsFailed carrying all failures. Returns a dict on success,
    including `guards` (the full verdict list) so a caller can record the
    passes too -- a guard that passed and a guard that never ran must not look
    the same in a log.

    `mesh` accepts an already-loaded mesh object, which is what makes the
    synthetic per-guard tests possible without a solve.
    """
    injected_A = injected_A or config.INJECTION_CURRENT_A
    shell_factor = OUTER_SHELL_FACTOR if shell_factor is None else shell_factor
    if mesh is None:
        from simnibs import mesh_io
        m = mesh_io.read_msh(str(mesh_path))
    else:
        m = mesh
    label = Path(str(mesh_path)).name if mesh_path is not None else "<in-memory>"
    ch = GuardChain(label)

    # ---- invariant 1: scan radii. A radius that ERRORS is recorded as NaN and
    # the scan continues, so one bad radius cannot hide the rest of the chain.
    vals, exts, scan_errors = [], [], []
    for r in radii:
        try:
            cut, ext, _ = patch_flux(m, elec_centre, float(r), sigma_by_tag)
            vals.append(cut / injected_A)
            exts.append(ext / injected_A)
        except Exception as e:                     # noqa: BLE001 - deliberate
            vals.append(float("nan"))
            exts.append(float("nan"))
            scan_errors.append(f"r={r:.0f}mm: {type(e).__name__}: {e}")
        if verbose:
            print(f"    r={r:>4.0f} mm  cut {vals[-1]:+.4f}  "
                  f"exterior {exts[-1]:+.4f}")
    if scan_errors:
        ch.verdicts.append(Verdict(
            "patch_flux_scan", "error",
            f"{len(scan_errors)} of {len(radii)} radii could not be "
            f"integrated: " + "; ".join(scan_errors)))

    pl = find_plateau(radii, vals)
    ch.record("invariant_1_plateau", pl is not None,
              (f"stationary over r={pl['radii'][0]:.0f}-{pl['radii'][-1]:.0f} mm "
               f"({len(pl['radii'])} radii), CV {pl['cv']*100:.2f}%"
               if pl is not None else
               f"no stationary plateau in the cut flux across {list(radii)} mm "
               f"({[round(v, 3) for v in vals]}). Charge conservation requires "
               f"the flux through any enclosing cut to be radius-independent "
               f"once the patch contains the injection surface, so the solve "
               f"did not converge."),
              value=None if pl is None else pl["cv"],
              threshold=f"CV <= {PLATEAU_CV_TOL:.0%}")

    # ---- invariant 1, magnitude. Evaluated even when the plateau failed, by
    # falling back to the median of the scan: "the plateau test failed so we
    # cannot say anything about magnitude" is how the first failure hides the
    # second.
    finite = [v for v in vals if np.isfinite(v)]
    mean_ratio = (pl["mean"] if pl is not None
                  else (float(np.median(finite)) if finite else float("nan")))
    mag_ok = (np.isfinite(mean_ratio)
              and PLATEAU_MEAN_MIN <= abs(mean_ratio) <= PLATEAU_MEAN_MAX)
    ch.record("invariant_1_magnitude", mag_ok,
              (f"delivered {mean_ratio:+.4f} x requested"
               + ("" if pl is not None else " (median of the scan; no plateau)")
               if np.isfinite(mean_ratio) else
               "no finite cut flux at any radius")
              + ("" if mag_ok else
                 f" -- outside the loose gross-error band "
                 f"[{PLATEAU_MEAN_MIN}, {PLATEAU_MEAN_MAX}]. A uniform scale "
                 f"error passes both the plateau test and invariant 2; this is "
                 f"the only per-solve guard that sees it."),
              value=mean_ratio,
              threshold=f"{PLATEAU_MEAN_MIN}-{PLATEAU_MEAN_MAX} x injected")

    # ---- invariant 2: whole-domain charge conservation, plus the support the
    # integral actually has. Coverage is checked FIRST as a verdict but does
    # not gate the net check -- both are recorded either way.
    frac = float("nan")
    cover = float("nan")
    unknown = float("nan")
    with ch.guard("invariant_2_outer_net"):
        cog = m.nodes.node_coord.mean(0)
        big = float(np.percentile(
            np.linalg.norm(m.nodes.node_coord - cog, axis=1), 99)) * shell_factor
        net, cover, unknown = enclosed_current(m, cog, big, sigma_by_tag)
        frac = net / injected_A
        if verbose:
            print(f"    outer shell r={big:.0f} mm  net {net:+.3e} A "
                  f"({frac:+.4f} x injected), {cover:.2%} of the shell inside "
                  f"the conductor")
        ch.record("invariant_2_outer_net", abs(frac) <= BOUNDARY_NET_TOL,
                  f"net through a shell enclosing the whole domain is "
                  f"{frac:+.6f} x injected"
                  + ("" if abs(frac) <= BOUNDARY_NET_TOL else
                     ", should be 0. Current is entering or leaving through "
                     "the outer boundary, so the solve does not conserve "
                     "charge and no value from it is usable."),
                  value=frac, threshold=f"|.| <= {BOUNDARY_NET_TOL}")

    ch.record("invariant_2_coverage",
              bool(np.isfinite(cover) and cover >= BOUNDARY_MIN_COVERAGE),
              (f"{cover:.2%} of the outer shell lies inside the conductor"
               if np.isfinite(cover) else "coverage could not be measured")
              + ("" if np.isfinite(cover) and cover >= BOUNDARY_MIN_COVERAGE
                 else f" -- below {BOUNDARY_MIN_COVERAGE:.0%}, so the surface "
                      f"integral has no support and its result is not "
                      f"evidence either way. A net of zero here means 'nothing "
                      f"was sampled', not 'charge is conserved'."),
              value=cover, threshold=f">= {BOUNDARY_MIN_COVERAGE:.0%}")

    if np.isfinite(unknown) and unknown > 0:
        ch.record("invariant_2_unknown_tags", False,
                  f"{unknown:.2%} of the sampled shell sits in elements whose "
                  f"tag has no conductivity, and was silently zeroed. Add the "
                  f"tags to the conductivity map or exclude them explicitly.",
                  value=unknown, threshold="0%")

    ch.raise_if_failed()
    return dict(vals=vals, exterior=exts, plateau=pl,
                cv=pl["cv"] if pl is not None else float("nan"),
                mean_ratio=mean_ratio, outer_net_frac=frac,
                outer_coverage=cover, guards=ch.verdicts)


if __name__ == "__main__":
    # This block raised NameError on an undefined ENCLOSED_CURRENT_TOL from the
    # day it was written, which means the documented way to inspect the
    # tolerances had never once been run. Small, but the same class as every
    # other finding here: nobody executed it, so nobody knew.
    print(__doc__)
    print("tolerances")
    print(f"  invariant 1 plateau CV   <= {PLATEAU_CV_TOL:.0%}")
    print(f"  invariant 1 magnitude       {PLATEAU_MEAN_MIN}-"
          f"{PLATEAU_MEAN_MAX} x injected")
    print(f"  invariant 2 outer net    <= {BOUNDARY_NET_TOL:.0%} of injected")
    print(f"  invariant 2 coverage     >= {BOUNDARY_MIN_COVERAGE:.0%} of shell")
    print(f"  invariant 3 linearity    <= {LINEARITY_TOL:.0e} relative")
    print(f"  invariant 4 reciprocity  <= {RECIPROCITY_TOL:.0e} relative")
    print(f"  shell-quadrature CV gate <= {ENCLOSED_CURRENT_CV_TOL:.2%} "
          f"(calibration 1, n=4; superseded by the plateau test)")
