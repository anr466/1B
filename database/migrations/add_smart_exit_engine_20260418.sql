-- Smart Exit Engine Migration
-- Applied: 2026-04-18
-- Purpose: Add support for partial closes, exit phases, and dynamic trailing stops
-- Status: PENDING

-- 1. Add columns for partial close tracking
ALTER TABLE active_positions ADD COLUMN IF NOT EXISTS quantity_remaining DOUBLE PRECISION;
ALTER TABLE active_positions ADD COLUMN IF NOT EXISTS quantity_closed DOUBLE PRECISION DEFAULT 0;

-- 2. Add columns for exit phase management
ALTER TABLE active_positions ADD COLUMN IF NOT EXISTS exit_phase TEXT DEFAULT 'ACTIVE'; 
-- Phases: ACTIVE, SECURED, BREAK_EVEN, TRAILING, CLOSED

-- 3. Add column for break-even activation
ALTER TABLE active_positions ADD COLUMN IF NOT EXISTS break_even_activated BOOLEAN DEFAULT FALSE;

-- 4. Add columns for partial close history
ALTER TABLE active_positions ADD COLUMN IF NOT EXISTS partial_close_1_price DOUBLE PRECISION;
ALTER TABLE active_positions ADD COLUMN IF NOT EXISTS partial_close_1_pnl DOUBLE PRECISION DEFAULT 0;
ALTER TABLE active_positions ADD COLUMN IF NOT EXISTS partial_close_2_price DOUBLE PRECISION;
ALTER TABLE active_positions ADD COLUMN IF NOT EXISTS partial_close_2_pnl DOUBLE PRECISION DEFAULT 0;

-- 5. Backfill existing rows (set quantity_remaining = quantity for old positions)
UPDATE active_positions 
SET quantity_remaining = quantity 
WHERE quantity_remaining IS NULL;

-- 6. Create index for faster phase queries
CREATE INDEX IF NOT EXISTS idx_active_positions_phase ON active_positions(exit_phase);
