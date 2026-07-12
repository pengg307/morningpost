"""
定时数据获取任务 - 每12小时执行一次
=====================================
从config读取要获取的股票列表，多渠道获取并存入数据库。

功能：
1. 从data_source_config.ini读取标的列表
2. 为每个标的调用多个数据源
3. 代理Fallback策略
4. 失败重试3次
5. 数据规整
6. 代理使用情况记录
7. 定时调度支持

用法:
    python fetch_all_data.py              # 立即执行一次
    python fetch_all_data.py --schedule   # 启动定时调度 (每12小时)
    python fetch_all_data.py --once       # 仅执行一次 (默认)
"""
import os
import sys
import time
import json
import argparse
import logging
from datetime import datetime, timedelta

from data_acquisition_manager import DataAcquisitionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("FetchAllData")


def fetch_category(manager: DataAcquisitionManager, category: str, 
                   symbols: dict, sources: list, delay: float = 0.5):
    """Fetch data for a category of symbols."""
    total_success = 0
    total_attempted = 0
    
    # 映射类别到asset_class_id
    category_to_id = {
        'us_stock': 1,
        'a_stock': 2,
        'futures': 3,
        'crypto': 4
    }
    
    asset_class_id = category_to_id.get(category, 1)
    
    for symbol, name in symbols.items():
        total_attempted += 1
        results = manager.acquire_raw_data(symbol, asset_class_id, sources, max_retries=3)
        
        success_count = sum(1 for r in results.values() if r.get("status") == "success")
        total_success += success_count
        
        if success_count > 0:
            logger.info(f"✅ {symbol} ({name}): {success_count}/{len(sources)} sources successful")
        else:
            logger.warning(f"❌ {symbol} ({name}): All sources failed")
            
        time.sleep(delay)
        
    return total_success, total_attempted


def main(schedule: bool = False):
    """Main function to fetch all data."""
    logger.info("=" * 60)
    logger.info("Starting data acquisition task")
    logger.info("=" * 60)
    
    manager = DataAcquisitionManager()
    
    try:
        # 1. 美股数据
        logger.info("Fetching US stocks...")
        us_stocks = dict(manager.config.items('us_stocks')) if manager.config.has_section('us_stocks') else {}
        us_success, us_total = fetch_category(manager, 'us_stock', us_stocks, [1], delay=0.1)
        logger.info(f"US stocks: {us_success}/{us_total} successful")
        
        # 2. A股数据
        logger.info("Fetching A-shares...")
        a_sectors = {}
        if manager.config.has_section('a_sectors'):
            for sector_name, symbols_str in manager.config.items('a_sectors'):
                for symbol in symbols_str.split(','):
                    symbol = symbol.strip()
                    if symbol:
                        a_sectors[symbol] = sector_name.strip()
        
        a_success, a_total = fetch_category(manager, 'a_stock', a_sectors, [2], delay=0.1)
        logger.info(f"A-shares: {a_success}/{a_total} successful")
        
        # 3. 期货数据
        logger.info("Fetching futures...")
        futures = dict(manager.config.items('futures')) if manager.config.has_section('futures') else {}
        # 期货代码需要大写
        futures_upper = {k.upper(): v for k, v in futures.items()}
        fu_success, fu_total = fetch_category(manager, 'futures', futures_upper, [1], delay=0.1)
        logger.info(f"Futures: {fu_success}/{fu_total} successful")
        
        # 4. 加密货币数据
        logger.info("Fetching cryptocurrencies...")
        crypto = dict(manager.config.items('crypto')) if manager.config.has_section('crypto') else {}
        cr_success, cr_total = fetch_category(manager, 'crypto', crypto, [6], delay=0.1)
        logger.info(f"Crypto: {cr_success}/{cr_total} successful")
        
        # 5. 数据规整
        logger.info("Consolidating data...")
        manager.consolidate_data()
        
        # 6. 统计信息
        cursor = manager.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM raw_data")
        raw_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM clean_data")
        clean_count = cursor.fetchone()[0]
        
        logger.info("=" * 60)
        logger.info(f"Data acquisition complete!")
        logger.info(f"Raw data records: {raw_count}")
        logger.info(f"Clean data records: {clean_count}")
        logger.info("=" * 60)
        
        return {
            'total_fetched': raw_count,
            'total_consolidated': clean_count
        }
        
    except Exception as e:
        logger.error(f"Data acquisition failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        manager.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="定时数据获取任务")
    parser.add_argument("--schedule", action="store_true", help="启动定时调度")
    parser.add_argument("--once", action="store_true", help="仅执行一次")
    args = parser.parse_args()
    
    if args.schedule:
        logger.info("Starting scheduled data acquisition (every 12 hours)")
        while True:
            try:
                result = main()
                if result:
                    logger.info(f"Next run in 12 hours...")
                    time.sleep(12 * 60 * 60)  # 12 hours
                else:
                    logger.error("Failed to fetch data, retrying in 1 hour...")
                    time.sleep(60 * 60)  # 1 hour
            except KeyboardInterrupt:
                logger.info("Scheduled task stopped by user")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60 * 60)  # 1 hour on error
    else:
        result = main()
        if result:
            print(f"✅ 定时任务执行完成!")
            print(f"  获取数据: {result['total_fetched']}条")
            print(f"  规整数据: {result['total_consolidated']}条")
        else:
            print("❌ 定时任务执行失败")
            sys.exit(1)
