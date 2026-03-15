# PHASE 4: Full End-to-End Flow Analysis
> Flutter Trading App — Complete User Journey Validation

---

## 🔴 CRITICAL E2E ISSUES

### 1. No Forced Logout on Persistent 401 (Session Expiry)
**Severity:** 🔴 HIGH — Behavioral bug affecting all authenticated users

**Flow:**
```
API call → 401 → _onError interceptor → _refreshToken()
  ├── Refresh succeeds → retry original call ✅
  └── Refresh fails → original 401 propagates to caller
      └── Caller shows generic error → user stays "authenticated" ❌
```

**Problem:** When both access and refresh tokens expire:
- `ApiService._onError()` catches 401, tries `_refreshToken()`, which fails
- Original 401 error propagates to the calling provider/screen
- Screen shows "خطأ" snackbar but **user remains in `AuthStatus.authenticated` state**
- **Every subsequent API call fails** — dashboard, portfolio, trades all show errors
- User must manually navigate to Profile → Logout to fix the state
- No "session expired" message or automatic redirect to login

**Impact:** User trapped in broken state after token expiry. Terrible UX.

**Fix:** Add global 401 handler in `_onError` that calls `authProvider.forceUnauthenticated()` when refresh fails:
```dart
// In _onError, after refresh fails:
if (!refreshed) {
  _isRefreshing = false;
  // Force logout on unrecoverable 401
  // Need a callback or event bus to notify AuthNotifier
}
```

---

### 2. UserModel Data Loss on checkAuth() Re-serialization
**Severity:** 🔴 HIGH — Data integrity issue (already identified in Phase 3)

**Flow:**
```
checkAuth() → API returns full user JSON (with fullName, tradingMode, hasBinanceKeys, etc.)
  → UserModel.fromJson() creates new model (STRIPS fields not in active model)
  → storage.saveUserData(user.toJson()) OVERWRITES storage with stripped data
  → Fields like fullName, tradingMode, hasBinanceKeys LOST permanently
```

---

## 🟡 MEDIUM E2E ISSUES

### 3. Registration Does Not Auto-Login
**Severity:** 🟡 MEDIUM — UX friction

**Flow:**
```
Register Screen → sendRegistrationOtp() → OTP Screen → verifyRegistrationOtp()
  → ✅ success → context.go(RouteNames.login)
  → User must enter credentials AGAIN to login
```

**Impact:** User just created account, verified OTP, but must re-enter email and password. The backend's `verify-registration-otp` returns user data + tokens, but the app ignores them and redirects to login.

**Fix:** After successful registration OTP, use returned tokens to auto-login:
```dart
if (result['success'] == true && result['token'] != null) {
  // Auto-save tokens, set authenticated, go to dashboard
}
```

---

### 4. Biometric Credential Saving Race Condition
**Severity:** 🟡 LOW — Edge case

**Flow:**
```
Login Screen → successful login
  → if storage.biometricEnabled → saveCredentialsForBiometric(email, password)
  → But biometric was ENABLED via Security Settings with OTP
  → The message says: "تم تفعيل البصمة — سجّل الدخول مرة لحفظ بياناتك"
```

**The UX is correct** — after enabling biometric, user must login once to store credentials. But:
- If user enables biometric and then the app crashes before next login, biometric won't work
- The "login once" instruction is clear, so this is low severity

---

## ✅ VALIDATED E2E FLOWS

### Flow 1: New User Registration
```
Onboarding → Register Screen → Fill form (name, email, username, phone, password)
  → sendRegistrationOtp() → 200 OK → Navigate to OTP Screen
  → Enter 6-digit OTP → verifyRegistrationOtp()
  → 200 OK → Snackbar "تم إنشاء الحساب بنجاح" → Navigate to Login
```
**Validation:** ✅ Form validation, mounted checks, error handling, OTP resend with countdown, navigation

### Flow 2: Returning User Login
```
Login Screen → Enter email/password → _login()
  → AuthNotifier.login() → AuthService.login() → API /auth/login
  → 200 OK → Parse UserModel → Set authenticated
  → Save remember-me if checked → Save biometric credentials if enabled
  → Navigate to Dashboard
```
**Validation:** ✅ Remember-me pre-fill, loading state, error display, mounted checks

### Flow 3: Biometric Auto-Login (Splash)
```
Splash Screen → Animation (2.5s) → Exit fade → _checkAuth()
  → biometricEnabled? → Saved credentials exist?
    → bio.authenticate() → Success?
      → YES → AuthNotifier.login(saved creds) → Navigate to dashboard
      → NO → fallback checkAuth() (token validation) → Navigate based on auth
  → NOT biometric → checkAuth() → Navigate based on auth
  → TIMEOUT (splashTimeoutMs) → forceUnauthenticated() → Login
```
**Validation:** ✅ Timeout safety, _navigated flag prevents double nav, post-frame callback

### Flow 4: Token Auto-Refresh
```
Any API call → 401 response → _onError interceptor
  → _isRefreshing guard (prevents concurrent refresh)
  → _refreshToken() → New Dio instance (avoids interceptor loop)
    → POST /auth/refresh-token {refresh_token}
    → Parse access_token + refresh_token from response
    → Save to storage → Retry original request → Return response
```
**Validation:** ✅ Concurrent refresh guard, separate Dio instance, token format handling

### Flow 5: Dashboard Data Loading
```
DashboardScreen.build() →
  ref.watch(portfolioProvider)   → PortfolioRepository.getPortfolio() → API /user/portfolio/<id>
  ref.watch(statsProvider)       → PortfolioRepository.getStats()     → API /user/stats/<id>
  ref.watch(recentTradesProvider)→ TradesRepository.getRecentTrades() → API /user/trades/<id>
  ref.watch(systemStatusProvider)→ AdminRepository.getSystemStatus()  → API /system/status (admin only)
  
  Pull-to-refresh → invalidate all 4 providers → re-fetch
```
**Validation:** ✅ Parallel loading with individual AsyncValue states, shimmer loading, error display

### Flow 6: Trade Lifecycle
```
Dashboard → tap "عرض الكل" → Navigate to Trades Screen
  → loadFirstPage() → API /user/trades/<id>?page=1
  → Filter chips → loadFirstPage(statusFilter: 'open'|'closed'|null)
  → Scroll → loadNextPage() → Append results
  → Tap trade → Navigate to TradeDetailScreen(trade: model)
    → trade == null check → fallback UI
```
**Validation:** ✅ Pagination, filtering, null-safe detail screen

### Flow 7: Settings Change (Trading Settings)
```
Profile → Trading Settings → Load settings from API
  → Modify sliders/toggles → Save
  → settingsRepository.updateSettings() → API PUT /user/settings/<id>
  → Success → Snackbar → Invalidate settingsDataProvider
```
**Validation:** ✅ Form validation, save confirmation, provider invalidation

### Flow 8: Security — Change Password
```
Security Settings → Enter current password → Send OTP
  → authService.sendChangePasswordOtp(email, oldPassword) → API
  → Navigate to OTP screen (type: 'change_password', old_password passed)
  → Enter OTP → Show new password dialog (strong password validation + confirm)
  → authService.verifyChangePasswordOtp(email, otp, newPassword) → API
  → Success → Update biometric credentials → Update remember-me credentials
  → Pop with result(true) → Snackbar "تم تغيير كلمة المرور بنجاح"
```
**Validation:** ✅ Full secure flow, credential update after change, strong password enforcement

### Flow 9: Security — Change Email
```
Security Settings → Enter new email → Send OTP
  → authService.sendChangeEmailOtp(userId, newEmail) → API
  → Navigate to OTP screen (type: 'change_email')
  → Enter OTP → authService.verifyChangeEmailOtp(userId, otp, newEmail) → API
  → Success → Pop with result(true) → Snackbar
```
**Validation:** ✅ Email validation, OTP flow, mounted checks

### Flow 10: Security — Biometric Toggle
```
Toggle ON:
  → Check device support (bio.isAvailable)
  → Prompt biometric (bio.authenticate) → Confirm
  → requestSecureVerification('change_biometric', 'email', 'enable') → API
  → Show OTP dialog → verifySecureAction('change_biometric', otp, 'enable') → API
  → storage.setBiometricEnabled(true)
  → Message: "تم تفعيل البصمة — سجّل الدخول مرة لحفظ بياناتك"

Toggle OFF:
  → requestSecureVerification → OTP → verifySecureAction → disable
  → clearBiometricCredentials()
```
**Validation:** ✅ Full server-verified secure action, local + remote state sync

### Flow 11: Admin Trading Control
```
Admin Dashboard → Trading Control Screen
  → Watch systemStatusProvider + mlStatusProvider
  → Toggle Start/Stop → adminRepository.startTrading()/stopTrading() → API
  → Verify response state (RUNNING/STOPPED) → invalidate systemStatusProvider
  → Emergency Stop → confirmation dialog → adminRepository.emergencyStop()
  → Reset Error → adminRepository.resetError()
```
**Validation:** ✅ Confirmation dialog for destructive action, state verification, provider invalidation

### Flow 12: Password Recovery
```
Login → Forgot Password → Enter email → authService.forgotPassword()
  → Navigate to OTP screen (type: 'forgot_password')
  → Verify OTP → get reset_token → Navigate to Reset Password screen
  → Enter + confirm new password (strong validation)
  → authService.resetPassword(email, resetToken, newPassword) → API
  → Success → Navigate to Login
```
**Validation:** ✅ Complete recovery chain, reset token passing, password validation

### Flow 13: Notification Flow
```
PushNotificationService.start(userId):
  → Firebase Messaging setup + polling fallback (30s)
  → On message → update unread count
  → On tap → navigate to notifications screen

NotificationsScreen:
  → loadFirstPage() → API /user/notifications/<id>
  → Scroll → loadNextPage()
  → Mark All Read → markAllRead() → API → invalidate unreadCountProvider
```
**Validation:** ✅ Dual delivery (push + polling), pagination, badge update

### Flow 14: Logout
```
Profile → "تسجيل الخروج" → AuthNotifier.logout()
  → pushService.stopPolling() (silent catch)
  → authService.logout() → Clear tokens + user data from storage
  → State → AuthStatus.unauthenticated
  → GoRouter redirect → Login screen
```
**Validation:** ✅ Clean resource release, storage clear, state reset, redirect

---

## 📊 PHASE 4 SUMMARY

| Category | Count |
|----------|-------|
| 🔴 Critical E2E bugs | 2 (no forced logout on 401, UserModel data loss) |
| 🟡 Medium UX issues | 1 (no auto-login after registration) |
| 🟢 Low edge cases | 1 (biometric credential save timing) |
| ✅ Validated E2E flows | 14 complete user journeys |

### Top Priority Fixes:
1. **Global 401 forced logout** — implement event bus or callback from ApiService to AuthNotifier
2. **Consolidate UserModel** — single model with all fields
3. **Auto-login after registration** — use returned tokens from OTP verification
