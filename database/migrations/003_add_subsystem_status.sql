-- Migration 003: Add subsystem_status column to system_status
-- Date: 2026-04-14
-- Purpose: StateManager reads/writes subsystem_status (JSON) but column was missing

ALTER TABLE system_status
ADD COLUMN IF NOT EXISTS subsystem_status TEXT DEFAULT '{}';
