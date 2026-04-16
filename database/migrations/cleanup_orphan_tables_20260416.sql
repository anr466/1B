-- Database Cleanup Migration
-- Applied: 2026-04-16
-- Purpose: Remove orphaned/deprecated tables that have been replaced
-- Status: PENDING

-- 1. demo_accounts — replaced by portfolio.is_demo=TRUE
--    Already dropped by improve_schema_20260403.sql, but safe to repeat
DROP TABLE IF EXISTS demo_accounts CASCADE;

-- 2. user_trades — replaced by active_positions (SSOT for all trades)
--    Code explicitly removed all references (db_portfolio_mixin.py:157, 1412)
DROP TABLE IF EXISTS user_trades CASCADE;

-- 3. paper_trading_log — defined in schema but zero Python code references it
DROP TABLE IF EXISTS paper_trading_log CASCADE;

-- 4. Drop orphaned indexes for user_trades (if they still exist)
DROP INDEX IF EXISTS idx_user_trades_user_date;
DROP INDEX IF EXISTS idx_user_trades_status;
DROP INDEX IF EXISTS idx_user_trades_symbol;
DROP INDEX IF EXISTS idx_user_trades_user_demo;

-- 5. Drop orphaned indexes for paper_trading_log (if they still exist)
DROP INDEX IF EXISTS idx_paper_trading_user;
DROP INDEX IF EXISTS idx_paper_trading_symbol;
