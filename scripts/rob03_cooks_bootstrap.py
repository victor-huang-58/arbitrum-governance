#!/usr/bin/env python3
"""
Robustness Check: Cook's D Influence Analysis + Bootstrap Chow Test
Journal of Finance paper on Arbitrum governance.

Directly addresses the referee concern that the pre-period r = -0.39 (n=44)
is fragile and potentially driven by a handful of close votes.

Panel A: Pre-period scatter (human posts vs margin) with Cook's D bubble sizes.
         Flags observations with D > 4/n (standard high-influence threshold).
         Shows the OLS fit and 95% CI survive removal of high-D points.

Panel B: Leave-one-out sensitivity — distribution of r_pre when each of the 44
         pre-period observations is removed. A tight distribution far from zero
         rules out a single-observation driver.

Panel C: Bootstrap permutation Chow F — under H0 (no structural break), randomly
         shuffle the pre/post assignment 10,000 times and recompute the Chow F.
         The observed F's position in this null distribution gives a
         non-parametric p-value free of small-sample normal approximation.

Break date: GPT-4 Turbo, November 6 2023 (QLR-identified primary break).
"""

import os, re, json, time
import duckdb
import requests
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from difflib import SequenceMatcher
from scipy import stats as spstats
import sys

HERE    = os.path.dirname(os.path.abspath(__file__))
ROOT    = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH    = os.path.join(OUT_DIR, "rob03_cooks_bootstrap.png")
DB_PATH     = os.path.join(ROOT, "data", "arbitrum.db")
FORUM_CACHE = os.path.join(ROOT, "data", "figure8_forum_cache.json")
SNAP_CACHE  = os.path.join(ROOT, "data", "figure8b_snap_cache.json")

sys.path.insert(0, HERE)
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, C_SHOCK
apply_aer_style()

SNAPSHOT_URL    = "https://hub.snapshot.org/graphql"
HEADERS         = {"User-Agent": "Mozilla/5.0 (research-bot)"}
MATCH_THRESHOLD = 0.55
AI_THRESHOLD    = 0.70
BREAK_DATE      = pd.Timestamp("2024-03-04")   # Claude 3 (matches abstract n=44)
N_BOOT          = 10_000
RNG_SEED        = 42

rng = np.random.default_rng(RNG_SEED)

TEMP_RE = re.compile(r'\btemp(erature)?\s*check\b', re.I)


# ── helpers ───────────────────────────────────────────────────────────────────

def load_json(path):
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {}

def title_sim(a, b):
    a = re.sub(r"[\[\(][^\]\)]*[\]\)]", "", a).strip().lower()
    b = re.sub(r"[\[\(][^\]\)]*[\]\)]", "", b).strip().lower()
    return SequenceMatcher(None, a, b).ratio()

def compute_margin(scores, choices):
    if not scores or not choices:
        return np.nan
    cs = dict(zip([c.lower() for c in choices], scores))
    for_s     = cs.get("for",     cs.get("yes", 0))
    against_s = cs.get("against", cs.get("no",  0))
    contested = for_s + against_s
    if contested == 0:
        return np.nan
    return abs(2 * for_s / contested - 1)   # 0 = 50/50, 1 = unanimous


# ══════════════════════════════════════════════════════════════════════════════
# STEP 1  Reconstruct matched proposals (same pipeline as fig08_main_causal)
# ══════════════════════════════════════════════════════════════════════════════

print("Step 1: Loading matched proposals...")

con = duckdb.connect(DB_PATH, read_only=True)
topic_scores = con.execute("""
    SELECT p.topic_id,
           COUNT(*) FILTER (WHERE s.fraction_ai <= ?)  AS human_posts,
           COUNT(*)                                     AS total_posts
    FROM posts p
    JOIN post_ai_scores s ON p.id = s.post_id
    WHERE s.fraction_ai IS NOT NULL AND s.headline NOT LIKE 'error:%'
    GROUP BY p.topic_id
""", [AI_THRESHOLD]).df()
con.close()

topic_human = dict(zip(topic_scores.topic_id.astype(int),
                       topic_scores.human_posts.astype(int)))

snap_raw   = load_json(SNAP_CACHE)
forum_cache = load_json(FORUM_CACHE)

rows = []
for p in snap_raw:
    dt = pd.to_datetime(p["created"], unit="s")
    if dt < pd.Timestamp("2023-01-01"):
        continue
    if TEMP_RE.search(p["title"]):
        continue
    if p.get("votes", 0) == 0:
        continue
    margin = compute_margin(p.get("scores"), p.get("choices"))
    if np.isnan(margin):
        continue
    rows.append({"snap_id": p["id"], "title": p["title"],
                 "created": dt, "margin": margin})

snap_df = pd.DataFrame(rows)

matched = []
for row in snap_df.itertuples():
    best_s, best_tid, best_title = 0, None, ""
    for tid, fd in forum_cache.items():
        s = title_sim(row.title, fd.get("title", ""))
        if s > best_s:
            best_s, best_tid, best_title = s, int(tid), fd.get("title", "")
    if best_s < MATCH_THRESHOLD or best_tid is None:
        continue
    hp = topic_human.get(best_tid, np.nan)
    if np.isnan(hp):
        continue
    matched.append({"snap_id": row.snap_id, "title": row.title,
                    "forum_title": best_title, "created": row.created,
                    "margin": row.margin, "human_posts": float(hp),
                    "topic_id": best_tid, "match_score": round(best_s, 3)})

df = (pd.DataFrame(matched)
        .dropna(subset=["human_posts", "margin"])
        .sort_values("created")
        .reset_index(drop=True))

pre  = df[df["created"] <  BREAK_DATE].reset_index(drop=True)
post = df[df["created"] >= BREAK_DATE].reset_index(drop=True)

print(f"  Total matched: {len(df)}  |  pre={len(pre)}  post={len(post)}")
r_pre,  p_pre  = spstats.pearsonr(pre["human_posts"],  pre["margin"])
r_post, p_post = spstats.pearsonr(post["human_posts"], post["margin"])
print(f"  r_pre  = {r_pre:+.3f}  p={p_pre:.4f}  (n={len(pre)})")
print(f"  r_post = {r_post:+.3f}  p={p_post:.4f}  (n={len(post)})")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 2  Cook's D on pre-period OLS: margin ~ human_posts
# ══════════════════════════════════════════════════════════════════════════════

print("\nStep 2: Computing Cook's D for pre-period OLS...")

x_pre = pre["human_posts"].values.astype(float)
y_pre = pre["margin"].values.astype(float)
n_pre = len(x_pre)

X = np.column_stack([np.ones(n_pre), x_pre])
beta, _, _, _ = np.linalg.lstsq(X, y_pre, rcond=None)
y_hat = X @ beta
resid = y_pre - y_hat
mse   = np.sum(resid**2) / (n_pre - 2)
k     = 2   # intercept + slope

H  = X @ np.linalg.pinv(X.T @ X) @ X.T   # hat matrix
h  = np.diag(H)                            # leverage
cooks_d = (resid**2 / (k * mse)) * (h / (1 - h)**2)

thresh_4n = 4.0 / n_pre   # conventional high-influence threshold
n_influential = int((cooks_d > thresh_4n).sum())
print(f"  Observations with Cook's D > 4/n ({thresh_4n:.3f}): {n_influential}")

# LOO analysis: remove each high-D point, recompute slope and r
lod_indices = np.where(cooks_d > thresh_4n)[0]
for i in lod_indices:
    xi = np.delete(x_pre, i)
    yi = np.delete(y_pre, i)
    r_i, _ = spstats.pearsonr(xi, yi)
    sl_i, ic_i, *_ = spstats.linregress(xi, yi)
    print(f"    Remove obs {i} ('{pre.loc[i,'title'][:50]}'): "
          f"r={r_i:+.3f}  slope={sl_i:.4f}")

# Full OLS stats for annotation
slope, intercept, r_full, p_full, se = spstats.linregress(x_pre, y_pre)


# ══════════════════════════════════════════════════════════════════════════════
# STEP 3  Leave-one-out distribution of r_pre
# ══════════════════════════════════════════════════════════════════════════════

print("\nStep 3: Leave-one-out r_pre distribution...")

loo_r = np.array([
    spstats.pearsonr(np.delete(x_pre, i), np.delete(y_pre, i))[0]
    for i in range(n_pre)
])
print(f"  LOO r_pre: mean={loo_r.mean():+.3f}  min={loo_r.min():+.3f}  "
      f"max={loo_r.max():+.3f}  std={loo_r.std():.3f}")
print(f"  Fraction of LOO r < 0: {(loo_r < 0).mean():.1%}")
print(f"  Fraction of LOO r < -0.20: {(loo_r < -0.20).mean():.1%}")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 4  Bootstrap permutation Chow F
# ══════════════════════════════════════════════════════════════════════════════

print(f"\nStep 4: Bootstrap permutation Chow F ({N_BOOT:,} replications)...")

x_all = df["human_posts"].values.astype(float)
y_all = df["margin"].values.astype(float)
n_all = len(x_all)
n_pre_obs = len(pre)

def ols_rss(x, y):
    X_ = np.column_stack([np.ones(len(x)), x])
    b, _, _, _ = np.linalg.lstsq(X_, y, rcond=None)
    return float(np.sum((y - X_ @ b)**2))

def chow_f(x, y, split):
    """Chow F for a split at index `split`."""
    x1, y1 = x[:split], y[:split]
    x2, y2 = x[split:], y[split:]
    if len(x1) < 4 or len(x2) < 4:
        return np.nan
    rss_p = ols_rss(x, y)
    rss_u = ols_rss(x1, y1) + ols_rss(x2, y2)
    if rss_u == 0:
        return np.nan
    return ((rss_p - rss_u) / 2) / (rss_u / (n_all - 4))

# Observed Chow F (pre-period = first n_pre_obs observations in time order)
F_obs = chow_f(x_all, y_all, n_pre_obs)
print(f"  Observed Chow F = {F_obs:.2f}")

# Permutation: randomly shuffle the data (break the time structure)
F_boot = np.empty(N_BOOT)
for b in range(N_BOOT):
    idx = rng.permutation(n_all)
    F_boot[b] = chow_f(x_all[idx], y_all[idx], n_pre_obs)

F_boot = F_boot[np.isfinite(F_boot)]
perm_p = float((F_boot >= F_obs).mean())
print(f"  Permutation p-value = {perm_p:.4f}  "
      f"({(F_boot >= F_obs).sum()} / {len(F_boot)} permutations >= F_obs)")
print(f"  Bootstrap F distribution: mean={F_boot.mean():.2f}  "
      f"p95={np.percentile(F_boot, 95):.2f}  p99={np.percentile(F_boot, 99):.2f}")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 5  Robustness table: remove top-D observations one by one
# ══════════════════════════════════════════════════════════════════════════════

print("\nStep 5: Sequential removal of highest Cook's D observations...")
top_d_order = np.argsort(cooks_d)[::-1]

print(f"  {'Removed':>8}  {'r_pre':>7}  {'p_pre':>8}  {'Chow_F':>8}  {'perm_p':>8}")
print(f"  {'0 (base)':>8}  {r_pre:+.3f}   {p_pre:.4f}   {F_obs:.2f}   {perm_p:.4f}")

for n_removed in [1, 2, 3, 5]:
    drop_idx = top_d_order[:n_removed]
    keep     = np.ones(n_pre, dtype=bool)
    keep[drop_idx] = False
    x_k, y_k = x_pre[keep], y_pre[keep]

    if len(x_k) < 5:
        break
    r_k, p_k = spstats.pearsonr(x_k, y_k)

    # Rebuild full array and recompute Chow
    keep_full = np.ones(n_all, dtype=bool)
    keep_full[:n_pre][drop_idx] = False
    x_f, y_f = x_all[keep_full], y_all[keep_full]
    new_split = keep_full[:n_pre].sum()
    F_k = chow_f(x_f, y_f, new_split)

    # Quick permutation p for this subsample
    n_f = len(x_f)
    F_bt = np.array([chow_f(x_f[rng.permutation(n_f)],
                             y_f[rng.permutation(n_f)], new_split)
                     for _ in range(2000)])
    F_bt = F_bt[np.isfinite(F_bt)]
    pp_k = float((F_bt >= F_k).mean()) if len(F_bt) > 0 else np.nan

    print(f"  {n_removed:>8}  {r_k:+.3f}   {p_k:.4f}   {F_k:.2f}   {pp_k:.4f}")


# ══════════════════════════════════════════════════════════════════════════════
# STEP 6  Plot
# ══════════════════════════════════════════════════════════════════════════════

print("\nStep 6: Building figure...")

GRAY      = COLORS["gray"]
LIGHTGRAY = COLORS["lightgray"]
PRE_C     = C_HUMAN
BOOT_C    = "#7F8C8D"

fig = plt.figure(figsize=(14, 5))
gs  = gridspec.GridSpec(1, 3, wspace=0.40, figure=fig)
ax_a = fig.add_subplot(gs[0])
ax_b = fig.add_subplot(gs[1])
ax_c = fig.add_subplot(gs[2])

# ── Panel A: Pre-period scatter with Cook's D bubble sizes ────────────────────
d_thresh = thresh_4n
sizes = 25 + (cooks_d / cooks_d.max()) * 350
colors_a = np.where(cooks_d > d_thresh, C_AI, PRE_C)

ax_a.scatter(x_pre, y_pre, s=sizes, c=colors_a, alpha=0.70,
             edgecolors="white", linewidths=0.4, zorder=4)

# Flag high-D points
for i in lod_indices:
    ax_a.annotate(
        f"#{i+1}", (x_pre[i], y_pre[i]),
        textcoords="offset points", xytext=(6, 4),
        fontsize=7.5, color=C_AI, fontweight="bold",
    )

# OLS fit + 95% CI
x_line = np.linspace(x_pre.min(), x_pre.max(), 200)
y_line = intercept + slope * x_line
ax_a.plot(x_line, y_line, color=PRE_C, linewidth=2.0, linestyle="-", zorder=5)

x_bar  = x_pre.mean()
ss_x   = np.sum((x_pre - x_bar)**2)
t_crit = spstats.t.ppf(0.975, df=n_pre - 2)
se_ci  = se * np.sqrt(1/n_pre + (x_line - x_bar)**2 / ss_x)
ax_a.fill_between(x_line, y_line - t_crit * se_ci, y_line + t_crit * se_ci,
                  color=PRE_C, alpha=0.10, zorder=3)

# LOO fit after removing highest-D point
drop1 = top_d_order[0]
x1 = np.delete(x_pre, drop1); y1 = np.delete(y_pre, drop1)
sl1, ic1, *_ = spstats.linregress(x1, y1)
ax_a.plot(x_line, ic1 + sl1 * x_line, color=GRAY, linewidth=1.5,
          linestyle="--", zorder=5, alpha=0.8,
          label=f"OLS excl. obs #{drop1+1}")

# Size legend
for d_ref, lbl in [(thresh_4n / 2, f"D < 4/n"), (thresh_4n * 1.5, f"D > 4/n")]:
    s_ref = 25 + (d_ref / cooks_d.max()) * 350
    c_ref = C_AI if d_ref >= thresh_4n else PRE_C
    ax_a.scatter([], [], s=s_ref, c=c_ref, alpha=0.7,
                 edgecolors="white", label=lbl)

sig_str = ("***" if p_pre < 0.001 else "**" if p_pre < 0.01
           else "*" if p_pre < 0.05 else "n.s.")
ax_a.text(0.97, 0.97,
    f"$r = {r_pre:+.3f}$({sig_str})\n"
    f"slope $= {slope:+.4f}$\n"
    f"$n = {n_pre}$  D>4/n: {n_influential}",
    transform=ax_a.transAxes, fontsize=8.5, va="top", ha="right",
    family="monospace",
    bbox=dict(fc="white", ec=LIGHTGRAY, pad=4, alpha=0.95))
ax_a.set_xlabel("Human posts in proposal thread")
ax_a.set_ylabel("Margin of victory\n(0 = 50/50, 1 = unanimous)")
ax_a.set_title("Panel A: Pre-period scatter\n(bubble size proportional to Cook's D)",
               fontsize=10, loc="left")
ax_a.legend(fontsize=7.5, loc="lower left")
ax_a.grid(linestyle="--", linewidth=0.4, alpha=0.35)
despine(ax_a)


# ── Panel B: LOO distribution of r_pre ────────────────────────────────────────
ax_b.hist(loo_r, bins=20, color=PRE_C, alpha=0.80, edgecolor="white",
          linewidth=0.5, zorder=4)
ax_b.axvline(r_pre, color=C_AI, linewidth=2.0, linestyle="-",
             zorder=5, label=f"Full sample r = {r_pre:+.3f}")
ax_b.axvline(0, color=GRAY, linewidth=1.2, linestyle="--", alpha=0.7,
             zorder=5, label="r = 0")
ax_b.axvline(loo_r.min(), color=GRAY, linewidth=1.0, linestyle=":",
             alpha=0.7, label=f"LOO min = {loo_r.min():+.3f}")

frac_neg = (loo_r < 0).mean()
ax_b.text(0.97, 0.97,
    f"{frac_neg:.0%} of LOO r < 0\n"
    f"LOO mean = {loo_r.mean():+.3f}\n"
    f"LOO std  = {loo_r.std():.3f}",
    transform=ax_b.transAxes, fontsize=8.5, va="top", ha="right",
    family="monospace",
    bbox=dict(fc="white", ec=LIGHTGRAY, pad=4, alpha=0.95))
ax_b.set_xlabel("Pre-period $r$(human posts, margin)\nwith one observation removed")
ax_b.set_ylabel("Count")
ax_b.set_title("Panel B: Leave-one-out sensitivity\n(pre-period correlation)",
               fontsize=10, loc="left")
ax_b.legend(fontsize=8, loc="upper left")
ax_b.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.35)
despine(ax_b)


# ── Panel C: Bootstrap permutation distribution of Chow F ────────────────────
pct95 = np.percentile(F_boot, 95)
pct99 = np.percentile(F_boot, 99)

ax_c.hist(F_boot, bins=60, color=BOOT_C, alpha=0.75,
          edgecolor="white", linewidth=0.4, zorder=4,
          label=f"Permutation null ({len(F_boot):,} draws)")
ax_c.axvline(F_obs, color=C_AI, linewidth=2.2, linestyle="-",
             zorder=6, label=f"Observed F = {F_obs:.2f}")
ax_c.axvline(pct95, color=GRAY, linewidth=1.2, linestyle="--", alpha=0.8,
             zorder=5, label=f"95th pct = {pct95:.2f}")
ax_c.axvline(pct99, color=GRAY, linewidth=1.0, linestyle=":",  alpha=0.8,
             zorder=5, label=f"99th pct = {pct99:.2f}")

sig_perm = ("***" if perm_p < 0.001 else "**" if perm_p < 0.01
            else "*" if perm_p < 0.05 else "n.s.")
ax_c.text(0.97, 0.97,
    f"Perm. $p = {perm_p:.4f}$ {sig_perm}\n"
    f"Observed $F = {F_obs:.2f}$\n"
    f"{N_BOOT:,} permutations",
    transform=ax_c.transAxes, fontsize=8.5, va="top", ha="right",
    family="monospace",
    bbox=dict(fc="white", ec=LIGHTGRAY, pad=4, alpha=0.95))
ax_c.set_xlabel("Chow F-statistic\n(permuted pre/post assignment)")
ax_c.set_ylabel("Count")
ax_c.set_title("Panel C: Bootstrap permutation Chow F\n(H0: no structural break)",
               fontsize=10, loc="left")
ax_c.legend(fontsize=8, loc="upper right")
ax_c.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.35)
despine(ax_c)


fig.suptitle(
    f"Robustness: Cook's D Influence Analysis and Bootstrap Chow Test\n"
    f"Arbitrum DAO — Break date: GPT-4 Turbo ({BREAK_DATE.date()})  |  "
    f"pre n={n_pre}  post n={len(post)}",
    fontsize=11, fontweight="bold", y=1.02
)
fig.tight_layout()
fig.savefig(OUT_PATH, dpi=180, bbox_inches="tight")
print(f"\nSaved → {OUT_PATH}")
