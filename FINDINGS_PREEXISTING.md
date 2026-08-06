# Pre-existing findings

Defects found in `main` at `f633865` while porting this pipeline to Windows.
**None of these were introduced by the port.** Each was verified to be present in
the committed tree before anything was changed — by reading `git show HEAD:<path>`
or by running the check against `HEAD`'s copy of the file, never against a
worktree that a live process might have rewritten underneath the reader.

Ordered by consequence. **Finding 6 is a RETRACTION** — it was written up as a
finding, turned out to be something this repository had already measured and
corrected, and is kept as a record of how that happened rather than deleted.

---

## 1. A corrupted tissue name reaches Table 1

**`results/01_table1_conductivities.csv` and `paper/TABLE1_conductivities.csv`
contain `Skull Diplo<U+FFFD>` where MIDA's own lookup table says `Skull Diploë`.**

MIDA v1.0 ships `MIDA_v1.txt` in latin-1. Label 52 is `Skull Diploë`, where the
`ë` is the single byte `0xEB`. The committed artifacts instead carry the three
bytes `EF BF BD`, which is UTF-8 for U+FFFD REPLACEMENT CHARACTER. The character
was destroyed at generation time; this is not a display artifact.

| file | bytes at the accent | reads as |
|---|---|---|
| `data/MIDA_v1.0/MIDA_v1_voxels/MIDA_v1.txt` (source of truth) | `EB` | `Skull Diploë` |
| `results/01_label_inventory.csv` @ `f633865` | `EF BF BD` | `Skull Diplo<U+FFFD>` |
| `results/01_table1_conductivities.csv` @ `f633865` | `EF BF BD` | `Skull Diplo<U+FFFD>` |
| `paper/TABLE1_conductivities.csv` @ `f633865` | `EF BF BD` | `Skull Diplo<U+FFFD>` |

### Cause

`src/01_build_mesh.py`, `parse_lut()`:

```python
text = path.read_text(errors="replace")
```

No `encoding=`, so the platform default; and `errors="replace"` substitutes
U+FFFD rather than raising. On a UTF-8 platform the latin-1 `0xEB` is an invalid
start byte and is silently replaced. On a cp1252 platform it decodes correctly.

**The bug is platform-dependent and macOS-specific.** A tissue name is an
identity, and identities must not depend on which machine read them.

### Scope

Confined to those three CSVs. `PAPER1_full_manuscript.md` and every other
`.md` / `.tex` / `.bib` under `paper/` is clean — checked by scanning raw bytes
for `EF BF BD`, not by grepping for a rendered character.

### Fixed here

`parse_lut()` now reads bytes and decodes UTF-8 strictly, falling back to
latin-1 — which is total, every byte 0x00–0xFF maps to a character, so nothing
can be silently dropped. Nothing is ever replaced. Both inventory writers pin
`encoding="utf-8"` so the output no longer depends on the writing machine.

Verified: `parse_lut` on the real MIDA LUT returns `'Skull Diploë'`, 116 labels,
no U+FFFD. `results/01_label_inventory.csv` regenerated with the fix is valid
UTF-8 (`C3 AB`) and differs from the committed file by exactly one line.

### Still outstanding

**The two Table 1 artifacts are not fixed.** `build_table1.py` needs
`data/itis/itis_lf_v4.2_conductivity.csv` — the IT'IS LF v4.2 export, DOI
10.13099/VIP21000-04-2 — which is not in the repository and must come from the
IT'IS SQLite database. Table 1 cannot be regenerated without it. The code path is
fixed; the published artifacts still carry the bad character.

---

## 2. `test_no_hardcoded_geometry.py` fails on a clean checkout

The suite is red at `f633865`:

```
FAIL: hardcoded electrode geometry found:
   src/03d_cavity_solves.py:87: el.shape="ellipse"; el.dimensions=[10,10]; el.thickness=2
Use config.ELECTRODE_DIAMETER_MM.
```

Verified pre-existing: line 87 is byte-identical to `git show
HEAD:src/03d_cavity_solves.py`.

**Fixed here** using the idiom already at `src/03_leadfields.py:171`:
`el.dimensions = [config.ELECTRODE_DIAMETER_MM] * 2`. `ELECTRODE_DIAMETER_MM` is
`10.0`, so `[10, 10] == [config.ELECTRODE_DIAMETER_MM] * 2` — the change is
numerically identical and the test now passes.

---

## 3. A fourth convergence density exists and is excluded from the fit

`src/val_convergence_fit.py` hardcodes three densities:

```python
DENSITIES = [
    ("vcoarse", "vcoarse.csv", 2.957, 118_169),
    ("coarse",  "coarse.csv",  2.257, 265_620),
    ("medium",  "medium.csv",  1.677, 647_323),
]
```

But a complete `fine` run is committed: `results/convergence/fine.csv` (120
rows), `fine_fields.npz`, `fine.ini`, and 16 `fine/e*` solve directories.

The script then prints, as its own interpretation of the result:

> *NOT a confirmation: 3 points and 3 free parameters give an exact fit by
> construction (residual ~1e-26), so the fit cannot fail and carries no
> goodness-of-fit evidence. **A 4th density would test it.***

That 4th density's data is sitting unused in the same directory. The caveat is
correct about the fit; it is wrong that no 4th point exists.

Committed medians, including the excluded row:

| density | RDM median % | MAG median % | in `DENSITIES` |
|---|---|---|---|
| vcoarse | 6.0977 | +5.5282 | yes |
| coarse | 5.1472 | +22.0184 | yes |
| medium | 4.3552 | +4.4002 | yes |
| **fine** | **3.8125** | **+9.4637** | **no** |

**Not fixed here.** Adding `fine` to `DENSITIES` requires its `h_mean` and tet
count, which are properties of the mesh that was actually solved and are recorded
nowhere. Supplying them from a mesh rebuilt on a different machine would make a
mixed-provenance row — a Mac-measured RDM against a Windows-measured `h` — which
is exactly the kind of quietly-wrong input this repository's own rules are
written against. It needs the `h` and tet count from the Mac run that produced
`fine.csv`, or a full same-machine rebuild of all four.

Note also that `MAG` is **not** monotone across the committed densities
(+5.53 → +22.02 → +4.40 → +9.46), while RDM is (6.098 → 5.147 → 4.355 → 3.813).

### `fine.ini` does not actually produce a finer mesh

Attempting the 4-density rebuild surfaced why the 4th point is awkward. Built on
one machine from the repo's own `.ini` files:

| density | tets | h_mean mm |
|---|---|---|
| vcoarse | 120,792 | 2.8721 |
| coarse | 271,397 | 2.1726 |
| medium (default) | 649,176 | 1.5610 |
| **fine (`fine.ini`)** | **646,841** | **1.5566** |

`fine` is not finer than `medium` — it is marginally **coarser**, a refinement
ratio of 1.003. `fine.ini` requests `elem_sizes` `[0.8, 2.5]` against a 0.5 mm
label volume and saturates, exactly as `val_convergence_fit.py`'s docstring
already says: *"meshmesh's element-size range cannot refine below the
label-volume floor"*.

So `fine` is a **second sample at the medium density**, not a fourth density.
Fitting it as one is degenerate: two near-identical `h` with different RDM gives
`RDM_0 = -5.6 %` (unphysical), `p` pinned at its lower bound, and leave-one-out
swinging `p` between both bounds. Excluding `fine` from `DENSITIES` is therefore
defensible — but the reason is not recorded anywhere, and the data being present
invites exactly the mistake made here.

---

## 4. `test_guard_coverage.py --strict` fails on a clean checkout

The second red check at `f633865`. It names two solving scripts that run without
the guard chain:

```
  FAILED
    2 script(s) solve without their guards:

      03g_fat_swap.py
        MISSING: calibration (records the solver's own fields_summary.txt value)
        MISSING: invariants 1 and 2 (radius plateau, magnitude, charge conservation)
        MISSING: conductivity span gate (sigma_max/sigma_min)

      03h_homog_scalp.py
        MISSING: calibration
        MISSING: invariants 1 and 2
        MISSING: conductivity span gate
```

Verified pre-existing by running the check against a pristine `git archive main`
checkout, not the working tree. The only changes made here to either file are
one-word `encoding="utf-8"` additions.

This matters more than the geometry test in finding 2, because **both scripts
produce committed results that feed published analysis** — `results/03_fat_swap.csv`
and `results/03_homog_scalp.csv`, consumed downstream by
`04e_fat_contrast_statisticA.csv` and `04i_homog_scalp.csv`. Those solves ran
without the calibration readback that caught both of this project's real solver
failures (the σ_air 1e-15 conditioning failure at 200 %, and the neck-extended
mesh leaking at ~100 %), and without the σ-span gate that exists precisely
because an excessive span makes the iterative solver fail to converge *while
still writing a result file*.

Note the check itself is **not** defective: without `--strict` it prints FAILED
and returns 0, which is the same deliberate convention `preflight.py` uses and is
documented in its own docstring (`--strict  # non-zero exit blocks a run`).

**Not fixed here.** Wiring the invariants into two solve paths is substantive
work, not a mechanical edit: by this repository's own standard a guard is not
trusted until it has been shown to fire in isolation, so adding the calls without
also adding synthetic cases to `test_guards_fire.py` would produce exactly the
unproven green tick `CLAUDE.md` warns about. Either wire them in properly, or add
both scripts to `EXEMPT` with a reason that survives a reviewer — the same choice
the check's own output offers.

---

## 5. Mac-only paths in executable code

Three sites assumed a macOS layout and would fail anywhere else. All fixed here.

| file | was | now |
|---|---|---|
| `src/03d_cavity_solves.py:47` | `ROOT=Path("/Users/carl/CODELocalProjects/ear-emg-forward-model")` | `Path(__file__).resolve().parent.parent`, the idiom at `config.py:9` |
| `src/run_solves_parallel.py:26` | `Path.home()/"Applications/SimNIBS-4.6/bin/simnibs_python"` | `shutil.which()` first, then both platform defaults, mirroring `01_build_mesh.py` |
| `src/01_build_mesh.py` | `meshmesh` fallback checked only the macOS install path | also checks `~/SimNIBS-4.6/bin/meshmesh.cmd` |

The remaining `~/Applications/SimNIBS-4.6/...` references in other files are
docstrings, and are left alone.

**Not changed:** `run_solves_parallel.py` still carries `PEAK_RSS_GB = 10.8` and
`TOTAL_RAM_GB = 48.0`. Those are measurements from the machine that took them.
They should be re-measured per machine, not edited to taste.

---

## 6. RETRACTED — mesh-realisation noise is already measured, and better

**This was written up as a finding. It is not one. Retained as a correction
rather than deleted, because the way it went wrong is the useful part.**

The observation was real: two runs of the same command on the same machine give
different meshes and different metrics.

| run | tets | h_mean | RDM % | MAG % |
|---|---|---|---|---|
| A | 650,285 | 1.56236 | 3.8518 | +1.1510 |
| B | 649,176 | 1.56100 | 3.9568 | +3.8027 |
| Δ | −1,109 (−0.17 %) | −0.087 % | +0.1049 pp | **+2.6517 pp** |

The conclusion drawn from it — that this noise is unquantified and that `RDM_0`
inherits it invisibly — was **wrong**. This repository already:

- **names the phenomenon**: the *electrode-meshing floor*. `measure_electrode_floor.py`
  solves "two nominally-identical sphere meshes (0.13 % apart in element count)"
  and states plainly that the difference "is not physics: it is the electrode's
  contact geometry being realised differently by incidental surface triangulation".
- **made exactly this n=2 measurement**, got |ΔMAG| = 1.5198 pp → 0.1310 dB, and
  labelled it in the output file `# n = 2 (one difference, not a distribution)`.
- **superseded it** with `measure_floor_multidraw.py`: n = 6 draws, each a rigid
  rotation of electrodes *and* sources on one fixed mesh, so relative geometry is
  identical and any spread is realisation noise by construction.
- **publishes the result**: `results/electrode_meshing_floor.txt` holds 0.272 dB,
  per-site spread 0.12–0.49 dB, electrode-specific residual SD 3.181 pp, and
  records the median-MAG distribution's SD as **4.607 pp**.
- **guards the ordering**: `measure_electrode_floor.py` refuses to overwrite the
  n=6 file, because re-running the n=2 estimate "would quietly loosen every
  threshold the floor gates".
- **carries it into the paper**: `METHODS.md:203` tests a spread against "a
  0.27 dB electrode-meshing floor", and `METHODS_LOG.md` has a dated ruling on
  correcting it.

Against that, the measurement above is **one draw from a distribution whose SD is
already published as 4.607 pp**. |ΔMAG| = 2.65 pp is an unremarkable member of it.
It is a useful independent cross-platform corroboration — a different OS, compiler
and BLAS reproduce the same order of realisation noise — and nothing more.

### Why this is recorded

`CLAUDE.md` states the rule that was broken:

> **Verifying that a step is absent HERE does not verify that it is absent.**
> Check upstream before concluding a specification was not applied. […] Before
> reporting that a specification was not applied, name the file where it WOULD
> have been applied and show it is not there either.

The finding was written after observing the noise in `val_convergence_fit.py` and
`val_rdm_mag.py`, without grepping for an existing floor measurement. Two files
named `measure_electrode_floor.py` and `measure_floor_multidraw.py` sat in the
same directory. The repository had not only done the work, it had already made and
then corrected the precise mistake being reported — quoting an n=2 difference as
if it were a spread.

It was also, in `CLAUDE.md`'s words, "tidier than the truth": a clean story about
unquantified noise undermining a headline number is more interesting than
"independently reproduced a known floor", which is what actually happened.

---
