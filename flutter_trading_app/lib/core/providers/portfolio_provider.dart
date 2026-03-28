import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/models/portfolio_model.dart';
import 'package:trading_app/core/models/stats_model.dart';
import 'package:trading_app/core/models/trade_model.dart';
import 'package:trading_app/core/providers/admin_provider.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/notifications_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/providers/trades_provider.dart';
import 'package:trading_app/core/services/debounce_service.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';

class AccountTradingState {
  final bool? enabled;
  final bool isLoading;
  final bool systemRunning;
  final String systemState;

  const AccountTradingState({
    this.enabled,
    this.isLoading = false,
    this.systemRunning = false,
    this.systemState = 'STOPPED',
  });

  bool get enabledSafe => enabled ?? false;

  AccountTradingState copyWith({
    bool? enabled,
    bool? isLoading,
    bool? systemRunning,
    String? systemState,
  }) {
    return AccountTradingState(
      enabled: enabled ?? this.enabled,
      isLoading: isLoading ?? this.isLoading,
      systemRunning: systemRunning ?? this.systemRunning,
      systemState: systemState ?? this.systemState,
    );
  }
}

class AccountTradingNotifier extends StateNotifier<AccountTradingState> {
  final Ref _ref;
  bool _disposed = false;
  bool _busy = false;
  final Debouncer _debouncer = Debouncer(
    duration: const Duration(milliseconds: 500),
  );

  AccountTradingNotifier(this._ref)
    : super(
        AccountTradingState(
          enabled: _ref.read(authProvider).user?.tradingEnabled ?? false,
        ),
      ) {
    load();
  }

  @override
  void dispose() {
    _disposed = true;
    _debouncer.dispose();
    super.dispose();
  }

  void _setStateSafely(AccountTradingState nextState) {
    if (_disposed) return;
    state = nextState;
  }

  Future<void> load() async {
    final auth = _ref.read(authProvider);
    final user = auth.user;
    if (user == null) {
      _setStateSafely(
        const AccountTradingState(enabled: false, isLoading: false),
      );
      return;
    }

    _setStateSafely(
      state.copyWith(
        enabled: state.enabled ?? user.tradingEnabled,
        isLoading: true,
      ),
    );

    try {
      final repo = _ref.read(settingsRepositoryProvider);
      final mode = auth.isAdmin ? _ref.read(adminPortfolioModeProvider) : null;
      final settings = await repo.getSettings(user.id, mode: mode);

      // Get system status - don't fail if slow
      bool systemRunning = false;
      String systemState = 'UNKNOWN';
      try {
        final status = await _ref
            .read(adminRepositoryProvider)
            .getPublicTradingState()
            .timeout(const Duration(seconds: 5));
        if (!_disposed) {
          systemRunning = status.isEffectivelyRunning || status.isRunning;
          systemState = status.state.toString().toUpperCase();
        }
      } catch (_) {
        // Keep default system status
      }

      if (_disposed) return;
      _setStateSafely(
        state.copyWith(
          enabled: settings.tradingEnabled,
          systemRunning: systemRunning,
          systemState: systemState,
          isLoading: false,
        ),
      );
      _syncAuthTrading(settings.tradingEnabled);
    } catch (_) {
      if (_disposed) return;
      _setStateSafely(state.copyWith(enabled: false, isLoading: false));
    }
  }

  Future<bool> setEnabled(bool enabled) async {
    // Debounce rapid taps - wait for 500ms after last tap
    if (_busy) return false;

    // Use debouncer to prevent rapid spam
    final completer = Completer<bool>();
    _debouncer.runFuture(() async {
      final result = await _setEnabledInternal(enabled);
      if (!completer.isCompleted) {
        completer.complete(result);
      }
    });

    return completer.future;
  }

  Future<bool> _setEnabledInternal(bool enabled) async {
    if (_busy) return false;
    _busy = true;

    final auth = _ref.read(authProvider);
    final user = auth.user;
    if (user == null) {
      _busy = false;
      return false;
    }

    final previous = state.enabled ?? user.tradingEnabled;

    // Optimistic update - only update UI, not auth state yet
    _setStateSafely(state.copyWith(enabled: enabled, isLoading: true));

    try {
      final repo = _ref.read(settingsRepositoryProvider);
      final mode = auth.isAdmin ? _ref.read(adminPortfolioModeProvider) : null;
      await repo.updateSettings(user.id, {
        'tradingEnabled': enabled,
      }, mode: mode);

      final settings = await repo.getSettings(user.id, mode: mode);

      // Get system status separately - don't fail if it's slow
      bool systemRunning = state.systemRunning;
      String systemState = state.systemState;
      try {
        final status = await _ref
            .read(adminRepositoryProvider)
            .getPublicTradingState()
            .timeout(const Duration(seconds: 5));
        if (!_disposed) {
          systemRunning = status.isEffectivelyRunning || status.isRunning;
          systemState = status.state.toString().toUpperCase();
        }
      } catch (_) {
        // Keep previous system status if timeout
      }

      if (_disposed) return true;

      // ✅ Update both UI and Auth state AFTER API success
      _setStateSafely(
        state.copyWith(
          enabled: settings.tradingEnabled,
          systemRunning: systemRunning,
          systemState: systemState,
          isLoading: false,
        ),
      );
      _syncAuthTrading(settings.tradingEnabled);
      return true;
    } catch (_) {
      if (_disposed) return false;
      // ✅ Revert UI but NOT auth state (auth wasn't updated optimistically)
      _setStateSafely(state.copyWith(enabled: previous, isLoading: false));
      return false;
    } finally {
      _busy = false;
    }
  }

  void _syncAuthTrading(bool enabled) {
    final auth = _ref.read(authProvider);
    final currentUser = auth.user;
    if (currentUser == null) return;
    _ref
        .read(authProvider.notifier)
        .updateCurrentUser(currentUser.copyWith(tradingEnabled: enabled));
  }
}

/// Admin portfolio mode — 'demo' | 'real' (only relevant when isAdmin == true)
/// Regular users always see their single portfolio (no mode switching)
final adminPortfolioModeProvider = StateProvider<String>((ref) => 'real');

final accountTradingProvider =
    StateNotifierProvider<AccountTradingNotifier, AccountTradingState>((ref) {
      final auth = ref.watch(authProvider);
      if (auth.isAdmin) {
        ref.watch(adminPortfolioModeProvider);
      }
      return AccountTradingNotifier(ref);
    });

/// Daily status provider — reads daily_pnl from /user/daily-status (based on actual trades)
final dailyStatusProvider = FutureProvider.autoDispose<Map<String, dynamic>>((
  ref,
) async {
  final auth = ref.watch(authProvider);
  if (!auth.isAuthenticated || auth.user == null) return {};
  final repo = ref.watch(settingsRepositoryProvider);
  final mode = auth.isAdmin ? ref.watch(adminPortfolioModeProvider) : null;
  return repo.getDailyStatus(auth.user!.id, mode: mode);
});

/// Portfolio data provider — passes mode for admin users
final portfolioProvider = FutureProvider.autoDispose<PortfolioModel>((
  ref,
) async {
  final auth = ref.watch(authProvider);
  if (!auth.isAuthenticated || auth.user == null) {
    throw Exception('غير مصادق');
  }
  final mode = auth.isAdmin ? ref.watch(adminPortfolioModeProvider) : null;
  final repo = ref.watch(portfolioRepositoryProvider);
  return repo.getPortfolio(auth.user!.id, mode: mode);
});

final activePositionsProvider = FutureProvider.autoDispose<List<TradeModel>>((
  ref,
) async {
  final auth = ref.watch(authProvider);
  if (!auth.isAuthenticated || auth.user == null) {
    throw Exception('غير مصادق');
  }
  final mode = auth.isAdmin ? ref.watch(adminPortfolioModeProvider) : null;
  final repo = ref.watch(portfolioRepositoryProvider);
  return repo.getActivePositions(auth.user!.id, mode: mode);
});

/// Successful (qualified) coins provider
final successfulCoinsProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
      final auth = ref.watch(authProvider);
      if (!auth.isAuthenticated || auth.user == null) return [];
      final mode = auth.isAdmin ? ref.watch(adminPortfolioModeProvider) : null;
      final repo = ref.watch(portfolioRepositoryProvider);
      return repo.getSuccessfulCoins(auth.user!.id, mode: mode);
    });

/// Stats data provider — passes mode for admin users
/// ✅ NOT autoDispose for auto-refresh support
final statsProvider = FutureProvider<StatsModel>((ref) async {
  final auth = ref.watch(authProvider);
  if (!auth.isAuthenticated || auth.user == null) {
    throw Exception('غير مصادق');
  }
  final mode = auth.isAdmin ? ref.watch(adminPortfolioModeProvider) : null;
  final repo = ref.watch(portfolioRepositoryProvider);
  return repo.getStats(auth.user!.id, mode: mode);
});

/// Portfolio refresh coordinator — polls and invalidates all trading data
/// ✅ Ensures portfolio data stays fresh without manual refresh
final portfolioRefreshCoordinatorProvider = StateNotifierProvider((ref) {
  return PortfolioRefreshCoordinator(ref);
});

class PortfolioRefreshCoordinator extends StateNotifier<int> {
  final Ref _ref;
  Timer? _pollingTimer;
  static const _pollInterval = Duration(seconds: 10);

  PortfolioRefreshCoordinator(this._ref) : super(0) {
    _startPolling();
  }

  void _startPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = Timer.periodic(_pollInterval, (_) {
      _invalidateAll();
    });
  }

  void _invalidateAll() {
    _ref.invalidate(portfolioProvider);
    _ref.invalidate(statsProvider);
    _ref.invalidate(activePositionsProvider);
  }

  void refresh() => _invalidateAll();

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }
}

/// Helper to toggle trading with biometric authentication
/// Returns true if successful, false otherwise
Future<bool> toggleTradingWithBiometric({
  required WidgetRef ref,
  required bool enabled,
  required Future<bool> Function(String reason) biometricAuth,
  required void Function(String message, SnackType type) showMessage,
}) async {
  final bio = ref.read(biometricServiceProvider);
  if (await bio.isAvailable) {
    final reason = enabled ? 'تأكيد تفعيل التداول' : 'تأكيد إيقاف التداول';
    final ok = await biometricAuth(reason);
    if (!ok) {
      showMessage('فشل التحقق من البصمة', SnackType.error);
      return false;
    }
  }

  final success = await ref
      .read(accountTradingProvider.notifier)
      .setEnabled(enabled);

  ref.invalidate(portfolioProvider);
  ref.invalidate(statsProvider);
  ref.invalidate(activePositionsProvider);
  ref.invalidate(recentTradesProvider);
  ref.invalidate(tradesListProvider);
  ref.invalidate(dailyStatusProvider);
  ref.invalidate(systemStatusProvider);

  showMessage(
    success
        ? (enabled ? 'تم تفعيل التداول' : 'تم إيقاف التداول')
        : 'تعذر إتمام العملية، حاول مرة أخرى',
    success ? SnackType.success : SnackType.error,
  );

  return success;
}

/// Unified refresh helper — invalidates all trading-related providers
/// Use this instead of manually invalidating multiple providers
void refreshTradingData(WidgetRef ref) {
  ref.invalidate(portfolioProvider);
  ref.invalidate(statsProvider);
  ref.invalidate(activePositionsProvider);
  ref.invalidate(recentTradesProvider);
  ref.invalidate(tradesListProvider);
  ref.invalidate(dailyStatusProvider);
  ref.invalidate(systemStatusProvider);
  ref.invalidate(accountTradingProvider);
}

/// Refresh specific providers based on type
void refreshByType(WidgetRef ref, RefreshType type) {
  switch (type) {
    case RefreshType.tradingData:
      refreshTradingData(ref);
      break;
    case RefreshType.notifications:
      ref.invalidate(unreadCountProvider);
      ref.invalidate(notificationsListProvider);
      break;
    case RefreshType.full:
      refreshTradingData(ref);
      ref.invalidate(unreadCountProvider);
      ref.invalidate(notificationsListProvider);
      break;
  }
}

enum RefreshType { tradingData, notifications, full }
