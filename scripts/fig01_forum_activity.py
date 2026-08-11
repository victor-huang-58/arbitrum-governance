#!/usr/bin/env python3
"""
Figure 1: Forum Participation and Token-Market Co-movement
Journal of Finance paper on Arbitrum governance.

Walk-through:
  1. Pull monthly post/topic counts from DuckDB
  2. Fetch ARB/USD daily price + volume from CryptoCompare (3 batches)
  3. Aggregate price data to monthly (month-end close, sum of daily volumes)
  4. Merge on month, clip to Jan 2023 – Mar 2026
  5. Plot dual-axis figure
"""

import os
import time
import requests
import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import sys as _sys
_sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
from aer_style import apply_aer_style, despine, COLORS, C_HUMAN, C_AI, C_TOTAL, C_SHOCK, savefig as aer_savefig
import freeze
apply_aer_style()
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import numpy as np

HERE    = os.path.dirname(os.path.abspath(__file__))
ROOT    = os.path.dirname(HERE)   # project root
DB_PATH = os.path.join(ROOT, "data", "arbitrum.db")
OUT_DIR = os.path.join(ROOT, "output", "figures")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, "fig01_forum_activity.png")


# ── Step 1: Forum data from DuckDB ────────────────────────────────────────────
# We count posts and new topics per calendar month.
# strftime extracts the year-month string; we cast created_at (stored as a
# VARCHAR ISO-8601 string) to TIMESTAMP first.

print("Step 1: Querying forum data...")
con = duckdb.connect(DB_PATH, read_only=True)

posts_monthly = con.execute("""
    SELECT
        DATE_TRUNC('month', created_at::TIMESTAMP)::DATE AS month,
        COUNT(*) AS post_count
    FROM posts
    WHERE created_at::TIMESTAMP >= '2023-01-01'
      AND created_at::TIMESTAMP <  '2026-04-01'
    GROUP BY 1
    ORDER BY 1
""").df()

topics_monthly = con.execute("""
    SELECT
        DATE_TRUNC('month', created_at::TIMESTAMP)::DATE AS month,
        COUNT(*) AS topic_count
    FROM topics
    WHERE created_at::TIMESTAMP >= '2023-01-01'
      AND created_at::TIMESTAMP <  '2026-04-01'
    GROUP BY 1
    ORDER BY 1
""").df()

con.close()
posts_monthly['month'] = pd.to_datetime(posts_monthly['month'])
topics_monthly['month'] = pd.to_datetime(topics_monthly['month'])

forum = posts_monthly.merge(topics_monthly, on='month', how='outer').sort_values('month')
print(f"  Forum months: {len(forum)}, range: {forum['month'].min()} – {forum['month'].max()}")


# ── Step 2: Fetch ARB/USD daily data from CryptoCompare ──────────────────────
# CryptoCompare returns at most 400 days per call, counting backwards from
# a supplied Unix timestamp (toTs).  We make 3 calls to cover ~1,150 days.
#
# Each row from the API contains:
#   time       – Unix timestamp (start of day, UTC)
#   close      – closing price in USD
#   volumefrom – ARB volume traded that day (denominated in ARB)
#   volumeto   – ARB volume traded that day (denominated in USD) ← we use this

def fetch_crypto_history(to_ts: int, limit: int = 400) -> pd.DataFrame:
    url = "https://min-api.cryptocompare.com/data/v2/histoday"
    params = {"fsym": "ARB", "tsym": "USD", "limit": limit, "toTs": to_ts}
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("Response") != "Success":
        raise RuntimeError(f"CryptoCompare error: {data}")
    rows = data["Data"]["Data"]
    df = pd.DataFrame(rows)[["time", "close", "volumeto"]]
    df["date"] = pd.to_datetime(df["time"], unit="s", utc=True).dt.tz_localize(None)
    df = df.drop(columns="time")
    return df

print("Step 2: Fetching ARB/USD price history (3 API calls)...")

# Batch end-timestamps (Unix seconds):
#   Batch A: up to 2024-03-01  →  covers approx Jun 2023 – Feb 2024
#   Batch B: up to 2025-02-01  →  covers approx Mar 2024 – Jan 2025
#   Batch C: up to 2026-04-01  →  covers approx Feb 2025 – Mar 2026
batch_ends = [
    int(pd.Timestamp("2024-03-01").timestamp()),
    int(pd.Timestamp("2025-02-01").timestamp()),
    int(pd.Timestamp("2026-04-02").timestamp()),
]

def _fetch_price_daily():
    frames = []
    for ts in batch_ends:
        df = fetch_crypto_history(ts, limit=400)
        frames.append(df)
        print(f"  Fetched batch ending {pd.to_datetime(ts, unit='s').date()}: {len(df)} rows")
        time.sleep(1)
    out = (pd.concat(frames)
             .drop_duplicates("date")
             .sort_values("date")
             .reset_index(drop=True))
    out = out[out["close"] > 0]
    return out.assign(date=out["date"].dt.strftime("%Y-%m-%d")).to_dict("records")

price_daily = pd.DataFrame(freeze.frozen_json("fig01_arb_price_daily", _fetch_price_daily))
price_daily["date"] = pd.to_datetime(price_daily["date"])
print(f"  Daily price rows after dedup: {len(price_daily)}, "
      f"range: {price_daily['date'].min().date()} – {price_daily['date'].max().date()}")


# ── Step 3: Aggregate daily → monthly ────────────────────────────────────────
# For price  : we take the last closing price of each month (month-end)
#              This is standard in financial time-series — "month-end close"
# For volume : we sum all daily volumes in the month
#              Total activity during the month is more informative than a single day

price_daily["month"] = price_daily["date"].dt.to_period("M").dt.to_timestamp()

price_monthly = price_daily.groupby("month").agg(
    close=("close", "last"),        # month-end closing price
    volume=("volumeto", "sum")      # total USD volume in the month
).reset_index()

price_monthly["month"] = pd.to_datetime(price_monthly["month"])
print(f"  Monthly price rows: {len(price_monthly)}")


# ── Step 4: Merge forum + market data ────────────────────────────────────────
# We do an outer merge so months present in one but not the other still appear.
# Then clip to Jan 2023 – Mar 2026 inclusive.

df = forum.merge(price_monthly, on="month", how="outer").sort_values("month")
df = df[(df["month"] >= "2023-01-01") & (df["month"] <= "2026-03-31")]
df = df.fillna(0)
print(f"\nMerged dataset: {len(df)} months")
print(df[["month", "post_count", "topic_count", "close", "volume"]].to_string(index=False))


# ── Step 5: Plot ──────────────────────────────────────────────────────────────
# Layout: one set of axes (ax1) for forum activity on the LEFT y-axis.
#         A twin axes (ax2) sharing the same x-axis for price/volume on the RIGHT.
#
# Visual choices:
#   - Post count: filled bars in slate-blue (the dominant series)
#   - Topic count: line with markers in orange (smaller numbers, easier to read as line)
#   - Price: solid dark line on right axis
#   - Volume: light shaded area on right axis (behind price line)

print("\nStep 5: Building supply schedule...")

# ARB circulating supply from published vesting schedule (team + investors only)
# Source: Arbitrum Foundation token distribution
# TGE Mar 16 2023: 1.275B (airdrop 1.162B + DAO airdrop 0.113B)
# Cliff Mar 16 2024: 12 months of team+investor vesting unlocks at once
#   Team (2.694B) + Investors (1.753B) = 4.447B, over 48 months → 92.6M/month
#   Cliff release: 12 × 92.6M = 1.112B
# Note: actual circulating supply is higher (includes Foundation + DAO treasury releases)
MONTHLY_VEST  = 4_447_000_000 / 48
CLIFF_RELEASE = 12 * MONTHLY_VEST
TGE_SUPPLY    = 1_275_000_000
CLIFF_MONTH   = pd.Timestamp("2024-03-01")

supply_rows = []
for m in pd.date_range("2023-01-01", "2026-04-01", freq="MS"):
    if m < pd.Timestamp("2023-03-01"):
        circ = 0.0
    elif m < CLIFF_MONTH:
        circ = TGE_SUPPLY
    elif m == CLIFF_MONTH:
        circ = TGE_SUPPLY + CLIFF_RELEASE
    else:
        months_post = (m.year - CLIFF_MONTH.year) * 12 + (m.month - CLIFF_MONTH.month)
        circ = TGE_SUPPLY + CLIFF_RELEASE + months_post * MONTHLY_VEST
    supply_rows.append({"month": m, "circ_bn": circ / 1e9})
supply_df = pd.DataFrame(supply_rows)

print("\nStep 6: Building figure...")

fig, ax1 = plt.subplots(figsize=(7, 4))
ax2 = ax1.twinx()
ax3 = ax1.twinx()
ax3.spines["right"].set_position(("outward", 60))

BAR_COLOR   = COLORS["blue"]
TOPIC_COLOR = COLORS["orange"]
PRICE_COLOR = COLORS["black"]
VOL_COLOR   = COLORS["sky"]

months = df["month"]

# --- Left axis: forum bars and topic line ---
bar_width = 20  # days, since x is a datetime axis
ax1.bar(months, df["post_count"],  width=bar_width, color=BAR_COLOR,
        alpha=0.75, label="Posts per month", zorder=2)
ax1.set_ylabel("Monthly forum posts")
ax1.set_ylim(0, df["post_count"].max() * 1.25)
ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

# --- Right axis: volume shaded area, then price line on top ---
# We scale volume to billions for readability
vol_bn = df["volume"] / 1e9
ax2.fill_between(months, vol_bn, color=VOL_COLOR, alpha=0.6,
                 label="Monthly trading volume (USD bn)", zorder=1)
ax2.plot(months, df["close"], color=PRICE_COLOR, linewidth=2,
         label="ARB/USD month-end close", zorder=4)

ax2.set_ylabel("ARB/USD price  |  Volume (USD bn)")
ax2.set_ylim(0, max(vol_bn.max(), df["close"].max()) * 1.4)
ax2.yaxis.set_major_formatter(mticker.FuncFormatter(
    lambda x, _: f"${x:.2f}" if x < 5 else f"${x:.1f}bn"
))

# --- X-axis formatting ---
ax1.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b\n%Y"))
ax1.set_xlim(pd.Timestamp("2023-01-01"), pd.Timestamp("2026-04-01"))

# --- Third axis label only (no embedded title — caption in LaTeX) ---

# --- Third axis: circulating supply (team + investors vesting schedule) ---
SUPPLY_COLOR = COLORS["green"]
ax3.step(supply_df["month"], supply_df["circ_bn"], where="post",
         color=SUPPLY_COLOR, linewidth=1.2, linestyle="-.",
         label="Circ. supply — team+investor vesting (approx., B ARB)", zorder=6)
ax3.set_ylabel("Circ. supply (B ARB)", color=SUPPLY_COLOR)
ax3.set_ylim(0, supply_df["circ_bn"].max() * 2.5)
ax3.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f}B"))
ax3.tick_params(axis="y", labelcolor=SUPPLY_COLOR)
ax3.spines["right"].set_edgecolor(SUPPLY_COLOR)

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
lines3, labels3 = ax3.get_legend_handles_labels()
ax1.legend(lines1 + lines2 + lines3, labels1 + labels2 + labels3,
           loc="upper right", framealpha=0.9)

despine(ax1)
fig.tight_layout()
aer_savefig(fig, OUT_PATH)
