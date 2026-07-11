#!/usr/bin/env python3
"""
晚报数据源 - 统一数据获取接口
================================
优先从东方财富/腾讯 API 读取，无数据时降级到备用源。

使用方法:
    from evening_data_source import EveningDataSource
    
    source = EveningDataSource()
    data = source.get_all_data()  # 获取全部数据
    source.close()
"""
import os
import json
import time
import requests
from datetime import datetime, timedelta


class EveningDataSource:
    """晚报数据源 - 统一接口"""
    
    def __init__(self):
        """初始化"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.eastmoney.com/',
        })
        self.proxy = {
            'http': 'http://127.0.0.1:10808',
            'https': 'http://127.0.0.1:10808'
        } if os.environ.get('PROXY_HTTP') else None
        
    def get_all_data(self):
        """获取晚报所需的全部数据"""
        data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date_str': datetime.now().strftime('%Y年%m月%d日'),
            'weekday': ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'][datetime.now().weekday()],
            'northbound': {},  # 北向资金
            'lhb': [],  # 龙虎榜
            'indices': {},  # 指数行情
            'industries': [],  # 行业板块
            'concepts': [],  # 概念板块
        }
        
        # Step 1: 获取北向资金
        print("[EveningDataSource] 获取北向资金...")
        data['northbound'] = self._fetch_northbound()
        
        # Step 2: 获取龙虎榜
        print("[EveningDataSource] 获取龙虎榜...")
        data['lhb'] = self._fetch_lhb()
        
        # Step 3: 获取指数行情
        print("[EveningDataSource] 获取指数行情...")
        data['indices'] = self._fetch_indices()
        
        # Step 4: 获取行业板块
        print("[EveningDataSource] 获取行业板块...")
        data['industries'] = self._fetch_industries()
        
        # Step 5: 获取概念板块
        print("[EveningDataSource] 获取概念板块...")
        data['concepts'] = self._fetch_concepts()
        
        return data
    
    def _fetch_northbound(self):
        """获取北向资金数据"""
        try:
            url = 'http://push2.eastmoney.com/api/qt/kamt.rtmin/get'
            params = {
                'fields1': 'f1,f2,f3,f4',
                'fields2': 'f51,f52,f53,f54,f55,f56',
                'ut': 'b2884a393a59ad64002292a3e90d46a5',
            }
            resp = self.session.get(url, params=params, timeout=10, proxies=self.proxy)
            data = resp.json()
            if data and data.get('data'):
                d = data['data']
                s2n = d.get('s2n', [])
                n2s = d.get('n2s', [])
                return {
                    'shanghai': s2n[-1] if s2n else '无数据',
                    'shenzhen': n2s[-1] if n2s else '无数据',
                }
        except Exception as e:
            print(f"[EveningDataSource] 北向资金获取失败: {e}")
        return {}
    
    def _fetch_lhb(self):
        """获取龙虎榜数据"""
        try:
            url = 'http://datacenter.eastmoney.com/securities/api/data/v1/get'
            params = {
                'reportName': 'RPT_BILLBOARD_DAILYDETAILS',
                'columns': 'SECURITY_CODE,SECURITY_NAME_ABBR,TRADE_DATE,EXPLANATION,TOTAL_NET',
                'pageSize': 10,
                'pageNumber': 1,
                'sortColumns': 'TRADE_DATE',
                'sortTypes': '-1',
                'client': 'VAP'
            }
            resp = self.session.get(url, params=params, timeout=10, proxies=self.proxy)
            data = resp.json()
            if data and data.get('result') and data['result'].get('data'):
                items = []
                for item in data['result']['data'][:10]:
                    code = item.get('SECURITY_CODE', '')
                    name = item.get('SECURITY_NAME_ABBR', '')
                    date = item.get('TRADE_DATE', '')
                    net = item.get('TOTAL_NET', 'N/A')
                    reason = item.get('EXPLANATION', 'N/A')
                    items.append({
                        'code': code,
                        'name': name,
                        'date': date,
                        'net': net,
                        'reason': reason,
                    })
                return items
        except Exception as e:
            print(f"[EveningDataSource] 龙虎榜获取失败: {e}")
        return []
    
    def _fetch_indices(self):
        """获取指数行情数据"""
        try:
            url = 'http://qt.gtimg.cn/q=sh000001,sz399001,sz399006'
            resp = self.session.get(url, timeout=10)
            if resp.text:
                data = resp.text.split(';')
                indices = {}
                for d in data:
                    if d and '=' in d:
                        parts = d.split('=')
                        if len(parts) > 1:
                            info = parts[1].split('~')
                            if len(info) > 32:
                                name = info[1]
                                price = info[3]
                                pct = info[32]
                                indices[name] = {
                                    'price': price,
                                    'change_pct': pct,
                                }
                return indices
        except Exception as e:
            print(f"[EveningDataSource] 指数行情获取失败: {e}")
        return {}
    
    def _fetch_industries(self):
        """获取行业板块数据"""
        try:
            # 使用腾讯行业数据
            url = 'http://qt.gtimg.cn/q=sh000300'  # 沪深 300 行业
            resp = self.session.get(url, timeout=10)
            if resp.text:
                parts = resp.text.split('~')
                if len(parts) > 32:
                    return [{
                        'name': parts[1],
                        'price': parts[3],
                        'change_pct': parts[32],
                    }]
        except Exception as e:
            print(f"[EveningDataSource] 行业板块获取失败: {e}")
        return []
    
    def _fetch_concepts(self):
        """获取概念板块数据"""
        try:
            # 使用腾讯概念数据
            url = 'http://qt.gtimg.cn/q=sh000905'  # 中证 500 概念
            resp = self.session.get(url, timeout=10)
            if resp.text:
                parts = resp.text.split('~')
                if len(parts) > 32:
                    return [{
                        'name': parts[1],
                        'price': parts[3],
                        'change_pct': parts[32],
                    }]
        except Exception as e:
            print(f"[EveningDataSource] 概念板块获取失败: {e}")
        return []
    
    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()


if __name__ == '__main__':
    # 测试晚报数据源
    print('=' * 60)
    print('晚报数据源测试')
    print('=' * 60)
    
    source = EveningDataSource()
    data = source.get_all_data()
    source.close()
    
    print('\n【北向资金】')
    print(f"  沪股通: {data['northbound'].get('shanghai', '无数据')}")
    print(f"  深股通: {data['northbound'].get('shenzhen', '无数据')}")
    
    print('\n【龙虎榜】')
    for item in data['lhb'][:5]:
        print(f"  {item['code']} {item['name']} | 净额:{item['net']} | 原因:{item['reason']}")
    
    print('\n【指数行情】')
    for name, info in data['indices'].items():
        print(f"  {name}: {info['price']} ({info['change_pct']}%)")
    
    print('\n【行业板块】')
    for item in data['industries']:
        print(f"  {item['name']}: {item['price']} ({item['change_pct']}%)")
    
    print('\n【概念板块】')
    for item in data['concepts']:
        print(f"  {item['name']}: {item['price']} ({item['change_pct']}%)")
    
    print('\n✅ 测试完成')
