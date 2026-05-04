-- ============================================
-- Migration: Enable Foreign Keys & Add Missing Indexes
-- تاريخ: 2026-01-19
-- الهدف: تفعيل Foreign Keys وإضافة Indexes للأداء
-- ============================================

-- ⚠️ ملاحظة: Foreign Keys يجب تفعيلها في كل اتصال
-- هذا الملف للتوثيق والمرجع فقط
-- التفعيل الفعلي يتم في database_manager.py

-- ============================================
-- 1️⃣ إضافة Indexes المفقودة للأداء
-- ============================================

-- user_portfolio indexes
CREATE INDEX IF NOT EXISTS idx_user_portfolio_user_id ON user_portfolio(user_id);

-- user_trades indexes
CREATE INDEX IF NOT EXISTS idx_user_trades_user_id ON user_trades(user_id);
CREATE INDEX IF NOT EXISTS idx_user_trades_symbol ON user_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_user_trades_status ON user_trades(status);
CREATE INDEX IF NOT EXISTS idx_user_trades_entry_time ON user_trades(entry_time DESC);

-- user_settings indexes
CREATE INDEX IF NOT EXISTS idx_user_settings_user_demo ON user_settings(user_id, is_demo);

-- user_binance_keys indexes
CREATE INDEX IF NOT EXISTS idx_user_binance_keys_user_id ON user_binance_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_user_binance_keys_active ON user_binance_keys(is_active);

-- notifications indexes
CREATE INDEX IF NOT EXISTS idx_notifications_user_id ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_is_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at DESC);

-- active_positions indexes
CREATE INDEX IF NOT EXISTS idx_active_positions_user_id ON active_positions(user_id);
CREATE INDEX IF NOT EXISTS idx_active_positions_symbol ON active_positions(symbol);
CREATE INDEX IF NOT EXISTS idx_active_positions_is_active ON active_positions(is_active);

-- trading_history indexes (الأعمدة الفعلية: user_id, symbol, entry_time, exit_time)
CREATE INDEX IF NOT EXISTS idx_trading_history_user_id ON trading_history(user_id);
CREATE INDEX IF NOT EXISTS idx_trading_history_symbol ON trading_history(symbol);
CREATE INDEX IF NOT EXISTS idx_trading_history_entry_time ON trading_history(entry_time DESC);

-- group_a_audit indexes (الأعمدة الفعلية: run_date, created_at)
CREATE INDEX IF NOT EXISTS idx_group_a_audit_run_date ON group_a_audit(run_date DESC);
CREATE INDEX IF NOT EXISTS idx_group_a_audit_created_at ON group_a_audit(created_at DESC);

-- backtest_results indexes (حسب البنية الفعلية)
CREATE INDEX IF NOT EXISTS idx_backtest_results_created_at ON backtest_results(created_at DESC);

-- system_status indexes
CREATE INDEX IF NOT EXISTS idx_system_status_last_update ON system_status(last_update DESC);

-- fcm_tokens indexes
CREATE INDEX IF NOT EXISTS idx_fcm_tokens_user_id ON fcm_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_fcm_tokens_created_at ON fcm_tokens(created_at DESC);

-- ============================================
-- 2️⃣ ملاحظات التنفيذ
-- ============================================

-- Foreign Keys يتم تفعيلها تلقائياً في database_manager.py:
-- 1. في _init_connection_pool() - سطر 311، 315
-- 2. في get_connection() - يجب التأكد من التفعيل

-- للتحقق من حالة Foreign Keys:
-- PRAGMA foreign_keys;  -- يجب أن يرجع 1

-- للتحقق من الـ Indexes:
-- SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';

-- ============================================
-- 3️⃣ اختبار بعد التطبيق
-- ============================================

-- اختبار Foreign Keys:
-- SELECT * FROM pragma_foreign_key_list('user_trades');
-- SELECT * FROM pragma_foreign_key_list('user_portfolio');

-- اختبار الأداء:
-- EXPLAIN QUERY PLAN SELECT * FROM user_trades WHERE user_id = 1;
-- EXPLAIN QUERY PLAN SELECT * FROM user_trades WHERE symbol = 'BTCUSDT';

-- ============================================
-- ✅ الحالة: جاهز للتطبيق
-- ============================================
