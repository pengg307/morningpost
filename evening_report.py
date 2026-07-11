#!/usr/bin/env python3
"""
晚报报告生成器 - 模板模式（零Token）
================================
完全基于规则引擎和字符串拼接生成报告，无需LLM调用。

使用方法:
    from evening_report import build_evening_report
    
    report = build_evening_report(data)
    print(report)
"""


def build_evening_report(data):
    """
    生成晚报报告（零Token模板模式）
    
    Args:
        data: EveningDataSource.get_all_data() 返回的数据字典
    
    Returns:
        str: Markdown格式的晚报报告
    """
    lines = []
    timestamp = data.get('timestamp', '')
    date_str = data.get('date_str', '')
    weekday = data.get('weekday', '')
    
    # ========== 标题 ==========
    lines.append("=" * 60)
    lines.append(f"📊 【活跃股操盘晚报】{date_str} {weekday}")
    lines.append(f"🕒 数据获取时间: {timestamp}")
    lines.append("=" * 60)
    lines.append("")
    
    # ========== 一、三句话看懂今日市场 ==========
    lines.append("💡 三句话看懂今日市场")
    lines.append("-" * 40)
    
    # 从指数数据提取一句话
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
        
        # 解析净流入数据
        sh_net = _parse_northbound_data(shanghai)
        sz_net = _parse_northbound_data(shenzhen)
        
        lines.append(f"🟢 沪股通净流入: {sh_net} 元")
        lines.append(f"🟢 深股通净流入: {sz_net} 元")
        
        total_net = 0
        try:
            total_net = float(sh_net.replace(',', '')) + float(sz_net.replace(',', ''))
        except:
            pass
        
        if total_net > 100000000:  # 大于 1 亿
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
        # 统计买入/卖出净额
        buy_stocks = [s for s in lhb if s.get('net', 'N/A') and float(str(s['net']).replace(',', '')) > 0]
        sell_stocks = [s for s in lhb if s.get('net', 'N/A') and float(str(s['net']).replace(',', '')) < 0]
        
        lines.append(f"📊 今日上榜: {len(lhb)} 只")
        lines.append(f"🟢 净买入: {len(buy_stocks)} 只")
        lines.append(f"🔴 净卖出: {len(sell_stocks)} 只")
        lines.append("")
        
        # 展示前 5 大净买入
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
        
        # 展示前 5 大净卖出
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
        
        # 展示上榜原因
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
    
    # ========== 八、免责声明 ==========
    lines.append("=" * 60)
    lines.append("⚠️ 免责声明：本报告仅供参考，不构成投资建议。股市有风险，投资需谨慎。")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def _parse_northbound_data(data_str):
    """
    解析北向资金数据
    
    格式: "时间，状态，净流入，..."
    返回净流入数值（元）
    """
    if not data_str or data_str == '无数据':
        return '0'
    
    parts = data_str.split(',')
    if len(parts) >= 3:
        # 第 3 个字段是净流入（单位：元）
        return parts[2].strip()
    return '0'


if __name__ == '__main__':
    # 测试晚报报告生成
    print("=" * 60)
    print("晚报报告生成测试")
    print("=" * 60)
    
    # 模拟数据
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
    
    report = build_evening_report(mock_data)
    print(report)
    
    # 保存到文件
    with open('projects/evening_report_test.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    print("\n✅ 报告已保存到 projects/evening_report_test.txt")
