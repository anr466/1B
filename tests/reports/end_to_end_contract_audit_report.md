# End-to-End Contract Audit Report (Auth + User + Admin)

## Scope
- Flutter app contract path: `screen -> provider -> repository/service -> ApiEndpoints -> backend routes`
- Domains:
  1. Auth/Security
  2. User (portfolio, stats, trades, notifications, settings)
  3. Admin (trading control, users, logs, ML)

## Critical Deviations Found (Expected vs Actual)

### 1) Session restoration could authenticate without canonical user context
- **Expected:** if token/session valid, app restores canonical user object from backend response.
- **Actual:** `checkAuth()` mainly depended on local `storage.userData`; stale/missing data could produce partial authenticated state.
- **Fix:** use `/auth/validate-session` response `user` as source of truth, then sync to storage.
- **File:** `flutter_trading_app/lib/core/providers/auth_provider.dart`

### 2) Pagination query duplication on notifications/trades (root cause)
- **Expected:** single authoritative `page/limit` query sent by repository.
- **Actual:** endpoint builders embedded query defaults, while repositories added queryParameters again (duplicate keys risk wrong page/limit).
- **Fix:** make endpoint builders path-first and append query only when explicitly passed.
- **File:** `flutter_trading_app/lib/core/constants/api_endpoints.dart`

### 3) Push polling notification contract mismatch
- **Expected:** backend contract uses `limit`; response payload nested in `data.notifications`.
- **Actual:** client used `per_page` and read top-level `notifications` only.
- **Fix:** use `limit` and parse nested payload with safe fallback.
- **File:** `flutter_trading_app/lib/core/services/push_notification_service.dart`

### 4) Portfolio growth endpoint mismatch
- **Expected:** growth data from `/user/portfolio-growth/<id>?days=`.
- **Actual:** repository queried `/user/portfolio/<id>` with non-contract `growth=true` params.
- **Fix:** call dedicated `portfolioGrowth` endpoint and map period -> days.
- **File:** `flutter_trading_app/lib/core/repositories/portfolio_repository.dart`

### 5) Admin logs pagination param mismatch
- **Expected:** backend `/admin/activity-logs` accepts `limit`.
- **Actual:** repository sent `per_page`.
- **Fix:** switched to `limit`.
- **File:** `flutter_trading_app/lib/core/repositories/admin_repository.dart`

### 6) Hardcoded hasMore threshold in notifications provider
- **Expected:** use central pagination constant.
- **Actual:** hardcoded `20`.
- **Fix:** use `AppConstants.notificationsPerPage`.
- **File:** `flutter_trading_app/lib/core/providers/notifications_provider.dart`

---

## Verification Evidence

### Static Validation
- `flutter analyze` => **No issues found**.

### Live API Behavioral Checks (server on `127.0.0.1:3002`)

#### Contract checks after fixes
- Login success + token/user extraction ✅
- Notifications pagination contract (`page=2, limit=5`) reflected by backend ✅
- Trades pagination contract (`page=2, limit=7`) reflected in response pagination ✅
- Admin logs contract (`limit=3`) reflected by backend ✅

#### Domain smoke checks
- Auth: validate-session, forgot-password/send OTP paths, verify invalid OTP/error contracts ✅
- User: portfolio/stats/trades/settings/notification-settings contracts ✅
- Admin: trading state/users/activity logs/ml status contracts ✅

All executed checks in this audit session passed:
- Set A: **4/4** passed
- Set B: **11/11** passed
- Set C (auth-flow contracts): **11/11** passed

Total executed checks this session: **26/26 passed**.

---

## Final Status (This Audit Scope)

### ✅ What is now verified working End-to-End
- Auth core and security contract alignment (request/response/error shape) for the covered routes.
- User domain contract alignment for portfolio/stats/trades/notifications/settings.
- Admin domain contract alignment for trading-state/users/logs/ml.
- Fixed mismatches were revalidated behaviorally against live backend.

### ⚠️ Notes
- OTP delivery itself depends on external channels (email/SMS provider availability), but API contract behavior and OTP validation/error paths are verified.

---

## Changed Files in this phase
1. `flutter_trading_app/lib/core/providers/auth_provider.dart`
2. `flutter_trading_app/lib/core/constants/api_endpoints.dart`
3. `flutter_trading_app/lib/core/services/push_notification_service.dart`
4. `flutter_trading_app/lib/core/repositories/portfolio_repository.dart`
5. `flutter_trading_app/lib/core/repositories/admin_repository.dart`
6. `flutter_trading_app/lib/core/providers/notifications_provider.dart`
