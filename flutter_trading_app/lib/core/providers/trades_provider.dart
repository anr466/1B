import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/models/trade_model.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/providers/unified_async_state.dart';

final recentTradesProvider =
    FutureProvider.autoDispose<List<TradeModel>>((ref) async {
  final auth = ref.watch(authProvider);
  if (!auth.isAuthenticated || auth.user == null) {
    throw Exception('غير مصادق');
  }
  final repo = ref.watch(tradesRepositoryProvider);
  return repo.getRecentTrades(auth.user!.id);
});

final analyticsTradesProvider = FutureProvider.autoDispose<List<TradeModel>>((ref) async {
  final auth = ref.watch(authProvider);
  if (!auth.isAuthenticated || auth.user == null) {
    throw Exception('غير مصادق');
  }
  final repo = ref.watch(tradesRepositoryProvider);
  final result = await repo.getTrades(
    auth.user!.id,
    page: 1,
    perPage: 100,
  );
  return result.trades;
});

class TradesListState {
  final List<TradeModel> trades;
  final int currentPage;
  final int totalPages;
  final bool isLoading;
  final bool hasMore;
  final String? error;
  final String? statusFilter;

  const TradesListState({
    this.trades = const [],
    this.currentPage = 0,
    this.totalPages = 1,
    this.isLoading = false,
    this.hasMore = true,
    this.error,
    this.statusFilter,
  });

  TradesListState copyWith({
    List<TradeModel>? trades,
    int? currentPage,
    int? totalPages,
    bool? isLoading,
    bool? hasMore,
    String? error,
    String? statusFilter,
  }) =>
      TradesListState(
        trades: trades ?? this.trades,
        currentPage: currentPage ?? this.currentPage,
        totalPages: totalPages ?? this.totalPages,
        isLoading: isLoading ?? this.isLoading,
        hasMore: hasMore ?? this.hasMore,
        error: error,
        statusFilter: statusFilter ?? this.statusFilter,
      );
}

class TradesListNotifier extends StateNotifier<TradesListState> {
  final Ref _ref;

  TradesListNotifier(this._ref) : super(const TradesListState());

  Future<void> loadFirstPage({String? statusFilter}) async {
    state = TradesListState(
      isLoading: true,
      statusFilter: statusFilter ?? state.statusFilter,
    );
    await _loadPage(1);
  }

  Future<void> loadNextPage() async {
    if (state.isLoading || !state.hasMore) return;
    state = state.copyWith(isLoading: true);
    await _loadPage(state.currentPage + 1);
  }

  Future<void> refresh() async {
    await loadFirstPage(statusFilter: state.statusFilter);
  }

  Future<void> setFilter(String? status) async {
    if (status == state.statusFilter) return;
    await loadFirstPage(statusFilter: status);
  }

  Future<void> _loadPage(int page) async {
    try {
      final auth = _ref.read(authProvider);
      if (!auth.isAuthenticated || auth.user == null) {
        state = state.copyWith(
          isLoading: false,
          error: 'غير مصادق',
        );
        return;
      }

      final repo = _ref.read(tradesRepositoryProvider);
      final result = await repo.getTrades(
        auth.user!.id,
        page: page,
        status: state.statusFilter,
      );

      final allTrades = page == 1
          ? result.trades
          : [...state.trades, ...result.trades];

      state = state.copyWith(
        trades: allTrades,
        currentPage: page,
        totalPages: result.pages,
        isLoading: false,
        hasMore: page < result.pages,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }
}

final tradesListProvider =
    StateNotifierProvider.autoDispose<TradesListNotifier, TradesListState>((ref) {
  return TradesListNotifier(ref);
});

/// Derived provider — extracts active positions from the unified source.
/// NO independent API calls.
final activePositionsProvider = Provider<LoadingState<List<TradeModel>>>((ref) {
  final account = ref.watch(accountTradingProvider);
  return account.when(
    data: (state) => LoadingState(
      status: LoadingStatus.loaded,
      data: state.activePositions,
    ),
    loading: () => const LoadingState(status: LoadingStatus.loading),
    error: (err, _) => LoadingState(status: LoadingStatus.error, error: err),
  );
});
