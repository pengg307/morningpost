#!/usr/bin/env python3
"""
期货深度分析报告生成器 - Phase 2（零 Token）
================================
完全基于规则引擎和字符串拼接生成报告，无需 LLM 调用。

使用方法:
    from futures_report import build_futures_report
    
    report = build_futures_report(data)
    print(report)
"""


def build_futures_report(data):
    """
    生成期货深度分析报告（零 Token 模板模式）
    
    Args:
        data: FuturesDataSource.get_all_data() 返回的数据字典
    
    Returns:
        str: Markdown 格式的期货研判报告
    """
    lines = []
    timestamp = data.get('timestamp', '')
    date_str = data.get('date_str', '')
    weekday = data.get('weekday', '')
    futures = data.get('futures', [])
    
    # ========== 标题 ==========
    lines.append("=" * 60)
    lines.append(f"📊 【期货深度研判报告】{date_str} {weekday}")
    lines.append(f"🕒 数据获取时间: {timestamp}")
    lines.append("=" * 60)
    lines.append("")
    
    # ========== 一、三句话看懂期货市场 ==========
    lines.append("💡 三句话看懂期货市场")
    lines.append("-" * 40)
    
    if futures:
        # 统计涨跌
        up_count = sum(1 for f in futures if f.get('change_pct', 0) > 0)
        down_count = sum(1 for f in futures if f.get('change_pct', 0) < 0)
        flat_count = len(futures) - up_count - down_count
        
        # 找出涨跌幅最大的品种
        max_up = max(futures, key=lambda x: x.get('change_pct', 0)) if up_count > 0 else None
        max_down = min(futures, key=lambda x: x.get('change_pct', 0)) if down_count > 0 else None
        
        lines.append(f"1️⃣ 市场概况：{len(futures)} 只期货，{up_count} 涨 {down_count} 跌 {flat_count} 平")
        
        if max_up:
            lines.append(f"2️⃣ 领涨品种：{max_up['name']} (+{max_up['change_pct']:.2f}%)")
        if max_down:
            lines.append(f"3️⃣ 领跌品种：{max_down['name']} ({max_down['change_pct']:.2f}%)")
    else:
        lines.append("1️⃣ 市场概况：无数据")
        lines.append("2️⃣ 领涨品种：暂无")
        lines.append("3️⃣ 领跌品种：暂无")
    lines.append("")
    
    # ========== 二、期货行情概览 ==========
    lines.append("📈 期货行情概览")
    lines.append("-" * 40)
    
    if futures:
        for fut in futures:
            name = fut.get('name', '')
            code = fut.get('code', '')
            price = fut.get('price', 0)
            change_pct = fut.get('change_pct', 0)
            high = fut.get('high', 0)
            low = fut.get('low', 0)
            volume = fut.get('volume', 0)
            
            # 格式化成交量
            if volume >= 10000:
                vol_str = f"{volume/10000:.1f}万手"
            else:
                vol_str = f"{volume}手"
            
            lines.append(f"- **{name}** ({code}): {price} ({change_pct:+.2f}%) | 最高:{high} 最低:{low} | 量:{vol_str}")
    else:
        lines.append("⚠️ 期货行情数据暂不可用")
    lines.append("")
    
    # ========== 三、重点品种分析 ==========
    lines.append("🔍 重点品种分析")
    lines.append("-" * 40)
    
    if futures:
        # 按涨跌幅排序
        sorted_futures = sorted(futures, key=lambda x: abs(x.get('change_pct', 0)), reverse=True)
        
        for i, fut in enumerate(sorted_futures[:5], 1):
            name = fut.get('name', '')
            price = fut.get('price', 0)
            change_pct = fut.get('change_pct', 0)
            open_price = fut.get('open', 0)
            prev_close = fut.get('prev_close', 0)
            
            # 计算振幅
            high = fut.get('high', 0)
            low = fut.get('low', 0)
            amplitude = ((high - low) / prev_close * 100) if prev_close else 0
            
            lines.append(f"{i}. **{name}**")
            lines.append(f"   - 最新价: {price}")
            lines.append(f"   - 涨跌幅: {change_pct:+.2f}%")
            lines.append(f"   - 开盘价: {open_price}")
            lines.append(f"   - 昨收价: {prev_close}")
            lines.append(f"   - 振幅: {amplitude:.2f}%")
            
            # 根据涨跌幅给出点评
            if change_pct > 2:
                lines.append(f"   - 💡 **点评**: 强势上涨，关注后续动能")
            elif change_pct < -2:
                lines.append(f"   - 💡 **点评**: 大幅下跌，注意风险")
            elif abs(change_pct) <= 1:
                lines.append(f"   - 💡 **点评**: 震荡整理，观望为主")
            else:
                lines.append(f"   - 💡 **点评**: 小幅波动，正常行情")
            lines.append("")
    else:
        lines.append("⚠️ 期货品种数据暂不可用")
    lines.append("")
    
    # ========== 四、交易建议 ==========
    lines.append("🎯 交易建议")
    lines.append("-" * 40)
    
    if futures:
        # 找出强势品种
        strong_up = [f for f in futures if f.get('change_pct', 0) > 1]
        strong_down = [f for f in futures if f.get('change_pct', 0) < -1]
        
        if strong_up:
            lines.append("🟢 **强势品种（可关注做多机会）**:")
            for f in strong_up[:3]:
                lines.append(f"  - {f['name']} ({f['change_pct']:+.2f}%)")
            lines.append("")
        
        if strong_down:
            lines.append("🔴 **弱势品种（可关注做空机会）**:")
            for f in strong_down[:3]:
                lines.append(f"  - {f['name']} ({f['change_pct']:+.2f}%)")
            lines.append("")
        
        lines.append("⚠️ **风险提示**:")
        lines.append("1. 期货交易杠杆高，注意风险控制")
        lines.append("2. 设置止损止盈，避免大幅亏损")
        lines.append("3. 关注外围市场影响（美股、原油等）")
        lines.append("4. 注意持仓限额和保证金要求")
    else:
        lines.append("⚠️ 暂无数据，无法提供交易建议")
    lines.append("")
    
    # ========== 五、免责声明 ==========
    lines.append("=" * 60)
    lines.append("⚠️ 免责声明：本报告仅供参考，不构成投资建议。期货交易有风险，投资需谨慎。")
    lines.append("=" * 60)
    
    return "\n".join(lines)


if __name__ == '__main__':
    # 测试期货报告生成
    print("=" * 60)
    print("期货报告生成测试")
    print("=" * 60)
    
    # 模拟数据
    mock_data = {
        'timestamp': '2026-07-11 18:30:00',
        'date_str': '2026 年 07 月 11 日',
        'weekday': '星期六',
        'futures': [
            {'name': '纽约原油', 'code': 'hf_CL', 'price': 71.43, 'change_pct': 2.00, 'high': 71.52, 'low': 70.77, 'volume': 100000, 'open': 71.50, 'prev_close': 70.03},
            {'name': '纽约黄金', 'code': 'hf_GC', 'price': 4130.63, 'change_pct': 0.50, 'high': 4144.60, 'low': 4081.70, 'volume': 50000, 'open': 4128.40, 'prev_close': 4110.00},
            {'name': '纽约白银', 'code': 'hf_SI', 'price': 60.37, 'change_pct': -1.50, 'high': 61.00, 'low': 59.50, 'volume': 30000, 'open': 60.80, 'prev_close': 61.29},
            {'name': '美铜', 'code': 'hf_HG', 'price': 628.95, 'change_pct': 1.20, 'high': 630.00, 'low': 620.00, 'volume': 20000, 'open': 622.00, 'prev_close': 621.50},
            {'name': '美国天然气', 'code': 'hf_NG', 'price': 2.89, 'change_pct': -3.00, 'high': 3.00, 'low': 2.85, 'volume': 80000, 'open': 2.95, 'prev_close': 2.98},
        ],
    }
    
    report = build_futures_report(mock_data)
    print(report)
    
    # 保存到文件
    with open('projects/futures_report_test.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    print("\n✅ 报告已保存到 projects/futures_report_test.txt")
