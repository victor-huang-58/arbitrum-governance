#!/usr/bin/env python3
"""
Figure 6: The Vote Rental Market — LobbyFi on Arbitrum DAO
Journal of Finance paper on Arbitrum governance.

LobbyFi is a protocol that aggregates delegated ARB voting power and
auctions it to the highest bidder on a per-proposal basis.  Token holders
earn yield by delegating; buyers direct votes for a fee.

Voter proxy address:  0x7a45eE0be5C4BdC938A5F00A2AEF393f46502D26
  (identified as the top voter on the April 2025 OAT election with
   exactly 19.30M ARB VP cast in a single direction for choice 8 only —
   consistent with a pooled auction mechanism)

Three phases visible in the data:
  Phase 1 (Jul 2024 – Jan 2025)   Pilot — ~1M ARB, ~0.6% of votes
  Phase 2 (Feb 2025 – Oct 2025)   Scale-up — 13–21M ARB, 8–14% of votes
  Phase 3 (Nov 2025 – present)    Dormant — zero votes cast
"""

import os
import requests
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys as _sys
_sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, C_TOTAL, C_SHOCK, savefig as aer_savefig
import freeze
apply_aer_style()
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
import matplotlib.patches as mpatches

HERE     = os.path.dirname(os.path.abspath(__file__))
ROOT     = os.path.dirname(HERE)   # project root
OUT_DIR  = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH     = os.path.join(OUT_DIR, "fig06_lobbyfi.png")
SNAPSHOT_URL = "https://hub.snapshot.org/graphql"
LOBBYFI_ADDR = "0x7a45eE0be5C4BdC938A5F00A2AEF393f46502D26"

# ── Key events ────────────────────────────────────────────────────────────────
EVENTS = [
    {
        "date":  "2024-07-22",
        "label": "LobbyFi\nlaunches",
        "color": "#7F8C8D",
        "y_frac": 0.92,
    },
    {
        "date":  "2025-02-06",
        "label": "Large VP\ninflux",
        "color": "#E67E22",
        "y_frac": 0.92,
    },
    {
        "date":  "2025-04-02",
        "label": "hitmonlee\nincident\n(OAT election)",
        "color": "#C0392B",
        "y_frac": 0.70,
    },
    {
        "date":  "2025-10-30",
        "label": "LobbyFi\ngoes dark",
        "color": "#2C3E50",
        "y_frac": 0.92,
    },
]

# ── Phase shading ─────────────────────────────────────────────────────────────
PHASES = [
    {"start": "2024-07-01", "end": "2025-01-31",
     "color": "#EBF5FB", "label": "Phase 1 — Pilot\n(~$1.3M, ~0.6% share)"},
    {"start": "2025-02-01", "end": "2025-10-31",
     "color": "#FEF9E7", "label": "Phase 2 — Scale-up\n($17–27M, 8–14% share)"},
    {"start": "2025-11-01", "end": "2026-05-01",
     "color": "#FDEDEC", "label": "Phase 3 — Dormant\n(0 votes cast)"},
]


# ── Step 1: Fetch LobbyFi votes ───────────────────────────────────────────────

VOTES_QUERY = """
{
  votes(
    first: 1000
    where: { voter: "%s", space: "arbitrumfoundation.eth" }
    orderBy: "created"
    orderDirection: asc
  ) {
    proposal { id title created scores_total }
    vp
    created
  }
}
""" % LOBBYFI_ADDR

print("Fetching LobbyFi voting history (frozen; --refresh to re-pull)...")
raw_votes = freeze.frozen_json(
    "fig06_lobbyfi_votes",
    lambda: requests.post(SNAPSHOT_URL, json={"query": VOTES_QUERY}, timeout=30).json().get("data", {}).get("votes", []),
)
print(f"  {len(raw_votes)} votes found")

records = []
for v in raw_votes:
    p = v["proposal"]
    created  = pd.to_datetime(v["created"], unit="s")
    total_vp = p["scores_total"]
    share    = v["vp"] / total_vp * 100 if total_vp > 0 else np.nan
    records.append({
        "voted_at":    created,
        "prop_date":   pd.to_datetime(p["created"], unit="s"),
        "title":       p["title"],
        "lobbyfi_vp":  freeze.to_value(v["vp"]) / 1e6,   # millions USD (at fixed TGE rate)
        "total_vp":    total_vp / 1e6,
        "share":       share,
    })

df = pd.DataFrame(records).sort_values("voted_at").reset_index(drop=True)
print(f"\nData range: {df['voted_at'].min().date()} → {df['voted_at'].max().date()}")
print(f"VP range:   {df['lobbyfi_vp'].min():.2f}M → {df['lobbyfi_vp'].max():.2f}M USD")
print(f"Share range:{df['share'].min():.1f}% → {df['share'].max():.1f}%")
print(f"\nPhase breakdown:")
print(f"  Phase 1 (Jul 2024 – Jan 2025): {len(df[df['voted_at'] < '2025-02-01'])} proposals")
print(f"  Phase 2 (Feb 2025 – Oct 2025): {len(df[(df['voted_at'] >= '2025-02-01') & (df['voted_at'] <= '2025-10-31')])} proposals")
print(f"  Phase 3 (Nov 2025+):           {len(df[df['voted_at'] > '2025-10-31'])} proposals")


# ── Step 2: Plot ──────────────────────────────────────────────────────────────
# Two stacked panels sharing the x-axis:
#   Top    — LobbyFi's total VP (millions ARB): the supply-side of the market
#   Bottom — LobbyFi's share of total VP cast per proposal: the governance impact

fig, (ax_vp, ax_share) = plt.subplots(
    2, 1, figsize=(14, 8), sharex=True,
    gridspec_kw={"height_ratios": [1, 1.1], "hspace": 0.06}
)

x_min = pd.Timestamp("2024-06-15")
x_max = pd.Timestamp("2026-05-01")

# ── Phase shading (both panels) ───────────────────────────────────────────────
for ph in PHASES:
    for ax in (ax_vp, ax_share):
        ax.axvspan(pd.Timestamp(ph["start"]), pd.Timestamp(ph["end"]),
                   color=ph["color"], alpha=0.85, zorder=0)

# ── Top panel: LobbyFi VP (millions ARB) ─────────────────────────────────────
COL_VP = "#2980B9"

ax_vp.plot(df["voted_at"], df["lobbyfi_vp"], color=COL_VP,
           linewidth=2.0, marker="o", markersize=5.5,
           markerfacecolor="white", markeredgewidth=1.5, zorder=4)
ax_vp.fill_between(df["voted_at"], df["lobbyfi_vp"],
                   color=COL_VP, alpha=0.10, zorder=3)

# Dormant zone annotation
ax_vp.annotate("No votes cast\n(Nov 2025 – Apr 2026)",
               xy=(pd.Timestamp("2026-01-15"), 5),
               fontsize=9, color="#922B21", ha="center",
               bbox=dict(fc="white", ec="#C0392B", pad=3, alpha=0.85))

ax_vp.set_ylabel("LobbyFi Voting Power\n(USD millions)", fontsize=11)
ax_vp.set_ylim(0, df["lobbyfi_vp"].max() * 1.35)
ax_vp.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:.0f}M"))
ax_vp.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.4)

# ── Bottom panel: VP share per proposal ──────────────────────────────────────
COL_SHARE = "#C0392B"

# Scatter (each dot = one proposal vote)
ax_share.scatter(df["voted_at"], df["share"],
                 color=COL_SHARE, s=55, alpha=0.80, zorder=5,
                 edgecolors="white", linewidths=0.5)

# Smoothed trend (rolling median, 5-proposal window)
df_sorted = df.sort_values("voted_at").copy()
roll_share = df_sorted.set_index("voted_at")["share"].rolling("60D", min_periods=2).median()
ax_share.plot(roll_share.index, roll_share.values,
              color=COL_SHARE, linewidth=2.2, alpha=0.55, zorder=4,
              label="60-day rolling median")

# Reference lines
ax_share.axhline(10, color="gray", linewidth=0.8, linestyle=":", alpha=0.6)
ax_share.text(x_max, 10.3, "10%", fontsize=8, color="gray", ha="right", va="bottom")

ax_share.set_ylabel("LobbyFi VP Share of\nTotal VP Cast (per proposal)", fontsize=11)
ax_share.set_ylim(0, df["share"].max() * 1.30)
ax_share.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax_share.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.4)

# Annotate the hitmonlee incident specifically
hitmonlee_row = df[df["title"].str.contains("Oversight and Transparency", na=False)].iloc[0]
ax_share.annotate(
    f"OAT election: $25M of voting power\nbought for 5 ETH (~$10k)\n→ {hitmonlee_row['share']:.1f}% of all votes cast",
    xy=(hitmonlee_row["voted_at"], hitmonlee_row["share"]),
    xytext=(hitmonlee_row["voted_at"] - pd.Timedelta(days=100),
            hitmonlee_row["share"] + 1.5),
    fontsize=8, color="#922B21",
    arrowprops=dict(arrowstyle="->", color="#922B21", lw=1.2),
    bbox=dict(fc="white", ec="#C0392B", pad=3, alpha=0.9),
    ha="right"
)

# ── Event vertical lines (both panels) ───────────────────────────────────────
vp_ymax = ax_vp.get_ylim()[1]
share_ymax = ax_share.get_ylim()[1]

for ev in EVENTS:
    xd = pd.Timestamp(ev["date"])
    for ax in (ax_vp, ax_share):
        ax.axvline(xd, color=ev["color"], linewidth=1.4,
                   linestyle="--", alpha=0.75, zorder=6)
    # Label only on top panel
    ax_vp.text(xd, vp_ymax * ev["y_frac"], ev["label"],
               color=ev["color"], fontsize=8, ha="center", va="top",
               bbox=dict(fc="white", ec=ev["color"], pad=2, alpha=0.9))

# ── X-axis ────────────────────────────────────────────────────────────────────
ax_share.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
ax_share.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
ax_share.set_xlim(x_min, x_max)

# ── Phase legend ──────────────────────────────────────────────────────────────
phase_patches = [
    mpatches.Patch(color=ph["color"], alpha=0.85, label=ph["label"])
    for ph in PHASES
]
ax_vp.legend(handles=phase_patches, loc="upper left",
             fontsize=8.5, framealpha=0.95, title="Market phases", title_fontsize=8.5)

# ── Titles ────────────────────────────────────────────────────────────────────
fig.suptitle(
    "Figure A3: The Vote Rental Market — LobbyFi on Arbitrum DAO\n"
    "Delegated Voting Power and Governance Share of the LobbyFi Proxy, July 2024 – April 2026\n"
    "(Each dot = one Snapshot proposal vote; 78 votes total, 0 after October 2025)",
    fontsize=11.5, fontweight="bold", y=1.01
)

fig.savefig(OUT_PATH, dpi=180, bbox_inches="tight")
print(f"\nSaved to {OUT_PATH}")
