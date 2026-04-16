-- Migration 006: Add bio and avatar columns to users table
-- Date: 2026-04-14
-- Purpose: Support profile updates with bio and avatar fields

BEGIN;

ALTER TABLE users
ADD COLUMN IF NOT EXISTS bio TEXT DEFAULT NULL;

ALTER TABLE users
ADD COLUMN IF NOT EXISTS avatar TEXT DEFAULT NULL;

COMMIT;
