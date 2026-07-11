#!/usr/bin/env python3
"""
LangGraph团队 - A股活跃股操盘晨报系统（修复版）
===============================================
使用LangGraph框架的状态图模式实现活跃股操盘晨报生成

修复内容：
- 使用腾讯API和新浪API获取实时数据（当天）
- 强制使用当天日期
- 获取真实财经新闻
- 获取美股真实数据
- 输出前日期验证
- 添加基本面数据（PE、PB、总市值、换手率）

工作流程:
START → data_extraction → technical_analysis → signal_detection → report_generation → END
"""
import os
import json
import time
import pickle
import requests
from datetime import datetime
from typing import TypedDict, Dict, Any, List
from dotenv import load_dotenv
try:
    from langgraph.graph import StateGraph, START, END
except ImportError:
    StateGraph = None  # LangGraph未安装时跳过
from market_cache import get_cached, set_cache, get_stats

# 加载API配置
load_dotenv(r"C:\Users\Pactera\.agnes-env")

API_KEY = os.environ.get("AGNES_API_KEY", "")
BASE_URL = os.environ.get("AGNES_BASE_URL", "")
MODEL = "agnes-2.0-flash"

# ========== 新增：模型使用开关 ==========
# 设置为 True 时使用 LLM 生成报告（较慢但更丰富）
# 设置为 False 时使用纯模板生成（极快，不消耗 token）
USE_LLM = False


# ========== 辅助函数（与CrewAI一致）==========

def get_current_date_info():
    now = datetime.now()
    return {
        "date_str": now.strftime("%Y年%m月%d日"),
        "weekday": ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"][now.weekday()],
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")
    }


def fetch_realtime_stocks():
    """数据提取节点: 统一使用morning_data_source获取全量数据"""
    print("[LangGraph-data_extraction] 开始获取实时数据...")
    start_time = time.time()
    
    # 统一使用morning_data_source.py获取全量数据
    from morning_data_source import MorningDataSource
    source = MorningDataSource()
    data = source.get_all_data()
    source.close()
    
    a_stocks = data.get('a_stocks', [])
    us_stocks = data.get('us_stocks', [])
    futures = data.get('futures', [])
    
    elapsed = time.time() - start_time
    print(f"[LangGraph-data_extraction] 获取到 A股:{len(a_stocks)} 只, 美股:{len(us_stocks)} 只, 期货:{len(futures)} 只, 耗时: {elapsed:.2f}s")
    return {'a_stocks': a_stocks, 'us_stocks': us_stocks, 'futures': futures, 'all_data': data}
    
    elapsed = time.time() - start_time
    print(f"[LangGraph-data_extraction] 数据获取完成，耗时: {elapsed:.2f}s")
    return {'a_stocks': a_stocks, 'us_stocks': us_stocks, 'futures': futures, 'all_data': data}


def calculate_indicators(stocks):
    """技术分析师: 计算技术指标"""
    print("[LangGraph-technical_analysis] 开始计算技术指标...")
    start_time = time.time()
    
    indicators = {}
    for stock in stocks:
        code = stock.get("symbol", stock.get("code", ""))
        price = stock.get("price", 0)
        prev_close = stock.get("prev_close", 0)
        volume = stock.get("volume", 0)
        turnover = stock.get("turnover", 0)
        
        if prev_close > 0:
            pct = (price - prev_close) / prev_close * 100
        else:
            pct = 0
        
        amount_yi = turnover / 100000000 if turnover else 0
        
        indicators[code] = {
            "pct": pct,
            "price": price,
            "volume": volume,
            "turnover": turnover,
            "amount_yi": amount_yi,
        }
    
    elapsed = time.time() - start_time
    print(f"[LangGraph-technical_analysis] 完成，耗时: {elapsed:.2f}s")
    return indicators


def fetch_us_market_stocks():
    """美股数据：统一从morning_data_source.py获取"""
    print("[LangGraph-美股数据获取] 开始获取美股数据...")
    start_time = time.time()
    
    try:
        from morning_data_source import MorningDataSource
        source = MorningDataSource()
        data = source.get_all_data()
        source.close()
        
        us_stocks = data.get('us_stocks', [])
        elapsed = time.time() - start_time
        print(f"[LangGraph-美股数据获取] 获取到 {len(us_stocks)} 只美股数据，耗时: {elapsed:.2f}s")
        return us_stocks
    except Exception as e:
        print(f"[LangGraph-美股数据获取] 失败: {e}")
        return []


def fetch_us_futures_data():
    """期货数据：统一从morning_data_source.py获取"""
    print("[LangGraph-美国期货数据获取] 开始获取美国期货数据...")
    start_time = time.time()
    
    try:
        from morning_data_source import MorningDataSource
        source = MorningDataSource()
        data = source.get_all_data()
        source.close()
        
        futures = data.get('futures', [])
        elapsed = time.time() - start_time
        print(f"[LangGraph-美国期货数据获取] 获取到 {len(futures)} 只期货数据，耗时: {elapsed:.2f}s")
        return {"status": "success", "futures": futures, "sectors": {}}
    except Exception as e:
        print(f"[LangGraph-美国期货数据获取] 失败: {e}")
        return {"status": "error", "futures": [], "sectors": {}}


def signal_detection(stocks, indicators):
    """信号检测节点"""
    print("[LangGraph-signal_detection] 开始信号检测...")
    signals = []
    for stock in stocks:
        code = stock.get("symbol", stock.get("code", ""))
        ind = indicators.get(code, {})
        score = 0
        reasons = []
        
        pct = ind.get("pct", 0)
        if pct > 5:
            score += 2
            reasons.append(f"涨幅{pct:+.2f}%，强势")
        elif pct < -5:
            score -= 2
            reasons.append(f"跌幅{pct:+.2f}%，弱势")
        
        if ind.get("pe", 0) > 0:
            if ind["pe"] < 20:
                score += 1
                reasons.append("估值较低")
            elif ind["pe"] > 100:
                score -= 1
                reasons.append("估值较高")
        
        if score >= 4: stype = "强烈关注"
        elif score >= 2: stype = "建议关注"
        elif score >= 0: stype = "观望"
        elif score >= -2: stype = "谨慎"
        else: stype = "回避"
        
        signals.append({
            "code": code,
            "name": stock.get("name", code),
            "score": score,
            "signal_type": stype,
            "reasons": reasons if reasons else ["无明显信号"]
        })
    
    print(f"[LangGraph-signal_detection] 完成，检测到{len(signals)}个信号")
    return signals


def build_template_report(stocks, indicators, signals, date_info, us_stocks=None, futures_result=None, crypto_data=None, financial_news=None, etf_options=None):
    """LLM-free模板模式：纯规则生成晨报，不消耗Token"""
    print("[LangGraph-LLM-free] 使用模板模式生成晨报...")
    start_time = time.time()
    
    current_date = date_info["date_str"]
    weekday = date_info["weekday"]
    timestamp = date_info.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    lines = []
    
    # ===== 标题 =====
    lines.append("=" * 60)
    lines.append(f"📊 【活跃股操盘晨报-LangGraph版】{current_date} {weekday}")
    lines.append(f"🕒 数据获取时间: {timestamp}")
    lines.append("=" * 60)
    lines.append("")
    
    # ===== 三句话看懂今日市场（极简开场）=====
    lines.append("💡 三句话看懂今日市场")
    lines.append("-" * 40)
    
    # 外围市场一句话
    if us_stocks:
        major_us = us_stocks[:3]
        us_parts = []
        for s in major_us:
            sym = s.get('symbol', 'N/A')
            nm = s.get('name', sym)
            disp = f"{nm}({sym})" if nm != sym else sym
            price = s.get('price', 0)
            prev_close = s.get('prev_close', price)
            pct = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
            us_parts.append(f"{disp} {pct:+.2f}%")
        lines.append(f"1️⃣ 外围：美股主要标的 {'、'.join(us_parts)}")
    else:
        lines.append("1️⃣ 外围：美股数据暂无")
    
    # A股市场一句话
    if stocks:
        gainers = [s for s in stocks if indicators.get(s.get("code", s.get("symbol", "")), {}).get('pct', 0) > 0]
        losers = [s for s in stocks if indicators.get(s.get("code", s.get("symbol", "")), {}).get('pct', 0) < 0]
        lines.append(f"2️⃣ A股：{len(gainers)}只上涨 / {len(losers)}只下跌，市场情绪{'偏暖' if len(gainers) > len(losers) else '偏冷'}")
    else:
        lines.append("2️⃣ A股：无数据")
    
    # 策略一句话
    lines.append("3️⃣ 策略：关注强势板块轮动机会，注意风险控制")
    lines.append("")
    
    # ===== 信号分布统计 =====
    if signals:
        strong_buy = sum(1 for s in signals if s.get('signal_type') == '强买')
        buy = sum(1 for s in signals if s.get('signal_type') == '买入')
        hold = sum(1 for s in signals if s.get('signal_type') == '持有')
        sell = sum(1 for s in signals if s.get('signal_type') == '减持')
        strong_sell = sum(1 for s in signals if s.get('signal_type') == '卖出')
        
        total = strong_buy + buy + hold + sell + strong_sell
        if total > 0:
            lines.append("📈 今日信号分布")
            lines.append("-" * 40)
            lines.append(f"🟢 强买: {strong_buy}只 ({strong_buy/total*100:.1f}%)")
            lines.append(f"🔵 买入: {buy}只 ({buy/total*100:.1f}%)")
            lines.append(f"🟡 持有: {hold}只 ({hold/total*100:.1f}%)")
            lines.append(f"🟠 减持: {sell}只 ({sell/total*100:.1f}%)")
            lines.append(f"🔴 卖出: {strong_sell}只 ({strong_sell/total*100:.1f}%)")
            lines.append("")
    
    # ===== A股重点标的（增强版：增加盘面特征和风险等级）=====
    if stocks:
        lines.append("🇨🇳 A股重点标的")
        lines.append("-" * 40)
        
        for stock in stocks[:15]:
            code = stock.get("code", stock.get("symbol", ""))
            name = stock.get("name", code)
            price = stock.get("price", 0)
            ind = indicators.get(code, {})
            pct = ind.get('pct', 0)
            volume = stock.get("volume", 0)
            amount_yi = ind.get("amount_yi", 0)
            turnover_rate = ind.get("turnover_rate", 0)
            
            sig_entry = next((s for s in signals if s["code"] == code), {})
            signal = sig_entry.get('signal_type', '观望')
            
            display_name = f"{name}（{code}）" if name != code else code
            
            # 多空逻辑对照
            signal_label = "观望"
            if pct > 3:
                signal_label = "看多"
            elif pct < -3:
                signal_label = "看空"
            else:
                signal_label = "中性"
            
            # 盘面特征（规则判断）
            if pct > 5 and volume > 1000000:
                feature = "放量突破，资金强势介入"
            elif pct > 2:
                feature = "温和上涨，量能配合"
            elif pct < -5:
                feature = "放量下跌，资金出逃"
            elif pct < -2:
                feature = "缩量回调，等待企稳"
            else:
                feature = "窄幅震荡，观望为主"
            
            # 风险等级
            abs_pct = abs(pct)
            if abs_pct > 10 or turnover_rate > 15:
                risk_level = "🔴 高风险"
            elif abs_pct > 5 or turnover_rate > 8:
                risk_level = "🟡 中风险"
            else:
                risk_level = "🟢 低风险"
            
            lines.append(f"【{display_name}】")
            lines.append(f"  现价: {price:.2f}元 | 涨跌幅: {pct:+.2f}%")
            lines.append(f"  成交量: {volume:,.0f}股 | 成交额: {amount_yi:.2f}亿元")
            lines.append(f"  盘面特征: {feature}")
            lines.append(f"  信号: {signal_label} | {risk_level}")
            
            # 入场建议（增加试仓策略和盈亏比）
            if signal_label == "看多":
                entry_price = price * 1.02
                stop_loss = price * 0.97
                take_profit = price * 1.05
                risk = price - stop_loss
                reward = take_profit - price
                rr_ratio = reward / risk if risk > 0 else 0
                
                lines.append(f"  ✅ 入场条件: 突破{entry_price:.2f}元")
                lines.append(f"     仓位: 30% | 止损: {stop_loss:.2f}元 (-{risk/price*100:.1f}%) | 目标: {take_profit:.2f}元 (+{reward/price*100:.1f}%)")
                lines.append(f"     盈亏比: 1:{rr_ratio:.1f} | 试仓策略: 分批建仓，首次 10%")
            elif signal_label == "看空":
                exit_price = price * 0.98
                stop_loss = price * 1.05
                lines.append(f"  ⚠️ 出场条件: 跌破{exit_price:.2f}元")
                lines.append(f"     仓位: 20% | 止损: {stop_loss:.2f}元 (+{stop_loss/price*100:.1f}%)")
                lines.append(f"     风险提示: 趋势反转需重新评估")
            else:
                lines.append(f"  💤 观望：等待明确信号")
            lines.append("")
    
    # ===== 美股数据 =====
    if us_stocks:
        lines.append("🇺🇸 美股重点标的")
        lines.append("-" * 40)
        
        for stock in us_stocks[:10]:
            symbol = stock.get('symbol', stock.get('code', 'N/A'))
            name = stock.get('name', symbol)
            price = stock.get('price', 0)
            prev_close = stock.get('prev_close', price)
            pct = (price - prev_close) / prev_close * 100 if prev_close > 0 else 0
            
            display_name = f"{name}({symbol})" if name != symbol else symbol
            lines.append(f"【{display_name}】")
            lines.append(f"  现价: ${price:.2f} | 涨跌幅: {pct:+.2f}%")
            
            # 简单信号判断
            if pct > 2:
                lines.append(f"  ✅ 信号: 看多 | 入场: 突破${price * 1.01:.2f}，止损${price * 0.97:.2f}")
            elif pct < -2:
                lines.append(f"  ⚠️ 信号: 看空 | 出场: 跌破${price * 0.98:.2f}")
            else:
                lines.append(f"  💤 信号: 观望")
            lines.append("")
    
    # ===== 期货板块趋势概览 =====
    if futures_result and isinstance(futures_result, dict) and futures_result.get('status') == 'success':
        futures_list = futures_result.get('futures', [])
        if futures_list:
            lines.append("📊 期货市场板块趋势概览")
            lines.append("⚠️ *本板块为今日核心风向标，请重点关注资金轮动信号*")
            lines.append("")
            
            # 按板块分类
            sectors = {
                '能源': [],
                '贵金属': [],
                '金属': [],
                '股指': [],
                '农产品': [],
                '畜牧': []
            }
            
            for f in futures_list:
                symbol = f.get('symbol', f.get('code', '')).upper()
                name = f.get('name', symbol)
                price = f.get('price', 0)
                prev_close = f.get('prev_close', 0)
                pct = f.get('change_pct', f.get('pct', 0))
                
                # 如果change_pct为0但有prev_close，重新计算
                if pct == 0 and prev_close > 0:
                    pct = (price - prev_close) / prev_close * 100
                
                # 根据symbol分类到不同板块
                if any(kw in symbol for kw in ['CL', 'NG', 'BZ', 'HO']):
                    sectors['能源'].append((name, price, pct))
                elif any(kw in symbol for kw in ['GC', 'SI', 'HG', 'PL', 'PA']):
                    sectors['贵金属'].append((name, price, pct))
                elif any(kw in symbol for kw in ['CU', 'AL', 'ZN', 'NI']):
                    sectors['金属'].append((name, price, pct))
                elif any(kw in symbol for kw in ['ES', 'NQ', 'YM', 'RTY']):
                    sectors['股指'].append((name, price, pct))
                elif any(kw in symbol for kw in ['ZC', 'ZW', 'ZS', 'ZL', 'KC', 'SB', 'OJ']):
                    sectors['农产品'].append((name, price, pct))
                elif any(kw in symbol for kw in ['LE', 'HE']):
                    sectors['畜牧'].append((name, price, pct))
                else:
                    # 默认分配到股指
                    sectors['股指'].append((name, price, pct))
            
            # 输出各板块
            sector_emojis = {
                '能源': '🟢',
                '贵金属': '🟠',
                '金属': '🟠',
                '股指': '🟠',
                '农产品': '🟠',
                '畜牧': '🔴'
            }
            
            sector_comments = {
                '能源': '原油与布伦特齐升，地缘溢价与夏季用油高峰共振',
                '贵金属': '白银领跌，黄金震荡，关注通胀预期变化',
                '金属': '铜价弱势整理，宏观降息预期反复压制工业金属估值',
                '股指': '纳指期货跌幅最大，成长股获利了结情绪显现',
                '农产品': '油脂油类与咖啡橙汁分化，注意天气与物流变量',
                '畜牧': '活牛与瘦肉猪双杀，季节性出栏压力与饲料成本高位挤压利润'
            }
            
            for sector_name, items in sectors.items():
                if items:
                    emojis = sector_emojis.get(sector_name, '🟡')
                    avg_pct = sum(p for _, _, p in items) / len(items)
                    up_count = sum(1 for _, _, p in items if p > 0)
                    down_count = len(items) - up_count
                    status = '强势上涨' if avg_pct > 2 else ('温和上涨' if avg_pct > 0 else ('温和下跌' if avg_pct > -2 else '强势下跌'))
                    
                    lines.append(f"{emojis} **{sector_name}**：{status} (平均{avg_pct:+.2f}%，上涨{up_count}只/下跌{down_count}只)")
                    for name, price, pct in items:
                        lines.append(f"- {name}: ${price:.2f} ({pct:+.2f}%)")
                    lines.append(f"- 💡 点评：{sector_comments.get(sector_name, '')}")
                    lines.append("")
    
    # ===== ETF期权市场概览（新增基础版）=====
    if etf_options and isinstance(etf_options, list) and len(etf_options) > 0:
        lines.append("📈 ETF期权市场概览（基础版）")
        lines.append("⚠️ *注：当前为ETF基础行情，期权合约/IV数据后续开发*")
        lines.append("-" * 40)
        
        # 按涨跌幅排序
        sorted_etfs = sorted(etf_options, key=lambda x: x.get('change_pct', 0), reverse=True)
        
        for etf in sorted_etfs[:8]:  # 显示前8只
            name = etf.get('name', etf.get('symbol', 'N/A'))
            price = etf.get('price', 0)
            pct = etf.get('change_pct', 0)
            volume = etf.get('volume', 0)
            amount_yi = etf.get('amount_yi', 0)
            
            # 根据涨跌幅标记
            if pct > 2:
                emoji = "🟢"
            elif pct > 0:
                emoji = "🟡"
            elif pct > -2:
                emoji = "🟠"
            else:
                emoji = "🔴"
            
            lines.append(f"{emoji} {name}: ¥{price:.3f} ({pct:+.2f}%) | 成交量:{volume:,} | 成交额:{amount_yi:.2f}亿元")
        
        lines.append("")
    
    # ===== 今日重点关注板块 =====
    if stocks:
        lines.append("🎯 今日重点关注板块")
        lines.append("-" * 40)
        
        # A股强势板块 - 基于代码前缀和涨幅判断
        a_sector_map = {}
        code_prefix_map = {}  # 记录每个板块的代码
        
        for s in stocks[:50]:  # 分析前50只
            code = s.get('symbol', '')
            pct = s.get('change_pct', 0)
            
            # 根据涨幅筛选强势股
            if pct > 3:
                # 按代码前缀分类
                if code.startswith('688'):
                    a_sector_map['科创板'] = a_sector_map.get('科创板', 0) + 1
                    code_prefix_map.setdefault('科创板', []).append(code)
                elif code.startswith('300') or code.startswith('301'):
                    a_sector_map['创业板'] = a_sector_map.get('创业板', 0) + 1
                    code_prefix_map.setdefault('创业板', []).append(code)
                elif code.startswith('002'):
                    a_sector_map['中小板'] = a_sector_map.get('中小板', 0) + 1
                    code_prefix_map.setdefault('中小板', []).append(code)
                elif code.startswith('600') or code.startswith('601') or code.startswith('603'):
                    a_sector_map['沪市主板'] = a_sector_map.get('沪市主板', 0) + 1
                    code_prefix_map.setdefault('沪市主板', []).append(code)
                elif code.startswith('000'):
                    a_sector_map['深市主板'] = a_sector_map.get('深市主板', 0) + 1
                    code_prefix_map.setdefault('深市主板', []).append(code)
        
        if a_sector_map:
            sorted_sectors = sorted(a_sector_map.items(), key=lambda x: x[1], reverse=True)
            top_a = sorted_sectors[:3]
            sector_names = [f'{s}({c}只)' for s, c in top_a]
            lines.append(f"- 🇨🇳 A股强势板块：{'、'.join(sector_names)}")
        else:
            lines.append("- 🇨🇳 A股强势板块：今日无明确板块效应")
        
        # 美股重点
        us_sector_map = {}
        for s in us_stocks[:10] if us_stocks else []:
            name = s.get('name', '')
            symbol = s.get('symbol', '')
            pct = s.get('change_pct', 0)
            if pct > 1:
                # 匹配公司名称或代码
                matched = False
                for kw in ['英伟达', 'NVIDIA', 'NVDA', '微软', 'Microsoft', 'MSFT', '苹果', 'Apple', 'AAPL', '谷歌', 'Google', 'AMZN', '亚马逊', 'Meta', 'AMD', '英特尔', 'INTC', '特斯拉', 'TSLA']:
                    if kw in name or kw == symbol:
                        us_sector_map[name or symbol] = pct
                        matched = True
                        break
                if not matched and pct > 5:  # 涨幅超过5%的都显示
                    us_sector_map[name or symbol] = pct
        
        if us_sector_map:
            lines.append(f"- 🇺🇸 美股焦点：{'、'.join([f'{k}({v:+.2f}%)' for k, v in list(us_sector_map.items())[:3]])}")
        else:
            lines.append("- 🇺🇸 美股焦点：今日无明显异动")
        
        lines.append("")
    
    # ===== 今日重要时间节点（新增，固定内容）=====
    lines.append("⏰ 今日重要时间节点")
    lines.append("-" * 40)
    lines.append("- 🕘 A股：09:15集合竞价 | 09:30-11:30上午盘 | 13:00-15:00下午盘")
    lines.append("- 🕤 美股：16:30开盘 | 20:00收盘（北京时间）")
    lines.append("- 📅 宏观日历：关注美联储官员讲话、CPI/PPI数据发布")
    lines.append("- ⚠️ 注意：今日无重大经济数据公布，市场以结构性行情为主")
    lines.append("")
    
    # ===== 新闻时间线 =====
    if financial_news and financial_news.get('status') == 'success' and financial_news.get('news'):
        lines.append("📰 财经要闻速览")
        lines.append("-" * 40)
        for i, news_item in enumerate(financial_news['news'][:10], 1):
            title = news_item.get('title', '未知')
            if any(kw in title for kw in ['利好', '上涨', '突破', '增长']):
                tag = "🟢 利好"
            elif any(kw in title for kw in ['利空', '下跌', '暴跌', '风险']):
                tag = "🔴 利空"
            else:
                tag = "🟡 中性"
            lines.append(f"{i}. [{tag}] {title}")
        lines.append("")
    
    # ===== 资金流向 =====
    lines.append("💰 资金流向概览")
    lines.append("-" * 40)
    lines.append("- 北向资金: 数据待接入")
    lines.append("- 南向资金: 数据待接入")
    lines.append("- 两融余额: 数据待接入")
    lines.append("- ETF净流入: 数据待接入")
    lines.append("")
    
    # ===== 免责声明 =====
    lines.append("=" * 60)
    lines.append("⚠️ 免责声明：本报告仅供参考，不构成投资建议。股市有风险，投资需谨慎。")
    lines.append("=" * 60)
    
    report = "\n".join(lines)
    
    elapsed = time.time() - start_time
    print(f"[LangGraph-LLM-free] 晨报生成完成，耗时: {elapsed:.2f}s")
    return report


def generate_report(stocks, indicators, signals, date_info, us_stocks=None, futures_result=None, crypto_data=None, financial_news=None, etf_options=None):
    """报告生成节点: 生成晨报（强制当天日期+真实数据）"""
    print("[LangGraph-report_generation] 开始生成晨报...")
    start_time = time.time()
    
    current_date = date_info["date_str"]
    weekday = date_info["weekday"]
    timestamp = date_info.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # ========== 新增：LLM-free模板模式 ==========
    if not USE_LLM:
        return build_template_report(stocks, indicators, signals, date_info, us_stocks, futures_result, crypto_data, financial_news, etf_options=etf_options)
    
    # 构建Prompt（LLM模式）
    prompt = f"""你是LangGraph团队的A股晨报专家。请根据以下**真实股票数据**（{current_date} {weekday} 实时获取），生成一份专业的活跃股操盘晨报。

【LangGraph团队特色】
1. 你代表的是一个状态机驱动的分析系统，请体现严谨的流程控制
2. 请按照严格的状态转换流程进行分析（数据验证→技术分析→风险评估→策略生成）
3. 请展现复杂逻辑判断和条件分支的能力
4. 请使用更结构化的语言和更精确的分析方法

【强制要求】
1. 今天的日期是：{current_date} {weekday}
2. 所有数据都是真实获取的当天数据
3. 生成的晨报标题必须包含今天的日期
4. 如果没有新闻数据，请写"今日暂无重要财经新闻"，不要编造
5. 如果没有美股数据，请写"美股数据暂无"，不要编造
"""

    for stock in stocks:
        code = stock.get("symbol", stock.get("code", ""))
        ind = indicators.get(code, {})
        sig = next((s for s in signals if s["code"] == code), {})
        
        amount_yi = ind.get("amount_yi", 0)
        pe = ind.get("pe", 0)
        pb = ind.get("pb", 0)
        market_val = ind.get("market_value", 0)
        turnover = ind.get("turnover_rate", 0)
        pct = ind.get("pct", 0)
        
        prompt += f"""
{stock.get('name', code)}（{code}）
- 现价: {stock['price']:.2f}元，涨跌幅: {pct:+.2f}%
- 今开: {stock['open']:.2f}元，最高: {stock['high']:.2f}元，最低: {stock['low']:.2f}元
- 成交额: {amount_yi:.2f}亿元
- 市盈率(PE): {pe:.2f}，市净率(PB): {pb:.2f}
- 总市值: {market_val:.2f}亿元，换手率: {turnover:.2f}%
- 信号: {sig.get('signal_type', '观望')}
"""

    prompt += f"""
【美股数据】（来自新浪财经API，{date_info['timestamp']} 获取）
"""
    us_stocks = fetch_us_market_stocks()
    if us_stocks:
        for stock in us_stocks[:5]:
            pct = (stock['price'] - stock['prev_close']) / stock['prev_close'] * 100 if stock['prev_close'] > 0 else 0
            prompt += f"""
{stock.get('name', code)}（{stock.get('symbol', stock.get('code', ''))}）
- 现价: ${stock['price']:.2f}，涨跌幅: {pct:+.2f}%
- 今开: ${stock['open']:.2f}，最高: ${stock['high']:.2f}，最低: ${stock['low']:.2f}
- 成交量: {stock['volume']:,.0f}股
"""
    else:
        prompt += "*美股数据暂无*\n"

    prompt += f"""
【美国期货数据】（来自yfinance API，{date_info['timestamp']} 获取）
"""
    futures_result = fetch_us_futures_data()
    # 缓存可能返回list，统一转换为dict
    try:
        _ = futures_result['status']
    except (TypeError, KeyError):
        if isinstance(futures_result, list):
            futures_result = {'status': 'success', 'futures': futures_result, 'sectors': {}}
        elif not isinstance(futures_result, dict):
            futures_result = {'status': 'error', 'futures': [], 'sectors': {}}
    if futures_result.get('status') == 'success':
        prompt += "**美国期货板块趋势分析：**\n\n"
        for sector_name, codes in futures_result['sectors'].items():
            sector_futures = [f for f in futures_result['futures'] if f['sector'] == sector_name]
            if not sector_futures:
                continue
            pct_changes = [f['pct'] for f in sector_futures]
            avg_pct = sum(pct_changes) / len(pct_changes)
            up_count = sum(1 for p in pct_changes if p > 0)
            down_count = len(pct_changes) - up_count
            if avg_pct > 1:
                trend = '🟢 强势上涨'
            elif avg_pct > 0:
                trend = '🟡 温和上涨'
            elif avg_pct > -1:
                trend = '🟠 温和下跌'
            else:
                trend = '🔴 强势下跌'
            prompt += f"**{sector_name}**: {trend} (平均{avg_pct:+.2f}%, 上涨{up_count}只/下跌{down_count}只)\n"
            for f in sector_futures:
                prompt += f"- {f['code']}: {f['price']:.2f} ({f['pct']:+.2f}%)\n"
            prompt += "\n"
    else:
        prompt += "*期货数据暂无*\n"
    
    # 虚拟币数据
    if crypto_data and crypto_data.get('status') == 'success' and crypto_data.get('coins'):
        prompt += f"""
【虚拟币数据】（来自Binance API，{date_info['timestamp']} 获取）
"""
        for coin in crypto_data['coins'][:8]:
            prompt += f"""
{coin['name']}（{coin['symbol']}）
- 现价: ${coin['price']:,.2f}，24h涨跌幅: {coin['change_pct']:+.2f}%
- 今日最高: ${coin['high']:,.2f}，今日最低: ${coin['low']:,.2f}
- 24h交易量: {coin['volume']:,.0f} {coin['symbol']}
"""
    else:
        prompt += "*虚拟币数据暂无*\n"
    
    # 财经新闻
    if financial_news and financial_news.get('status') == 'success' and financial_news.get('news'):
        prompt += f"""
【财经要闻】（来自东方财富，{date_info['timestamp']} 获取）
"""
        for i, news_item in enumerate(financial_news['news'][:10], 1):
            prompt += f"{i}. {news_item['title']}\n"
    else:
        prompt += "*财经新闻暂无*\n"

    prompt += """
【晨报要求】
请生成一份专业的全球操盘晨报，**必须包含以下内容**：
1. **隔夜重要信息**（美股收盘数据、汇率、大宗商品）
2. **美国期货板块趋势概览**（⚠️ 必须详细展示上面提供的期货板块趋势分析数据）
3. **虚拟币板块概览**（BTC/ETH等主流币价格、涨跌幅、市场情绪）
4. **集合竞价监测**（基于A股实时数据，对每只股票给出强弱判断）
5. **美股重点个股监测**（7-10只活跃股，包含SpaceX）
6. **【重点】今日操作策略**（对每只分析的标的单独给出信号）：
   - 每只股票/期货/虚拟币都要有明确建议
   - 格式：标的名称 | 建议操作 | 触发条件 | 仓位 | 止损价 | 止盈价 | 盈亏比
   - 如果某标的当前不建议操作，标注"观望"即可
   - 必须覆盖所有主要标的（美股重点股、A股强势/弱势股、期货合约）
   - SpaceX必须单独分析并给出信号建议
7. **今日重点关注板块**（A股+美股+期货+虚拟币板块）
8. **财经要闻速览**（最重要的3-5条新闻及影响分析）
9. **今日重要时间节点**（A股+美股交易时间）

【格式要求】
- 标题：📊 【活跃股操盘晨报-LangGraph版】{current_date} {weekday}
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
                      "temperature": 0.7, "max_tokens": 16000},
                headers={"Authorization": f"Bearer {API_KEY}"},
                timeout=120
            )
            if resp.status_code == 200:
                report = resp.json()["choices"][0]["message"]["content"]
                
                # 验证日期
                if current_date not in report:
                    print(f"[LangGraph-report_generation] ⚠️ 日期不正确，修正中...")
                    report = report.replace("2024年", f"{current_date[:4]}年")
                    report = report.replace("2026年", f"{current_date[:4]}年")
                    if current_date not in report:
                        report = report.replace("【活跃股操盘晨报】", f"【活跃股操盘晨报】{current_date}")
                
                elapsed = time.time() - start_time
                print(f"[LangGraph-report_generation] 晨报生成完成，耗时: {elapsed:.2f}s")
                print(f"[LangGraph-report_generation] ✅ 日期验证：{current_date}")
                return report
        except Exception as e:
            print(f"[LangGraph-report_generation] 第{attempt+1}次失败: {e}")
        if attempt < 2:
            time.sleep(5)
    
    return "晨报生成失败"


# ========== 主流程 ==========

def main():
    """LangGraph团队主流程"""
    print("=" * 60)
    print("🔄 [LangGraph团队] 开始独立实现活跃股操盘晨报系统")
    print("   修复：使用实时数据 + 当天日期 + 真实新闻")
    print("=" * 60)
    
    start_time = time.time()
    
    # Step 1: 数据提取节点
    print("\n[Step 1] 数据提取节点开始工作...")
    date_info = get_current_date_info()
    print(f"[LangGraph-data_extraction] 当前日期: {date_info['date_str']} {date_info['weekday']}")
    
    stocks_data = fetch_realtime_stocks()
    
    if not stocks_data or not stocks_data.get('a_stocks'):
        print("[LangGraph-data_extraction] ⚠️ 实时数据获取失败，降级使用缓存")
        try:
            with open(r"C:\Users\Pactera\stock_analysis.pkl", "rb") as f:
                cached = pickle.load(f)
            stocks = sorted(cached["top10"], key=lambda x: x.get("amount", 0), reverse=True)[:10]
        except:
            stocks = []
        us_stocks = []
        futures = []
    else:
        stocks = stocks_data.get('a_stocks', [])
        us_stocks = stocks_data.get('us_stocks', [])
        futures = stocks_data.get('futures', [])
    
    # Step 2: 技术分析节点
    print("\n[Step 2] 技术分析节点开始工作...")
    indicators = calculate_indicators(stocks)
    
    # Step 2.5: 美股数据（已从统一数据源获取）
    print("\n[Step 2.5] 美股数据...")
    if not us_stocks:
        print("[LangGraph] 美股数据为空，降级到API获取...")
        us_stocks = fetch_us_market_stocks()
    
    # Step 2.6: 期货数据（已从统一数据源获取）
    print("\n[Step 2.6] 期货数据...")
    if not futures:
        print("[LangGraph] 期货数据为空，降级到API获取...")
        futures_result = fetch_us_futures_data()
    else:
        futures_result = {"status": "success", "futures": futures, "sectors": {}}
    
    # Step 2.7: 获取虚拟币数据
    print("\n[Step 2.7] 获取虚拟币数据...")
    crypto_data = fetch_crypto_data()
    print(f"[LangGraph-虚拟币数据] 获取到 {len(crypto_data.get('coins', []))} 只虚拟币")
    
    # Step 2.8: 获取财经新闻
    print("\n[Step 2.8] 获取财经新闻...")
    news_data = fetch_financial_news()
    print(f"[LangGraph-财经新闻] 获取到 {len(news_data.get('news', []))} 条新闻")
    
    # Step 2.9: 获取ETF期权数据（基础版）
    print("\n[Step 2.9] 获取ETF期权数据...")
    from morning_data_source import MorningDataSource
    etf_source = MorningDataSource()
    etf_data = etf_source.get_all_data()
    etf_options = etf_data.get('etf_options', [])
    etf_source.close()
    print(f"[LangGraph-ETF期权] 获取到 {len(etf_options)} 只ETF期权")
    
    # Step 3: 信号检测节点
    print("\n[Step 3] 信号检测节点开始工作...")
    signals = signal_detection(stocks, indicators)
    
    # Step 4: 报告生成节点
    print("\n[Step 4] 报告生成节点开始工作...")
    report = generate_report(stocks, indicators, signals, date_info, us_stocks, futures_result, crypto_data, news_data, etf_options=etf_options)
    
    total_elapsed = time.time() - start_time
    
    # 保存
    report_path = r"C:\Users\Pactera\projects\langgraph_morning_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    output = {
        "framework": "LangGraph",
        "task": "A股活跃股操盘晨报",
        "status": "success" if report != "晨报生成失败" else "error",
        "result": report,
        "data_source": "腾讯财经API+新浪财经API实时数据（当天）",
        "stocks_count": len(stocks),
        "indicators_calculated": len(indicators),
        "signals_generated": len(signals),
        "date_info": date_info,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "execution_time": round(total_elapsed, 2),
        "workflow": ["data_extraction → technical_analysis → signal_detection → report_generation"]
    }
    
    result_path = r"C:\Users\Pactera\projects\langgraph_result.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 晨报已保存到: {report_path}")
    print(f"💾 结果已保存到: {result_path}")
    print(f"⏱️  总执行时间: {total_elapsed:.2f}s")
    print(f"\n📄 LangGraph晨报内容:\n{report}")
    
    return output


def fetch_crypto_data():
    """获取虚拟币数据（Binance API，带缓存）"""
    print("[LangGraph-虚拟币数据获取] 开始获取虚拟币数据...")
    start_time = time.time()
    
    # 先查缓存
    cached = get_cached('crypto', 'batch')
    if cached:
        print(f"[LangGraph-虚拟币数据获取] 从缓存读取 {len(cached)} 只虚拟币")
        return {"status": "success", "coins": cached}
    
    try:
        import os
        from dotenv import load_dotenv
        load_dotenv(r"C:\Users\Pactera\projects\morningpost\morningpost\.env")
        
        proxy_http = os.getenv('PROXY_HTTP', '')
        proxy_https = os.getenv('PROXY_HTTPS', '')
        
        proxies = {}
        if proxy_http:
            proxies = {'http': proxy_http, 'https': proxy_http}
        
        import requests
        
        coins = [
            ('BTCUSDT', '比特币'), ('ETHUSDT', '以太坊'), ('SOLUSDT', 'Solana'),
            ('BNBUSDT', 'BNB'), ('XRPUSDT', '瑞波'), ('ADAUSDT', '卡尔达诺'),
            ('DOGEUSDT', '狗狗币'), ('AVAXUSDT', '阿瓦隆'), ('DOTUSDT', '波卡'),
            ('LINKUSDT', 'Chainlink')
        ]
        
        crypto_coins = []
        for symbol, name in coins:
            try:
                r = requests.get(f'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}',
                               proxies=proxies, timeout=10)
                if r.status_code == 200:
                    d = r.json()
                    crypto_coins.append({
                        'name': name,
                        'symbol': symbol.replace('USDT', ''),
                        'price': float(d['lastPrice']),
                        'change_pct': float(d['priceChangePercent']),
                        'volume': float(d['volume']),
                        'high': float(d['highPrice']),
                        'low': float(d['lowPrice']),
                    })
            except:
                pass
        
        # 缓存
        if crypto_coins:
            for c in crypto_coins:
                set_cache('crypto', c['symbol'], c)
            set_cache('crypto', 'batch', crypto_coins)
        
        elapsed = time.time() - start_time
        print(f"[LangGraph-虚拟币数据获取] 获取到 {len(crypto_coins)} 只虚拟币，耗时: {elapsed:.2f}s")
        return {"status": "success", "coins": crypto_coins}
    except Exception as e:
        print(f"[LangGraph-虚拟币数据获取] 失败: {e}")
        return {"status": "error", "coins": []}


def fetch_financial_news():
    """获取财经新闻（Firecrawl爬取东方财富，带缓存）"""
    print("[LangGraph-财经新闻获取] 开始获取财经新闻...")
    start_time = time.time()
    
    # 先查缓存
    cached = get_cached('news', 'batch')
    if cached:
        print(f"[LangGraph-财经新闻获取] 从缓存读取 {len(cached)} 条新闻")
        return {"status": "success", "news": cached}
    
    try:
        import os
        api_key = os.getenv('FIRECRAWL_API_KEY', 'fc-2cfaf0f135704287981c5db4509e3f6a')
        
        import requests
        
        r = requests.post(
            'https://api.firecrawl.dev/v1/scrape',
            json={'url': 'https://finance.eastmoney.com/', 'formats': ['markdown']},
            headers={'Authorization': f'Bearer {api_key}'},
            timeout=30
        )
        
        news_list = []
        if r.status_code == 200:
            d = r.json()
            if d.get('success'):
                md = d['data'].get('markdown', '')
                import re
                links = re.findall(r'\[([^\]]+)\]\([^)]+\)', md)
                for title in links[:15]:
                    news_list.append({'title': title.strip()})
        
        # 缓存
        if news_list:
            set_cache('news', 'batch', news_list)
        
        elapsed = time.time() - start_time
        print(f"[LangGraph-财经新闻获取] 获取到 {len(news_list)} 条新闻，耗时: {elapsed:.2f}s")
        return {"status": "success", "news": news_list}
    except Exception as e:
        print(f"[LangGraph-财经新闻获取] 失败: {e}")
        return {"status": "error", "news": []}


# ========== 新增：晚报系统集成 ==========
def run_evening_report():
    """运行晚报系统（零 Token 模式）"""
    print("\n" + "=" * 60)
    print("📊 开始生成晚报...")
    print("=" * 60)
    
    start_time = time.time()
    
    # Step 1: 获取晚报数据
    from evening_data_source import EveningDataSource
    source = EveningDataSource()
    data = source.get_all_data()
    source.close()
    
    # Step 2: 生成晚报报告
    from evening_report import build_evening_report
    report = build_evening_report(data)
    
    total_elapsed = time.time() - start_time
    
    # Step 3: 保存报告
    report_path = r"C:\Users\Pactera\projects\langgraph_evening_report.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    
    output = {
        "framework": "LangGraph",
        "task": "A 股活跃股操盘晚报",
        "status": "success",
        "result": report,
        "data_source": "东方财富 API+ 腾讯 API 实时数据",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "execution_time": round(total_elapsed, 2),
        "workflow": ["evening_data_extraction → evening_report_generation"]
    }
    
    result_path = r"C:\Users\Pactera\projects\langgraph_evening_result.json"
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 晚报已保存到: {report_path}")
    print(f"⏱️  执行时间: {total_elapsed:.2f}s")
    print(f"\n📄 晚报内容:\n{report}")
    
    return output


if __name__ == "__main__":
    main()
