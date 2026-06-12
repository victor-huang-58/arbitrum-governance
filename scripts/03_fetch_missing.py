#!/usr/bin/env python3
"""Fetch missing categories: DAO Programs & Initiatives and Voting Rationale & Governance Calls."""

import os
import time
import json
import requests
import duckdb

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)   # project root
DB_PATH = os.path.join(ROOT, "data", "arbitrum.db")

BASE_URL = "https://forum.arbitrum.foundation"
DELAY = 1.0

MISSING = {
    "DAO Programs & Initiatives": 16,
    "Voting Rationale & Governance Calls": 6,
}

session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; ArbitrumForumScraper/1.0)",
})


def get(path, params=None, retries=3):
    url = f"{BASE_URL}{path}"
    for attempt in range(retries):
        try:
            resp = session.get(url, params=params, timeout=30)
            resp.raise_for_status()
            time.sleep(DELAY)
            return resp.json()
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt < retries - 1:
                wait = 10 * (attempt + 1)
                print(f"    Connection error ({e}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def fetch_topics_for_category(con, category_id, category_name):
    print(f"\nFetching topics for: {category_name} (id={category_id})")
    # Get already-fetched topic IDs
    existing = {r[0] for r in con.execute("SELECT id FROM topics").fetchall()}
    page = 0
    total = 0
    new_topic_ids = []

    while True:
        try:
            data = get(f"/c/{category_id}/l/latest.json", params={"page": page})
        except requests.HTTPError as e:
            print(f"  HTTP error on page {page}: {e}")
            break

        topic_list = data.get("topic_list", {})
        topics = topic_list.get("topics", [])
        if not topics:
            break

        for t in topics:
            tags = t.get("tags", [])
            row = (
                t.get("id"),
                t.get("category_id", category_id),
                t.get("title", ""),
                t.get("slug", ""),
                t.get("posts_count", 0),
                t.get("reply_count", 0),
                t.get("views", 0),
                t.get("like_count", 0),
                t.get("created_at", ""),
                t.get("last_posted_at", ""),
                t.get("pinned", False),
                t.get("closed", False),
                t.get("archived", False),
                json.dumps(tags),
                json.dumps(t),
            )
            con.execute("INSERT OR REPLACE INTO topics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
            if t.get("id") not in existing:
                new_topic_ids.append(t.get("id"))

        con.commit()
        total += len(topics)
        print(f"  Page {page}: {len(topics)} topics")

        more_topics_url = topic_list.get("more_topics_url")
        if not more_topics_url:
            break
        page += 1

    print(f"  Total topics: {total}, new: {len(new_topic_ids)}")
    return new_topic_ids


def fetch_posts_for_topic(con, topic_id):
    # Skip if we already have posts for this topic
    existing_count = con.execute(
        "SELECT COUNT(*) FROM posts WHERE topic_id = ?", [topic_id]
    ).fetchone()[0]
    if existing_count > 0:
        return 0

    all_posts = []
    try:
        data = get(f"/t/{topic_id}.json")
    except requests.HTTPError as e:
        print(f"    HTTP error fetching topic {topic_id}: {e}")
        return 0

    post_stream = data.get("post_stream", {})
    posts = post_stream.get("posts", [])
    all_posts.extend(posts)

    stream_ids = post_stream.get("stream", [])
    fetched_ids = {p["id"] for p in posts}
    remaining_ids = [pid for pid in stream_ids if pid not in fetched_ids]

    chunk_size = 20
    for i in range(0, len(remaining_ids), chunk_size):
        chunk = remaining_ids[i:i + chunk_size]
        try:
            resp = session.get(f"{BASE_URL}/t/{topic_id}/posts.json",
                               params={"post_ids[]": chunk}, timeout=30)
            resp.raise_for_status()
            time.sleep(DELAY)
            chunk_posts = resp.json().get("post_stream", {}).get("posts", [])
            all_posts.extend(chunk_posts)
        except requests.HTTPError as e:
            print(f"    Chunk error for topic {topic_id}: {e}")
            break

    for p in all_posts:
        row = (
            p.get("id"),
            topic_id,
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
        )
        con.execute("INSERT OR REPLACE INTO posts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row)

    con.commit()
    return len(all_posts)


def main():
    con = duckdb.connect(DB_PATH)

    all_new_topic_ids = []
    for cat_name, cat_id in MISSING.items():
        new_ids = fetch_topics_for_category(con, cat_id, cat_name)
        all_new_topic_ids.extend(new_ids)

    print(f"\nFetching posts for {len(all_new_topic_ids)} new topics...")
    total_posts = 0
    for i, topic_id in enumerate(all_new_topic_ids, 1):
        n = fetch_posts_for_topic(con, topic_id)
        total_posts += n
        if i % 10 == 0 or i == len(all_new_topic_ids):
            print(f"  Progress: {i}/{len(all_new_topic_ids)} topics, {total_posts} posts")

    print("\n=== Final Totals ===")
    counts = con.execute("""
        SELECT
            (SELECT COUNT(*) FROM categories) as categories,
            (SELECT COUNT(*) FROM topics) as topics,
            (SELECT COUNT(*) FROM posts) as posts
    """).fetchone()
    print(f"  Categories: {counts[0]}")
    print(f"  Topics:     {counts[1]}")
    print(f"  Posts:      {counts[2]}")

    print("\nTopics per target category:")
    rows = con.execute("""
        SELECT c.name, COUNT(DISTINCT t.id) as topics, SUM(t.posts_count) as approx_posts
        FROM categories c
        LEFT JOIN topics t ON t.category_id = c.id
        WHERE c.name IN (
            'Proposals', 'DAO Programs & Initiatives',
            'Voting Rationale & Governance Calls', 'Security Council'
        )
        GROUP BY c.name ORDER BY topics DESC
    """).fetchall()
    for r in rows:
        print(f"  {r[0]}: {r[1]} topics, ~{r[2]} posts")

    con.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
