-- Activity Logs Cleanup Migration
-- Applied: 2026-04-16
-- Purpose: Auto-cleanup old activity_logs to prevent unbounded growth
-- Status: PENDING

-- 1. حذف السجلات الأقدم من 90 يوم
DELETE FROM activity_logs WHERE created_at < NOW() - INTERVAL '90 days';

-- 2. حذف السجلات المحلولة الأقدم من 30 يوم من system_errors
DELETE FROM system_errors WHERE resolved = TRUE AND resolved_at < NOW() - INTERVAL '30 days';

-- 3. حذف الإشارات المنتهية الأقدم من 7 أيام
DELETE FROM signals_queue WHERE status IN ('FILLED', 'REJECTED', 'EXPIRED')
    AND processed_at < NOW() - INTERVAL '7 days';

-- 4. حذف سجلات التحقق المنتهية
DELETE FROM verification_codes WHERE expires_at < EXTRACT(EPOCH FROM NOW() - INTERVAL '1 day');

-- 5. حذف الجلسات المنتهية
DELETE FROM user_sessions WHERE is_active = FALSE OR expires_at < NOW() - INTERVAL '1 day';

-- 6. حذف رموز FCM غير النشطة
DELETE FROM fcm_tokens WHERE is_active = FALSE AND updated_at < NOW() - INTERVAL '30 days';

-- 7. تنظيف سجل الإشعارات الأقدم من 60 يوم
DELETE FROM notification_history WHERE created_at < NOW() - INTERVAL '60 days';

-- 8. إعادة تعيين تسلسل المعرفات بعد الحذف
SELECT setval('activity_logs_id_seq', COALESCE((SELECT MAX(id) FROM activity_logs), 1), false);
SELECT setval('system_errors_id_seq', COALESCE((SELECT MAX(id) FROM system_errors), 1), false);
SELECT setval('signals_queue_id_seq', COALESCE((SELECT MAX(id) FROM signals_queue), 1), false);
