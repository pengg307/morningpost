# 数据获取管理系统开发任务

## 项目背景
构建一个完整的市场数据获取和管理系统，为晨报推送提供数据支持。

## 核心需求
1. **多渠道数据获取** - 每个品种至少2个数据源
2. **原始数据永存** - 每次获取都存入数据库
3. **数据规整** - 去重、取最优、质量评分
4. **代理Fallback** - 能不用就不用，用不了通知
5. **定时任务** - 每12小时自动获取

## 数据库设计

### 1. asset_classes (资产类别表)
```sql
CREATE TABLE asset_classes (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT
);
-- 数据: 1-us_stock, 2-a_stock, 3-futures, 4-crypto
```

### 2. data_sources (数据源表)
```sql
CREATE TABLE data_sources (
    id INTEGER PRIMARY KEY,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    need_proxy INTEGER DEFAULT 0,
    reliability REAL DEFAULT 1.0
);
-- 数据: 1-sina, 2-tencent, 3-eastmoney, 4-yahoo, 5-yfinance, 6-binance, 7-coinbase, 8-firecrawl
```

### 3. raw_data (原始数据表)
```sql
CREATE TABLE raw_data (
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
    retry_count INTEGER DEFAULT 0
);
```

### 4. clean_data (规整数据表)
```sql
CREATE TABLE clean_data (
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
    data_quality_score REAL
);
```

### 5. source_health (数据源健康表)
```sql
CREATE TABLE source_health (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    last_success DATETIME,
    last_fail DATETIME,
    success_count INTEGER DEFAULT 0,
    fail_count INTEGER DEFAULT 0,
    proxy_usage_count INTEGER DEFAULT 0,
    rate_limited_count INTEGER DEFAULT 0,
    health_score REAL DEFAULT 1.0
);
```

### 6. notification_log (通知日志表)
```sql
CREATE TABLE notification_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    level TEXT,
    message TEXT,
    proxy_used INTEGER DEFAULT 0,
    source_id INTEGER,
    asset_class_id INTEGER
);
```

## 配置文件 (data_source_config.ini)

```ini
[us_stocks]
TSLA=Tesla
AAPL=Apple
GOOGL=Google
MSFT=Microsoft
NVDA=NVIDIA
AMZN=Amazon
META=Meta
NFLX=Netflix
TSM=TSMC
INTC=Intel
SPCX=SpaceX

[futures]
GC=Gold
SI=Silver
CL=Crude Oil
NG=Natural Gas
HG=Copper
ES=S&P 500
NQ=Nasdaq 100
YM=Dow Jones
RTY=Russell 2000

[crypto]
BTC=Bitcoin
ETH=Ethereum
BNB=Binance Coin
SOL=Solana
XRP=Ripple
ADA=Cardano
DOGE=Dogecoin
AVAX=Avalanche
DOT=Polkadot
LINK=Chainlink

[a_sectors]
电子=000688,002384,688001,688012,002415,603501,000725,688981,688041,002230,688111,002049,688036,688396,688008,002371,688256,688017,688082,688126
存储=001309,300223,688256,688008,300308,688385,688072,688047,688020,688187,688206,688056,688118,688172,688279,688258,688052,688085,688166
面板=000725,000016,600745,600839,601234,603005,600584,600703,603228,603160,603501,603986,601127,600345,600207,600563,600637,600845,600747,600890
算力=688256,000977,300308,688041,688111,002415,603501,688981,688008,688396,688012,002371,688001,688017,688082,688126,688256,688047,688056,688118

[proxy_config]
tencent_no_proxy=true
sina_no_proxy=true
yahoo_need_proxy=true
binance_need_proxy=true
coinbase_no_proxy=true
firecrawl_no_proxy=true
eastmoney_no_proxy=true
```

## 实现要求

### 1. 数据获取函数

每个数据类型需要实现多个数据源的获取函数：

```python
# 美股
def fetch_us_stock_sina(symbol, proxy=None): ...
def fetch_us_stock_yahoo(symbol, proxy=None): ...

# A股
def fetch_a_stock_tencent(symbol, proxy=None): ...
def fetch_a_stock_sina(symbol, proxy=None): ...
def fetch_a_stock_eastmoney(symbol, proxy=None): ...

# 期货
def fetch_futures_sina(symbol, proxy=None): ...
def fetch_futures_yfinance(symbol, proxy=None): ...

# 加密货币
def fetch_crypto_binance(symbol, proxy=None): ...
def fetch_crypto_coinbase(symbol, proxy=None): ...
```

### 2. 代理Fallback策略

```python
def fetch_with_fallback(symbol, data_type, sources):
    """
    多渠道获取，代理Fallback
    
    策略:
    1. 优先尝试不用代理的数据源
    2. 如果不用代理失败，尝试用代理
    3. 如果所有数据源都失败，发送通知
    """
    results = {}
    
    for source in sources:
        # 先尝试不用代理
        try:
            data = fetch_from_source(symbol, source, use_proxy=False)
            if data:
                results[source] = {'status': 'success', 'data': data, 'proxy_used': False}
                continue
        except:
            pass
            
        # 不用代理失败，尝试用代理
        try:
            data = fetch_from_source(symbol, source, use_proxy=True)
            if data:
                results[source] = {'status': 'success', 'data': data, 'proxy_used': True}
                log_notification(f"使用代理获取成功: {symbol} ({source})", proxy_used=True)
                continue
        except:
            pass
            
        results[source] = {'status': 'failed', 'error': 'All attempts failed'}
        
    return results
```

### 3. 数据规整逻辑

```python
def consolidate_data():
    """
    数据规整 - 从raw_data生成clean_data
    
    策略:
    1. 对每个symbol，获取所有数据源的数据
    2. 计算每个数据源的质量评分
    3. 选择质量最高的数据
    4. 存入clean_data
    """
    # 1. 获取所有symbol
    symbols = get_all_symbols()
    
    for symbol in symbols:
        # 2. 获取该symbol的所有原始数据
        raw_records = get_raw_data_for_symbol(symbol)
        
        if not raw_records:
            continue
            
        # 3. 评估每个数据源的质量
        best_record = None
        best_score = 0
        
        for record in raw_records:
            score = calculate_quality_score(record)
            if score > best_score:
                best_score = score
                best_record = record
                
        # 4. 存入clean_data
        insert_clean_data(best_record, best_score)
        
        # 5. 更新source_health
        update_source_health(best_record['source_id'], adopted=True)
```

### 4. 数据质量评分标准

```python
def calculate_quality_score(record):
    """
    数据质量评分 (0-1.0)
    
    评分标准:
    - 数据完整性 (0.4): 必填字段是否都有
    - 数据源可靠性 (0.3): 从data_sources表的reliability读取
    - 数据新鲜度 (0.2): 获取时间越近分数越高
    - 数据一致性 (0.1): 与其他数据源的一致性
    """
    score = 0.0
    
    # 1. 数据完整性 (0-0.4)
    required_fields = ['price', 'volume', 'change_pct']
    present_fields = sum(1 for f in required_fields if record.get(f) is not None)
    score += (present_fields / len(required_fields)) * 0.4
    
    # 2. 数据源可靠性 (0-0.3)
    source_reliability = get_source_reliability(record['source_id'])
    score += source_reliability * 0.3
    
    # 3. 数据新鲜度 (0-0.2)
    hours_since_update = (datetime.now() - record['timestamp']).total_seconds() / 3600
    if hours_since_update <= 1:
        score += 0.2
    elif hours_since_update <= 6:
        score += 0.15
    elif hours_since_update <= 24:
        score += 0.1
    else:
        score += 0.05
        
    # 4. 数据一致性 (0-0.1)
    if record['data_type'] in ['us_stock', 'a_stock']:
        # 与其他数据源的价格差异
        consistency = check_price_consistency(record['symbol'], record['price'])
        score += consistency * 0.1
        
    return score
```

### 5. 定时任务

```python
# fetch_all_data.py
def main():
    # 1. 从config读取要获取的股票列表
    config = load_config()
    
    # 2. 获取美股数据
    for symbol, name in config['us_stocks']:
        sources = ['sina', 'yahoo']  # 新浪优先，Yahoo备用
        results = fetch_with_fallback(symbol, 'us_stock', sources)
        save_raw_data(results)
        
    # 3. 获取期货数据
    for symbol, name in config['futures']:
        sources = ['sina', 'yfinance']
        results = fetch_with_fallback(symbol, 'futures', sources)
        save_raw_data(results)
        
    # 4. 获取加密货币数据
    for symbol, name in config['crypto']:
        sources = ['binance', 'coinbase']
        results = fetch_with_fallback(symbol, 'crypto', sources)
        save_raw_data(results)
        
    # 5. 获取A股数据
    for sector, symbols in config['a_sectors']:
        for symbol in symbols:
            sources = ['tencent', 'sina', 'eastmoney']
            results = fetch_with_fallback(symbol, 'a_stock', sources)
            save_raw_data(results)
            
    # 6. 数据规整
    consolidate_data()
    
    # 7. 统计信息
    print_stats()
```

### 6. 晨报数据准备

```python
# prepare_morning_data.py
def main():
    # 1. 从clean_data读取规整后的数据
    clean_data = get_all_clean_data()
    
    # 2. 按数据类型分组
    data_by_type = {
        'us_stock': [d for d in clean_data if d['asset_class'] == 'us_stock'],
        'futures': [d for d in clean_data if d['asset_class'] == 'futures'],
        'crypto': [d for d in clean_data if d['asset_class'] == 'crypto'],
        'a_stock': [d for d in clean_data if d['asset_class'] == 'a_stock']
    }
    
    # 3. 保存到临时文件
    save_to_json(data_by_type)
    
    # 4. 返回数据供晨报分析使用
    return data_by_type
```

## 输出要求

1. **完整的Python代码** - 包含所有数据获取函数
2. **数据库初始化脚本** - 创建所有表和索引
3. **配置文件** - data_source_config.ini
4. **定时任务脚本** - fetch_all_data.py
5. **晨报数据准备脚本** - prepare_morning_data.py
6. **测试用例** - 验证数据获取和规整逻辑

## 注意事项

1. **不要硬编码敏感信息** - API Key从.env读取
2. **错误处理** - 每个数据获取函数都要有try-except
3. **日志记录** - 记录每次获取的成功/失败状态
4. **代理使用** - 记录是否使用了代理
5. **数据完整性** - 确保必填字段都有值
6. **性能优化** - 避免重复获取相同数据

## 完成标准

1. ✅ 数据库表创建成功
2. ✅ 所有数据源获取函数实现
3. ✅ 代理Fallback逻辑工作正常
4. ✅ 数据规整逻辑正确
5. ✅ 定时任务可以正常运行
6. ✅ 晨报数据准备完成
7. ✅ 所有测试通过
