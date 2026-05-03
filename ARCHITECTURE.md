# 🏗️ Trading AI Bot — Architecture

> Load this file when working on screens, providers, navigation, data flow, or backend API design.

---

## 1. App Philosophy & Roles

### User (مستخدم)
- **Full self-management**: register, login, manage profile, manage API keys, control trading on/off
- **Set all risk parameters**: stop loss %, take profit %, trade amount, position size, max positions, risk level, daily loss limit
- **View**: portfolio, trades, analytics, notifications
- **One portfolio only** (real trading)

### Admin (مدير)
- **System control only** — does NOT manage individual user accounts
- **Controls**: trading engine start/stop/emergency-stop, ML learning, background scheduler, system logs
- **Has TWO independent portfolios**: Demo + Real, each with independent balance and trading toggle
- **Can switch** between demo/real modes from PortfolioScreen/TradingSettingsScreen
- **Cannot**: block users, reset passwords, force-close other users' positions, toggle other users' trading

### Key Principle
المستخدم مسؤول عن حسابه بالكامل. الأدمن مسؤول عن المحرك الخلفي والنظام فقط.

---

## 2. User Journey (Complete Flow)

```
1. Splash → Brand animation (2.6s)
     ├── First run → Onboarding (3 pages) → Login
     ├── Token valid + no biometric → Dashboard directly
     ├── Token valid + biometric enabled → Login screen (auto-prompt fingerprint)
     └── No valid token → Login

2. Login
     ├── "Remember Me" checkbox → saves encrypted credentials
     ├── Biometric auto-prompt → fingerprint/face login
     ├── Traditional email+password login
     ├── Forgot password → OTP → Reset
     └── Register → OTP verification → Login

3. Dashboard (Tab 0) — 5 bottom tabs
     ├── Hero balance card
     ├── Daily PnL bar
     ├── Open positions strip (if any)
     ├── Performance section (win rate, profit factor)
     ├── Stats grid (total trades, PnL, drawdown)
     ├── Chart section (equity curve)
     └── Recent trades list

4. Portfolio (Tab 1)
     ├── Balance overview (total, available, invested)
     ├── Demo/Real switcher (admin only)
     ├── Portfolio breakdown (asset allocation)
     ├── Open positions distribution
     └── Growth chart

5. Trades (Tab 2)
     ├── Trades list (paginated)
     ├── Summary chart (win/loss pie)
     └── Tap trade → TradeDetailScreen

6. Analytics (Tab 3)
     ├── Equity curve
     ├── Monthly PnL breakdown
     └── Performance metrics

7. Profile (Tab 4) — Self-service account management
     ├── User info card (name, email, admin badge)
     ├── Edit profile dialog (name, phone)
     ├── TradingToggle (biometric-secured ON/OFF)
     ├── Settings group:
     │     ├── Trading Settings → stop loss, take profit, position size, risk
     │     ├── Binance Keys → save, verify, encrypt API keys
     │     ├── Security → change password, change email, biometric toggle
     │     ├── Notifications → enable/disable, customize report time
     │     ├── Skin Picker → theme selection
     │     └── Onboarding → re-view tutorial
     ├── Delete Account (password + DELETE text confirmation)
     └── Logout

8. Admin Dashboard (admin-only, pushed from Tab 4)
     ├── System status card (running/stopped, uptime)
     ├── Stats grid (users, trades, profit, win rate)
     ├── Quick actions:
     │     ├── Trading Control → engine start/stop/emergency
     │     ├── System Logs → audit/error/activity logs
     │     ├── Logs Dashboard → overview + charts
     │     ├── Background Control → scheduler management
     │     └── ML Dashboard → model training/status
     └── No user management (users self-manage)
```

---

## 3. Flutter Route Tree (GoRouter)

```
/ (redirect → /splash)
├── /splash → SplashScreen
├── /onboarding → OnboardingScreen
├── /login → LoginScreen
├── /register → RegisterScreen
├── /otp-verification → OtpVerificationScreen
├── /forgot-password → ForgotPasswordScreen
├── /reset-password → ResetPasswordScreen
│
├── ShellRoute → MainShell (BottomNavigationBar 5 tabs)
│     ├── /dashboard → DashboardScreen
│     ├── /portfolio → PortfolioScreen
│     ├── /trades → TradesScreen
│     ├── /analytics → AnalyticsScreen
│     └── /profile → ProfileScreen (tab 4 pushes admin if isAdmin)
│
├── Push routes (outside ShellRoute):
│     ├── /trades/detail → TradeDetailScreen
│     ├── /settings/trading → TradingSettingsScreen
│     ├── /settings/binance-keys → BinanceKeysScreen
│     ├── /settings/security → SecuritySettingsScreen
│     ├── /settings/skin → SkinPickerScreen
│     ├── /settings/notifications → NotificationSettingsScreen
│     ├── /notifications → NotificationsScreen
│     │
│     └── Admin routes (push from tab 4 when isAdmin):
│           ├── /admin/dashboard → AdminDashboardScreen
│           ├── /admin/trading-control → TradingControlScreen
│           ├── /admin/logs → SystemLogsScreen
│           ├── /admin/logs/dashboard → AdminLogsDashboardScreen
│           ├── /admin/logs/error → ErrorDetailsScreen
│           ├── /admin/ml → AdminMLDashboardScreen
│           └── /admin/background → AdminBackgroundControlScreen
```

### Navigation Rules
- **Tab switching inside shell**: `context.go()` — replaces current tab
- **Push to detail/settings**: `context.push()` — stays on top of shell
- **Admin dashboard from tab 4**: `context.push()` — returns to tab 4 on back
- **After logout**: `context.go(RouteNames.login)` — clears stack
- **Auth guard**: GoRouter redirect checks auth state, pushes to /login if unauthenticated

---

## 4. Backend Architecture (Flask under FastAPI)

```
start_server.py (FastAPI app)
  └── app.mount("/api", WSGIMiddleware(flask_app))

Flask Blueprints:
├── auth_bp (/auth) → login, register, OTP, forgot/reset password, validate
├── mobile_bp (/user) → portfolio, stats, trades, settings, binance-keys, active-positions
├── admin_unified_bp (/admin) → dashboard, system/stats, trading/start/stop, logs, errors, ML, background
├── token_refresh_bp (/auth) → refresh, logout
├── trading_control_bp (/admin/trading) → engine start/stop/status
├── system_bp (/system) → status, health
├── secure_actions_bp (/user/secure) → verified account actions
├── smart_exit_bp → smart exit settings
├── ml_learning_bp → ML training endpoints
├── fcm_bp (/notifications) → push notification tokens
├── login_otp_bp (/auth/login) → OTP-based login
└── background_bp (/admin/background) → background scheduler
```

### Auth Layer
| Guard | Middleware | Purpose |
|-------|-----------|---------|
| `require_auth` | `auth_middleware.py` | Validates JWT, sets `g.user_id` |
| `require_admin` | `admin_auth.py` | Extends require_auth + checks `user_type = 'admin'` |

### API URL Pattern
```
Flutter baseUrl: "http://72.60.190.188:3002/api"
Example: /api/auth/login → Flask auth_bp
Example: /api/user/portfolio/3 → Flask mobile_bp
Example: /api/admin/dashboard → Flask admin_unified_bp
```

---

## 5. Core Trading Engine Architecture

### 5.1 Docker Services

| Service | Container | Role |
|---------|-----------|------|
| **API** | `trading-ai-api` | Flask+FastAPI, user/admin endpoints, spawns GroupBSystem |
| **Executor** | `trading-ai-executor` | Processes signals_queue entries, monitors (skips when GroupBSystem RUNNING) |
| **Scanner** | `trading-ai-scanner` | Fetches 50 symbols from Binance, generates signal candidates |
| **Postgres** | `trading-ai-postgres` | All data storage (48 tables) |
| **Nginx** | `trading-ai-nginx` | Reverse proxy port 80 → API:3002 |

### 5.2 Main Trading Loop

```
GroupBSystem._run_user_cycle() (every 60s via API-spawned process)
├── 1. Portfolio & Risk
│     ├── Load balance from portfolio table
│     ├── Enforce max drawdown (5%)
│     └── Update peak balance
├── 2. Position Monitoring (ALL active positions)
│     └── MonitoringEngine.monitor_positions()
│           ├── CLOSE → _close_position() → Binance sell (real) / simulate (demo)
│           ├── PARTIAL_CLOSE → _close_position(close_pct)
│           │     - TP1: 1.5R profit → close 40%
│           │     - TP2: 2.5R profit → close 35%
│           └── UPDATE → trailing SL, breakeven, highest_price
├── 3. Entry Scanning
│     └── TradingOrchestrator._scan_and_enter()
│           ├── For each symbol (50 max):
│           │     ├── CoinStateAnalyzer → regime/trend/volatility
│           │     ├── StrategyModules (Trend/Range/Volatility/Scalping) × DecisionMatrix
│           │     ├── TradingBrain (ML confirm/reject)
│           │     ├── MTFConfirmation (multi-timeframe)
│           │     ├── DualModeRouter → Spot LONG / Margin SHORT
│           │     └── PortfolioRiskManager → Kelly position sizing
│           └── _open_position() → Binance buy (real) / simulate (demo)
└── 4. Cleanup (orphaned signals >24h)
```

### 5.3 Exit Flow (`_close_position`)

```
position_manager.py:688 → _close_position(pos, exit_price, reason, close_pct)
├── Demo Account:
│     ├── _simulate_demo_fill() → slippage + commission
│     ├── Slippage protection (floor/ceiling based on trail/SL)
│     └── Atomic DB: close_position_on_conn() + update balance
├── Real Account:
│     ├── binance_manager.execute_sell_order() → BINANCE MARKET SELL
│     ├── _execute_real_order_with_retry() → 3 attempts, 1.5s apart
│     ├── Uses real fill price + real commission from Binance
│     ├── If Binance fails → position stays OPEN (returns None)
│     └── Atomic DB: close_position_on_conn() + update balance
└── Post-close: ML recording + TradingBrain learning + risk state update
```

### 5.4 Dual-Mode (Demo vs Real)

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

### 5.5 Executor Guard (Race Condition Prevention)

```
ExecutorWorker.run() (every 5s)
├── Check: system_status.trading_state = 'RUNNING'?
│     ├── YES → GroupBSystem active → skip monitor_open_positions()
│     └── NO → monitor_open_positions() via SmartExitEngine
└── Always: process_pending_signals() from signals_queue
```

### 5.6 Database Tables

| Table | Purpose |
|-------|---------|
| `users` | User accounts (id, email, username, password_hash, user_type) |
| `portfolio` | User portfolio (user_id, is_demo, total_balance, available_balance, initial_balance) |
| `user_settings` | Trading settings (trading_enabled, max_positions, risk_level, stop_loss_pct, etc.) |
| `active_positions` | Open/closed positions (symbol, entry_price, quantity, stop_loss, take_profit, profit_loss) |
| `user_binance_keys` | Encrypted Binance API keys (api_key, api_secret encrypted, is_active) |
| `trading_signals` | Generated trading signals |
| `signals_queue` | Pending signals for executor (status: PENDING/FILLED/REJECTED) |
| `system_status` | Engine state (trading_state: RUNNING/STOPPED/ERROR) |
| `system_errors` | Error log (error_type, error_message, severity, resolved) |
| `security_audit_log` | Security events (action, user_id, ip_address, timestamp) |
| `user_notification_settings` | Per-user notification preferences |
| `notifications` | Notification queue for push delivery |

---

## 6. Flutter Provider Architecture

```
accountTradingProvider (StateNotifier, polls every 15s)
│  Single source: portfolio + stats + active positions
│
├── portfolioProvider (derived — zero network calls)
│     → PortfolioScreen, DashboardScreen, AdminDashboardScreen
├── statsProvider (derived — zero network calls)
│     → DashboardScreen, AnalyticsScreen
├── activePositionsProvider (derived — zero network calls)
│     → DashboardScreen
│
├── recentTradesProvider (FutureProvider — independent)
│     → DashboardScreen
├── tradesListProvider (FutureProvider — paginated)
│     → TradesScreen
├── analyticsTradesProvider (FutureProvider)
│     → AnalyticsScreen
│
├── settingsDataProvider (FutureProvider.autoDispose)
│     → TradingSettingsScreen, ProfileScreen
│     ⚠️ Invalidated after trading toggle
│
├── authProvider (StateNotifier)
│     → All screens (auth state, user data, isAdmin)
├── adminPortfolioModeProvider (StateProvider<String>)
│     → demo/real mode for admin portfolio switching
├── systemStatsProvider (FutureProvider)
│     → AdminDashboardScreen
├── systemStatusProvider (FutureProvider, polls every 10s)
│     → AdminDashboardScreen, TradingControlScreen
│
├── notificationsProvider (StateNotifier)
│     → NotificationsScreen
│
└── tradingToggleServiceProvider (Service)
      → toggleSelf() → updates settings, invalidates providers
```

### Provider Invalidation Rules
| Action | Invalidate |
|--------|-----------|
| Trading toggle ON/OFF | `accountTradingProvider`, `settingsDataProvider` |
| Admin mode switch (demo↔real) | `portfolioProvider`, `statsProvider`, `activePositionsProvider`, `accountTradingProvider` |
| Dashboard pull-to-refresh | `recentTradesProvider`, `activePositionsProvider`, `portfolioProvider`, `statsProvider` |
| Portfolio pull-to-refresh | `portfolioProvider` only |
| Admin close trade | `recentTradesProvider`, `activePositionsProvider`, `tradesListProvider` |
| Login/Logout | `authProvider`, all user-specific providers |

---

## 7. Shared Design Components

| Widget | File | Replaces |
|--------|------|----------|
| `AppCard` | `design/widgets/app_card.dart` | `Container(borderRadius)` |
| `AppButton` | `design/widgets/app_button.dart` | `TextButton`, `ElevatedButton` |
| `StatusBadge` | `design/widgets/status_badge.dart` | Raw `Container` badges |
| `DemoRealBanner` | `design/widgets/demo_real_banner.dart` | 9 duplicate `_buildDemoRealBanner` methods |
| `TradingStatusStrip` | `design/widgets/trading_status_strip.dart` | Trading toggle on profile |
| `TradingToggleButton` | `design/widgets/trading_toggle_button.dart` | User trading toggle |
| `AppScreenHeader` | `design/widgets/app_screen_header.dart` | Raw AppBar/header |
| `AppSettingTile` | `design/widgets/app_setting_tile.dart` | Raw ListTile |
| `LoadingShimmer` | `design/widgets/loading_shimmer.dart` | Raw CircularProgressIndicator |
| `ErrorState` | `design/widgets/error_state.dart` | Raw error text |
| `EmptyState` | `design/widgets/empty_state.dart` | Raw empty text |
| `MoneyText` | `design/widgets/money_text.dart` | Raw `\${amount}` formatting |
| `PnLIndicator` | `design/widgets/pnl_indicator.dart` | Profit/loss colored display |

---

## 8. Working Directory Map

```
/Users/anr/Desktop/trading_ai_bot-1/
├── ARCHITECTURE.md              ← This file
├── DESIGN.md                    ← Design system spec (colors, typography, spacing, components)
├── AGENTS.md                    ← Behavioral rules
├── start_server.py              ← Docker entrypoint (FastAPI + Flask)
├── docker-compose.yml           ← Docker service definitions
├── bin/
│   ├── executor_worker.py       ← Signal processing + position reconciliation
│   └── scanner_worker.py        ← Market scanning + signal generation
├── backend/
│   ├── api/                     ← Flask Blueprints
│   │   ├── auth_endpoints.py    ← Login, logout, register, validate
│   │   ├── auth_middleware.py    ← require_auth, require_admin
│   │   ├── auth_registration_routes.py  ← Registration flow
│   │   ├── mobile_endpoints.py  ← Portfolio, trades, stats, profile
│   │   ├── mobile_settings_routes.py    ← Settings, binance keys
│   │   ├── admin_unified_api.py ← ALL admin endpoints
│   │   ├── background_control.py ← Engine start/stop
│   │   └── ...
│   ├── core/
│   │   ├── group_b_system.py    ← Main trading loop (God Object)
│   │   ├── trading_orchestrator.py ← 5-system ensemble + entry
│   │   ├── position_manager.py  ← _open_position, _close_position
│   │   ├── dual_mode_router.py  ← Spot LONG vs Margin SHORT
│   │   ├── monitoring_engine.py ← SL/TP/trail/time/partial checks
│   │   ├── exit_engine.py       ← PnL calculation
│   │   ├── exit_manager.py      ← Position evaluation (unused in loop)
│   │   ├── coin_state_analyzer.py ← Trend/regime analysis
│   │   ├── portfolio_risk_manager.py ← Kelly sizing
│   │   ├── mtf_confirmation.py  ← Multi-timeframe confirmation
│   │   ├── cognitive_decision_matrix.py ← Cognitive scoring
│   │   ├── demo_training_engine.py ← Standalone simulator (unused)
│   │   └── modules/             ← Trend, Range, Volatility, Scalping
│   ├── ml/                      ← ML engine
│   ├── utils/                   ← BinanceManager, DataProvider, trading_context
│   └── infrastructure/          ← DB access
├── database/
│   ├── database_manager.py      ← PostgresConnectionWrapper, pool, migrations
│   ├── db_portfolio_mixin.py    ← Portfolio CRUD, Binance keys
│   ├── db_users_mixin.py        ← User CRUD, settings
│   ├── db_trading_mixin.py      ← Position CRUD
│   └── migrations/              ← SQL files (NEVER modify existing)
├── flutter_trading_app/
│   ├── lib/
│   │   ├── main.dart
│   │   ├── app.dart
│   │   ├── core/
│   │   │   ├── constants/       ← api_endpoints, app_constants, ux_messages
│   │   │   ├── models/          ← TradeModel, PortfolioModel, UserModel
│   │   │   ├── providers/       ← Riverpod providers (single source of truth)
│   │   │   ├── repositories/    ← API call wrappers
│   │   │   └── services/        ← Auth, biometric, storage, trading_toggle
│   │   ├── design/
│   │   │   ├── widgets/         ← Shared components (25 widgets)
│   │   │   ├── tokens/          ← Colors, typography, spacing
│   │   │   ├── skins/           ← Theme definitions
│   │   │   └── icons/           ← Brand icons
│   │   ├── features/
│   │   │   ├── auth/screens/    ← Splash, login, register, OTP, forgot, reset
│   │   │   ├── dashboard/screens/
│   │   │   ├── portfolio/screens/
│   │   │   ├── trades/screens/
│   │   │   ├── analytics/screens/
│   │   │   ├── profile/screens/
│   │   │   ├── settings/screens/ ← Trading, binance keys, security, skin
│   │   │   ├── notifications/screens/
│   │   │   ├── onboarding/screens/
│   │   │   └── admin/screens/    ← Dashboard, trading control, logs, ML, background
│   │   └── navigation/           ← GoRouter, MainShell, route_names
│   └── build/app/outputs/flutter-apk/app-debug.apk  ← Built APK
└── config/
    └── unified_settings.py       ← NEVER modify
```

---

## 9. Critical Guardrails

### Security
- ❌ NEVER return DB URL in API responses
- ❌ NEVER source Binance keys from env vars (must come from `user_binance_keys` table)
- ❌ NEVER skip auth guards on admin routes
- ✅ Encrypt all API secrets before storing
- ✅ Validate JWT on every authenticated request
- ✅ Check `is_active` flag before allowing login

### Trading Engine
- ❌ NEVER execute Binance orders for demo accounts
- ❌ NEVER close a position in DB without confirming Binance execution (real accounts)
- ❌ NEVER let both executor AND GroupBSystem monitor the same positions
- ✅ Use `_close_position()` not `_close_position_in_db()` for exits
- ✅ Update portfolio balance atomically with position close (same transaction)
- ✅ Check `trading_enabled` before opening new positions

### Flutter
- ❌ NEVER use `Scaffold` inside ShellRoute children
- ❌ NEVER use raw `Color(0xFF...)` outside token files (except splash/brand)
- ❌ NEVER use raw `TextStyle()` — use `TypographyTokens`
- ❌ NEVER use `TextButton`/`ElevatedButton` — use `AppButton`
- ❌ NEVER use `Container(borderRadius)` — use `AppCard`
- ❌ NEVER create duplicate data providers
- ✅ Push admin routes, don't go() — stays in tab stack
- ✅ Invalidate affected providers after state changes

### Database
- ❌ NEVER use `SELECT *` — explicit columns
- ❌ NEVER modify existing migration files — create new ones
- ❌ NEVER use f-strings in SQL — parameterized queries
- ✅ Use `get_write_connection()` for writes
- ✅ Use `ON CONFLICT` with explicit targets for PostgreSQL
- ✅ Monitor idle connections (auto-timeout at 5min)

---

## 10. Deployment

### VPS
```
Host: root@72.60.190.188
Project: /root/trading_ai_bot-1/
GitHub: https://github.com/anr466/1B

Deploy: rsync files → docker compose restart
Start trading: POST /api/admin/trading/start (JWT required)
Status: GET /api/admin/system/stats
```

### Commands
```bash
# Deploy code
rsync -avz ./backend/core/group_b_system.py root@72.60.190.188:/root/trading_ai_bot-1/backend/core/

# Restart services
ssh root@72.60.190.188 "cd /root/trading_ai_bot-1 && docker compose restart api executor scanner"

# Build Flutter APK
cd flutter_trading_app && flutter build apk --debug

# Install on device
adb install -r build/app/outputs/flutter-apk/app-debug.apk
```
