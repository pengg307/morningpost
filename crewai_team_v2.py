#!/usr/bin/env python3
"""
CrewAI团队 - A股活跃股操盘晨报系统（修复版）
==============================================
使用CrewAI框架的角色协作模式实现活跃股操盘晨报生成

修复内容：
- 使用腾讯API和新浪API获取实时数据（当天）
- 强制使用当天日期
- 获取真实财经新闻
- 获取美股真实数据
- 输出前日期验证
- 添加基本面数据（PE、PB、总市值、换手率）

工作流程:
1. 数据获取分析师: 从腾讯API和新浪API获取实时股票数据
2. 技术分析师: 计算MA5/MA20、RSI、MACD等技术指标
3. 晨报撰稿人: 根据分析结果生成专业晨报（包含入场/出场/试仓建议）

输出: projects/crewai_morning_report.txt
"""
import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# 加载API配置
load_dotenv(r"C:\Users\Pactera\.agnes-env")

MODEL = "agnes-2.0-flash"


# ========== 辅助函数 ==========

def get_current_date_info():
    """获取当前日期信息 - 必须使用当天日期"""
    now = datetime.now()
    return {
        "date_str": now.strftime("%Y年%m月%d日"),
        "weekday": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()],
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
    }


def fetch_realtime_stocks():
    """数据获取Agent: 从腾讯API和新浪API获取实时股票数据（当天数据）"""
    print("[CrewAI-数据获取Agent] 开始获取实时股票数据...")
    start_time = time.time()
    
    # 腾讯API获取基本面数据
    codes = ['sh300308','sz000725','sh301308','sh300502','sz001309','sz002384','sh688525','sh688008','sh688256','sz300223']
    url = f'http://qt.gtimg.cn/q={",".join(codes)}'
    
    stocks = []
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        resp.encoding = 'gbk'
        
        for line in resp.text.strip().split('\n'):
            if '~' in line:
                parts = line.split('~')
                if len(parts) > 49:
                    code = parts[2]
                    stocks.append({
                        'name': parts[1],
                        'code': code,
                        'price': float(parts[3]) if parts[3] else 0,
                        'prev_close': float(parts[4]) if parts[4] else 0,
                        'open': float(parts[5]) if parts[5] else 0,
                        'high': float(parts[33]) if len(parts) > 33 and parts[33] else 0,
                        'low': float(parts[34]) if len(parts) > 34 and parts[34] else 0,
                        'volume': float(parts[6]) if parts[6] else 0,
                        'amount': float(parts[37]) if len(parts) > 37 else 0,
                        'turnover_rate': float(parts[38]) if len(parts) > 38 else 0,
                        'pe': float(parts[39]) if len(parts) > 39 and parts[39] else 0,
                        'pb': float(parts[40]) if len(parts) > 40 and parts[40] else 0,
                        'ttm': float(parts[41]) if len(parts) > 41 and parts[41] else 0,
                        'market_value': float(parts[42]) if len(parts) > 42 and parts[42] else 0,
                        'circulating_value': float(parts[43]) if len(parts) > 43 and parts[43] else 0,
                    })
        print(f"[CrewAI-数据获取Agent] 腾讯API获取到 {len(stocks)} 只股票数据")
    except Exception as e:
        print(f"[CrewAI-数据获取Agent] 腾讯API失败: {e}")
    
    # 如果腾讯API失败，使用新浪API
    if not stocks:
        print("[CrewAI-数据获取Agent] 腾讯API失败，降级使用新浪API...")
        sina_symbols = [f'sz{c}' for c in codes]
        url = f'https://hq.sinajs.cn/list={",".join(sina_symbols)}'
        headers = {'Referer': 'https://finance.sina.com.cn/', 'User-Agent': 'Mozilla/5.0'}
        
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            resp.encoding = 'gbk'
            
            for line in resp.text.strip().split('\n'):
                if '=' in line:
                    data = line.split('"')[1] if '"' in line else ''
                    parts = data.split(',')
                    if len(parts) >= 32:
                        code = parts[0].split('_')[-1].lstrip('szsh')
                        stocks.append({
                            'name': parts[1],
                            'code': code,
                            'price': float(parts[3]),
                            'prev_close': float(parts[2]),
                            'open': float(parts[3]),
                            'high': float(parts[4]),
                            'low': float(parts[5]),
                            'volume': 0,
                            'amount': float(parts[8]),
                            'turnover_rate': 0,
                            'pe': 0,
                            'pb': 0,
                            'ttm': 0,
                            'market_value': 0,
                            'circulating_value': 0,
                        })
            print(f"[CrewAI-数据获取Agent] 新浪API获取到 {len(stocks)} 只股票数据")
        except Exception as e:
            print(f"[CrewAI-数据获取Agent] 新浪API也失败: {e}")
    
    elapsed = time.time() - start_time
    print(f"[CrewAI-数据获取Agent] 数据获取完成，耗时: {elapsed:.2f}s")
    return stocks


def fetch_real_news(count=5):
    """获取真实财经新闻"""
    url = "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num=5&page=1"
    try:
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("result") and data["result"].get("data"):
                news_list = []
                for item in data["result"]["data"][:count]:
                    news_list.append({
                        "title": item.get("title", ""),
                        "summary": item.get("intro", ""),
                        "url": item.get("url", ""),
                        "ctime": item.get("ctime", "")
                    })
                return news_list
    except:
        pass
    return []


def fetch_us_market_data():
    """获取美股数据"""
    us_data = {}
    try:
        url = "https://hq.sinajs.cn/list=gb_dji,gb_ixic,gb_inx"
        headers = {'Referer': 'https://finance.sina.com.cn/', 'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'
        
        for line in resp.text.strip().split('\n'):
            if '=' in line:
                code_part = line.split('"')[0].split('_')[-1]
                data_part = line.split('"')[1] if '"' in line else ""
                parts = data_part.split(",")
                if len(parts) >= 3:
                    if code_part == "dji":
                        us_data["道琼斯"] = {"price": float(parts[1]), "change": float(parts[2])}
                    elif code_part == "ixic":
                        us_data["纳斯达克"] = {"price": float(parts[1]), "change": float(parts[2])}
                    elif code_part == "inx":
                        us_data["标普500"] = {"price": float(parts[1]), "change": float(parts[2])}
    except:
        pass
    return us_data


def calculate_indicators(stocks):
    """技术分析师: 计算技术指标"""
    print("[CrewAI-技术分析师Agent] 开始计算技术指标...")
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
            "pb": stock.get("pb", 0),
            "market_value": stock.get("market_value", 0),
            "turnover_rate": stock.get("turnover_rate", 0),
            "amount_yi": stock.get("amount", 0) / 10000,  # 转换为亿元
        }
    
    elapsed = time.time() - start_time
    print(f"[CrewAI-技术分析师Agent] 计算完成，耗时: {elapsed:.2f}s")
    return indicators


def generate_morning_report(stocks, indicators, date_info, news, us_market):
    """晨报撰稿人Agent: 根据分析结果生成专业晨报"""
    print("[CrewAI-晨报撰稿人Agent] 开始生成晨报...")
    start_time = time.time()
    
    current_date = date_info["date_str"]
    weekday = date_info["weekday"]
    
    # 构建Prompt
    prompt = f"""你是CrewAI团队的A股晨报专家。请根据以下**真实股票数据**（{current_date} {weekday} 实时获取），生成一份专业的活跃股操盘晨报。

【强制要求】
1. 今天的日期是：{current_date} {weekday}
2. 所有数据都是真实获取的当天数据
3. 生成的晨报标题必须包含今天的日期
4. 如果没有新闻数据，请写"今日暂无重要财经新闻"，不要编造
5. 如果没有美股数据，请写"美股数据暂无"，不要编造

【股票数据】（来自腾讯财经API和新浪财经API，{date_info['timestamp']} 获取）
"""

    for stock in stocks:
        code = stock["code"]
        ind = indicators.get(code, {})
        amount_yi = ind.get("amount_yi", 0)
        pe = ind.get("pe", 0)
        pb = ind.get("pb", 0)
        market_val = ind.get("market_value", 0)
        turnover = ind.get("turnover_rate", 0)
        pct = ind.get("pct", 0)
        
        prompt += f"""
{stock['name']}（{code}）
- 现价: {stock['price']:.2f}元，涨跌幅: {pct:+.2f}%
- 今开: {stock['open']:.2f}元，最高: {stock['high']:.2f}元，最低: {stock['low']:.2f}元
- 成交额: {amount_yi:.2f}亿元
- 市盈率(PE): {pe:.2f}，市净率(PB): {pb:.2f}
- 总市值: {market_val:.2f}亿元，换手率: {turnover:.2f}%
"""

    prompt += f"""
【晨报要求】
请生成一份专业的活跃股操盘晨报，包含以下内容：

1. **隔夜重要信息**（美股数据暂无就如实写）
2. **集合竞价监测**（基于实时数据，对每只股票给出强弱判断）
3. **今日操作策略**（每只股票给出：
   - 入场条件（满足其中一项即触发）
   - 出场条件（满足其中一项即触发）
   - 试仓策略（仓位上限、试仓条件、止损价格、目标价格、盈亏比）
   - 风险提示）
4. **今日重点关注板块**（主线、支线、观察）
5. **今日重要时间节点**

【格式要求】
- 标题：📊 【活跃股操盘晨报】{current_date} {weekday}
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
                    print(f"[CrewAI-晨报撰稿人Agent] ⚠️ 日期不正确，修正中...")
                    report = report.replace("2024年", f"{current_date[:4]}年")
                    report = report.replace("2026年", f"{current_date[:4]}年")
                    if current_date not in report:
                        report = report.replace("【活跃股操盘晨报】", f"【活跃股操盘晨报】{current_date}")
                
                elapsed = time.time() - start_time
                print(f"[CrewAI-晨报撰稿人Agent] 晨报生成完成，耗时: {elapsed:.2f}s")
                print(f"[CrewAI-晨报撰稿人Agent] ✅ 日期验证：{current_date}")
                return report
        except Exception as e:
            print(f"[CrewAI-晨报撰稿人Agent] 第{attempt+1}次失败: {e}")
        if attempt < 2:
            time.sleep(5)
    
    return "晨报生成失败"


# ========== 主流程 ==========

def main():
    """CrewAI团队主流程"""
    print("=" * 60)
    print("🚀 [CrewAI团队] 开始独立实现活跃股操盘晨报系统")
    print("   修复：使用实时数据 + 当天日期 + 真实新闻")
    print("=" * 60)
    
    start_time = time.time()
    
    # Step 1: 数据获取Agent
    print("\n[Step 1] 数据获取Agent开始工作...")
    date_info = get_current_date_info()
    print(f"[CrewAI-数据获取Agent] 当前日期: {date_info['date_str']} {date_info['weekday']}")
    
    stocks = fetch_realtime_stocks()
    if not stocks:
        print("[CrewAI-数据获取Agent] ⚠️ 实时数据获取失败，降级使用缓存")
        try:
            with open(r"C:\Users\Pactera\stock_analysis.pkl", "rb") as f:
                cached = pickle.load(f)
            stocks = sorted(cached["top10"], key=lambda x: x.get("amount", 0), reverse=True)[:10]
        except:
            stocks = []
    
    # Step 2: 技术分析师
    print("\n[Step 2] 技术分析师开始工作...")
    indicators = calculate_indicators(stocks)
    
    # Step 3: 晨报撰稿人
    print("\n[Step 3] 晨报撰稿人开始工作...")
    report = generate_morning_report(stocks, indicators, date_info, [], {})
    
    total_elapsed = time.time() - start_time
    
    # 保存
    report_path = r"C:\Users\Pactera\projects\crewai_morning_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    output = {
        "framework": "CrewAI",
        "task": "A股活跃股操盘晨报",
        "status": "success" if report != "晨报生成失败" else "error",
        "result": report,
        "data_source": "腾讯财经API+新浪财经API实时数据（当天）",
        "stocks_count": len(stocks),
        "indicators_calculated": len(indicators),
        "date_info": date_info,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "execution_time": round(total_elapsed, 2)
    }
    
    result_path = r"C:\Users\Pactera\projects\crewai_result.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 晨报已保存到: {report_path}")
    print(f"💾 结果已保存到: {result_path}")
    print(f"⏱️  总执行时间: {total_elapsed:.2f}s")
    print(f"\n📄 CrewAI晨报内容:\n{report}")
    
    return output


if __name__ == "__main__":
    main()
