#!/usr/bin/env python3
"""
Figure 10: Cross-DAO Governance Benchmarking
Journal of Finance paper on Arbitrum governance.

Four-panel comparison of governance concentration and participation
across Arbitrum and five comparable DeFi DAOs on Snapshot.

Metrics (all computed from Snapshot API, comparable across DAOs):
  (i)  Gini coefficient of actual VP exercised — concentration of voting power
       among those who actually vote (from top-1000 voter VP distributions,
       sampled from 3 recent high-turnout proposals per DAO)
  (ii) Median participation rate — median VP cast as % of circulating supply
       (CoinGecko circulating supply; makes VPs comparable across token scales)
  (iii) Proposal passage rate — % of closed proposals where For > Against
        (excludes approval/weighted elections which have no For/Against)
  (iv) Nakamoto coefficient (50%) — minimum number of unique voters
       whose combined VP exceeds 50% of total VP cast
       (lower = more concentrated; Arbitrum's figure-3 context)

DAOs included:
  Arbitrum  (ARB)  — arbitrumfoundation.eth   — primary subject
  Aave      (AAVE) — aavedao.eth              — large DeFi lending
  ENS               — ens.eth                  — identity/naming
  Lido      (LDO)  — lido-snapshot.eth        — liquid staking
  Compound  (COMP) — comp-vote.eth             — pioneering DeFi DAO

Note: Optimism and Uniswap conduct primary governance on-chain via
Agora and Governor Bravo respectively and are not available through
the main Snapshot GraphQL API. They are not included in this analysis.

Circulating supply (CoinGecko, as of data collection date):
  ARB:  6.15B tokens  ENS:  0.040B  LDO:  0.85B
  AAVE: 0.019B        COMP: 0.009B
"""

import os, json, time, re
import requests
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sys as _sys
_sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, C_TOTAL, C_SHOCK, savefig as aer_savefig
apply_aer_style()
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches

HERE         = os.path.dirname(os.path.abspath(__file__))
ROOT         = os.path.dirname(HERE)   # project root
OUT_DIR      = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH     = os.path.join(OUT_DIR, "fig10_crossdao.png")
CACHE_PATH   = os.path.join(ROOT, "data", "figure10_voter_cache.json")
FIG5_CACHE   = os.path.join(ROOT, "data", "figure5_votes_cache.json")
SNAPSHOT_URL = "https://hub.snapshot.org/graphql"

os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)

# ── DAO configuration ─────────────────────────────────────────────────────────
DAOS = [
    {"name": "Arbitrum", "ticker": "ARB",  "space": "arbitrumfoundation.eth",
     "color": "#2980B9", "supply_B": 6.150},
    {"name": "Aave",     "ticker": "AAVE", "space": "aavedao.eth",
     "color": "#B6509E", "supply_B": 0.019},
    {"name": "ENS",      "ticker": "ENS",  "space": "ens.eth",
     "color": "#5298FF", "supply_B": 0.040},
    {"name": "Lido",     "ticker": "LDO",  "space": "lido-snapshot.eth",
     "color": "#00A3FF", "supply_B": 0.850},
    {"name": "Compound", "ticker": "COMP", "space": "comp-vote.eth",
     "color": "#00D395", "supply_B": 0.009},
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

def gini(values):
    """Gini coefficient of a list of non-negative values."""
    v = np.array(sorted([x for x in values if x > 0]), dtype=float)
    if len(v) < 2:
        return np.nan
    n = len(v)
    idx = np.arange(1, n + 1)
    return (2 * np.sum(idx * v) / (n * np.sum(v))) - (n + 1) / n

def nakamoto(vp_list, threshold=0.50):
    """Min voters whose cumulative VP > threshold × total VP."""
    sorted_vp = sorted(vp_list, reverse=True)
    total = sum(sorted_vp)
    if total == 0:
        return np.nan
    cumsum = 0
    for i, v in enumerate(sorted_vp):
        cumsum += v
        if cumsum / total >= threshold:
            return i + 1
    return len(sorted_vp)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1  Fetch proposals for each DAO
# ══════════════════════════════════════════════════════════════════════════════

PROP_QUERY = """
{
  proposals(
    first: 200
    where: { space_in: ["%s"], state: "closed" }
    orderBy: "created"
    orderDirection: desc
  ) {
    id title created type choices scores scores_total votes
  }
}
"""

print("Step 1: Fetching proposals for each DAO...")
dao_proposals = {}
for dao in DAOS:
    r = requests.post(SNAPSHOT_URL,
                      json={"query": PROP_QUERY % dao["space"]},
                      timeout=30)
    props = r.json().get("data", {}).get("proposals", [])
    # Filter to 2023+ only
    props = [p for p in props
             if pd.to_datetime(p["created"], unit="s") >= pd.Timestamp("2023-01-01")]
    dao_proposals[dao["name"]] = props
    print(f"  {dao['name']:12} {len(props):3d} proposals")
    time.sleep(0.4)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2  Fetch voter VP distributions (for Gini + Nakamoto) — cached
# ══════════════════════════════════════════════════════════════════════════════

VOTES_QUERY = """
{
  votes(
    first: 1000
    skip: %d
    where: { proposal: "%s" }
    orderBy: "vp"
    orderDirection: desc
  ) { voter vp }
}
"""

print("\nStep 2: Fetching voter VP distributions (cached)...")
cache = load_json(CACHE_PATH)

# For Arbitrum, seed from figure5 cache
if os.path.exists(FIG5_CACHE):
    fig5 = load_json(FIG5_CACHE)
    for pid, votes in fig5.items():
        if pid not in cache:
            cache[pid] = [{"voter": v["voter"], "vp": v["vp"]} for v in votes]
    print(f"  Seeded {len(fig5)} Arbitrum proposals from figure5 cache")

# For each DAO: sample the 5 highest-turnout proposals for Gini calculation
for dao in DAOS:
    props = dao_proposals[dao["name"]]
    # Pick 5 proposals with highest VP
    sample = sorted(props, key=lambda p: p["scores_total"], reverse=True)[:5]
    for p in sample:
        pid = p["id"]
        if pid in cache:
            continue
        votes_all = []
        skip = 0
        while True:
            r = requests.post(SNAPSHOT_URL,
                              json={"query": VOTES_QUERY % (skip, pid)},
                              timeout=30)
            batch = r.json().get("data", {}).get("votes", [])
            if not batch:
                break
            votes_all.extend(batch)
            if len(batch) < 1000:
                break
            skip += 1000
            time.sleep(0.2)
        cache[pid] = [{"voter": v["voter"], "vp": v["vp"]} for v in votes_all]
        time.sleep(0.3)

save_json(CACHE_PATH, cache)
print(f"  Cache now has {len(cache)} proposals")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3  Compute metrics per DAO
# ══════════════════════════════════════════════════════════════════════════════

print("\nStep 3: Computing metrics...")

# For passage rate: basic proposals only (single-choice For/Against/Abstain)
FOR_RE = re.compile(r'^for\b', re.I)

def is_basic_pass(p):
    """True if this is a basic For/Against/Abstain proposal that passed."""
    if p["type"] not in ("basic", "single-choice"):
        return None
    ch = p.get("choices") or []
    sc = p.get("scores") or []
    if not ch or not sc:
        return None
    # Find For and Against indices
    for_vp = against_vp = 0
    for c, s in zip(ch, sc):
        c_lower = c.lower().strip()
        if c_lower.startswith("for") or c_lower == "yes" or c_lower == "yae":
            for_vp = max(for_vp, s)
        elif c_lower.startswith("against") or c_lower == "no" or c_lower == "nay":
            against_vp = max(against_vp, s)
    # First choice is typically "For" in basic proposals
    if for_vp == 0 and sc:
        for_vp = sc[0]
    if against_vp == 0 and len(sc) > 1:
        against_vp = sc[1]
    return for_vp > against_vp

results = []
for dao in DAOS:
    props = dao_proposals[dao["name"]]
    supply = dao["supply_B"] * 1e9   # in tokens

    # ── Passage rate ──────────────────────────────────────────────────────────
    pass_results = [is_basic_pass(p) for p in props]
    pass_results = [x for x in pass_results if x is not None]
    passage_rate = np.mean(pass_results) * 100 if pass_results else np.nan

    # ── Participation rate (VP as % of circulating supply) ────────────────────
    vp_vals = [p["scores_total"] for p in props if p["scores_total"] > 0]
    median_vp = np.median(vp_vals) if vp_vals else np.nan
    participation_rate = median_vp / supply * 100 if supply > 0 else np.nan

    # ── Gini + Nakamoto from voter VP data ────────────────────────────────────
    # Use 5 highest-turnout proposals
    sample_pids = [p["id"] for p in sorted(props, key=lambda p: p["scores_total"],
                                           reverse=True)[:5]]
    all_vp_lists = []
    for pid in sample_pids:
        if pid in cache:
            vps = [v["vp"] for v in cache[pid] if v["vp"] > 0]
            if vps:
                all_vp_lists.append(vps)

    gini_vals     = [gini(v) for v in all_vp_lists]
    nakamoto_vals = [nakamoto(v, 0.50) for v in all_vp_lists]
    gini_med      = np.median([x for x in gini_vals if not np.isnan(x)])
    naka_med      = np.median([x for x in nakamoto_vals if not np.isnan(x)])

    results.append({
        "name":             dao["name"],
        "ticker":           dao["ticker"],
        "color":            dao["color"],
        "n_proposals":      len(props),
        "n_basic":          len(pass_results),
        "passage_rate":     passage_rate,
        "median_vp_M":      median_vp / 1e6,
        "participation_pct": participation_rate,
        "gini":             gini_med,
        "nakamoto_50":      naka_med,
    })
    print(f"  {dao['name']:12}  n={len(props):3d}  passage={passage_rate:.1f}%  "
          f"partic={participation_rate:.2f}%  gini={gini_med:.3f}  "
          f"nakamoto={naka_med:.0f}")

df = pd.DataFrame(results)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4  Plot
# ══════════════════════════════════════════════════════════════════════════════

print("\nStep 4: Building figure...")

fig, axes = plt.subplots(2, 2, figsize=(14, 10),
                         gridspec_kw={"hspace": 0.45, "wspace": 0.38})
((ax_gini, ax_partic), (ax_pass, ax_naka)) = axes

NAMES   = df["name"].tolist()
COLORS  = df["color"].tolist()
x       = np.arange(len(df))
BAR_W   = 0.6

def bar_panel(ax, values, ylabel, title, fmt="{:.2f}", highlight_idx=0,
              pct=False, invert_note=None):
    bars = ax.bar(x, values, width=BAR_W, color=COLORS, alpha=0.82,
                  edgecolor="white", linewidth=0.8, zorder=3)
    # Highlight Arbitrum with thicker edge
    bars[highlight_idx].set_edgecolor("#1A252F")
    bars[highlight_idx].set_linewidth(2.0)
    # Value labels on top
    for bar, val in zip(bars, values):
        if np.isnan(val):
            continue
        label = (f"{val:.1f}%" if pct else fmt.format(val))
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.003 * ax.get_ylim()[1],
                label, ha="center", va="bottom", fontsize=8.5, color="#333")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{r['name']}\n({r['ticker']})" for _, r in df.iterrows()],
                        fontsize=9)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title, fontsize=10.5, fontweight="bold", pad=8)
    ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.4)
    ax.set_ylim(0, max(v for v in values if not np.isnan(v)) * 1.25)
    if invert_note:
        ax.text(0.97, 0.97, invert_note, transform=ax.transAxes,
                fontsize=8, ha="right", va="top", color="#7F8C8D",
                bbox=dict(fc="white", ec="#BDC3C7", pad=3, alpha=0.8))

# ── (i) Gini coefficient ──────────────────────────────────────────────────────
bar_panel(ax_gini, df["gini"].tolist(),
          "Gini Coefficient of VP\n(among active voters)",
          "(i) Voting Power Concentration\n[higher = more concentrated; Arbitrum outlined]",
          fmt="{:.3f}",
          invert_note="Computed from top-1000 voters\nin 5 highest-turnout proposals")

# ── (ii) Participation rate ───────────────────────────────────────────────────
bar_panel(ax_partic, df["participation_pct"].tolist(),
          "Median VP Cast\n(% of circulating supply)",
          "(ii) Token Participation Rate\n[VP cast / circulating token supply]",
          fmt="{:.2f}%", pct=True,
          invert_note="Circulating supply: CoinGecko\nas of data collection date")

# ── (iii) Passage rate ────────────────────────────────────────────────────────
bar_panel(ax_pass, df["passage_rate"].tolist(),
          "% of Proposals Passing\n(For > Against)",
          "(iii) Proposal Passage Rate\n[basic For/Against proposals only]",
          fmt="{:.1f}%", pct=True)

# ── (iv) Nakamoto coefficient ─────────────────────────────────────────────────
bar_panel(ax_naka, df["nakamoto_50"].tolist(),
          "Min. Voters to Reach 50% VP\n(Nakamoto Coefficient)",
          "(iv) Nakamoto Coefficient (50% threshold)\n[lower = more concentrated; harder to block]",
          fmt="{:.0f}",
          invert_note="Median across 5 highest-turnout\nproposals per DAO")

# ── Common legend: Arbitrum highlight note ────────────────────────────────────
arb_patch = mpatches.Patch(facecolor=df.loc[df["name"]=="Arbitrum","color"].iloc[0],
                            edgecolor="#1A252F", linewidth=2,
                            label="Arbitrum (primary subject, bold border)")
fig.legend(handles=[arb_patch], loc="lower center", fontsize=9,
           framealpha=0.92, bbox_to_anchor=(0.5, -0.02))

fig.suptitle(
    "Figure A6: Cross-DAO Governance Benchmarking\n"
    "Voting Power Concentration, Participation, Passage Rate, and Minimum Control "
    "— Five DeFi DAOs on Snapshot, Jan 2023–Apr 2026\n"
    "(Optimism and Uniswap use on-chain governance not accessible via Snapshot API and are excluded)",
    fontsize=11.5, fontweight="bold", y=1.02
)

fig.savefig(OUT_PATH, dpi=180, bbox_inches="tight")
print(f"\nSaved to {OUT_PATH}")
print("\nFull results table:")
print(df[["name", "n_proposals", "passage_rate", "participation_pct",
          "gini", "nakamoto_50"]].to_string(index=False))
