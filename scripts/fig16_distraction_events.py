#!/usr/bin/env python3
"""
fig16_distraction_events.py

Comprehensive distraction instrument analysis for Arbitrum DAO governance paper.

Theory (Hirshleifer et al.): exogenous attention shocks unrelated to proposal quality
reduce forum participation → tests whether the forum→governance channel is real.

Instruments:
  A. Airdrop claim deadlines (ZKsync+LayerZero Jun 2024, Starknet Feb 2024)
  B. Exchange hacks (Bybit Feb 2025, November 2023 cluster, Euler Mar 2023)
  C. Market crashes (BoJ Aug 2024, SVB Mar 2023)
  D. Regulatory/macro events (SEC Jun 2023, BTC ETF Jan 2024, halving Apr 2024)
  E. Concurrent DAO proposals (Hirshleifer "competing attention" analog)
  F. ETH volatility (expected wrong sign — DAO ≠ retail investors)

First stage:  log(human_posts + 1) ~ instrument
Reduced form: margin ~ instrument
"""

import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats as spstats

HERE     = os.path.dirname(os.path.abspath(__file__))
ROOT     = os.path.dirname(HERE)   # project root
DATA     = os.path.join(ROOT, "data")
OUT_DIR  = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT      = os.path.join(OUT_DIR, "fig16_distraction_events.png")
OUT2     = os.path.join(OUT_DIR, "fig16_distraction_events_scatter.png")

# ── 1. Load matched proposals ─────────────────────────────────────────────────
CSV_PATH = os.path.join(ROOT, "data", "matched_proposals.csv")
if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(
        f"Required file not found: {CSV_PATH}\n"
        "Run scripts/fig08_main_causal.py first to generate it."
    )

props = pd.read_csv(CSV_PATH, parse_dates=["created"])
props["log_human"] = np.log1p(props["human_posts"])
props["log_total"] = np.log1p(props["total_posts"])
props["ai_posts"]  = (props["total_posts"] - props["human_posts"]).clip(lower=0)
props["log_ai"]    = np.log1p(props["ai_posts"])
props = props.sort_values("created").reset_index(drop=True)

CLAUDE3 = pd.Timestamp("2024-03-04")
props["post_claude3"] = (props["created"] >= CLAUDE3).astype(int)

print(f"Loaded {len(props)} proposals  "
      f"({props['created'].min().date()} – {props['created'].max().date()})")
print(f"  Pre-Claude 3:  {(props['post_claude3']==0).sum()} proposals")
print(f"  Post-Claude 3: {(props['post_claude3']==1).sum()} proposals")

# ── 2. Distraction event catalog ──────────────────────────────────────────────
# (label, window_start, window_end, tier, category, description)
# tier 1 = strongest a priori instruments; tier 0 = AI shocks (main treatment, not instruments)
# window = dates during which an Arbitrum proposal discussion would be affected

EVENTS = [
    # ── AIRDROPS ────────────────────────────────────────────────────────────────
    ("airdrop_zksync_lz",
     "2024-06-13", "2024-06-22", 1, "airdrop",
     "ZKsync ($ZK Jun 17) + LayerZero ($ZRO Jun 20) claim cluster — ~$1B FDV"),

    ("airdrop_starknet",
     "2024-02-17", "2024-02-24", 1, "airdrop",
     "Starknet ($STRK) airdrop claim Feb 20 2024 — eligibility checking mania"),

    ("airdrop_arb",
     "2023-03-20", "2023-03-27", 2, "airdrop",
     "ARB token airdrop Mar 23 2023 — own-protocol, may excite rather than distract"),

    # ── EXCHANGE HACKS ──────────────────────────────────────────────────────────
    ("hack_bybit",
     "2025-02-19", "2025-02-26", 1, "hack",
     "Bybit hack $1.5B Feb 21 2025 — Lazarus Group, largest exchange hack ever"),

    ("hack_nov2023",
     "2023-11-08", "2023-11-26", 1, "hack",
     "Nov 2023 cluster: Poloniex Nov10, Binance DOJ Nov21, HTX Nov22, Kyber Nov23  "
     "[NOTE: overlaps QLR break Nov 25]"),

    ("hack_euler",
     "2023-03-11", "2023-03-17", 2, "hack",
     "Euler Finance hack $197M Mar 13 2023"),

    ("hack_mixin",
     "2023-09-21", "2023-09-27", 2, "hack",
     "Mixin Network hack $200M Sep 23 2023"),

    # ── MARKET CRASHES ──────────────────────────────────────────────────────────
    ("crash_boj",
     "2024-08-03", "2024-08-10", 1, "crash",
     "BoJ carry unwind crash Aug 5 2024: BTC/ETH -25% in 24h, global Black Monday"),

    ("crash_svb",
     "2023-03-08", "2023-03-15", 1, "crash",
     "SVB collapse + USDC depeg to $0.87, Mar 10-13 2023"),

    ("crash_ftx",
     "2022-11-07", "2022-11-14", 2, "crash",
     "FTX collapse Nov 8-11 2022 (pre-sample boundary)"),

    # ── REGULATORY / MACRO ──────────────────────────────────────────────────────
    ("sec_binance_cb",
     "2023-06-03", "2023-06-10", 1, "regulatory",
     "SEC sues Binance (Jun5) and Coinbase (Jun6) 2023 — named 13+ tokens as securities"),

    ("btc_etf_approval",
     "2024-01-08", "2024-01-15", 1, "regulatory",
     "Bitcoin spot ETF approved Jan 10-11 2024 — BlackRock/Fidelity launch, media saturation"),

    ("btc_halving",
     "2024-04-17", "2024-04-23", 2, "scheduled",
     "Bitcoin halving Apr 19-20 2024 — scheduled but dominates crypto media"),

    # ── AI SHOCKS (main treatment, flagged tier=0, excluded from instruments) ───
    ("ai_gpt4",      "2023-03-14", "2023-03-14", 0, "ai_shock", "GPT-4 release"),
    ("ai_gpt4turbo", "2023-11-06", "2023-11-06", 0, "ai_shock", "GPT-4 Turbo + plugins"),
    ("ai_claude3",   "2024-03-04", "2024-03-04", 0, "ai_shock", "Claude 3 release"),
    ("ai_gpt4o",     "2024-05-13", "2024-05-13", 0, "ai_shock", "GPT-4o release"),
    ("ai_deepseek",  "2025-01-20", "2025-01-20", 0, "ai_shock", "DeepSeek R1 release"),
]

events_df = pd.DataFrame(EVENTS, columns=["label","start","end","tier","category","description"])
events_df["start"] = pd.to_datetime(events_df["start"])
events_df["end"]   = pd.to_datetime(events_df["end"])

# ── 3. Tag proposals with event windows ──────────────────────────────────────
# Proposal active window: [created, created + DISCUSSION_DAYS]
# Treated if: event_window ∩ proposal_window ≠ ∅

DISCUSSION_DAYS = 10   # typical Snapshot proposal: 5-7 day vote + a few days discussion

def overlaps(prop_date, ev_start, ev_end, discussion_days=DISCUSSION_DAYS):
    prop_end = prop_date + pd.Timedelta(days=discussion_days)
    return (prop_date <= ev_end) and (prop_end >= ev_start)

for _, ev in events_df.iterrows():
    col = f"ev_{ev['label']}"
    props[col] = props["created"].apply(
        lambda d, s=ev["start"], e=ev["end"]: int(overlaps(d, s, e))
    )

print("\nEvent treatment counts:")
for _, ev in events_df.iterrows():
    col = f"ev_{ev['label']}"
    n = props[col].sum()
    print(f"  {'[T'+str(ev['tier'])+']':<5} {ev['label']:<25} n={n:>3}  {ev['description'][:60]}")

# ── 4. Concurrent DAO proposals instrument ───────────────────────────────────
print("\nBuilding concurrent DAO proposals instrument...")
with open(os.path.join(DATA, "other_dao_proposals.json")) as f:
    other_raw = json.load(f)

other_df = pd.DataFrame(other_raw)
other_df["created_dt"] = pd.to_datetime(other_df["created"], unit="s", utc=True).dt.tz_localize(None)
other_df["end_dt"]     = pd.to_datetime(other_df["end"],     unit="s", utc=True).dt.tz_localize(None)
other_df["space_id"]   = other_df["space"].apply(
    lambda x: x["id"] if isinstance(x, dict) else str(x)
)

print(f"  {len(other_df)} proposals from: {dict(other_df['space_id'].value_counts())}")

def count_concurrent(prop_date, discussion_days=DISCUSSION_DAYS):
    prop_end = prop_date + pd.Timedelta(days=discussion_days)
    mask = (other_df["created_dt"] <= prop_end) & (other_df["end_dt"] >= prop_date)
    return int(mask.sum())

props["concurrent_dao"] = props["created"].apply(count_concurrent)
print(f"  concurrent_dao: mean={props['concurrent_dao'].mean():.1f}  "
      f"median={props['concurrent_dao'].median():.0f}  "
      f"max={props['concurrent_dao'].max()}  "
      f"pct_zero={100*(props['concurrent_dao']==0).mean():.0f}%")

props["log_concurrent"] = np.log1p(props["concurrent_dao"])

# ── 5. ETH volatility instrument ─────────────────────────────────────────────
print("\nLoading ETH price data...")
with open(os.path.join(DATA, "eth_price_cache.json")) as f:
    eth_raw = json.load(f)

eth_df = pd.DataFrame([
    {"date": pd.Timestamp(k), **v} for k, v in eth_raw.items()
])
eth_df = eth_df.sort_values("date").reset_index(drop=True)
eth_df["log_ret"] = np.log(eth_df["close"] / eth_df["close"].shift(1))
eth_df["abs_ret"]  = eth_df["log_ret"].abs()
eth_df["vol_5d"]   = eth_df["abs_ret"].rolling(5,  min_periods=3).mean()
eth_df["vol_7d"]   = eth_df["abs_ret"].rolling(7,  min_periods=3).mean()
eth_df["vol_14d"]  = eth_df["abs_ret"].rolling(14, min_periods=5).mean()
eth_dict = {row.date.date(): row for row in eth_df.itertuples()}

def prop_avg_vol(prop_date, window_days=DISCUSSION_DAYS, col="vol_7d"):
    days = pd.date_range(prop_date, periods=window_days, freq="D")
    vals = [getattr(eth_dict[d.date()], col)
            for d in days if d.date() in eth_dict]
    return np.mean(vals) if vals else np.nan

props["eth_vol_7d"]  = props["created"].apply(lambda d: prop_avg_vol(d, col="vol_7d"))
props["eth_vol_14d"] = props["created"].apply(lambda d: prop_avg_vol(d, col="vol_14d"))

q75 = props["eth_vol_7d"].quantile(0.75)
props["high_vol"] = (props["eth_vol_7d"] > q75).astype(int)
print(f"  eth_vol_7d: mean={props['eth_vol_7d'].mean():.4f}  "
      f"q75={q75:.4f}  high_vol n={props['high_vol'].sum()}")

# ── 6. Composite instruments ──────────────────────────────────────────────────
tier1_cols = [f"ev_{ev['label']}" for _, ev in events_df.iterrows()
              if ev["tier"] == 1 and ev["category"] != "ai_shock"]
props["any_tier1"]    = (props[tier1_cols].sum(axis=1) > 0).astype(int)

airdrop_cols = [f"ev_{ev['label']}" for _, ev in events_df.iterrows()
                if ev["tier"] == 1 and ev["category"] == "airdrop"]
props["any_airdrop"]  = (props[airdrop_cols].sum(axis=1) > 0).astype(int)

hack_cols = [f"ev_{ev['label']}" for _, ev in events_df.iterrows()
             if ev["tier"] == 1 and ev["category"] == "hack"]
props["any_hack"]     = (props[hack_cols].sum(axis=1) > 0).astype(int)

crash_cols = [f"ev_{ev['label']}" for _, ev in events_df.iterrows()
              if ev["tier"] == 1 and ev["category"] == "crash"]
props["any_crash"]    = (props[crash_cols].sum(axis=1) > 0).astype(int)

print(f"\nComposite treatment counts:")
print(f"  any_tier1:   n={props['any_tier1'].sum()}  ({100*props['any_tier1'].mean():.0f}%)")
print(f"  any_airdrop: n={props['any_airdrop'].sum()}")
print(f"  any_hack:    n={props['any_hack'].sum()}")
print(f"  any_crash:   n={props['any_crash'].sum()}")

# ── 7. OLS helper ─────────────────────────────────────────────────────────────

def ols_1d(x_series, y_series, label_x="x", label_y="y"):
    mask = ~(x_series.isna() | y_series.isna())
    x = x_series[mask].values.astype(float)
    y = y_series[mask].values.astype(float)
    n = len(x)
    if n < 5 or np.std(x) == 0:
        return dict(n=n, beta1=np.nan, se1=np.nan, t1=np.nan, p1=np.nan,
                    F=np.nan, r2=np.nan, ci_lo=np.nan, ci_hi=np.nan)
    X = np.column_stack([np.ones(n), x])
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    s2    = resid @ resid / (n - 2)
    cov   = s2 * np.linalg.inv(X.T @ X)
    se    = np.sqrt(np.diag(cov))
    t     = beta / se
    p     = 2 * (1 - spstats.t.cdf(np.abs(t), df=n - 2))
    ss_tot = np.sum((y - y.mean())**2)
    r2 = 1 - (resid @ resid) / ss_tot if ss_tot > 0 else 0.0
    t_crit = spstats.t.ppf(0.975, df=n - 2)
    return dict(n=n, beta1=beta[1], se1=se[1], t1=t[1], p1=p[1],
                F=t[1]**2, r2=r2,
                ci_lo=beta[1] - t_crit*se[1],
                ci_hi=beta[1] + t_crit*se[1])

# ── 8. Define instrument battery ──────────────────────────────────────────────
# (display_name, column, kind, expected_fs_sign, expected_rf_sign, note)

INSTRUMENTS = [
    # Airdrops
    ("ZKsync+LayerZero airdrop",  "ev_airdrop_zksync_lz", "binary",     -1, +1, "BEST"),
    ("Starknet airdrop",          "ev_airdrop_starknet",  "binary",     -1, +1, ""),
    ("ARB airdrop (own token)",   "ev_airdrop_arb",       "binary",      0, +1, "neg.ctrl"),
    ("Any airdrop (Tier 1)",      "any_airdrop",          "binary",     -1, +1, "composite"),
    # Hacks
    ("Bybit hack ($1.5B)",        "ev_hack_bybit",        "binary",     -1, +1, "BEST"),
    ("Nov 2023 hack cluster",     "ev_hack_nov2023",      "binary",     -1, +1, "⚠ QLR"),
    ("Euler hack ($197M)",        "ev_hack_euler",        "binary",     -1, +1, ""),
    ("Any hack (Tier 1)",         "any_hack",             "binary",     -1, +1, "composite"),
    # Crashes
    ("BoJ crash Aug 2024",        "ev_crash_boj",         "binary",     -1, +1, "BEST"),
    ("SVB/USDC depeg Mar 2023",   "ev_crash_svb",         "binary",     -1, +1, ""),
    ("Any crash (Tier 1)",        "any_crash",            "binary",     -1, +1, "composite"),
    # Regulatory/macro
    ("SEC vs Binance+CB",         "ev_sec_binance_cb",    "binary",     -1, +1, ""),
    ("Bitcoin ETF approval",      "ev_btc_etf_approval",  "binary",     -1, +1, ""),
    ("Bitcoin halving",           "ev_btc_halving",       "binary",      0,  0, "scheduled"),
    # Composite
    ("Any Tier 1 distraction",    "any_tier1",            "binary",     -1, +1, "composite"),
    # Hirshleifer concurrent
    ("Concurrent DAO proposals",  "log_concurrent",       "continuous", -1, +1, "Hirshleifer"),
    # ETH volatility (control — expected wrong sign)
    ("High ETH vol (q75)",        "high_vol",             "binary",     -1,  0, "wrong sign"),
    ("ETH vol 7d (continuous)",   "eth_vol_7d",           "continuous", -1,  0, "wrong sign"),
]

# ── 9. Run regressions ─────────────────────────────────────────────────────────

print("\n" + "="*90)
print("FIRST STAGE: log(human_posts + 1) ~ instrument")
print("="*90)
hdr = f"  {'Instrument':<32} {'nT':>4} {'β_fs':>8} {'se':>7} {'t':>6} {'p':>7} {'F':>7} {'✓?':>6} {'note'}"
print(hdr)
print("-"*90)

fs_rows = []
for (disp, col, kind, exp_fs, exp_rf, note) in INSTRUMENTS:
    n_treat = int(props[col].sum()) if kind == "binary" else "—"
    res = ols_1d(props[col], props["log_human"])
    sign = ("✓" if (exp_fs == -1 and res["beta1"] < 0) or
                   (exp_fs ==  1 and res["beta1"] > 0) or
                   (exp_fs ==  0) else "✗")
    star = ("***" if not np.isnan(res["p1"]) and res["p1"] < 0.01
            else "**" if not np.isnan(res["p1"]) and res["p1"] < 0.05
            else "*"  if not np.isnan(res["p1"]) and res["p1"] < 0.10
            else "")
    print(f"  {disp:<32} {str(n_treat):>4} {res['beta1']:>8.3f} {res['se1']:>7.3f} "
          f"{res['t1']:>6.2f} {res['p1']:>7.4f} {res['F']:>7.2f} {sign+star:>6}  {note}")
    fs_rows.append(dict(disp=disp, col=col, kind=kind, exp_fs=exp_fs, note=note, **res))

fs_df = pd.DataFrame(fs_rows)

print("\n" + "="*90)
print("REDUCED FORM: margin ~ instrument")
print("="*90)
print(hdr)
print("-"*90)

rf_rows = []
for (disp, col, kind, exp_fs, exp_rf, note) in INSTRUMENTS:
    n_treat = int(props[col].sum()) if kind == "binary" else "—"
    res = ols_1d(props[col], props["margin"])
    sign = ("✓" if (exp_rf == +1 and res["beta1"] > 0) or
                   (exp_rf == -1 and res["beta1"] < 0) or
                   (exp_rf ==  0) else "✗")
    star = ("***" if not np.isnan(res["p1"]) and res["p1"] < 0.01
            else "**" if not np.isnan(res["p1"]) and res["p1"] < 0.05
            else "*"  if not np.isnan(res["p1"]) and res["p1"] < 0.10
            else "")
    print(f"  {disp:<32} {str(n_treat):>4} {res['beta1']:>8.3f} {res['se1']:>7.3f} "
          f"{res['t1']:>6.2f} {res['p1']:>7.4f} {res['F']:>7.2f} {sign+star:>6}  {note}")
    rf_rows.append(dict(disp=disp, col=col, kind=kind, note=note, **res))

rf_df = pd.DataFrame(rf_rows)

# ── 10. Group means for binary instruments ─────────────────────────────────────
print("\n" + "="*90)
print("GROUP MEANS: treated vs control")
print("="*90)

gm_rows = []
for (disp, col, kind, exp_fs, exp_rf, note) in INSTRUMENTS:
    if kind != "binary":
        continue
    ctrl  = props[props[col] == 0]
    treat = props[props[col] == 1]
    if len(treat) < 2:
        continue
    cp  = ctrl["human_posts"].mean()
    tp  = treat["human_posts"].mean()
    cm  = ctrl["margin"].mean()
    tm  = treat["margin"].mean()
    delta_pct = 100 * (tp - cp) / cp if cp > 0 else np.nan
    _, p_posts = spstats.ttest_ind(ctrl["human_posts"], treat["human_posts"])
    gm_rows.append(dict(disp=disp, col=col, n_ctrl=len(ctrl), n_treat=len(treat),
                        ctrl_posts=cp, treat_posts=tp, delta_pct=delta_pct,
                        ctrl_margin=cm, treat_margin=tm, p_posts=p_posts))

gm_df = pd.DataFrame(gm_rows)

# ── 11. IV estimate for best instrument (airdrop cluster) ─────────────────────
print("\n" + "="*90)
print("IV ESTIMATE (Wald): airdrop_zksync_lz → log_human → margin")
print("="*90)
best_col = "ev_airdrop_zksync_lz"
fs_best  = fs_df[fs_df["col"] == best_col].iloc[0]
rf_best  = rf_df[rf_df["col"] == best_col].iloc[0]
if fs_best["beta1"] != 0 and not np.isnan(fs_best["beta1"]):
    iv_est = rf_best["beta1"] / fs_best["beta1"]
    print(f"  First stage  β_fs = {fs_best['beta1']:.3f} (t={fs_best['t1']:.2f}, F={fs_best['F']:.2f})")
    print(f"  Reduced form β_rf = {rf_best['beta1']:.3f} (t={rf_best['t1']:.2f})")
    print(f"  IV estimate  β_iv = β_rf / β_fs = {iv_est:.3f}")

# ── 12. Pre-Claude 3 subsample ────────────────────────────────────────────────
print("\n" + "="*90)
print("PRE-CLAUDE 3 SUBSAMPLE (the relevant identification window)")
print("="*90)
pre = props[props["post_claude3"] == 0].copy()
print(f"  N = {len(pre)} proposals")
for (disp, col, kind, exp_fs, exp_rf, note) in INSTRUMENTS[:8]:
    fsr = ols_1d(pre[col], pre["log_human"])
    rfr = ols_1d(pre[col], pre["margin"])
    print(f"  {disp:<32} {fsr['beta1']:>8.3f} {fsr['t1']:>6.2f} "
          f"{rfr['beta1']:>8.3f} {rfr['t1']:>6.2f}")

# ── 13. Figures ───────────────────────────────────────────────────────────────

C_POS  = "#27AE60"   # green — correct sign
C_NEG  = "#E74C3C"   # red — wrong sign
C_NULL = "#95A5A6"   # grey — composite or expected null
C_BEST = "#2980B9"   # blue — highlighted best instruments

# ── Figure 1: forest plot (first stage) + group means bar ───────────────────
fig, axes = plt.subplots(1, 2, figsize=(16, 8))
fig.subplots_adjust(wspace=0.35)
ax_forest, ax_bar = axes

# Forest plot: only non-composite, non-ai_shock instruments
plot_rows = fs_df[~fs_df["note"].isin(["composite", "wrong sign"])].copy()
plot_rows = plot_rows.sort_values("t1")  # ascending so worst at bottom

y_pos = np.arange(len(plot_rows))
colors_f = []
for _, row in plot_rows.iterrows():
    if row["note"] == "BEST":
        colors_f.append(C_BEST)
    elif row["beta1"] < 0:
        colors_f.append(C_POS)
    elif row["note"] == "wrong sign":
        colors_f.append(C_NEG)
    else:
        colors_f.append(C_NULL)

for i, (_, row) in enumerate(plot_rows.iterrows()):
    c = colors_f[i]
    if np.isnan(row["beta1"]):
        continue
    xerr_lo = row["beta1"] - row["ci_lo"]
    xerr_hi = row["ci_hi"] - row["beta1"]
    ax_forest.errorbar(
        row["beta1"], y_pos[i],
        xerr=[[max(0, xerr_lo)], [max(0, xerr_hi)]],
        fmt="o", markersize=5, linewidth=1.4,
        color=c, ecolor=c,
        markerfacecolor=c, markeredgecolor=c
    )

ax_forest.axvline(0, color="#2C3E50", linewidth=0.9, linestyle="--")
ax_forest.set_yticks(y_pos)
ax_forest.set_yticklabels(plot_rows["disp"], fontsize=8.5)
ax_forest.set_xlabel("β (first stage: log(human posts + 1) ~ instrument)", fontsize=9)
ax_forest.set_title(
    "Panel A: First-Stage Estimates\n"
    "Each instrument → log(human posts). Negative = fewer posts as expected.",
    fontsize=9.5, fontweight="bold", loc="left"
)
ax_forest.grid(axis="x", linestyle="--", linewidth=0.4, alpha=0.5)

legend_handles = [
    mpatches.Patch(color=C_BEST, label="Highlighted (best a priori)"),
    mpatches.Patch(color=C_POS,  label="Correct sign (−)"),
    mpatches.Patch(color=C_NULL, label="Null / ambiguous sign"),
]
ax_forest.legend(handles=legend_handles, fontsize=8, loc="lower right")

# Bar chart: group means (human posts) for select instruments
gm_plot = gm_df[gm_df["disp"].isin([
    "ZKsync+LayerZero airdrop", "Bybit hack ($1.5B)", "BoJ crash Aug 2024",
    "SVB/USDC depeg Mar 2023", "SEC vs Binance+CB", "Bitcoin ETF approval",
    "ARB airdrop (own token)", "Nov 2023 hack cluster",
])].copy()

x_idx = np.arange(len(gm_plot))
width = 0.35
bars_ctrl  = ax_bar.bar(x_idx - width/2, gm_plot["ctrl_posts"],  width,
                         color="#BDC3C7", label="Non-distracted proposals")
bars_treat = ax_bar.bar(x_idx + width/2, gm_plot["treat_posts"], width,
                         color=C_BEST, alpha=0.85, label="Distracted proposals")

for i, (_, row) in enumerate(gm_plot.iterrows()):
    star = ("***" if row["p_posts"] < 0.01 else "**" if row["p_posts"] < 0.05
            else "*" if row["p_posts"] < 0.10 else "")
    top = max(row["ctrl_posts"], row["treat_posts"]) + 2
    if star:
        ax_bar.text(i, top + 1, star, ha="center", va="bottom", fontsize=9,
                    color="#2C3E50")

ax_bar.set_xticks(x_idx)
ax_bar.set_xticklabels(gm_plot["disp"], rotation=30, ha="right", fontsize=8)
ax_bar.set_ylabel("Avg. human posts in proposal thread", fontsize=9)
ax_bar.set_title(
    "Panel B: Human Posts — Distracted vs Control Proposals\n"
    "* p<0.10, ** p<0.05, *** p<0.01 (t-test)",
    fontsize=9.5, fontweight="bold", loc="left"
)
ax_bar.legend(fontsize=8.5)
ax_bar.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.4)

fig.suptitle(
    "Figure 16: Distraction Instrument First Stage — Arbitrum DAO Governance\n"
    f"N = {len(props)} proposals  |  Outcome: log(human posts in proposal thread)",
    fontsize=11, fontweight="bold", y=1.01
)
fig.savefig(OUT, dpi=180, bbox_inches="tight")
print(f"\nSaved → {OUT}")
plt.close()

# ── Figure 2: scatter plots for best instruments ──────────────────────────────
fig2, axes2 = plt.subplots(2, 2, figsize=(14, 10))
fig2.subplots_adjust(hspace=0.45, wspace=0.35)

SCATTER_SPECS = [
    ("ev_airdrop_zksync_lz", "ZKsync+LayerZero airdrop (binary)",  "binary",
     "log_human",  "log(human posts + 1)"),
    ("log_concurrent",        "Concurrent DAO proposals (log+1)",   "continuous",
     "log_human",  "log(human posts + 1)"),
    ("ev_airdrop_zksync_lz", "ZKsync+LayerZero airdrop (binary)",  "binary",
     "margin",     "Margin of victory"),
    ("log_concurrent",        "Concurrent DAO proposals (log+1)",   "continuous",
     "margin",     "Margin of victory"),
]

for ax, (xcol, xlabel, kind, ycol, ylabel) in zip(axes2.flat, SCATTER_SPECS):
    x = props[xcol]
    y = props[ycol]
    mask = ~(x.isna() | y.isna())
    xv, yv = x[mask].values.astype(float), y[mask].values.astype(float)

    c = np.where(props["post_claude3"][mask] == 1, C_NEG, C_BEST)
    ax.scatter(xv, yv, c=c, alpha=0.4, s=20, linewidths=0)

    if np.std(xv) > 0:
        m, b = np.polyfit(xv, yv, 1)
        xfit = np.linspace(xv.min(), xv.max(), 100)
        ax.plot(xfit, m*xfit + b, color="#2C3E50", linewidth=1.5, linestyle="--")
        res = ols_1d(pd.Series(xv), pd.Series(yv))
        star = ("***" if res["p1"] < 0.01 else "**" if res["p1"] < 0.05
                else "*" if res["p1"] < 0.10 else "n.s.")
        ax.text(0.97, 0.97,
                f"β = {res['beta1']:.3f}  t = {res['t1']:.2f} {star}\n"
                f"N = {res['n']}",
                transform=ax.transAxes, fontsize=8, va="top", ha="right",
                family="monospace",
                bbox=dict(fc="white", ec="#BDC3C7", pad=3, alpha=0.9))

    ax.set_xlabel(xlabel, fontsize=9)
    ax.set_ylabel(ylabel, fontsize=9)
    ax.set_title(f"{ylabel} ~ {xlabel[:35]}", fontsize=9.5, fontweight="bold", loc="left")
    ax.grid(linestyle="--", linewidth=0.4, alpha=0.4)

    leg = [mpatches.Patch(color=C_BEST, label="Pre-Claude 3"),
           mpatches.Patch(color=C_NEG,  label="Post-Claude 3")]
    ax.legend(handles=leg, fontsize=8, loc="upper left")

fig2.suptitle(
    "Figure 16b: Distraction Instruments vs. Forum Activity and Governance Outcomes\n"
    "First stage (top row) and reduced form (bottom row) — full sample",
    fontsize=11, fontweight="bold", y=1.01
)
fig2.savefig(OUT2, dpi=180, bbox_inches="tight")
print(f"Saved → {OUT2}")
plt.close()

print("\nDone.")
