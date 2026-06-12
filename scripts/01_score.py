#!/usr/bin/env python3
"""
Score all Arbitrum forum posts with the Pangram AI-detection API.

Reads posts from DuckDB, strips HTML, sends each to Pangram v3, and stores
fraction_ai / fraction_ai_assisted / fraction_human in a post_ai_scores table.

Fully restartable: already-scored posts are skipped.
Posts under MIN_WORDS are recorded as NULL so they aren't re-attempted.

Usage:
    python3 01_score.py
    PANGRAM_API_KEY=<key> python3 01_score.py
"""

import os, re, time, sys
import duckdb
from pangram import Pangram
from datetime import datetime, timezone

HERE      = os.path.dirname(os.path.abspath(__file__))
ROOT      = os.path.dirname(HERE)   # project root
DB_PATH   = os.path.join(ROOT, "data", "arbitrum.db")
MIN_WORDS  = 20
RATE_DELAY = 0.65   # ~1.5 req/sec — conservative to avoid rate limits
SAVE_EVERY = 100    # commit to DuckDB every N processed posts


def load_env_key():
    """Walk up from ROOT looking for a .env file with PANGRAM_API_KEY."""
    path = ROOT
    for _ in range(5):
        env_file = os.path.join(path, ".env")
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("PANGRAM_API_KEY="):
                        return line.split("=", 1)[1].strip()
        path = os.path.dirname(path)
    return ""


def strip_html(html):
    return re.sub(r"<[^>]+>", " ", html or "").strip()


def word_count(text):
    return len(text.split())


def score_text(client, text):
    return client.predict(text)


def setup_table(con):
    con.execute("""
        CREATE TABLE IF NOT EXISTS post_ai_scores (
            post_id              INTEGER PRIMARY KEY,
            fraction_ai          DOUBLE,
            fraction_ai_assisted DOUBLE,
            fraction_human       DOUBLE,
            headline             VARCHAR,
            word_count           INTEGER,
            scored_at            VARCHAR
        )
    """)
    con.commit()


def main():
    api_key = os.environ.get("PANGRAM_API_KEY") or load_env_key()
    if not api_key:
        sys.exit("ERROR: PANGRAM_API_KEY not set. Add it to .env or set the env var.")

    client = Pangram(api_key=api_key)

    print(f"DB: {DB_PATH}")
    con = duckdb.connect(DB_PATH)
    setup_table(con)

    already_scored = con.execute(
        "SELECT COUNT(*) FROM post_ai_scores"
    ).fetchone()[0]
    print(f"Already scored: {already_scored} posts")

    rows = con.execute("""
        SELECT p.id, p.cooked
        FROM posts p
        WHERE p.id NOT IN (SELECT post_id FROM post_ai_scores)
        ORDER BY p.id
    """).fetchall()
    print(f"Posts remaining: {len(rows)}")

    if not rows:
        print("Nothing to do.")
        con.close()
        return

    n_scored  = 0
    n_skipped = 0
    n_errors  = 0
    batch     = []

    def flush(batch, con):
        for record in batch:
            con.execute(
                "INSERT OR REPLACE INTO post_ai_scores VALUES (?,?,?,?,?,?,?)",
                record,
            )
        con.commit()

    for i, (post_id, cooked) in enumerate(rows, 1):
        text = strip_html(cooked)
        wc   = word_count(text)
        now  = datetime.now(timezone.utc).isoformat()

        if wc < MIN_WORDS:
            batch.append((post_id, None, None, None, "too_short", wc, now))
            n_skipped += 1
        else:
            try:
                result = score_text(client, text)
                batch.append((
                    post_id,
                    result.get("fraction_ai"),
                    result.get("fraction_ai_assisted"),
                    result.get("fraction_human"),
                    result.get("headline", ""),
                    wc,
                    now,
                ))
                n_scored += 1
                time.sleep(RATE_DELAY)
            except Exception as e:
                print(f"  ERROR post {post_id}: {e}")
                batch.append((post_id, None, None, None, f"error:{str(e)[:80]}", wc, now))
                n_errors += 1

        if len(batch) >= SAVE_EVERY:
            flush(batch, con)
            batch = []

        if i % 250 == 0 or i == len(rows):
            pct = i / len(rows) * 100
            print(
                f"  [{pct:5.1f}%] {i}/{len(rows)}  "
                f"scored={n_scored}  skipped={n_skipped}  errors={n_errors}"
            )

    if batch:
        flush(batch, con)

    print(f"\nDone.  scored={n_scored}  skipped(too short)={n_skipped}  errors={n_errors}")

    row = con.execute("""
        SELECT
            COUNT(*)                                        AS total,
            AVG(fraction_ai)                               AS avg_ai,
            COUNT(*) FILTER (WHERE fraction_ai >  0.7)    AS ai_written,
            COUNT(*) FILTER (WHERE fraction_ai <= 0.7
                             AND fraction_ai IS NOT NULL)  AS human_written
        FROM post_ai_scores
        WHERE headline != 'too_short' AND headline NOT LIKE 'error:%'
    """).fetchone()

    print(f"\nDB summary (scored posts only):")
    print(f"  Total with scores : {row[0]}")
    print(f"  Avg fraction_ai   : {row[1]:.3f}" if row[1] is not None else "  Avg fraction_ai   : N/A")
    print(f"  AI-written  >0.7  : {row[2]}")
    print(f"  Human-written ≤0.7: {row[3]}")

    con.close()


if __name__ == "__main__":
    main()
