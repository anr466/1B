-- ============================================================================
-- Database Migration: توحيد جداول المحفظة - إصلاح الخطأ #16 الحرج
-- ============================================================================
-- التاريخ: 2026-02-14
-- الهدف: توحيد جداول المحفظة المتعددة في جدول portfolio واحد
-- المشكلة: تعدد جداول المحفظة يسبب عدم تزامن البيانات
-- الحل: استخدام portfolio table كمصدر وحيد للحقيقة
-- ============================================================================

BEGIN TRANSACTION;

-- ============================================================================
-- 1. التأكد من وجود عمود is_demo في جدول portfolio
-- ============================================================================

-- تحديث UNIQUE constraint ليشمل is_demo
-- (سيتم تجاهل الخطأ إذا كان موجوداً بالفعل)
CREATE UNIQUE INDEX IF NOT EXISTS idx_portfolio_user_demo ON portfolio(user_id, is_demo);

-- ============================================================================
-- 2. دمج البيانات من user_portfolio إلى portfolio (إذا وُجد)
-- ============================================================================

-- نسخ البيانات من user_portfolio إلى portfolio إذا كان الجدول موجوداً
INSERT OR IGNORE INTO portfolio (
    user_id, 
    total_balance, 
    available_balance, 
    invested_balance,
    total_profit_loss,
    is_demo,
    created_at,
    updated_at
)
SELECT 
    user_id,
    COALESCE(balance, 1000.0) as total_balance,
    COALESCE(balance, 1000.0) as available_balance,
    0.0 as invested_balance,
    COALESCE(total_profit, 0.0) as total_profit_loss,
    0 as is_demo,  -- user_portfolio is for real accounts
    COALESCE(last_updated, CURRENT_TIMESTAMP) as created_at,
    COALESCE(last_updated, CURRENT_TIMESTAMP) as updated_at
FROM user_portfolio 
WHERE EXISTS (SELECT 1 FROM sqlite_master WHERE type='table' AND name='user_portfolio');

-- ============================================================================
-- 4. إنشاء محافظ demo للأدمن إذا لم تكن موجودة
-- ============================================================================

INSERT OR IGNORE INTO portfolio (
    user_id, 
    total_balance, 
    available_balance, 
    invested_balance,
    total_profit_loss,
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
    1 as is_demo,  -- demo portfolio
    CURRENT_TIMESTAMP as created_at,
    CURRENT_TIMESTAMP as updated_at
FROM users u 
WHERE u.user_type = 'admin' 
AND NOT EXISTS (
    SELECT 1 FROM portfolio p 
    WHERE p.user_id = u.id AND p.is_demo = 1
);

-- ============================================================================
-- 5. تنظيف الجداول القديمة (اختياري - يمكن تأجيله)
-- ============================================================================

-- إعادة تسمية الجداول القديمة بدلاً من حذفها للأمان
-- يمكن حذفها لاحقاً بعد التأكد من سلامة النظام

-- ALTER TABLE user_portfolios RENAME TO user_portfolios_backup_20260214;
-- ALTER TABLE user_portfolios_new RENAME TO user_portfolios_new_backup_20260214;

-- ============================================================================
-- 6. إضافة فهارس للأداء
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_portfolio_user_id ON portfolio(user_id);
CREATE INDEX IF NOT EXISTS idx_portfolio_is_demo ON portfolio(is_demo);
CREATE INDEX IF NOT EXISTS idx_portfolio_updated_at ON portfolio(updated_at);

COMMIT;

-- ============================================================================
-- تحقق من النتائج
-- ============================================================================

-- عرض إحصائيات المحافظ بعد التوحيد
SELECT 
    'Portfolio Statistics' as info,
    COUNT(*) as total_portfolios,
    COUNT(CASE WHEN is_demo = 0 THEN 1 END) as real_portfolios,
    COUNT(CASE WHEN is_demo = 1 THEN 1 END) as demo_portfolios,
    SUM(CASE WHEN is_demo = 0 THEN total_balance ELSE 0 END) as total_real_balance,
    SUM(CASE WHEN is_demo = 1 THEN total_balance ELSE 0 END) as total_demo_balance
FROM portfolio;
