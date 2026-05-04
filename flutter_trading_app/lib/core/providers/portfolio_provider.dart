import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/models/portfolio_model.dart';
import 'package:trading_app/core/models/stats_model.dart';
import 'package:trading_app/core/models/trade_model.dart';
import 'package:trading_app/core/providers/admin_provider.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/providers/unified_async_state.dart';

const _portfolioPollingInterval = Duration(seconds: 15);

/// Unified single source of truth for portfolio + stats + active positions.
/// All derived providers read from this to avoid duplicate API calls.
final accountTradingProvider = StateNotifierProvider<AccountTradingNotifier,
    LoadingState<AccountTradingState>>((ref) {
  return AccountTradingNotifier(ref);
});

class AccountTradingState {
  final PortfolioModel? portfolio;
  final StatsModel? stats;
  final List<TradeModel> activePositions;

  const AccountTradingState({
    this.portfolio,
    this.stats,
    this.activePositions = const [],
  });
}

class AccountTradingNotifier
    extends StateNotifier<LoadingState<AccountTradingState>> {
  final Ref _ref;
  Timer? _pollingTimer;
  bool _disposed = false;

  AccountTradingNotifier(this._ref)
      : super(const LoadingState()) {
    _init();
  }

  void _init() {
    final auth = _ref.read(authProvider);
    if (auth.isAuthenticated && auth.user != null) {
      fetch();
      startPolling();
    }
  }

  String? _resolveMode() {
    final auth = _ref.read(authProvider);
    if (!auth.isAdmin) return null;
    return _ref.read(adminPortfolioModeProvider);
  }

  Future<void> fetch() async {
    if (_disposed) return;
    state = const LoadingState(status: LoadingStatus.loading);

    try {
      final auth = _ref.read(authProvider);
      if (!auth.isAuthenticated || auth.user == null) {
        state = const LoadingState(status: LoadingStatus.error, error: 'غير مصادق');
        return;
      }

      final portfolioRepo = _ref.read(portfolioRepositoryProvider);
      final mode = _resolveMode();

      final results = await Future.wait([
        portfolioRepo.getPortfolio(auth.user!.id, mode: mode),
        portfolioRepo.getStats(auth.user!.id, mode: mode),
        portfolioRepo.getActivePositions(auth.user!.id, mode: mode),
      ]);

      final accountState = AccountTradingState(
        portfolio: results[0] as PortfolioModel,
        stats: results[1] as StatsModel,
        activePositions: results[2] as List<TradeModel>,
      );

      state = LoadingState(status: LoadingStatus.loaded, data: accountState);
    } catch (e) {
      state = LoadingState(status: LoadingStatus.error, error: e.toString());
    }
  }

  Future<void> refresh() => fetch();

  void startPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = Timer.periodic(
      _portfolioPollingInterval,
      (_) => _silentFetch(),
    );
  }

  void stopPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = null;
  }

  Future<void> _silentFetch() async {
    try {
      final auth = _ref.read(authProvider);
      if (!auth.isAuthenticated || auth.user == null) return;

      final portfolioRepo = _ref.read(portfolioRepositoryProvider);
      final mode = _resolveMode();

      final results = await Future.wait([
        portfolioRepo.getPortfolio(auth.user!.id, mode: mode),
        portfolioRepo.getStats(auth.user!.id, mode: mode),
        portfolioRepo.getActivePositions(auth.user!.id, mode: mode),
      ]);

      final accountState = AccountTradingState(
        portfolio: results[0] as PortfolioModel,
        stats: results[1] as StatsModel,
        activePositions: results[2] as List<TradeModel>,
      );

      if (_disposed) return;
      if (mounted) {
        state = LoadingState(status: LoadingStatus.loaded, data: accountState);
      }
    } catch (e) {
      debugPrint('[AccountTradingNotifier] silent fetch error: $e');
    }
  }

  @override
  void dispose() {
    _disposed = true;
    _pollingTimer?.cancel();
    super.dispose();
  }
}

/// Derived provider — extracts PortfolioModel from the unified source.
/// NO independent API calls.
final portfolioProvider = Provider<LoadingState<PortfolioModel>>((ref) {
  final account = ref.watch(accountTradingProvider);
  return account.when(
    data: (state) => LoadingState(
      status: LoadingStatus.loaded,
      data: state.portfolio,
    ),
    loading: () => const LoadingState(status: LoadingStatus.loading),
    error: (err, _) => LoadingState(status: LoadingStatus.error, error: err),
  );
});

/// Derived provider — extracts StatsModel from the unified source.
/// NO independent API calls.
final statsProvider = Provider<LoadingState<StatsModel>>((ref) {
  final account = ref.watch(accountTradingProvider);
  return account.when(
    data: (state) => LoadingState(
      status: LoadingStatus.loaded,
      data: state.stats,
    ),
    loading: () => const LoadingState(status: LoadingStatus.loading),
    error: (err, _) => LoadingState(status: LoadingStatus.error, error: err),
  );
});
