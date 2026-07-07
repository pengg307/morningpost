#!/usr/bin/env python3
"""Quick test of data sources"""
import requests
import time

def test_sina_us():
    """Test Sina US stock API"""
    try:
        resp = requests.get(
            'https://hq.sinajs.cn/list=gb_tsla,gb_nvda,gb_aapl',
            headers={'Referer': 'https://finance.sina.com.cn/'},
            timeout=15
        )
        resp.encoding = 'gbk'
        print("=== SINA US STOCK ===")
        for line in resp.text.strip().split('\n'):
            print(line[:200])
        return True
    except Exception as e:
        print(f"Sina US error: {e}")
        return False

def test_tencent():
    """Test Tencent A-stock API"""
    try:
        resp = requests.get(
            'https://qt.gtimg.cn/q=sh600519,sz000725',
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=15
        )
        resp.encoding = 'gbk'
        print("\n=== TENCENT A-STOCK ===")
        for line in resp.text.strip().split('\n'):
            print(line[:200])
        return True
    except Exception as e:
        print(f"Tencent error: {e}")
        return False

def test_sina_futures():
    """Test Sina Futures API"""
    try:
        resp = requests.get(
            'https://hq.sinajs.cn/list=hf_GC,hf_SI,hf_CL',
            headers={'Referer': 'https://finance.sina.com.cn/'},
            timeout=15
        )
        resp.encoding = 'gbk'
        print("\n=== SINA FUTURES ===")
        for line in resp.text.strip().split('\n'):
            print(line[:200])
        return True
    except Exception as e:
        print(f"Sina Futures error: {e}")
        return False

def test_binance():
    """Test Binance API"""
    try:
        resp = requests.get(
            'https://api.binance.com/api/v3/ticker/24hr?symbols=["BTCUSDT","ETHUSDT"]',
            timeout=15
        )
        print("\n=== BINANCE ===")
        data = resp.json()
        for item in data:
            print(f"{item['symbol']}: price={item['lastPrice']} vol={item['volume']}")
        return True
    except Exception as e:
        print(f"Binance error: {e}")
        return False

def test_coinbase():
    """Test Coinbase API"""
    try:
        resp = requests.get(
            'https://api.coinbase.com/api/v3/balance/available',
            timeout=15
        )
        print("\n=== COINBASE ===")
        print(f"Status: {resp.status_code}")
        print(resp.text[:300])
        return True
    except Exception as e:
        print(f"Coinbase error: {e}")
        return False

def test_eastmoney_sector():
    """Test EastMoney sector API"""
    try:
        url = 'https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&po=1&np=1&fltt=2&invt=2&fid=f6&fs=m:90+t:2,m:90+t:3,m:90+t:4&fields=f12,f14,f2,f3,f6'
        resp = requests.get(url, headers={'Referer': 'https://quote.eastmoney.com/'}, timeout=15)
        print("\n=== EASTMONEY SECTOR ===")
        data = resp.json()
        if data.get('data'):
            for item in data['data']['diff'][:5]:
                print(f"{item.get('f14')} ({item.get('f12')}): price={item.get('f2')} pct={item.get('f3')} amount={item.get('f6')}")
        return True
    except Exception as e:
        print(f"EastMoney error: {e}")
        return False

if __name__ == '__main__':
    test_sina_us()
    time.sleep(0.5)
    test_tencent()
    time.sleep(0.5)
    test_sina_futures()
    time.sleep(0.5)
    test_binance()
    time.sleep(0.5)
    test_coinbase()
    time.sleep(0.5)
    test_eastmoney_sector()
