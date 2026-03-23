import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/models/portfolio_model.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/privacy_provider.dart';
import 'package:trading_app/design/icons/brand_logo.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/utils/responsive_utils.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_info_row.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/money_text.dart';
import 'package:trading_app/design/widgets/pnl_indicator.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Portfolio Screen — عرض تفصيلي للمحفظة
class PortfolioScreen extends ConsumerStatefulWidget {
  const PortfolioScreen({super.key});

  @override
  ConsumerState<PortfolioScreen> createState() => _PortfolioScreenState();
}

class _PortfolioScreenState extends ConsumerState<PortfolioScreen> {
  @override
  void initState() {
    super.initState();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final auth = ref.watch(authProvider);
    final isAdmin = auth.isAdmin;
    final portfolio = ref.watch(portfolioProvider);
    final hideBalance = ref.watch(balanceVisibilityProvider);
    final portfolioMode = isAdmin
        ? ref.watch(adminPortfolioModeProvider)
        : null;
    final pagePadding = ResponsiveUtils.pageHorizontalPadding(context);
    final maxWidth = ResponsiveUtils.maxContentWidth(context);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: RefreshIndicator(
            color: cs.primary,
            onRefresh: () async {
              ref.invalidate(portfolioProvider);
            },
            child: Center(
              child: ConstrainedBox(
                constraints: BoxConstraints(maxWidth: maxWidth),
                child: ListView(
                  padding: EdgeInsets.all(pagePadding),
                  children: [
                    const SizedBox(height: SpacingTokens.sm),
                    AppScreenHeader(
                      title: 'المحفظة',
                      padding: EdgeInsets.zero,
                      trailing: IconButton(
                        onPressed: () => ref
                            .read(balanceVisibilityProvider.notifier)
                            .toggle(),
                        icon: Icon(
                          hideBalance
                              ? Icons.visibility_off_rounded
                              : Icons.visibility_rounded,
                          color: cs.onSurface.withValues(alpha: 0.65),
                        ),
                      ),
                    ),

                    // ─── Admin: Demo | Real Switcher ────────────────
                    if (isAdmin) ...[
                      const SizedBox(height: SpacingTokens.sm),
                      _buildAdminModeSwitcher(context, ref, cs, portfolioMode!),
                    ],

                    const SizedBox(height: SpacingTokens.base),

                    // ─── Balance Hero ─────────────────────
                    portfolio.when(
                      loading: () =>
                          const LoadingShimmer(itemCount: 1, itemHeight: 200),
                      error: (e, _) => AppCard(
                        child: Center(
                          child: Text(
                            'خطأ: $e',
                            style: TypographyTokens.bodySmall(cs.error),
                          ),
                        ),
                      ),
                      data: (p) => AppCard(
                        level: 2,
                        borderRadius: SpacingTokens.radiusXxl,
                        gradientColors: [
                          cs.primary.withValues(alpha: 0.10),
                          cs.surface,
                        ],
                        padding: const EdgeInsets.all(SpacingTokens.lg),
                        child: Stack(
                          children: [
                            Positioned(
                              left: 8,
                              top: 8,
                              child: IgnorePointer(
                                child: Opacity(
                                  opacity: 0.11,
                                  child: BrandLogo.mono(
                                    size: 88,
                                    monoColor: cs.onSurface,
                                  ),
                                ),
                              ),
                            ),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'الرصيد الحالي',
                                  style: TypographyTokens.caption(
                                    cs.onSurface.withValues(alpha: 0.5),
                                  ),
                                ),
                                const SizedBox(height: SpacingTokens.xs),
                                MoneyText(
                                  amount: p.currentBalance,
                                  isHero: true,
                                  isSensitive: true,
                                ),
                                const SizedBox(height: SpacingTokens.lg),
                                AppInfoRow(
                                  label: 'الرصيد المتاح',
                                  valueWidget: _PortfolioBalanceValue(
                                    amount: p.availableBalance,
                                  ),
                                ),
                                AppInfoRow(
                                  label: 'الرصيد المحجوز',
                                  valueWidget: _PortfolioBalanceValue(
                                    amount: p.reservedBalance,
                                  ),
                                ),
                                AppInfoRow(
                                  label: 'الرصيد الابتدائي',
                                  valueWidget: _PortfolioBalanceValue(
                                    amount: p.initialBalance,
                                  ),
                                ),
                                const Divider(height: SpacingTokens.lg),
                                Row(
                                  children: [
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            'إجمالي الربح الحالي',
                                            style: TypographyTokens.caption(
                                              cs.onSurface.withValues(
                                                alpha: 0.4,
                                              ),
                                            ),
                                          ),
                                          const SizedBox(
                                            height: SpacingTokens.xs,
                                          ),
                                          PnlIndicator(
                                            amount: p.totalPnl,
                                            percentage: p.totalPnlPct,
                                          ),
                                        ],
                                      ),
                                    ),
                                    const SizedBox(width: SpacingTokens.sm),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            'الربح غير المحقق',
                                            style: TypographyTokens.caption(
                                              cs.onSurface.withValues(
                                                alpha: 0.4,
                                              ),
                                            ),
                                          ),
                                          const SizedBox(
                                            height: SpacingTokens.xs,
                                          ),
                                          PnlIndicator(
                                            amount: p.unrealizedPnl,
                                            percentage: p.unrealizedPnlPct,
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: SpacingTokens.md),
                                Row(
                                  children: [
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            'الربح المحقق',
                                            style: TypographyTokens.caption(
                                              cs.onSurface.withValues(
                                                alpha: 0.4,
                                              ),
                                            ),
                                          ),
                                          const SizedBox(
                                            height: SpacingTokens.xs,
                                          ),
                                          PnlIndicator(
                                            amount: p.realizedPnl,
                                            percentage: p.realizedPnlPct,
                                          ),
                                        ],
                                      ),
                                    ),
                                    const SizedBox(width: SpacingTokens.sm),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.start,
                                        children: [
                                          Text(
                                            'ربح اليوم',
                                            style: TypographyTokens.caption(
                                              cs.onSurface.withValues(
                                                alpha: 0.4,
                                              ),
                                            ),
                                          ),
                                          const SizedBox(
                                            height: SpacingTokens.xs,
                                          ),
                                          PnlIndicator(
                                            amount: p.dailyPnl,
                                            percentage: p.dailyPnlPct,
                                          ),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    ),

                    const SizedBox(height: SpacingTokens.base),

                    // ─── Portfolio Breakdown (Column Chart) ─────
                    portfolio.when(
                      loading: () =>
                          const LoadingShimmer(itemCount: 1, itemHeight: 220),
                      error: (_, __) => const SizedBox.shrink(),
                      data: (p) => _buildPortfolioBreakdownChart(
                        context,
                        p,
                        hideBalance,
                      ),
                    ),

                    const SizedBox(height: SpacingTokens.xl),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildPortfolioBreakdownChart(
    BuildContext context,
    PortfolioModel p,
    bool hideBalance,
  ) {
    final cs = Theme.of(context).colorScheme;
    final semantic = SemanticColors.of(context);

    final total = p.currentBalance > 0 ? p.currentBalance : p.initialBalance;
    final availablePct = total > 0 ? (p.availableBalance / total) * 100 : 0.0;
    final reservedPct = total > 0 ? (p.reservedBalance / total) * 100 : 0.0;

    final sections = <PieChartSectionData>[
      if (p.availableBalance > 0)
        PieChartSectionData(
          value: p.availableBalance,
          title: '${availablePct.toStringAsFixed(0)}%',
          color: semantic.positive,
          radius: 55,
          titleStyle: TypographyTokens.caption(
            cs.surface,
          ).copyWith(fontWeight: FontWeight.w700, color: cs.surface),
        ),
      if (p.reservedBalance > 0)
        PieChartSectionData(
          value: p.reservedBalance,
          title: '${reservedPct.toStringAsFixed(0)}%',
          color: semantic.info,
          radius: 55,
          titleStyle: TypographyTokens.caption(
            cs.surface,
          ).copyWith(fontWeight: FontWeight.w700, color: cs.surface),
        ),
    ];

    if (sections.isEmpty) {
      sections.add(
        PieChartSectionData(
          value: 1,
          title: '',
          color: cs.surfaceContainerHighest,
          radius: 55,
        ),
      );
    }

    return AppCard(
      gradientColors: [
        Color.alphaBlend(
          cs.primary.withValues(alpha: 0.1),
          cs.surfaceContainerHigh,
        ),
        cs.surfaceContainer,
      ],
      padding: const EdgeInsets.all(SpacingTokens.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('هيكل المحفظة', style: TypographyTokens.h3(cs.onSurface)),
          const SizedBox(height: SpacingTokens.md),
          Row(
            children: [
              Expanded(
                child: SizedBox(
                  height: 150,
                  child: PieChart(
                    PieChartData(
                      sections: sections,
                      centerSpaceRadius: 35,
                      sectionsSpace: 2,
                      pieTouchData: PieTouchData(
                        touchCallback: (event, response) {},
                      ),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: SpacingTokens.md),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _legendItem(
                    'متاح',
                    p.availableBalance,
                    semantic.positive,
                    cs,
                  ),
                  const SizedBox(height: SpacingTokens.sm),
                  _legendItem(
                    'إجمالي الربح',
                    p.totalPnl,
                    p.totalPnl >= 0 ? semantic.positive : semantic.negative,
                    cs,
                  ),
                  const SizedBox(height: SpacingTokens.sm),
                  _legendItem(
                    'غير محقق',
                    p.unrealizedPnl,
                    p.unrealizedPnl >= 0 ? semantic.info : semantic.negative,
                    cs,
                  ),
                  const SizedBox(height: SpacingTokens.sm),
                  _legendItem(
                    'محجوز',
                    p.reservedBalance,
                    SemanticColors.of(context).info,
                    cs,
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _legendItem(String label, double value, Color color, ColorScheme cs) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(2),
          ),
        ),
        const SizedBox(width: 6),
        Flexible(
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '$label: ',
                style: TypographyTokens.caption(
                  cs.onSurface.withValues(alpha: 0.45),
                ),
              ),
              _PortfolioBalanceValue(amount: value, fontSize: 11),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildAdminModeSwitcher(
    BuildContext context,
    WidgetRef ref,
    ColorScheme cs,
    String currentMode,
  ) {
    return Row(
      children: [
        _modeChip(cs, ref, 'تجريبي', 'demo', currentMode),
        const SizedBox(width: SpacingTokens.sm),
        _modeChip(cs, ref, 'حقيقي', 'real', currentMode),
        const Spacer(),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(
            color: cs.primary.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(SpacingTokens.radiusBadge),
            border: Border.all(
              color: cs.primary.withValues(alpha: 0.22),
              width: 0.6,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.admin_panel_settings_outlined,
                size: 12,
                color: cs.primary.withValues(alpha: 0.7),
              ),
              const SizedBox(width: 4),
              Text(
                'أدمن',
                style: TypographyTokens.caption(
                  cs.primary.withValues(alpha: 0.7),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _modeChip(
    ColorScheme cs,
    WidgetRef ref,
    String label,
    String mode,
    String currentMode,
  ) {
    final isSelected = currentMode == mode;
    return GestureDetector(
      onTap: () => context.push(RouteNames.tradingSettings),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        padding: const EdgeInsets.symmetric(
          horizontal: SpacingTokens.md,
          vertical: SpacingTokens.xs,
        ),
        decoration: BoxDecoration(
          color: isSelected ? cs.primary : cs.surfaceContainerHigh,
          borderRadius: BorderRadius.circular(SpacingTokens.radiusBadge),
          border: Border.all(
            color: isSelected ? cs.primary : cs.outline.withValues(alpha: 0.3),
            width: 0.8,
          ),
        ),
        child: Text(
          label,
          style:
              TypographyTokens.caption(
                isSelected ? cs.onPrimary : cs.onSurface.withValues(alpha: 0.6),
              ).copyWith(
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
              ),
        ),
      ),
    );
  }
}

class _PortfolioBalanceValue extends StatelessWidget {
  final double amount;
  final double? fontSize;

  const _PortfolioBalanceValue({required this.amount, this.fontSize});

  @override
  Widget build(BuildContext context) {
    return MoneyText(
      amount: amount,
      isSensitive: true,
      fontSize: fontSize ?? 14,
    );
  }
}
