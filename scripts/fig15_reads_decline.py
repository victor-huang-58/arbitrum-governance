#!/usr/bin/env python3
"""
Figure 15 — Forum Readership Decline: Direct Behavioral Evidence

Monthly median reads per human-authored post on matched governance proposal
threads. Measures actual delegate/voter engagement, not inferred behavior.
"""

import duckdb
import json
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
DB_PATH      = "data/arbitrum.db"
FORUM_CACHE  = "data/figure8_forum_cache.json"
OUT_PNG      = "fig15_reads_decline.png"
OUT_PNG_ALT  = "output/figures/fig15_reads_decline.png"

GPT4T_DATE   = pd.Timestamp("2023-11-06", tz="UTC")   # GPT-4 Turbo release
CLAUDE3_DATE = pd.Timestamp("2024-03-04", tz="UTC")   # Claude 3 (main break)
HUMAN_THRESH = 0.30
MIN_WORDS    = 20
MIN_MONTH_N  = 5   # drop months with fewer than this many human posts

# ── Load data ─────────────────────────────────────────────────────────────────
con = duckdb.connect(DB_PATH, read_only=True)

q = """
SELECT p.id, p.created_at, p.reads, p.topic_id, pas.fraction_ai, pas.word_count
FROM posts p
JOIN post_ai_scores pas ON p.id = pas.post_id
WHERE pas.fraction_ai IS NOT NULL AND pas.word_count >= {}
""".format(MIN_WORDS)

df = con.execute(q).fetchdf()
df["created_at"] = pd.to_datetime(df["created_at"], utc=True)

# ── Matched proposal topics ───────────────────────────────────────────────────
cache    = json.loads(Path(FORUM_CACHE).read_text())
topic_ids = set(int(k) for k in cache.keys())

prop_df = df[df["topic_id"].isin(topic_ids)].copy()
prop_df  = prop_df[prop_df["fraction_ai"] < HUMAN_THRESH].copy()   # human only

import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    prop_df["month"] = prop_df["created_at"].dt.to_period("M")

# Monthly stats
monthly = (
    prop_df.groupby("month")
    .agg(n=("id", "count"), median_reads=("reads", "median"), mean_reads=("reads", "mean"))
    .reset_index()
)
monthly = monthly[monthly["n"] >= MIN_MONTH_N].copy()
monthly["month_ts"] = monthly["month"].dt.to_timestamp()

# Restrict to study window
monthly = monthly[
    (monthly["month_ts"] >= pd.Timestamp("2023-01-01")) &
    (monthly["month_ts"] <= pd.Timestamp("2025-06-01"))
].copy()

# Use tz-naive timestamps throughout for plotting (month_ts is tz-naive)
GPT4T_NAIVE   = GPT4T_DATE.tz_localize(None)
CLAUDE3_NAIVE = CLAUDE3_DATE.tz_localize(None)

# Pre / post colours
pre_mask  = monthly["month_ts"] < CLAUDE3_NAIVE
post_mask = ~pre_mask

# ── Means for annotation ──────────────────────────────────────────────────────
pre_med  = prop_df[prop_df["created_at"] < CLAUDE3_DATE]["reads"].median()
post_med = prop_df[prop_df["created_at"] >= CLAUDE3_DATE]["reads"].median()
pct_drop = (pre_med - post_med) / pre_med * 100

# ── Plot ──────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 4.5))

# Bar chart by month coloured by period
bar_colors = ["#4878CF" if p else "#D65F5F" for p in pre_mask]
ax.bar(monthly["month_ts"], monthly["median_reads"], width=25,
       color=bar_colors, alpha=0.75, zorder=2)

# Smoothed trend (5-month centred rolling)
monthly_sorted = monthly.sort_values("month_ts")
rolling = monthly_sorted["median_reads"].rolling(5, center=True, min_periods=2).mean()
ax.plot(monthly_sorted["month_ts"], rolling, color="#333333",
        linewidth=2, zorder=3, label="5-month moving average")

# Event lines
ax.axvline(GPT4T_NAIVE,   color="#E07B39", linewidth=1.5, linestyle="--", zorder=4)
ax.axvline(CLAUDE3_NAIVE, color="#B03A2E", linewidth=1.5, linestyle="--", zorder=4)

# Pre / post horizontal means
pre_months  = monthly_sorted[monthly_sorted["month_ts"] < CLAUDE3_NAIVE]["month_ts"]
post_months = monthly_sorted[monthly_sorted["month_ts"] >= CLAUDE3_NAIVE]["month_ts"]
if len(pre_months):
    ax.hlines(pre_med, pre_months.iloc[0], CLAUDE3_NAIVE,
              colors="#4878CF", linewidth=1.5, linestyle=":", zorder=3)
if len(post_months):
    ax.hlines(post_med, CLAUDE3_NAIVE, post_months.iloc[-1],
              colors="#D65F5F", linewidth=1.5, linestyle=":", zorder=3)

# Annotations for event lines
ymax = ax.get_ylim()[1]
ax.text(GPT4T_NAIVE, ymax * 0.97, "GPT-4 Turbo\n(Nov 2023)",
        ha="center", va="top", fontsize=8, color="#E07B39",
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))
ax.text(CLAUDE3_NAIVE, ymax * 0.97, "Claude 3\n(Mar 2024)",
        ha="center", va="top", fontsize=8, color="#B03A2E",
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=0.8))

# Period mean annotations
ax.text(pd.Timestamp("2023-07-01"), pre_med + 3,
        f"Pre median: {pre_med:.0f}", fontsize=8, color="#4878CF", va="bottom")
ax.text(pd.Timestamp("2024-09-01"), post_med + 3,
        f"Post median: {post_med:.0f}", fontsize=8, color="#D65F5F", va="bottom")

# Legend
pre_patch  = mpatches.Patch(color="#4878CF", alpha=0.75, label="Pre-shock (before Claude 3)")
post_patch = mpatches.Patch(color="#D65F5F", alpha=0.75, label="Post-shock (after Claude 3)")
ax.legend(handles=[pre_patch, post_patch], loc="upper right", fontsize=8, framealpha=0.9)

ax.set_xlabel("Month", fontsize=10)
ax.set_ylabel("Median reads per human post", fontsize=10)
ax.set_title(
    f"Forum Readership Decline on Governance Proposal Threads\n"
    f"Median reads per human-authored post fell {pct_drop:.0f}% post-shock "
    f"({pre_med:.0f} → {post_med:.0f})",
    fontsize=11
)
ax.set_xlim(pd.Timestamp("2023-01-01").tz_localize(None),
            pd.Timestamp("2025-07-01").tz_localize(None))
ax.yaxis.grid(True, alpha=0.3, zorder=0)
ax.set_axisbelow(True)
fig.tight_layout()

for out in [OUT_PNG, OUT_PNG_ALT]:
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved: {out}")

print(f"\nKey stats:")
print(f"  Pre-break median reads/post:  {pre_med:.1f}")
print(f"  Post-break median reads/post: {post_med:.1f}")
print(f"  Decline: {pct_drop:.1f}%")
print(f"\nMonthly data:")
print(monthly[["month_ts", "n", "median_reads"]].to_string(index=False))
