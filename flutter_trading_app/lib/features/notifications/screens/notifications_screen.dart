import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/models/notification_model.dart';
import 'package:trading_app/core/providers/notifications_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/empty_state.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Notifications Screen — الإشعارات مع pagination + mark all read
class NotificationsScreen extends ConsumerStatefulWidget {
  const NotificationsScreen({super.key});

  @override
  ConsumerState<NotificationsScreen> createState() =>
      _NotificationsScreenState();
}

class _NotificationsScreenState extends ConsumerState<NotificationsScreen> {
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    Future.microtask(() {
      ref.read(notificationsListProvider.notifier).loadFirstPage();
    });
  }

  void _onScroll() {
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      ref.read(notificationsListProvider.notifier).loadNextPage();
    }
  }

  void _refresh() {
    ref.read(notificationsListProvider.notifier).loadFirstPage();
    ref.invalidate(unreadCountProvider);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final state = ref.watch(notificationsListProvider);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppScreenHeader(
                title: 'الإشعارات',
                showBack: true,
                trailing:
                    state.notifications.isNotEmpty && !state.isMarkingAllRead
                    ? AppButton(
                        label: 'الكل كمقروء',
                        variant: AppButtonVariant.text,
                        isFullWidth: false,
                        onPressed: () async {
                          await ref
                              .read(notificationsListProvider.notifier)
                              .markAllRead();
                          if (!context.mounted) return;
                          AppSnackbar.show(
                            context,
                            message: 'تم تحديد الكل كمقروء',
                            type: SnackType.success,
                          );
                        },
                      )
                    : null,
              ),
              Expanded(
                child: RefreshIndicator(
                  color: cs.primary,
                  onRefresh: () async {
                    _refresh();
                  },
                  child: _buildBody(cs, state),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBody(ColorScheme cs, NotificationsListState state) {
    if (state.isLoading && state.notifications.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(SpacingTokens.base),
        child: LoadingShimmer(itemCount: 5, itemHeight: 72),
      );
    }

    if (state.notifications.isEmpty) {
      return const EmptyState(message: 'لا توجد إشعارات');
    }

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.symmetric(horizontal: SpacingTokens.base),
      itemCount: state.notifications.length + (state.hasMore ? 1 : 0),
      itemBuilder: (_, i) {
        if (i >= state.notifications.length) {
          return const Padding(
            padding: EdgeInsets.all(SpacingTokens.base),
            child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
          );
        }

        final n = state.notifications[i];
        return Padding(
          padding: const EdgeInsets.only(bottom: SpacingTokens.sm),
          child: AppCard(
            backgroundColor: n.isRead
                ? null
                : cs.primary.withValues(alpha: 0.05),
            padding: const EdgeInsets.all(SpacingTokens.md),
            onTap: () => _handleNotificationTap(n),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    if (!n.isRead)
                      Container(
                        width: 8,
                        height: 8,
                        margin: const EdgeInsetsDirectional.only(
                          end: SpacingTokens.sm,
                        ),
                        decoration: BoxDecoration(
                          color: cs.primary,
                          shape: BoxShape.circle,
                        ),
                      ),
                    Expanded(
                      child: Text(
                        n.title,
                        style: TypographyTokens.body(cs.onSurface).copyWith(
                          fontWeight: n.isRead
                              ? FontWeight.w400
                              : FontWeight.w600,
                        ),
                      ),
                    ),
                    if (_isTradeNotification(n))
                      Icon(Icons.trending_up, size: 16, color: cs.primary),
                  ],
                ),
                const SizedBox(height: SpacingTokens.xs),
                Text(
                  n.message,
                  style: TypographyTokens.bodySmall(
                    cs.onSurface.withValues(alpha: 0.6),
                  ),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                if (n.createdAt != null) ...[
                  const SizedBox(height: SpacingTokens.xs),
                  Text(
                    n.createdAt!.split('T').first,
                    style: TypographyTokens.caption(
                      cs.onSurface.withValues(alpha: 0.3),
                    ),
                  ),
                ],
              ],
            ),
          ),
        );
      },
    );
  }

  void _handleNotificationTap(NotificationModel notification) {
    // تحديد الإشعار كمقروء
    if (!notification.isRead) {
      ref.read(notificationsListProvider.notifier).markAsRead(notification.id);
    }

    // التوجيه بناءً على نوع الإشعار
    if (_isTradeNotification(notification)) {
      _navigateToTradeDetails(notification);
    } else {
      // للإشعارات الأخرى، يمكن إضافة توجيهات مختلفة
      _handleOtherNotification(notification);
    }
  }

  bool _isTradeNotification(NotificationModel notification) {
    final tradeTypes = [
      'trade_opened',
      'trade_closed',
      'trade_closed_profit',
      'trade_closed_loss',
      'trade_completed',
      'trade_modified',
      'trade_error',
      'trade_signal',
    ];
    return tradeTypes.contains(notification.type) ||
        notification.title.toLowerCase().contains('صفقة') ||
        notification.message.toLowerCase().contains('صفقة');
  }

  void _navigateToTradeDetails(NotificationModel notification) async {
    // استخراج بيانات الصفقة من الإشعار
    final tradeData = notification.data ?? {};
    final rawTradeId = tradeData['trade_id'] ?? tradeData['tradeId'];
    final tradeId = switch (rawTradeId) {
      int value => value,
      num value => value.toInt(),
      String value => int.tryParse(value),
      _ => null,
    };
    final symbol = tradeData['symbol'] as String?;

    // استخراج الرمز من الرسالة إذا لم يكن موجوداً في البيانات
    final extractedSymbol = _extractSymbolFromMessage(notification.message);
    final finalSymbol = symbol ?? extractedSymbol;

    if (tradeId != null) {
      try {
        final repo = ref.read(tradesRepositoryProvider);
        final trade = await repo.getTradeById(tradeId);
        if (mounted) {
          context.push(RouteNames.tradeDetail, extra: trade);
        }
      } catch (e) {
        if (mounted) {
          context.go(RouteNames.trades);
        }
      }
    } else if (finalSymbol != null) {
      // التوجيه لصفحة الصفقات مع فلتر الرمز
      context.go(RouteNames.trades);
    } else {
      // التوجيه لصفحة الصفقات العامة
      context.go(RouteNames.trades);
    }
  }

  String? _extractSymbolFromMessage(String message) {
    // استخراج رمز العملة من رسالة الإشعار
    // أمثلة: "BNBUSDT", "LINKUSDT", "BTCUSDT"
    final symbolPattern = RegExp(r'[A-Z]{3,6}USDT');
    final match = symbolPattern.firstMatch(message);
    return match?.group(0);
  }

  void _handleOtherNotification(NotificationModel notification) {
    switch (notification.type) {
      case 'system':
        AppSnackbar.show(
          context,
          message: notification.message ?? 'إشعار نظام',
          type: SnackType.info,
        );
      case 'error':
        AppSnackbar.show(
          context,
          message: notification.message ?? 'إشعار خطأ',
          type: SnackType.error,
        );
      default:
        break;
    }
  }
}
