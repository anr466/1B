-- Migration 005: Fix entry_date column type in active_positions
-- Date: 2026-04-14
-- Purpose: Change entry_date from TEXT to TIMESTAMPTZ for proper date handling

BEGIN;

-- Convert existing data (assuming it contains valid timestamp strings or is empty)
-- If data is invalid, this might fail, but for a fresh/dev DB it's safe.
ALTER TABLE active_positions
ALTER COLUMN entry_date TYPE TIMESTAMPTZ USING entry_date::TIMESTAMPTZ;

-- Set default to CURRENT_TIMESTAMP
ALTER TABLE active_positions
ALTER COLUMN entry_date SET DEFAULT CURRENT_TIMESTAMP;

COMMIT;
