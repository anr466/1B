-- 002_workers_setup.sql
-- إنشاء بنية العمال المتوازية (Scanner & Executor)

-- 1. جدول طابور الإشارات (الجسر بين الصياد والمنفذ)
CREATE TABLE IF NOT EXISTS signals_queue (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    symbol VARCHAR(20) NOT NULL,
    type VARCHAR(10) NOT NULL, -- 'LONG' or 'SHORT'
    entry_price DECIMAL(18, 8),
    stop_loss DECIMAL(18, 8),
    take_profit DECIMAL(18, 8),
    score INT DEFAULT 0,
    strategy_name VARCHAR(50),
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, PROCESSING, FILLED, REJECTED, EXPIRED
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,
    processed_at TIMESTAMP,
    rejection_reason TEXT,
    trade_id INT
);

-- 2. جدول الإشعارات (نظام صامت وقابل للتخصيص)
CREATE TABLE IF NOT EXISTS user_notifications (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL,
    type VARCHAR(20) NOT NULL, -- 'info', 'success', 'warning', 'error', 'critical'
    title VARCHAR(100),
    message TEXT,
    metadata JSONB DEFAULT '{}',
    channel VARCHAR(20) DEFAULT 'in_app', -- 'push', 'email', 'in_app'
    is_read BOOLEAN DEFAULT FALSE,
    is_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- 3. فهارس للأداء العالي
CREATE INDEX IF NOT EXISTS idx_signals_status_expires ON signals_queue(status, expires_at);
CREATE INDEX IF NOT EXISTS idx_signals_user_status ON signals_queue(user_id, status);
CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON user_notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON user_notifications(created_at);

-- 4. إضافة عمود التحكم الدقيق في الدخول (اختياري، لتعزيز الأمان)
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS allow_new_entries BOOLEAN DEFAULT TRUE;
