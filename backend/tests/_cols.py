import sqlite3
conn = sqlite3.connect('database/trading_database.db')
cols = [c[1] for c in conn.execute('PRAGMA table_info(active_positions)').fetchall()]
print(cols)
conn.close()
