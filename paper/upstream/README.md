# Follow-up for simnibs/simnibs discussions/666

**NOTHING HERE HAS BEEN POSTED. Carl posts, not an agent.**
**Post after `both_electrode_flux.py` completes all 22 solves** — the table
below is the confirmation leg and should go up complete, not at n = 4.

The maintainer's correction is accepted in full. Reported calibration is
`e = 2|a−b|/(a+b)` over the two electrode-interface flux estimates, after which
the solution is scaled so `mean(a,b)` equals the requested current. Our issue
**#665 is wrong and needs correcting, not defending**: it compared that
interface-consistency measure against a delivered-current measure, which are
different physical quantities.

What follows replaces it, and it is a **physics argument that needs no data.**

---

## The argument

Take a two-electrode montage on a domain whose boundary is insulating
everywhere except at the two electrodes. Let `S` be any closed surface
enclosing electrode A and not electrode B. Charge conservation gives

    ∮_S J·n dA  =  I_A

for **every** such surface — at the electrode interface, at 25 mm, at 75 mm —
because no source lies between them. The same holds around B with `I_B = −I_A`.

**So the true interface fluxes at A and B are equal in magnitude, identically,
not approximately.** There is no physical asymmetry for a calibration error to
measure.

A reported `e = 19.67%` means the solver's two estimates satisfy `a = 1.098`,
`b = 0.902` — they **differ by 21.8% of the smaller**. Conservation forbids
that difference in this configuration. It follows that

> **in a two-electrode insulating-boundary montage, a nonzero
> current-calibration error is by construction an error in the interface-flux
> ESTIMATOR, not a physical asymmetry. The asymmetry it purports to measure
> cannot exist.**

This is why the check is still worth having — it is a genuine numerical
diagnostic, and it correctly caught both of our real solver failures (below).
But its magnitude cannot be read as "how unbalanced the electrodes are",
because that quantity is zero by construction.

Worked, for the values we see: reported 11.90% ⇒ estimates differ by 12.7%;
19.67% ⇒ 21.8%; 32.99% ⇒ 39.5%.

**Note what this argument does NOT depend on.** It makes no use of our own
integral's absolute level, which we cannot pin down better than ±28% (see the
method section). It is entirely about SimNIBS's two estimates disagreeing with
*each other*, and conservation settles that independently of any measurement of
ours.

---

## The confirmation: is the premise actually satisfied?

The argument holds only if the boundary really is insulating and there is no
third current path. That is an empirical question about our mesh, and it is
what the 22-solve table answers.

We integrate `J·n = σE·n̂` over a closed surface around **each** electrode,
using the mesh's own tetrahedron faces as the quadrature (method below), at
radii 25–75 mm. If the premise holds, the two must come out equal and opposite.

| electrode | SimNIBS reports | flux around active | flux around reference | recomputed `2\|a−b\|/(a+b)` |
|---|---|---|---|---|
| `above_ear` | clean | +0.9463 | −0.9458 | **0.06%** |
| `buccal` | clean | +0.8870 | −0.9038 | **1.87%** |
| `cg02` | clean | +0.9579 | −0.9566 | **0.13%** |
| **`cg01`** | **19.67%** | **+1.0055** | **−1.0069** | **0.14%** |

*(n = 4 of 22 at the time of writing — **complete this table before posting.**)*

The two fluxes agree to **0.14%** on `cg01`, the solve SimNIBS reports at
19.67%. So the premise is satisfied: the domain conserves charge, the boundary
is insulating, and there is no third path. The reported 19.67% is therefore an
estimator artefact by the argument above, and the table confirms rather than
establishes that.

Note also that our integral's absolute level sits at 0.946–1.006 rather than
1.000. That is our own ~5% low bias; it affects both electrodes identically and
cancels from the relative difference, which is why these percentages are usable
where our absolute numbers are not.

---

## Where this leaves the check

**Keep it — it works, and it caught things we would otherwise have shipped.**
Both of our real solver failures produce exact algebraic signatures, and both
check out:

| reading | requires | our case |
|---|---|---|
| **200.00%** | one interface flux exactly zero | `sigma_air = 1e-15`, a non-conducting return path |
| **~100%** | `a/b = 3.000000` | neck-extended mesh leaking through its inferior face; measured 100.49% and 95.84% back-solve to **3.020** and **2.840** |

In the leak case the premise genuinely fails — there *is* a third current path —
so the check is reading real physics there. That is the distinction worth
documenting: **the calibration error measures estimator noise when the boundary
is insulating, and real physics when it is not**, and nothing in the output
tells the user which regime they are in.

Three things that would help, in decreasing order of value:

1. **Say what the number means when the boundary is insulating.** A line in the
   docs, or in the warning itself, distinguishing "your estimator disagrees with
   itself" from "your domain is leaking", would have saved us three reversals.
2. **Warn at setup when `max(σ)/min(σ)` over assigned tags is extreme.** A span
   of 1.879e15 (air at 1e-15) broke every solve here with fields 10–20× too
   large. The check catches it, but only after a full solve. 1.879e6 is clean.
3. **Expose the iterative solver's residual and iteration count.** `hypre`
   surfaces neither through this path, so the calibration line is the only
   convergence signal available, with no severity and nothing to trend.

---

## Method for the table

Surface integral of `J·n = σE·n̂` over a closed surface around an electrode,
using the **mesh's own tetrahedron faces** as the quadrature rather than a
sampled sphere:

1. Take all tets whose centroid is within radius *r* of the electrode centre.
2. Take that patch's boundary faces (multiplicity 1 within the patch), oriented
   outward by the opposing vertex.
3. Split them by multiplicity in the **full** mesh: 2 = an interior cut, 1 = a
   face on the mesh exterior.
4. Integrate over the **interior cut only**.

Step 4 matters: SimNIBS imposes the injection as a Dirichlet condition on the
electrode's exterior surface, not as a volumetric source, so a patch around the
electrode contains no source — current enters through the exterior face and
leaves through the cut, and the *net* over the closed patch is ~0. Measured on
one solve: +0.968 out through the cut, −0.938 in through the exterior.

Repeated over r = 25, 35, 45, 55, 65, 75 mm; a stationary plateau is required
before the value is used. Enclosure and orientation are exact by construction
(the patch surface closes to 1.2e-16 of its own area) and there is no
inside/outside point test.

**What is and is not validated about it.** Radius-consistency is: plateau CV is
under 0.7% on every analytic-sphere density tested and 0.49% on the head mesh.
The forward setup is: RDM median 4.36%, MAG median +4.40% over 120 sources
against the analytic multilayer sphere. **The absolute level is not** — the same
integral reads 0.9406 / 1.2481 / 1.1134 across three sphere densities, a spread
of 28% of its own mean, non-monotone and sign-changing. None of the argument
above rests on it.

---

## Artifacts

| # | file | status |
|---|---|---|
| a | `interface_fluxes_derived.csv` | **DERIVED, not raw.** `fields_summary.txt` prints only the percentage, so `a` and `b` are reconstructed as `1 ± e/2`. Emitting the raw pair would be a small, useful feature request. |
| b | `both_electrode_flux.py`, `both_electrode_flux.csv` | the confirmation table above. ~10 min/electrode on a 15.4M-element mesh. |
| c | `tet_patch_standalone.py` | standalone, runnable, no project imports |
| d | **four-layer analytic sphere** | **highest value, fully shareable** — not MIDA-derived, no licence constraint. `data/val_sphere.nii.gz`, `src/val_rdm_mag.py`, `sphere_calibration_per_solve.csv`. **5 of 16 solves emit the warning while the lead fields match the closed form at RDM 4.36%.** |

**On (d): it is the clean test of the argument.** A symmetric four-layer sphere
with identical electrodes has an exact solution, an insulating boundary and no
third current path, so the true interface fluxes are provably equal. Any nonzero
calibration error there is unambiguously estimator error, with a closed-form
reference to measure it against. That is where the 11–15% could actually be
characterised.

---

## Note on the previous drafts — kept, not deleted

The first draft claimed the check "emits exactly 200.00% on custom meshes
because it cannot locate the m2m folder, while the actual failure mode goes
undetected". **False, and never posted.** The maintainer has since confirmed the
calibration path uses only mesh, conductivities, electrode tags, scalp tags and
potentials — the m2m message is unrelated.

That draft was withdrawn on the reasoning that the check works and the error was
ours for not reading `fields_summary.txt`. **Also wrong**, and it became #665,
which claimed an anti-correlation with delivered current. That anti-correlation
was an artifact of taking `abs()` of a signed deviation: against the *signed*
value the same data gives Spearman **+0.932**, p < 1e-5, which is what the
maintainer's model predicts.

Three reversals on one check, all of them downstream of not knowing what it
computed. Recorded in `paper/METHODS_LOG.md`.
