"""
晨报数据准备 - 从规整数据表中读取数据，准备晨报分析
"""
import os
import json
from datetime import datetime
from data_acquisition_manager import DataAcquisitionManager

def prepare_morning_report_data():
    """准备晨报所需数据"""
    print(f"\n{'='*60}")
    print(f"📋 [{datetime.now()}] 开始准备晨报数据")
    print(f"{'='*60}\n")
    
    manager = DataAcquisitionManager()
    
    try:
        # 获取所有规整数据
        clean_data = manager.get_clean_data()
        
        # 按数据类型分组
        data_by_type = {
            'us_stock': [],
            'futures': [],
            'crypto': [],
            'a_stock': []
        }
        
        for record in clean_data:
            data_type = record['data_type']
            if data_type in data_by_type:
                data_by_type[data_type].append(record)
                
        # 打印统计信息
        print("📊 晨报数据准备完成:")
        print(f"  美股: {len(data_by_type['us_stock'])} 只")
        print(f"  期货: {len(data_by_type['futures'])} 只")
        print(f"  加密: {len(data_by_type['crypto'])} 只")
        print(f"  A股: {len(data_by_type['a_stock'])} 只")
        
        # 保存到临时文件供晨报分析使用
        output_dir = os.path.join(os.path.dirname(__file__), 'projects')
        os.makedirs(output_dir, exist_ok=True)
        
        output_file = os.path.join(output_dir, f'morning_data_{datetime.now().strftime("%Y%m%d_%H%M")}.json')
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data_by_type, f, ensure_ascii=False, indent=2, default=str)
            
        print(f"\n✅ 数据已保存到: {output_file}")
        
        return data_by_type
        
    except Exception as e:
        print(f"\n❌ 晨报数据准备失败: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        manager.close()

if __name__ == '__main__':
    prepare_morning_report_data()
