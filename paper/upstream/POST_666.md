Thank you — that is the piece we were missing, and it settles it. Reported
calibration is `e = 2|a−b|/(a+b)` over the two interface flux estimates, with
the solution then scaled so `mean(a,b)` is the requested current, so each
interface sits `e/2` from it. **Our #665 is wrong and I will correct it**: it
compared that interface-consistency measure against a delivered-current
measure, which are different quantities, and the "anti-correlation" it reported
was an artifact of an `abs()` on our side (details at the end).

Having understood what the number is, there is a narrower point that I think is
still worth raising, and it needs no data from us.

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

| electrode | SimNIBS reports | flux around active | flux around reference | measured asymmetry `2\|a−b\|/(a+b)` |
|---|---|---|---|---|
| `mental` | **32.99%** | +1.0746 | -1.0684 | **0.58%** |
| `cg08` | **28.82%** | +1.0508 | -1.0488 | **0.19%** |
| `cg04` | **26.83%** | +1.0431 | -1.0397 | **0.33%** |
| `cg09` | **25.27%** | +1.0296 | -1.0325 | **0.29%** |
| `post_lobule` | **21.24%** | +1.0134 | -1.0140 | **0.06%** |
| `cg01` | **19.67%** | +1.0055 | -1.0069 | **0.14%** |
| `earlobe_ipsi` | **17.03%** | +0.9887 | -0.9948 | **0.61%** |
| `cg06` | **15.57%** | +0.9841 | -0.9880 | **0.39%** |
| `cg03` | **13.99%** | +0.9812 | -0.9808 | **0.04%** |
| `submental_mid` | **13.65%** | +0.9864 | -0.9820 | **0.45%** |
| `cg10` | **11.90%** | +0.9671 | -0.9712 | **0.43%** |
| `buccal` | clean | +0.8870 | -0.9038 | **1.87%** |
| `cg07` | clean | +0.9619 | -0.9575 | **0.46%** |
| `hyoid` | clean | +0.9606 | -0.9569 | **0.38%** |
| `mastoid` | clean | +0.9420 | -0.9363 | **0.60%** |
| `cg05` | clean | +0.9452 | -0.9448 | **0.04%** |
| `midjaw` | clean | +0.9461 | -0.9455 | **0.07%** |
| `cg02` | clean | +0.9579 | -0.9566 | **0.13%** |
| `pre_tragus` | clean | +0.9210 | -0.9227 | **0.19%** |
| `submaxillary` | clean | +0.9431 | -0.9332 | **1.06%** |
| `submental_lat` | clean | +0.9593 | -0.9527 | **0.68%** |
| `above_ear` | clean | +0.9463 | -0.9458 | **0.06%** |

**All 22 solves. The measured interface asymmetry is 0.04–1.87% on every one of
them**, while SimNIBS reports 11.90–32.99% on eleven. The premise is satisfied
throughout: the domain conserves charge, the boundary is insulating, there is
no third current path, and the true asymmetry the calibration number purports
to measure is — as the argument requires — zero to within our quadrature noise.

The two quantities are **completely decoupled**:

| | |
|---|---|
| Spearman(reported, measured) | **−0.086, p = 0.703, n = 22** |
| reported ÷ measured, on warned solves | **28× to 384×** (median 81×) |
| mean measured asymmetry, warned solves | **0.32%** |
| mean measured asymmetry, clean solves | **0.50%** |

The warned solves are, if anything, *more* internally consistent than the clean
ones. And the extremes invert cleanly: **`buccal` has the largest measured
asymmetry in the set at 1.87% and is reported clean**, while **`mental` is
reported at 32.99% and measures 0.58%** — a factor of 57 apart in the opposite
direction.

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

## Attached

| file | what it is |
|---|---|
| `both_electrode_flux.csv` | the 22-solve table above, raw |
| `both_electrode_flux.py` | the script that produced it |
| `tet_patch_standalone.py` | the flux integral on its own, no project imports — `patch_flux(mesh, centre, radius, sigma_by_tag)` |
| `interface_fluxes_derived.csv` | your reported `e` per solve with `a`, `b` reconstructed as `1 ± e/2`. **Derived, not raw** — `fields_summary.txt` prints only the percentage. Emitting the raw pair would be a small and useful addition. |
| `sphere_calibration_per_solve.csv` | the sphere case, per solve |

**The sphere case is the one I'd point you at.** It is a four-layer analytic
sphere — not derived from any licensed model, so I can share the whole thing
including the mesh if useful. Symmetric, identical electrodes, insulating
boundary, no third current path, and a closed-form solution. The true interface
fluxes are provably equal there, so any nonzero calibration error is
unambiguously estimator error with an exact reference to measure it against.
**5 of 16 solves emit the warning while the lead fields match the closed form at
RDM median 4.36%.** That is where the 11–15% could actually be characterised,
and it should reproduce on your side in minutes.

---

## On our previous framing

Our first draft claimed the check "emits exactly 200.00% on custom meshes
because it cannot locate the m2m folder, while the actual failure mode goes
undetected". **False, and never filed.** The maintainer has since confirmed the
calibration path uses only mesh, conductivities, electrode tags, scalp tags and
potentials — the m2m message is unrelated.

We withdrew that on the reasoning that the check works and the error was
ours for not reading `fields_summary.txt`. **Also wrong**, and it became #665,
which claimed an anti-correlation with delivered current. That anti-correlation
was an artifact of taking `abs()` of a signed deviation: against the *signed*
value the same data gives Spearman **+0.932**, p < 1e-5, which is what your
description predicts.

Three reversals on one check, all of them downstream of not knowing what it
computed. Happy to share the full record if it is useful.
