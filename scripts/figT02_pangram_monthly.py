#!/usr/bin/env python3
"""
figT02_pangram_monthly.py
Clean standalone table PNG — monthly Pangram AI scores.
"""

import duckdb, os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE     = os.path.dirname(os.path.abspath(__file__))
ROOT     = os.path.dirname(HERE)   # project root
DB_PATH  = os.path.join(ROOT, "data", "arbitrum.db")
OUT_DIR  = os.path.join(ROOT, "output", "tables")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, "figT02_pangram_monthly.png")

con = duckdb.connect(DB_PATH, read_only=True)
monthly = con.execute("""
    SELECT
        date_trunc('month', CAST(p.created_at AS TIMESTAMP)) AS month,
        COUNT(*)                                             AS total_posts,
        COUNT(*) FILTER (WHERE s.fraction_ai > 0.70)        AS ai_posts,
        COUNT(*) FILTER (WHERE s.fraction_ai <= 0.70)       AS human_posts,
        AVG(s.fraction_ai)                                  AS avg_fai,
        COUNT(DISTINCT p.username)                          AS users,
        COUNT(DISTINCT CASE WHEN s.fraction_ai > 0.70
              THEN p.username END)                          AS ai_users
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

monthly["month_dt"] = pd.to_datetime(monthly["month"])
monthly["ai_pct"]   = monthly["ai_posts"] / monthly["total_posts"] * 100
monthly["lbl"]      = monthly["month_dt"].dt.strftime("%b %Y")

# ── event annotations ─────────────────────────────────────────────────────────
EVENTS = {
    "2023-03": "GPT-4",
    "2023-07": "Claude 2",
    "2023-11": "GPT-4 Turbo  ← QLR break",
    "2024-03": "Claude 3",
    "2024-05": "GPT-4o",
    "2025-01": "DeepSeek R1",
}

def get_event(dt):
    key = dt.strftime("%Y-%m")
    return EVENTS.get(key, "")

monthly["event"] = monthly["month_dt"].apply(get_event)

# ── build table rows ──────────────────────────────────────────────────────────
col_headers = [
    "Month", "Total\nPosts", "Human\nPosts", "AI\nPosts",
    "AI %", "Avg\nFrac_AI", "Unique\nUsers", "AI\nUsers", "Event / Note"
]

rows = []
for _, r in monthly.iterrows():
    rows.append([
        r["lbl"],
        f"{int(r['total_posts']):,}",
        f"{int(r['human_posts']):,}",
        f"{int(r['ai_posts']):,}",
        f"{r['ai_pct']:.1f}%",
        f"{r['avg_fai']:.3f}",
        f"{int(r['users']):,}",
        f"{int(r['ai_users']):,}",
        r["event"],
    ])

n_rows = len(rows)
n_cols = len(col_headers)

# ── figure sizing ─────────────────────────────────────────────────────────────
row_h   = 0.28      # inches per data row
head_h  = 0.55      # header height
fig_h   = head_h + n_rows * row_h + 1.0   # +1 for title/footer
fig_w   = 16

fig, ax = plt.subplots(figsize=(fig_w, fig_h))
ax.axis("off")

tbl = ax.table(
    cellText=rows,
    colLabels=col_headers,
    loc="upper center",
    cellLoc="center",
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(8.5)

# Row height
for (row, col), cell in tbl.get_celld().items():
    if row == 0:
        cell.set_height(head_h / fig_h)
    else:
        cell.set_height(row_h / fig_h)

# ── colours ───────────────────────────────────────────────────────────────────
HEADER_BG  = "#1A252F"
HEADER_FG  = "white"
EVENT_BG   = "#FDF2E9"    # warm yellow — shock month
HIGH_AI_BG = "#FADBD8"    # light red — AI% >= 10
ALT_BG     = "#F2F3F4"    # light grey alternating
WHITE      = "white"
EVENT_FG   = "#C0392B"    # dark red text for event column

# header
for j in range(n_cols):
    cell = tbl[0, j]
    cell.set_facecolor(HEADER_BG)
    cell.set_text_props(color=HEADER_FG, fontweight="bold", fontsize=8.5)
    cell.set_edgecolor("#2C3E50")

# data rows
for i, (_, r) in enumerate(monthly.iterrows(), start=1):
    has_event = bool(r["event"])
    high_ai   = r["ai_pct"] >= 10.0
    alt       = (i % 2 == 0)

    if high_ai and has_event:
        bg = "#F1948A"          # strong red — high AI AND shock
    elif high_ai:
        bg = HIGH_AI_BG
    elif has_event:
        bg = EVENT_BG
    elif alt:
        bg = ALT_BG
    else:
        bg = WHITE

    for j in range(n_cols):
        cell = tbl[i, j]
        cell.set_facecolor(bg)
        cell.set_edgecolor("#D5D8DC")
        # event column text colour
        if j == n_cols - 1 and has_event:
            cell.set_text_props(color=EVENT_FG, fontweight="bold", fontsize=8)

# column widths (proportional)
col_widths = [0.09, 0.08, 0.08, 0.08, 0.07, 0.09, 0.09, 0.08, 0.24]
for j, w in enumerate(col_widths):
    for i in range(n_rows + 1):
        tbl[i, j].set_width(w)

# ── title / footer ────────────────────────────────────────────────────────────
fig.text(0.5, 0.995,
         "Arbitrum DAO Forum — Monthly AI Post Fraction (Pangram Detection, 2023–2026)",
         ha="center", va="top", fontsize=12, fontweight="bold", color="#1A252F")

fig.text(0.5, 0.002,
         "AI threshold: fraction_ai > 0.70  |  Source: Pangram API scores on 17,553 posts  |  "
         "Key finding: QLR structural break (Nov 2023) and Claude 3 break (Mar 2024) precede "
         "the meaningful AI volume surge (mid-2024 onward)",
         ha="center", va="bottom", fontsize=7.5, color="#555555", style="italic")

# colour legend
legend_items = [
    (HIGH_AI_BG, "AI% ≥ 10%"),
    (EVENT_BG,   "AI shock month"),
    ("#F1948A",  "AI% ≥ 10% + shock month"),
    (ALT_BG,     "Alternating rows"),
]
x_leg = 0.01
for bg, label in legend_items:
    fig.add_artist(plt.Rectangle((x_leg, 0.005), 0.012, 0.012,
                                  transform=fig.transFigure,
                                  facecolor=bg, edgecolor="#555", linewidth=0.6))
    fig.text(x_leg + 0.014, 0.011, label, va="center", fontsize=7, color="#333")
    x_leg += 0.13

fig.savefig(OUT_PATH, dpi=180, bbox_inches="tight", facecolor="white")
print(f"Saved → {OUT_PATH}")
