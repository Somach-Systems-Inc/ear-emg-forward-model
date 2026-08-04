#!/usr/bin/env python3
"""
Every guard, shown firing on a synthetic input that fails THAT GUARD AND
NOTHING ELSE.

WHY THIS EXISTS, AND WHY END-TO-END CASES WERE NOT ENOUGH

CLAUDE.md already required a known-bad case per guard. Invariant 2 had one --
the extended mesh measured to leak 1.07 mA of a 1 mA injection -- and it was
still never demonstrated, because that mesh ALSO destroys the radius plateau.
Invariant 1 raised first and returned, and invariant 2 never executed. A real
known-bad case trips several guards at once, and the first one to raise hides
the rest.

A synthetic input can fail exactly one guard. That is the whole point:

    a guard is not validated until a synthetic input has made it fire
    IN ISOLATION, with every other guard in the chain passing.

That property is also the only automatic detector of the unreachability defect
this file was written in response to. `test_guard_coverage.py` resolves whether
a guard is CALLED; it cannot see that a called guard sits after another guard's
raise. A synthetic case that must make invariant 2 and only invariant 2 fire
does see it -- under the old fail-fast chain the case below reports invariant 1
failing too, and the test rejects it.

THE SYNTHETIC MESH

A tetrahedralised ball with an analytic field, built in numpy. No solve, no
SimNIBS, no MIDA geometry, so this runs in seconds in the plain venv and is
safe to put in front of every production run.

  - MONOPOLE at the centre: E = k r_hat / r^2, uniform sigma. Flux through any
    enclosing surface is 4 pi sigma k, INDEPENDENT OF RADIUS, so invariant 1
    passes exactly. But a monopole means net current through the outer boundary
    equals the source current, which is NOT zero, so invariant 2 must fire.
    This is Carl's specification: radius-stationary flux AND nonzero net
    outer-boundary current, with no solve.

  - DIPOLE (source + sink inside the ball): flux far from both nets to zero, so
    invariant 2 passes. Used as the all-clean control.

    python src/test_guards_fire.py
    python src/test_guards_fire.py --strict     # non-zero exit blocks a run
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

import numpy as np
from scipy.spatial import Delaunay, cKDTree

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config              # noqa: E402
import preflight           # noqa: E402
import solve_invariants as SI  # noqa: E402

SIGMA = 0.35           # S/m, uniform; a plausible muscle value, nothing hangs on it
TAG = 63               # any tag present in the conductivity map
BALL_R = 90.0          # mm
INJ = config.INJECTION_CURRENT_A


# ----------------------------------------------------------------------
# A duck-typed mesh, matching only the surface the invariants actually touch
# ----------------------------------------------------------------------
class _Elm:
    def __init__(self, node_number_list, tag1):
        self.node_number_list = node_number_list          # 1-based, (n,4)
        self.tag1 = tag1
        self.elm_type = np.full(len(tag1), 4, dtype=int)


class _Nodes:
    def __init__(self, coord):
        self.node_coord = coord


class _Field:
    def __init__(self, value):
        self.value = value


class SyntheticMesh:
    """The subset of the SimNIBS mesh API that solve_invariants uses.

    Implemented against what the code calls, not against the full class: nodes,
    elements, tags, a vector E, element volumes, and nearest-element lookup.
    """

    def __init__(self, nodes, tets, tags, E):
        self.nodes = _Nodes(nodes)
        self.elm = _Elm(tets + 1, tags)
        self.field = {"E": _Field(E)}
        self._cent = nodes[tets].mean(axis=1)
        self._tree = cKDTree(self._cent)
        a = nodes[tets[:, 1]] - nodes[tets[:, 0]]
        b = nodes[tets[:, 2]] - nodes[tets[:, 0]]
        c = nodes[tets[:, 3]] - nodes[tets[:, 0]]
        self._vol = np.abs(np.einsum("ij,ij->i", a, np.cross(b, c))) / 6.0

    def elements_volumes_and_areas(self):
        return self._vol

    def find_closest_element(self, pts, return_index=True):
        _, idx = self._tree.query(np.atleast_2d(pts))
        return None, idx + 1                       # 1-based, as SimNIBS returns


def _ball(n=22000, radius=BALL_R, seed=0):
    """Tetrahedralised ball. Delaunay of a jittered lattice inside the sphere.

    A ball is used because the analytic monopole and dipole fields below are
    then EXACT, so every invariant has a closed-form expected value and a
    failure is unambiguously the guard's, not the harness's.
    """
    rng = np.random.default_rng(seed)
    k = int(np.ceil(n ** (1 / 3)))
    g = np.linspace(-radius, radius, k)
    P = np.stack(np.meshgrid(g, g, g, indexing="ij"), -1).reshape(-1, 3)
    P = P + rng.normal(0, radius / k * 0.25, P.shape)
    P = P[np.linalg.norm(P, axis=1) <= radius]
    # a shell of exact-radius points so the outer boundary is clean
    P = np.vstack([P, SI._fib_sphere(1500) * radius])
    tri = Delaunay(P)
    tets = tri.simplices
    cent = P[tets].mean(axis=1)
    return P, tets[np.linalg.norm(cent, axis=1) <= radius * 0.999]


def _monopole_field(cent, current_A, sigma=SIGMA):
    """E from a point source at the origin: J = I r_hat / (4 pi r^2)."""
    r = np.linalg.norm(cent, axis=1)
    r = np.maximum(r, 1e-6)
    rhat = cent / r[:, None]
    # r in mm -> m for the 1/r^2
    return (current_A / (4.0 * np.pi * sigma * (r * 1e-3) ** 2))[:, None] * rhat


SINK_Z = -80.0     # far enough that no patch radius in the scan encloses it


def _dipole_field(cent, current_A, sigma=SIGMA):
    """Source at the ORIGIN, sink at SINK_Z.

    The source sits at the patch centre and the sink is outside every radius in
    the scan, which is the real montage: one electrode inside the patch, the
    reference far away. The cut flux around the source is therefore +I at every
    radius (the sink contributes zero net through a surface not enclosing it),
    giving a perfect plateau at 1.0. The outer shell encloses BOTH, so
    invariant 2 nets to zero.
    """
    out = np.zeros_like(cent)
    for sign, z in ((+1.0, 0.0), (-1.0, SINK_Z)):
        d = cent - np.array([0.0, 0.0, z])
        r = np.maximum(np.linalg.norm(d, axis=1), 1e-6)
        out += sign * (current_A / (4.0 * np.pi * sigma * (r * 1e-3) ** 2)
                       )[:, None] * (d / r[:, None])
    return out


def make_mesh(kind, scale=1.0, seed=0, tag_hole=False):
    P, tets = _ball(seed=seed)
    cent = P[tets].mean(axis=1)
    E = (_monopole_field(cent, INJ) if kind == "monopole"
         else _dipole_field(cent, INJ))
    tags = np.full(len(tets), TAG, dtype=int)
    if tag_hole:
        # Unmapped tag placed OUTSIDE every patch radius in the scan, so
        # patch_flux never touches it and only the outer shell does. Otherwise
        # patch_flux raises and the case would trip two guards.
        tags[np.linalg.norm(cent, axis=1) > 70.0] = 9999
    return SyntheticMesh(P, tets, tags, E * scale)


# ----------------------------------------------------------------------
# The cases. Each names the ONE guard it must fail.
# ----------------------------------------------------------------------
SIGMA_MAP = {TAG: SIGMA}


def _run_chain(m, shell_factor=None, sigma_map=None):
    """Run the invariant chain and return {guard_name: status}."""
    try:
        out = SI.check_solve_plateau(
            None, np.zeros(3), sigma_map or SIGMA_MAP, injected_A=INJ,
            radii=(25., 35., 45., 55., 65.), verbose=False, mesh=m,
            shell_factor=shell_factor)
        return {v.name: v.status for v in out["guards"]}, out
    except SI.GuardsFailed as e:
        return {v.name: v.status for v in e.verdicts}, None


def case_invariant_2_outer_net():
    """MONOPOLE: radius-stationary flux, but the domain does not conserve charge.

    Exactly the case Carl specified. Invariant 1 must PASS (the flux really is
    radius-independent) while invariant 2 FAILS (all the injected current
    crosses the outer boundary, because there is no sink).
    """
    return _run_chain(make_mesh("monopole")), "invariant_2_outer_net"


def case_invariant_1_plateau():
    """Flux that grows with radius: no stationary plateau.

    Built by scaling the dipole field by (1 + r/R), so the cut flux rises with
    the patch radius instead of holding. The median over the scan stays inside
    the magnitude band, so ONLY the plateau guard may fire.
    """
    P, tets = _ball()
    cent = P[tets].mean(axis=1)
    E = _dipole_field(cent, INJ)
    E = E * (0.7 + 0.9 * np.linalg.norm(cent, axis=1) / BALL_R)[:, None]
    m = SyntheticMesh(P, tets, np.full(len(tets), TAG, int), E)
    return _run_chain(m), "invariant_1_plateau"


def case_invariant_1_magnitude():
    """DIPOLE scaled 0.2x: perfect plateau, outer net still zero, but only a
    fifth of the requested current is delivered.

    A uniform scale error leaves the plateau exactly stationary and leaves the
    outer net at zero, so this is the only per-solve guard that sees it.

    Scaled DOWN rather than up, deliberately. At 5x the case also trips
    invariant 2, and not for a physical reason: invariant 2's residual is
    proportional to the field, so multiplying E by 5 multiplies a residual that
    was comfortably inside tolerance into one that is outside it. That is worth
    knowing on its own -- invariant 2 is not scale-invariant, and a large
    enough scale error trips it through numerical amplification rather than
    through charge conservation -- but it makes 5x useless as an isolation
    test, because two guards firing cannot tell you either one works.
    """
    return _run_chain(make_mesh("dipole", scale=0.2)), "invariant_1_magnitude"


def case_invariant_2_coverage():
    """Push the shell out until it escapes the conductor entirely.

    This is the MIDA measurement reproduced synthetically. On the real mesh,
    raising the multiplier from 1.05 to 1.30 takes coverage 5.35% -> 0.00% and
    the net to exactly +0.000000, which the net tolerance reads as 'charge is
    conserved'. The field here is the clean dipole, so nothing is wrong with
    the solve at all: the only thing that fails is that the integral has no
    support, and that must be reported as such rather than as a pass.
    """
    return (_run_chain(make_mesh("dipole"), shell_factor=1.6),
            "invariant_2_coverage")


def case_unknown_tag():
    """A mesh tag with no conductivity in the analysis map.

    Two ways this goes wrong silently, and the project hit both: points are
    zeroed (a shell that is half unmapped reads as one through which little
    current flows), or -- if the tag lands in 100-899 -- `with_electrode_tags`
    fills it in as electrode material. Tag 200 became 29.4 S/m rubber that way.

    The tag is placed OUTSIDE every patch radius in the scan so that
    `patch_flux` never touches it and only the map-coverage guard fires.
    """
    return _run_chain(make_mesh("dipole", tag_hole=True)), \
        "conductivity_map_covers_mesh"


def case_all_clean():
    """DIPOLE at 1x: every guard must pass. The control that proves the cases
    above fail for their stated reason and not because the harness is broken."""
    return _run_chain(make_mesh("dipole")), None


# ---- guards outside the invariant chain, checked directly ----------------

def case_conductivity_span():
    """preflight.check_conductivity_range on the measured 1.879e15 failure."""
    try:
        preflight.check_conductivity_range([1e-15, 1.879], label="synthetic")
        return False, "no raise on a 1.879e15 span"
    except ValueError as e:
        return ("conductivity span" in str(e)), str(e)[:90]


def case_conductivity_span_clean():
    """...and passes on the span that actually worked (1.879e6)."""
    try:
        preflight.check_conductivity_range([1e-6, 1.879], label="synthetic")
        return True, "1.879e6 span accepted"
    except ValueError as e:
        return False, f"false positive on a known-good span: {e}"


def case_read_calibration_parse():
    """read_calibration must return the ERROR (11.90), not the THRESHOLD (10).

    The line reads '...exceeded 10%! Estimated error value: 11.90%', so a naive
    first-percentage match returns 10 and every solve looks identically bad.
    """
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "fields_summary.txt").write_text(
            "some header\n"
            "The current calibration error exceeded 10%! "
            "Estimated error value: 11.90%\n")
        got = preflight.read_calibration(p)
        return (got == 11.90), f"parsed {got!r}, expected 11.90"


def case_read_calibration_clean():
    """...and returns None, not 0.0, when the solver printed no warning."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "fields_summary.txt").write_text("no warning here\n")
        got = preflight.read_calibration(p)
        return (got is None), f"parsed {got!r}, expected None"


def case_linearity():
    """Invariant 3 on a pair that is 2.5x, not 2x."""
    P, tets = _ball()
    cent = P[tets].mean(axis=1)
    E = _dipole_field(cent, INJ)
    pts = cent[:500]
    a = SyntheticMesh(P, tets, np.full(len(tets), TAG, int), E)
    b = SyntheticMesh(P, tets, np.full(len(tets), TAG, int), E * 2.5)
    worst, same, note = SI._check_linearity_fields(a, b, pts)
    # 2.5x instead of 2x is a 25% deviation. Reported, not gated.
    return (abs(worst - 0.25) < 1e-9 and same), \
        f"worst {worst:.3e} (expect 2.5e-01), same_mesh={same} — {note}"


def case_reciprocity():
    """Invariant 4 on a pair that is not exactly negated."""
    P, tets = _ball()
    cent = P[tets].mean(axis=1)
    E = _dipole_field(cent, INJ)
    pts = cent[:500]
    a = SyntheticMesh(P, tets, np.full(len(tets), TAG, int), E)
    b = SyntheticMesh(P, tets, np.full(len(tets), TAG, int), -E * 1.01)
    worst, same, note = SI._check_reciprocity_fields(a, b, pts)
    # -1.01x leaves a 1% residual. Reported, not gated.
    return (abs(worst - 0.01) < 1e-9 and same), \
        f"worst {worst:.3e} (expect 1.0e-02), same_mesh={same} — {note}"


CHAIN_CASES = [
    ("invariant 2 fires alone (monopole: stationary flux, unconserved charge)",
     case_invariant_2_outer_net),
    ("invariant 1 plateau fires alone (flux rising with radius)",
     case_invariant_1_plateau),
    ("invariant 1 magnitude fires alone (0.2x uniform scale, plateau intact)",
     case_invariant_1_magnitude),
    ("invariant 2 coverage fires alone (shell escapes the mesh)",
     case_invariant_2_coverage),
    ("map-coverage guard fires alone (mesh tag with no conductivity)",
     case_unknown_tag),
    ("control: every guard passes on a clean dipole", case_all_clean),
]

DIRECT_CASES = [
    ("conductivity span gate fires on 1.879e15", case_conductivity_span),
    ("conductivity span gate passes on 1.879e6", case_conductivity_span_clean),
    ("read_calibration parses 11.90, not the 10 threshold",
     case_read_calibration_parse),
    ("read_calibration returns None on a clean solve",
     case_read_calibration_clean),
    ("invariant 3 measures 0.25 on a 2.5x pair", case_linearity),
    ("invariant 4 measures 0.01 on a -1.01x pair", case_reciprocity),
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="test_guards_fire.py")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args(argv)

    print("PER-GUARD SYNTHETIC TESTS")
    print("=" * 72)
    print("Each case must fail exactly ONE guard, with every other guard in")
    print("the chain passing. A case that trips two guards cannot tell you")
    print("which one works.\n")

    failures = []

    for label, fn in CHAIN_CASES:
        (statuses, _), expect = fn()
        fired = sorted(k for k, v in statuses.items() if v != "pass")
        if expect is None:
            ok = not fired
            detail = "all passed" if ok else f"unexpectedly fired: {fired}"
        else:
            ok = fired == [expect]
            detail = (f"fired exactly {expect}" if ok else
                      f"expected [{expect}], got {fired}")
        print(f"  {'PASS' if ok else 'FAIL'}  {label}\n        {detail}")
        if not ok:
            failures.append(label)

    print()
    for label, fn in DIRECT_CASES:
        ok, detail = fn()
        print(f"  {'PASS' if ok else 'FAIL'}  {label}\n        {detail}")
        if not ok:
            failures.append(label)

    print()
    print("=" * 72)
    if failures:
        print(f"  FAILED — {len(failures)} guard(s) not demonstrated:")
        for f in failures:
            print(f"      {f}")
        print()
        print("  A guard that cannot be made to fire in isolation is either")
        print("  unreachable, or masked by an earlier guard's raise, or not")
        print("  measuring what its name says. All three have happened here.")
        print("=" * 72)
        return 1 if a.strict else 0
    print("  PASSED — every guard fired on a synthetic input that fails it")
    print("  and nothing else, and the clean control tripped none of them.")
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
