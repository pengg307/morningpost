import requests

# Test all futures at once
futures_list = 'hf_GC,hf_SI,hf_CL,hf_NG,hf_HG,hf_ES,hf_NQ,hf_YM,hf_RTY'
url = f'https://hq.sinajs.cn/list={futures_list}'
headers = {'Referer': 'https://finance.sina.com.cn'}
r = requests.get(url, headers=headers, timeout=10)
print(f'All futures batch status: {r.status_code}, length: {len(r.text)}')
lines = r.text.strip().split('\n')
for line in lines:
    symbol = line.split('_')[-1].strip().rstrip('"').lower()
    start = line.find('="') + 2
    end = line.find('"', start)
    if start > 1 and end > 0:
        parts = line[start:end].split(',')
        print(f'  {symbol}: price={parts[0]}, prev_close={parts[2]}, open={parts[3]}, high={parts[4]}, low={parts[5]}')
    else:
        print(f'  {symbol}: NO DATA (len={len(line)})')

print()

# Test Chinese futures
cn_futures = 'hf_cu0,hf_ag0,hf_rb0,hf.au0'
url2 = f'https://hq.sinajs.cn/list={cn_futures}'
r2 = requests.get(url2, headers=headers, timeout=10)
print(f'CN futures status: {r2.status_code}, length: {len(r2.text)}')
lines2 = r2.text.strip().split('\n')
for line in lines2:
    symbol = line.split('_')[-1].strip().rstrip('"').lower()
    start = line.find('="') + 2
    end = line.find('"', start)
    if start > 1 and end > 0:
        parts = line[start:end].split('~')
        if len(parts) > 5:
            print(f'  {symbol}: name={parts[1]}, price={parts[3]}, high={parts[33] if len(parts)>33 else "N/A"}, low={parts[34] if len(parts)>34 else "N/A"}')
        else:
            parts2 = line[start:end].split(',')
            print(f'  {symbol}: {parts2[:6]}')
    else:
        print(f'  {symbol}: NO DATA')

print()

# Test Binance with proxy
try:
    import os
    proxy = os.environ.get('PROXY_HTTP', 'http://127.0.0.1:10808')
    print(f'Testing Binance with proxy: {proxy}')
    proxies = {'http': proxy, 'https': proxy}
    r3 = requests.get('https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT', proxies=proxies, timeout=15)
    print(f'Binance BTC status: {r3.status_code}')
    if r3.status_code == 200:
        data = r3.json()
        print(f'  BTC: price={data["lastPrice"]}, change={data["priceChangePercent"]}%, vol={data["quoteVolume"]}')
except Exception as e:
    print(f'Binance failed: {e}')
