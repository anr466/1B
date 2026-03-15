# Auth, Security, Balance, and Onboarding Update

## Scope

This document records the functional update that fixed the balance source, unified login/session/biometric behavior, and made the usage guide available both on first launch and from inside settings.

## Balance Source Fix

### Problem

The app could display a non-authoritative balance due to two UI-side issues:

- `PortfolioModel` used a fallback initial balance value of `1000`
- admin portfolio mode could start on `demo` by default instead of the active portfolio resolved from backend settings

### Fix

The following changes were applied:

- `lib/core/models/portfolio_model.dart`
  - removed the hardcoded `1000` fallback for `initialBalance`
  - `initialBalance` now falls back to `0`
- `lib/features/analytics/screens/analytics_screen.dart`
  - removed the chart reference fallback of `1000.0`
  - analytics now falls back to `0.0` when portfolio data is unavailable
- `lib/core/providers/portfolio_provider.dart`
  - changed `adminPortfolioModeProvider` default from `demo` to `real`
- `lib/core/providers/auth_provider.dart`
  - added `_syncAdminPortfolioMode()`
  - on login, restored session, and authenticated setup, admin users now resolve their active portfolio from backend settings and update local mode state accordingly

### Result

The displayed balance no longer relies on a dummy client fallback. Admin balance flow now follows the backend-resolved active portfolio instead of defaulting to demo mode.

## Security and Login Flow Unification

### Problem

Security-related behavior was split across multiple screens and services:

- `LoginScreen`
- `SecuritySettingsScreen`
- `BiometricSetupScreen`
- `StorageService`
- `AuthService`
- `AuthProvider`

This caused overlap between:

- traditional login
- remembered credentials
- biometric login enablement
- biometric stored credentials
- logout/session clearing behavior

### Unified Rules After Update

#### Remember Me

- controls only whether login fields should be pre-filled later
- stored in local preferences
- can exist independently from biometric login

#### Biometric Login

- requires biometric support on device
- requires biometric login to be enabled in settings
- requires locally saved credentials
- those credentials are stored only after a successful manual login while biometric login is enabled

#### Manual Login

After successful manual login:

- if `remember me` is enabled, credentials are saved for field prefill
- if `remember me` is disabled, remembered credentials are cleared
- if biometric login is enabled, biometric credentials are saved
- if biometric login is disabled, biometric credentials are cleared

#### Logout

Logout now clears the authenticated session while preserving explicit user preferences and login options.

### Files Updated

- `lib/core/services/storage_service.dart`
  - `clearAll()` is now a true full clear
  - added `clearSessionPreservingLoginOptions()`
- `lib/core/services/auth_service.dart`
  - `logout()` now uses `clearSessionPreservingLoginOptions()`
- `lib/core/providers/auth_provider.dart`
  - resets admin portfolio mode on logout, forced unauthenticated state, and session expiry
- `lib/features/auth/screens/login_screen.dart`
  - explicitly synchronizes remembered credentials and biometric credentials after successful login
- `lib/features/auth/screens/biometric_setup_screen.dart`
  - enabling biometric login also updates the authenticated user state in memory/storage-backed flow
- `lib/features/settings/screens/security_settings_screen.dart`
  - now loads and displays actual security state from storage
  - now exposes remembered credentials state, biometric credential state, remember-me toggle, and clear-saved-credentials action

## Security Settings Behavior

`SecuritySettingsScreen` now reflects the effective local auth configuration:

- biometric enabled state
- remember me enabled state
- whether remembered credentials are currently stored
- whether biometric credentials are currently stored

It also includes:

- biometric toggle
- remember-me toggle
- clear all saved login credentials action
- secure email/password change flows
- current session behavior messaging

## Onboarding / Usage Guide Availability

### Problem

The usage guide was linked from the profile/settings area, but the router treated `/onboarding` as an auth-only route and redirected authenticated users back to dashboard.

### Fix

- `lib/navigation/app_router.dart`
  - authenticated users are still redirected away from auth routes
  - `RouteNames.onboarding` is now exempt from that redirect

### Result

The usage guide now works in both cases:

- first launch for new users
- manual access later from profile/security/settings

## Canonical Admin Portfolio Source

### Canonical Source Rule

The system now treats the canonical admin record with `id = 1` as the authoritative source for demo-linked portfolio data.

The canonical balance source is:

- `portfolio`
- `user_id = 1`
- `is_demo = 1`

This row is now the single source of truth for demo-linked balance fields:

- `total_balance`
- `available_balance`
- `invested_balance`
- `initial_balance`
- `total_profit_loss`
- `total_profit_loss_percentage`

### Routing Rule

Backend trading context resolution now exposes `portfolio_owner_id`.

That means:

- real mode continues to use the requesting user's own portfolio
- demo-linked reads now resolve through the canonical owner instead of per-user demo portfolio rows

### Backend Areas Unified

The canonical source rule was applied across the backend paths that read or reset portfolio-linked demo data:

- portfolio endpoint
- stats endpoint
- daily risk status
- trades history and active positions
- daily pnl and portfolio growth endpoints
- dashboard aggregation
- demo reset flows
- ML admin status
- low-level portfolio/trading database reset and growth calculations

### Defaults Removed

To prevent hidden divergence, the previous implicit `1000` balance fallback was removed from runtime portfolio, stats, reset, and database helper paths involved in the demo-linked source flow.

New or missing rows now resolve to stored values only, with `0` used instead of a fabricated portfolio amount when no authoritative balance exists.

## Final Behavioral Summary

### Balance

- no fake UI fallback balance
- admin mode is aligned with backend active portfolio

### Session Lifecycle

- session restore remains token-based
- session expiry resets authenticated state and admin portfolio mode safely
- logout clears session without wiping user-selected onboarding/theme/privacy/login-option preferences

### Credentials

- remembered credentials are for prefilling login only
- biometric credentials are for explicit biometric sign-in only
- both can be removed from security settings in one action

### Onboarding

- still appears automatically for first-time users
- now also remains reachable later from inside the app

## Validation

After this update, Flutter analysis was run on the impacted files and then on the full Flutter project.

Result:

- `No errors`
