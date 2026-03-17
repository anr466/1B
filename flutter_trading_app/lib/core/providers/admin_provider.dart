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

final publicSystemStatusProvider =
    FutureProvider.autoDispose<SystemStatusModel>((ref) async {
      final repo = ref.watch(adminRepositoryProvider);
      return repo.getPublicTradingState();
    });

/// Live polling provider — syncs with backend trading cycle every 15 seconds
final tradingCycleLiveProvider = StreamProvider.autoDispose<SystemStatusModel>((
  ref,
) async* {
  final repo = ref.read(adminRepositoryProvider);

  // Emit immediately
  yield await repo.getTradingState();

  // Then poll every 15 seconds
  await for (final _ in Stream.periodic(const Duration(seconds: 15))) {
    try {
      yield await repo.getTradingState();
    } catch (_) {
      // Keep last emitted value on transient error — no yield
    }
  }
});

/// Admin users list
final adminUsersProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
      final repo = ref.watch(adminRepositoryProvider);
      return repo.getAllUsers();
    });

/// ML Status
final mlStatusProvider = FutureProvider.autoDispose<Map<String, dynamic>>((
  ref,
) async {
  final auth = ref.watch(authProvider);
  final mode = auth.isAdmin ? ref.watch(adminPortfolioModeProvider) : null;
  final repo = ref.watch(adminRepositoryProvider);
  return repo.getMlStatus(mode: mode);
});
