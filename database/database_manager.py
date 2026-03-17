"""
مدير قاعدة البيانات الموحد
يوفر واجهة موحدة للتفاعل مع قاعدة البيانات
يستخدم من قبل النظام الخلفي وواجهة المستخدم
"""

import json
import logging
import time
import queue
import re
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from contextlib import contextmanager
from threading import Lock
import threading
from urllib.parse import urlparse

try:
    import psycopg2
    import psycopg2.extras
    from psycopg2 import IntegrityError as PostgresIntegrityError
    PSYCOPG2_AVAILABLE = True
except ImportError:
    psycopg2 = None
    PostgresIntegrityError = Exception
    PSYCOPG2_AVAILABLE = False

# استيراد مدير التشفير
try:
    from backend.utils.encryption_utils import encrypt_key, decrypt_key
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False

# إضافة مسار config للوصول إلى unified_settings
sys.path.insert(0, str(Path(__file__).parent.parent / 'config'))

try:
    from unified_settings import settings, get_database_engine, get_database_url
    USE_UNIFIED_SETTINGS = True
except ImportError:
    USE_UNIFIED_SETTINGS = False

# ==================== Mixin imports (God Object split) ====================
from database.db_trading_mixin import DbTradingMixin
from database.db_users_mixin import DbUsersMixin
from database.db_portfolio_mixin import DbPortfolioMixin
from database.db_notifications_mixin import DbNotificationsMixin


POSTGRES_UPSERT_CONFLICTS = {
    'system_status': ['id'],
    'user_settings': ['user_id', 'is_demo'],
    'portfolio': ['user_id', 'is_demo'],
    'verification_codes': ['email'],
    'user_sessions': ['user_id'],
    'user_devices': ['user_id', 'device_id'],
    'biometric_auth': ['user_id'],
    'pending_verifications': ['user_id', 'action'],
    'user_binance_keys': ['user_id'],
    'successful_coins': ['symbol'],
    'active_positions': ['user_id', 'symbol', 'strategy', 'is_demo'],
    'trading_signals': ['symbol', 'strategy', 'timeframe'],
    'portfolio_growth_history': ['user_id', 'date', 'is_demo'],
    'coin_states': ['symbol'],
}

POSTGRES_BOOLEAN_COLUMNS = {
    'is_active',
    'is_demo',
    'is_read',
    'trading_enabled',
    'is_running',
    'is_processed',
    'email_verified',
    'is_phone_verified',
    'notifications_enabled',
    'verified',
    'resolved',
    'requires_admin',
    'read',
}


def _replace_qmark_params(sql: str) -> str:
    out = []
    in_single = False
    in_double = False
    for ch in sql:
        if ch == "'" and not in_double:
            in_single = not in_single
            out.append(ch)
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            out.append(ch)
            continue
        if ch == '?' and not in_single and not in_double:
            out.append('%s')
        else:
            out.append(ch)
    return ''.join(out)


def _translate_datetime_literals(sql: str) -> str:
    replacements = {
        "datetime('now')": 'CURRENT_TIMESTAMP',
        'datetime("now")': 'CURRENT_TIMESTAMP',
        "DATE('now')": 'CURRENT_DATE',
        'DATE("now")': 'CURRENT_DATE',
        "datetime('now', '+7 days')": "CURRENT_TIMESTAMP + INTERVAL '7 days'",
        'datetime("now", "+7 days")': "CURRENT_TIMESTAMP + INTERVAL '7 days'",
        "datetime('now', '-7 days')": "CURRENT_TIMESTAMP - INTERVAL '7 days'",
        "datetime('now', '-30 days')": "CURRENT_TIMESTAMP - INTERVAL '30 days'",
        "datetime('now', '-3 days')": "CURRENT_TIMESTAMP - INTERVAL '3 days'",
        "datetime('now', '-24 hours')": "CURRENT_TIMESTAMP - INTERVAL '24 hours'",
        "datetime('now', '-1 hour')": "CURRENT_TIMESTAMP - INTERVAL '1 hour'",
    }
    for old, new in replacements.items():
        sql = sql.replace(old, new)
    def _replace_relative_now(match: re.Match) -> str:
        sign = match.group(1)
        amount = match.group(2)
        unit = match.group(3).lower()
        normalized_unit = unit if unit.endswith('s') else f'{unit}s'
        operator = '+' if sign == '+' else '-'
        return f"CURRENT_TIMESTAMP {operator} INTERVAL '{amount} {normalized_unit}'"

    sql = re.sub(
        r"""datetime\(\s*['"]now['"]\s*,\s*['"]([+-])(\d+)\s*(day|days|hour|hours|minute|minutes)['"]\s*\)""",
        _replace_relative_now,
        sql,
        flags=re.IGNORECASE,
    )
    sql = re.sub(r"""datetime\(\s*['"]now['"]\s*\)""", 'CURRENT_TIMESTAMP', sql, flags=re.IGNORECASE)
    sql = re.sub(r"""date\(\s*['"]now['"]\s*\)""", 'CURRENT_DATE', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bdatetime\(\s*([a-zA-Z_][a-zA-Z0-9_\.]*)\s*\)', r'\1', sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bDATE\(\s*([a-zA-Z_][a-zA-Z0-9_\.]*)\s*\)', r'\1::date', sql, flags=re.IGNORECASE)
    return sql


def _translate_boolean_literal_comparisons(sql: str) -> str:
    for col in POSTGRES_BOOLEAN_COLUMNS:
        sql = re.sub(rf'\b{re.escape(col)}\s*=\s*1\b', f'{col} = TRUE', sql, flags=re.IGNORECASE)
        sql = re.sub(rf'\b{re.escape(col)}\s*=\s*0\b', f'{col} = FALSE', sql, flags=re.IGNORECASE)
        sql = re.sub(rf'\b{re.escape(col)}\s*<>\s*1\b', f'{col} <> TRUE', sql, flags=re.IGNORECASE)
        sql = re.sub(rf'\b{re.escape(col)}\s*<>\s*0\b', f'{col} <> FALSE', sql, flags=re.IGNORECASE)
        sql = re.sub(rf'COALESCE\(\s*{re.escape(col)}\s*,\s*1\s*\)', f'COALESCE({col}, TRUE)', sql, flags=re.IGNORECASE)
        sql = re.sub(rf'COALESCE\(\s*{re.escape(col)}\s*,\s*0\s*\)', f'COALESCE({col}, FALSE)', sql, flags=re.IGNORECASE)
    return sql


def _translate_insert_or_ignore(sql: str) -> Optional[str]:
    upper_sql = sql.upper()
    marker = 'INSERT OR IGNORE INTO '
    if marker not in upper_sql:
        return None
    idx = upper_sql.index(marker)
    rest = sql[idx + len(marker):]
    table_name = rest.split('(', 1)[0].strip().strip('"')
    prefix = sql[:idx]
    translated = prefix + 'INSERT INTO ' + rest
    return translated.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'


def _translate_insert_or_replace(sql: str) -> Optional[str]:
    upper_sql = sql.upper()
    marker = 'INSERT OR REPLACE INTO '
    if marker not in upper_sql:
        return None
    idx = upper_sql.index(marker)
    rest = sql[idx + len(marker):]
    table_name = rest.split('(', 1)[0].strip().strip('"')
    conflict_cols = POSTGRES_UPSERT_CONFLICTS.get(table_name)
    if not conflict_cols:
        return None
    col_section = rest.split('(', 1)[1].split(')', 1)[0]
    columns = [c.strip().strip('"') for c in col_section.split(',')]
    update_cols = [c for c in columns if c not in conflict_cols and c != 'id']
    prefix = sql[:idx]
    base = prefix + 'INSERT INTO ' + rest
    if update_cols:
        set_clause = ', '.join(f'{col} = EXCLUDED.{col}' for col in update_cols)
        return base.rstrip().rstrip(';') + f" ON CONFLICT ({', '.join(conflict_cols)}) DO UPDATE SET {set_clause}"
    return base.rstrip().rstrip(';') + f" ON CONFLICT ({', '.join(conflict_cols)}) DO NOTHING"


def _translate_sql_for_postgres(sql: str) -> Optional[str]:
    stripped = sql.strip()
    upper_sql = stripped.upper()
    if upper_sql.startswith('PRAGMA '):
        return None
    if upper_sql.startswith('BEGIN IMMEDIATE'):
        return None
    sql = _translate_datetime_literals(sql)
    sql = _translate_boolean_literal_comparisons(sql)
    translated = _translate_insert_or_replace(sql)
    if translated is None:
        translated = _translate_insert_or_ignore(sql)
    if translated is not None:
        sql = translated
    return _replace_qmark_params(sql)


def _coerce_postgres_boolean_params(sql: str, params):
    if not params:
        return params
    coerced = list(params)
    for col in POSTGRES_BOOLEAN_COLUMNS:
        pattern = re.compile(rf'\b{re.escape(col)}\s*=\s*%s\b', re.IGNORECASE)
        for match in pattern.finditer(sql):
            param_index = sql[:match.start()].count('%s')
            if param_index < len(coerced) and coerced[param_index] in (0, 1):
                coerced[param_index] = bool(coerced[param_index])
    return tuple(coerced)


def _normalize_postgres_param_value(value):
    if hasattr(value, 'item') and callable(getattr(value, 'item')):
        try:
            return value.item()
        except Exception:
            pass
    if isinstance(value, (list, tuple)):
        return type(value)(_normalize_postgres_param_value(item) for item in value)
    if isinstance(value, dict):
        return {key: _normalize_postgres_param_value(item) for key, item in value.items()}
    return value


def _normalize_postgres_params(params):
    if not params:
        return params
    if isinstance(params, dict):
        return {key: _normalize_postgres_param_value(value) for key, value in params.items()}
    return tuple(_normalize_postgres_param_value(value) for value in params)


class PostgresCursorWrapper:
    def __init__(self, cursor, connection_wrapper):
        self._cursor = cursor
        self._connection_wrapper = connection_wrapper
        self.lastrowid = None
        self._empty_result = False

    def execute(self, sql, params=None):
        translated_sql = _translate_sql_for_postgres(sql)
        if translated_sql is None:
            self._empty_result = True
            self.lastrowid = None
            return self
        try:
            self._empty_result = False
            normalized_params = _normalize_postgres_params(params or ())
            coerced_params = _coerce_postgres_boolean_params(translated_sql, normalized_params)
            self._cursor.execute(translated_sql, coerced_params)
            self.lastrowid = None
            normalized_sql = translated_sql.strip().upper()
            if self._cursor.description and normalized_sql.startswith('INSERT') and 'RETURNING' in normalized_sql:
                row = self._cursor.fetchone()
                if row is not None:
                    self.lastrowid = row[0] if not isinstance(row, dict) else row.get('id')
                    self._connection_wrapper._pending_prefetched_row = row
            return self
        except PostgresIntegrityError as e:
            from psycopg2 import IntegrityError as _PgIntegrityError
            raise _PgIntegrityError(str(e)) from e

    def fetchone(self):
        if self._empty_result:
            return None
        if self._connection_wrapper._pending_prefetched_row is not None:
            row = self._connection_wrapper._pending_prefetched_row
            self._connection_wrapper._pending_prefetched_row = None
            return row
        return self._cursor.fetchone()

    def fetchall(self):
        if self._empty_result:
            return []
        if self._connection_wrapper._pending_prefetched_row is not None:
            row = self._connection_wrapper._pending_prefetched_row
            self._connection_wrapper._pending_prefetched_row = None
            rest = self._cursor.fetchall()
            return [row] + rest
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount

    def __getattr__(self, name):
        return getattr(self._cursor, name)


class PostgresConnectionWrapper:
    def __init__(self, raw_conn):
        self._conn = raw_conn
        self.row_factory = None  # PostgreSQL DictCursor handles dict-like access
        self._pending_prefetched_row = None

    def execute(self, sql, params=None):
        cursor = self.cursor()
        translated_sql = _translate_sql_for_postgres(sql) if isinstance(sql, str) else sql
        if translated_sql and translated_sql.strip().upper().startswith('INSERT INTO '):
            table_name = translated_sql.split('INSERT INTO ', 1)[1].split('(', 1)[0].strip().strip('"')
            if table_name in {'users', 'active_positions'} and 'RETURNING' not in translated_sql.upper():
                translated_sql = translated_sql.rstrip().rstrip(';') + ' RETURNING id'
        return cursor.execute(translated_sql if translated_sql is not None else sql, params)

    def cursor(self):
        return PostgresCursorWrapper(self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor), self)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    @property
    def in_transaction(self):
        return self._conn.status != psycopg2.extensions.STATUS_READY

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()
        return False

    def __getattr__(self, name):
        return getattr(self._conn, name)


class DatabaseManager(DbTradingMixin, DbUsersMixin, DbPortfolioMixin, DbNotificationsMixin):
    """مدير قاعدة البيانات الموحد - محسن لتجنب التضارب"""
    
    # ✅ FIX: Singleton pattern لمنع تسريب الاتصالات
    _instance = None
    _initialized = False
    _singleton_lock = threading.Lock()
    
    def __new__(cls):
        """تأكد من وجود instance واحد فقط"""
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self):
        # ✅ FIX: منع إعادة التهيئة
        if DatabaseManager._initialized:
            return
            
        self.database_engine = 'postgresql'
        self.database_url = ''
             
        if USE_UNIFIED_SETTINGS:
            self.database_engine = get_database_engine()
            self.database_url = get_database_url()
        self._local = threading.local()
        self.logger = logging.getLogger(__name__)
        self._postgres_dsn = self._build_postgres_dsn()
        
        # نظام منع التضارب
        self._write_lock = threading.RLock()
        self._connection_pool = queue.Queue(maxsize=10)
        self._pool_initialized = False

        if not self.is_postgres():
            raise RuntimeError(
                f"Unsupported DATABASE_ENGINE='{self.database_engine}'. This project now runs in PostgreSQL-only mode."
            )

        self.logger.info("✅ DATABASE_ENGINE=postgresql enabled - using PostgreSQL runtime path")
         
        self._init_database()
        self._init_connection_pool()
        self._apply_migrations()  # تطبيق أي migrations مطلوبة
        
        DatabaseManager._initialized = True
        self.logger.info("✅ DatabaseManager initialized (Singleton)")
    
    def _init_database(self):
        """تهيئة قاعدة البيانات - PostgreSQL فقط."""
        self.logger.info(
            "✅ PostgreSQL runtime detected - schema initialization is managed by postgres_schema.sql and runtime migrations"
        )
        return
    
    def _init_connection_pool(self):
        """تهيئة مجموعة الاتصالات لتجنب التضارب"""
        try:
            for _ in range(5):  # 5 اتصالات في المجموعة
                conn = self._build_connection(timeout=30.0)
                self._connection_pool.put(conn, block=False)

            self.logger.info("✅ تم تهيئة مجموعة الاتصالات بنجاح")
            return
        except Exception as e:
            self.logger.error(f"خطأ في تهيئة مجموعة الاتصالات: {e}")

    def _build_postgres_dsn(self) -> str:
        if not self.is_postgres():
            return ''
        if self.database_url:
            return self.database_url
        host = os.getenv('POSTGRES_HOST', '127.0.0.1').strip()
        port = os.getenv('POSTGRES_PORT', '5432').strip()
        db_name = os.getenv('POSTGRES_DB', 'trading_ai_bot').strip()
        user = os.getenv('POSTGRES_USER', 'trading_user').strip()
        password = os.getenv('POSTGRES_PASSWORD', 'change-this-password')
        return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"

    def _connect_postgres(self, timeout: float = 60.0) -> PostgresConnectionWrapper:
        if not PSYCOPG2_AVAILABLE:
            raise RuntimeError("psycopg2 is required for PostgreSQL runtime")
        dsn = self._postgres_dsn or self._build_postgres_dsn()
        parsed = urlparse(dsn)
        raw_conn = psycopg2.connect(
            dbname=(parsed.path or '/').lstrip('/'),
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname,
            port=parsed.port or 5432,
            connect_timeout=max(1, int(timeout)),
        )
        raw_conn.autocommit = False
        return PostgresConnectionWrapper(raw_conn)

    def _build_connection(self, timeout: float = 60.0):
        """إنشاء اتصال PostgreSQL موحّد الإعدادات لكل مسارات القراءة/الكتابة."""
        return self._connect_postgres(timeout=timeout)

    def is_sqlite(self) -> bool:
        """Always False — PostgreSQL only."""
        return False

    def is_postgres(self) -> bool:
        """هل المحرك الحالي PostgreSQL؟"""
        return self.database_engine in {'postgres', 'postgresql'}

    def _migrate_user_settings_unique_constraint(self, conn):
        """Legacy SQLite migration — no-op on PostgreSQL."""
        return

    def _migrate_portfolio_unique_constraint(self, conn):
        """Legacy SQLite migration — no-op on PostgreSQL."""
        return

    def _migrate_active_positions_unique_constraint(self, conn):
        """Legacy SQLite migration — no-op on PostgreSQL."""
        return

    def _apply_migrations(self):
        """تطبيق أي migrations مطلوبة على قاعدة البيانات — PostgreSQL only."""
        self._apply_postgres_runtime_migrations()

    def _apply_postgres_runtime_migrations(self):
        """Apply lightweight compatibility migrations for existing PostgreSQL databases."""
        try:
            with self.get_write_connection() as conn:
                conn.execute("ALTER TABLE system_status ADD COLUMN IF NOT EXISTS message TEXT DEFAULT ''")
                conn.execute("ALTER TABLE system_status ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ")
                conn.execute("ALTER TABLE system_status ADD COLUMN IF NOT EXISTS pid INTEGER")
                conn.execute("ALTER TABLE system_status ADD COLUMN IF NOT EXISTS session_id TEXT")
                conn.execute("ALTER TABLE system_status ADD COLUMN IF NOT EXISTS mode TEXT DEFAULT 'demo'")
                conn.execute("ALTER TABLE system_status ADD COLUMN IF NOT EXISTS initiated_by TEXT")
                conn.execute("ALTER TABLE system_status ADD COLUMN IF NOT EXISTS subsystem_status TEXT DEFAULT '{}' ")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS admin_notification_settings (
                        id BIGINT PRIMARY KEY,
                        telegram_enabled BOOLEAN DEFAULT FALSE,
                        telegram_bot_token TEXT,
                        telegram_chat_id TEXT,
                        email_enabled BOOLEAN DEFAULT FALSE,
                        admin_email TEXT,
                        webhook_enabled BOOLEAN DEFAULT FALSE,
                        webhook_url TEXT,
                        push_enabled BOOLEAN DEFAULT TRUE,
                        notify_on_error BOOLEAN DEFAULT TRUE,
                        notify_on_trade BOOLEAN DEFAULT TRUE,
                        notify_on_warning BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("INSERT INTO admin_notification_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS security_audit_log (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
                        action TEXT NOT NULL,
                        resource TEXT,
                        ip_address TEXT,
                        user_agent TEXT,
                        status TEXT DEFAULT 'success',
                        details TEXT,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS system_alerts (
                        id BIGSERIAL PRIMARY KEY,
                        alert_type TEXT DEFAULT 'general',
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        severity TEXT DEFAULT 'info',
                        data TEXT,
                        read BOOLEAN DEFAULT FALSE,
                        resolved BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS coin_states (
                        symbol TEXT PRIMARY KEY,
                        state TEXT NOT NULL,
                        position_size_multiplier DOUBLE PRECISION DEFAULT 1.0,
                        stop_loss_multiplier DOUBLE PRECISION DEFAULT 1.0,
                        consecutive_wins INTEGER DEFAULT 0,
                        consecutive_losses INTEGER DEFAULT 0,
                        total_trades INTEGER DEFAULT 0,
                        winning_trades INTEGER DEFAULT 0,
                        total_pnl DOUBLE PRECISION DEFAULT 0.0,
                        blacklist_until TEXT,
                        last_updated TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS coin_trade_history (
                        id BIGSERIAL PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        entry_time TEXT NOT NULL,
                        exit_time TEXT NOT NULL,
                        pnl DOUBLE PRECISION NOT NULL,
                        profit_pct DOUBLE PRECISION NOT NULL,
                        exit_reason TEXT,
                        strategy TEXT,
                        timeframe TEXT,
                        market_regime TEXT
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS trade_learning_log (
                        id BIGSERIAL PRIMARY KEY,
                        symbol TEXT NOT NULL,
                        side TEXT NOT NULL,
                        entry_price DOUBLE PRECISION NOT NULL,
                        exit_price DOUBLE PRECISION NOT NULL,
                        pnl DOUBLE PRECISION NOT NULL,
                        pnl_pct DOUBLE PRECISION NOT NULL,
                        exit_reason TEXT NOT NULL,
                        sl_pct_used DOUBLE PRECISION DEFAULT 0.01,
                        hold_minutes INTEGER DEFAULT 0,
                        open_positions_count INTEGER DEFAULT 1,
                        hour_of_day INTEGER DEFAULT 0,
                        day_of_week TEXT DEFAULT '',
                        rsi DOUBLE PRECISION,
                        macd DOUBLE PRECISION,
                        bb_position DOUBLE PRECISION,
                        volume_ratio DOUBLE PRECISION,
                        ema_trend TEXT,
                        atr_pct DOUBLE PRECISION,
                        trend_4h TEXT,
                        score DOUBLE PRECISION,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tll_symbol ON trade_learning_log(symbol)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tll_created ON trade_learning_log(created_at)")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS learning_validation_log (
                        id BIGSERIAL PRIMARY KEY,
                        validated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        total_trades INTEGER NOT NULL,
                        trades_with_indicators INTEGER NOT NULL,
                        holdout_size INTEGER NOT NULL,
                        scorer_accuracy DOUBLE PRECISION NOT NULL,
                        scorer_precision DOUBLE PRECISION,
                        baseline_accuracy DOUBLE PRECISION NOT NULL,
                        lift DOUBLE PRECISION NOT NULL,
                        factor_weights TEXT,
                        factor_accuracies TEXT,
                        verdict TEXT NOT NULL,
                        details TEXT
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS signal_learning (
                        id BIGSERIAL PRIMARY KEY,
                        signal_id TEXT NOT NULL UNIQUE,
                        user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                        combination TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        strategy TEXT NOT NULL,
                        timeframe TEXT NOT NULL,
                        entry_price DOUBLE PRECISION,
                        entry_rsi DOUBLE PRECISION,
                        entry_macd DOUBLE PRECISION,
                        entry_volume DOUBLE PRECISION,
                        market_regime TEXT,
                        volatility DOUBLE PRECISION,
                        support_distance DOUBLE PRECISION,
                        resistance_distance DOUBLE PRECISION,
                        actual_profit_pct DOUBLE PRECISION,
                        exit_reason TEXT,
                        signal_quality_score DOUBLE PRECISION,
                        was_correct INTEGER,
                        holding_time_minutes INTEGER,
                        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_learning_combo ON signal_learning(combination, timestamp DESC)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_learning_quality ON signal_learning(signal_quality_score DESC)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_learning_user ON signal_learning(user_id, timestamp DESC)")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_onboarding (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        step TEXT NOT NULL,
                        shown_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        dismissed_at TIMESTAMPTZ,
                        UNIQUE(user_id, step)
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS biometric_auth (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        biometric_hash TEXT,
                        device_id TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    ALTER TABLE biometric_auth
                    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                """)
                conn.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS ux_biometric_auth_user
                    ON biometric_auth(user_id)
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_devices (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        device_id TEXT,
                        device_type TEXT,
                        device_name TEXT,
                        os_version TEXT,
                        app_version TEXT,
                        push_token TEXT,
                        fcm_token TEXT,
                        is_trusted BOOLEAN DEFAULT TRUE,
                        device_model TEXT,
                        is_active BOOLEAN DEFAULT TRUE,
                        last_login TIMESTAMPTZ,
                        last_active_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS ux_user_devices_user_device
                    ON user_devices(user_id, device_id)
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS pending_verifications (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        action TEXT NOT NULL,
                        otp TEXT NOT NULL,
                        expires_at TIMESTAMPTZ,
                        method TEXT DEFAULT 'email',
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS password_reset_requests (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        token TEXT NOT NULL,
                        used BOOLEAN DEFAULT FALSE,
                        expires_at TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS trading_history (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        symbol TEXT NOT NULL,
                        side TEXT,
                        entry_price DOUBLE PRECISION,
                        exit_price DOUBLE PRECISION,
                        quantity DOUBLE PRECISION,
                        profit_loss DOUBLE PRECISION DEFAULT 0,
                        profit_pct DOUBLE PRECISION DEFAULT 0,
                        status TEXT DEFAULT 'closed',
                        entry_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        exit_time TIMESTAMPTZ,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ml_training_data (
                        id BIGSERIAL PRIMARY KEY,
                        symbol TEXT,
                        strategy TEXT,
                        timeframe TEXT,
                        entry_price DOUBLE PRECISION,
                        exit_price DOUBLE PRECISION,
                        profit_loss DOUBLE PRECISION DEFAULT 0,
                        is_winning BOOLEAN DEFAULT FALSE,
                        source TEXT DEFAULT 'runtime',
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ml_training_history (
                        id BIGSERIAL PRIMARY KEY,
                        cycle_number INTEGER DEFAULT 0,
                        total_samples INTEGER DEFAULT 0,
                        accuracy DOUBLE PRECISION DEFAULT 0,
                        is_ready BOOLEAN DEFAULT FALSE,
                        status TEXT DEFAULT 'pending',
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ml_models (
                        id BIGSERIAL PRIMARY KEY,
                        model_name TEXT,
                        accuracy DOUBLE PRECISION DEFAULT 0,
                        is_best BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS backtest_vs_reality (
                        id BIGSERIAL PRIMARY KEY,
                        symbol TEXT,
                        strategy TEXT,
                        timeframe TEXT,
                        backtest_win_rate DOUBLE PRECISION DEFAULT 0,
                        actual_result DOUBLE PRECISION DEFAULT 0,
                        reliability_score DOUBLE PRECISION DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS combo_reliability (
                        id BIGSERIAL PRIMARY KEY,
                        symbol TEXT,
                        strategy TEXT,
                        timeframe TEXT,
                        total_trades INTEGER DEFAULT 0,
                        actual_win_rate DOUBLE PRECISION DEFAULT 0,
                        reliability_score DOUBLE PRECISION DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS operation_log (
                        id BIGSERIAL PRIMARY KEY,
                        operation_type TEXT,
                        operation_name TEXT,
                        status TEXT DEFAULT 'started',
                        start_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        end_time TIMESTAMPTZ,
                        details TEXT
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS dynamic_blacklist (
                        id BIGSERIAL PRIMARY KEY,
                        user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
                        symbol TEXT NOT NULL,
                        reason TEXT,
                        added_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        expires_at TIMESTAMPTZ
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS agent_memory (
                        id BIGSERIAL PRIMARY KEY,
                        memory_type TEXT,
                        category TEXT,
                        symbol TEXT,
                        title TEXT,
                        content TEXT,
                        confidence DOUBLE PRECISION DEFAULT 0,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ml_patterns (
                        id BIGSERIAL PRIMARY KEY,
                        pattern_name TEXT,
                        pattern_data TEXT,
                        success_rate DOUBLE PRECISION DEFAULT 0,
                        frequency INTEGER DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ml_quality_metrics (
                        id BIGSERIAL PRIMARY KEY,
                        metric_type TEXT,
                        total_validated INTEGER DEFAULT 0,
                        valid_count INTEGER DEFAULT 0,
                        validity_rate DOUBLE PRECISION DEFAULT 0,
                        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("""
                    DELETE FROM user_settings us
                    WHERE us.id IN (
                        SELECT id FROM (
                            SELECT id,
                                   ROW_NUMBER() OVER (
                                       PARTITION BY user_id, is_demo
                                       ORDER BY COALESCE(updated_at, created_at) DESC, id DESC
                                   ) AS rn
                            FROM user_settings
                        ) ranked
                        WHERE rn > 1
                    )
                """)
                conn.execute("""
                    DELETE FROM portfolio p
                    WHERE p.id IN (
                        SELECT id FROM (
                            SELECT id,
                                   ROW_NUMBER() OVER (
                                       PARTITION BY user_id, is_demo
                                       ORDER BY COALESCE(updated_at, created_at) DESC, id DESC
                                   ) AS rn
                            FROM portfolio
                        ) ranked
                        WHERE rn > 1
                    )
                """)
                conn.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS ux_user_settings_user_mode
                    ON user_settings(user_id, is_demo)
                """)
                conn.execute("""
                    CREATE UNIQUE INDEX IF NOT EXISTS ux_portfolio_user_mode
                    ON portfolio(user_id, is_demo)
                """)
                conn.execute("""
                    INSERT INTO user_settings (
                        user_id, is_demo, trading_enabled, trade_amount,
                        position_size_percentage, stop_loss_pct, take_profit_pct,
                        trailing_distance, max_positions, risk_level, max_daily_loss_pct,
                        trading_mode, created_at, updated_at
                    )
                    SELECT
                        u.id, FALSE, FALSE, 100.0,
                        10.0, 2.0, 5.0,
                        3.0, 5, 'medium', 10.0,
                        'real', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    FROM users u
                    WHERE NOT EXISTS (
                        SELECT 1 FROM user_settings s WHERE s.user_id = u.id AND s.is_demo = FALSE
                    )
                """)
                conn.execute("""
                    INSERT INTO user_settings (
                        user_id, is_demo, trading_enabled, trade_amount,
                        position_size_percentage, stop_loss_pct, take_profit_pct,
                        trailing_distance, max_positions, risk_level, max_daily_loss_pct,
                        trading_mode, created_at, updated_at
                    )
                    SELECT
                        u.id, TRUE, FALSE, 100.0,
                        10.0, 2.0, 5.0,
                        3.0, 5, 'medium', 10.0,
                        'demo', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    FROM users u
                    WHERE u.user_type = 'admin'
                      AND NOT EXISTS (
                        SELECT 1 FROM user_settings s WHERE s.user_id = u.id AND s.is_demo = TRUE
                    )
                """)
                conn.execute("""
                    INSERT INTO portfolio (
                        user_id, total_balance, available_balance, invested_balance,
                        total_profit_loss, total_profit_loss_percentage, initial_balance,
                        is_demo, created_at, updated_at
                    )
                    SELECT
                        u.id, 0.0, 0.0, 0.0,
                        0.0, 0.0, 0.0,
                        FALSE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    FROM users u
                    WHERE NOT EXISTS (
                        SELECT 1 FROM portfolio p WHERE p.user_id = u.id AND p.is_demo = FALSE
                    )
                """)
                conn.execute("""
                    INSERT INTO portfolio (
                        user_id, total_balance, available_balance, invested_balance,
                        total_profit_loss, total_profit_loss_percentage, initial_balance,
                        is_demo, created_at, updated_at
                    )
                    SELECT
                        u.id, 10000.0, 10000.0, 0.0,
                        0.0, 0.0, 10000.0,
                        TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    FROM users u
                    WHERE u.user_type = 'admin'
                      AND NOT EXISTS (
                        SELECT 1 FROM portfolio p WHERE p.user_id = u.id AND p.is_demo = TRUE
                    )
                """)
                conn.execute("""
                    UPDATE portfolio
                    SET initial_balance = CASE
                        WHEN COALESCE(total_balance, 0) > 0 THEN total_balance
                        WHEN COALESCE(available_balance, 0) > 0 THEN available_balance
                        ELSE 1000
                    END
                    WHERE initial_balance IS NULL OR initial_balance <= 0
                """)
                conn.execute("""
                    INSERT INTO operation_log (operation_type, operation_name, status, start_time, details)
                    SELECT 'system', 'bootstrap', 'ok', CURRENT_TIMESTAMP, 'runtime migration bootstrap'
                    WHERE NOT EXISTS (SELECT 1 FROM operation_log)
                """)
            self.logger.info("✅ PostgreSQL runtime migrations applied")
        except Exception as e:
            self.logger.warning(f"⚠️ PostgreSQL runtime migration warning: {e}")
    
    def _get_pooled_connection(self):
        """الحصول على اتصال جديد (بدون Pool للحصول على بيانات فورية)"""
        # إنشاء اتصال جديد في كل مرة لضمان الحصول على البيانات الفورية
        conn = self._build_connection(timeout=60.0)
        return conn
    
    def _return_pooled_connection(self, conn):
        """إرجاع الاتصال إلى pool للاستخدام المستقبلي"""
        if conn is None:
            return
        try:
            # التحقق من أن الاتصال لا يزال مفتوحاً
            if conn.in_transaction:
                conn.commit()
            # إعادة الاتصال إلى pool
            self._connection_pool.put(conn, block=False)
        except queue.Full:
            try:
                conn.close()
            except Exception:
                pass
        except Exception as e:
            self.logger.warning(f"⚠️ خطأ في إرجاع الاتصال للـ pool: {e}")
            try:
                conn.close()
            except Exception:
                pass
    
    @contextmanager
    def get_connection(self):
        """الحصول على اتصال جديد مباشرة (بدون pool)"""
        conn = None
        try:
            conn = self._build_connection(timeout=60.0)
            yield conn
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
    
    @contextmanager 
    def get_write_connection(self):
        """اتصال محمي للكتابة لتجنب التضارب"""
        with self._write_lock:
            conn = None
            try:
                conn = self._build_connection(timeout=60.0)
                yield conn
                conn.commit()
            except Exception as e:
                if conn:
                    conn.rollback()
                self.logger.error(f"خطأ في عملية الكتابة: {e}")
                raise
            finally:
                if conn:
                    self._return_pooled_connection(conn)
    
    # ==================== حالة النظام العامة ====================
    
    def update_system_status(self, status: str, **kwargs):
        """تحديث حالة النظام العامة"""
        with self.get_write_connection() as conn:
            update_fields = ["status = ?", "last_update = CURRENT_TIMESTAMP"]
            values = [status]
            
            for key, value in kwargs.items():
                if key in ['group_b_status', 'total_coins_analyzed', 'successful_coins_count', 'system_uptime_seconds',
                          'trading_status', 'database_status']:
                    update_fields.append(f"{key} = ?")
                    values.append(value)
            
            query = f"UPDATE system_status SET {', '.join(update_fields)} WHERE id = 1"
            conn.execute(query, values)
            self.logger.info(f"تم تحديث حالة النظام: {status}")
    
    def get_system_status(self) -> Dict[str, Any]:
        """الحصول على حالة النظام العامة"""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM system_status WHERE id = 1").fetchone()
            if row:
                return dict(row)
            return {}

    # ==================== سجل الأنشطة ====================
    
    def log_activity(self, component: str, action: str, details: str = None, status: str = 'success', user_id: int = None):
        """تسجيل نشاط في السجل"""
        with self.get_write_connection() as conn:
            conn.execute("""
                INSERT INTO activity_logs (user_id, component, action, details, status)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, component, action, details, status))
    
    def get_recent_activities(self, limit: int = 100, user_id: int = None) -> List[Dict[str, Any]]:
        """الحصول على الأنشطة الأخيرة"""
        with self.get_connection() as conn:
            if user_id:
                rows = conn.execute("""
                    SELECT * FROM activity_logs 
                    WHERE user_id = ? OR user_id IS NULL
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (user_id, limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM activity_logs 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (limit,)).fetchall()
        
        return [dict(row) for row in rows]
    
    # ==================== إحصائيات السوق (مؤقتاً من system_status) ====================
    
    # ملاحظة: تم حذف دوال market_stats لأن الجدول غير موجود في قاعدة البيانات الحالية
    # يمكن إضافة الجدول لاحقاً إذا لزم الأمر
    
    def get_market_stats(self) -> Dict[str, Any]:
        """الحصول على إحصائيات السوق - مؤقتاً من system_status"""
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM system_status WHERE id = 1").fetchone()
            if row:
                return {
                    'total_coins_analyzed': row.get('total_coins_analyzed', 0),
                    'successful_coins_count': row.get('successful_coins_count', 0),
                    'market_sentiment': 'neutral',
                    'active_pairs_count': row.get('successful_coins_count', 0)
                }
        return {}
    
    # ==================== وظائف مساعدة ====================
    
    def cleanup_old_data(self, days: int = 30):
        """تنظيف البيانات القديمة"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        with self.get_write_connection() as conn:
            # تنظيف الإشارات القديمة المعالجة
            conn.execute("""
                DELETE FROM trading_signals 
                WHERE is_processed = TRUE AND generated_at < ?
            """, (cutoff_date,))
            
            # تنظيف سجل الأنشطة القديم
            conn.execute("""
                DELETE FROM activity_logs WHERE created_at < ?
            """, (cutoff_date,))
            
            self.logger.info(f"تم تنظيف البيانات الأقدم من {days} يوم")
    
    def get_database_stats(self) -> Dict[str, int]:
        """الحصول على إحصائيات قاعدة البيانات"""
        with self.get_connection() as conn:
            stats = {}
            
            tables = ['users', 'successful_coins', 'user_trades', 'trading_signals', 'activity_logs']
            for table in tables:
                count = conn.execute(f"SELECT COUNT(*) as count FROM {table}").fetchone()['count']
                stats[table] = count
            
            return stats
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """الحصول على قائمة جميع المستخدمين"""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT id, username, email, user_type, created_at 
                FROM users 
                ORDER BY created_at DESC
            """).fetchall()
            return [dict(row) for row in rows]
    
    def get_active_users(self) -> List[Dict[str, Any]]:
        """الحصول على قائمة المستخدمين النشطين"""
        with self.get_connection() as conn:
            rows = conn.execute("""
                SELECT id, username, email FROM users WHERE is_active = 1
            """).fetchall()
            return [dict(row) for row in rows]
    
    def execute_query(self, query: str, params: tuple = (), max_retries: int = 3):
        """تنفيذ استعلام SQL عام مع retry mechanism"""
        import time
        
        for attempt in range(max_retries):
            try:
                if query.strip().upper().startswith('SELECT'):
                    with self.get_connection() as conn:
                        rows = conn.execute(query, params).fetchall()
                        return [dict(row) for row in rows]
                else:
                    with self.get_write_connection() as conn:
                        cursor = conn.execute(query, params)
                        return cursor.rowcount
            except Exception as e:
                if 'database is locked' in str(e).lower() and attempt < max_retries - 1:
                    self.logger.warning(f"⚠️ Database locked, retry {attempt + 1}/{max_retries}")
                    time.sleep(0.5 * (attempt + 1))  # تأخير تصاعدي
                    continue
                raise
    # ==================== النظام ====================
    
    def reset_user_account_data(self, user_id: int) -> bool:
        """إعادة ضبط بيانات حساب المستخدم"""
        try:
            with self.get_write_connection() as conn:
                # إعادة ضبط المحفظة باستخدام الأعمدة الموجودة فعلياً
                portfolio_row = conn.execute("""
                    SELECT initial_balance FROM portfolio WHERE user_id = ? ORDER BY is_demo DESC, updated_at DESC LIMIT 1
                """, (user_id,)).fetchone()
                initial_balance = float(portfolio_row[0] or 0.0) if portfolio_row else 0.0
                conn.execute("""
                    UPDATE portfolio 
                    SET total_balance = ?, available_balance = ?,
                        invested_balance = 0.0,
                        total_profit_loss = 0.0,
                        total_profit_loss_percentage = 0.0,
                        total_trades = 0, winning_trades = 0, losing_trades = 0,
                        initial_balance = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (initial_balance, initial_balance, initial_balance, user_id))
                
                # حذف المراكز من active_positions
                conn.execute("DELETE FROM active_positions WHERE user_id = ?", (user_id,))
                
                # إعادة ضبط الإعدادات للافتراضية
                conn.execute("""
                    UPDATE user_settings 
                    SET trading_enabled = 0, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (user_id,))
                
                self.logger.info(f"تم إعادة ضبط بيانات المستخدم {user_id}")
                return True
                
        except Exception as e:
            self.logger.error(f"خطأ في إعادة ضبط بيانات المستخدم: {e}")
            return False
    
    def test_connection(self):
        """اختبار الاتصال بقاعدة البيانات"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            self.logger.error(f"خطأ في اختبار الاتصال: {e}")
            return False
    
    def get_total_users(self):
        """الحصول على إجمالي عدد المستخدمين"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM users")
                return cursor.fetchone()[0]
        except Exception as e:
            self.logger.error(f"خطأ في جلب عدد المستخدمين: {e}")
            return 0
    
    def get_active_trades_count(self):
        """الحصول على عدد الصفقات النشطة"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM active_positions")
                return cursor.fetchone()[0]
        except Exception as e:
            self.logger.error(f"خطأ في جلب عدد الصفقات النشطة: {e}")
            return 0
    
    def get_total_trades_count(self):
        """الحصول على إجمالي عدد الصفقات"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM active_positions")
                return cursor.fetchone()[0]
        except Exception as e:
            self.logger.error(f"خطأ في جلب إجمالي الصفقات: {e}")
            return 0
    
    def get_successful_coins_count(self):
        """الحصول على عدد العملات الناجحة"""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM successful_coins")
                return cursor.fetchone()[0]
        except Exception as e:
            self.logger.error(f"خطأ في جلب عدد العملات الناجحة: {e}")
            return 0
    
    def close(self):
        """إغلاق جميع الاتصالات"""
        try:
            # إغلاق جميع الاتصالات في المجموعة
            while not self._connection_pool.empty():
                try:
                    conn = self._connection_pool.get_nowait()
                    conn.close()
                except Exception:
                    pass
            self.logger.info("تم إغلاق جميع اتصالات قاعدة البيانات")
        except Exception as e:
            self.logger.error(f"خطأ في إغلاق الاتصالات: {e}")


# إنشاء مثيل مشترك
db_manager = DatabaseManager()
