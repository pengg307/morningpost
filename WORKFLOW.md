# 晨报系统Workflow文档

## 📋 系统架构

**双框架并行开发**：CrewAI版 + LangGraph版，独立实现相同功能

**数据源**：SQLite数据库 → API降级（腾讯/新浪）

**输出**：微信推送（每日08:00晨报 + 15:30晚报）

---

## 🔄 工作流程（7步）

### Step 1: 数据获取
```python
from morning_data_source import MorningDataSource
source = MorningDataSource()
data = source.get_all_data()
```

**获取内容**：
- A股股票（55只活跃股）
- 美股（12只重点股）
- 期货（8只美期）
- ETF期权（8只基础版）
- 加密货币（需代理）
- 财经新闻

### Step 2: 技术分析
```python
indicators = calculate_indicators(stocks)
```

**计算指标**：
- 涨跌幅、PE、PB
- 总市值、换手率
- 成交额（亿元）

### Step 2.5: 期货数据处理
```python
futures_result = {
    "status": "success",
    "futures": futures_list,
    "sectors": {}
}
```

### Step 2.6: 虚拟币数据
```python
crypto_data = fetch_crypto_data()
```
*注：当前环境不可用（需要代理）*

### Step 2.7: 财经新闻
```python
news_data = fetch_financial_news()
```

### Step 2.8: ETF期权数据
```python
etf_options = source.get_all_data().get('etf_options', [])
```

### Step 3: 信号检测
```python
signals = signal_detection(stocks, indicators)
```

**信号类型**：
- 强买（涨幅>5%且换手率>3%）
- 买入（涨幅>2%）
- 持有（-2% < 涨幅 < 2%）
- 减持（-5% < 涨幅 < -2%）
- 卖出（跌幅>5%）

### Step 4: 报告生成
```python
report = generate_report(...)  # CrewAI版
# 或
report = build_template_report(...)  # LangGraph版
```

---

## 📊 晨报内容结构

### 1. 三句话看懂今日市场
- 外围市场一句话
- A股市场一句话
- 策略一句话

### 2. ETF期权市场概览（基础版）
- 8只ETF行情
- 按涨跌幅排序
- 标注成交量和成交额

### 3. 期货板块趋势概览
- 能源板块（CL/NG）
- 贵金属板块（GC/SI/HG）
- 股指板块（ES/NQ/YM）

### 4. 今日信号分布
- 强买/买入/持有/减持/卖出统计

### 5. A股重点标的（前15只）
- 基本面数据
- 盘面特征描述
- 风险等级标签
- 入场/出场/试仓建议

### 6. 美股重点标的
- AAPL、AMD、AMZN等10只
- 信号标注

### 7. 今日重点关注板块
- A股强势板块（科创板/沪市/创业板）
- 美股焦点

### 8. 今日重要时间节点
- A股交易时间
- 美股交易时间
- 宏观日历

---

## 🔧 双框架差异

| 特性 | CrewAI版 | LangGraph版 |
|------|----------|-------------|
| **架构** | 角色协作 | 状态机驱动 |
| **特点** | 专家团队多视角 | 严谨流程控制 |
| **速度** | 较慢（LLM模式） | 较快 |
| **模板模式** | USE_LLM=False | USE_LLM=False |

---

## 📁 文件结构

```
morningpost/
├── morning_data_source.py      # 统一数据源
├── crewai_team_v2.py           # CrewAI版晨报
├── langgraph_team_v2.py        # LangGraph版晨报
├── data_acquisition_manager.py # 数据获取管理器
└── market_cache.py             # 缓存管理
```

---

## 🚀 运行方式

### 模板模式（零Token）
```bash
USE_LLM=False python crewai_team_v2.py
USE_LLM=False python langgraph_team_v2.py
```

### LLM模式（完整分析）
```bash
python crewai_team_v2.py
python langgraph_team_v2.py
```

---

## ⏰ Cronjob配置

```yaml
schedule: '0 8 * * *'  # 每天08:00
name: 晨报推送
skills: [market-data-acquisition]
prompt: 运行晨报系统并推送到微信
```

---

## 📈 后续优化方向

### v2.1 - 期权合约数据
- [ ] 接入东方财富期权API
- [ ] 获取IV隐含波动率
- [ ] 获取认购/认沽期权链
- [ ] 持仓量分析

### v2.2 - 资金流向
- [ ] 北向资金数据
- [ ] 南向资金数据
- [ ] 两融余额
- [ ] ETF净流入

### v2.3 - 增强功能
- [ ] 板块轮动分析
- [ ] 技术指标完善（MACD/RSI/BOLL）
- [ ] 新闻情感分析
- [ ] 风险预警系统

---

## ⚠️ 注意事项

1. **Git安全红线**：绝对禁止提交API密钥
2. **代理限制**：虚拟币数据需要代理
3. **ETF期权**：当前为基础版（ETF本身行情），非期权合约
4. **日期验证**：生成报告后必须验证日期正确性
5. **免责声明**：报告必须包含免责声明

---

## 📞 技术支持

- 问题反馈：联系开发团队
- 数据异常：检查API连接和代理设置
- 性能优化：调整缓存策略和请求频率
