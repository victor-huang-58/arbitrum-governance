#!/usr/bin/env python3
"""
Figure 4: Quorum Utilization & Counterfactual Fragility
Journal of Finance paper on Arbitrum governance.

Walk-through:
  1. Fetch all closed Arbitrum DAO proposals from Snapshot (scores_total + type)
  2. Classify proposals by economic purpose (reusing figure2b_v2 classifier)
  3. Assign approximate quorum thresholds by period and track
     (Snapshot's quorum field is always 0 for Arbitrum; thresholds hardcoded from
      the Arbitrum Constitution and governance proposals)
  4. Compute utilization ratio = scores_total / quorum_threshold
  5. Plot scatter (time × utilization), colored by economic category,
     with vertical lines at the four major quorum-rule change events and
     a horizontal reference at utilization = 1.0 (bare quorum)

Quorum thresholds (Arbitrum Constitution + governance records):
  Constitutional: 5 % of votable supply (~67.5 M ARB, 2023–2025);
                  reduced to 4 % (~54 M ARB) after May 2025 reduction AIP;
                  DVP model applies from Feb 2026 (mechanism changes, not %).
  Non-Constitutional / unlabeled: 3 % of votable supply (~40.5 M ARB throughout).
  Votable supply assumed constant at ~1.35 B ARB (delegated tokens at launch).
  All thresholds are approximate; ± 10–15 % uncertainty is plausible.
"""

import os
import time
import re
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys as _sys
_sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, C_TOTAL, C_SHOCK, savefig as aer_savefig
apply_aer_style()
import matplotlib.ticker as mticker
import matplotlib.lines as mlines

HERE     = os.path.dirname(os.path.abspath(__file__))
ROOT     = os.path.dirname(HERE)   # project root
OUT_DIR  = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, "fig04_taxonomy.png")

SNAPSHOT_URL = "https://hub.snapshot.org/graphql"
SPACE        = "arbitrumfoundation.eth"

# ── Quorum rule-change events ─────────────────────────────────────────────────
# Vertical lines on the time axis.  Dates are when the winning Snapshot vote
# closed, which marks when the rule became effective (or was ratified for
# off-chain action).
QUORUM_EVENTS = [
    {"date": "2023-03-27", "label": "Original\n(AIP-1)",          "color": "#7F8C8D"},
    {"date": "2025-05-22", "label": "Constitutional\nQuorum −1pp","color": "#8E44AD"},
    {"date": "2025-10-09", "label": "DVP Quorum\nTemp Check",     "color": "#E67E22"},
    {"date": "2026-02-05", "label": "DVP Quorum\nImplementation", "color": "#C0392B"},
]

# ── Approximate quorum thresholds (millions ARB) by period ────────────────────
# Votable supply ≈ 1.35 B ARB (constant approximation for the full period).
VOTABLE_SUPPLY_M = 1_350  # millions ARB

CONST_PCT = {
    "2023-03-27": 0.050,   # 5 %  (original)
    "2025-05-22": 0.040,   # 4 %  (Constitutional Quorum Threshold Reduction)
    "2026-02-05": 0.040,   # DVP mechanism applied; % unchanged but denominator shifts
}
NC_PCT = 0.030             # 3 % throughout (no NC-specific reduction passed)

def quorum_for(date: pd.Timestamp, is_constitutional: bool) -> float:
    """Return approximate quorum in millions ARB for a given date and track."""
    if is_constitutional:
        pct = 0.050
        for cutoff, p in sorted(CONST_PCT.items()):
            if date >= pd.Timestamp(cutoff):
                pct = p
        return pct * VOTABLE_SUPPLY_M
    else:
        return NC_PCT * VOTABLE_SUPPLY_M


# ── Step 1: Fetch all closed proposals ───────────────────────────────────────

QUERY = """
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
    body
    type
    created
    choices
    scores
    scores_total
  }
}
"""

print("Step 1: Fetching all closed proposals from Snapshot...")
all_proposals = []
skip = 0
while True:
    resp = requests.post(SNAPSHOT_URL, json={"query": QUERY % (skip, SPACE)}, timeout=30)
    resp.raise_for_status()
    batch = resp.json().get("data", {}).get("proposals", [])
    if not batch:
        break
    all_proposals.extend(batch)
    print(f"  Fetched {len(batch)} proposals (total: {len(all_proposals)})")
    if len(batch) < 1000:
        break
    skip += 1000
    time.sleep(0.5)

print(f"  Total: {len(all_proposals)}")


# ── Step 2: Economic classifier (identical to figure2b_v2) ───────────────────

TITLE_TRANSFER_RE = re.compile(r'\btransfer\b.{0,60}\b(eth|arb|stablecoin|usdc|usdt)\b', re.I)
TITLE_FUND_RE     = re.compile(r'\b(fund(s|ing)?(\s+the|\s+to)?|bootstrap|operational\s+cost)\b', re.I)
TITLE_INST_RE     = re.compile(
    r'\b(code\s+of\s+conduct|dao\s+procedures?|reporting\s+(and\s+information|function)|'
    r'security\s+council\s+election\s+date|time\s+management\s+in\s+arbitrum|'
    r'validator\b|metrics\s+for\s+orbit|orbit\s+chain.{0,20}metric|'
    r'expansion\s+program|treasury\s+management\s+council|'
    r'governance\s+forum|proposals\.app)\b', re.I)
RULES_KW = re.compile(
    r'\b(arbos|protocol\s+upgrade|deploy\s+contract|chain\s+owner|'
    r'amend(\s+the)?\s+constitution|constitution\s+(text|amendment)|'
    r'governance\s+timelock|l2\s+timelock|quorum\s+(threshold|reduction)|dvp\s+quorum|'
    r'smart\s+contract\s+parameter|stylus\s+(vm|upgrade|version|runtime)|'
    r'fee\s+parameter|gas\s+target|l2\s+base\s+fee|pricing\s+algor|'
    r'l2\s+upgrade|security\s+council\s+election\s+process|'
    r'permissionless\s+validation|timeboost|'
    r'upgrade\s+executor|tether\s+bridge|cost\s+cap|fee\s+router|'
    r'generic.custom\s+gateway|custom\s+gateway|'
    r'aip-?1\b|aip\s+1\b)\b', re.I)
INST_KW = re.compile(
    r'\b(establish\s+(a\s+)?(committee|council|working\s+group)|'
    r'\bcommittee\b|code\s+of\s+conduct|'
    r'standardized\s+guideline|governance\s+process|governance\s+framework|'
    r'delegate\s+incentive|delegate\s+code|election\s+standard|'
    r'non-?security\s+council\s+election|ratification\s+process|'
    r'dao\s+procedures|delegate\s+accountability|'
    r'domain\s+allocator\s+election|reconfirmation|re.confirmation|'
    r'voting\s+power\s+(of|adjustment|calibration)|'
    r'mission.{0,10}vision|agentic\s+governance|opco|'
    r'arbitrum\s+coalition|security\s+enhancement\s+fund)\b', re.I)
SPEND_KW = re.compile(
    r'\b(grant|budget|funding\s+request|disbursement|milestone|'
    r'arb\s+allocation|treasury\s+allocation|treasury\s+management|'
    r'service\s+provider|investment\s+(vehicle|fund|program)|'
    r'yield|rwa|real.world\s+asset|diversif|'
    r'ecosystem\s+fund|ltipp|stip|gaming\s+catalyst|'
    r'subsid|catalyst\s+program|exclusively\s+working\s+with|'
    r'arbiter\s+proposal|govhack|onboarding\s+incentive)\b', re.I)
ARBITRAGE_RE         = re.compile(r'direct\s+the\s+(arbitrum\s+)?foundation\s+to\s+implement', re.I)
TEMP_CHECK_RE        = re.compile(r'\btemp(erature)?\s*check\b', re.I)
CONSTITUTIONAL_RE    = re.compile(r'\[constitutional\]|\bconstitutional\s+aip\b', re.I)

def classify_economic(title, body, vote_type):
    if vote_type in ("ranked-choice", "weighted", "approval"):
        return "Institution Building"
    if TEMP_CHECK_RE.search(title):
        return "Temp Check"
    combined = title + " " + (body or "")
    if ARBITRAGE_RE.search(combined):
        return "Rules Change"
    if TITLE_TRANSFER_RE.search(title):
        return "Treasury Spend"
    if TITLE_INST_RE.search(title):
        return "Institution Building"
    if TITLE_FUND_RE.search(title) and not CONSTITUTIONAL_RE.search(title):
        return "Treasury Spend"
    if CONSTITUTIONAL_RE.search(title):
        return "Rules Change"
    if RULES_KW.search(combined):
        return "Rules Change"
    if INST_KW.search(combined):
        return "Institution Building"
    if SPEND_KW.search(combined):
        return "Treasury Spend"
    return "Unclassified"

def is_constitutional(title):
    return bool(CONSTITUTIONAL_RE.search(title))


# ── Step 3: Build records + assign quorum ─────────────────────────────────────

print("\nStep 2–3: Classifying and computing quorum utilization...")
records = []
for p in all_proposals:
    category = classify_economic(
        p.get("title", ""),
        p.get("body", "") or "",
        p.get("type", "single-choice"),
    )
    if category in ("Temp Check",):
        continue

    created = pd.to_datetime(p["created"], unit="s")
    total_votes_M = p.get("scores_total", 0) / 1e6

    constitutional = is_constitutional(p.get("title", ""))
    quorum_M = quorum_for(created, constitutional)
    utilization = total_votes_M / quorum_M if quorum_M > 0 else np.nan

    records.append({
        "id":           p["id"],
        "title":        p["title"],
        "category":     category,
        "constitutional": constitutional,
        "created":      created,
        "votes_M":      total_votes_M,
        "quorum_M":     quorum_M,
        "utilization":  utilization,
        "vote_type":    p.get("type", ""),
    })

df = pd.DataFrame(records)
df = df[(df["created"] >= "2023-01-01") & (df["created"] <= "2026-04-01")]

print(f"  Analysis universe: {len(df)} proposals")
print(df["category"].value_counts().to_string())
print(f"\n  Utilization stats:")
print(f"    min:    {df['utilization'].min():.2f}x")
print(f"    median: {df['utilization'].median():.2f}x")
print(f"    max:    {df['utilization'].max():.2f}x")
print(f"    below 1.0 (quorum miss): {(df['utilization'] < 1.0).sum()}")


# ── Step 4: Compute turnout % of votable supply ───────────────────────────────
# Voter turnout % = votes cast / votable supply × 100.
# Votable supply ≈ 1,350 M ARB (delegated at launch, held approximately constant).
# Quorum thresholds in % terms:
#   Constitutional: 5% through May 2025, then 4%
#   Non-Constitutional: 3% throughout
# "People are not trading their voting rights": most ARB holders never delegate,
# so effective participation is a small slice of circulating supply.

df["turnout_pct"] = df["votes_M"] / VOTABLE_SUPPLY_M * 100

df_const  = df[df["constitutional"]].copy()
df_nc     = df[~df["constitutional"]].copy()

print(f"\nStep 4: Building figure...")
print(f"  Constitutional proposals: {len(df_const)}")
print(f"  Non-Constitutional proposals: {len(df_nc)}")
print(f"  Turnout % — Constitutional: median={df_const['turnout_pct'].median():.1f}%  "
      f"NC: median={df_nc['turnout_pct'].median():.1f}%")

import matplotlib.dates as mdates
from scipy import stats as spstats

COL_SPEND = "#2980B9"
COL_RULES = "#C0392B"
COL_INST  = "#27AE60"
COL_OTHER = "#95A5A6"
CAT_COLORS = {
    "Treasury Spend":       COL_SPEND,
    "Rules Change":         COL_RULES,
    "Institution Building": COL_INST,
    "Unclassified":         COL_OTHER,
}

XLIM = (pd.Timestamp("2023-01-01"), pd.Timestamp("2026-05-01"))

fig, (ax_c, ax_nc_ax) = plt.subplots(1, 2, figsize=(16, 5.5),
                                      sharey=True, gridspec_kw={"wspace": 0.06})

def scatter_panel(ax, sub_df, panel_label):
    for cat, color in CAT_COLORS.items():
        s = sub_df[sub_df["category"] == cat]
        if s.empty:
            continue
        ax.scatter(s["created"], s["turnout_pct"],
                   color=color, s=48, alpha=0.78, zorder=4,
                   edgecolors="white", linewidths=0.4, label=cat)

    # Overall OLS trend line across all categories
    ds = sub_df.dropna(subset=["turnout_pct"]).sort_values("created")
    if len(ds) >= 5:
        x_num = (ds["created"] - ds["created"].min()).dt.days.values.astype(float)
        y     = ds["turnout_pct"].values
        slope, intercept, r, p, _ = spstats.linregress(x_num, y)
        x_line = np.array([0, (XLIM[1] - ds["created"].min()).days])
        y_line = intercept + slope * x_line
        t_dates = [ds["created"].min(), XLIM[1]]
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
        ax.plot(t_dates, y_line, color="#2C3E50", linewidth=2.0,
                linestyle="-", alpha=0.75, zorder=5,
                label=f"OLS trend  (r={r:.2f}, {sig})")

    ax.set_xlim(*XLIM)
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
    ax.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.set_title(panel_label, fontsize=11, style="italic", pad=8)

# ── Panel A: Constitutional ───────────────────────────────────────────────────
scatter_panel(ax_c, df_const, "(a) Constitutional track")

# Quorum line: 5% until May 2025, then steps to 4%
step_date = pd.Timestamp("2025-05-22")
ax_c.hlines(5.0, XLIM[0], step_date, colors="#1a1a1a",
            linewidth=1.5, linestyle="--", zorder=6)
ax_c.hlines(4.0, step_date, XLIM[1], colors="#1a1a1a",
            linewidth=1.5, linestyle="--", zorder=6)
ax_c.plot([step_date, step_date], [5.0, 4.0], color="#1a1a1a",
          linewidth=1.5, linestyle="--", zorder=6)
ax_c.text(pd.Timestamp("2023-06-01"), 5.25, "Quorum = 5%",
          fontsize=8, color="#1a1a1a", va="bottom")
ax_c.text(pd.Timestamp("2025-08-01"), 4.25, "4%",
          fontsize=8, color="#1a1a1a", va="bottom")

ax_c.set_ylabel("Voter Turnout  (% of delegated / votable supply)", fontsize=11)

# ── Panel B: Non-Constitutional ───────────────────────────────────────────────
scatter_panel(ax_nc_ax, df_nc, "(b) Non-Constitutional track")

ax_nc_ax.axhline(3.0, color="#1a1a1a", linewidth=1.5, linestyle="--", zorder=6)
ax_nc_ax.text(pd.Timestamp("2023-06-01"), 3.25, "Quorum = 3%",
              fontsize=8, color="#1a1a1a", va="bottom")
ax_nc_ax.tick_params(axis="y", left=False)

# ── Shared y-axis ─────────────────────────────────────────────────────────────
y_max = max(df["turnout_pct"].max() * 1.25, 25)
ax_c.set_ylim(0, y_max)
ax_c.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))

# ── Legend: build manually so all 4 categories + trend line always appear ─────
legend_elements = []
for cat, color in CAT_COLORS.items():
    legend_elements.append(
        mlines.Line2D([0], [0], marker="o", color="w", markerfacecolor=color,
                      markersize=7, label=cat))
legend_elements.append(
    mlines.Line2D([0], [0], color="#2C3E50", linewidth=2.0, linestyle="-",
                  alpha=0.75, label="OLS trend"))
ax_c.legend(handles=legend_elements, loc="upper left", fontsize=8.5, framealpha=0.92)

fig.suptitle(
    "Figure 4: Voter Turnout and Quorum Adequacy\n"
    "Arbitrum DAO — Snapshot Votes, 2023–2026  "
    "(% of delegated/votable supply; quorum thresholds marked)",
    fontsize=12, fontweight="bold", y=1.02
)

fig.tight_layout()
fig.savefig(OUT_PATH, dpi=180, bbox_inches="tight")
print(f"\nSaved to {OUT_PATH}")
