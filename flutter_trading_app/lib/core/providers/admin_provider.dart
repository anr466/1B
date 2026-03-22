import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/models/system_status_model.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';

/// System status provider for dashboard & admin (single fetch)
final systemStatusProvider = FutureProvider.autoDispose<SystemStatusModel>((
  ref,
) async {
  final repo = ref.watch(adminRepositoryProvider);
  return repo.getTradingState();
});

/// Live trading cycle provider — FutureProvider with 60s auto-refresh
/// Uses FutureProvider for stable state management (no flickering)
final tradingCycleLiveProvider =
    StateNotifierProvider<TradingCycleNotifier, AsyncValue<SystemStatusModel>>((
      ref,
    ) {
      return TradingCycleNotifier(ref);
    });

class TradingCycleNotifier
    extends StateNotifier<AsyncValue<SystemStatusModel>> {
  final Ref _ref;
  Timer? _pollingTimer;
  bool _disposed = false;

  TradingCycleNotifier(this._ref) : super(const AsyncValue.loading()) {
    _load();
    _startPolling();
  }

  Future<void> _load() async {
    if (_disposed) return;
    try {
      final repo = _ref.read(adminRepositoryProvider);
      final status = await repo.getTradingState();
      if (!_disposed) {
        state = AsyncValue.data(status);
      }
    } catch (e, st) {
      if (!_disposed) {
        state = AsyncValue.error(e, st);
      }
    }
  }

  void _startPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = Timer.periodic(const Duration(seconds: 60), (_) {
      _load();
    });
  }

  Future<void> refresh() async {
    state = const AsyncValue.loading();
    await _load();
  }

  @override
  void dispose() {
    _disposed = true;
    _pollingTimer?.cancel();
    super.dispose();
  }
}

/// Admin users list
final adminUsersProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
      final repo = ref.watch(adminRepositoryProvider);
      return repo.getAllUsers();
    });

/// ML Status — cached to prevent card recreation
final mlStatusProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final auth = ref.watch(authProvider);
  final mode = auth.isAdmin ? ref.watch(adminPortfolioModeProvider) : null;
  final repo = ref.watch(adminRepositoryProvider);
  return repo.getMlStatus(mode: mode);
});
