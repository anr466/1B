"""
Database Foreign Keys Enforcement
تفعيل Foreign Keys تلقائياً عند الاتصال
"""

import sqlite3
from functools import wraps

def with_foreign_keys(func):
    """Decorator to ensure foreign keys are enabled for database operations"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # If first arg is connection, enable FK on it
        if args and isinstance(args[0], sqlite3.Connection):
            conn = args[0]
            conn.execute("PRAGMA foreign_keys = ON")
        return func(*args, **kwargs)
    return wrapper

def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Get database connection with foreign keys enabled and thread-safe"""
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=60.0)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.row_factory = sqlite3.Row
    return conn
