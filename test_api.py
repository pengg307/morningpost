import requests

# Test SPCX via Sina GB
url = 'https://hq.sinajs.cn/list=gb_spcx'
headers = {'Referer': 'https://finance.sina.com.cn', 'User-Agent': 'Mozilla/5.0'}
r = requests.get(url, headers=headers, timeout=10)
print(f'SPCX Sina GB status: {r.status_code}, length: {len(r.text)}')
print(f'SPCX Sina GB response: {r.text[:500]}')
print()

# Test BTC via Coinbase
url2 = 'https://api.coinbase.com/apis/v2/prices/BTC-USD/spot'
r2 = requests.get(url2, timeout=10)
print(f'BTC Coinbase status: {r2.status_code}')
print(f'BTC Coinbase response: {r2.text[:300]}')
print()

# Test GC futures via Sina
url3 = 'https://hq.sinajs.cn/list=hf_GC'
headers3 = {'Referer': 'https://finance.sina.com.cn'}
r3 = requests.get(url3, headers=headers3, timeout=10)
print(f'GC Sina HF status: {r3.status_code}, length: {len(r3.text)}')
print(f'GC Sina HF response: {r3.text[:300]}')
print()

# Test ES futures via Sina
url4 = 'https://hq.sinajs.cn/list=hf_ES'
r4 = requests.get(url4, headers=headers3, timeout=10)
print(f'ES Sina HF status: {r4.status_code}, length: {len(r4.text)}')
print(f'ES Sina HF response: {r4.text[:300]}')
print()

# Test all futures at once
futures_list = 'hf_GC,hf_SI,hf_CL,hf_NG,hf_HG,hf_ES,hf_NQ,hf_YM,hf_RTY'
url5 = f'https://hq.sinajs.cn/list={futures_list}'
r5 = requests.get(url5, headers=headers3, timeout=10)
print(f'All futures batch status: {r5.status_code}, length: {len(r5.text)}')
lines = r5.text.strip().split('\n')
for line in lines:
    start = line.find('="') + 2
    end = line.find('"', start)
    if start > 1 and end > 0:
        parts = line[start:end].split(',')
        print(f'  {line.split("_")[-1].strip()} = {parts[:6] if len(parts) > 5 else parts}')
