-- ============================================================================
-- Enable Foreign Key Constraints - PostgreSQL Version
-- ============================================================================
-- التاريخ: 2026-02-14 (migrated from SQLite 2026-04-29)
-- الهدف: Ensure foreign key constraints and data integrity
-- ============================================================================

-- PostgreSQL enables foreign keys by default — no PRAGMA needed

-- Add missing foreign keys using real ALTER TABLE (PostgreSQL supports this)
-- Note: These run as idempotent safety checks

-- Add FK: active_positions.user_id -> users.id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_active_positions_user_id'
    ) THEN
        ALTER TABLE active_positions
        ADD CONSTRAINT fk_active_positions_user_id
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    END IF;
END $$;

-- Add FK: portfolio.user_id -> users.id
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_portfolio_user_id'
    ) THEN
        ALTER TABLE portfolio
        ADD CONSTRAINT fk_portfolio_user_id
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;
    END IF;
END $$;

-- ============================================================================
-- Clean orphan data
-- ============================================================================

-- Orphan portfolio rows
DELETE FROM portfolio WHERE user_id NOT IN (SELECT id FROM users);

-- Orphan active_positions rows
DELETE FROM active_positions WHERE user_id NOT IN (SELECT id FROM users);

SELECT 'Data integrity cleanup completed - PostgreSQL';
