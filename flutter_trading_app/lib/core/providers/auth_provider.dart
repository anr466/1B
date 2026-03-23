import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/models/user_model.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/services/api_service.dart';
import 'package:trading_app/main.dart';

/// Auth State
enum AuthStatus { initial, authenticated, unauthenticated, loading }

class AuthState {
  final AuthStatus status;
  final UserModel? user;
  final String? error;

  const AuthState({this.status = AuthStatus.initial, this.user, this.error});

  bool get isAuthenticated => status == AuthStatus.authenticated;
  bool get isLoading => status == AuthStatus.loading;
  bool get isAdmin => user?.isAdmin ?? false;

  AuthState copyWith({AuthStatus? status, UserModel? user, String? error}) =>
      AuthState(
        status: status ?? this.status,
        user: user ?? this.user,
        error: error,
      );
}

/// Auth Notifier — manages authentication state
class AuthNotifier extends StateNotifier<AuthState> {
  final Ref _ref;

  AuthNotifier(this._ref) : super(const AuthState()) {
    // Wire session expiry callback — when ApiService detects
    // unrecoverable 401 (refresh token failed), force logout.
    final api = _ref.read(apiServiceProvider);
    api.onSessionExpired = _onSessionExpired;
  }

  void _onSessionExpired() {
    _ref.read(adminPortfolioModeProvider.notifier).state = 'real';
    state = const AuthState(
      status: AuthStatus.unauthenticated,
      error: 'انتهت الجلسة، سجّل دخولك مرة أخرى',
    );
  }

  /// Check existing session on app start with strict validation
  Future<void> checkAuth() async {
    state = state.copyWith(status: AuthStatus.loading, error: null);
    try {
      final authService = _ref.read(authServiceProvider);

      // First check if token exists
      if (!authService.hasToken) {
        state = const AuthState(status: AuthStatus.unauthenticated);
        return;
      }

      final result = await authService.restoreSession();

      // Strict validation: must have success AND valid user data
      if (result['success'] == true &&
          result['user'] != null &&
          result['user'] is Map &&
          result['user']['id'] != null) {
        final user = UserModel.fromJson(
          Map<String, dynamic>.from(result['user'] as Map),
        );
        state = AuthState(status: AuthStatus.authenticated, user: user);
        await _syncAdminPortfolioMode(user);
        _startNotificationPolling(user.id);
        return;
      }

      // Clear any stale data on failure
      await authService.logout();
      state = const AuthState(status: AuthStatus.unauthenticated);
    } catch (e) {
      // Clear auth on any error
      try {
        final authService = _ref.read(authServiceProvider);
        await authService.logout();
      } catch (_) {}
      state = AuthState(
        status: AuthStatus.unauthenticated,
        error: null, // Don't show error on auto-check
      );
    }
  }

  /// Login
  Future<void> login({
    required String emailOrUsername,
    required String password,
  }) async {
    state = state.copyWith(status: AuthStatus.loading, error: null);

    try {
      final authService = _ref.read(authServiceProvider);
      final result = await authService.login(
        emailOrUsername: emailOrUsername,
        password: password,
      );

      if (result['success'] == true && result['user'] != null) {
        final user = UserModel.fromJson(result['user']);
        state = AuthState(status: AuthStatus.authenticated, user: user);
        await _syncAdminPortfolioMode(user);
        _startNotificationPolling(user.id);
      } else {
        state = AuthState(
          status: AuthStatus.unauthenticated,
          error: result['error'] ?? result['message'] ?? 'فشل تسجيل الدخول',
        );
      }
    } catch (e) {
      state = AuthState(
        status: AuthStatus.unauthenticated,
        error: ApiService.extractError(e),
      );
    }
  }

  /// Set authenticated after registration or biometric login
  void setAuthenticated(UserModel user) {
    state = AuthState(status: AuthStatus.authenticated, user: user);
    _syncAdminPortfolioMode(user);
    _startNotificationPolling(user.id);
  }

  /// Update current authenticated user fields without recreating session flow
  void updateCurrentUser(UserModel user) {
    if (!state.isAuthenticated) return;
    _ref.read(storageServiceProvider).saveUser(user);
    state = state.copyWith(user: user);
  }

  /// Force unauthenticated (timeout, token expired, biometric failed)
  Future<void> forceUnauthenticated({bool clearTokens = true}) async {
    try {
      _ref.read(pushNotificationServiceProvider).stopPolling();
    } catch (_) {}
    _ref.read(adminPortfolioModeProvider.notifier).state = 'real';

    if (clearTokens) {
      try {
        await _ref.read(authServiceProvider).logout();
      } catch (_) {}
    }

    state = const AuthState(status: AuthStatus.unauthenticated);
  }

  /// Start notification polling for authenticated user
  void _startNotificationPolling(int userId) {
    try {
      final pushService = _ref.read(pushNotificationServiceProvider);
      pushService.start(userId);
    } catch (_) {
      // Silent — notification polling is non-critical
    }
  }

  /// Logout
  Future<void> logout() async {
    try {
      final pushService = _ref.read(pushNotificationServiceProvider);
      // Unregister FCM token from backend before stopping
      final storage = _ref.read(storageServiceProvider);
      final fcmToken = storage.getString('fcm_token');
      if (fcmToken != null && fcmToken.isNotEmpty) {
        await pushService.unregisterFcmToken(fcmToken);
      }
      pushService.stopPolling();
    } catch (_) {}
    final authService = _ref.read(authServiceProvider);
    await authService.logout();
    _ref.read(adminPortfolioModeProvider.notifier).state = 'real';
    state = const AuthState(status: AuthStatus.unauthenticated);
  }

  /// Delete account permanently
  Future<Map<String, dynamic>> deleteAccount({
    required String password,
    required String confirmation,
  }) async {
    state = state.copyWith(status: AuthStatus.loading, error: null);
    try {
      final pushService = _ref.read(pushNotificationServiceProvider);
      pushService.stopPolling();
    } catch (_) {}

    try {
      final authService = _ref.read(authServiceProvider);
      final result = await authService.deleteAccount(
        password: password,
        confirmation: confirmation,
      );

      if (result['success'] == true) {
        state = const AuthState(status: AuthStatus.unauthenticated);
      } else {
        state = AuthState(
          status: AuthStatus.authenticated,
          user: state.user,
          error: result['error'] ?? result['message'] ?? 'تعذر حذف الحساب',
        );
      }
      return result;
    } catch (e) {
      final currentUser = state.user;
      state = AuthState(
        status: currentUser == null
            ? AuthStatus.unauthenticated
            : AuthStatus.authenticated,
        user: currentUser,
        error: ApiService.extractError(e),
      );
      return {'success': false, 'error': ApiService.extractError(e)};
    }
  }

  Future<void> _syncAdminPortfolioMode(UserModel user) async {
    if (!user.isAdmin) {
      _ref.read(adminPortfolioModeProvider.notifier).state = 'real';
      return;
    }

    try {
      final settings = await _ref
          .read(settingsRepositoryProvider)
          .getSettings(user.id);
      final resolvedMode = settings.activePortfolio == 'demo' ? 'demo' : 'real';
      _ref.read(adminPortfolioModeProvider.notifier).state = resolvedMode;
      updateCurrentUser(user.copyWith(tradingMode: resolvedMode));
    } catch (_) {
      // Fallback to login response mode on settings API failure
      final fallbackMode = user.tradingMode == 'demo' ? 'demo' : 'real';
      _ref.read(adminPortfolioModeProvider.notifier).state = fallbackMode;
    }
  }

  /// Clear error
  void clearError() {
    state = state.copyWith(error: null);
  }
}

/// Auth Provider
final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ref);
});
