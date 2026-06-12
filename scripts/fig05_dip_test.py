#!/usr/bin/env python3
"""
Figure 5: Incentives and Participation (DIP Test)
Journal of Finance paper on Arbitrum governance.

Walk-through:
  1. Fetch all closed Arbitrum DAO proposals from Snapshot
  2. For each proposal, fetch top-1000 voters sorted by VP descending
     (cached to disk — re-runs skip the API entirely)
  3. Identify "Large Delegates": voters with VP >= 500,000 ARB
  4. Per proposal: count large delegates and their combined VP share
  5. Aggregate to monthly series using all proposals in each month
  6. Plot time series with DIP event annotations

DIP timeline (from Snapshot governance record):
  Aug 2024  – "Temporary Extension of Delegate Incentive System" (bridge/predecessor)
  Sep 2024  – DIP formally launched  ("[Non-Constitutional] Arbitrum DAO Delegate Incentive Program")
  Jul 2025  – DIP 1.7 overhaul       ("Updates to the DIP, The Complete 1.7 Version")
  Oct 2025  – DIP 2.0                ("The DAO Incentive Program (DIP 2.0)")
  Dec 2025  – RAD Program            ("Rewarding Active Delegates (RAD) Program")
"""

import os
import time
import json
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys as _sys
_sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, C_TOTAL, C_SHOCK, savefig as aer_savefig
apply_aer_style()
import matplotlib.ticker as mticker
import matplotlib.dates as mdates

HERE     = os.path.dirname(os.path.abspath(__file__))
ROOT     = os.path.dirname(HERE)   # project root
OUT_DIR  = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH   = os.path.join(OUT_DIR, "fig05_dip_test.png")
CACHE_PATH = os.path.join(ROOT, "data", "figure5_votes_cache.json")

SNAPSHOT_URL = "https://hub.snapshot.org/graphql"
SPACE        = "arbitrumfoundation.eth"
LARGE_VP_THRESHOLD = 500_000   # ARB

# ── DIP event markers ─────────────────────────────────────────────────────────
DIP_EVENTS = [
    {"date": "2024-08-15", "label": "DIP\nExtension",  "color": "#E67E22"},
    {"date": "2024-09-19", "label": "DIP\nLaunch",     "color": "#C0392B"},
    {"date": "2025-07-31", "label": "DIP\n1.7",        "color": "#8E44AD"},
    {"date": "2025-10-23", "label": "DIP\n2.0",        "color": "#2980B9"},
    {"date": "2025-12-04", "label": "RAD\nProgram",    "color": "#27AE60"},
]


# ── Step 1: Fetch all proposals ───────────────────────────────────────────────

PROP_QUERY = """
{
  proposals(
    first: 1000
    skip: %d
    where: { space_in: ["%s"], state: "closed" }
    orderBy: "created"
    orderDirection: asc
  ) {
    id
    title
    created
    scores_total
    votes
  }
}
"""

def fetch_proposals():
    all_props = []
    skip = 0
    while True:
        resp = requests.post(SNAPSHOT_URL,
                             json={"query": PROP_QUERY % (skip, SPACE)},
                             timeout=30)
        resp.raise_for_status()
        batch = resp.json().get("data", {}).get("proposals", [])
        if not batch:
            break
        all_props.extend(batch)
        if len(batch) < 1000:
            break
        skip += 1000
        time.sleep(0.3)
    return all_props


# ── Step 2: Fetch top-1000 voters per proposal (cached) ──────────────────────
# We only need voters with VP >= 500k, which are always in the top-1000 by VP.
# One API call per proposal is sufficient.

VOTES_QUERY = """
{
  votes(
    first: 1000
    skip: %d
    where: { proposal: "%s" }
    orderBy: "vp"
    orderDirection: desc
  ) {
    voter
    vp
  }
}
"""

def fetch_votes_for_proposal(proposal_id):
    """Return list of {voter, vp} dicts for a proposal, all pages."""
    all_votes = []
    skip = 0
    while True:
        resp = requests.post(SNAPSHOT_URL,
                             json={"query": VOTES_QUERY % (skip, proposal_id)},
                             timeout=30)
        resp.raise_for_status()
        batch = resp.json().get("data", {}).get("votes", [])
        if not batch:
            break
        all_votes.extend(batch)
        # If the lowest VP in this page is already below threshold, stop
        if batch[-1]["vp"] < LARGE_VP_THRESHOLD or len(batch) < 1000:
            break
        skip += 1000
        time.sleep(0.2)
    return all_votes


def load_cache():
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH) as f:
            return json.load(f)
    return {}

def save_cache(cache):
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w") as f:
        json.dump(cache, f)


# ── Main data pipeline ────────────────────────────────────────────────────────

print("Step 1: Fetching proposals...")
proposals = fetch_proposals()
proposals = [p for p in proposals
             if pd.to_datetime(p["created"], unit="s") >= pd.Timestamp("2023-01-01")]
print(f"  {len(proposals)} proposals to process")

print("\nStep 2: Fetching voter VP distributions (cached)...")
cache = load_cache()
new_fetches = 0

for i, p in enumerate(proposals):
    pid = p["id"]
    if pid in cache:
        continue
    votes = fetch_votes_for_proposal(pid)
    cache[pid] = votes
    new_fetches += 1
    if new_fetches % 20 == 0:
        save_cache(cache)
        print(f"  {i+1}/{len(proposals)} proposals fetched ({new_fetches} new)...")
    time.sleep(0.25)

if new_fetches > 0:
    save_cache(cache)
print(f"  Done. {new_fetches} new fetches, {len(proposals)-new_fetches} from cache.")


# ── Step 3: Compute per-proposal metrics ──────────────────────────────────────

print("\nStep 3: Computing large-delegate metrics per proposal...")
records = []
for p in proposals:
    pid     = p["id"]
    votes   = cache.get(pid, [])
    created = pd.to_datetime(p["created"], unit="s")
    total_vp = p["scores_total"]

    large = [v for v in votes if v["vp"] >= LARGE_VP_THRESHOLD]
    n_large    = len(large)
    large_vp   = sum(v["vp"] for v in large)
    large_share = large_vp / total_vp * 100 if total_vp > 0 else np.nan

    records.append({
        "id":          pid,
        "title":       p["title"],
        "created":     created,
        "month":       created.to_period("M").to_timestamp(),
        "scores_total": total_vp,
        "n_large":     n_large,
        "large_vp":    large_vp,
        "large_share": large_share,
    })

df = pd.DataFrame(records)
df = df[(df["created"] >= "2023-01-01") & (df["created"] <= "2026-04-01")]
print(f"  {len(df)} proposals in analysis window")


# ── Step 4: Aggregate to monthly ──────────────────────────────────────────────
# For each month: use all proposals, take median n_large and median large_share.
# Also track the total unique large delegates who voted at least once that month.

print("\nStep 4: Aggregating to monthly series...")

def unique_large_delegates(month_proposals):
    """Count unique voters with VP >= threshold across all proposals in month."""
    seen = set()
    for pid in month_proposals:
        for v in cache.get(pid, []):
            if v["vp"] >= LARGE_VP_THRESHOLD:
                seen.add(v["voter"])
    return len(seen)

monthly = (
    df.groupby("month")
    .agg(
        n_proposals=("id", "count"),
        median_n_large=("n_large", "median"),
        median_large_share=("large_share", "median"),
        total_vp=("scores_total", "median"),
    )
    .reset_index()
)

# Unique large delegates per month
monthly["unique_large"] = monthly.apply(
    lambda row: unique_large_delegates(
        df[df["month"] == row["month"]]["id"].tolist()
    ), axis=1
)

print(monthly[["month", "n_proposals", "unique_large", "median_n_large",
               "median_large_share"]].to_string(index=False))


# ── Step 5: Plot ──────────────────────────────────────────────────────────────
# Two panels sharing the x-axis:
#   Top panel    – count of unique large delegates active per month
#   Bottom panel – their combined VP as share of total VP cast (median across proposals)

print("\nStep 5: Building figure...")

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True,
                                gridspec_kw={"height_ratios": [1, 1], "hspace": 0.08})

COLOR_COUNT = "#2C3E50"
COLOR_SHARE = "#C0392B"
PRE_COLOR   = "#ECF0F1"
POST_COLOR  = "#FDEBD0"

months = monthly["month"]

# ── Shade DIP-active period (Sep 2024 onwards) ───────────────────────────────
dip_start = pd.Timestamp("2024-09-19")
x_end     = pd.Timestamp("2026-04-01")
for ax in (ax1, ax2):
    ax.axvspan(dip_start, x_end, color="#FFF3E0", alpha=0.45, zorder=0,
               label="DIP active period")

# ── Top panel: unique large delegate count ────────────────────────────────────
ax1.plot(months, monthly["unique_large"], color=COLOR_COUNT,
         linewidth=2.0, marker="o", markersize=5, zorder=4)
ax1.fill_between(months, monthly["unique_large"],
                 color=COLOR_COUNT, alpha=0.12, zorder=3)

ax1.set_ylabel("Unique Large Delegates\nVoting per Month\n(VP ≥ 500k ARB)", fontsize=10)
ax1.yaxis.set_major_locator(mticker.MaxNLocator(integer=True, nbins=6))
ax1.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.4)

# ── Bottom panel: VP share ────────────────────────────────────────────────────
ax2.plot(months, monthly["median_large_share"], color=COLOR_SHARE,
         linewidth=2.0, marker="s", markersize=5, zorder=4)
ax2.fill_between(months, monthly["median_large_share"],
                 color=COLOR_SHARE, alpha=0.12, zorder=3)

ax2.set_ylabel("Large-Delegate VP Share\nof Total VP Cast (%)\n[median across proposals]",
               fontsize=10)
ax2.set_ylim(0, min(100, monthly["median_large_share"].max() * 1.35))
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax2.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.4)

# ── DIP event vertical lines ─────────────────────────────────────────────────
for ev in DIP_EVENTS:
    xd = pd.Timestamp(ev["date"])
    for ax in (ax1, ax2):
        ax.axvline(xd, color=ev["color"], linewidth=1.4, linestyle=":", alpha=0.9, zorder=5)
    # Label only on top panel
    ax1.text(xd, monthly["unique_large"].max() * 1.05, ev["label"],
             color=ev["color"], fontsize=7.5, ha="center", va="bottom",
             bbox=dict(fc="white", ec="none", pad=1))

# ── X-axis ────────────────────────────────────────────────────────────────────
ax2.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
ax2.set_xlim(pd.Timestamp("2023-01-01"), pd.Timestamp("2026-05-01"))

# ── Shared legend ─────────────────────────────────────────────────────────────
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
leg_handles = [
    mlines.Line2D([0],[0], color=COLOR_COUNT, linewidth=2, marker="o", markersize=5,
                  label="Unique large delegates (VP ≥ 500k)"),
    mlines.Line2D([0],[0], color=COLOR_SHARE, linewidth=2, marker="s", markersize=5,
                  label="Large-delegate VP share (median)"),
    mpatches.Patch(color="#FFF3E0", alpha=0.8, label="DIP active period (Sep 2024 →)"),
]
ax1.legend(handles=leg_handles, loc="upper left", fontsize=8.5, framealpha=0.92)

fig.suptitle(
    "Figure A2: Incentives and Participation — DIP Test\n"
    "Large-Delegate Activity (VP ≥ 500k ARB) Before and After the Delegate Incentive Program\n"
    "Arbitrum DAO Snapshot Votes, January 2023 – March 2026",
    fontsize=12, fontweight="bold", y=1.01
)

fig.savefig(OUT_PATH, dpi=180, bbox_inches="tight")
print(f"\nSaved to {OUT_PATH}")
