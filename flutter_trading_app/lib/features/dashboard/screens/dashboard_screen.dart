import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:fl_chart/fl_chart.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/models/trade_model.dart';
import 'package:trading_app/core/providers/admin_provider.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/privacy_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/providers/trades_provider.dart';
import 'package:trading_app/core/constants/ux_messages.dart';
import 'package:trading_app/design/icons/brand_icons.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/icons/brand_logo.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/utils/responsive_utils.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/empty_state.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/money_text.dart';
import 'package:trading_app/design/widgets/pnl_indicator.dart';
import 'package:trading_app/design/widgets/status_badge.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Dashboard Screen — الشاشة الرئيسية
class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final auth = ref.watch(authProvider);
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
              ref.invalidate(statsProvider);
              ref.invalidate(recentTradesProvider);
              ref.invalidate(activePositionsProvider);
              ref.invalidate(systemStatusProvider);
              ref.invalidate(accountTradingProvider);
            },
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

                    // ─── Stats Row ───────────────────────────
                    _buildStatsRow(context, ref),
                    const SizedBox(height: SpacingTokens.md),

                    // ─── Performance Chart ───────────────────
                    _buildPerformanceChart(context, ref),

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
                    cs.onSurface.withValues(alpha: 0.35),
                  ).copyWith(letterSpacing: 3.5, fontSize: 9),
                ),
              ],
            ),
          ],
        ),
        const Spacer(),
        // Visibility toggle
        _HeaderIconButton(
          icon: hideBalance
              ? Icons.visibility_off_rounded
              : Icons.visibility_rounded,
          onTap: () => ref.read(balanceVisibilityProvider.notifier).toggle(),
          color: cs.onSurface.withValues(alpha: 0.5),
        ),
        const SizedBox(width: SpacingTokens.xs),
        // Notifications
        _HeaderIconButton(
          icon: BrandIcons.bell,
          onTap: () => context.push(RouteNames.notifications),
          color: cs.onSurface.withValues(alpha: 0.5),
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
    final dailyStatus = ref.watch(dailyStatusProvider);
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
        final d = dailyStatus.valueOrNull ?? {};
        final dailyPnl = (d['daily_pnl'] as num?)?.toDouble() ?? p.dailyPnl;
        final dailyBase = (d['base_balance'] as num?)?.toDouble();
        final dailyPct = dailyBase != null && dailyBase > 0
            ? (dailyPnl / dailyBase) * 100
            : p.dailyPnlPct;

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
                          label: 'إجمالي الربح',
                          amount: p.totalPnl,
                          percentage: p.totalPnlPct,
                        ),
                      ),
                      const SizedBox(width: SpacingTokens.sm),
                      Expanded(
                        child: _BalanceSummaryMetric(
                          label: 'ربح اليوم',
                          amount: dailyPnl,
                          percentage: dailyPct,
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
          onTap: () => context.push(RouteNames.adminDashboard),
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
                              AnimatedContainer(
                                duration: const Duration(milliseconds: 600),
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
                  // Toggle chip
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: SpacingTokens.sm,
                    ),
                    child: _TradingToggleChip(
                      isRunning: s.isRunning,
                      onToggle: () => _toggleTrading(context, ref, s.isRunning),
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
    final bio = ref.read(biometricServiceProvider);
    if (await bio.isAvailable) {
      final label = enabled ? 'تأكيد تفعيل التداول' : 'تأكيد إيقاف التداول';
      final ok = await bio.authenticate(reason: label);
      if (!ok) {
        if (!context.mounted) return;
        AppSnackbar.show(
          context,
          message: 'فشل التحقق من البصمة',
          type: SnackType.error,
        );
        return;
      }
    }

    final success = await ref
        .read(accountTradingProvider.notifier)
        .setEnabled(enabled);
    ref.invalidate(dailyStatusProvider);
    ref.invalidate(portfolioProvider);
    ref.invalidate(statsProvider);
    ref.invalidate(activePositionsProvider);
    ref.invalidate(recentTradesProvider);
    if (!context.mounted) return;
    AppSnackbar.show(
      context,
      message: success
          ? (enabled ? 'تم تفعيل التداول' : 'تم إيقاف التداول')
          : 'تعذر إتمام العملية، حاول مرة أخرى',
      type: success ? SnackType.success : SnackType.error,
    );
  }

  Future<void> _toggleTrading(
    BuildContext context,
    WidgetRef ref,
    bool isRunning,
  ) async {
    final bio = ref.read(biometricServiceProvider);
    if (await bio.isAvailable) {
      final label = isRunning ? 'تأكيد إيقاف التداول' : 'تأكيد تشغيل التداول';
      final ok = await bio.authenticate(reason: label);
      if (!ok) {
        if (!context.mounted) return;
        AppSnackbar.show(
          context,
          message: 'فشل التحقق من البصمة',
          type: SnackType.error,
        );
        return;
      }
    }
    try {
      final repo = ref.read(adminRepositoryProvider);
      final result = isRunning
          ? await repo.stopTrading()
          : await repo.startTrading();
      if (!context.mounted) return;
      final state = (result['trading_state'] ?? result['state'] ?? '')
          .toString()
          .toUpperCase();
      final ok = isRunning
          ? (result['success'] == true &&
                (state == 'STOPPED' || state == 'STOPPING'))
          : (result['success'] == true &&
                (state == 'RUNNING' || state == 'STARTING'));
      ref.invalidate(systemStatusProvider);
      ref.invalidate(tradingCycleLiveProvider);
      ref.invalidate(accountTradingProvider);
      ref.invalidate(portfolioProvider);
      ref.invalidate(statsProvider);
      ref.invalidate(activePositionsProvider);
      ref.invalidate(recentTradesProvider);
      ref.invalidate(dailyStatusProvider);
      AppSnackbar.show(
        context,
        message: ok ? UxMessages.success : UxMessages.error,
        type: ok ? SnackType.success : SnackType.error,
      );
    } catch (_) {
      if (!context.mounted) return;
      AppSnackbar.show(
        context,
        message: UxMessages.error,
        type: SnackType.error,
      );
    }
  }

  // ──────────────────────────────────────────────────────────────
  //  STATS ROW — horizontal Row (no GridView, no overflow)
  // ──────────────────────────────────────────────────────────────
  Widget _buildStatsRow(BuildContext context, WidgetRef ref) {
    final stats = ref.watch(statsProvider);

    return stats.when(
      loading: () => const LoadingShimmer(itemCount: 1, itemHeight: 80),
      error: (_, __) => const SizedBox.shrink(),
      data: (s) {
        final cs = Theme.of(context).colorScheme;
        final semantic = SemanticColors.of(context);

        return IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: _StatTile(
                  label: 'الصفقات',
                  value: '${s.totalTrades}',
                  valueColor: cs.onSurface,
                ),
              ),
              const SizedBox(width: SpacingTokens.sm),
              Expanded(
                child: _StatTile(
                  label: 'نسبة الفوز',
                  value: '${s.winRate.toStringAsFixed(1)}%',
                  valueColor: s.winRate >= 50
                      ? semantic.positive
                      : semantic.negative,
                  subLabel: s.winRate >= 50 ? '▲ جيد' : '▼ منخفض',
                  subColor: s.winRate >= 50
                      ? semantic.positive
                      : semantic.negative,
                ),
              ),
              const SizedBox(width: SpacingTokens.sm),
              Expanded(
                child: _StatTile(
                  label: 'معامل الربح',
                  value: s.profitFactor.toStringAsFixed(2),
                  valueColor: s.profitFactor >= 1.5
                      ? semantic.positive
                      : s.profitFactor >= 1.0
                      ? cs.onSurface
                      : semantic.negative,
                  subLabel: s.profitFactor >= 1.5
                      ? '▲ ممتاز'
                      : s.profitFactor >= 1.0
                      ? '◆ مقبول'
                      : '▼ ضعيف',
                  subColor: s.profitFactor >= 1.5
                      ? semantic.positive
                      : s.profitFactor >= 1.0
                      ? cs.onSurface.withValues(alpha: 0.5)
                      : semantic.negative,
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  // ──────────────────────────────────────────────────────────────
  //  RECENT TRADES SECTION
  // ──────────────────────────────────────────────────────────────
  Widget _buildRecentTradesSection(BuildContext context, WidgetRef ref) {
    return Column(
      children: [
        const SizedBox(height: SpacingTokens.md),
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

    if (activeTrades.isLoading || recentTrades.isLoading) {
      return const LoadingShimmer(itemCount: 3, itemHeight: 60);
    }

    if (activeTrades.hasError && recentTrades.hasError) {
      return AppCard(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: SpacingTokens.xl),
          child: EmptyState(
            message: 'تعذر تحميل الصفقات',
            icon: Icons.receipt_long_outlined,
          ),
        ),
      );
    }

    final openList = activeTrades.valueOrNull ?? const <TradeModel>[];
    final recentList = recentTrades.valueOrNull ?? const <TradeModel>[];
    final closedList = recentList.where((trade) => !trade.isOpen).toList();
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
    final remainingSlots = math.max(0, maxItems - limitedOpen.length);
    final limitedClosed = closedTrades
        .take(remainingSlots == 0 ? 2 : remainingSlots)
        .toList();
    return [...limitedOpen, ...limitedClosed];
  }

  // ──────────────────────────────────────────────────────────────
  //  PERFORMANCE CHART — chart logic UNTOUCHED
  // ──────────────────────────────────────────────────────────────
  Widget _buildPerformanceChart(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final semantic = SemanticColors.of(context);
    final trades = ref.watch(recentTradesProvider);
    final portfolio = ref.watch(portfolioProvider);
    final referenceBalance = portfolio.maybeWhen(
      data: (p) => p.initialBalance > 0 ? p.initialBalance : p.currentBalance,
      orElse: () => 0.0,
    );

    return trades.when(
      loading: () => const LoadingShimmer(itemCount: 1, itemHeight: 170),
      error: (_, __) => const SizedBox.shrink(),
      data: (list) {
        if (referenceBalance <= 0) return const SizedBox.shrink();
        final closed = list.where((t) => t.pnl != null).toList();
        if (closed.length < 2) return const SizedBox.shrink();

        final ordered = closed.reversed.toList();
        double cumulative = 0;
        final spots = <FlSpot>[];
        for (var i = 0; i < ordered.length; i++) {
          final tradePnl = ordered[i].pnl ?? 0;
          if (tradePnl.isNaN || tradePnl.isInfinite) continue;
          cumulative += tradePnl;
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
        final zeroLine = HorizontalLine(
          y: 0,
          color: cs.outline.withValues(alpha: 0.40),
          strokeWidth: 1,
          dashArray: [5, 4],
        );
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

        return Column(
          children: [
            const _DashTitle(title: 'أداء المحفظة'),
            const SizedBox(height: SpacingTokens.sm),
            AppCard(
              gradientColors: [
                Color.alphaBlend(
                  cs.primary.withValues(alpha: 0.12),
                  cs.surfaceContainerHigh,
                ),
                cs.surfaceContainer,
              ],
              padding: const EdgeInsets.all(SpacingTokens.md),
              child: SizedBox(
                height: 180,
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: cs.outline.withValues(alpha: 0.16),
                    ),
                    gradient: LinearGradient(
                      begin: Alignment.topCenter,
                      end: Alignment.bottomCenter,
                      colors: [
                        cs.surfaceContainerHighest.withValues(alpha: 0.55),
                        cs.surfaceContainerLow.withValues(alpha: 0.2),
                      ],
                    ),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 6,
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
                        titlesData: const FlTitlesData(show: false),
                        extraLinesData: ExtraLinesData(
                          horizontalLines: [zeroLine],
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
                              final tradeNum = spot.x.toInt() + 1;
                              final pct = spot.y;
                              final sign = pct >= 0 ? '+' : '';
                              return LineTooltipItem(
                                'صفقة #$tradeNum\n$sign${pct.toStringAsFixed(2)}%',
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
                      ),
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: SpacingTokens.md),
          ],
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
            children: [
              Container(
                width: 4,
                height: 58,
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
                    const SizedBox(height: 4),
                    Wrap(
                      spacing: SpacingTokens.xs,
                      runSpacing: 4,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        Text(
                          trade.isBuy ? 'شراء' : 'بيع',
                          style: TypographyTokens.caption(
                            sideColor,
                          ).copyWith(fontWeight: FontWeight.w600),
                        ),
                        Text(
                          trade.isOpen && trade.currentPrice != null
                              ? 'الآن ${trade.currentPrice!.toStringAsFixed(4)}'
                              : trade.exitTime != null
                              ? _shortDateLabel(trade.exitTime!)
                              : 'سعر الدخول ${trade.entryPrice.toStringAsFixed(4)}',
                          style: TypographyTokens.caption(
                            cs.onSurface.withValues(alpha: 0.45),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: SpacingTokens.sm,
                ),
                child: trade.isOpen
                    ? _OpenTradeLiveIndicator(trade: trade)
                    : (trade.pnl != null
                          ? PnlIndicator(
                              amount: trade.pnl!,
                              percentage: trade.pnlPct,
                              compact: true,
                              fontSize: 13,
                            )
                          : StatusBadge(
                              text: 'مغلقة',
                              type: BadgeType.success,
                              showDot: false,
                            )),
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

/// Header icon button with consistent size and tap area
class _HeaderIconButton extends StatelessWidget {
  final dynamic icon; // IconData or BrandIcon key
  final VoidCallback onTap;
  final Color color;

  const _HeaderIconButton({
    required this.icon,
    required this.onTap,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: SizedBox(
        width: 36,
        height: 36,
        child: Center(
          child: icon is IconData
              ? Icon(icon as IconData, size: 22, color: color)
              : BrandIcon(icon as BrandIconData, size: 22, color: color),
        ),
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
          style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.4)),
        ),
        const SizedBox(height: SpacingTokens.xs),
        PnlIndicator(amount: amount, percentage: percentage, compact: true),
      ],
    );
  }
}

/// Stats tile — used in the horizontal stats row
class _StatTile extends StatelessWidget {
  final String label;
  final String value;
  final Color valueColor;
  final String? subLabel;
  final Color? subColor;

  const _StatTile({
    required this.label,
    required this.value,
    required this.valueColor,
    this.subLabel,
    this.subColor,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = cs.brightness == Brightness.dark;

    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.sm,
        vertical: SpacingTokens.md,
      ),
      decoration: BoxDecoration(
        color: isDark ? cs.surfaceContainerHigh : cs.surfaceContainerLow,
        borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
        border: Border.all(
          color: cs.outline.withValues(alpha: isDark ? 0.18 : 0.10),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: TypographyTokens.caption(
              cs.onSurface.withValues(alpha: 0.45),
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: SpacingTokens.xxs),
          Text(
            value,
            style: TypographyTokens.mono(
              valueColor,
              fontSize: 17,
            ).copyWith(fontWeight: FontWeight.w700),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          if (subLabel != null) ...[
            const SizedBox(height: 2),
            Text(
              subLabel!,
              style: TypographyTokens.caption(
                subColor ?? cs.onSurface.withValues(alpha: 0.4),
              ).copyWith(fontSize: 10, fontWeight: FontWeight.w600),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ],
      ),
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
              child: Text(
                actionText!,
                style: TypographyTokens.bodySmall(
                  cs.primary,
                ).copyWith(fontWeight: FontWeight.w600),
              ),
            ),
        ],
      ),
    );
  }
}

/// Compact inline trading toggle chip
class _TradingToggleChip extends StatelessWidget {
  final bool isRunning;
  final VoidCallback onToggle;

  const _TradingToggleChip({required this.isRunning, required this.onToggle});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final color = isRunning ? cs.error : cs.primary;
    final label = isRunning ? 'إيقاف' : 'تشغيل';
    final icon = isRunning
        ? Icons.stop_circle_outlined
        : Icons.play_circle_outline_rounded;

    return GestureDetector(
      onTap: onToggle,
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: SpacingTokens.sm,
          vertical: SpacingTokens.xs,
        ),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(SpacingTokens.radiusBadge),
          border: Border.all(color: color.withValues(alpha: 0.35), width: 0.8),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: color),
            const SizedBox(width: 4),
            Text(
              label,
              style: TypographyTokens.caption(
                color,
              ).copyWith(fontWeight: FontWeight.w600),
            ),
          ],
        ),
      ),
    );
  }
}
