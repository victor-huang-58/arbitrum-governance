#!/usr/bin/env python3
"""Scrape Arbitrum governance forum via Discourse JSON API and store in DuckDB."""

import os
import time
import json
import sys
import requests
import duckdb

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)   # project root
DB_PATH = os.path.join(ROOT, "data", "arbitrum.db")

BASE_URL = "https://forum.arbitrum.foundation"
DELAY = 1.0  # seconds between requests

TARGET_CATEGORIES = {
    "Proposals",
    "DAO Programs & Initiatives",
    "Voting Rationale & Governance Calls",
    "Security Council",
}

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


def setup_db(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            slug VARCHAR,
            description VARCHAR,
            topic_count INTEGER,
            post_count INTEGER,
            color VARCHAR,
            parent_category_id INTEGER,
            raw JSON
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS topics (
            id INTEGER PRIMARY KEY,
            category_id INTEGER,
            title VARCHAR,
            slug VARCHAR,
            posts_count INTEGER,
            reply_count INTEGER,
            views INTEGER,
            like_count INTEGER,
            created_at VARCHAR,
            last_posted_at VARCHAR,
            pinned BOOLEAN,
            closed BOOLEAN,
            archived BOOLEAN,
            tags JSON,
            raw JSON
        )
    """)
    con.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY,
            topic_id INTEGER,
            post_number INTEGER,
            username VARCHAR,
            created_at VARCHAR,
            updated_at VARCHAR,
            cooked TEXT,
            raw_content TEXT,
            reply_count INTEGER,
            quote_count INTEGER,
            incoming_link_count INTEGER,
            reads INTEGER,
            score DOUBLE,
            like_count INTEGER,
            reply_to_post_number INTEGER,
            raw JSON
        )
    """)
    con.commit()


def fetch_categories(con):
    print("Fetching categories...")
    data = get("/categories.json")
    cats = data.get("category_list", {}).get("categories", [])

    found = {}
    for cat in cats:
        name = cat.get("name", "")
        row = (
            cat.get("id"),
            name,
            cat.get("slug"),
            cat.get("description_text", ""),
            cat.get("topic_count", 0),
            cat.get("post_count", 0),
            cat.get("color", ""),
            cat.get("parent_category_id"),
            json.dumps(cat),
        )
        con.execute("""
            INSERT OR REPLACE INTO categories VALUES (?,?,?,?,?,?,?,?,?)
        """, row)
        if name in TARGET_CATEGORIES:
            found[name] = cat.get("id")
            print(f"  Found target category: {name} (id={cat['id']})")

    con.commit()
    print(f"  Total categories fetched: {len(cats)}")
    return found


def fetch_topics_for_category(con, category_id, category_name):
    """Fetch all topics in a category using pagination."""
    print(f"\nFetching topics for category: {category_name} (id={category_id})")
    page = 0
    total = 0

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
            con.execute("""
                INSERT OR REPLACE INTO topics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, row)

        con.commit()
        total += len(topics)
        print(f"  Page {page}: {len(topics)} topics (total so far: {total})")

        # Check if there's a next page
        more_topics_url = topic_list.get("more_topics_url")
        if not more_topics_url:
            break
        page += 1

    print(f"  Total topics for {category_name}: {total}")
    return total


def fetch_posts_for_topic(con, topic_id):
    """Fetch all posts for a topic, handling pagination."""
    all_posts = []

    try:
        data = get(f"/t/{topic_id}.json")
    except requests.HTTPError as e:
        print(f"    HTTP error fetching topic {topic_id}: {e}")
        return 0

    post_stream = data.get("post_stream", {})
    posts = post_stream.get("posts", [])
    all_posts.extend(posts)

    # Check for remaining post IDs not yet fetched
    stream_ids = post_stream.get("stream", [])
    fetched_ids = {p["id"] for p in posts}
    remaining_ids = [pid for pid in stream_ids if pid not in fetched_ids]

    # Fetch remaining posts in chunks of 20
    chunk_size = 20
    for i in range(0, len(remaining_ids), chunk_size):
        chunk = remaining_ids[i:i + chunk_size]
        try:
            params = {"post_ids[]": chunk}
            resp = session.get(f"{BASE_URL}/t/{topic_id}/posts.json", params=params, timeout=30)
            resp.raise_for_status()
            time.sleep(DELAY)
            chunk_data = resp.json()
            chunk_posts = chunk_data.get("post_stream", {}).get("posts", [])
            all_posts.extend(chunk_posts)
        except requests.HTTPError as e:
            print(f"    HTTP error fetching post chunk for topic {topic_id}: {e}")
            break

    # Insert posts
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
        con.execute("""
            INSERT OR REPLACE INTO posts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, row)

    con.commit()
    return len(all_posts)


def main():
    print(f"Connecting to DuckDB at {DB_PATH}")
    con = duckdb.connect(DB_PATH)
    setup_db(con)

    # Fetch and store categories
    category_map = fetch_categories(con)

    if not category_map:
        print("ERROR: No target categories found. Listing all available categories:")
        data = get("/categories.json")
        for cat in data.get("category_list", {}).get("categories", []):
            print(f"  - {cat['name']} (id={cat['id']})")
        sys.exit(1)

    # Fetch topics for each target category
    topic_ids = []
    for cat_name, cat_id in category_map.items():
        fetch_topics_for_category(con, cat_id, cat_name)

    # Get all topic IDs we need to scrape posts for
    rows = con.execute("""
        SELECT DISTINCT t.id FROM topics t
        JOIN categories c ON t.category_id = c.id
        WHERE c.name IN ('Proposals', 'DAO Programs & Initiatives', 'Voting Rationale & Governance Calls', 'Security Council')
        ORDER BY t.id
    """).fetchall()
    topic_ids = [r[0] for r in rows]

    print(f"\nFetching posts for {len(topic_ids)} topics...")
    total_posts = 0
    for i, topic_id in enumerate(topic_ids, 1):
        n = fetch_posts_for_topic(con, topic_id)
        total_posts += n
        if i % 10 == 0 or i == len(topic_ids):
            print(f"  Progress: {i}/{len(topic_ids)} topics, {total_posts} posts so far")

    # Summary
    print("\n=== Scrape Complete ===")
    counts = con.execute("""
        SELECT
            (SELECT COUNT(*) FROM categories) as categories,
            (SELECT COUNT(*) FROM topics) as topics,
            (SELECT COUNT(*) FROM posts) as posts
    """).fetchone()
    print(f"  Categories: {counts[0]}")
    print(f"  Topics:     {counts[1]}")
    print(f"  Posts:      {counts[2]}")

    # Per-category breakdown
    print("\nTopics per category:")
    rows = con.execute("""
        SELECT c.name, COUNT(t.id) as topic_count, SUM(t.posts_count) as post_count
        FROM categories c
        LEFT JOIN topics t ON t.category_id = c.id
        WHERE c.name IN ('Proposals', 'DAO Programs & Initiatives', 'Voting Rationale & Governance Calls', 'Security Council')
        GROUP BY c.name
        ORDER BY topic_count DESC
    """).fetchall()
    for r in rows:
        print(f"  {r[0]}: {r[1]} topics, ~{r[2]} posts")

    con.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
