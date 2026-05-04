#!/usr/bin/env python3
"""Migrate core application data from SQLite to PostgreSQL."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Iterable

import psycopg2
from psycopg2.extras import execute_values

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SQLITE_PATH = Path(
    os.getenv("SQLITE_PATH", PROJECT_ROOT / "database" / "trading_database.db")
)
POSTGRES_DSN = os.getenv("DATABASE_URL") or (
    f"dbname={os.getenv('POSTGRES_DB', 'trading_ai_bot')} "
    f"user={os.getenv('POSTGRES_USER', 'trading_user')} "
    f"password={os.getenv('POSTGRES_PASSWORD', '')} "
    f"host={os.getenv('POSTGRES_HOST', '127.0.0.1')} "
    f"port={os.getenv('POSTGRES_PORT', '5432')}"
)

TABLES_IN_ORDER = [
    "users",
    "user_settings",
    "portfolio",
    "user_binance_keys",
    "active_positions",
    "activity_logs",
    "successful_coins",
    "trading_signals",
    "system_status",
    "verification_codes",
    "notifications",
    "notification_history",
    "user_notification_settings",
    "user_devices",
    "fcm_tokens",
    "user_sessions",
    "system_errors",
]


def sqlite_connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def postgres_connect():
    return psycopg2.connect(POSTGRES_DSN)


def fetch_rows(conn: sqlite3.Connection, table: str) -> tuple[list[str], list[tuple]]:
    rows = conn.execute(f"SELECT * FROM {table}").fetchall()
    if not rows:
        cursor = conn.execute(f"SELECT * FROM {table} LIMIT 0")
        columns = [desc[0] for desc in cursor.description]
        return columns, []
    columns = list(rows[0].keys())
    values = [tuple(row[col] for col in columns) for row in rows]
    return columns, values


def sqlite_table_exists(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
        (table,),
    ).fetchone()
    return row is not None


def postgres_columns(pg_conn, table: str) -> list[str]:
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        return [row[0] for row in cur.fetchall()]


def postgres_column_types(pg_conn, table: str) -> dict[str, str]:
    with pg_conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
            """,
            (table,),
        )
        return {row[0]: row[1] for row in cur.fetchall()}


def normalize_value(value, pg_type: str):
    if value is None:
        return None

    if pg_type == "boolean":
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "t", "yes", "y"}:
                return True
            if lowered in {"0", "false", "f", "no", "n"}:
                return False

    return value


def reset_table(pg_conn, table: str):
    with pg_conn.cursor() as cur:
        cur.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE')
    pg_conn.commit()


def copy_table(sqlite_conn: sqlite3.Connection, pg_conn, table: str):
    if not sqlite_table_exists(sqlite_conn, table):
        print(f"-> {table}: skipped (missing in SQLite)")
        return

    columns, rows = fetch_rows(sqlite_conn, table)
    pg_columns = postgres_columns(pg_conn, table)
    pg_column_types = postgres_column_types(pg_conn, table)
    common_columns = [column for column in columns if column in pg_columns]

    if not pg_columns:
        print(f"-> {table}: skipped (missing in PostgreSQL)")
        return

    print(
        f"-> {table}: {len(rows)} rows "
        f"(common_columns={len(common_columns)}/{len(columns)})"
    )
    reset_table(pg_conn, table)

    if not rows or not common_columns:
        return

    column_indexes = [columns.index(column) for column in common_columns]
    filtered_rows = []
    for row in rows:
        filtered_rows.append(
            tuple(
                normalize_value(
                    row[index], pg_column_types.get(common_columns[pos], "text")
                )
                for pos, index in enumerate(column_indexes)
            )
        )

    quoted_columns = ", ".join(f'"{col}"' for col in common_columns)
    insert_sql = f'INSERT INTO "{table}" ({quoted_columns}) VALUES %s'
    with pg_conn.cursor() as cur:
        execute_values(cur, insert_sql, filtered_rows, page_size=500)
    pg_conn.commit()


def main():
    if not SQLITE_PATH.exists():
        raise FileNotFoundError(f"SQLite database not found: {SQLITE_PATH}")

    sqlite_conn = sqlite_connect()
    pg_conn = postgres_connect()
    try:
        for table in TABLES_IN_ORDER:
            copy_table(sqlite_conn, pg_conn, table)
        print("✅ Migration completed")
    finally:
        sqlite_conn.close()
        pg_conn.close()


if __name__ == "__main__":
    main()
