#!/usr/bin/env python3
"""
Figure 8b — Causal Identification: AI Posting Shocks and Forum Signal Degradation

Core claim: Before AI, forum posting volume is a genuine signal of vote contestedness
(more posts → more controversy → smaller margin of victory). AI model releases are
exogenous shocks to posting cost. After each shock, AI posts flood threads without
reflecting real opinion, so the posts→margin correlation degrades.

Panel A: Monthly AI vs human post volume with shock dates (cost-of-posting shocks).
Panel B: Rolling correlation — human post count vs margin of victory.
         Prediction: stable pre-shock, weakens post-shock.
Panel C: Rolling correlation — TOTAL post count vs margin of victory.
         Prediction: weakens faster than Panel B as AI contamination grows.

Identification:
  - Treatment: AI model release dates (GPT-4, Claude 2/3, GPT-4o, DeepSeek R1)
  - Exogenous to any specific Arbitrum proposal
  - Pangram scores let us separate human signal from AI noise within-proposal

Data:
  - DuckDB: posts + post_ai_scores
  - Snapshot: proposal scores/choices for margin of victory
  - Forum-Snapshot title matching for thread linkage
"""

import re, time, json, os
import duckdb
import requests
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.gridspec as gridspec
from scipy import stats as spstats
from difflib import SequenceMatcher
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, C_TOTAL, C_SHOCK, savefig as aer_savefig
apply_aer_style()

HERE         = os.path.dirname(os.path.abspath(__file__))
ROOT         = os.path.dirname(HERE)   # project root
DB_PATH      = os.path.join(ROOT, "data", "arbitrum.db")
OUT_DIR      = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH     = os.path.join(OUT_DIR, "fig08_main_causal.png")
FORUM_CACHE  = os.path.join(ROOT, "data", "figure8_forum_cache.json")
SNAP_CACHE   = os.path.join(ROOT, "data", "figure8b_snap_cache.json")

SNAPSHOT_URL    = "https://hub.snapshot.org/graphql"
HEADERS         = {"User-Agent": "Mozilla/5.0 (research-bot)"}
MATCH_THRESHOLD = 0.55
AI_THRESHOLD    = 0.70
ROLLING_WINDOW  = 25

AI_EVENTS = [
    ("2023-03-14", "GPT-4"),
    ("2023-07-11", "Claude 2"),
    ("2024-03-04", "Claude 3"),
    ("2024-05-13", "GPT-4o"),
    ("2024-09-12", "o1"),
    ("2025-01-20", "DeepSeek R1"),
]


# ── helpers ───────────────────────────────────────────────────────────────────

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def save_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f)

def strip_html(html):
    return re.sub(r"<[^>]+>", " ", html or "").strip()

def title_sim(a, b):
    a = re.sub(r"[\[\(][^\]\)]*[\]\)]", "", a).strip().lower()
    b = re.sub(r"[\[\(][^\]\)]*[\]\)]", "", b).strip().lower()
    return SequenceMatcher(None, a, b).ratio()

def compute_margin(scores, choices):
    """
    Returns margin of victory: For% among (For+Against) non-abstain votes.
    0 = perfectly split, 1 = unanimous.
    Returns NaN if no for/against choices identifiable.
    """
    if not scores or not choices:
        return np.nan
    choice_score = dict(zip([c.lower() for c in choices], scores))
    for_score = choice_score.get("for", choice_score.get("yes", 0))
    against_score = choice_score.get("against", choice_score.get("no", 0))
    contested = for_score + against_score
    if contested == 0:
        return np.nan
    for_share = for_score / contested
    return abs(2 * for_share - 1)   # 0 = 50/50, 1 = unanimous


# ── Step 1: Load AI scores from DuckDB ───────────────────────────────────────

print("Step 1: Loading AI scores from DuckDB...")
con = duckdb.connect(DB_PATH, read_only=True)

monthly_raw = con.execute("""
    SELECT
        date_trunc('month', CAST(p.created_at AS TIMESTAMP)) AS month,
        CASE WHEN s.fraction_ai > ? THEN 'ai' ELSE 'human' END AS label,
        COUNT(*) AS post_count
    FROM posts p
    JOIN post_ai_scores s ON p.id = s.post_id
    WHERE s.fraction_ai IS NOT NULL
      AND s.headline NOT LIKE 'error:%'
      AND s.headline != 'too_short'
    GROUP BY 1, 2 ORDER BY 1
""", [AI_THRESHOLD]).df()

topic_scores = con.execute("""
    SELECT
        p.topic_id,
        COUNT(*) FILTER (WHERE s.fraction_ai <= ?)  AS human_posts,
        COUNT(*) FILTER (WHERE s.fraction_ai >  ?)  AS ai_posts,
        COUNT(*)                                     AS total_posts
    FROM posts p
    JOIN post_ai_scores s ON p.id = s.post_id
    WHERE s.fraction_ai IS NOT NULL
      AND s.headline NOT LIKE 'error:%'
    GROUP BY p.topic_id
""", [AI_THRESHOLD, AI_THRESHOLD]).df()
con.close()

topic_human = dict(zip(topic_scores.topic_id.astype(int), topic_scores.human_posts.astype(int)))
topic_total = dict(zip(topic_scores.topic_id.astype(int), topic_scores.total_posts.astype(int)))
topic_ai    = dict(zip(topic_scores.topic_id.astype(int), topic_scores.ai_posts.astype(int)))

monthly_df = monthly_raw.pivot_table(
    index="month", columns="label", values="post_count", aggfunc="sum"
).fillna(0)
monthly_df.columns = [f"post_count_{c}" for c in monthly_df.columns]
monthly_df.index = pd.to_datetime(monthly_df.index)
monthly_df = monthly_df.sort_index()
print(f"  {len(topic_scores)} topics with AI scores  |  "
      f"{monthly_df.index.min().date()} – {monthly_df.index.max().date()}")


# ── Step 2: Fetch Snapshot proposals with margin data ────────────────────────

SNAP_QUERY = """
{
  proposals(
    first: 1000
    skip: %d
    where: { space_in: ["arbitrumfoundation.eth"], state: "closed" }
    orderBy: "created"
    orderDirection: asc
  ) {
    id title created votes scores_total scores choices
  }
}
"""

snap_cache = load_json(SNAP_CACHE)
TEMP_RE    = re.compile(r'\btemp(erature)?\s*check\b', re.I)

if not snap_cache:
    print("\nStep 2: Fetching Snapshot proposals...")
    raw_props = []
    skip = 0
    while True:
        r = requests.post(SNAPSHOT_URL, json={"query": SNAP_QUERY % skip},
                          headers=HEADERS, timeout=30)
        batch = r.json().get("data", {}).get("proposals", [])
        if not batch:
            break
        raw_props.extend(batch)
        if len(batch) < 1000:
            break
        skip += 1000
        time.sleep(0.3)
    save_json(SNAP_CACHE, raw_props)
    print(f"  {len(raw_props)} proposals fetched and cached")
else:
    raw_props = snap_cache
    print(f"\nStep 2: {len(raw_props)} proposals loaded from cache")

rows = []
for p in raw_props:
    dt = pd.to_datetime(p["created"], unit="s")
    if dt < pd.Timestamp("2023-01-01"):
        continue
    if TEMP_RE.search(p["title"]):
        continue
    if p["votes"] == 0:
        continue
    margin = compute_margin(p.get("scores"), p.get("choices"))
    if np.isnan(margin):
        continue
    rows.append({
        "snap_id": p["id"],
        "title":   p["title"],
        "created": dt,
        "votes":   p["votes"],
        "margin":  margin,
    })

snap_df = pd.DataFrame(rows)
print(f"  {len(snap_df)} proposals with computable margin  "
      f"(temp checks excluded, votes > 0)")
print(f"  Margin stats: mean={snap_df['margin'].mean():.3f}  "
      f"median={snap_df['margin'].median():.3f}  "
      f"min={snap_df['margin'].min():.3f}  max={snap_df['margin'].max():.3f}")


# ── Step 3: Load all forum topic titles from DuckDB ──────────────────────────

print("\nStep 3: Loading forum topic titles from DuckDB...")
con2 = duckdb.connect(DB_PATH, read_only=True)
all_topics_df = con2.execute("SELECT id, title FROM topics WHERE title IS NOT NULL").df()
con2.close()
all_topic_titles = dict(zip(all_topics_df["id"].astype(int), all_topics_df["title"]))
print(f"  {len(all_topic_titles)} forum topics available for matching")
# Only match to topics that have scored posts in DuckDB (so human_posts is not NaN)
matchable_tids = set(topic_human.keys())
print(f"  {len(matchable_tids)} topics have scored post data")


# ── Step 4: Match forum threads → Snapshot proposals ─────────────────────────

print("\nStep 4: Matching forum threads to Snapshot proposals...")

matched = []
for row in snap_df.itertuples():
    best_score, best_tid, best_title = 0, None, None
    for tid, ttitle in all_topic_titles.items():
        if tid not in matchable_tids:
            continue
        s = title_sim(row.title, ttitle)
        if s > best_score:
            best_score, best_tid, best_title = s, tid, ttitle
    if best_score < MATCH_THRESHOLD or best_tid is None:
        continue
    matched.append({
        "snap_id":     row.snap_id,
        "title":       row.title,
        "created":     row.created,
        "votes":       row.votes,
        "margin":      row.margin,
        "topic_id":    best_tid,
        "match_score": best_score,
        "human_posts": topic_human.get(best_tid, np.nan),
        "ai_posts":    topic_ai.get(best_tid, np.nan),
        "total_posts": topic_total.get(best_tid, np.nan),
    })

match_df = (pd.DataFrame(matched)
              .dropna(subset=["human_posts", "margin"])
              .sort_values("created")
              .reset_index(drop=True))

# De-duplicate: enforce 1-to-1 forum-thread → proposal matching.
# Batch grant programs (LTIPP, STIP Round 1) produce many proposals with
# similar titles that fuzzy-match to the same unrelated thread. We drop the
# retracted AIP 1.05 vote, then keep only the highest-score match per
# topic_id, then require match_score >= 0.65 to exclude residual bad matches.
match_df = match_df[~(match_df["title"].str.contains("AIP 1.05", na=False) &
                       ~match_df["title"].str.contains(r"\[REAL\]", na=False, regex=True))]
match_df = (match_df.sort_values("match_score", ascending=False)
                    .drop_duplicates("topic_id", keep="first"))
match_df = match_df[match_df["match_score"] >= 0.65].sort_values("created").reset_index(drop=True)
match_df["prop_index"] = match_df.index

MATCHED_CSV = os.path.join(ROOT, "data", "matched_proposals.csv")
match_df.to_csv(MATCHED_CSV, index=False)
print(f"  {len(match_df)} proposals matched with human/AI post counts and margin data (after de-dup)")
print(f"  Saved to {MATCHED_CSV}")

# Baseline correlation
r_human, p_human = spstats.pearsonr(match_df["human_posts"], match_df["margin"])
r_total, p_total = spstats.pearsonr(match_df["total_posts"], match_df["margin"])
r_ai,    p_ai    = spstats.pearsonr(match_df["ai_posts"],    match_df["margin"])
print(f"\n  Baseline correlations (all proposals, n={len(match_df)}):")
print(f"    r(human_posts, margin) = {r_human:+.3f}  p = {p_human:.4f}")
print(f"    r(total_posts, margin) = {r_total:+.3f}  p = {p_total:.4f}")
print(f"    r(ai_posts,    margin) = {r_ai:+.3f}  p = {p_ai:.4f}")


# ── Step 5: Pre/post shock comparison ─────────────────────────────────────────

print("\nStep 5: Pre/post shock correlations...")
shock_date = pd.Timestamp("2024-03-04")   # Claude 3 — first "capable" AI for long-form writing
pre  = match_df[match_df["created"] <  shock_date]
post = match_df[match_df["created"] >= shock_date]

for label, sub in [("Pre-Claude-3", pre), ("Post-Claude-3", post)]:
    if len(sub) < 10:
        continue
    rh, ph = spstats.pearsonr(sub["human_posts"], sub["margin"])
    rt, pt = spstats.pearsonr(sub["total_posts"], sub["margin"])
    print(f"  {label} (n={len(sub)}):  "
          f"r(human, margin)={rh:+.3f} p={ph:.3f}  |  "
          f"r(total, margin)={rt:+.3f} p={pt:.3f}")


# ── Step 6: Rolling correlation ───────────────────────────────────────────────

print("\nStep 6: Computing rolling correlations...")

def rolling_pearson(x, y, window):
    out = [np.nan] * len(x)
    for i in range(window - 1, len(x)):
        xi, yi = x[i - window + 1:i + 1], y[i - window + 1:i + 1]
        if np.std(xi) > 0 and np.std(yi) > 0:
            out[i] = spstats.pearsonr(xi, yi)[0]
    return out

human_arr = match_df["human_posts"].values.astype(float)
total_arr = match_df["total_posts"].values.astype(float)
margin_arr = match_df["margin"].values.astype(float)

match_df["roll_human"] = rolling_pearson(human_arr, margin_arr, ROLLING_WINDOW)
match_df["roll_total"] = rolling_pearson(total_arr, margin_arr, ROLLING_WINDOW)


# ── Step 7: Plot ──────────────────────────────────────────────────────────────

HUMAN_C = C_HUMAN
AI_C    = C_AI
TOTAL_C = C_TOTAL
SHOCK_C = C_SHOCK

fig = plt.figure(figsize=(7, 9))
gs  = gridspec.GridSpec(3, 1, hspace=0.50, figure=fig)
ax_a = fig.add_subplot(gs[0])
ax_b = fig.add_subplot(gs[1])
ax_c = fig.add_subplot(gs[2])

ai_event_dates  = [pd.Timestamp(d) for d, _ in AI_EVENTS]
ai_event_labels = [l for _, l in AI_EVENTS]
months = monthly_df.index
x_pos  = np.arange(len(months))

# ── Panel A: monthly post volume ──────────────────────────────────────────────
human_c = monthly_df.get("post_count_human", pd.Series(0, index=months)).values
ai_c    = monthly_df.get("post_count_ai",    pd.Series(0, index=months)).values

ax_a.bar(x_pos, human_c, 0.8, label="Human-written", color=HUMAN_C, alpha=0.9)
ax_a.bar(x_pos, ai_c,    0.8, label="AI-generated",
         bottom=human_c, color=AI_C, alpha=0.9)

tick_step = max(1, len(months) // 10)
ax_a.set_xticks(x_pos[::tick_step])
ax_a.set_xticklabels([m.strftime("%b '%y") for m in months[::tick_step]],
                     rotation=30, ha="right")
ax_a.set_ylabel("Posts per month")
ax_a.set_title("Panel A: Monthly forum posts, by author type",
               fontsize=10, loc="left")
ax_a.legend(loc="upper left", frameon=True)
ax_a.set_xlim(-0.5, len(months) - 0.5)

trans_a = ax_a.get_xaxis_transform()
for dt, lbl in zip(ai_event_dates, ai_event_labels):
    if dt < months[0] or dt > months[-1]:
        continue
    ni = int(np.argmin(np.abs([(m - dt).days for m in months])))
    ax_a.axvline(ni, color=SHOCK_C, linewidth=1.2, linestyle="--", alpha=0.65)
    ax_a.text(ni + 0.15, 0.97, lbl, transform=trans_a, rotation=90,
              va="top", ha="left", fontsize=7.5, color=SHOCK_C)


def plot_rolling(ax, roll_col, color, label, dates):
    rc = match_df[roll_col]
    valid = rc.notna()
    ax.plot(dates, rc, color=color, linewidth=1.5, zorder=4)
    ax.fill_between(dates[valid], 0, rc[valid],
                    where=(rc[valid] < 0), alpha=0.12, color=color)
    ax.fill_between(dates[valid], 0, rc[valid],
                    where=(rc[valid] > 0), alpha=0.08, color=COLORS["gray"])
    ax.axhline(0, color=COLORS["lightgray"], linewidth=0.8, zorder=1)
    for dt, lbl in zip(ai_event_dates, ai_event_labels):
        if dt < dates.min() or dt > dates.max():
            continue
        ax.axvline(dt, color=SHOCK_C, linewidth=0.9, linestyle="--", alpha=0.7, zorder=2)
        ax.text(dt, 0.96, lbl, transform=ax.get_xaxis_transform(),
                rotation=90, va="top", ha="right", fontsize=8,
                color=SHOCK_C, style="italic")
    ax.set_ylabel(r"Rolling Pearson $r$")
    ax.set_xlabel("Proposal date")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:.2f}"))
    ax.set_ylim(-0.85, 0.65)
    despine(ax)


# ── Panel B: rolling r(human_posts, margin) ───────────────────────────────────
dates = match_df["created"]
plot_rolling(ax_b, "roll_human", HUMAN_C, "r(human_posts, margin)", dates)

sig_h = ("***" if p_human < 0.001 else "**" if p_human < 0.01
         else "*" if p_human < 0.05 else "n.s.")
ax_b.text(0.97, 0.95,
    f"$r = {r_human:+.3f}${sig_h},  $n = {len(match_df)}$",
    transform=ax_b.transAxes, fontsize=9, va="top", ha="right",
    bbox=dict(fc="white", ec=COLORS["lightgray"], pad=3, alpha=0.95))
ax_b.set_title("Panel B: Human posts vs. margin of victory (rolling correlation)",
               fontsize=10, loc="left")

# ── Panel C: rolling r(total_posts, margin) ───────────────────────────────────
plot_rolling(ax_c, "roll_total", TOTAL_C, "r(total_posts, margin)", dates)

sig_t = ("***" if p_total < 0.001 else "**" if p_total < 0.01
         else "*" if p_total < 0.05 else "n.s.")
ax_c.text(0.97, 0.95,
    f"$r = {r_total:+.3f}${sig_t},  $n = {len(match_df)}$",
    transform=ax_c.transAxes, fontsize=9, va="top", ha="right",
    bbox=dict(fc="white", ec=COLORS["lightgray"], pad=3, alpha=0.95))
ax_c.set_title("Panel C: Total Posts vs. Margin of Victory",
               fontsize=10, loc="left")

for ax in [ax_a, ax_b, ax_c]:
    despine(ax)

fig.tight_layout()
aer_savefig(fig, OUT_PATH)
