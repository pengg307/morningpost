#!/usr/bin/env python3
"""
个股尽调数据源 - Phase 3
================================
使用腾讯 API 获取个股基本面数据

使用方法:
    from stock_dossier_source import StockDossierSource
    
    source = StockDossierSource()
    data = source.get_all_data(stock_codes=['600519', '000001'])  # 获取个股数据
    source.close()
"""
import os
import json
import time
import requests
from datetime import datetime


class StockDossierSource:
    """个股尽调数据源 - 统一接口"""
    
    def __init__(self):
        """初始化"""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.tencent.com/',
        })
        
    def get_all_data(self, stock_codes=None):
        """获取个股所需的全部数据"""
        if stock_codes is None:
            stock_codes = ['600519', '000001', '000858']  # 默认股票
        
        data = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'date_str': datetime.now().strftime('%Y年%m月%d日'),
            'weekday': ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'][datetime.now().weekday()],
            'stocks': [],  # 个股数据
        }
        
        # Step 1: 获取个股行情和基本面
        print("[StockDossierSource] 获取个股数据...")
        data['stocks'] = self._fetch_stock_quotes(stock_codes)
        
        return data
    
    def _safe_float(self, value, default=0.0):
        """安全转换为浮点数"""
        try:
            if not value or value == '-':
                return default
            # 处理包含 / 的字符串，取第一个值
            if '/' in value:
                value = value.split('/')[0]
            return float(value)
        except:
            return default
    
    def _safe_int(self, value, default=0):
        """安全转换为整数"""
        try:
            if not value or value == '-':
                return default
            # 处理包含 / 的字符串，取第一个值
            if '/' in value:
                value = value.split('/')[0]
            return int(float(value))
        except:
            return default
    
    def _fetch_stock_quotes(self, stock_codes):
        """获取个股行情和基本面数据（腾讯 API）"""
        try:
            # 转换股票代码格式
            symbols = []
            for code in stock_codes:
                if code.startswith('6'):
                    symbols.append(f'sh{code}')
                else:
                    symbols.append(f'sz{code}')
            
            url = f'http://qt.gtimg.cn/q={"," .join(symbols)}'
            resp = self.session.get(url, timeout=10)
            
            if resp.text and len(resp.text) > 100:
                stocks_list = []
                lines = resp.text.split(';')
                
                for line in lines:
                    if '=' in line and '"' in line:
                        parts = line.split('=')
                        if len(parts) > 1:
                            # 解析名称和代码
                            name_code = parts[0].replace('v_', '')
                            # 解析数据（~ 分隔）
                            data_str = parts[1].strip('\"')
                            data_parts = data_str.split('~')
                            
                            if len(data_parts) >= 45:
                                stocks_list.append({
                                    'name': data_parts[1],  # 名称
                                    'code': name_code,
                                    'price': self._safe_float(data_parts[3]),  # 最新价
                                    'change': self._safe_float(data_parts[31]),  # 涨跌额
                                    'change_pct': self._safe_float(data_parts[32]),  # 涨跌幅
                                    'volume': self._safe_int(data_parts[36]),  # 成交量
                                    'amount': self._safe_float(data_parts[37]),  # 成交额
                                    'pe': self._safe_float(data_parts[33]),  # PE
                                    'pb': self._safe_float(data_parts[34]),  # PB
                                    'total_market_cap': self._safe_float(data_parts[30]),  # 总市值
                                    'circulating_market_cap': self._safe_float(data_parts[35]),  # 流通市值
                                    'turnover_rate': self._safe_float(data_parts[38]),  # 换手率
                                    'high': self._safe_float(data_parts[44]),  # 最高
                                    'low': self._safe_float(data_parts[45]),  # 最低
                                    'open': self._safe_float(data_parts[5]),  # 开盘
                                    'prev_close': self._safe_float(data_parts[4]),  # 昨收
                                })
                
                return stocks_list
        except Exception as e:
            print(f"[StockDossierSource] 个股数据获取失败: {e}")
        return []
    
    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()


if __name__ == '__main__':
    # 测试个股数据源
    print('=' * 60)
    print('个股数据源测试')
    print('=' * 60)
    
    source = StockDossierSource()
    data = source.get_all_data(['600519', '000001', '000858'])
    source.close()
    
    print(f'\n【个股数据】共 {len(data["stocks"])} 只')
    for stock in data['stocks']:
        print(f"  {stock['name']} ({stock['code']}): {stock['price']} ({stock['change_pct']:+.2f}%) | PE:{stock['pe']} | PB:{stock['pb']}")
    
    print('\n✅ 测试完成')
