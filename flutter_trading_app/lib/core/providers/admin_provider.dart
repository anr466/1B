import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/models/system_status_model.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';

/// System status provider for dashboard & admin
/// ✅ UNIFIED: Single provider with 60s polling for consistent state
/// Uses StateNotifierProvider for stable state management (no flickering)
final systemStatusProvider =
    StateNotifierProvider<SystemStatusNotifier, AsyncValue<SystemStatusModel>>((
      ref,
    ) {
      return SystemStatusNotifier(ref);
    });

/// Backward compatibility alias
final tradingCycleLiveProvider = systemStatusProvider;

class SystemStatusNotifier
    extends StateNotifier<AsyncValue<SystemStatusModel>> {
  final Ref _ref;
  Timer? _pollingTimer;
  bool _disposed = false;
  bool _initialLoadDone = false;

  SystemStatusNotifier(this._ref) : super(const AsyncValue.loading()) {
    _load();
    _startPolling();
  }

  Future<void> _load() async {
    if (_disposed) return;
    try {
      final repo = _ref.read(adminRepositoryProvider);
      final status = await repo.getTradingState();
      if (!_disposed) {
        _initialLoadDone = true;
        state = AsyncValue.data(status);
      }
    } catch (e, _) {
      if (!_disposed) {
        if (!_initialLoadDone) {
          state = AsyncValue.error(e, StackTrace.current);
        }
      }
    }
  }

  void _startPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (!_disposed) {
        _loadSilent();
      }
    });
  }

  Future<void> _loadSilent() async {
    if (_disposed) return;
    try {
      final repo = _ref.read(adminRepositoryProvider);
      final status = await repo.getTradingState();
      if (!_disposed && _initialLoadDone) {
        state = AsyncValue.data(status);
      }
    } catch (_) {
      // Silent fail during polling - keep last known state
    }
  }

  Future<void> refresh() async {
    if (_disposed) return;
    final previousState = state;
    try {
      final repo = _ref.read(adminRepositoryProvider);
      final status = await repo.getTradingState();
      if (!_disposed) {
        _initialLoadDone = true;
        state = AsyncValue.data(status);
      }
    } catch (e) {
      if (!_disposed) {
        state = previousState;
      }
    }
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

/// ML Status — autoDispose to prevent memory leak
final mlStatusProvider = FutureProvider.autoDispose<Map<String, dynamic>>((
  ref,
) async {
  final auth = ref.watch(authProvider);
  final mode = auth.isAdmin ? ref.watch(adminPortfolioModeProvider) : null;
  final repo = ref.watch(adminRepositoryProvider);
  return repo.getMlStatus(mode: mode);
});
