#!/usr/bin/env python3
"""
晨报数据源 - 统一数据获取接口
================================
优先从SQLite数据库读取，无数据时降级到API获取。

使用方法:
    from morning_data_source import MorningDataSource
    
    source = MorningDataSource()
    data = source.get_all_data()  # 获取全部数据
    source.close()
"""
import os
import json
import time
import requests
from datetime import datetime, timedelta
from data_acquisition_manager import DataAcquisitionManager


class MorningDataSource:
    """晨报数据源 - 统一接口"""
    
    def __init__(self, db_path=None):
        """初始化"""
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), 'data', 'market_data.db')
        
        self.manager = DataAcquisitionManager(db_path=db_path)
        self.cache = {}  # 内存缓存
        
    def get_all_data(self):
        """获取晨报所需的全部数据"""
        if 'all' in self.cache:
            return self.cache['all']
        
        data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date_str': datetime.now().strftime('%Y年%m月%d日'),
            'weekday': ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'][datetime.now().weekday()],
            'us_stocks': [],
            'a_stocks': [],
            'futures': [],
            'crypto': [],
            'news': [],
            'indices': {}
        }
        
        # 1. 从SQLite读取
        self._load_from_db(data)
        
        # 2. 如果数据不足，降级到API获取
        if not data['us_stocks']:
            print("[MorningDataSource] 美股数据为空，降级到API获取...")
            data['us_stocks'] = self._fetch_us_stocks_api()
        
        if not data['a_stocks']:
            print("[MorningDataSource] A股数据为空，降级到API获取...")
            data['a_stocks'] = self._fetch_a_stocks_api()
        
        if not data['futures']:
            print("[MorningDataSource] 期货数据为空，降级到API获取...")
            data['futures'] = self._fetch_futures_api()
        
        if not data['crypto']:
            print("[MorningDataSource] 加密货币数据为空，降级到API获取...")
            data['crypto'] = self._fetch_crypto_api()
        
        if not data['news']:
            print("[MorningDataSource] 新闻数据为空，降级到API获取...")
            data['news'] = self._fetch_news_api()
        
        # 缓存
        self.cache['all'] = data
        return data
    
    def _load_from_db(self, data):
        """从SQLite数据库加载数据"""
        cursor = self.manager.conn.cursor()
        
        # 获取最近1天内的数据
        cutoff = (datetime.now() - timedelta(days=1)).isoformat()
        
        cursor.execute("""
            SELECT symbol, latest_price, prev_close, open_price, high, low,
                   volume, change_pct, data_quality_score, asset_class_id
            FROM clean_data
            WHERE last_updated >= ?
            ORDER BY asset_class_id, symbol
        """, (cutoff,))
        
        rows = cursor.fetchall()
        
        for row in rows:
            item = {
                'symbol': row['symbol'],
                'price': float(row['latest_price']) if row['latest_price'] else 0,
                'prev_close': float(row['prev_close']) if row['prev_close'] else 0,
                'open': float(row['open_price']) if row['open_price'] else 0,
                'high': float(row['high']) if row['high'] else 0,
                'low': float(row['low']) if row['low'] else 0,
                'volume': int(row['volume']) if row['volume'] else 0,
                'change_pct': float(row['change_pct']) if row['change_pct'] else 0,
                'quality': float(row['data_quality_score']) if row['data_quality_score'] else 0,
            }
            
            asset_id = row['asset_class_id']
            if asset_id == 1:  # 美股
                data['us_stocks'].append(item)
            elif asset_id == 2:  # A股
                data['a_stocks'].append(item)
            elif asset_id in (3, 5):  # 期货/中国期货
                data['futures'].append(item)
            elif asset_id == 4:  # 加密货币
                data['crypto'].append(item)
    
    def _fetch_us_stocks_api(self):
        """通过新浪财经API获取美股数据（降级）"""
        us_stocks = []
        try:
            symbols = 'gb_tsla,gb_aapl,gb_googl,gb_msft,gb_nvda,gb_amzn,gb_meta,gb_NFLX,gb_TSM,gb_INTC,gb_SPCX'
            url = f'https://hq.sinajs.cn/list={symbols}'
            headers = {'Referer': 'https://finance.sina.com.cn/', 'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = 'gbk'
            
            stock_names = {
                'tsla': '特斯拉', 'aapl': '苹果', 'googl': '谷歌', 'msft': '微软',
                'nvda': '英伟达', 'amzn': '亚马逊', 'meta': 'Meta', 'NFLX': '奈飞',
                'TSM': '台积电', 'INTC': '英特尔', 'SPCX': 'SpaceX'
            }
            
            for line in resp.text.strip().split('\n'):
                if '=' in line:
                    data = line.split('"')[1] if '"' in line else ''
                    parts = data.split(',')
                    if len(parts) >= 3:
                        code = line.split('=')[0].split('_')[-1].strip().rstrip('"').lower()
                        name = stock_names.get(code, code)
                        try:
                            current_price = float(parts[1])
                            prev_close = float(parts[5]) if len(parts) > 5 and parts[5] else 0
                            open_price = float(parts[4]) if len(parts) > 4 and parts[4] else 0
                            high = float(parts[6]) if len(parts) > 6 and parts[6] else 0
                            low = float(parts[7]) if len(parts) > 7 and parts[7] else 0
                            volume = int(float(parts[8])) if len(parts) > 8 else 0
                            
                            if current_price > 0 and volume > 0:
                                pct = (current_price - prev_close) / prev_close * 100 if prev_close > 0 else 0
                                us_stocks.append({
                                    'symbol': code.upper(),
                                    'name': name,
                                    'price': current_price,
                                    'prev_close': prev_close,
                                    'open': open_price,
                                    'high': high,
                                    'low': low,
                                    'volume': volume,
                                    'change_pct': pct,
                                    'source': 'sina_api'
                                })
                        except ValueError:
                            pass
        except Exception as e:
            print(f"[MorningDataSource] 美股API获取失败: {e}")
        
        return us_stocks
    
    def _fetch_a_stocks_api(self):
        """通过腾讯API获取A股数据（降级）"""
        a_stocks = []
        try:
            # 从配置中读取A股代码
            cursor = self.manager.conn.cursor()
            cursor.execute("SELECT symbol FROM clean_data WHERE asset_class_id = 2")
            rows = cursor.fetchall()
            
            if rows:
                # 取前10只
                symbols = [r['symbol'] for r in rows[:10]]
                url = f'http://qt.gtimg.cn/q={",".join(symbols)}'
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
                resp.encoding = 'gbk'
                
                for line in resp.text.strip().split('\n'):
                    if '~' in line:
                        parts = line.split('~')
                        if len(parts) > 49:
                            a_stocks.append({
                                'symbol': parts[2],
                                'name': parts[1],
                                'price': float(parts[3]) if parts[3] else 0,
                                'prev_close': float(parts[4]) if parts[4] else 0,
                                'open': float(parts[5]) if parts[5] else 0,
                                'high': float(parts[33]) if len(parts) > 33 and parts[33] else 0,
                                'low': float(parts[34]) if len(parts) > 34 and parts[34] else 0,
                                'volume': float(parts[6]) if parts[6] else 0,
                                'amount': float(parts[37]) if len(parts) > 37 else 0,
                                'turnover_rate': float(parts[38]) if len(parts) > 38 else 0,
                                'pe': float(parts[39]) if len(parts) > 39 and parts[39] else 0,
                                'source': 'tencent_api'
                            })
        except Exception as e:
            print(f"[MorningDataSource] A股API获取失败: {e}")
        
        return a_stocks
    
    def _fetch_futures_api(self):
        """通过新浪API获取期货数据（降级）"""
        futures = []
        try:
            cursor = self.manager.conn.cursor()
            cursor.execute("SELECT symbol FROM clean_data WHERE asset_class_id IN (3, 5)")
            rows = cursor.fetchall()
            
            if rows:
                symbols = [f"hf_{r['symbol'].upper()}" for r in rows[:5]]
                url = f'https://hq.sinajs.cn/list={",".join(symbols)}'
                headers = {'Referer': 'https://finance.sina.com.cn/'}
                resp = requests.get(url, headers=headers, timeout=10)
                resp.encoding = 'gbk'
                
                for line in resp.text.strip().split('\n'):
                    if '=' in line and '"' in line:
                        data = line.split('"')[1]
                        parts = data.split(',')
                        if len(parts) >= 3 and parts[1]:
                            code = line.split('=')[0].split('_')[-1].strip().lower()
                            try:
                                price = float(parts[1])
                                prev_close = float(parts[5]) if len(parts) > 5 and parts[5] else 0
                                pct = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
                                futures.append({
                                    'symbol': code.upper(),
                                    'price': price,
                                    'prev_close': prev_close,
                                    'change_pct': pct,
                                    'source': 'sina_futures_api'
                                })
                            except ValueError:
                                pass
        except Exception as e:
            print(f"[MorningDataSource] 期货API获取失败: {e}")
        
        return futures
    
    def _fetch_crypto_api(self):
        """通过Binance API获取加密货币数据（降级）"""
        # Binance需要代理，当前环境不可用，直接返回空
        print("[MorningDataSource] 加密货币API需要代理，跳过")
        return []
    
    def _fetch_news_api(self):
        """通过东方财富获取新闻（降级）"""
        news = []
        try:
            url = 'https://np-listapi.eastmoney.com/comm/web/getNewsByColumns'
            params = {
                'columns': 'ccfx',
                'page_index': 1,
                'page_size': 10,
                'shark_params': '',
                'extra_params': '{"cb_id":1,"type":"ccfx"}'
            }
            r = requests.get(url, params=params, timeout=5)
            if r.status_code == 200:
                data = r.json()
                if data and 'data' in data and data['data'] and 'list' in data['data']:
                    for item in data['data']['list'][:10]:
                        title = item.get('title', '') if item else ''
                        if title:
                            news.append({
                                'title': title,
                                'url': item.get('url', ''),
                                'source': 'eastmoney_news_api'
                            })
        except Exception as e:
            print(f"[MorningDataSource] 新闻API获取失败: {e}")
        
        return news
    
    def close(self):
        """关闭连接"""
        if self.manager:
            self.manager.close()


def main():
    """测试入口"""
    print(f"{'='*70}")
    print(f"📰 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 晨报数据源测试")
    print(f"{'='*70}\n")
    
    source = MorningDataSource()
    
    try:
        data = source.get_all_data()
        
        print(f"📊 数据概览:")
        print(f"  美股: {len(data['us_stocks'])}只")
        for s in data['us_stocks'][:3]:
            print(f"    {s['symbol']}: ${s['price']:.2f} ({s['change_pct']:+.2f}%)")
        
        print(f"  A股: {len(data['a_stocks'])}只")
        for s in data['a_stocks'][:3]:
            print(f"    {s['symbol']}: ¥{s['price']:.2f} ({s['change_pct']:+.2f}%)")
        
        print(f"  期货: {len(data['futures'])}只")
        for s in data['futures'][:3]:
            print(f"    {s['symbol']}: ${s['price']:.2f} ({s['change_pct']:+.2f}%)")
        
        print(f"  加密货币: {len(data['crypto'])}只")
        print(f"  新闻: {len(data['news'])}条")
        
        # 保存为JSON
        os.makedirs('projects', exist_ok=True)
        output_file = f'projects/morning_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n💾 数据已保存到: {output_file}")
        
    finally:
        source.close()
    
    print(f"\n{'='*70}\n")


if __name__ == '__main__':
    main()
