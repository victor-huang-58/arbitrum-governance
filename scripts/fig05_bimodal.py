#!/usr/bin/env python3
"""
Figure 5: Bimodal Distribution of AI-Detection Scores (main_flat.tex fig:dip)
Histogram of Pangram fraction_ai scores.

NOTE: despite the original filename, no Hartigan dip-test statistic is
computed here -- only descriptive percentages (share scoring exactly 0,
exactly 1, and intermediate). The output is also unrelated to
scripts/fig05_dip_test.py, which is a different figure (the Delegate
Incentive Program participation test) that happens to share the "fig05"
numbering. Renamed/relocated to output/figures/ to avoid the two scripts
colliding on the same output filename.
"""
import os, sys
import duckdb
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aer_style import apply_aer_style, despine, savefig as aer_savefig
apply_aer_style()

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR  = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, "fig05_ai_score_bimodality.png")

DB_PATH = os.path.join(ROOT, "data", "arbitrum.db")
con = duckdb.connect(DB_PATH, read_only=True)

scores = con.execute(
    "SELECT fraction_ai FROM post_ai_scores WHERE fraction_ai IS NOT NULL AND word_count >= 20"
).df()["fraction_ai"].values

con.close()

# ── Hartigan dip test (pure Python, no diptest package needed) ────────────────
# Simple approximation: bimodality index = (skewness^2 + 1) / kurtosis
# We report the result visually and note the statistic in the caption.

fig, axes = plt.subplots(1, 2, figsize=(11, 4),
                         gridspec_kw={"width_ratios": [2, 1]})

bins = np.linspace(0, 1, 51)
threshold = 0.70

# ── Left panel: full distribution, log y-axis ─────────────────────────────────
ax = axes[0]
counts, edges, patches = ax.hist(scores, bins=bins, color="#4B6FA8", edgecolor="white",
                                  linewidth=0.4, zorder=2)
for patch, left in zip(patches, edges[:-1]):
    if left >= threshold:
        patch.set_facecolor("#C0392B")

ax.set_yscale("log")
ax.axvline(threshold, color="black", lw=1.2, ls="--")
ax.set_xlabel(r"Pangram $\mathit{fraction\_ai}$ score", fontsize=10)
ax.set_ylabel("Number of posts (log scale)", fontsize=10)
ax.set_xlim(0, 1)
ax.set_title("Full distribution (log scale)", fontsize=9, pad=4)

pct_lo = np.mean(scores == 0.0) * 100
pct_hi = np.mean(scores == 1.0) * 100
pct_mid = 100 - pct_lo - pct_hi
ax.text(0.03, 0.97, f"{pct_lo:.0f}% score exactly 0\n(classified Human)",
        transform=ax.transAxes, ha="left", va="top", fontsize=8, color="#4B6FA8")
ax.text(0.97, 0.97, f"{pct_hi:.0f}% score exactly 1\n(classified AI)",
        transform=ax.transAxes, ha="right", va="top", fontsize=8, color="#C0392B")
ax.text(0.50, 0.20, f"{pct_mid:.1f}% intermediate",
        transform=ax.transAxes, ha="center", va="bottom", fontsize=8, color="gray")
despine(ax)

# ── Right panel: zoom into intermediate (0 < score < 1) ──────────────────────
ax2 = axes[1]
mid = scores[(scores > 0) & (scores < 1)]
bins_mid = np.linspace(0, 1, 26)
counts2, edges2, patches2 = ax2.hist(mid, bins=bins_mid, color="#7B9DC7",
                                      edgecolor="white", linewidth=0.4)
for patch, left in zip(patches2, edges2[:-1]):
    if left >= threshold:
        patch.set_facecolor("#E07070")

ax2.axvline(threshold, color="black", lw=1.2, ls="--",
            label=f"Threshold ({threshold})")
ax2.set_xlabel(r"$\mathit{fraction\_ai}$ score", fontsize=10)
ax2.set_ylabel("Posts", fontsize=10)
ax2.set_title(f"Intermediate values only\n(n = {len(mid):,}; {pct_mid:.1f}% of corpus)",
              fontsize=9, pad=4)
ax2.legend(fontsize=8, frameon=False)
despine(ax2)

fig.suptitle("Distribution of Pangram AI-Detection Scores — Arbitrum DAO Forum Posts",
             fontsize=11, y=1.01)
plt.tight_layout()
aer_savefig(fig, OUT_PATH)
print(f"Saved to {OUT_PATH}  (n={len(scores):,}; intermediate={len(mid):,})")
