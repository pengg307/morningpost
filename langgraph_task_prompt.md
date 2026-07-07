# LangGraph数据获取管理系统开发任务

## 项目背景
构建一个完整的市场数据获取和管理系统，为晨报推送提供高质量数据支持。

## 核心目标
1. **多渠道数据获取** - 每个品种至少2个数据源，确保数据完整性
2. **原始数据永存** - 每次获取都存入SQLite数据库，不丢失
3. **数据规整** - 去重、取最优、质量评分
4. **代理Fallback** - 能不用就不用，不用才用，用不了通知
5. **定时任务** - 每12小时自动获取

## 状态机节点定义

### 1. 数据提取节点 (data_extraction)
- **职责**: 负责从各个数据源获取原始数据
- **输入**: 股票代码列表，数据源配置
- **输出**: 原始数据字典，包含每个数据源的结果
- **技能**: API调用，错误处理，代理管理

### 2. 数据验证节点 (data_validation)
- **职责**: 验证获取数据的完整性和有效性
- **输入**: 原始数据字典
- **输出**: 验证结果，标记无效数据
- **技能**: 数据校验，格式检查，异常检测

### 3. 数据规整节点 (data_consolidation)
- **职责**: 对验证后的数据进行去重、质量评分、选择最优数据
- **输入**: 验证后的数据
- **输出**: 规整后的数据，包含质量评分
- **技能**: 数据合并，质量评估，最优选择算法

### 4. 健康监控节点 (health_monitoring)
- **职责**: 更新数据源健康状态，记录使用情况
- **输入**: 规整后的数据，数据源信息
- **输出**: 健康状态更新，使用统计
- **技能**: 统计分析，状态更新，日志记录

### 5. 通知发送节点 (notification_sending)
- **职责**: 发送异常通知，记录代理使用情况
- **输入**: 异常信息，代理使用记录
- **输出**: 通知日志，微信通知（如有必要）
- **技能**: 消息格式化，通知发送，日志记录

### 6. 晨报数据准备节点 (morning_data_preparation)
- **职责**: 从规整数据生成晨报可用格式
- **输入**: 规整后的数据
- **输出**: 晨报数据JSON文件
- **技能**: 数据格式化，文件输出，质量控制

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

## 状态机实现要求

### 1. 数据提取节点 (data_extraction)

```python
def data_extraction_node(state: AppState) -> AppState:
    """
    数据提取节点 - 从各个数据源获取原始数据
    
    Args:
        state: 当前状态，包含symbol列表和配置
        
    Returns:
        更新后的状态，包含原始数据
    """
    raw_data = {}
    
    for symbol in state.symbols:
        raw_data[symbol] = {}
        
        # 获取美股数据
        if symbol.data_type == 'us_stock':
            sources = ['sina', 'yahoo']
            for source in sources:
                try:
                    data = fetch_us_stock(source, symbol.code)
                    raw_data[symbol]['us_stock'][source] = data
                except Exception as e:
                    raw_data[symbol]['us_stock'][source] = {'error': str(e)}
                    
        # 获取A股数据
        elif symbol.data_type == 'a_stock':
            sources = ['tencent', 'sina', 'eastmoney']
            for source in sources:
                try:
                    data = fetch_a_stock(source, symbol.code)
                    raw_data[symbol]['a_stock'][source] = data
                except Exception as e:
                    raw_data[symbol]['a_stock'][source] = {'error': str(e)}
                    
        # 获取期货数据
        elif symbol.data_type == 'futures':
            sources = ['sina', 'yfinance']
            for source in sources:
                try:
                    data = fetch_futures(source, symbol.code)
                    raw_data[symbol]['futures'][source] = data
                except Exception as e:
                    raw_data[symbol]['futures'][source] = {'error': str(e)}
                    
        # 获取加密货币数据
        elif symbol.data_type == 'crypto':
            sources = ['binance', 'coinbase']
            for source in sources:
                try:
                    data = fetch_crypto(source, symbol.code)
                    raw_data[symbol]['crypto'][source] = data
                except Exception as e:
                    raw_data[symbol]['crypto'][source] = {'error': str(e)}
    
    state.raw_data = raw_data
    return state
```

### 2. 数据验证节点 (data_validation)

```python
def data_validation_node(state: AppState) -> AppState:
    """
    数据验证节点 - 验证获取数据的完整性和有效性
    
    Args:
        state: 当前状态，包含原始数据
        
    Returns:
        更新后的状态，包含验证结果
    """
    validated_data = {}
    
    for symbol, data_sources in state.raw_data.items():
        validated_data[symbol] = {}
        
        for data_type, sources in data_sources.items():
            validated_data[symbol][data_type] = {}
            
            for source, data in sources.items():
                if 'error' in data:
                    validated_data[symbol][data_type][source] = {
                        'valid': False,
                        'reason': data['error']
                    }
                else:
                    # 验证数据完整性
                    is_valid, reason = validate_data_completeness(data)
                    validated_data[symbol][data_type][source] = {
                        'valid': is_valid,
                        'reason': reason,
                        'data': data
                    }
    
    state.validated_data = validated_data
    return state

def validate_data_completeness(data: Dict) -> Tuple[bool, str]:
    """
    验证数据完整性
    
    Returns:
        (是否有效, 原因)
    """
    required_fields = ['price', 'volume', 'change_pct']
    missing_fields = [f for f in required_fields if f not in data or data[f] is None]
    
    if missing_fields:
        return False, f"缺少字段: {', '.join(missing_fields)}"
    
    # 验证价格合理性
    if data.get('price', 0) <= 0:
        return False, "价格不合理"
    
    return True, "数据完整有效"
```

### 3. 数据规整节点 (data_consolidation)

```python
def data_consolidation_node(state: AppState) -> AppState:
    """
    数据规整节点 - 对验证后的数据进行去重、质量评分、选择最优数据
    
    Args:
        state: 当前状态，包含验证后的数据
        
    Returns:
        更新后的状态，包含规整后的数据
    """
    consolidated_data = {}
    
    for symbol, data_types in state.validated_data.items():
        consolidated_data[symbol] = {}
        
        for data_type, sources in data_types.items():
            # 收集有效数据
            valid_sources = {
                source: result['data'] 
                for source, result in sources.items() 
                if result.get('valid')
            }
            
            if not valid_sources:
                consolidated_data[symbol][data_type] = None
                continue
            
            # 计算每个数据源的质量评分
            scores = {}
            for source, data in valid_sources.items():
                scores[source] = calculate_quality_score(data, source)
            
            # 选择质量最高的数据源
            best_source = max(scores, key=scores.get)
            best_data = valid_sources[best_source]
            best_score = scores[best_source]
            
            consolidated_data[symbol][data_type] = {
                'data': best_data,
                'source': best_source,
                'score': best_score
            }
    
    state.consolidated_data = consolidated_data
    return state

def calculate_quality_score(data: Dict, source: str) -> float:
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
    present_fields = sum(1 for f in required_fields if f in data and data[f] is not None)
    score += (present_fields / len(required_fields)) * 0.4
    
    # 2. 数据源可靠性 (0-0.3)
    source_reliability = get_source_reliability(source)
    score += source_reliability * 0.3
    
    # 3. 数据新鲜度 (0-0.2)
    hours_since_update = (datetime.now() - data.get('timestamp', datetime.now())).total_seconds() / 3600
    if hours_since_update <= 1:
        score += 0.2
    elif hours_since_update <= 6:
        score += 0.15
    elif hours_since_update <= 24:
        score += 0.1
    else:
        score += 0.05
        
    # 4. 数据一致性 (0-0.1)
    if data.get('data_type') in ['us_stock', 'a_stock']:
        # 与其他数据源的价格差异
        consistency = check_price_consistency(data['symbol'], data['price'])
        score += consistency * 0.1
        
    return score
```

### 4. 健康监控节点 (health_monitoring)

```python
def health_monitoring_node(state: AppState) -> AppState:
    """
    健康监控节点 - 更新数据源健康状态，记录使用情况
    
    Args:
        state: 当前状态，包含规整后的数据
        
    Returns:
        更新后的状态，包含健康监控结果
    """
    health_updates = []
    
    for symbol, data_types in state.consolidated_data.items():
        for data_type, result in data_types.items():
            if result:
                # 更新数据源健康状态
                source = result['source']
                score = result['score']
                
                health_updates.append({
                    'source': source,
                    'symbol': symbol,
                    'data_type': data_type,
                    'score': score,
                    'adopted': True
                })
            else:
                # 记录失败的数据源
                for source in get_sources_for_type(data_type):
                    health_updates.append({
                        'source': source,
                        'symbol': symbol,
                        'data_type': data_type,
                        'score': 0,
                        'adopted': False
                    })
    
    state.health_updates = health_updates
    return state
```

### 5. 通知发送节点 (notification_sending)

```python
def notification_sending_node(state: AppState) -> AppState:
    """
    通知发送节点 - 发送异常通知，记录代理使用情况
    
    Args:
        state: 当前状态，包含健康监控结果
        
    Returns:
        更新后的状态，包含通知发送结果
    """
    notifications = []
    
    for update in state.health_updates:
        if not update['adopted']:
            # 发送失败通知
            notification = {
                'level': 'error',
                'message': f"数据获取失败: {update['symbol']} ({update['source']})",
                'source': update['source'],
                'data_type': update['data_type']
            }
            notifications.append(notification)
            
            # 如果需要，发送微信通知
            if should_send_wechat_notification(notification):
                send_wechat_notification(notification)
    
    state.notifications = notifications
    return state
```

### 6. 晨报数据准备节点 (morning_data_preparation)

```python
def morning_data_preparation_node(state: AppState) -> AppState:
    """
    晨报数据准备节点 - 从规整数据生成晨报可用格式
    
    Args:
        state: 当前状态，包含规整后的数据
        
    Returns:
        更新后的状态，包含晨报数据
    """
    morning_data = {
        'us_stock': [],
        'a_stock': [],
        'futures': [],
        'crypto': []
    }
    
    for symbol, data_types in state.consolidated_data.items():
        for data_type, result in data_types.items():
            if result:
                morning_data[data_type].append({
                    'symbol': symbol,
                    'data': result['data'],
                    'source': result['source'],
                    'score': result['score']
                })
    
    # 保存到文件
    output_dir = os.path.join(os.path.dirname(__file__), 'projects')
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(output_dir, f'morning_data_{datetime.now().strftime("%Y%m%d_%H%M")}.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(morning_data, f, ensure_ascii=False, indent=2, default=str)
    
    state.morning_data_file = output_file
    return state
```

## 状态机定义

```python
from langgraph.graph import StateGraph, START, END

# 定义状态类型
class AppState(TypedDict):
    symbols: List[Dict]              # 要获取的股票列表
    raw_data: Dict                   # 原始数据
    validated_data: Dict             # 验证后的数据
    consolidated_data: Dict          # 规整后的数据
    health_updates: List[Dict]       # 健康监控结果
    notifications: List[Dict]        # 通知列表
    morning_data_file: str           # 晨报数据文件路径

# 构建状态机
workflow = StateGraph(AppState)

# 添加节点
workflow.add_node("data_extraction", data_extraction_node)
workflow.add_node("data_validation", data_validation_node)
workflow.add_node("data_consolidation", data_consolidation_node)
workflow.add_node("health_monitoring", health_monitoring_node)
workflow.add_node("notification_sending", notification_sending_node)
workflow.add_node("morning_data_preparation", morning_data_preparation_node)

# 添加边
workflow.add_edge(START, "data_extraction")
workflow.add_edge("data_extraction", "data_validation")
workflow.add_edge("data_validation", "data_consolidation")
workflow.add_edge("data_consolidation", "health_monitoring")
workflow.add_edge("health_monitoring", "notification_sending")
workflow.add_edge("notification_sending", "morning_data_preparation")
workflow.add_edge("morning_data_preparation", END)

# 编译状态机
app = workflow.compile()
```

## 输出要求

1. **完整的Python代码** - 包含所有状态节点实现
2. **数据库初始化脚本** - 创建所有表和索引
3. **配置文件** - data_source_config.ini
4. **状态机定义** - LangGraph状态机代码
5. **测试用例** - 验证状态机工作正常

## 注意事项

1. **不要硬编码敏感信息** - API Key从.env读取
2. **错误处理** - 每个节点都要有try-except
3. **日志记录** - 记录每个节点的执行状态
4. **代理使用** - 记录是否使用了代理
5. **数据完整性** - 确保必填字段都有值
6. **性能优化** - 避免重复获取相同数据

## 完成标准

1. ✅ 数据库表创建成功
2. ✅ 所有状态节点实现完成
3. ✅ 状态机可以正常运行
4. ✅ 代理Fallback逻辑工作正常
5. ✅ 数据规整逻辑正确
6. ✅ 晨报数据准备完成
7. ✅ 所有测试通过

## LangGraph特定要求

1. **使用LangGraph框架** - 按照LangGraph的最佳实践实现
2. **状态机设计清晰** - 每个节点职责单一
3. **状态传递正确** - 节点间状态传递符合TypedDict定义
4. **错误处理完善** - 节点失败时有适当的错误处理
5. **可扩展性好** - 方便后续添加新的数据源或数据类型
