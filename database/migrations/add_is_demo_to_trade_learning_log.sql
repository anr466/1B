-- Migration: Add is_demo column to trade_learning_log
-- Purpose: Isolate demo trades from real trades in ML learning system
-- Without this, demo trades pollute the adaptive optimizer's learning data.

ALTER TABLE trade_learning_log
    ADD COLUMN IF NOT EXISTS is_demo BOOLEAN NOT NULL DEFAULT FALSE;

-- Backfill: all existing rows are assumed real (safest default)
UPDATE trade_learning_log SET is_demo = FALSE WHERE is_demo IS NULL;

-- Index for fast filtered queries (optimizer reads with is_demo = FALSE frequently)
CREATE INDEX IF NOT EXISTS idx_trade_learning_log_is_demo
    ON trade_learning_log (is_demo, created_at);
