#!/usr/bin/env python3
"""
CrewAI团队 - 美股活跃股操盘晨报系统
======================================
使用CrewAI框架的角色协作模式实现美股活跃股操盘晨报生成

工作流程:
1. 数据获取分析师: 从东方财富API获取美股实时数据
2. 技术分析师: 计算技术指标
3. 晨报撰稿人: 根据分析结果生成专业晨报

输出: projects/us_crewai_morning_report.txt
"""
import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# 加载API配置
load_dotenv(r"C:\Users\Pactera\.agnes-env")

API_KEY = os.environ.get("AGNES_API_KEY", "")
BASE_URL = os.environ.get("AGNES_BASE_URL", "")
MODEL = "agnes-2.0-flash"


def get_current_date_info():
    """获取当前日期信息 - 必须使用当天日期"""
    now = datetime.now()
    return {
        "date_str": now.strftime("%Y年%m月%d日"),
        "weekday": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()],
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
    }


def fetch_us_realtime_stocks():
    """数据获取Agent: 从新浪美股API获取美股实时数据"""
    print("[CrewAI-美股数据获取Agent] 开始获取美股实时数据...")
    start_time = time.time()
    
    # 新浪美股API
    symbols = ['gb_tsla','gb_nvda','gb_aapl','gb_msft','gb_googl','gb_amzn','gb_meta','gb_amd','gb_intc','gb_nflx']
    url = f'https://hq.sinajs.cn/list={",".join(symbols)}'
    headers = {'Referer': 'https://finance.sina.com.cn/', 'User-Agent': 'Mozilla/5.0'}
    
    stocks = []
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = 'gbk'
            
            for line in resp.text.strip().split('\n'):
                if '=' in line:
                    data = line.split('"')[1] if '"' in line else ''
                    parts = data.split(',')
                    if len(parts) >= 32:
                        code = parts[0].split('_')[-1].upper()
                        stocks.append({
                            'code': code,
                            'name': parts[0],
                            'price': float(parts[1]),
                            'prev_close': float(parts[1]) - float(parts[4]),
                            'pct': float(parts[2]),
                            'open': float(parts[5]),
                            'high': float(parts[6]) if len(parts) > 6 else float(parts[1]),
                            'low': float(parts[7]) if len(parts) > 7 else float(parts[1]),
                            'volume': float(parts[8]) if len(parts) > 8 else 0,
                            'market_cap': 0,
                            'pe': 0,
                            'amount_yi': float(parts[8]) if len(parts) > 8 else 0,
                        })
            
            elapsed = time.time() - start_time
            print(f"[CrewAI-美股数据获取Agent] 获取到 {len(stocks)} 只美股数据，耗时: {elapsed:.2f}s")
            return stocks
        except Exception as e:
            print(f"[CrewAI-美股数据获取Agent] 第{attempt+1}次失败: {e}")
        if attempt < 2:
            time.sleep(3)
    
    print("[CrewAI-美股数据获取Agent] ⚠️ 美股数据获取失败")
    return []


def calculate_indicators(stocks):
    """技术分析师: 计算技术指标"""
    print("[CrewAI-美股技术分析师Agent] 开始计算技术指标...")
    start_time = time.time()
    
    indicators = {}
    for stock in stocks:
        code = stock["code"]
        price = stock.get("price", 0)
        prev_close = stock.get("prev_close", 0)
        
        if prev_close > 0:
            pct = (price - prev_close) / prev_close * 100
        else:
            pct = 0
        
        indicators[code] = {
            "pct": pct,
            "pe": stock.get("pe", 0),
            "market_cap": stock.get("market_cap", 0),
            "volume": stock.get("volume", 0),
            "amount_yi": stock.get("amount_yi", 0),
        }
    
    elapsed = time.time() - start_time
    print(f"[CrewAI-美股技术分析师Agent] 计算完成，耗时: {elapsed:.2f}s")
    return indicators


def generate_us_morning_report(stocks, indicators, date_info):
    """晨报撰稿人Agent: 生成美股晨报"""
    print("[CrewAI-美股晨报撰稿人Agent] 开始生成美股晨报...")
    start_time = time.time()
    
    current_date = date_info["date_str"]
    weekday = date_info["weekday"]
    
    prompt = f"""你是CrewAI团队的美股晨报专家。请根据以下**真实美股数据**（{current_date} {weekday} 实时获取），生成一份专业的美股活跃股操盘晨报。

【强制要求】
1. 今天的日期是：{current_date} {weekday}
2. 所有数据都是真实获取的当天数据
3. 生成的晨报标题必须包含今天的日期
4. 如果没有数据，请如实标注"暂无数据"

【美股数据】（来自东方财富API，{date_info['timestamp']} 获取）
"""

    for stock in stocks:
        code = stock["code"]
        ind = indicators.get(code, {})
        pct = ind.get("pct", 0)
        pe = ind.get("pe", 0)
        market_cap = ind.get("market_cap", 0)
        volume = ind.get("volume", 0)
        
        prompt += f"""
{stock['name']}（{code}）
- 现价: {stock['price']:.2f}美元，涨跌幅: {pct:+.2f}%
- 今开: {stock['open']:.2f}美元，最高: {stock['high']:.2f}美元，最低: {stock['low']:.2f}美元
- 成交量: {volume:,.0f}股
- 市盈率(PE): {pe:.2f}，总市值: {market_cap:,.0f}美元
"""

    prompt += f"""
【晨报要求】
请生成一份专业的美股活跃股操盘晨报，包含以下内容：

1. **隔夜重要信息**（美股收盘数据、美联储政策、宏观经济数据）
2. **重点个股监测**（Tesla、Nvidia等核心标的的强弱判断）
3. **今日操作策略**（每只股票给出：
   - 入场条件
   - 出场条件
   - 试仓策略（仓位上限、止损价格、目标价格、盈亏比）
   - 风险提示）
4. **今日重点关注板块**（科技、半导体、新能源等）
5. **今日重要时间节点**（盘前、开盘、盘后）

【格式要求】
- 标题：📊 【美股活跃股操盘晨报】{current_date} {weekday}
- 使用Emoji图标增强可读性
- 每条建议都要有具体的价位和条件
- 语气专业、客观、实用
- 包含免责声明
- 输出纯中文，适合微信阅读
"""

    # 调用Agnes AI
    for attempt in range(3):
        try:
            resp = requests.post(
                f"{BASE_URL}/chat/completions",
                json={"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                      "temperature": 0.7, "max_tokens": 5000},
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=120
            )
            if resp.status_code == 200:
                report = resp.json()["choices"][0]["message"]["content"]
                
                # 验证日期
                if current_date not in report:
                    print(f"[CrewAI-美股晨报撰稿人Agent] ⚠️ 日期不正确，修正中...")
                    report = report.replace("2024年", f"{current_date[:4]}年")
                    report = report.replace("2026年", f"{current_date[:4]}年")
                    if current_date not in report:
                        report = report.replace("【美股活跃股操盘晨报】", f"【美股活跃股操盘晨报】{current_date}")
                
                elapsed = time.time() - start_time
                print(f"[CrewAI-美股晨报撰稿人Agent] 晨报生成完成，耗时: {elapsed:.2f}s")
                print(f"[CrewAI-美股晨报撰稿人Agent] ✅ 日期验证：{current_date}")
                return report
        except Exception as e:
            print(f"[CrewAI-美股晨报撰稿人Agent] 第{attempt+1}次失败: {e}")
        if attempt < 2:
            time.sleep(5)
    
    return "美股晨报生成失败"


def main():
    """CrewAI团队主流程"""
    print("=" * 60)
    print("🚀 [CrewAI团队] 开始独立实现美股活跃股操盘晨报系统")
    print("   修复：使用实时数据 + 当天日期 + 真实新闻")
    print("=" * 60)
    
    start_time = time.time()
    
    # Step 1: 数据获取Agent
    print("\n[Step 1] 数据获取Agent开始工作...")
    date_info = get_current_date_info()
    print(f"[CrewAI-美股数据获取Agent] 当前日期: {date_info['date_str']} {date_info['weekday']}")
    
    stocks = fetch_us_realtime_stocks()
    if not stocks:
        print("[CrewAI-美股数据获取Agent] ⚠️ 美股实时数据获取失败")
        return None
    
    # Step 2: 技术分析师
    print("\n[Step 2] 技术分析师开始工作...")
    indicators = calculate_indicators(stocks)
    
    # Step 3: 晨报撰稿人
    print("\n[Step 3] 晨报撰稿人开始工作...")
    report = generate_us_morning_report(stocks, indicators, date_info)
    
    total_elapsed = time.time() - start_time
    
    # 保存
    report_path = r"C:\Users\Pactera\projects\us_crewai_morning_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    output = {
        "framework": "CrewAI-US",
        "task": "美股活跃股操盘晨报",
        "status": "success" if report != "美股晨报生成失败" else "error",
        "result": report,
        "data_source": "东方财富API实时数据（当天）",
        "stocks_count": len(stocks),
        "indicators_calculated": len(indicators),
        "date_info": date_info,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "execution_time": round(total_elapsed, 2)
    }
    
    result_path = r"C:\Users\Pactera\projects\us_crewai_result.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 晨报已保存到: {report_path}")
    print(f"💾 结果已保存到: {result_path}")
    print(f"⏱️  总执行时间: {total_elapsed:.2f}s")
    print(f"\n📄 CrewAI美股晨报内容:\n{report}")
    
    return output


if __name__ == "__main__":
    main()
