-- Migration 003: Missing tables, orphan cleanup, and new indexes
-- Created: 2026-04-30

-- ============================================================
-- 1. Drop orphan/zombie tables
-- ============================================================
DROP TABLE IF EXISTS user_notifications CASCADE;
DROP TABLE IF EXISTS activity_log CASCADE;

-- ============================================================
-- 2. Create missing tables
-- ============================================================

CREATE TABLE IF NOT EXISTS trade_learning_log (
    id SERIAL PRIMARY KEY,
    trade_id INT,
    signal_id INT,
    user_id INT,
    pattern TEXT,
    result TEXT,
    score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS signal_learning (
    id SERIAL PRIMARY KEY,
    symbol TEXT,
    timeframe TEXT,
    signal_type TEXT,
    confidence FLOAT,
    result TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    feedback JSONB
);

CREATE TABLE IF NOT EXISTS learning_validation_log (
    id SERIAL PRIMARY KEY,
    model_name TEXT,
    version TEXT,
    accuracy FLOAT,
    precision FLOAT,
    recall FLOAT,
    f1_score FLOAT,
    validated_at TIMESTAMPTZ DEFAULT NOW(),
    details JSONB
);

CREATE TABLE IF NOT EXISTS system_alerts (
    id SERIAL PRIMARY KEY,
    user_id INT,
    type TEXT,
    severity TEXT,
    title TEXT,
    message TEXT,
    is_read BOOLEAN DEFAULT FALSE,
    is_dismissed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS ml_patterns (
    id SERIAL PRIMARY KEY,
    pattern_name TEXT,
    symbol TEXT,
    timeframe TEXT,
    confidence FLOAT,
    occurrences INT DEFAULT 0,
    last_seen TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_onboarding (
    id SERIAL PRIMARY KEY,
    user_id INT UNIQUE,
    steps_completed JSONB DEFAULT '[]'::jsonb,
    is_complete BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS password_reset_requests (
    id SERIAL PRIMARY KEY,
    user_id INT,
    email TEXT,
    token TEXT UNIQUE,
    is_used BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- 3. Create missing indexes
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_active_positions_closed_at ON active_positions(closed_at);
CREATE INDEX IF NOT EXISTS idx_active_positions_user_demo ON active_positions(user_id, is_demo);
CREATE INDEX IF NOT EXISTS idx_system_alerts_user_read ON system_alerts(user_id, is_read);
