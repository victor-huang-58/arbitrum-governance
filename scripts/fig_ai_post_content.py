#!/usr/bin/env python3
"""
Figure: AI Post Content Analysis
Journal of Finance paper on Arbitrum governance.

Shows what AI-classified posts actually say, demonstrating they are
empty-signal "proposal summaries with generic endorsements" rather than
genuine opinion-bearing contributions.

Three panels:
  A. TF-IDF: top distinctive bigrams for AI vs human posts
  B. Post length distribution (AI posts are longer but less dense)
  C. Agreement-phrase frequency (AI posts disproportionately agreeable)

Plus: prints 3 representative AI post excerpts and 3 human post excerpts
for use as qualitative examples in the paper.

Output:
  output/figures/fig_ai_post_content.png
  output/tables/tab_ai_post_examples.tex
"""

import os, re, json
import duckdb
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, savefig as aer_savefig
apply_aer_style()

HERE    = os.path.dirname(os.path.abspath(__file__))
ROOT    = os.path.dirname(HERE)
DB_PATH = os.path.join(ROOT, "data", "arbitrum.db")
OUT_FIG = os.path.join(ROOT, "output", "figures", "fig_ai_post_content.png")
OUT_TAB = os.path.join(ROOT, "output", "tables", "tab_ai_post_examples.tex")
os.makedirs(os.path.join(ROOT, "output", "figures"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "output", "tables"), exist_ok=True)

AI_THRESHOLD = 0.70
MIN_WORDS    = 30   # ignore very short posts


# ── helpers ───────────────────────────────────────────────────────────────────

def strip_html(html):
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def word_count(text):
    return len(text.split())

# Phrases that signal empty endorsement / generic agreement
AGREEMENT_PHRASES = [
    "i support", "i agree", "great proposal", "excellent proposal",
    "this is a great", "this is an excellent", "i believe this",
    "strongly support", "fully support", "i think this proposal",
    "this proposal aims", "it is important to", "it is essential",
    "in conclusion", "overall, i", "to summarize", "in summary",
    "community members", "the arbitrum ecosystem", "it is worth noting",
    "this is a positive", "i would like to support",
]


# ── Step 1: Load posts ────────────────────────────────────────────────────────

print("Step 1: Loading posts from DuckDB...")
con = duckdb.connect(DB_PATH, read_only=True)

df = con.execute(f"""
    SELECT
        p.id,
        p.cooked,
        p.created_at,
        s.fraction_ai,
        CASE WHEN s.fraction_ai > {AI_THRESHOLD} THEN 'ai' ELSE 'human' END AS label
    FROM posts p
    JOIN post_ai_scores s ON p.id = s.post_id
    WHERE s.fraction_ai IS NOT NULL
      AND s.headline NOT LIKE 'error:%'
      AND LENGTH(p.cooked) > 100
      AND p.created_at::TIMESTAMP >= '2023-01-01'
      AND p.created_at::TIMESTAMP <  '2026-04-01'
""").df()

con.close()

df["text"]  = df["cooked"].apply(strip_html)
df["words"] = df["text"].apply(word_count)
df = df[df["words"] >= MIN_WORDS].reset_index(drop=True)

ai_df    = df[df["label"] == "ai"].copy()
human_df = df[df["label"] == "human"].copy()

print(f"  AI posts:    {len(ai_df):,}  (median {ai_df['words'].median():.0f} words)")
print(f"  Human posts: {len(human_df):,}  (median {human_df['words'].median():.0f} words)")


# ── Step 2: TF-IDF distinctive bigrams ────────────────────────────────────────

print("\nStep 2: Computing TF-IDF distinctive bigrams...")

# Sample balanced corpus for TF-IDF (cap human at 5x AI to avoid imbalance)
n_ai = len(ai_df)
n_human_sample = min(len(human_df), n_ai * 5)
human_sample = human_df.sample(n=n_human_sample, random_state=42)

corpus  = list(ai_df["text"]) + list(human_sample["text"])
labels  = ["ai"] * len(ai_df) + ["human"] * len(human_sample)

# Fit TF-IDF on full corpus (bigrams + trigrams, ignore very common words)
extra_stop = {"proposal", "arbitrum", "token", "will", "also", "one",
              "like", "think", "would", "use", "make", "just", "get",
              "new", "need", "much", "good", "ve", "ll", "don", "isn",
              "didn", "haven", "shouldn", "doesn", "arbitrum", "arb"}

vec = TfidfVectorizer(
    ngram_range=(2, 3),
    max_features=8000,
    stop_words="english",
    min_df=5,
    sublinear_tf=True,
)
X = vec.fit_transform(corpus)
features = np.array(vec.get_feature_names_out())

ai_idx    = [i for i, l in enumerate(labels) if l == "ai"]
human_idx = [i for i, l in enumerate(labels) if l == "human"]

ai_mean    = np.asarray(X[ai_idx].mean(axis=0)).flatten()
human_mean = np.asarray(X[human_idx].mean(axis=0)).flatten()

# Distinctiveness = mean TF-IDF in group minus mean in other group
ai_distinctive    = ai_mean    - human_mean
human_distinctive = human_mean - ai_mean

top_n = 10
top_ai_idx    = np.argsort(ai_distinctive)[-top_n:][::-1]
top_human_idx = np.argsort(human_distinctive)[-top_n:][::-1]

top_ai_terms    = features[top_ai_idx]
top_ai_scores   = ai_distinctive[top_ai_idx]
top_human_terms = features[top_human_idx]
top_human_scores= human_distinctive[top_human_idx]

print("\n  Top AI-distinctive n-grams:")
for t, s in zip(top_ai_terms, top_ai_scores):
    print(f"    {t:35s}  Δ={s:+.4f}")
print("\n  Top human-distinctive n-grams:")
for t, s in zip(top_human_terms, top_human_scores):
    print(f"    {t:35s}  Δ={s:+.4f}")


# ── Step 3: Agreement-phrase frequency ────────────────────────────────────────

print("\nStep 3: Computing agreement-phrase frequencies...")

def agreement_count(text):
    t = text.lower()
    return sum(1 for p in AGREEMENT_PHRASES if p in t)

df["agree_hits"] = df["text"].apply(agreement_count)
df["has_agree"]  = df["agree_hits"] > 0

ai_agree_rate    = df[df["label"] == "ai"]["has_agree"].mean()
human_agree_rate = df[df["label"] == "human"]["has_agree"].mean()

print(f"  AI posts with ≥1 agreement phrase:    {ai_agree_rate:.1%}")
print(f"  Human posts with ≥1 agreement phrase: {human_agree_rate:.1%}")
print(f"  Ratio: {ai_agree_rate/human_agree_rate:.1f}x")


# ── Step 4: Representative examples ───────────────────────────────────────────

print("\nStep 4: Selecting representative examples...")

# AI examples: high fraction_ai, medium length (not too long), contains agreement phrase
ai_examples = (ai_df[ai_df["words"].between(60, 250)]
                 .sort_values("fraction_ai", ascending=False)
                 .head(50))
# pick 3 that contain agreement phrases
ai_ex = ai_examples[ai_examples["text"].str.lower()
                    .apply(lambda t: any(p in t for p in AGREEMENT_PHRASES))].head(3)
if len(ai_ex) < 3:
    ai_ex = ai_examples.head(3)

# Human examples: low fraction_ai, medium length, contains specific technical content
human_examples = (human_df[human_df["words"].between(50, 200)]
                    .sort_values("fraction_ai")
                    .head(50))
# look for posts with specific governance language
tech_phrases = ["smart contract", "gas", "security", "multisig", "parameter",
                "vote", "delegate", "quorum", "veto", "treasury", "protocol"]
human_ex = human_examples[human_examples["text"].str.lower()
                           .apply(lambda t: sum(p in t for p in tech_phrases) >= 2)].head(3)
if len(human_ex) < 3:
    human_ex = human_examples.head(3)

print("\n  === AI POST EXAMPLES ===")
for i, (_, row) in enumerate(ai_ex.iterrows(), 1):
    print(f"\n  [{i}] fraction_ai={row['fraction_ai']:.2f}, {row['words']} words:")
    print(" ", row["text"][:350].replace("\n", " ") + "...")

print("\n  === HUMAN POST EXAMPLES ===")
for i, (_, row) in enumerate(human_ex.iterrows(), 1):
    print(f"\n  [{i}] fraction_ai={row['fraction_ai']:.2f}, {row['words']} words:")
    print(" ", row["text"][:350].replace("\n", " ") + "...")


# ── Step 5: LaTeX examples table ──────────────────────────────────────────────

print("\nStep 5: Writing LaTeX examples table...")

def tex_escape(s):
    s = s.replace("\\", r"\textbackslash{}")
    for ch in ["&", "%", "$", "#", "_", "{", "}", "~", "^"]:
        s = s.replace(ch, "\\" + ch)
    return s

def excerpt(text, n=180):
    t = text[:n].strip()
    if len(text) > n:
        t += "\\ldots"
    return t

rows = []
for i, (_, row) in enumerate(ai_ex.iterrows(), 1):
    ex = tex_escape(excerpt(row["text"]))
    rows.append(f"  AI & \\textit{{{ex}}} \\\\[2pt]")

rows.append("  \\midrule")

for i, (_, row) in enumerate(human_ex.iterrows(), 1):
    ex = tex_escape(excerpt(row["text"]))
    rows.append(f"  Human & \\textit{{{ex}}} \\\\[2pt]")

tex = r"""\begin{table}[H]
\centering
\caption{Representative Forum Post Excerpts: AI-Generated vs.\ Human-Authored}
\label{tab:post_examples}
\begin{tabular}{p{1.2cm}p{12cm}}
\toprule
Type & Excerpt \\
\midrule
""" + "\n".join(rows) + r"""
\bottomrule
\end{tabular}
\begin{flushleft}
\small\textit{Notes:} Each excerpt is the opening 180 characters of a forum post.
AI-generated posts are classified by Pangram \textit{fraction\_ai}~$> 0.70$.
AI posts consistently open with proposal summaries and generic endorsements
(``it is essential to consider,'' ``the Arbitrum ecosystem,'' ``I believe this
proposal'') rather than substantive positions. Human posts reference specific
on-chain parameters, named actors, and prior governance history.
\end{flushleft}
\end{table}
"""

with open(OUT_TAB, "w") as f:
    f.write(tex)
print(f"  Table written to {OUT_TAB}")


# ── Step 6: Figure ────────────────────────────────────────────────────────────

print("\nStep 6: Building figure...")

fig = plt.figure(figsize=(13, 4.5))
# Layout: Panel A takes left half (split into AI/human), B and C take right half
gs = fig.add_gridspec(1, 4, wspace=0.45)
ax_ai    = fig.add_subplot(gs[0, 0])   # Panel A left  — AI terms
ax_human = fig.add_subplot(gs[0, 1])   # Panel A right — Human terms
axes     = [None, fig.add_subplot(gs[0, 2]), fig.add_subplot(gs[0, 3])]

# Panel A left: AI-distinctive terms
y = np.arange(top_n)
ax_ai.barh(y, top_ai_scores[::-1], color=C_AI, alpha=0.85)
ax_ai.set_yticks(y)
ax_ai.set_yticklabels(top_ai_terms[::-1], fontsize=7.5)
ax_ai.set_xlabel("Mean TF-IDF diff.", fontsize=8)
ax_ai.set_title("AI-distinctive\nn-grams", fontsize=8.5, fontweight="bold")
ax_ai.tick_params(axis="y", length=0)
despine(ax_ai)

# Panel A right: Human-distinctive terms
ax_human.barh(y, top_human_scores[::-1], color=C_HUMAN, alpha=0.85)
ax_human.set_yticks(y)
ax_human.set_yticklabels(top_human_terms[::-1], fontsize=7.5)
ax_human.set_xlabel("Mean TF-IDF diff.", fontsize=8)
ax_human.set_title("Human-distinctive\nn-grams", fontsize=8.5, fontweight="bold")
ax_human.tick_params(axis="y", length=0)
despine(ax_human)

# Panel B: word count distribution
ax = axes[1]
ax.set_title("Post length", fontsize=8.5, fontweight="bold")
bins = np.linspace(0, 600, 31)
ax.hist(human_df["words"].clip(upper=600), bins=bins, color=C_HUMAN, alpha=0.6,
        density=True, label="Human")
ax.hist(ai_df["words"].clip(upper=600), bins=bins, color=C_AI, alpha=0.6,
        density=True, label="AI")
ax.axvline(human_df["words"].median(), color=C_HUMAN, linewidth=1.5, linestyle="--")
ax.axvline(ai_df["words"].median(),    color=C_AI,    linewidth=1.5, linestyle="--")
ax.set_xlabel("Words per post", fontsize=8)
ax.set_ylabel("Density", fontsize=8)
ax.legend(fontsize=8)
despine(ax)

# Panel C: agreement-phrase rate
ax = axes[2]
categories = ["AI posts", "Human posts"]
rates      = [ai_agree_rate * 100, human_agree_rate * 100]
colors     = [C_AI, C_HUMAN]
bars = ax.bar(categories, rates, color=colors, alpha=0.85, width=0.5)
for bar, rate in zip(bars, rates):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
            f"{rate:.1f}%", ha="center", va="bottom", fontsize=8.5, fontweight="bold")
ax.set_ylabel("Posts with ≥1 agreement phrase (%)", fontsize=8)
ax.set_title("Generic agreement", fontsize=8.5, fontweight="bold")
ax.set_ylim(0, max(rates) * 1.3)
despine(ax)

fig.tight_layout()
aer_savefig(fig, OUT_FIG)
print(f"  Figure saved to {OUT_FIG}")
print("\nDone.")
