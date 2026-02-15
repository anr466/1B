-- ============================================================================
-- Enable Foreign Key Constraints - ضمان Data Integrity
-- ============================================================================
-- التاريخ: 2026-02-14
-- الهدف: تفعيل foreign key constraints وإضافة المفقودة
-- ============================================================================

-- تفعيل foreign keys (يجب تطبيقه في كل session)
PRAGMA foreign_keys = ON;

-- التحقق من التفعيل
SELECT 'Foreign keys status: ' || CASE WHEN foreign_keys = 1 THEN 'ENABLED' ELSE 'DISABLED' END 
FROM pragma_foreign_keys;

-- ============================================================================
-- إضافة Foreign Keys المفقودة
-- ============================================================================

-- ملاحظة: SQLite لا يدعم ADD CONSTRAINT مباشرة
-- يجب إعادة إنشاء الجداول مع foreign keys

-- سنتأكد من أن الجداول الجديدة تحتوي على foreign keys صحيحة
-- وسنضيف triggers للتحقق من data integrity

-- ============================================================================
-- Triggers للتحقق من Data Integrity
-- ============================================================================

-- 1. التحقق من user_id في portfolio
CREATE TRIGGER IF NOT EXISTS check_portfolio_user_id
BEFORE INSERT ON portfolio
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Foreign key violation: user_id not found in users')
    WHERE NOT EXISTS (SELECT 1 FROM users WHERE id = NEW.user_id);
END;

-- 2. التحقق من user_id في active_positions
CREATE TRIGGER IF NOT EXISTS check_positions_user_id
BEFORE INSERT ON active_positions
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Foreign key violation: user_id not found in users')
    WHERE NOT EXISTS (SELECT 1 FROM users WHERE id = NEW.user_id);
END;

-- 3. التحقق من user_id في user_trades
CREATE TRIGGER IF NOT EXISTS check_trades_user_id
BEFORE INSERT ON user_trades
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Foreign key violation: user_id not found in users')
    WHERE NOT EXISTS (SELECT 1 FROM users WHERE id = NEW.user_id);
END;

-- 4. منع حذف users لديهم بيانات نشطة
CREATE TRIGGER IF NOT EXISTS prevent_user_delete_with_positions
BEFORE DELETE ON users
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete user with active positions')
    WHERE EXISTS (SELECT 1 FROM active_positions WHERE user_id = OLD.id AND is_active = 1);
END;

-- 5. منع حذف users لديهم محفظة
CREATE TRIGGER IF NOT EXISTS prevent_user_delete_with_portfolio
BEFORE DELETE ON users
FOR EACH ROW
BEGIN
    SELECT RAISE(ABORT, 'Cannot delete user with portfolio data')
    WHERE EXISTS (SELECT 1 FROM portfolio WHERE user_id = OLD.id);
END;

-- ============================================================================
-- التحقق من البيانات اليتيمة الموجودة
-- ============================================================================

-- التحقق من portfolio بدون users
SELECT 'Orphan portfolios: ' || COUNT(*) 
FROM portfolio p 
LEFT JOIN users u ON p.user_id = u.id 
WHERE u.id IS NULL;

-- التحقق من active_positions بدون users
SELECT 'Orphan positions: ' || COUNT(*) 
FROM active_positions ap 
LEFT JOIN users u ON ap.user_id = u.id 
WHERE u.id IS NULL;

-- التحقق من user_trades بدون users
SELECT 'Orphan trades: ' || COUNT(*) 
FROM user_trades ut 
LEFT JOIN users u ON ut.user_id = u.id 
WHERE u.id IS NULL;

-- ============================================================================
-- تنظيف البيانات اليتيمة (إذا وُجدت)
-- ============================================================================

-- حذف portfolio بدون users
DELETE FROM portfolio 
WHERE user_id NOT IN (SELECT id FROM users);

-- حذف active_positions بدون users
DELETE FROM active_positions 
WHERE user_id NOT IN (SELECT id FROM users);

-- حذف user_trades بدون users
DELETE FROM user_trades 
WHERE user_id NOT IN (SELECT id FROM users);

SELECT 'Data integrity cleanup completed';
