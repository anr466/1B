import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/models/system_status_model.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/providers/unified_async_state.dart';

final systemStatusProvider =
    StateNotifierProvider<SystemStatusNotifier, AsyncValue<SystemStatusModel>>((ref) {
  return SystemStatusNotifier(ref);
});

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
    } catch (e, st) {
      if (!_disposed) {
        if (!_initialLoadDone) {
          state = AsyncValue.error(e, st);
        }
      }
    }
  }

  void _startPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = Timer.periodic(const Duration(seconds: 30), (_) {
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
    } catch (_) {}
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

final adminUsersProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
  final repo = ref.watch(adminRepositoryProvider);
  return repo.getAllUsers();
});

final mlStatusProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final repo = ref.watch(adminRepositoryProvider);
  return repo.getMlStatus();
});

final adminPortfolioModeProvider = StateProvider<String?>((ref) => null);

final adminPortfolioStateProvider = StateNotifierProvider<AdminPortfolioNotifier,
    UnifiedAsyncState<AdminPortfolioData>>((ref) {
  return AdminPortfolioNotifier(ref);
});

class AdminPortfolioData {
  final List<Map<String, dynamic>> users;
  final Map<String, dynamic> systemStatus;
  final Map<String, dynamic> mlStatus;

  const AdminPortfolioData({
    this.users = const [],
    this.systemStatus = const {},
    this.mlStatus = const {},
  });

  AdminPortfolioData copyWith({
    List<Map<String, dynamic>>? users,
    Map<String, dynamic>? systemStatus,
    Map<String, dynamic>? mlStatus,
  }) =>
      AdminPortfolioData(
        users: users ?? this.users,
        systemStatus: systemStatus ?? this.systemStatus,
        mlStatus: mlStatus ?? this.mlStatus,
      );
}

class AdminPortfolioNotifier
    extends StateNotifier<UnifiedAsyncState<AdminPortfolioData>> {
  final Ref _ref;
  Timer? _pollingTimer;

  AdminPortfolioNotifier(this._ref)
      : super(UnifiedAsyncState<AdminPortfolioData>.initial()) {
    _init();
  }

  void _init() {
    fetch();
    _startPolling();
  }

  void _startPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      _silentFetch();
    });
  }

  Future<void> _silentFetch() async {
    try {
      final repo = _ref.read(adminRepositoryProvider);
      final results = await Future.wait([
        repo.getAllUsers(),
        repo.getTradingState().then((s) => <String, dynamic>{
          'state': s.state,
          'is_running': s.isRunning,
        }),
        repo.getMlStatus(),
      ]);

      final data = AdminPortfolioData(
        users: List<Map<String, dynamic>>.from(results[0] as List),
        systemStatus: Map<String, dynamic>.from(results[1] as Map),
        mlStatus: Map<String, dynamic>.from(results[2] as Map),
      );

      if (mounted) {
        state = UnifiedAsyncState<AdminPortfolioData>.loaded(data);
      }
    } catch (_) {}
  }

  Future<void> fetch() async {
    state = UnifiedAsyncState<AdminPortfolioData>.loading();
    await _silentFetch();
  }

  Future<void> refresh() => fetch();

  @override
  void dispose() {
    _pollingTimer?.cancel();
    super.dispose();
  }
}

final adminActivePositionsProvider = FutureProvider.family<List<Map<String, dynamic>>, int>((ref, userId) async {
  final repo = ref.watch(adminRepositoryProvider);
  return repo.getActivePositionsForUser(userId);
});

/// Daily status for the current date — single source of truth.
final dailyStatusProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final repo = ref.watch(adminRepositoryProvider);
  final today = DateTime.now().toIso8601String().substring(0, 10);
  return repo.getDailyStatus(today);
});
