# 🧠 Master Patterns — Thinking, Planning & Execution

> Unified patterns extracted from Claude Code architecture + Trading Bot System + Frontend Design.
> Reusable across any project with opencode/oh-my-opencode.
> Version: 1.0 | Last Updated: 2026-04-03

---

## Part 1: Bootstrap & Initialization Patterns

### 1.1 Bootstrap Graph — Ordered Initialization

**Pattern**: `prefetch → guards → parser → parallel_load → deferred_init → routing → execution_loop`

**Rule**: Never skip stages. Each stage depends on the previous completing successfully.

**Apply when**: Starting any new workflow, loading modules, or initializing system state.

**Example — Staged Blueprint Loading**:
```python
# Stage 1: Core (required for basic functionality)
_core = [("Mobile", load_mobile), ("Auth", load_auth), ("System", load_system)]
for name, loader in _core:
    try: register(loader())
    except: fail_hard(name)  # Core failures are fatal

# Stage 2: Admin (depends on core)
_admin = [("Admin", load_admin), ("Trading", load_trading)]
for name, loader in _admin:
    try: register(loader())
    except: warn(name)  # Admin failures are recoverable

# Stage 3: Auxiliary (optional, non-blocking)
_aux = [("FCM", load_fcm), ("Logs", load_logs), ("ML", load_ml)]
for name, loader in _aux:
    try: register(loader())
    except: log(name)  # Aux failures are silent
```

### 1.2 Deferred Init — Trust-Gated Loading

**Pattern**: Quick validation → Heavy initialization (only after trust confirmed)

```python
# Phase 1: Fast validation (fail fast)
if not validate_trust_gate(): abort()

# Phase 2: Heavy initialization (expensive, only after trust)
init_heavy_modules()
load_large_datasets()
```

### 1.3 Mode Routing — Environment-Specific Paths

```python
if target.is_remote: route_ssh(target)
elif target.is_local: route_direct(target)
else: route_default(target)
```

---

## Part 2: Execution & Query Patterns

### 2.1 Turn-Based Execution

**Pattern**: `submit → route → execute → persist → compact`

**Lifecycle**:
1. Match commands/tools from prompt tokens
2. Check permissions before execution
3. Execute matched handlers
4. Record result with token usage
5. Compact history if exceeding threshold
6. Persist session on completion

**Apply when**: Processing requests requiring multi-step reasoning.

### 2.2 Intent Routing — Token Matching

```python
tokens = tokenize(prompt)
matches = score_tokens_against_registry(tokens)
selected = pick_best(matches, limit=N)
```

**Scoring**: Token overlap against name, description, responsibility.

### 2.3 Backlog-First Planning

```python
backlog = build_backlog(modules)
for module in backlog:
    plan(module) → execute(module) → verify(module)
```

### 2.4 Parity Audit — Consistency Verification

```python
compare(source, target) → gaps → fix_gaps → re_compare()
```

**Apply when**: Verifying local matches remote, or source matches target.

---

## Part 3: State & Session Patterns

### 3.1 Session Persistence

```python
session = StoredSession(id, messages, tokens)
save(session) → load(id) → resume()
```

**Apply when**: Long-running tasks that may need resumption after interruption.

### 3.2 Transcript Compaction

```python
store.append(entry)
if len(store) > keep_last:
    store[:] = store[-keep_last:]
```

**Apply when**: Managing conversation history to stay within token limits.

### 3.3 Permission Context — Gated Execution

```python
ctx = ToolPermissionContext(deny_names, deny_prefixes)
if ctx.blocks(tool_name): deny()
```

**Apply when**: Tools or actions have different permission levels.

### 3.4 Single Source of Truth

- Database is the ONLY source for trading data
- NO mock data, NO hardcoded values
- ONE source for each data type
- ONE path for each operation
- State stored in ONE place only

---

## Part 4: Frontend & UI Patterns

### 4.1 State Stability

- NO automatic timers for refresh (causes flickering)
- Silent updates for polling (no loading indicator)
- Pull-to-refresh for manual refresh
- Use FutureProvider/StateNotifierProvider
- NO autoDispose for critical state (prevents shimmer)

### 4.2 RTL & Arabic UI

- All text must support Arabic RTL
- Use `Directionality(textDirection: TextDirection.rtl)`
- Icons and layouts must mirror for RTL
- Error messages in Arabic
- Number formatting: Arabic-Indic or Western digits consistently

### 4.3 Component Hierarchy

```
lib/
├── design/
│   ├── tokens/          # Spacing, typography, color tokens
│   ├── skins/           # Theme skins (dark, light, brand)
│   └── widgets/         # Reusable UI components
├── core/
│   ├── providers/       # State management
│   ├── repositories/    # API abstraction layer
│   └── services/        # Business logic
└── features/
    └── [feature]/
        ├── screens/     # Full-screen widgets
        └── widgets/     # Feature-specific widgets
```

### 4.4 Error State Handling

Every screen MUST handle:
- **Loading**: Shimmer skeleton (not spinner for lists)
- **Empty**: Custom empty state with action button
- **Error**: Specific error message with retry button
- **Success**: Actual content

```dart
Widget build(BuildContext context) {
  return ref.watch(provider).when(
    loading: () => const LoadingShimmer(),
    error: (e, _) => ErrorState(message: e.toString(), onRetry: () => ref.refresh(provider)),
    data: (data) => data.isEmpty
        ? EmptyState(onAction: () => /* action */)
        : ContentList(data: data),
  );
}
```

### 4.5 Responsive Design

- Use `LayoutBuilder` for adaptive layouts
- Breakpoints: mobile (<600), tablet (600-1024), desktop (>1024)
- Touch targets minimum 48x48
- Text scaling respects system settings
- Safe area handling for notches and system bars

### 4.6 Animation Guidelines

- Duration: 200-300ms for transitions
- Curve: `Curves.easeInOut` for standard, `Curves.easeOut` for entrance
- Stagger list items by 50ms
- Use `ImplicitlyAnimatedWidget` for simple animations
- Use `AnimationController` for complex sequences
- Respect `MediaQuery.accessibleNavigation` — reduce animations for accessibility

### 4.7 Color System

```dart
// Token-based color system
abstract class ColorTokens {
  static const primary = Color(0xFF1B5E20);    // Brand green
  static const secondary = Color(0xFF2E7D32);  // Light green
  static const error = Color(0xFFD32F2F);      // Error red
  static const warning = Color(0xFFFFA000);    // Warning amber
  static const success = Color(0xFF388E3C);    // Success green
  static const info = Color(0xFF1976D2);       // Info blue
}
```

### 4.8 Typography System

```dart
abstract class TypographyTokens {
  static const displayLarge = TextStyle(fontSize: 32, fontWeight: FontWeight.bold);
  static const headlineMedium = TextStyle(fontSize: 24, fontWeight: FontWeight.w600);
  static const titleLarge = TextStyle(fontSize: 20, fontWeight: FontWeight.w600);
  static const bodyLarge = TextStyle(fontSize: 16, fontWeight: FontWeight.normal);
  static const bodyMedium = TextStyle(fontSize: 14, fontWeight: FontWeight.normal);
  static const labelSmall = TextStyle(fontSize: 12, fontWeight: FontWeight.w500);
}
```

### 4.9 Spacing System

```dart
abstract class SpacingTokens {
  static const xxs = 4.0;
  static const xs = 8.0;
  static const sm = 12.0;
  static const md = 16.0;
  static const lg = 24.0;
  static const xl = 32.0;
  static const xxl = 48.0;
}
```

---

## Part 5: Backend & API Patterns

### 5.1 REST API Design

- Resource-based URLs: `/api/users`, `/api/trades`
- HTTP methods: GET (read), POST (create), PUT (update), DELETE (remove)
- Consistent response format: `{success, data, error}`
- Pagination for list endpoints
- Rate limiting on all endpoints
- Authentication via JWT tokens

### 5.2 Error Handling

```python
# Consistent error response format
{
    "success": False,
    "error": "User message in Arabic",
    "code": "ERROR_CODE"
}
```

### 5.3 Database Patterns

- Use parameterized queries (NEVER string interpolation)
- Foreign keys for referential integrity
- `created_at`, `updated_at` on all tables
- Soft deletes where appropriate (`is_deleted` flag)
- Indexes on frequently queried columns

### 5.4 User Isolation

```sql
-- Every query MUST include user_id + is_demo
SELECT * FROM portfolio WHERE user_id = %s AND is_demo = %s;
```

---

## Part 6: Security Patterns

### 6.1 Authentication Flow

```
Login → Save credentials for biometric automatically
Enable Biometric → User logged in → Just enable, NO credential prompt
Biometric Fail → Clear tokens → Force logout
Remember Me → Save credentials during login
```

### 6.2 API Security

- JWT tokens with expiration
- Refresh token rotation
- Rate limiting per endpoint
- Input validation on all endpoints
- CORS configured for production origins only
- HTTPS in production

### 6.3 Data Protection

- Encrypt sensitive data at rest
- Never log passwords, tokens, or API keys
- Use environment variables for secrets
- Validate and sanitize all user input

---

## Part 7: Testing Patterns

### 7.1 Flutter Testing

```bash
flutter analyze  # 0 errors required
flutter test     # All tests pass
```

### 7.2 Backend Testing

```bash
docker-compose restart api worker
curl http://server:3002/api/system/status
```

### 7.3 Coverage Check (BEFORE planning)

- Layers analyzed? (Backend? DB? Mobile? API?)
- Features tested? (Auth? Orders? Risk?)
- Scenarios considered? (Success? Failure? Edge?)
- States verified? (Initial? Loading? Error?)
- Integrations checked?

### 7.4 Re-Audit (MANDATORY after fixes)

- MINIMUM 1 new issue or prove perfect
- Edge cases MANDATORY for EVERY component
- Coverage checkpoint before declaring done

---

## Part 8: Workflow Patterns

### 8.1 Intent Classification

| User Intent | Action |
|---|---|
| "explain X" / "how does Y work" | explore → synthesize → answer |
| "implement X" / "add Y" / "create Z" | plan → delegate → verify |
| "look into X" / "check Y" | explore → report findings |
| "what do you think about X?" | evaluate → propose → wait |
| "I'm seeing error X" / "Y is broken" | diagnose → fix minimally |
| "refactor" / "improve" / "clean up" | assess → propose → wait |

### 8.2 Delegation

| Task Type | Category | Skills |
|---|---|---|
| Frontend/UI | `visual-engineering` | frontend-ui-ux |
| Complex logic | `ultrabrain` | debugging, architecture |
| Quick fixes | `quick` | lint-and-validate |
| Hard problems | `deep` | oracle consultation |
| Documentation | `writing` | documentation |

### 8.3 Commit Workflow

```bash
git add -A && git commit -m "type: description" && git push
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

---

## Part 9: Quality Gates

### 9.1 Zero Tolerance

| Violation | Status |
|-----------|--------|
| "I couldn't because..." | UNACCEPTABLE |
| "This is simplified..." | UNACCEPTABLE |
| "You can extend later..." | UNACCEPTABLE |
| "Due to limitations..." | UNACCEPTABLE |
| "I made assumptions..." | UNACCEPTABLE |
| Hardcoded values | UNACCEPTABLE |
| Mock data in production | UNACCEPTABLE |

### 9.2 Code Quality Checklist

- [ ] 0 lint/analyze errors
- [ ] All tests pass
- [ ] No hardcoded values
- [ ] Single source of truth maintained
- [ ] Proper error handling
- [ ] Edge cases handled
- [ ] Coverage check done
- [ ] Re-audit completed

---

## Part 10: Quick Reference

### When to Use Each Pattern

| Pattern | Trigger |
|---------|---------|
| Bootstrap Graph | System startup, module loading |
| Turn-Based Execution | Multi-turn reasoning tasks |
| Intent Routing | Tool/agent selection |
| Permission Context | Destructive or mode-specific actions |
| Transcript Compaction | Long conversations approaching limits |
| Session Persistence | Tasks that may be interrupted |
| Backlog-First | Complex multi-module tasks |
| Parity Audit | Local vs remote consistency checks |
| State Stability | UI refresh and polling |
| Error State Handling | Every screen/widget |
| Responsive Design | Cross-device layouts |

---

**This file is project-agnostic — use with any opencode/oh-my-opencode project.**
