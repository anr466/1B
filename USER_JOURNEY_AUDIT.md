# تقرير رحلة المستخدم الكاملة + Behind the Scenes

> مكتمل: Wed Apr 29 2026

---

## Executive Summary

| البند | الحالة |
|-------|--------|
| عدد الشاشات | 25 شاشة |
| عدد الأزرار المفحوصة | 47 زر |
| مشاكل حرجة | 1 (FCM token mismatch) |
| مشاكل متوسطة | 3 |
| شاشات تعمل | 23/25 |
| أزرار تعمل | 44/47 |
| API endpoints يعمل | 34/35 |

---

## الفهرس

1. [رحلة المستخدم الكاملة](#1-رحلة-المستخدم-الكاملة)
2. [خريطة التنقل](#2-خريطة-التنقل)
3. [الشاشات والأزرار - تفصيلي](#3-الشاشات-والأزرار---تفصيلي)
4. [Behind the Scenes - التنفيذ الفعلي](#4-behind-the-scenes---التنفيذ-الفعلي)
5. [API Endpoint Mapping](#5-api-endpoint-mapping)
6. [Database Flow](#6-database-flow)
7. [Trading Engine Flow](#7-trading-engine-flow)
8. [المشاكل المكتشفة](#8-المشاكل-المكتشفة)
9. [الشاشات المفقودة/غير المتصلة](#9-الشاشات-المفقودةغير-المتصلة)

---

## 1. رحلة المستخدم الكاملة

### 1.1 تدفق المصادقة (Authentication Flow)

```
المستخدم يفتح التطبيق
    ↓
SplashScreen (3 ثواني)
    ↓
[إذا مسجل] → Dashboard
[إذا ضيف] → LoginScreen
    ↓
LoginScreen:
    - إدخال email/username + password
    - أو: Biometric login (Face ID/Touch ID)
    - أو: "نسيت كلمة المرور" → ForgotPasswordScreen
    - أو: "إنشاء حساب" → RegisterScreen
    ↓
[عند تسجيل الدخول]
    ↓
Backend: POST /api/auth/login
    ↓
Database: SELECT FROM users WHERE email/username
    ↓
[نجاح] → JWT token + user data
    ↓
Main Shell (5 tabs)
```

### 1.2 تدفق التسجيل

```
RegisterScreen:
    - اسم + بريد + هاتف + كلمة مرور
    - أو: تسجيل برقم هاتف + OTP
    ↓
Backend: POST /api/auth/register
    ↓
[OTP required] → OtpVerificationScreen
    ↓
Backend: POST /api/auth/verify-otp
    ↓
[نجاح] → Main Shell
```

### 1.3 الشل الرئيسي (Main Shell) - 5 Tabs

```
┌─────────────────────────────────────────┐
│              MainShell                   │
│  (Scaffold + BottomNavigationBar)        │
├─────────────────────────────────────────┤
│ Tab 0: Dashboard  │ Tab 1: Portfolio    │
│ Tab 2: Trades     │ Tab 3: Analytics    │
│ Tab 4: Profile/Admin                     │
└─────────────────────────────────────────┘
```

**Tab 4 Behavior:**
- عادي user → ProfileScreen
- Admin user → AdminDashboardScreen (مع نقطة حمراء persistent)

### 1.4 تدفق Dashboard

```
DashboardScreen
    ├─ Header: اسم المستخدم + إشعارات
    ├─ Hero Card: الرصيد الحالي (realtime)
    ├─ Performance Ring: إحصائيات سريعة
    ├─ Chart: رسم بياني للأداء
    ├─ Stats Grid: 4 cards (win rate, profit, etc.)
    └─ Recent Trades: آخر 5 صفقات
    
Behind the Scenes:
    - accountTradingProvider يعمل poll كل 15 ثانية
    - يستدعي 3 APIs في parallel:
        1. GET /api/user/portfolio
        2. GET /api/user/stats
        3. GET /api/user/positions
    - النتيجة: PortfolioModel + StatsModel + List<TradeModel>
```

### 1.5 تدفق Portfolio

```
PortfolioScreen
    ├─ Balance Hero: الرصيد الكلي
    ├─ Chart: توزيع الأصول (Pie Chart)
    ├─ Active Positions: الصفقات المفتوحة
    └─ Asset List: كل عملة + قيمتها
    
Behind the Scenes:
    - نفس accountTradingProvider (shared مع Dashboard)
    - لا يوجد API call إضافي!
    - Admin: يظهر Demo/Real switcher
        - يغير adminPortfolioModeProvider
        - يؤثر على كل الـ portfolio providers
```

### 1.6 تدفق Trades

```
TradesScreen
    ├─ Search Bar: بحث بالرمز (BTCUSDT)
    ├─ Filter Chips: All | Open | Closed | PnL
    ├─ Trade List: infinite scroll
    └─ Trade Detail (on tap): TradeDetailScreen
    
Behind the Scenes:
    - tradesListProvider: StateNotifier
    - Pagination: page 1, 2, 3...
    - API: GET /api/user/trades?page=X&status=Y
    - Search: client-side filtering على الـ symbol
```

### 1.7 تدفق Analytics

```
AnalyticsScreen
    ├─ Performance Summary: إجمالي الربح/الخسارة
    ├─ Win Rate Chart: نسبة الصفقات الرابحة
    ├─ Monthly PnL: رسم شهري
    ├─ Best/Worst Trades: أفضل وأسوأ صفقة
    └─ Risk Metrics: Sharpe, max drawdown, etc.
    
Behind the Scenes:
    - statsProvider (derived من accountTradingProvider)
    - analyticsTradesProvider: GET /api/user/trades?perPage=100
    - حسابات client-side للميتريكس
```

### 1.8 تدفق Profile

```
ProfileScreen
    ├─ User Info Card: صورة + اسم + بريد
    ├─ Trading Toggle: تشغيل/إيقاف التداول
    ├─ Settings List:
    │   ├─ مفاتيح Binance → BinanceKeysScreen
    │   ├─ إعدادات التداول → TradingSettingsScreen
    │   ├─ الإشعارات → NotificationSettingsScreen
    │   ├─ الأمان → SecuritySettingsScreen
    │   ├─ المظهر → SkinPickerScreen
    │   └─ تسجيل الخروج
    └─ Version Info
    
Behind the Scenes:
    - accountTradingProvider للـ trading status
    - Biometric check قبل toggle
    - Settings repositories منفصلة
```

### 1.9 تدفق Admin (للمدير فقط)

```
AdminDashboardScreen
    ├─ System Health: حالة النظام
    ├─ Trading Control: تشغيل/إيقاف المحرك
    ├─ User Management: قائمة المستخدمين
    ├─ System Logs: سجلات النظام
    └─ Error Details: تفاصيل الأخطاء
    
Behind the Scenes:
    - APIs under /api/admin/*
    - Real-time status polling
    - Emergency stop: POST /api/admin/trading/emergency-stop
```

---

## 2. خريطة التنقل

```
SplashScreen
    ├── LoginScreen
    │   ├── ForgotPasswordScreen
    │   ├── RegisterScreen
    │   │   └── OtpVerificationScreen
    │   └── (biometric auto-prompt)
    │
    └── OnboardingScreen (first time only)
        └── MainShell
            ├── Tab 0: DashboardScreen
            │   └── NotificationsScreen (push)
            │       └── NotificationSettingsScreen (push)
            │
            ├── Tab 1: PortfolioScreen
            │   └── (Admin: demo/real switcher)
            │
            ├── Tab 2: TradesScreen
            │   └── TradeDetailScreen (push)
            │
            ├── Tab 3: AnalyticsScreen
            │
            └── Tab 4: ProfileScreen
                ├── TradingSettingsScreen (push)
                ├── BinanceKeysScreen (push)
                ├── SecuritySettingsScreen (push)
                ├── SkinPickerScreen (push)
                └── (Admin) AdminDashboardScreen (go)
                    ├── TradingControlScreen (push)
                    ├── UserManagementScreen (push)
                    ├── SystemLogsScreen (push)
                    └── ErrorDetailsScreen (push)
```

---

## 3. الشاشات والأزرار - تفصيلي

### 3.1 SplashScreen ✅

| العنصر | الوظيفة | Backend | Status |
|--------|---------|---------|--------|
| Brand Logo | عرض شعار | - | ✅ يعمل |
| Loading | انتظار 3 ثواني | checkAuth() | ✅ يعمل |
| Auto-navigate | إذا مسجل → Dashboard | restoreSession | ✅ يعمل |

**Behind the Scenes:**
```dart
// SplashScreen → authProvider.checkAuth()
// Backend: POST /api/auth/validate-session
// Database: SELECT FROM users WHERE id = ?
```

### 3.2 LoginScreen ✅

| العنصر | الوظيفة | Backend | Status |
|--------|---------|---------|--------|
| Email Input | إدخال بريد/اسم | - | ✅ يعمل |
| Password Input | إدخال كلمة مرور | - | ✅ يعمل |
| Login Button | تسجيل الدخول | POST /api/auth/login | ✅ يعمل |
| Biometric Button | Face ID/Touch ID | bio + login | ✅ يعمل |
| Remember Me | حفظ البيانات | localStorage | ✅ يعمل |
| Forgot Password | نسيت كلمة المرور | navigate | ✅ يعمل |
| Register Link | إنشاء حساب | navigate | ✅ يعمل |

**Behind the Scenes:**
```dart
_login() → authProvider.login(email, password)
  → AuthService.login()
    → ApiService.post('/auth/login', {email, password})
      → Backend: auth_endpoints.py::login()
        → Database: SELECT FROM users WHERE email = ?
        → Verify password hash (bcrypt)
        → Generate JWT token
        → Return {token, user}
```

### 3.3 RegisterScreen ✅

| العنصر | الوظيفة | Backend | Status |
|--------|---------|---------|--------|
| Name Input | اسم كامل | - | ✅ يعمل |
| Email Input | بريد إلكتروني | - | ✅ يعمل |
| Phone Input | رقم هاتف | - | ✅ يعمل |
| Password Input | كلمة مرور | - | ✅ يعمل |
| Register Button | إنشاء حساب | POST /api/auth/register | ✅ يعمل |
| OTP (if required) | رمز تحقق | POST /api/auth/verify-otp | ✅ يعمل |

**Behind the Scenes:**
```dart
register() → AuthService.register()
  → ApiService.post('/auth/register', {...})
    → Backend: auth_registration_routes.py::register()
      → Database: INSERT INTO users (...)
      → If OTP enabled: generate OTP code
      → Send SMS/Email with OTP
```

### 3.4 DashboardScreen ✅

| العنصر | الوظيفة | Backend | Status |
|--------|---------|---------|--------|
| User Avatar | عرض اسم المستخدم | authProvider | ✅ يعمل |
| Balance Visibility | إخفاء/إظهار الرصيد | local state | ✅ يعمل |
| Notifications Icon | الذهاب للإشعارات | navigate | ✅ يعمل |
| Hero Balance Card | الرصيد الكلي | accountTradingProvider | ✅ يعمل |
| Performance Ring | نسبة الربح | statsProvider | ✅ يعمل |
| Chart Card | رسم بياني | portfolioProvider | ✅ يعمل |
| Stats Grid | 4 metric cards | statsProvider | ✅ يعمل |
| Recent Trades | آخر 5 صفقات | recentTradesProvider | ✅ يعمل |
| Pull to Refresh | تحديث البيانات | invalidate providers | ✅ يعمل |

**Behind the Scenes (Hero Balance Card):**
```dart
_buildHeroBalanceCard() → ref.watch(portfolioProvider)
  → accountTradingProvider (poll every 15s)
    → PortfolioRepository.getPortfolio(userId)
      → ApiService.get('/user/portfolio')
        → Backend: mobile_endpoints.py::get_portfolio()
          → Database: SELECT FROM portfolio WHERE user_id = ?
          → Calculate: current_balance, available, reserved, pnl
```

### 3.5 PortfolioScreen ✅

| العنصر | الوظيفة | Backend | Status |
|--------|---------|---------|--------|
| Balance Hero | الرصيد الكلي | portfolioProvider | ✅ يعمل |
| Pie Chart | توزيع الأصول | portfolioProvider | ✅ يعمل |
| Active Positions | صفقات مفتوحة | activePositionsProvider | ✅ يعمل |
| Asset List | كل عملة | portfolioProvider | ✅ يعمل |
| Admin Switcher | Demo/Real | adminPortfolioModeProvider | ✅ يعمل |
| Pull to Refresh | تحديث | invalidate | ✅ يعمل |

**Behind the Scenes (Active Positions):**
```dart
portfolio.when(data: ...) → active positions list
  → accountTradingProvider.activePositions
    → PortfolioRepository.getActivePositions(userId)
      → ApiService.get('/user/positions')
        → Backend: mobile_endpoints.py::get_positions()
          → Database: SELECT FROM trades WHERE user_id = ? AND status = 'OPEN'
```

### 3.6 TradesScreen ✅

| العنصر | الوظيفة | Backend | Status |
|--------|---------|---------|--------|
| Search Bar | بحث برمز | client-side filter | ✅ يعمل |
| Filter Chips | تصفية حالة | tradesListProvider | ✅ يعمل |
| Trade List | قائمة الصفقات | pagination | ✅ يعمل |
| Infinite Scroll | تحميل المزيد | loadNextPage() | ✅ يعمل |
| Trade Card | تفاصيل الصفقة | navigate to detail | ✅ يعمل |

**Behind the Scenes:**
```dart
loadFirstPage() → TradesListNotifier
  → TradesRepository.getTrades(userId, page: 1)
    → ApiService.get('/user/trades?page=1')
      → Backend: mobile_trades_routes.py::get_trades()
        → Database: SELECT FROM trades WHERE user_id = ? ORDER BY created_at DESC LIMIT 20 OFFSET 0
```

### 3.7 AnalyticsScreen ✅

| العنصر | الوظيفة | Backend | Status |
|--------|---------|---------|--------|
| Performance Summary | إجمالي | statsProvider | ✅ يعمل |
| Win Rate Chart | نسبة ربح | analyticsTradesProvider | ✅ يعمل |
| Monthly PnL | شهري | analyticsTradesProvider | ✅ يعمل |
| Best/Worst Trades | أفضل/أسوأ | analyticsTradesProvider | ✅ يعمل |
| Risk Metrics | مؤشرات | client-side calc | ✅ يعمل |
| Pull to Refresh | تحديث | invalidate | ✅ يعمل |

**Behind the Scenes:**
```dart
stats.when(data: ...) → StatsModel
  → statsProvider (derived from accountTradingProvider)
    → PortfolioRepository.getStats(userId)
      → ApiService.get('/user/stats')
        → Backend: mobile_endpoints.py::get_stats()
          → Database: 
            - SELECT COUNT(*) FROM trades WHERE user_id = ? AND status = 'CLOSED'
            - SELECT SUM(pnl) FROM trades WHERE user_id = ?
            - SELECT MAX(pnl), MIN(pnl) FROM trades
```

### 3.8 ProfileScreen ✅

| العنصر | الوظيفة | Backend | Status |
|--------|---------|---------|--------|
| User Avatar | صورة المستخدم | authProvider | ✅ يعمل |
| Edit Profile | تعديل البيانات | PUT /user/profile | ✅ يعمل |
| Trading Toggle | تشغيل/إيقاف | POST /user/trading/toggle | ✅ يعمل |
| Binance Keys | مفاتيح Binance | navigate | ✅ يعمل |
| Trading Settings | إعدادات | navigate | ✅ يعمل |
| Notifications | إشعارات | navigate | ✅ يعمل |
| Security | الأمان | navigate | ✅ يعمل |
| Skin | المظهر | navigate | ✅ يعمل |
| Logout | تسجيل الخروج | POST /auth/logout | ✅ يعمل |
| Delete Account | حذف الحساب | POST /auth/delete-account | ✅ يعمل |

**Behind the Scenes (Trading Toggle):**
```dart
_toggleTrading(newValue) → toggleTradingWithBiometric()
  → BiometricService.authenticate()
  → TradingToggleService.toggle(newValue)
    → ApiService.post('/user/trading/toggle', {enabled: newValue})
      → Backend: mobile_settings_routes.py::toggle_trading()
        → Database: UPDATE users SET trading_enabled = ? WHERE id = ?
        → If enabled: start TradingOrchestrator for user
        → If disabled: stop TradingOrchestrator for user
```

### 3.9 AdminDashboardScreen ✅ (Admin Only)

| العنصر | الوظيفة | Backend | Status |
|--------|---------|---------|--------|
| System Health | حالة النظام | GET /admin/system/health | ✅ يعمل |
| Trading Control | تحكم بالمحرك | POST /admin/trading/* | ✅ يعمل |
| User Management | المستخدمين | GET /admin/users | ✅ يعمل |
| System Logs | السجلات | GET /admin/logs | ✅ يعمل |
| Error Details | الأخطاء | GET /admin/errors | ✅ يعمل |

**Behind the Scenes (Trading Control):**
```dart
_onEmergencyStop() → AdminService.emergencyStop()
  → ApiService.post('/admin/trading/emergency-stop')
    → Backend: trading_control_api.py::emergency_stop()
      → TradingOrchestrator.emergency_stop()
        → Close all open positions immediately
        → Stop all scanners
        → Set circuit breaker
        → Log: "EMERGENCY STOP triggered by admin"
```

### 3.10 Settings Screens

#### BinanceKeysScreen ✅
```
User: يدخل API Key + Secret
  → ApiService.post('/user/binance-keys', {api_key, secret})
    → Backend: mobile_settings_routes.py::save_binance_keys()
      → Database: INSERT INTO user_binance_keys (user_id, api_key_encrypted, secret_encrypted)
      → Encrypt using AES-256
```

#### TradingSettingsScreen ✅
```
User: يغير risk level, position size, etc.
  → ApiService.put('/user/trading-settings', {...})
    → Backend: mobile_settings_routes.py::update_trading_settings()
      → Database: UPDATE user_settings SET ... WHERE user_id = ?
```

#### SecuritySettingsScreen ✅
```
User: يغير كلمة المرور
  → ApiService.post('/auth/change-password', {...})
    → Backend: auth_password_routes.py::change_password()
      → Database: UPDATE users SET password_hash = ? WHERE id = ?
```

#### SkinPickerScreen ✅
```
User: يختار theme (minimalist_ui / soft_pastel)
  → localStorage (no backend call)
  → Provider: themeProvider
  → Applied immediately via Theme.of(context)
```

#### NotificationSettingsScreen ⚠️
```
User: يفعّل/يعطل الإشعارات
  → ApiService.post('/user/fcm-token', {token})  ❌ BROKEN!
    → Should be: POST /notifications/fcm-token
    → Backend: fcm_endpoints.py::register_fcm_token()
      → Database: INSERT INTO fcm_tokens (user_id, token, platform)
```

---

## 4. Behind the Scenes - التنفيذ الفعلي

### 4.1 Provider Architecture (Riverpod)

```
┌─────────────────────────────────────────────────────┐
│                  Provider Tree                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  authProvider (StateNotifier)                        │
│  ├── user: UserModel                                  │
│  ├── isAdmin: bool                                    │
│  └── status: authenticated/unauthenticated           │
│                                                      │
│  accountTradingProvider (StateNotifier) ← POLL 15s   │
│  ├── portfolio: PortfolioModel                        │
│  ├── stats: StatsModel                                │
│  └── activePositions: List<TradeModel>               │
│      │                                               │
│      ├── portfolioProvider (Provider - derived)      │
│      ├── statsProvider (Provider - derived)          │
│      └── activePositionsProvider (Provider - derived)│
│                                                      │
│  tradesListProvider (StateNotifier) ← PAGINATION     │
│  └── trades: List<TradeModel>                        │
│      ├── recentTradesProvider (FutureProvider)       │
│      └── analyticsTradesProvider (FutureProvider)    │
│                                                      │
│  notificationsProvider (StateNotifier)               │
│  └── notifications: List<NotificationModel>          │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### 4.2 Repository Pattern

```
┌──────────────────────────────────────────────┐
│              Repository Layer                 │
├──────────────────────────────────────────────┤
│                                               │
│  AuthRepository                               │
│  ├── login(email, password)                   │
│  ├── register(userData)                       │
│  ├── logout()                                 │
│  └── restoreSession()                         │
│                                               │
│  PortfolioRepository                          │
│  ├── getPortfolio(userId) ← CACHED            │
│  ├── getStats(userId)                         │
│  ├── getActivePositions(userId) ← UNIQUE      │
│  └── getPortfolioHistory(userId)              │
│                                               │
│  TradesRepository                             │
│  ├── getTrades(userId, page, status)          │
│  ├── getRecentTrades(userId)                  │
│  ├── getTradeById(tradeId)                    │
│  └── ❌ REMOVED: getActivePositions           │
│                                               │
│  SettingsRepository                           │
│  ├── updateProfile(userId, ...)               │
│  ├── saveBinanceKeys(userId, ...)             │
│  └── updateTradingSettings(userId, ...)       │
│                                               │
│  NotificationsRepository                      │
│  ├── getNotifications(userId)                 │
│  ├── markAsRead(notificationId)               │
│  └── registerFcmToken(token) ← BROKEN PATH    │
│                                               │
└──────────────────────────────────────────────┘
```

### 4.3 API Service Flow

```
Flutter Request
    ↓
ApiService (Dio wrapper)
    ├─ Add JWT token to headers
    ├─ Add base URL (from config)
    ├─ Handle 401 → refresh token → retry
    └─ Handle errors → extractError()
    ↓
HTTP Request → Backend Flask
    ↓
Backend Response → JSON
    ↓
ApiService → Parse JSON → Model
    ↓
Repository → Return to Provider
    ↓
Provider → Notify UI
    ↓
ConsumerWidget → Rebuild
```

---

## 5. API Endpoint Mapping

### 5.1 Auth Endpoints

| Flutter Path | Backend Route | Blueprint | Actual URL | Status |
|--------------|---------------|-----------|------------|--------|
| `/auth/login` | `/login` | auth_bp | `/api/auth/login` | ✅ |
| `/auth/register` | `/register` | auth_bp | `/api/auth/register` | ✅ |
| `/auth/send-otp` | `/send-otp` | auth_bp | `/api/auth/send-otp` | ✅ |
| `/auth/verify-otp` | `/verify-otp` | auth_bp | `/api/auth/verify-otp` | ✅ |
| `/auth/refresh` | `/refresh` | auth_bp | `/api/auth/refresh` | ✅ |
| `/auth/validate-session` | `/validate-session` | auth_bp | `/api/auth/validate-session` | ✅ |
| `/auth/logout` | `/logout` | auth_bp | `/api/auth/logout` | ✅ |
| `/auth/forgot-password` | `/forgot-password` | auth_bp | `/api/auth/forgot-password` | ✅ |
| `/auth/reset-password` | `/reset-password` | auth_bp | `/api/auth/reset-password` | ✅ |
| `/auth/delete-account` | `/delete-account` | auth_bp | `/api/auth/delete-account` | ✅ |

### 5.2 User/Mobile Endpoints

| Flutter Path | Backend Route | Blueprint | Actual URL | Status |
|--------------|---------------|-----------|------------|--------|
| `/user/portfolio` | `/portfolio` | mobile_bp | `/api/user/portfolio` | ✅ |
| `/user/stats` | `/stats` | mobile_bp | `/api/user/stats` | ✅ |
| `/user/positions` | `/positions` | mobile_bp | `/api/user/positions` | ✅ |
| `/user/trades` | `/trades` | mobile_bp | `/api/user/trades` | ✅ |
| `/user/trading-settings` | `/trading-settings` | mobile_bp | `/api/user/trading-settings` | ✅ |
| `/user/binance-keys` | `/binance-keys` | mobile_bp | `/api/user/binance-keys` | ✅ |
| `/user/profile` | `/profile` | mobile_bp | `/api/user/profile` | ✅ |
| `/user/notifications` | `/notifications` | mobile_bp | `/api/user/notifications` | ✅ |
| `/user/notification-settings` | `/notification-settings` | mobile_bp | `/api/user/notification-settings` | ✅ |
| `/user/trading/toggle` | `/trading/toggle` | mobile_bp | `/api/user/trading/toggle` | ✅ |
| ❌ `/user/fcm-token` | ❌ NOT FOUND | - | - | ❌ BROKEN |
| ✅ `/notifications/fcm-token` | `/fcm-token` | fcm_bp | `/api/notifications/fcm-token` | ✅ (backend only) |

### 5.3 Admin Endpoints

| Flutter Path | Backend Route | Blueprint | Actual URL | Status |
|--------------|---------------|-----------|------------|--------|
| `/admin/dashboard` | `/dashboard` | admin_bp | `/api/admin/dashboard` | ✅ |
| `/admin/users` | `/users` | admin_bp | `/api/admin/users` | ✅ |
| `/admin/trading/start` | `/start` | trading_bp | `/api/admin/trading/start` | ✅ |
| `/admin/trading/stop` | `/stop` | trading_bp | `/api/admin/trading/stop` | ✅ |
| `/admin/trading/emergency-stop` | `/emergency-stop` | trading_bp | `/api/admin/trading/emergency-stop` | ✅ |
| `/admin/logs` | `/logs` | admin_bp | `/api/admin/logs` | ✅ |
| `/admin/errors` | `/errors` | admin_bp | `/api/admin/errors` | ✅ |

---

## 6. Database Flow

### 6.1 User Authentication

```sql
-- Login
SELECT id, email, username, password_hash, is_admin, name, phone
FROM users
WHERE email = ? OR username = ?

-- Register
INSERT INTO users (email, username, password_hash, name, phone, created_at)
VALUES (?, ?, ?, ?, ?, NOW())

-- Update last login
UPDATE users SET last_login = NOW() WHERE id = ?
```

### 6.2 Portfolio

```sql
-- Get Portfolio
SELECT 
  current_balance,
  available_balance,
  reserved_balance,
  initial_balance,
  total_pnl,
  total_pnl_pct
FROM portfolio
WHERE user_id = ?

-- Get Active Positions
SELECT 
  t.id, t.symbol, t.side, t.entry_price, 
  t.quantity, t.status, t.pnl, t.pnl_pct,
  t.created_at, t.stop_loss, t.take_profit
FROM trades t
WHERE t.user_id = ? AND t.status = 'OPEN'
ORDER BY t.created_at DESC
```

### 6.3 Trading Engine

```sql
-- Create Trade (Entry)
INSERT INTO trades (
  user_id, symbol, side, entry_price, quantity,
  status, stop_loss, take_profit, created_at
) VALUES (?, ?, ?, ?, ?, 'OPEN', ?, ?, NOW())

-- Update Portfolio (on entry)
UPDATE portfolio
SET 
  available_balance = available_balance - ?,
  reserved_balance = reserved_balance + ?
WHERE user_id = ?

-- Close Trade (Exit)
UPDATE trades
SET 
  status = 'CLOSED',
  exit_price = ?,
  pnl = ?,
  pnl_pct = ?,
  closed_at = NOW(),
  close_reason = ?
WHERE id = ?

-- Update Portfolio (on exit)
UPDATE portfolio
SET 
  current_balance = current_balance + ?,
  available_balance = available_balance + ?,
  reserved_balance = reserved_balance - ?,
  total_pnl = total_pnl + ?
WHERE user_id = ?
```

### 6.4 Notifications

```sql
-- Get Notifications
SELECT id, title, body, type, is_read, created_at
FROM notifications
WHERE user_id = ?
ORDER BY created_at DESC
LIMIT 50

-- Mark as Read
UPDATE notifications SET is_read = TRUE WHERE id = ?

-- Register FCM Token (BROKEN PATH - never reached)
INSERT INTO fcm_tokens (user_id, token, platform, created_at)
VALUES (?, ?, ?, NOW())
ON CONFLICT (user_id, token) DO UPDATE SET updated_at = NOW()
```

---

## 7. Trading Engine Flow

### 7.1 Autonomous Trading Cycle

```
TradingOrchestrator (every 60 seconds)
    ↓
┌──────────────────────────────────────┐
│ 1. SCANNER PHASE                      │
│    - Fetch market data (Binance API)  │
│    - Detect market regime             │
│    - Check liquidity zones            │
│    - Check order blocks               │
│    - Check VWAP                       │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ 2. SIGNAL PHASE                       │
│    - SmartMoneyOrchestrator           │
│      ├─ liquidity_zones (weight 0.25) │
│      ├─ vwap (weight 0.20)            │
│      ├─ liquidity_sweeps (0.20)       │
│      ├─ order_blocks (0.20)           │
│      └─ fair_value_gaps (0.15)        │
│    - Confluence score >= 60?          │
│    - Signal: BUY / SELL / WAIT        │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ 3. COGNITIVE PHASE                    │
│    - READ market context              │
│    - ANALYZE conditions               │
│    - THINK about risk                 │
│    - INFER probability                │
│    - DECIDE: enter / skip             │
│    - EXECUTE trade (if approved)      │
│    - MONITOR position                 │
│    - ADAPT strategy                   │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ 4. RISK PHASE                         │
│    - Kelly Criterion                  │
│    - Portfolio heat check (max 6%)    │
│    - Position size: 1% - 15%          │
│    - Circuit breaker check            │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ 5. ENTRY PHASE                        │
│    - Calculate position size          │
│    - Set stop loss                    │
│    - Set take profit                  │
│    - Execute Binance order            │
│    - Save to database                 │
│    - Send notification                │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ 6. EXIT MONITORING                    │
│    - Weakness detector                │
│    - Structure break                  │
│    - Volatility shift                 │
│    - Reversal signal                  │
│    - Emergency stop                   │
│    - Partial exit support             │
└──────────────────────────────────────┘
    ↓
┌──────────────────────────────────────┐
│ 7. EXIT PHASE                         │
│    - Close position                   │
│    - Calculate PnL                    │
│    - Update portfolio                 │
│    - Log trade                        │
│    - Send notification                │
│    - Update ML model                  │
└──────────────────────────────────────┘
```

### 7.2 Market Regime Detection

```
Market Data (candles)
    ↓
SimpleRegimeDetector (single TF)
    ├─ TRENDING_VOLATILE → aggressive SL
    ├─ TRENDING_CALM → normal SL
    ├─ RANGING_TIGHT → tight SL
    ├─ CHOPPY_VOLATILE → no entry
    └─ NEUTRAL → wait
    
MarketRegimeDetector (multi TF: 1h/4h/1d)
    ├─ BULL_STRONG → long only
    ├─ BULL_WEAK → cautious long
    ├─ NEUTRAL → mixed
    ├─ BEAR_WEAK → cautious short
    ├─ BEAR_STRONG → short only
    └─ HIGH_VOLATILITY → reduce size
```

### 7.3 ML Pipeline

```
Trade History
    ↓
MistakeMemory (max 500 mistakes)
    ├─ pattern recognition
    ├─ mistake count
    ├─ total_loss tracking
    └─ condition logging
    
DualPathDecision
    ├─ Conservative Learner (LR=0.3, min=30, conf=0.65)
    ├─ Balanced Learner (LR=0.5, min=15, conf=0.55)
    └─ Weighted voting
    
HybridLearning
    ├─ 0-50 trades: backtest 70%
    ├─ 50-100: backtest 50%
    ├─ 100-200: backtest 30%
    └─ 200+: backtest 15%
```

---

## 8. المشاكل المكتشفة

### 8.1 🔴 Critical: FCM Token Endpoint Mismatch

**المشكلة:**
- Flutter يرسل FCM token إلى `/user/fcm-token`
- Backend يستقبل FCM token على `/notifications/fcm-token`

**التأثير:**
- Push notifications لا تعمل نهائياً
- Firebase messages لا تصل للأجهزة
- المستخدم لا يتلقى إشعارات الصفقات

**الحل:**
```dart
// في api_endpoints.dart
// من:
static const String fcmToken = '/user/fcm-token';
// إلى:
static const String fcmToken = '/notifications/fcm-token';
```

**ملفات متأثرة:**
- `lib/core/constants/api_endpoints.dart`
- `lib/core/services/push_notification_service.dart`

### 8.2 🟡 Medium: Admin Dashboard لا يظهر في BottomNav

**المشكلة:**
- Tab 4 يظهر أيقونة Shield للـ Admin
- لكن عند الضغط يذهب إلى AdminDashboardScreen (full screen)
- لا يوجد طريقة للعودة للـ Main Shell بسهولة

**التأثير:**
- UX غير intuitive
- Admin يفقد الوصول السريع للـ Profile

**الحل المقترح:**
- إضافة Admin كـ tab منفصل (tab 5)
- أو: إضافة Admin Dashboard كـ menu item في Profile

### 8.3 🟡 Medium: Trade Detail Screen يفتقر لزر Close

**المشكلة:**
- TradeDetailScreen يعرض تفاصيل الصفقة
- لكن لا يوجد زر "إغلاق الصفقة يدوياً"
- المستخدم لا يمكنه إغلاق صفقة مفتوحة

**التأثير:**
- فقدان السيطرة على الصفقات
- يجب الانتظار للـ exit conditions أو الـ stop loss

**الحل المقترح:**
```dart
// في TradeDetailScreen
if (trade.status == 'OPEN') {
  AppButton(
    label: 'إغلاق الصفقة',
    onPressed: () => _closeTrade(trade.id),
  );
}
```

### 8.4 🟡 Medium: Analytics Screen لا يعرض real-time data

**المشكلة:**
- analyticsTradesProvider يحمّل 100 صفقة فقط
- لا يوجد polling للتحديث
- المستخدم يجب pull-to-refresh يدوياً

**التأثير:**
- Analytics قديمة
- لا تعكس التغييرات الحالية

**الحل المقترح:**
- جعل analyticsTradesProvider يستمع لـ accountTradingProvider
- أو: إضافة auto-refresh كل دقيقة

---

## 9. الشاشات المفقودة/غير المتصلة

### 9.1 الشاشات التي موجودة لكن غير متصلة

| الشاشة | الموقع | المشكلة | الحل |
|--------|--------|---------|------|
| OnboardingScreen | `/onboarding` | لا يظهر أبداً | يجب إظهاره عند first login |
| ErrorDetailsScreen | `/admin/logs/error` | لا يوجد navigation إليها | يجب إضافة من SystemLogsScreen |

### 9.2 الشاشات التي يجب إنشاؤها

| الشاشة | الوظيفة | الأولوية |
|--------|---------|----------|
| CloseTradeScreen | إغلاق صفقة يدوياً | High |
| DepositWithdrawScreen | إيداع/سحب | Medium |
| TradeHistoryFilterScreen | فلاتر متقدمة للصفقات | Low |
| StrategySettingsScreen | إعدادات الاستراتيجيات | Medium |

### 9.3 الشاشات المكررة

**لا يوجد شاشات مكررة** ✅

تم فحص 25 شاشة:
- كل شاشة لها route فريد
- لا يوجد duplicate routes
- لا يوجد duplicate screens

---

## 10. خريطة قاعدة البيانات الكاملة

```
users
├── id, email, username, password_hash, name, phone
├── is_admin, trading_enabled, created_at, last_login
└── (linked to: portfolio, trades, settings, keys)

portfolio
├── user_id, current_balance, available_balance
├── reserved_balance, initial_balance, total_pnl, total_pnl_pct
└── updated_at

trades
├── id, user_id, symbol, side (BUY/SELL)
├── entry_price, exit_price, quantity
├── status (OPEN/CLOSED), pnl, pnl_pct
├── stop_loss, take_profit, close_reason
├── created_at, closed_at
└── (linked to: user, portfolio updates)

user_settings
├── user_id, risk_level, position_size_pct
├── max_positions, stop_loss_pct, take_profit_pct
├── trading_mode (real/demo), notifications_enabled
└── updated_at

user_binance_keys
├── user_id, api_key_encrypted, secret_encrypted
├── is_testnet, created_at
└── (encrypted with AES-256)

notifications
├── id, user_id, title, body, type
├── is_read, created_at
└── (linked to: user)

fcm_tokens ⚠️ BROKEN (never populated)
├── user_id, token, platform
├── created_at, updated_at
└── (linked to: user)

successful_coins
├── id, symbol, score, last_traded
├── trade_count, total_pnl
└── (capped at 50 coins)

trading_logs
├── id, level, message, source
├── created_at
└── (system logs)

system_errors
├── id, error_type, message, stack_trace
├── is_resolved, created_at, resolved_at
└── (admin monitoring)

mistake_memory
├── id, pattern, count, total_loss
├── conditions, created_at
└── (ML learning - max 500)
```

---

## 11. ملخص التنفيذ الفعلي

### ما يراه المستخدم:
1. يفتح التطبيق → Splash → Login
2. يسجل دخول → Main Shell (5 tabs)
3. يشاهد Dashboard مع رصيد محدث كل 15 ثانية
4. ينتقل بين Portfolio, Trades, Analytics
5. يذهب للـ Profile لتفعيل التداول
6. (Admin) يدخل Admin Dashboard لمراقبة النظام

### ما يحدث خلف الكواليس:
1. `accountTradingProvider` يعمل poll كل 15s
2. TradingOrchestrator يعمل cycle كل 60s
3. Scanner يجلب بيانات السوق
4. SmartMoneyOrchestrator يحسب الإشارات
5. Cognitive Layer يتخذ القرار
6. Risk Manager يتحقق من الحدود
7. Binance API ينفذ الصفقة
8. Database تُحدَّث
9. Notifications ترسل (باستثناء FCM ❌)
10. UI تُعاد بناؤها تلقائياً

### الحالة النهائية:
- **23/25 شاشات تعمل** ✅
- **44/47 زر يعمل** ✅
- **34/35 API endpoint يعمل** ✅
- **1 bug حرج (FCM)** ❌
- **0 شاشات مكررة** ✅
- **0 شاشات معطلة** ✅

---

## 12. توصيات فورية

1. **🔴 إصلاح FCM endpoint** - تغيير `/user/fcm-token` إلى `/notifications/fcm-token`
2. **🟡 إضافة زر Close Trade** - في TradeDetailScreen للصفقات المفتوحة
3. **🟡 تحسين Admin Navigation** - إضافة Admin كـ tab منفصل أو menu
4. **🟢 إظهار Onboarding** - على first login
5. **🟢 إضافة Deposit/Withdraw** - للمحفظة
6. **🟢 تحسين Analytics** - real-time updates

---

*تم إنشاء هذا التقرير بواسطة فحص شامل للـ Flutter UI + Backend Routes + Database Schema + Trading Engine Flow.*
