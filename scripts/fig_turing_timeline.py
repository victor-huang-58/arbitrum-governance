#!/usr/bin/env python3
"""
fig_turing_timeline: independent (non-vendor) evidence for the AI
indistinguishability threshold.

Best-available-AI Turing-test pass rate (share of interrogators who judged the
AI to be human) across three studies, with the human baseline (~66%), the 50%
chance line, and the November 2023-March 2024 capability-threshold window shaded.

DATA IS HARD-CODED from the cited papers (no database needed):
  - Jones & Bergen (2023/NAACL 2024), "Does GPT-4 pass the Turing test?":
        GPT-4 best prompt 49.7%   (public online, 2-player; humans 66%, ELIZA 22%)
  - Jones & Bergen (2024, FAccT 2025), "People cannot distinguish GPT-4 ...":
        GPT-4 54%                  (randomized, preregistered 2-player; humans 67%)
  - Jones & Bergen (2025, PNAS), "Large Language Models Pass the Turing Test":
        GPT-4.5 73%                (3-player; PERSONA-prompted; above human baseline)

CAVEATS (stated in the caption): the three studies use different designs
(online vs. controlled 2-player vs. 3-player) and the 2025 point requires
prompting the model to adopt a humanlike persona; the connecting line indicates
the frontier over time, not a single controlled panel.
"""
import os, sys
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, savefig as aer_savefig
apply_aer_style()

ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, "fig_turing_timeline.png")

# ── Verified data points (date, pass-rate %, label) ──────────────────────────
points = [
    (datetime(2023, 10, 1), 49.7, "GPT-4\n(2023, online 2-player)"),
    (datetime(2024, 5, 1),  54.0, "GPT-4\n(2024, controlled 2-player)"),
    (datetime(2025, 3, 1),  73.0, "GPT-4.5\n(2025, 3-player, persona)"),
]
dates = [p[0] for p in points]
rates = [p[1] for p in points]
labels = [p[2] for p in points]

HUMAN_BASELINE = 66.0   # ~66-67% across the two controlled studies
CHANCE = 50.0
WIN_START = datetime(2023, 11, 6)   # GPT-4 Turbo
WIN_END   = datetime(2024, 3, 4)    # Claude 3

fig, ax = plt.subplots(figsize=(7.2, 4.2))

# capability-threshold window
ax.axvspan(WIN_START, WIN_END, color=COLORS["orange"], alpha=0.12, zorder=0)
ax.text(WIN_START, 96, "  capability-threshold window\n  (GPT-4 Turbo → Claude 3)",
        fontsize=7.5, va="top", ha="left", color=COLORS["orange"])

# reference lines
ax.axhline(CHANCE, ls="--", lw=1.0, color=COLORS["gray"], zorder=1)
ax.text(datetime(2025, 6, 1), CHANCE + 1.2, "chance (50%)", fontsize=8,
        ha="right", color=COLORS["gray"])
ax.axhline(HUMAN_BASELINE, ls=":", lw=1.0, color=COLORS["black"], zorder=1)
ax.text(datetime(2025, 6, 1), HUMAN_BASELINE + 1.2, "human baseline (~66%)",
        fontsize=8, ha="right", color=COLORS["black"])

# frontier line + points
ax.plot(dates, rates, "-", color=COLORS["blue"], lw=1.4, zorder=3, alpha=0.7)
ax.scatter(dates, rates, s=70, color=COLORS["blue"], zorder=4,
           edgecolor="white", linewidth=1.0)
for (d, r, lab) in points:
    dy = 10 if r < 60 else -14
    va = "bottom" if dy > 0 else "top"
    ax.annotate(f"{r:.1f}%", (d, r), textcoords="offset points",
                xytext=(0, 6 if dy > 0 else -6), ha="center", va=va,
                fontsize=9, fontweight="bold", color=COLORS["blue"])
    ax.annotate(lab, (d, r), textcoords="offset points", xytext=(0, dy + (6 if dy>0 else -6)),
                ha="center", va=va, fontsize=7.5, color=COLORS["gray"])

ax.set_ylim(15, 100)
ax.set_xlim(datetime(2023, 6, 1), datetime(2025, 7, 1))
ax.set_ylabel("Share judged human (\\%)" if False else "Share judged human (%)")
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b '%y"))
plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
despine(ax)

aer_savefig(fig, OUT_PATH)
print(f"Saved -> {OUT_PATH}")
