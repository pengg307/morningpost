"""
market_cache - Simple SQLite-backed cache for morning report data.
Provides get_cached, set_cache, get_stats functions.
"""
import os
import json
import time
import sqlite3
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "market_cache.db")


def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            category TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            ts REAL NOT NULL,
            PRIMARY KEY (category, key)
        )
    """)
    conn.commit()
    return conn


def set_cache(category: str, key: str, value):
    """Store a value in the cache with current timestamp."""
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO cache (category, key, value, ts) VALUES (?, ?, ?, ?)",
            (category, key, json.dumps(value, ensure_ascii=False), time.time()),
        )
        conn.commit()
    finally:
        conn.close()


def get_cached(category: str, key: str, max_age_hours: int = 6) -> dict | list | None:
    """Retrieve a cached value if it exists and is not older than max_age_hours."""
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT value, ts FROM cache WHERE category = ? AND key = ?",
            (category, key),
        ).fetchone()
        if row is None:
            return None
        value_str, ts = row
        if time.time() - ts > max_age_hours * 3600:
            return None
        return json.loads(value_str)
    except Exception:
        return None
    finally:
        conn.close()


def get_stats() -> dict:
    """Return cache statistics: total entries, categories, oldest/newest."""
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT category, COUNT(*), MIN(ts), MAX(ts) FROM cache GROUP BY category").fetchall()
        total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        cat_stats = {}
        for cat, cnt, min_ts, max_ts in rows:
            cat_stats[cat] = {
                "entries": cnt,
                "oldest": datetime.fromtimestamp(min_ts).strftime("%Y-%m-%d %H:%M") if min_ts else None,
                "newest": datetime.fromtimestamp(max_ts).strftime("%Y-%m-%d %H:%M") if max_ts else None,
            }
        return {"total_entries": total, "categories": cat_stats}
    finally:
        conn.close()
