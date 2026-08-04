# SimNIBS issue — current-calibration check on a custom mesh

**Status: FILED 2026-08-03 as https://github.com/simnibs/simnibs/issues/665.**

Rewritten and measured before filing. The previous draft was withdrawn for
asserting something false and is superseded; see the note at the end. The
filed body is this file from `## Body` down, excluding that note.

---

## Title

Current-calibration error ranks solves in the opposite order to an independent
measurement of delivered current (custom MIDA mesh, SimNIBS 4.6.0)

## Body

### Summary

On a custom head mesh, `fields_summary.txt`'s current-calibration error does not
agree with an independent measurement of how much current each solve actually
delivered — and the disagreement is not noise. It is ordered the wrong way: the
solve with the **largest** true deviation is reported **clean**, and the solve
flagged **worst** is one of the more accurate in the set.

I am reporting the pattern rather than a p-value, because the pattern is what a
maintainer can act on.

### The two ends of the set

22 tDCS solves, 1 mA requested, one electrode against a common reference, on a
custom mesh built from the MIDA model (IT'IS Foundation) with per-label
conductivities. Delivered current measured independently for each (method
below).

| electrode | delivered current, measured | calibration line says |
|---|---|---|
| **`buccal`** | **0.8870 mA** — the largest deviation in all 22 | **no warning** |
| **`mental`** | **1.0746 mA** — closer to correct than `buccal` | **error 32.99%** |

Those are the extremes, and they are inverted. The middle behaves the same way:

- warned solves (n = 11) average **1.0113 mA**
- un-warned solves (n = 11) average **0.9428 mA**

The warned group is *closer* to the requested 1 mA than the silent group.

Across all 22, measured delivered current spans **0.887–1.075 mA** (implied
error 0.5–11.3%), while the calibration line reports 0% or 11.90–32.99%.

### Agreement between the two, stated with its tolerance

Counting a solve as "agreeing" when the reported error and the measured
deviation fall within **±5 percentage points**: **4 of 22**. That threshold is
a free parameter and the count is sensitive to it — 0 of 22 at ±3 pp, 2 at
±4 pp, 4 at ±5 pp, 9 at ±6 pp — so it should be read as "they rarely agree
closely", not as a statistic. The parameter-free version is the table above.

### Supporting, and deliberately not the headline

Spearman correlation between the reported calibration error and the measured
|deviation| is **−0.425, p = 0.048, n = 22** (Pearson −0.349, p = 0.111). A
marginal p on n = 22 is fragile and I am not resting anything on it; it is
included because the sign is informative. The two extreme cases above do not
need it.

### How delivered current was measured

Surface integral of **J·n** = σ **E**·n̂ over a closed surface around the
injection electrode, using the **mesh's own tetrahedron faces** as the
quadrature rather than a sampled sphere:

1. Take all tets whose centroid is within radius *r* of the electrode centre.
2. Take that patch's boundary faces (multiplicity 1 within the patch), oriented
   outward by the opposing vertex.
3. Split them by multiplicity in the **full** mesh: 2 = an interior cut, 1 = a
   face on the mesh exterior.
4. Integrate σ **E**·n̂ over the **interior cut only**.

Step 4 matters. SimNIBS imposes the injection as a Dirichlet condition on the
electrode's exterior surface, not as a volumetric source, so a patch around the
electrode contains no source: current enters through the exterior face and
leaves through the cut, and the *net* over the closed patch is ~0. Measured on
one solve: +0.968 out through the cut, −0.938 in through the exterior. The
quantity equal to the injected current is the cut flux.

Repeated over r = 25, 35, 45, 55, 65, 75 mm; a stationary plateau is required
before the value is used. Enclosure and orientation are exact by construction
(the patch surface closes to 1.2e-16 of its own area) and there is no
inside/outside point test.

### What is and is not validated about that measurement

Being explicit, because it bounds the claim:

- **Radius-consistency is validated.** Plateau CV is under 0.7% on every
  four-layer analytic-sphere mesh density tested, and 0.49% on the head mesh.
- **The forward setup is validated** against the analytic multilayer sphere:
  RDM median 4.36%, MAG median +4.40% over 120 sources.
- **The absolute level is NOT independently established.** On the sphere the
  same integral reads 0.9406 / 1.2481 / 1.1134 across three mesh densities —
  non-monotone in element size and changing sign, most plausibly from electrode
  meshing rather than volume discretisation. That is unresolved at my end.

So I am **not** claiming "every solve delivers within 11.3% and SimNIBS is
wrong about the magnitude". I am claiming the **ordering** disagrees, and that
claim is immune to a common multiplicative offset: a per-realisation scale
factor shifts every solve together and cannot invert a ranking. The `buccal`
vs `mental` inversion and the warned-vs-un-warned means both survive it.

### One more thing, possibly the cause

Every one of these summaries also contains:

    Cannot locate subjects m2m folder
    some postprocessing options might fail

These meshes are built with `meshmesh` and custom per-label conductivities;
there is no m2m folder and no `charm` run behind them. If the calibration
estimate depends on anything resolved from m2m, that would explain both the
false positives and why they are uncorrelated with the real error. A separate
observation consistent with this: on a **four-layer analytic sphere**, where the
solution can be checked against the closed form, 5 of 16 solves emitted the
calibration warning while matching the analytic oracle at RDM 4.36% — i.e. the
warning fired on solves that were demonstrably correct.

### What would help, independent of the above

1. **Warn at setup when `max(σ)/min(σ)` over assigned tags is extreme.** A span
   of 1.879e15 (from assigning air 1e-15) broke every solve here — fields
   10–20× too large — and there is no warning for it at any stage. That
   conditioning failure *did* produce a calibration warning (200.00%), so the
   check catches it, but only after a full solve. 1.879e6 is clean.
2. **Expose the iterative solver's residual and iteration count.** `hypre`
   surfaces neither through this path, so the binary calibration line is the
   only convergence signal available, with no severity and nothing to trend.
3. **Document what the calibration estimate is computed from**, and whether it
   is meaningful without an m2m folder. If it is not, saying so in the summary
   would be enough — the line currently reads as a physical measurement.

### Environment

SimNIBS 4.6.0, macOS (Apple Silicon, native), Python 3.11. Custom mesh, ~15.4M
tetrahedra, 118 conductivity labels, 10 mm ellipse electrodes, 2 mm thickness,
`fields = "E"`.

Happy to supply the 22-row table (electrode, reported calibration, measured
delivered current) or the integration code if useful. The mesh itself is
MIDA-derived and licensed by the IT'IS Foundation, so I cannot attach it.

---

## Note on the previous draft — kept, not deleted

The earlier version of this file claimed the check "emits exactly 200.00% on
custom meshes because it cannot locate the m2m folder, while the actual failure
mode goes undetected". **That was false and was never filed.** On the
conditioning failure the check behaved correctly: it fired on the broken solve
and stayed silent on the good one.

That draft was then withdrawn with the conclusion that the check works and the
error was mine for not reading `fields_summary.txt`. **That conclusion was also
wrong**, and it is what this version replaces. The withdrawal was an argument,
not a measurement; the tet-patch integral above is the measurement, and it
disagrees with the check on ordering. Both the original overclaim and its
retraction are recorded in `METHODS_LOG.md` under "the double reversal".

What survived unchanged from the first draft: the false-positive observation on
the analytic sphere, and suggestions 1 and 2.
