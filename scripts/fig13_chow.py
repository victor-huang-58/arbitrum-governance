#!/usr/bin/env python3
"""
Chow test for structural break in forum-posts → margin-of-victory relationship.

Tests each of the 6 AI shock dates as a candidate breakpoint.
For each candidate:
  1. Run pooled OLS: margin ~ human_posts (restricted)
  2. Run separate OLS pre and post (unrestricted)
  3. Compute Chow F-statistic and p-value
  4. Report pre/post Pearson r and sample sizes

Also runs an unknown-breakpoint test (Quandt Likelihood Ratio) to find the
endogenously estimated break date.
"""

import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import sys as _sys
_sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, C_TOTAL, C_SHOCK, savefig as aer_savefig
apply_aer_style()
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy import stats as spstats

HERE     = os.path.dirname(os.path.abspath(__file__))
ROOT     = os.path.dirname(HERE)   # project root
OUT_DIR  = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, "fig13_chow.png")

# ── AI shock dates ─────────────────────────────────────────────────────────────
AI_EVENTS = [
    ("2023-03-14", "GPT-4"),
    ("2023-07-11", "Claude 2"),
    ("2023-11-06", "GPT-4 Turbo"),   # 128K context, 3× cheaper — QLR-aligned primary break
    ("2024-03-04", "Claude 3"),
    ("2024-05-13", "GPT-4o"),
    ("2024-09-12", "o1"),
    ("2025-01-20", "DeepSeek R1"),
]

# ── Load matched proposals ────────────────────────────────────────────────────
MATCHED_CSV = os.path.join(ROOT, "data", "matched_proposals.csv")
if not os.path.exists(MATCHED_CSV):
    raise FileNotFoundError(
        f"Required file not found: {MATCHED_CSV}\n"
        "Run scripts/fig08_main_causal.py first to generate it."
    )
df = pd.read_csv(MATCHED_CSV, parse_dates=["created"])
df = df.sort_values("created").reset_index(drop=True)
n_total = len(df)
print(f"N = {n_total} matched proposals  "
      f"({df['created'].min().date()} – {df['created'].max().date()})")

x_all = df["human_posts"].values.astype(float)
y_all = df["margin"].values.astype(float)


# ── Chow test function ────────────────────────────────────────────────────────

def ols_rss(x, y):
    """Return (beta, RSS) for OLS y ~ 1 + x."""
    X = np.column_stack([np.ones(len(x)), x])
    beta, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    return beta, np.sum(resid**2)

def chow_test(x, y, split_idx):
    """
    Chow F-test for structural break at split_idx.
    Returns (F_stat, p_value, n_pre, n_post, beta_pre, beta_post)
    """
    x1, y1 = x[:split_idx], y[:split_idx]
    x2, y2 = x[split_idx:], y[split_idx:]

    if len(x1) < 5 or len(x2) < 5:
        return np.nan, np.nan, len(x1), len(x2), None, None

    beta_pool, rss_pool = ols_rss(x, y)
    beta1,     rss1     = ols_rss(x1, y1)
    beta2,     rss2     = ols_rss(x2, y2)

    k = 2   # intercept + slope
    n = len(x)
    rss_unr = rss1 + rss2

    if rss_unr == 0:
        return np.nan, np.nan, len(x1), len(x2), beta1, beta2

    F = ((rss_pool - rss_unr) / k) / (rss_unr / (n - 2 * k))
    p = 1 - spstats.f.cdf(F, k, n - 2 * k)
    return F, p, len(x1), len(x2), beta1, beta2

def pearson_with_ci(x, y, alpha=0.05):
    """Return (r, p, r_lo, r_hi) with Fisher-z 95% CI."""
    if len(x) < 5 or np.std(x) == 0 or np.std(y) == 0:
        return np.nan, np.nan, np.nan, np.nan
    r, p = spstats.pearsonr(x, y)
    z    = np.arctanh(r)
    se   = 1 / np.sqrt(len(x) - 3)
    zc   = spstats.norm.ppf(1 - alpha / 2)
    return r, p, np.tanh(z - zc * se), np.tanh(z + zc * se)


# ── Quandt LR test (endogenous breakpoint) ────────────────────────────────────

def quandt_lr_test(x, y, trim=0.15):
    """
    Test for unknown breakpoint (QLR / sup-F).
    Scans all split points in [trim*n, (1-trim)*n] and returns
    the index with the largest F-stat.
    """
    n = len(x)
    lo, hi = int(trim * n), int((1 - trim) * n)
    F_stats = []
    idxs    = list(range(lo, hi + 1))
    for idx in idxs:
        F, p, n1, n2, _, _ = chow_test(x, y, idx)
        F_stats.append(F if not np.isnan(F) else 0)
    best_i   = int(np.argmax(F_stats))
    best_idx = idxs[best_i]
    best_F   = F_stats[best_i]
    # QLR critical values (Andrews 1993, 5% with k=2): ~8.85 for 15% trim
    qlr_cv_5pct = 8.85
    return best_idx, best_F, qlr_cv_5pct, idxs, F_stats


# ── Run Chow tests ─────────────────────────────────────────────────────────────

print("\n" + "="*72)
print("CHOW TESTS: structural break at each AI shock date")
print("="*72)
print(f"{'Shock':<20} {'Date':<12} {'n_pre':>6} {'n_post':>7} "
      f"{'r_pre':>7} {'r_post':>7} {'Δr':>7} {'F':>8} {'p':>8}")
print("-"*72)

results = []
for date_str, label in AI_EVENTS:
    shock_dt  = pd.Timestamp(date_str)
    split_idx = int((df["created"] < shock_dt).sum())

    pre  = df[df["created"] <  shock_dt]
    post = df[df["created"] >= shock_dt]

    r_pre,  p_pre,  lo_pre,  hi_pre  = pearson_with_ci(
        pre["human_posts"].values, pre["margin"].values)
    r_post, p_post, lo_post, hi_post = pearson_with_ci(
        post["human_posts"].values, post["margin"].values)

    F, p_chow, n1, n2, b1, b2 = chow_test(x_all, y_all, split_idx)

    sig = ("***" if (p_chow is not None and p_chow < 0.001) else
           "**"  if (p_chow is not None and p_chow < 0.01)  else
           "*"   if (p_chow is not None and p_chow < 0.05)  else "")

    r_pre_s  = f"{r_pre:+.3f}"  if not np.isnan(r_pre)  else "  n/a"
    r_post_s = f"{r_post:+.3f}" if not np.isnan(r_post) else "  n/a"
    delta_r  = (r_post - r_pre) if not (np.isnan(r_pre) or np.isnan(r_post)) else np.nan
    delta_s  = f"{delta_r:+.3f}" if not np.isnan(delta_r) else "  n/a"
    F_s      = f"{F:8.2f}" if not np.isnan(F) else "     n/a"
    p_s      = f"{p_chow:.4f}" if (p_chow is not None and not np.isnan(p_chow)) else "   n/a"

    print(f"{label:<20} {date_str:<12} {n1:>6} {n2:>7} "
          f"{r_pre_s:>7} {r_post_s:>7} {delta_s:>7} {F_s} {p_s} {sig}")

    results.append({
        "label": label, "date": shock_dt,
        "n_pre": n1, "n_post": n2,
        "r_pre": r_pre, "r_post": r_post,
        "r_pre_lo": lo_pre, "r_pre_hi": hi_pre,
        "r_post_lo": lo_post, "r_post_hi": hi_post,
        "p_pre": p_pre, "p_post": p_post,
        "delta_r": delta_r, "F": F, "p_chow": p_chow,
        "beta_pre": b1, "beta_post": b2,
    })

res_df = pd.DataFrame(results)

# ── Quandt LR (sup-F) ─────────────────────────────────────────────────────────

print("\n" + "="*72)
print("QUANDT LR TEST: endogenous break detection (no assumed date)")
print("="*72)
best_idx, best_F, qlr_cv, idxs, F_series = quandt_lr_test(x_all, y_all, trim=0.15)
best_date = df["created"].iloc[best_idx].date()
print(f"  Sup-F = {best_F:.2f}  at proposal index {best_idx} ({best_date})")
print(f"  QLR critical value (5%, k=2, 15% trim, Andrews 1993): {qlr_cv}")
print(f"  {'REJECT' if best_F > qlr_cv else 'FAIL TO REJECT'} H0 of no structural break")

# Also report the top 3 candidate dates
sorted_F = sorted(zip(F_series, idxs), reverse=True)[:3]
print(f"\n  Top 3 candidate breakpoints:")
for f_val, idx in sorted_F:
    print(f"    idx={idx}  date={df['created'].iloc[idx].date()}  F={f_val:.2f}")


# ── Plot ──────────────────────────────────────────────────────────────────────

fig = plt.figure(figsize=(14, 11))
gs  = gridspec.GridSpec(2, 2, hspace=0.45, wspace=0.35, figure=fig)
ax_bar   = fig.add_subplot(gs[0, :])   # full-width top: pre/post r by shock
ax_qlr   = fig.add_subplot(gs[1, 0])   # QLR F-stat scan
ax_break = fig.add_subplot(gs[1, 1])   # scatter pre vs post best break

HUMAN_C = "#2980B9"
AI_C    = "#E74C3C"
GRAY_C  = "#95A5A6"
SHOCK_C = "#7F8C8D"

# ── Top panel: pre/post r for each shock, with 95% CI ────────────────────────
valid = res_df.dropna(subset=["r_pre", "r_post", "F"])
x_pos = np.arange(len(valid))
width = 0.35

bars_pre  = ax_bar.bar(x_pos - width/2, valid["r_pre"],  width,
                       color=HUMAN_C, alpha=0.85, label="Pre-shock  r(human posts, margin)")
bars_post = ax_bar.bar(x_pos + width/2, valid["r_post"], width,
                       color=AI_C,    alpha=0.85, label="Post-shock r(human posts, margin)")

# 95% CI error bars
ax_bar.errorbar(x_pos - width/2, valid["r_pre"],
                yerr=[valid["r_pre"] - valid["r_pre_lo"],
                      valid["r_pre_hi"] - valid["r_pre"]],
                fmt="none", color="#1A5276", capsize=4, linewidth=1.5)
ax_bar.errorbar(x_pos + width/2, valid["r_post"],
                yerr=[valid["r_post"] - valid["r_post_lo"],
                      valid["r_post_hi"] - valid["r_post"]],
                fmt="none", color="#922B21", capsize=4, linewidth=1.5)

# Annotate Chow F and p
for i, (_, row) in enumerate(valid.iterrows()):
    sig = ("***" if row["p_chow"] < 0.001 else
           "**"  if row["p_chow"] < 0.01  else
           "*"   if row["p_chow"] < 0.05  else "n.s.")
    ax_bar.text(i, max(row["r_pre_hi"] if not np.isnan(row["r_pre_hi"]) else 0,
                       row["r_post_hi"] if not np.isnan(row["r_post_hi"]) else 0) + 0.04,
                f"F={row['F']:.1f}{sig}\n(n={row['n_pre']}/{row['n_post']})",
                ha="center", fontsize=7.5, color="#2C3E50")

ax_bar.axhline(0, color=GRAY_C, linewidth=0.9)
ax_bar.set_xticks(x_pos)
ax_bar.set_xticklabels([f"{r['label']}\n{str(r['date'])[:10]}" for _, r in valid.iterrows()],
                        fontsize=9)
ax_bar.set_ylabel("Pearson r  (human posts vs margin of victory)", fontsize=10)
ax_bar.set_title(
    "Chow Test: Pre vs Post-Shock Correlation — Forum Posts and Margin of Victory\n"
    "95% CI shown  |  F = Chow statistic  |  n = pre/post proposal counts",
    fontsize=10.5, fontweight="bold", loc="left")
ax_bar.legend(fontsize=9, loc="lower left")
ax_bar.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.4)
ax_bar.set_ylim(-0.85, 0.55)

# ── QLR scan ─────────────────────────────────────────────────────────────────
scan_dates = [df["created"].iloc[i] for i in idxs]
ax_qlr.plot(scan_dates, F_series, color=SHOCK_C, linewidth=1.8)
ax_qlr.axhline(qlr_cv, color=AI_C, linewidth=1.5, linestyle="--",
               label=f"5% CV = {qlr_cv}")
ax_qlr.axvline(df["created"].iloc[best_idx], color="#1ABC9C", linewidth=1.8,
               linestyle="--", label=f"Sup-F at {best_date}")

for dt_str, lbl in AI_EVENTS:
    dt = pd.Timestamp(dt_str)
    if scan_dates[0] <= dt <= scan_dates[-1]:
        ax_qlr.axvline(dt, color=SHOCK_C, linewidth=1.0, linestyle=":", alpha=0.7)
        ax_qlr.text(dt, ax_qlr.get_ylim()[1] if ax_qlr.get_ylim()[1] > 0 else 5,
                    lbl, rotation=90, fontsize=7, va="top", color=SHOCK_C)

ax_qlr.set_ylabel("Chow F-statistic", fontsize=10)
ax_qlr.set_xlabel("Candidate break date", fontsize=10)
ax_qlr.set_title("Quandt LR Test: Unknown Breakpoint Scan\n(15% trim, k=2)",
                  fontsize=10, fontweight="bold", loc="left")
ax_qlr.legend(fontsize=8)
ax_qlr.grid(linestyle="--", linewidth=0.4, alpha=0.4)

# ── Scatter: pre vs post best break ──────────────────────────────────────────
# Use the Chow-identified best break from named shocks
best_named = res_df.loc[res_df["F"].idxmax()]
split_dt   = best_named["date"]
pre_mask   = df["created"] <  split_dt
post_mask  = df["created"] >= split_dt

def scatter_with_fit(ax, x, y, color, label, marker):
    ax.scatter(x, y, color=color, alpha=0.55, s=25, marker=marker, label=label)
    if len(x) >= 5 and np.std(x) > 0:
        slope, intercept, r, p, _ = spstats.linregress(x, y)
        xr = np.linspace(x.min(), x.max(), 100)
        ax.plot(xr, slope * xr + intercept, color=color, linewidth=2, linestyle="--")
        return r, p
    return np.nan, np.nan

r1, p1 = scatter_with_fit(ax_break,
    df.loc[pre_mask,  "human_posts"].values,
    df.loc[pre_mask,  "margin"].values,
    HUMAN_C, f"Pre-{best_named['label']} (n={pre_mask.sum()})", "o")
r2, p2 = scatter_with_fit(ax_break,
    df.loc[post_mask, "human_posts"].values,
    df.loc[post_mask, "margin"].values,
    AI_C, f"Post-{best_named['label']} (n={post_mask.sum()})", "^")

sig1 = "***" if p1 < 0.001 else "**" if p1 < 0.01 else "*" if p1 < 0.05 else "n.s."
sig2 = "***" if p2 < 0.001 else "**" if p2 < 0.01 else "*" if p2 < 0.05 else "n.s."
ax_break.text(0.97, 0.97,
    f"Pre:  r = {r1:+.3f} {sig1}\nPost: r = {r2:+.3f} {sig2}",
    transform=ax_break.transAxes, fontsize=9, va="top", ha="right",
    family="monospace", bbox=dict(fc="white", ec="#BDC3C7", pad=4, alpha=0.93))

ax_break.set_xlabel("Human posts in proposal thread", fontsize=10)
ax_break.set_ylabel("Margin of victory", fontsize=10)
ax_break.set_title(
    f"Best Named Break: {best_named['label']} ({str(best_named['date'])[:10]})\n"
    f"Chow F = {best_named['F']:.2f}",
    fontsize=10, fontweight="bold", loc="left")
ax_break.legend(fontsize=8.5)
ax_break.grid(linestyle="--", linewidth=0.4, alpha=0.4)

fig.suptitle(
    f"Figure A9: Structural Break Analysis — Forum-to-Governance Signal\n"
    f"N = {n_total} matched Arbitrum proposals  |  Y = margin of victory  |  X = human post count",
    fontsize=12, fontweight="bold", y=1.01
)
fig.savefig(OUT_PATH, dpi=180, bbox_inches="tight")
print(f"\nSaved → {OUT_PATH}")
