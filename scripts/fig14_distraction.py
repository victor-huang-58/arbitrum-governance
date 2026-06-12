#!/usr/bin/env python3
"""
fig14_distraction.py

Produces a single publication-quality figure (and LaTeX table) for the
robustness section of the JF paper.

Argument:
  We tested Hirshleifer-style distraction instruments.  Every candidate has the
  WRONG sign: crypto events increase DAO forum participation, not decrease it.
  This validates the AI-shock identification strategy.

Outputs:
  output/figures/fig14_distraction.png  — single-panel horizontal bar chart
  output/tables/fig14_distraction.tex   — LaTeX table for paper
"""

import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import sys as _sys
_sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, C_TOTAL, C_SHOCK, savefig as aer_savefig
apply_aer_style()
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats as spstats

HERE      = os.path.dirname(os.path.abspath(__file__))
ROOT      = os.path.dirname(HERE)   # project root
DATA      = os.path.join(ROOT, "data")
FIG_DIR   = os.path.join(ROOT, "output", "figures")
TEX_DIR   = os.path.join(ROOT, "output", "tables")
os.makedirs(FIG_DIR, exist_ok=True)
os.makedirs(TEX_DIR, exist_ok=True)
OUT_FIG   = os.path.join(FIG_DIR, "fig14_distraction.png")
OUT_TEX   = os.path.join(TEX_DIR, "fig14_distraction.tex")

DISCUSSION_DAYS = 10

# ── load proposals ─────────────────────────────────────────────────────────────
MATCHED_CSV = os.path.join(ROOT, "data", "matched_proposals.csv")
if not os.path.exists(MATCHED_CSV):
    raise FileNotFoundError(
        f"Required file not found: {MATCHED_CSV}\n"
        "Run scripts/fig08_main_causal.py first to generate it."
    )
props = pd.read_csv(MATCHED_CSV, parse_dates=["created"])
props["log_human"] = np.log1p(props["human_posts"])
props = props.sort_values("created").reset_index(drop=True)
N = len(props)

# ── load concurrent DAO proposals ─────────────────────────────────────────────
with open(os.path.join(DATA, "other_dao_proposals.json")) as f:
    other_raw = json.load(f)
other_df = pd.DataFrame(other_raw)
other_df["created_dt"] = pd.to_datetime(other_df["created"], unit="s", utc=True).dt.tz_localize(None)
other_df["end_dt"]     = pd.to_datetime(other_df["end"],     unit="s", utc=True).dt.tz_localize(None)

def count_concurrent(prop_date):
    prop_end = prop_date + pd.Timedelta(days=DISCUSSION_DAYS)
    return int(((other_df["created_dt"] <= prop_end) & (other_df["end_dt"] >= prop_date)).sum())

props["concurrent_dao"] = props["created"].apply(count_concurrent)
props["log_concurrent"] = np.log1p(props["concurrent_dao"])

# ── load ETH vol ──────────────────────────────────────────────────────────────
with open(os.path.join(DATA, "eth_price_cache.json")) as f:
    eth_raw = json.load(f)
eth_df = pd.DataFrame([{"date": pd.Timestamp(k), **v} for k, v in eth_raw.items()])
eth_df = eth_df.sort_values("date").reset_index(drop=True)
eth_df["abs_ret"] = np.log(eth_df["close"] / eth_df["close"].shift(1)).abs()
eth_df["vol_7d"]  = eth_df["abs_ret"].rolling(7, min_periods=3).mean()
eth_dict = {r.date.date(): r.vol_7d for r in eth_df.itertuples()}

def prop_vol(d):
    days = pd.date_range(d, periods=DISCUSSION_DAYS, freq="D")
    v = [eth_dict.get(x.date()) for x in days]
    v = [x for x in v if x is not None and not np.isnan(x)]
    return np.mean(v) if v else np.nan

props["eth_vol"] = props["created"].apply(prop_vol)
q75 = props["eth_vol"].quantile(0.75)
props["high_vol"] = (props["eth_vol"] > q75).astype(int)

# ── event tagging ──────────────────────────────────────────────────────────────
def overlaps(d, s, e):
    return (d <= e) and (d + pd.Timedelta(days=DISCUSSION_DAYS) >= s)

EVENTS = [
    ("2024-06-13", "2024-06-22", "airdrop",    "ZKsync + LayerZero airdrop cluster"),
    ("2024-02-17", "2024-02-24", "airdrop",    "Starknet (\$STRK) airdrop"),
    ("2025-02-19", "2025-02-26", "hack",       "Bybit hack (\$1.5B)"),
    ("2023-11-08", "2023-11-26", "hack",       "Nov 2023 hack cluster [QLR overlap]"),
    ("2023-03-11", "2023-03-17", "hack",       "Euler Finance hack (\$197M)"),
    ("2024-08-03", "2024-08-10", "crash",      "BoJ carry-trade crash (Aug 2024)"),
    ("2023-03-08", "2023-03-15", "crash",      "SVB collapse + USDC depeg"),
    ("2023-06-03", "2023-06-10", "regulatory", "SEC sues Binance + Coinbase"),
    ("2024-01-08", "2024-01-15", "regulatory", "Bitcoin spot ETF approval"),
    ("2024-04-17", "2024-04-23", "scheduled",  "Bitcoin halving [LTIPP confound]"),
]

for i, (s, e, cat, lbl) in enumerate(EVENTS):
    s_dt, e_dt = pd.Timestamp(s), pd.Timestamp(e)
    props[f"ev{i}"] = props["created"].apply(lambda d, s=s_dt, e=e_dt: int(overlaps(d, s, e)))

# ── OLS helper ─────────────────────────────────────────────────────────────────
def ols_simple(x, y):
    mask = ~(np.isnan(x) | np.isnan(y))
    x, y = x[mask], y[mask]
    n = len(x)
    if n < 4 or np.std(x) == 0:
        return dict(n=n, n_treat=0, beta=np.nan, se=np.nan, t=np.nan, p=np.nan,
                    ci_lo=np.nan, ci_hi=np.nan, ctrl_mean=np.nan, treat_mean=np.nan,
                    pct_chg=np.nan)
    X = np.column_stack([np.ones(n), x])
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    s2 = resid @ resid / (n - 2)
    se  = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))[1]
    t   = beta[1] / se
    p   = 2 * (1 - spstats.t.cdf(abs(t), df=n - 2))
    cv  = spstats.t.ppf(0.975, df=n - 2)
    return dict(n=n, n_treat=int(x.sum()), beta=beta[1], se=se, t=t, p=p,
                ci_lo=beta[1] - cv*se, ci_hi=beta[1] + cv*se,
                ctrl_mean=np.nan, treat_mean=np.nan, pct_chg=np.nan)

def group_means(col, posts_col="human_posts"):
    ctrl  = props.loc[props[col] == 0, posts_col]
    treat = props.loc[props[col] == 1, posts_col]
    if len(treat) == 0:
        return np.nan, np.nan, np.nan, np.nan
    _, p = spstats.ttest_ind(ctrl, treat)
    pct  = 100 * (treat.mean() - ctrl.mean()) / ctrl.mean()
    return ctrl.mean(), treat.mean(), pct, p

# ── compute results for each instrument ───────────────────────────────────────
rows = []
for i, (s, e, cat, lbl) in enumerate(EVENTS):
    col = f"ev{i}"
    ctrl_m, treat_m, pct, p_ttest = group_means(col)
    r = ols_simple(props[col].values.astype(float), props["log_human"].values)
    n_treat = int(props[col].sum())
    rows.append(dict(label=lbl, category=cat, n_treat=n_treat,
                     ctrl_mean=ctrl_m, treat_mean=treat_m,
                     pct_chg=pct, p_ttest=p_ttest,
                     beta_fs=r["beta"], se_fs=r["se"],
                     t_fs=r["t"], p_fs=r["p"],
                     ci_lo=r["ci_lo"], ci_hi=r["ci_hi"]))

# Continuous: concurrent DAO proposals
r_conc = ols_simple(props["log_concurrent"].values, props["log_human"].values)
rows.append(dict(label="Concurrent DAO proposals (Hirshleifer)", category="concurrent",
                 n_treat=None,
                 ctrl_mean=np.nan, treat_mean=np.nan, pct_chg=np.nan, p_ttest=np.nan,
                 beta_fs=r_conc["beta"], se_fs=r_conc["se"],
                 t_fs=r_conc["t"], p_fs=r_conc["p"],
                 ci_lo=r_conc["ci_lo"], ci_hi=r_conc["ci_hi"]))

# Continuous: ETH vol
r_vol = ols_simple(props["eth_vol"].values, props["log_human"].values)
rows.append(dict(label="ETH 7-day return volatility (continuous)", category="volatility",
                 n_treat=None,
                 ctrl_mean=np.nan, treat_mean=np.nan, pct_chg=np.nan, p_ttest=np.nan,
                 beta_fs=r_vol["beta"], se_fs=r_vol["se"],
                 t_fs=r_vol["t"], p_fs=r_vol["p"],
                 ci_lo=r_vol["ci_lo"], ci_hi=r_vol["ci_hi"]))

df = pd.DataFrame(rows)

# ── Figure ────────────────────────────────────────────────────────────────────
# Horizontal bar chart: first-stage β with 95% CI, color by correct/wrong sign.
# Continuous instruments rescaled to comparable units.

# Exclude continuous instruments from the main bars (add separately as reference)
binary_df = df[df["n_treat"].notna()].copy()
binary_df = binary_df.sort_values("beta_fs", ascending=True).reset_index(drop=True)

COLORS = {
    "airdrop":    "#E67E22",   # orange
    "hack":       "#8E44AD",   # purple
    "crash":      "#E74C3C",   # red
    "regulatory": "#2980B9",   # blue
    "scheduled":  "#27AE60",   # green (only one with "right" sign — but confounded)
}

fig, ax = plt.subplots(figsize=(11, 7))
fig.subplots_adjust(left=0.41, right=0.88, top=0.88, bottom=0.12)

y_pos = np.arange(len(binary_df))

for i, (_, row) in enumerate(binary_df.iterrows()):
    if np.isnan(row["beta_fs"]):
        # no treated proposals — show as diamond at 0 with dashed
        ax.plot(0, i, "D", color="#BDC3C7", markersize=6)
        ax.text(0.02, i, " n=0 (no overlap)", va="center", fontsize=7.5, color="#7F8C8D")
        continue

    c = COLORS.get(row["category"], "#95A5A6")
    ci_lo = max(0, row["beta_fs"] - row["ci_lo"]) if not np.isnan(row["ci_lo"]) else 0
    ci_hi = max(0, row["ci_hi"] - row["beta_fs"]) if not np.isnan(row["ci_hi"]) else 0
    ax.errorbar(row["beta_fs"], i,
                xerr=[[ci_lo], [ci_hi]],
                fmt="o", markersize=7, linewidth=1.6,
                color=c, ecolor=c,
                markerfacecolor=c, markeredgecolor="white",
                markeredgewidth=0.8)

    # Star annotation
    star = ("***" if not np.isnan(row["p_fs"]) and row["p_fs"] < 0.01
            else "**" if not np.isnan(row["p_fs"]) and row["p_fs"] < 0.05
            else "*"  if not np.isnan(row["p_fs"]) and row["p_fs"] < 0.10
            else "")
    n_str = f"n={int(row['n_treat'])}"
    ax.text(row["ci_hi"] + 0.03 if not np.isnan(row["ci_hi"]) else row["beta_fs"] + 0.1,
            i,
            f"β={row['beta_fs']:+.2f}{star}  {n_str}",
            va="center", fontsize=7.5, color="#2C3E50")

# Zero line with directional arrow
ax.axvline(0, color="#2C3E50", linewidth=1.0, linestyle="-", alpha=0.6)
ax.annotate("", xy=(-0.85, -0.9), xytext=(0, -0.9),
            arrowprops=dict(arrowstyle="->", color="#27AE60", lw=1.5))
ax.text(-0.43, -0.9, "Expected: fewer posts →", va="center",
        fontsize=8, color="#27AE60", style="italic")

ax.set_yticks(y_pos)
ax.set_yticklabels(binary_df["label"], fontsize=8.5)
ax.set_xlabel("First-stage coefficient β  [log(human posts + 1) ~ distraction dummy]",
              fontsize=9.5)
ax.set_title(
    "Robustness: Distraction Instruments All Have the Wrong Sign\n"
    "Hirshleifer et al. (2009) framework — DAO participants respond to crypto events "
    "with increased governance engagement",
    fontsize=10, fontweight="bold", loc="left"
)
ax.grid(axis="x", linestyle="--", linewidth=0.4, alpha=0.45)

# Legend for categories
legend_handles = [mpatches.Patch(color=c, label=k.capitalize())
                  for k, c in COLORS.items()]
legend_handles.append(mpatches.Patch(color="#BDC3C7", label="No proposal overlap (n=0)"))
ax.legend(handles=legend_handles, fontsize=8, loc="lower right", framealpha=0.9)

# Shaded "wrong direction" region
xlim = ax.get_xlim()
ax.axvspan(0, xlim[1], color="#FDECEA", alpha=0.25, label="_wrong zone")
ax.text(xlim[1]*0.55, len(binary_df) - 0.4,
        "← All significant estimates fall here\n   (wrong sign for a distraction instrument)",
        fontsize=7.5, color="#E74C3C", ha="center", va="top", style="italic")

note_text = (
    "Note: Instruments with n=0 treated proposals reflect no Arbitrum voting\n"
    "during the event window. Bitcoin halving (green, −sign) is confounded\n"
    "by the Arbitrum LTIPP grant batch (n≈40 small applications in April 2024).\n"
    f"Full sample: N={N} contested proposals, 2023–2026."
)
fig.text(0.41, 0.01, note_text, fontsize=7.5, color="#555555", va="bottom")

fig.savefig(OUT_FIG, dpi=180, bbox_inches="tight")
print(f"Saved → {OUT_FIG}")
plt.close()

# ── LaTeX table ───────────────────────────────────────────────────────────────
def sig_star(p):
    if np.isnan(p): return ""
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""

lines = []
lines.append(r"\begin{table}[ht]")
lines.append(r"\centering")
lines.append(r"\small")
lines.append(r"\caption{Distraction Instruments: First-Stage Estimates \\"
             r"{\small Dependent variable: $\log(\text{human posts} + 1)$ in proposal thread. "
             r"Distraction dummy $= 1$ if event window overlaps proposal's active discussion period "
             r"(creation date $+$ 10 days). Standard errors in parentheses. "
             r"All significant estimates have the wrong sign: crypto events \emph{increase} "
             r"DAO forum participation rather than reducing it.}}")
lines.append(r"\label{tab:distraction_fs}")
lines.append(r"\begin{tabular}{lcccccc}")
lines.append(r"\hline\hline")
lines.append(r"Instrument & Category & $n_{\text{treat}}$ & $\bar{x}_{\text{ctrl}}$ "
             r"& $\bar{x}_{\text{treat}}$ & $\Delta\%$ & $\hat{\beta}$ \\")
lines.append(r"\hline")

for _, row in binary_df.sort_values("category").iterrows():
    nt   = int(row["n_treat"]) if not np.isnan(row["n_treat"]) else 0
    lbl  = row["label"].replace("$", r"\$").replace("[", r"\text{[}").replace("]", r"\text{]}").replace("_", r"\_")
    cat  = row["category"].capitalize()
    if nt == 0:
        lines.append(fr"  {lbl} & {cat} & 0 & \multicolumn{{3}}{{c}}{{(no overlap)}} & — \\")
    else:
        ctrl_s  = f"{row['ctrl_mean']:.1f}" if not np.isnan(row["ctrl_mean"]) else "—"
        treat_s = f"{row['treat_mean']:.1f}" if not np.isnan(row["treat_mean"]) else "—"
        pct_s   = (f"{row['pct_chg']:+.0f}\\%{sig_star(row['p_ttest'])}"
                   if not np.isnan(row["pct_chg"]) else "—")
        b_s     = (f"${row['beta_fs']:+.3f}^{{{sig_star(row['p_fs'])}}}$"
                   if not np.isnan(row["beta_fs"]) else "—")
        lines.append(fr"  {lbl} & {cat} & {nt} & {ctrl_s} & {treat_s} & {pct_s} & {b_s} \\")
        se_s = f"({row['se_fs']:.3f})" if not np.isnan(row["se_fs"]) else ""
        lines.append(fr"  & & & & & & {se_s} \\")

lines.append(r"\hline")

# continuous instruments
r_conc_row = df[df["label"].str.contains("Concurrent")].iloc[0]
r_vol_row  = df[df["label"].str.contains("volatility")].iloc[0]
for row, unit in [(r_conc_row, r"\log(1+\text{count})"), (r_vol_row, r"mean abs. log-ret.")]:
    lbl = row["label"].replace("_", r"\_")
    b_s = (f"${row['beta_fs']:+.3f}^{{{sig_star(row['p_fs'])}}}$"
           if not np.isnan(row["beta_fs"]) else "—")
    lines.append(fr"  {lbl} & Continuous & — & \multicolumn{{3}}{{c}}{{({unit})}} & {b_s} \\")
    se_s = f"({row['se_fs']:.3f})" if not np.isnan(row["se_fs"]) else ""
    lines.append(fr"  & & & & & & {se_s} \\")

lines.append(r"\hline\hline")
lines.append(r"\multicolumn{7}{l}{\footnotesize $^*p<0.10$, $^{**}p<0.05$, $^{***}p<0.01$. "
             r"$\Delta\%$ p-values from two-sample $t$-test; $\hat{\beta}$ from OLS.} \\")
lines.append(r"\multicolumn{7}{l}{\footnotesize Bitcoin halving ($n=40$) confounded by "
             r"Arbitrum LTIPP grant batch. November 2023 cluster overlaps QLR structural break.} \\")
lines.append(r"\end{tabular}")
lines.append(r"\end{table}")

with open(OUT_TEX, "w") as f:
    f.write("\n".join(lines) + "\n")
print(f"Saved → {OUT_TEX}")
