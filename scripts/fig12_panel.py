#!/usr/bin/env python3
"""
Panel regression: does AI posting intensity predict delegation changes?

Dataset: delegate × proposal panel
  - Y: Δlog(vp) from proposal t-1 to proposal t  (delegation flow)
  - X: fraction_ai of delegate's posts in the 30 days before proposal t
  - Controls: log(vp_{t-1}), proposal order (time trend), delegate FE

Also produces:
  - Rolling: does the ai→delegation relationship strengthen or weaken over time?
  - Scatter: cumulative delegation change vs avg_ai (AI early adopters vs late)

Needs:
  - data/arbitrum.db  (posts, post_ai_scores, delegate_wallet_map)
  - data/figure5_votes_cache.json
  - data/snapshot_proposal_dates.json
"""

import os, json
import duckdb
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import sys as _sys
_sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, C_TOTAL, C_SHOCK, savefig as aer_savefig
apply_aer_style()
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from scipy import stats as spstats

HERE         = os.path.dirname(os.path.abspath(__file__))
ROOT         = os.path.dirname(HERE)   # project root
DB_PATH      = os.path.join(ROOT, "data", "arbitrum.db")
VOTES_CACHE  = os.path.join(ROOT, "data", "figure5_votes_cache.json")
DATES_CACHE  = os.path.join(ROOT, "data", "snapshot_proposal_dates.json")
OUT_DIR      = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH     = os.path.join(OUT_DIR, "fig12_panel.png")

AI_WINDOW_DAYS = 30   # look-back window for computing delegate's AI fraction


# ── load ──────────────────────────────────────────────────────────────────────

print("Loading data...")
con = duckdb.connect(DB_PATH, read_only=True)

wallet_map = con.execute(
    "SELECT forum_username, wallet_address FROM delegate_wallet_map "
    "WHERE wallet_address IS NOT NULL"
).fetchall()
username_to_wallet = {u: w.lower() for u, w in wallet_map}
wallet_to_username = {w.lower(): u for u, w in wallet_map}

# Per-post AI scores with timestamps
post_scores = con.execute("""
    SELECT p.username, p.created_at, s.fraction_ai
    FROM posts p
    JOIN post_ai_scores s ON p.id = s.post_id
    WHERE s.fraction_ai IS NOT NULL
      AND s.headline NOT LIKE 'error:%'
      AND s.headline != 'too_short'
""").fetchall()
con.close()

posts_df = pd.DataFrame(post_scores, columns=["username", "created_at", "fraction_ai"])
posts_df["created_at"] = pd.to_datetime(posts_df["created_at"], utc=True).dt.tz_localize(None)

# Snapshot votes: proposal_id → [{voter, vp}]
with open(VOTES_CACHE) as f:
    votes_raw = json.load(f)

with open(DATES_CACHE) as f:
    snap_dates = json.load(f)

prop_order = sorted(snap_dates.items(), key=lambda x: x[1])   # (pid, unix_ts) sorted
prop_df = pd.DataFrame(prop_order, columns=["prop_id", "unix_ts"])
prop_df["date"] = pd.to_datetime(prop_df["unix_ts"], unit="s")
prop_df = prop_df.sort_values("date").reset_index(drop=True)
prop_df["prop_index"] = prop_df.index
print(f"  {len(prop_df)} proposals  |  "
      f"{prop_df['date'].min().date()} – {prop_df['date'].max().date()}")

# Build vp matrix: (username, prop_id) → vp
vp_records = []
for pid, voter_list in votes_raw.items():
    for v in voter_list:
        uname = wallet_to_username.get(v["voter"].lower())
        if uname:
            vp_records.append({"username": uname, "prop_id": pid, "vp": v["vp"]})

vp_df = pd.DataFrame(vp_records)
vp_df = vp_df.merge(prop_df[["prop_id", "date", "prop_index"]], on="prop_id")
print(f"  {len(vp_df)} delegate-proposal vp observations  |  "
      f"{vp_df['username'].nunique()} delegates")


# ── compute rolling fraction_ai per delegate per proposal ─────────────────────

print("\nComputing rolling AI fraction per delegate...")

# Index posts by (username, date)
posts_idx = posts_df.sort_values("created_at")

def ai_fraction_before(username: str, cutoff: pd.Timestamp, window_days: int) -> float | None:
    """Mean fraction_ai of username's posts in [cutoff - window, cutoff)."""
    start = cutoff - pd.Timedelta(days=window_days)
    mask = (
        (posts_idx["username"] == username) &
        (posts_idx["created_at"] >= start) &
        (posts_idx["created_at"] <  cutoff)
    )
    sub = posts_idx.loc[mask, "fraction_ai"]
    return sub.mean() if len(sub) >= 1 else np.nan


# For each (username, proposal), look up their rolling AI fraction
# Vectorise by pre-grouping posts per user into sorted arrays
user_posts = {}
for uname, grp in posts_idx.groupby("username"):
    user_posts[uname] = grp[["created_at", "fraction_ai"]].sort_values("created_at")

def fast_ai_stats(username, cutoff, window_days):
    """Return (avg_fraction_ai, post_count) for username in [cutoff-window, cutoff)."""
    df = user_posts.get(username)
    if df is None:
        return np.nan, 0
    start = cutoff - pd.Timedelta(days=window_days)
    mask = (df["created_at"] >= start) & (df["created_at"] < cutoff)
    sub = df.loc[mask]
    if len(sub) == 0:
        return np.nan, 0
    return sub["fraction_ai"].mean(), len(sub)

print("  Building per-delegate rolling AI fractions and post counts (this takes ~30s)...")
stats = [fast_ai_stats(row.username, row.date, AI_WINDOW_DAYS)
         for row in vp_df.itertuples()]
vp_df["ai_frac_30d"]  = [s[0] for s in stats]
vp_df["posts_30d"]    = [s[1] for s in stats]
vp_df["log_posts_30d"] = np.log1p(vp_df["posts_30d"])

# Sort and compute Δlog(vp) within each delegate
vp_df = vp_df.sort_values(["username", "prop_index"])
vp_df["log_vp"] = np.log10(vp_df["vp"].clip(lower=1))
vp_df["log_vp_prev"] = vp_df.groupby("username")["log_vp"].shift(1)
vp_df["delta_log_vp"] = vp_df["log_vp"] - vp_df["log_vp_prev"]

panel = vp_df.dropna(subset=["delta_log_vp", "ai_frac_30d", "log_posts_30d"]).copy()
print(f"  Panel rows (delegate × proposal with AI data): {len(panel)}")
print(f"  Delegates represented: {panel['username'].nunique()}")


# ── panel regression ──────────────────────────────────────────────────────────

def run_within_ols(panel, y_col, x_cols, label):
    """Demean by delegate and run OLS. Returns (beta, se, t_stats, r2, n)."""
    all_cols = [y_col] + x_cols
    for col in all_cols:
        gm = panel.groupby("username")[col].transform("mean")
        panel[f"{col}_dm"] = panel[col] - gm

    y = panel[f"{y_col}_dm"].values
    X = np.column_stack([panel[f"{c}_dm"].values for c in x_cols])
    X = np.column_stack([np.ones(len(X)), X])

    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    y_hat = X @ beta
    ss_res = np.sum((y - y_hat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r2 = 1 - ss_res / ss_tot

    resid = y - y_hat
    n, k = X.shape
    sigma2 = np.sum(resid**2) / (n - k)
    se = np.sqrt(np.diag(sigma2 * np.linalg.inv(X.T @ X)))
    t_stats = beta / se

    print(f"\n=== {label} (N={n}, {panel['username'].nunique()} delegates, within R²={r2:.4f}) ===")
    print(f"  {'Variable':<22} {'beta':>8} {'se':>8} {'t':>8}")
    labels = ["(intercept)"] + x_cols
    for i, lbl in enumerate(labels):
        sig = ("***" if abs(t_stats[i]) > 3.29 else "**" if abs(t_stats[i]) > 2.58
               else "*" if abs(t_stats[i]) > 1.96 else "")
        print(f"  {lbl:<22} {beta[i]:>8.4f} {se[i]:>8.4f} {t_stats[i]:>7.2f} {sig}")
    return beta, se, t_stats, r2, n

# Model 1: without posting volume control
beta1, se1, t1, r2_1, n1 = run_within_ols(
    panel.copy(),
    "delta_log_vp",
    ["ai_frac_30d", "log_vp_prev", "prop_index"],
    "Model 1: Δlog(vp) ~ ai_frac_30d + log_vp_prev + prop_index"
)

# Model 2: with log posting volume — key test: does AI coefficient survive?
beta2, se2, t2, r2_2, n2 = run_within_ols(
    panel.copy(),
    "delta_log_vp",
    ["ai_frac_30d", "log_posts_30d", "log_vp_prev", "prop_index"],
    "Model 2: + log(posts_30d) control  [key: does AI coef survive?]"
)

r_raw, p_raw = spstats.pearsonr(panel["ai_frac_30d"], panel["delta_log_vp"])
r_posts, p_posts = spstats.pearsonr(panel["log_posts_30d"], panel["delta_log_vp"])
print(f"\n  Raw r(ai_frac_30d, Δlog_vp)    = {r_raw:.4f}  p = {p_raw:.4f}")
print(f"  Raw r(log_posts_30d, Δlog_vp)  = {r_posts:.4f}  p = {p_posts:.4f}")

# Use Model 1 coefs for the figure annotation
beta, t_stats, n = beta1, t1, n1


# ── rolling: does the ai→vp relationship change over time? ────────────────────

# Split by proposal date quartiles
panel["date"] = pd.to_datetime(
    panel["prop_id"].map(snap_dates.get) * 1e9  # ns
)
panel = panel.sort_values("date")

# Rolling 50-obs window correlation
min_w = 50
roll_dates = []
roll_r = []
for i in range(min_w, len(panel)):
    sub = panel.iloc[i - min_w:i]
    if sub["ai_frac_30d"].std() > 0 and sub["delta_log_vp"].std() > 0:
        r, _ = spstats.pearsonr(sub["ai_frac_30d"], sub["delta_log_vp"])
        roll_r.append(r)
        roll_dates.append(sub["date"].iloc[-1])

print(f"\n  Rolling correlation computed over {len(roll_r)} windows")


# ── plot ──────────────────────────────────────────────────────────────────────

fig, axes = plt.subplots(2, 1, figsize=(12, 10))
fig.subplots_adjust(hspace=0.45)
ax_panel, ax_roll = axes

HUMAN_C = "#2980B9"
AI_C    = "#E74C3C"
CORR_C  = "#2C3E50"

# Panel A: scatter Δlog(vp) vs ai_frac_30d (sample of points, coloured by delegate avg_ai)
delegate_avg_ai = panel.groupby("username")["ai_frac_30d"].mean()
panel["delegate_avg_ai"] = panel["username"].map(delegate_avg_ai)
colors = panel["delegate_avg_ai"].apply(lambda x: AI_C if x > 0.20 else HUMAN_C)

sample = panel.sample(min(3000, len(panel)), random_state=42)
ax_panel.scatter(sample["ai_frac_30d"], sample["delta_log_vp"],
                 c=colors.loc[sample.index], alpha=0.15, s=8, linewidths=0)

# OLS line (pooled, no FE — for visual)
xr = np.linspace(0, panel["ai_frac_30d"].max(), 100)
slope_raw = np.polyfit(panel["ai_frac_30d"], panel["delta_log_vp"], 1)
ax_panel.plot(xr, np.polyval(slope_raw, xr),
              color=CORR_C, linewidth=2, linestyle="--", label="Pooled OLS")
ax_panel.axhline(0, color="#95A5A6", linewidth=0.8)

sig_str = ("***" if abs(t_stats[1]) > 3.29 else "**" if abs(t_stats[1]) > 2.58
           else "*" if abs(t_stats[1]) > 1.96 else "n.s.")
ax_panel.text(0.97, 0.97,
    f"Within-FE: β(ai_frac) = {beta[1]:.3f}  t = {t_stats[1]:.2f} {sig_str}\n"
    f"Raw r = {r_raw:.3f}  |  N = {n} obs  |  {panel['username'].nunique()} delegates",
    transform=ax_panel.transAxes, fontsize=8.5, va="top", ha="right",
    family="monospace",
    bbox=dict(fc="white", ec="#BDC3C7", pad=4, alpha=0.93))

import matplotlib.patches as mpatches
ax_panel.legend(handles=[
    mpatches.Patch(color=HUMAN_C, label="Delegate avg AI < 20%"),
    mpatches.Patch(color=AI_C,    label="Delegate avg AI ≥ 20%"),
], fontsize=9, loc="upper left")

ax_panel.set_xlabel("Delegate's fraction_ai in prior 30 days", fontsize=10)
ax_panel.set_ylabel("Δ log₁₀(voting power)", fontsize=10)
ax_panel.set_title(
    "Panel A: Does AI Posting Predict Delegation Changes?\n"
    "Each point = one delegate × proposal  |  Y = log-change in vp from previous proposal",
    fontsize=10.5, fontweight="bold", loc="left"
)
ax_panel.grid(linestyle="--", linewidth=0.4, alpha=0.4)

# Panel B: rolling correlation over time
ax_roll.plot(roll_dates, roll_r, color=CORR_C, linewidth=2)
ax_roll.fill_between(roll_dates, 0, roll_r,
                     where=[r > 0 for r in roll_r], alpha=0.12, color=CORR_C)
ax_roll.fill_between(roll_dates, 0, roll_r,
                     where=[r < 0 for r in roll_r], alpha=0.12, color=AI_C)
ax_roll.axhline(0, color="#95A5A6", linewidth=0.8)

# Mark AI shock dates
for dt_str, label in [("2023-03-14", "GPT-4"), ("2024-03-04", "Claude 3"),
                       ("2024-05-13", "GPT-4o"), ("2025-01-20", "DeepSeek R1")]:
    dt = pd.Timestamp(dt_str)
    if dt >= pd.Timestamp(roll_dates[0]) if roll_dates else False:
        ax_roll.axvline(dt, color="#7F8C8D", linewidth=1.2, linestyle="--", alpha=0.65)
        ax_roll.text(dt, ax_roll.get_ylim()[1] * 0.9 if ax_roll.get_ylim()[1] else 0.5,
                     label, rotation=90, fontsize=7.5, color="#7F8C8D", va="top")

ax_roll.set_ylabel(f"r(ai_frac_30d, Δlog_vp)  [rolling {min_w}-obs window]", fontsize=10)
ax_roll.set_xlabel("Proposal date", fontsize=10)
ax_roll.set_title(
    "Panel B: Rolling Correlation — AI Posting Intensity vs. Delegation Change\n"
    "Does the ai→delegation relationship strengthen after major AI releases?",
    fontsize=10.5, fontweight="bold", loc="left"
)
ax_roll.grid(linestyle="--", linewidth=0.4, alpha=0.4)

fig.suptitle(
    "Figure 12: Panel Regression — AI Posting and Delegation Flows in Arbitrum DAO\n"
    f"N = {n} delegate × proposal observations  |  {panel['username'].nunique()} delegates",
    fontsize=11.5, fontweight="bold", y=1.01
)
fig.savefig(OUT_PATH, dpi=180, bbox_inches="tight")
print(f"\nSaved → {OUT_PATH}")
