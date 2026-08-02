# Methods log

Decisions, specification defects and non-obvious tool behaviour, recorded as
they happen. Kept because the corrections here are often more instructive than
the original plans, and because a defect that is not written down gets paid for
twice.

Distinct from OUTLINE.md, which holds the paper's argument. This holds the
process.

---

## 2026-08-02 — SPEC DEFECT (mine, Carl): interface-proximity test was collinear by construction

**Requested:** measure forward error against source-to-interface distance on
the concentric validation sphere, to set an error envelope for sensitivity
values near compartment surfaces.

**Defect:** on a concentric sphere a source at radius *r* is at distance
(78 − *r*) mm from the innermost interface **by construction**. Distance to
interface and eccentricity are perfectly collinear, so no regression on that
geometry can separate them. The measurement came out backwards from the
hypothesis — RDM *fell* toward the interface, correlation +0.676 with distance —
which is what exposed it. That is the well-known degradation of forward
solutions for deep central sources, wearing the wrong label.

**Correction:** hold source radius fixed (~50 mm) and vary the *layer boundary*
radius (55, 60, 65, 70 mm). Interface distance varies, eccentricity is
constant, the geometry stays concentric so the analytic oracle still applies.
Preferred over an eccentric inclusion or a self-converged head reference, both
of which trade an exact oracle for an approximate one.

**Recorded as a specification defect, not a result.** The requested experiment
could not have answered the question asked of it.

---

## 2026-08-02 — TOOL BEHAVIOUR: `meshmesh` element-size range does not override the label-volume floor

**Cost:** one full convergence run (48 solves) that produced two densities
instead of three.

Asking for `elem_sizes = {"standard": {"range": [0.8, 2.5]}}` on a 0.5 mm label
volume produced a mesh **0.13% larger** than the default-range mesh, at
identical element size (648,170 vs 647,323 tets; h_mean 1.676 vs 1.677 mm).

Element size is floored by two things the size range does not override:

1. the **label volume resolution** — 0.5 mm voxels cannot support sub-millimetre
   tetrahedra faithfully
2. **MMG's remeshing pass**, which runs after CGAL and renormalises element
   sizes (visible as `Tetraedras after remeshing run 1/2` in the log)

**Consequences.** To refine, refine the *label volume* (or use
`--voxsize_meshing`), not the size range. To coarsen, the size range works
fine — which is why the three-density study is being completed by adding a
**coarser** density rather than a finer one, sidestepping the floor entirely at
the cost of one cheap solve.

**Check before trusting any density request:** compare `h_mean` between meshes,
never the requested range. Two meshes with the same `h_mean` are the same
experiment run twice.

---

## 2026-08-02 — MEASUREMENT: electrode meshing is per-site noise, not global scale

Two statistically identical sphere meshes (0.13% apart in element count) gave
MAG differing by **5.06 percentage points** and RDM by 0.54. Electrode contact
area is realised from incidental surface triangulation, so it changes
discontinuously when surface triangles move.

**This does not cancel in ratios.** Each electrode's contact is realised
independently, so the term is per-site noise rather than a global scale factor,
and it propagates into every site-to-site comparison the paper makes.
5.06% = 20·log₁₀(1.0506) = **0.43 dB**.

Two things follow. It sets the **resolution floor for the channel-redundancy
analysis**, where differences between adjacent sites may be smaller than the
noise. And it sits only ~2.3x below the boundary run's 1.0 dB decision
threshold, so a boundary shift under ~0.5 dB cannot be separated from meshing
noise by a single pair of solves.

---

## 2026-08-02 — RETRACTION: the +4.4% MAG figure

Reported as an accuracy figure before its repeatability was known. A nominally
identical mesh gives +9.5%. Withdrawn; MAG is not quotable at this precision
until the electrode confound is removed.

RDM is the more robust metric and carries the headline, with the caveat that
5.147 → 4.355 across two densities is **monotone decreasing across the two
available densities**, not a convergence demonstration. It does not become
"converged" until a rate is fitted across three genuine densities.
