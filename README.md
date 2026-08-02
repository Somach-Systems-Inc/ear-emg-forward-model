# Paper 1 — Articulator muscle sources at retroauricular electrode sites

A volume-conductor model answering: **which speech muscles can you actually see from behind the ear, and how much do you lose versus the jaw?**

- **Human subjects:** none. No IRB required — state this explicitly in Methods.
- **Hardware:** none. Runs on the MacBook.
- **Blocked by:** nothing.

Read `paper/OUTLINE.md` first. It has the gap statement, the method, the figure plan, and the citations.

---

## Setup — do these in order

### 1. SimNIBS 4.6.0
**Native Apple Silicon** — Intel Mac support was discontinued at 4.5, so the M-series machine is the right one. Not needed for `--list-labels`; only from the mesh build onward.

Two routes, both manual (the release assets are on GitHub, not PyPI):

**A. Wheel into this repo's venv (recommended).** 184 MB, isolated, nothing system-wide:
```bash
uv pip install https://github.com/simnibs/simnibs/releases/download/v4.6.0/simnibs-4.6.0-cp311-cp311-macosx_11_0_arm64.whl
postinstall_simnibs --setup-links     # puts meshmesh/charm on PATH
```

**B. Full installer.** `simnibs_installer_macos.pkg` (849 MB) from
https://github.com/simnibs/simnibs/releases/tag/v4.6.0 — double-click, ~5–10 min.
Adds the GUI and all external tools. Installs outside this repo.

Verify either way with `meshmesh -h`, then run a stock example before touching MIDA. If the reference example doesn't run, nothing downstream will.

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

- **If individually segmented** → proceed as designed. The strongest part of the argument is intact.
- **If inside a generic "muscles" catch-all** → you must sub-segment them from the label volume by hand, and document it as a methods limitation. Still a paper, but budget a few extra days.

Confirmed present: masseter, temporalis, pterygoids, orbicularis oris, buccinator, zygomaticus, platysma, SCM.

Fill the `mida_label` column in `src/config.py` once you know the real numbers.

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
- [ ] SimNIBS installed and stock example runs
- [ ] MIDA downloaded, **suprahyoid segmentation verified**
- [ ] Mesh built with muscle labels
- [ ] Electrodes placed
- [ ] Reciprocity solves
- [ ] Figures
- [ ] Draft → arXiv
