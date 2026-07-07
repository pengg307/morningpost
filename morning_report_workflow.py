"""
晨报推送工作流 - 每天8点执行
从数据库读取规整数据，生成晨报并推送到微信
"""
import sys
sys.path.insert(0, r'C:\Users\Pactera\projects\morningpost\morningpost')

from datetime import datetime
from data_acquisition_manager import DataAcquisitionManager
import json
import os

def generate_morning_report():
    """生成晨报"""
    print(f"{'='*70}")
    print(f"📰 [{datetime.now()}] 生成晨报")
    print(f"{'='*70}\n")
    
    manager = DataAcquisitionManager()
    
    try:
        # 1. 获取规整数据
        print("📊 获取规整数据...")
        clean_data = manager.get_clean_data()
        print(f"  获取到 {len(clean_data)} 条规整数据")
        
        # 2. 按数据类型分组
        print("\n📋 按数据类型分组:")
        data_by_type = {
            '美股': [],
            'A股': [],
            '期货': [],
            '加密货币': []
        }
        
        for row in clean_data:
            asset_class = row['asset_class_name']
            if asset_class in data_by_type:
                data_by_type[asset_class].append(dict(row))
                
        for data_type, items in data_by_type.items():
            print(f"  {data_type}: {len(items)}条")
            
        # 3. 生成晨报内容
        print("\n📝 生成晨报内容...")
        report = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'us_stocks': data_by_type['美股'],
            'a_stocks': data_by_type['A股'],
            'futures': data_by_type['期货'],
            'crypto': data_by_type['加密货币']
        }
        
        # 4. 保存到文件
        output_file = f'morning_report_{datetime.now().strftime("%Y%m%d_%H%M")}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        print(f"  已保存到: {output_file}")
        
        # 5. 推送到微信 (这里需要集成微信推送功能)
        print("\n📤 推送到微信...")
        # TODO: 集成微信推送功能
        print(f"  ✅ 晨报生成完成，准备推送")
        
        return report
        
    except Exception as e:
        print(f"\n❌ 晨报生成失败: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        manager.close()


if __name__ == "__main__":
    result = generate_morning_report()
    if result:
        print(f"\n✅ 晨报推送工作流执行完成!")
    else:
        print(f"\n❌ 晨报推送工作流执行失败")
        sys.exit(1)
