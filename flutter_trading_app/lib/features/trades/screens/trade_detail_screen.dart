import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/models/trade_model.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/providers/trades_provider.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/error_state.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/money_text.dart';
import 'package:trading_app/design/widgets/pnl_indicator.dart';
import 'package:trading_app/design/widgets/status_badge.dart';

/// Trade Detail Screen — تفاصيل صفقة واحدة
class TradeDetailScreen extends ConsumerWidget {
  final TradeModel? trade;
  final int? tradeId;

  const TradeDetailScreen({super.key, this.trade, this.tradeId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;

    if (trade == null && tradeId != null) {
      return _TradeDetailLoader(tradeId: tradeId!);
    }

    if (trade == null) {
      return Directionality(
        textDirection: TextDirection.rtl,
        child: Scaffold(
          backgroundColor: cs.surface,
          body: SafeArea(
            child: Column(
              children: [
                AppScreenHeader(title: 'تفاصيل الصفقة', showBack: true),
                Center(
                  child: Text(
                    'لا توجد بيانات',
                    style: TypographyTokens.body(
                      cs.onSurface.withValues(alpha: 0.5),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
    }

    final t = trade!;
    final isBuy = t.side == 'BUY';

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            children: [
              AppScreenHeader(title: t.symbol, showBack: true),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.all(SpacingTokens.base),
                  children: [
                    AppCard(
                      gradientColors: [
                        cs.primary.withValues(alpha: 0.1),
                        cs.surface,
                      ],
                      padding: const EdgeInsets.all(SpacingTokens.lg),
                      child: Column(
                        children: [
                          Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    t.symbol,
                                    style: TypographyTokens.h2(cs.onSurface),
                                  ),
                                  const SizedBox(height: SpacingTokens.xs),
                                  StatusBadge(
                                    text: isBuy ? 'شراء' : 'بيع',
                                    type: isBuy
                                        ? BadgeType.success
                                        : BadgeType.error,
                                    showDot: false,
                                  ),
                                ],
                              ),
                              Column(
                                crossAxisAlignment: CrossAxisAlignment.end,
                                children: [
                                  StatusBadge(
                                    text: t.isOpen ? 'مفتوحة' : 'مغلقة',
                                    type: t.isOpen
                                        ? BadgeType.info
                                        : BadgeType.success,
                                  ),
                                  if (t.pnl != null) ...[
                                    const SizedBox(height: SpacingTokens.sm),
                                    PnlIndicator(
                                      amount: t.pnl!,
                                      percentage: t.pnlPct,
                                      priceChangePercentage: t.priceChangePct,
                                    ),
                                  ],
                                ],
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(height: SpacingTokens.md),
                    AppCard(
                      padding: const EdgeInsets.all(SpacingTokens.md),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'معلومات السعر',
                            style: TypographyTokens.label(cs.onSurface),
                          ),
                          const SizedBox(height: SpacingTokens.md),
                          _detailRow(
                            cs,
                            'سعر الدخول',
                            '\$${t.entryPrice.toStringAsFixed(6)}',
                          ),
                          if (t.isOpen && t.currentPrice != null)
                            _detailRow(
                              cs,
                              'السعر الحالي',
                              '\$${t.currentPrice!.toStringAsFixed(6)}',
                            ),
                          if (t.exitPrice != null)
                            _detailRow(
                              cs,
                              'سعر الخروج',
                              '\$${t.exitPrice!.toStringAsFixed(6)}',
                            ),
                          _detailRow(
                            cs,
                            'الكمية',
                            t.quantity.toStringAsFixed(4),
                          ),
                          _detailRowWidget(
                            cs,
                            'مبلغ الدخول',
                            MoneyText(amount: t.entryAmount),
                          ),
                          if (t.pnl != null)
                            _detailRowWidget(
                              cs,
                              'الربح/الخسارة',
                              MoneyText(amount: t.pnl!, showSign: true),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(height: SpacingTokens.md),
                    if (t.stopLoss != null || t.takeProfit != null)
                      AppCard(
                        padding: const EdgeInsets.all(SpacingTokens.md),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'إدارة المخاطر',
                              style: TypographyTokens.label(cs.onSurface),
                            ),
                            const SizedBox(height: SpacingTokens.md),
                            if (t.stopLoss != null)
                              _detailRow(
                                cs,
                                'وقف الخسارة',
                                '\$${t.stopLoss!.toStringAsFixed(6)}${t.stopLossPct != null ? ' (${t.stopLossPct!.abs().toStringAsFixed(2)}%)' : ''}',
                              ),
                            if (t.takeProfit != null)
                              _detailRow(
                                cs,
                                'جني الأرباح',
                                '\$${t.takeProfit!.toStringAsFixed(6)}${t.takeProfitPct != null ? ' (${t.takeProfitPct!.abs().toStringAsFixed(2)}%)' : ''}',
                              ),
                          ],
                        ),
                      ),
                    if (t.stopLoss != null || t.takeProfit != null)
                      const SizedBox(height: SpacingTokens.md),
                    AppCard(
                      padding: const EdgeInsets.all(SpacingTokens.md),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'التوقيت',
                            style: TypographyTokens.label(cs.onSurface),
                          ),
                          const SizedBox(height: SpacingTokens.md),
                          if (t.entryTime != null)
                            _detailRow(
                              cs,
                              'وقت الدخول',
                              _formatDateTime(t.entryTime!),
                            ),
                          if (t.exitTime != null)
                            _detailRow(
                              cs,
                              'وقت الخروج',
                              _formatDateTime(t.exitTime!),
                            ),
                        ],
                      ),
                    ),
                    if (t.isOpen) ...[
                      const SizedBox(height: SpacingTokens.md),
                      _CloseTradeButton(trade: t),
                      const SizedBox(height: SpacingTokens.md),
                    ],
                    if (t.strategy != null ||
                        t.notes != null ||
                        t.timeframe != null)
                      AppCard(
                        padding: const EdgeInsets.all(SpacingTokens.md),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'الاستراتيجية',
                              style: TypographyTokens.label(cs.onSurface),
                            ),
                            const SizedBox(height: SpacingTokens.md),
                            if (t.strategy != null)
                              _detailRow(cs, 'الاستراتيجية', t.strategy!),
                            if (t.timeframe != null)
                              _detailRow(cs, 'الإطار الزمني', t.timeframe!),
                            if (t.mlConfidence != null)
                              _detailRow(
                                cs,
                                'ثقة الذكاء الاصطناعي',
                                '${t.mlConfidence!.toStringAsFixed(1)}%',
                              ),
                            if (t.exitReason != null)
                              _detailRow(cs, 'سبب الإغلاق', t.exitReason!),
                            if (t.notes != null) ...[
                              const SizedBox(height: SpacingTokens.sm),
                              Text(
                                t.notes!,
                                style: TypographyTokens.bodySmall(
                                  cs.onSurface.withValues(alpha: 0.6),
                                ),
                              ),
                            ],
                          ],
                        ),
                      ),
                    const SizedBox(height: SpacingTokens.xl),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _detailRow(ColorScheme cs, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: SpacingTokens.sm),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TypographyTokens.bodySmall(
              cs.onSurface.withValues(alpha: 0.5),
            ),
          ),
          Text(value, style: TypographyTokens.mono(cs.onSurface, fontSize: 14)),
        ],
      ),
    );
  }

  Widget _detailRowWidget(ColorScheme cs, String label, Widget valueWidget) {
    return Padding(
      padding: const EdgeInsets.only(bottom: SpacingTokens.sm),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TypographyTokens.bodySmall(
              cs.onSurface.withValues(alpha: 0.5),
            ),
          ),
          valueWidget,
        ],
      ),
    );
  }

  String _formatDateTime(String iso) {
    try {
      final dt = DateTime.parse(iso);
      return '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')} '
          '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return iso;
    }
  }
}

class _CloseTradeButton extends ConsumerStatefulWidget {
  final TradeModel trade;
  const _CloseTradeButton({required this.trade});

  @override
  ConsumerState<_CloseTradeButton> createState() => _CloseTradeButtonState();
}

class _CloseTradeButtonState extends ConsumerState<_CloseTradeButton> {
  bool _isClosing = false;

  @override
  Widget build(BuildContext context) {
    final isAdmin = ref.watch(authProvider).isAdmin;
    if (!isAdmin) return const SizedBox.shrink();

    return AppButton(
      label: 'إغلاق الصفقة يدوياً (أدمن)',
      variant: AppButtonVariant.danger,
      icon: Icons.close,
      isLoading: _isClosing,
      onPressed: _isClosing ? null : _handleCloseTrade,
    );
  }

  Future<void> _handleCloseTrade() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('تأكيد الإغلاق'),
        content: Text(
          'هل أنت متأكد من إغلاق صفقة ${widget.trade.symbol} يدوياً؟\n'
          'سعر الدخول: \$${widget.trade.entryPrice.toStringAsFixed(6)}',
        ),
        actions: [
          AppButton(
            label: 'إلغاء',
            variant: AppButtonVariant.text,
            isFullWidth: false,
            onPressed: () => Navigator.pop(ctx, false),
          ),
          AppButton(
            label: 'إغلاق',
            variant: AppButtonVariant.danger,
            isFullWidth: false,
            onPressed: () => Navigator.pop(ctx, true),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    setState(() => _isClosing = true);
    try {
      final positionId = widget.trade.id ?? 0;
      final repo = ref.read(adminRepositoryProvider);
      await repo.closePosition(positionId, reason: 'MANUAL_CLOSE');
      if (mounted) {
        AppSnackbar.show(
          context,
          message: 'تم إغلاق صفقة ${widget.trade.symbol}',
          type: SnackType.success,
        );
        ref.invalidate(recentTradesProvider);
        ref.invalidate(activePositionsProvider);
        ref.invalidate(tradesListProvider);
        setState(() => _isClosing = false);
      }
    } catch (e) {
      if (mounted) {
        AppSnackbar.show(context, message: 'خطأ: $e', type: SnackType.error);
        setState(() => _isClosing = false);
      }
    }
  }
}

final _tradeDetailProvider = FutureProvider.family.autoDispose<TradeModel, int>(
  (ref, tradeId) async {
    final repo = ref.watch(tradesRepositoryProvider);
    return repo.getTradeById(tradeId);
  },
);

class _TradeDetailLoader extends ConsumerWidget {
  final int tradeId;

  const _TradeDetailLoader({required this.tradeId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final tradeAsync = ref.watch(_tradeDetailProvider(tradeId));

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: tradeAsync.when(
            loading: () => const LoadingShimmer(itemCount: 1, itemHeight: 400),
            error: (e, _) => ErrorState(
              message: e.toString(),
              onRetry: () => ref.invalidate(_tradeDetailProvider(tradeId)),
            ),
            data: (loadedTrade) => TradeDetailScreen(trade: loadedTrade),
          ),
        ),
      ),
    );
  }
}
