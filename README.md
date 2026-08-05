# Canonical jaw electrode sites outperform retroauricular sites for every resolvable speech articulator

A volume-conductor model with orientation and electrode-count controls, answering:
**which speech muscles can you actually see from behind the ear, and how much do
you lose versus the jaw?**

The answer is one-sided. Five articulators favour the jaw montage by 8.6 to
20.2 dB and no articulator robustly favours the ear once source orientation and
electrode count are controlled. Three that appeared to did not survive the
controls; §4.8 reports how that happened.

- **Human subjects:** none. No IRB required — state this explicitly in Methods.
- **Hardware:** none. Runs on the MacBook.
- **Blocked by:** nothing.

Read `paper/OUTLINE.md` first. It has the gap statement, the method, the figure plan, and the citations.

---

## Setup — do these in order

### 1. SimNIBS 4.6.0
**Native Apple Silicon** — Intel Mac support was discontinued at 4.5, so the M-series machine is the right one. Not needed for `--list-labels`; only from the mesh build onward.

**Use the official installer.** `simnibs_installer_macos.pkg` (849 MB) from
https://github.com/simnibs/simnibs/releases/tag/v4.6.0 — double-click, or:

```bash
sudo installer -pkg ~/Downloads/simnibs_installer_macos.pkg -target /
```

Signed by Axel Thielscher, notarized by Apple. Installs outside this repo and brings its own Python environment. Verify with `meshmesh -h`, then run a stock example before touching MIDA. If the reference example doesn't run, nothing downstream will.

<details>
<summary><b>Do not pip-install the wheel into a venv.</b> Tried and abandoned 2026-08-02 — how far it gets, and why it dies.</summary>

The release publishes `simnibs-4.6.0-cp311-cp311-macosx_11_0_arm64.whl` (184 MB, native arm64), which looks like a clean isolated install. It only resolves if you also hand pip the six dependencies from `environment_macos.yml` that are not on PyPI:

```
fmm3dpy 1.0.4 · cortech 0.1 · petsc4py 3.22.2 · samseg 0.5a0
brainnet@git+…@v0.2 · brainsynth@git+…@v0.1
```

That installs, and still does not work, for two reasons.

1. The CGAL extensions link `libmpfr.6` / `libgmp.10` / `libz.1` through `@rpath`, and the only baked-in rpath is the maintainer's build machine, `/Users/axelt/miniforge3/envs/simnibs_dev/lib`. Survivable: `brew install mpfr`, then `install_name_tool -add_rpath /opt/homebrew/lib` and an ad-hoc `codesign -f -s -` on three `.so` files.

2. Then `simnibs/__init__.py` imports the FEM module, which imports `mumps`. `python-mumps` is sdist-only on PyPI and needs a Fortran build against MUMPS; Homebrew has no `mumps` formula. This is where it ends, and it blocks even `meshmesh`, because the package's import chain pulls FEM in regardless of which CLI you invoke.

The binaries are built against one specific conda environment. The `.pkg` ships that environment. Reproducing it with Homebrew and pip is a losing game.
</details>

> **Stage 3 constraint, noted now so it isn't a surprise later:** the PARDISO
> solver does not work on Apple Silicon. Use **MUMPS** for the reciprocity
> solves. (SimNIBS 4.6.0 release notes.)

### 2. MIDA head model
IT'IS Foundation, free (handling fee), requires registration:
https://itis.swiss/virtual-population/regional-human-models/mida-model

Download the **voxel / NIfTI** distribution. Put it in `data/`.

### 3. ⚠️ The one thing that could change the paper design

```bash
python src/01_build_mesh.py --list-labels data/<the-label-file>.nii.gz
```

Pass the real path — the script will not guess a filename. If MIDA's tissue-name
list isn't picked up automatically from alongside the volume, point at it with
`--lut <file>`; without names the script refuses to guess and says so.

This prints every anatomical label in MIDA, writes `results/01_label_inventory.csv`,
and ends with an explicit verdict on the fork below. **Find the suprahyoid
muscles** — digastric (posterior belly especially), stylohyoid, mylohyoid, geniohyoid.

**Answered 2026-08-02 — the catch-all branch applies.** None of digastric, stylohyoid, mylohyoid, geniohyoid or genioglossus is individually segmented in MIDA v1.0's 116-label voxel distribution. They sit inside `Muscle (General)` (label 38) and `Tongue` (label 42), and must be sub-segmented by hand and reported as a methods limitation. Budget a few extra days; the limitation is honest, not fatal.

Verified and filled in `src/config.py` (10 of 18): masseter 66, temporalis/temporoparietalis 63, medial pterygoid 81, lateral pterygoid 65, orbicularis oris 75, buccinator 84, mentalis 71, depressor anguli oris 72, platysma 60, SCM 68. The other 8 stay `None` on purpose — a wrong label is worse than a missing one — with their containers recorded in `config.MIDA_POOLED`.

Full inventory: `results/01_label_inventory.csv`.

### 4. Python — must be 3.11

Not a preference. The only native Apple Silicon SimNIBS 4.6.0 build is a
**cp311** wheel, so a 3.12+ interpreter cannot load it.

```bash
uv venv --python 3.11 .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

`--list-labels` needs only numpy + nibabel, so the label question can be
resolved before SimNIBS is installed.

---

## Pipeline

| Step | Script | Output |
|---|---|---|
| 1 | `01_build_mesh.py` | tetrahedral mesh with muscle compartments as custom labels |
| 2 | `02_place_electrodes.py` | electrode coordinates on the skin surface, written back to config |
| 3 | `03_leadfields.py` | one reciprocity solve per montage → E-field volumes |
| 4 | `04_analyze.py` | sensitivity matrix, dB tables, all figures |

---

## The method in one paragraph

Do **not** place thousands of muscle-fibre sources and solve forward for each. Use **reciprocity**: inject 1 mA at an electrode pair, solve for **E** throughout the head, and read the field inside each muscle compartment. The lead field for a source at **r** with orientation **n̂** is `E(r) · n̂`. SimNIBS's tDCS solver already does exactly this computation — you're repurposing it. One solve per montage (~20 total) instead of one per source (intractable).

---

## Two things that make this more than a lookup table

**Muscle anisotropy.** Muscle conducts ~4× better along fibres than across (0.4 vs 0.1 S/m). Head models almost universally assume isotropy because brain sources barely care. Run it both ways. If the ear sensitivity estimate shifts materially, that's a second finding: *isotropic head models systematically mis-estimate muscle coupling.*

**It predicts Paper 2.** The model says which sites and which muscle groups survive at the ear. Your physical 8-channel jaw-vs-ear rig then tests that prediction directly. Model predicts, experiment confirms or refutes — that pairing is far stronger than either paper alone, and it's why this one goes first.

---

## Status

- [x] Outline, gap statement, citations
- [x] Config: conductivities, muscle list, montages
- [x] Python 3.11 venv + pinned `requirements.txt`
- [x] `01_build_mesh.py` — both modes written, failure paths verified
- [x] MIDA downloaded, **suprahyoid segmentation verified** — pooled, sub-segmentation required
- [x] SimNIBS 4.6.0 installed → `~/Applications/SimNIBS-4.6` (`meshmesh`, `fem`, `mumps` all verified)
- [ ] Stock SimNIBS example runs end to end
- [ ] Suprahyoid group sub-segmented from label 38
- [ ] Mesh built with muscle labels
- [ ] Electrodes placed
- [ ] Reciprocity solves
- [ ] Figures
- [ ] Draft → arXiv
