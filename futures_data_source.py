#!/usr/bin/env python3
"""
期货深度分析数据源 - Phase 2
================================
使用腾讯 API 获取期货数据

使用方法:
    from futures_data_source import FuturesDataSource
    
    source = FuturesDataSource()
    data = source.get_all_data()  # 获取全部期货数据
    source.close()
"""
import os
import json
import time
import requests
from datetime import datetime


class FuturesDataSource:
    """期货数据源 - 统一接口"""
    
    def __init__(self):
        """初始化"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.tencent.com/',
        })
        
    def get_all_data(self):
        """获取期货所需的全部数据"""
        data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date_str': datetime.now().strftime('%Y年%m月%d日'),
            'weekday': ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'][datetime.now().weekday()],
            'futures': [],  # 期货行情
        }
        
        # Step 1: 获取期货行情
        print("[FuturesDataSource] 获取期货行情...")
        data['futures'] = self._fetch_futures_quotes()
        
        return data
    
    def _fetch_futures_quotes(self):
        """获取期货行情数据（腾讯 API）"""
        try:
            # 主要期货品种
            symbols = [
                'hf_CL',   # 原油
                'hf_NQ',   # 纳斯达克
                'hf_GC',   # 黄金
                'hf_SI',   # 白银
                'hf_HG',   # 铜
                'hf_NG',   # 天然气
                'hf_ZC',   # 动力煤
                'hf_I',    # 铁矿石
                'hf_J',    # 焦炭
                'hf_M',    # 豆粕
            ]
            
            url = f'http://qt.gtimg.cn/q={"," .join(symbols)}'
            resp = self.session.get(url, timeout=10)
            
            if resp.text and len(resp.text) > 100:
                futures_list = []
                lines = resp.text.split(';')
                
                for line in lines:
                    if '=' in line and '"' in line:
                        parts = line.split('=')
                        if len(parts) > 1:
                            # 解析名称和代码
                            name_code = parts[0].replace('v_', '')
                            # 解析数据（逗号分隔，在引号内）
                            data_str = parts[1].strip('\"')
                            data_parts = data_str.split(',')
                            
                            if len(data_parts) >= 10:
                                futures_list.append({
                                    'name': data_parts[-1],  # 名称（最后字段）
                                    'code': name_code,
                                    'price': float(data_parts[0]) if data_parts[0] else 0,  # 最新价
                                    'change': float(data_parts[1]) if data_parts[1] else 0,  # 涨跌额
                                    'open': float(data_parts[2]) if data_parts[2] else 0,  # 开盘价
                                    'prev_close': float(data_parts[3]) if data_parts[3] else 0,  # 昨收
                                    'high': float(data_parts[4]) if data_parts[4] else 0,  # 最高价
                                    'low': float(data_parts[5]) if data_parts[5] else 0,  # 最低价
                                    'time': data_parts[6],  # 时间
                                    'bid': data_parts[7],  # 买一
                                    'ask': data_parts[8],  # 卖一
                                    'volume': int(float(data_parts[9])) if data_parts[9] else 0,  # 成交量
                                    'change_pct': float(data_parts[10]) if data_parts[10] else 0,  # 涨跌幅
                                })
                
                return futures_list
        except Exception as e:
            print(f"[FuturesDataSource] 期货行情获取失败: {e}")
        return []
    
    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()


if __name__ == '__main__':
    # 测试期货数据源
    print('=' * 60)
    print('期货数据源测试')
    print('=' * 60)
    
    source = FuturesDataSource()
    data = source.get_all_data()
    source.close()
    
    print(f'\n【期货行情】共 {len(data["futures"])} 只')
    for fut in data['futures'][:5]:
        print(f"  {fut['name']} ({fut['code']}): {fut['price']} ({fut['change_pct']:+.2f}%)")
    
    print('\n✅ 测试完成')
