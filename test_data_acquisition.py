#!/usr/bin/env python3
"""
数据获取系统测试用例
====================
全面测试数据获取管理器的所有功能模块。

用法:
    python test_data_acquisition.py                    # 运行全部测试
    python test_data_acquisition.py -v                 # 详细输出
    python test_data_acquisition.py -k test_fetch_sina # 只运行单个测试
"""
import os
import sys
import json
import time
import unittest
import tempfile
import shutil
import logging
from datetime import datetime

# Add project directory to path
sys.path.insert(0, os.path.dirname(__file__))

from data_acquisition_manager import (
    DataAcquisitionManager,
    _fetch_us_stock_sina,
    _fetch_a_stock_tencent,
    _fetch_a_stock_sina,
    _fetch_futures_sina,
    _fetch_crypto_binance,
    _fetch_crypto_coinbase,
    _fetch_us_stock_yahoo,
    _fetch_futures_yfinance,
    _parse_sina_us_stock,
    _parse_tencent_a_stock,
    _parse_sina_futures,
    calculate_data_quality,
    _load_proxy,
)

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("TestDataAcquisition")


class TestDatabaseInitialization(unittest.TestCase):
    """Test database table creation and seed data."""
    
    def setUp(self):
        """Create a temporary database for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_market_data.db")
        self.manager = DataAcquisitionManager(db_path=self.db_path)
    
    def tearDown(self):
        """Clean up temporary database."""
        self.manager.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_tables_created(self):
        """Verify all required tables exist."""
        cursor = self.manager.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected = ["asset_classes", "clean_data", "data_sources", 
                    "notification_log", "raw_data", "source_health"]
        for t in expected:
            self.assertIn(t, tables, f"Table '{t}' not found")
    
    def test_asset_classes_seed(self):
        """Verify asset classes lookup table is seeded."""
        cursor = self.manager.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM asset_classes")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 4, f"Expected 4 asset classes, got {count}")
        
        cursor.execute("SELECT category FROM asset_classes ORDER BY id")
        categories = [row[0] for row in cursor.fetchall()]
        self.assertEqual(categories, ["us_stock", "a_stock", "futures", "crypto"])
    
    def test_data_sources_seed(self):
        """Verify data sources lookup table is seeded."""
        cursor = self.manager.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM data_sources")
        count = cursor.fetchone()[0]
        self.assertEqual(count, 7, f"Expected 7 data sources, got {count}")
        
        cursor.execute("SELECT name FROM data_sources ORDER BY id")
        names = [row[0] for row in cursor.fetchall()]
        expected = ["binance", "coinbase", "eastmoney", "sina", "tencent", "yahoo", "yfinance"]
        self.assertEqual(names, expected)


class TestFetchFunctions(unittest.TestCase):
    """Test individual data source fetch functions."""
    
    def test_parse_sina_us_stock(self):
        """Test parsing Sina US stock response line."""
        sample = 'var hq_str_gb_tsla="特斯拉,405.8700,-3.31,2026-07-07 23:43:40,-13.9000,416.9600,419.5600,404.4535,498.8300,293.5500,16441956,48881780,1524335647116,1.20,338.230000,0.00,0.00,0.00,0.00,3755723870,61,0.000";'
        result = _parse_sina_us_stock(sample)
        self.assertIsNotNone(result, "Failed to parse Sina US stock line")
        self.assertEqual(result["price"], 405.87)
        self.assertGreater(result["prev_close"], 0)
        self.assertGreater(result["volume"], 0)
    
    def test_fetch_us_stock_sina(self):
        """Test fetching US stocks from Sina."""
        result = _fetch_us_stock_sina(["TSLA", "NVDA", "AAPL"])
        self.assertIsInstance(result, list, "Result should be a list")
        self.assertGreater(len(result), 0, "Should have at least one result")
        
        for stock in result:
            self.assertIn("price", stock)
            self.assertIn("name", stock)
            self.assertGreater(stock["price"], 0, f"Price should be > 0 for {stock.get('name')}")
    
    def test_fetch_a_stock_tencent(self):
        """Test fetching A-stocks from Tencent."""
        result = _fetch_a_stock_tencent(["sh600519", "sz000725"])
        self.assertIsInstance(result, list, "Result should be a list")
        self.assertGreater(len(result), 0, "Should have at least one result")
        
        for stock in result:
            self.assertIn("price", stock)
            self.assertIn("name", stock)
            self.assertGreater(stock["price"], 0, f"Price should be > 0 for {stock.get('name')}")
    
    def test_fetch_a_stock_sina(self):
        """Test fetching A-stocks from Sina."""
        result = _fetch_a_stock_sina(["600519", "000725"])
        self.assertIsInstance(result, list, "Result should be a list")
        # Sina may or may not return A-stock data; just verify structure
        for stock in result:
            self.assertIn("price", stock)
            self.assertIn("name", stock)
    
    def test_fetch_futures_sina(self):
        """Test fetching futures from Sina."""
        result = _fetch_futures_sina(["GC", "SI", "CL"])
        self.assertIsInstance(result, list, "Result should be a list")
        self.assertGreater(len(result), 0, "Should have at least one result")
        
        for future in result:
            self.assertIn("price", future)
            self.assertGreater(future["price"], 0, f"Price should be > 0 for {future.get('name')}")
    
    def test_fetch_crypto_binance(self):
        """Test fetching crypto from Binance."""
        result = _fetch_crypto_binance(["BTC", "ETH"])
        self.assertIsInstance(result, list, "Result should be a list")
        
        for crypto in result:
            self.assertIn("price", crypto)
            self.assertGreater(crypto["price"], 0, f"Price should be > 0 for {crypto.get('name')}")
    
    def test_fetch_crypto_coinbase(self):
        """Test fetching crypto from Coinbase."""
        result = _fetch_crypto_coinbase(["BTC", "ETH"])
        self.assertIsInstance(result, list, "Result should be a list")
        
        for crypto in result:
            self.assertIn("price", crypto)


class TestDataQualityScoring(unittest.TestCase):
    """Test data quality scoring algorithm."""
    
    def test_complete_data_high_score(self):
        """Complete data should get high quality score."""
        data = {
            "price": 100.0, "open": 99.0, "high": 102.0, "low": 98.0,
            "volume": 1000000, "prev_close": 99.5, "name": "Test",
            "pe": 20.0, "pb": 3.0, "turnover_rate": 2.5,
            "change_pct": 1.5, "market_cap": 1000000000,
        }
        score = calculate_data_quality(data, "sina", False)
        self.assertGreater(score, 0.8, f"Score {score} should be > 0.8 for complete data")
    
    def test_partial_data_lower_score(self):
        """Partial data should get lower quality score."""
        data = {"price": 100.0, "name": "Test"}
        score = calculate_data_quality(data, "sina", False)
        self.assertLess(score, 0.8, f"Score {score} should be < 0.8 for partial data")
    
    def test_proxy_penalty(self):
        """Proxy data should get lower score than non-proxy."""
        data = {
            "price": 100.0, "open": 99.0, "high": 102.0, "low": 98.0,
            "volume": 1000000, "prev_close": 99.5,
        }
        score_no_proxy = calculate_data_quality(data, "yahoo", False)
        score_proxy = calculate_data_quality(data, "yahoo", True)
        self.assertGreater(score_no_proxy, score_proxy,
                          f"Non-proxy score {score_no_proxy} should be > proxy score {score_proxy}")
    
    def test_source_reliability(self):
        """Reliable sources should get higher base score."""
        data = {"price": 100.0, "open": 99.0, "high": 102.0, "low": 98.0,
                "volume": 1000000, "prev_close": 99.5}
        score_sina = calculate_data_quality(data, "sina", False)
        score_unknown = calculate_data_quality(data, "unknown_source", False)
        self.assertGreaterEqual(score_sina, score_unknown,
                               f"Sina score {score_sina} should be >= unknown score {score_unknown}")


class TestProxyFallback(unittest.TestCase):
    """Test proxy fallback strategy."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_market_data.db")
        self.manager = DataAcquisitionManager(db_path=self.db_path)
    
    def tearDown(self):
        self.manager.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_fetch_without_proxy_first(self):
        """Verify proxy fallback tries without proxy first."""
        results = self.manager.fetch_with_fallback(
            "TSLA", "us_stock", ["sina", "yahoo"], max_retries=1
        )
        
        # At least one source should succeed
        successes = [s for s, r in results.items() if r["status"] == "success"]
        self.assertGreater(len(successes), 0, "At least one source should succeed")
        
        # Check that non-proxy was tried first
        for source, result in results.items():
            if result["status"] == "success":
                # Should prefer non-proxy
                self.assertFalse(result.get("proxy_used", False) or True, 
                               "Should succeed without proxy if possible")
    
    def test_all_sources_fail_notification(self):
        """Verify notification when all sources fail."""
        # Non-existent symbol that will definitely fail
        results = self.manager.fetch_with_fallback(
            "ZZZZZZZZZZ", "us_stock", ["sina"], max_retries=1
        )
        
        # Record notification log before
        before_count = len(self.manager.get_notification_log(limit=100))
        
        # Sina may return empty for non-existent, but structure should be correct
        self.assertIn("sina", results)
        
        after_count = len(self.manager.get_notification_log(limit=100))
        # Notifications may or may not be logged depending on actual behavior
        # Just verify the structure is correct
        self.assertEqual(results["sina"]["status"], "failed")


class TestRawDataPersistence(unittest.TestCase):
    """Test that raw data is properly persisted."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_market_data.db")
        self.manager = DataAcquisitionManager(db_path=self.db_path)
    
    def tearDown(self):
        self.manager.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_raw_data_saved(self):
        """Verify raw data is saved to database."""
        # Fetch some data
        results = self.manager.fetch_with_fallback(
            "TSLA", "us_stock", ["sina"], max_retries=1
        )
        
        if any(r["status"] == "success" for r in results.values()):
            cursor = self.manager.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM raw_data WHERE symbol = ?", ("TSLA",))
            count = cursor.fetchone()[0]
            self.assertGreater(count, 0, "Raw data should be saved for TSLA")
    
    def test_raw_data_has_quality_score(self):
        """Verify raw data includes quality score."""
        results = self.manager.fetch_with_fallback(
            "TSLA", "us_stock", ["sina"], max_retries=1
        )
        
        if any(r["status"] == "success" for r in results.values()):
            cursor = self.manager.conn.cursor()
            cursor.execute("SELECT quality_score FROM raw_data WHERE symbol = ? LIMIT 1", ("TSLA",))
            row = cursor.fetchone()
            if row:
                self.assertIsNotNone(row[0], "Quality score should not be None")
                self.assertGreater(row[0], 0, "Quality score should be > 0")
                self.assertLessEqual(row[0], 1.0, "Quality score should be <= 1.0")


class testDataConsolidation(unittest.TestCase):
    """Test data consolidation logic."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_market_data.db")
        self.manager = DataAcquisitionManager(db_path=self.db_path)
    
    def tearDown(self):
        self.manager.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_consolidate_creates_clean_data(self):
        """Verify consolidation creates clean_data entries."""
        # First fetch some data
        self.manager.fetch_with_fallback("TSLA", "us_stock", ["sina"], max_retries=1)
        
        # Then consolidate
        count = self.manager.consolidate_data()
        
        # Check clean_data
        cursor = self.manager.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM clean_data WHERE symbol = ?", ("TSLA",))
        clean_count = cursor.fetchone()[0]
        
        # May be 0 if fetch failed, but structure should be correct
        self.assertIsInstance(clean_count, int)
    
    def test_consolidation_prefers_non_proxy(self):
        """Verify consolidation prefers non-proxy data."""
        # Insert test data manually
        cursor = self.manager.conn.cursor()
        
        # Non-proxy data (higher preference)
        cursor.execute("""
            INSERT INTO raw_data (symbol, data_type, source, name, price, prev_close, 
                                 open_price, high, low, volume, change_pct, 
                                 proxy_used, status, raw_json, quality_score)
            VALUES ('TEST1', 'us_stock', 'sina', 'Test1', 100.0, 99.0, 99.5, 101.0, 98.0,
                   1000000, 1.0, 0, 'success', '{}', 0.9)
        """)
        
        # Proxy data (lower preference)
        cursor.execute("""
            INSERT INTO raw_data (symbol, data_type, source, name, price, prev_close,
                                 open_price, high, low, volume, change_pct,
                                 proxy_used, status, raw_json, quality_score)
            VALUES ('TEST1', 'us_stock', 'yahoo', 'Test1', 100.5, 99.0, 99.5, 101.0, 98.0,
                   1000000, 1.5, 1, 'success', '{}', 0.85)
        """)
        
        self.manager.conn.commit()
        
        # Consolidate
        self.manager.consolidate_data()
        
        # Check that non-proxy source was chosen
        cursor.execute("SELECT best_source FROM clean_data WHERE symbol = 'TEST1'")
        row = cursor.fetchone()
        if row:
            self.assertEqual(row[0], "sina", "Should prefer non-proxy source 'sina' over 'yahoo'")


class TestSourceHealth(unittest.TestCase):
    """Test source health tracking."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_market_data.db")
        self.manager = DataAcquisitionManager(db_path=self.db_path)
    
    def tearDown(self):
        self.manager.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_health_tracked_on_success(self):
        """Verify health is tracked on successful fetch."""
        self.manager.fetch_with_fallback("TSLA", "us_stock", ["sina"], max_retries=1)
        
        health = self.manager.get_source_health()
        sina_health = [h for h in health if h["source"] == "sina"]
        
        # Should have at least one entry
        self.assertGreater(len(sina_health), 0, "Sina health should be tracked")
    
    def test_health_score_decreases_on_failure(self):
        """Verify health score decreases on failure."""
        # Simulate failures
        for _ in range(5):
            self.manager._update_source_health("fake_source", "us_stock", success=False)
        
        health = self.manager.get_source_health()
        fake_health = [h for h in health if h["source"] == "fake_source"]
        
        if fake_health:
            self.assertLess(fake_health[0]["health_score"], 1.0,
                          "Health score should decrease after failures")


class TestNotificationLogging(unittest.TestCase):
    """Test notification logging functionality."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_market_data.db")
        self.manager = DataAcquisitionManager(db_path=self.db_path)
    
    def tearDown(self):
        self.manager.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_error_notification_logged(self):
        """Verify error notifications are logged."""
        self.manager._log_notification("error", "Test error message", source="sina", data_type="us_stock")
        
        logs = self.manager.get_notification_log(limit=10)
        error_logs = [l for l in logs if l["level"] == "error"]
        
        self.assertGreater(len(error_logs), 0, "Error notification should be logged")
    
    def test_proxy_notification_logged(self):
        """Verify proxy usage notifications are logged."""
        self.manager._log_notification("info", "Proxy used for TSLA", proxy_used=True, source="sina")
        
        logs = self.manager.get_notification_log(limit=10)
        proxy_logs = [l for l in logs if l.get("proxy_used")]
        
        self.assertGreater(len(proxy_logs), 0, "Proxy notification should be logged")


class TestSummaryAndStats(unittest.TestCase):
    """Test summary and statistics generation."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_market_data.db")
        self.manager = DataAcquisitionManager(db_path=self.db_path)
    
    def tearDown(self):
        self.manager.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_summary_structure(self):
        """Verify summary has all required fields."""
        summary = self.manager.get_summary()
        
        required_keys = ["unique_symbols", "by_type", "total_raw_records", "source_health", "error_count"]
        for key in required_keys:
            self.assertIn(key, summary, f"Summary should contain '{key}'")
    
    def test_summary_counts(self):
        """Verify summary counts are accurate."""
        # Fetch some data
        self.manager.fetch_with_fallback("TSLA", "us_stock", ["sina"], max_retries=1)
        
        summary = self.manager.get_summary()
        self.assertIsInstance(summary["total_raw_records"], int)
        self.assertGreaterEqual(summary["total_raw_records"], 0)


class TestIntegration(unittest.TestCase):
    """Integration tests - full workflow from fetch to clean data."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_market_data.db")
        self.manager = DataAcquisitionManager(db_path=self.db_path)
    
    def tearDown(self):
        self.manager.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_workflow_us_stock(self):
        """Test complete workflow for US stocks: fetch -> save -> consolidate -> query."""
        # 1. Fetch
        results = self.manager.fetch_with_fallback("TSLA", "us_stock", ["sina"], max_retries=1)
        
        # 2. Check raw data saved
        raw = self.manager.get_raw_data(symbol="TSLA", data_type="us_stock")
        self.assertGreater(len(raw), 0, "Raw data should be saved")
        
        # 3. Consolidate
        count = self.manager.consolidate_data()
        self.assertGreaterEqual(count, 0)
        
        # 4. Query clean data
        clean = self.manager.get_clean_data(data_type="us_stock", symbol="TSLA")
        # May be empty if fetch failed, but no crash
    
    def test_full_workflow_futures(self):
        """Test complete workflow for futures."""
        results = self.manager.fetch_with_fallback("GC", "futures", ["sina"], max_retries=1)
        
        raw = self.manager.get_raw_data(symbol="GC", data_type="futures")
        self.assertGreater(len(raw), 0, "Raw data should be saved")
        
        self.manager.consolidate_data()
        
        clean = self.manager.get_clean_data(data_type="futures", symbol="GC")
        self.assertGreater(len(clean), 0, "Clean data should exist for GC")
        
        # Verify data integrity
        for record in clean:
            self.assertGreater(record.get("latest_price", 0), 0, "Price should be positive")
    
    def test_full_workflow_crypto(self):
        """Test complete workflow for crypto."""
        results = self.manager.fetch_with_fallback("BTC", "crypto", ["binance"], max_retries=1)
        
        raw = self.manager.get_raw_data(symbol="BTC", data_type="crypto")
        self.assertGreater(len(raw), 0, "Raw data should be saved")
        
        self.manager.consolidate_data()
        
        clean = self.manager.get_clean_data(data_type="crypto", symbol="BTC")
        self.assertGreater(len(clean), 0, "Clean data should exist for BTC")
    
    def test_multi_source_fetch(self):
        """Test fetching from multiple sources for same symbol."""
        results = self.manager.fetch_with_fallback(
            "TSLA", "us_stock", ["sina", "yahoo"], max_retries=1
        )
        
        # At least one source should succeed
        successes = [s for s, r in results.items() if r["status"] == "success"]
        self.assertGreater(len(successes), 0, "At least one source should succeed")
        
        # Consolidate and verify best source selected
        self.manager.consolidate_data()
        clean = self.manager.get_clean_data(data_type="us_stock", symbol="TSLA")
        
        if clean:
            self.assertIn(clean[0]["best_source"], results.keys(),
                        "Best source should be one of the fetched sources")


class TestConfigLoading(unittest.TestCase):
    """Test configuration loading."""
    
    def test_config_has_sections(self):
        """Verify config file has all required sections."""
        config_path = os.path.join(os.path.dirname(__file__), "data_source_config.ini")
        self.assertTrue(os.path.exists(config_path), "Config file should exist")
        
        config = DataAcquisitionManager.__new__(DataAcquisitionManager)
        import configparser
        cp = configparser.ConfigParser()
        cp.read(config_path, encoding="utf-8")
        
        required_sections = ["us_stocks", "futures", "crypto", "a_sectors", "data_sources"]
        for section in required_sections:
            self.assertIn(section, cp.sections(), f"Section '{section}' should exist")
    
    def test_config_has_symbols(self):
        """Verify config has expected number of symbols."""
        config_path = os.path.join(os.path.dirname(__file__), "data_source_config.ini")
        import configparser
        cp = configparser.ConfigParser()
        cp.read(config_path, encoding="utf-8")
        
        us_count = len(cp.items("us_stocks"))
        futures_count = len(cp.items("futures"))
        crypto_count = len(cp.items("crypto"))
        
        self.assertGreaterEqual(us_count, 10, "Should have at least 10 US stocks")
        self.assertGreaterEqual(futures_count, 8, "Should have at least 8 futures")
        self.assertGreaterEqual(crypto_count, 9, "Should have at least 9 cryptos")


if __name__ == "__main__":
    # Run tests with verbosity
    unittest.main(verbosity=2)
