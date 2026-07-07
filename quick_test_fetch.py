"""
快速测试定时任务 - 只获取少量数据
"""
import sys
sys.path.insert(0, r'C:\Users\Pactera\projects\morningpost\morningpost')

from datetime import datetime
from data_acquisition_manager import DataAcquisitionManager

print(f"{'='*70}")
print(f"⚡ [{datetime.now()}] 快速定时任务测试")
print(f"{'='*70}\n")

manager = DataAcquisitionManager()

try:
    # 1. 只获取少量美股
    print("📊 获取美股 (限制3只)...")
    us_symbols = ['TSLA', 'AAPL', 'MSFT']
    for symbol in us_symbols:
        result = manager.acquire_raw_data(symbol, 1, [1], max_retries=1)
        for source, data in result.items():
            if data['status'] == 'success':
                print(f"  ✅ {symbol}: ${data['data'].get('price', 'N/A')}")
            else:
                print(f"  ❌ {symbol}: {data.get('error', 'Unknown')}")
    
    # 2. 只获取少量A股
    print("\n🇨🇳 获取A股 (限制3只)...")
    a_symbols = ['000725', '002384', '600519']
    for symbol in a_symbols:
        result = manager.acquire_raw_data(symbol, 2, [2], max_retries=1)
        for source, data in result.items():
            if data['status'] == 'success':
                print(f"  ✅ {symbol}: ¥{data['data'].get('price', 'N/A')}")
            else:
                print(f"  ❌ {symbol}: {data.get('error', 'Unknown')}")
    
    # 3. 只获取少量期货
    print("\n📈 获取期货 (限制3只)...")
    fu_symbols = ['GC', 'CL', 'SI']
    for symbol in fu_symbols:
        result = manager.acquire_raw_data(symbol, 3, [1], max_retries=1)
        for source, data in result.items():
            if data['status'] == 'success':
                print(f"  ✅ {symbol}: ${data['data'].get('price', 'N/A')}")
            else:
                print(f"  ❌ {symbol}: {data.get('error', 'Unknown')}")
    
    # 4. 数据规整
    print("\n🔧 数据规整...")
    manager.consolidate_data()
    
    # 5. 统计
    cursor = manager.conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM raw_data")
    raw_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM clean_data")
    clean_count = cursor.fetchone()[0]
    
    print(f"\n📊 统计:")
    print(f"  raw_data: {raw_count}条")
    print(f"  clean_data: {clean_count}条")
    
    print(f"\n{'='*70}")
    print(f"✅ 快速测试完成!")
    print(f"{'='*70}\n")
    
except Exception as e:
    print(f"\n❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    manager.close()
