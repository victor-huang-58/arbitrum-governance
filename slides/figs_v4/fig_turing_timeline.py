#!/usr/bin/env python3
"""Best-available AI vs. the Turing test — time series for FSIL deck.

Data: Jones & Bergen (UCSD), three measurement waves with consistent
interactive-Turing-test designs:
  Wave 1: arXiv:2310.20216 (Oct 2023)  — best AI: GPT-4, 41% judged human;
          ELIZA 27%; human confederates 63%
  Wave 2: arXiv:2405.08007 (May 2024)  — best AI: GPT-4, 54%; ELIZA 22%;
          humans 67%
  Wave 3: arXiv:2503.23674 (Mar 2025)  — best AI: GPT-4.5 (persona), 73%
          (three-party design: >50% = judged human MORE often than the
          actual human)
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date

NAVY   = "#003057"
ORANGE = "#d55e00"
BLUE   = "#0072b2"
GRAY   = "#999999"
SAND   = "#f0e9d8"

waves      = [date(2023, 10, 15), date(2024, 5, 15), date(2025, 3, 15)]
best_ai    = [41, 54, 73]
ai_labels  = ["GPT-4\n41%", "GPT-4\n54%", "GPT-4.5\n73%"]

fig, ax = plt.subplots(figsize=(9.6, 5.0), dpi=200)

# Chance line
ax.axhline(50, color=GRAY, ls=":", lw=1.4)
ax.text(date(2025, 5, 25), 50.8, "50%: judged human as often as chance",
        fontsize=9, color="#666666", ha="right")

# Structural-break window: QLR break (Nov 25, 2023) to Claude 3 (Mar 4, 2024)
ax.axvspan(date(2023, 11, 25), date(2024, 3, 4), color=ORANGE, alpha=0.15, lw=0)
ax.axvline(date(2023, 11, 6), color=ORANGE, ls="--", lw=1.1)
ax.axvline(date(2024, 3, 4),  color=ORANGE, ls="--", lw=1.1)
ax.text(date(2023, 11, 16), 83, "GPT-4 Turbo\n(Nov 2023)", fontsize=8.5,
        color=ORANGE, ha="center", va="top")
ax.text(date(2024, 3, 14), 83, "Claude 3\n(Mar 2024)", fontsize=8.5,
        color=ORANGE, ha="left", va="top")
ax.text(date(2024, 1, 1), 33, "structural-break\nwindow", fontsize=8.5,
        color=ORANGE, ha="center", style="italic")

# Best-available AI series
ax.plot(waves, best_ai, "-", color=NAVY, lw=2.2, zorder=4)
ax.plot(waves, best_ai, "o", ms=9, color=NAVY, zorder=5)
for x, y, lab in zip(waves, best_ai, ai_labels):
    ax.annotate(lab, (x, y), textcoords="offset points", xytext=(0, 11),
                fontsize=10, color=NAVY, ha="center", fontweight="bold")

ax.set_ylim(30, 85)
ax.set_xlim(date(2023, 6, 1), date(2025, 6, 30))
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
ax.set_ylabel("Share of judges rating the AI as human", fontsize=10.5)
ax.set_title("Best Available AI vs.\\ the Turing Test"
             .replace("\\\\", ""), fontsize=12.5, color=NAVY, weight="bold")
ax.set_title("Best Available AI vs. the Turing Test", fontsize=12.5,
             color=NAVY, weight="bold")
ax.spines[["top", "right"]].set_visible(False)
ax.tick_params(labelsize=9)
ax.grid(axis="y", color="#dddddd", lw=0.6, alpha=0.6)

fig.text(0.01, 0.012,
         "Interactive Turing tests, Jones & Bergen (UCSD): arXiv 2310.20216, "
         "2405.08007, 2503.23674. Best-performing model/prompt per wave. "
         "Wave 3 is a three-party design (>50% = chosen over the actual human).",
         fontsize=7.2, color="#777777")

fig.tight_layout(rect=(0, 0.035, 1, 1))
out = "/Users/jhall390/GaTech Dropbox/Joseph Hall/ArbitrumProject/slides/figs_v4/fig_turing_timeline.png"
fig.savefig(out, bbox_inches="tight")
print("saved", out)
