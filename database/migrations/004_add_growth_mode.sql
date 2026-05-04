-- Migration 004: Add growth_mode column to portfolio table
-- Date: 2026-04-14
-- Purpose: Track the current growth mode (Launch, Growth, Standard, Pro) for each portfolio

ALTER TABLE portfolio
ADD COLUMN IF NOT EXISTS growth_mode TEXT DEFAULT 'Launch';

-- Add a comment to explain the values
COMMENT ON COLUMN portfolio.growth_mode IS 'Current growth mode: Launch (<$100), Growth ($100-$1k), Standard ($1k-$10k), Pro (>$10k)';
