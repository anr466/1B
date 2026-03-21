CREATE TABLE IF NOT EXISTS demo_accounts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    initial_balance DOUBLE PRECISION DEFAULT 1000.0,
    available_balance DOUBLE PRECISION DEFAULT 1000.0,
    invested_balance DOUBLE PRECISION DEFAULT 0.0,
    total_balance DOUBLE PRECISION DEFAULT 1000.0,
    total_profit_loss DOUBLE PRECISION DEFAULT 0.0,
    total_profit_loss_percentage DOUBLE PRECISION DEFAULT 0.0,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    reset_count INTEGER DEFAULT 0,
    last_reset_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

INSERT INTO demo_accounts (
    user_id,
    initial_balance,
    available_balance,
    invested_balance,
    total_balance,
    total_profit_loss,
    total_profit_loss_percentage,
    total_trades,
    winning_trades,
    losing_trades,
    updated_at
)
SELECT
    p.user_id,
    COALESCE(NULLIF(p.initial_balance, 0), 1000.0),
    COALESCE(p.available_balance, COALESCE(NULLIF(p.initial_balance, 0), 1000.0)),
    COALESCE(p.invested_balance, 0.0),
    COALESCE(p.total_balance, COALESCE(NULLIF(p.initial_balance, 0), 1000.0)),
    COALESCE(p.total_profit_loss, 0.0),
    COALESCE(p.total_profit_loss_percentage, 0.0),
    COALESCE(p.total_trades, 0),
    COALESCE(p.winning_trades, 0),
    COALESCE(p.losing_trades, 0),
    CURRENT_TIMESTAMP
FROM portfolio p
WHERE p.is_demo = TRUE
ON CONFLICT (user_id) DO NOTHING;
