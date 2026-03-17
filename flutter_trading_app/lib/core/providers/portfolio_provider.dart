import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/models/portfolio_model.dart';
import 'package:trading_app/core/models/stats_model.dart';
import 'package:trading_app/core/models/trade_model.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';

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

  AccountTradingNotifier(this._ref)
    : super(
        AccountTradingState(
          enabled: _ref.read(authProvider).user?.tradingEnabled,
        ),
      ) {
    load();
  }

  Future<void> load() async {
    final auth = _ref.read(authProvider);
    final user = auth.user;
    if (user == null) {
      state = const AccountTradingState(enabled: false, isLoading: false);
      return;
    }

    state = state.copyWith(
      enabled: state.enabled ?? user.tradingEnabled,
      isLoading: true,
    );

    try {
      final repo = _ref.read(settingsRepositoryProvider);
      final mode = auth.isAdmin ? _ref.read(adminPortfolioModeProvider) : null;
      final settings = await repo.getSettings(user.id, mode: mode);
      final status = await _ref
          .read(adminRepositoryProvider)
          .getPublicTradingState();
      state = state.copyWith(
        enabled: settings.tradingEnabled,
        systemRunning: status.isEffectivelyRunning || status.isRunning,
        systemState: status.state.toString().toUpperCase(),
        isLoading: false,
      );
      _syncAuthTrading(settings.tradingEnabled);
    } catch (_) {
      state = state.copyWith(
        enabled: state.enabled ?? user.tradingEnabled,
        isLoading: false,
      );
    }
  }

  Future<bool> setEnabled(bool enabled) async {
    final auth = _ref.read(authProvider);
    final user = auth.user;
    if (user == null) return false;

    final previous = state.enabled ?? user.tradingEnabled;
    state = state.copyWith(enabled: previous, isLoading: true);

    try {
      // Fetch system state for display only — does NOT block user activation
      final status = await _ref
          .read(adminRepositoryProvider)
          .getPublicTradingState();
      final systemRunning = status.isEffectivelyRunning || status.isRunning;
      final systemState = status.state.toString().toUpperCase();

      final repo = _ref.read(settingsRepositoryProvider);
      final mode = auth.isAdmin ? _ref.read(adminPortfolioModeProvider) : null;
      await repo.updateSettings(user.id, {'tradingEnabled': enabled}, mode: mode);
      state = state.copyWith(
        enabled: enabled,
        systemRunning: systemRunning,
        systemState: systemState,
        isLoading: false,
      );
      _syncAuthTrading(enabled);
      return true;
    } catch (_) {
      state = state.copyWith(enabled: previous, isLoading: false);
      return false;
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
    StateNotifierProvider.autoDispose<
      AccountTradingNotifier,
      AccountTradingState
    >((ref) {
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
      final repo = ref.watch(portfolioRepositoryProvider);
      return repo.getSuccessfulCoins(auth.user!.id);
    });

/// Stats data provider — passes mode for admin users
final statsProvider = FutureProvider.autoDispose<StatsModel>((ref) async {
  final auth = ref.watch(authProvider);
  if (!auth.isAuthenticated || auth.user == null) {
    throw Exception('غير مصادق');
  }
  final mode = auth.isAdmin ? ref.watch(adminPortfolioModeProvider) : null;
  final repo = ref.watch(portfolioRepositoryProvider);
  return repo.getStats(auth.user!.id, mode: mode);
});
