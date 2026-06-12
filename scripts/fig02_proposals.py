#!/usr/bin/env python3
"""
Figure 2 (v2): Proposal Activity and Vote Margins by Economic Category
Journal of Finance paper on Arbitrum governance.

Walk-through:
  1. Fetch all closed Arbitrum DAO proposals from Snapshot (title + body + type)
  2. Exclude temperature checks (non-binding sentiment polls)
  3. Classify by ECONOMIC PURPOSE from first principles — not the self-reported
     Constitutional/Non-Constitutional label, which is endogenous to passage difficulty:
       - Treasury Spend    : grants, service providers, investments, programs
       - Rules Change      : protocol upgrades, constitution amendments, quorum changes
       - Institution Build : committees, frameworks, election rules, codes of conduct
       - [flagged]         : "Constitutional Arbitrage" — Routes a Rules Change through
                             the Non-Constitutional track via "direct the Foundation" framing
  4. Print full breakdown so categories can be validated manually
  5. Group by half-year → plot submission counts (stacked bars) + avg For% (lines)
"""

import os
import time
import re
import requests
import pandas as pd
import matplotlib.pyplot as plt
import sys as _sys
_sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, C_TOTAL, C_SHOCK, savefig as aer_savefig
apply_aer_style()
import matplotlib.ticker as mticker
import numpy as np

HERE    = os.path.dirname(os.path.abspath(__file__))
ROOT    = os.path.dirname(HERE)   # project root
OUT_DIR = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, "fig02_proposals.png")

SNAPSHOT_URL   = "https://hub.snapshot.org/graphql"
SPACE          = "arbitrumfoundation.eth"

# ── Step 1: Fetch all closed proposals ───────────────────────────────────────
# We now fetch body + type in addition to title/scores so the economic
# classifier can use proposal text rather than just the bracket label.
#
# body  – full proposal markdown text (used for keyword matching)
# type  – Snapshot vote type: "single-choice" | "ranked-choice" | "weighted"
#         ranked-choice / weighted → committee or council elections

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
    state
    created
    choices
    scores
    scores_total
  }
}
"""

print("Step 1: Fetching all closed proposals from Snapshot (with body + type)...")
all_proposals = []
skip = 0

while True:
    resp = requests.post(
        SNAPSHOT_URL,
        json={"query": QUERY % (skip, SPACE)},
        timeout=30
    )
    resp.raise_for_status()
    batch = resp.json().get("data", {}).get("proposals", [])
    if not batch:
        break
    all_proposals.extend(batch)
    print(f"  Fetched {len(batch)} proposals (total so far: {len(all_proposals)})")
    if len(batch) < 1000:
        break
    skip += 1000
    time.sleep(0.5)

print(f"  Total proposals fetched: {len(all_proposals)}")


# ── Step 2: Economic classifier ───────────────────────────────────────────────
# Categories are mutually exclusive and ordered by specificity.
# Priority order matters: arbitrage flag → temp-check exclude → rules change →
# institution building → treasury spend → unclassified.
#
# "Constitutional Arbitrage": proposals that say "direct the Foundation to
#  implement X" to route a substantive protocol change through the lower-quorum
#  Non-Constitutional track.  Treated as Rules Change in the analysis but
#  flagged separately so you can study them as a distinct phenomenon.

# Title-level overrides applied before any body-text keyword matching.
# These catch proposals whose titles unambiguously signal a category
# but whose bodies would otherwise trigger a wrong keyword.

# Treasury Spend: "Transfer X ETH/ARB/stablecoins from the treasury..."
TITLE_TRANSFER_RE = re.compile(
    r'\btransfer\b.{0,60}\b(eth|arb|stablecoin|usdc|usdt)\b',
    re.I
)

# Treasury Spend: fund/bootstrap/operational-cost titles that mention a
# specific protocol or sprint (e.g. "Fund the Stylus Sprint", "Funds to
# bootstrap the first BoLD validator")
TITLE_FUND_RE = re.compile(
    r'\b(fund(s|ing)?(\s+the|\s+to)?|bootstrap|operational\s+cost)\b',
    re.I
)

# Institution Building: code-of-conduct / DAO-procedures updates in title
TITLE_INST_RE = re.compile(
    r'\b(code\s+of\s+conduct|dao\s+procedures?|reporting\s+(and\s+information|function)|'
    r'security\s+council\s+election\s+date|time\s+management\s+in\s+arbitrum|'
    r'validator\b|metrics\s+for\s+orbit|orbit\s+chain.{0,20}metric|'
    r'expansion\s+program|treasury\s+management\s+council|'
    r'governance\s+forum|proposals\.app)\b',
    re.I
)

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
    r'aip-?1\b|aip\s+1\b)\b',
    re.I
)

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
    r'arbitrum\s+coalition|security\s+enhancement\s+fund)\b',
    re.I
)

SPEND_KW = re.compile(
    r'\b(grant|budget|funding\s+request|disbursement|milestone|'
    r'arb\s+allocation|treasury\s+allocation|treasury\s+management|'
    r'service\s+provider|investment\s+(vehicle|fund|program)|'
    r'yield|rwa|real.world\s+asset|diversif|'
    r'ecosystem\s+fund|ltipp|stip|gaming\s+catalyst|'
    r'subsid|catalyst\s+program|exclusively\s+working\s+with|'
    r'arbiter\s+proposal|govhack|onboarding\s+incentive)\b',
    re.I
)

ARBITRAGE_RE = re.compile(
    r'direct\s+the\s+(arbitrum\s+)?foundation\s+to\s+implement',
    re.I
)

TEMP_CHECK_RE = re.compile(
    r'\btemp(erature)?\s*check\b',
    re.I
)


CONSTITUTIONAL_TITLE_RE = re.compile(r'\[constitutional\]|\bconstitutional\s+aip\b', re.I)


def classify_economic(title: str, body: str, vote_type: str) -> str:
    # Elections use ranked-choice or weighted voting → Institution Building
    if vote_type in ("ranked-choice", "weighted", "approval"):
        return "Institution Building"

    # Temperature checks are non-binding sentiment polls → exclude
    if TEMP_CHECK_RE.search(title):
        return "Temp Check (exclude)"

    combined = title + " " + (body or "")

    # Constitutional Arbitrage: Routes a protocol change via "direct the Foundation"
    if ARBITRAGE_RE.search(combined):
        return "Rules Change (Arbitrage)"

    # Title-level overrides: these bypass body-text keywords entirely,
    # catching proposals whose titles make their category unambiguous.
    if TITLE_TRANSFER_RE.search(title):
        return "Treasury Spend"
    if TITLE_INST_RE.search(title):
        return "Institution Building"
    if TITLE_FUND_RE.search(title) and not CONSTITUTIONAL_TITLE_RE.search(title):
        return "Treasury Spend"

    # [Constitutional] bracket in title is a strong Rules Change signal —
    # proposers only use it when invoking the Core Governor (chain-level authority)
    if CONSTITUTIONAL_TITLE_RE.search(title):
        return "Rules Change"

    if RULES_KW.search(combined):
        return "Rules Change"

    if INST_KW.search(combined):
        return "Institution Building"

    if SPEND_KW.search(combined):
        return "Treasury Spend"

    return "Unclassified"


# ── Step 3: Build records ─────────────────────────────────────────────────────

records = []
for p in all_proposals:
    category = classify_economic(
        p.get("title", ""),
        p.get("body", "") or "",
        p.get("type", "single-choice"),
    )

    created_dt = pd.to_datetime(p["created"], unit="s")

    choices = [c.lower().strip() for c in p.get("choices", [])]
    scores  = p.get("scores", [])

    # Arbitrum Snapshot proposals use many non-standard choice labels.
    # Strategy: collect ALL for-side and ALL against-side indices, then sum
    # their scores.  This handles multi-option "for" votes correctly.
    #
    # Priority:
    #   1. Exact synonym match  ("for", "yes", "approve", ...)
    #   2. Prefix match         ("for:", "for -", "for [", "against:", ...)
    #   3. Keyword match        ("fund X" → for; "do not fund" → against)

    FOR_EXACT     = {"for", "yes", "yea", "approve", "support", "in favor",
                     "in favour", "accept", "agree"}
    AGAINST_EXACT = {"against", "no", "nay", "reject", "oppose",
                     "do not support", "disagree"}
    FOR_PFXS     = ("for ", "for:", "for,", "for-", "for–", "for—",
                    "for[", "in favor", "in favour", "yes,", "yes-",
                    "approve ", "fund ", "elect ")
    AGAINST_PFXS = ("against ", "against:", "against,", "against-",
                    "against–", "against—", "no,", "no-", "no ",
                    "do not ", "don't ", "decline", "reject ", "not in favor",
                    "against[")

    for_idxs, against_idxs = [], []
    for idx, ch in enumerate(choices):
        if ch in FOR_EXACT:
            for_idxs.append(idx)
        elif ch in AGAINST_EXACT:
            against_idxs.append(idx)
        elif any(ch.startswith(p) for p in FOR_PFXS):
            for_idxs.append(idx)
        elif any(ch.startswith(p) for p in AGAINST_PFXS):
            against_idxs.append(idx)

    for_pct = None
    passed  = None
    if for_idxs and against_idxs:
        fv = sum(scores[i] for i in for_idxs if i < len(scores))
        av = sum(scores[i] for i in against_idxs if i < len(scores))
        contested = fv + av
        if contested > 0:
            for_pct = fv / contested * 100
        passed = fv > av

    records.append({
        "id":           p["id"],
        "title":        p["title"],
        "category":     category,
        "created":      created_dt,
        "passed":       passed,
        "for_pct":      for_pct,
        "scores_total": p.get("scores_total", 0),
        "vote_type":    p.get("type", ""),
    })

df = pd.DataFrame(records)


# ── Step 4: Full classification breakdown ─────────────────────────────────────

print("\n" + "="*70)
print("CLASSIFICATION BREAKDOWN")
print("="*70)

counts = df["category"].value_counts()
print(f"\nCategory counts (all {len(df)} proposals):")
for cat, n in counts.items():
    print(f"  {cat:<35} {n:>4}")

for cat in df["category"].unique():
    sub = df[df["category"] == cat].sort_values("created")
    print(f"\n── {cat} (n={len(sub)}) ─────────────────────────────")
    for _, row in sub.iterrows():
        date_str = row["created"].strftime("%Y-%m")
        print(f"  [{date_str}] {row['title'][:90]}")


df["cat_analysis"] = df["category"].replace("Rules Change (Arbitrage)", "Rules Change")
ANALYSIS_CATS = ["Treasury Spend", "Rules Change", "Institution Building"]

# ── Step 4b: Vote data diagnostics ───────────────────────────────────────────

print("\n" + "="*70)
print("VOTE DATA DIAGNOSTICS")
print("="*70)

# How many proposals have no for_pct (can't compute pass/fail)?
no_forpct = df[df["for_pct"].isna()]
print(f"\nProposals with no For/Against choices (for_pct = None): {len(no_forpct)}")
print("  (these are elections, approval votes, or non-standard formats)")
for _, row in no_forpct.sort_values("created").iterrows():
    print(f"  [{row['created'].strftime('%Y-%m')}] [{row['vote_type']:<14}] {row['title'][:80]}")

# Proposals with zero total votes
zero_votes = df[df["scores_total"] == 0]
print(f"\nProposals with scores_total = 0: {len(zero_votes)}")
for _, row in zero_votes.iterrows():
    print(f"  [{row['created'].strftime('%Y-%m')}] {row['title'][:80]}")

# Distribution of scores_total for proposals with For/Against
has_vote = df[df["for_pct"].notna()].copy()
print(f"\nscores_total distribution for proposals with For/Against (n={len(has_vote)}):")
print(f"  min:    {has_vote['scores_total'].min():>15,.0f} ARB")
print(f"  p10:    {has_vote['scores_total'].quantile(0.10):>15,.0f} ARB")
print(f"  median: {has_vote['scores_total'].quantile(0.50):>15,.0f} ARB")
print(f"  p90:    {has_vote['scores_total'].quantile(0.90):>15,.0f} ARB")
print(f"  max:    {has_vote['scores_total'].max():>15,.0f} ARB")

# Very low participation proposals (scores_total < 1M ARB)
low_part = has_vote[has_vote["scores_total"] < 1_000_000].sort_values("scores_total")
print(f"\nProposals with scores_total < 1M ARB (n={len(low_part)}) — may be junk votes:")
for _, row in low_part.iterrows():
    print(f"  [{row['created'].strftime('%Y-%m')}] {row['scores_total']:>12,.0f} ARB  for_pct={row['for_pct']:.1f}%  {row['title'][:65]}")

# Pass rate by category
print(f"\nPass rate by category (For > Against, among proposals with For/Against choices):")
for cat in ANALYSIS_CATS:
    sub = df[df["cat_analysis"] == cat] if "cat_analysis" in df.columns else df[df["category"] == cat]
    sub_voted = sub[sub["for_pct"].notna()]
    if len(sub_voted) == 0:
        continue
    passed_n = sub_voted["passed"].sum()
    print(f"  {cat:<25} {passed_n:>3}/{len(sub_voted):>3} passed ({100*passed_n/len(sub_voted):.1f}%)")

# Weighted avg For% (by scores_total) vs unweighted, for sanity check
print(f"\nWeighted vs unweighted avg For% (full analysis universe with For/Against):")
for cat in ["Treasury Spend", "Rules Change", "Institution Building"]:
    sub = df[df["category"].isin([cat, "Rules Change (Arbitrage)" if cat == "Rules Change" else cat])]
    sub = sub[sub["for_pct"].notna() & (sub["scores_total"] > 0)]
    if len(sub) == 0:
        continue
    unweighted = sub["for_pct"].mean()
    weighted   = np.average(sub["for_pct"], weights=sub["scores_total"])
    print(f"  {cat:<25}  unweighted={unweighted:.1f}%   weighted={weighted:.1f}%")


# ── Step 5: Filter for analysis ───────────────────────────────────────────────
df_analysis = df[
    df["cat_analysis"].isin(ANALYSIS_CATS) &
    (df["created"] >= "2023-01-01") &
    (df["created"] <= "2026-03-31")
].copy()

print(f"\n\nAnalysis universe (excl. temp checks, 2023–2026): {len(df_analysis)} proposals")
print(df_analysis["cat_analysis"].value_counts().to_string())


# ── Step 6: Aggregate by half-year × category ─────────────────────────────────

def to_half(dt):
    return f"{dt.year}H{'1' if dt.month <= 6 else '2'}"

df_analysis["half"] = df_analysis["created"].apply(to_half)

summary = (
    df_analysis.groupby(["half", "cat_analysis"])
    .agg(
        count=("id", "count"),
        avg_for_pct=("for_pct", "mean"),
    )
    .reset_index()
)

halves   = sorted(df_analysis["half"].unique())
x        = np.arange(len(halves))

def series(cat):
    sub = summary[summary["cat_analysis"] == cat].set_index("half")
    counts  = [sub.loc[h, "count"]       if h in sub.index else 0       for h in halves]
    margins = [sub.loc[h, "avg_for_pct"] if h in sub.index else np.nan  for h in halves]
    return counts, margins

spend_counts,  spend_margins  = series("Treasury Spend")
rules_counts,  rules_margins  = series("Rules Change")
inst_counts,   inst_margins   = series("Institution Building")

print(f"\nHalf-year summary:")
print(summary.to_string(index=False))


# ── Step 7: Plot ──────────────────────────────────────────────────────────────
# Left panel  – stacked bar of submission counts per economic category per half
# Right panel – avg For% lines (one per category) with 50% threshold dashed

COL_SPEND = COLORS["blue"]
COL_RULES = COLORS["red"]
COL_INST  = COLORS["green"]
BAR_ALPHA = 0.85

fig, (ax_count, ax_rate) = plt.subplots(1, 2, figsize=(7, 3.8))

# ── Left: stacked bars ────────────────────────────────────────────────────────
bar_w = 0.55
ax_count.bar(x, spend_counts, bar_w, color=COL_SPEND, alpha=BAR_ALPHA,
             label="Treasury Spend")
ax_count.bar(x, rules_counts, bar_w, bottom=spend_counts, color=COL_RULES,
             alpha=BAR_ALPHA, label="Rules Change")
inst_bottom = [s + r for s, r in zip(spend_counts, rules_counts)]
ax_count.bar(x, inst_counts, bar_w, bottom=inst_bottom, color=COL_INST,
             alpha=BAR_ALPHA, label="Institution Building")

# Total labels on top of each stack
totals = [s + r + i for s, r, i in zip(spend_counts, rules_counts, inst_counts)]
for xi, tot in zip(x, totals):
    if tot > 0:
        ax_count.text(xi, tot + 0.2, str(int(tot)),
                      ha="center", va="bottom", fontsize=8.5, fontweight="bold")

ax_count.set_ylabel("Proposals submitted")
ax_count.set_ylim(0, max(totals) * 1.45)
ax_count.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
ax_count.set_xticks(x)
ax_count.set_xticklabels(halves, rotation=45, ha="right", fontsize=8)
ax_count.set_xlim(-0.6, len(halves) - 0.4)
ax_count.legend(fontsize=9, framealpha=0.9, loc="upper left")
ax_count.set_title("(a) Proposals submitted per half-year\n(by economic purpose)",
                   fontsize=11, style="italic")
ax_count.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.4)

# ── Right: For% margin lines ──────────────────────────────────────────────────
ax_rate.plot(x, spend_margins, color=COL_SPEND, linewidth=1.8,
             marker="o", markersize=6, label="Treasury Spend")
ax_rate.plot(x, rules_margins, color=COL_RULES, linewidth=1.8,
             marker="D", markersize=6, label="Rules Change")
ax_rate.plot(x, inst_margins,  color=COL_INST,  linewidth=1.8,
             marker="s", markersize=6, label="Institution Building")

ax_rate.axhline(50, color="gray", linewidth=1.0, linestyle="--", alpha=0.7,
                label="50% threshold (For > Against)")

ax_rate.set_ylabel("Avg. For% of contested votes")
ax_rate.set_ylim(0, 110)
ax_rate.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
ax_rate.set_xticks(x)
ax_rate.set_xticklabels(halves, rotation=45, ha="right", fontsize=8)
ax_rate.set_xlim(-0.6, len(halves) - 0.4)
ax_rate.legend(fontsize=9, framealpha=0.9)
ax_rate.set_title("(b) Avg. vote margin per half-year\n(For% of For+Against votes)",
                  fontsize=11, style="italic")
ax_rate.grid(axis="y", linestyle="--", linewidth=0.5, alpha=0.4)

for ax in [ax_count, ax_rate]:
    despine(ax)
fig.tight_layout()
aer_savefig(fig, OUT_PATH)
