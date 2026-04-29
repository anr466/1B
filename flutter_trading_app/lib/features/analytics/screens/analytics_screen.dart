import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/trades_provider.dart';
import 'package:trading_app/design/icons/brand_logo.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/utils/responsive_utils.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/empty_state.dart';
import 'package:trading_app/design/widgets/error_state.dart';
import 'package:trading_app/design/widgets/financial_metric_tile.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/money_text.dart';
import 'package:trading_app/design/widgets/pnl_indicator.dart';

/// Analytics Screen — التحليلات والإحصائيات
class AnalyticsScreen extends ConsumerStatefulWidget {
  const AnalyticsScreen({super.key});

  @override
  ConsumerState<AnalyticsScreen> createState() => _AnalyticsScreenState();
}

class _AnalyticsScreenState extends ConsumerState<AnalyticsScreen> {
  void _refresh() {
    ref.invalidate(statsProvider);
    ref.invalidate(analyticsTradesProvider);
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final stats = ref.watch(statsProvider);
    final pagePadding = ResponsiveUtils.pageHorizontalPadding(context);
    final maxWidth = ResponsiveUtils.maxContentWidth(context);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: SafeArea(
        child: RefreshIndicator(
            color: cs.primary,
            onRefresh: () async {
              _refresh();
            },
            child: Center(
              child: ConstrainedBox(
                constraints: BoxConstraints(maxWidth: maxWidth),
                child: ListView(
                  padding: EdgeInsets.all(pagePadding),
                  children: [
                    const SizedBox(height: SpacingTokens.sm),
                    AppScreenHeader(
                      title: 'التحليلات',
                      padding: EdgeInsets.zero,
                    ),
                    const SizedBox(height: SpacingTokens.base),

                    stats.when(
                      loading: () =>
                          const LoadingShimmer(itemCount: 4, itemHeight: 90),
                      error: (e, _) => ErrorState(
                        message: e.toString(),
                        onRetry: () => ref.invalidate(statsProvider),
                      ),
                      data: (s) => Column(
                        children: [
                          // ─── Performance Summary ──────────
                          AppCard(
                            level: 0,
                            padding: const EdgeInsets.all(SpacingTokens.lg),
                            child: Stack(
                              children: [
                                Positioned(
                                  left: 8,
                                  top: 8,
                                  child: IgnorePointer(
                                    child: Opacity(
                                      opacity: 0.08,
                                      child: BrandLogo.mono(
                                        size: 140,
                                        monoColor: cs.onSurface,
                                      ),
                                    ),
                                  ),
                                ),
                                Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'ملخص الأداء',
                                      style: TypographyTokens.h3(cs.onSurface),
                                    ),
                                    const SizedBox(height: SpacingTokens.md),
                                    Row(
                                      children: [
                                        Expanded(
                                          child: _metric(
                                            cs,
                                            'إجمالي الربح/الخسارة',
                                            pnl: s.totalPnl,
                                          ),
                                        ),
                                        Expanded(
                                          child: _metric(
                                            cs,
                                            'الربح المحقق',
                                            pnl: s.realizedPnl,
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: SpacingTokens.md),
                                    Row(
                                      children: [
                                        Expanded(
                                          child: _metric(
                                            cs,
                                            'غير المحقق',
                                            pnl: s.unrealizedPnl,
                                          ),
                                        ),
                                        Expanded(
                                          child: _metric(
                                            cs,
                                            'متوسط الربح',
                                            amount: s.averagePnl,
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: SpacingTokens.md),
                                    Row(
                                      children: [
                                        Expanded(
                                          child: _metric(
                                            cs,
                                            'أفضل صفقة',
                                            amount: s.bestTrade,
                                          ),
                                        ),
                                        Expanded(
                                          child: _metric(
                                            cs,
                                            'أسوأ صفقة',
                                            amount: s.worstTrade,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: SpacingTokens.md),

                          // ─── Win/Loss ─────────────────────
                          Row(
                            children: [
                              Expanded(
                                child: FinancialMetricTile(
                                  label: 'نسبة الفوز',
                                  value: '${s.winRate.toStringAsFixed(1)}%',
                                  footer: _progressBar(
                                    cs,
                                    s.winRate / 100,
                                    cs.primary,
                                  ),
                                ),
                              ),
                              const SizedBox(width: SpacingTokens.sm),
                              Expanded(
                                child: Tooltip(
                                  message:
                                      'إجمالي الأرباح ÷ إجمالي الخسائر. '
                                      'قيمة > 1 تعني أن الأرباح أكبر من الخسائر. '
                                      'قيمة مثالية: 1.5+',
                                  child: FinancialMetricTile(
                                    label: 'معامل الربح',
                                    value: s.profitFactor.toStringAsFixed(2),
                                    footer: _progressBar(
                                      cs,
                                      (s.profitFactor / 3).clamp(0, 1),
                                      cs.primary,
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                          const SizedBox(height: SpacingTokens.md),

                          // ─── Equity Curve ───────────────────
                          _equityCurveCard(context, ref),
                          const SizedBox(height: SpacingTokens.md),

                          // ─── Trades Breakdown ─────────────
                          AppCard(
                            padding: const EdgeInsets.all(SpacingTokens.md),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'تفصيل الصفقات',
                                  style: TypographyTokens.h3(cs.onSurface),
                                ),
                                const SizedBox(height: SpacingTokens.md),
                                _breakdownRow(
                                  cs,
                                  'الصفقات المغلقة',
                                  '${s.closedTrades}',
                                ),
                                _breakdownRow(
                                  cs,
                                  'صفقات رابحة',
                                  '${s.winningTrades}',
                                  color: SemanticColors.of(context).positive,
                                ),
                                _breakdownRow(
                                  cs,
                                  'صفقات خاسرة',
                                  '${s.losingTrades}',
                                  color: SemanticColors.of(context).negative,
                                ),
                                if (s.activeTrades > 0)
                                  _breakdownRow(
                                    cs,
                                    'صفقات مفتوحة',
                                    '${s.activeTrades}',
                                    color: cs.secondary,
                                  ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: SpacingTokens.xl),
                  ],
                ),
              ),
            ),
          ),
        ),
    );
  }

  Widget _metric(ColorScheme cs, String label, {double? amount, double? pnl}) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.4)),
        ),
        const SizedBox(height: SpacingTokens.xs),
        if (pnl != null)
          PnlIndicator(amount: pnl, compact: true)
        else
          MoneyText(amount: amount ?? 0, fontSize: 15),
      ],
    );
  }

  Widget _progressBar(ColorScheme cs, double value, Color color) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(4),
      child: LinearProgressIndicator(
        value: value.clamp(0.0, 1.0),
        backgroundColor: cs.outline.withValues(alpha: 0.2),
        valueColor: AlwaysStoppedAnimation(color),
        minHeight: 6,
      ),
    );
  }

  Widget _breakdownRow(
    ColorScheme cs,
    String label,
    String value, {
    Color? color,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: SpacingTokens.sm),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TypographyTokens.body(cs.onSurface.withValues(alpha: 0.6)),
          ),
          Text(
            value,
            style: TypographyTokens.body(
              color ?? cs.onSurface,
            ).copyWith(fontWeight: FontWeight.w600),
          ),
        ],
      ),
    );
  }

  Widget _equityCurveCard(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final semantic = SemanticColors.of(context);
    final trades = ref.watch(analyticsTradesProvider);
    final portfolio = ref.watch(portfolioProvider);
    final referenceBalance = portfolio.maybeWhen(
      data: (p) => p.initialBalance > 0 ? p.initialBalance : p.currentBalance,
      orElse: () => 0.0,
    );

    return trades.when(
      loading: () => const LoadingShimmer(itemCount: 1, itemHeight: 190),
      error: (_, __) => const SizedBox.shrink(),
      data: (list) {
        if (referenceBalance <= 0) return const SizedBox.shrink();
        final closed = list.where((t) => t.pnl != null).toList();
        if (closed.length < 2) {
          return EmptyState(
            message: 'لا توجد بيانات كافية لرسم المنحنى',
            subtitle: 'مطلوب صفقتان على الأقل',
            icon: Icons.show_chart_rounded,
          );
        }

        final ordered = closed.reversed.toList();
        double cumulative = 0;
        final spots = <FlSpot>[];
        final dollarValues = <double>[];
        for (var i = 0; i < ordered.length; i++) {
          final tradePnl = ordered[i].pnl ?? 0;
          if (tradePnl.isNaN || tradePnl.isInfinite) continue;
          cumulative += tradePnl;
          dollarValues.add(cumulative);
          final cumulativePct = referenceBalance > 0
              ? (cumulative / referenceBalance) * 100
              : 0.0;
          spots.add(FlSpot(i.toDouble(), cumulativePct));
        }
        if (spots.length < 2) return const SizedBox.shrink();

        final ys = spots.map((e) => e.y).toList();
        final minY = ys.reduce((a, b) => a < b ? a : b);
        final maxY = ys.reduce((a, b) => a > b ? a : b);
        final range = (maxY - minY).abs();
        final yPadding = math.max(1.0, range * 0.18);
        final chartMinY = minY - yPadding;
        final chartMaxY = maxY + yPadding;
        final isUpTrend = spots.last.y >= spots.first.y;
        final chartColor = isUpTrend ? semantic.positive : semantic.negative;
        final lineGradient = LinearGradient(
          colors: [
            chartColor.withValues(alpha: 0.92),
            chartColor.withValues(alpha: 0.72),
          ],
        );
        final areaGradient = LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: [
            chartColor.withValues(alpha: 0.26),
            chartColor.withValues(alpha: 0.04),
          ],
        );
        final selectedIndex = spots.length ~/ 2;
        final horizontalInterval = _niceAxisInterval(chartMaxY - chartMinY);
        final verticalInterval = spots.length <= 4
            ? 1.0
            : (spots.length / 4).ceilToDouble();
        final barData = LineChartBarData(
          spots: spots,
          isCurved: true,
          curveSmoothness: 0.38,
          gradient: lineGradient,
          barWidth: 2.3,
          isStrokeCapRound: true,
          showingIndicators: [selectedIndex],
          dotData: const FlDotData(show: false),
          belowBarData: BarAreaData(show: true, gradient: areaGradient),
        );

        return AppCard(
          gradientColors: [
            Color.alphaBlend(
              cs.primary.withValues(alpha: 0.12),
              cs.surfaceContainerHigh,
            ),
            cs.surfaceContainer,
          ],
          padding: const EdgeInsets.all(SpacingTokens.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      'منحنى الأداء التراكمي',
                      style: TypographyTokens.h4(cs.onSurface),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: SpacingTokens.sm,
                      vertical: SpacingTokens.xxs,
                    ),
                    decoration: BoxDecoration(
                      color: chartColor.withValues(alpha: 0.10),
                      borderRadius: BorderRadius.circular(
                        SpacingTokens.radiusFull,
                      ),
                      border: Border.all(
                        color: chartColor.withValues(alpha: 0.18),
                      ),
                    ),
                    child: Text(
                      '${spots.last.y >= 0 ? '+' : ''}${spots.last.y.toStringAsFixed(2)}%',
                      style: TypographyTokens.mono(
                        chartColor,
                        fontSize: 12,
                      ).copyWith(fontWeight: FontWeight.w700),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: SpacingTokens.sm),
              SizedBox(
                height: 190,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(12),
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        cs.surfaceContainerHighest.withValues(alpha: 0.60),
                        cs.surfaceContainerLow.withValues(alpha: 0.24),
                      ],
                    ),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 8,
                    ),
                    child: LineChart(
                      LineChartData(
                        minX: 0,
                        maxX: (spots.length - 1).toDouble(),
                        minY: chartMinY,
                        maxY: chartMaxY,
                        gridData: FlGridData(
                          show: true,
                          drawVerticalLine: true,
                          horizontalInterval: horizontalInterval,
                          verticalInterval: verticalInterval,
                          getDrawingHorizontalLine: (_) => FlLine(
                            color: cs.outline.withValues(alpha: 0.15),
                            strokeWidth: 1,
                          ),
                          getDrawingVerticalLine: (_) => FlLine(
                            color: cs.outline.withValues(alpha: 0.12),
                            strokeWidth: 1,
                            dashArray: const [4, 4],
                          ),
                        ),
                        borderData: FlBorderData(show: false),
                        titlesData: FlTitlesData(
                          show: true,
                          topTitles: const AxisTitles(
                            sideTitles: SideTitles(showTitles: false),
                          ),
                          rightTitles: const AxisTitles(
                            sideTitles: SideTitles(showTitles: false),
                          ),
                          bottomTitles: const AxisTitles(
                            sideTitles: SideTitles(showTitles: false),
                          ),
                          leftTitles: AxisTitles(
                            sideTitles: SideTitles(
                              showTitles: true,
                              reservedSize: 48,
                              interval: horizontalInterval,
                              getTitlesWidget: (value, meta) {
                                final idx = value.round();
                                final dollarVal =
                                    (idx >= 0 && idx < dollarValues.length)
                                    ? dollarValues[idx]
                                    : null;
                                return Padding(
                                  padding: const EdgeInsetsDirectional.only(
                                    end: 6,
                                  ),
                                  child: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        '${value.toStringAsFixed(0)}%',
                                        style: TypographyTokens.caption(
                                          cs.onSurface.withValues(alpha: 0.45),
                                        ),
                                        textAlign: TextAlign.start,
                                      ),
                                      if (dollarVal != null)
                                        Text(
                                          '\$${dollarVal.toStringAsFixed(1)}',
                                          style: TypographyTokens.caption(
                                            cs.onSurface.withValues(alpha: 0.3),
                                          ),
                                          textAlign: TextAlign.start,
                                        ),
                                    ],
                                  ),
                                );
                              },
                            ),
                          ),
                        ),
                        lineTouchData: LineTouchData(
                          enabled: true,
                          handleBuiltInTouches: true,
                          touchTooltipData: LineTouchTooltipData(
                            getTooltipColor: (_) => cs.surfaceContainerHighest,
                            tooltipBorder: BorderSide(
                              color: chartColor.withValues(alpha: 0.7),
                              width: 1,
                            ),
                            fitInsideHorizontally: true,
                            fitInsideVertically: true,
                            getTooltipItems: (touchedSpots) => touchedSpots.map((
                              spot,
                            ) {
                              final pct = spot.y;
                              final idx = spot.x.round();
                              final dollarVal =
                                  (idx >= 0 && idx < dollarValues.length)
                                  ? dollarValues[idx]
                                  : 0.0;
                              return LineTooltipItem(
                                '${pct >= 0 ? '+' : ''}${pct.toStringAsFixed(2)}%\n\$${dollarVal.toStringAsFixed(2)}',
                                TypographyTokens.caption(
                                  cs.onSurface,
                                ).copyWith(fontWeight: FontWeight.w700),
                              );
                            }).toList(),
                          ),
                          getTouchedSpotIndicator: (barData, spotIndexes) {
                            return spotIndexes.map((_) {
                              return TouchedSpotIndicatorData(
                                FlLine(
                                  color: cs.outline.withValues(alpha: 0.32),
                                  strokeWidth: 1,
                                  dashArray: const [4, 3],
                                ),
                                FlDotData(
                                  show: true,
                                  getDotPainter: (_, __, ___, ____) =>
                                      FlDotCirclePainter(
                                        radius: 4.8,
                                        color: chartColor,
                                        strokeColor: cs.surface,
                                        strokeWidth: 1.8,
                                      ),
                                ),
                              );
                            }).toList();
                          },
                        ),
                        lineBarsData: [barData],
                        showingTooltipIndicators: [
                          ShowingTooltipIndicators([
                            LineBarSpot(barData, 0, spots[selectedIndex]),
                          ]),
                        ],
                        // ─── Zero reference line ───────────────
                        extraLinesData: ExtraLinesData(
                          horizontalLines: [
                            HorizontalLine(
                              y: 0,
                              color: cs.outline.withValues(alpha: 0.45),
                              strokeWidth: 1.0,
                              dashArray: const [5, 4],
                              label: HorizontalLineLabel(
                                show: true,
                                alignment: Alignment.topRight,
                                labelResolver: (_) => '0%',
                                style: TypographyTokens.caption(
                                  cs.outline.withValues(alpha: 0.55),
                                ).copyWith(fontSize: 9),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  double _niceAxisInterval(double span) {
    if (span <= 0 || span.isNaN || span.isInfinite) return 1;
    final raw = span / 4;
    final pow10 = math.pow(10, (math.log(raw) / math.ln10).floor()).toDouble();
    final n = raw / pow10;
    final step = n <= 1
        ? 1
        : n <= 2
        ? 2
        : n <= 5
        ? 5
        : 10;
    return step * pow10;
  }
}
