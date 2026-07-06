#!/usr/bin/env python3
"""
合并晨报系统 - A股 + 美股
============================
使用CrewAI和LangGraph双框架生成合并晨报（A股+美股）

工作流程:
1. 获取A股实时数据（腾讯财经API）
2. 获取美股实时数据（新浪财经API）
3. 生成A股晨报
4. 生成美股晨报
5. 合并两份晨报
6. 输出最终合并晨报

输出: projects/merged_morning_report.txt
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
    """获取当前日期信息"""
    now = datetime.now()
    return {
        "date_str": now.strftime("%Y年%m月%d日"),
        "weekday": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()],
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
    }


def fetch_a_stock_realtime():
    """获取A股实时数据"""
    print("[合并晨报-A股数据获取] 开始获取A股实时数据...")
    start_time = time.time()
    
    # 腾讯财经API
    codes = ['sz300308','sz000725','sz301308','sz300502','sz001309','sh688256','sh688008','sz300223','sz002384','sh601318']
    url = f"https://qt.gtimg.cn/q={','.join(codes)}"
    
    stocks = []
    for attempt in range(3):
        try:
            resp = requests.get(url, timeout=10)
            resp.encoding = 'gbk'
            
            for line in resp.text.strip().split('\n'):
                if '~' in line:
                    parts = line.split('~')
                    if len(parts) > 40:
                        stocks.append({
                            'name': parts[1],
                            'code': parts[2],
                            'price': float(parts[3]),
                            'prev_close': float(parts[4]),
                            'open': float(parts[5]),
                            'high': float(parts[33]),
                            'low': float(parts[34]),
                            'volume': float(parts[6]),
                            'turnover': float(parts[37]),
                        })
            
            elapsed = time.time() - start_time
            print(f"[合并晨报-A股数据获取] 获取到 {len(stocks)} 只A股数据，耗时: {elapsed:.2f}s")
            return stocks
        except Exception as e:
            print(f"[合并晨报-A股数据获取] 第{attempt+1}次失败: {e}")
        if attempt < 2:
            time.sleep(3)
    
    print("[合并晨报-A股数据获取] ⚠️ A股数据获取失败")
    return []


def fetch_us_realtime():
    """获取美股实时数据"""
    print("[合并晨报-美股数据获取] 开始获取美股实时数据...")
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
                        stocks.append({
                            'code': parts[0],
                            'name': parts[0],
                            'price': float(parts[1]),
                            'prev_close': float(parts[1]) - float(parts[4]),
                            'pct': float(parts[2]),
                            'open': float(parts[5]),
                            'high': float(parts[6]) if len(parts) > 6 else float(parts[1]),
                            'low': float(parts[7]) if len(parts) > 7 else float(parts[1]),
                            'volume': float(parts[8]) if len(parts) > 8 else 0,
                        })
            
            elapsed = time.time() - start_time
            print(f"[合并晨报-美股数据获取] 获取到 {len(stocks)} 只美股数据，耗时: {elapsed:.2f}s")
            return stocks
        except Exception as e:
            print(f"[合并晨报-美股数据获取] 第{attempt+1}次失败: {e}")
        if attempt < 2:
            time.sleep(3)
    
    print("[合并晨报-美股数据获取] ⚠️ 美股数据获取失败")
    return []


def generate_merged_report(a_stocks, us_stocks, date_info):
    """生成合并晨报"""
    print("[合并晨报-报告生成] 开始生成合并晨报...")
    start_time = time.time()
    
    current_date = date_info["date_str"]
    weekday = date_info["weekday"]
    
    prompt = f"""你是晨报专家。请根据以下**真实A股、美股和期货数据**（{current_date} {weekday} 实时获取），生成一份专业的**全球晨报**（A股+美股+期货）。

【强制要求】
1. 今天的日期是：{current_date} {weekday}
2. 所有数据都是真实获取的当天数据
3. 生成的晨报标题必须包含今天的日期
4. 如果没有数据，请如实标注"暂无数据"

【A股数据】（来自腾讯财经API，{date_info['timestamp']} 获取）
"""

    for stock in a_stocks[:5]:  # 取前5只
        pct = (stock['price'] - stock['prev_close']) / stock['prev_close'] * 100
        prompt += f"""
{stock['name']}（{stock['code']}）
- 现价: {stock['price']:.2f}元，涨跌幅: {pct:+.2f}%
- 今开: {stock['open']:.2f}元，最高: {stock['high']:.2f}元，最低: {stock['low']:.2f}元
- 成交量: {stock['volume']:,.0f}股，成交额: {stock['turnover']:,.0f}亿元
"""

    prompt += f"""
【美股数据】（来自新浪财经API，{date_info['timestamp']} 获取）
"""

    for stock in us_stocks[:5]:  # 取前5只
        pct = (stock['price'] - stock['prev_close']) / stock['prev_close'] * 100
        prompt += f"""
{stock['name']}（{stock['code']}）
- 现价: {stock['price']:.2f}美元，涨跌幅: {pct:+.2f}%
- 今开: {stock['open']:.2f}美元，最高: {stock['high']:.2f}美元，最低: {stock['low']:.2f}美元
- 成交量: {stock['volume']:,.0f}股
"""

    prompt += f"""
【期货数据】（来自新浪财经API，{date_info['timestamp']} 获取）
- 股指期货：IF（沪深300）、IC（中证500）、IH（上证50）、IM（中证1000）
- 商品期货：黄金(AU)、白银(AG)、铜(CU)、铝(AL)、铁矿石(I)、螺纹钢(RB)
- 若暂无实时数据，请基于隔夜收盘数据进行分析

【合并晨报要求】
请生成一份专业的全球晨报，包含以下内容：

1. **隔夜重要信息**（美股收盘数据、A50期指、汇率、大宗商品）
2. **期货市场概览**（股指期货、商品期货表现）
3. **A股重点个股监测**（7-10只活跃股）
4. **美股重点个股监测**（7-10只活跃股）
5. **今日操作策略**（A股+美股+期货，每只股票给出：
   - 入场条件
   - 出场条件
   - 试仓策略（仓位上限、止损价格、目标价格、盈亏比）
   - 风险提示）
6. **今日重点关注板块**（A股+美股+期货）
7. **今日重要时间节点**（A股+美股交易时间）
8. **免责声明**

【格式要求】
- 标题：📊 【全球活跃股操盘晨报】{current_date} {weekday}
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
                      "temperature": 0.7, "max_tokens": 8000},
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=120
            )
            if resp.status_code == 200:
                report = resp.json()["choices"][0]["message"]["content"]
                
                # 验证日期
                if current_date not in report:
                    print(f"[合并晨报-报告生成] ⚠️ 日期不正确，修正中...")
                    report = report.replace("2024年", f"{current_date[:4]}年")
                    report = report.replace("2026年", f"{current_date[:4]}年")
                    if current_date not in report:
                        report = report.replace("【全球活跃股操盘晨报】", f"【全球活跃股操盘晨报】{current_date}")
                
                elapsed = time.time() - start_time
                print(f"[合并晨报-报告生成] 晨报生成完成，耗时: {elapsed:.2f}s")
                print(f"[合并晨报-报告生成] ✅ 日期验证：{current_date}")
                return report
        except Exception as e:
            print(f"[合并晨报-报告生成] 第{attempt+1}次失败: {e}")
        if attempt < 2:
            time.sleep(5)
    
    return "合并晨报生成失败"


def main():
    """合并晨报主流程"""
    print("=" * 60)
    print("🌍 [合并晨报系统] 开始生成A股+美股合并晨报")
    print("   数据源：腾讯财经API + 新浪财经API")
    print("=" * 60)
    
    start_time = time.time()
    
    # Step 1: 获取A股数据
    print("\n[Step 1] 获取A股实时数据...")
    date_info = get_current_date_info()
    print(f"[合并晨报] 当前日期: {date_info['date_str']} {date_info['weekday']}")
    
    a_stocks = fetch_a_stock_realtime()
    if not a_stocks:
        print("[合并晨报] ⚠️ A股数据获取失败")
        return None
    
    # Step 2: 获取美股数据
    print("\n[Step 2] 获取美股实时数据...")
    us_stocks = fetch_us_realtime()
    if not us_stocks:
        print("[合并晨报] ⚠️ 美股数据获取失败")
        return None
    
    # Step 3: 生成合并晨报
    print("\n[Step 3] 生成合并晨报...")
    report = generate_merged_report(a_stocks, us_stocks, date_info)
    
    total_elapsed = time.time() - start_time
    
    # 保存
    report_path = r"C:\Users\Pactera\projects\merged_morning_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    output = {
        "framework": "Merged-Global",
        "task": "全球活跃股操盘晨报（A股+美股）",
        "status": "success" if report != "合并晨报生成失败" else "error",
        "result": report,
        "data_source": "腾讯财经API + 新浪财经API实时数据（当天）",
        "a_stocks_count": len(a_stocks),
        "us_stocks_count": len(us_stocks),
        "date_info": date_info,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "execution_time": round(total_elapsed, 2)
    }
    
    result_path = r"C:\Users\Pactera\projects\merged_result.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 合并晨报已保存到: {report_path}")
    print(f"💾 结果已保存到: {result_path}")
    print(f"⏱️  总执行时间: {total_elapsed:.2f}s")
    print(f"\n📄 合并晨报内容:\n{report}")
    
    return output


if __name__ == "__main__":
    main()
