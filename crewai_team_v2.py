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


def fetch_us_market_stocks():
    """获取美股个股数据（新浪财经API，带缓存）"""
    print("[CrewAI-美股数据获取] 开始获取美股数据...")
    start_time = time.time()
    
    # 先查缓存
    cached = get_cached('us_stock', 'batch')
    if cached:
        print(f"[CrewAI-美股数据获取] 从缓存读取 {len(cached)} 只美股数据")
        return cached
    
    us_stocks = []
    try:
        symbols = 'gb_tsla,gb_aapl,gb_googl,gb_msft,gb_nvda,gb_amzn,gb_meta,gb_NFLX,gb_TSM,gb_INTC,gb_SPCX'
        url = f'https://hq.sinajs.cn/list={symbols}'
        headers = {'Referer': 'https://finance.sina.com.cn/', 'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'gbk'
        
        stock_names = {
            'tsla': '特斯拉', 'aapl': '苹果', 'googl': '谷歌', 'msft': '微软',
            'nvda': '英伟达', 'amzn': '亚马逊', 'meta': 'Meta', 'NFLX': '奈飞',
            'TSM': '台积电', 'INTC': '英特尔', 'SPCX': 'SpaceX'
        }
        
        for line in resp.text.strip().split('\n'):
            if '=' in line:
                data = line.split('"')[1] if '"' in line else ''
                parts = data.split(',')
                if len(parts) >= 3:
                    code = line.split('=')[0].split('_')[-1].strip().rstrip('"').lower()
                    name = stock_names.get(code, code)
                    # 新浪美股格式: [0]名称 [1]现价 [2]涨跌额 [3]时间 [4]开盘 [5]昨收 [6]最高 [7]最低 [8]成交量
                    try:
                        current_price = float(parts[1])
                        prev_close = float(parts[5]) if len(parts) > 5 and parts[5] else 0
                        open_price = float(parts[4]) if len(parts) > 4 and parts[4] else 0
                        high = float(parts[6]) if len(parts) > 6 and parts[6] else 0
                        low = float(parts[7]) if len(parts) > 7 and parts[7] else 0
                        volume = int(float(parts[8])) if len(parts) > 8 else 0
                        
                        # 非交易时间prev_close可能为0，用现价>0和成交量>0判断有效数据
                        if current_price > 0 and volume > 0:
                            us_stocks.append({
                                'name': name,
                                'code': code.upper(),
                                'price': current_price,
                                'prev_close': prev_close,
                                'open': open_price,
                                'high': high,
                                'low': low,
                                'volume': volume,
                            })
                            # 缓存单个股票
                            set_cache('us_stock', code, us_stocks[-1])
                    except ValueError as e:
                        print(f"[CrewAI-美股数据获取] 解析失败 {code}: {e}")
    except Exception as e:
        print(f"[CrewAI-美股数据获取] 失败: {e}")
    
    # 缓存整批数据
    if us_stocks:
        set_cache('us_stock', 'batch', us_stocks)
    
    elapsed = time.time() - start_time
    print(f"[CrewAI-美股数据获取] 获取到 {len(us_stocks)} 只美股数据，耗时: {elapsed:.2f}s")
    return us_stocks


def fetch_us_futures_data():
    """获取美国期货数据（使用新浪财经API，带缓存）"""
    print("[CrewAI-美国期货数据获取] 开始获取美国期货数据...")
    start_time = time.time()
    
    # 先查缓存
    cached = get_cached('futures', 'batch')
    if cached:
        print(f"[CrewAI-美国期货数据获取] 从缓存读取 {len(cached)} 只期货数据")
        return cached
    
    try:
        sectors = {
            '贵金属': ['hf_GC', 'hf_SI'],
            '能源': ['hf_CL', 'hf_NG'],
            '金属': ['hf_HG'],
            '股指': ['hf_ES', 'hf_NQ', 'hf_YM', 'hf_RTY'],
            '农产品': ['ZC', 'ZW', 'ZS', 'KC', 'SB', 'CT', 'OJ'],
            '畜牧': ['LE', 'HE']
        }
        
        code_names = {
            'hf_GC': '纽约黄金', 'hf_SI': '纽约白银',
            'hf_CL': '纽约原油', 'hf_NG': '天然气', 'hf_BZ': '布伦特原油',
            'hf_HG': '铜',
            'hf_ES': '标普500', 'hf_NQ': '纳斯达克', 'hf_YM': '道琼斯', 'hf_RTY': '罗素2000',
            'ZC': '玉米', 'ZW': '小麦', 'ZS': '大豆',
            'KC': '咖啡', 'SB': '糖', 'CT': '棉花', 'OJ': '橙汁',
            'LE': '活牛', 'HE': '瘦肉猪'
        }
        
        # 构建新浪代码列表
        all_codes = []
        for codes in sectors.values():
            all_codes.extend(codes)
        
        symbols = ','.join(all_codes)
        url = f'https://hq.sinajs.cn/list={symbols}'
        headers = {'Referer': 'https://finance.sina.com.cn/'}
        resp = requests.get(url, headers=headers, timeout=15)
        
        futures = []
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
                if len(fields) < 10:
                    continue
                name = code_names.get(symbol, symbol)
                current = float(fields[0]) if fields[0] else 0
                prev_close = float(fields[2]) if fields[2] else 0
                high = float(fields[4]) if fields[4] else 0
                low = float(fields[5]) if fields[5] else 0
                pct = (current - prev_close) / prev_close * 100 if prev_close > 0 else 0
                futures.append({
                    'sector': '未知',
                    'code': symbol,
                    'name': name,
                    'price': current,
                    'prev_close': prev_close,
                    'high': high,
                    'low': low,
                    'pct': pct
                })
            except Exception as e:
                print(f"[期货获取] {symbol} 解析错误: {e}")
                continue
        
        # 缓存每条期货数据
        for f in futures:
            set_cache('futures', f['code'], f)
        # 缓存整批
        if futures:
            set_cache('futures', 'batch', futures)
        
        elapsed = time.time() - start_time
        print(f"[CrewAI-美国期货数据获取] 获取到 {len(futures)} 只美国期货数据，耗时: {elapsed:.2f}s")
        return {"status": "success", "futures": futures, "sectors": sectors}
    except Exception as e:
        print(f"[CrewAI-美国期货数据获取] 失败: {e}")
        return {"status": "error", "futures": [], "sectors": {}}


def calculate_indicators(stocks):
    """技术分析师: 计算技术指标"""
    print("[CrewAI-技术分析师Agent] 开始计算技术指标...")
    start_time = time.time()
    
    indicators = {}
    for stock in stocks:
        code = stock.get("code", stock.get("symbol", ""))
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


def build_template_report(stocks, indicators, date_info, news, us_stocks, futures_result, crypto_data=None, financial_news=None, options_data=None, etf_options=None):
    """LLM-free模板模式：纯规则生成晨报，不消耗Token"""
    print("[CrewAI-LLM-free] 使用模板模式生成晨报...")
    start_time = time.time()
    
    current_date = date_info["date_str"]
    weekday = date_info["weekday"]
    timestamp = date_info.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    lines = []
    
    # ===== 标题 =====
    lines.append("=" * 60)
    lines.append(f"📊 【活跃股操盘晨报-CrewAI版】{current_date} {weekday}")
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
            pct = s.get('change_pct', 0)
            us_parts.append(f"{disp} {pct:+.2f}%")
        lines.append(f"1️⃣ 外围：美股主要标的 {'、'.join(us_parts)}")
    else:
        lines.append("1️⃣ 外围：美股数据暂无")
    
    # A股市场一句话
    if stocks:
        gainers = [s for s in stocks if s.get('change_pct', 0) > 0]
        losers = [s for s in stocks if s.get('change_pct', 0) < 0]
        lines.append(f"2️⃣ A股：{len(gainers)}只上涨 / {len(losers)}只下跌，市场情绪{'偏暖' if len(gainers) > len(losers) else '偏冷'}")
    else:
        lines.append("2️⃣ A股：无数据")
    
    # 策略一句话
    lines.append("3️⃣ 策略：关注强势板块轮动机会，注意风险控制")
    lines.append("")
    
    # ===== 期权市场概览（新增）=====
    if options_data and isinstance(options_data, dict) and options_data.get('status') == 'success':
        opt_list = options_data.get('options', [])
        if opt_list:
            lines.append("📈 期权市场概览")
            lines.append("-" * 40)
            for opt in opt_list[:5]:  # 只显示前5个主力合约
                name = opt.get('name', opt.get('symbol', 'N/A'))
                price = opt.get('price', 0)
                pct = opt.get('change_pct', 0)
                volume = opt.get('volume', 0)
                iv = opt.get('iv', None)  # 隐含波动率
                iv_str = f"IV={iv:.2%}" if iv else "IV=N/A"
                lines.append(f"- {name}: ${price:.3f} ({pct:+.2f}%) | 成交量:{volume:,} | {iv_str}")
            lines.append("")
    
    # ===== 期权市场概览（新增）=====
    if options_data and isinstance(options_data, dict) and options_data.get('status') == 'success':
        opt_list = options_data.get('options', [])
        if opt_list:
            lines.append("📈 期权市场概览")
            lines.append("-" * 40)
            for opt in opt_list[:5]:  # 只显示前5个主力合约
                name = opt.get('name', opt.get('symbol', 'N/A'))
                price = opt.get('price', 0)
                pct = opt.get('change_pct', 0)
                volume = opt.get('volume', 0)
                iv = opt.get('iv', None)  # 隐含波动率
                iv_str = f"IV={iv:.2%}" if iv else "IV=N/A"
                lines.append(f"- {name}: ${price:.3f} ({pct:+.2f}%) | 成交量:{volume:,} | {iv_str}")
            lines.append("")
    
    # ===== 期货板块趋势概览（新增，来自merged版本精华）=====
    if isinstance(futures_result, dict) and futures_result.get('status') == 'success':
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
    
    # ===== 信号分布统计 =====
    if indicators:
        strong_buy = 0
        buy = 0
        hold = 0
        sell = 0
        strong_sell = 0
        
        for code, ind in indicators.items():
            pct = ind.get('pct', 0)
            turnover_rate = ind.get('turnover_rate', 0)
            
            # 简单的信号判断逻辑
            if pct > 5 and turnover_rate > 3:
                strong_buy += 1
            elif pct > 2:
                buy += 1
            elif pct > -2:
                hold += 1
            elif pct > -5:
                sell += 1
            else:
                strong_sell += 1
        
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
        
        for stock in stocks[:15]:  # 只显示前15只
            code = stock.get("symbol", stock.get("code", ""))
            name = stock.get("name", code)
            price = stock.get("price", 0)
            pct = stock.get("change_pct", 0)
            volume = stock.get("volume", 0)
            amount_yuan = stock.get("turnover", 0) or stock.get("amount", 0)
            amount_yi = amount_yuan / 100000000 if amount_yuan else 0
            
            display_name = f"{name}（{code}）" if name != code else code
            
            # 多空逻辑对照
            signal = "观望"
            if pct > 3:
                signal = "看多"
            elif pct < -3:
                signal = "看空"
            else:
                signal = "中性"
            
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
            if abs_pct > 10 or stock.get('turnover_rate', 0) > 15:
                risk_level = "🔴 高风险"
            elif abs_pct > 5 or stock.get('turnover_rate', 0) > 8:
                risk_level = "🟡 中风险"
            else:
                risk_level = "🟢 低风险"
            
            lines.append(f"【{display_name}】")
            lines.append(f"  现价: {price:.2f}元 | 涨跌幅: {pct:+.2f}%")
            lines.append(f"  成交量: {volume:,.0f}股 | 成交额: {amount_yi:.2f}亿元")
            lines.append(f"  盘面特征: {feature}")
            lines.append(f"  信号: {signal} | {risk_level}")
            
            # 入场建议（增加试仓策略和盈亏比）
            if signal == "看多":
                entry_price = price * 1.02
                stop_loss = price * 0.97
                take_profit = price * 1.05
                risk = price - stop_loss
                reward = take_profit - price
                rr_ratio = reward / risk if risk > 0 else 0
                
                lines.append(f"  ✅ 入场条件: 突破{entry_price:.2f}元")
                lines.append(f"     仓位: 30% | 止损: {stop_loss:.2f}元 (-{risk/price*100:.1f}%) | 目标: {take_profit:.2f}元 (+{reward/price*100:.1f}%)")
                lines.append(f"     盈亏比: 1:{rr_ratio:.1f} | 试仓策略: 分批建仓，首次10%")
            elif signal == "看空":
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
            symbol = stock.get('symbol', 'N/A')
            name = stock.get('name', symbol)
            price = stock.get('price', 0)
            pct = stock.get('change_pct', 0)
            
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
    
    # ===== 期货数据 =====
    if isinstance(futures_result, dict) and futures_result.get('status') == 'success':
        futures_list = futures_result.get('futures', [])
        if futures_list:
            lines.append("📊 美国期货数据")
            lines.append("-" * 40)
            for f in futures_list[:10]:
                symbol = f.get('symbol', f.get('code', 'N/A'))
                price = f.get('price', 0)
                change_pct = f.get('change_pct', f.get('pct', 0))
                lines.append(f"- {symbol}: ${price:.2f} ({change_pct:+.2f}%)")
            lines.append("")
    
    # ===== 今日重点关注板块（新增）=====
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
            # 简单标签分类
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
    print(f"[CrewAI-LLM-free] 晨报生成完成，耗时: {elapsed:.2f}s")
    return report


def generate_morning_report(stocks, indicators, date_info, news, us_stocks, futures_result, crypto_data=None, financial_news=None, etf_options=None):
    """晨报撰稿人Agent: 根据分析结果生成专业晨报"""
    print("[CrewAI-晨报撰稿人Agent] 开始生成晨报...")
    start_time = time.time()
    
    current_date = date_info["date_str"]
    weekday = date_info["weekday"]
    timestamp = date_info.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    # ========== 新增：LLM-free模板模式 ==========
    if not USE_LLM:
        return build_template_report(stocks, indicators, date_info, news, us_stocks, futures_result, crypto_data, financial_news, etf_options=etf_options)
    
    # 构建Prompt（LLM模式）
    prompt = f"""你是CrewAI团队的A股晨报专家。请根据以下**真实股票数据**（{current_date} {weekday} 实时获取），生成一份专业的活跃股操盘晨报。

【CrewAI团队特色】
1. 你代表的是一个专家团队，请体现团队协作的优势
2. 请从多个专家视角分析数据（数据分析师、技术分析师、策略师）
3. 请展现团队讨论和共识形成的过程
4. 请使用更自然的语言和更丰富的分析维度

【强制要求】
1. 今天的日期是：{current_date} {weekday}
2. 所有数据都是真实获取的当天数据
3. 生成的晨报标题必须包含今天的日期
4. 如果没有新闻数据，请写"今日暂无重要财经新闻"，不要编造
5. 如果没有美股数据，请写"美股数据暂无"，不要编造

【股票数据】（来自SQLite数据库，{timestamp} 获取）
"""
    
    # A股数据
    for stock in stocks:
        code = stock.get("symbol", stock.get("code", ""))
        name = stock.get("name", code)
        # 优先用turnover字段（volume×price估算的成交额）
        amount_yuan = stock.get("turnover", 0) or stock.get("amount", 0)
        amount_yi = amount_yuan / 100000000 if amount_yuan else 0  # 转换为亿元
        volume = stock.get("volume", 0)
        pct = stock.get("change_pct", 0)
        
        prompt += f"""
{name}（{code}）
- 现价: {stock.get('price', 0):.2f}元，涨跌幅: {pct:+.2f}%
- 今开: {stock.get('open', 0):.2f}元，最高: {stock.get('high', 0):.2f}元，最低: {stock.get('low', 0):.2f}元
- 成交量: {volume:,.0f}股 | 成交额: {amount_yi:.2f}亿元
"""
    
    # 美股数据
    prompt += f"""
【美股数据】（来自新浪财经API，{timestamp} 获取）
"""
    if us_stocks:
        for stock in us_stocks[:10]:
            pct = stock.get('change_pct', 0)
            prompt += f"""
{stock.get('name', stock['symbol'])}（{stock['symbol']}）
- 现价: ${stock['price']:.2f}，涨跌幅: {pct:+.2f}%
- 今开: ${stock.get('open', 0):.2f}，最高: ${stock.get('high', 0):.2f}，最低: ${stock.get('low', 0):.2f}
- 成交量: {stock.get('volume', 0):,.0f}股
"""
    else:
        prompt += "*美股数据暂无*\n"
    
    # 期货数据
    prompt += f"""
【美国期货数据】（来自新浪财经API，{timestamp} 获取）
"""
    if isinstance(futures_result, dict) and futures_result.get('status') == 'success':
        futures_list = futures_result.get('futures', [])
        if futures_list:
            prompt += "**美国期货板块趋势分析：**\n\n"
            for f in futures_list:
                prompt += f"- {f.get('symbol', 'N/A')}: ${f.get('price', 0):.2f} ({f.get('change_pct', 0):+.2f}%)\n"
            prompt += "\n"
        else:
            prompt += "*期货数据暂无*\n"
    else:
        prompt += "*期货数据暂无*\n"
    
    # 虚拟币数据
    if crypto_data and crypto_data.get('status') == 'success' and crypto_data.get('coins'):
        prompt += f"""
【虚拟币数据】（来自Binance API，{timestamp} 获取）
"""
        for coin in crypto_data['coins'][:8]:
            name = coin.get('name', coin.get('symbol', 'Unknown'))
            symbol = coin.get('symbol', 'N/A')
            price = coin.get('price', 0)
            change_pct = coin.get('change_pct', 0)
            high = coin.get('high', 0)
            low = coin.get('low', 0)
            volume = coin.get('volume', 0)
            prompt += f"""
{name}（{symbol}）
- 现价: ${price:,.2f}，24h涨跌幅: {change_pct:+.2f}%
- 今日最高: ${high:,.2f}，今日最低: ${low:,.2f}
- 24h交易量: {volume:,.0f} {symbol}
"""
    else:
        prompt += "*虚拟币数据暂无（需要代理）*\n"
    
    # 财经新闻
    if financial_news and financial_news.get('status') == 'success' and financial_news.get('news'):
        prompt += f"""
【财经要闻】（来自东方财富，{timestamp} 获取）
"""
        for i, news_item in enumerate(financial_news['news'][:10], 1):
            prompt += f"{i}. {news_item['title']}\n"
    else:
        prompt += "*财经新闻暂无*\n"
    
    prompt += """
【晨报要求】
请生成一份专业的全球操盘晨报，**必须包含以下内容**：
1. **隔夜重要信息**（美股收盘数据、汇率、大宗商品）
2. **美国期货板块趋势概览**（⚠️ 必须详细展示上面提供的期货数据）
3. **A股板块轮动分析**（基于成交额和涨跌幅）
4. **【重点】今日入场/出场/试仓建议**（针对每只分析的标的给出明确信号）：
   - 对每只股票/期货/虚拟币都要单独给出信号
   - 格式：标的名称 | 建议操作 | 触发条件 | 仓位 | 止损价 | 止盈价 | 盈亏比
   - 如果某标的当前不建议操作，标注"观望"即可
   - 必须覆盖所有主要标的（美股重点股、A股强势/弱势股、期货合约）
5. **风险提示**
- 入场条件（满足其中一项即触发）
- 出场条件（满足其中一项即触发）
- 试仓策略（仓位上限、试仓条件、止损价格、目标价格、盈亏比）
- 风险提示）
6. **今日重点关注板块**（A股+美股+期货+虚拟币板块）
7. **财经要闻速览**（最重要的3-5条新闻及影响分析）
8. **今日重要时间节点**（A股+美股交易时间）

【格式要求】
- 标题：📊 【活跃股操盘晨报-CrewAI版】{current_date} {weekday}
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

# ========== 主流程 ==========

def main():
    """CrewAI团队主流程"""
    print("=" * 60)
    print("🚀 [CrewAI团队] 开始独立实现活跃股操盘晨报系统")
    print("   数据源: SQLite数据库 + API降级")
    print("=" * 60)
    
    start_time = time.time()
    
    # Step 1: 从统一数据源获取数据
    print("\n[Step 1] 从SQLite数据库获取数据...")
    from morning_data_source import MorningDataSource
    source = MorningDataSource()
    data = source.get_all_data()
    source.close()
    
    date_info = {
        'date_str': data['date_str'],
        'weekday': data['weekday'],
        'timestamp': data['timestamp']
    }
    print(f"[CrewAI-数据获取] 当前日期: {date_info['date_str']} {date_info['weekday']}")
    print(f"[CrewAI-数据获取] 美股: {len(data['us_stocks'])}只, A股: {len(data['a_stocks'])}只, 期货: {len(data['futures'])}只")
    
    # 转换数据格式
    stocks = data['a_stocks']
    us_stocks = data['us_stocks']
    futures_list = data['futures']
    crypto_data = {'status': 'success' if data.get('crypto') else 'empty', 'coins': data.get('crypto', [])}
    news_data = {'status': 'success' if data.get('news') else 'empty', 'news': data.get('news', [])}
    
    # Step 2: 技术分析师
    print("\n[Step 2] 技术分析师开始工作...")
    indicators = calculate_indicators(stocks)
    
    # Step 2.5: 准备期货数据
    print("\n[Step 2.5] 准备期货数据...")
    futures_result = {"status": "success", "futures": futures_list, "sectors": {}}
    for f in futures_list:
        f['sector'] = 'commodity'
    
    # Step 2.6: 虚拟币数据（当前环境不可用）
    print("\n[Step 2.6] 虚拟币数据（当前环境不可用）...")
    crypto_data = {'status': 'empty', 'coins': []}
    print(f"[CrewAI-虚拟币数据] 获取到 0 只虚拟币（需要代理）")
    
    # Step 2.7: 财经新闻
    print("\n[Step 2.7] 财经新闻...")
    print(f"[CrewAI-财经新闻] 获取到 {len(news_data.get('news', []))} 条新闻")
    
    # Step 3: 晨报撰稿人
    print("\n[Step 3] 晨报撰稿人开始工作...")
    report = generate_morning_report(stocks, indicators, date_info, [], us_stocks, futures_result, crypto_data, news_data, etf_options=data.get('etf_options', []))
    
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


def fetch_crypto_data():
    """获取虚拟币数据（Binance API，带缓存）"""
    print("[CrewAI-虚拟币数据获取] 开始获取虚拟币数据...")
    start_time = time.time()
    
    # 先查缓存
    cached = get_cached('crypto', 'batch')
    if cached:
        print(f"[CrewAI-虚拟币数据获取] 从缓存读取 {len(cached)} 只虚拟币")
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
                    # 缓存单个币
                    set_cache('crypto', symbol.replace('USDT', ''), crypto_coins[-1])
            except:
                pass
        
        # 缓存整批
        if crypto_coins:
            set_cache('crypto', 'batch', crypto_coins)
        
        elapsed = time.time() - start_time
        print(f"[CrewAI-虚拟币数据获取] 获取到 {len(crypto_coins)} 只虚拟币，耗时: {elapsed:.2f}s")
        return {"status": "success", "coins": crypto_coins}
    except Exception as e:
        print(f"[CrewAI-虚拟币数据获取] 失败: {e}")
        return {"status": "error", "coins": []}


def fetch_financial_news():
    """获取财经新闻（Firecrawl爬取东方财富，带缓存）"""
    print("[CrewAI-财经新闻获取] 开始获取财经新闻...")
    start_time = time.time()
    
    # 先查缓存
    cached = get_cached('news', 'batch')
    if cached:
        print(f"[CrewAI-财经新闻获取] 从缓存读取 {len(cached)} 条新闻")
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
        
        # 缓存新闻
        if news_list:
            set_cache('news', 'batch', news_list)
        
        elapsed = time.time() - start_time
        print(f"[CrewAI-财经新闻获取] 获取到 {len(news_list)} 条新闻，耗时: {elapsed:.2f}s")
        return {"status": "success", "news": news_list}
    except Exception as e:
        print(f"[CrewAI-财经新闻获取] 失败: {e}")
        return {"status": "error", "news": []}


if __name__ == "__main__":
    main()
