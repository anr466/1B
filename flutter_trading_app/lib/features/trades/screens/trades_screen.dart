import 'dart:async';
import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/providers/trades_provider.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/empty_state.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/pnl_indicator.dart';
import 'package:trading_app/design/widgets/status_badge.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Trades Screen — قائمة الصفقات مع فلاتر + pagination
class TradesScreen extends ConsumerStatefulWidget {
  const TradesScreen({super.key});

  @override
  ConsumerState<TradesScreen> createState() => _TradesScreenState();
}

class _TradesScreenState extends ConsumerState<TradesScreen> {
  final _scrollController = ScrollController();
  String? _selectedFilter;
  int _touchedSection = -1;
  Timer? _debounceTimer;

  @override
  void initState() {
    super.initState();
    _scrollController.addListener(_onScroll);
    Future.microtask(() {
      ref.read(tradesListProvider.notifier).loadFirstPage();
    });
  }

  void _onScroll() {
    _debounceTimer?.cancel();
    if (_scrollController.position.pixels >=
        _scrollController.position.maxScrollExtent - 200) {
      _debounceTimer = Timer(const Duration(milliseconds: 500), () {
        ref.read(tradesListProvider.notifier).loadNextPage();
      });
    }
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  void _applyFilter(String? filter) {
    setState(() => _selectedFilter = filter);
    ref.read(tradesListProvider.notifier).loadFirstPage(statusFilter: filter);
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final state = ref.watch(tradesListProvider);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // ─── Header ──────────────────────
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  SpacingTokens.base,
                  SpacingTokens.sm,
                  SpacingTokens.base,
                  0,
                ),
                child: AppScreenHeader(
                  title: 'الصفقات',
                  padding: EdgeInsets.zero,
                ),
              ),
              const SizedBox(height: SpacingTokens.md),

              // ─── Filters ──────────────────────────
              SizedBox(
                height: 36,
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  padding: const EdgeInsets.symmetric(
                    horizontal: SpacingTokens.base,
                  ),
                  children: [
                    _filterChip(cs, null, 'الكل'),
                    _filterChip(cs, 'open', 'مفتوحة'),
                    _filterChip(cs, 'closed', 'مغلقة'),
                  ],
                ),
              ),
              const SizedBox(height: SpacingTokens.md),

              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: SpacingTokens.base,
                ),
                child: _buildTradesSummaryChart(context, state),
              ),
              const SizedBox(height: SpacingTokens.md),

              // ─── List ─────────────────────────────
              Expanded(
                child: RefreshIndicator(
                  color: cs.primary,
                  onRefresh: () =>
                      ref.read(tradesListProvider.notifier).refresh(),
                  child: _buildList(cs, state),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _filterChip(ColorScheme cs, String? value, String label) {
    final isSelected = _selectedFilter == value;
    return Padding(
      padding: const EdgeInsetsDirectional.only(start: SpacingTokens.sm),
      child: GestureDetector(
        onTap: () => _applyFilter(value),
        child: Container(
          padding: const EdgeInsets.symmetric(
            horizontal: SpacingTokens.md,
            vertical: SpacingTokens.xs,
          ),
          decoration: BoxDecoration(
            color: isSelected ? cs.primary : cs.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(SpacingTokens.radiusFull),
            border: Border.all(
              color: isSelected ? cs.primary : cs.outline,
              width: 1,
            ),
          ),
          child: Text(
            label,
            style: TypographyTokens.bodySmall(
              isSelected ? cs.onPrimary : cs.onSurface.withValues(alpha: 0.6),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildList(ColorScheme cs, TradesListState state) {
    if (state.isLoading && state.trades.isEmpty) {
      return const Padding(
        padding: EdgeInsets.all(SpacingTokens.base),
        child: LoadingShimmer(itemCount: 5, itemHeight: 72),
      );
    }

    if (state.trades.isEmpty) {
      return const EmptyState(message: 'لا توجد صفقات');
    }

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.symmetric(horizontal: SpacingTokens.base),
      itemCount: state.trades.length + (state.hasMore ? 1 : 0),
      itemBuilder: (_, i) {
        if (i >= state.trades.length) {
          return const Padding(
            padding: EdgeInsets.all(SpacingTokens.base),
            child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
          );
        }

        final trade = state.trades[i];
        final semantic = SemanticColors.of(context);
        final accentColor = trade.pnl == null
            ? null
            : (trade.pnl! > 0 ? semantic.positive : semantic.negative);
        return Padding(
          padding: const EdgeInsets.only(bottom: SpacingTokens.sm),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(SpacingTokens.radiusXl),
            child: Stack(
              children: [
                AppCard(
                  onTap: () =>
                      context.push(RouteNames.tradeDetail, extra: trade),
                  padding: const EdgeInsets.all(SpacingTokens.md),
                  borderRadius: SpacingTokens.radiusXl,
                  child: Row(
                    children: [
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Text(
                                  trade.symbol,
                                  style: TypographyTokens.body(
                                    cs.onSurface,
                                  ).copyWith(fontWeight: FontWeight.w600),
                                ),
                                const SizedBox(width: SpacingTokens.sm),
                                StatusBadge(
                                  text: trade.side,
                                  type: trade.side == 'BUY'
                                      ? BadgeType.success
                                      : BadgeType.error,
                                  showDot: false,
                                ),
                              ],
                            ),
                            const SizedBox(height: SpacingTokens.xs),
                            Text(
                              'مبلغ الدخول: \$${trade.entryAmount.toStringAsFixed(2)}',
                              style: TypographyTokens.caption(
                                cs.onSurface.withValues(alpha: 0.4),
                              ),
                            ),
                          ],
                        ),
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          if (trade.pnl != null)
                            PnlIndicator(
                              amount: trade.pnl!,
                              percentage: trade.pnlPct,
                              compact: true,
                              fontSize: 13,
                            )
                          else
                            StatusBadge(
                              text: trade.isOpen ? 'مفتوحة' : 'مغلقة',
                              type: trade.isOpen
                                  ? BadgeType.info
                                  : BadgeType.success,
                              showDot: false,
                            ),
                          if (trade.entryTime != null) ...[
                            const SizedBox(height: SpacingTokens.xs),
                            Text(
                              _formatArabicDate(trade.entryTime!),
                              style: TypographyTokens.caption(
                                cs.onSurface.withValues(alpha: 0.3),
                              ),
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),
                // ─── Leading accent bar (win/loss) ────────────
                if (accentColor != null)
                  Positioned(
                    right: 0,
                    top: 0,
                    bottom: 0,
                    child: Container(
                      width: 3.5,
                      decoration: BoxDecoration(
                        color: accentColor,
                        borderRadius: const BorderRadius.only(
                          topRight: Radius.circular(SpacingTokens.radiusXl),
                          bottomRight: Radius.circular(SpacingTokens.radiusXl),
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildTradesSummaryChart(BuildContext context, TradesListState state) {
    final cs = Theme.of(context).colorScheme;
    final semantic = SemanticColors.of(context);
    final trades = state.trades;

    if (trades.isEmpty) {
      return const SizedBox.shrink();
    }

    final closed = trades.where((t) => t.isClosed && t.pnl != null).toList();
    final open = trades.where((t) => t.isOpen).length;
    final wins = closed.where((t) => (t.pnl ?? 0) > 0).length;
    final losses = closed.where((t) => (t.pnl ?? 0) < 0).length;
    final neutral = closed.where((t) => (t.pnl ?? 0) == 0).length;
    final totalClosed = closed.length;
    final winRate = totalClosed > 0 ? (wins / totalClosed) * 100 : 0.0;

    final sections = <_TradePieSectionData>[
      _TradePieSectionData('رابحة', wins.toDouble(), semantic.positive),
      _TradePieSectionData('خاسرة', losses.toDouble(), semantic.negative),
      _TradePieSectionData('تعادل', neutral.toDouble(), cs.tertiary),
      _TradePieSectionData('مفتوحة', open.toDouble(), cs.secondary),
    ].where((s) => s.value > 0).toList();

    if (sections.isEmpty) {
      return const SizedBox.shrink();
    }

    final selectedSection =
        (_touchedSection >= 0 && _touchedSection < sections.length)
        ? sections[_touchedSection]
        : null;

    return AppCard(
      gradientColors: [
        Color.alphaBlend(
          cs.secondary.withValues(alpha: 0.09),
          cs.surfaceContainerHigh,
        ),
        cs.surfaceContainer,
      ],
      padding: const EdgeInsets.all(SpacingTokens.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('ملخص السجل (حلقي)', style: TypographyTokens.h3(cs.onSurface)),
          const SizedBox(height: SpacingTokens.xs),
          Text(
            'انقر على أي جزء لقراءة تفاصيله',
            style: TypographyTokens.caption(
              cs.onSurface.withValues(alpha: 0.55),
            ),
          ),
          const SizedBox(height: SpacingTokens.md),
          Row(
            children: [
              SizedBox(
                height: 136,
                width: 136,
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    PieChart(
                      PieChartData(
                        centerSpaceRadius: 34,
                        sectionsSpace: 3,
                        startDegreeOffset: -90,
                        pieTouchData: PieTouchData(
                          enabled: true,
                          touchCallback: (event, response) {
                            if (!event.isInterestedForInteractions ||
                                response?.touchedSection == null) {
                              if (_touchedSection != -1) {
                                setState(() => _touchedSection = -1);
                              }
                              return;
                            }
                            final idx =
                                response!.touchedSection!.touchedSectionIndex;
                            if (idx != _touchedSection) {
                              setState(() => _touchedSection = idx);
                            }
                          },
                        ),
                        sections: List.generate(sections.length, (i) {
                          final section = sections[i];
                          final isTouched = i == _touchedSection;
                          final percent = section.value / trades.length * 100;
                          return PieChartSectionData(
                            value: section.value,
                            color: section.color,
                            radius: isTouched ? 46 : 40,
                            title: '${percent.toStringAsFixed(0)}%',
                            titleStyle: TypographyTokens.caption(
                              cs.onSurface,
                            ).copyWith(fontWeight: FontWeight.w700),
                          );
                        }),
                      ),
                    ),
                    Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          selectedSection?.label ?? 'الكل',
                          style: TypographyTokens.caption(
                            cs.onSurface.withValues(alpha: 0.66),
                          ),
                        ),
                        Text(
                          '${(selectedSection?.value ?? trades.length.toDouble()).toInt()}',
                          style: TypographyTokens.h3(cs.onSurface),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: SpacingTokens.md),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    _legendRow(cs, sections, 0),
                    const SizedBox(height: SpacingTokens.xs),
                    if (sections.length > 1) _legendRow(cs, sections, 1),
                    if (sections.length > 2) ...[
                      const SizedBox(height: SpacingTokens.xs),
                      _legendRow(cs, sections, 2),
                    ],
                    if (sections.length > 3) ...[
                      const SizedBox(height: SpacingTokens.xs),
                      _legendRow(cs, sections, 3),
                    ],
                    const SizedBox(height: SpacingTokens.md),
                    Text(
                      'Win Rate: ${winRate.toStringAsFixed(1)}%',
                      style: TypographyTokens.body(
                        cs.onSurface,
                      ).copyWith(fontWeight: FontWeight.w700),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  String _formatArabicDate(String isoDate) {
    try {
      final dt = DateTime.parse(isoDate);
      return '${dt.day}/${dt.month}/${dt.year}';
    } catch (_) {
      return isoDate.split('T').first;
    }
  }

  Widget _legendRow(
    ColorScheme cs,
    List<_TradePieSectionData> sections,
    int index,
  ) {
    final item = sections[index];
    return Row(
      children: [
        Container(
          width: 9,
          height: 9,
          decoration: BoxDecoration(color: item.color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            '${item.label}: ${item.value.toInt()}',
            style: TypographyTokens.caption(
              cs.onSurface.withValues(alpha: 0.72),
            ),
          ),
        ),
      ],
    );
  }
}

class _TradePieSectionData {
  final String label;
  final double value;
  final Color color;

  const _TradePieSectionData(this.label, this.value, this.color);
}
