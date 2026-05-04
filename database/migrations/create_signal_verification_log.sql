-- Migration: Create signal_verification_log table
-- Purpose: Log all signals for verification and analysis

CREATE TABLE IF NOT EXISTS signal_verification_log (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(50) NOT NULL,
    signal_side VARCHAR(20) NOT NULL,  -- 'LONG', 'SHORT', 'UNKNOWN'
    strategy VARCHAR(50) NOT NULL,
    entry_price DECIMAL(20, 8),
    stop_loss DECIMAL(20, 8),
    score DECIMAL(10, 4),
    confidence DECIMAL(5, 2),
    trend VARCHAR(20),
    predicted_wr DECIMAL(5, 2),
    risk_reward_ratio DECIMAL(10, 4),
    mode VARCHAR(20),  -- 'demo', 'real'
    entry_indicators JSONB,
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for efficient querying
CREATE INDEX IF NOT EXISTS idx_signal_verification_symbol ON signal_verification_log(symbol);
CREATE INDEX IF NOT EXISTS idx_signal_verification_created ON signal_verification_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signal_verification_mode ON signal_verification_log(mode);
