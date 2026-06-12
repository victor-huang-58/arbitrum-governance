#!/usr/bin/env python3
"""
Robustness: Cross-DAO Placebo Test (Uniswap)
Journal of Finance paper on Arbitrum governance.

Identifies the vesting cliff alternative: Arbitrum's March 2024 token unlock
brought 1.1B whale tokens into circulation. If this caused margins to widen
(concentrated power → less contested votes), the forum signal break would be
Arbitrum-specific, not AI-driven.

Placebo: Run the same posts-margin correlation analysis on Uniswap DAO, which:
  (a) had no token vesting cliff in March 2024
  (b) uses the same Snapshot voting infrastructure
  (c) has a public governance forum at gov.uniswap.org (Discourse)

If the forum signal also collapses at Claude 3 in Uniswap, the vesting cliff
cannot be the cause — the shock is ecosystem-wide (AI capability threshold),
not Arbitrum-specific.

Output:
  output/figures/rob01_uniswap_placebo.png
  data/uniswap_snap_cache.json
  data/uniswap_forum_cache.json
"""

import os, json, re, time
import requests
import numpy as np
import pandas as pd
from scipy import stats as spstats
from scipy.stats import f as f_dist
from difflib import SequenceMatcher
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, C_TOTAL, C_SHOCK, savefig as aer_savefig
apply_aer_style()

HERE         = os.path.dirname(os.path.abspath(__file__))
ROOT         = os.path.dirname(HERE)
SNAP_CACHE   = os.path.join(ROOT, "data", "uniswap_snap_cache.json")
FORUM_CACHE  = os.path.join(ROOT, "data", "uniswap_forum_cache.json")
OTHER_PROPS  = os.path.join(ROOT, "data", "other_dao_proposals.json")
OUT_FIG      = os.path.join(ROOT, "output", "figures", "rob01_uniswap_placebo.png")
os.makedirs(os.path.join(ROOT, "output", "figures"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)

SNAPSHOT_URL    = "https://hub.snapshot.org/graphql"
FORUM_BASE      = "https://gov.uniswap.org"
MATCH_THRESHOLD = 0.45
AI_THRESHOLD    = 0.70
CLAUDE3_DATE    = pd.Timestamp("2024-03-04")
ROLLING_WINDOW  = 12   # smaller than Arbitrum (25) since n is smaller


# ── helpers ───────────────────────────────────────────────────────────────────

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f)

def gql(query, retries=4):
    for attempt in range(retries):
        try:
            r = requests.post(SNAPSHOT_URL, json={"query": query}, timeout=30)
            return r.json()
        except Exception:
            time.sleep(3 * (attempt + 1))
    return {}

def title_sim(a, b):
    a = re.sub(r"[\[\(][^\]\)]*[\]\)]", "", a).strip().lower()
    b = re.sub(r"[\[\(][^\]\)]*[\]\)]", "", b).strip().lower()
    return SequenceMatcher(None, a, b).ratio()

def compute_margin(scores, choices):
    if not scores or not choices:
        return np.nan
    cs = dict(zip([c.lower() for c in choices], scores))
    f = cs.get("for", cs.get("yes", 0))
    a = cs.get("against", cs.get("no", 0))
    if f + a == 0:
        return np.nan
    return abs(2 * f / (f + a) - 1)

def chow_test(df, x_col, y_col, break_col="post_shock"):
    pre  = df[~df[break_col]]
    post = df[df[break_col]]
    def ols_ssr(d):
        if len(d) < 3:
            return np.nan, len(d)
        s, i, *_ = spstats.linregress(d[x_col].values, d[y_col].values)
        resid = d[y_col].values - (i + s * d[x_col].values)
        return float(np.sum(resid**2)), len(d)
    ssr_f, n   = ols_ssr(df)
    ssr_pre, _ = ols_ssr(pre)
    ssr_po, _  = ols_ssr(post)
    if any(v is np.nan for v in [ssr_f, ssr_pre, ssr_po]):
        return np.nan, np.nan, len(pre), len(post)
    k = 2
    F = ((ssr_f - ssr_pre - ssr_po) / k) / ((ssr_pre + ssr_po) / (n - 2*k))
    p = 1 - f_dist.cdf(F, k, n - 2*k)
    return float(F), float(p), len(pre), len(post)


# ── Step 1: Load Uniswap Snapshot proposals ───────────────────────────────────

print("Step 1: Loading Uniswap Snapshot proposals...")
snap_cache = load_json(SNAP_CACHE)

# Load seed proposal IDs from other_dao_proposals.json
with open(OTHER_PROPS) as f:
    other_props = json.load(f)
uni_seed_ids = [p["id"] for p in other_props if p["space"]["id"] == "uniswapgovernance.eth"]
print(f"  {len(uni_seed_ids)} seed proposal IDs from other_dao_proposals.json")

# Fetch full details for any not in cache
to_fetch = [pid for pid in uni_seed_ids if pid not in snap_cache]
print(f"  {len(to_fetch)} proposals need fetching from Snapshot API...")

for i in range(0, len(to_fetch), 10):
    batch = to_fetch[i:i+10]
    ids_str = '["' + '","'.join(batch) + '"]'
    q = f'{{ proposals(where: {{id_in: {ids_str}}}) {{ id title created scores choices scores_total votes }} }}'
    data = gql(q).get("data", {}).get("proposals", [])
    for p in data:
        snap_cache[p["id"]] = p
    time.sleep(0.5)

# Also fetch any additional Uniswap proposals from 2023-2026 not in the seed list
print("  Fetching additional Uniswap proposals from Snapshot...")
for skip in range(0, 500, 100):
    q = f"""
    {{
      proposals(
        first: 100 skip: {skip}
        where: {{ space: "uniswapgovernance.eth", state: "closed" }}
        orderBy: "created" orderDirection: asc
      ) {{ id title created scores choices scores_total votes }}
    }}
    """
    data = gql(q).get("data", {}).get("proposals", [])
    if not data:
        break
    for p in data:
        snap_cache[p["id"]] = p
    if len(data) < 100:
        break
    time.sleep(0.5)

save_json(SNAP_CACHE, snap_cache)
print(f"  Total cached: {len(snap_cache)} Uniswap proposals")

snap_rows = []
for pid, p in snap_cache.items():
    margin = compute_margin(p.get("scores"), p.get("choices"))
    if np.isnan(margin):
        continue
    ts = p.get("created", 0)
    date = pd.Timestamp(ts, unit="s")
    if not (pd.Timestamp("2023-01-01") <= date <= pd.Timestamp("2026-03-31")):
        continue
    if (p.get("votes") or 0) < 5:
        continue
    snap_rows.append({
        "proposal_id": pid,
        "title":       p.get("title", ""),
        "date":        date,
        "margin":      margin,
    })

snap_df = pd.DataFrame(snap_rows).sort_values("date").reset_index(drop=True)
print(f"  {len(snap_df)} Uniswap proposals with computable margin (Jan 2023 – Mar 2026)")


# ── Step 2: Scrape Uniswap governance forum ──────────────────────────────────

print("\nStep 2: Scraping Uniswap governance forum (gov.uniswap.org)...")
forum_cache = load_json(FORUM_CACHE)

# Scrape topic listings page by page
page = 0
new_topics = 0
while True:
    url = f"{FORUM_BASE}/latest.json?page={page}&per_page=30"
    try:
        resp = requests.get(url, timeout=20,
                            headers={"User-Agent": "research-bot/1.0"})
        if resp.status_code != 200:
            break
        data = resp.json()
    except Exception:
        break

    topics = data.get("topic_list", {}).get("topics", [])
    if not topics:
        break

    for t in topics:
        tid = str(t.get("id"))
        if tid not in forum_cache:
            created = t.get("created_at", "")
            if created:
                try:
                    ts = pd.Timestamp(created)
                    if ts < pd.Timestamp("2022-01-01"):
                        continue
                except Exception:
                    pass
            forum_cache[tid] = {
                "id":          tid,
                "title":       t.get("title", ""),
                "posts_count": t.get("posts_count", 0),
                "created_at":  t.get("created_at", ""),
            }
            new_topics += 1

    # Stop if we've gone past Jan 2023 start
    oldest = min((t.get("created_at", "9999") for t in topics), default="9999")
    if oldest < "2022-06-01":
        break

    page += 1
    time.sleep(0.8)
    if page > 60:   # safety cap
        break

save_json(FORUM_CACHE, forum_cache)
print(f"  {len(forum_cache)} topics in forum cache ({new_topics} newly scraped)")


# ── Step 3: Match forum topics to Snapshot proposals ─────────────────────────

print("\nStep 3: Matching forum topics to Snapshot proposals...")
forum_list = [v for v in forum_cache.values()
              if v.get("created_at", "") >= "2022-01-01"]
forum_titles = [t["title"] for t in forum_list]

matched = []
for row in snap_df.itertuples():
    sims = [title_sim(row.title, ft) for ft in forum_titles]
    best_idx = int(np.argmax(sims))
    best_sim = sims[best_idx]
    if best_sim < MATCH_THRESHOLD:
        continue
    best = forum_list[best_idx]
    matched.append({
        "proposal_id":  row.proposal_id,
        "date":         row.date,
        "margin":       row.margin,
        "posts_count":  best["posts_count"],
        "match_title":  best["title"],
        "match_sim":    best_sim,
        "snap_title":   row.title,
    })

match_df = pd.DataFrame(matched).dropna(subset=["posts_count", "margin"])
match_df = match_df.sort_values("date").reset_index(drop=True)
match_df["post_shock"] = match_df["date"] >= CLAUDE3_DATE

print(f"  {len(match_df)} matched Uniswap proposals")
print(f"  Pre-Claude3: {(~match_df['post_shock']).sum()}  Post: {match_df['post_shock'].sum()}")
if len(match_df) > 0:
    print(f"  Median match similarity: {match_df['match_sim'].median():.3f}")
    print(f"  Sample matches:")
    for _, r in match_df.head(3).iterrows():
        print(f"    Snapshot: '{r['snap_title'][:60]}'")
        print(f"    Forum:    '{r['match_title'][:60]}'  sim={r['match_sim']:.2f}")


# ── Step 4: Chow test ─────────────────────────────────────────────────────────

print("\nStep 4: Computing Chow test...")
pre  = match_df[~match_df["post_shock"]]
post = match_df[match_df["post_shock"]]

r_pre  = spstats.pearsonr(pre["posts_count"],  pre["margin"])[0]  if len(pre)  > 3 else np.nan
r_post = spstats.pearsonr(post["posts_count"], post["margin"])[0] if len(post) > 3 else np.nan
F, p_val, n_pre, n_post = chow_test(match_df, "posts_count", "margin")

print(f"\n  Uniswap (no vesting cliff):")
print(f"    Pre-Claude3:  n={n_pre:3d}  r={r_pre:+.3f}")
print(f"    Post-Claude3: n={n_post:3d}  r={r_post:+.3f}")
print(f"    Chow F={F:.2f}  p={p_val:.4f}")


# ── Step 5: Rolling correlation ───────────────────────────────────────────────

print("\nStep 5: Computing rolling correlation...")
roll_corr = []
roll_dates = []
for i in range(ROLLING_WINDOW - 1, len(match_df)):
    window = match_df.iloc[i - ROLLING_WINDOW + 1 : i + 1]
    r, _ = spstats.pearsonr(window["posts_count"], window["margin"])
    roll_corr.append(r)
    roll_dates.append(window["date"].iloc[-1])


# ── Step 6: Figure ────────────────────────────────────────────────────────────

print("\nStep 6: Building figure...")
fig, axes = plt.subplots(1, 2, figsize=(7, 3.5))

# Panel A: scatter pre vs post
ax = axes[0]
ax.scatter(pre["posts_count"],  pre["margin"],  color=C_HUMAN, s=20, alpha=0.75,
           label=f"Pre–Claude 3 ($r={r_pre:+.2f}$)", zorder=3)
ax.scatter(post["posts_count"], post["margin"], color=C_AI,   s=20, alpha=0.75,
           label=f"Post–Claude 3 ($r={r_post:+.2f}$)", zorder=3)
for subset, color in [(pre, C_HUMAN), (post, C_AI)]:
    if len(subset) > 2:
        x = subset["posts_count"].values
        y = subset["margin"].values
        s, i, *_ = spstats.linregress(x, y)
        xr = np.linspace(x.min(), x.max(), 100)
        ax.plot(xr, i + s*xr, color=color, linewidth=1.4)
ax.set_xlabel("Forum posts per thread")
ax.set_ylabel("Margin of victory")
ax.set_title("Uniswap DAO\n(no vesting cliff)", fontsize=9)
ax.legend(fontsize=7.5, loc="upper right")
ax.text(0.97, 0.05,
        f"Chow $F={F:.1f}$, $p={p_val:.3f}$",
        transform=ax.transAxes, fontsize=7.5, ha="right", va="bottom",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white", alpha=0.8))
despine(ax)

# Panel B: rolling correlation
ax = axes[1]
if roll_corr:
    ax.plot(roll_dates, roll_corr, color=C_TOTAL, linewidth=1.8)
    ax.axhline(0, color="black", linewidth=0.7, linestyle="--", alpha=0.5)
    ax.axvline(CLAUDE3_DATE, color=C_SHOCK, linewidth=1.5, linestyle="--",
               label="Claude 3 (Mar 2024)")
    ax.set_ylabel(f"Rolling {ROLLING_WINDOW}-proposal Pearson $r$")
    ax.set_xlabel("")
    ax.set_title("Rolling forum signal\n(Uniswap)", fontsize=9)
    ax.set_ylim(-1.05, 1.05)
    ax.legend(fontsize=7.5)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:+.1f}"))
despine(ax)

fig.tight_layout()
aer_savefig(fig, OUT_FIG)
print(f"  Figure saved to {OUT_FIG}")

print("\n── SUMMARY ──────────────────────────────────────────────────────────────")
print(f"  Uniswap matched proposals: {len(match_df)}")
print(f"  Pre-Claude3:  n={n_pre}  r={r_pre:+.3f}")
print(f"  Post-Claude3: n={n_post}  r={r_post:+.3f}")
print(f"  Chow F={F:.2f}  p={p_val:.4f}")
print(f"  Figure: {OUT_FIG}")
