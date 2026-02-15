-- Migration: إضافة الحقول المفقودة الحرجة
-- Date: 2025-12-31
-- Purpose: توافق النظام مع المفهوم الموحد

BEGIN TRANSACTION;

-- 1. إضافة الحقول المفقودة في user_trades
ALTER TABLE user_trades ADD COLUMN strategy TEXT DEFAULT 'scalping';
ALTER TABLE user_trades ADD COLUMN timeframe TEXT DEFAULT '5m';
ALTER TABLE user_trades ADD COLUMN side TEXT DEFAULT 'buy';
ALTER TABLE user_trades ADD COLUMN stop_loss REAL;
ALTER TABLE user_trades ADD COLUMN take_profit REAL;

-- 2. إضافة الحقول المفقودة في system_status
ALTER TABLE system_status ADD COLUMN trading_status TEXT DEFAULT 'stopped';
ALTER TABLE system_status ADD COLUMN database_status TEXT DEFAULT 'connected';

-- 3. إضافة الحقول المتوسطة
ALTER TABLE user_settings ADD COLUMN biometric_enabled BOOLEAN DEFAULT 0;
ALTER TABLE notification_history ADD COLUMN notification_type TEXT DEFAULT 'info';
ALTER TABLE user_devices ADD COLUMN push_token TEXT;
ALTER TABLE user_devices ADD COLUMN is_trusted BOOLEAN DEFAULT 0;
ALTER TABLE user_devices ADD COLUMN last_login TIMESTAMP;
ALTER TABLE user_biometric_auth ADD COLUMN biometric_hash TEXT;
ALTER TABLE verification_codes ADD COLUMN used_at TIMESTAMP;
ALTER TABLE activity_logs ADD COLUMN component TEXT DEFAULT 'system';
ALTER TABLE users ADD COLUMN email_verified_at TIMESTAMP;

-- 4. إنشاء فهارس للحقول الجديدة
CREATE INDEX IF NOT EXISTS idx_user_trades_strategy ON user_trades(strategy);
CREATE INDEX IF NOT EXISTS idx_user_trades_timeframe ON user_trades(timeframe);
CREATE INDEX IF NOT EXISTS idx_user_trades_side ON user_trades(side);
CREATE INDEX IF NOT EXISTS idx_system_status_trading ON system_status(trading_status);

COMMIT;
