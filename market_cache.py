"""
市场数据缓存管理器 - SQLite本地数据库
每天只调一次API，其余从缓存读取（有效期24小时）
支持: A股(stock)、美股(us_stock)、期货(futures)、虚拟币(crypto)、新闻(news)
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'market_cache.db')
CACHE_HOURS = 24


def init_db():
    """初始化数据库"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS market_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        symbol TEXT NOT NULL,
        data_json TEXT NOT NULL,
        fetched_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        UNIQUE(category, symbol)
    )''')
    c.execute('CREATE INDEX IF NOT EXISTS idx_category ON market_cache(category)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_expires ON market_cache(expires_at)')
    conn.commit()
    conn.close()


def get_cached(category: str, symbol: str) -> dict | None:
    """从缓存读取数据，过期则返回None"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT data_json FROM market_cache
            WHERE category=? AND symbol=? AND expires_at > datetime('now')
        """, (category, symbol))
        row = c.fetchone()
        conn.close()
        if row:
            return json.loads(row['data_json'])
        return None
    except Exception:
        return None


def set_cache(category: str, symbol: str, data: dict):
    """缓存数据，有效期24小时"""
    try:
        now = datetime.now()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("""
            INSERT OR REPLACE INTO market_cache
            (category, symbol, data_json, fetched_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            category, symbol, json.dumps(data, ensure_ascii=False),
            now.strftime('%Y-%m-%d %H:%M:%S'),
            (now + timedelta(hours=CACHE_HOURS)).strftime('%Y-%m-%d %H:%M:%S')
        ))
        conn.commit()
        conn.close()
    except Exception:
        pass


def get_batch(category: str) -> list[dict]:
    """批量读取某类别的所有缓存数据"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT symbol, data_json FROM market_cache
            WHERE category=? AND expires_at > datetime('now')
            ORDER BY symbol
        """, (category,))
        rows = c.fetchall()
        conn.close()
        return [{'symbol': r['symbol'], 'data': json.loads(r['data_json'])} for r in rows]
    except Exception:
        return []


def clear_expired():
    """清理过期数据"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM market_cache WHERE expires_at <= datetime('now')")
        deleted = c.rowcount
        conn.commit()
        conn.close()
        return deleted
    except Exception:
        return 0


def get_stats() -> dict:
    """获取缓存统计信息"""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT category, COUNT(*) as cnt FROM market_cache GROUP BY category")
        categories = {row[0]: row[1] for row in c.fetchall()}
        c.execute("SELECT COUNT(*) FROM market_cache WHERE expires_at > datetime('now')")
        active = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM market_cache")
        total = c.fetchone()[0]
        conn.close()
        return {'categories': categories, 'active': active, 'total': total}
    except Exception:
        return {}


# 初始化
init_db()
