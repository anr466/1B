-- ============================================================================
-- 🔧 SCHEMA UNIFICATION BLUEPRINT v1.0
-- ============================================================================
-- TYPE: DATABASE_SCHEMA_AUDIT + NAMING_UNIFICATION
-- TIER: PRODUCTION
-- DATE: 2026-01-03
-- DATABASE: trading_database.db (43 tables)
-- ============================================================================

-- ============================================================================
-- PHASE 1: BACKUP VERIFICATION (RUN MANUALLY FIRST!)
-- ============================================================================
-- IMPORTANT: Ensure WAL mode is enabled before proceeding
-- PRAGMA journal_mode; -- Should return 'wal'

-- ============================================================================
-- PHASE 2: DUPLICATE TABLE RESOLUTION
-- ============================================================================

-- ISSUE: Two tables for activity logs: activity_log (1 row) and activity_logs (3 rows)
-- ACTION: Merge activity_log into activity_logs, then drop activity_log

-- Step 2.1: Add missing columns to activity_logs if needed
-- activity_log has: id, action, ip_address, details, created_at
-- activity_logs has: id, user_id, action, details, timestamp, created_at, endpoint, ip_address, user_agent, method, status, response_time, error_message, component

-- Step 2.2: Migrate data from activity_log to activity_logs
INSERT INTO activity_logs (action, ip_address, details, created_at, component)
SELECT action, ip_address, details, created_at, 'legacy_migration'
FROM activity_log
WHERE id NOT IN (SELECT id FROM activity_logs);

-- Step 2.3: Drop the duplicate table (CAUTION!)
-- DROP TABLE activity_log; -- Uncomment after verifying migration

-- ============================================================================
-- PHASE 3: DUPLICATE INDEX CLEANUP
-- ============================================================================

-- user_trades: Remove duplicate indexes (keep most useful ones)
-- Current: 10 indexes (excessive!)
-- Keep: idx_user_trades_user_id, idx_user_trades_user_demo_status, idx_user_trades_created_at
DROP INDEX IF EXISTS idx_user_trades_user;          -- Duplicate of idx_user_trades_user_id
DROP INDEX IF EXISTS idx_user_trades_user_date;     -- Covered by idx_user_trades_user_id + created_at

-- system_errors: Remove duplicates
DROP INDEX IF EXISTS idx_errors_created_at;         -- Duplicate of idx_system_errors_created_at
DROP INDEX IF EXISTS idx_errors_resolved;           -- Duplicate of idx_system_errors_resolved

-- activity_logs: Remove duplicates
DROP INDEX IF EXISTS idx_activity_logs_user;        -- Duplicate of idx_activity_logs_user_id

-- active_positions: Remove duplicates
DROP INDEX IF EXISTS idx_active_positions_user;     -- Duplicate of idx_active_positions_user_id

-- notification_history: Remove duplicates
DROP INDEX IF EXISTS idx_notif_history_user;        -- Duplicate of idx_notification_history_user_id

-- fcm_tokens: Remove duplicates
DROP INDEX IF EXISTS idx_fcm_user;                  -- Duplicate of idx_fcm_tokens_user_id

-- user_binance_keys: Remove duplicates
DROP INDEX IF EXISTS idx_binance_keys_user;         -- Duplicate of idx_user_binance_keys_user_id

-- user_biometric_auth: Remove duplicates
DROP INDEX IF EXISTS idx_biometric_user;            -- Duplicate of idx_user_biometric_auth_user_id

-- user_devices: Remove duplicates
DROP INDEX IF EXISTS idx_devices_user;              -- Duplicate of idx_user_devices_user_id

-- user_notification_settings: Remove duplicates
DROP INDEX IF EXISTS idx_notif_settings_user;       -- Duplicate of idx_user_notification_settings_user_id

-- user_sessions: Remove duplicates
DROP INDEX IF EXISTS idx_sessions_user;             -- Duplicate of idx_user_sessions_user_id

-- security_audit_log: Remove duplicates (keep specific ones)
DROP INDEX IF EXISTS idx_audit_user;                -- Covered by more specific indexes

-- operation_log: Remove duplicates
DROP INDEX IF EXISTS idx_operation_log_user;        -- Duplicate of idx_operation_log_user_id

-- ============================================================================
-- PHASE 4: MISSING INDEX CREATION
-- ============================================================================

-- Add performance-critical indexes that are missing

-- active_positions: Add status index for WHERE status='active' queries
CREATE INDEX IF NOT EXISTS idx_active_positions_status ON active_positions(is_active);

-- user_trades: Add composite index for common queries
CREATE INDEX IF NOT EXISTS idx_user_trades_user_status ON user_trades(user_id, status);

-- portfolio: Ensure composite index exists
CREATE INDEX IF NOT EXISTS idx_portfolio_user_demo ON portfolio(user_id, is_demo);

-- ============================================================================
-- PHASE 5: DATA TYPE CONSISTENCY FIXES
-- ============================================================================

-- NOTE: SQLite doesn't support ALTER COLUMN, so we need to recreate tables
-- For verification_codes, the data types are inconsistent:
-- - created_at is TEXT (should be TIMESTAMP)
-- - expires_at is REAL (Unix timestamp - acceptable but inconsistent)

-- Since this is a verification table that gets cleaned regularly,
-- we can recreate it with proper types

-- Create new table with correct schema
CREATE TABLE IF NOT EXISTS verification_codes_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    otp_code TEXT NOT NULL,
    purpose TEXT DEFAULT 'verification',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    attempts INTEGER DEFAULT 0,
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMP,
    code TEXT,
    code_type TEXT,
    max_attempts INTEGER DEFAULT 3,
    is_used BOOLEAN DEFAULT 0,
    used_at TIMESTAMP,
    UNIQUE(email, purpose)
);

-- Migration would be:
-- INSERT INTO verification_codes_new SELECT * FROM verification_codes WHERE created_at > datetime('now', '-1 day');
-- DROP TABLE verification_codes;
-- ALTER TABLE verification_codes_new RENAME TO verification_codes;

-- ============================================================================
-- PHASE 6: MISSING FOREIGN KEY INDEXES
-- ============================================================================

-- Every FK should have an index for JOIN performance
-- Most are covered, but verify:

CREATE INDEX IF NOT EXISTS idx_password_reset_user_id ON password_reset_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_notification_history_type ON notification_history(type);
CREATE INDEX IF NOT EXISTS idx_system_alerts_severity ON system_alerts(severity);
CREATE INDEX IF NOT EXISTS idx_system_alerts_resolved ON system_alerts(resolved);

-- ============================================================================
-- PHASE 7: NAMING CONVENTION VALIDATION
-- ============================================================================

-- All tables follow snake_case ✅
-- All columns follow snake_case ✅
-- All indexes follow idx_{table}_{column} pattern ✅ (after cleanup)

-- No violations found in naming conventions

-- ============================================================================
-- PHASE 8: CONSTRAINT VALIDATION
-- ============================================================================

-- user_binance_keys: Has UNIQUE(user_id, api_key) ✅
-- portfolio: Has UNIQUE(user_id, is_demo) ✅
-- user_settings: Has UNIQUE(user_id, is_demo) ✅
-- All have proper ON DELETE CASCADE ✅

-- ============================================================================
-- PHASE 9: PERFORMANCE OPTIMIZATIONS
-- ============================================================================

-- Enable memory-mapped I/O for better performance
PRAGMA mmap_size = 268435456; -- 256MB

-- Optimize database
VACUUM;
ANALYZE;

-- ============================================================================
-- DEBT SCORE CALCULATION
-- ============================================================================
/*
Violations Found:
- Duplicate tables: 1 (activity_log/activity_logs) × 50 = 50
- Duplicate indexes: 14 × 5 = 70
- Data type inconsistencies: 2 (verification_codes) × 10 = 20
- Missing indexes: 4 × 10 = 40

TOTAL DEBT SCORE: 180

INTERPRETATION:
- Score < 100: Safe for production ❌
- Score 100-300: Fix naming violations before next sprint ✅ (WE ARE HERE)
- Score > 300: BLOCK deployment

RECOMMENDATION: FIX_FIRST (Fix duplicate indexes and table before production)
*/

-- ============================================================================
-- EXECUTION ORDER
-- ============================================================================
/*
1. Run PHASE 3 first (index cleanup) - Safe, no data loss
2. Run PHASE 4 (missing indexes) - Safe, improves performance
3. Run PHASE 6 (FK indexes) - Safe, improves performance
4. Run PHASE 9 (VACUUM/ANALYZE) - Safe, improves performance
5. Run PHASE 2 (table merge) - CAUTION: Verify data first!
6. Run PHASE 5 (data type fix) - CAUTION: Test in dev first!
*/
