"""
定时数据获取任务 - 每12小时执行一次
从config读取要获取的股票列表，多渠道获取并存入数据库
"""
import os
import sys
import time
import json
from datetime import datetime
from data_acquisition_manager import DataAcquisitionManager

def fetch_all_data():
    """获取所有数据"""
    print(f"\n{'='*60}")
    print(f"🚀 [{datetime.now()}] 开始定时数据获取任务")
    print(f"{'='*60}\n")
    
    # 初始化数据管理器
    manager = DataAcquisitionManager()
    
    try:
        # 1. 获取美股数据
        print("📊 开始获取美股数据...")
        us_stocks = manager.config.get('us_stocks', fallback={})
        for symbol, name in us_stocks.items():
            sources = ['sina', 'yahoo']  # 新浪优先，Yahoo备用
            results = manager.acquire_raw_data(symbol, 'us_stock', sources)
            print(f"  {symbol} ({name}): {len([r for r in results.values() if r['status'] == 'success'])}/{len(sources)} 数据源成功")
            time.sleep(0.5)  # 避免限流
            
        # 2. 获取期货数据
        print("\n📈 开始获取期货数据...")
        futures = manager.config.get('futures', fallback={})
        for symbol, name in futures.items():
            sources = ['sina', 'yfinance']  # 新浪优先，yfinance备用
            results = manager.acquire_raw_data(symbol, 'futures', sources)
            print(f"  {symbol} ({name}): {len([r for r in results.values() if r['status'] == 'success'])}/{len(sources)} 数据源成功")
            time.sleep(0.5)
            
        # 3. 获取加密货币数据
        print("\n💰 开始获取加密货币数据...")
        cryptos = manager.config.get('crypto', fallback={})
        for symbol, name in cryptos.items():
            sources = ['binance', 'coinbase']  # Binance优先，Coinbase备用
            results = manager.acquire_raw_data(symbol, 'crypto', sources)
            print(f"  {symbol} ({name}): {len([r for r in results.values() if r['status'] == 'success'])}/{len(sources)} 数据源成功")
            time.sleep(0.5)
            
        # 4. 获取A股数据（按板块）
        print("\n🇨🇳 开始获取A股数据...")
        a_sectors = manager.config.get('a_sectors', fallback={})
        for sector_name, symbols_str in a_sectors.items():
            symbols = [s.strip() for s in symbols_str.split(',')]
            print(f"  板块: {sector_name} ({len(symbols)} 只)")
            for symbol in symbols[:20]:  # 最多20只
                sources = ['tencent', 'sina', 'eastmoney']  # 多渠道
                results = manager.acquire_raw_data(symbol, 'a_stock', sources)
                success_count = len([r for r in results.values() if r['status'] == 'success'])
                if success_count > 0:
                    print(f"    {symbol}: {success_count}/{len(sources)} 数据源成功")
                time.sleep(0.3)  # 避免限流
                
        # 5. 数据规整
        print("\n🔧 开始数据规整...")
        manager.consolidate_data()
        print("  ✅ 数据规整完成")
        
        # 6. 统计信息
        print("\n📋 数据统计:")
        clean_data = manager.get_clean_data()
        print(f"  总记录数: {len(clean_data)}")
        print(f"  美股: {len([d for d in clean_data if d['data_type'] == 'us_stock'])}")
        print(f"  期货: {len([d for d in clean_data if d['data_type'] == 'futures'])}")
        print(f"  加密: {len([d for d in clean_data if d['data_type'] == 'crypto'])}")
        print(f"  A股: {len([d for d in clean_data if d['data_type'] == 'a_stock'])}")
        
        print(f"\n{'='*60}")
        print(f"✅ [{datetime.now()}] 数据获取任务完成")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\n❌ 数据获取任务失败: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        manager.close()

if __name__ == '__main__':
    fetch_all_data()
