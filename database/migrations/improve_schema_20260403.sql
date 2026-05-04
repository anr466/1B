-- Database Improvements Migration
-- Applied: 2026-04-03
-- Status: SUCCESS

-- 1. Indexes (8 created)
CREATE INDEX IF NOT EXISTS idx_trading_signals_strategy ON trading_signals(strategy);
CREATE INDEX IF NOT EXISTS idx_trading_signals_symbol ON trading_signals(symbol);
CREATE INDEX IF NOT EXISTS idx_trading_signals_generated ON trading_signals(generated_at DESC);
CREATE INDEX IF NOT EXISTS idx_activity_logs_action_status ON activity_logs(action, status);
CREATE INDEX IF NOT EXISTS idx_activity_logs_created ON activity_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_system_errors_severity ON system_errors(severity, resolved);
CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires ON revoked_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires ON user_sessions(expires_at);

-- 2. created_at columns (9 tables)
ALTER TABLE coin_trade_history ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE dynamic_blacklist ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE learning_validation_log ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE notification_delivery_log ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE operation_log ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE signal_learning ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE trading_signals ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE user_binance_balance ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE user_onboarding ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- 3. updated_at columns
ALTER TABLE system_status ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- 4. Portfolio defaults
ALTER TABLE portfolio ALTER COLUMN total_balance SET DEFAULT 0;
ALTER TABLE portfolio ALTER COLUMN available_balance SET DEFAULT 0;
ALTER TABLE portfolio ALTER COLUMN total_profit_loss SET DEFAULT 0;

-- 5. Drop orphan table
DROP TABLE IF EXISTS demo_accounts CASCADE;
