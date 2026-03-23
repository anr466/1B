import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/models/trade_model.dart';
import 'package:trading_app/core/providers/admin_provider.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/privacy_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/providers/trades_provider.dart';
import 'package:trading_app/design/icons/brand_icons.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/icons/brand_logo.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/utils/responsive_utils.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/empty_state.dart';
import 'package:trading_app/design/widgets/error_state.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/money_text.dart';
import 'package:trading_app/design/widgets/pnl_indicator.dart';
import 'package:trading_app/design/widgets/app_icon_button.dart';
import 'package:trading_app/design/widgets/status_badge.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Dashboard Screen — الشاشة الرئيسية
class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  void _refresh() {
    refreshTradingData(ref);
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final auth = ref.watch(authProvider);
    final pagePadding = ResponsiveUtils.pageHorizontalPadding(context);
    final maxWidth = ResponsiveUtils.maxContentWidth(context);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        key: const Key('dashboard_screen'),
        backgroundColor: cs.surface,
        body: SafeArea(
          child: RefreshIndicator(
            key: const Key('dashboard_refresh'),
            color: cs.primary,
            onRefresh: () async => _refresh(),
            child: Center(
              child: ConstrainedBox(
                constraints: BoxConstraints(maxWidth: maxWidth),
                child: ListView(
                  padding: EdgeInsets.only(
                    left: pagePadding,
                    right: pagePadding,
                    top: SpacingTokens.sm,
                    bottom: SpacingTokens.xl,
                  ),
                  children: [
                    // ─── Header ──────────────────────────────
                    _buildHeader(context, ref, auth),
                    const SizedBox(height: SpacingTokens.md),

                    // ─── Balance Card (Hero) ─────────────────
                    _buildBalanceCard(context, ref),
                    const SizedBox(height: SpacingTokens.md),

                    if (!auth.isAdmin) ...[
                      _buildAccountTradingStrip(context, ref),
                      const SizedBox(height: SpacingTokens.md),
                    ],

                    // ─── System Status Strip (admin only) ────
                    if (auth.isAdmin) ...[
                      _buildSystemStatusStrip(context, ref),
                      const SizedBox(height: SpacingTokens.md),
                    ],

                    // ─── Recent Trades ───────────────────────
                    _buildRecentTradesSection(context, ref),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────
  //  HEADER
  // ──────────────────────────────────────────────────────────────
  Widget _buildHeader(BuildContext context, WidgetRef ref, AuthState auth) {
    final cs = Theme.of(context).colorScheme;
    final hideBalance = ref.watch(balanceVisibilityProvider);
    final name = auth.user?.name ?? auth.user?.username ?? '';

    return Row(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        // Avatar / Initials circle
        Container(
          width: 40,
          height: 40,
          decoration: BoxDecoration(
            color: cs.primary.withValues(alpha: 0.15),
            shape: BoxShape.circle,
            border: Border.all(
              color: cs.primary.withValues(alpha: 0.25),
              width: 1,
            ),
          ),
          child: Center(
            child: Text(
              name.isNotEmpty ? name[0].toUpperCase() : 'U',
              style: TypographyTokens.body(
                cs.primary,
              ).copyWith(fontWeight: FontWeight.w700),
            ),
          ),
        ),
        const SizedBox(width: SpacingTokens.sm),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('مرحباً، $name', style: TypographyTokens.h3(cs.onSurface)),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                const BrandLogo.mini(size: 14),
                const SizedBox(width: 4),
                Text(
                  'TRADING',
                  style: TypographyTokens.caption(
                    cs.onSurface.withValues(alpha: 0.50),
                  ).copyWith(letterSpacing: 2.0, fontSize: 10),
                ),
              ],
            ),
          ],
        ),
        const Spacer(),
        AppIconButton(
          icon: hideBalance
              ? Icons.visibility_off_rounded
              : Icons.visibility_rounded,
          onTap: () => ref.read(balanceVisibilityProvider.notifier).toggle(),
          color: cs.onSurface.withValues(alpha: 0.5),
        ),
        const SizedBox(width: SpacingTokens.xs),
        AppIconButton(
          child: BrandIcon(
            BrandIcons.bell,
            size: 22,
            color: cs.onSurface.withValues(alpha: 0.5),
          ),
          onTap: () => context.push(RouteNames.notifications),
        ),
      ],
    );
  }

  // ──────────────────────────────────────────────────────────────
  //  HERO BALANCE CARD
  // ──────────────────────────────────────────────────────────────
  Widget _buildBalanceCard(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final isDark = cs.brightness == Brightness.dark;
    final portfolio = ref.watch(portfolioProvider);
    final auth = ref.watch(authProvider);
    final portfolioMode = auth.isAdmin
        ? ref.watch(adminPortfolioModeProvider)
        : 'real';

    return portfolio.when(
      loading: () => const LoadingShimmer(itemCount: 1, itemHeight: 150),
      error: (e, _) => AppCard(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(SpacingTokens.lg),
            child: Text(
              'خطأ في تحميل المحفظة',
              style: TypographyTokens.bodySmall(cs.error),
            ),
          ),
        ),
      ),
      data: (p) {
        final modeLabel = portfolioMode == 'real' ? 'حقيقي' : 'تجريبي';

        return AppCard(
          level: 2,
          borderRadius: SpacingTokens.radiusXxl,
          gradientColors: [cs.primary.withValues(alpha: 0.10), cs.surface],
          padding: const EdgeInsets.all(SpacingTokens.lg),
          child: Stack(
            children: [
              Positioned(
                left: 8,
                top: 8,
                child: IgnorePointer(
                  child: Opacity(
                    opacity: 0.11,
                    child: BrandLogo.mono(size: 88, monoColor: cs.onSurface),
                  ),
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: Text(
                          'الرصيد الحالي',
                          style: TypographyTokens.caption(
                            cs.onSurface.withValues(alpha: 0.5),
                          ),
                        ),
                      ),
                      if (portfolioMode == 'real')
                        StatusBadge(
                          text: 'وضع $modeLabel',
                          type: BadgeType.error,
                          showDot: false,
                        ),
                    ],
                  ),
                  const SizedBox(height: SpacingTokens.xs),
                  MoneyText(
                    amount: p.currentBalance,
                    isHero: true,
                    isSensitive: true,
                  ),
                  const SizedBox(height: SpacingTokens.lg),
                  Divider(
                    color: cs.outline.withValues(alpha: isDark ? 0.14 : 0.10),
                    height: 1,
                  ),
                  const SizedBox(height: SpacingTokens.md),
                  Row(
                    children: [
                      Expanded(
                        child: _BalanceSummaryMetric(
                          label: 'إجمالي الربح الحالي',
                          amount: p.totalPnl,
                          percentage: p.totalPnlPct,
                        ),
                      ),
                      const SizedBox(width: SpacingTokens.sm),
                      Expanded(
                        child: _BalanceSummaryMetric(
                          label: 'غير المحقق',
                          amount: p.unrealizedPnl,
                          percentage: p.unrealizedPnlPct,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  // ──────────────────────────────────────────────────────────────
  //  ACCOUNT TRADING STRIP (user quick toggle)
  // ──────────────────────────────────────────────────────────────
  Widget _buildAccountTradingStrip(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final tradingState = ref.watch(accountTradingProvider);

    if (tradingState.enabled == null && tradingState.isLoading) {
      return const LoadingShimmer(itemCount: 1, itemHeight: 56);
    }

    final enabled = tradingState.enabled ?? false;
    final canEnable = tradingState.systemRunning;
    final statusTone = enabled ? cs.primary : cs.tertiary;
    final badgeType = enabled ? BadgeType.success : BadgeType.warning;
    final label = enabled ? 'مفعل' : 'متوقف';
    final subtitle = !canEnable && !enabled
        ? 'تعذر التفعيل لأن النظام العام ${tradingState.systemState == 'ERROR' ? 'في حالة خطأ' : 'متوقف'}'
        : enabled
        ? 'النظام ينفذ صفقات جديدة'
        : 'التداول معطل لحسابك';
    final isDark = cs.brightness == Brightness.dark;

    return IntrinsicHeight(
      child: Container(
        decoration: BoxDecoration(
          color: isDark ? cs.surfaceContainerHigh : cs.surfaceContainerLow,
          borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
          border: Border.all(
            color: cs.outline.withValues(alpha: isDark ? 0.18 : 0.12),
            width: 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 4,
              decoration: BoxDecoration(
                color: statusTone,
                borderRadius: const BorderRadius.only(
                  topRight: Radius.circular(SpacingTokens.radiusMd),
                  bottomRight: Radius.circular(SpacingTokens.radiusMd),
                ),
              ),
            ),
            const SizedBox(width: SpacingTokens.sm),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: SpacingTokens.md),
              child: BrandIcon(BrandIcons.shield, size: 16, color: statusTone),
            ),
            const SizedBox(width: SpacingTokens.xs),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: SpacingTokens.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: SpacingTokens.xs,
                      runSpacing: 4,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        Text(
                          'حالة التداول',
                          style: TypographyTokens.bodySmall(
                            cs.onSurface.withValues(alpha: 0.8),
                          ).copyWith(fontWeight: FontWeight.w600),
                        ),
                        StatusBadge(text: label, type: badgeType),
                      ],
                    ),
                    const SizedBox(height: 2),
                    Text(
                      subtitle,
                      style: TypographyTokens.caption(
                        cs.onSurface.withValues(alpha: 0.45),
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: SpacingTokens.sm),
              child: tradingState.isLoading
                  ? SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: statusTone,
                      ),
                    )
                  : Switch(
                      value: enabled,
                      onChanged: (!canEnable && !enabled)
                          ? null
                          : (value) =>
                                _toggleAccountTrading(context, ref, value),
                      activeThumbColor: cs.primary,
                    ),
            ),
          ],
        ),
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────
  //  SYSTEM STATUS STRIP (admin only) — compact, tappable
  // ──────────────────────────────────────────────────────────────
  Widget _buildSystemStatusStrip(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final status = ref.watch(tradingCycleLiveProvider);

    return status.when(
      loading: () => const LoadingShimmer(itemCount: 1, itemHeight: 56),
      error: (_, __) => const SizedBox.shrink(),
      data: (s) {
        final badgeType = s.isEffectivelyRunning
            ? BadgeType.success
            : s.isRunning
            ? BadgeType.warning
            : s.isError
            ? BadgeType.error
            : BadgeType.warning;
        final label = s.isEffectivelyRunning
            ? 'يعمل فعلياً'
            : s.isRunning
            ? 'يعمل'
            : s.isError
            ? 'خطأ'
            : 'متوقف';
        final statusTone = switch (badgeType) {
          BadgeType.success => cs.primary,
          BadgeType.error => cs.error,
          BadgeType.warning => cs.tertiary,
          BadgeType.info => cs.secondary,
        };
        final isDark = cs.brightness == Brightness.dark;
        final cycleColor = s.isCycleActive
            ? cs.primary
            : cs.onSurface.withValues(alpha: 0.3);
        final modeBadgeType = s.tradingMode == 'real'
            ? BadgeType.error
            : BadgeType.warning;
        final modeLabel = s.tradingMode == 'real' ? 'حقيقي' : 'تجريبي';

        return GestureDetector(
          onTap: () => context.push(RouteNames.tradingControl),
          child: IntrinsicHeight(
            child: Container(
              decoration: BoxDecoration(
                color: isDark
                    ? cs.surfaceContainerHigh
                    : cs.surfaceContainerLow,
                borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
                border: Border.all(
                  color: cs.outline.withValues(alpha: isDark ? 0.18 : 0.12),
                  width: 1,
                ),
              ),
              child: Row(
                children: [
                  // Colored start accent bar — fills full strip height
                  Container(
                    width: 4,
                    decoration: BoxDecoration(
                      color: statusTone,
                      borderRadius: const BorderRadius.only(
                        topRight: Radius.circular(SpacingTokens.radiusMd),
                        bottomRight: Radius.circular(SpacingTokens.radiusMd),
                      ),
                    ),
                  ),
                  const SizedBox(width: SpacingTokens.sm),
                  // Icon
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      vertical: SpacingTokens.md,
                    ),
                    child: BrandIcon(
                      BrandIcons.shield,
                      size: 16,
                      color: statusTone,
                    ),
                  ),
                  const SizedBox(width: SpacingTokens.xs),
                  // Texts
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        vertical: SpacingTokens.md,
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Wrap(
                            spacing: SpacingTokens.xs,
                            runSpacing: 4,
                            crossAxisAlignment: WrapCrossAlignment.center,
                            children: [
                              Text(
                                'حالة النظام',
                                style: TypographyTokens.bodySmall(
                                  cs.onSurface.withValues(alpha: 0.8),
                                ).copyWith(fontWeight: FontWeight.w600),
                              ),
                              StatusBadge(text: label, type: badgeType),
                              StatusBadge(
                                text: 'وضع $modeLabel',
                                type: modeBadgeType,
                                showDot: false,
                              ),
                            ],
                          ),
                          const SizedBox(height: 2),
                          Row(
                            children: [
                              Container(
                                width: 6,
                                height: 6,
                                decoration: BoxDecoration(
                                  color: cycleColor,
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 4),
                              Expanded(
                                child: Text(
                                  'دورة #${s.totalCycles} · ${s.lastCycleLabel}',
                                  style: TypographyTokens.caption(
                                    cs.onSurface.withValues(alpha: 0.45),
                                  ),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: SpacingTokens.sm,
                    ),
                    child: Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          'إدارة',
                          style: TypographyTokens.caption(
                            cs.onSurface.withValues(alpha: 0.6),
                          ),
                        ),
                        const SizedBox(width: 4),
                        Icon(
                          Icons.arrow_forward_ios_rounded,
                          size: 14,
                          color: cs.onSurface.withValues(alpha: 0.45),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }

  Future<void> _toggleAccountTrading(
    BuildContext context,
    WidgetRef ref,
    bool enabled,
  ) async {
    await toggleTradingWithBiometric(
      ref: ref,
      enabled: enabled,
      biometricAuth: (reason) =>
          ref.read(biometricServiceProvider).authenticate(reason: reason),
      showMessage: (message, type) =>
          AppSnackbar.show(context, message: message, type: type),
    );
  }

  // ──────────────────────────────────────────────────────────────
  //  RECENT TRADES SECTION
  // ──────────────────────────────────────────────────────────────
  Widget _buildRecentTradesSection(BuildContext context, WidgetRef ref) {
    return Column(
      children: [
        _DashTitle(
          title: 'آخر الصفقات',
          actionText: 'عرض الكل',
          onAction: () => context.go(RouteNames.trades),
        ),
        const SizedBox(height: SpacingTokens.sm),
        _buildRecentTrades(context, ref),
      ],
    );
  }

  Widget _buildRecentTrades(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final activeTrades = ref.watch(activePositionsProvider);
    final recentTrades = ref.watch(recentTradesProvider);

    if (recentTrades.isLoading && activeTrades.isLoading) {
      return const LoadingShimmer(itemCount: 3, itemHeight: 60);
    }

    if (recentTrades.hasError && activeTrades.hasError) {
      return ErrorState(
        message: 'تعذر تحميل الصفقات',
        onRetry: () {
          ref.invalidate(recentTradesProvider);
          ref.invalidate(activePositionsProvider);
        },
      );
    }

    // recentTradesProvider is the unified source — returns ALL trades (open+closed)
    // respecting admin demo/real mode via adminPortfolioModeProvider
    final allTrades = recentTrades.valueOrNull ?? const <TradeModel>[];
    // Prefer live PnL from activePositionsProvider for open trades when available
    final livePositions = activeTrades.valueOrNull ?? const <TradeModel>[];
    final liveMap = {for (final t in livePositions) t.id: t};
    final openList = allTrades
        .where((t) => t.isOpen)
        .map((t) => liveMap[t.id] ?? t)
        .toList();
    final closedList = allTrades.where((t) => !t.isOpen).toList();
    final hybridItems = _buildHybridTradeItems(openList, closedList);

    if (hybridItems.isEmpty) {
      return AppCard(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: SpacingTokens.xl),
          child: EmptyState(
            message: 'لا توجد صفقات حديثة',
            icon: Icons.receipt_long_outlined,
          ),
        ),
      );
    }

    final openCount = openList.length;
    final closedCount = closedList.length;

    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.md),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: _HybridSummaryChip(
                  label: 'مفتوحة الآن',
                  value: '$openCount',
                  tone: cs.primary,
                ),
              ),
              const SizedBox(width: SpacingTokens.sm),
              Expanded(
                child: _HybridSummaryChip(
                  label: 'أغلقت مؤخرًا',
                  value: '$closedCount',
                  tone: cs.secondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.md),
          ...hybridItems.asMap().entries.map((entry) {
            final index = entry.key;
            final item = entry.value;
            return Padding(
              padding: EdgeInsets.only(
                bottom: index == hybridItems.length - 1 ? 0 : SpacingTokens.xs,
              ),
              child: _HybridTradeTile(trade: item),
            );
          }),
        ],
      ),
    );
  }

  List<TradeModel> _buildHybridTradeItems(
    List<TradeModel> openTrades,
    List<TradeModel> closedTrades,
  ) {
    const maxItems = 5;
    final limitedOpen = openTrades.take(3).toList();
    final remainingSlots = (maxItems - limitedOpen.length).clamp(0, maxItems);
    final limitedClosed = closedTrades
        .take(remainingSlots == 0 ? 2 : remainingSlots)
        .toList();
    return [...limitedOpen, ...limitedClosed];
  }
}

// ──────────────────────────────────────────────────────────────
//  PRIVATE WIDGETS
// ──────────────────────────────────────────────────────────────

class _HybridSummaryChip extends StatelessWidget {
  final String label;
  final String value;
  final Color tone;

  const _HybridSummaryChip({
    required this.label,
    required this.value,
    required this.tone,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.sm,
        vertical: SpacingTokens.sm,
      ),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
        border: Border.all(color: tone.withValues(alpha: 0.14), width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TypographyTokens.caption(
              cs.onSurface.withValues(alpha: 0.55),
            ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: TypographyTokens.body(
              cs.onSurface,
            ).copyWith(fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}

class _HybridTradeTile extends StatelessWidget {
  final TradeModel trade;

  const _HybridTradeTile({required this.trade});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final semantic = SemanticColors.of(context);
    final sideColor = trade.isBuy ? semantic.positive : semantic.negative;

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => context.push(RouteNames.tradeDetail, extra: trade),
        borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
        child: IntrinsicHeight(
          child: Container(
            padding: const EdgeInsets.symmetric(vertical: SpacingTokens.sm),
            decoration: BoxDecoration(
              color: cs.surfaceContainerLow,
              borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
              border: Border.all(
                color: cs.outline.withValues(alpha: 0.10),
                width: 1,
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Container(
                  width: 4,
                  decoration: BoxDecoration(
                    color: sideColor,
                    borderRadius: const BorderRadius.only(
                      topRight: Radius.circular(SpacingTokens.radiusMd),
                      bottomRight: Radius.circular(SpacingTokens.radiusMd),
                    ),
                  ),
                ),
                const SizedBox(width: SpacingTokens.sm),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              trade.symbol,
                              style: TypographyTokens.body(
                                cs.onSurface,
                              ).copyWith(fontWeight: FontWeight.w700),
                            ),
                          ),
                          StatusBadge(
                            text: trade.isOpen ? 'مفتوحة' : 'مغلقة',
                            type: trade.isOpen
                                ? BadgeType.info
                                : BadgeType.success,
                            showDot: false,
                          ),
                        ],
                      ),
                      const SizedBox(height: 5),
                      Row(
                        children: [
                          StatusBadge(
                            text: trade.isBuy ? 'شراء' : 'بيع',
                            type: trade.isBuy
                                ? BadgeType.success
                                : BadgeType.error,
                            showDot: false,
                          ),
                          const SizedBox(width: SpacingTokens.xs),
                          Expanded(
                            child: Text(
                              trade.isOpen
                                  ? (trade.currentPrice != null
                                        ? 'الآن ${trade.currentPrice!.toStringAsFixed(4)}'
                                        : 'مبلغ الدخول ${trade.entryAmount.toStringAsFixed(2)}')
                                  : (trade.exitTime != null
                                        ? 'خروج: ${_shortDateLabel(trade.exitTime!)}'
                                        : trade.exitPrice != null
                                        ? 'خرج بـ ${trade.exitPrice!.toStringAsFixed(4)}'
                                        : 'مبلغ الدخول ${trade.entryAmount.toStringAsFixed(2)}'),
                              style: TypographyTokens.caption(
                                cs.onSurface.withValues(alpha: 0.45),
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                SizedBox(
                  width: 90,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: SpacingTokens.xs,
                    ),
                    child: trade.isOpen
                        ? _OpenTradeLiveIndicator(trade: trade)
                        : trade.pnl != null
                        ? FittedBox(
                            fit: BoxFit.scaleDown,
                            alignment: AlignmentDirectional.centerEnd,
                            child: PnlIndicator(
                              amount: trade.pnl!,
                              percentage: trade.pnlPct,
                              compact: true,
                              fontSize: 12,
                            ),
                          )
                        : const SizedBox.shrink(),
                  ),
                ),
                Padding(
                  padding: const EdgeInsetsDirectional.only(
                    end: SpacingTokens.sm,
                  ),
                  child: Icon(
                    Icons.chevron_left_rounded,
                    size: 18,
                    color: cs.onSurface.withValues(alpha: 0.25),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _shortDateLabel(String iso) {
    try {
      final dt = DateTime.parse(iso).toLocal();
      return '${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return iso;
    }
  }
}

class _OpenTradeLiveIndicator extends StatelessWidget {
  final TradeModel trade;

  const _OpenTradeLiveIndicator({required this.trade});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final semantic = SemanticColors.of(context);
    final pnl = trade.pnl ?? 0;
    final pct = trade.pnlPct ?? 0;
    final isPositive = pnl > 0;
    final isNegative = pnl < 0;
    final tone = isPositive
        ? semantic.positive
        : isNegative
        ? semantic.negative
        : cs.tertiary;
    final sign = pct > 0 ? '+' : '';

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.sm,
        vertical: 6,
      ),
      decoration: BoxDecoration(
        color: tone.withValues(alpha: 0.10),
        borderRadius: BorderRadius.circular(999),
        border: Border.all(color: tone.withValues(alpha: 0.20), width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: BoxDecoration(color: tone, shape: BoxShape.circle),
          ),
          const SizedBox(width: 6),
          Text(
            '$sign${pct.toStringAsFixed(2)}%',
            style: TypographyTokens.caption(
              tone,
            ).copyWith(fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}

class _BalanceSummaryMetric extends StatelessWidget {
  final String label;
  final double amount;
  final double? percentage;

  const _BalanceSummaryMetric({
    required this.label,
    required this.amount,
    this.percentage,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.55)),
        ),
        const SizedBox(height: SpacingTokens.xs),
        PnlIndicator(amount: amount, percentage: percentage, compact: true),
      ],
    );
  }
}

/// Section title for dashboard — zero extra horizontal padding
/// Aligns flush with card edges (unlike SectionHeader which adds 16px)
class _DashTitle extends StatelessWidget {
  final String title;
  final String? actionText;
  final VoidCallback? onAction;

  const _DashTitle({required this.title, this.actionText, this.onAction});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: SpacingTokens.xs),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            title,
            style: TypographyTokens.label(
              cs.onSurface.withValues(alpha: 0.72),
            ).copyWith(fontWeight: FontWeight.w600),
          ),
          if (actionText != null && onAction != null)
            GestureDetector(
              onTap: onAction,
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: SpacingTokens.sm,
                  vertical: SpacingTokens.sm,
                ),
                child: Text(
                  actionText!,
                  style: TypographyTokens.bodySmall(
                    cs.primary,
                  ).copyWith(fontWeight: FontWeight.w600),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
