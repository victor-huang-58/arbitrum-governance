#!/usr/bin/env python3
"""
Table: OLS Structural Break — Forum Posts and Margin of Victory
Journal of Finance paper on Arbitrum governance.

Upgrades the main result from Pearson r to OLS with controls, addressing
the referee concern that the correlation is fragile and confounded.

Specifications:
  (1) Pre-period, bivariate:    margin ~ human_posts
  (2) Pre-period, with controls: margin ~ human_posts + category_FE + log(votes)
  (3) Post-period, bivariate:   margin ~ human_posts
  (4) Post-period, with controls: margin ~ human_posts + category_FE + log(votes)

All standard errors are HC3 heteroskedasticity-robust.
Chow test on the human_posts coefficient: (2) vs. (4).

Outputs:
  - Console: formatted regression table
  - output/tables/tab_ols_structural_break.tex  (LaTeX booktabs table)
  - output/figures/fig_ols_coef_break.png       (coefficient plot)
"""

import os, re, json
import duckdb
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf
import statsmodels.api as sm
from difflib import SequenceMatcher
from scipy import stats as spstats
import sys

HERE    = os.path.dirname(os.path.abspath(__file__))
ROOT    = os.path.dirname(HERE)
OUT_FIG = os.path.join(ROOT, "output", "figures", "fig_ols_coef_break.png")
OUT_TEX = os.path.join(ROOT, "output", "tables", "tab_ols_structural_break.tex")
os.makedirs(os.path.dirname(OUT_FIG), exist_ok=True)
os.makedirs(os.path.dirname(OUT_TEX), exist_ok=True)

DB_PATH     = os.path.join(ROOT, "data", "arbitrum.db")
FORUM_CACHE = os.path.join(ROOT, "data", "figure8_forum_cache.json")
SNAP_CACHE  = os.path.join(ROOT, "data", "figure8b_snap_cache.json")

sys.path.insert(0, HERE)
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI
apply_aer_style()

MATCH_THRESHOLD = 0.55
AI_THRESHOLD    = 0.70
BREAK_DATE      = pd.Timestamp("2024-03-04")   # Claude 3

TEMP_RE  = re.compile(r'\btemp(erature)?\s*check\b', re.I)
CONST_RE = re.compile(r'\[constitutional\]|\bconstitutional\s+aip\b', re.I)
RULES_KW = re.compile(
    r'\b(arbos|protocol\s+upgrade|amend.*constitution|quorum|dvp|timeboost|'
    r'stylus|fee\s+parameter|security\s+council)\b', re.I)
SPEND_KW = re.compile(
    r'\b(grant|budget|funding|stip|ltipp|gaming\s+catalyst|drip|step|'
    r'treasury\s+allocation|service\s+provider|yield|rwa|opco)\b', re.I)
INST_KW  = re.compile(
    r'\b(committee|delegate\s+incentive|election|code\s+of\s+conduct|'
    r'oversight|domain\s+allocator|reconfirmation|agentic)\b', re.I)

def classify(title, vtype=""):
    if vtype in ("ranked-choice", "weighted", "approval"):
        return "Institution"
    if TEMP_RE.search(title):
        return "TempCheck"
    if CONST_RE.search(title) or RULES_KW.search(title):
        return "RulesChange"
    if SPEND_KW.search(title):
        return "TreasurySpend"
    if INST_KW.search(title):
        return "Institution"
    return "Other"

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
    return abs(2 * for_s / contested - 1)


# ══════════════════════════════════════════════════════════════════════════════
# Build matched dataset
# ══════════════════════════════════════════════════════════════════════════════

print("Loading matched proposals...")

con = duckdb.connect(DB_PATH, read_only=True)
ts  = con.execute("""
    SELECT p.topic_id,
           COUNT(*) FILTER (WHERE s.fraction_ai <= ?)  AS human_posts,
           COUNT(*)                                     AS total_posts
    FROM posts p
    JOIN post_ai_scores s ON p.id = s.post_id
    WHERE s.fraction_ai IS NOT NULL AND s.headline NOT LIKE 'error:%'
    GROUP BY p.topic_id
""", [AI_THRESHOLD]).df()
con.close()

topic_human = dict(zip(ts.topic_id.astype(int), ts.human_posts.astype(int)))
topic_total = dict(zip(ts.topic_id.astype(int), ts.total_posts.astype(int)))

def load_json(p):
    if os.path.exists(p):
        with open(p) as f: return json.load(f)
    return {}

snap_raw    = load_json(SNAP_CACHE)
forum_cache = load_json(FORUM_CACHE)

rows = []
for p in snap_raw:
    dt = pd.to_datetime(p["created"], unit="s")
    if dt < pd.Timestamp("2023-01-01"): continue
    if TEMP_RE.search(p["title"]):      continue
    if p.get("votes", 0) == 0:          continue
    margin = compute_margin(p.get("scores"), p.get("choices"))
    if np.isnan(margin): continue
    rows.append({"snap_id": p["id"], "title": p["title"],
                 "created": dt, "margin": margin, "votes": p.get("votes", 0)})

snap_df = pd.DataFrame(rows)

matched = []
for row in snap_df.itertuples():
    best_s, best_tid = 0, None
    for tid, fd in forum_cache.items():
        s = title_sim(row.title, fd.get("title", ""))
        if s > best_s:
            best_s, best_tid = s, int(tid)
    if best_s < MATCH_THRESHOLD or best_tid is None: continue
    hp = topic_human.get(best_tid, np.nan)
    if np.isnan(hp): continue
    cat = classify(row.title)
    matched.append({
        "snap_id":     row.snap_id,
        "title":       row.title,
        "created":     row.created,
        "margin":      row.margin,
        "human_posts": float(hp),
        "total_posts": float(topic_total.get(best_tid, hp)),
        "votes":       row.votes,
        "category":    cat,
    })

df = (pd.DataFrame(matched)
        .dropna(subset=["human_posts", "margin"])
        .sort_values("created")
        .reset_index(drop=True))

df["log_votes"]    = np.log1p(df["votes"])
df["period"]       = np.where(df["created"] < BREAK_DATE, "pre", "post")
df["hp_std"]       = (df["human_posts"] - df["human_posts"].mean()) / df["human_posts"].std()

pre  = df[df["period"] == "pre"].copy()
post = df[df["period"] == "post"].copy()
print(f"  pre n={len(pre)}  post n={len(post)}  total={len(df)}")

# Drop categories too rare for FE (need ≥2 observations per period)
def safe_cats(d, min_n=2):
    counts = d["category"].value_counts()
    keep = counts[counts >= min_n].index.tolist()
    d = d.copy()
    d.loc[~d["category"].isin(keep), "category"] = "Other"
    return d

pre  = safe_cats(pre)
post = safe_cats(post)

print("\nCategory distribution:")
for period, sub in [("pre", pre), ("post", post)]:
    print(f"  {period}: " + "  ".join(
        f"{c}={n}" for c, n in sub["category"].value_counts().items()))


# ══════════════════════════════════════════════════════════════════════════════
# OLS regressions (HC3 robust SEs)
# ══════════════════════════════════════════════════════════════════════════════

print("\nRunning OLS regressions...")

# Reference category for FE: "Other" (most common or alphabetically first)
# statsmodels treats the first level alphabetically as reference by default

specs = [
    ("(1) Pre, bivariate",     pre,  "margin ~ human_posts"),
    ("(2) Pre, + controls",    pre,  "margin ~ human_posts + C(category) + log_votes"),
    ("(3) Post, bivariate",    post, "margin ~ human_posts"),
    ("(4) Post, + controls",   post, "margin ~ human_posts + C(category) + log_votes"),
]

results = {}
for label, data, formula in specs:
    m = smf.ols(formula, data=data).fit(cov_type="HC3")
    results[label] = m
    b  = m.params["human_posts"]
    se = m.bse["human_posts"]
    t  = m.tvalues["human_posts"]
    p  = m.pvalues["human_posts"]
    ci = m.conf_int().loc["human_posts"]
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    print(f"  {label:30}  β={b:+.5f}  SE={se:.5f}  t={t:+.2f}  p={p:.4f}{sig:3}  "
          f"R²={m.rsquared:.3f}  n={int(m.nobs)}")


# ══════════════════════════════════════════════════════════════════════════════
# Chow test on the human_posts coefficient: spec (2) vs. (4)
# ══════════════════════════════════════════════════════════════════════════════

print("\nChow test on human_posts coefficient (controlled specs)...")

# Wald test: β_pre = β_post
# Stack pre + post with interaction: margin ~ human_posts * post + controls
df["post_dummy"] = (df["period"] == "post").astype(float)
df_clean = df.copy()
# Align categories across periods
all_cats = sorted(set(pre["category"]) | set(post["category"]))
df_clean["category"] = pd.Categorical(df_clean["category"], categories=all_cats)

m_pool = smf.ols(
    "margin ~ human_posts + post_dummy + human_posts:post_dummy + "
    "C(category) + log_votes",
    data=df_clean
).fit(cov_type="HC3")

b_interaction = m_pool.params.get("human_posts:post_dummy", np.nan)
se_interaction = m_pool.bse.get("human_posts:post_dummy", np.nan)
t_interaction  = m_pool.tvalues.get("human_posts:post_dummy", np.nan)
p_interaction  = m_pool.pvalues.get("human_posts:post_dummy", np.nan)

sig_int = ("***" if p_interaction < 0.001 else "**" if p_interaction < 0.01
           else "*"  if p_interaction < 0.05 else "n.s.")
print(f"  Interaction (Δβ = β_post − β_pre):")
print(f"    β_interaction = {b_interaction:+.5f}  SE={se_interaction:.5f}  "
      f"t={t_interaction:+.2f}  p={p_interaction:.4f}  {sig_int}")

# Also report the Chow F via RSS comparison
m2 = results["(2) Pre, + controls"]
m4 = results["(4) Post, + controls"]

rss2 = m2.ssr;  n2 = int(m2.nobs);  k2 = m2.df_model + 1
rss4 = m4.ssr;  n4 = int(m4.nobs);  k4 = m4.df_model + 1

# Pooled restricted model (same coefficients pre and post)
df_pool_vars = pd.concat([
    pre[["margin","human_posts","log_votes","category"]],
    post[["margin","human_posts","log_votes","category"]]
]).copy()
df_pool_vars["category"] = pd.Categorical(
    df_pool_vars["category"],
    categories=sorted(df_pool_vars["category"].unique()))

m_restricted = smf.ols(
    "margin ~ human_posts + C(category) + log_votes",
    data=df_pool_vars
).fit()
rss_r = m_restricted.ssr
rss_u = rss2 + rss4
k     = k2   # number of restricted params (same in both)
n     = n2 + n4

chow_F = ((rss_r - rss_u) / k) / (rss_u / (n - 2 * k))
chow_p = float(1 - spstats.f.cdf(chow_F, k, n - 2 * k))
sig_chow = ("***" if chow_p < 0.001 else "**" if chow_p < 0.01
            else "*" if chow_p < 0.05 else "n.s.")
print(f"\n  Chow F (controlled): F={chow_F:.2f}  p={chow_p:.4f}  {sig_chow}")
print(f"  (k={k}, df_u={n - 2*k})")


# ══════════════════════════════════════════════════════════════════════════════
# Print formatted regression table
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "="*78)
print("OLS REGRESSION TABLE — Forum Posts and Margin of Victory")
print("Dep. var: margin of victory (0=50/50, 1=unanimous)  |  SE: HC3 robust")
print("="*78)

col_labels  = ["(1) Pre", "(2) Pre+FE", "(3) Post", "(4) Post+FE"]
col_keys    = list(results.keys())
vars_report = ["human_posts", "log_votes"]

def fmt_coef(b, p):
    stars = "***" if p<0.001 else "**" if p<0.01 else "*" if p<0.05 else ""
    return f"{b:+.4f}{stars}"

def fmt_se(se):
    return f"({se:.4f})"

print(f"\n{'Variable':<28}" + "".join(f"{c:>14}" for c in col_labels))
print("-"*78)

for var in vars_report:
    row_b  = f"{'human_posts' if var=='human_posts' else 'log(votes)':<28}"
    row_se = f"{'':28}"
    for key in col_keys:
        m = results[key]
        if var in m.params:
            row_b  += f"{fmt_coef(m.params[var], m.pvalues[var]):>14}"
            row_se += f"{fmt_se(m.bse[var]):>14}"
        else:
            row_b  += f"{'—':>14}"
            row_se += f"{'':>14}"
    print(row_b)
    print(row_se)

print("-"*78)
print(f"{'Category FE':<28}" + "".join(
    f"{'No' if 'bivariate' in k else 'Yes':>14}" for k in col_keys))
print(f"{'N':<28}" + "".join(f"{int(results[k].nobs):>14}" for k in col_keys))
rsq_vals = "".join(f"{results[k].rsquared:>14.3f}" for k in col_keys)
print(f"{'R-squared':<28}" + rsq_vals)
print("="*78)
print(f"Chow F (bivariate):   {chow_F:.2f}{sig_chow}  (p={chow_p:.4f})")
print(f"Interaction β (controlled): {b_interaction:+.5f}  SE={se_interaction:.5f}"
      f"  p={p_interaction:.4f}  {sig_int}")
print("*p<0.05  **p<0.01  ***p<0.001  |  HC3 heteroskedasticity-robust SE")


# ══════════════════════════════════════════════════════════════════════════════
# LaTeX table
# ══════════════════════════════════════════════════════════════════════════════

def stars(p):
    return "^{***}" if p<0.001 else "^{**}" if p<0.01 else "^{*}" if p<0.05 else ""

lines = []
lines += [
    r"\begin{table}[H]",
    r"\centering",
    r"\caption{OLS Regressions: Human Forum Posts and Margin of Victory}",
    r"\label{tab:ols_structural_break}",
    r"\small",
    r"\begin{tabular}{lcccc}",
    r"\toprule",
    r" & \multicolumn{2}{c}{Pre-period} & \multicolumn{2}{c}{Post-period} \\",
    r"\cmidrule(lr){2-3}\cmidrule(lr){4-5}",
    r" & (1) & (2) & (3) & (4) \\",
    r"\midrule",
]

for var, label in [("human_posts", r"\textit{Human posts}"),
                   ("log_votes",   r"Log(votes)")]:
    row_b = f"{label}"
    row_s = ""
    for key in col_keys:
        m = results[key]
        if var in m.params:
            b = m.params[var]; p = m.pvalues[var]; se = m.bse[var]
            row_b += f" & ${b:+.4f}{stars(p)}$"
            row_s += f" & $({se:.4f})$"
        else:
            row_b += " & ---"
            row_s += " & "
    lines.append(row_b + r" \\")
    lines.append(row_s + r" \\")
    lines.append(r"\addlinespace[2pt]")

lines += [
    r"\midrule",
    r"Category FE & No & Yes & No & Yes \\",
    "N & " + " & ".join(str(int(results[k].nobs)) for k in col_keys) + r" \\",
    r"$R^2$ & " + " & ".join(f"{results[k].rsquared:.3f}" for k in col_keys) + r" \\",
    r"\midrule",
    rf"Chow $F$ (controlled) & \multicolumn{{4}}{{c}}"
    rf"{{$F = {chow_F:.2f}{stars(chow_p)}$, $p = {chow_p:.4f}$}} \\",
    rf"$\Delta\beta$ (post $-$ pre) & \multicolumn{{4}}{{c}}"
    rf"{{${b_interaction:+.5f}{stars(p_interaction)}$ $({se_interaction:.5f})$}} \\",
    r"\bottomrule",
    r"\end{tabular}",
    r"\begin{minipage}{\linewidth}",
    r"\smallskip",
    r"\footnotesize",
    r"\textit{Notes:} Dependent variable is margin of victory: $|\text{For\%} - "
    r"\text{Against\%}| / (\text{For\%} + \text{Against\%})$, ranging from 0 "
    r"(50/50 split) to 1 (unanimous). Human posts is the count of forum posts "
    r"with Pangram \textit{fraction\_ai} $\leq 0.70$ in the proposal's discussion "
    r"thread. Pre-period: January 2023 -- February 2024; post-period: March 2024 "
    r"onward (Claude~3 release date). Category fixed effects: Rules Change, Treasury "
    r"Spend, Institution Building, Other. All standard errors are HC3 "
    r"heteroskedasticity-robust. Chow $F$ tests equality of the "
    r"\textit{human\_posts} slope across periods in the controlled specification "
    r"(columns 2 and 4). $\Delta\beta$ is the coefficient on the "
    r"human\_posts $\times$ post interaction in a pooled regression.",
    r"\end{minipage}",
    r"\end{table}",
]

with open(OUT_TEX, "w") as f:
    f.write("\n".join(lines))
print(f"\nLaTeX table saved → {OUT_TEX}")


# ══════════════════════════════════════════════════════════════════════════════
# Coefficient plot: human_posts β with 95% CI, pre vs. post
# ══════════════════════════════════════════════════════════════════════════════

print("\nBuilding coefficient plot...")

fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), sharey=False)

GRAY = COLORS["gray"]

for ax_i, (ax, spec_pairs, title) in enumerate(zip(
    axes,
    [
        [("(1) Pre, bivariate", C_HUMAN), ("(3) Post, bivariate", C_AI)],
        [("(2) Pre, + controls", C_HUMAN), ("(4) Post, + controls", C_AI)],
    ],
    ["Bivariate", "With controls\n(category FE + log votes)"],
)):
    xs, ys, errs, cols, lbls = [], [], [], [], []
    for i, (key, col) in enumerate(spec_pairs):
        m   = results[key]
        b   = m.params["human_posts"]
        ci  = m.conf_int(alpha=0.05).loc["human_posts"]
        xs.append(i)
        ys.append(b)
        errs.append([[b - ci[0]], [ci[1] - b]])
        cols.append(col)
        period = "Pre" if "Pre" in key else "Post"
        n_obs  = int(m.nobs)
        lbls.append(f"{period}\n(n={n_obs})")

    for x, y, err, col in zip(xs, ys, errs, cols):
        ax.errorbar(x, y, yerr=err, fmt="o", color=col,
                    capsize=6, capthick=1.8, elinewidth=1.8,
                    markersize=9, zorder=5)

    ax.axhline(0, color=GRAY, linewidth=1.0, linestyle="--", alpha=0.7)
    ax.set_xticks(xs)
    ax.set_xticklabels(lbls, fontsize=10)
    ax.set_ylabel("OLS coefficient on human posts\n(95% CI, HC3 robust SE)")
    ax.set_title(title, fontsize=10.5, fontweight="bold")
    ax.set_xlim(-0.5, 1.5)
    ax.grid(axis="y", linestyle="--", linewidth=0.4, alpha=0.35)
    despine(ax)

    # Annotate Chow / interaction
    if ax_i == 1:
        sig_str = ("***" if p_interaction < 0.001 else "**" if p_interaction < 0.01
                   else "*" if p_interaction < 0.05 else "n.s.")
        ax.text(0.97, 0.03,
            f"$\\Delta\\beta = {b_interaction:+.4f}$ {sig_str}\n"
            f"Chow $F = {chow_F:.2f}$  $p = {chow_p:.4f}$",
            transform=ax.transAxes, fontsize=8.5, va="bottom", ha="right",
            family="monospace",
            bbox=dict(fc="white", ec=COLORS["lightgray"], pad=4, alpha=0.95))

fig.suptitle(
    "OLS Coefficient on Human Forum Posts — Pre vs. Post Claude 3\n"
    "Dep. var: margin of victory  |  HC3 robust SEs  |  "
    f"Break: {BREAK_DATE.date()}",
    fontsize=11, fontweight="bold", y=1.02
)
fig.tight_layout()
fig.savefig(OUT_FIG, dpi=180, bbox_inches="tight")
print(f"Figure saved → {OUT_FIG}")
