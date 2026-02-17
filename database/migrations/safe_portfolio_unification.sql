-- ============================================================================
-- Safe Portfolio Unification Migration - إصلاح آمن لتضارب جداول المحفظة
-- ============================================================================
-- التاريخ: 2026-02-15
-- الهدف: توحيد آمن لجداول المحفظة مع تنظيف البيانات المعطلة
-- ============================================================================

-- تعطيل foreign keys مؤقتاً للmigration
PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- ============================================================================
-- 1. تنظيف البيانات المعطلة من user_portfolio
-- ============================================================================

-- حذف البيانات المعطلة (user_ids غير موجودة في users)
DELETE FROM user_portfolio 
WHERE user_id NOT IN (SELECT id FROM users);

-- ============================================================================
-- 2. التأكد من وجود عمود is_demo في portfolio
-- ============================================================================

-- إضافة عمود is_demo إذا لم يكن موجوداً
ALTER TABLE portfolio ADD COLUMN is_demo INTEGER DEFAULT 0;

-- ============================================================================
-- 3. دمج البيانات الآمنة من user_portfolio إلى portfolio
-- ============================================================================

-- دمج فقط البيانات لمستخدمين موجودين
INSERT OR REPLACE INTO portfolio (
    user_id, 
    total_balance, 
    available_balance, 
    invested_balance,
    total_profit_loss,
    total_profit_loss_percentage,
    is_demo,
    created_at,
    updated_at
)
SELECT 
    up.user_id,
    COALESCE(up.balance, 1000.0) as total_balance,
    COALESCE(up.balance, 1000.0) as available_balance,
    0.0 as invested_balance,
    COALESCE(up.total_profit, 0.0) as total_profit_loss,
    COALESCE(up.profit_percentage, 0.0) as total_profit_loss_percentage,
    0 as is_demo,  -- user_portfolio = حقيقي
    COALESCE(up.created_at, CURRENT_TIMESTAMP) as created_at,
    COALESCE(up.last_updated, CURRENT_TIMESTAMP) as updated_at
FROM user_portfolio up
INNER JOIN users u ON up.user_id = u.id  -- فقط المستخدمين الموجودين
WHERE NOT EXISTS (
    SELECT 1 FROM portfolio p 
    WHERE p.user_id = up.user_id AND p.is_demo = 0
);

-- ============================================================================
-- 4. إنشاء محافظ demo للأدمن
-- ============================================================================

INSERT OR IGNORE INTO portfolio (
    user_id, 
    total_balance, 
    available_balance, 
    invested_balance,
    total_profit_loss,
    total_profit_loss_percentage,
    is_demo,
    created_at,
    updated_at
)
SELECT 
    u.id as user_id,
    10000.0 as total_balance,  -- رصيد demo افتراضي
    10000.0 as available_balance,
    0.0 as invested_balance,
    0.0 as total_profit_loss,
    0.0 as total_profit_loss_percentage,
    1 as is_demo,
    CURRENT_TIMESTAMP as created_at,
    CURRENT_TIMESTAMP as updated_at
FROM users u 
WHERE u.user_type = 'admin' 
AND NOT EXISTS (
    SELECT 1 FROM portfolio p 
    WHERE p.user_id = u.id AND p.is_demo = 1
);

-- ============================================================================
-- 5. إنشاء محافظ حقيقية للمستخدمين العاديين الناقصين
-- ============================================================================

INSERT OR IGNORE INTO portfolio (
    user_id, 
    total_balance, 
    available_balance, 
    invested_balance,
    total_profit_loss,
    total_profit_loss_percentage,
    is_demo,
    created_at,
    updated_at
)
SELECT 
    u.id as user_id,
    1000.0 as total_balance,   -- رصيد حقيقي افتراضي
    1000.0 as available_balance,
    0.0 as invested_balance,
    0.0 as total_profit_loss,
    0.0 as total_profit_loss_percentage,
    0 as is_demo,
    CURRENT_TIMESTAMP as created_at,
    CURRENT_TIMESTAMP as updated_at
FROM users u 
WHERE u.user_type = 'user'
AND NOT EXISTS (
    SELECT 1 FROM portfolio p 
    WHERE p.user_id = u.id AND p.is_demo = 0
);

-- ============================================================================
-- 6. إضافة فهارس ومفاتيح للأداء والتكامل
-- ============================================================================

-- إنشاء unique constraint للتأكد من عدم التكرار
DROP INDEX IF EXISTS idx_portfolio_user_demo;
CREATE UNIQUE INDEX idx_portfolio_user_demo ON portfolio(user_id, is_demo);

-- فهارس الأداء
CREATE INDEX IF NOT EXISTS idx_portfolio_user_id ON portfolio(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_is_demo ON portfolio(is_demo);
CREATE INDEX IF NOT EXISTS idx_portfolio_updated_at ON portfolio(updated_at DESC);

-- ============================================================================
-- 7. إعادة تسمية الجداول القديمة للأمان
-- ============================================================================

-- نسخ احتياطية للجداول القديمة
ALTER TABLE user_portfolio RENAME TO user_portfolio_backup_20260215;

-- إذا كان جدول user_portfolios موجوداً، نسخه أيضاً
-- ALTER TABLE user_portfolios RENAME TO user_portfolios_backup_20260215;

COMMIT;

-- إعادة تفعيل foreign keys
PRAGMA foreign_keys = ON;

-- ============================================================================
-- التحقق من النتائج
-- ============================================================================

-- إحصائيات المحافظ الموحدة
SELECT 
    '=== Portfolio Unification Results ===' as section;

SELECT 
    'Total Portfolios' as metric,
    COUNT(*) as value
FROM portfolio;

SELECT 
    'Real Portfolios' as metric,
    COUNT(*) as value
FROM portfolio WHERE is_demo = 0;

SELECT 
    'Demo Portfolios' as metric,
    COUNT(*) as value
FROM portfolio WHERE is_demo = 1;

SELECT 
    'Admin Users with Both Portfolios' as metric,
    COUNT(DISTINCT user_id) as value
FROM portfolio p
WHERE EXISTS (SELECT 1 FROM users u WHERE u.id = p.user_id AND u.user_type = 'admin')
AND user_id IN (
    SELECT user_id FROM portfolio GROUP BY user_id HAVING COUNT(DISTINCT is_demo) = 2
);

-- عرض عينة من البيانات
SELECT 
    u.email,
    u.user_type,
    p.is_demo,
    p.total_balance,
    p.updated_at
FROM portfolio p
JOIN users u ON p.user_id = u.id
ORDER BY u.user_type, u.email, p.is_demo
LIMIT 10;
