import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/models/portfolio_model.dart';
import 'package:trading_app/core/providers/admin_provider.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/privacy_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/providers/settings_provider.dart';
import 'package:trading_app/core/providers/trades_provider.dart';
import 'package:trading_app/design/icons/brand_logo.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/utils/responsive_utils.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_info_row.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/error_state.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/money_text.dart';
import 'package:trading_app/design/widgets/pnl_indicator.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';

/// Portfolio Screen — عرض تفصيلي للمحفظة
class PortfolioScreen extends ConsumerStatefulWidget {
  const PortfolioScreen({super.key});

  @override
  ConsumerState<PortfolioScreen> createState() => _PortfolioScreenState();
}

class _PortfolioScreenState extends ConsumerState<PortfolioScreen> {
  bool _isSwitchingMode = false;

  Future<void> _switchPortfolioMode(String mode) async {
    final cs = Theme.of(context).colorScheme;
    final isDemo = mode == 'demo';
    final label = isDemo ? 'التجريبي' : 'الحقيقي';

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          backgroundColor: cs.surfaceContainerHighest,
          title: Text(
            'التبديل للوضع $label',
            style: TypographyTokens.h3(cs.onSurface),
          ),
          content: Text(
            isDemo
                ? 'سيتم عرض بيانات المحفظة التجريبية. هل تريد المتابعة؟'
                : 'سيتم عرض بيانات المحفظة الحقيقية. تأكد من وجود مفاتيح Binance. هل تريد المتابعة؟',
            style: TypographyTokens.body(cs.onSurface.withValues(alpha: 0.7)),
          ),
          actions: [
            AppButton(
              label: 'إلغاء',
              variant: AppButtonVariant.text,
              isFullWidth: false,
              onPressed: () => Navigator.of(ctx).pop(false),
            ),
            AppButton(
              label: 'تبديل',
              variant: AppButtonVariant.primary,
              isFullWidth: false,
              onPressed: () => Navigator.of(ctx).pop(true),
            ),
          ],
        ),
      ),
    );

    if (confirmed != true) return;

    setState(() => _isSwitchingMode = true);
    try {
      final auth = ref.read(authProvider);
      if (auth.user == null) return;

      // Persist mode change to backend
      final settingsRepo = ref.read(settingsRepositoryProvider);
      await settingsRepo.updateTradingMode(auth.user!.id, mode);

      if (!mounted) return;

      // Update mode provider — triggers portfolio refresh
      ref.read(adminPortfolioModeProvider.notifier).state = mode;

      // Invalidate ALL dependent providers so they re-fetch with new mode
      ref.invalidate(accountTradingProvider);
      ref.invalidate(settingsDataProvider);
      ref.invalidate(dailyStatusProvider);
    } catch (_) {
      if (mounted) {
        AppSnackbar.show(context, message: 'فشل تبديل وضع المحفظة', type: SnackType.error);
      }
    } finally {
      if (mounted) setState(() => _isSwitchingMode = false);
    }
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
        : 'real';
    final pagePadding = ResponsiveUtils.pageHorizontalPadding(context);
    final maxWidth = ResponsiveUtils.maxContentWidth(context);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: SafeArea(
        child: RefreshIndicator(
            color: cs.primary,
            onRefresh: () async {
              ref.invalidate(accountTradingProvider);
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
                      _buildAdminModeSwitcher(context, ref, cs, portfolioMode),
                    ],

                    const SizedBox(height: SpacingTokens.base),

                    // ─── Balance Hero ─────────────────────
                    portfolio.when(
                      loading: () =>
                          const LoadingShimmer(itemCount: 1, itemHeight: 200),
                      error: (e, _) => ErrorState(
                        message: e.toString(),
                        onRetry: () => ref.invalidate(accountTradingProvider),
                      ),
                      data: (p) => AppCard(
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
                                            'إجمالي الربح/الخسارة',
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

                    // ─── Portfolio Breakdown (Bars) ────
                    portfolio.when(
                      loading: () =>
                          const LoadingShimmer(itemCount: 1, itemHeight: 120),
                      error: (e, _) => ErrorState(
                        message: e.toString(),
                        onRetry: () => ref.invalidate(accountTradingProvider),
                      ),
                      data: (p) =>
                          _buildPortfolioBreakdown(context, p, hideBalance),
                    ),

                    const SizedBox(height: SpacingTokens.base),

                    // ─── Open Positions Distribution ──
                    _buildOpenPositionsDistribution(context, ref, hideBalance),

                    const SizedBox(height: SpacingTokens.xl),
                  ],
                ),
              ),
            ),
          ),
        ),
    );
  }

  Widget _buildPortfolioBreakdown(
    BuildContext context,
    PortfolioModel p,
    bool hideBalance,
  ) {
    final cs = Theme.of(context).colorScheme;
    final semantic = SemanticColors.of(context);
    final total = p.currentBalance > 0 ? p.currentBalance : p.initialBalance;
    final availablePct =
        total > 0 ? ((p.availableBalance / total) * 100).clamp(0, 100) : 0.0;
    final reservedPct =
        total > 0 ? ((p.reservedBalance / total) * 100).clamp(0, 100) : 0.0;

    return AppCard(
      level: 0,
      padding: const EdgeInsets.all(SpacingTokens.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('هيكل المحفظة', style: TypographyTokens.h3(cs.onSurface)),
          const SizedBox(height: SpacingTokens.lg),
          // ── Available ──
          Row(
            children: [
              SizedBox(
                width: 50,
                child: Text(
                  'متاح',
                  style: TypographyTokens.caption(
                    cs.onSurface.withValues(alpha: 0.6),
                  ),
                ),
              ),
              const SizedBox(width: SpacingTokens.sm),
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(SpacingTokens.xs),
                  child: LinearProgressIndicator(
                    value: availablePct / 100,
                    backgroundColor: cs.surfaceContainerHighest,
                    color: semantic.positive,
                    minHeight: 14,
                  ),
                ),
              ),
              const SizedBox(width: SpacingTokens.sm),
              SizedBox(
                width: 100,
                child: MoneyText(
                  amount: p.availableBalance,
                  isSensitive: hideBalance,
                  fontSize: 13,
                ),
              ),
              const SizedBox(width: SpacingTokens.xs),
              SizedBox(
                width: 42,
                child: Text(
                  '${availablePct.toStringAsFixed(0)}%',
                  style: TypographyTokens.mono(
                    semantic.positive,
                    fontSize: 13,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.md),
          // ── Reserved ──
          Row(
            children: [
              SizedBox(
                width: 50,
                child: Text(
                  'محجوز',
                  style: TypographyTokens.caption(
                    cs.onSurface.withValues(alpha: 0.6),
                  ),
                ),
              ),
              const SizedBox(width: SpacingTokens.sm),
              Expanded(
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(SpacingTokens.xs),
                  child: LinearProgressIndicator(
                    value: reservedPct / 100,
                    backgroundColor: cs.surfaceContainerHighest,
                    color: semantic.info,
                    minHeight: 14,
                  ),
                ),
              ),
              const SizedBox(width: SpacingTokens.sm),
              SizedBox(
                width: 100,
                child: MoneyText(
                  amount: p.reservedBalance,
                  isSensitive: hideBalance,
                  fontSize: 13,
                ),
              ),
              const SizedBox(width: SpacingTokens.xs),
              SizedBox(
                width: 42,
                child: Text(
                  '${reservedPct.toStringAsFixed(0)}%',
                  style: TypographyTokens.mono(semantic.info, fontSize: 13),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildOpenPositionsDistribution(
    BuildContext context,
    WidgetRef ref,
    bool hideBalance,
  ) {
    final cs = Theme.of(context).colorScheme;
    final semantic = SemanticColors.of(context);
    final positions = ref.watch(activePositionsProvider);

    return positions.when(
      loading: () => const LoadingShimmer(itemCount: 1, itemHeight: 100),
      error: (e, _) => const SizedBox.shrink(),
      data: (list) {
        if (list.isEmpty) return const SizedBox.shrink();

        return AppCard(
          level: 0,
          padding: const EdgeInsets.all(SpacingTokens.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'توزيع الصفقات المفتوحة',
                style: TypographyTokens.h3(cs.onSurface),
              ),
              const SizedBox(height: SpacingTokens.md),
              ...list.map((pos) {
                final invested =
                    pos.positionSize ??
                    (pos.entryPrice * pos.quantity);
                return Padding(
                  padding: const EdgeInsets.only(bottom: SpacingTokens.sm),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Row(
                        children: [
                          Container(
                            width: 8,
                            height: 8,
                            decoration: BoxDecoration(
                              color: pos.pnl != null && pos.pnl! >= 0
                                  ? semantic.positive
                                  : pos.pnl != null && pos.pnl! < 0
                                  ? semantic.negative
                                  : cs.primary,
                              borderRadius: BorderRadius.circular(SpacingTokens.xxs),
                            ),
                          ),
                          const SizedBox(width: SpacingTokens.sm),
                          Text(
                            pos.symbol,
                            style: TypographyTokens.body(cs.onSurface),
                          ),
                        ],
                      ),
                      MoneyText(
                        amount: invested,
                        isSensitive: hideBalance,
                        fontSize: 14,
                      ),
                    ],
                  ),
                );
              }),
            ],
          ),
        );
      },
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
          padding: const EdgeInsets.symmetric(horizontal: SpacingTokens.sm, vertical: SpacingTokens.xxs),
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
      onTap: isSelected ? null : () => _switchPortfolioMode(mode),
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
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (_isSwitchingMode && isSelected)
              Padding(
                padding: const EdgeInsets.only(right: 4),
                child: SizedBox(
                  width: 12,
                  height: 12,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    color: cs.onPrimary,
                  ),
                ),
              ),
            Text(
              label,
              style:
                  TypographyTokens.caption(
                    isSelected ? cs.onPrimary : cs.onSurface.withValues(alpha: 0.6),
                  ).copyWith(
                    fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PortfolioBalanceValue extends StatelessWidget {
  final double amount;

  const _PortfolioBalanceValue({required this.amount});

  @override
  Widget build(BuildContext context) {
    return MoneyText(
      amount: amount,
      isSensitive: true,
      fontSize: 14,
    );
  }
}
