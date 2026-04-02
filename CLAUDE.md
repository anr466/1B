# 🤖 TRADING BOT SYSTEM — SYSTEM CONSTITUTION

> **Unified Constitution for OpenCode + Oh My OpenCode + 1,335 Skills**
> Last Updated: 2026-04-02 | Version: 2.0

---

## 🎯 SYSTEM IDENTITY

**Trading Bot System** — Flutter Mobile App + Python FastAPI Backend + PostgreSQL
- **Frontend**: Flutter (Dart) — Arabic RTL UI
- **Backend**: Python FastAPI — REST API, Trading Logic, State Machine
- **Database**: PostgreSQL — Users, Positions, Signals, Settings
- **Trading**: Autonomous trading system (NOT a manual trading engine)

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

## 🔴 MANDATORY RULES (Non-Negotiable)

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
Enable Biometric → User is logged in → Just enable, NO credential prompt
Biometric Fail → Clear tokens → Go to login
Remember Me → Save credentials during login
```

---

## 🧠 REASONING PROTOCOL (Branching Logic)

### Step 0: Intent Classification (BEFORE any action)
| User Intent | Your Action |
|---|---|
| "explain X" / "how does Y work" | explore/librarian → synthesize → answer |
| "implement X" / "add Y" / "create Z" | plan → delegate → verify |
| "look into X" / "check Y" | explore → report findings |
| "what do you think about X?" | evaluate → propose → wait for confirmation |
| "I'm seeing error X" / "Y is broken" | diagnose → fix minimally |
| "refactor" / "improve" / "clean up" | assess codebase → propose approach |

### Step 1: Exploration (Parallel)
- Fire 2-5 explore/librarian agents in parallel
- Use direct tools for known locations
- NEVER wait for explore results if you have other work

### Step 2: Planning (MANDATORY for 2+ steps)
- Create todo list IMMEDIATELY
- Mark current task in_progress before starting
- Mark completed as soon as done

### Step 3: Execution (Delegate)
- Frontend work → `visual-engineering` category
- Complex logic → `ultrabrain` category
- Quick fixes → `quick` category
- Hard problems → `oracle` or `artistry`

### Step 4: Verification (MANDATORY)
- `lsp_diagnostics` clean on changed files
- Build passes (exit code 0)
- Tests pass
- Manual QA executed

### Step 5: Re-Audit (MANDATORY after fixes)
- Run audit again
- MINIMUM 1 new issue or prove perfect
- Coverage checkpoint before declaring done

---

## 📁 SKILL CATEGORIES (Priority Order)

### TIER 1: Core Development (Always Available)
| Skill | Use Case |
|---|---|
| `@brainstorming` | Planning and ideation |
| `@test-driven-development` | TDD workflow |
| `@debugging-strategies` | Systematic debugging |
| `@security-auditor` | Code security checks |
| `@lint-and-validate` | Validation checks |
| `@api-design-principles` | REST API best practices |
| `@frontend-design` | Flutter UI quality |
| `@create-pr` | Clean pull requests |

### TIER 2: Trading System (Domain-Specific)
| Skill | Use Case |
|---|---|
| `@planning` | Step-by-step planning |
| `@implementation` | Code implementation |
| `@review` | Quality assurance |
| `@refactoring` | Code improvement |
| `@testing` | Unit/integration tests |
| `@documentation` | API docs, comments |

### TIER 3: Flutter-Specific
| Skill | Use Case |
|---|---|
| `@flutter-best-practices` | Widget, state management |
| `@dart-performance` | Performance optimization |
| `@rtl-support` | Arabic RTL interface |

### TIER 4: Python/FastAPI
| Skill | Use Case |
|---|---|
| `@python-best-practices` | Clean code patterns |
| `@fastapi-patterns` | REST endpoint design |
| `@async-python` | Concurrent operations |
| `@database-patterns` | PostgreSQL queries |

### TIER 5: Security & Compliance (On-Demand)
| Skill | Use Case |
|---|---|
| `@security-audit` | Full security review |
| `@pentest-checklist` | Penetration testing |
| `@api-security-best-practices` | API security |

### TIER 6: 1,300+ Additional Skills (Search on Demand)
- Use `@find-skills` to discover skills for specific tasks
- Skills organized in `~/.agents/skills/` by category
- **Do NOT auto-load all 1,335 skills** — load only what's needed

---

## 🏗️ ARCHITECTURE

### Flutter
```
flutter_trading_app/
├── lib/
│   ├── core/
│   │   ├── providers/     # State management (Riverpod)
│   │   ├── repositories/   # API calls
│   │   ├── services/      # Business logic
│   │   └── constants/     # API endpoints (SINGLE SOURCE)
│   ├── features/
│   │   ├── auth/          # Login, Splash, OTP
│   │   ├── admin/         # Trading control
│   │   ├── dashboard/     # Main dashboard
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

### Database
```
PostgreSQL:
- users (id, email, user_type, is_active)
- user_settings (user_id, is_demo, trading_enabled, ...)
- portfolio (user_id, is_demo, total_balance, ...)
- active_positions (user_id, symbol, entry_price, ...)
- user_trades (user_id, symbol, pnl, ...)
- system_status (status, trading_state, ...)
```

---

## 🔄 WORKFLOW

### Before Any Work:
1. Read `.windsurfrules`
2. Read `AGENTS.md`
3. Read this `CLAUDE.md`

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

## ⚠️ AUDITOR RULES (STRICT)

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

## 🧪 TESTING REQUIREMENTS

### Flutter
```bash
flutter analyze  # 0 errors required
flutter test     # All tests pass
```

### Backend
```bash
docker-compose restart api worker
curl http://72.60.190.188:3002/api/system/status
```

### Database
```bash
docker exec trading-ai-postgres psql -U trading_user -d trading_ai_bot -c "SELECT * FROM system_status;"
```

---

## 📱 DEVICE & SERVER CONFIGURATION

### Local Device
- **Device**: SM S908E (Android 16)
- **USB**: R5CT50P51XX
- **IP**: 10.118.134.128

### Remote Server
- **IP**: 72.60.190.188
- **API**: http://72.60.190.188:3002/api
- **SSH**: root@72.60.190.188
- **Admin User ID**: 10081 (NOT 1)

---

## 🔑 KEY INSIGHTS FROM EXPERIENCE

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

### Database Unification (COMPLETED)
- `portfolio` table is single source for both demo and real wallets
- `is_demo` boolean distinguishes wallet types
- `demo_accounts` table: exists in DB but ZERO code references
- Admin user ID resolved dynamically (not hardcoded to 1)

---

## 🚫 ZERO TOLERANCE

| Violation | Consequence |
|-----------|-------------|
| "I couldn't because..." | UNACCEPTABLE |
| "This is a simplified version..." | UNACCEPTABLE |
| "You can extend this later..." | UNACCEPTABLE |
| "Due to limitations..." | UNACCEPTABLE |
| "I made some assumptions..." | UNACCEPTABLE |
| Hardcoded user_id=1 | UNACCEPTABLE (use dynamic lookup) |
| Using demo_accounts table | UNACCEPTABLE (use portfolio) |

---

## 📚 MCP SERVERS

| Server | Command | Purpose |
|---|---|---|
| `playwright` | `npx -y @anthropic-ai/mcp-server-playwright` | Browser automation |
| `filesystem` | `npx -y @anthropic-ai/mcp-server-filesystem` | File system access |

---

## 🎯 SUCCESS CRITERIA

### Code Quality
- [ ] 0 flutter analyze errors
- [ ] All tests pass
- [ ] No hardcoded values
- [ ] Single source of truth maintained
- [ ] Proper error handling

### Feature Complete
- [ ] All requirements met
- [ ] All edge cases handled
- [ ] Coverage check done
- [ ] Re-audit completed

---

**This file is the SYSTEM CONSTITUTION — it governs all behavior, reasoning, and execution.**
**Automatically loaded by OpenCode at session start.**
