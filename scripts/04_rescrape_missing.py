#!/usr/bin/env python3
"""
Scrape the 125 forum threads that are in the figure8 forum cache
but missing from DuckDB's posts table. Inserts directly into the
existing arbitrum.db posts table so Pangram scoring can follow.
"""

import json, time, requests, duckdb, os

HERE       = os.path.dirname(os.path.abspath(__file__))
ROOT       = os.path.dirname(HERE)   # project root
DB_PATH    = os.path.join(ROOT, "data", "arbitrum.db")
CACHE_PATH = os.path.join(ROOT, "data", "figure8_forum_cache.json")
BASE_URL   = "https://forum.arbitrum.foundation"
DELAY      = 1.0  # seconds between requests

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; ArbitrumForumScraper/1.0)",
})

def get(path, params=None):
    url = f"{BASE_URL}{path}"
    resp = session.get(url, params=params, timeout=30)
    resp.raise_for_status()
    time.sleep(DELAY)
    return resp.json()

# ── Find missing topic IDs ────────────────────────────────────────────────────

with open(CACHE_PATH) as f:
    forum_cache = json.load(f)

con = duckdb.connect(DB_PATH)
all_topics_in_db = set(
    int(r[0]) for r in con.execute("SELECT DISTINCT topic_id FROM posts").fetchall()
)

cache_tids = {int(tid) for tid in forum_cache.keys()}
missing_tids = sorted(cache_tids - all_topics_in_db)
print(f"Forum cache: {len(cache_tids)} topics")
print(f"DuckDB:      {len(all_topics_in_db)} topics")
print(f"Missing:     {len(missing_tids)} topics to scrape")

# ── Fetch and insert posts ────────────────────────────────────────────────────

inserted_total = 0
skipped_topics = 0

for i, tid in enumerate(missing_tids, 1):
    posts_all = []
    post_no   = 1
    while True:
        try:
            d = get(f"/t/{tid}/{post_no}.json")
        except requests.HTTPError as e:
            print(f"  [{i}/{len(missing_tids)}] topic {tid}: HTTP {e.response.status_code} — skipping")
            skipped_topics += 1
            break

        chunk = d.get("post_stream", {}).get("posts", [])
        if not chunk:
            break
        posts_all.extend(chunk)
        highest = d.get("highest_post_number", 0)
        last    = chunk[-1]["post_number"] if chunk else post_no
        if last >= highest:
            break
        post_no = last + 1

    if not posts_all:
        continue

    rows = []
    for p in posts_all:
        rows.append((
            p.get("id"),
            tid,
            p.get("post_number"),
            p.get("username", ""),
            p.get("created_at", ""),
            p.get("updated_at", ""),
            p.get("cooked", ""),
            p.get("raw", ""),
            p.get("reply_count", 0),
            p.get("quote_count", 0),
            p.get("incoming_link_count", 0),
            p.get("reads", 0),
            p.get("score", 0.0),
            p.get("like_count", 0),
            p.get("reply_to_post_number"),
            json.dumps(p),
        ))

    con.executemany("""
        INSERT OR IGNORE INTO posts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, rows)
    con.commit()
    inserted_total += len(rows)

    print(f"  [{i}/{len(missing_tids)}] topic {tid}: {len(rows)} posts inserted  "
          f"(total so far: {inserted_total})")

con.close()
print(f"\nDone. {inserted_total} posts inserted across "
      f"{len(missing_tids) - skipped_topics} topics "
      f"({skipped_topics} skipped).")
