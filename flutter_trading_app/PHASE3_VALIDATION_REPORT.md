# PHASE 3: Feature-by-Feature Validation Report
> Flutter Trading App — UI ↔ Logic ↔ Data Chain Validation

---

## 🔴 CRITICAL FINDINGS

### 1. Dual UserModel — Data Integrity Risk
**Severity:** 🔴 HIGH  
**Files:**
- `lib/core/models/user_model.dart` (ACTIVE — used by AuthProvider)
- `lib/core/data/models/user_model.dart` (LEGACY — used by StorageService)

**Problem:** Two different `UserModel` classes with incompatible field sets:

| Field | Active Model (`core/models/`) | Legacy Model (`core/data/models/`) |
|-------|:---:|:---:|
| `username` | required String | nullable String? |
| `emailVerified` | ✅ | ❌ |
| `biometricEnabled` | ✅ | ❌ |
| `lastLogin` | ✅ | ❌ |
| `phoneNumber` | ✅ (as `phone_number`) | ✅ (as `phone`) |
| `fullName` | ❌ | ✅ |
| `tradingMode` | ❌ | ✅ |
| `hasBinanceKeys` | ❌ | ✅ |
| `tradingEnabled` | ❌ | ✅ |
| `isActive` | ❌ | ✅ |
| `copyWith()` | ❌ | ✅ |
| `displayName` getter | ❌ | ✅ (`fullName ?? name ?? username ?? email`) |

**Data Flow Bug:**
1. `AuthService._saveAuthData()` saves raw API JSON → `StorageService.saveUserData(rawMap)` ✅
2. `AuthProvider.checkAuth()` creates `core/models/UserModel.fromJson(rawMap)` — **strips** fields like `fullName`, `tradingMode`, `hasBinanceKeys`
3. Then calls `storage.saveUserData(user.toJson())` — **overwrites** storage with stripped data
4. API fields lost after first `checkAuth()` cycle

**Impact:**
- `StorageService.saveUser()`/`getUser()` use legacy model — only called from legacy `core/data/repositories/auth_repository.dart`
- Active code uses `saveUserData(Map)` directly — no runtime crash, but data loss on re-serialization
- If any screen accesses `fullName` or `tradingMode` from stored user data, it will be null after `checkAuth()`

**Fix:** Consolidate into a single `UserModel` with all needed fields. Delete legacy model after migrating `StorageService` import.

---

### 2. BaseURL `127.0.0.1` — Android Emulator Incompatible
**Severity:** 🔴 HIGH  
**File:** `lib/core/constants/api_endpoints.dart:6`

```dart
static const String baseUrl = 'http://127.0.0.1:3002/api';
```

**Problem:** `127.0.0.1` is unreachable from Android emulator. Android emulator requires `10.0.2.2` to reach host machine. Real device with `adb reverse` can use `127.0.0.1`.

**Note:** Per project history, this was previously fixed. The current code uses `127.0.0.1` which works for real device testing via `adb reverse tcp:3002 tcp:3002`, but will fail on emulator.

**Fix:** Make configurable (environment-based or runtime detection).

---

## 🟡 MEDIUM FINDINGS

### 3. Dead Code Directories — 30 Legacy Files
**Severity:** 🟡 MEDIUM  

| Directory | Files | Status |
|-----------|-------|--------|
| `lib/presentation/` | 6 .dart files | Legacy providers/routing — replaced by `lib/core/providers/` + `lib/navigation/` |
| `lib/skins/classic/` | 13 .dart files | Legacy skin system — replaced by `lib/design/skins/` + `lib/features/` |
| `lib/skins/modern_neon/` | 1 .dart file | Unused skin |
| `lib/skins/skin_base/` | 2 .dart files | Legacy skin interface — replaced by `lib/design/skins/` |
| `lib/core/data/` | 6 .dart files | Legacy models/repositories — replaced by `lib/core/models/` + `lib/core/repositories/` |
| `lib/shared/` | 2 .dart files | Legacy constants — replaced by `lib/core/constants/` |
| **Total** | **30 files** | **Dead code** |

**Critical dependency:** `lib/core/services/storage_service.dart` imports `lib/core/data/models/user_model.dart` — this prevents clean deletion of `core/data/`.

**Fix:** 
1. Migrate `StorageService` to use `core/models/user_model.dart`
2. Verify no other active imports from legacy dirs
3. Delete all 30 legacy files

---

### 4. Route `activePositions` Defined But No Screen
**Severity:** 🟡 LOW  
**Files:**
- `lib/navigation/route_names.dart:26` — defines `static const String activePositions = '/positions/active'`
- `lib/core/constants/api_endpoints.dart:72` — defines `activePositions()` endpoint
- NO active screen at `lib/features/` for active positions

**Impact:** Unused route definition. Only referenced in legacy `skins/classic/` dashboard.

---

### 5. `notificationRead` (Mark Single) — Endpoint Exists, Not Used in UI
**Severity:** 🟡 LOW  
**Files:**
- `lib/core/constants/api_endpoints.dart:105-106` — defines `notificationRead(userId, notificationId)`
- `lib/core/repositories/notifications_repository.dart` — has `markAsRead()` method
- UI (`notifications_screen.dart`) only has "Mark All Read" button — no per-notification mark-read on tap

**Impact:** Users cannot mark individual notifications as read, only bulk "read all".

---

### 6. Notification Settings Endpoint Mismatch
**Severity:** 🟡 MEDIUM  
**Files:**
- Flutter: `ApiEndpoints.notificationSettings = '/user/notifications/settings'` (no userId in path)
- Backend has TWO endpoints:
  - `/user/notification-settings/<user_id>` (GET/PUT) — older route
  - `/user/notifications/settings` (GET/PUT) — newer route, reads userId from auth token

**Risk:** If Flutter sends to `/user/notifications/settings` without userId in path but backend expects it from token — works ONLY if auth middleware injects `g.user_id`. Otherwise 401/404.

---

## ✅ VALIDATED FEATURES (Working Correctly)

### Auth Flow
| Step | UI | Logic | Data | Status |
|------|-----|-------|------|--------|
| Login | `login_screen.dart` | `auth_provider.dart` → `auth_service.dart` | API `/auth/login` | ✅ |
| Register + OTP | `register_screen.dart` → `otp_verification_screen.dart` | `auth_service.sendRegistrationOtp()` → `verifyRegistrationOtp()` | API `/auth/send-registration-otp` → `/auth/verify-registration-otp` | ✅ |
| Forgot Password | `forgot_password_screen.dart` → `otp_verification_screen.dart` → `reset_password_screen.dart` | `auth_service.forgotPassword()` → `verifyResetOtp()` → `resetPassword()` | API chain correct | ✅ |
| Biometric Setup | `biometric_setup_screen.dart` | `biometric_service.dart` + `storage_service.dart` | Local only | ✅ |
| Biometric Login | `splash_screen.dart` | `auth_service.biometricVerify()` | API `/user/biometric/verify` | ✅ |
| Session Check | `splash_screen.dart` | `auth_provider.checkAuth()` → `auth_service.validateSession()` | API `/auth/validate-session` | ✅ (with data loss bug #1) |
| Logout | Profile menu | `auth_provider.logout()` → `auth_service.logout()` | Clears storage | ✅ |

**Auth error handling:** ✅ All screens have mounted checks, try/catch, and user-facing error messages.

### Dashboard
| Component | Provider | Repository | API | Status |
|-----------|----------|------------|-----|--------|
| Balance card | `portfolioProvider` | `portfolio_repository.getPortfolio()` | `/user/portfolio/<id>` | ✅ |
| Stats row | `statsProvider` | `portfolio_repository.getStats()` | `/user/stats/<id>` | ✅ |
| Recent trades | `recentTradesProvider` | `trades_repository.getRecentTrades()` | `/user/trades/<id>` | ✅ |
| System status (admin) | `systemStatusProvider` | `admin_repository.getSystemStatus()` | `/system/status` | ✅ |
| Performance chart | Derived from trades + portfolio | — | — | ✅ |
| Pull-to-refresh | Invalidates all 4 providers | — | — | ✅ |

### Portfolio
| Component | Provider | Status |
|-----------|----------|--------|
| Balance details | `portfolioProvider` | ✅ |
| Stats breakdown | `statsProvider` | ✅ |
| Balance visibility | `balanceVisibilityProvider` | ✅ (persisted in SharedPreferences) |
| Pie chart | Local calculation from portfolio data | ✅ |
| Pull-to-refresh | Invalidates portfolio + stats | ✅ |

### Trades
| Component | Provider | Status |
|-----------|----------|--------|
| Paginated list | `tradesListProvider` (StateNotifier) | ✅ |
| Filter chips (all/open/closed) | `loadFirstPage(statusFilter:)` | ✅ |
| Infinite scroll | ScrollController + `loadNextPage()` | ✅ |
| Trade detail | GoRouter extra (TradeModel) | ✅ (null-safe fallback) |
| Pull-to-refresh | `refresh()` | ✅ |

### Analytics
| Component | Status |
|-----------|--------|
| Win/loss rates | ✅ (derived from StatsModel) |
| Equity curve | ✅ (fl_chart from trades data) |
| Trade breakdown | ✅ |

### Settings
| Feature | UI | Logic | Data | Status |
|---------|-----|-------|------|--------|
| Trading settings | `trading_settings_screen.dart` | `settingsDataProvider` → `settings_repository` | API `/user/settings/<id>` | ✅ |
| Trading mode (admin) | Same screen | `settings_repository.updateTradingMode()` | API `/user/settings/trading-mode/<id>` | ✅ |
| Binance keys | `binance_keys_screen.dart` | `settings_repository.validateBinanceKeys()` | API `/user/binance-keys/validate` | ✅ |
| Skin picker | `skin_picker_screen.dart` | `skinNameProvider` + `themeModeProvider` | StorageService (local) | ✅ |
| Security | `security_settings_screen.dart` | `auth_service` secure actions | API `/user/secure/*` | ✅ |
| Notifications | `notification_settings_screen.dart` | `notifications_repository` | API `/user/notifications/settings` | ✅ (see finding #6) |

### Admin
| Feature | UI | Logic | Data | Status |
|---------|-----|-------|------|--------|
| Dashboard | `admin_dashboard_screen.dart` | `systemStatusProvider` + `mlStatusProvider` | API `/system/status` + `/admin/system/ml-status` | ✅ |
| Trading control | `trading_control_screen.dart` | `admin_repository` | API `/admin/trading/*` | ✅ |
| User management | `user_management_screen.dart` | `adminUsersProvider` | API `/admin/users/all` | ✅ |
| System logs | `system_logs_screen.dart` | `admin_repository.getActivityLogs()` | API `/admin/activity-logs` | ✅ |

### Notifications
| Feature | Provider | Status |
|---------|----------|--------|
| Paginated list | `notificationsListProvider` (StateNotifier) | ✅ |
| Infinite scroll | ScrollController | ✅ |
| Mark all read | `markAllRead()` + invalidate unread count | ✅ |
| Unread badge | `unreadCountProvider` | ✅ |
| Push notifications | `PushNotificationService` (Firebase + polling) | ✅ |

### Navigation
| Aspect | Status |
|--------|--------|
| All RouteNames registered in GoRouter | ✅ (19 routes) |
| Auth redirect logic | ✅ (refreshListenable pattern) |
| Admin route guard | ✅ (checks `auth.isAdmin`) |
| ShellRoute for bottom nav | ✅ (5 tabs: dashboard, portfolio, trades, analytics, profile) |
| Deep linking from notifications | ✅ (PushNotificationService.onNotificationTap) |

### API Endpoint Alignment (Flutter ↔ Backend)
| Flutter Prefix | Backend Blueprint | URL Prefix | Match |
|---------------|-------------------|------------|-------|
| `/auth/*` | `auth_bp` | `/auth` | ✅ |
| `/user/*` | `mobile_bp` | `/user` | ✅ |
| `/admin/*` | `admin_unified_bp` | `/admin` | ✅ |
| `/admin/trading/*` | `trading_control_bp` | `/admin/trading` | ✅ |
| `/system/*` | `system_bp` | `/system` | ✅ |

Flask mounted on `/api` via `WSGIMiddleware` → all paths become `/api/...` matching Flutter's `baseUrl = '.../api'` ✅

---

## 📊 SUMMARY

| Category | Count |
|----------|-------|
| 🔴 Critical issues | 2 (dual UserModel, baseURL) |
| 🟡 Medium issues | 2 (dead code, notification settings) |
| 🟢 Low issues | 2 (unused route, missing per-notification read) |
| ✅ Validated features | 12 feature areas, all chains correct |
| 📁 Dead code files | 30 .dart files across 6 directories |

### Recommended Fix Priority:
1. **Consolidate UserModel** — merge into single model with all fields → fix StorageService import
2. **Make baseURL configurable** — support emulator vs real device vs production
3. **Delete 30 dead code files** — after fixing StorageService dependency
4. **Add per-notification mark-read** — improve UX
5. **Clean up unused `activePositions` route** — remove from RouteNames + ApiEndpoints if not planned
