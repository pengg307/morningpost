#!/usr/bin/env python3
"""
个股尽调报告生成器 - Phase 3（零 Token）
================================
完全基于规则引擎和字符串拼接生成报告，无需 LLM 调用。

使用方法:
    from stock_dossier_report import build_stock_dossier_report
    
    report = build_stock_dossier_report(data)
    print(report)
"""


def build_stock_dossier_report(data):
    """
    生成个股尽调报告（零 Token 模板模式）
    
    Args:
        data: StockDossierSource.get_all_data() 返回的数据字典
    
    Returns:
        str: Markdown 格式的个股尽调报告
    """
    lines = []
    timestamp = data.get('timestamp', '')
    date_str = data.get('date_str', '')
    weekday = data.get('weekday', '')
    stocks = data.get('stocks', [])
    
    # ========== 标题 ==========
    lines.append("=" * 60)
    lines.append(f"📊 【A 股个股尽调报告】{date_str} {weekday}")
    lines.append(f"🕒 数据获取时间: {timestamp}")
    lines.append("=" * 60)
    lines.append("")
    
    # ========== 一、三句话看懂市场 ==========
    lines.append("💡 三句话看懂今日 A 股")
    lines.append("-" * 40)
    
    if stocks:
        up_count = sum(1 for s in stocks if s.get('change_pct', 0) > 0)
        down_count = sum(1 for s in stocks if s.get('change_pct', 0) < 0)
        
        lines.append(f"1️⃣ 今日关注: {len(stocks)} 只重点股票，{up_count} 涨 {down_count} 跌")
        
        # 找出涨跌幅最大的股票
        max_up = max(stocks, key=lambda x: x.get('change_pct', 0)) if up_count > 0 else None
        max_down = min(stocks, key=lambda x: x.get('change_pct', 0)) if down_count > 0 else None
        
        if max_up:
            lines.append(f"2️⃣ 领涨股: {max_up['name']} (+{max_up['change_pct']:.2f}%)")
        if max_down:
            lines.append(f"3️⃣ 领跌股: {max_down['name']} ({max_down['change_pct']:.2f}%)")
    else:
        lines.append("1️⃣ 今日关注: 无数据")
        lines.append("2️⃣ 领涨股: 暂无")
        lines.append("3️⃣ 领跌股: 暂无")
    lines.append("")
    
    # ========== 二、个股详细分析 ==========
    lines.append("📈 个股详细分析")
    lines.append("-" * 40)
    
    if stocks:
        for i, stock in enumerate(stocks, 1):
            name = stock.get('name', '')
            code = stock.get('code', '')
            price = stock.get('price', 0)
            change_pct = stock.get('change_pct', 0)
            pe = stock.get('pe', 0)
            pb = stock.get('pb', 0)
            total_market_cap = stock.get('total_market_cap', 0)
            turnover_rate = stock.get('turnover_rate', 0)
            
            # 格式化总市值
            if total_market_cap >= 1e8:
                market_cap_str = f"{total_market_cap/1e8:.2f}亿"
            elif total_market_cap >= 1e4:
                market_cap_str = f"{total_market_cap/1e4:.2f}万"
            else:
                market_cap_str = f"{total_market_cap}"
            
            lines.append(f"**{i}. {name} ({code})**")
            lines.append(f"- 最新价: {price}")
            lines.append(f"- 涨跌幅: {change_pct:+.2f}%")
            lines.append(f"- PE: {pe:.2f} | PB: {pb:.2f}")
            lines.append(f"- 总市值: {market_cap_str}")
            lines.append(f"- 换手率: {turnover_rate:.2f}%")
            
            # 根据估值给出点评
            if pe > 50:
                lines.append(f"- 💡 **估值**: 偏高，注意回调风险")
            elif pe < 10:
                lines.append(f"- 💡 **估值**: 偏低，可能有价值投资机会")
            else:
                lines.append(f"- 💡 **估值**: 合理区间")
            
            # 根据涨跌幅给出建议
            if change_pct > 3:
                lines.append(f"- 🎯 **操作建议**: 强势上涨，可考虑追高或持有")
            elif change_pct < -3:
                lines.append(f"- 🎯 **操作建议**: 大幅下跌，注意风险，观望为主")
            elif abs(change_pct) <= 1:
                lines.append(f"- 🎯 **操作建议**: 震荡整理，观望为主")
            else:
                lines.append(f"- 🎯 **操作建议**: 小幅波动，正常行情")
            lines.append("")
    else:
        lines.append("⚠️ 个股数据暂不可用")
    lines.append("")
    
    # ========== 三、风险提示 ==========
    lines.append("⚠️ 风险提示")
    lines.append("-" * 40)
    lines.append("1. 股市有风险，投资需谨慎")
    lines.append("2. 本报告仅供参考，不构成投资建议")
    lines.append("3. 请结合个人风险承受能力做出投资决策")
    lines.append("4. 注意设置止损止盈，控制仓位")
    lines.append("")
    
    # ========== 四、免责声明 ==========
    lines.append("=" * 60)
    lines.append("⚠️ 免责声明：本报告仅供参考，不构成投资建议。股市有风险，投资需谨慎。")
    lines.append("=" * 60)
    
    return "\n".join(lines)


if __name__ == '__main__':
    # 测试个股报告生成
    print("=" * 60)
    print("个股报告生成测试")
    print("=" * 60)
    
    # 模拟数据
    mock_data = {
        'timestamp': '2026-07-11 18:30:00',
        'date_str': '2026 年 07 月 11 日',
        'weekday': '星期六',
        'stocks': [
            {'name': '贵州茅台', 'code': 'sh600519', 'price': 1204.98, 'change_pct': 1.93, 'pe': 1204.98, 'pb': 1170.28, 'total_market_cap': 150000000000, 'turnover_rate': 0.42},
            {'name': '平安银行', 'code': 'sz000001', 'price': 10.45, 'change_pct': -0.38, 'pe': 10.51, 'pb': 10.40, 'total_market_cap': 20000000000, 'turnover_rate': 0.49},
            {'name': '五粮液', 'code': 'sz000858', 'price': 73.69, 'change_pct': 3.94, 'pe': 74.31, 'pb': 70.69, 'total_market_cap': 57000000000, 'turnover_rate': 1.20},
        ],
    }
    
    report = build_stock_dossier_report(mock_data)
    print(report)
    
    # 保存到文件
    with open('projects/stock_dossier_report_test.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    print("\n✅ 报告已保存到 projects/stock_dossier_report_test.txt")
