#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🗄️ تهيئة قاعدة البيانات - إضافة الجداول الناقصة
================================================

هذا الملف يضيف جميع الجداول المطلوبة إلى قاعدة البيانات المستقلة
بدون حذف أو تعديل البيانات الموجودة

الجداول المطلوبة:
1. users - بيانات المستخدمين
2. user_trades - سجل الصفقات
3. portfolio - بيانات المحفظة
4. activity_logs - سجل النشاط
5. successful_coins - العملات الناجحة
6. portfolio_growth_history - تاريخ نمو المحفظة
7. system_status - حالة النظام
"""

import sqlite3
from pathlib import Path
import sys

# تحديد مسار قاعدة البيانات
DB_PATH = Path(__file__).parent / "trading_database.db"

def check_existing_tables():
    """فحص الجداول الموجودة بالفعل"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    conn.close()
    
    existing = [t[0] for t in tables]
    print("\n📊 الجداول الموجودة بالفعل:")
    for table in existing:
        print(f"   ✅ {table}")
    
    return existing

def create_tables():
    """إنشاء جميع الجداول المطلوبة"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # تفعيل foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    print("\n🔨 إنشاء الجداول المطلوبة...\n")
    
    # 1. جدول المستخدمين
    print("1️⃣ جدول users...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            phone_number TEXT,
            user_type TEXT DEFAULT 'user',
            email_verified BOOLEAN DEFAULT FALSE,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login_at TIMESTAMP
        )
    """)
    print("   ✅ تم إنشاء جدول users")
    
    # 2. جدول الصفقات
    print("2️⃣ جدول user_trades...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            entry_time TEXT NOT NULL,
            exit_time TEXT,
            entry_price REAL NOT NULL,
            exit_price REAL,
            quantity REAL NOT NULL,
            status TEXT DEFAULT 'open',
            profit_loss REAL,
            profit_loss_percentage REAL,
            is_demo BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    print("   ✅ تم إنشاء جدول user_trades")
    
    # 3. جدول المحفظة
    print("3️⃣ جدول portfolio...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            total_balance REAL DEFAULT 0,
            available_balance REAL DEFAULT 0,
            invested_balance REAL DEFAULT 0,
            total_profit_loss REAL DEFAULT 0,
            total_profit_loss_percentage REAL DEFAULT 0,
            is_demo BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    print("   ✅ تم إنشاء جدول portfolio")
    
    # 4. جدول سجلات النشاط
    print("4️⃣ جدول activity_logs...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    print("   ✅ تم إنشاء جدول activity_logs")
    
    # 5. جدول العملات الناجحة
    print("5️⃣ جدول successful_coins...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS successful_coins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT UNIQUE NOT NULL,
            success_count INTEGER DEFAULT 0,
            total_trades INTEGER DEFAULT 0,
            success_rate REAL DEFAULT 0,
            score REAL DEFAULT 0,
            is_active BOOLEAN DEFAULT TRUE,
            market_trend TEXT,
            avg_trade_duration_hours REAL,
            trading_style TEXT,
            analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    print("   ✅ تم إنشاء جدول successful_coins")
    
    # 6. جدول نمو المحفظة
    print("6️⃣ جدول portfolio_growth_history...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS portfolio_growth_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            total_balance REAL NOT NULL,
            daily_pnl REAL NOT NULL,
            daily_pnl_percentage REAL NOT NULL,
            active_trades_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            UNIQUE(user_id, date)
        )
    """)
    print("   ✅ تم إنشاء جدول portfolio_growth_history")
    
    # 7. جدول حالة النظام
    print("7️⃣ جدول system_status...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT DEFAULT 'online',
            last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_users INTEGER DEFAULT 0,
            active_trades INTEGER DEFAULT 0,
            total_trades INTEGER DEFAULT 0
        )
    """)
    print("   ✅ تم إنشاء جدول system_status")
    
    # إنشاء الفهارس
    print("\n📑 إنشاء الفهارس للأداء...\n")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_trades_user ON user_trades(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_trades_symbol ON user_trades(symbol)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_trades_status ON user_trades(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_trades_user_date ON user_trades(user_id, entry_time DESC)")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_logs_user ON activity_logs(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON activity_logs(timestamp DESC)")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_growth_user ON portfolio_growth_history(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_growth_date ON portfolio_growth_history(date DESC)")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_successful_coins_score ON successful_coins(score DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_successful_coins_active ON successful_coins(is_active)")
    
    print("   ✅ تم إنشاء جميع الفهارس")
    
    # إدراج بيانات افتراضية
    print("\n📝 إدراج البيانات الافتراضية...\n")
    
    # إدراج مستخدم admin
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO users (id, username, email, password_hash, user_type, email_verified, is_active)
            VALUES (1, 'admin', 'admin@demo.com', '8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918', 'admin', 1, 1)
        """)
        print("   ✅ تم إدراج مستخدم admin")
    except Exception as e:
        print(f"   ⚠️ خطأ في إدراج admin: {e}")
    
    # إدراج حالة النظام
    try:
        cursor.execute("""
            INSERT OR IGNORE INTO system_status (id, status)
            VALUES (1, 'online')
        """)
        print("   ✅ تم إدراج حالة النظام")
    except Exception as e:
        print(f"   ⚠️ خطأ في إدراج system_status: {e}")
    
    # حفظ التغييرات
    conn.commit()
    conn.close()
    
    print("\n✅ تم إنشاء جميع الجداول بنجاح!")

def verify_database():
    """التحقق من صحة قاعدة البيانات"""
    print("\n🔍 التحقق من قاعدة البيانات...\n")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    required_tables = [
        'users', 'user_trades', 'portfolio', 'activity_logs',
        'successful_coins', 'portfolio_growth_history', 'system_status'
    ]
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [t[0] for t in cursor.fetchall()]
    
    print("📊 التحقق من الجداول:")
    all_ok = True
    for table in required_tables:
        if table in existing_tables:
            # عد الأعمدة
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            print(f"   ✅ {table} ({len(columns)} أعمدة)")
        else:
            print(f"   ❌ {table} - مفقود!")
            all_ok = False
    
    # التحقق من البيانات الافتراضية
    print("\n📝 التحقق من البيانات الافتراضية:")
    
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"   ✅ عدد المستخدمين: {user_count}")
    
    cursor.execute("SELECT COUNT(*) FROM system_status")
    status_count = cursor.fetchone()[0]
    print(f"   ✅ حالة النظام: {status_count}")
    
    conn.close()
    
    if all_ok:
        print("\n✅ قاعدة البيانات جاهزة وكاملة!")
        return True
    else:
        print("\n❌ هناك مشاكل في قاعدة البيانات")
        return False

def main():
    """الدالة الرئيسية"""
    print("=" * 60)
    print("🗄️  تهيئة قاعدة البيانات")
    print("=" * 60)
    
    if not DB_PATH.exists():
        print(f"\n⚠️ قاعدة البيانات غير موجودة: {DB_PATH}")
        print("سيتم إنشاء قاعدة بيانات جديدة...")
    else:
        print(f"\n✅ قاعدة البيانات موجودة: {DB_PATH}")
    
    # فحص الجداول الموجودة
    existing = check_existing_tables()
    
    # إنشاء الجداول
    create_tables()
    
    # التحقق
    verify_database()
    
    print("\n" + "=" * 60)
    print("✅ انتهت عملية التهيئة بنجاح!")
    print("=" * 60)

if __name__ == "__main__":
    main()
