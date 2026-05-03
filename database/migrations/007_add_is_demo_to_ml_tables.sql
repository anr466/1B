-- Migration 007: Add is_demo column to ML/learning tables
-- Date: 2026-05-02
-- Purpose: Track whether signals/patterns/alerts belong to demo or real mode
--           for proper admin filtering and analytics separation.

ALTER TABLE signal_learning
ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_signal_learning_is_demo ON signal_learning(is_demo);

ALTER TABLE system_alerts
ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_system_alerts_is_demo ON system_alerts(is_demo);

ALTER TABLE learning_validation_log
ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_learning_validation_log_is_demo ON learning_validation_log(is_demo);

ALTER TABLE ml_patterns
ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_ml_patterns_is_demo ON ml_patterns(is_demo);

ALTER TABLE signals_queue
ADD COLUMN IF NOT EXISTS is_demo BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_signals_queue_is_demo ON signals_queue(is_demo);
