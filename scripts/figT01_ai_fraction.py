#!/usr/bin/env python3
"""
figT01_ai_fraction.py
Monthly AI fraction from Pangram scores — bar chart + data table.
"""

import duckdb, os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker

HERE     = os.path.dirname(os.path.abspath(__file__))
ROOT     = os.path.dirname(HERE)   # project root
DB_PATH  = os.path.join(ROOT, "data", "arbitrum.db")
OUT_DIR  = os.path.join(ROOT, "output", "tables")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, "figT01_ai_fraction.png")

# ── query ─────────────────────────────────────────────────────────────────────
con = duckdb.connect(DB_PATH, read_only=True)
monthly = con.execute("""
    SELECT
        date_trunc('month', CAST(p.created_at AS TIMESTAMP)) AS month,
        COUNT(*)                                              AS total_posts,
        COUNT(*) FILTER (WHERE s.fraction_ai > 0.70)         AS ai_posts,
        AVG(s.fraction_ai)                                   AS avg_fai,
        COUNT(DISTINCT p.username)                           AS users,
        COUNT(DISTINCT CASE WHEN s.fraction_ai > 0.70
              THEN p.username END)                           AS ai_users
    FROM posts p
    JOIN post_ai_scores s ON p.id = s.post_id
    WHERE s.fraction_ai IS NOT NULL
      AND s.headline NOT LIKE 'error:%'
      AND s.headline != 'too_short'
      AND CAST(p.created_at AS TIMESTAMP) >= '2023-01-01'
    GROUP BY 1
    ORDER BY 1
""").df()
con.close()

monthly["month_dt"]  = pd.to_datetime(monthly["month"])
monthly["ai_pct"]    = monthly["ai_posts"] / monthly["total_posts"] * 100
monthly["month_lbl"] = monthly["month_dt"].dt.strftime("%b '%y")

# Key dates
BREAKS = [
    ("2023-03-14", "GPT-4",         "#8E44AD"),
    ("2023-11-06", "GPT-4 Turbo",   "#E67E22"),
    ("2023-11-25", "QLR break",     "#E74C3C"),
    ("2024-03-04", "Claude 3",      "#2980B9"),
    ("2024-05-13", "GPT-4o",        "#1ABC9C"),
    ("2025-01-20", "DeepSeek R1",   "#95A5A6"),
]
break_dts = [(pd.Timestamp(d), lbl, c) for d, lbl, c in BREAKS]

# ── layout: bar chart (top) + table (bottom) ──────────────────────────────────
fig = plt.figure(figsize=(18, 11))
ax_bar = fig.add_axes([0.06, 0.42, 0.92, 0.50])   # bar chart
ax_tbl = fig.add_axes([0.06, 0.00, 0.92, 0.38])   # table
ax_tbl.axis("off")

# ── bar chart ─────────────────────────────────────────────────────────────────
x   = np.arange(len(monthly))
w   = 0.72
clr = ["#E74C3C" if v >= 10 else "#2980B9" if v >= 6 else "#AED6F1"
       for v in monthly["ai_pct"]]

bars = ax_bar.bar(x, monthly["ai_pct"], width=w, color=clr, alpha=0.88, zorder=3)

# shade post-Claude 3 region
claude3_idx = monthly[monthly["month_dt"] >= pd.Timestamp("2024-03-01")].index
if len(claude3_idx):
    first = int(monthly.index.get_loc(claude3_idx[0]))
    ax_bar.axvspan(first - 0.5, len(monthly) - 0.5,
                   color="#FEF9E7", alpha=0.5, zorder=1)

# vertical lines for key dates
used_y = {}
for dt, lbl, c in break_dts:
    if dt < monthly["month_dt"].min() or dt > monthly["month_dt"].max():
        continue
    # find nearest month index
    diffs = (monthly["month_dt"] - dt).abs()
    xi = float(diffs.idxmin())
    ax_bar.axvline(xi, color=c, linewidth=1.6, linestyle="--", alpha=0.85, zorder=4)
    # stagger label heights to avoid overlap
    base_y = monthly["ai_pct"].max() * 1.02
    offset = used_y.get(round(xi), 0)
    ax_bar.text(xi + 0.15, base_y + offset, lbl,
                rotation=90, fontsize=7.5, color=c, va="bottom", zorder=5)
    used_y[round(xi)] = offset + monthly["ai_pct"].max() * 0.12

ax_bar.set_xticks(x[::2])
ax_bar.set_xticklabels(monthly["month_lbl"].iloc[::2], rotation=45, ha="right", fontsize=7.5)
ax_bar.set_ylabel("% of posts scored AI (fraction_ai > 0.70)", fontsize=10)
ax_bar.set_title(
    "AI-Written Post Fraction by Month — Arbitrum DAO Forum\n"
    "Pangram AI detection  |  Threshold: fraction_ai > 0.70  |  "
    "Structural break (QLR) Nov 25, 2023 predates meaningful AI surge",
    fontsize=10.5, fontweight="bold", loc="left"
)
ax_bar.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax_bar.set_xlim(-0.6, len(monthly) - 0.4)
ax_bar.set_ylim(0, monthly["ai_pct"].max() * 1.55)
ax_bar.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.5, zorder=0)

# legend
legend_h = [
    mpatches.Patch(color="#E74C3C", alpha=0.88, label="AI% ≥ 10%  (high)"),
    mpatches.Patch(color="#2980B9", alpha=0.88, label="AI% 6–10%  (moderate)"),
    mpatches.Patch(color="#AED6F1", alpha=0.88, label="AI% < 6%   (low)"),
    mpatches.Patch(color="#FEF9E7", alpha=0.8,  label="Post-Claude 3 region"),
] + [mpatches.Patch(color=c, label=lbl) for _, lbl, c in break_dts]
ax_bar.legend(handles=legend_h, fontsize=7.5, loc="upper left",
              ncol=2, framealpha=0.92)

# ── table ─────────────────────────────────────────────────────────────────────
col_labels = ["Month", "Total\nposts", "AI\nposts", "AI%",
              "Avg\nfrac_ai", "Unique\nusers", "AI\nusers", "Note"]

def make_note(row):
    m = row["month_dt"]
    notes = []
    for dt, lbl, _ in break_dts:
        if abs((m - dt).days) <= 15:
            notes.append(lbl)
    if m >= pd.Timestamp("2024-03-01") and not notes:
        notes.append("post-Claude 3")
    return " | ".join(notes) if notes else ""

monthly["note"] = monthly.apply(make_note, axis=1)

table_data = []
for _, r in monthly.iterrows():
    table_data.append([
        r["month_lbl"],
        f"{int(r['total_posts']):,}",
        f"{int(r['ai_posts']):,}",
        f"{r['ai_pct']:.1f}%",
        f"{r['avg_fai']:.3f}",
        f"{int(r['users']):,}",
        f"{int(r['ai_users']):,}",
        r["note"],
    ])

tbl = ax_tbl.table(
    cellText=table_data,
    colLabels=col_labels,
    loc="upper center",
    cellLoc="center",
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(7.2)
tbl.scale(1.0, 1.18)

# Color header
for j in range(len(col_labels)):
    tbl[0, j].set_facecolor("#2C3E50")
    tbl[0, j].set_text_props(color="white", fontweight="bold")

# Color rows by AI% and note
note_col_idx = len(col_labels) - 1
for i, (_, r) in enumerate(monthly.iterrows(), start=1):
    row_color = "white"
    if r["ai_pct"] >= 10:
        row_color = "#FADBD8"   # light red
    elif r["note"] and any(lbl in r["note"] for _, lbl, _ in break_dts[:4]):
        row_color = "#FEF9E7"   # light yellow for shock months

    for j in range(len(col_labels)):
        tbl[i, j].set_facecolor(row_color)
        if j == note_col_idx and r["note"]:
            tbl[i, j].set_text_props(color="#E74C3C", fontweight="bold")

# Column widths
tbl.auto_set_column_width(list(range(len(col_labels))))

fig.suptitle(
    "Figure: Pangram AI Detection — Monthly AI Post Fraction, Arbitrum DAO 2023–2026\n"
    "Key finding: structural break (Nov 2023 / Mar 2024) PRECEDES meaningful AI volume surge (mid-2024+)",
    fontsize=11, fontweight="bold", y=0.98
)

fig.savefig(OUT_PATH, dpi=180, bbox_inches="tight")
print(f"Saved → {OUT_PATH}")
