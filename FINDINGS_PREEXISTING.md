# Pre-existing findings

Defects found in `main` at `f633865` while porting this pipeline to Windows.
**None of these were introduced by the port.** Each was verified to be present in
the committed tree before anything was changed — by reading `git show HEAD:<path>`
or by running the check against `HEAD`'s copy of the file, never against a
worktree that a live process might have rewritten underneath the reader.

Ordered by consequence.

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

## 5. `meshmesh` is not deterministic, and the convergence inputs carry unquantified noise

Two runs of the **same command on the same machine** produce different meshes and
different metrics:

| run | tets | h_mean | RDM % | MAG % |
|---|---|---|---|---|
| A | 650,285 | 1.56236 | 3.8518 | +1.1510 |
| B | 649,176 | 1.56100 | 3.9568 | +3.8027 |
| Δ | −1,109 (−0.17 %) | −0.087 % | **+0.1049 pp** | **+2.6517 pp** |

Because `fine.ini` saturates to the medium density (finding 3), the `fine` row is
an independent realisation at essentially fixed density, which is what makes this
measurable at all.

Consequences:

- **`MAG` is dominated by mesh realisation.** A 2.65 pp swing at fixed density is
  the same order as the differences between densities. Any MAG comparison at or
  below this magnitude carries no information.
- **`RDM_0 = 2.0118 %` is quoted to four decimals from three inputs that each
  carry ~0.1 pp of mesh noise.** The 3-point fit is exact by construction, so it
  propagates that noise into `RDM_0` invisibly and reports a residual of ~1e-26
  that describes only the algebra, not the measurement.
- A repeat of any density is not a reproduction check unless the same `.msh` is
  reused; rebuilding the mesh changes the answer.

**Caveat on this finding:** n = 2. This is a single pairwise difference and a
lower bound on the spread, not a standard deviation. Establishing the real
distribution needs several rebuilds per density — which is also the cheapest way
to put an honest error bar on `RDM_0`.

**Not fixed here.** The remedy is a design decision for the authors: either pin
the mesh (ship or hash the `.msh` used for the published fit), or repeat each
density N times and quote `RDM_0` with an interval.

---

## 4. Mac-only paths in executable code

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
