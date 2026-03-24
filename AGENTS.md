# AGENTS.md - Trading Bot System Agent Rules

## 📋 System Overview

This is a **Flutter Trading Application** with:
- **Frontend**: Flutter Mobile App (Arabic UI)
- **Backend**: Python FastAPI
- **Database**: PostgreSQL
- **Trading**: Autonomous trading system (NOT a trading engine)

### User Capabilities (MUST follow)
Users CAN ONLY:
- ✅ activate/deactivate trading
- ✅ connect API keys
- ✅ monitor system status
- UI = Reflection of System State

Users CANNOT:
- ❌ modify trading strategies
- ❌ modify take profit / stop loss
- ❌ interfere with trade logic

### User Types
1. **ADMIN**: Has demo + real wallets, can switch between them
2. **NORMAL USER**: Real trading only, no demo mode

### Critical Rule: Trading Enable/Disable
```
6 users enabled → trading engine OPENS trades for them
4 users disabled → trading engine ONLY manages their open trades
```

---

## 🔴 MANDATORY RULES

### 1. Single Source of Truth
- Database is the ONLY source for trading data
- NO mock data, NO hardcoded values, NO fake wallets
- All UI data must come from backend API

### 2. User Isolation
- Each user has isolated data (user_id + is_demo)
- NO data leakage between users
- Demo/Real wallets are separate records

### 3. State Management
- ONE source for each data
- ONE path for each operation
- State stored in ONE place only
- Direct updates MUST go through source

### 4. Error Handling
- All API calls MUST have try-catch
- Show specific error messages (not generic)
- Verify state after operations

### 5. Biometric & Auth Flow
```
Login Success → Save credentials for biometric automatically
Enable Biometric → User is logged in → Just enable, no credential prompt
Biometric Fail → Clear tokens → Go to login
Remember Me → Save credentials during login
```

---

## 📁 Critical Files

### Flutter
```
flutter_trading_app/
├── lib/
│   ├── core/
│   │   ├── providers/     # State management
│   │   ├── repositories/   # API calls
│   │   ├── services/      # Business logic
│   │   └── constants/     # API endpoints (SINGLE SOURCE)
│   ├── features/
│   │   ├── auth/          # Login, Splash, OTP
│   │   ├── admin/         # Trading control
│   │   ├── dashboard/    # Main dashboard
│   │   ├── portfolio/     # Portfolio view
│   │   ├── trades/        # Trades list
│   │   └── settings/      # Settings screens
│   └── design/            # UI components
```

### Backend
```
backend/
├── api/                   # FastAPI endpoints
├── core/
│   ├── trading_state_machine.py  # SINGLE SOURCE for trading state
│   └── state_manager.py         # State coordination
└── infrastructure/
    └── db_access.py       # Database access
```

---

## 🏗️ Architecture Rules

### 1. Trading State (CRITICAL)
```
SINGLE SOURCE: TradingStateMachine
     ↓
_transition() → Database (system_status table)
     ↓
NO direct DB updates from other modules
NO in-memory caching for state
```

### 2. User Trading State
```
user_settings.trading_enabled = true/false
     ↓
Trading engine reads this to decide:
- Open new trades for enabled users
- Continue managing open trades for all users
```

### 3. Provider Architecture
```
Providers:
- Use FutureProvider/StateNotifierProvider
- NO autoDispose for critical state (prevents shimmer)
- Silent updates for polling (no loading indicator)
- Explicit refresh only for pull-to-refresh
```

---

## ⚠️ Auditor Rules (STRICT)

### Forbidden Phrases
- ❌ "All good"
- ❌ "No issues found"
- ❌ "Works as expected"
- ❌ "Probably fine"

### Required Phrases
- ✅ "Found [N] issues:"
- ✅ "Edge case failure in [component]:"
- ✅ "Critical risk:"
- ✅ "Coverage check:"
- ✅ "Re-audit results:"

### Minimum Requirements
- MINIMUM 3 issues per review
- Edge cases MANDATORY for EVERY component
- Coverage checkpoint BEFORE planning
- Re-audit MANDATORY after fixes

---

## 🔄 Workflow Steps

### Before Any Work:
1. Read .windsurfrules
2. Read this AGENTS.md
3. Read .TRADING_BOT_SYSTEM_DESIGN_v1.2.md

### For Each Task:
1. **ANALYZE** → Find issues (min 3)
2. **PLAN** → Create fix plan
3. **EXECUTE** → Implement fixes
4. **TEST** → Run analyze + tests
5. **COMMIT** → git add -A && git commit && git push

### Coverage Check (BEFORE planning):
- Layers analyzed? (Backend? DB? Mobile? API?)
- Features tested? (Auth? Orders? Risk?)
- Scenarios considered? (Success? Failure? Edge?)
- States verified? (Initial? Loading? Error?)
- Integrations checked?

---

## 🧪 Testing Requirements

### Flutter
```bash
flutter analyze  # 0 errors required
flutter test     # All tests pass
```

### Backend
```bash
docker-compose restart api worker
curl http://10.118.134.44:3002/api/system/status
```

### Database
```bash
docker exec trading-ai-postgres psql -U trading_user -d trading_ai_bot -c "SELECT * FROM system_status;"
```

---

## 📱 Device Configuration

- **Device**: SM S908E (Android 16)
- **USB**: R5CT50P51XX
- **IP**: 10.118.134.128
- **Backend**: http://10.118.134.44:3002/api

---

## 🔑 Key Insights from Experience

### Auth Flow (FIXED)
1. Login → credentials saved for biometric automatically
2. Enable biometric → user logged in → just enable, NO credential prompt
3. App open → if biometric enabled → require biometric
4. Biometric fail → clear tokens + force logout

### Trading Toggle (UNIFIED)
All screens use `accountTradingProvider.setEnabled()`:
- Dashboard
- Profile
- Settings

### State Stability
- NO automatic timers for refresh (causes flickering)
- Silent updates for polling (no loading indicator)
- Pull-to-refresh for manual refresh

### Single Source of Truth
- API endpoints → ApiEndpoints class
- Trading state → TradingStateMachine
- User state → Database (user_settings)
