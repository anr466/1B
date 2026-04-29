-- ============================================================================
-- Database Migration: إصلاح Schema لدعم المحفظتين (Demo + Real)
-- ============================================================================
-- التاريخ: 2025-12-31
-- الهدف: مطابقة قاعدة البيانات مع منطق التطبيق والنظام الخلفي
-- ============================================================================

-- ============================================================================
-- 1. إصلاح جدول user_portfolios
-- ============================================================================
-- المشكلة: لا يوجد عمود is_demo، UNIQUE على user_id فقط
-- الحل: إعادة بناء الجدول مع is_demo و UNIQUE(user_id, is_demo)

BEGIN TRANSACTION;

-- أ) إنشاء جدول جديد بالـ Schema الصحيح
CREATE TABLE user_portfolios_new (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    is_demo INTEGER NOT NULL DEFAULT 0,
    balance NUMERIC(18,8) DEFAULT 1000.0,
    available_balance NUMERIC(18,8) DEFAULT 1000.0,
    locked_balance NUMERIC(18,8) DEFAULT 0.0,
    total_profit_loss NUMERIC(18,8) DEFAULT 0.0,
    daily_profit_loss NUMERIC(18,8) DEFAULT 0.0,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    win_rate NUMERIC(5,2) DEFAULT 0.0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, is_demo)  -- ✅ كل مستخدم له محفظتين: Demo + Real
);

CREATE INDEX idx_user_portfolios_user_demo ON user_portfolios_new(user_id, is_demo);

-- ب) نسخ البيانات الموجودة (كـ Real portfolios)
INSERT INTO user_portfolios_new (
    id, user_id, is_demo, balance, total_profit_loss, 
    total_trades, winning_trades, losing_trades, win_rate, updated_at
)
SELECT 
    id, 
    user_id, 
    0 as is_demo,  -- جميع البيانات الموجودة = Real
    balance, 
    COALESCE(total_profit_loss, 0.0),
    COALESCE(total_trades, 0),
    COALESCE(winning_trades, 0),
    COALESCE(losing_trades, 0),
    COALESCE(win_rate, 0.0),
    COALESCE(updated_at, CURRENT_TIMESTAMP)
FROM user_portfolios;

-- ج) للأدمن: إنشاء Demo portfolios
INSERT INTO user_portfolios_new (
    user_id, is_demo, balance, available_balance,
    total_profit_loss, daily_profit_loss
)
SELECT 
    u.id,
    1 as is_demo,  -- Demo
    1000.0 as balance,
    1000.0 as available_balance,
    0.0 as total_profit_loss,
    0.0 as daily_profit_loss
FROM users u
WHERE u.user_type = 'admin'
AND NOT EXISTS (
    SELECT 1 FROM user_portfolios_new p 
    WHERE p.user_id = u.id AND p.is_demo = 1
);

-- د) حذف الجدول القديم وإعادة تسمية الجديد
DROP TABLE user_portfolios;
ALTER TABLE user_portfolios_new RENAME TO user_portfolios;

COMMIT;

-- ============================================================================
-- 2. تصحيح بيانات user_settings للمستخدمين العاديين
-- ============================================================================
-- المشكلة: بعض المستخدمين لديهم is_demo=1، يجب أن يكون is_demo=0
-- الحل: تحديث جميع المستخدمين العاديين إلى is_demo=0

BEGIN TRANSACTION;

-- أ) تحديث المستخدمين العاديين الموجودين بـ is_demo=1
UPDATE user_settings
SET is_demo = 0
WHERE user_id IN (
    SELECT id FROM users WHERE user_type = 'user'
)
AND is_demo = 1;

-- ب) التأكد من وجود إعدادات Real لكل مستخدم عادي
INSERT OR IGNORE INTO user_settings (
    user_id, is_demo, trading_enabled, trade_amount, 
    position_size_percentage, stop_loss_pct, take_profit_pct,
    trailing_distance, max_positions, risk_level, trading_mode
)
SELECT 
    u.id,
    0 as is_demo,  -- Real فقط
    0 as trading_enabled,
    100.0 as trade_amount,
    10.0 as position_size_percentage,
    2.0 as stop_loss_pct,
    5.0 as take_profit_pct,
    3.0 as trailing_distance,
    5 as max_positions,
    'medium' as risk_level,
    'auto' as trading_mode
FROM users u
WHERE u.user_type = 'user'
AND NOT EXISTS (
    SELECT 1 FROM user_settings s 
    WHERE s.user_id = u.id AND s.is_demo = 0
);

COMMIT;

-- ============================================================================
-- 3. التأكد من وجود محفظتين للأدمن (Demo + Real)
-- ============================================================================

BEGIN TRANSACTION;

-- أ) إنشاء إعدادات Demo للأدمن (إذا لم تكن موجودة)
INSERT OR IGNORE INTO user_settings (
    user_id, is_demo, trading_enabled, trade_amount,
    position_size_percentage, stop_loss_pct, take_profit_pct,
    trailing_distance, max_positions, risk_level, trading_mode
)
SELECT 
    u.id,
    1 as is_demo,  -- Demo
    0 as trading_enabled,
    150.0 as trade_amount,
    10.0 as position_size_percentage,
    2.0 as stop_loss_pct,
    5.0 as take_profit_pct,
    3.0 as trailing_distance,
    5 as max_positions,
    'medium' as risk_level,
    'demo' as trading_mode
FROM users u
WHERE u.user_type = 'admin'
AND NOT EXISTS (
    SELECT 1 FROM user_settings s 
    WHERE s.user_id = u.id AND s.is_demo = 1
);

-- ب) إنشاء إعدادات Real للأدمن (إذا لم تكن موجودة)
INSERT OR IGNORE INTO user_settings (
    user_id, is_demo, trading_enabled, trade_amount,
    position_size_percentage, stop_loss_pct, take_profit_pct,
    trailing_distance, max_positions, risk_level, trading_mode
)
SELECT 
    u.id,
    0 as is_demo,  -- Real
    0 as trading_enabled,
    75.0 as trade_amount,
    10.0 as position_size_percentage,
    2.0 as stop_loss_pct,
    5.0 as take_profit_pct,
    3.0 as trailing_distance,
    3 as max_positions,
    'medium' as risk_level,
    'demo' as trading_mode
FROM users u
WHERE u.user_type = 'admin'
AND NOT EXISTS (
    SELECT 1 FROM user_settings s 
    WHERE s.user_id = u.id AND s.is_demo = 0
);

COMMIT;

-- ============================================================================
-- 4. التحقق النهائي
-- ============================================================================

-- عرض النتائج
SELECT '=== user_portfolios Schema ===' as info;
-- PostgreSQL: check table columns instead of sqlite_master
SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'portfolio';

SELECT '=== المستخدمون والمحافظ ===' as info;
SELECT 
    u.id,
    u.email,
    u.user_type,
    COUNT(DISTINCT p.is_demo) as portfolio_count,
    GROUP_CONCAT(CASE WHEN p.is_demo=0 THEN 'Real' WHEN p.is_demo=1 THEN 'Demo' END) as portfolios
FROM users u
LEFT JOIN user_portfolios p ON u.id = p.user_id
WHERE u.user_type IN ('user', 'admin')
GROUP BY u.id, u.email, u.user_type
ORDER BY u.user_type, u.id;

SELECT '=== user_settings count ===' as info;
SELECT 
    u.user_type,
    COUNT(*) as settings_count,
    SUM(CASE WHEN s.is_demo = 0 THEN 1 ELSE 0 END) as real_count,
    SUM(CASE WHEN s.is_demo = 1 THEN 1 ELSE 0 END) as demo_count
FROM users u
LEFT JOIN user_settings s ON u.id = s.user_id
WHERE u.user_type IN ('user', 'admin')
GROUP BY u.user_type;

SELECT '=== Migration Complete ===' as info;
