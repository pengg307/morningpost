import sqlite3

conn = sqlite3.connect('C:/Users/Pactera/projects/morningpost/morningpost/data/market_data.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Check raw_data counts by asset class
print('=== RAW DATA SUMMARY ===')
cur.execute('SELECT ac.name_zh, COUNT(*) FROM raw_data rd JOIN asset_classes ac ON rd.asset_class_id = ac.id GROUP BY ac.name_zh')
for r in cur.fetchall():
    print(f'  {r["name_zh"]}: {r[1]} records')

# Check clean_data
print()
print('=== CLEAN DATA SUMMARY ===')
cur.execute('SELECT ac.name_zh, cd.symbol, cd.latest_price, cd.change_pct FROM clean_data cd JOIN asset_classes ac ON cd.asset_class_id = ac.id ORDER BY cd.asset_class_id, cd.symbol')
for r in cur.fetchall():
    print(f'  [{r["name_zh"]}] {r["symbol"]}: price={r["latest_price"]}, change={r["change_pct"]}%')

# Check SpaceX specifically
print()
print('=== SPACEX CHECK ===')
cur.execute("SELECT * FROM clean_data WHERE LOWER(symbol) LIKE '%spcx%'")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(dict(r))
else:
    print('No SPCX in clean_data')

cur.execute("SELECT * FROM raw_data WHERE LOWER(symbol) LIKE '%spcx%'")
rows = cur.fetchall()
print(f'SPCX raw_data records: {len(rows)}')
for r in rows:
    d = dict(r)
    print(f'  source_id={d["source_id"]}, price={d["price"]}, status={d["status"]}')

# Check raw_data status summary
print()
print('=== RAW DATA STATUS ===')
cur.execute('SELECT source_id, status, COUNT(*) FROM raw_data GROUP BY source_id, status')
for r in cur.fetchall():
    print(f'  source_id={r["source_id"]}, status={r["status"]}: {r[2]} records')

conn.close()
