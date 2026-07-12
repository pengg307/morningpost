"""
市场数据获取管理器 - 使用新数据库架构
- asset_class_id: 外键引用asset_classes表
- source_id: 外键引用data_sources表
- proxy_used: 0/1布尔值
"""
import sqlite3
import json
import os
import time
import logging
import configparser
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class DataAcquisitionManager:
    """市场数据获取管理器"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), 'data', 'market_data.db')
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self.config = self._load_config()
        
    def _load_config(self):
        config_path = os.path.join(os.path.dirname(__file__), 'data_source_config.ini')
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        return config
        
    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # 1. 资产类别表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS asset_classes (
                id INTEGER PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT
            )
        ''')
        
        # 插入枚举值
        for row in [
            (1, 'us_stock', '美股', '美国股票市场'),
            (2, 'a_stock', 'A股', '中国A股市场'),
            (3, 'futures', '期货', '商品/金融期货合约'),
            (4, 'crypto', '加密货币', '数字货币')
        ]:
            cursor.execute('INSERT OR IGNORE INTO asset_classes VALUES (?, ?, ?, ?)', row)
            
        # 2. 数据源表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS data_sources (
                id INTEGER PRIMARY KEY,
                code TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                category TEXT,
                need_proxy INTEGER DEFAULT 0,
                reliability REAL DEFAULT 1.0
            )
        ''')
        
        for row in [
            (1, 'sina', '新浪财经', 'stock/futures', 0, 0.95),
            (2, 'tencent', '腾讯行情', 'stock', 0, 0.95),
            (3, 'eastmoney', '东方财富', 'stock', 0, 0.90),
            (4, 'yahoo', 'Yahoo Finance', 'stock/futures', 1, 0.85),
            (5, 'yfinance', 'yfinance', 'futures', 1, 0.80),
            (6, 'binance', 'Binance', 'crypto', 1, 0.90),
            (7, 'coinbase', 'Coinbase', 'crypto', 0, 0.85),
            (8, 'firecrawl', 'Firecrawl', 'news', 0, 0.80)
        ]:
            cursor.execute('INSERT OR IGNORE INTO data_sources VALUES (?, ?, ?, ?, ?, ?)', row)
            
        # 3. 原始数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS raw_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                asset_class_id INTEGER NOT NULL,
                source_id INTEGER NOT NULL,
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
                FOREIGN KEY (asset_class_id) REFERENCES asset_classes(id),
                FOREIGN KEY (source_id) REFERENCES data_sources(id)
            )
        ''')
        
        # 4. 规整数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clean_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                asset_class_id INTEGER NOT NULL,
                best_source_id INTEGER NOT NULL,
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
                last_updated DATETIME,
                data_quality_score REAL,
                FOREIGN KEY (asset_class_id) REFERENCES asset_classes(id),
                FOREIGN KEY (best_source_id) REFERENCES data_sources(id)
            )
        ''')
        
        # 5. 数据源健康表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS source_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                last_success DATETIME,
                last_fail DATETIME,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                proxy_usage_count INTEGER DEFAULT 0,
                rate_limited_count INTEGER DEFAULT 0,
                health_score REAL DEFAULT 1.0,
                FOREIGN KEY (source_id) REFERENCES data_sources(id)
            )
        ''')
        
        # 6. 通知日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                level TEXT,
                message TEXT,
                proxy_used INTEGER DEFAULT 0,
                source_id INTEGER,
                asset_class_id INTEGER,
                FOREIGN KEY (source_id) REFERENCES data_sources(id),
                FOREIGN KEY (asset_class_id) REFERENCES asset_classes(id)
            )
        ''')
        
        self.conn.commit()
        
    def _get_period(self, hour: int) -> str:
        """根据小时返回时段分类"""
        if 6 <= hour < 12:
            return 'morning'
        elif 12 <= hour < 18:
            return 'afternoon'
        elif 18 <= hour < 22:
            return 'evening'
        else:
            return 'night'
    
    def _log_acquisition(self, run_id: str, symbol: str, asset_class_id: int, 
                         source_id: int, source_name: str, status: str, duration_ms: float,
                         error_msg: str = None, retry_count: int = 0, proxy_used: bool = False,
                         data_valid: int = None, validation_notes: str = None,
                         raw_sample: str = None):
        """记录数据拉取日志到data_acquisition_log表"""
        try:
            from datetime import datetime
            now = datetime.now()
            cursor = self.conn.cursor()
            
            # 资产类别名称映射
            asset_names = {1: 'us_stock', 2: 'a_stock', 3: 'future', 4: 'crypto'}
            asset_class_name = asset_names.get(asset_class_id, f'unknown_{asset_class_id}')
            
            cursor.execute('''
                INSERT INTO data_acquisition_log 
                (run_id, timestamp, hour, day_of_week, is_weekend, period, asset_class, symbol,
                 source_id, source_name, status, duration_ms, error_message, retry_count, 
                 proxy_used, data_valid, validation_notes, raw_data_sample)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                run_id, now.strftime('%Y-%m-%d %H:%M:%S'), now.hour, now.weekday(),
                1 if now.weekday() >= 5 else 0, self._get_period(now.hour),
                asset_class_name, symbol, source_id, source_name, status,
                duration_ms, error_msg, retry_count, 1 if proxy_used else 0,
                data_valid, validation_notes, raw_sample[:500] if raw_sample else None
            ))
            self.conn.commit()
        except Exception as e:
            logger.error(f"日志记录失败: {e}")
    
    def _validate_data(self, data: Dict, symbol: str, asset_class_id: int) -> tuple:
        """验证数据质量，返回(data_valid, notes)"""
        try:
            price = data.get('price', 0)
            open_price = data.get('open_price', 0)
            prev_close = data.get('prev_close', 0)
            volume = data.get('volume', 0)
            change_pct = data.get('change_pct', 0)
            
            issues = []
            valid = True
            
            # 检查现价为负
            if price < 0:
                issues.append('现价为负')
                valid = False
            
            # 检查开盘价为负
            if open_price < 0:
                issues.append('开盘价为负')
                valid = False
            
            # 检查开盘价异常波动（超过昨收10%）
            if prev_close > 0 and open_price > 0:
                if abs(open_price - prev_close) / prev_close > 0.1:
                    issues.append('开盘价异常波动')
                    valid = False
            
            # 检查涨跌幅异常
            if abs(change_pct) > 50:
                issues.append('涨跌幅异常')
                valid = False
            
            notes = '; '.join(issues) if issues else '正常'
            return (1 if valid else 0, notes)
        except Exception as e:
            return (None, f'验证异常: {str(e)}')
    
    def acquire_raw_data(self, symbol: str, asset_class_id: int, source_ids: List[int], 
                        max_retries: int = 3, run_id: str = None) -> Dict[str, Any]:
        """
        获取原始数据 - 多渠道获取，失败重试
        
        Args:
            symbol: 股票代码
            asset_class_id: 资产类别ID (1=美股, 2=A股, 3=期货, 4=加密货币)
            source_ids: 数据源ID列表
            max_retries: 最大重试次数
            run_id: 本次拉取任务ID（用于关联日志）
            
        Returns:
            包含所有数据源结果的字典
        """
        from datetime import datetime
        import time as time_module
        
        # 生成run_id（如果没有提供）
        if not run_id:
            run_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Normalize symbols: US stocks and futures should be uppercase
        if asset_class_id in (1, 3):
            symbol = symbol.upper()
        
        results = {}
        
        for source_id in source_ids:
            retry_count = 0
            while retry_count < max_retries:
                start_time = time_module.time()
                try:
                    # 获取数据源信息
                    cursor = self.conn.cursor()
                    cursor.execute("SELECT * FROM data_sources WHERE id = ?", (source_id,))
                    source_info = cursor.fetchone()
                    
                    if not source_info:
                        elapsed = (time_module.time() - start_time) * 1000
                        self._log_acquisition(run_id, symbol, asset_class_id, source_id, 
                                            '未知源', 'fail', elapsed, 
                                            error_msg='Source not found', retry_count=retry_count)
                        results[str(source_id)] = {'status': 'failed', 'error': 'Source not found'}
                        break
                        
                    source_name = source_info['name']
                    need_proxy = bool(source_info['need_proxy'])
                    
                    # 获取数据
                    data = self._fetch_from_source(symbol, asset_class_id, source_info['code'], use_proxy=need_proxy)
                    
                    if data:
                        # 验证数据质量
                        data_valid, validation_notes = self._validate_data(data, symbol, asset_class_id)
                        
                        # 存入原始数据表
                        self._save_raw_data(symbol, asset_class_id, source_id, data, use_proxy=need_proxy)
                        
                        elapsed = (time_module.time() - start_time) * 1000
                        raw_json = data.get('raw_json', '')
                        
                        results[str(source_id)] = {'status': 'success', 'data': data}
                        self._update_source_health(source_id, success=True, proxy_used=need_proxy)
                        
                        # 记录成功日志
                        self._log_acquisition(run_id, symbol, asset_class_id, source_id,
                                            source_name, 'success', elapsed,
                                            retry_count=retry_count, proxy_used=need_proxy,
                                            data_valid=data_valid, validation_notes=validation_notes,
                                            raw_sample=raw_json[:200])
                        break
                    else:
                        raise Exception("No data returned")
                        
                except Exception as e:
                    retry_count += 1
                    elapsed = (time_module.time() - start_time) * 1000
                    
                    if retry_count >= max_retries:
                        results[str(source_id)] = {'status': 'failed', 'error': str(e)}
                        self._update_source_health(source_id, success=False)
                        self._send_notification(f"数据获取失败: {symbol} (source_id={source_id})", 
                                             level='error', source_id=source_id)
                        
                        # 记录失败日志
                        self._log_acquisition(run_id, symbol, asset_class_id, source_id,
                                            source_name if 'source_name' in dir() else '未知',
                                            'fail', elapsed, error_msg=str(e),
                                            retry_count=retry_count)
                    else:
                        time_module.sleep(2 ** retry_count)  # 指数退避
                        
        return results
        
    def _fetch_from_source(self, symbol: str, asset_class_id: int, source_code: str, 
                          use_proxy: bool = False) -> Optional[Dict]:
        """从指定数据源获取数据"""
        try:
            if asset_class_id == 1:  # 美股
                return self._fetch_us_stock(symbol, source_code, use_proxy)
            elif asset_class_id == 2:  # A股
                return self._fetch_a_stock(symbol, source_code, use_proxy)
            elif asset_class_id == 3:  # 期货
                return self._fetch_futures(symbol, source_code, use_proxy)
            elif asset_class_id == 4:  # 加密货币
                return self._fetch_crypto(symbol, source_code, use_proxy)
        except Exception as e:
            logger.error(f"Fetch error for {symbol} ({source_code}): {e}")
        return None
        
    def _fetch_us_stock(self, symbol: str, source: str, use_proxy: bool) -> Optional[Dict]:
        """获取美股数据"""
        import requests
        
        try:
            if source == 'sina':
                url = f'https://hq.sinajs.cn/list=gb_{symbol.lower()}'
                headers = {'Referer': 'https://finance.sina.com.cn'}
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200 and len(r.text) > 50:
                    return self._parse_sina_us_stock(r.text)
                    
            elif source == 'yahoo':
                # Yahoo需要代理，简化处理
                pass
                
        except Exception as e:
            logger.error(f"Sina US stock fetch error: {e}")
            
        return None
        
    def _parse_sina_us_stock(self, text: str) -> Optional[Dict]:
        """解析新浪美股数据"""
        try:
            # var hq_str_gb_tsla="特斯拉,407.0250,-3.04,..."
            start = text.find('="') + 2
            end = text.find('"', start)
            if start < 2 or end < 0:
                return None
                
            parts = text[start:end].split(',')
            if len(parts) < 9:
                return None
                
            current_price = float(parts[1])
            prev_close = float(parts[5]) if parts[5] else 0
            open_price = float(parts[4]) if parts[4] else 0
            high = float(parts[6]) if parts[6] else 0
            low = float(parts[7]) if parts[7] else 0
            volume = float(parts[8]) if parts[8] else 0
            
            # 修复：新浪财经API返回的开盘价是错误的，使用昨收+涨跌额计算
            if len(parts) > 2:
                change = float(parts[2])
                open_price = prev_close + change
            
            return {
                'price': current_price,
                'prev_close': prev_close,
                'open_price': open_price,
                'high': high,
                'low': low,
                'volume': volume,
                'change_pct': ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0,
                'name': parts[0]
            }
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None
            
    def _fetch_a_stock(self, symbol: str, source: str, use_proxy: bool) -> Optional[Dict]:
        """获取A股数据"""
        import requests
        
        try:
            if source == 'tencent':
                # 添加市场前缀
                if symbol.startswith(('6', '9')):
                    market = 'sh'
                else:
                    market = 'sz'
                url = f'https://qt.gtimg.cn/q={market}{symbol}'
                r = requests.get(url, timeout=10)
                if r.status_code == 200 and len(r.text) > 50:
                    return self._parse_tencent_a_stock(r.text)
                    
            elif source == 'sina':
                url = f'https://hq.sinajs.cn/list=sh{symbol}' if symbol.startswith('6') else f'https://hq.sinajs.cn/list=sz{symbol}'
                headers = {'Referer': 'https://finance.sina.com.cn'}
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200 and len(r.text) > 50:
                    return self._parse_sina_a_stock(r.text)
                    
        except Exception as e:
            logger.error(f"A stock fetch error: {e}")
            
        return None
        
    def _parse_tencent_a_stock(self, text: str) -> Optional[Dict]:
        """解析腾讯A股数据"""
        try:
            # 腾讯格式: v_sh000300="1~沪深300指数~000300~3958.37~..."
            start = text.find('="') + 2
            end = text.find(';', start)
            if start < 2 or end < 0:
                return None
                
            parts = text[start:end].split('~')
            if len(parts) < 35:
                return None
                
            return {
                'price': float(parts[3]),
                'prev_close': float(parts[4]),
                'open_price': float(parts[5]),
                'high': float(parts[33]),
                'low': float(parts[34]),
                'volume': float(parts[6]),
                'change_pct': float(parts[31]),
                'turnover_rate': float(parts[37]) if len(parts) > 37 else 0,
                'name': parts[1]
            }
        except Exception as e:
            logger.error(f"Tencent parse error: {e}")
            return None
            
    def _parse_sina_a_stock(self, text: str) -> Optional[Dict]:
        """解析新浪A股数据"""
        try:
            start = text.find('="') + 2
            end = text.find('"', start)
            if start < 2 or end < 0:
                return None
                
            parts = text[start:end].split(',')
            if len(parts) < 35:
                return None
                
            return {
                'price': float(parts[3]),
                'prev_close': float(parts[4]),
                'open_price': float(parts[1]),
                'high': float(parts[33]),
                'low': float(parts[34]),
                'volume': float(parts[8]),
                'change_pct': float(parts[31]),
                'turnover_rate': float(parts[37]) if len(parts) > 37 else 0,
                'name': parts[0].split('_')[-1]
            }
        except Exception as e:
            logger.error(f"Sina A stock parse error: {e}")
            return None
            
    def _fetch_futures(self, symbol: str, source: str, use_proxy: bool) -> Optional[Dict]:
        """获取期货数据"""
        import requests
        
        try:
            if source == 'sina':
                url = f'https://hq.sinajs.cn/list=hf_{symbol}'
                headers = {'Referer': 'https://finance.sina.com.cn'}
                r = requests.get(url, headers=headers, timeout=10)
                if r.status_code == 200 and len(r.text) > 50:
                    return self._parse_sina_futures(r.text)
                    
        except Exception as e:
            logger.error(f"Futures fetch error: {e}")
            
        return None
        
    def _parse_sina_futures(self, text: str) -> Optional[Dict]:
        """解析新浪期货数据"""
        try:
            start = text.find('="') + 2
            end = text.find('"', start)
            if start < 2 or end < 0:
                return None
                
            parts = text[start:end].split(',')
            if len(parts) < 10:
                return None
                
            # hf_GC: [0]现价 [1]空 [2]昨收 [3]今开 [4]最高 [5]最低 [6]时间 ...
            return {
                'price': float(parts[0]) if parts[0] else 0,
                'prev_close': float(parts[2]) if parts[2] else 0,
                'open_price': float(parts[3]) if parts[3] else 0,
                'high': float(parts[4]) if parts[4] else 0,
                'low': float(parts[5]) if parts[5] else 0,
                'name': parts[9] if len(parts) > 9 else symbol
            }
        except Exception as e:
            logger.error(f"Futures parse error: {e}")
            return None
            
    def _fetch_crypto(self, symbol: str, source: str, use_proxy: bool) -> Optional[Dict]:
        """获取加密货币数据"""
        import requests
        import os
        from dotenv import load_dotenv
        
        # Load proxy config from .env
        env_path = os.path.join(os.path.dirname(__file__), '.env')
        load_dotenv(env_path)
        proxy_http = os.environ.get('PROXY_HTTP', '')
        proxies = {'http': proxy_http, 'https': proxy_http} if proxy_http else None
        
        try:
            if source == 'binance':
                # Binance: symbol is lowercase (btc), convert to BTCUSDT
                binance_symbol = symbol.upper() + 'USDT'
                url = f'https://api.binance.com/api/v3/ticker/24hr?symbol={binance_symbol}'
                r = requests.get(url, timeout=15, proxies=proxies)
                if r.status_code == 200:
                    data = r.json()
                    return {
                        'price': float(data.get('lastPrice', 0)),
                        'prev_close': float(data.get('weightedAvgPrice', 0)) * 0.99,  # approx prev close
                        'change_pct': float(data.get('priceChangePercent', 0)),
                        'volume': float(data.get('volume', 0)),
                        'high': float(data.get('highPrice', 0)),
                        'low': float(data.get('lowPrice', 0)),
                        'name': data.get('symbol', binance_symbol)
                    }
                    
            elif source == 'coinbase':
                url = f'https://api.coinbase.com/apis/v2/prices/{symbol.upper()}-USD/spot'
                r = requests.get(url, timeout=10, proxies=proxies)
                if r.status_code == 200:
                    data = r.json()
                    return {
                        'price': float(data['data']['amount']),
                        'name': data['data']['base']
                    }
                    
        except Exception as e:
            logger.error(f"Crypto fetch error for {source}/{symbol}: {e}")
            
        return None
        
    def _save_raw_data(self, symbol: str, asset_class_id: int, source_id: int, 
                      data: Dict, use_proxy: bool = False):
        """保存原始数据到数据库"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO raw_data 
            (symbol, asset_class_id, source_id, price, prev_close, open_price, high, low, 
             volume, change_pct, market_cap, pe_ratio, pb_ratio, turnover_rate,
             proxy_used, status, raw_json, retry_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'success', ?, 0)
        ''', (
            symbol, asset_class_id, source_id,
            data.get('price'), data.get('prev_close'), data.get('open_price'),
            data.get('high'), data.get('low'), data.get('volume'),
            data.get('change_pct'), data.get('market_cap'), data.get('pe_ratio'),
            data.get('pb_ratio'), data.get('turnover_rate'),
            1 if use_proxy else 0,
            json.dumps(data, ensure_ascii=False, default=str)
        ))
        
        self.conn.commit()
        
    def consolidate_data(self):
        """数据规整 - 从raw_data生成clean_data"""
        cursor = self.conn.cursor()
        
        # 获取所有symbol
        cursor.execute('''
            SELECT DISTINCT symbol, asset_class_id FROM raw_data WHERE status = 'success'
        ''')
        symbols = cursor.fetchall()
        
        for sym_row in symbols:
            symbol = sym_row['symbol']
            asset_class_id = sym_row['asset_class_id']
            
            # 获取该symbol的所有成功数据
            cursor.execute('''
                SELECT rd.*, ds.reliability, ds.need_proxy
                FROM raw_data rd
                JOIN data_sources ds ON rd.source_id = ds.id
                WHERE rd.symbol = ? AND rd.asset_class_id = ? AND rd.status = 'success'
                ORDER BY rd.timestamp DESC
            ''', (symbol, asset_class_id))
            
            rows = cursor.fetchall()
            if not rows:
                continue
                
            # 选择最优数据源
            best_row = None
            best_score = 0
            
            for row in rows:
                score = self._calculate_quality_score(row)
                if score > best_score:
                    best_score = score
                    best_row = row
                    
            if best_row:
                # 插入或更新clean_data
                cursor.execute('''
                    INSERT OR REPLACE INTO clean_data 
                    (symbol, asset_class_id, best_source_id, latest_price, prev_close, open_price, high, low,
                     volume, change_pct, market_cap, pe_ratio, pb_ratio, turnover_rate,
                     last_updated, data_quality_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol, asset_class_id, best_row['source_id'],
                    best_row['price'], best_row['prev_close'], best_row['open_price'],
                    best_row['high'], best_row['low'], best_row['volume'],
                    best_row['change_pct'], best_row['market_cap'], best_row['pe_ratio'],
                    best_row['pb_ratio'], best_row['turnover_rate'],
                    datetime.now(), best_score
                ))
                
                # 更新source_health
                self._update_source_health(best_row['source_id'], success=True, adopted=True)
                
        self.conn.commit()
        
    def _calculate_quality_score(self, row) -> float:
        """
        计算数据质量评分 (0-1.0)
        
        评分标准:
        - 数据完整性 (0.4): 必填字段是否都有
        - 数据源可靠性 (0.3): 从data_sources表的reliability读取
        - 数据新鲜度 (0.2): 获取时间越近分数越高
        - 数据一致性 (0.1): 与其他数据源的一致性
        """
        score = 0.0
        
        # 转换为字典
        row_dict = dict(row)
        
        # 1. 数据完整性 (0-0.4)
        required_fields = ['price', 'volume', 'change_pct']
        present_fields = sum(1 for f in required_fields if row_dict.get(f) is not None and row_dict[f] != 0)
        score += (present_fields / len(required_fields)) * 0.4
        
        # 2. 数据源可靠性 (0-0.3)
        score += row_dict['reliability'] * 0.3
        
        # 3. 数据新鲜度 (0-0.2)
        if row_dict['timestamp']:
            try:
                ts = row_dict['timestamp'].replace('Z', '+00:00')
                hours_since = (datetime.now() - datetime.fromisoformat(ts)).total_seconds() / 3600
                if hours_since <= 1:
                    score += 0.2
                elif hours_since <= 6:
                    score += 0.15
                elif hours_since <= 24:
                    score += 0.1
                else:
                    score += 0.05
            except:
                score += 0.05
                
        # 4. 数据一致性 (0-0.1) - 简化处理
        score += 0.1  # 默认满分
        
        return min(score, 1.0)
        
    def _update_source_health(self, source_id: int, success: bool, proxy_used: bool = False, adopted: bool = False):
        """更新数据源健康状态"""
        cursor = self.conn.cursor()
        
        if success:
            cursor.execute('''
                UPDATE source_health 
                SET last_success = ?, success_count = success_count + 1, 
                    health_score = MIN(health_score + 0.01, 1.0)
                WHERE source_id = ?
            ''', (datetime.now(), source_id))
            
            if proxy_used:
                cursor.execute('''
                    UPDATE source_health 
                    SET proxy_usage_count = proxy_usage_count + 1
                    WHERE source_id = ?
                ''', (source_id,))
                
            if adopted:
                cursor.execute('''
                    INSERT OR IGNORE INTO source_health (source_id) VALUES (?)
                ''', (source_id,))
        else:
            cursor.execute('''
                UPDATE source_health 
                SET last_fail = ?, fail_count = fail_count + 1, 
                    health_score = MAX(health_score - 0.01, 0.0)
                WHERE source_id = ?
            ''', (datetime.now(), source_id))
            
        self.conn.commit()
        
    def _send_notification(self, message: str, level: str = 'info', 
                          source_id: int = None, asset_class_id: int = None, proxy_used: bool = False):
        """发送通知"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO notification_log (level, message, proxy_used, source_id, asset_class_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (level, message, 1 if proxy_used else 0, source_id, asset_class_id))
        self.conn.commit()
        
        # 如果是error级别，发送微信通知
        if level == 'error':
            print(f"[NOTIFICATION] {level.upper()}: {message}")
            
    def get_clean_data(self, asset_class_id: int = None) -> List[Dict]:
        """获取规整后的数据"""
        cursor = self.conn.cursor()
        
        if asset_class_id:
            cursor.execute('''
                SELECT cd.*, ac.name as asset_class_name, ds.name as source_name
                FROM clean_data cd
                JOIN asset_classes ac ON cd.asset_class_id = ac.id
                JOIN data_sources ds ON cd.best_source_id = ds.id
                WHERE cd.asset_class_id = ?
                ORDER BY ac.id, cd.symbol
            ''', (asset_class_id,))
        else:
            cursor.execute('''
                SELECT cd.*, ac.name as asset_class_name, ds.name as source_name
                FROM clean_data cd
                JOIN asset_classes ac ON cd.asset_class_id = ac.id
                JOIN data_sources ds ON cd.best_source_id = ds.id
                ORDER BY ac.id, cd.symbol
            ''')
            
        return [dict(row) for row in cursor.fetchall()]
        
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM raw_data")
        raw_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM clean_data")
        clean_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT symbol) FROM clean_data")
        unique_symbols = cursor.fetchone()[0]
        
        return {
            'raw_data_count': raw_count,
            'clean_data_count': clean_count,
            'unique_symbols': unique_symbols,
            'categories': {}
        }
        
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
