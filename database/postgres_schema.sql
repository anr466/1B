CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    phone_number TEXT,
    name TEXT,
    user_type TEXT DEFAULT 'user',
    email_verified BOOLEAN DEFAULT FALSE,
    is_phone_verified BOOLEAN DEFAULT FALSE,
    preferred_verification_method TEXT DEFAULT 'email',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMPTZ,
    email_verified_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS user_settings (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_demo BOOLEAN DEFAULT FALSE,
    trading_enabled BOOLEAN DEFAULT FALSE,
    trade_amount DOUBLE PRECISION DEFAULT 100.0,
    position_size_percentage DOUBLE PRECISION DEFAULT 10.0,
    stop_loss_pct DOUBLE PRECISION DEFAULT 2.0,
    trailing_distance DOUBLE PRECISION DEFAULT 3.0,
    take_profit_pct DOUBLE PRECISION DEFAULT 5.0,
    max_positions INTEGER DEFAULT 5,
    risk_level TEXT DEFAULT 'medium',
    max_trades_per_day INTEGER DEFAULT 10,
    max_position_size DOUBLE PRECISION DEFAULT 100,
    max_daily_loss_pct DOUBLE PRECISION DEFAULT 10.0,
    trading_mode TEXT DEFAULT 'demo',
    notifications_enabled BOOLEAN DEFAULT TRUE,
    onboarding_completed BOOLEAN DEFAULT FALSE,
    volatility_buffer DOUBLE PRECISION DEFAULT 0.3,
    min_signal_strength DOUBLE PRECISION DEFAULT 0.6,
    daily_loss_limit DOUBLE PRECISION DEFAULT 100.0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, is_demo)
);

CREATE TABLE IF NOT EXISTS portfolio (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    balance DOUBLE PRECISION DEFAULT 1000.0,
    initial_balance DOUBLE PRECISION DEFAULT 0.0,
    totalbalance DOUBLE PRECISION DEFAULT 1000.0,
    availablebalance DOUBLE PRECISION DEFAULT 1000.0,
    total_balance DOUBLE PRECISION DEFAULT 1000.0,
    available_balance DOUBLE PRECISION DEFAULT 1000.0,
    invested_balance DOUBLE PRECISION DEFAULT 0,
    total_profit_loss DOUBLE PRECISION DEFAULT 0,
    totalprofitloss DOUBLE PRECISION DEFAULT 0,
    total_profit_loss_percentage DOUBLE PRECISION DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    is_demo BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, is_demo)
);

CREATE TABLE IF NOT EXISTS user_binance_keys (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    api_key TEXT NOT NULL,
    api_secret TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_trades (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    entry_time TEXT NOT NULL,
    exit_time TEXT,
    entry_price DOUBLE PRECISION NOT NULL,
    exit_price DOUBLE PRECISION,
    quantity DOUBLE PRECISION NOT NULL,
    status TEXT DEFAULT 'open',
    profit_loss DOUBLE PRECISION,
    profit_loss_percentage DOUBLE PRECISION,
    is_demo BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    strategy TEXT DEFAULT 'SCALP_V8',
    timeframe TEXT DEFAULT '1h',
    side TEXT DEFAULT 'LONG',
    stop_loss DOUBLE PRECISION,
    take_profit DOUBLE PRECISION,
    is_favorite BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS active_positions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    strategy TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    position_type TEXT NOT NULL,
    entry_date TEXT NOT NULL,
    entry_price DOUBLE PRECISION,
    quantity DOUBLE PRECISION,
    stop_loss DOUBLE PRECISION,
    take_profit DOUBLE PRECISION,
    order_id TEXT,
    entry_commission DOUBLE PRECISION DEFAULT 0,
    exit_commission DOUBLE PRECISION DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    is_demo BOOLEAN DEFAULT FALSE,
    ml_status TEXT DEFAULT 'none',
    ml_confidence DOUBLE PRECISION DEFAULT 0.0,
    signal_metadata TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    trailing_sl_price DOUBLE PRECISION DEFAULT 0,
    highest_price DOUBLE PRECISION DEFAULT 0,
    exit_reason TEXT,
    exit_price DOUBLE PRECISION,
    profit_loss DOUBLE PRECISION DEFAULT 0,
    profit_pct DOUBLE PRECISION,
    closed_at TIMESTAMPTZ,
    entry_indicators TEXT,
    exit_order_id TEXT,
    position_size DOUBLE PRECISION DEFAULT 0,
    break_even_moved INTEGER DEFAULT 0,
    tp_levels_hit TEXT,
    brain_decision_id TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_active_positions_unique_open
ON active_positions(user_id, symbol, strategy, is_demo)
WHERE is_active = TRUE;

CREATE TABLE IF NOT EXISTS activity_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    component TEXT,
    action TEXT NOT NULL,
    details TEXT,
    status TEXT DEFAULT 'success',
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS successful_coins (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    strategy TEXT,
    timeframe TEXT,
    success_count INTEGER DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    success_rate DOUBLE PRECISION DEFAULT 0,
    score DOUBLE PRECISION DEFAULT 0,
    profit_pct DOUBLE PRECISION DEFAULT 0,
    win_rate DOUBLE PRECISION DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    market_trend TEXT,
    avg_trade_duration_hours DOUBLE PRECISION,
    trading_style TEXT,
    analysis_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(symbol, strategy, timeframe)
);

CREATE TABLE IF NOT EXISTS trading_signals (
    id BIGSERIAL PRIMARY KEY,
    symbol TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    strategy TEXT,
    timeframe TEXT,
    price DOUBLE PRECISION,
    confidence DOUBLE PRECISION DEFAULT 0,
    is_processed BOOLEAN DEFAULT FALSE,
    generated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_status (
    id BIGINT PRIMARY KEY,
    status TEXT DEFAULT 'running',
    last_update TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_running BOOLEAN DEFAULT TRUE,
    group_b_status TEXT DEFAULT 'idle',
    total_coins_analyzed INTEGER DEFAULT 0,
    successful_coins_count INTEGER DEFAULT 0,
    system_uptime_seconds INTEGER DEFAULT 0,
    total_users INTEGER DEFAULT 0,
    active_trades INTEGER DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    trading_status TEXT DEFAULT 'idle',
    database_status TEXT DEFAULT 'connected',
    trading_state TEXT DEFAULT 'stopped',
    message TEXT DEFAULT '',
    session_id TEXT,
    mode TEXT DEFAULT 'demo',
    initiated_by TEXT,
    started_at TIMESTAMPTZ,
    pid INTEGER
);

INSERT INTO system_status (id, status, is_running)
VALUES (1, 'running', TRUE)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS verification_codes (
    id BIGSERIAL PRIMARY KEY,
    email TEXT NOT NULL,
    otp_code TEXT NOT NULL,
    purpose TEXT DEFAULT 'verification',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    expires_at DOUBLE PRECISION NOT NULL,
    attempts INTEGER DEFAULT 0,
    verified BOOLEAN DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    UNIQUE(email, purpose)
);

CREATE TABLE IF NOT EXISTS notifications (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'info',
    is_read BOOLEAN DEFAULT FALSE,
    data TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS notification_history (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    notification_type TEXT DEFAULT 'general',
    type TEXT DEFAULT 'general',
    title TEXT,
    message TEXT,
    sent_via TEXT DEFAULT 'push',
    status TEXT DEFAULT 'sent',
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS user_notification_settings (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    trade_notifications BOOLEAN DEFAULT TRUE,
    price_alerts BOOLEAN DEFAULT TRUE,
    system_notifications BOOLEAN DEFAULT TRUE,
    marketing_notifications BOOLEAN DEFAULT FALSE,
    push_enabled BOOLEAN DEFAULT TRUE,
    email_enabled BOOLEAN DEFAULT TRUE,
    sms_enabled BOOLEAN DEFAULT FALSE,
    notify_new_deal BOOLEAN DEFAULT TRUE,
    notify_deal_profit BOOLEAN DEFAULT TRUE,
    notify_deal_loss BOOLEAN DEFAULT TRUE,
    notify_daily_profit BOOLEAN DEFAULT TRUE,
    notify_daily_loss BOOLEAN DEFAULT TRUE,
    notify_low_balance BOOLEAN DEFAULT TRUE,
    settings_data TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_devices (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_id TEXT,
    device_type TEXT,
    device_name TEXT,
    os_version TEXT,
    app_version TEXT,
    push_token TEXT,
    fcm_token TEXT,
    is_trusted BOOLEAN DEFAULT TRUE,
    device_model TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMPTZ,
    last_active_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fcm_tokens (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    fcm_token TEXT NOT NULL UNIQUE,
    platform TEXT DEFAULT 'android',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_sessions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token TEXT NOT NULL,
    device_info TEXT,
    ip_address TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_errors (
    id BIGSERIAL PRIMARY KEY,
    error_type TEXT NOT NULL,
    error_message TEXT NOT NULL,
    component TEXT,
    severity TEXT DEFAULT 'error',
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS admin_notification_settings (
    id BIGINT PRIMARY KEY,
    telegram_enabled BOOLEAN DEFAULT FALSE,
    telegram_bot_token TEXT,
    telegram_chat_id TEXT,
    email_enabled BOOLEAN DEFAULT FALSE,
    admin_email TEXT,
    webhook_enabled BOOLEAN DEFAULT FALSE,
    webhook_url TEXT,
    push_enabled BOOLEAN DEFAULT TRUE,
    notify_on_error BOOLEAN DEFAULT TRUE,
    notify_on_trade BOOLEAN DEFAULT TRUE,
    notify_on_warning BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO admin_notification_settings (id)
VALUES (1)
ON CONFLICT (id) DO NOTHING;

CREATE TABLE IF NOT EXISTS security_audit_log (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    resource TEXT,
    ip_address TEXT,
    user_agent TEXT,
    status TEXT DEFAULT 'success',
    details TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_phone_number_unique
ON users(phone_number)
WHERE phone_number IS NOT NULL AND phone_number <> '';
CREATE INDEX IF NOT EXISTS idx_users_user_type ON users(user_type);
CREATE INDEX IF NOT EXISTS idx_user_settings_user_id ON user_settings(user_id);
CREATE INDEX IF NOT EXISTS idx_user_binance_keys_user_active ON user_binance_keys(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_active_positions_user ON active_positions(user_id);
CREATE INDEX IF NOT EXISTS idx_active_positions_symbol ON active_positions(symbol);
CREATE INDEX IF NOT EXISTS idx_active_positions_active ON active_positions(is_active);
CREATE INDEX IF NOT EXISTS idx_active_positions_user_active ON active_positions(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_user_trades_user_date ON user_trades(user_id, entry_time DESC);
CREATE INDEX IF NOT EXISTS idx_user_trades_status ON user_trades(user_id, status);
CREATE INDEX IF NOT EXISTS idx_user_trades_symbol ON user_trades(symbol);
CREATE INDEX IF NOT EXISTS idx_successful_coins_symbol ON successful_coins(symbol, is_active);
CREATE INDEX IF NOT EXISTS idx_successful_coins_score ON successful_coins(score DESC, is_active);
