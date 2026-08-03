"""Artifact IO. Scripts communicate with the report generator through files.

Every measurement script writes ``out/data/<name>.json`` (numbers plus the
full provenance block) and, where the result is tabular, ``out/data/<name>.csv``
holding the same numbers. The CSV is not an afterthought: the figure palette
raises a contrast warning on two of its light-mode slots, and the `dataviz`
skill's relief rule requires that every value also be reachable without color.
The CSV is that path, and `06_report.py` folds it into the report as a table.

The report generator never guesses. A missing artifact is reported by name,
with the command that produces it, and the report is marked incomplete --
never quietly rendered with a panel missing.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable, Optional, Sequence


def data_path(out_dir: Path, name: str, suffix: str = ".json") -> Path:
    return Path(out_dir) / "data" / f"{name}{suffix}"


def fig_stem(out_dir: Path, name: str) -> Path:
    return Path(out_dir) / "figures" / name


def ensure_out(out_dir: Path) -> None:
    for sub in ("data", "figures"):
        (Path(out_dir) / sub).mkdir(parents=True, exist_ok=True)


def write_json(out_dir: Path, name: str, payload: dict) -> Path:
    ensure_out(out_dir)
    p = data_path(out_dir, name)
    p.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str))
    print(f"  wrote {p}")
    return p


def read_json(out_dir: Path, name: str) -> Optional[dict]:
    p = data_path(out_dir, name)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def write_csv(out_dir: Path, name: str, rows: Sequence[dict],
              fieldnames: Optional[Sequence[str]] = None) -> Optional[Path]:
    if not rows:
        return None
    ensure_out(out_dir)
    p = data_path(out_dir, name, ".csv")
    fields = list(fieldnames or rows[0].keys())
    with p.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fields})
    print(f"  wrote {p}")
    return p


def read_csv(out_dir: Path, name: str) -> list[dict]:
    p = data_path(out_dir, name, ".csv")
    if not p.exists():
        return []
    with p.open(newline="") as fh:
        return list(csv.DictReader(fh))


# ---------------------------------------------------------------------------
# The manifest the report generator reads
# ---------------------------------------------------------------------------

PRODUCERS: dict[str, str] = {
    "00_gain_check": "python bench/00_gain_check.py --synthetic",
    "01_noise_floor_10k": "python bench/01_noise_floor.py --synthetic",
    "01_noise_floor_short": "python bench/01_noise_floor.py --synthetic --condition short",
    "02_psd_mains": "python bench/02_psd_mains.py --synthetic",
    "03_cmrr": "python bench/03_cmrr_sweep.py --synthetic",
    "04_bias": "python bench/04_bias_on_off.py --synthetic",
    "05_ad8232": "python bench/05_ad8232_compare.py --synthetic",
}


def missing(out_dir: Path, names: Iterable[str]) -> list[tuple[str, str]]:
    """(artifact, command that makes it) for everything not on disk."""
    out = []
    for n in names:
        if not data_path(out_dir, n).exists():
            out.append((n, PRODUCERS.get(n, "(unknown producer)")))
    return out


def provenance_conflicts(metas: Iterable[dict]) -> list[str]:
    """Refuse to build one report out of runs that disagree about reality.

    Mixing a gain-8 run with a gain-24 run, or a synthetic run with a hardware
    run, produces a figure set whose panels are not comparable. Silently
    stitching them together is exactly the class of error the gain guard
    exists to prevent, one level up.
    """
    metas = [m for m in metas if m]
    problems = []
    for key, label in (("host_pga_gain", "host PGA gain"),
                       ("fs_hz", "sample rate"),
                       ("mains_hz", "mains frequency"),
                       ("source", "data source")):
        vals = sorted({str(m.get(key)) for m in metas if key in m})
        if len(vals) > 1:
            problems.append(f"{label} differs across artifacts: {', '.join(vals)}")
    unverified = [m.get("script", "?") for m in metas
                  if not m.get("gain_verified", False)]
    if unverified:
        problems.append("gain was never verified for: " + ", ".join(sorted(set(unverified))))
    return problems
