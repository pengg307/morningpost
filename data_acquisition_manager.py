"""
数据获取管理器 - 完整架构设计
1. 原始数据表 (raw_data) - 永不删除，记录每次获取
2. 规整数据表 (clean_data) - 去重、合并、取最优
3. 数据源健康表 (source_health) - 记录代理使用情况
"""
import sqlite3
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import configparser

class DataAcquisitionManager:
    """数据获取管理器"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), 'data', 'market_data.db')
        self.db_path = db_path
        self.config = self._load_config()
        self.conn = sqlite3.connect(db_path)
        self._create_tables()
        
    def _load_config(self):
        """加载配置文件"""
        config_path = os.path.join(os.path.dirname(__file__), 'data_source_config.ini')
        config = configparser.ConfigParser()
        config.read(config_path, encoding='utf-8')
        return config
        
    def _create_tables(self):
        """创建数据库表"""
        cursor = self.conn.cursor()
        
        # 1. 原始数据表 - 记录每次获取的所有数据
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS raw_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,          -- 股票代码
                data_type TEXT NOT NULL,       -- us_stock/futures/crypto/a_stock
                source TEXT NOT NULL,          -- sina/yahoo/binance/tencent等
                price REAL,                    -- 价格
                prev_close REAL,               -- 昨收
                open_price REAL,               -- 开盘
                high REAL,                     -- 最高
                low REAL,                      -- 最低
                volume REAL,                   -- 成交量
                change_pct REAL,               -- 涨跌幅
                market_cap REAL,               -- 市值
                pe_ratio REAL,                 -- 市盈率
                pb_ratio REAL,                 -- 市净率
                turnover_rate REAL,            -- 换手率
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,  -- 获取时间
                proxy_used INTEGER DEFAULT 0,  -- 是否使用代理
                status TEXT DEFAULT 'success', -- success/error/limited
                raw_json TEXT,                 -- 原始JSON数据
                retry_count INTEGER DEFAULT 0  -- 重试次数
            )
        ''')
        
        # 2. 规整数据表 - 去重后的可用数据
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clean_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                data_type TEXT NOT NULL,
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
                best_source TEXT,              -- 最优数据源
                last_updated DATETIME,
                data_quality_score REAL        -- 数据质量评分
            )
        ''')
        
        # 3. 数据源健康表 - 记录每个数据源的可用性
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS source_health (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,          -- 数据源名称
                data_type TEXT NOT NULL,       -- 数据类型
                last_success DATETIME,
                last_fail DATETIME,
                success_count INTEGER DEFAULT 0,
                fail_count INTEGER DEFAULT 0,
                proxy_needed INTEGER DEFAULT 0,
                rate_limited INTEGER DEFAULT 0,
                health_score REAL              -- 健康度评分
            )
        ''')
        
        # 4. 通知日志表 - 记录代理使用和通知
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                level TEXT,                    -- info/warning/error
                message TEXT,
                proxy_used INTEGER DEFAULT 0,
                source TEXT,
                data_type TEXT
            )
        ''')
        
        self.conn.commit()
        
    def acquire_raw_data(self, symbol: str, data_type: str, sources: List[str], 
                        max_retries: int = 3) -> Dict[str, Any]:
        """
        获取原始数据 - 多渠道获取，失败重试
        
        Args:
            symbol: 股票代码
            data_type: 数据类型 (us_stock/futures/crypto/a_stock)
            sources: 数据源列表
            max_retries: 最大重试次数
            
        Returns:
            包含所有数据源结果的字典
        """
        results = {}
        
        for source in sources:
            retry_count = 0
            while retry_count < max_retries:
                try:
                    # 检查是否需要代理
                    need_proxy = self._check_proxy_required(source, data_type)
                    
                    # 获取数据
                    data = self._fetch_from_source(symbol, data_type, source, use_proxy=need_proxy)
                    
                    if data:
                        # 存入原始数据表
                        self._save_raw_data(symbol, data_type, source, data, use_proxy=need_proxy)
                        results[source] = {'status': 'success', 'data': data}
                        self._update_source_health(source, data_type, success=True)
                        break
                    else:
                        raise Exception("No data returned")
                        
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        results[source] = {'status': 'failed', 'error': str(e)}
                        self._update_source_health(source, data_type, success=False)
                        self._send_notification(f"数据获取失败: {symbol} ({source})", level='error')
                    else:
                        # 重试前等待
                        import time
                        time.sleep(2 ** retry_count)  # 指数退避
                        
        return results
        
    def _check_proxy_required(self, source: str, data_type: str) -> bool:
        """
        检查是否需要代理 - 能不用则不用
        
        Returns:
            True: 需要代理, False: 不需要代理
        """
        # 从配置读取
        proxy_config = self.config.get('proxy_config', fallback={})
        
        # 默认策略：大多数国内数据源不需要代理
        no_proxy_sources = {
            'sina', 'tencent', 'eastmoney', 'firecrawl', 'coinbase'
        }
        
        # 需要代理的数据源
        proxy_sources = {
            'yahoo', 'binance'  # 某些地区需要代理访问
        }
        
        # 优先尝试不使用代理
        if source in no_proxy_sources:
            return False
        elif source in proxy_sources:
            # 先尝试不用代理，失败后再用代理
            return False  # 总是先尝试不用代理
            
        return False
        
    def _fetch_from_source(self, symbol: str, data_type: str, source: str, 
                          use_proxy: bool = False) -> Optional[Dict]:
        """
        从指定数据源获取数据
        
        Returns:
            数据字典，失败返回None
        """
        # 根据数据类型和数据源选择获取函数
        fetch_func = self._get_fetch_function(data_type, source)
        if not fetch_func:
            return None
            
        try:
            # 如果有代理，设置代理
            if use_proxy:
                proxy = self._get_proxy()
            else:
                proxy = None
                
            # 获取数据
            data = fetch_func(symbol, proxy=proxy)
            return data
            
        except Exception as e:
            # 如果不用代理失败了，尝试用代理
            if not use_proxy:
                try:
                    proxy = self._get_proxy()
                    data = fetch_func(symbol, proxy=proxy)
                    self._log_notification(f"使用代理获取成功: {symbol} ({source})", 
                                         level='info', proxy_used=True)
                    return data
                except Exception as e2:
                    self._log_notification(f"代理也失败: {symbol} ({source}): {e2}", 
                                         level='warning', proxy_used=True)
                    return None
            return None
            
    def _get_fetch_function(self, data_type: str, source: str):
        """获取对应的数据获取函数"""
        # 映射关系
        fetch_functions = {
            ('us_stock', 'sina'): self._fetch_us_stock_sina,
            ('us_stock', 'yahoo'): self._fetch_us_stock_yahoo,
            ('futures', 'sina'): self._fetch_futures_sina,
            ('futures', 'yfinance'): self._fetch_futures_yfinance,
            ('crypto', 'binance'): self._fetch_crypto_binance,
            ('crypto', 'coinbase'): self._fetch_crypto_coinbase,
            ('a_stock', 'tencent'): self._fetch_a_stock_tencent,
            ('a_stock', 'sina'): self._fetch_a_stock_sina,
            ('a_stock', 'eastmoney'): self._fetch_a_stock_eastmoney,
        }
        
        return fetch_functions.get((data_type, source))
        
    def _save_raw_data(self, symbol: str, data_type: str, source: str, 
                      data: Dict, use_proxy: bool = False):
        """保存原始数据到数据库"""
        cursor = self.conn.cursor()
        
        cursor.execute('''
            INSERT INTO raw_data 
            (symbol, data_type, source, price, prev_close, open_price, high, low, 
             volume, change_pct, market_cap, pe_ratio, pb_ratio, turnover_rate,
             proxy_used, status, raw_json, retry_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'success', ?, 0)
        ''', (
            symbol, data_type, source,
            data.get('price'), data.get('prev_close'), data.get('open_price'),
            data.get('high'), data.get('low'), data.get('volume'),
            data.get('change_pct'), data.get('market_cap'), data.get('pe_ratio'),
            data.get('pb_ratio'), data.get('turnover_rate'),
            1 if use_proxy else 0,
            json.dumps(data, ensure_ascii=False)
        ))
        
        self.conn.commit()
        
    def consolidate_data(self):
        """
        数据规整 - 从原始数据生成规整数据
        策略：取最新、最准确的数据源
        """
        cursor = self.conn.cursor()
        
        # 获取所有symbol
        cursor.execute('SELECT DISTINCT symbol, data_type FROM raw_data')
        symbols = cursor.fetchall()
        
        for symbol, data_type in symbols:
            # 获取该symbol的所有数据源
            cursor.execute('''
                SELECT source, timestamp, raw_json, proxy_used 
                FROM raw_data 
                WHERE symbol = ? AND data_type = ? AND status = 'success'
                ORDER BY timestamp DESC
            ''', (symbol, data_type))
            
            rows = cursor.fetchall()
            if not rows:
                continue
                
            # 选择最优数据源（优先不用代理的，最新的）
            best_source = None
            best_data = None
            
            for row in rows:
                source, timestamp, raw_json, proxy_used = row
                data = json.loads(raw_json)
                
                # 选择标准：不用代理 > 用代理，最新数据
                if best_source is None or (proxy_used == 0 and best_data.get('proxy_used', 1) == 1):
                    best_source = source
                    best_data = data
                    
            if best_data:
                # 插入或更新规整数据
                cursor.execute('''
                    INSERT OR REPLACE INTO clean_data 
                    (symbol, data_type, latest_price, prev_close, open_price, high, low,
                     volume, change_pct, market_cap, pe_ratio, pb_ratio, turnover_rate,
                     best_source, last_updated, data_quality_score)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol, data_type,
                    best_data.get('price'), best_data.get('prev_close'), 
                    best_data.get('open_price'), best_data.get('high'), best_data.get('low'),
                    best_data.get('volume'), best_data.get('change_pct'),
                    best_data.get('market_cap'), best_data.get('pe_ratio'),
                    best_data.get('pb_ratio'), best_data.get('turnover_rate'),
                    best_source, datetime.now(), 1.0  # 质量评分满分
                ))
                
        self.conn.commit()
        
    def _update_source_health(self, source: str, data_type: str, success: bool):
        """更新数据源健康状态"""
        cursor = self.conn.cursor()
        
        if success:
            cursor.execute('''
                UPDATE source_health 
                SET last_success = ?, success_count = success_count + 1, health_score = MIN(health_score + 0.1, 1.0)
                WHERE source = ? AND data_type = ?
            ''', (datetime.now(), source, data_type))
        else:
            cursor.execute('''
                UPDATE source_health 
                SET last_fail = ?, fail_count = fail_count + 1, rate_limited = rate_limited + 1, health_score = MAX(health_score - 0.1, 0.0)
                WHERE source = ? AND data_type = ?
            ''', (datetime.now(), source, data_type))
                
        self.conn.commit()
        
    def _send_notification(self, message: str, level: str = 'info', 
                          proxy_used: bool = False, source: str = None, data_type: str = None):
        """发送通知（微信/Hermes）"""
        # 记录到通知日志表
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO notification_log (level, message, proxy_used, source, data_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (level, message, 1 if proxy_used else 0, source, data_type))
        self.conn.commit()
        
        # 如果是error级别，发送微信通知
        if level == 'error':
            # 这里可以集成Hermes微信通知
            print(f"[NOTIFICATION] {level.upper()}: {message}")
            
    def _log_notification(self, message: str, level: str = 'info', proxy_used: bool = False):
        """记录通知日志"""
        self._send_notification(message, level, proxy_used)
        
    def get_clean_data(self, data_type: str = None) -> List[Dict]:
        """获取规整后的数据"""
        cursor = self.conn.cursor()
        
        if data_type:
            cursor.execute('SELECT * FROM clean_data WHERE data_type = ?', (data_type,))
        else:
            cursor.execute('SELECT * FROM clean_data')
            
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        
        return [dict(zip(columns, row)) for row in rows]
        
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
