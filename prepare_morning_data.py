#!/usr/bin/env python3
"""
晨报数据准备脚本
================
从规整数据表 (clean_data) 读取数据，按数据类型分组，
保存到JSON文件供晨报分析使用。

用法:
    python prepare_morning_data.py              # 使用默认数据库
    python prepare_morning_data.py --days 1      # 只取最近N天的数据
    python prepare_morning_data.py --output out.json  # 指定输出路径
"""
import os
import sys
import json
import argparse
import logging
from datetime import datetime, timedelta

from data_acquisition_manager import DataAcquisitionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("PrepareMorningData")


def prepare_morning_report_data(manager: DataAcquisitionManager, days: int = 1,
                                 output_dir: str = None) -> dict:
    """Prepare data for morning report from clean_data table.
    
    Args:
        manager: DataAcquisitionManager instance
        days: Only include data from last N days (default: 1)
        output_dir: Directory to save JSON output
        
    Returns:
        dict: Data grouped by type
    """
    cutoff = datetime.now() - timedelta(days=days)
    
    # Get all clean data
    clean_data = manager.get_clean_data()
    
    # Filter by recency
    recent_data = []
    for record in clean_data:
        last_updated = record.get("last_updated", "")
        if last_updated:
            try:
                updated_dt = datetime.strptime(last_updated[:19], "%Y-%m-%d %H:%M:%S")
                if updated_dt >= cutoff:
                    recent_data.append(record)
            except ValueError:
                recent_data.append(record)  # Include if can't parse
        else:
            recent_data.append(record)  # Include if no timestamp
    
    # Group by data type
    data_by_type = {
        "us_stock": [],
        "futures": [],
        "crypto": [],
        "a_stock": [],
    }
    
    for record in recent_data:
        data_type = record.get("data_type", "")
        if data_type in data_by_type:
            # Convert to serializable format
            clean_record = {
                "symbol": record.get("symbol"),
                "name": record.get("name", ""),
                "latest_price": record.get("latest_price"),
                "prev_close": record.get("prev_close"),
                "open_price": record.get("open_price"),
                "high": record.get("high"),
                "low": record.get("low"),
                "volume": record.get("volume"),
                "change_pct": record.get("change_pct"),
                "market_cap": record.get("market_cap"),
                "pe_ratio": record.get("pe_ratio"),
                "pb_ratio": record.get("pb_ratio"),
                "turnover_rate": record.get("turnover_rate"),
                "best_source": record.get("best_source"),
                "last_updated": record.get("last_updated"),
                "data_quality_score": record.get("data_quality_score"),
            }
            data_by_type[data_type].append(clean_record)
    
    # Sort by change_pct descending (most active first)
    for dtype in data_by_type:
        data_by_type[dtype].sort(
            key=lambda x: abs(x.get("change_pct", 0) or 0), reverse=True
        )
    
    # Build output structure
    output = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "date": datetime.now().strftime("%Y-%m-%d"),
        "days_included": days,
        "summary": {
            "total_records": sum(len(v) for v in data_by_type.values()),
            "by_type": {k: len(v) for k, v in data_by_type.items()},
        },
        "data": data_by_type,
    }
    
    # Print statistics
    logger.info("📊 晨报数据准备完成:")
    logger.info(f"  美股: {len(data_by_type['us_stock'])} 只")
    logger.info(f"  期货: {len(data_by_type['futures'])} 只")
    logger.info(f"  加密: {len(data_by_type['crypto'])} 只")
    logger.info(f"  A股: {len(data_by_type['a_stock'])} 只")
    logger.info(f"  总计: {output['summary']['total_records']} 条记录")
    
    # Save to JSON
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "projects")
    os.makedirs(output_dir, exist_ok=True)
    
    # Save with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"morning_data_{timestamp}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    
    # Also save as "latest" symlink
    latest_file = os.path.join(output_dir, "morning_data_latest.json")
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2, default=str)
    
    logger.info(f"\n✅ 数据已保存到:")
    logger.info(f"  时间戳文件: {output_file}")
    logger.info(f"  最新版本:   {latest_file}")
    
    return output


def main():
    parser = argparse.ArgumentParser(description="晨报数据准备")
    parser.add_argument("--days", type=int, default=1, help="包含最近N天的数据 (默认: 1)")
    parser.add_argument("--output-dir", type=str, default=None, help="输出目录")
    parser.add_argument("--db", type=str, default=None, help="数据库路径")
    args = parser.parse_args()
    
    manager = DataAcquisitionManager(db_path=args.db)
    
    try:
        output = prepare_morning_report_data(manager, days=args.days, output_dir=args.output_dir)
        
        # Also print top movers for quick reference
        logger.info("\n🔥 涨跌幅排行:")
        for dtype, label in [("us_stock", "美股"), ("futures", "期货"), ("crypto", "加密")]:
            movers = output["data"].get(dtype, [])[:5]
            if movers:
                logger.info(f"  {label}:")
                for m in movers:
                    pct = m.get("change_pct", 0) or 0
                    logger.info(f"    {m.get('symbol', '?')}: ${m.get('latest_price', 0):.2f} ({pct:+.2f}%)")
        
        logger.info("\n✅ 晨报数据准备完成")
        
    except Exception as e:
        logger.error(f"❌ 晨报数据准备失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        manager.close()


if __name__ == "__main__":
    main()
