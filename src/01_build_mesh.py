#!/usr/bin/env python3
"""
Stage 1 -- tetrahedral head mesh from the MIDA label volume.

Two modes:

  --list-labels <nifti>
      Inventory every label integer present in a label volume: voxel count,
      physical volume, and the anatomical name if a MIDA lookup table can be
      found next to it. Then answer the suprahyoid question from CLAUDE.md
      directly -- are digastric / stylohyoid / mylohyoid / geniohyoid
      individually segmented, or pooled into a catch-all?

      This mode needs only numpy + nibabel. It deliberately does NOT require
      SimNIBS, because resolving the label question is the fork in the road
      and should not be blocked on a 4 GB install.

  (default)
      Run SimNIBS `meshmesh` on the label volume, write DATA/mida_headneck.msh,
      and emit the label -> conductivity mapping that stage 3 will bind.

This script never downloads anything. MIDA requires manual registration with
the IT'IS Foundation (DOI 10.13099/ViP-MIDA-V1.0).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

# The muscles whose segmentation status decides the paper's design.
# CLAUDE.md: "Individually segmented -> proceed as designed. Inside a generic
# 'muscles' catch-all -> sub-segment manually and document as a limitation."
DECISION_MUSCLES = [
    "digastric",
    "stylohyoid",
    "mylohyoid",
    "geniohyoid",
    "genioglossus",
]

# Labels that pool many muscles into one compartment rather than naming one.
# MIDA v1.0 ships "Muscle (General)" and an undivided "Tongue"; specific muscles
# are named "Muscle - Masseter", so the " - " is what distinguishes them.
CATCH_ALL_PATTERNS = [
    r"^muscles?\s*$",
    r"^muscles?\s*\(?\s*(general|generic|unspecified|other|remaining|nos)\b",
    r"^skeletal[\s_-]*muscle",
    r"^muscle[\s_-]*tissue",
    r"^generic[\s_-]*muscle",
    r"^soft[\s_-]*tissue",
    r"^tongue\s*$",
]

LUT_GLOBS = ["*.txt", "*.csv", "*.tsv", "*.lut", "*.label", "*.ctbl", "*.json"]


class Stage1Error(RuntimeError):
    """A precondition failed. Message is meant to be read by a human."""


# ----------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------
def load_label_volume(path: Path):
    """Return (label_array_int, voxel_volume_mm3, nibabel_image).

    Uses dataobj rather than get_fdata(): a 500 um head volume is large and
    get_fdata() would upcast integer labels to float64.
    """
    try:
        import numpy as np
        import nibabel as nib
    except ImportError as exc:  # pragma: no cover
        raise Stage1Error(
            f"Missing dependency: {exc.name}\n"
            f"  Install with:  uv pip install -r requirements.txt\n"
            f"  (or activate the project venv: source .venv/bin/activate)"
        ) from exc

    if not path.exists():
        raise Stage1Error(_missing_volume_message(path))

    img = nib.load(str(path))
    arr = np.asanyarray(img.dataobj)

    if arr.dtype.kind == "f":
        finite = arr[np.isfinite(arr)]
        if finite.size and not np.all(finite == np.rint(finite)):
            raise Stage1Error(
                f"{path} holds non-integer values, so it is not a label volume.\n"
                f"  dtype={arr.dtype}  min={float(finite.min())}  max={float(finite.max())}\n"
                f"  Point --list-labels at MIDA's discrete label/segmentation file,\n"
                f"  not at an intensity or tissue-probability image."
            )
        arr = np.rint(arr).astype(np.int32)
    elif arr.dtype.kind not in ("i", "u"):
        raise Stage1Error(f"{path} has unsupported dtype {arr.dtype} for a label volume.")

    zooms = img.header.get_zooms()[:3]
    voxel_mm3 = float(zooms[0] * zooms[1] * zooms[2])
    return arr, voxel_mm3, img


def _missing_volume_message(path: Path) -> str:
    listing = ""
    if config.DATA.exists():
        found = sorted(
            p.name for p in config.DATA.iterdir() if not p.name.startswith(".")
        )
        listing = (
            "  data/ currently contains: " + (", ".join(found) if found else "(empty)") + "\n"
        )
    else:
        listing = f"  data/ does not exist yet ({config.DATA})\n"

    return (
        f"Label volume not found: {path}\n"
        f"{listing}"
        f"\n"
        f"MIDA is not downloadable by script. It requires manual registration:\n"
        f"  1. Register at https://itis.swiss/virtual-population/regional-human-models/mida-model/\n"
        f"     (MIDA v1.0, DOI 10.13099/ViP-MIDA-V1.0)\n"
        f"  2. Download and unpack it into {config.DATA}\n"
        f"  3. Re-run this pointing at the label/segmentation NIfTI, e.g.\n"
        f"       python src/01_build_mesh.py --list-labels data/<the-label-file>.nii.gz\n"
        f"\n"
        f"This script will not guess a filename. Pass the real path."
    )


# ----------------------------------------------------------------------
# Lookup table discovery + parsing
# ----------------------------------------------------------------------
def parse_lut(path: Path) -> dict[int, str]:
    """Parse a label lookup table into {label_int: name}.

    Handles the formats MIDA and its neighbours actually ship in:
      - FreeSurfer / ITK-SNAP:  <idx> <r> <g> <b> <a> <vis> <msh> "Name"
      - ITK-SNAP alt:           <idx> <Name> <r> <g> <b>
      - plain:                  <idx><sep><Name>
      - csv/tsv with a header naming an index column and a name column
      - json: {"1": "Name"} or [{"label": 1, "name": "..."}]

    ENCODING. This was `read_text(errors="replace")`: no encoding, so the
    platform default, and errors="replace" turns any byte the codec rejects
    into U+FFFD without raising. MIDA v1.0's own LUT is latin-1 -- label 52 is
    "Skull Diplo\xebe", a single 0xEB byte -- so on a UTF-8 platform that byte
    is invalid and silently became U+FFFD, while on a cp1252 platform it
    decoded correctly. A tissue NAME is an identity, and identities must not
    depend on the machine that read them.

    So: try UTF-8 strictly, then fall back to latin-1, which is total (every
    byte 0x00-0xFF maps to a character) and therefore cannot silently drop
    anything. Nothing is ever replaced.
    """
    raw = path.read_bytes()
    for enc in ("utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:                                   # pragma: no cover - latin-1 is total
        raise Stage1Error(f"cannot decode LUT {path} as utf-8 or latin-1")

    if path.suffix.lower() == ".json":
        return _parse_lut_json(text)

    lut = _parse_lut_delimited(path, text)
    if lut:
        return lut
    return _parse_lut_freeform(text)


def _parse_lut_json(text: str) -> dict[int, str]:
    try:
        obj = json.loads(text)
    except json.JSONDecodeError:
        return {}
    lut: dict[int, str] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            try:
                lut[int(k)] = str(v) if not isinstance(v, dict) else str(
                    v.get("name") or v.get("label") or v
                )
            except (TypeError, ValueError):
                continue
    elif isinstance(obj, list):
        for item in obj:
            if not isinstance(item, dict):
                continue
            idx = item.get("label", item.get("index", item.get("id")))
            name = item.get("name", item.get("structure", item.get("tissue")))
            try:
                if idx is not None and name is not None:
                    lut[int(idx)] = str(name)
            except (TypeError, ValueError):
                continue
    return lut


def _parse_lut_delimited(path: Path, text: str) -> dict[int, str]:
    if path.suffix.lower() not in (".csv", ".tsv"):
        return {}
    delim = "\t" if path.suffix.lower() == ".tsv" else ","
    rows = list(csv.reader(text.splitlines(), delimiter=delim))
    if not rows:
        return {}

    header = [c.strip().lower() for c in rows[0]]
    idx_col = next(
        (i for i, c in enumerate(header) if c in ("label", "index", "id", "value", "idx")),
        None,
    )
    name_col = next(
        (i for i, c in enumerate(header)
         if c in ("name", "structure", "tissue", "region", "description")),
        None,
    )
    if idx_col is None or name_col is None:
        return {}

    lut: dict[int, str] = {}
    for row in rows[1:]:
        if len(row) <= max(idx_col, name_col):
            continue
        try:
            lut[int(float(row[idx_col].strip()))] = row[name_col].strip()
        except ValueError:
            continue
    return lut


def _parse_lut_freeform(text: str) -> dict[int, str]:
    lut: dict[int, str] = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].split("//", 1)[0].strip()
        if not line:
            continue

        quoted = re.match(r'^\s*(\d+)\D.*?["\']([^"\']+)["\']', line)
        if quoted:
            lut[int(quoted.group(1))] = quoted.group(2).strip()
            continue

        tokens = re.split(r"[\s,;\t]+", line)
        if len(tokens) < 2:
            continue
        try:
            idx = int(tokens[0])
        except ValueError:
            continue

        words = [t for t in tokens[1:] if not re.fullmatch(r"[-+]?\d*\.?\d+", t)]
        if words:
            lut[idx] = " ".join(words).strip().strip('"\'')
    return lut


def find_lut(volume_path: Path, labels_present: set[int], explicit: Path | None):
    """Locate a lookup table. Returns (lut, source_path_or_None, note)."""
    if explicit is not None:
        if not explicit.exists():
            raise Stage1Error(f"--lut given but not found: {explicit}")
        lut = parse_lut(explicit)
        if not lut:
            raise Stage1Error(
                f"--lut {explicit} parsed to zero entries.\n"
                f"  Expected lines like '17 Masseter' or '17 255 0 0 255 1 1 \"Masseter\"'."
            )
        return lut, explicit, "explicit --lut"

    candidates: list[Path] = []
    seen: set[Path] = set()
    for directory in (volume_path.parent, volume_path.parent.parent):
        if not directory.is_dir():
            continue
        for pattern in LUT_GLOBS:
            for cand in sorted(directory.glob(pattern)):
                if cand.resolve() in seen or cand.stat().st_size > 5_000_000:
                    continue
                seen.add(cand.resolve())
                candidates.append(cand)

    best, best_path, best_overlap = {}, None, 0
    for cand in candidates:
        try:
            lut = parse_lut(cand)
        except (OSError, UnicodeError):
            continue
        if len(lut) < 5:
            continue
        overlap = len(labels_present & set(lut))
        if overlap > best_overlap:
            best, best_path, best_overlap = lut, cand, overlap

    if best_path is None:
        return {}, None, "no lookup table found -- names unavailable"

    coverage = 100.0 * best_overlap / max(len(labels_present), 1)
    return best, best_path, f"matched {best_overlap}/{len(labels_present)} labels ({coverage:.0f}%)"


# ----------------------------------------------------------------------
# --list-labels
# ----------------------------------------------------------------------
def list_labels(volume_path: Path, lut_path: Path | None, out_csv: Path | None) -> int:
    import numpy as np

    arr, voxel_mm3, img = load_label_volume(volume_path)
    values, counts = np.unique(arr, return_counts=True)

    labels_present = {int(v) for v in values}
    lut, lut_src, lut_note = find_lut(volume_path, labels_present, lut_path)

    zooms = " x ".join(f"{float(z):g}" for z in img.header.get_zooms()[:3])
    print(f"Label volume : {volume_path}")
    print(f"Shape        : {tuple(int(s) for s in arr.shape)}   dtype={arr.dtype}")
    print(f"Voxel size   : {zooms} mm  ({voxel_mm3:.6g} mm^3/voxel)")
    # MIDA labels background as 50, not 0, so detect it by name as well.
    background = {
        v for v in labels_present
        if v == 0 or lut.get(v, "").strip().lower() in ("background", "air", "outside")
    }
    print(f"Unique labels: {len(values)}  ({len(values) - len(background)} excluding background)")
    print(f"Lookup table : {lut_src if lut_src else '(none found)'}  [{lut_note}]")
    print()

    header = f"{'label':>7}  {'voxels':>12}  {'volume_mm3':>14}  name"
    print(header)
    print("-" * max(len(header), 64))

    rows = []
    order = np.argsort(counts)[::-1]
    for i in order:
        label = int(values[i])
        n = int(counts[i])
        vol = n * voxel_mm3
        name = lut.get(label, "")
        rows.append({"label": label, "voxels": n, "volume_mm3": vol, "name": name})
        shown = name if label != 0 else (name or "(background)")
        print(f"{label:>7}  {n:>12,}  {vol:>14,.1f}  {shown}")

    print()
    _report_decision(rows)

    if out_csv is not None:
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        # encoding pinned: without it the file is written in the platform
        # default (UTF-8 on macOS, cp1252 on Windows), so the same run on two
        # machines produces two different files and tissue names round-trip
        # differently.
        with out_csv.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["label", "voxels", "volume_mm3", "name"])
            writer.writeheader()
            writer.writerows(sorted(rows, key=lambda r: r["label"]))
        print(f"Inventory written to {out_csv}")

    return 0


def _report_decision(rows: list[dict]) -> None:
    """Answer the question this script exists to answer."""
    named = [r for r in rows if r["name"]]

    print("=" * 64)
    print("SUPRAHYOID / TONGUE SEGMENTATION CHECK  (CLAUDE.md 'fork in the road')")
    print("=" * 64)

    if not named:
        print("No lookup table resolved, so names cannot be checked automatically.")
        print("Pass --lut <file> pointing at MIDA's tissue-name list, or inspect the")
        print("volume in ITK-SNAP / freeview and fill config.MUSCLES by hand.")
        print("NOT RESOLVED -- do not fill mida_label from guesswork.")
        return

    for target in DECISION_MUSCLES:
        hits = [r for r in named if target in r["name"].lower().replace("-", " ")]
        if hits:
            detail = ", ".join(
                f"label {h['label']} ({h['name']}, {h['voxels']:,} vox)" for h in hits[:6]
            )
            print(f"  FOUND    {target:<14} {detail}")
        else:
            print(f"  MISSING  {target:<14} no label name contains '{target}'")

    catch_alls = [
        r for r in named
        if any(re.search(p, r["name"].strip().lower()) for p in CATCH_ALL_PATTERNS)
    ]
    print()
    if catch_alls:
        print("Pooled compartment(s) the missing muscles are likely inside:")
        for r in catch_alls:
            print(f"    label {r['label']:>4}  {r['name']:<24} "
                  f"{r['voxels']:>12,} voxels  ({r['volume_mm3']:,.0f} mm^3)")
        print("  -> These are the volumes to sub-segment by hand. CLAUDE.md:")
        print("     document it as a methods limitation. Do NOT substitute a")
        print("     nearby label.")
    else:
        print("No pooled muscle/tongue compartment detected.")

    missing = [
        t for t in DECISION_MUSCLES
        if not any(t in r["name"].lower().replace("-", " ") for r in named)
    ]
    print()
    if missing:
        print(f"VERDICT: NOT individually segmented -> {', '.join(missing)}")
        print("         The manual sub-segmentation branch applies.")
    else:
        print("VERDICT: all decision muscles individually segmented -> proceed as designed.")
    print("Fill config.MUSCLES[*].mida_label from the table above. Verified integers only.")


# ----------------------------------------------------------------------
# default mode -- build the mesh
# ----------------------------------------------------------------------
def resolved_muscle_labels() -> tuple[list[tuple], list[tuple]]:
    resolved, unresolved = [], []
    for entry in config.MUSCLES:
        (resolved if entry[2] is not None else unresolved).append(entry)
    return resolved, unresolved


def build_mesh(volume_path: Path, out_mesh: Path, force: bool,
               extra: list[str] | None = None,
               skip_label_check: bool = False) -> int:
    resolved, unresolved = resolved_muscle_labels()
    if unresolved and not skip_label_check:
        names = ", ".join(e[0] for e in unresolved)
        raise Stage1Error(
            f"{len(unresolved)} of {len(config.MUSCLES)} muscles still have "
            f"mida_label = None in src/config.py:\n"
            f"  {names}\n\n"
            f"Resolve them first:\n"
            f"  python src/01_build_mesh.py --list-labels <mida-label-volume.nii.gz>\n\n"
            f"CLAUDE.md: 'a wrong label is worse than a missing one'. Refusing to "
            f"build a mesh whose muscle compartments cannot be verified.\n\n"
            f"To build a PROVISIONAL mesh covering only the {len(resolved)} verified\n"
            f"muscles -- useful for exercising stages 2-4 before the hand\n"
            f"sub-segmentation is done -- pass --skip-label-check."
        )

    if unresolved:
        names = ", ".join(e[0] for e in unresolved)
        print("=" * 68)
        print("PROVISIONAL MESH -- --skip-label-check was passed.")
        print("=" * 68)
        print(f"{len(unresolved)} of {len(config.MUSCLES)} muscles have no verified "
              f"MIDA label and\nwill NOT be resolvable as separate compartments in "
              f"this mesh:\n  {names}\n")
        print("They are pooled inside:")
        for muscle, container in sorted(config.MIDA_POOLED.items(),
                                        key=lambda kv: kv[1]):
            print(f"    {muscle:<22} -> label {container}")
        print("\nThe mesh itself is complete -- meshmesh meshes every label in the")
        print("volume. What is provisional is the MUSCLE MAPPING, not the geometry.")
        print("Any sensitivity result for the muscles above is invalid until they")
        print("are sub-segmented. Do not put them in a figure.\n")

    if not volume_path.exists():
        raise Stage1Error(_missing_volume_message(volume_path))

    meshmesh = shutil.which("meshmesh")
    if meshmesh is None:
        # The installer adds this to PATH -- via ~/.zprofile on macOS, via the
        # user PATH on Windows -- and neither is visible to a shell that was
        # already open. Fall back to the default install locations before
        # giving up, so a plain `python src/01_build_mesh.py` works.
        #   macOS: ~/Applications/SimNIBS-4.6/bin/meshmesh
        #   Windows: %USERPROFILE%\SimNIBS-4.6\bin\meshmesh.cmd
        defaults = [Path.home() / "Applications/SimNIBS-4.6/bin/meshmesh",
                    Path.home() / "SimNIBS-4.6/bin/meshmesh.cmd"]
        for default in defaults:
            if default.is_file():
                meshmesh = str(default)
                break
        else:
            listed = "\n".join(f"  {d}" for d in defaults)
            raise Stage1Error(
                "SimNIBS `meshmesh` is not on PATH and is not at any of\n"
                f"{listed}\n\n"
                "Install SimNIBS 4.6.0 from the installer for your platform\n"
                "(simnibs_installer_macos.pkg / simnibs_installer_windows.exe;\n"
                "see README.md -- the pip wheel route does not work). Then verify:\n"
                "  meshmesh -h\n"
                "If it is installed but not found, open a new shell so the\n"
                "PATH the installer set is visible (~/.zprofile on macOS, the\n"
                "user PATH on Windows)."
            )

    if out_mesh.exists() and not force:
        raise Stage1Error(
            f"{out_mesh} already exists. Pass --force to overwrite, or delete it."
        )

    out_mesh.parent.mkdir(parents=True, exist_ok=True)
    cmd = [meshmesh, str(volume_path), str(out_mesh)] + list(extra or [])
    print("Running:", " ".join(cmd), flush=True)
    print("(MIDA is 480x480x350 at 500 um; expect this to take a while and to\n"
          " need several GB of RAM. Ctrl-C leaves no partial mesh behind.)\n",
          flush=True)

    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        raise Stage1Error(
            f"meshmesh exited {proc.returncode}. Mesh NOT written.\n"
            f"  Command: {' '.join(cmd)}"
        )
    if not out_mesh.exists():
        raise Stage1Error(
            f"meshmesh reported success but {out_mesh} does not exist."
        )

    size_mb = out_mesh.stat().st_size / 1e6
    print(f"\nMesh written: {out_mesh}  ({size_mb:.1f} MB)")

    cond_csv = write_conductivity_map(config.RESULTS / "01_conductivity_map.csv")
    print(f"Conductivity map written: {cond_csv}")
    print(
        "\nNote: a SimNIBS .msh carries tissue TAGS, not conductivities. The values\n"
        "above bind at simulation time in stage 3 via s.cond[label-1].value.\n"
        "This file is the single source of truth for Table 1."
    )
    return 0


def write_conductivity_map(out_csv: Path) -> Path:
    """Emit label -> conductivity, for stage 3 to bind and for Table 1."""
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    # encoding pinned: without it the file is written in the platform default
    # (UTF-8 on macOS, cp1252 on Windows), so the SAME run on two machines
    # produces two different files and tissue names round-trip differently.
    with out_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["mida_label", "muscle", "group", "verified", "pooled_in",
             "sigma_iso_S_per_m", "sigma_long_S_per_m", "sigma_trans_S_per_m",
             "expected_at_ear"]
        )
        for name, group, label, expected in config.MUSCLES:
            # `verified` exists so stage 4 cannot silently plot a muscle whose
            # compartment was never actually resolved.
            writer.writerow([
                label if label is not None else "",
                name, group,
                "yes" if label is not None else "no",
                "" if label is not None else config.MIDA_POOLED.get(name, ""),
                config.SIGMA["muscle_iso"],
                config.SIGMA["muscle_long"],
                config.SIGMA["muscle_trans"],
                expected,
            ])
    return out_csv


# ----------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="01_build_mesh.py",
        description="Stage 1: inventory MIDA labels, or build the tetrahedral mesh.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python src/01_build_mesh.py --list-labels data/MIDA_v1_labels.nii.gz\n"
            "  python src/01_build_mesh.py --list-labels data/labels.nii.gz --lut data/tissues.txt\n"
            "  python src/01_build_mesh.py --label-volume data/labels.nii.gz\n"
        ),
    )
    parser.add_argument(
        "--list-labels", metavar="NIFTI", type=Path,
        help="inventory every label integer in NIFTI and run the suprahyoid check",
    )
    parser.add_argument(
        "--lut", metavar="FILE", type=Path,
        help="explicit label lookup table (else auto-discovered next to the volume)",
    )
    parser.add_argument(
        "--label-volume", metavar="NIFTI", type=Path,
        help="MIDA label volume to mesh (default mode)",
    )
    parser.add_argument(
        "--out", metavar="MSH", type=Path, default=config.MESH,
        help=f"output mesh path (default: {config.MESH})",
    )
    parser.add_argument(
        "--no-csv", action="store_true",
        help="do not write the label inventory CSV",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="overwrite an existing mesh",
    )
    parser.add_argument(
        "--skip-label-check", action="store_true",
        help="build a PROVISIONAL mesh while some mida_label are still None "
             "(for exercising stages 2-4 before hand sub-segmentation)",
    )
    # Passed straight through to meshmesh. MIDA is already 500 um isotropic, so
    # meshmesh's "twice the minimum resolution" rule of thumb does not apply
    # unmodified -- leave --voxsize-meshing unset unless you have a reason.
    parser.add_argument(
        "--voxsize-meshing", metavar="MM", type=float,
        help="meshmesh --voxsize_meshing: internal upsampling resolution in mm",
    )
    parser.add_argument(
        "--nthreads", metavar="N", type=int,
        help="meshmesh --nthreads: meshing threads",
    )
    parser.add_argument(
        "--usesettings", metavar="INI", type=Path,
        help="meshmesh --usesettings: ini file controlling per-label tet sizes",
    )
    args = parser.parse_args(argv)

    extra: list[str] = []
    if args.voxsize_meshing is not None:
        extra += ["--voxsize_meshing", str(args.voxsize_meshing)]
    if args.nthreads is not None:
        extra += ["--nthreads", str(args.nthreads)]
    if args.usesettings is not None:
        if not args.usesettings.exists():
            print(f"\nERROR: --usesettings file not found: {args.usesettings}",
                  file=sys.stderr)
            return 1
        extra += ["--usesettings", str(args.usesettings)]

    try:
        if args.list_labels is not None:
            out_csv = None if args.no_csv else config.RESULTS / "01_label_inventory.csv"
            return list_labels(args.list_labels, args.lut, out_csv)

        if args.label_volume is None:
            parser.error(
                "no input given.\n"
                "  Inventory labels:  --list-labels <nifti>\n"
                "  Build the mesh:    --label-volume <nifti>\n"
                "There is no default MIDA filename -- pass the real path."
            )
        return build_mesh(args.label_volume, args.out, args.force, extra,
                          args.skip_label_check)

    except Stage1Error as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
