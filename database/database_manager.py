"""
مدير قاعدة البيانات الموحد
يوفر واجهة موحدة للتفاعل مع قاعدة البيانات
يستخدم من قبل النظام الخلفي وواجهة المستخدم
"""

import sqlite3
import json
import logging
import time
import queue
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
from contextlib import contextmanager
from threading import Lock
import threading

# استيراد Foreign Keys helper
try:
    from database.ensure_foreign_keys import get_db_connection
    FK_HELPER_AVAILABLE = True
except ImportError:
    FK_HELPER_AVAILABLE = False

# استيراد مدير التشفير
try:
    from backend.utils.encryption_utils import encrypt_key, decrypt_key
    ENCRYPTION_AVAILABLE = True
except ImportError:
    ENCRYPTION_AVAILABLE = False

# إضافة مسار config للوصول إلى unified_settings
sys.path.insert(0, str(Path(__file__).parent.parent / 'config'))

try:
    from unified_settings import settings, get_database_path
    USE_UNIFIED_SETTINGS = True
except ImportError:
    USE_UNIFIED_SETTINGS = False

# ==================== Mixin imports (God Object split) ====================
from database.db_trading_mixin import DbTradingMixin
from database.db_users_mixin import DbUsersMixin
from database.db_portfolio_mixin import DbPortfolioMixin
from database.db_notifications_mixin import DbNotificationsMixin


class DatabaseManager(DbTradingMixin, DbUsersMixin, DbPortfolioMixin, DbNotificationsMixin):
    """مدير قاعدة البيانات الموحد - محسن لتجنب التضارب"""
    
    # ✅ FIX: Singleton pattern لمنع تسريب الاتصالات
    _instance = None
    _initialized = False
    _singleton_lock = threading.Lock()
    
    def __new__(cls, db_path: str = None):
        """تأكد من وجود instance واحد فقط"""
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance
    
    def __init__(self, db_path: str = None):
        # ✅ FIX: منع إعادة التهيئة
        if DatabaseManager._initialized:
            return
            
        if db_path is None:
            if USE_UNIFIED_SETTINGS:
                db_path = get_database_path()
            else:
                # مسار نسبي كبديل
                db_path = str(Path(__file__).parent / 'trading_database.db')
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._local = threading.local()
        self.logger = logging.getLogger(__name__)
        
        # نظام منع التضارب
        self._write_lock = threading.RLock()
        self._connection_pool = queue.Queue(maxsize=10)
        self._pool_initialized = False
        
        self._init_database()
        self._init_connection_pool()
        self._apply_migrations()  # تطبيق أي migrations مطلوبة
        
        DatabaseManager._initialized = True
        self.logger.info("✅ DatabaseManager initialized (Singleton)")
    
    def _init_database(self):
        """تهيئة قاعدة البيانات - بدون أي تعديلات على البيانات الموجودة"""
        try:
            # فحص ما إذا كانت قاعدة البيانات موجودة بالفعل
            if self.db_path.exists():
                self.logger.info("✅ قاعدة البيانات موجودة مسبقاً - بدون أي تعديلات")
                # لا نفعل أي شيء - قاعدة البيانات معزولة تماماً
                return
            
            # إنشاء قاعدة البيانات فقط إذا لم تكن موجودة (مرة واحدة فقط)
            self.logger.info("📝 إنشاء قاعدة البيانات الجديدة...")
            if FK_HELPER_AVAILABLE:
                with get_db_connection(str(self.db_path)) as conn:
                    pass  # FK enabled automatically
            else:
                with sqlite3.connect(self.db_path, timeout=60.0, check_same_thread=False) as conn:
                    # تفعيل foreign keys
                    conn.execute("PRAGMA foreign_keys = ON")
                
                # تفعيل WAL mode لتجنب التضارب
                conn.execute("PRAGMA journal_mode = WAL")
                
                # تحسين الأداء وتقليل التضارب
                conn.execute("PRAGMA synchronous = NORMAL")
                conn.execute("PRAGMA cache_size = -64000")  # 64MB cache (أفضل أداء)
                conn.execute("PRAGMA temp_store = MEMORY")
                conn.execute("PRAGMA mmap_size = 30000000000")  # memory-mapped I/O
                conn.execute("PRAGMA page_size = 4096")  # حجم صفحة محسّن
                conn.execute("PRAGMA busy_timeout = 30000")  # 30 ثانية (حل database locked)
                
                # إنشاء جدول verification_codes للتحقق من الإيميل
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS verification_codes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        email TEXT NOT NULL,
                        otp_code TEXT NOT NULL,
                        purpose TEXT DEFAULT 'verification',
                        created_at TEXT NOT NULL,
                        expires_at REAL NOT NULL,
                        attempts INTEGER DEFAULT 0,
                        verified BOOLEAN DEFAULT FALSE,
                        verified_at TEXT,
                        UNIQUE(email, purpose)
                    )
                """)
                
                # إضافة فهرس للبحث السريع
                conn.execute("CREATE INDEX IF NOT EXISTS idx_verification_email ON verification_codes(email)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_verification_expires ON verification_codes(expires_at)")
                
                # ✅ جدول أخبار العملات الرقمية (للحماية من التقلبات)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS crypto_news (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        symbol TEXT NOT NULL,
                        impact TEXT NOT NULL,
                        published_at TIMESTAMP NOT NULL,
                        source TEXT,
                        url TEXT,
                        votes INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute("CREATE INDEX IF NOT EXISTS idx_crypto_news_symbol ON crypto_news(symbol)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_crypto_news_published ON crypto_news(published_at)")
                
                # إنشاء جدول مراقبة الصفقات المفتوحة
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS active_positions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        symbol TEXT NOT NULL,
                        strategy TEXT NOT NULL,
                        timeframe TEXT NOT NULL,
                        position_type TEXT NOT NULL,
                        entry_date TEXT NOT NULL,
                        entry_price REAL,
                        quantity REAL,
                        stop_loss REAL,
                        take_profit REAL,
                        order_id TEXT,
                        entry_commission REAL DEFAULT 0,
                        exit_commission REAL DEFAULT 0,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, symbol, strategy)
                    )
                """)
                
                # إضافة فهارس للبحث السريع
                conn.execute("CREATE INDEX IF NOT EXISTS idx_active_positions_user ON active_positions(user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_active_positions_symbol ON active_positions(symbol)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_active_positions_active ON active_positions(is_active)")
                
                # ✅ Phase 1: إضافة فهارس إضافية للأداء
                # فهارس user_trades لتسريع الاستعلامات
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_trades_user_date ON user_trades(user_id, entry_time DESC)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_trades_status ON user_trades(user_id, status)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_trades_symbol ON user_trades(symbol)")
                
                # فهارس activity_logs للتقارير
                conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_logs_user_date ON activity_logs(user_id, timestamp DESC)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_activity_logs_action ON activity_logs(action, timestamp DESC)")
                
                # فهارس successful_coins (جدول مشترك - بدون user_id)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_successful_coins_symbol ON successful_coins(symbol, is_active)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_successful_coins_score ON successful_coins(score DESC, is_active)")
                
                # ✅ جداول جديدة: تتبع نمو المحفظة
                # جدول نمو المحفظة للمستخدمين العاديين والأدمن الحقيقي
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS portfolio_growth_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        date DATE NOT NULL,
                        total_balance REAL NOT NULL,
                        daily_pnl REAL NOT NULL,
                        daily_pnl_percentage REAL NOT NULL,
                        active_trades_count INTEGER DEFAULT 0,
                        is_demo INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                        UNIQUE(user_id, date, is_demo)
                    )
                """)
                
                # جدول نمو المحفظة الوهمية للأدمن (عزل تام)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS admin_demo_portfolio_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        admin_id INTEGER NOT NULL,
                        date DATE NOT NULL,
                        total_balance REAL NOT NULL,
                        daily_pnl REAL NOT NULL,
                        daily_pnl_percentage REAL NOT NULL,
                        active_trades_count INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE,
                        UNIQUE(admin_id, date)
                    )
                """)
                
                # إنشاء جدول حالة النظام
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS system_status (
                        id INTEGER PRIMARY KEY DEFAULT 1,
                        status TEXT DEFAULT 'running',
                        last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_running BOOLEAN DEFAULT 1,
                        group_b_status TEXT DEFAULT 'idle',
                        total_coins_analyzed INTEGER DEFAULT 0,
                        successful_coins_count INTEGER DEFAULT 0,
                        system_uptime_seconds INTEGER DEFAULT 0
                    )
                """)
                
                # إدراج صف افتراضي إذا لم يكن موجوداً
                conn.execute("""
                    INSERT OR IGNORE INTO system_status (id, status, is_running)
                    VALUES (1, 'running', 1)
                """)
                
                # فهارس للأداء
                conn.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_growth_user_date ON portfolio_growth_history(user_id, date DESC)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_admin_demo_portfolio_user_date ON admin_demo_portfolio_history(admin_id, date DESC)")
                
                # ✅ فهارس إضافية لتحسين الأداء على الجداول الحرجة
                # فهارس user_trades - للاستعلامات الشائعة
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_trades_user_demo_status ON user_trades(user_id, is_demo, status)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_trades_created_at ON user_trades(created_at DESC)")
                
                # فهارس active_positions - للاستعلامات الشائعة
                conn.execute("CREATE INDEX IF NOT EXISTS idx_active_positions_user_active ON active_positions(user_id, is_active)")
                
                # ✅ إضافة عمود signal_metadata (للتعلم التكيّفي)
                try:
                    conn.execute("ALTER TABLE active_positions ADD COLUMN signal_metadata TEXT DEFAULT NULL")
                except Exception:
                    pass  # العمود موجود بالفعل
                
                # ✅ إضافة عمود is_demo لجدول portfolio_growth_history (للقواعد الموجودة مسبقاً)
                try:
                    conn.execute("ALTER TABLE portfolio_growth_history ADD COLUMN is_demo INTEGER DEFAULT 0")
                except Exception:
                    pass  # العمود موجود بالفعل
                
                # فهارس portfolio - للاستعلامات الشائعة
                conn.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_user_demo ON portfolio(user_id, is_demo)")
                
                # فهارس users - للبحث السريع
                conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_users_user_type ON users(user_type)")
                
                # فهارس user_settings - للاستعلامات الشائعة
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id)")
                
                # فهارس user_binance_keys - للاستعلامات الشائعة
                conn.execute("CREATE INDEX IF NOT EXISTS idx_user_binance_keys_user_active ON user_binance_keys(user_id, is_active)")
                
                self.logger.info("✅ تم إنشاء جميع الفهارس لتحسين الأداء")
                
                # فحص إذا كانت قاعدة البيانات مهيأة مسبقاً
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
                tables_exist = cursor.fetchone() is not None
                
                if not tables_exist:
                    # قراءة وتنفيذ ملف schema.sql فقط إذا لم تكن الجداول موجودة
                    schema_path = Path(__file__).parent / "schema.sql"
                    if schema_path.exists():
                        with open(schema_path, 'r', encoding='utf-8') as f:
                            schema_sql = f.read()
                        conn.executescript(schema_sql)
                        self.logger.info("تم إنشاء قاعدة البيانات بنجاح")
                    else:
                        self.logger.error("ملف schema.sql غير موجود")
                else:
                    self.logger.info("قاعدة البيانات موجودة مسبقاً - تم تخطي إنشاء الجداول")
        except Exception as e:
            self.logger.error(f"خطأ في تهيئة قاعدة البيانات: {e}")
            raise
    
    def _init_connection_pool(self):
        """تهيئة مجموعة الاتصالات لتجنب التضارب"""
        try:
            for _ in range(5):  # 5 اتصالات في المجموعة
                if FK_HELPER_AVAILABLE:
                    conn = get_db_connection(str(self.db_path))
                else:
                    conn = sqlite3.connect(
                        self.db_path, 
                        check_same_thread=False,
                        timeout=30.0
                    )
                    conn.execute("PRAGMA foreign_keys = ON")
                conn.row_factory = sqlite3.Row
                
                # تطبيق نفس الإعدادات
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode = WAL")
                conn.execute("PRAGMA synchronous = NORMAL")
                conn.execute("PRAGMA busy_timeout = 30000")
                
                self._connection_pool.put(conn)
            
            self._pool_initialized = True
            self.logger.info("تم تهيئة مجموعة الاتصالات بنجاح")
        except Exception as e:
            self.logger.error(f"خطأ في تهيئة مجموعة الاتصالات: {e}")
    
    def _apply_migrations(self):
        """تطبيق أي migrations مطلوبة على قاعدة البيانات"""
        try:
            with self.get_write_connection() as conn:
                # فحص ما إذا كان جدول portfolio يحتوي على عمود is_demo
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(portfolio)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'is_demo' not in columns:
                    # إضافة عمود is_demo إذا لم يكن موجوداً
                    self.logger.info("🔧 إضافة عمود is_demo إلى جدول portfolio...")
                    conn.execute("ALTER TABLE portfolio ADD COLUMN is_demo BOOLEAN DEFAULT 0")
                    conn.commit()
                    self.logger.info("✅ تم إضافة عمود is_demo بنجاح")
                
                # فحص ما إذا كان جدول active_positions يحتوي على عمود is_demo
                cursor.execute("PRAGMA table_info(active_positions)")
                columns = [row[1] for row in cursor.fetchall()]
                
                if 'is_demo' not in columns:
                    # إضافة عمود is_demo إذا لم يكن موجوداً
                    self.logger.info("🔧 إضافة عمود is_demo إلى جدول active_positions...")
                    conn.execute("ALTER TABLE active_positions ADD COLUMN is_demo BOOLEAN DEFAULT 0")
                    conn.commit()
                    self.logger.info("✅ تم إضافة عمود is_demo بنجاح")
                
                # ✅ إضافة أعمدة ML للصفقات النشطة
                if 'ml_status' not in columns:
                    self.logger.info("🔧 إضافة أعمدة ML إلى جدول active_positions...")
                    conn.execute("ALTER TABLE active_positions ADD COLUMN ml_status TEXT DEFAULT 'none'")
                    conn.execute("ALTER TABLE active_positions ADD COLUMN ml_confidence REAL DEFAULT 0.0")
                    conn.commit()
                    self.logger.info("✅ تم إضافة أعمدة ML بنجاح")
                
                # ✅ جدول جديد: مقارنة Backtesting مع الواقع (لنظام ML الجديد)
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='backtest_vs_reality'")
                if not cursor.fetchone():
                    self.logger.info("🔧 إنشاء جدول backtest_vs_reality...")
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS backtest_vs_reality (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            
                            -- معرف التركيبة
                            symbol TEXT NOT NULL,
                            strategy TEXT NOT NULL,
                            timeframe TEXT NOT NULL,
                            
                            -- توقعات Backtesting (من successful_coins)
                            backtest_win_rate REAL,
                            backtest_profit_pct REAL,
                            backtest_score REAL,
                            backtest_total_trades INTEGER,
                            
                            -- النتيجة الفعلية
                            actual_result TEXT NOT NULL,  -- 'win' or 'loss'
                            actual_profit_pct REAL NOT NULL,
                            
                            -- ظروف السوق عند الدخول
                            market_trend TEXT,
                            
                            -- التوقيت
                            trade_id INTEGER,
                            trade_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            
                            -- حسابات الموثوقية (تُحدّث لاحقاً)
                            reliability_score REAL DEFAULT NULL,
                            
                            FOREIGN KEY (trade_id) REFERENCES user_trades(id) ON DELETE SET NULL
                        )
                    """)
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_backtest_reality_combo ON backtest_vs_reality(symbol, strategy, timeframe)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_backtest_reality_date ON backtest_vs_reality(trade_date DESC)")
                    conn.commit()
                    self.logger.info("✅ تم إنشاء جدول backtest_vs_reality بنجاح")
                
                # ✅ جدول موثوقية التركيبات (ملخص محسوب)
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='combo_reliability'")
                if not cursor.fetchone():
                    self.logger.info("🔧 إنشاء جدول combo_reliability...")
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS combo_reliability (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            
                            -- معرف التركيبة
                            symbol TEXT NOT NULL,
                            strategy TEXT NOT NULL,
                            timeframe TEXT NOT NULL,
                            
                            -- إحصائيات الموثوقية
                            total_trades INTEGER DEFAULT 0,
                            winning_trades INTEGER DEFAULT 0,
                            actual_win_rate REAL DEFAULT 0,
                            
                            -- مقارنة مع Backtesting
                            avg_backtest_win_rate REAL DEFAULT 0,
                            reliability_score REAL DEFAULT 0,  -- 0-100%
                            deviation_pct REAL DEFAULT 0,  -- الفرق بين التوقع والواقع
                            
                            -- التحديث
                            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            
                            UNIQUE(symbol, strategy, timeframe)
                        )
                    """)
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_combo_reliability_score ON combo_reliability(reliability_score DESC)")
                    conn.commit()
                    self.logger.info("✅ تم إنشاء جدول combo_reliability بنجاح")
                
                # ✅ جدول تعلم الإشارات (Smart Incremental Learning)
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signal_learning'")
                if not cursor.fetchone():
                    self.logger.info("🔧 إنشاء جدول signal_learning...")
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS signal_learning (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            signal_id TEXT NOT NULL UNIQUE,
                            user_id INTEGER,
                            
                            -- التركيبة
                            combination TEXT NOT NULL,
                            symbol TEXT NOT NULL,
                            strategy TEXT NOT NULL,
                            timeframe TEXT NOT NULL,
                            
                            -- بيانات الدخول
                            entry_price REAL,
                            entry_rsi REAL,
                            entry_macd REAL,
                            entry_volume REAL,
                            market_regime TEXT,
                            volatility REAL,
                            support_distance REAL,
                            resistance_distance REAL,
                            
                            -- النتيجة الفعلية
                            actual_profit_pct REAL,
                            exit_reason TEXT,
                            signal_quality_score REAL,
                            was_correct INTEGER,
                            holding_time_minutes INTEGER,
                            
                            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            
                            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                        )
                    """)
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_learning_combo ON signal_learning(combination, timestamp DESC)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_learning_quality ON signal_learning(signal_quality_score DESC)")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_signal_learning_user ON signal_learning(user_id, timestamp DESC)")
                    conn.commit()
                    self.logger.info("✅ تم إنشاء جدول signal_learning بنجاح")
                
                # ============================================================
                # Shadow Tables Migration — formerly created at runtime by services
                # Centralized here as the single source of truth for DB schema
                # ============================================================
                
                # ST-1: coin_states (from coin_state_tracker.py)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS coin_states (
                        symbol TEXT PRIMARY KEY,
                        state TEXT NOT NULL,
                        position_size_multiplier REAL DEFAULT 1.0,
                        stop_loss_multiplier REAL DEFAULT 1.0,
                        consecutive_wins INTEGER DEFAULT 0,
                        consecutive_losses INTEGER DEFAULT 0,
                        total_trades INTEGER DEFAULT 0,
                        winning_trades INTEGER DEFAULT 0,
                        total_pnl REAL DEFAULT 0.0,
                        blacklist_until TEXT,
                        last_updated TEXT NOT NULL
                    )
                """)
                
                # ST-2: coin_trade_history (from coin_state_tracker.py)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS coin_trade_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        entry_time TEXT NOT NULL,
                        exit_time TEXT NOT NULL,
                        pnl REAL NOT NULL,
                        profit_pct REAL NOT NULL,
                        exit_reason TEXT,
                        strategy TEXT,
                        timeframe TEXT,
                        market_regime TEXT
                    )
                """)
                
                # ST-3: trade_learning_log (from adaptive_optimizer.py)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS trade_learning_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        side TEXT NOT NULL,
                        entry_price REAL NOT NULL,
                        exit_price REAL NOT NULL,
                        pnl REAL NOT NULL,
                        pnl_pct REAL NOT NULL,
                        exit_reason TEXT NOT NULL,
                        sl_pct_used REAL DEFAULT 0.01,
                        hold_minutes INTEGER DEFAULT 0,
                        open_positions_count INTEGER DEFAULT 1,
                        hour_of_day INTEGER DEFAULT 0,
                        day_of_week TEXT DEFAULT '',
                        rsi REAL DEFAULT NULL,
                        macd REAL DEFAULT NULL,
                        bb_position REAL DEFAULT NULL,
                        volume_ratio REAL DEFAULT NULL,
                        ema_trend TEXT DEFAULT NULL,
                        atr_pct REAL DEFAULT NULL,
                        trend_4h TEXT DEFAULT NULL,
                        score REAL DEFAULT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tll_symbol ON trade_learning_log(symbol)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_tll_created ON trade_learning_log(created_at)")
                
                # ST-4: learning_validation_log (from adaptive_optimizer.py)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS learning_validation_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        validated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        total_trades INTEGER NOT NULL,
                        trades_with_indicators INTEGER NOT NULL,
                        holdout_size INTEGER NOT NULL,
                        scorer_accuracy REAL NOT NULL,
                        scorer_precision REAL,
                        baseline_accuracy REAL NOT NULL,
                        lift REAL NOT NULL,
                        factor_weights TEXT,
                        factor_accuracies TEXT,
                        verdict TEXT NOT NULL,
                        details TEXT
                    )
                """)
                
                # ST-5: admin_notification_settings (from admin_notification_service.py)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS admin_notification_settings (
                        id INTEGER PRIMARY KEY,
                        telegram_enabled BOOLEAN DEFAULT 0,
                        telegram_bot_token TEXT,
                        telegram_chat_id TEXT,
                        email_enabled BOOLEAN DEFAULT 0,
                        admin_email TEXT,
                        webhook_enabled BOOLEAN DEFAULT 0,
                        webhook_url TEXT,
                        push_enabled BOOLEAN DEFAULT 1,
                        notify_on_error BOOLEAN DEFAULT 1,
                        notify_on_trade BOOLEAN DEFAULT 1,
                        notify_on_warning BOOLEAN DEFAULT 1,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # ST-6: system_alerts (from admin_notification_service.py + system_alerts.py)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS system_alerts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        alert_type VARCHAR(50) NOT NULL,
                        title TEXT NOT NULL,
                        message TEXT NOT NULL,
                        severity VARCHAR(20) DEFAULT 'warning',
                        data TEXT,
                        read INTEGER DEFAULT 0,
                        resolved INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        resolved_at TIMESTAMP
                    )
                """)
                
                # ST-7: user_onboarding (from user_onboarding_service.py)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS user_onboarding (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        step TEXT NOT NULL,
                        shown_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        dismissed_at TIMESTAMP,
                        UNIQUE(user_id, step)
                    )
                """)
                
                # ST-8: security_audit_log (from security_audit_service.py)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS security_audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        action TEXT NOT NULL,
                        resource TEXT,
                        ip_address TEXT,
                        user_agent TEXT,
                        status TEXT DEFAULT 'success',
                        details TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON security_audit_log(user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON security_audit_log(action)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_resource ON security_audit_log(resource)")
                
                # ST-9: smart_exit_stats (from smart_exit_api.py)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS smart_exit_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        symbol TEXT NOT NULL,
                        exit_type TEXT NOT NULL,
                        exit_price REAL,
                        profit_loss REAL DEFAULT 0,
                        profit_pct REAL DEFAULT 0,
                        is_demo INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ses_user ON smart_exit_stats(user_id)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ses_type ON smart_exit_stats(exit_type)")
                
                # ST-10: smart_exit_errors (from smart_exit_api.py)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS smart_exit_errors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        symbol TEXT NOT NULL,
                        error_type TEXT NOT NULL,
                        error_message TEXT,
                        error_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_see_user ON smart_exit_errors(user_id)")
                
                # ST-11: pending_verifications (from secure_actions_endpoints.py — was in-memory dict)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS pending_verifications (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        action TEXT NOT NULL,
                        otp TEXT NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        method TEXT DEFAULT 'email',
                        new_value TEXT,
                        old_password TEXT,
                        attempts INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, action)
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_pv_user_action ON pending_verifications(user_id, action)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_pv_expires ON pending_verifications(expires_at)")
                
                conn.commit()
                self.logger.debug("✅ Shadow tables migration complete")
                
        except Exception as e:
            self.logger.warning(f"⚠️ خطأ في تطبيق migrations: {e}")
    
    def _get_pooled_connection(self):
        """الحصول على اتصال جديد (بدون Pool للحصول على بيانات فورية)"""
        # إنشاء اتصال جديد في كل مرة لضمان الحصول على البيانات الفورية
        if FK_HELPER_AVAILABLE:
            conn = get_db_connection(str(self.db_path))
        else:
            conn = sqlite3.connect(
                self.db_path, 
                check_same_thread=False,
                timeout=60.0
            )
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=60000")
            conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 30000")
        conn.execute("PRAGMA synchronous = FULL")  # ضمان الكتابة الفورية
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
            conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=60.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=60000")
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
                conn = sqlite3.connect(self.db_path, check_same_thread=False, timeout=60.0)
                conn.row_factory = sqlite3.Row
                # ✅ FIX: تفعيل FK لاتصالات الكتابة أيضاً
                conn.execute("PRAGMA foreign_keys = ON")
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA busy_timeout=60000")
                conn.execute("BEGIN IMMEDIATE")  # قفل فوري للكتابة
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
                conn.execute("""
                    UPDATE portfolio 
                    SET balance = 1000.0, totalBalance = 1000.0, availableBalance = 1000.0,
                        total_profit_loss = 0.0, totalProfitLoss = 0.0, 
                        total_trades = 0, winning_trades = 0, losing_trades = 0, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (user_id,))
                
                # حذف الصفقات
                conn.execute("DELETE FROM user_trades WHERE user_id = ?", (user_id,))
                
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
                cursor = conn.execute("SELECT COUNT(*) FROM user_trades")
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
