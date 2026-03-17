import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/models/trade_model.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';

/// Recent trades for dashboard
final recentTradesProvider = FutureProvider.autoDispose<List<TradeModel>>((
  ref,
) async {
  final auth = ref.watch(authProvider);
  if (!auth.isAuthenticated || auth.user == null) {
    throw Exception('غير مصادق');
  }
  final mode = auth.isAdmin ? ref.watch(adminPortfolioModeProvider) : null;
  final repo = ref.watch(tradesRepositoryProvider);
  return repo.getRecentTrades(auth.user!.id, mode: mode);
});

/// Trades list state for pagination
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
  }) => TradesListState(
    trades: trades ?? this.trades,
    currentPage: currentPage ?? this.currentPage,
    totalPages: totalPages ?? this.totalPages,
    isLoading: isLoading ?? this.isLoading,
    hasMore: hasMore ?? this.hasMore,
    error: error,
    statusFilter: statusFilter ?? this.statusFilter,
  );
}

/// Trades list notifier with pagination
class TradesListNotifier extends StateNotifier<TradesListState> {
  final Ref _ref;

  TradesListNotifier(this._ref) : super(const TradesListState());

  Future<void> loadFirstPage({String? statusFilter}) async {
    state = TradesListState(isLoading: true, statusFilter: statusFilter);
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

  Future<void> _loadPage(int page) async {
    try {
      final auth = _ref.read(authProvider);
      if (!auth.isAuthenticated || auth.user == null) return;

      final repo = _ref.read(tradesRepositoryProvider);
      final mode = auth.isAdmin ? _ref.read(adminPortfolioModeProvider) : null;
      final result = await repo.getTrades(
        auth.user!.id,
        page: page,
        mode: mode,
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
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }
}

final tradesListProvider =
    StateNotifierProvider.autoDispose<TradesListNotifier, TradesListState>((
      ref,
    ) {
      return TradesListNotifier(ref);
    });
