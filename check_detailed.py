import sqlite3

conn = sqlite3.connect('C:/Users/Pactera/projects/morningpost/morningpost/data/market_data.db')
cur = conn.cursor()

# Check SPCX records with timestamps
print('=== SPCX ALL RECORDS WITH TIMESTAMPS ===')
cur.execute("SELECT id, symbol, source_id, price, status, timestamp, raw_json FROM raw_data WHERE UPPER(symbol) = 'SPCX' OR symbol = 'spcx' ORDER BY timestamp DESC")
for r in cur.fetchall():
    print(f"  id={r[0]} symbol={r[1]} src={r[2]} price={r[3]} status={r[4]} ts={r[5]}")
    print(f"    raw_json: {r[6][:200] if r[6] else 'None'}")

# Check futures data
print('\n=== FUTURES DATA ===')
cur.execute("SELECT symbol, price, prev_close, change_pct, timestamp FROM raw_data WHERE asset_class_id=3 ORDER BY timestamp DESC LIMIT 10")
for r in cur.fetchall():
    print(f"  {r[0]}: price={r[1]} prev_close={r[2]} change={r[3]}% ts={r[4]}")

# Check crypto
print('\n=== CRYPTO DATA ===')
cur.execute("SELECT symbol, price, change_pct, timestamp FROM raw_data WHERE asset_class_id=4 ORDER BY timestamp DESC LIMIT 10")
for r in cur.fetchall():
    print(f"  {r[0]}: price={r[1]} change={r[3]}% ts={r[3]}")

# Check if crypto has any records
cur.execute("SELECT COUNT(*) FROM raw_data WHERE asset_class_id=4")
print(f"\n  Crypto total records: {cur.fetchone()[0]}")

conn.close()
