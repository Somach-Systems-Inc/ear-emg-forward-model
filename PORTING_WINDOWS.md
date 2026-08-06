# Running this pipeline on Windows

`REPRODUCTION.md` describes a macOS setup. This document records what is
different on Windows, measured on one machine rather than assumed. It does not
replace `REPRODUCTION.md`; read that first.

Defects found along the way that are **not** Windows-specific are in
`FINDINGS_PREEXISTING.md`.

**Reference machine.** Windows 11 Home 24H2 (build 26200), native — not WSL.
Ryzen 9 9950X, 16 cores / 32 threads. 61.61 GB RAM at 6400 MT/s. NVMe SSD.
PowerShell 7.6.4.

---

## 1. Environment

`requirements.txt` pins Python **3.11** to match SimNIBS 4.6.0's `cp311` build.
`uv` fetches it; nothing needs to be on the machine first.

```powershell
uv venv --python 3.11 .venv
.\.venv\Scripts\Activate.ps1          # not source .venv/bin/activate
uv pip install -r requirements.txt
uv pip install mne==1.12.1
```

**`mne` is required but absent from `requirements.txt`.** `val_rdm_mag.py`,
`val_reciprocity.py` and `measure_floor_multidraw.py` all import it, and
`REPRODUCTION.md` §3 refers to "a separate `.venv` for analysis that needs
`mne`". Pin it to `1.12.1` to match `results/val_environments.json`.

Installing the pinned set produced an environment matching the recorded
`analytic_phase` fingerprint exactly: Python 3.11.15, numpy 2.4.6, scipy 1.17.1,
mne 1.12.1, nibabel 5.4.2. No CUDA/GPU package is pulled in — this workload is
CPU and memory bound and the GPU is irrelevant to it.

## 2. SimNIBS 4.6.0

Use `simnibs_installer_windows.exe` from the v4.6.0 release, not the macOS `.pkg`
and not the wheel (`requirements.txt` explains why the wheel route fails).

**The installer is NSIS. The silent switch is `/S`, uppercase.**

```powershell
.\simnibs_installer_windows.exe /S
```

The official documentation states silent mode is Linux-only. That is wrong for
Windows: `/S` works. Passing `-s` is silently ignored and opens the GUI wizard
instead, which will hang any unattended script. `/D=<path>` sets the target if
you need one.

Measured: 3.01 min, exit 0, **no elevation required**, installs to
`%USERPROFILE%\SimNIBS-4.6` (3.5 GB, 62,930 files) and adds
`…\SimNIBS-4.6\bin` to the **user** PATH.

The installer is **not Authenticode-signed**. It is the official GitHub release
asset over HTTPS and its size matches the published 857.3 MB; SmartScreen will
still warn.

SimNIBS's bundled interpreter matched the recorded `simnibs_phase` fingerprint
exactly: Python 3.11.14, SimNIBS 4.6.0, numpy 2.3.0, scipy 1.17.1, nibabel 5.3.3.

## 3. Windows-specific gotchas

**PATH is set at user scope, so an already-open shell will not see it.** This is
the single most likely cause of a confusing `meshmesh not found`. Either open a
new shell, or refresh in-process:

```powershell
$env:PATH = [Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
            [Environment]::GetEnvironmentVariable("PATH","User")
```

**`bin\` ships `meshmesh.cmd`, not `meshmesh.exe`.** `shutil.which("meshmesh")`
still resolves it via `PATHEXT`, so `01_build_mesh.py` needs no change — verified
on this machine.

**`simnibs_python.cmd` mangles a multi-line `-c` string, exits 0, and prints
nothing.** A silent success is worse than a failure. Use a script file, or keep
`-c` to a single line.

**`core.autocrlf` defaults to true and there is no `.gitattributes`.** Committed
CSVs check out with CRLF. Compare results by parsing floats, never by diffing
bytes, or every line will appear changed.

**Default text encoding is cp1252, not UTF-8** (`PYTHONUTF8` is off). Any bare
`open()` inherits it. This is the mechanism behind finding 1 in
`FINDINGS_PREEXISTING.md`, and it bites in both directions — on Windows the
latin-1 MIDA LUT happens to decode correctly, which masks the bug rather than
fixing it.

## 4. Per-clone setup

Required once, and not cloned with the repo (`REPRODUCTION.md` §2):

```powershell
git config core.hooksPath .githooks
```

The hook is bash and runs fine under Git for Windows. Verified to fire on this
machine: a staged `.geo` is rejected on extension, a staged 4.6 MB `.csv` is
rejected on size, and a small `.py` control is accepted.

**Set `user.name` / `user.email` before testing the hook.** A missing git
identity aborts the commit *before* the hook runs, so an unset identity looks
exactly like a hook rejection.

MIDA is licensed and must not enter the repo. On Windows the clean way to keep it
out of `data/` while still satisfying the path the pipeline expects is a
**directory junction**, which needs no elevation (a symlink does):

```powershell
New-Item -ItemType Junction -Path data\MIDA_v1.0 -Target <canonical-copy>
```

Verified afterwards that `git status` stays clean and `git check-ignore` still
covers `data/MIDA_v1.0/MIDA_v1_voxels/MIDA_v1.nii`.

## 5. Validation results on this machine

`src/preflight.py` **PASSES** under both interpreters.

The drift NOTE it prints is an artifact worth understanding before anyone chases
it: `preflight` compares the *current* interpreter against **both** recorded
phases, so whichever phase you are running under, the other one always reports
drift. Each phase matched its own record exactly here. There is no real drift.

`src/test_guards_fire.py` passes — all 12 synthetic cases fire exactly one guard
each, with the clean control tripping none.

`src/val_convergence_fit.py` recomputes `fit.csv` **bit-identically** from the
committed convergence CSVs, including `RDM_0=2.0118, C=1.411734, p=0.9802`. The
analysis code is deterministic on Windows; any difference in results therefore
comes from the mesh and the solve, not from arithmetic.

### The sphere validation does NOT reproduce the committed numbers

Rebuilding the sphere and re-solving gives, on identical source points (max
coordinate delta exactly 0):

| | committed | this machine |
|---|---|---|
| RDM median | 4.35521 % | 3.85182 % |
| MAG median | +4.40023 % | +1.15099 % |

Zero of 120 rows match to 1e-9. Both pass `preflight`'s ≤5 % gates.

Before reading anything into that, note the scale this repository has already
established for mesh-realisation noise. `results/electrode_meshing_floor.txt`
records the median-MAG distribution's **SD as 4.607 pp** (n = 6 draws,
`measure_floor_multidraw.py`), and a per-site floor of **0.272 dB**.

Two runs of the same command on this machine differ by 0.10 pp RDM and 2.65 pp
MAG — an unremarkable draw from that published distribution, and a cross-platform
corroboration of it rather than a new result. **The MAG difference above is
comfortably inside the known floor and should not be interpreted.** The RDM
difference is the part that is not obviously accounted for.

Measured across all four `.ini` densities on this machine, against the committed
Mac values:

| density | tets | h_mean | RDM % | Mac RDM % | MAG % | Mac MAG % |
|---|---|---|---|---|---|---|
| vcoarse | 120,792 | 2.8721 | 4.6302 | 6.0977 | −3.9154 | +5.5282 |
| coarse | 271,397 | 2.1726 | 4.4913 | 5.1472 | +2.3578 | +22.0184 |
| medium | 649,176 | 1.5610 | 3.9568 | 4.3552 | +3.8027 | +4.4002 |
| fine | 646,841 | 1.5566 | 4.1385 | 3.8125 | +2.3583 | +9.4637 |

RDM is consistently lower here, and the gap narrows with refinement. Note that
`fine` is not a fourth density — it saturates to medium (finding 3), so those two
rows are two samples at one density.

**This is not resolved.** Mesh density alone does not account for the RDM gap:
extrapolating the Mac's own fitted curve to the `h` measured here explains only
about 8 % of it at vcoarse and 31 % at medium. What remains is unexplained and
would need the point-electrode ablation, or several rebuilds per density to
establish the real spread, before anyone claims one platform is more accurate
than the other.

## 6. Timings and memory

Measured by sampling working-set across the whole process tree at 4 Hz, not by
estimation. `meshmesh`, not the solves, is the memory peak of the sphere
validation.

| step | wall clock | peak RSS |
|---|---|---|
| `val_sphere_build.py --voxel 0.5` | 0.76 s | 0.18 GB |
| `meshmesh` (sphere, medium) | 2.91 min | 3.52 GB |
| `val_reciprocity --phase simnibs` (3 solves) | 31.4 s | 0.56 GB |
| `val_reciprocity --phase analytic` | 5.1 s | 0.14 GB |
| `val_rdm_mag --phase simnibs` (16 solves) | 2.50 min | 0.67 GB |
| `val_rdm_mag --phase analytic` | 1.6 s | 0.13 GB |
| `val_convergence_fit` | 0.7 s | 0.07 GB |

One sphere solve is roughly 9.4 s and 0.67 GB peak.

### Not yet measured

The numbers above are the **sphere validation only**. The production workload —
building `mida_headneck.msh` from MIDA and solving a leadfield on it — is a
different scale and is not characterised here yet. Do not extrapolate from the
sphere: the head mesh is roughly 20× the element count.

Partial figure, for the mesh build only: on this machine `01_build_mesh.py` was
still running past 38 minutes with a peak of 9.15 GB, having spent 6:49 on
preparation and 6:10 on meshing before entering post-processing. That is a
lower bound, not a result.

Note also that the full-configuration mesh **cannot be built from a clean
checkout**: 8 of 18 muscles are pooled in MIDA labels 38/42 awaiting hand
sub-segmentation (`config.py:200-231`), and `01_build_mesh.py` correctly refuses
without `--skip-label-check`. The provisional mesh that flag produces has
complete geometry but provisional muscle mapping, so it is valid for timing and
memory measurement and **not** for any sensitivity result.
