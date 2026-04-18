-- Migration: Strategy Learning Table
-- Purpose: Persist learning data in DB so Scanner and Executor share the same brain.
CREATE TABLE IF NOT EXISTS strategy_learning (
    strategy_name TEXT NOT NULL,
    regime TEXT NOT NULL,
    score DOUBLE PRECISION DEFAULT 0.0,
    trades INTEGER DEFAULT 0,
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (strategy_name, regime)
);

-- Index for faster reads
CREATE INDEX IF NOT EXISTS idx_strategy_learning_name ON strategy_learning(strategy_name);
