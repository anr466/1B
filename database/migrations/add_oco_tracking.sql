-- Migration: Add OCO Tracking and Reconciliation Columns
ALTER TABLE active_positions ADD COLUMN IF NOT EXISTS order_list_id BIGINT;
ALTER TABLE active_positions ADD COLUMN IF NOT EXISTS binance_order_id TEXT;
