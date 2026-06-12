#!/usr/bin/env python3
"""
Figure — Top DAO Treasuries, Mid-2024
Panel A: grouped bar per DAO, stacked by asset type
Panel B: single stacked bar, each DAO a distinct color
Source: DeFiLlama treasury data, accessed June 2024.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from pathlib import Path

OUT_PNG     = "output/figures/fig_dao_treasuries.png"
OUT_PNG_ALT = "fig_dao_treasuries.png"

# ── Data (DeFiLlama, mid-2024 snapshot, USD millions) ─────────────────────────
# (name, native_token, stablecoins_and_other)
daos_raw = [
    ("Arbitrum",  2_950, 550),
    ("Uniswap",   2_800, 350),
    ("Optimism",    720, 180),
    ("Aave",        380, 170),
    ("MakerDAO",     80, 290),
    ("Compound",    100,  60),
    ("dYdX",         70,  60),
    ("ENS",          60,  45),
    ("Lido",         50,  45),
    ("Nouns",        25,  20),
]

labels = [d[0] for d in daos_raw]
native = np.array([d[1] for d in daos_raw], dtype=float)
other  = np.array([d[2] for d in daos_raw], dtype=float)
total  = native + other

# Sort descending by total
order  = np.argsort(total)[::-1]
labels = [labels[i] for i in order]
native = native[order]
other  = other[order]
total  = total[order]

# ── Colour palette — one distinct colour per DAO ──────────────────────────────
DAO_COLORS = [
    "#183151",  # Arbitrum   — dark navy
    "#E07B39",  # Uniswap    — orange
    "#C0392B",  # Optimism   — red
    "#2980B9",  # Aave       — blue
    "#27AE60",  # MakerDAO   — green
    "#8E44AD",  # Compound   — purple
    "#16A085",  # dYdX       — teal
    "#D4AC0D",  # ENS        — gold
    "#884EA0",  # Lido       — violet
    "#717D7E",  # Nouns      — grey
]

ASSET_COLORS = ["#183151", "#7BA7BC"]   # Panel A: native / other

# ── Figure: two panels ────────────────────────────────────────────────────────
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5),
                                gridspec_kw={"width_ratios": [3, 1]})

# ── Panel A: grouped bars stacked by asset type ───────────────────────────────
x     = np.arange(len(labels))
width = 0.6

ax1.bar(x, native / 1000, width, color=ASSET_COLORS[0], label="Native governance token")
ax1.bar(x, other  / 1000, width, bottom=native / 1000,
        color=ASSET_COLORS[1], label="Stablecoins & other assets")

for i, t in enumerate(total):
    ax1.text(i, t / 1000 + 0.05, f"${t/1000:.1f}B", ha="center", va="bottom",
             fontsize=8, fontweight="bold", color="#333333")

ax1.set_xticks(x)
ax1.set_xticklabels(labels, fontsize=10)
ax1.set_ylabel("Treasury value (USD billions)", fontsize=11)
ax1.set_title("By DAO, split by asset type", fontsize=11, fontweight="bold")
ax1.set_ylim(0, max(total) / 1000 * 1.20)
ax1.yaxis.grid(True, alpha=0.3, zorder=0)
ax1.set_axisbelow(True)
ax1.spines["top"].set_visible(False)
ax1.spines["right"].set_visible(False)
ax1.legend(fontsize=9, loc="upper right", framealpha=0.9)

# ── Panel B: single stacked bar, each DAO a distinct colour ──────────────────
bottom = 0.0
for i, (lbl, t, col) in enumerate(zip(labels, total, DAO_COLORS)):
    ax2.bar(0, t / 1000, width=0.5, bottom=bottom, color=col, label=lbl)
    mid = bottom + t / 2000
    if t / 1000 > 0.12:   # only label segments large enough to read
        ax2.text(0, mid, f"{lbl}\n${t/1000:.1f}B",
                 ha="center", va="center", fontsize=8,
                 color="white", fontweight="bold")
    bottom += t / 1000

ax2.set_xticks([])
ax2.set_ylabel("Treasury value (USD billions)", fontsize=11)
ax2.set_title("Combined", fontsize=11, fontweight="bold")
ax2.set_ylim(0, bottom * 1.06)
ax2.yaxis.grid(True, alpha=0.3, zorder=0)
ax2.set_axisbelow(True)
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)
ax2.text(0, bottom * 1.03, f"${bottom:.1f}B",
         ha="center", va="bottom", fontsize=10, fontweight="bold")

# ── Shared title & source ─────────────────────────────────────────────────────
fig.suptitle("Treasury Assets of the Ten Largest DAOs, Mid-2024",
             fontsize=13, fontweight="bold", y=1.01)
fig.text(0.99, -0.02, "Source: DeFiLlama, June 2024",
         ha="right", fontsize=8, color="gray")

fig.tight_layout()

for out in [OUT_PNG, OUT_PNG_ALT]:
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved: {out}")

print(f"\nTotal (top 10): ${total.sum()/1000:.2f}B")
