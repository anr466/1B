# Database Schema — قاعدة البيانات

> **مبني على الملفات الفعلية في `database/` و `postgres_schema.sql`**
> **آخر تحديث:** 2026-04-14 — تكامل محرك النمو الذكي + ملف التعلم الذاتي

## نظرة عامة
قاعدة بيانات PostgreSQL تدعم نظام التداول الذكي. تتضمن 27 جدولاً أساسياً، بالإضافة إلى ملف حالة خارجي `data/risk_learning_state.json` لتخزين خبرة النظام.

---

## ملفات قاعدة البيانات الفعلية

| الملف | الوظيفة |
|-------|---------|
| `database_manager.py` | مدير قاعدة البيانات الموحد (1566 سطر) — God Object مقسّم |
| `db_trading_mixin.py` | mixin عمليات التداول |
| `db_users_mixin.py` | mixin عمليات المستخدمين |
| `db_portfolio_mixin.py` | mixin عمليات المحفظة |
| `db_notifications_mixin.py` | mixin عمليات الإشعارات |
| `postgres_schema.sql` | مخطط PostgreSQL الكامل (487 سطر) |
| `database_config.json` | تكوين الاتصال |
| `migrations/` | ملفات الترحيل (14 ملف SQL) |

---

## الجداول الفعلية (27 جدول)

### مجموعة المستخدمين (5 جداول)

| الجدول | الأعمدة الرئيسية | القيود |
|--------|-----------------|--------|
| `users` | id, username, email, password_hash, phone_number, user_type, email_verified, is_active | UNIQUE(username), UNIQUE(email), UNIQUE(phone_number WHERE NOT NULL) |
| `user_settings` | user_id, is_demo, trading_enabled, trade_amount, position_size_percentage, stop_loss_pct, risk_level, max_trades_per_day, max_daily_loss_pct, volatility_buffer, min_signal_strength | UNIQUE(user_id, is_demo) |
| `user_binance_keys` | user_id, api_key, api_secret, is_active, is_testnet, permissions, last_verified | FK→users |
| `user_sessions` | user_id, session_token, device_info, ip_address, is_active, expires_at | FK→users |
| `user_devices` | user_id, device_id, device_type, device_name, push_token, fcm_token, is_trusted | FK→users |

### مجموعة التداول (4 جداول)

| الجدول | الأعمدة الرئيسية | القيود |
|--------|-----------------|--------|
| `active_positions` | user_id, symbol, strategy, timeframe, entry_price, stop_loss, take_profit, trailing_sl_price, highest_price, is_active, ml_status, ml_confidence, brain_decision_id, exit_reason, tp_levels_hit | UNIQUE(user_id, symbol, strategy, is_demo) WHERE is_active |
| `user_trades` | user_id, symbol, entry_time, exit_time, entry_price, exit_price, quantity, status, profit_loss, strategy, timeframe, side, is_demo | FK→users |
| `trading_signals` | symbol, signal_type, strategy, timeframe, price, confidence, is_processed | — |
| `successful_coins` | symbol, strategy, timeframe, success_count, total_trades, success_rate, score, win_rate, market_trend, trading_style | UNIQUE(symbol, strategy, timeframe) |

### مجموعة المحفظة (3 جداول)

| الجدول | الأعمدة الرئيسية | القيود |
|--------|-----------------|--------|
| `portfolio` | user_id, initial_balance, total_balance, available_balance, invested_balance, total_profit_loss, total_trades, winning_trades, losing_trades, is_demo, first_trade_balance, first_trade_at, initial_balance_source | UNIQUE(user_id, is_demo) |
| `demo_accounts` | user_id, initial_balance, available_balance, invested_balance, total_balance, total_profit_loss, total_trades, winning_trades, losing_trades, reset_count | UNIQUE(user_id) |
| `portfolio_growth_history` | user_id, date, total_balance, daily_pnl, daily_pnl_percentage, active_trades_count, is_demo | UNIQUE(user_id, date, is_demo) |

### مجموعة المصادقة والتحقق (3 جداول)

| الجدول | الأعمدة الرئيسية | القيود |
|--------|-----------------|--------|
| `verification_codes` | email, otp_code, purpose, expires_at, attempts, verified | UNIQUE(email, purpose) |
| `pending_verifications` | user_id, action, otp, expires_at, method, new_value, old_password, attempts | UNIQUE(user_id, action) |
| `security_audit_log` | user_id, action, resource, ip_address, user_agent, status, details | FK→users |

### مجموعة الإشعارات (4 جداول)

| الجدول | الأعمدة الرئيسية | القيود |
|--------|-----------------|--------|
| `notifications` | user_id, title, message, type, is_read, data | FK→users |
| `notification_history` | user_id, notification_type, type, title, message, sent_via, status, read_at | FK→users |
| `user_notification_settings` | user_id, trade_notifications, price_alerts, push_enabled, notify_new_deal, notify_deal_profit, notify_deal_loss | UNIQUE(user_id) |
| `fcm_tokens` | user_id, fcm_token, platform, is_active | UNIQUE(fcm_token) |

### مجموعة النظام (5 جداول)

| الجدول | الأعمدة الرئيسية | القيود |
|--------|-----------------|--------|
| `system_status` | id, status, is_running, trading_state, group_b_status, mode, session_id, pid, total_users, active_trades, total_trades, database_status, system_uptime_seconds | PK=1 (سجل واحد) |
| `system_errors` | error_type, error_message, component, severity, resolved, resolved_at | — |
| `activity_logs` | user_id, component, action, details, status | FK→users |
| `admin_notification_settings` | telegram_enabled, telegram_bot_token, telegram_chat_id, email_enabled, webhook_enabled, notify_on_error, notify_on_trade, notify_on_warning | PK=1 (سجل واحد) |
| `user_binance_balance` | user_id, asset, free_balance, locked_balance, total_balance | FK→users |

### مجموعة التعلم الآلي (3 جداول)

| الجدول | الأعمدة الرئيسية | القيود |
|--------|-----------------|--------|
| `backtest_results` | symbol, strategy, timeframe, entry_price, exit_price, profit_pct, is_win, indicators(JSONB), imported_to_ml, weight | — |
| `paper_trading_log` | user_id, symbol, strategy, side, entry_price, exit_price, pnl_pct, is_win, exit_reason, session_id | FK→users |
| `trading_phase_state` | current_phase, backtest_win_rate, backtest_total_trades, paper_win_rate, paper_total_trades, validation_passed, phase_history(JSONB) | PK=1 (سجل واحد) |

---

## الفهارس الفعلية (24 فهرس)

```sql
-- المستخدمين
idx_users_email ON users(email)
idx_users_user_type ON users(user_type)
idx_users_phone_number_unique ON users(phone_number) WHERE phone_number IS NOT NULL

-- الإعدادات
idx_user_settings_user_id ON user_settings(user_id)
idx_user_settings_user_demo ON user_settings(user_id, is_demo)

-- Binance
idx_user_binance_keys_user_active ON user_binance_keys(user_id, is_active)
idx_user_binance_balance_user ON user_binance_balance(user_id)
idx_user_binance_balance_user_asset ON user_binance_balance(user_id, asset)

-- المراكز النشطة
idx_active_positions_user ON active_positions(user_id)
idx_active_positions_symbol ON active_positions(symbol)
idx_active_positions_active ON active_positions(is_active)
idx_active_positions_user_active ON active_positions(user_id, is_active)
idx_active_positions_user_demo_active ON active_positions(user_id, is_demo, is_active)

-- الصفقات
idx_user_trades_user_date ON user_trades(user_id, entry_time DESC)
idx_user_trades_status ON user_trades(user_id, status)
idx_user_trades_symbol ON user_trades(symbol)
idx_user_trades_user_demo ON user_trades(user_id, is_demo)

-- الإشعارات
idx_notifications_user ON notifications(user_id)
idx_notifications_user_read ON notifications(user_id, is_read)

-- العملات الناجحة
idx_successful_coins_symbol ON successful_coins(symbol, is_active)
idx_successful_coins_score ON successful_coins(score DESC, is_active)

-- المحفظة
idx_portfolio_growth_user_date ON portfolio_growth_history(user_id, date)

-- ML
idx_backtest_results_symbol ON backtest_results(symbol)
idx_backtest_results_strategy ON backtest_results(strategy)
idx_backtest_results_imported ON backtest_results(imported_to_ml)
idx_paper_trading_user ON paper_trading_log(user_id)
idx_paper_trading_symbol ON paper_trading_log(symbol)
```

---

## ملفات الترحيل الفعلية (14 ملف)

| الملف | الوظيفة |
|-------|---------|
| `002_workers_setup.sql` | إعداد العمال |
| `schema_unification.sql` | توحيد المخطط |
| `improve_schema_20260403.sql` | تحسين المخطط |
| `enable_foreign_keys.sql` | تفعيل المفاتيح الخارجية |
| `enable_foreign_keys_and_indexes.sql` | تفعيل المفاتيح والفهارس |
| `fix_critical_missing_fields.sql` | إصلاح الحقول المفقودة الحرجة |
| `fix_db_schema_for_dual_portfolios.sql` | إصلاح المحافظ المزدوجة |
| `unify_portfolio_tables.sql` | توحيد جداول المحافظ |
| `safe_portfolio_unification.sql` | توحيد المحافظ الآمن |
| `add_first_trade_snapshot_to_portfolio.sql` | إضافة لقطة أول صفقة |
| `create_demo_accounts_table.sql` | إنشاء جدول الحسابات التجريبية |
| `create_signal_verification_log.sql` | إنشاء جدول التحقق من الإشارات |
| `add_is_demo_to_trade_learning_log.sql` | إضافة is_demo لسجل التعلم |

---

## نظام UPSERT الفعلي

الجداول التي تدعم `ON CONFLICT` في `DatabaseManager`:

| الجدول | أعمدة التعارض |
|--------|--------------|
| `system_status` | id |
| `user_settings` | user_id, is_demo |
| `portfolio` | user_id, is_demo |
| `verification_codes` | email |
| `user_sessions` | user_id |
| `user_devices` | user_id, device_id |
| `pending_verifications` | user_id, action |
| `user_binance_keys` | user_id |
| `successful_coins` | symbol, strategy, timeframe |
| `active_positions` | user_id, symbol, strategy, is_demo |
| `trading_signals` | symbol, strategy, timeframe |
| `portfolio_growth_history` | user_id, date, is_demo |
| `coin_states` | symbol |

---

## ملف التعلم الذاتي (Smart State)

| الملف | الوظيفة |
|-------|---------|
| `data/risk_learning_state.json` | يحفظ أداء النظام (Win Rate, Avg Win/Loss, Consecutive Losses) |
| `backend/core/portfolio_risk_manager.py` | يقرأ الملف عند البدء ويحدثه بعد كل صفقة |

**البيانات المحفوظة:**
```json
{
  "total_trades": 150,
  "winning_trades": 95,
  "avg_win_pct": 0.018,
  "avg_loss_pct": -0.012,
  "consecutive_losses": 0
}
```

---

## التكامل مع محرك النمو الذكي

1. **أوضاع النمو:** يقرأ `PortfolioRiskManager` الرصيد من جدول `portfolio` ويحدد الوضع (Launch/Growth/Standard/Pro).
2. **تتبع الوضع:** يتم حفظ `growth_mode` الحالي في عمود `portfolio.growth_mode` (تمت إضافته في Migration 004).
3. **حجم الصفقة:** يحسب الحجم بناءً على الوضع ونوع العملة (`MAJOR`, `MEME`, etc.) ويخزنه في `active_positions.quantity`.
4. **التعلم:** بعد إغلاق الصفقة، يحدث `TradingOrchestrator` ملف `risk_learning_state.json` بالنتيجة الجديدة.
5. **التكيف:** في الدورة التالية، يستخدم النظام الخبرة الجديدة لتعديل حجم الصفقة وحدود المخاطرة.
6. **التحقق:** تم التحقق من تكامل المسارات والبيانات عبر سكربت `verify_integration.py`.

---

## طبقة الوصول الفعلية

```
backend/infrastructure/db_access.py
    ├── get_db_manager() → DatabaseManager singleton
    ├── get_db_connection() → read connection (context manager)
    └── get_db_write_connection() → write connection (context manager)

database/database_manager.py (1566 سطر)
    ├── DbTradingMixin
    ├── DbUsersMixin
    ├── DbPortfolioMixin
    └── DbNotificationsMixin
```
