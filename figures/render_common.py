#!/usr/bin/env python3
r"""
figures/render_common.py — shared plumbing for the Paper-1 figure renderers
(render_fig2..5). Not a figure itself; holds the one CSV loader, the validated
print palette, and the save/watermark helpers so the four renderers stay small
and consistent.

Palette provenance. Colours are the repo's already-validated set (see
src/02b_qa_render.py and the dataviz skill's references/palette.md), re-checked
for these figures with scripts/validate_palette.js on a light surface:

  * montage identity (Fig 3) — jaw #2a78d6 / ear #eb6834:
        --pairs all --mode light -> worst CVD ΔE 96.7, contrast >=3:1, ALL PASS.
  * full 8-slot reference categorical (context) — ALL PASS (aqua/yellow/magenta
        carry a sub-3:1 contrast WARN, so they are never used as bare fills here).
  * sequential blue ramp (Fig 2) and diverging blue<->red (Fig 4) are magnitude/
        polarity ramps; the categorical validator FAILs those BY DESIGN (they
        span the lightness band), so they are checked for lightness monotonicity
        instead, not run through the categorical six.

Everything is light-background, colourblind-safe, and sized for a single journal
column. Markers double as a secondary channel wherever colour identity is used,
which is the relief the validator's contrast WARN requires.

The renderers read data from ONE csv only. This module may consult src/config.py
for the muscle/montage *vocabulary and ordering* (labels, not numbers) and to
back-fill the denormalized montage/muscle_group columns if a bare six-column
real CSV is passed.
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import config  # noqa: E402

FIGDIR = ROOT / "figures"
DEFAULT_CSV = config.RESULTS / "04_sensitivity.csv"          # the real contract path
MOCK_CSV = config.RESULTS / "04_sensitivity_MOCK.csv"         # what mock_data.py writes

# ---------------------------------------------------------------- palette / ink
SURFACE = "#fcfcfb"        # light chart surface
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"      # axes / minor labels
GRID = "#e1e0d9"           # hairline gridlines
BASELINE = "#c3c2b7"       # axis rule
DEEMPH = "#c3c2b7"         # emphasis-form "everything else" grey

# montage identity — matches src/02b_qa_render.py exactly (shared vocabulary)
MONTAGE_STYLE = {
    "jaw":       ("#2a78d6", "o", "Jaw (canonical)"),
    "ear":       ("#eb6834", "^", "Retroauricular (ear)"),
    "ceegrid":   ("#1baf7a", "s", "cEEGrid C-path"),
    "reference": ("#52514e", "X", "Reference / BIAS"),
}
ACCENT = "#2a78d6"         # emphasis accent (blue slot 1)

# blue sequential ramp, light->dark (palette.md steps 100..700)
_BLUE_RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
              "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
# diverging poles: red <-> gray <-> blue (warm/cool, neutral midpoint)
_DIV_RED, _DIV_MID, _DIV_BLUE = "#b21f1e", "#f0efec", "#184f95"


def sequential_cmap():
    """One-hue blue ramp for magnitude (Fig 2). Light = low, dark = high."""
    cm = LinearSegmentedColormap.from_list("seq_blue", _BLUE_RAMP)
    cm.set_bad(SURFACE)
    return cm


def diverging_cmap():
    """red <-> neutral gray <-> blue for signed deltas (Fig 4)."""
    cm = LinearSegmentedColormap.from_list("div_rb", [_DIV_RED, _DIV_MID, _DIV_BLUE])
    cm.set_bad(SURFACE)
    return cm


# ------------------------------------------------------------- config vocabulary
MUSCLE_ORDER = [name for name, _g, _l, _e in config.MUSCLES]
GROUP_ORDER = list(dict.fromkeys(g for _n, g, _l, _e in config.MUSCLES))
_GROUP_OF = {name: g for name, g, _l, _e in config.MUSCLES}
PCA_MUSCLES = set(config.FIBRE_PCA_MUSCLES)   # anisotropy applied only to these

# electrode column order for the matrices (reference sites are not sensing channels)
ELECTRODE_ORDER = list(config.MONTAGES["jaw"]) + list(config.MONTAGES["ear"]) \
    + list(config.MONTAGES["ceegrid"])
_MONTAGE_OF = {}
for _m, _names in config.MONTAGES.items():
    for _n in _names:
        _MONTAGE_OF[_n] = _m
_MONTAGE_OF[config.REFERENCE] = "reference"
_MONTAGE_OF[config.BIAS] = "reference"

CORE_COLUMNS = ["electrode", "muscle", "condition", "mesh", "lead_field", "db_rel_best_jaw"]


def pretty(name: str) -> str:
    return name.replace("_", " ")


# ------------------------------------------------------------------- CSV loading
def _detect_mock(path: Path) -> bool:
    if "mock" in path.name.lower():
        return True
    try:
        with open(path) as fh:
            first = fh.readline()
        return first.lstrip().startswith("#") and "SYNTHETIC" in first.upper()
    except OSError:
        return False


def load_sensitivity(path: Path) -> pd.DataFrame:
    """Read the sensitivity CSV and return a validated, enriched frame.

    Tolerates the leading `# SYNTHETIC` banner, and back-fills montage /
    muscle_group from config if a real six-column file omits them, so a bare
    contract file still renders. `df.attrs['is_mock']` and `df.attrs['source']`
    are set for downstream watermarking/provenance.
    """
    path = Path(path)
    if not path.exists():
        raise SystemExit(
            f"{path} not found.\n"
            f"  For the real figure, run the solve pipeline so it writes {DEFAULT_CSV.name}.\n"
            f"  To preview against synthetic data:  simnibs_python figures/mock_data.py\n"
            f"  then pass  --csv {MOCK_CSV}")
    df = pd.read_csv(path, comment="#")

    missing = [c for c in CORE_COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"{path} is missing required contract columns: {missing}")

    if "montage" not in df.columns:
        df["montage"] = df["electrode"].map(_MONTAGE_OF)
    if "muscle_group" not in df.columns:
        df["muscle_group"] = df["muscle"].map(_GROUP_OF)
    if df["montage"].isna().any():
        bad = sorted(df.loc[df["montage"].isna(), "electrode"].unique())
        raise SystemExit(f"electrodes not in config.MONTAGES vocabulary: {bad}")

    df.attrs["is_mock"] = _detect_mock(path)
    df.attrs["source"] = str(path)
    return df


def slice_condition_mesh(df: pd.DataFrame, condition: str, mesh: str) -> pd.DataFrame:
    out = df[(df["condition"] == condition) & (df["mesh"] == mesh)].copy()
    if out.empty:
        have = (df[["condition", "mesh"]].drop_duplicates()
                .to_records(index=False).tolist())
        raise SystemExit(f"no rows for condition={condition!r} mesh={mesh!r}; "
                         f"available (condition, mesh): {have}")
    return out


def ordered_matrix(df_slice: pd.DataFrame, value: str,
                   electrodes=None) -> tuple[np.ndarray, list[str], list[str]]:
    """Pivot to a muscles(rows, config order) x electrodes(cols) matrix of `value`."""
    electrodes = electrodes or ELECTRODE_ORDER
    piv = df_slice.pivot_table(index="muscle", columns="electrode", values=value,
                               aggfunc="mean")
    rows = [m for m in MUSCLE_ORDER if m in piv.index]
    cols = [e for e in electrodes if e in piv.columns]
    return piv.loc[rows, cols].to_numpy(), rows, cols


# --------------------------------------------------------------- print styling
def use_print_style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "font.family": "sans-serif",
        "font.sans-serif": ["Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 8,
        "axes.titlesize": 9,
        "axes.labelsize": 8,
        "axes.edgecolor": BASELINE,
        "axes.linewidth": 0.8,
        "axes.labelcolor": INK_PRIMARY,
        "axes.titlecolor": INK_PRIMARY,
        "xtick.color": INK_MUTED,
        "ytick.color": INK_MUTED,
        "xtick.labelcolor": INK_SECONDARY,
        "ytick.labelcolor": INK_SECONDARY,
        "xtick.labelsize": 7,
        "ytick.labelsize": 7,
        "text.color": INK_PRIMARY,
        "axes.grid": False,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "legend.frameon": False,
        "legend.fontsize": 7,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "pdf.fonttype": 42,      # embed real fonts, not paths — editable in the paper
        "ps.fonttype": 42,
    })


def add_watermark(fig, is_mock: bool):
    if not is_mock:
        return
    fig.text(0.5, 0.5, "SYNTHETIC  ·  MOCK DATA", transform=fig.transFigure,
             ha="center", va="center", rotation=24, fontsize=34,
             color=INK_MUTED, alpha=0.13, fontweight="bold", zorder=1000)


def footer(fig, df: pd.DataFrame):
    # A thin provenance line pinned to the TOP-LEFT corner, above the title —
    # the one place clear of axis labels on every figure shape (a bottom stamp
    # collides with the centered x-axis label on the narrow single-column plots).
    tag = "SYNTHETIC MOCK — not a solve result — " if df.attrs.get("is_mock") else ""
    src = Path(df.attrs.get("source", "?")).name
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    fig.text(0.006, 0.996, f"{tag}source: {src} · rendered {stamp}",
             ha="left", va="top", fontsize=5.2, color=INK_MUTED, alpha=0.9)


def decorate_matrix(ax, rows, cols, row_labels=None):
    """Shared axis dressing for the Fig 2 / Fig 4 muscle x electrode matrices:
    tick labels, 2px surface-colour group gaps, montage headers spanning their
    columns, and muscle-group labels parked in the left margin (clear of the
    muscle names). Returns (col_montage, row_group) for any per-cell overlay."""
    ax.set_xticks(range(len(cols)))
    ax.set_xticklabels([pretty(c) for c in cols], rotation=90, ha="center")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(row_labels if row_labels is not None else [pretty(r) for r in rows])
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)

    col_montage = [_MONTAGE_OF[c] for c in cols]
    row_group = [_GROUP_OF[r] for r in rows]

    def _boundaries(labels):
        return [i for i in range(1, len(labels)) if labels[i] != labels[i - 1]]
    for i in _boundaries(col_montage):
        ax.axvline(i - 0.5, color=SURFACE, lw=2.0)
    for i in _boundaries(row_group):
        ax.axhline(i - 0.5, color=SURFACE, lw=2.0)

    def _spans(labels):
        out, start = [], 0
        for i in range(1, len(labels) + 1):
            if i == len(labels) or labels[i] != labels[start]:
                out.append((labels[start], start, i - 1))
                start = i
        return out
    for name, i0, i1 in _spans(col_montage):
        ax.text((i0 + i1) / 2, -0.9, MONTAGE_STYLE[name][2].split(" (")[0],
                ha="center", va="bottom", fontsize=7.5, color=INK_SECONDARY,
                fontweight="bold")
    for name, i0, i1 in _spans(row_group):
        ax.annotate(name, xy=(0, (i0 + i1) / 2), xycoords=("axes fraction", "data"),
                    xytext=(-94, 0), textcoords="offset points",
                    ha="center", va="center", rotation=90, fontsize=6.5,
                    color=INK_MUTED, annotation_clip=False)
    return col_montage, row_group


def matrix_titles(ax, title, subtitle):
    """Title above, caption below it — consistent with the scatter/bar figures,
    sitting clear of the montage headers that ride just above the matrix."""
    ax.set_title(title, loc="left", fontsize=9.5, fontweight="bold", pad=34)
    ax.text(0, 1.052, subtitle, transform=ax.transAxes, va="bottom", ha="left",
            fontsize=6.5, color=INK_SECONDARY)


def save(fig, stem: str, df: pd.DataFrame, outdir: Path = FIGDIR):
    """Write <stem>.pdf (paper) and <stem>.png (repo). Mock renders are prefixed
    MOCK_ so a synthetic figure can never be mistaken for a real one."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    add_watermark(fig, df.attrs.get("is_mock", False))
    footer(fig, df)
    prefix = "MOCK_" if df.attrs.get("is_mock") else ""
    base = outdir / f"{prefix}{stem}"
    paths = []
    for ext in ("pdf", "png"):
        p = base.with_suffix("." + ext)
        fig.savefig(p, bbox_inches="tight")
        paths.append(p)
    plt.close(fig)
    for p in paths:
        print(f"  wrote {p}")
    return paths
