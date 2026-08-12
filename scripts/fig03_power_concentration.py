#!/usr/bin/env python3
"""
Figure 3 (revised): Evolution of Voting Power Concentration
Journal of Finance paper on Arbitrum governance.

Metrics:
  - Nakamoto Coefficient at 51% threshold (bars, left axis):
      minimum number of delegates needed to collectively reach a simple majority.
  - Nakamoto Coefficient at 33% threshold (bars, left axis):
      minimum number needed to hold a blocking minority (veto power).
  - Top-10 delegate share of total VP (line, right axis):
      cumulative VP held by the 10 largest voters as a % of total VP cast.

Data source: highest-turnout Snapshot proposal in each Security Council
election window. VP distributions come from active voters, which is the
relevant pool for governance concentration analysis.
"""

import os
import time
import requests
import numpy as np
import matplotlib.pyplot as plt
import sys as _sys
_sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, C_TOTAL, C_SHOCK, savefig as aer_savefig
import freeze
apply_aer_style()
import matplotlib.ticker as mticker

HERE    = os.path.dirname(os.path.abspath(__file__))
ROOT    = os.path.dirname(HERE)   # project root
OUT_DIR = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, "fig03_power_concentration.png")

SNAPSHOT_URL = "https://hub.snapshot.org/graphql"

PROPOSALS = [
    {"label": "Sep 2023", "id": "0x6fc671517d63e69232fafd581e9461c50150008aa61f5571d2767a150d24779c"},
    {"label": "Mar 2024", "id": "0xf08fe07ad299db8400b53fc76f7cf2b686fcc82dde01102e0764afdbacf3805f"},
    {"label": "Sep 2024", "id": "0xb581f3aed701ae889c1d79406acdf3d653e6eb4323cb5e46635f729e6313da4d"},
    {"label": "Mar 2025", "id": "0xab1a7ff1a294882315f3beaa77fa0d4b2ec68633792046b941714108209ce737"},
    {"label": "Sep 2025", "id": "0x95a85f5d3d82215793ba9771ff06610d2ba9e2eaf58cdba904d7a9cb5b8bdc94"},
    {"label": "Mar 2026", "id": "0x3ac48360cb2cf6f921e391a97416a53c8ca442e3a621a9f7bb406719a8f8034d"},
]

PROP_QUERY  = '{ proposal(id: "%s") { votes scores_total } }'
VOTES_QUERY = """
{
  votes(first:1000 skip:%d where:{proposal:"%s"} orderBy:"vp" orderDirection:desc){vp}
}
"""


# ── Step 1: Fetch VP distributions ───────────────────────────────────────────

def gql(query, retries=4):
    for attempt in range(retries):
        try:
            resp = requests.post(SNAPSHOT_URL, json={"query": query}, timeout=30)
            return resp.json()
        except Exception:
            time.sleep(3 * (attempt + 1))
    return {}

def fetch_vp(proposal_id):
    meta = gql(PROP_QUERY % proposal_id).get("data", {}).get("proposal") or {}
    n_total  = meta.get("votes", 0)
    vp_total = meta.get("scores_total", 0.0)

    top_vp = []
    for skip in range(0, 5000, 1000):
        batch = gql(VOTES_QUERY % (skip, proposal_id)).get("data", {}).get("votes") or []
        top_vp.extend(v["vp"] for v in batch if v.get("vp") and v["vp"] > 0)
        if len(batch) < 1000:
            break
        time.sleep(0.5)

    top_vp = np.array(top_vp, dtype=float)

    # Reconstruct tail voters with residual VP split equally
    n_tail = max(0, n_total - len(top_vp))
    vp_tail_total = max(0.0, vp_total - top_vp.sum())
    if n_tail > 0 and vp_tail_total > 0:
        tail = np.full(n_tail, vp_tail_total / n_tail)
        return np.concatenate([tail, top_vp])
    return top_vp

print("Step 1: Fetching VP distributions (frozen; --refresh to re-pull)...")

def _fetch_distributions():
    out = []
    for p in PROPOSALS:
        vp = fetch_vp(p["id"])
        out.append(vp.tolist())
        print(f"  fetched {p['label']}: {len(vp):,} voters")
        time.sleep(0.4)
    return out

distributions = [np.array(v, dtype=float) for v in
                 freeze.frozen_json("fig03_vp_distributions", _fetch_distributions)]
for p, vp in zip(PROPOSALS, distributions):
    print(f"  {p['label']}: {len(vp):,} voters, total VP = {vp.sum()/1e6:.1f}M ARB")


# ── Step 2: Compute metrics ───────────────────────────────────────────────────
# Nakamoto Coefficient at threshold T:
#   Sort delegates largest-first. Walk down the list accumulating VP.
#   The count when cumulative VP first exceeds T × total is the Nakamoto number.
#
# Top-10 share:
#   Sum of the 10 largest VP values divided by total VP, expressed as a %.

def nakamoto(vp: np.ndarray, threshold: float) -> int:
    sorted_vp = np.sort(vp)[::-1]   # descending
    total = sorted_vp.sum()
    cumsum = np.cumsum(sorted_vp)
    hits = np.where(cumsum >= threshold * total)[0]
    return int(hits[0]) + 1 if len(hits) else len(sorted_vp)

def top_k_share(vp: np.ndarray, k: int = 10) -> float:
    sorted_vp = np.sort(vp)[::-1]
    return sorted_vp[:k].sum() / vp.sum() * 100

print("\nStep 2: Computing metrics...")
nak51, nak33, top10 = [], [], []
for p, vp in zip(PROPOSALS, distributions):
    n51 = nakamoto(vp, 0.51)
    n33 = nakamoto(vp, 0.33)
    t10 = top_k_share(vp, 10)
    nak51.append(n51)
    nak33.append(n33)
    top10.append(t10)
    print(f"  {p['label']}: Nak@51%={n51:3d}  Nak@33%={n33:3d}  Top-10 share={t10:.1f}%")


# ── Step 3: Plot ──────────────────────────────────────────────────────────────
# Grouped bars (left axis): Nakamoto at 51% and 33% per election window.
# Lower Nakamoto = more concentrated = higher governance risk.
# Line (right axis): Top-10 share — rising line means more power in fewer hands.

print("\nStep 3: Building figure...")

COL_51  = COLORS["red"]
COL_33  = COLORS["orange"]
COL_T10 = COLORS["black"]

fig, ax1 = plt.subplots(figsize=(7, 3.8))
ax2 = ax1.twinx()

x     = np.arange(len(PROPOSALS))
bar_w = 0.30
labels = [p["label"] for p in PROPOSALS]

bars51 = ax1.bar(x - bar_w/2, nak51, bar_w, color=COL_51, alpha=0.82,
                  label="Nakamoto @ 51% (majority)")
bars33 = ax1.bar(x + bar_w/2, nak33, bar_w, color=COL_33, alpha=0.82,
                  label="Nakamoto @ 33% (blocking minority)")

# Label each bar with its value
for bar in bars51 + bars33:
    h = bar.get_height()
    ax1.text(bar.get_x() + bar.get_width()/2, h + 0.15, str(int(h)),
             ha="center", va="bottom", fontsize=8.5, fontweight="bold")

ax2.plot(x, top10, color=COL_T10, linewidth=2.2, marker="o", markersize=7,
         label="Top-10 delegate share of total VP", zorder=5)

# Axis formatting
ax1.set_ylabel("Nakamoto coefficient (# delegates)")
ax1.set_ylim(0, max(max(nak51), max(nak33)) * 1.5)
ax1.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))

ax2.set_ylabel("Top-10 delegate share of total VP (%)")
ax2.set_ylim(0, 105)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))

ax1.set_xticks(x)
ax1.set_xticklabels(labels, fontsize=10)
ax1.set_xlim(-0.6, len(PROPOSALS) - 0.4)

# Combined legend
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="upper right", framealpha=0.9)
despine(ax1)
fig.tight_layout()
aer_savefig(fig, OUT_PATH)
