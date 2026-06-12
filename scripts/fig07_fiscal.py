#!/usr/bin/env python3
"""
Figure 7: Fiscal Evolution & Treasury Dynamics
Journal of Finance paper on Arbitrum governance.

Data source: Snapshot governance proposals (proposal body text + known program records).

Approach:
  Layer 1 — Curated anchors for verified major programs (>5M ARB each).
             Amounts cross-referenced against Arbitrum Foundation public records,
             Gauntlet LTIPP retro, and community governance posts.
  Layer 2 — Targeted regex parsing of Treasury Spend proposal bodies for
             remaining smaller programs (<5M ARB), using request-specific
             language patterns to avoid false positives.

Category definitions:
  Ecosystem Incentives  STIP, LTIPP, Gaming Catalyst, DRIP, STIP-Bridge addenda
  Treasury Management   STEP programs, ATMC, RWA investments
  Grants & Research     Questbook, ARDC, Gitcoin, service providers, OpCo
  Delegate & Ops        DIP, RAD, Security Council, MSS, events, legal

The figure shows governance-approved disbursements mapped to the quarter of
DAO approval — not the accounting settlement date.  For a governance paper,
the decision date is the relevant event.
"""

import os
import re
import time
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys as _sys
_sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, C_TOTAL, C_SHOCK, savefig as aer_savefig
apply_aer_style()
import matplotlib.ticker as mticker
import matplotlib.patches as mpatches

HERE     = os.path.dirname(os.path.abspath(__file__))
ROOT     = os.path.dirname(HERE)   # project root
OUT_DIR  = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH     = os.path.join(OUT_DIR, "fig07_fiscal.png")
SNAPSHOT_URL = "https://hub.snapshot.org/graphql"
SPACE        = "arbitrumfoundation.eth"

# ── Layer 1: Curated major program anchors ────────────────────────────────────
# Each entry: (approval_quarter, arb_millions, category, label)
# Sources: Arbitrum Foundation transparency posts, Gauntlet LTIPP retro,
#          Messari governance reports, and on-chain confirmation.
ANCHORS = [
    # Ecosystem Incentives
    ("2023Q4", 71.4,  "Ecosystem Incentives", "STIP (71.4M)"),
    ("2024Q1", 45.0,  "Ecosystem Incentives", "LTIPP (45M)"),
    ("2024Q1", 200.0, "Ecosystem Incentives", "Gaming Catalyst (200M)"),
    ("2024Q3", 36.0,  "Ecosystem Incentives", "STIP-Bridge (36M)"),
    ("2025Q2", 80.0,  "Ecosystem Incentives", "DRIP (80M)"),

    # Treasury Management
    ("2024Q1", 35.0,  "Treasury Management",  "STEP 1.0 (35M)"),
    ("2024Q3", 35.0,  "Treasury Management",  "STEP 1.1 (35M)"),
    ("2024Q3", 250.0, "Treasury Management",  "Foundation Strategic (250M)"),
    ("2025Q1", 35.0,  "Treasury Management",  "STEP 2.0 (35M)"),

    # Grants & Research
    ("2023Q2", 4.0,   "Grants & Research",    "Questbook Phase 1 (4M)"),
    ("2023Q4", 1.7,   "Grants & Research",    "ARDC v1 (1.7M)"),
    ("2024Q1", 1.5,   "Grants & Research",    "Entropy v1 (1.5M)"),
    ("2024Q4", 22.0,  "Grants & Research",    "OpCo (22M)"),
    ("2025Q3", 15.0,  "Grants & Research",    "Entropy v2 (15M)"),

    # Delegate & Ops
    ("2023Q4", 1.5,   "Delegate & Ops",       "DIP v1 (1.5M)"),
    ("2024Q3", 11.0,  "Delegate & Ops",       "DIP Extension (11M)"),
    ("2024Q4", 4.0,   "Delegate & Ops",       "Events Budget (4M)"),
    ("2025Q4", 0.2,   "Delegate & Ops",       "RAD (0.2M)"),
]

CATEGORIES = [
    "Ecosystem Incentives",
    "Treasury Management",
    "Grants & Research",
    "Delegate & Ops",
]

CAT_COLORS = {
    "Ecosystem Incentives": "#2980B9",
    "Treasury Management":  "#8E44AD",
    "Grants & Research":    "#27AE60",
    "Delegate & Ops":       "#E67E22",
}

# ── Layer 2: Parse smaller proposals from Snapshot body text ──────────────────
# Patterns that strongly indicate a budget request (not a reference):
REQUEST_RE = re.compile(
    r'(?:request(?:ing)?|budget(?:\s+of)?|ask(?:ing)?|propos(?:e|ing)\s+to\s+(?:spend|use|allocate)|'
    r'total\s+(?:cost|budget|ask|request)|fund(?:ing)?\s+of|allocat(?:e|ion)\s+of)\s*:?\s*'
    r'(?P<n>[\d,]+(?:\.\d+)?)\s*(?P<unit>M|K|million|thousand)?\s*(?:\$\s*)?ARB\b',
    re.I
)
# Also catch "X ARB" in abstract/summary sections of proposals
AMOUNT_RE = re.compile(
    r'\b(?P<n>[\d,]+(?:\.\d+)?)\s*(?P<unit>M|million)?\s*ARB\b',
    re.I
)

def parse_request_arb(title, body):
    """Extract the primary budget request in ARB from a proposal."""
    text = (title + "\n" + body[:4000])

    # Try strong request patterns first
    for m in REQUEST_RE.finditer(text):
        n = float(m.group('n').replace(',', ''))
        u = (m.group('unit') or '').lower()
        if u in ('m', 'million'): n *= 1e6
        elif u in ('k', 'thousand'): n *= 1e3
        if 10_000 <= n <= 50_000_000:   # 0.01M – 50M ARB range for small proposals
            return n / 1e6

    # Fallback: first plausible amount in abstract section
    abstract_match = re.search(r'(?:abstract|summary|overview|tldr)[:\s]*(.{0,600})', text, re.I | re.S)
    search_zone = abstract_match.group(1) if abstract_match else text[:600]
    for m in AMOUNT_RE.finditer(search_zone):
        n = float(m.group('n').replace(',', ''))
        u = (m.group('unit') or '').lower()
        if u in ('m', 'million'): n *= 1e6
        if 100_000 <= n <= 5_000_000:   # 0.1M – 5M only for fallback
            return n / 1e6

    return None


# ── Step 1: Fetch all proposals ───────────────────────────────────────────────

PROP_QUERY = """
{
  proposals(
    first: 1000
    skip: 0
    where: { space_in: ["%s"], state: "closed" }
    orderBy: "created"
    orderDirection: asc
  ) {
    id title body type created scores_total
  }
}
""" % SPACE

print("Step 1: Fetching proposals from Snapshot...")
resp = requests.post(SNAPSHOT_URL, json={"query": PROP_QUERY}, timeout=30)
proposals = resp.json()["data"]["proposals"]
print(f"  {len(proposals)} proposals")


# ── Step 2: Apply figure2b_v2 classifier to identify Treasury Spend ───────────

TITLE_TRANSFER_RE = re.compile(r'\btransfer\b.{0,60}\b(eth|arb|stablecoin|usdc|usdt)\b', re.I)
TITLE_FUND_RE     = re.compile(r'\b(fund(s|ing)?(\s+the|\s+to)?|bootstrap|operational\s+cost)\b', re.I)
TITLE_INST_RE     = re.compile(
    r'\b(code\s+of\s+conduct|dao\s+procedures?|security\s+council\s+election\s+date|'
    r'validator\b|expansion\s+program|treasury\s+management\s+council|governance\s+forum)\b', re.I)
RULES_KW = re.compile(
    r'\b(arbos|protocol\s+upgrade|amend(\s+the)?\s+constitution|governance\s+timelock|'
    r'quorum\s+(threshold|reduction)|dvp\s+quorum|stylus\s+(vm|upgrade)|timeboost|'
    r'tether\s+bridge|fee\s+router|aip-?1\b|aip\s+1\b)\b', re.I)
INST_KW = re.compile(
    r'\b(establish\s+(a\s+)?(committee|council|working\s+group)|\bcommittee\b|'
    r'delegate\s+incentive|election\s+standard|dao\s+procedures|delegate\s+accountability|'
    r'reconfirmation|voting\s+power\s+(of|adjustment)|agentic\s+governance|opco)\b', re.I)
SPEND_KW = re.compile(
    r'\b(grant|budget|funding\s+request|disbursement|milestone|arb\s+allocation|'
    r'treasury\s+allocation|treasury\s+management|service\s+provider|'
    r'investment\s+(vehicle|fund|program)|yield|rwa|real.world\s+asset|'
    r'ecosystem\s+fund|ltipp|stip|gaming\s+catalyst|subsid|catalyst\s+program|'
    r'exclusively\s+working\s+with|govhack)\b', re.I)
ARBITRAGE_RE   = re.compile(r'direct\s+the\s+(arbitrum\s+)?foundation\s+to\s+implement', re.I)
TEMP_CHECK_RE  = re.compile(r'\btemp(erature)?\s*check\b', re.I)
CONST_RE       = re.compile(r'\[constitutional\]|\bconstitutional\s+aip\b', re.I)

def classify(title, body, vote_type):
    if vote_type in ("ranked-choice", "weighted", "approval"):
        return "Institution Building"
    if TEMP_CHECK_RE.search(title): return "Temp Check"
    combined = title + " " + (body or "")
    if ARBITRAGE_RE.search(combined): return "Rules Change"
    if TITLE_TRANSFER_RE.search(title): return "Treasury Spend"
    if TITLE_INST_RE.search(title): return "Institution Building"
    if TITLE_FUND_RE.search(title) and not CONST_RE.search(title): return "Treasury Spend"
    if CONST_RE.search(title): return "Rules Change"
    if RULES_KW.search(combined): return "Rules Change"
    if INST_KW.search(combined): return "Institution Building"
    if SPEND_KW.search(combined): return "Treasury Spend"
    return "Unclassified"


# ── Step 3: Parse Layer 2 amounts from Treasury Spend proposals ───────────────

print("Step 2-3: Classifying and parsing smaller Treasury Spend proposals...")

# Anchor proposal titles to skip in Layer 2 (already captured in Layer 1)
ANCHOR_TITLE_SKIP = re.compile(
    r'short.term\s+incentive|long.term\s+incentive\s+pilot|ltipp|stip|'
    r'gaming\s+catalyst|hadouken|step\s+program|stable\s+treasury\s+endow|'
    r'defi\s+renaissance|stip.bridge|foundation.{0,30}strategic\s+partner|'
    r'opco|delegate\s+incentive\s+program|rewarding\s+active|events\s+budget|'
    r'entropy\s+advisor',
    re.I
)

# Sub-proposal patterns to skip
SUB_PROPOSAL_SKIP = re.compile(
    r'(round\s+[12]|post\s+council\s+feedback|\[post\s+council|ltipp\s+extension|'
    r'stip\s+addendum|ltipp\s+council\s+recommended|retroactive\s+community\s+funding|'
    r'msig\s+support|restitution|msig|aave\s+dao|pyth\s+network\s+ltipp|'
    r'synthetix\s+ltip)',
    re.I
)

layer2_records = []
for p in proposals:
    title = p["title"]
    body  = p["body"] or ""
    cat   = classify(title, body, p.get("type","single-choice"))
    dt    = pd.to_datetime(p["created"], unit="s")

    if cat != "Treasury Spend":
        continue
    if ANCHOR_TITLE_SKIP.search(title):
        continue
    if SUB_PROPOSAL_SKIP.search(title):
        continue
    if dt < pd.Timestamp("2023-01-01") or dt > pd.Timestamp("2026-04-01"):
        continue

    arb_m = parse_request_arb(title, body)
    if arb_m is None or arb_m < 0.05:
        continue

    # Assign sub-category
    t = title.lower()
    b = body.lower()
    if any(k in t+b for k in ['questbook','domain allocat','gitcoin','hackathon',
                                'research','ardc','watchdog','bounty','audit']):
        sub_cat = "Grants & Research"
    elif any(k in t+b for k in ['treasury management','atmc','tmc','endowment',
                                  'step','rwa','real.world','diversif','yield',
                                  'token swap','strategic']):
        sub_cat = "Treasury Management"
    elif any(k in t+b for k in ['delegate','council\s+comp','security council',
                                  'mss','event','legal','advocacy','rad\s+program',
                                  'dip ','operational']):
        sub_cat = "Delegate & Ops"
    else:
        sub_cat = "Grants & Research"

    layer2_records.append({
        "quarter": str(pd.Period(dt, "Q")),
        "arb_m":   arb_m,
        "category": sub_cat,
        "label":   f"{title[:40]} ({arb_m:.1f}M)",
    })
    print(f"  Layer 2: {dt.strftime('%Y-%m')}  {arb_m:6.2f}M ARB  [{sub_cat}]  {title[:55]}")

print(f"\n  Layer 2 total: {len(layer2_records)} proposals, "
      f"{sum(r['arb_m'] for r in layer2_records):.1f}M ARB")


# ── Step 4: Merge layers and aggregate to quarters ────────────────────────────

print("\nStep 4: Aggregating to quarters...")

# All quarters 2023Q1 – 2026Q1
all_q = [str(q) for q in pd.period_range("2023Q1", "2026Q1", freq="Q")]

records = []
for q, arb_m, cat, label in ANCHORS:
    records.append({"quarter": q, "arb_m": arb_m, "category": cat, "label": label})
records.extend(layer2_records)

df = pd.DataFrame(records)
df["quarter"] = pd.Categorical(df["quarter"], categories=all_q, ordered=True)

spend_df = (
    df.groupby(["quarter", "category"])["arb_m"]
    .sum()
    .unstack(fill_value=0)
    .reindex(all_q, fill_value=0)
    .reindex(columns=CATEGORIES, fill_value=0)
)

# Governance-implied treasury balance
# DAO treasury received 3,500M ARB at genesis (Mar 2023)
# Plus 69M ARB from unclaimed airdrop (Sep 2023 = 2023Q3)
GENESIS_M  = 3_500.0
AIRDROP_M  =    69.0

quarterly_net = -spend_df.sum(axis=1).copy()
quarterly_net["2023Q3"] += AIRDROP_M   # airdrop reclaim inflow

balance = pd.Series(index=all_q, dtype=float)
running = GENESIS_M
for q in all_q:
    running    += quarterly_net[q]
    balance[q]  = running

print(f"\nQuarterly disbursements (M ARB):")
print(spend_df.to_string())
print(f"\nImplied treasury balance (M ARB):")
for q, b in balance.items():
    print(f"  {q}: {b:.0f}M ARB")
print(f"\nTotal approved disbursements: {spend_df.sum().sum():.0f}M ARB")


# ── Step 5: Plot ──────────────────────────────────────────────────────────────

print("\nStep 5: Building figure...")

fig, (ax_spend, ax_bal) = plt.subplots(
    2, 1, figsize=(15, 9), sharex=True,
    gridspec_kw={"height_ratios": [1.3, 1], "hspace": 0.06}
)

x      = np.arange(len(all_q))
bar_w  = 0.68

# ── Top: stacked bars by category ────────────────────────────────────────────
bottoms = np.zeros(len(all_q))
for cat in CATEGORIES:
    vals = spend_df[cat].values
    ax_spend.bar(x, vals, bar_w, bottom=bottoms,
                 color=CAT_COLORS[cat], alpha=0.88,
                 label=cat, zorder=3)
    # Label significant bars (>10M ARB for a category slice)
    for xi, (v, b) in enumerate(zip(vals, bottoms)):
        if v >= 10:
            ax_spend.text(xi, b + v/2, f"{v:.0f}M",
                          ha="center", va="center",
                          fontsize=7, fontweight="bold", color="white")
    bottoms += vals

# Stack total on top
for xi, tot in enumerate(bottoms):
    if tot >= 5:
        ax_spend.text(xi, tot + 1.5, f"{tot:.0f}M",
                      ha="center", va="bottom", fontsize=7.5, fontweight="bold")

ax_spend.set_ylabel("ARB Approved for Disbursement (M ARB)", fontsize=11)
ax_spend.set_ylim(0, bottoms.max() * 1.40)
ax_spend.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}M"))
ax_spend.legend(loc="upper left", fontsize=9, framealpha=0.92, ncol=2)
ax_spend.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.35)
ax_spend.set_title("(a) Quarterly ARB Approved by Category (governance date)",
                   fontsize=11, style="italic", pad=5)

# Annotate the two dominant programs
for q_str, lbl, offset in [("2023Q4", "STIP", 5), ("2024Q1", "LTIPP +\nGaming", 5)]:
    if q_str in all_q:
        xi  = all_q.index(q_str)
        tot = spend_df.loc[q_str].sum()
        ax_spend.annotate(lbl,
            xy=(xi, tot), xytext=(xi + 0.55, tot + offset),
            fontsize=8.5, color="#1a5276", fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="#1a5276", lw=1.1))

# ── Bottom: governance-implied treasury balance ───────────────────────────────
bal_vals = balance.values

ax_bal.plot(x, bal_vals, color="#2C3E50", linewidth=2.4,
            marker="o", markersize=5.5, zorder=4,
            markerfacecolor="white", markeredgewidth=1.8,
            label="Governance-implied treasury balance")
ax_bal.fill_between(x, bal_vals, color="#2C3E50", alpha=0.08, zorder=3)

# Shade the post-Foundation-Strategic-Partnerships drop
drop_start = all_q.index("2024Q3") if "2024Q3" in all_q else None
if drop_start:
    ax_bal.annotate("Foundation Strategic\nPartnership transfer\n(250M ARB)",
        xy=(drop_start, balance["2024Q3"]),
        xytext=(drop_start + 1.2, balance["2024Q3"] + 150),
        fontsize=8, color="#6c3483",
        arrowprops=dict(arrowstyle="->", color="#6c3483", lw=1.1),
        bbox=dict(fc="white", ec="#8e44ad", pad=2.5, alpha=0.9))

ax_bal.set_ylabel("ARB Treasury Balance\n(governance-implied, M ARB)", fontsize=11)
ax_bal.set_ylim(0, GENESIS_M * 1.15)
ax_bal.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v/1000:.1f}B"))
ax_bal.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.35)
ax_bal.legend(loc="upper right", fontsize=9, framealpha=0.92)
ax_bal.set_title("(b) Governance-Implied Treasury Balance (end of quarter)",
                 fontsize=11, style="italic", pad=5)

# ── X-axis ────────────────────────────────────────────────────────────────────
ax_bal.set_xticks(x)
ax_bal.set_xticklabels(all_q, rotation=45, ha="right", fontsize=8)
ax_bal.set_xlim(-0.6, len(all_q) - 0.4)

fig.suptitle(
    "Figure 7: Fiscal Evolution & Treasury Dynamics\n"
    "Arbitrum DAO — Quarterly ARB Approved by Governance, 2023 Q1 – 2026 Q1\n"
    "(Layer 1: curated major programs; Layer 2: parsed Treasury Spend proposals; "
    "balance inferred from approved disbursements)",
    fontsize=11, fontweight="bold", y=1.02
)

fig.savefig(OUT_PATH, dpi=180, bbox_inches="tight")
print(f"\nSaved to {OUT_PATH}")
