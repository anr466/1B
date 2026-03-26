import os
import psycopg2
from contextlib import contextmanager


class DBConnection:
    def __init__(self, dsn=None):
        if dsn:
            self.dsn = dsn
        else:
            host = os.environ.get("POSTGRES_HOST", "localhost")
            port = os.environ.get("POSTGRES_PORT", "5432")
            db = os.environ.get("POSTGRES_DB", "trading_ai_bot")
            user = os.environ.get("POSTGRES_USER", "trading_user")
            password = os.environ.get("POSTGRES_PASSWORD", "")
            self.dsn = (
                f"dbname={db} user={user} password={password} host={host} port={port}"
            )

    @contextmanager
    def get_write_connection(self):
        conn = psycopg2.connect(self.dsn)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    @contextmanager
    def get_read_connection(self):
        conn = psycopg2.connect(self.dsn)
        try:
            yield conn
        finally:
            conn.close()
