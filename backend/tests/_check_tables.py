import sqlite3
conn = sqlite3.connect('database/trading_bot.db')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    name = t[0]
    if 'trade' in name.lower() or 'position' in name.lower() or 'user_trade' in name.lower():
        cols = [c[1] for c in conn.execute(f"PRAGMA table_info({name})").fetchall()]
        print(f"{name}: {cols}")
conn.close()
