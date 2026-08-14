#!/usr/bin/env python3
"""
Delegate-level analysis: does AI posting correlate with delegation accumulation?

Figure:
  Panel A — Scatter: avg_ai vs log10(avg_vp), sized by post count, annotated.
             Tests whether AI-heavy delegates attracted more or less voting power.
  Panel B — Voting power time-series for selected delegates, sorted by proposal date.
             Shows whether AI-heavy delegates' vp grew or declined relative to human-heavy ones.
  Panel C — Regression: avg_ai predicts log10(avg_vp), controlling for first-post year.

Needs:
  - data/arbitrum.db  (posts, post_ai_scores, delegate_wallet_map)
  - data/figure5_votes_cache.json  (proposal_id → [{voter, vp}])
  - Snapshot API for proposal dates (cached inline)
"""

import os, json, time, re
import duckdb
import requests
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy import stats as spstats
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, savefig as aer_savefig
import freeze
apply_aer_style()

HERE             = os.path.dirname(os.path.abspath(__file__))
ROOT             = os.path.dirname(HERE)   # project root
DB_PATH          = os.path.join(ROOT, "data", "arbitrum.db")
VOTES_CACHE      = os.path.join(ROOT, "data", "figure5_votes_cache.json")
SNAP_DATE_CACHE  = os.path.join(ROOT, "data", "snapshot_proposal_dates.json")
OUT_DIR          = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH         = os.path.join(OUT_DIR, "fig11_delegates.png")

SNAPSHOT_URL = "https://hub.snapshot.org/graphql"
HEADERS      = {"User-Agent": "Mozilla/5.0 (research-bot)"}

# ── load data ─────────────────────────────────────────────────────────────────

SNAP_QUERY = """
{
  proposals(
    first: 1000
    skip: %d
    where: { space_in: ["arbitrumfoundation.eth"], state: "closed" }
    orderBy: "created"
    orderDirection: asc
  ) {
    id created
  }
}
"""

def load_snapshot_dates(cache_path):
    if os.path.exists(cache_path):
        with open(cache_path) as f:
            data = json.load(f)
        if data:
            return data
    print("Fetching Snapshot proposal dates...")
    dates = {}
    skip = 0
    while True:
        try:
            r = requests.post(SNAPSHOT_URL, json={"query": SNAP_QUERY % skip},
                              headers=HEADERS, timeout=30)
            resp = r.json()
            batch = resp.get("data", {}).get("proposals", [])
            if not batch:
                break
            for p in batch:
                dates[p["id"]] = p["created"]
            if len(batch) < 1000:
                break
            skip += 1000
            time.sleep(0.3)
        except Exception as e:
            print(f"  Snapshot fetch error: {e}")
            break
    with open(cache_path, "w") as f:
        json.dump(dates, f)
    print(f"  {len(dates)} proposals cached")
    return dates


print("Loading data...")
con = duckdb.connect(DB_PATH, read_only=True)

# Delegate wallet map
wallet_map = con.execute(
    "SELECT forum_username, wallet_address FROM delegate_wallet_map "
    "WHERE wallet_address IS NOT NULL"
).fetchall()
username_to_wallet = {u: w.lower() for u, w in wallet_map}
wallet_to_username = {w.lower(): u for u, w in wallet_map}

# AI scores per delegate
ai_rows = con.execute("""
    SELECT p.username,
           AVG(s.fraction_ai)   AS avg_ai,
           COUNT(*)             AS n_posts,
           MIN(p.created_at)    AS first_post
    FROM posts p
    JOIN post_ai_scores s ON p.id = s.post_id
    WHERE s.fraction_ai IS NOT NULL
      AND s.headline NOT LIKE 'error:%'
      AND s.headline != 'too_short'
    GROUP BY p.username
""").fetchall()
ai_map = {r[0]: {"avg_ai": r[1], "n_posts": r[2], "first_post": r[3][:10]}
          for r in ai_rows}

con.close()

# Votes cache
with open(VOTES_CACHE) as f:
    votes_raw = json.load(f)

# Snapshot dates
snap_dates = load_snapshot_dates(SNAP_DATE_CACHE)

# proposal_id → unix timestamp (int); converted to Timestamp later
prop_dates = snap_dates

# ── build delegate-level frame ────────────────────────────────────────────────

delegate_vp = {}   # username → {proposal_id: vp}
for prop_id, voter_list in votes_raw.items():
    for v in voter_list:
        uname = wallet_to_username.get(v["voter"].lower())
        if uname:
            delegate_vp.setdefault(uname, {})[prop_id] = freeze.to_value(v["vp"])

rows = []
for uname, vpdata in delegate_vp.items():
    ai = ai_map.get(uname, {})
    avg_vp = np.mean(list(vpdata.values()))
    max_vp = max(vpdata.values())
    n_props = len(vpdata)
    first_post = ai.get("first_post", "2025-01-01")
    rows.append({
        "username":    uname,
        "avg_ai":      ai.get("avg_ai", np.nan),
        "n_posts":     ai.get("n_posts", 0),
        "first_post":  first_post,
        "first_year":  int(first_post[:4]) if first_post else 2025,
        "avg_vp":      avg_vp,
        "log_avg_vp":  np.log10(max(avg_vp, 1)),
        "max_vp":      max_vp,
        "n_proposals": n_props,
        "vp_series":   vpdata,
    })

df = pd.DataFrame(rows).dropna(subset=["avg_ai", "avg_vp"])
df = df[df["avg_vp"] > 0]
print(f"Analysis frame: {len(df)} delegates")

# Protocol / institutional flag (large vp, few posts relative to vp)
# Simple threshold: vp per post ratio — protocol delegates post very little
# relative to their vp, individual delegates post more
df["vp_per_post"] = df["avg_vp"] / df["n_posts"].clip(lower=1)
df["is_protocol"] = df["vp_per_post"] > 500_000  # heuristic

# ── regression ────────────────────────────────────────────────────────────────

df_ind = df[~df["is_protocol"]].copy()
df_inst = df[df["is_protocol"]].copy()

# OLS: log_avg_vp ~ avg_ai + first_year
X = df_ind[["avg_ai", "first_year"]].values
X = np.column_stack([np.ones(len(X)), X])
y = df_ind["log_avg_vp"].values
beta, res, rank, sv = np.linalg.lstsq(X, y, rcond=None)
y_hat = X @ beta
ss_res = np.sum((y - y_hat) ** 2)
ss_tot = np.sum((y - y.mean()) ** 2)
r2 = 1 - ss_res / ss_tot
r_ai, p_ai = spstats.pearsonr(df_ind["avg_ai"], df_ind["log_avg_vp"])
print(f"\nIndividual delegates (n={len(df_ind)}):")
print(f"  Pearson r(avg_ai, log_vp) = {r_ai:.3f}  p = {p_ai:.4f}")
print(f"  OLS R² = {r2:.3f}  beta_ai = {beta[1]:.3f}  beta_year = {beta[2]:.3f}")

# ── build vp time series for select delegates ─────────────────────────────────

HIGHLIGHT = [
    # (username, color, style)
    ("Griff",              "#2980B9", "-"),
    ("TreasureDAO",        "#1ABC9C", "-"),
    ("BlockworksResearch", "#27AE60", "-"),
    ("Curia",              "#E74C3C", "--"),
    ("Euphoria",           "#E67E22", "--"),
    ("TodayInDeFi",        "#C0392B", "--"),
]
HL_NAMES = {h[0] for h in HIGHLIGHT}

ts_rows = []
for _, row in df.iterrows():
    if row["username"] not in HL_NAMES:
        continue
    for pid, vp in row["vp_series"].items():
        dt = prop_dates.get(pid)
        if dt:
            ts_rows.append({"username": row["username"],
                            "date": pd.Timestamp(dt, unit="s"), "vp": vp})
ts_df = pd.DataFrame(ts_rows).sort_values("date") if ts_rows else pd.DataFrame(columns=["username", "date", "vp"])

# ── plot ──────────────────────────────────────────────────────────────────────

fig, axes = plt.subplots(2, 1, figsize=(7, 8))
fig.subplots_adjust(hspace=0.45)
ax_scatter, ax_ts = axes

# ── Panel A: scatter ──────────────────────────────────────────────────────────
HUMAN_C   = C_HUMAN
AI_C      = C_AI
PROTO_C   = COLORS["lightgray"]

def delegate_color(row):
    if row["is_protocol"]:
        return PROTO_C
    return AI_C if row["avg_ai"] > 0.20 else HUMAN_C

colors  = df.apply(delegate_color, axis=1)
sizes   = np.clip(df["n_posts"] * 4, 20, 400)

ax_scatter.scatter(df["avg_ai"], df["log_avg_vp"],
                   c=colors, s=sizes, alpha=0.75, linewidths=0.5,
                   edgecolors="white", zorder=3)

# Regression line (individual delegates only)
x_range = np.linspace(0, df_ind["avg_ai"].max() + 0.02, 100)
X_plot = np.column_stack([np.ones(100), x_range,
                           np.full(100, df_ind["first_year"].mean())])
y_plot = X_plot @ beta
ax_scatter.plot(x_range, y_plot, color="#2C3E50", linewidth=1.8,
                linestyle="--", zorder=4, label="OLS fit (individual delegates)")

# Annotate notable delegates
ANNOTATE = {"Curia", "Griff", "TreasureDAO", "BlockworksResearch",
            "Euphoria", "WintermuteGovernance", "Entropy", "Frisson",
            "TodayInDeFi", "karpatkey", "AlexLumley"}
for _, row in df.iterrows():
    if row["username"] in ANNOTATE:
        ax_scatter.annotate(
            row["username"],
            xy=(row["avg_ai"], row["log_avg_vp"]),
            xytext=(6, 0), textcoords="offset points",
            fontsize=7.5, color="#2C3E50", va="center"
        )

# Legend proxies
import matplotlib.patches as mpatches
human_patch  = mpatches.Patch(color=HUMAN_C,  label="Individual (low AI, <20%)")
ai_patch     = mpatches.Patch(color=AI_C,     label="Individual (high AI, ≥20%)")
proto_patch  = mpatches.Patch(color=PROTO_C,  label="Protocol / institutional")
ax_scatter.legend(handles=[human_patch, ai_patch, proto_patch],
                  fontsize=9, loc="upper right", framealpha=0.9)

sig = ("***" if p_ai < 0.001 else "**" if p_ai < 0.01
       else "*" if p_ai < 0.05 else "n.s.")
ax_scatter.text(0.03, 0.96,
    f"Individual delegates: r = {r_ai:.3f} {sig}  (n={len(df_ind)})",
    transform=ax_scatter.transAxes, fontsize=9, va="top",
    family="monospace",
    bbox=dict(fc="white", ec="#BDC3C7", pad=4, alpha=0.93))

ax_scatter.set_xlabel("Avg Pangram fraction_ai  (0 = fully human, 1 = fully AI)", fontsize=10)
ax_scatter.set_ylabel(r"$\log_{10}$(avg voting power, USD)", fontsize=10)
ax_scatter.set_title(
    "Panel A: AI Posting Intensity vs. Delegated Voting Power\n"
    "Bubble size = forum post count  |  Individual vs. protocol delegates separated",
    fontsize=10.5, fontweight="bold", loc="left"
)
ax_scatter.grid(linestyle="--", linewidth=0.4, alpha=0.4)

# ── Panel B: vp time series ───────────────────────────────────────────────────
for uname, color, ls in HIGHLIGHT:
    sub = ts_df[ts_df["username"] == uname].sort_values("date")
    if sub.empty:
        continue
    ai_val = df.loc[df["username"] == uname, "avg_ai"].values
    label_ai = f" (AI={ai_val[0]:.0%})" if len(ai_val) else ""
    ax_ts.semilogy(sub["date"], sub["vp"], color=color, linewidth=1.8,
                   linestyle=ls, alpha=0.9, label=f"{uname}{label_ai}")

ax_ts.set_ylabel("Voting power, USD (log scale)", fontsize=10)
ax_ts.set_xlabel("Proposal date", fontsize=10)
ax_ts.set_title(
    "Panel B: Voting power trajectory — selected delegates",
    fontsize=10, loc="left"
)
ax_ts.legend(fontsize=8.5, loc="upper left", ncol=2)
ax_ts.yaxis.set_major_formatter(mticker.FuncFormatter(
    lambda v, _: f"{v/1e6:.1f}M" if v >= 1e6 else f"{v/1e3:.0f}K"
))

for ax in axes:
    despine(ax)

fig.tight_layout()
aer_savefig(fig, OUT_PATH)

# ── print summary table ───────────────────────────────────────────────────────
print("\n=== Summary: High-AI vs Low-AI Individual Delegates ===")
print(f"{'Group':<12} {'n':>4} {'avg AI':>8} {'avg log(vp)':>12} {'avg vp':>14}")
for label, sub in [("High-AI (≥20%)", df_ind[df_ind["avg_ai"] >= 0.20]),
                    ("Low-AI (<20%)",  df_ind[df_ind["avg_ai"] <  0.20])]:
    if len(sub):
        print(f"{label:<12} {len(sub):>4} {sub['avg_ai'].mean():>8.3f} "
              f"{sub['log_avg_vp'].mean():>12.3f} "
              f"{sub['avg_vp'].mean():>14,.0f}")
