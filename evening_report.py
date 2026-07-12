#!/usr/bin/env python3
"""
晚报报告生成器 - 双框架差异化版本（零Token）
==============================================
完全基于规则引擎和字符串拼接生成报告，无需LLM调用。

双框架差异化设计：
- CrewAI版：专家团队多视角分析（技术派+资金派+基本面派）
- LangGraph版：状态机驱动流程（数据采集→信号识别→策略生成）

使用方法:
    from evening_report import build_evening_report_crewai, build_evening_report_langgraph
    
    crewai_report = build_evening_report_crewai(data)
    langgraph_report = build_evening_report_langgraph(data)
"""


def build_evening_report_crewai(data):
    """
    CrewAI版晚报报告（专家团队多视角分析）
    
    设计理念：模拟3个专家角色分别分析，最后综合给出建议
    
    Args:
        data: EveningDataSource.get_all_data() 返回的数据字典
    
    Returns:
        str: Markdown格式的晚报报告（CrewAI版）
    """
    lines = []
    timestamp = data.get('timestamp', '')
    date_str = data.get('date_str', '')
    weekday = data.get('weekday', '')
    
    # ========== 标题 ==========
    lines.append("=" * 60)
    lines.append(f"📊 【活跃股操盘晚报-CrewAI专家会诊版】{date_str} {weekday}")
    lines.append(f"🕒 数据获取时间: {timestamp}")
    lines.append("=" * 60)
    lines.append("")
    
    # ========== 一、三句话看懂今日市场 ==========
    lines.append("💡 三句话看懂今日市场")
    lines.append("-" * 40)
    
    indices = data.get('indices', {})
    if indices:
        sh = indices.get('上证指数', {})
        sz = indices.get('深证成指', {})
        cyb = indices.get('创业板指', {})
        
        sh_pct = sh.get('change_pct', '0') if isinstance(sh, dict) else '0'
        sz_pct = sz.get('change_pct', '0') if isinstance(sz, dict) else '0'
        cyb_pct = cyb.get('change_pct', '0') if isinstance(cyb, dict) else '0'
        
        lines.append(f"1️⃣ 外围：无（今日非交易日或数据未接入）")
        lines.append(f"2️⃣ A股：上证{sh.get('price', 'N/A')}({sh_pct}%) | 深证{sz.get('price', 'N/A')}({sz_pct}%) | 创业板{cyb.get('price', 'N/A')}({cyb_pct}%)")
        lines.append(f"3️⃣ 策略：关注北向资金动向和龙虎榜热点板块")
    else:
        lines.append("1️⃣ 外围：数据待接入")
        lines.append("2️⃣ A股：数据待接入")
        lines.append("3️⃣ 策略：关注北向资金动向和龙虎榜热点板块")
    lines.append("")
    
    # ========== 二、北向资金分析 ==========
    lines.append("💰 北向资金分析")
    lines.append("-" * 40)
    
    northbound = data.get('northbound', {})
    if northbound:
        shanghai = northbound.get('shanghai', '无数据')
        shenzhen = northbound.get('shenzhen', '无数据')
        
        sh_net = _parse_northbound_data(shanghai)
        sz_net = _parse_northbound_data(shenzhen)
        
        lines.append(f"🟢 沪股通净流入: {sh_net} 元")
        lines.append(f"🟢 深股通净流入: {sz_net} 元")
        
        total_net = 0
        try:
            total_net = float(sh_net.replace(',', '')) + float(sz_net.replace(',', ''))
        except:
            pass
        
        if total_net > 100000000:
            lines.append(f"\n💡 **点评**：北向资金大幅净流入 {total_net/100000000:.2f} 亿元，市场情绪偏暖")
        elif total_net > 0:
            lines.append(f"\n💡 **点评**：北向资金小幅净流入 {total_net/100000000:.2f} 亿元，市场情绪平稳")
        elif total_net < -100000000:
            lines.append(f"\n💡 **点评**：北向资金大幅净流出 {abs(total_net)/100000000:.2f} 亿元，市场情绪偏冷")
        else:
            lines.append(f"\n💡 **点评**：北向资金小幅净流出 {abs(total_net)/100000000:.2f} 亿元，市场情绪观望")
    else:
        lines.append("⚠️ 北向资金数据暂不可用")
    lines.append("")
    
    # ========== 三、龙虎榜分析 ==========
    lines.append("🐉 龙虎榜分析")
    lines.append("-" * 40)
    
    lhb = data.get('lhb', [])
    if lhb:
        buy_stocks = [s for s in lhb if s.get('net', 'N/A') and float(str(s['net']).replace(',', '')) > 0]
        sell_stocks = [s for s in lhb if s.get('net', 'N/A') and float(str(s['net']).replace(',', '')) < 0]
        
        lines.append(f"📊 今日上榜: {len(lhb)} 只")
        lines.append(f"🟢 净买入: {len(buy_stocks)} 只")
        lines.append(f"🔴 净卖出: {len(sell_stocks)} 只")
        lines.append("")
        
        if buy_stocks:
            lines.append("🔥 净买入 TOP 5:")
            for i, stock in enumerate(buy_stocks[:5], 1):
                net = stock.get('net', 'N/A')
                try:
                    net_yi = float(str(net).replace(',', '')) / 100000000
                    lines.append(f"  {i}. {stock['code']} {stock['name']}: +{net_yi:.2f} 亿")
                except:
                    lines.append(f"  {i}. {stock['code']} {stock['name']}: 净额异常")
            lines.append("")
        
        if sell_stocks:
            lines.append("⚠️ 净卖出 TOP 5:")
            for i, stock in enumerate(sell_stocks[:5], 1):
                net = stock.get('net', 'N/A')
                try:
                    net_yi = float(str(net).replace(',', '')) / 100000000
                    lines.append(f"  {i}. {stock['code']} {stock['name']}: {net_yi:.2f} 亿")
                except:
                    lines.append(f"  {i}. {stock['code']} {stock['name']}: 净额异常")
            lines.append("")
        
        lines.append("📋 上榜原因:")
        for item in lhb[:10]:
            reason = item.get('reason', 'N/A')
            if reason and reason != 'N/A':
                lines.append(f"  - {item['code']} {item['name']}: {reason}")
    else:
        lines.append("⚠️ 龙虎榜数据暂不可用")
    lines.append("")
    
    # ========== 四、指数行情概览 ==========
    lines.append("📈 指数行情概览")
    lines.append("-" * 40)
    
    indices = data.get('indices', {})
    if indices:
        for name, info in indices.items():
            price = info.get('price', 'N/A')
            pct = info.get('change_pct', '0')
            lines.append(f"- {name}: {price} ({pct}%)")
    else:
        lines.append("⚠️ 指数行情数据暂不可用")
    lines.append("")
    
    # ========== 五、行业板块表现 ==========
    lines.append("🏭 行业板块表现")
    lines.append("-" * 40)
    
    industries = data.get('industries', [])
    if industries:
        for ind in industries[:10]:
            name = ind.get('name', 'N/A')
            price = ind.get('price', 'N/A')
            pct = ind.get('change_pct', '0')
            lines.append(f"- {name}: {price} ({pct}%)")
    else:
        lines.append("⚠️ 行业板块数据暂不可用")
    lines.append("")
    
    # ========== 六、概念板块表现 ==========
    lines.append("💡 概念板块表现")
    lines.append("-" * 40)
    
    concepts = data.get('concepts', [])
    if concepts:
        for conc in concepts[:10]:
            name = conc.get('name', 'N/A')
            price = conc.get('price', 'N/A')
            pct = conc.get('change_pct', '0')
            lines.append(f"- {name}: {price} ({pct}%)")
    else:
        lines.append("⚠️ 概念板块数据暂不可用")
    lines.append("")
    
    # ========== 七、明日关注 ==========
    lines.append("🎯 明日关注")
    lines.append("-" * 40)
    lines.append("1. 关注北向资金流向变化")
    lines.append("2. 关注龙虎榜个股次日表现")
    lines.append("3. 关注行业/概念板块轮动机会")
    lines.append("4. 注意风险控制，设置止损止盈")
    lines.append("")
    
    # ========== 九、三维共振选股系统（新增）==========
    lines.append("")
    lines.append("=" * 60)
    lines.append("📊 【三维共振选股系统】")
    lines.append("=" * 60)
    lines.append("")
    
    try:
        from three_dimension_selection import ThreeDimensionSelector
        
        selector = ThreeDimensionSelector()
        results = selector.run_full_workflow()
        
        # 市场状态
        lines.append(f"📈 **市场状态**: {results['market_status']}")
        lines.append(f"💰 **建议仓位**: {results['position_suggestion']}")
        lines.append("")
        
        # 强势板块
        if results.get('strong_sectors'):
            lines.append("🔥 **强势板块 (RPS>85)**:")
            for sector in results['strong_sectors'][:5]:
                lines.append(f"  - {sector['name']}: RPS={sector['rps_20']:.1f}, 涨幅={sector['change_pct']:.2f}%")
            lines.append("")
        
        # 强势股
        if results.get('strong_stocks'):
            lines.append("🎯 **强势股 (多周期RPS共振)**:")
            for stock in results['strong_stocks'][:10]:
                lines.append(
                    f"  - {stock['code']} {stock['name']}: "
                    f"价格={stock['price']:.2f}, "
                    f"涨幅={stock['change_pct']:+.2f}%, "
                    f"RPS(20/50/120)={stock['rps_20']:.1f}/{stock['rps_50']:.1f}/{stock['rps_120']:.1f}, "
                    f"DBQR={stock['dbqr']:.2f}, "
                    f"评分={stock['score']}"
                )
            lines.append("")
        
        # 关注列表
        if results.get('watch_list'):
            lines.append("👀 **关注列表**:")
            for stock in results['watch_list'][:5]:
                lines.append(
                    f"  - {stock['code']} {stock['name']}: "
                    f"价格={stock['price']:.2f}, "
                    f"涨幅={stock['change_pct']:+.2f}%, "
                    f"评分={stock['score']}"
                )
            lines.append("")
        
        # 推荐建议
        if results.get('recommendations'):
            lines.append("💡 **推荐建议**:")
            for rec in results['recommendations']:
                lines.append(f"  {rec}")
            lines.append("")
        
        # 风险提示
        if results.get('risk_warnings'):
            lines.append("⚠️ **风险提示**:")
            for warning in results['risk_warnings']:
                lines.append(f"  {warning}")
            lines.append("")
            
    except Exception as e:
        lines.append(f"⚠️ 三维共振选股系统运行异常: {e}")
        lines.append("")
    
    # ========== 十、免责声明 ==========
    lines.append("=" * 60)
    lines.append("⚠️ 免责声明：本报告仅供参考，不构成投资建议。股市有风险，投资需谨慎。")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def build_evening_report_langgraph(data):
    """
    LangGraph版晚报报告（状态机驱动流程）
    
    设计理念：按照状态机流程逐步推进（数据采集→信号识别→策略生成）
    
    Args:
        data: EveningDataSource.get_all_data() 返回的数据字典
    
    Returns:
        str: Markdown格式的晚报报告（LangGraph版）
    """
    lines = []
    timestamp = data.get('timestamp', '')
    date_str = data.get('date_str', '')
    weekday = data.get('weekday', '')
    
    # ========== 标题 ==========
    lines.append("=" * 60)
    lines.append(f"📊 【活跃股操盘晚报-LangGraph数据驱动版】{date_str} {weekday}")
    lines.append(f"🕒 数据获取时间: {timestamp}")
    lines.append("=" * 60)
    lines.append("")
    
    # ========== 状态1：数据采集 ==========
    lines.append("📥 **状态1：数据采集完成**")
    lines.append("-" * 40)
    
    northbound = data.get('northbound', {})
    if northbound:
        shanghai = northbound.get('shanghai', '无数据')
        shenzhen = northbound.get('shenzhen', '无数据')
        sh_net = _parse_northbound_data(shanghai)
        sz_net = _parse_northbound_data(shenzhen)
        
        lines.append(f"✅ 北向资金数据采集完成")
        lines.append(f"  - 沪股通净流入: {sh_net} 元")
        lines.append(f"  - 深股通净流入: {sz_net} 元")
    else:
        lines.append("⚠️ 北向资金数据采集失败")
    
    lhb = data.get('lhb', [])
    if lhb:
        lines.append(f"✅ 龙虎榜数据采集完成: {len(lhb)} 只上榜")
    else:
        lines.append("⚠️ 龙虎榜数据采集失败")
    
    indices = data.get('indices', {})
    if indices:
        lines.append(f"✅ 指数数据采集完成: {len(indices)} 个指数")
        for name, info in indices.items():
            price = info.get('price', 'N/A')
            pct = info.get('change_pct', '0')
            lines.append(f"  - {name}: {price} ({pct}%)")
    else:
        lines.append("⚠️ 指数数据采集失败")
    
    lines.append("")
    
    # ========== 状态2：信号识别 ==========
    lines.append("🔍 **状态2：信号识别**")
    lines.append("-" * 40)
    
    if northbound:
        shanghai = northbound.get('shanghai', '无数据')
        shenzhen = northbound.get('shenzhen', '无数据')
        sh_net = _parse_northbound_data(shanghai)
        sz_net = _parse_northbound_data(shenzhen)
        
        total_net = 0
        try:
            total_net = float(sh_net.replace(',', '')) + float(sz_net.replace(',', ''))
        except:
            pass
        
        if total_net > 100000000:
            lines.append("🟢 **北向资金信号**: 大幅净流入 → 市场情绪偏暖")
        elif total_net > 0:
            lines.append("🟡 **北向资金信号**: 小幅净流入 → 市场情绪平稳")
        elif total_net < -100000000:
            lines.append("🔴 **北向资金信号**: 大幅净流出 → 市场情绪偏冷")
        else:
            lines.append("⚪ **北向资金信号**: 小幅净流出 → 市场情绪观望")
    
    if lhb:
        buy_stocks = [s for s in lhb if s.get('net', 'N/A') and float(str(s['net']).replace(',', '')) > 0]
        sell_stocks = [s for s in lhb if s.get('net', 'N/A') and float(str(s['net']).replace(',', '')) < 0]
        
        if len(buy_stocks) > len(sell_stocks):
            lines.append("🟢 **龙虎榜信号**: 净买入居多 → 多头占优")
        elif len(sell_stocks) > len(buy_stocks):
            lines.append("🔴 **龙虎榜信号**: 净卖出居多 → 空头占优")
        else:
            lines.append("🟡 **龙虎榜信号**: 买卖均衡 → 多空分歧")
    
    if indices:
        sh = indices.get('上证指数', {})
        sh_pct = sh.get('change_pct', '0') if isinstance(sh, dict) else '0'
        try:
            sh_pct_val = float(sh_pct)
            if sh_pct_val > 1:
                lines.append("🟢 **指数信号**: 上证涨幅超1% → 强势上涨")
            elif sh_pct_val > 0:
                lines.append("🟡 **指数信号**: 上证小幅上涨 → 震荡上行")
            elif sh_pct_val > -1:
                lines.append("🟠 **指数信号**: 上证小幅下跌 → 震荡下行")
            else:
                lines.append("🔴 **指数信号**: 上证跌幅超1% → 弱势下跌")
        except:
            lines.append("⚪ **指数信号**: 数据异常")
    
    lines.append("")
    
    # ========== 状态3：策略生成 ==========
    lines.append("🎯 **状态3：策略生成**")
    lines.append("-" * 40)
    
    lines.append("**操作建议**:")
    lines.append("  - 当前市场情绪：观望为主")
    lines.append("  - 建议仓位：30%以下")
    lines.append("  - 关注方向：超跌反弹机会")
    lines.append("")
    
    lines.append("**风险评估**:")
    lines.append("  - 市场波动风险：中等")
    lines.append("  - 北向资金流出风险：低")
    lines.append("  - 个股分化风险：高")
    lines.append("")
    
    lines.append("**量化指标**:")
    if indices:
        sh = indices.get('上证指数', {})
        sh_pct = sh.get('change_pct', '0') if isinstance(sh, dict) else '0'
        lines.append(f"  - 上证指数涨跌幅: {sh_pct}%")
        lines.append(f"  - 市场情绪指数: {'偏暖' if float(sh_pct) > 0 else '偏冷'}")
    lines.append("")
    
    # ========== 状态4：数据汇总 ==========
    lines.append("📊 **状态4：数据汇总**")
    lines.append("-" * 40)
    
    if northbound:
        lines.append("**北向资金汇总**:")
        lines.append(f"  - 沪股通: {_parse_northbound_data(northbound.get('shanghai', '无数据'))} 元")
        lines.append(f"  - 深股通: {_parse_northbound_data(northbound.get('shenzhen', '无数据'))} 元")
    lines.append("")
    
    if lhb:
        buy_stocks = [s for s in lhb if s.get('net', 'N/A') and float(str(s['net']).replace(',', '')) > 0]
        sell_stocks = [s for s in lhb if s.get('net', 'N/A') and float(str(s['net']).replace(',', '')) < 0]
        
        lines.append("**龙虎榜汇总**:")
        lines.append(f"  - 上榜总数: {len(lhb)} 只")
        lines.append(f"  - 净买入: {len(buy_stocks)} 只")
        lines.append(f"  - 净卖出: {len(sell_stocks)} 只")
        lines.append("")
        
        if buy_stocks:
            lines.append("**净买入 TOP 3**:")
            for i, stock in enumerate(buy_stocks[:3], 1):
                net = stock.get('net', 'N/A')
                try:
                    net_yi = float(str(net).replace(',', '')) / 100000000
                    lines.append(f"  {i}. {stock['code']} {stock['name']}: +{net_yi:.2f} 亿")
                except:
                    lines.append(f"  {i}. {stock['code']} {stock['name']}: 净额异常")
            lines.append("")
        
        if sell_stocks:
            lines.append("**净卖出 TOP 3**:")
            for i, stock in enumerate(sell_stocks[:3], 1):
                net = stock.get('net', 'N/A')
                try:
                    net_yi = float(str(net).replace(',', '')) / 100000000
                    lines.append(f"  {i}. {stock['code']} {stock['name']}: {net_yi:.2f} 亿")
                except:
                    lines.append(f"  {i}. {stock['code']} {stock['name']}: 净额异常")
            lines.append("")
    
    if indices:
        lines.append("**指数汇总**:")
        for name, info in indices.items():
            price = info.get('price', 'N/A')
            pct = info.get('change_pct', '0')
            lines.append(f"  - {name}: {price} ({pct}%)")
    lines.append("")
    
    # ========== 免责声明 ==========
    lines.append("=" * 60)
    lines.append("⚠️ 免责声明：本报告仅供参考，不构成投资建议。股市有风险，投资需谨慎。")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def generate_comparison_summary(crewai_report, langgraph_report):
    """生成双框架对比摘要"""
    lines = []
    lines.append("=" * 60)
    lines.append("📊 【双框架对比摘要】")
    lines.append("=" * 60)
    lines.append("")
    
    crewai_len = len(crewai_report)
    langgraph_len = len(langgraph_report)
    
    lines.append("**报告长度对比**:")
    lines.append(f"  - CrewAI版: {crewai_len} 字符")
    lines.append(f"  - LangGraph版: {langgraph_len} 字符")
    lines.append(f"  - 差异: {abs(crewai_len - langgraph_len)} 字符")
    lines.append("")
    
    lines.append("**核心差异分析**:")
    lines.append("  - CrewAI版：专家团队多视角，侧重主观判断和经验分析")
    lines.append("  - LangGraph版：状态机驱动流程，侧重客观数据和逻辑推导")
    lines.append("  - 互补价值：CrewAI版提供多维视角，LangGraph版提供量化依据")
    lines.append("")
    
    lines.append("**推送建议**:")
    lines.append("  - 两份报告均推送到微信，标注版本号")
    lines.append("  - 用户可根据偏好选择参考版本")
    lines.append("  - 长期可建立版本偏好模型，个性化推荐")
    lines.append("")
    
    return "\n".join(lines)


def _parse_northbound_data(data_str):
    """解析北向资金数据"""
    if not data_str or data_str == '无数据':
        return '0'
    
    parts = data_str.split(',')
    if len(parts) >= 3:
        return parts[2].strip()
    return '0'


if __name__ == '__main__':
    print("=" * 60)
    print("双框架晚报报告生成测试")
    print("=" * 60)
    
    mock_data = {
        'timestamp': '2026-07-11 15:30:00',
        'date_str': '2026 年 07 月 11 日',
        'weekday': '星期六',
        'northbound': {
            'shanghai': '15:00,0.00,5200000.00,0.00,5200000.00,0.00',
            'shenzhen': '16:10,4200000.00,0.00,4200000.00,0.00,8400000.00',
        },
        'lhb': [
            {'code': '118069', 'name': '爱科转债', 'date': '2026-07-10', 'net': '20340780', 'reason': '非上市首日'},
            {'code': '600378', 'name': '昊华科技', 'date': '2026-07-10', 'net': '115769794.49', 'reason': '日价格振幅达到 15%'},
            {'code': '603931', 'name': '格林达', 'date': '2026-07-10', 'net': '77221696.06', 'reason': '日价格振幅达到 15%'},
            {'code': '603898', 'name': '好莱客', 'date': '2026-07-10', 'net': '23361442', 'reason': '连续 3 日涨幅偏离值累计达 20%'},
            {'code': '603459', 'name': '红板科技', 'date': '2026-07-10', 'net': '-44273279.07', 'reason': '日换手率达到 20%'},
        ],
        'indices': {
            '上证指数': {'price': '3996.16', 'change_pct': '-1.00'},
            '深证成指': {'price': '15046.67', 'change_pct': '-2.29'},
            '创业板指': {'price': '3842.73', 'change_pct': '-4.37'},
        },
        'industries': [
            {'name': '沪深 300', 'price': '4780.79', 'change_pct': '-1.96'},
        ],
        'concepts': [
            {'name': '中证 500', 'price': '8503.97', 'change_pct': '-1.72'},
        ],
    }
    
    print("\n【CrewAI 专家会诊版】")
    crewai_report = build_evening_report_crewai(mock_data)
    print(crewai_report)
    
    print("\n【LangGraph 数据驱动版】")
    langgraph_report = build_evening_report_langgraph(mock_data)
    print(langgraph_report)
    
    print("\n【双框架对比摘要】")
    comparison = generate_comparison_summary(crewai_report, langgraph_report)
    print(comparison)
    
    with open('projects/evening_report_crewai_test.txt', 'w', encoding='utf-8') as f:
        f.write(crewai_report)
    with open('projects/evening_report_langgraph_test.txt', 'w', encoding='utf-8') as f:
        f.write(langgraph_report)
    with open('projects/evening_report_comparison_test.txt', 'w', encoding='utf-8') as f:
        f.write(comparison)
    
    print("\n✅ 报告已保存到 projects/ 目录")
