"""
AER-style matplotlib configuration for Arbitrum DAO governance paper.

Usage in figure scripts:
    from aer_style import apply_aer_style, despine, COLORS, savefig

Call apply_aer_style() once at module level after importing matplotlib.
"""

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ── Color palette ──────────────────────────────────────────────────────────────
# Colorblind-safe palette (Wong 2011), limited to 5 for AER aesthetics
COLORS = {
    "black":       "#000000",
    "blue":        "#0072B2",
    "orange":      "#E69F00",
    "green":       "#009E73",
    "red":         "#D55E00",
    "sky":         "#56B4E9",
    "gray":        "#666666",
    "lightgray":   "#CCCCCC",
    "fill":        "#E8E8E8",   # for shaded confidence bands
}

# Semantic aliases for this paper
C_HUMAN = COLORS["blue"]
C_AI    = COLORS["red"]
C_TOTAL = COLORS["gray"]
C_SHOCK = COLORS["gray"]


# ── rcParams ───────────────────────────────────────────────────────────────────
AER_RC = {
    # Font
    "font.family":        "serif",
    "font.serif":         ["Times New Roman", "DejaVu Serif", "Computer Modern Roman"],
    "font.size":          10,
    "axes.titlesize":     10,
    "axes.labelsize":     10,
    "xtick.labelsize":    9,
    "ytick.labelsize":    9,
    "legend.fontsize":    9,
    "figure.titlesize":   11,

    # Lines
    "lines.linewidth":    1.5,
    "lines.markersize":   5,
    "patch.linewidth":    0.5,

    # Axes
    "axes.linewidth":     0.8,
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.grid":          True,
    "grid.color":         "#DDDDDD",
    "grid.linewidth":     0.5,
    "grid.linestyle":     "--",
    "grid.alpha":         1.0,

    # Ticks
    "xtick.direction":    "out",
    "ytick.direction":    "out",
    "xtick.major.width":  0.8,
    "ytick.major.width":  0.8,
    "xtick.major.size":   4,
    "ytick.major.size":   4,

    # Legend
    "legend.frameon":       True,
    "legend.framealpha":    0.9,
    "legend.edgecolor":     "#CCCCCC",
    "legend.handlelength":  1.5,

    # Figure
    "figure.dpi":           150,
    "savefig.dpi":          300,
    "savefig.bbox":         "tight",
    "savefig.pad_inches":   0.05,
}


def apply_aer_style():
    """Apply AER rcParams globally. Call once per script after importing matplotlib."""
    mpl.rcParams.update(AER_RC)


def despine(ax, left=False):
    """Remove top and right spines. Optionally keep left spine."""
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    if left:
        ax.spines["left"].set_visible(False)
        ax.yaxis.set_ticks_position("none")


def add_shock_lines(ax, events, transform=None, fontsize=8, va="top"):
    """
    Draw vertical dashed lines for AI model release dates.

    events: list of (pd.Timestamp, label) tuples
    transform: axis transform for text; defaults to ax.get_xaxis_transform()
    """
    if transform is None:
        transform = ax.get_xaxis_transform()
    for dt, label in events:
        ax.axvline(dt, color=C_SHOCK, linewidth=0.9, linestyle="--", alpha=0.7, zorder=2)
        ax.text(dt, 0.96, label, transform=transform, rotation=90,
                va=va, ha="right", fontsize=fontsize, color=C_SHOCK,
                style="italic")


def add_corr_box(ax, r, p, n, loc="upper right"):
    """Add a small annotation box with correlation, p-value, and n."""
    stars = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    text = f"$r = {r:+.3f}${stars}\n$n = {n}$"
    props = dict(boxstyle="round,pad=0.3", facecolor="white",
                 edgecolor="#CCCCCC", alpha=0.9)
    x = 0.97 if "right" in loc else 0.03
    y = 0.97 if "upper" in loc else 0.05
    ha = "right" if "right" in loc else "left"
    va = "top" if "upper" in loc else "bottom"
    ax.text(x, y, text, transform=ax.transAxes, fontsize=9,
            ha=ha, va=va, bbox=props, family="monospace")


def savefig(fig, path, **kwargs):
    """Save figure with AER defaults. Path should be absolute."""
    fig.savefig(path, dpi=300, bbox_inches="tight", **kwargs)
    print(f"Saved → {path}")
