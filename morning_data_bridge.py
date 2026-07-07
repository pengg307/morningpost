#!/usr/bin/env python3
"""
晨报数据准备脚本 - 从market_data.db读取规整数据
===============================================
将SQLite数据库中已获取的规整数据转换为晨报脚本所需的格式。

使用方法:
    python morning_data_bridge.py              # 使用默认数据库
    python morning_data_bridge.py --days 1     # 只取最近N天内的数据
    python morning_data_bridge.py --output data.json  # 指定输出路径
"""
import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from data_acquisition_manager import DataAcquisitionManager


def prepare_morning_report_data(manager: DataAcquisitionManager, days: int = 1,
                                 output_dir: str = None) -> dict:
    """
    从clean_data表读取规整数据，转换为晨报所需格式
    
    Args:
        manager: DataAcquisitionManager实例
        days: 数据时效天数（默认1天）
        output_dir: 输出目录
    
    Returns:
        dict: 晨报所需的全部数据
    """
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), 'projects')
    os.makedirs(output_dir, exist_ok=True)
    
    current_time = datetime.now()
    cutoff_time = current_time - timedelta(days=days)
    
    cursor = manager.conn.cursor()
    
    # 获取规整数据
    cursor.execute("""
        SELECT cd.symbol, cd.latest_price, cd.prev_close, cd.open_price,
               cd.high, cd.low, cd.volume, cd.change_pct,
               cd.data_quality_score, cd.last_updated,
               ac.name as asset_class_name,
               ds.name as source_name
        FROM clean_data cd
        JOIN asset_classes ac ON cd.asset_class_id = ac.id
        JOIN data_sources ds ON cd.best_source_id = ds.id
        WHERE cd.last_updated >= ?
        ORDER BY ac.id, cd.symbol
    """, (cutoff_time.isoformat(),))
    
    rows = cursor.fetchall()
    
    # 按资产类别分组
    data = {
        'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
        'date_str': current_time.strftime('%Y年%m月%d日'),
        'weekday': ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'][current_time.weekday()],
        'us_stocks': [],
        'a_stocks': [],
        'futures': [],
        'crypto': [],
        'market_indices': [],
        'summary': {}
    }
    
    for row in rows:
        item = {
            'symbol': row['symbol'],
            'price': float(row['latest_price']) if row['latest_price'] else 0,
            'prev_close': float(row['prev_close']) if row['prev_close'] else 0,
            'open': float(row['open_price']) if row['open_price'] else 0,
            'high': float(row['high']) if row['high'] else 0,
            'low': float(row['low']) if row['low'] else 0,
            'volume': int(row['volume']) if row['volume'] else 0,
            'change_pct': float(row['change_pct']) if row['change_pct'] else 0,
            'quality': float(row['data_quality_score']) if row['data_quality_score'] else 0,
            'source': row['source_name'],
            'updated': row['last_updated']
        }
        
        asset_class = row['asset_class_name']
        
        if asset_class == '美股':
            data['us_stocks'].append(item)
        elif asset_class == 'A股':
            data['a_stocks'].append(item)
        elif asset_class in ('期货', '中国期货'):
            data['futures'].append(item)
        elif asset_class == '加密货币':
            data['crypto'].append(item)
    
    # 生成摘要
    data['summary'] = {
        'total_clean': len(rows),
        'us_stocks_count': len(data['us_stocks']),
        'a_stocks_count': len(data['a_stocks']),
        'futures_count': len(data['futures']),
        'crypto_count': len(data['crypto']),
        'avg_quality': round(sum(r['data_quality_score'] for r in rows if r['data_quality_score']) / max(len(rows), 1), 3)
    }
    
    # 保存为JSON
    output_file = os.path.join(output_dir, f'morning_data_{current_time.strftime("%Y%m%d_%H%M%S")}.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"[晨报数据准备] 已保存到: {output_file}")
    print(f"[晨报数据准备] 摘要: {json.dumps(data['summary'], ensure_ascii=False, indent=2)}")
    
    return data


def main():
    parser = argparse.ArgumentParser(description='晨报数据准备脚本')
    parser.add_argument('--days', type=int, default=1, help='数据时效天数')
    parser.add_argument('--output', type=str, default=None, help='输出目录')
    args = parser.parse_args()
    
    print(f"{'='*70}")
    print(f"📰 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 晨报数据准备")
    print(f"{'='*70}")
    
    manager = DataAcquisitionManager()
    
    try:
        result = prepare_morning_report_data(manager, days=args.days, output_dir=args.output)
        print(f"\n✅ 晨报数据准备完成!")
        return result
    except Exception as e:
        print(f"\n❌ 晨报数据准备失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        manager.close()


if __name__ == '__main__':
    main()
