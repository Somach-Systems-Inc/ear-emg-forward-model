# SimNIBS issue — DRAFT, NOT FILED

**Held back because the premise it was authorised on turned out to be false.**

## What was believed when filing was approved

That the current-calibration check "emits exactly 200.00% on custom meshes
because it cannot locate the m2m folder, while the actual failure mode ...
goes undetected."

## What is actually true

| Case | conductivity span | calibration line | solve correct? |
|---|---|---|---|
| MIDA, air 1e-15 | 1.879e15 | **200.00%** | no, fields 10-20x too large |
| MIDA, air 1e-6 | 1.879e6 | **no warning** | yes |
| Sphere (4 layers) | 2.5e2 | warning on **5 of 16** | yes, matched analytic oracle |

**On MIDA the check worked correctly.** It fired on the broken solve and stayed
silent on the good one. It was not constant, and it did not miss the failure.

The failure was mine: I did not read `fields_summary.txt`. SimNIBS detected the
problem and reported it in writing, and I took the field values anyway.

## What remains, and it is much weaker

A false-positive rate on well-conditioned custom meshes: 5 of 16 sphere solves
emitted the warning while agreeing with the analytic multilayer-sphere solution
at RDM 4.36%. Together with `Cannot locate subjects m2m folder` in the same
summaries, that suggests the check degrades without an m2m folder — but it
degrades toward false alarms, not toward silence.

Two suggestions would still stand on their own merits:

1. Warn at setup when `max(sigma)/min(sigma)` across assigned tags exceeds
   ~1e8. This is the condition that actually broke the solve, and there is
   currently no warning for it at any stage.
2. Expose the iterative solver's residual and iteration count. `hypre` surfaces
   neither, so the binary calibration line is the only convergence signal.

## Recommendation

**Do not file as drafted.** The headline claim is wrong. If anything is filed
it should be the narrow false-positive report plus the two suggestions above,
and it should not assert that the real failure went undetected — it did not.
