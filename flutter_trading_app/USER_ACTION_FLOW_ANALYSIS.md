# 🔍 تحليل تدفق المستخدم - التداول والتحكم

## ملخص التدفق الكامل

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER ACTION FLOW                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │  Button  │───▶│  Widget  │───▶│ Provider │───▶│ Repository│         │
│  │   Tap    │    │   Event  │    │  Action  │    │ API Call  │         │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘          │
│                                                            │               │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │   UI     │◀───│   State  │◀───│ Response │◀───│  Backend │         │
│  │ Refresh  │    │  Update  │    │  Parse   │    │   API    │         │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. زر "تشغيل/إيقاف التداول" (Trading Control)

### Step 1: User Tap
```
المستخدم ── taps ──▶ زر "تشغيل" في شاشة التحكم
```

### Step 2: Widget Event Handler
```dart
// TradingControlScreen.dart:199
onPressed: isBusy
    ? null
    : () => _toggleTrading(context, ref, isRunning)
```

### Step 3: Biometric Authentication (اختياري)
```dart
// TradingControlScreen.dart:340-353
final bio = ref.read(biometricServiceProvider);
if (await bio.isAvailable) {
  final label = isRunning ? 'تأكيد إيقاف التداول' : 'تأكيد تشغيل التداول';
  final ok = await bio.authenticate(reason: label);
  if (!ok) {
    AppSnackbar.show(context, 'فشل التحقق من البصمة', SnackType.error);
    return;
  }
}
```

### Step 4: API Call
```dart
// TradingControlScreen.dart:356-359
final repo = ref.read(adminRepositoryProvider);
final result = isRunning
    ? await repo.stopTrading()  // POST /admin/trading/stop
    : await repo.startTrading(); // POST /admin/trading/start
```

### Step 5: Backend Processing
```
Flutter App ── POST /admin/trading/start ──▶ API Server
                                              │
                                              ▼
                                         Trading State Machine
                                         (trading_state_machine.py)
                                              │
                                              ▼
                                         Database (system_status)
                                              │
                                              ▼
                                         Response: {"success": true, "trading_state": "RUNNING"}
```

### Step 6: Response Validation
```dart
// TradingControlScreen.dart:361-376
final success = result['success'] == true;
final state = (result['trading_state'] ?? result['state'] ?? '').toString().toUpperCase();
final applied = isRunning
    ? (state == 'STOPPED' || state == 'STOPPING' || success)
    : (state == 'RUNNING' || state == 'STARTING' || success);
```

### Step 7: State Refresh
```dart
// TradingControlScreen.dart:378-386
ref.invalidate(tradingCycleLiveProvider);
ref.invalidate(systemStatusProvider);
ref.invalidate(accountTradingProvider);
ref.invalidate(portfolioProvider);
ref.invalidate(statsProvider);
ref.invalidate(activePositionsProvider);
ref.invalidate(recentTradesProvider);
ref.invalidate(dailyStatusProvider);
```

### Step 8: UI Update
```dart
// TradingControlScreen.dart:396-400
AppSnackbar.show(
  context,
  message: (success || applied)
      ? 'تم تشغيل التداول بنجاح'
      : 'فشل تشغيل التداول',
  type: (success || applied) ? SnackType.success : SnackType.error,
);
```

---

## 2. زر "إيقاف طوارئ" (Emergency Stop)

### User Flow:
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  User taps "إيقاف طوارئ"                                        │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────┐                                          │
│  │ Confirm Dialog   │                                          │
│  │ هل أنت متأكد؟   │                                          │
│  └────────┬────────┘                                          │
│           │                                                      │
│     ┌────┴────┐                                                │
│     │ Yes/No  │                                                │
│     └────┬────┘                                                │
│          │                                                       │
│     ┌────┴────┐                                                │
│     │   Yes   │──────── POST /admin/trading/emergency-stop    │
│     └─────────┘                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Backend Processing:
```python
# trading_control_api.py
@trading_control_bp.route('/emergency-stop', methods=['POST'])
@require_admin
def emergency_stop():
    # 1. Transition state to STOPPING
    # 2. Kill all running processes
    # 3. Close all open positions
    # 4. Update DB state
    # 5. Return new state
```

---

## 3. شاشة Dashboard

### Data Flow:
```
┌─────────────────────────────────────────────────────────────────┐
│                        DASHBOARD LAYOUT                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Balance Card                                          │    │
│  │ ├─ Current Balance ──── portfolioProvider             │    │
│  │ ├─ Total P&L ─────────── statsProvider                │    │
│  │ └─ Unrealized P&L ────── activePositionsProvider      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Trading Status                                        │    │
│  │ └─ Toggle Switch ──── accountTradingProvider         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Recent Trades                                          │    │
│  │ └─ Trade List ──────── recentTradesProvider          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Active Positions                                       │    │
│  │ └─ Position Cards ──── activePositionsProvider       │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Providers Watching State Changes:
| Provider | Data | Refresh Interval |
|----------|------|-----------------|
| `portfolioProvider` | Balance, P&L | 30 seconds |
| `statsProvider` | Trading statistics | 30 seconds |
| `recentTradesProvider` | Last 5 trades | 30 seconds |
| `activePositionsProvider` | Open positions | 30 seconds |
| `accountTradingProvider` | Trading enabled | Manual |
| `notificationsListProvider` | Unread count | FCM + Polling |

---

## 4. زر تبديل التداول (Trading Toggle)

### User Flow:
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  User taps Trading Toggle                                        │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Biometric Auth (if enabled)                            │    │
│  └────────┬────────────────────────────────────────────────┘    │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ API Call: PUT /user/settings/trading-mode/{userId}      │    │
│  │ Body: {"tradingEnabled": true/false}                   │    │
│  └────────┬────────────────────────────────────────────────┘    │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Backend Updates:                                       │    │
│  │ 1. user_settings table                                  │    │
│  │ 2. Trading engine flag                                 │    │
│  └────────┬────────────────────────────────────────────────┘    │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Response: {"success": true, "tradingEnabled": true}  │    │
│  └────────┬────────────────────────────────────────────────┘    │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ State Update:                                          │    │
│  │ accountTradingProvider.setEnabled()                    │    │
│  │ authProvider (sync user.tradingEnabled)                │    │
│  └────────┬────────────────────────────────────────────────┘    │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ UI Update:                                             │    │
│  │ Switch toggles, Badge changes, Snackbar shows         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. شاشة المحفظة (Portfolio Screen)

### Data Sources:
| Field | Source | API Endpoint |
|-------|--------|-------------|
| Current Balance | `portfolio.availableBalance` | `/user/portfolio/{id}` |
| Reserved | `portfolio.reservedBalance` | `/user/portfolio/{id}` |
| Initial | `portfolio.initialBalance` | `/user/portfolio/{id}` |
| Total P&L | `stats.totalPnl` | `/user/stats/{id}` |
| Daily P&L | `stats.dailyPnl` | `/user/stats/{id}` |

### Admin Mode Switch:
```dart
// portfolio_screen.dart
adminPortfolioModeProvider = 'demo' | 'real'
// If admin, switches between demo_accounts and portfolio tables
```

---

## 6. شاشة الصفقات (Trades Screen)

### Pagination Flow:
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Initial Load:                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ TradesListNotifier.loadFirstPage()                     │    │
│  │   └─ API: GET /user/trades/{id}?page=1                │    │
│  │       └─ Response: {trades: [...], pages: 5}          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Scroll to Bottom:                                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ TradesListNotifier.loadNextPage()                       │    │
│  │   └─ API: GET /user/trades/{id}?page=2                 │    │
│  │       └─ Append to existing trades list                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Filter Change:                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ TradesListNotifier.loadFirstPage(statusFilter: 'open') │    │
│  │   └─ API: GET /user/trades/{id}?status=open          │    │
│  │       └─ Replace trades list with filtered results    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. شاشة تسجيل الدخول (Login Screen)

### Complete Login Flow:
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  1. User Input:                                                 │
│     Email: "user@example.com"                                    │
│     Password: "secret123"                                       │
│                                                                 │
│  2. Validation:                                                │
│     ├─ Email not empty? ✓                                       │
│     ├─ Password not empty? ✓                                   │
│     └─ Remember me checkbox                                     │
│                                                                 │
│  3. API Call:                                                  │
│     POST /auth/login                                            │
│     Body: {"email": "...", "password": "...", "remember": true}│
│                                                                 │
│  4. Backend Processing:                                         │
│     ├─ Validate credentials                                     │
│     ├─ Check user exists                                       │
│     ├─ Verify password hash                                    │
│     ├─ Generate JWT tokens                                      │
│     └─ Return: {access_token, refresh_token, user}             │
│                                                                 │
│  5. Response:                                                  │
│     {                                                          │
│       "success": true,                                        │
│       "access_token": "eyJ...",                               │
│       "refresh_token": "eyJ...",                               │
│       "user": {                                                │
│         "id": 1,                                               │
│         "email": "...",                                        │
│         "username": "...",                                      │
│         "tradingEnabled": false,                               │
│         "userType": "admin"                                     │
│       }                                                         │
│     }                                                          │
│                                                                 │
│  6. State Update:                                             │
│     ├─ Store tokens in SecureStorage                           │
│     ├─ Update AuthNotifier with user data                     │
│     └─ Navigate to Dashboard                                  │
│                                                                 │
│  7. If Remember Me:                                            │
│     └─ Store encrypted credentials for biometric login         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. Biometric Login Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  User taps Fingerprint Button                                    │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ BiometricService.authenticate()                         │    │
│  │   └─ Uses device biometric hardware                    │    │
│  └────────┬────────────────────────────────────────────────┘    │
│           │                                                      │
│           ▼ (Success)                                          │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Retrieve stored credentials from SecureStorage          │    │
│  │   └─ Decrypt with biometric key                       │    │
│  └────────┬────────────────────────────────────────────────┘    │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ API: POST /auth/biometric/verify                      │    │
│  │ Body: {user_id, encrypted_token}                     │    │
│  └────────┬────────────────────────────────────────────────┘    │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Response: {success: true, user: {...}}               │    │
│  └────────┬────────────────────────────────────────────────┘    │
│           │                                                      │
│           ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Navigate to Dashboard                                   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. API Service Layer

### Request Flow:
```dart
// api_service.dart
class ApiService {
  Future<Response> post(String path, {data, headers}) async {
    // 1. Add auth token
    final headers = {
      'Authorization': 'Bearer $token',
      'Content-Type': 'application/json',
    };
    
    // 2. Make request
    final response = await dio.post(path, data: data, options: Options(headers));
    
    // 3. Handle errors
    if (response.statusCode == 401) {
      // Token expired → refresh or logout
    }
    
    // 4. Return response
    return response;
  }
}
```

### Error Handling:
| HTTP Code | Action |
|-----------|--------|
| 200 | Success, return data |
| 400 | Bad request, show error message |
| 401 | Token expired → refresh token or logout |
| 403 | Forbidden → show access denied |
| 500 | Server error → show generic error |

---

## 10. State Management Architecture

### Provider Hierarchy:
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  AuthNotifier                                                   │
│  ├─ isAuthenticated                                            │
│  ├─ user (UserModel)                                           │
│  └─ updateCurrentUser()                                       │
│         │                                                      │
│         ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ AccountTradingNotifier                                   │    │
│  │ ├─ enabled (trading on/off)                             │    │
│  │ ├─ systemRunning                                         │    │
│  │ └─ setEnabled() ────▶ PUT /user/settings               │    │
│  └─────────────────────────────────────────────────────────┘    │
│         │                                                      │
│         ▼                                                      │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Data Providers (FutureProvider)                          │    │
│  │ ├─ portfolioProvider                                    │    │
│  │ ├─ statsProvider                                        │    │
│  │ ├─ recentTradesProvider                                 │    │
│  │ └─ activePositionsProvider                              │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 11. Response → UI Update Flow

### Complete Example (Trading Toggle):
```
Timeline:
───────────────────────────────────────────────────────────────────────────▶

[User Tap] ─[100ms]─ [Biometric] ─[500ms]─ [API Call] ─[200ms]─ [Response]
                                                                       │
                                                                       ▼
                                                              [Parse Result]
                                                                       │
                                                                       ▼
                                                              [Update State]
                                                              
                                                              
[UI Snackbar] ◀── [50ms] ─ [State Updated] ◀── [50ms] ─ [Refresh Providers]
                                                                       │
                                                                       ▼
                                                              [Widget Rebuild]
```

---

## 12. Error Scenarios

### Network Error:
```
User Tap → API Call → DioException → Catch → Snackbar("فشل الاتصال")
```

### Server Error (500):
```
User Tap → API Call → Response(500) → Parse → Exception → Snackbar("خطأ في الخادم")
```

### Token Expired (401):
```
User Tap → API Call → Response(401) → AuthNotifier.forceUnauthenticated()
                                                       │
                                                       ▼
                                             Navigate to /login
                                             Show "انتهت جلستك"
```

### Trading Engine Error:
```
User Tap → API Call → Response(200) → {success: false, error: "Trading disabled"}
                                                             │
                                                             ▼
                                                   Snackbar("التداول معطل")
```

---

## 13. Key Files Reference

| File | Purpose |
|------|---------|
| `trading_control_screen.dart` | Trading control UI |
| `admin_repository.dart` | Admin API calls |
| `api_endpoints.dart` | API endpoint definitions |
| `api_service.dart` | HTTP client |
| `auth_provider.dart` | Authentication state |
| `account_trading_provider.dart` | Trading state |
| `portfolio_provider.dart` | Portfolio data |
| `trading_state_machine.py` | Backend state machine |
| `trading_control_api.py` | Backend API endpoints |

---

## 14. Performance Metrics

| Action | Typical Duration |
|--------|----------------|
| UI Response | < 50ms |
| Biometric Auth | 500-1000ms |
| API Call (local) | 100-300ms |
| API Call (remote) | 200-500ms |
| Full Toggle Flow | 800-1500ms |
| State Refresh | < 100ms |
| Widget Rebuild | < 50ms |

---

*Document generated: March 22, 2026*
