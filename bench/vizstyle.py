"""Figure system for the bench suite.

Built to the `dataviz` skill, so every figure in the report reads as one
system. The parameters that skill calls for are filled in below and nothing
else in the repo picks a color.

Decisions this file encodes, and why:

* **Palette.** The skill's default categorical order, slots 1-4 (blue,
  orange, aqua, yellow), light and dark steps. Validated with the skill's
  own validator, not by eye:

      slots 1-4, adjacent pairs, light : all checks pass
                                  dark : all checks pass
      slots 1-3, ALL pairs,     light : all checks pass
                                  dark : all checks pass

  Four series is the cap for line/bar figures here; three for anything where
  any two marks can end up adjacent. The light run raises a contrast WARN on
  aqua and yellow, which under the skill's relief rule obliges direct labels
  or a table view. This suite ships both: every figure direct-labels its
  series at the line end, and `06_report.py` writes the same numbers to CSV.

* **Both modes rendered, not flipped.** A PNG cannot respond to the viewer's
  theme, so each figure is written twice with steps chosen for its own
  surface.

* **Provenance is part of the figure.** Synthetic data carries a SYNTHETIC
  badge and unverified gain carries a GAIN NOT VERIFIED badge, in status
  colors with a text label. A synthetic figure that could pass for a
  measurement is worse than no figure, and this suite generates a lot of
  synthetic figures.

* **No dual axes anywhere.** Where two quantities of different scale need
  comparing, they get two stacked panels sharing an x-axis.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402


FONT_STACK = ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans", "sans-serif"]

LINE_W = 1.7          # ~2px at export dpi
HAIRLINE_W = 0.7
MARKER_SIZE = 4.6     # >= 8px diameter
RING_W = 1.3          # 2px surface ring
DPI = 200


@dataclass
class Theme:
    name: str
    surface: str
    page: str
    ink: str
    secondary: str
    muted: str
    grid: str
    baseline: str
    series: tuple[str, ...]
    sequential: tuple[str, ...]
    diverging: tuple[str, str, str]
    good: str = "#0ca30c"
    warning: str = "#fab219"
    serious: str = "#ec835a"
    critical: str = "#d03b3b"
    deemphasis: str = "#898781"

    def color(self, i: int) -> str:
        """Categorical slot ``i``. Never cycles -- a 5th series is a bug."""
        if i >= len(self.series):
            raise ValueError(
                f"asked for categorical slot {i + 1} but this palette seats "
                f"{len(self.series)}. Do not generate a hue: fold the tail "
                "into 'other', facet into small multiples, or use emphasis "
                "(one series in slot 1, the rest in deemphasis gray).")
        return self.series[i]


LIGHT = Theme(
    name="light",
    surface="#fcfcfb", page="#f9f9f7",
    ink="#0b0b0b", secondary="#52514e", muted="#898781",
    grid="#e1e0d9", baseline="#c3c2b7",
    series=("#2a78d6", "#eb6834", "#1baf7a", "#eda100"),
    sequential=("#cde2fb", "#9ec5f4", "#5598e7", "#2a78d6", "#184f95"),
    diverging=("#2a78d6", "#f0efec", "#d03b3b"),
)

DARK = Theme(
    name="dark",
    surface="#1a1a19", page="#0d0d0d",
    ink="#ffffff", secondary="#c3c2b7", muted="#898781",
    grid="#2c2c2a", baseline="#383835",
    series=("#3987e5", "#d95926", "#199e70", "#c98500"),
    sequential=("#184f95", "#256abf", "#3987e5", "#6da7ec", "#b7d3f6"),
    diverging=("#3987e5", "#383835", "#d03b3b"),
)

THEMES = {"light": LIGHT, "dark": DARK}


def resolve_themes(choice: str) -> list[Theme]:
    if choice == "both":
        return [LIGHT, DARK]
    return [THEMES[choice]]


# ===========================================================================
# rcParams
# ===========================================================================

def _rc(t: Theme) -> dict:
    return {
        "figure.facecolor": t.surface,
        "figure.edgecolor": t.surface,
        "savefig.facecolor": t.surface,
        "savefig.edgecolor": t.surface,
        "axes.facecolor": t.surface,
        "axes.edgecolor": t.baseline,
        "axes.linewidth": HAIRLINE_W,
        "axes.labelcolor": t.secondary,
        "axes.titlecolor": t.ink,
        "axes.titlesize": 11.5,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 9,
        "axes.labelsize": 9.5,
        "axes.grid": True,
        "axes.grid.which": "major",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.color": t.grid,
        "grid.linestyle": "-",          # never dashed
        "grid.linewidth": HAIRLINE_W,
        "grid.alpha": 1.0,
        "xtick.color": t.muted,
        "ytick.color": t.muted,
        "xtick.labelcolor": t.secondary,
        "ytick.labelcolor": t.secondary,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "xtick.minor.size": 0,
        "ytick.minor.size": 0,
        "legend.frameon": False,
        "legend.fontsize": 8.5,
        "legend.labelcolor": t.secondary,
        "legend.handlelength": 1.6,
        "legend.borderpad": 0.2,
        "legend.columnspacing": 1.4,
        "lines.linewidth": LINE_W,
        "lines.solid_capstyle": "round",
        "lines.solid_joinstyle": "round",
        "lines.markersize": MARKER_SIZE,
        "font.family": "sans-serif",
        "font.sans-serif": FONT_STACK,
        "font.size": 9.5,
        "text.color": t.ink,
        "figure.dpi": DPI,
        "savefig.dpi": DPI,
        "figure.constrained_layout.use": True,
    }


@contextmanager
def theme(t: Theme):
    with plt.rc_context(_rc(t)):
        yield t


# ===========================================================================
# Figure furniture
# ===========================================================================

def title_block(ax, title: str, subtitle: Optional[str] = None) -> None:
    """Title on the axes; subtitle in secondary ink just beneath it.

    The title carries the identity of a single-series chart, which is why
    single-series figures here never get a one-swatch legend box.

    Both are placed in offset POINTS rather than axes fractions -- an axes
    fraction offset scales with panel height, so a subtitle that clears the
    title on a tall panel lands underneath it on a short one.
    """
    ax.set_title(title, pad=22 if subtitle else 9)
    if subtitle:
        ax.annotate(subtitle, xy=(0.0, 1.0), xycoords="axes fraction",
                    xytext=(0, 5), textcoords="offset points",
                    ha="left", va="bottom", fontsize=8.5,
                    color=plt.rcParams["axes.labelcolor"],
                    annotation_clip=False)


def reference_line(ax, y: float, label: str, t: Theme, *,
                   x: float = 0.99, va: str = "bottom", ha: str = "right",
                   color: Optional[str] = None) -> None:
    """A solid hairline threshold with its own label. Never dashed."""
    c = color or t.muted
    ax.axhline(y, color=c, linewidth=HAIRLINE_W, zorder=1.5)
    ax.text(x, y, label, transform=ax.get_yaxis_transform(),
            ha=ha, va=va, fontsize=8, color=t.secondary)


def vertical_marks(ax, xs: Sequence[float], t: Theme, *,
                   labels: Optional[Sequence[Optional[str]]] = None,
                   y_frac: float = 0.97, va: str = "top") -> None:
    """Annotation hairlines -- used for the mains harmonic comb.

    Label selectively: the caller passes None for the harmonics it does not
    want named. A number on every one of eight harmonics is unreadable.
    """
    for i, x in enumerate(xs):
        ax.axvline(x, color=t.grid, linewidth=HAIRLINE_W, zorder=1.2)
        lab = labels[i] if labels is not None else None
        if lab:
            ax.text(x, y_frac, f" {lab}", transform=ax.get_xaxis_transform(),
                    ha="left", va=va, fontsize=7.5, color=t.muted,
                    rotation=90)


def end_label(ax, x, y, text: str, t: Theme, *, color: Optional[str] = None,
              dx: float = 0.0, dy: float = 0.0) -> None:
    """Direct label at a line end. Text wears ink, never the series color."""
    ax.annotate(text, xy=(x, y), xytext=(6 + dx, dy),
                textcoords="offset points", ha="left", va="center",
                fontsize=8.5, color=t.secondary,
                annotation_clip=False)


def dot(ax, x, y, t: Theme, color: str) -> None:
    """End marker with a 2px surface ring, so it stays legible on a crossing."""
    ax.plot([x], [y], marker="o", color=color, markersize=MARKER_SIZE,
            markeredgecolor=t.surface, markeredgewidth=RING_W, zorder=5,
            linestyle="none")


def bars(ax, x, heights, t: Theme, color: str, *, width: float = 0.6,
         label: Optional[str] = None):
    """Bar marks with the surface gap between neighbours.

    DEVIATION, stated rather than silently taken: the mark spec asks for a 4px
    rounded data-end square at the baseline. matplotlib's bar primitive has no
    per-corner radius, and every workaround (FancyBboxPatch, hand-built Bezier
    paths) rounds in data units, so the corner distorts whenever the x and y
    scales differ -- which is always, on these axes. Square ends do not change
    how the chart reads; a skewed corner does. Everything else in the spec
    (thin marks, the 2px surface gap, no stroke around the mark, recessive
    grid) is honoured.
    """
    # Anchor at zero and grow with the tallest bar drawn so far on these axes.
    # A bare ax.set_ylim(bottom=0) on an empty axes freezes the limit at the
    # default (0, 1) and switches autoscaling off, so every later bar taller
    # than 1.0 is silently drawn off the top of the panel. That happened, and
    # it looked exactly like a set of bars that all happened to max out.
    h = float(np.nanmax(heights)) if len(heights) else 0.0
    prev = getattr(ax, "_bench_bar_max", 0.0)
    ax._bench_bar_max = max(prev, h)
    ax.set_ylim(0, max(ax._bench_bar_max * 1.18, 1e-12))
    return ax.bar(x, heights, width=width * 0.86, color=color,
                  edgecolor="none", zorder=3, label=label)


def category_axis(ax, keys: Sequence[float], *, min_slots: int = 5) -> None:
    """Give a small set of categories a sane x extent.

    Two categories on an auto-scaled axis get half the panel each, and a bar
    filling half a panel reads as a design element rather than a measurement.
    Reserving a minimum number of slots keeps the mark thin whether the
    spectrum contained two harmonics or eight.
    """
    ks = list(keys)
    if not ks:
        return
    ax.set_xticks(ks)
    ax.set_xlim(min(ks) - 0.65, max(max(ks), min(ks) + min_slots - 1) + 0.65)


def legend(ax, t: Theme, *, loc: str = "best", ncol: int = 1,
           handles: Optional[Iterable] = None) -> None:
    """Always present for two or more series; omitted for one."""
    if handles is not None:
        ax.legend(handles=list(handles), loc=loc, ncol=ncol)
    else:
        h, l = ax.get_legend_handles_labels()
        if len(h) >= 2:
            ax.legend(loc=loc, ncol=ncol)


def key_handle(label: str, color: str) -> Line2D:
    return Line2D([0], [0], color=color, linewidth=LINE_W, label=label)


# ===========================================================================
# Provenance -- badges and footer
# ===========================================================================

def badge(fig, text: str, t: Theme, kind: str = "warning") -> None:
    color = {"warning": t.warning, "critical": t.critical,
             "good": t.good, "serious": t.serious}[kind]
    glyph = {"warning": "!", "critical": "!!", "good": "ok",
             "serious": "!"}[kind]
    fig.text(0.995, 0.995, f"[{glyph}] {text}", ha="right", va="top",
             fontsize=8, color=color, weight="bold", zorder=10)


def footer(fig, meta: dict, t: Theme) -> None:
    """One line of provenance under every figure.

    Gain and its verification status are on the face of the figure because a
    figure outlives the terminal it was made in.
    """
    gain = meta.get("host_pga_gain", "?")
    verified = meta.get("gain_verified", False)
    lsb = meta.get("lsb_volts", 0.0) * 1e6
    src = meta.get("source", "?")
    bits = [
        f"PGA gain {gain} ({lsb:.5f} uV/count)",
        "gain verified" if verified else "GAIN NOT VERIFIED",
        f"source {src}",
        f"fs {meta.get('fs_hz', '?'):g} SPS",
        f"mains {meta.get('mains_hz', '?'):g} Hz",
        meta.get("timestamp_utc", ""),
        f"rev {meta.get('git_revision', '?')}",
    ]
    fig.text(0.005, 0.004, "  |  ".join(str(b) for b in bits if b),
             ha="left", va="bottom", fontsize=6.5, color=t.muted)


def stamp(fig, meta: dict, t: Theme, *, top: Optional[float] = None) -> None:
    """Footer, badges, and the layout margin they need.

    Reserving the strip explicitly is not cosmetic: without it the x-axis
    label of the bottom panel lands on top of the provenance line, and the
    provenance line is the part that says whether the gain was verified.
    """
    has_badge = bool(meta.get("synthetic")) or not meta.get("gain_verified", False)
    bottom = 0.035
    # `top` is an absolute figure fraction; matplotlib's rect wants a height,
    # and conflating the two put the panels back under the badge.
    top_f = top if top is not None else (0.962 if has_badge else 0.992)
    engine = fig.get_layout_engine()
    if engine is not None:
        try:
            engine.set(rect=(0.0, bottom, 1.0, max(top_f - bottom, 0.1)))
        except (AttributeError, TypeError):
            pass
    footer(fig, meta, t)
    if meta.get("synthetic"):
        badge(fig, "SYNTHETIC -- modelled, not measured", t, "warning")
    elif not meta.get("gain_verified", False):
        badge(fig, "GAIN NOT VERIFIED", t, "critical")


# ===========================================================================
# Saving
# ===========================================================================

def save(fig, stem: Path, t: Theme, *, also_pdf: bool = False) -> list[Path]:
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    written = []
    png = stem.with_name(f"{stem.name}_{t.name}.png")
    fig.savefig(png, dpi=DPI)
    written.append(png)
    if also_pdf:
        pdf = stem.with_name(f"{stem.name}_{t.name}.pdf")
        fig.savefig(pdf)
        written.append(pdf)
    plt.close(fig)
    return written


def render(build: Callable[[Theme], "plt.Figure"], stem: Path,
           themes: Sequence[Theme], *, also_pdf: bool = False) -> list[Path]:
    """Build the same figure once per theme. Steps are chosen per surface."""
    out: list[Path] = []
    for t in themes:
        with theme(t):
            fig = build(t)
            out.extend(save(fig, stem, t, also_pdf=also_pdf))
    return out


def log_written(paths: Iterable[Path]) -> None:
    for p in paths:
        print(f"  wrote {p}")
