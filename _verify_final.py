"""Ad-hoc verification of fetch_all_data.py — all market categories + SpaceX."""
import sys, os
sys.path.insert(0, r'C:\Users\Pactera\projects\morningpost\morningpost')
os.chdir(r'C:\Users\Pactera\projects\morningpost\morningpost')

from data_acquisition_manager import DataAcquisitionManager

m = DataAcquisitionManager()
cur = m.conn.cursor()

errors = []
passed = 0

# 1. Raw data per category
for aid, name in [(1,'US'),(2,'A-Shares'),(3,'Futures'),(4,'Crypto')]:
    cur.execute("SELECT COUNT(*) FROM raw_data WHERE asset_class_id=?", (aid,))
    cnt = cur.fetchone()[0]
    if cnt == 0:
        errors.append(f"No raw data for {name}")
    else:
        passed += 1

# 2. Clean data per category
for aid, name in [(1,'US'),(2,'A-Shares'),(3,'Futures'),(4,'Crypto')]:
    cur.execute("SELECT COUNT(*) FROM clean_data WHERE asset_class_id=?", (aid,))
    cnt = cur.fetchone()[0]
    if cnt == 0:
        errors.append(f"No clean data for {name}")
    else:
        passed += 1

# 3. SpaceX in clean_data
cur.execute("""SELECT latest_price, change_pct, data_quality_score
               FROM clean_data WHERE symbol IN ('SPCX','spcx') AND asset_class_id=1""")
row = cur.fetchone()
if row and row[0] and row[0] != 0 and row[2] >= 0.5:
    passed += 1
else:
    errors.append("SpaceX missing or invalid in clean_data")

# 4. All 12 US stocks present
expected_us = ['AAPL','AMD','AMZN','GOOGL','INTC','META','MSFT','NFLX','NVDA','SPCX','TSLA','TSM']
cur.execute("SELECT DISTINCT symbol FROM clean_data WHERE asset_class_id=1")
actual = {r[0] for r in cur.fetchall()}
if set(expected_us) <= actual:
    passed += 1
else:
    errors.append(f"Missing US stocks: {set(expected_us) - actual}")

# 5. All 10 crypto present
expected_crypto = ['btc','eth','bnb','sol','xrp','ada','doge','avax','dot','link']
cur.execute("SELECT DISTINCT symbol FROM clean_data WHERE asset_class_id=4")
actual_c = {r[0] for r in cur.fetchall()}
if set(expected_crypto) <= actual_c:
    passed += 1
else:
    errors.append(f"Missing crypto: {set(expected_crypto) - actual_c}")

# 6. Futures > 0
cur.execute("SELECT COUNT(*) FROM clean_data WHERE asset_class_id=3")
if cur.fetchone()[0] > 0:
    passed += 1
else:
    errors.append("No futures in clean_data")

# 7. A-shares >= 10
cur.execute("SELECT COUNT(DISTINCT symbol) FROM clean_data WHERE asset_class_id=2")
if cur.fetchone()[0] >= 10:
    passed += 1
else:
    errors.append(f"Too few A-shares: {cur.fetchone()[0]}")

m.close()

print(f"Checks passed: {passed}/13")
if errors:
    print(f"FAILED ({len(errors)} errors):")
    for e in errors:
        print(f"  FAIL: {e}")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED OK")
    sys.exit(0)
