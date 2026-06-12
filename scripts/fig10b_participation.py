#!/usr/bin/env python3
"""
Figure 10b: Unique Voters Per Month — Five DeFi DAOs on Snapshot
Journal of Finance paper on Arbitrum governance.

Each dot = one month for one DAO.
Y = median number of unique voter addresses per proposal that month.
No connecting lines — shows raw participation breadth over time.

Snapshot's `votes` field = count of distinct wallet addresses that voted
on that proposal (one vote per address per proposal on Snapshot).
Monthly median across all proposals in that month.
"""

import os, json, time
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sys as _sys
_sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, C_TOTAL, C_SHOCK, savefig as aer_savefig
apply_aer_style()
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import matplotlib.lines as mlines

HERE         = os.path.dirname(os.path.abspath(__file__))
ROOT         = os.path.dirname(HERE)   # project root
OUT_DIR      = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH     = os.path.join(OUT_DIR, "fig10b_participation.png")
CACHE_PATH   = os.path.join(ROOT, "data", "figure10b_proposals_cache.json")
SNAPSHOT_URL = "https://hub.snapshot.org/graphql"

os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)

DAOS = [
    {"name": "Arbitrum", "ticker": "ARB",  "space": "arbitrumfoundation.eth",
     "color": "#2980B9", "marker": "o",  "size": 55},
    {"name": "Aave",     "ticker": "AAVE", "space": "aavedao.eth",
     "color": "#B6509E", "marker": "s",  "size": 40},
    {"name": "ENS",      "ticker": "ENS",  "space": "ens.eth",
     "color": "#5298FF", "marker": "^",  "size": 45},
    {"name": "Lido",     "ticker": "LDO",  "space": "lido-snapshot.eth",
     "color": "#27AE60", "marker": "D",  "size": 38},
    {"name": "Compound", "ticker": "COMP", "space": "comp-vote.eth",
     "color": "#E67E22", "marker": "P",  "size": 50},
]


def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1  Fetch proposals (with voter count)
# ══════════════════════════════════════════════════════════════════════════════

PROP_QUERY = """
{
  proposals(
    first: 1000
    skip: %d
    where: { space_in: ["%s"], state: "closed" }
    orderBy: "created"
    orderDirection: asc
  ) {
    id created votes
  }
}
"""

print("Step 1: Fetching proposals (with voter counts, paginated, cached)...")
cache = load_json(CACHE_PATH)

for dao in DAOS:
    name = dao["name"]
    if name in cache:
        print(f"  {name:12} (cached: {len(cache[name])} proposals)")
        continue

    all_props = []
    skip = 0
    while True:
        try:
            r = requests.post(SNAPSHOT_URL,
                              json={"query": PROP_QUERY % (skip, dao["space"])},
                              timeout=30)
            batch = r.json().get("data", {}).get("proposals", [])
        except Exception as e:
            print(f"  Warning ({name}): {e}")
            break
        if not batch:
            break
        all_props.extend(batch)
        if len(batch) < 1000:
            break
        skip += 1000
        time.sleep(0.3)

    all_props = [
        p for p in all_props
        if pd.Timestamp("2023-01-01")
           <= pd.to_datetime(p["created"], unit="s")
           < pd.Timestamp("2026-05-01")
    ]
    cache[name] = all_props
    print(f"  {name:12} {len(all_props):4d} proposals fetched")
    time.sleep(0.6)

save_json(CACHE_PATH, cache)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2  Aggregate to monthly median voter count
# ══════════════════════════════════════════════════════════════════════════════

print("\nStep 2: Aggregating to monthly median voter count...")

monthly_data = {}
for dao in DAOS:
    name  = dao["name"]
    props = cache.get(name, [])

    rows = []
    for p in props:
        n_voters = p.get("votes", 0)
        if n_voters <= 0:
            continue
        created = pd.to_datetime(p["created"], unit="s")
        rows.append({
            "month":    created.to_period("M").to_timestamp(),
            "n_voters": n_voters,
        })

    if not rows:
        print(f"  {name:12} — no data")
        continue

    df_dao  = pd.DataFrame(rows)
    monthly = (
        df_dao.groupby("month")
        .agg(median_voters=("n_voters", "median"),
             n_proposals=("n_voters", "count"))
        .reset_index()
        .sort_values("month")
    )
    monthly_data[name] = monthly

    print(f"  {name:12} {len(monthly):3d} months  "
          f"voter range: {monthly['median_voters'].min():.0f} – {monthly['median_voters'].max():.0f}")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3  Plot — scatter only, no connecting lines
# ══════════════════════════════════════════════════════════════════════════════

print("\nStep 3: Building figure...")

fig, ax = plt.subplots(figsize=(15, 6.5))

legend_handles = []

for dao in DAOS:
    name    = dao["name"]
    color   = dao["color"]
    marker  = dao["marker"]
    sz      = dao["size"]
    monthly = monthly_data.get(name)
    if monthly is None or len(monthly) < 2:
        continue

    ax.scatter(monthly["month"], monthly["median_voters"],
               color=color, marker=marker, s=sz,
               alpha=0.75, zorder=4, edgecolors="white", linewidths=0.5)

    handle = mlines.Line2D(
        [0], [0], marker=marker, color="w",
        markerfacecolor=color, markersize=7,
        label=f"{name} ({dao['ticker']})"
    )
    legend_handles.append(handle)


# ── Axis formatting ───────────────────────────────────────────────────────────
ax.set_ylabel("Median Unique Voters per Proposal\n(addresses, that month)", fontsize=11)
ax.set_xlabel("Date", fontsize=10)

ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
ax.set_xlim(pd.Timestamp("2023-01-01"), pd.Timestamp("2026-06-01"))
ax.set_yscale("log")
ax.set_ylim(bottom=10)

ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
ax.yaxis.set_minor_formatter(mticker.NullFormatter())
ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.40)
ax.grid(axis="x", linestyle=":",  linewidth=0.4, alpha=0.25)

ax.legend(handles=legend_handles, loc="upper right",
          fontsize=9.5, framealpha=0.93,
          title="Each dot = one month", title_fontsize=8.5)

fig.suptitle(
    "Figure A7: Participation Breadth Over Time — Unique Voters per Proposal\n"
    "Five DeFi DAOs on Snapshot, Jan 2023 – Apr 2026  "
    "|  Each dot = median voter count for proposals in that month",
    fontsize=12, fontweight="bold", y=1.01
)

fig.tight_layout()
fig.savefig(OUT_PATH, dpi=180, bbox_inches="tight")
print(f"\nSaved to {OUT_PATH}")

# ── Summary table ─────────────────────────────────────────────────────────────
print("\nMedian voter summary by DAO:")
for dao in DAOS:
    name = dao["name"]
    m = monthly_data.get(name)
    if m is not None:
        print(f"  {name:12}  overall median: {m['median_voters'].median():7.0f}  "
              f"peak: {m['median_voters'].max():7.0f}  "
              f"latest: {m.iloc[-1]['median_voters']:7.0f}")
