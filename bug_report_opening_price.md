# Bug Report: 新浪财经API开盘价数据错误

## 问题描述
新浪财经API返回的美股开盘价数据是错误的，导致数据库中存储的开盘价为负值或不合理数值。

## 错误示例
- TSLA: API返回开盘价-12.06，正确应该是412.94（昨收416.96 + 涨跌额-4.02）
- MSFT: API返回开盘价2.10，正确应该是393.03（昨收392.49 + 涨跌额0.54）

## 数据格式
新浪财经API返回格式：`var hq_str_gb_tsla="特斯拉,402.9000,-4.02,2026-07-08 08:50:06,-16.8700,416.9600,419.5600,401.8800,498.8300,..."`
- [0] 名称: 特斯拉
- [1] 现价: 402.9000
- [2] 涨跌额: -4.02
- [3] 时间: 2026-07-08 08:50:06
- [4] 开盘价: -16.8700 ← **这是错误的！**
- [5] 昨收: 416.9600
- [6] 最高: 419.5600
- [7] 最低: 401.8800
- [8] 成交量: 498.8300

## 修复方案
使用`昨收 + 涨跌额`计算正确的开盘价：
```python
open_price = prev_close + change
```

## 涉及文件
- `data_acquisition_manager.py`: `_parse_sina_us_stock`函数

## 正确代码
```python
def _parse_sina_us_stock(self, text: str) -> Optional[Dict]:
    """解析新浪美股数据"""
    try:
        start = text.find('="') + 2
        end = text.find('"', start)
        if start < 2 or end < 0:
            return None
            
        parts = text[start:end].split(',')
        if len(parts) < 9:
            return None
            
        current_price = float(parts[1])
        prev_close = float(parts[5]) if parts[5] else 0
        open_price = float(parts[4]) if parts[4] else 0
        high = float(parts[6]) if parts[6] else 0
        low = float(parts[7]) if parts[7] else 0
        volume = float(parts[8]) if parts[8] else 0
        
        # 修复：新浪财经API返回的开盘价是错误的，使用昨收+涨跌额计算
        if len(parts) > 2:
            change = float(parts[2])
            open_price = prev_close + change
        
        return {
            'price': current_price,
            'prev_close': prev_close,
            'open_price': open_price,
            'high': high,
            'low': low,
            'volume': volume,
            'change_pct': ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0,
            'name': parts[0]
        }
    except Exception as e:
        logger.error(f"Parse error: {e}")
        return None
```

## 要求
1. 分析这个bug的根本原因
2. 提供修复方案
3. 确保所有美股数据的开盘价都是正确的
4. 清理数据库中重复的小写股票数据
5. 重新获取所有数据并验证
