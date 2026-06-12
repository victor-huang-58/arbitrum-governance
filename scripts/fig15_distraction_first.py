#!/usr/bin/env python3
"""
First-stage analysis: do distraction events reduce Arbitrum forum posting?

Strategy (Hirshleifer et al. 2009 / Peress & Schmidt 2020 analog):
  Instrument = exogenous events that draw crypto-community attention away from
  governance forums. Two distraction proxies:
    1. ETH daily price volatility (|log return|) — when price moves sharply,
       traders watch dashboards, not governance forums.
    2. Major crypto conferences — pre-announced, clearly exogenous to proposal quality.

  First stage test:
    forum_posts_on_proposal_day ~ distraction_proxy + controls

  If first stage is significant, proceed to second stage:
    (instrumented) forum_posts → margin_of_victory / voter_turnout

Data sources:
  - CoinGecko free API: ETH/BTC daily OHLCV (no key needed)
  - Conference dates: hard-coded from public records
  - Proposal dates + forum posts: from DuckDB + figure8b matched proposals
"""

import os, json, time
import requests
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats as spstats
import duckdb

HERE         = os.path.dirname(os.path.abspath(__file__))
ROOT         = os.path.dirname(HERE)   # project root
DB_PATH      = os.path.join(ROOT, "data", "arbitrum.db")
SNAP_CACHE   = os.path.join(ROOT, "data", "figure8b_snap_cache.json")
FORUM_CACHE  = os.path.join(ROOT, "data", "figure8_forum_cache.json")
PRICE_CACHE  = os.path.join(ROOT, "data", "eth_price_cache.json")
OUT_DIR      = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH     = os.path.join(OUT_DIR, "fig15_distraction_first.png")

CRYPTOCOMPARE = "https://min-api.cryptocompare.com/data/v2/histoday"
HEADERS       = {"User-Agent": "Mozilla/5.0 (research-bot)"}


# ── Crypto conference dates (major events, exogenous to Arbitrum proposals) ───
# Sources: official conference websites, publicly announced schedules

CONFERENCES = [
    # (start, end, name)
    ("2023-02-24", "2023-03-05", "ETHDenver 2023"),
    ("2023-04-26", "2023-04-28", "Consensus 2023"),
    ("2023-09-13", "2023-09-14", "Token2049 Singapore 2023"),
    ("2023-11-13", "2023-11-16", "Devcon Istanbul 2023"),
    ("2024-02-29", "2024-03-03", "ETHDenver 2024"),
    ("2024-05-29", "2024-05-31", "Consensus 2024"),
    ("2024-09-18", "2024-09-19", "Token2049 Singapore 2024"),
    ("2024-11-12", "2024-11-15", "Devcon Bangkok 2024"),
    ("2025-02-28", "2025-03-02", "ETHDenver 2025"),
    ("2025-05-14", "2025-05-16", "Consensus 2025"),
]

# Major crypto distraction events (price crashes, major news)
# These are well-known events, exogenous to Arbitrum governance
CRYPTO_EVENTS = [
    ("2023-03-10", "2023-03-13", "SVB Collapse / USDC Depeg"),
    ("2023-06-05", "2023-06-10", "SEC Binance/Coinbase Lawsuits"),
    ("2024-01-10", "2024-01-12", "Bitcoin ETF Approval"),
    ("2024-03-14", "2024-03-14", "Bitcoin ATH ~$73k"),
    ("2024-08-05", "2024-08-07", "Global Market Crash (Yen carry)"),
    ("2025-01-18", "2025-01-21", "Trump Inauguration + TRUMP memecoin"),
    ("2025-02-03", "2025-02-05", "Tariff announcement market crash"),
]


# ── Load ETH price data ────────────────────────────────────────────────────────

def fetch_eth_prices(cache_path):
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            data = json.load(f)
        if data:
            return data
    print("Fetching ETH price history from CryptoCompare...")
    all_prices = {}
    # Fetch up to 2000 days ending today
    r = requests.get(CRYPTOCOMPARE,
                     params={"fsym": "ETH", "tsym": "USD", "limit": 2000},
                     headers=HEADERS, timeout=30)
    data = r.json()
    if data.get("Response") == "Success":
        for row in data["Data"]["Data"]:
            date = pd.Timestamp(row["time"], unit="s").strftime("%Y-%m-%d")
            all_prices[date] = {"open": row["open"], "close": row["close"],
                                "high": row["high"], "low": row["low"]}
    with open(cache_path, "w") as f:
        json.dump(all_prices, f)
    print(f"  {len(all_prices)} daily ETH prices cached")
    return all_prices


price_data = fetch_eth_prices(PRICE_CACHE)
price_df = pd.DataFrame([
    {"date": pd.Timestamp(d), "eth_open": v["open"], "eth_close": v["close"]}
    for d, v in price_data.items()
]).sort_values("date").reset_index(drop=True)

price_df["log_return"]    = np.log(price_df["eth_close"] / price_df["eth_open"])
price_df["abs_return"]    = price_df["log_return"].abs()
price_df["volatility_3d"] = price_df["abs_return"].rolling(3, center=True).mean()
print(f"ETH prices: {price_df['date'].min().date()} – {price_df['date'].max().date()}")
print(f"  Median daily |return|: {price_df['abs_return'].median():.3f}")
print(f"  90th pct daily |return|: {price_df['abs_return'].quantile(0.9):.3f}")


# ── Build conference / event distraction indicator ─────────────────────────────

def is_conference_day(date):
    for start, end, name in CONFERENCES:
        s, e = pd.Timestamp(start), pd.Timestamp(end)
        # Also include 3 days before (pre-conference travel) and 2 days after
        if s - pd.Timedelta(days=3) <= date <= e + pd.Timedelta(days=2):
            return 1
    return 0

def conference_name(date):
    for start, end, name in CONFERENCES:
        s, e = pd.Timestamp(start), pd.Timestamp(end)
        if s - pd.Timedelta(days=3) <= date <= e + pd.Timedelta(days=2):
            return name
    return None

def is_crypto_event_day(date):
    for start, end, name in CRYPTO_EVENTS:
        s, e = pd.Timestamp(start), pd.Timestamp(end)
        if s - pd.Timedelta(days=1) <= date <= e + pd.Timedelta(days=1):
            return 1
    return 0


# ── Load matched proposal data ─────────────────────────────────────────────────

print("\nLoading proposal + forum data...")
from difflib import SequenceMatcher
import re

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
    contested = f + a
    if contested == 0:
        return np.nan
    return abs(2 * f / contested - 1)

# Load Snapshot proposals
with open(SNAP_CACHE) as f:
    raw_props = json.load(f)

TEMP_RE = re.compile(r'\btemp(erature)?\s*check\b', re.I)
snap_rows = []
for p in raw_props:
    dt = pd.to_datetime(p["created"], unit="s")
    if dt < pd.Timestamp("2023-01-01") or TEMP_RE.search(p["title"]):
        continue
    if p["votes"] == 0:
        continue
    margin = compute_margin(p.get("scores"), p.get("choices"))
    if np.isnan(margin):
        continue
    snap_rows.append({"snap_id": p["id"], "title": p["title"],
                      "created": dt, "votes": p["votes"], "margin": margin})
snap_df = pd.DataFrame(snap_rows)

# Load forum thread cache + AI scores from DB
with open(FORUM_CACHE) as f:
    forum_cache = json.load(f)

con = duckdb.connect(DB_PATH, read_only=True)
AI_THR = 0.70
topic_scores = con.execute(f"""
    SELECT p.topic_id,
           COUNT(*) FILTER (WHERE s.fraction_ai <= {AI_THR}) AS human_posts,
           COUNT(*) FILTER (WHERE s.fraction_ai >  {AI_THR}) AS ai_posts,
           COUNT(*) AS total_posts
    FROM posts p
    JOIN post_ai_scores s ON p.id = s.post_id
    WHERE s.fraction_ai IS NOT NULL
      AND s.headline NOT LIKE 'error:%'
    GROUP BY p.topic_id
""").df()
con.close()
topic_human = dict(zip(topic_scores.topic_id.astype(int), topic_scores.human_posts.astype(int)))
topic_total = dict(zip(topic_scores.topic_id.astype(int), topic_scores.total_posts.astype(int)))

# Match proposals to forum threads
MATCH_THRESHOLD = 0.55
matched = []
for row in snap_df.itertuples():
    best_score, best_tid = 0, None
    for tid, fdata in forum_cache.items():
        s = title_sim(row.title, fdata.get("title", ""))
        if s > best_score:
            best_score, best_tid = s, int(tid)
    if best_score < MATCH_THRESHOLD or best_tid is None:
        continue
    h = topic_human.get(best_tid, np.nan)
    t = topic_total.get(best_tid, np.nan)
    if np.isnan(h):
        continue
    matched.append({
        "snap_id":     row.snap_id,
        "title":       row.title,
        "created":     row.created,
        "votes":       row.votes,
        "margin":      row.margin,
        "human_posts": h,
        "total_posts": t,
    })

prop_df = pd.DataFrame(matched).sort_values("created").reset_index(drop=True)
print(f"  {len(prop_df)} matched proposals  "
      f"({prop_df['created'].min().date()} – {prop_df['created'].max().date()})")


# ── Merge distraction variables onto proposals ─────────────────────────────────

price_map      = dict(zip(price_df["date"].dt.strftime("%Y-%m-%d"), price_df["abs_return"]))
vol3d_map      = dict(zip(price_df["date"].dt.strftime("%Y-%m-%d"), price_df["volatility_3d"]))

prop_df["date_str"]      = prop_df["created"].dt.strftime("%Y-%m-%d")
prop_df["eth_abs_ret"]   = prop_df["date_str"].map(price_map)
prop_df["eth_vol_3d"]    = prop_df["date_str"].map(vol3d_map)
prop_df["conf_day"]      = prop_df["created"].apply(is_conference_day)
prop_df["crypto_event"]  = prop_df["created"].apply(is_crypto_event_day)
prop_df["any_distract"]  = ((prop_df["conf_day"] == 1) | (prop_df["crypto_event"] == 1)).astype(int)
prop_df["high_vol"]      = (prop_df["eth_abs_ret"] > prop_df["eth_abs_ret"].quantile(0.75)).astype(int)
prop_df["conference_name"] = prop_df["created"].apply(conference_name)

print(f"\nDistraction summary:")
print(f"  Conference days: {prop_df['conf_day'].sum()} proposals")
print(f"  Crypto event days: {prop_df['crypto_event'].sum()} proposals")
print(f"  High volatility (top 25%): {prop_df['high_vol'].sum()} proposals")
print(f"  Any distraction: {prop_df['any_distract'].sum()} proposals")

# Show which proposals fell during conferences
conf_props = prop_df[prop_df["conf_day"] == 1][["title", "created", "conference_name", "human_posts", "margin", "votes"]]
if len(conf_props):
    print(f"\nProposals during conferences (n={len(conf_props)}):")
    for _, r in conf_props.iterrows():
        print(f"  [{r['created'].date()}] {r['title'][:55]:<55}  "
              f"posts={int(r['human_posts']):3d}  margin={r['margin']:.2f}  "
              f"conf={r['conference_name']}")


# ── FIRST STAGE: do distraction events reduce forum posting? ──────────────────

print("\n" + "="*65)
print("FIRST STAGE: Distraction → Forum Posts")
print("="*65)

clean = prop_df.dropna(subset=["eth_abs_ret", "human_posts", "margin"]).copy()

# OLS: log(human_posts+1) ~ distraction proxies
clean["log_human"]  = np.log1p(clean["human_posts"])
clean["log_total"]  = np.log1p(clean["total_posts"])

def ols_summary(y, X_df, label):
    X = np.column_stack([np.ones(len(y)), X_df.values])
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    sigma2 = np.sum(resid**2) / (n - k)
    se = np.sqrt(np.diag(sigma2 * np.linalg.inv(X.T @ X)))
    t  = beta / se
    r2 = 1 - np.sum(resid**2) / np.sum((y - y.mean())**2)
    print(f"\n  {label}  (n={n}, R²={r2:.3f})")
    cols = ["(intercept)"] + list(X_df.columns)
    for i, c in enumerate(cols):
        sig = ("***" if abs(t[i]) > 3.29 else "**" if abs(t[i]) > 2.58
               else "*" if abs(t[i]) > 1.96 else "")
        print(f"    {c:<22} β={beta[i]:+.4f}  t={t[i]:+.2f} {sig}")
    return beta, se, t, r2

y_human = clean["log_human"].values
y_total = clean["log_total"].values

# Model A: conference + crypto event
ols_summary(y_human, clean[["conf_day", "crypto_event"]], "Y=log(human_posts) ~ conf + crypto_event")
ols_summary(y_human, clean[["any_distract"]],             "Y=log(human_posts) ~ any_distraction")
ols_summary(y_human, clean[["eth_abs_ret"]],              "Y=log(human_posts) ~ eth_abs_return")
ols_summary(y_human, clean[["high_vol"]],                 "Y=log(human_posts) ~ high_vol_dummy")
ols_summary(y_human, clean[["conf_day", "crypto_event", "eth_abs_ret"]],
            "Y=log(human_posts) ~ conf + crypto_event + eth_vol (combined)")

# Simple group means
print("\n  --- Group means ---")
for label, mask in [
    ("Conference days",   clean["conf_day"] == 1),
    ("Non-conference",    clean["conf_day"] == 0),
    ("Crypto event days", clean["crypto_event"] == 1),
    ("Non-event",         clean["crypto_event"] == 0),
    ("High volatility",   clean["high_vol"] == 1),
    ("Low volatility",    clean["high_vol"] == 0),
]:
    sub = clean[mask]
    if len(sub) == 0:
        continue
    print(f"    {label:<22}  n={len(sub):3d}  "
          f"avg_human_posts={sub['human_posts'].mean():.1f}  "
          f"avg_margin={sub['margin'].mean():.3f}  "
          f"avg_votes={sub['votes'].mean():.0f}")

# t-tests
for (g1_name, g1), (g2_name, g2) in [
    (("Conference", clean[clean["conf_day"]==1]["log_human"]),
     ("Non-conf",   clean[clean["conf_day"]==0]["log_human"])),
    (("Crypto event", clean[clean["crypto_event"]==1]["log_human"]),
     ("Non-event",    clean[clean["crypto_event"]==0]["log_human"])),
    (("High vol", clean[clean["high_vol"]==1]["log_human"]),
     ("Low vol",  clean[clean["high_vol"]==0]["log_human"])),
]:
    if len(g1) >= 5:
        t, p = spstats.ttest_ind(g1, g2)
        print(f"\n  t-test {g1_name} vs {g2_name}: t={t:.2f}  p={p:.4f}  "
              f"Δmean={g1.mean()-g2.mean():+.3f} log posts")


# ── REDUCED FORM: distraction → margin / votes ────────────────────────────────

print("\n" + "="*65)
print("REDUCED FORM: Distraction → Governance Outcomes")
print("="*65)

ols_summary(clean["margin"].values, clean[["conf_day", "crypto_event"]], "Y=margin ~ conf + crypto_event")
ols_summary(clean["margin"].values, clean[["any_distract"]],             "Y=margin ~ any_distraction")
ols_summary(np.log1p(clean["votes"].values), clean[["conf_day", "crypto_event"]], "Y=log(votes) ~ conf + crypto_event")


# ── Plot ──────────────────────────────────────────────────────────────────────

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.subplots_adjust(hspace=0.4, wspace=0.35)

CONF_C   = "#E74C3C"
EVENT_C  = "#E67E22"
NORMAL_C = "#2980B9"

def scatter_with_groups(ax, x_col, y_col, xlabel, ylabel, title, log_y=False):
    colors = clean.apply(
        lambda r: CONF_C if r["conf_day"] else (EVENT_C if r["crypto_event"] else NORMAL_C),
        axis=1
    )
    y = np.log1p(clean[y_col]) if log_y else clean[y_col]
    ax.scatter(clean[x_col], y, c=colors, alpha=0.6, s=30, linewidths=0)
    # Add trend line
    valid = clean[[x_col]].join(pd.Series(y, name=y_col, index=clean.index)).dropna()
    if len(valid) > 5:
        slope, intercept, r, p, _ = spstats.linregress(valid[x_col], valid[y_col])
        xr = np.linspace(valid[x_col].min(), valid[x_col].max(), 100)
        ax.plot(xr, slope * xr + intercept, "k--", linewidth=1.5, alpha=0.7)
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "n.s."
        ax.text(0.97, 0.97, f"r={r:.3f} {sig}", transform=ax.transAxes,
                fontsize=9, va="top", ha="right", family="monospace",
                bbox=dict(fc="white", ec="#BDC3C7", pad=3, alpha=0.9))
    ax.set_xlabel(xlabel, fontsize=10)
    ax.set_ylabel(ylabel, fontsize=10)
    ax.set_title(title, fontsize=10, fontweight="bold", loc="left")
    ax.grid(linestyle="--", linewidth=0.4, alpha=0.4)

import matplotlib.patches as mpatches
legend_handles = [
    mpatches.Patch(color=CONF_C,   label="Conference window"),
    mpatches.Patch(color=EVENT_C,  label="Crypto event"),
    mpatches.Patch(color=NORMAL_C, label="Normal day"),
]

scatter_with_groups(axes[0,0], "eth_abs_ret", "human_posts",
    "ETH |daily return|", "Human posts in thread",
    "ETH Volatility vs. Forum Posting", log_y=True)
axes[0,0].legend(handles=legend_handles, fontsize=8, loc="upper right")

scatter_with_groups(axes[0,1], "eth_abs_ret", "margin",
    "ETH |daily return|", "Margin of victory",
    "ETH Volatility vs. Margin of Victory")

# Box plots: conference vs non-conference
ax_box1 = axes[1,0]
data_conf    = clean[clean["conf_day"]==1]["human_posts"]
data_noconf  = clean[clean["conf_day"]==0]["human_posts"]
data_event   = clean[clean["crypto_event"]==1]["human_posts"]
data_noevent = clean[clean["crypto_event"]==0]["human_posts"]
ax_box1.boxplot([data_noconf, data_conf, data_noevent, data_event],
                labels=["No conf", "Conference", "No event", "Crypto event"],
                showfliers=False, patch_artist=True,
                boxprops=dict(facecolor="#ECF0F1"))
ax_box1.set_ylabel("Human posts in proposal thread", fontsize=10)
ax_box1.set_title("Posting Volume: Distraction vs. Normal Days", fontsize=10, fontweight="bold", loc="left")
ax_box1.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.4)

ax_box2 = axes[1,1]
margin_conf    = clean[clean["conf_day"]==1]["margin"]
margin_noconf  = clean[clean["conf_day"]==0]["margin"]
margin_event   = clean[clean["crypto_event"]==1]["margin"]
margin_noevent = clean[clean["crypto_event"]==0]["margin"]
ax_box2.boxplot([margin_noconf, margin_conf, margin_noevent, margin_event],
                labels=["No conf", "Conference", "No event", "Crypto event"],
                showfliers=False, patch_artist=True,
                boxprops=dict(facecolor="#ECF0F1"))
ax_box2.set_ylabel("Margin of victory", fontsize=10)
ax_box2.set_title("Vote Margin: Distraction vs. Normal Days", fontsize=10, fontweight="bold", loc="left")
ax_box2.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.4)

fig.suptitle(
    "Figure 15: First Stage — Do Distraction Events Reduce Forum Participation?\n"
    "Arbitrum DAO 2023–2026  |  Distraction proxies: ETH volatility + conferences + crypto events",
    fontsize=12, fontweight="bold", y=1.01
)
fig.savefig(OUT_PATH, dpi=180, bbox_inches="tight")
print(f"\nSaved → {OUT_PATH}")
