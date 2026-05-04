BEGIN;

ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS first_trade_balance DOUBLE PRECISION;
ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS first_trade_at TIMESTAMPTZ;
ALTER TABLE portfolio ADD COLUMN IF NOT EXISTS initial_balance_source TEXT DEFAULT 'system_seed';

UPDATE portfolio
SET initial_balance_source = CASE
    WHEN COALESCE(initial_balance_source, '') = '' AND is_demo = TRUE THEN 'demo_account_seed'
    WHEN COALESCE(initial_balance_source, '') = '' THEN 'system_seed'
    ELSE initial_balance_source
END
WHERE COALESCE(initial_balance_source, '') = '';

COMMIT;
