#!/usr/bin/env python3
"""
Figure 9: Institutional Design & Election Legitimacy
Journal of Finance paper on Arbitrum governance.

Two panels:

Panel 9a — Institutional Elections: Nominee Competition vs. Voter Turnout
  Scatter of all multi-choice institutional elections on Snapshot
  (committee elections, council elections, program elections).
  X = number of nominees/choices; Y = total VP cast (millions ARB).
  Note: Security Council member elections are conducted on-chain via the
  SecurityCouncilMemberElectionGovernor contract and are not present in the
  Snapshot dataset. This panel uses the full set of Snapshot institutional
  elections as a representative sample of DAO election dynamics.

Panel 9b — Constitutional Amendment Lifecycle
  For each of the 14 [Constitutional] proposals on Snapshot, shows:
    - Forum discussion period (first forum post → Snapshot vote open)
    - Voting period (vote open → vote close)
    - Outcome (For-vote share; all passed)
    - Classification by type (protocol upgrade, governance mechanics,
      security/timelock, institutional rules)
  Highlights proposals that change "barrier to entry" for participation.

Key rule change annotations:
  - Jan 2024: Constitution + SC election process standardized
  - May 2025: Constitutional quorum threshold 5% → 4% (barrier to vote ↓)
  - Sep 2025: SC nomination threshold 0.2% → 0.1% ARB (barrier to run ↓)
  - Oct/Feb 2025-26: DVP Quorum (dynamic quorum reform)

Data sources:
  Snapshot GraphQL API (all proposal metadata and vote breakdowns)
  forum.arbitrum.foundation (Discourse JSON API for discussion start dates)
"""

import os
import re, time, requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys as _sys
_sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, C_TOTAL, C_SHOCK, savefig as aer_savefig
apply_aer_style()
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
import matplotlib.lines as mlines
import matplotlib.patches as mpatches

HERE     = os.path.dirname(os.path.abspath(__file__))
ROOT     = os.path.dirname(HERE)   # project root
OUT_DIR  = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH     = os.path.join(OUT_DIR, "fig09_amendments.png")
SNAPSHOT_URL = "https://hub.snapshot.org/graphql"
FORUM_BASE   = "https://forum.arbitrum.foundation"
HEADERS      = {"User-Agent": "Mozilla/5.0 (research bot)"}

# ── Constitutional proposal metadata ──────────────────────────────────────────
# Barrier-to-entry classification:
#   "barrier_down"  — reduces requirements to participate (run, vote, propose)
#   "barrier_up"    — increases requirements
#   None            — does not primarily affect barrier to entry

CONST_META = {
    "Changes to the Constitution and the Security Council": {
        "short":    "SC Election\nProcess v1",
        "category": "Institutional Rules",
        "barrier":  None,
    },
    "Extend Delay on L2Time Lock": {
        "short":    "L2 Timelock\nDelay",
        "category": "Security / Timelock",
        "barrier":  None,
    },
    "ArbOS Version 40 Callisto": {
        "short":    "ArbOS 40\nCallisto",
        "category": "Protocol Upgrade",
        "barrier":  None,
    },
    "register the Sky Custom Gateway": {
        "short":    "Sky Gateway\nRegistration",
        "category": "Protocol Upgrade",
        "barrier":  None,
    },
    "Constitutional Quorum Threshold Reduction": {
        "short":    "Quorum\nThreshold −1pp",
        "category": "Governance Mechanics",
        "barrier":  "barrier_down",
    },
    "Remove Cost Cap on Arbitrum Nova": {
        "short":    "Nova\nCost Cap",
        "category": "Protocol Upgrade",
        "barrier":  None,
    },
    "Update the Upgrade Executors": {
        "short":    "Upgrade\nExecutors",
        "category": "Security / Timelock",
        "barrier":  None,
    },
    "Register $BORING": {
        "short":    "BORING\nGateway",
        "category": "Protocol Upgrade",
        "barrier":  None,
    },
    "Disable Legacy Tether Bridge": {
        "short":    "Tether Bridge\nDisable",
        "category": "Protocol Upgrade",
        "barrier":  None,
    },
    "ArbOS Version 50 Dia": {
        "short":    "ArbOS 50\nDia",
        "category": "Protocol Upgrade",
        "barrier":  None,
    },
    "Security Council Election Process Improvements": {
        "short":    "SC Election\nProcess v2\n(threshold ↓)",
        "category": "Institutional Rules",
        "barrier":  "barrier_down",
    },
    "DVP Quorum": {
        "short":    "DVP Quorum\nTemp Check",
        "category": "Governance Mechanics",
        "barrier":  None,
    },
    "DVP Quorum for ArbitrumDAO: Implementation": {
        "short":    "DVP Quorum\nImplementation",
        "category": "Governance Mechanics",
        "barrier":  None,
    },
    "ArbOS 60 Elara": {
        "short":    "ArbOS 60\nElara",
        "category": "Protocol Upgrade",
        "barrier":  None,
    },
}

CAT_COLORS = {
    "Protocol Upgrade":    "#2980B9",
    "Governance Mechanics": "#E67E22",
    "Security / Timelock": "#27AE60",
    "Institutional Rules": "#C0392B",
}


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1  Fetch all Snapshot proposals
# ══════════════════════════════════════════════════════════════════════════════

QUERY = """
{
  proposals(
    first: 1000
    where: { space_in: ["arbitrumfoundation.eth"], state: "closed" }
    orderBy: "created"
    orderDirection: asc
  ) {
    id title created end type choices scores scores_total votes
  }
}
"""

print("Step 1: Fetching Snapshot proposals...")
r = requests.post(SNAPSHOT_URL, json={"query": QUERY}, timeout=30)
props = r.json()["data"]["proposals"]
print(f"  {len(props)} proposals")

CONST_RE = re.compile(r'\[constitutional\]', re.I)
TEMP_RE  = re.compile(r'\btemp(erature)?\s*check\b', re.I)

# Split into constitutional and election subsets
const_list = [p for p in props if CONST_RE.search(p["title"])]
election_list = [
    p for p in props
    if p["type"] in ("approval", "weighted", "ranked-choice")
    and len(p.get("choices") or []) >= 4
    and not TEMP_RE.search(p["title"])
]
print(f"  Constitutional proposals: {len(const_list)}")
print(f"  Institutional elections:  {len(election_list)}")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2  For each constitutional proposal, find forum discussion start date
# ══════════════════════════════════════════════════════════════════════════════

print("\nStep 2: Finding forum discussion start dates for constitutional proposals...")

def forum_discussion_start(title):
    """Search forum for this proposal title, return earliest topic date."""
    # Strip [Constitutional] prefix and clean
    q = re.sub(r'\[.*?\]', '', title).strip()
    q = q[:60]   # Discourse search handles ~60 chars well
    try:
        r = requests.get(f"{FORUM_BASE}/search.json",
                         params={"q": q, "order": "latest_topic"},
                         headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        d = r.json()
        topics = d.get("topics", [])
        if not topics:
            return None
        # Pick earliest topic that mentions this proposal
        dates = []
        for t in topics[:5]:
            ts = pd.to_datetime(t.get("created_at", ""), utc=True, errors="coerce")
            if pd.notna(ts):
                dates.append(ts.tz_localize(None))
        return min(dates) if dates else None
    except Exception:
        return None

const_records = []
for p in const_list:
    snap_vote_start = pd.to_datetime(p["created"], unit="s")
    snap_vote_end   = pd.to_datetime(p["end"],     unit="s")
    ch    = p.get("choices") or []
    sc    = p.get("scores")  or []
    total = p["scores_total"]

    # For share: find "For" choice
    for_vp = 0.0
    for c, s in zip(ch, sc):
        if re.search(r'\bfor\b', c, re.I) or re.search(r'^for\s', c, re.I):
            for_vp = s
    if not for_vp and sc:
        for_vp = sc[0]   # first choice = For in basic proposals
    for_pct = for_vp / total * 100 if total > 0 else 0

    # Find matching metadata
    meta = None
    for key, m in CONST_META.items():
        if key.lower() in p["title"].lower():
            meta = m
            break
    if meta is None:
        meta = {"short": p["title"][:20], "category": "Protocol Upgrade", "barrier": None}

    # Forum search
    forum_start = forum_discussion_start(p["title"])
    time.sleep(0.4)

    days_discussion = (
        (snap_vote_start - forum_start).days
        if forum_start is not None and forum_start < snap_vote_start
        else None
    )

    const_records.append({
        "id":             p["id"],
        "title":          p["title"],
        "short":          meta["short"],
        "category":       meta["category"],
        "barrier":        meta["barrier"],
        "snap_start":     snap_vote_start,
        "snap_end":       snap_vote_end,
        "forum_start":    forum_start,
        "days_discussion": days_discussion,
        "for_pct":        for_pct,
        "scores_total_M": total / 1e6,
        "votes":          p["votes"],
    })
    print(f"  {snap_vote_start.date()}  forum={forum_start.date() if forum_start else '?':10}  "
          f"({days_discussion or '?':>4}d discussion)  {meta['short'].replace(chr(10),' ')}")

const_df = pd.DataFrame(const_records).sort_values("snap_start").reset_index(drop=True)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3  Classify institutional elections
# ══════════════════════════════════════════════════════════════════════════════

print("\nStep 3: Classifying institutional elections...")

SC_RE     = re.compile(r'security council', re.I)
ARDC_RE   = re.compile(r'\bardc\b|research.{0,15}development.{0,15}collective', re.I)
OAT_RE    = re.compile(r'\boat\b|oversight.{0,20}transparency', re.I)
COUNCIL_RE= re.compile(r'council|committee|pilot\s+program', re.I)
DAO_RE    = re.compile(r'\bdao\b.{0,30}(election|season)|domain.{0,20}election', re.I)
MSS_RE    = re.compile(r'\bmss\b|multisig\s+support', re.I)

def election_type(title):
    if SC_RE.search(title):    return "Security Council"
    if ARDC_RE.search(title):  return "Research (ARDC)"
    if OAT_RE.search(title):   return "Oversight (OAT)"
    if MSS_RE.search(title):   return "Multisig (MSS)"
    if DAO_RE.search(title):   return "Domain Allocator"
    if COUNCIL_RE.search(title): return "Program Council"
    return "Other Election"

ETYPE_COLORS = {
    "Security Council":  "#C0392B",
    "Research (ARDC)":   "#2980B9",
    "Oversight (OAT)":   "#8E44AD",
    "Program Council":   "#E67E22",
    "Domain Allocator":  "#27AE60",
    "Multisig (MSS)":    "#16A085",
    "Other Election":    "#95A5A6",
}

elec_records = []
for p in election_list:
    created = pd.to_datetime(p["created"], unit="s")
    n_choices = len(p.get("choices") or [])
    elec_records.append({
        "title":       p["title"],
        "created":     created,
        "type":        election_type(p["title"]),
        "n_choices":   n_choices,
        "scores_total_M": p["scores_total"] / 1e6,
        "votes":       p["votes"],
    })

elec_df = pd.DataFrame(elec_records).sort_values("created").reset_index(drop=True)
print(elec_df.groupby("type")["title"].count().to_string())


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4  Plot — panel 9b only (full figure)
# ══════════════════════════════════════════════════════════════════════════════

print("\nStep 4: Building figure...")

# Sort by forum discussion start date (proposed date); fall back to snap_start
const_df["sort_date"] = const_df["forum_start"].combine_first(const_df["snap_start"])
df = const_df.sort_values("sort_date").reset_index(drop=True)
n  = len(df)

# Tag passed vs failed
df["passed"] = df["for_pct"] >= 50

passed_n = df["passed"].sum()
failed_n = (~df["passed"]).sum()

fig, ax2 = plt.subplots(figsize=(15, 0.55 * n + 3))

# Y positions: one row per proposal
y_pos = np.arange(n)

# ── Discussion bars (forum start → snap vote open) ────────────────────────────
for i, row in df.iterrows():
    color = CAT_COLORS.get(row["category"], "#95A5A6")
    bar_start = row["forum_start"] if row["forum_start"] is not None else row["snap_start"]
    # Discussion phase
    ax2.barh(i, width=(row["snap_start"] - bar_start).total_seconds() / 86400,
             left=mdates.date2num(bar_start),
             height=0.45, color=color, alpha=0.30, zorder=3,
             edgecolor=color, linewidth=0.5)
    # Voting phase
    ax2.barh(i, width=(row["snap_end"] - row["snap_start"]).total_seconds() / 86400,
             left=mdates.date2num(row["snap_start"]),
             height=0.45, color=color, alpha=0.85, zorder=4,
             edgecolor="white", linewidth=0.4)

    # Outcome marker at vote-end
    passed = row["passed"]
    marker_color = color if passed else "#E74C3C"
    ax2.scatter(mdates.date2num(row["snap_end"]), i,
                s=70, color=marker_color, zorder=6,
                marker="o" if passed else "X",
                edgecolors="white", linewidths=0.7)

    # Label: For% if passed, FAILED if not
    if passed:
        label_txt = f"  {row['for_pct']:.0f}% For"
        label_col = color
    else:
        label_txt = f"  FAILED  ({row['for_pct']:.0f}% For)"
        label_col = "#E74C3C"
    ax2.text(mdates.date2num(row["snap_end"]) + 5, i,
             label_txt, va="center", ha="left", fontsize=7.5, color=label_col,
             fontweight="bold" if not passed else "normal")

    # Barrier annotation
    if row["barrier"] == "barrier_down":
        ax2.text(mdates.date2num(row["snap_start"]) - 2, i + 0.35,
                 "barrier ↓", fontsize=6.5, color="#C0392B",
                 ha="right", va="bottom",
                 bbox=dict(fc="white", ec="#C0392B", pad=1.5, alpha=0.85))

# Y axis labels
ax2.set_yticks(y_pos)
ax2.set_yticklabels(
    [row["short"].replace("\n", " ") for _, row in df.iterrows()],
    fontsize=8
)
ax2.set_ylim(-0.7, n - 0.3)
ax2.invert_yaxis()

# X axis: dates
ax2.xaxis_date()
ax2.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
ax2.set_xlim(
    mdates.date2num(pd.Timestamp("2023-10-01")),
    mdates.date2num(pd.Timestamp("2026-06-01"))
)
ax2.grid(axis="x", linestyle="--", linewidth=0.5, alpha=0.35)

# Legend: category colors
cat_patches = [
    mpatches.Patch(color=c, alpha=0.85, label=cat)
    for cat, c in CAT_COLORS.items()
]
discuss_patch = mpatches.Patch(color="#AAA", alpha=0.30, label="Forum discussion phase (light)")
vote_patch    = mpatches.Patch(color="#AAA", alpha=0.85, label="Snapshot voting phase (solid)")
barrier_patch = mpatches.Patch(color="white", ec="#C0392B", label='"barrier ↓" = reduces participation barrier')
passed_marker = mlines.Line2D([0],[0], marker="o", color="w", markerfacecolor="#555",
                               markersize=7, label="Passed (●)")
failed_marker = mlines.Line2D([0],[0], marker="X", color="w", markerfacecolor="#E74C3C",
                               markersize=8, label="Failed (✕)")
ax2.legend(handles=cat_patches + [discuss_patch, vote_patch, barrier_patch,
                                   passed_marker, failed_marker],
           loc="upper left", fontsize=7.5, framealpha=0.92, ncol=2)

ax2.set_xlabel("Date", fontsize=10)

fig.suptitle(
    "Figure A5: Constitutional Amendment Lifecycle — Forum Discussion → DAO Vote → Outcome\n"
    f"Arbitrum DAO, 2023–2026  ({passed_n} passed, {failed_n} failed; "
    r"2 reduced participation barriers ↓)",
    fontsize=12, fontweight="bold", y=1.01
)

fig.savefig(OUT_PATH, dpi=180, bbox_inches="tight")
print(f"\nSaved to {OUT_PATH}")

# ── Summary table ─────────────────────────────────────────────────────────────
print("\nConstitutional proposal summary:")
print(const_df[["snap_start", "short", "category", "barrier",
                 "days_discussion", "for_pct", "scores_total_M"]
               ].to_string(index=False))
