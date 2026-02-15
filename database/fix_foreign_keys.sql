-- إصلاح Foreign Key Issues
-- تنظيف البيانات اليتيمة (Orphaned Records)

BEGIN TRANSACTION;

-- 1. حذف السجلات اليتيمة من activity_logs
DELETE FROM activity_logs 
WHERE user_id NOT IN (SELECT id FROM users);

-- 2. حذف السجلات اليتيمة من user_notification_settings
DELETE FROM user_notification_settings 
WHERE user_id NOT IN (SELECT id FROM users);

-- 3. حذف السجلات اليتيمة من notification_history
DELETE FROM notification_history 
WHERE user_id NOT IN (SELECT id FROM users);

-- 4. حذف السجلات اليتيمة من user_sessions
DELETE FROM user_sessions 
WHERE user_id NOT IN (SELECT id FROM users);

-- 5. حذف السجلات اليتيمة من user_trades
DELETE FROM user_trades 
WHERE user_id NOT IN (SELECT id FROM users);

-- 6. حذف السجلات اليتيمة من portfolio
DELETE FROM portfolio 
WHERE user_id NOT IN (SELECT id FROM users);

-- 7. حذف السجلات اليتيمة من user_settings
DELETE FROM user_settings 
WHERE user_id NOT IN (SELECT id FROM users);

-- 8. حذف السجلات اليتيمة من active_positions
DELETE FROM active_positions 
WHERE user_id NOT IN (SELECT id FROM users);

-- 9. حذف السجلات اليتيمة من operation_log
DELETE FROM operation_log 
WHERE user_id IS NOT NULL AND user_id NOT IN (SELECT id FROM users);

-- 10. حذف السجلات اليتيمة من admin_demo_portfolio_history
DELETE FROM admin_demo_portfolio_history 
WHERE admin_id NOT IN (SELECT id FROM users WHERE user_type = 'admin');

-- 11. حذف السجلات اليتيمة من user_binance_keys
DELETE FROM user_binance_keys 
WHERE user_id NOT IN (SELECT id FROM users);

-- التحقق بعد التنظيف
SELECT '=== نتائج التحقق بعد التنظيف ===' as status;
PRAGMA foreign_key_check;

COMMIT;
