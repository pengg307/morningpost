#!/usr/bin/env python3
"""
下载A股活跃前1000只股票最近半年历史数据
===========================================
功能：
1. 从东方财富获取A股活跃股列表（按成交额排序）
2. 批量下载每只股票近半年日线数据
3. 存储到SQLite数据库
4. 进度显示 + 错误处理

使用方法：
    python download_historical_data.py
"""

import requests
import sqlite3
import time
import os
from datetime import datetime, timedelta


class HistoricalDataDownloader:
    """历史数据下载器"""
    
    def __init__(self, db_path='data/market_data.db'):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
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
    
    def fetch_active_stocks(self, top_n=1000):
        """
        从东方财富获取活跃股列表
        
        Args:
            top_n: 获取前N只活跃股
            
        Returns:
            list: 股票列表 [{code, name, market, total_amount}, ...]
        """
        print(f"\n📊 正在获取A股活跃前{top_n}只股票...")
        
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
            resp = self.session.get(url, params=params, timeout=30)
            data = resp.json()
            
            if not data.get('data') or not data['data'].get('diff'):
                print("❌ 未获取到股票数据")
                return []
            
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
            
            # 保存到数据库
            self._save_active_stocks(stocks)
            
            return stocks
            
        except Exception as e:
            print(f"❌ 获取股票列表失败: {e}")
            return []
    
    def _save_active_stocks(self, stocks):
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
                stock['total_amount'],
                now
            ))
        
        conn.commit()
        conn.close()
        print(f"💾 已保存 {len(stocks)} 只股票到数据库")
    
    def fetch_daily_kline(self, code, market):
        """
        获取单只股票近半年日线数据
        
        Args:
            code: 股票代码
            market: 'sh' 或 'sz'
            
        Returns:
            list: K线数据 [{'date', 'open', 'close', 'high', 'low', 'volume', 'amount'}, ...]
        """
        # 计算半年前的日期
        end_date = datetime.now().strftime('%Y%m%d')
        beg_date = (datetime.now() - timedelta(days=180)).strftime('%Y%m%d')
        
        # 设置secid
        secid = f'1.{code}' if market == 'sh' else f'0.{code}'
        
        url = 'http://push2his.eastmoney.com/api/qt/stock/kline/get'
        params = {
            'secid': secid,
            'fields1': 'f1,f2,f3,f4,f5,f6',
            'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61',
            'klt': 101,  # 日线
            'fqt': 1,  # 前复权
            'beg': beg_date,
            'end': end_date,
            'lmt': 150  # 最大返回150条
        }
        
        try:
            resp = self.session.get(url, params=params, timeout=15)
            data = resp.json()
            
            if not data.get('data') or not data['data'].get('klines'):
                return []
            
            klines = []
            for line in data['data']['klines']:
                parts = line.split(',')
                if len(parts) < 7:
                    continue
                
                klines.append({
                    'date': parts[0],
                    'open': float(parts[1]),
                    'close': float(parts[2]),
                    'high': float(parts[3]),
                    'low': float(parts[4]),
                    'volume': float(parts[5]),
                    'amount': float(parts[6])
                })
            
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
                # 计算涨跌幅
                change_pct = 0
                if kline['open'] > 0:
                    change_pct = ((kline['close'] - kline['open']) / kline['open']) * 100
                
                # 计算换手率（简化估算）
                turnover_rate = 0
                
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
                    change_pct,
                    turnover_rate
                ))
                saved_count += 1
                
            except Exception as e:
                continue
        
        conn.commit()
        conn.close()
        return saved_count
    
    def download_all(self, top_n=1000, delay=0.5):
        """
        批量下载所有活跃股历史数据
        
        Args:
            top_n: 下载前N只股票
            delay: 每只股票请求间隔（秒），避免被封IP
        """
        print("\n" + "=" * 70)
        print("🚀 A股活跃股历史数据下载工具")
        print("=" * 70)
        
        # 1. 获取活跃股列表
        stocks = self.fetch_active_stocks(top_n)
        if not stocks:
            print("❌ 未获取到股票列表，退出")
            return
        
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
        print(f"平均每只股票: {total_saved // max(success_count, 1):.0f} 天")
        print("=" * 70)


def main():
    """主函数"""
    downloader = HistoricalDataDownloader()
    downloader.download_all(top_n=1000, delay=0.3)


if __name__ == '__main__':
    main()
