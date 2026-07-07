#!/usr/bin/env python3
"""
数据库初始化脚本
================
创建并初始化市场数据SQLite数据库，包含所有必要的表和查找数据。

用法:
    python init_database.py                  # 使用默认路径
    python init_database.py /path/to/db.db   # 指定路径
"""
import os
import sys
import sqlite3
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("InitDatabase")


def init_database(db_path: str) -> sqlite3.Connection:
    """Initialize the market data database with all tables and seed data."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # Remove old DB if exists (fresh start)
    if os.path.exists(db_path):
        logger.info(f"Removing existing database: {db_path}")
        os.remove(db_path)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    logger.info("Creating tables...")
    
    # 1. Asset classes
    cursor.execute("""
        CREATE TABLE asset_classes (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            name_zh TEXT NOT NULL,
            category TEXT UNIQUE NOT NULL
        )
    """)
    
    # 2. Data sources
    cursor.execute("""
        CREATE TABLE data_sources (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            display_name TEXT,
            category TEXT,
            needs_proxy INTEGER DEFAULT 0,
            reliability REAL DEFAULT 0.8
        )
    """)
    
    # 3. Raw data (append-only)
    cursor.execute("""
        CREATE TABLE raw_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            data_type TEXT NOT NULL,
            source TEXT NOT NULL,
            name TEXT,
            price REAL,
            prev_close REAL,
            open_price REAL,
            high REAL,
            low REAL,
            volume REAL,
            change_pct REAL,
            market_cap REAL,
            pe_ratio REAL,
            pb_ratio REAL,
            turnover_rate REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            proxy_used INTEGER DEFAULT 0,
            status TEXT DEFAULT 'success',
            raw_json TEXT,
            retry_count INTEGER DEFAULT 0,
            quality_score REAL
        )
    """)
    cursor.execute("CREATE INDEX idx_raw_symbol ON raw_data(symbol, data_type)")
    cursor.execute("CREATE INDEX idx_raw_ts ON raw_data(timestamp)")
    
    # 4. Clean data (deduplicated)
    cursor.execute("""
        CREATE TABLE clean_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            data_type TEXT NOT NULL,
            name TEXT,
            latest_price REAL,
            prev_close REAL,
            open_price REAL,
            high REAL,
            low REAL,
            volume REAL,
            change_pct REAL,
            market_cap REAL,
            pe_ratio REAL,
            pb_ratio REAL,
            turnover_rate REAL,
            best_source TEXT,
            last_updated DATETIME,
            data_quality_score REAL,
            UNIQUE(symbol, data_type)
        )
    """)
    
    # 5. Source health
    cursor.execute("""
        CREATE TABLE source_health (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            data_type TEXT NOT NULL,
            last_success DATETIME,
            last_fail DATETIME,
            success_count INTEGER DEFAULT 0,
            fail_count INTEGER DEFAULT 0,
            proxy_needed_count INTEGER DEFAULT 0,
            total_requests INTEGER DEFAULT 0,
            health_score REAL DEFAULT 1.0,
            UNIQUE(source, data_type)
        )
    """)
    
    # 6. Notification log
    cursor.execute("""
        CREATE TABLE notification_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            level TEXT,
            message TEXT,
            proxy_used INTEGER DEFAULT 0,
            source TEXT,
            data_type TEXT,
            symbol TEXT
        )
    """)
    
    conn.commit()
    
    # Seed data
    logger.info("Seeding lookup tables...")
    
    cursor.executemany("INSERT INTO asset_classes VALUES (?, ?, ?, ?)", [
        (1, "US Stock", "美股", "us_stock"),
        (2, "A-Share", "A股", "a_stock"),
        (3, "Futures", "期货", "futures"),
        (4, "Cryptocurrency", "加密货币", "crypto"),
    ])
    
    cursor.executemany("INSERT INTO data_sources VALUES (?, ?, ?, ?, ?, ?)", [
        (1, "sina", "新浪财经", "china", 0, 0.95),
        (2, "tencent", "腾讯财经", "china", 0, 0.95),
        (3, "eastmoney", "东方财富", "china", 0, 0.90),
        (4, "yahoo", "Yahoo Finance", "global", 0, 0.85),
        (5, "yfinance", "yfinance", "global", 0, 0.85),
        (6, "binance", "Binance", "crypto", 0, 0.90),
        (7, "coinbase", "Coinbase", "crypto", 0, 0.85),
    ])
    
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM asset_classes")
    ac_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM data_sources")
    ds_count = cursor.fetchone()[0]
    
    logger.info(f"✅ Database initialized successfully: {db_path}")
    logger.info(f"   Asset classes: {ac_count}")
    logger.info(f"   Data sources: {ds_count}")
    logger.info(f"   Tables: asset_classes, data_sources, raw_data, clean_data, source_health, notification_log")
    
    return conn


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "data", "market_data.db"
    )
    logger.info(f"Initializing database at: {db_path}")
    conn = init_database(db_path)
    conn.close()
    logger.info("Done.")
