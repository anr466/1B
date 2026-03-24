import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/constants/app_constants.dart';
import 'package:trading_app/core/models/notification_model.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';

/// Unread count for badge
final unreadCountProvider = FutureProvider.autoDispose<int>((ref) async {
  final auth = ref.watch(authProvider);
  if (!auth.isAuthenticated || auth.user == null) return 0;
  final repo = ref.watch(notificationsRepositoryProvider);
  return repo.getUnreadCount(auth.user!.id);
});

/// Notifications list state
class NotificationsListState {
  final List<NotificationModel> notifications;
  final int currentPage;
  final bool isLoading;
  final bool hasMore;
  final String? error;
  final bool isMarkingAllRead;

  const NotificationsListState({
    this.notifications = const [],
    this.currentPage = 0,
    this.isLoading = false,
    this.hasMore = true,
    this.error,
    this.isMarkingAllRead = false,
  });

  NotificationsListState copyWith({
    List<NotificationModel>? notifications,
    int? currentPage,
    bool? isLoading,
    bool? hasMore,
    String? error,
    bool? isMarkingAllRead,
  }) => NotificationsListState(
    notifications: notifications ?? this.notifications,
    currentPage: currentPage ?? this.currentPage,
    isLoading: isLoading ?? this.isLoading,
    hasMore: hasMore ?? this.hasMore,
    error: error,
    isMarkingAllRead: isMarkingAllRead ?? this.isMarkingAllRead,
  );
}

class NotificationsListNotifier extends StateNotifier<NotificationsListState> {
  final Ref _ref;
  bool _busy = false;

  NotificationsListNotifier(this._ref) : super(const NotificationsListState());

  Future<void> loadFirstPage() async {
    if (_busy) return;
    _busy = true;
    state = const NotificationsListState(isLoading: true);
    await _loadPage(1);
    _busy = false;
  }

  Future<void> loadNextPage() async {
    if (_busy || state.isLoading || !state.hasMore) return;
    _busy = true;
    state = state.copyWith(isLoading: true);
    await _loadPage(state.currentPage + 1);
    _busy = false;
  }

  Future<void> markAllRead() async {
    if (_busy) return;
    state = state.copyWith(isMarkingAllRead: true);

    try {
      final auth = _ref.read(authProvider);
      if (!auth.isAuthenticated || auth.user == null) return;
      final repo = _ref.read(notificationsRepositoryProvider);
      await repo.markAllRead(auth.user!.id);
      _ref.invalidate(unreadCountProvider);
      await loadFirstPage();
    } finally {
      state = state.copyWith(isMarkingAllRead: false);
    }
  }

  Future<void> markAsRead(int notificationId) async {
    if (_busy) return;
    final auth = _ref.read(authProvider);
    if (!auth.isAuthenticated || auth.user == null) return;
    final repo = _ref.read(notificationsRepositoryProvider);
    await repo.markOneRead(notificationId);
    _ref.invalidate(unreadCountProvider);
    await loadFirstPage();
  }

  Future<void> _loadPage(int page) async {
    try {
      final auth = _ref.read(authProvider);
      if (!auth.isAuthenticated || auth.user == null) return;

      final repo = _ref.read(notificationsRepositoryProvider);
      final result = await repo.getNotifications(auth.user!.id, page: page);

      final all = page == 1
          ? result.notifications
          : [...state.notifications, ...result.notifications];

      state = state.copyWith(
        notifications: all,
        currentPage: page,
        isLoading: false,
        hasMore:
            result.notifications.length >= AppConstants.notificationsPerPage,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }
}

final notificationsListProvider =
    StateNotifierProvider.autoDispose<
      NotificationsListNotifier,
      NotificationsListState
    >((ref) {
      return NotificationsListNotifier(ref);
    });
