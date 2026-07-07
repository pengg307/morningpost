import sqlite3

conn = sqlite3.connect('C:/Users/Pactera/projects/morningpost/morningpost/data/market_data.db')
cur = conn.cursor()

# Check latest raw_data timestamps
print('=== LATEST RAW_DATA BY ASSET CLASS ===')
cur.execute("""
    SELECT asset_class_id, symbol, source_id, status, timestamp, price 
    FROM raw_data 
    WHERE timestamp = (SELECT MAX(timestamp) FROM raw_data rd2 WHERE rd2.symbol = raw_data.symbol AND rd2.asset_class_id = raw_data.asset_class_id)
    ORDER BY asset_class_id, symbol
""")
for r in cur.fetchall():
    print(f"  [{r[0]}] {r[1]} src={r[2]} status={r[3]} ts={r[4]} price={r[5]}")

# Count total records
print('\n=== TOTAL RECORDS ===')
cur.execute("SELECT COUNT(*) FROM raw_data")
print(f"  raw_data: {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM clean_data")
print(f"  clean_data: {cur.fetchone()[0]}")

# Check SPCX specifically
print('\n=== ALL SPCX RECORDS ===')
cur.execute("SELECT * FROM raw_data WHERE UPPER(symbol) = 'SPCX' OR symbol = 'spcx' ORDER BY timestamp DESC")
for r in cur.fetchall():
    print(f"  id={r[0]} symbol={r[1]} asset_class_id={r[2]} source_id={r[3]} price={r[4]} status={r[18]} ts={r[17]}")

conn.close()
