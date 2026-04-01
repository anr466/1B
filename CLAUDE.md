# CLAUDE.md - Trading Bot System Enhanced Rules

> **Enhanced with Antigravity Awesome Skills v9.4.0 | 1,340+ Agentic Skills**

---

## 🎯 Project Overview

**Trading Bot System** - Flutter Mobile App + Python FastAPI Backend + PostgreSQL

### Tech Stack
- **Frontend**: Flutter (Dart) - Arabic RTL UI
- **Backend**: Python FastAPI
- **Database**: PostgreSQL
- **Trading**: Autonomous trading system (NOT a trading engine)

### Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Flutter Mobile App                        │
│  (Arabic RTL UI, State Management, API Calls)               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Python FastAPI Backend                    │
│  (REST API, Trading Logic, State Machine)                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                       │
│  (Users, Positions, Signals, Settings)                      │
└─────────────────────────────────────────────────────────────┘
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

## 🛠️ Available Skills (from Antigravity Awesome Skills)

### Core Development Skills
| Skill | Description | Use Case |
|-------|-------------|----------|
| `@brainstorming` | Planning and ideation | Feature planning, MVP design |
| `@test-driven-development` | TDD workflow | Writing tests first |
| `@debugging-strategies` | Systematic debugging | Fixing complex bugs |
| `@security-auditor` | Security review | Code security checks |
| `@lint-and-validate` | Code quality | Validation checks |
| `@api-design-principles` | API design | REST API best practices |
| `@frontend-design` | UI/UX patterns | Flutter UI quality |
| `@create-pr` | PR packaging | Clean pull requests |

### Trading System Skills
| Skill | Description | Use Case |
|-------|-------------|----------|
| `@planning` | Step-by-step planning | Complex feature planning |
| `@implementation` | Code implementation | Building features |
| `@review` | Code review | Quality assurance |
| `@refactoring` | Code refactoring | Improving code structure |
| `@testing` | Test creation | Unit, integration tests |
| `@documentation` | Documentation | API docs, comments |

### Flutter-Specific Skills
| Skill | Description | Use Case |
|-------|-------------|----------|
| `@flutter-best-practices` | Flutter patterns | Widget, state management |
| `@dart-performance` | Performance | Optimization |
| `@rtl-support` | RTL/UI | Arabic interface |

### Python/FastAPI Skills
| Skill | Description | Use Case |
|-------|-------------|----------|
| `@python-best-practices` | Python patterns | Clean code |
| `@fastapi-patterns` | FastAPI design | REST endpoints |
| `@async-python` | Async/await | Concurrent operations |
| `@database-patterns` | DB patterns | PostgreSQL queries |

---

## 🚀 ULTRAWORK MODE (When Enabled)

### MANDATORY PROTOCOL

**BEFORE ANY IMPLEMENTATION:**
1. **UNDERSTAND** - What does the user ACTUALLY want?
2. **EXPLORE** - Check existing patterns, architecture
3. **PLAN** - Crystal clear work plan
4. **RESOLVE** - No ambiguity

**IF NOT 100% CERTAIN:**
- Use `@brainstorming` skill for planning
- Use `@debugging-strategies` for complex bugs
- Consult Oracle for architecture decisions

### CERTAINTY PROTOCOL
```
1. THINK DEEPLY → True intent
2. EXPLORE THOROUGHLY → Fire explore/librarian agents
3. CONSULT SPECIALISTS → Oracle/Artistry for hard problems
4. ASK USER → If ambiguity remains
```

---

## 📁 Project Structure

### Flutter
```
flutter_trading_app/
├── lib/
│   ├── core/
│   │   ├── providers/     # State management
│   │   ├── repositories/   # API calls
│   │   ├── services/       # Business logic
│   │   └── constants/      # API endpoints
│   ├── features/
│   │   ├── auth/           # Login, Splash, OTP
│   │   ├── admin/          # Trading control
│   │   ├── dashboard/     # Main dashboard
│   │   ├── portfolio/      # Portfolio view
│   │   ├── trades/         # Trades list
│   │   └── settings/       # Settings screens
│   └── design/             # UI components
```

### Backend
```
backend/
├── api/                    # FastAPI endpoints
├── core/
│   ├── trading_state_machine.py  # SINGLE SOURCE for trading state
│   └── state_manager.py          # State coordination
└── infrastructure/
    └── db_access.py        # Database access
```

---

## 🎨 Code Quality Standards

### Flutter/Dart
```dart
// ✅ Good: Clear naming, single responsibility
class AccountTradingNotifier extends StateNotifier<AccountTradingState> {
  // Use descriptive names
  // Keep methods small (< 50 lines)
  // One responsibility per class
}

// ❌ Bad: Vague naming, multiple responsibilities
class Manager {
  void doStuff() { ... }  // What does this do?
}
```

### Python/FastAPI
```python
# ✅ Good: Type hints, docstrings
async def get_user_portfolio(
    user_id: int,
    is_demo: bool = False
) -> Dict[str, Any]:
    """Get user portfolio data.
    
    Args:
        user_id: The user ID
        is_demo: Whether to get demo portfolio
        
    Returns:
        Dict with portfolio data
    """
    pass

# ❌ Bad: No types, no docs
def get_data(id, demo=False):
    pass
```

---

## 📋 Workflow

### Before Any Work
1. Read `.windsurfrules`
2. Read `AGENTS.md`
3. Read `CLAUDE.md` (this file)

### For Each Task
1. **ANALYZE** → Find issues (min 3)
2. **PLAN** → Create fix plan
3. **EXECUTE** → Implement fixes
4. **TEST** → Run analyze + tests
5. **COMMIT** → git add -A && git commit && git push

### Coverage Check
- Layers analyzed? (Backend? DB? Mobile? API?)
- Features tested? (Auth? Orders? Risk?)
- Scenarios considered? (Success? Failure? Edge?)
- States verified? (Initial? Loading? Error?)

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

---

## 🚫 Zero Tolerance

| Violation | Consequence |
|-----------|-------------|
| "I couldn't because..." | UNACCEPTABLE |
| "This is a simplified version..." | UNACCEPTABLE |
| "You can extend this later..." | UNACCEPTABLE |
| "Due to limitations..." | UNACCEPTABLE |
| "I made some assumptions..." | UNACCEPTABLE |

---

## 📚 Skill Usage Guidelines

### When to Use Skills
- **Planning**: Use `@brainstorming` before complex features
- **Debugging**: Use `@debugging-strategies` for hard bugs
- **Security**: Use `@security-auditor` for auth/finance code
- **Testing**: Use `@test-driven-development` for new features
- **API**: Use `@api-design-principles` for endpoints

### How to Invoke
```
Use @skill-name to [task description]
```

Example:
```
Use @brainstorming to design the portfolio refresh mechanism
Use @security-auditor to review the authentication flow
Use @debugging-strategies to find why trades aren't showing
```

---

## 🎯 Success Criteria

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

**This file is automatically loaded by OpenCode and enhances every session with project-specific context and capabilities.**