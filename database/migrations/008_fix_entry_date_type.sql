-- Migration 008: Fix entry_date column type from text → timestamp
-- The entry_date column in active_positions was created as text
-- but other date columns (created_at, updated_at, closed_at) are timestamp with time zone.
-- This causes COALESCE(entry_date, created_at) to fail with "types text and timestamp cannot be matched"
--
-- Fix: Convert entry_date to timestamp with time zone, using CURRENT_TIMESTAMP as fallback for invalid values

BEGIN;

-- Step 1: Convert any invalid/non-timestamp text values to NULL first (they'll get CURRENT_TIMESTAMP)
UPDATE active_positions
SET entry_date = NULL
WHERE entry_date IS NOT NULL
  AND entry_date !~ '^\d{4}-\d{2}-\d{2}';

-- Step 2: Add a temporary column with proper timestamp type
ALTER TABLE active_positions
ADD COLUMN entry_date_ts TIMESTAMP WITH TIME ZONE;

-- Step 3: Copy valid timestamps to the new column
UPDATE active_positions
SET entry_date_ts = 
    CASE 
        WHEN entry_date IS NOT NULL THEN entry_date::TIMESTAMP WITH TIME ZONE
        ELSE created_at
    END;

-- Step 4: Drop old column and rename new one
ALTER TABLE active_positions DROP COLUMN entry_date;
ALTER TABLE active_positions RENAME COLUMN entry_date_ts TO entry_date;

-- Step 5: Set NOT NULL constraint
ALTER TABLE active_positions ALTER COLUMN entry_date SET NOT NULL;
ALTER TABLE active_positions ALTER COLUMN entry_date SET DEFAULT CURRENT_TIMESTAMP;

COMMIT;
