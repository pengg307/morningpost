#!/usr/bin/env python3
"""
下载A股活跃前1000只股票最近半年历史数据
===========================================
使用 baostock 免费API获取历史K线数据

使用方法:
    uv run python download_historical_data.py

依赖: baostock, pandas (已安装)
"""

import baostock as bs
import pandas as pd
import sqlite3
import time
import os
from datetime import datetime, timedelta


class HistoricalDataDownloader:
    """历史数据下载器 - 使用 baostock"""
    
    def __init__(self, db_path='data/market_data.db'):
        self.db_path = db_path
        self.session = bs.login()
        
        # 确保数据库目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # 初始化数据库表
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建活跃股表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS active_stocks (
                code TEXT PRIMARY KEY,
                name TEXT,
                market TEXT,
                total_amount REAL,
                updated_at TIMESTAMP
            )
        ''')
        
        # 创建历史K线表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_klines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                close REAL,
                high REAL,
                low REAL,
                volume REAL,
                amount REAL,
                change_pct REAL,
                turnover_rate REAL,
                UNIQUE(code, date)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_klines_code ON stock_klines(code)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_klines_date ON stock_klines(date)')
        
        conn.commit()
        conn.close()
        print("✅ 数据库表初始化完成")
    
    def get_active_stocks(self, top_n=1000):
        """
        获取活跃股列表（使用东方财富接口）
        
        Returns:
            list: 股票列表 [{code, name, market}, ...]
        """
        import requests
        
        print(f"\n📊 正在从东方财富获取活跃股列表...")
        
        url = 'http://push2.eastmoney.com/api/qt/clist/get'
        params = {
            'pn': 1,
            'pz': top_n,
            'po': 1,
            'np': 1,
            'fltt': 2,
            'invt': 2,
            'fid': 'f62',  # 按成交额排序
            'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048',
            'fields': 'f12,f14,f62'  # 代码、名称、成交额
        }
        
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
            
            if not data.get('data') or not data['data'].get('diff'):
                print("❌ 未获取到股票数据，使用备用方案")
                return self._get_all_a_stocks(top_n)
            
            stocks = []
            for item in data['data']['diff']:
                code = str(item.get('f12', ''))
                name = item.get('f14', '')
                amount = item.get('f62', 0) or 0
                
                if not code or len(code) != 6:
                    continue
                
                # 判断市场
                market = 'sh' if code.startswith(('6', '9')) else 'sz'
                
                stocks.append({
                    'code': code,
                    'name': name,
                    'market': market,
                    'total_amount': amount
                })
            
            print(f"✅ 成功获取 {len(stocks)} 只活跃股票")
            return stocks
            
        except Exception as e:
            print(f"❌ 获取股票列表失败: {e}，使用备用方案")
            return self._get_all_a_stocks(top_n)
    
    def _get_all_a_stocks(self, top_n=1000):
        """
        备用方案：通过 baostock 获取所有A股列表
        
        Args:
            top_n: 返回前N只
            
        Returns:
            list: 股票列表
        """
        print("\n📋 通过 baostock 获取A股列表...")
        
        rs = bs.query_stock_basic()
        data_list = []
        while rs.next():
            data_list.append(rs.get_row_data())
        
        df = pd.DataFrame(data_list, columns=rs.fields)
        
        # 过滤上交所和深交所股票
        a_stocks = df[df['exchange'].isin(['SSE', 'SZSE'])].head(top_n)
        
        stocks = []
        for _, row in a_stocks.iterrows():
            code = str(row['code'])
            name = str(row['name'])
            market = 'sh' if code.startswith('sh.') else 'sz'
            
            stocks.append({
                'code': code.replace('.', ''),
                'name': name,
                'market': market,
                'total_amount': 0
            })
        
        print(f"✅ 获取到 {len(stocks)} 只A股")
        return stocks
    
    def fetch_daily_kline(self, code, market):
        """
        获取单只股票近半年日线数据
        
        Args:
            code: 股票代码（如 '600519'）
            market: 'sh' 或 'sz'
            
        Returns:
            list: K线数据
        """
        # baostock 格式：sh.600519 或 sz.000001
        bs_code = f'{market}.{code}'
        
        # 计算半年前的日期
        end_date = datetime.now().strftime('%Y-%m-%d')
        beg_date = (datetime.now() - timedelta(days=180)).strftime('%Y-%m-%d')
        
        try:
            rs = bs.query_history_k_data_plus(
                bs_code,
                'date,code,open,high,low,close,volume,amount,turn,pctChg',
                start_date=beg_date,
                end_date=end_date,
                frequency='d',
                adjustflag='2'  # 2：前复权
            )
            
            if rs.error_code != '0':
                print(f"  ❌ {bs_code} 查询失败: {rs.error_msg}")
                return []
            
            klines = []
            while rs.next():
                row = rs.get_row_data()
                if len(row) >= 7:
                    try:
                        klines.append({
                            'date': row[0],
                            'open': float(row[2]),
                            'close': float(row[5]),
                            'high': float(row[3]),
                            'low': float(row[4]),
                            'volume': float(row[6]),
                            'amount': float(row[7]) if len(row) > 7 else 0,
                            'change_pct': float(row[9]) if len(row) > 9 else 0,
                            'turnover_rate': float(row[8]) if len(row) > 8 else 0
                        })
                    except (ValueError, IndexError):
                        continue
            
            return klines
            
        except Exception as e:
            return []
    
    def save_klines(self, code, klines):
        """保存K线数据到数据库"""
        if not klines:
            return 0
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved_count = 0
        for kline in klines:
            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO stock_klines 
                    (code, date, open, close, high, low, volume, amount, change_pct, turnover_rate)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    code,
                    kline['date'],
                    kline['open'],
                    kline['close'],
                    kline['high'],
                    kline['low'],
                    kline['volume'],
                    kline['amount'],
                    kline.get('change_pct', 0),
                    kline.get('turnover_rate', 0)
                ))
                saved_count += 1
                
            except Exception as e:
                continue
        
        conn.commit()
        conn.close()
        return saved_count
    
    def save_active_stocks(self, stocks):
        """保存活跃股列表到数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for stock in stocks:
            cursor.execute('''
                INSERT OR REPLACE INTO active_stocks (code, name, market, total_amount, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                stock['code'],
                stock['name'],
                stock['market'],
                stock.get('total_amount', 0),
                now
            ))
        
        conn.commit()
        conn.close()
        print(f"💾 已保存 {len(stocks)} 只股票到数据库")
    
    def download_all(self, top_n=1000, delay=0.2):
        """
        批量下载所有活跃股历史数据
        
        Args:
            top_n: 下载前N只股票
            delay: 每只股票请求间隔（秒）
        """
        print("\n" + "=" * 70)
        print("🚀 A股活跃股历史数据下载工具 (baostock)")
        print("=" * 70)
        
        # 1. 获取活跃股列表
        stocks = self.get_active_stocks(top_n)
        if not stocks:
            print("❌ 未获取到股票列表，退出")
            return
        
        # 保存活跃股列表
        self.save_active_stocks(stocks)
        
        print(f"\n📋 待下载 {len(stocks)} 只股票历史数据")
        print("=" * 70)
        
        # 2. 批量下载
        total_saved = 0
        success_count = 0
        fail_count = 0
        
        for i, stock in enumerate(stocks, 1):
            code = stock['code']
            name = stock['name']
            market = stock['market']
            
            # 显示进度
            progress = f"[{i}/{len(stocks)}]"
            print(f"\r{progress} 下载 {code} {name}...", end="", flush=True)
            
            # 获取K线数据
            klines = self.fetch_daily_kline(code, market)
            
            if klines:
                saved = self.save_klines(code, klines)
                total_saved += saved
                success_count += 1
                print(f" ✅ 获取 {saved} 天数据")
            else:
                fail_count += 1
                print(f" ❌ 无数据")
            
            # 延迟，避免请求过快
            if i < len(stocks):
                time.sleep(delay)
        
        print("\n" + "=" * 70)
        print("📊 下载完成统计")
        print("=" * 70)
        print(f"总股票数: {len(stocks)}")
        print(f"成功: {success_count}")
        print(f"失败: {fail_count}")
        print(f"总K线条数: {total_saved:,}")
        if success_count > 0:
            print(f"平均每只股票: {total_saved // success_count:.0f} 天")
        print("=" * 70)
    
    def cleanup(self):
        """登出 baostock"""
        bs.logout()
        print("✅ baostock 已登出")


def main():
    """主函数"""
    downloader = HistoricalDataDownloader()
    try:
        downloader.download_all(top_n=1000, delay=0.2)
    finally:
        downloader.cleanup()


if __name__ == '__main__':
    main()
