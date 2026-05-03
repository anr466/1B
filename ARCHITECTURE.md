# 🏗️ Trading AI Bot — Full Architecture

> Load this file when working on screens, providers, navigation, data flow, or backend API design.

---

## 1. App Philosophy & Roles

### User (مستخدم)
- Full self-management: register, login, manage profile, manage API keys, control trading on/off
- Set all risk parameters: stop loss %, take profit %, trade amount, position size, max positions, risk level, daily loss limit
- View portfolio, trades, analytics, notifications
- One portfolio only (real trading)

### Admin (مدير)
- **System control only** — does NOT manage individual user accounts
- Controls: trading engine start/stop/emergency-stop, ML learning system, background scheduler
- Views: system stats, user list (read-only), system logs, ML metrics
- Has TWO independent portfolios: Demo + Real, each with independent balance and trading toggle
- Can switch between demo/real modes — screens reflect the active portfolio's data
- **Cannot**: block users, reset passwords, force-close other users' positions, toggle other users' trading

### Key Principle
المستخدم مسؤول عن حسابه بالكامل. الأدمن مسؤول عن المحرك الخلفي والنظام فقط.

---

## 2. Backend Architecture (Flask + PostgreSQL)

```
┌─────────────────────────────────────────────────────────┐
│                    start_server.py                       │
│  Registers Blueprints → auth_bp, admin_unified_bp,      │
│  mobile_endpoints_bp, token_refresh_bp, smart_exit_bp,  │
│  ml_learning_bp, fcm_bp, background_bp, system_health_bp│
├─────────────────────────────────────────────────────────┤
│                  Auth Layer                              │
│  auth_middleware.py → require_auth, require_admin        │
│  ❌ require_auth: validates JWT, sets g.user_id          │
│  ❌ require_auth_atomic: validates JWT + checks URL      │
│     user_id matches g.current_user_id (for writes)       │
│  ❌ require_admin: extends require_auth + checks admin   │
├─────────────────────────────────────────────────────────┤
│              Database Layer                              │
│  database_manager.py → PostgresConnectionWrapper         │
│  PostgresCursorWrapper → safe execute/fetchone/fetchall  │
│  ⚠️ INSERT OR REPLACE → translated to ON CONFLICT       │
│  ⚠️ POSTGRES_UPSERT_CONFLICTS dict maps table→columns   │
├─────────────────────────────────────────────────────────┤
│               Core Tables (postgres_schema.sql)           │
│  users, active_positions, portfolio, user_settings,      │
│  successful_coins, trading_signals, notifications,       │
│  user_binance_keys, system_status, security_audit_log,   │
│  system_errors, activity_logs, strategy_learning,        │
│  admin_notification_settings, user_notification_settings │
│  ➕ 003_missing_tables.sql: trade_learning_log,          │
│     signal_learning, learning_validation_log,            │
│     system_alerts, ml_patterns, user_onboarding,         │
│     password_reset_requests                              │
├─────────────────────────────────────────────────────────┤
│             DB Mixins (scattered through db_*.py)         │
│  DbPortfolioMixin: get_portfolio, get_open_trades,       │
│    _ensure_demo_account (ADMIN-ONLY guard at line 24)    │
│  DbTradingMixin: add_position_on_conn, close_position    │
│  DbUsersMixin: create_user, get_user_by_id               │
├─────────────────────────────────────────────────────────┤
│            Key API Patterns                              │
│  ✅ Auth: /auth/login (checks is_active → 403 if disabled)│
│  ✅ Auth: /auth/logout (requires auth, revokes token)    │
│  ✅ Auth: /auth/validate-session (catches ExpiredSig)    │
│  ✅ Admin: /admin/system/stats (system-wide, not per-user)│
│  ✅ Admin: /admin/positions/<id>/close (admin manual close)│
│  ⚠️ user_lookup_service.py: single source for user lookup│
│     (returns is_active + all fields)                     │
│  ⚠️ Registration: email_verified SEPARATE from phone now │
│  ⚠️ Password: enforced 8+ chars in all registration paths│
│  ⚠️ SQL: parameterized queries preferred (NOT f-strings) │
│  ⚠️ JSON keys: standardized to "message" (not "error")   │
│  ⚠️ DB URL: NEVER returned in API responses              │
│  ⚠️ SELECT *: replaced with explicit columns              │
│  ⚠️ Unbounded queries: now have LIMIT                     │
│  ⚠️ write connections: use get_write_connection()        │
├─────────────────────────────────────────────────────────┤
│           Exceptions NOT silenced anymore                 │
│  ✅ secure_actions_endpoints.py: pending verif fail logs  │
│  ✅ mobile_endpoints.py: silent except→pass replaced      │
│  ✅ admin_unified_api.py: pgrep failure logs error        │
│  ✅ ON CONFLICT targets: now explicit (user_id)           │
│  ✅ UPSERT_CONFLICTS: table names corrected               │
└─────────────────────────────────────────────────────────┘
```

## 3. Core Trading Engine Architecture

### 3.1 Main Loop (`_run_user_cycle` in group_b_system.py)

```
_analysis_loop (infinite loop every 60s)
  └── _run_user_cycle()
        ├── 1. Portfolio & risk check
        │     ├── Load balance from portfolio table
        │     ├── Enforce max drawdown (5% default)
        │     └── Update peak balance tracking
        ├── 2. Position Monitoring (ALL positions)
        │     ├── Fetch current prices from Binance
        │     └── MonitoringEngine.monitor_positions()
        │           ├── CLOSE → self._close_position() ← EXECUTES BINANCE SELL
        │           │     - Real account: Binance order → real price/commission
        │           │     - Demo account: simulate_fill() → DB only
        │           ├── PARTIAL_CLOSE → self._close_position(close_pct)
        │           └── UPDATE → _update_position_in_db()
        ├── 3. New Entry Scanning
        │     └── TradingOrchestrator.run_cycle()
        │           └── _scan_and_enter()
        │                 ├── CoinStateAnalyzer → regime/trend
        │                 ├── 5 Strategy Modules (ensemble scoring)
        │                 ├── TradingBrain (ML confirmation)
        │                 ├── MTFConfirmation (multi-timeframe)
        │                 ├── DualModeRouter → Spot LONG / Margin SHORT
        │                 └── _open_position() ← EXECUTES BINANCE BUY
        └── 4. Cleanup (orphaned signals >24h)
```

### 3.2 Entry Flow (Detailed)

```
TradingOrchestrator._scan_and_enter()
  ├── For each symbol:
  │     ├── StateAnalyzer.analyze() → CoinState (trend, regime, volatility)
  │     ├── For each StrategyModule (Trend, Range, Volatility, Scalping):
  │     │     ├── module.evaluate(df, context) → signal
  │     │     ├── module.get_entry_price() / get_stop_loss() / get_take_profit()
  │     │     └── CognitiveDecisionMatrix.evaluate() → score + decision
  │     ├── Ensemble bonus: +3 per agreeing module
  │     ├── TradingBrain.think() → REJECT or confirm + score
  │     ├── MTFConfirmationEngine.confirm_entry() → confirmed + score
  │     ├── PortfolioRiskManager.get_position_size() → size in USDT
  │     ├── DualModeRouter.route_signal(signal, regime)
  │     │     ├── LONG + spot_enabled → Spot executor
  │     │     ├── SHORT + margin_enabled → Margin executor
  │     │     └── otherwise → REJECTED
  │     └── _open_position(symbol, signal)
  │           ├── Demo: _simulate_demo_fill() → DB insert
  │           └── Real: binance_manager.execute_buy_order() → Binance API → DB insert
```

### 3.3 Exit Flow (Detailed)

```
PositionManager._close_position(pos, exit_price, reason, close_pct)
  ├── Demo Account:
  │     ├── _simulate_demo_fill() → slip_page + commission
  │     ├── Slippage protection (floor/ceiling)
  │     └── Atomic DB: close_position_on_conn() + update balance
  ├── Real Account:
  │     ├── binance_manager.execute_sell_order() → BINANCE MARKET ORDER
  │     ├── Uses real fill price + real commission from Binance response
  │     ├── If Binance fails → position stays OPEN in DB (no false close)
  │     └── Atomic DB: close_position_on_conn() + update balance
  └── Post-close: ML recording + TradingBrain learning + risk state update
```

### 3.4 Dual-Mode Execution (Demo vs Real)

```
                              ┌─ is_demo_trading? ─┐
                              │                     │
                         DEMO ▼                 REAL ▼
              ┌──────────────────┐    ┌──────────────────┐
              │ Signals: Real     │    │ Signals: Real     │
              │ from Binance      │    │ from Binance      │
              ├──────────────────┤    ├──────────────────┤
              │ Entry: Simulated  │    │ Entry: Binance    │
              │ fill + DB only    │    │ MARKET BUY order  │
              ├──────────────────┤    ├──────────────────┤
              │ Exit: Simulated   │    │ Exit: Binance     │
              │ fill + DB only    │    │ MARKET SELL order │
              ├──────────────────┤    ├──────────────────┤
              │ Balance: Virtual  │    │ Balance: Real     │
              │ $10,000 initial   │    │ from Binance API  │
              └──────────────────┘    └──────────────────┘
```

### 3.5 Strategy Architecture

```
BaseStrategy (V8) — unified strategy interface (group_b_system)
  ├── prepare_data(df) → indicators
  ├── check_entry(df, context) → entry signal
  └── check_exit(df, position) → exit signal

TradingOrchestrator — 5-system ensemble (orchestrator)
  ├── TrendModule → trend-following signals
  ├── RangeModule → mean-reversion signals
  ├── VolatilityModule → breakout signals
  ├── ScalpingModule → short-term signals
  └── CognitiveDecisionMatrix → score + ENTER/ENTER_REDUCED/HOLD/EXIT

⚠️ These two strategy systems coexist:
  - BaseStrategy: used by PositionManager._manage_position() for exits
  - StrategyModules: used by TradingOrchestrator._scan_and_enter() for entries
  - The orchestrator path also uses MonitoringEngine for exits (via main loop)
```

### 3.6 Key Component Hierarchy

```
GroupBSystem (God Object, 1059 lines)
  ├── PositionManagerMixin → _open_position, _close_position, _manage_position
  ├── ScannerMixin → _scan_for_entries, _get_tradeable_symbols  
  ├── RiskManagerMixin → _check_risk_gates, _calculate_position_size
  └── Owns:
        ├── TradingOrchestrator
        │     ├── CoinStateAnalyzer → trend/regime analysis
        │     ├── StrategyRouter → selects active strategy
        │     ├── EntryExecutor (EMA 8/21/55 + RSI + ADX + ATR)
        │     ├── MonitoringEngine → SL/TP/trail/time/partial checks
        │     ├── ExitEngine → PnL calculation
        │     ├── ExitManager → position evaluation
        │     ├── PortfolioRiskManager → Kelly sizing, tier classification
        │     ├── MTFConfirmationEngine → multi-timeframe confirmation
        │     ├── CognitiveDecisionMatrix → cognitive scoring
        │     ├── DualModeRouter → Spot LONG vs Margin SHORT
        │     └── 4 StrategyModules (Trend, Range, Volatility, Scalping)
        ├── DualModeRouter → regime-based routing
        ├── DynamicCoinSelector → coin selection
        ├── TradingBrain → ML-based phase-aware decisions
        ├── AdaptiveOptimizer → position size multiplier
        ├── DataProvider → Binance market data
        └── BinanceManager → order execution + circuit breaker
```

### 3.7 DemoTrainingEngine (Unused)

- `demo_training_engine.py`: standalone simulation class
- `initial_balance=10000.0`, commission=0.1%, slippage=0.05%
- **Currently NOT used** in the main trading loop
- Actual demo trading is handled by `_simulate_demo_fill()` in PositionManager
- Considered a reference/backup module

### 3.8 Exit engines comparison

| Feature | MonitoringEngine (main loop) | ExitManager (unused) | PositionManager._manage_position |
|---------|------------------------------|----------------------|----------------------------------|
| SL check | ✅ | ✅ | ✅ (historical + current) |
| Trail SL | ✅ | ✅ | via BaseStrategy |
| Breakeven | ✅ | ✅ | via BaseStrategy |
| Time exits | ✅ (8h stagnant, 6h early-cut) | ✅ | via BaseStrategy |
| Partial close | ✅ (TP1 1.5R 40%, TP2 2.5R 35%) | ✅ | via BaseStrategy |
| Binance execution | ✅ (via _close_position) | ❌ (DB only) | ✅ (via _close_position) |
| Used in loop | ✅ | ❌ | ❌ (defined, not called) |

## 4. Flutter App Architecture (GoRouter + Riverpod)

```
app.dart
├── splash_screen.dart → checks onboardingDone → checks auth
├── onboarding_screen.dart → 3 pages, then goes to login
├── login_screen.dart → biometric auto-prompt if enabled
├── register_screen.dart → OTP verification flow
│
├── MainShell (ShellRoute → Scaffold + BottomNav 5 tabs)
│   ├── Tab 0: /dashboard → DashboardScreen
│   ├── Tab 1: /portfolio → PortfolioScreen
│   ├── Tab 2: /trades → TradesScreen
│   ├── Tab 3: /analytics → AnalyticsScreen
│   ├── Tab 4: /profile → ProfileScreen (admin sees shield icon)
│   └── Tab 4 (admin): push /admin-dashboard (NOT go—stays in stack)
│
├── Non-shell routes (pushed on top):
│   ├── /trade-detail → TradeDetailScreen
│   ├── /trading-settings → TradingSettingsScreen
│   ├── /binance-keys → BinanceKeysScreen
│   ├── /notifications → NotificationsScreen
│   ├── /onboarding → OnboardingScreen (auth user → pop; unauth → login)
│   │
│   └── Admin routes:
│       ├── /admin-dashboard → AdminDashboardScreen (VIEW-ONLY: system-wide stats)
│       ├── /admin/trading-control → TradingControlScreen (SYSTEM-CONTROL: engine start/stop/emergency)
│       ├── /admin/users → UserManagementScreen (VIEW-ONLY: user list, no edit/delete/block)
│       ├── /admin/user-detail → AdminUserDetailScreen (VIEW-ONLY: user trade history)
│       ├── /admin/ml-dashboard → AdminMLDashboardScreen (SYSTEM-CONTROL: ML learning management)
│       ├── /admin/background-control → AdminBackgroundControlScreen (SYSTEM-CONTROL: background scheduler)
│       ├── /admin/logs-dashboard → AdminLogsDashboardScreen (VIEW-ONLY: system logs overview)
│       ├── /admin/system-logs → SystemLogsScreen (VIEW-ONLY: audit/error logs)
│       └── /admin/error-details → ErrorDetailsScreen (VIEW-ONLY: error drill-down)
```

## 5. Unified Provider Architecture (Single Source of Truth)

```
accountTradingProvider (StateNotifier, polls every 15s)
│  Fetches: portfolio + stats + active positions in ONE call
│
├── portfolioProvider (derived — ZERO network calls)
│     → PortfolioScreen, DashboardScreen, AdminDashboardScreen
│
├── statsProvider (derived — ZERO network calls)
│     → DashboardScreen, AnalyticsScreen
│     ⚠️ This is PER-USER stats — NOT system-wide
│
├── activePositionsProvider (derived — ZERO network calls)
│     → DashboardScreen
│
├── systemStatsProvider (FutureProvider — admin system-wide stats)
│     → AdminDashboardScreen ONLY
│
├── recentTradesProvider (FutureProvider — independent fetch)
│     → DashboardScreen
│
├── tradesListProvider (FutureProvider — paginated search)
│     → TradesScreen
│
├── analyticsTradesProvider (FutureProvider)
│     → AnalyticsScreen (equity curve data)
│
├── settingsDataProvider (FutureProvider.autoDispose → settings_provider.dart)
│     → TradingSettingsScreen, ProfileScreen
│     ⚠️ Invalidated after trading toggle (via TradingToggleService)
│
├── tradingToggleServiceProvider (Service)
│     → toggleSelf() → updates settings, invalidates accountTradingProvider + settingsDataProvider
│     → toggleUser() → admin toggles another user's trading
│
└── adminUsersProvider, systemStatusProvider, dailyStatusProvider...
```

## 6. Trading Toggle Architecture (CRITICAL — 3 Distinct Concepts)

| # | Concept | Location | Purpose |
|---|---------|----------|---------|
| 1 | **TradingToggleButton** | `design/widgets/trading_toggle_button.dart` | Unified widget for self + admin toggle |
| 2 | **TradingToggleService** | `core/services/trading_toggle_service.dart` | toggleSelf() + toggleUser() logic |
| 3 | **TradingStatusStrip** | `design/widgets/trading_status_strip.dart` | Visual status strip + Switch (used in ProfileScreen) |
| 4 | **TradingControlScreen toggle** | `features/admin/screens/trading_control_screen.dart` | SYSTEM ENGINE start/stop (NOT user tradingEnabled) |
| 5 | **LoadingState.enabled** | `core/providers/unified_async_state.dart:36` | ⚠️ UI readiness flag (NOT trading toggle!) |

⚠️ **BUG FIXED**: ProfileScreen now reads `tradingEnabled` from `settingsDataProvider`, not from `LoadingState.enabled`. The old code passed `tradingState.enabled` (which returns `true` whenever the provider loaded data) as the toggle value — the switch showed "on" regardless of actual trading state.

### Admin Demo/Real Portfolio Architecture
- `adminPortfolioModeProvider` (StateProvider<String>) — 'demo' or 'real', initialized to 'demo'
- `_resolveMode()` in portfolio_provider.dart — reads mode for admin, passes `is_demo` to ALL API calls
- Demo/Real chips in PortfolioScreen and TradingSettingsScreen switch mode directly with confirmation dialog
- After mode switch: invalidate `accountTradingProvider`, call `updateTradingMode` API
- Trading toggle is per-portfolio: `tradingToggleService.toggleSelf()` passes the active mode
- Each portfolio has INDEPENDENT balance, trades, and trading toggle state

## 7. Key Navigation Rules
## 8. Data Conflicts Between Screens (Known)
## 9. Provider Invalidation Rules
## 10. Working Directory Map
## 11. Common Anti-Patterns to Avoid

- ❌ Creating new providers that duplicate API calls already made by `accountTradingProvider`
- ❌ `cursor.execute(...).fetchone()` without separating (wrappers handle it, but raw code doesn't)
- ❌ Using `context.go()` for admin routes from within the ShellRoute
- ❌ `SELECT *` in queries — always use explicit columns
- ❌ `except: pass` — always log errors
- ❌ Hardcoding `user_id` or using `or 1` fallback in auth context
- ❌ Using `tradingState.enabled` (LoadingState readiness) as `tradingEnabled` value
- ❌ Not invalidating `tradesListProvider` after closing a trade from admin screen
- ❌ Returning DB connection strings in API responses
- ❌ Bare `ON CONFLICT DO NOTHING` without explicit conflict target in PostgreSQL
- ❌ Admin controlling individual user settings (block, reset password, toggle their trading)
- ❌ Admin-gating features that users should self-manage (risk sliders, API keys)
- ❌ Mixing demo and real portfolio data — always pass is_demo filter
