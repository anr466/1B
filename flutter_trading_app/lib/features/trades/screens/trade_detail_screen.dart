import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/models/trade_model.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
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
                    const SizedBox(height: SpacingTokens.md),
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
            loading: () => Column(
              children: const [
                AppScreenHeader(title: 'تفاصيل الصفقة', showBack: true),
                Expanded(child: Center(child: CircularProgressIndicator())),
              ],
            ),
            error: (e, _) => Column(
              children: [
                const AppScreenHeader(title: 'تفاصيل الصفقة', showBack: true),
                Expanded(
                  child: Center(
                    child: Text(
                      'تعذر تحميل الصفقة: $e',
                      style: TypographyTokens.body(cs.error),
                    ),
                  ),
                ),
              ],
            ),
            data: (loadedTrade) => TradeDetailScreen(trade: loadedTrade),
          ),
        ),
      ),
    );
  }
}
