"""
morning_data_source - Unified data source for morning report generation.
Provides MorningDataSource class that aggregates all market data.
"""
import os
import json
import time
import requests
from datetime import datetime


class MorningDataSource:
    """Unified data source for morning report generation."""

    def __init__(self):
        self.conn = None  # SQLite connection placeholder
        self._cache = {}

    def get_all_data(self) -> dict:
        """Fetch all data from various sources and return unified dict."""
        result = {
            'date_str': '',
            'weekday': '',
            'timestamp': '',
            'a_stocks': [],
            'us_stocks': [],
            'futures': [],
            'crypto': [],
            'news': [],
            'etf_options': [],
        }

        now = datetime.now()
        result['date_str'] = now.strftime('%Y年%m月%d日')
        result['weekday'] = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'][now.weekday()]
        result['timestamp'] = now.strftime('%Y-%m-%d %H:%M:%S')

        # Fetch A-stock data (Tencent - fast, reliable)
        result['a_stocks'] = self._fetch_a_stocks()
        print(f"[MorningDataSource] A股数据: {len(result['a_stocks'])}只")

        # Fetch US stock data (Sina - may timeout, use fallback)
        result['us_stocks'] = self._fetch_us_stocks()
        print(f"[MorningDataSource] 美股数据: {len(result['us_stocks'])}只")

        # Fetch futures data (Sina - may timeout, use fallback)
        result['futures'] = self._fetch_futures()
        print(f"[MorningDataSource] 期货数据: {len(result['futures'])}只")

        # Fetch crypto data (Binance - needs proxy, skip for now)
        result['crypto'] = self._fetch_crypto()
        print(f"[MorningDataSource] 虚拟币数据: {len(result['crypto'])}只")

        # Fetch news (Sina - fast)
        result['news'] = self._fetch_news()
        print(f"[MorningDataSource] 新闻数据: {len(result['news'])}条")

        # Fetch ETF options (Tencent - fast)
        result['etf_options'] = self._fetch_etf_options()
        print(f"[MorningDataSource] ETF期权数据: {len(result['etf_options'])}只")

        return result

    def _safe_get(self, url, headers=None, timeout=3, retries=1, params=None):
        """Safe HTTP GET with short timeout and retry."""
        for i in range(retries + 1):
            try:
                resp = requests.get(url, headers=headers, timeout=timeout, params=params)
                return resp
            except Exception as e:
                if i < retries:
                    time.sleep(0.5)
                else:
                    return None
        return None

    def _fetch_a_stocks(self) -> list:
        """Fetch A-stock real-time data from Tencent API - expanded to 50+ active stocks."""
        codes = [
            # 沪深300权重股
            'sh600519','sh601318','sz000858','sz000333','sz002594','sz000725',
            'sh600036','sh601166','sh600900','sh600276','sh601888','sh600809',
            'sz000568','sz002415','sz002304','sz000001','sz002714','sz002475',
            # 创业板/科创板热门股
            'sz300750','sz300059','sz300015','sz300760','sz300124','sz300308',
            'sh688981','sh688012','sh688008','sh688525','sh688256','sh688111',
            # 新能源/光伏/半导体
            'sz300274','sz300750','sz002129','sz002459','sz002142','sz002340',
            'sz002230','sz002049','sz002493','sz002192',
            # 消费/医药
            'sz000858','sz000596','sz002304','sz300015','sz300760',
            # 金融/地产
            'sh600036','sh601318','sh601688','sh601288','sh600030',
            # 军工/航天
            'sh600760','sh600893','sz002013','sz002179',
            # 其他活跃股
            'sz000651','sz000725','sz002384','sz300223','sh603259','sh600585',
        ]
        # 去重
        codes = list(dict.fromkeys(codes))
        url = f'http://qt.gtimg.cn/q={",".join(codes)}'
        stocks = []
        resp = self._safe_get(url, timeout=5)
        if resp and resp.status_code == 200:
            resp.encoding = 'gbk'
            for line in resp.text.strip().split('\n'):
                if '~' in line:
                    parts = line.split('~')
                    if len(parts) > 49:
                        price = float(parts[3]) if parts[3] else 0
                        prev_close = float(parts[4]) if parts[4] else 0
                        pct = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
                        stocks.append({
                            'name': parts[1],
                            'code': parts[2],
                            'price': price,
                            'prev_close': prev_close,
                            'open': float(parts[5]) if parts[5] else 0,
                            'high': float(parts[33]) if len(parts) > 33 and parts[33] else 0,
                            'low': float(parts[34]) if len(parts) > 34 and parts[34] else 0,
                            'volume': float(parts[6]) if parts[6] else 0,
                            'amount': float(parts[37]) if len(parts) > 37 else 0,
                            'turnover_rate': float(parts[38]) if len(parts) > 38 else 0,
                            'pe': float(parts[39]) if len(parts) > 39 and parts[39] else 0,
                            'pb': float(parts[40]) if len(parts) > 40 and parts[40] else 0,
                            'change_pct': pct,
                        })
        return stocks

    def _fetch_us_stocks(self) -> list:
        """Fetch US stock data from Sina Finance API with fallback."""
        us_stocks = []
        stock_names = {
            'tsla': '特斯拉', 'aapl': '苹果', 'googl': '谷歌', 'msft': '微软',
            'nvda': '英伟达', 'amzn': '亚马逊', 'meta': 'Meta', 'NFLX': '奈飞',
            'TSM': '台积电', 'INTC': '英特尔', 'SPCX': 'SpaceX'
        }
        symbols = 'gb_tsla,gb_aapl,gb_googl,gb_msft,gb_nvda,gb_amzn,gb_meta,gb_NFLX,gb_TSM,gb_INTC,gb_SPCX'
        
        # Try Sina first (short timeout)
        url = f'https://hq.sinajs.cn/list={symbols}'
        headers = {'Referer': 'https://finance.sina.com.cn/', 'User-Agent': 'Mozilla/5.0'}
        resp = self._safe_get(url, headers=headers, timeout=3)
        
        if not resp or resp.status_code != 200 or len(resp.text) < 100:
            # Fallback: use Tencent US stock API
            print("[MorningDataSource] 美股Sina超时，尝试腾讯API...")
            codes = 's_sh_aapl,s_sz_tsla,s_sh_googl,s_sz_msft,s_sz_nvda,s_sz_amzn,s_sz_meta,s_sz_nflx,s_sz_tsm,s_sz_intc'
            url2 = f'http://qt.gtimg.cn/q={codes}'
            resp = self._safe_get(url2, timeout=3)
            if resp and resp.status_code == 200:
                resp.encoding = 'gbk'
                for line in resp.text.strip().split(';'):
                    if '=' in line and '~' in line:
                        parts = line.split('=')
                        name_part = parts[1].split('~')
                        if len(name_part) > 1:
                            code = name_part[2]
                            name = name_part[1]
                            try:
                                price = float(name_part[3]) if name_part[3] else 0
                                prev_close = float(name_part[4]) if name_part[4] else 0
                                pct = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
                                us_stocks.append({
                                    'name': name,
                                    'symbol': code.upper(),
                                    'price': price,
                                    'prev_close': prev_close,
                                    'open': float(name_part[5]) if name_part[5] else 0,
                                    'high': float(name_part[33]) if len(name_part) > 33 else 0,
                                    'low': float(name_part[34]) if len(name_part) > 34 else 0,
                                    'volume': float(name_part[6]) if name_part[6] else 0,
                                    'change_pct': pct,
                                })
                            except (ValueError, IndexError):
                                pass
            return us_stocks
        
        resp.encoding = 'gbk'
        for line in resp.text.strip().split('\n'):
            if '=' in line:
                data_part = line.split('"')[1] if '"' in line else ''
                parts = data_part.split(',')
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
                            change_pct = (current_price - prev_close) / prev_close * 100 if prev_close > 0 else 0
                            us_stocks.append({
                                'name': name,
                                'symbol': code.upper(),
                                'price': current_price,
                                'prev_close': prev_close,
                                'open': open_price,
                                'high': high,
                                'low': low,
                                'volume': volume,
                                'change_pct': change_pct,
                            })
                    except ValueError:
                        pass
        return us_stocks

    def _fetch_futures(self) -> list:
        """Fetch US futures data from Sina Finance API with fallback."""
        futures = []
        code_names = {
            'hf_GC': '纽约黄金', 'hf_SI': '纽约白银',
            'hf_CL': '纽约原油', 'hf_NG': '天然气', 'hf_BZ': '布伦特原油',
            'hf_HG': '铜',
        }
        all_codes = list(code_names.keys())
        symbols = ','.join(all_codes)
        url = f'https://hq.sinajs.cn/list={symbols}'
        headers = {'Referer': 'https://finance.sina.com.cn/'}
        resp = self._safe_get(url, headers=headers, timeout=3)
        
        if not resp or resp.status_code != 200 or len(resp.text) < 100:
            # Fallback: use Tencent futures API
            print("[MorningDataSource] 期货Sina超时，尝试腾讯API...")
            codes = 'hf_GC,hf_SI,hf_CL'
            url2 = f'http://qt.gtimg.cn/q={codes}'
            resp = self._safe_get(url2, timeout=3)
            if resp and resp.status_code == 200:
                resp.encoding = 'gbk'
                for line in resp.text.strip().split(';'):
                    if '=' in line and '~' in line:
                        parts = line.split('=')
                        name_part = parts[1].split('~')
                        if len(name_part) > 1:
                            code = name_part[2]
                            try:
                                price = float(name_part[3]) if name_part[3] else 0
                                prev_close = float(name_part[4]) if name_part[4] else 0
                                pct = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
                                futures.append({
                                    'name': code_names.get(code, code),
                                    'symbol': code,
                                    'price': price,
                                    'prev_close': prev_close,
                                    'change_pct': pct,
                                })
                            except (ValueError, IndexError):
                                pass
            return futures
        
        for line in resp.text.strip().split('\n'):
            if not line.strip():
                continue
            try:
                parts = line.split('=')
                if len(parts) < 2:
                    continue
                symbol = parts[0].split('_')[-1].strip().rstrip('"')
                data_str = parts[1].strip().strip('"').strip(';')
                if not data_str:
                    continue
                fields = data_str.split(',')
                if len(fields) >= 10:
                    try:
                        price = float(fields[1])
                        prev_close = float(fields[5]) if len(fields) > 5 and fields[5] else 0
                        pct = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
                        futures.append({
                            'name': code_names.get(symbol, symbol),
                            'symbol': symbol,
                            'price': price,
                            'prev_close': prev_close,
                            'change_pct': pct,
                        })
                    except (ValueError, IndexError):
                        pass
            except Exception:
                continue
        return futures

    def _fetch_crypto(self) -> list:
        """Fetch crypto data - returns empty since Binance needs proxy."""
        print("[MorningDataSource] 加密货币API需要代理，跳过")
        return []

    def _fetch_news(self) -> list:
        """Fetch financial news from Sina."""
        news = []
        url = 'https://feed.mix.sina.com.cn/api/roll/get'
        params = {
            'pageid': '153',
            'lid': '2516',
            'k': '',
            'num': 10,
            'page': '1'
        }
        resp = self._safe_get(url, params=params, timeout=5)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                if data and 'result' in data and data['result'] and 'data' in data['result']:
                    for item in data['result']['data'][:10]:
                        title = item.get('title', '') if item else ''
                        if title:
                            news.append({
                                'title': title,
                                'url': item.get('url', ''),
                                'source': 'sina_news_api'
                            })
            except Exception:
                pass
        return news

    def _fetch_etf_options(self) -> list:
        """Fetch ETF data from Tencent API."""
        etf_options = []
        etf_codes = [
            'sh510050', 'sh510300', 'sh588000', 'sz159919', 'sz159922',
            'sh510500', 'sh518880', 'sz159985'
        ]
        codes_str = ','.join(etf_codes)
        url = f'http://qt.gtimg.cn/q={codes_str}'
        resp = self._safe_get(url, timeout=5)
        
        if resp and resp.status_code == 200:
            for line in resp.text.strip().split(';'):
                if line.strip() and '~' in line:
                    parts = line.split('~')
                    if len(parts) > 38:
                        name = parts[1]
                        price = float(parts[3]) if parts[3] else 0
                        pct = float(parts[32]) if parts[32] else 0
                        volume = int(parts[37]) if parts[37] else 0
                        amount = float(parts[38]) if parts[38] else 0
                        etf_options.append({
                            'symbol': parts[2],
                            'name': name,
                            'price': price,
                            'change_pct': pct,
                            'volume': volume,
                            'amount_yi': amount,
                            'type': 'etf_option_base'
                        })
        return etf_options

    def close(self):
        """Placeholder for compatibility."""
        pass


if __name__ == '__main__':
    """Test entry"""
    print(f"{'='*70}")
    print(f"📰 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 晨报数据源测试")
    print(f"{'='*70}\n")
    
    source = MorningDataSource()
    
    try:
        data = source.get_all_data()
        
        print(f"\n📊 数据概览:")
        print(f"  美股: {len(data['us_stocks'])}只")
        for s in data['us_stocks'][:3]:
            print(f"    {s['symbol']}: ${s['price']:.2f} ({s['change_pct']:+.2f}%)")
        
        print(f"  A股: {len(data['a_stocks'])}只")
        for s in data['a_stocks'][:3]:
            print(f"    {s['code']}: ¥{s['price']:.2f} ({s['change_pct']:+.2f}%)")
        
        print(f"  期货: {len(data['futures'])}只")
        for s in data['futures'][:3]:
            print(f"    {s['symbol']}: {s['price']} ({s['change_pct']:+.2f}%)")
        
        print(f"  加密货币: {len(data['crypto'])}只")
        print(f"  新闻: {len(data['news'])}条")
        
        # Save as JSON
        os.makedirs('projects', exist_ok=True)
        output_file = f'projects/morning_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n💾 数据已保存到: {output_file}")
        
    finally:
        pass
    
    print(f"\n{'='*70}\n")
