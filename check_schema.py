import sqlite3

conn = sqlite3.connect('C:/Users/Pactera/projects/morningpost/morningpost/data/market_data.db')
cur = conn.cursor()

# Get table schemas
cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cur.fetchall()
print("=== TABLES ===")
for t in tables:
    print(f"  {t[0]}")
    cur.execute(f"PRAGMA table_info({t[0]})")
    cols = cur.fetchall()
    for c in cols:
        print(f"    {c[1]} ({c[2]})")

# Check asset_classes columns
print("\n=== ASSET_CLASSES DATA ===")
cur.execute("SELECT * FROM asset_classes")
for r in cur.fetchall():
    print(r)

# Check raw_data counts
print("\n=== RAW DATA BY ASSET_CLASS_ID ===")
cur.execute("SELECT asset_class_id, COUNT(*) FROM raw_data GROUP BY asset_class_id")
for r in cur.fetchall():
    print(f"  asset_class_id={r[0]}: {r[1]} records")

# Check clean_data
print("\n=== CLEAN DATA ===")
cur.execute("SELECT COUNT(*) FROM clean_data")
print(f"  Total: {cur.fetchone()[0]} records")
cur.execute("SELECT * FROM clean_data LIMIT 5")
for r in cur.fetchall():
    print(f"  {r}")

# Check SpaceX
print("\n=== SPACEX ===")
cur.execute("SELECT * FROM raw_data WHERE LOWER(symbol) LIKE '%spcx%'")
rows = cur.fetchall()
print(f"  raw_data records: {len(rows)}")
for r in rows:
    print(f"  {r}")

cur.execute("SELECT * FROM clean_data WHERE LOWER(symbol) LIKE '%spcx%'")
rows = cur.fetchall()
print(f"  clean_data records: {len(rows)}")
for r in rows:
    print(f"  {r}")

conn.close()
