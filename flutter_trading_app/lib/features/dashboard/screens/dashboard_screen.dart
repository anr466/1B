import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/models/trade_model.dart';
import 'package:trading_app/core/providers/admin_provider.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/privacy_provider.dart';
import 'package:trading_app/core/providers/settings_provider.dart';
import 'package:trading_app/core/providers/trades_provider.dart';
import 'package:trading_app/design/icons/brand_logo.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/utils/responsive_utils.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_section_label.dart';
import 'package:trading_app/design/widgets/error_state.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/metric_card.dart';
import 'package:trading_app/design/widgets/status_ring.dart';
import 'package:trading_app/design/widgets/chart_card.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Dashboard Screen — الشاشة الرئيسية بتصميم Soft Pastel
/// Bento Grid layout + ألوان ناعمة + بدون حواف حادة
class DashboardScreen extends ConsumerStatefulWidget {
  const DashboardScreen({super.key});

  @override
  ConsumerState<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends ConsumerState<DashboardScreen> {
  int _secondsSinceUpdate = 0;
  Timer? _updateTimer;

  @override
  void initState() {
    super.initState();
    _updateTimer = Timer.periodic(const Duration(seconds: 10), (_) {
      if (mounted) setState(() => _secondsSinceUpdate += 10);
    });
  }

  @override
  void dispose() {
    _updateTimer?.cancel();
    super.dispose();
  }

  void _refresh() {
    _secondsSinceUpdate = 0;
    ref.invalidate(portfolioProvider);
    ref.invalidate(statsProvider);
    ref.invalidate(recentTradesProvider);
    ref.invalidate(activePositionsProvider);
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final auth = ref.watch(authProvider);
    final pagePadding = ResponsiveUtils.pageHorizontalPadding(context);
    final maxWidth = ResponsiveUtils.maxContentWidth(context);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: SafeArea(
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

                    // ─── Trading Readiness Checklist ────────
                    _buildReadinessChecklist(cs, ref),
                    const SizedBox(height: SpacingTokens.md),

                    // ─── Hero Balance Card ───────────────────
                    _buildHeroBalanceCard(context, ref),
                    const SizedBox(height: SpacingTokens.md),

                    // ─── Daily PnL Bar ──────────────────────
                    _buildDailyPnlBar(context, ref),
                    const SizedBox(height: SpacingTokens.md),

                    // ─── Open Positions Strip ───────────────
                    _buildOpenPositionsStrip(context, ref),
                    const SizedBox(height: SpacingTokens.md),

                    // ─── Performance Ring + Quick Stats ──────
                    _buildPerformanceSection(context, ref),
                    const SizedBox(height: SpacingTokens.md),

                    // ─── Chart ───────────────────────────────
                    _buildChartSection(context, ref),
                    const SizedBox(height: SpacingTokens.md),

                    // ─── Stats Grid ──────────────────────────
                    const AppSectionLabel(text: 'ملخص المحفظة'),
                    _buildStatsGrid(context, ref),
                    const SizedBox(height: SpacingTokens.md),

                    // ─── Recent Trades ───────────────────────
                    _buildRecentTradesSection(context, ref),
                  ],
                ),
              ),
            ),
          ),
        ),
    );
  }

  // ──────────────────────────────────────────────────────────────
  //  TRADING READINESS CHECKLIST
  // ──────────────────────────────────────────────────────────────
  Widget _buildReadinessChecklist(ColorScheme cs, WidgetRef ref) {
    final auth = ref.read(authProvider);
    final isAdmin = auth.isAdmin;
    final settings = ref.watch(settingsDataProvider);

    return settings.maybeWhen(
      data: (s) {
        final needsKeys = !isAdmin && !s.hasBinanceKeys;
        final needsTrading = !s.tradingEnabled;

        // All good — no checklist needed
        if (!needsKeys && !needsTrading) {
          return const SizedBox.shrink();
        }

        return AppCard(
          backgroundColor: cs.tertiary.withValues(alpha: 0.08),
          padding: const EdgeInsets.all(SpacingTokens.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Icon(Icons.tips_and_updates, color: cs.tertiary, size: 20),
                const SizedBox(width: SpacingTokens.sm),
                Text('لبدء التداول:', style: TypographyTokens.label(cs.onSurface)),
              ]),
              const SizedBox(height: SpacingTokens.sm),
              if (needsKeys)
                _checkItem(cs, Icons.key, 'أضف مفاتيح Binance', false, () => context.push(RouteNames.binanceKeys)),
              if (needsTrading)
                _checkItem(cs, Icons.power_settings_new, 'فعّل التداول', false, null),
              if (needsKeys && needsTrading) ...[
                const SizedBox(height: SpacingTokens.xs),
                Text(
                  'المحرك يحدد حجم الصفقة وإدارة المخاطرة تلقائياً',
                  style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.45)),
                ),
              ],
              if (!needsKeys && !needsTrading) ...[
                const SizedBox(height: SpacingTokens.xs),
                Row(children: [
                  Icon(Icons.check_circle, color: cs.primary, size: 16),
                  const SizedBox(width: SpacingTokens.xs),
                  Text('التداول نشط — بانتظار إشارات السوق',
                    style: TypographyTokens.caption(cs.primary)),
                ]),
              ],
            ],
          ),
        );
      },
      orElse: () => const SizedBox.shrink(),
    );
  }

  Widget _checkItem(ColorScheme cs, IconData icon, String text, bool done, VoidCallback? onTap) {
    return Padding(
      padding: const EdgeInsets.only(bottom: SpacingTokens.xs),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(SpacingTokens.radiusSm),
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: SpacingTokens.xxs),
          child: Row(children: [
            Icon(done ? Icons.check_circle : Icons.radio_button_unchecked,
              size: 18,
              color: done ? cs.primary.withValues(alpha: 0.5) : cs.tertiary,
            ),
            const SizedBox(width: SpacingTokens.sm),
            Text(text, style: TypographyTokens.bodySmall(
              done ? cs.onSurface.withValues(alpha: 0.6) : cs.onSurface,
            )),
            const Spacer(),
            if (onTap != null && !done)
              Icon(Icons.chevron_left, size: 16, color: cs.tertiary),
          ]),
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
                  'تداول',
                  style: TypographyTokens.caption(
                    cs.onSurface.withValues(alpha: 0.50),
                  ).copyWith(letterSpacing: 1.0),
                ),
              ],
            ),
            _buildLastUpdated(context, ref),
          ],
        ),
        const Spacer(),
        // Balance visibility toggle
        GestureDetector(
          onTap: () => ref.read(balanceVisibilityProvider.notifier).toggle(),
          child: Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: cs.onSurface.withValues(alpha: 0.08),
              shape: BoxShape.circle,
            ),
            child: Icon(
              hideBalance
                  ? Icons.visibility_off_rounded
                  : Icons.visibility_rounded,
              size: 20,
              color: cs.onSurface.withValues(alpha: 0.5),
            ),
          ),
        ),
        const SizedBox(width: SpacingTokens.xs),
        // Notifications
        GestureDetector(
          onTap: () => context.push(RouteNames.notifications),
          child: Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: cs.onSurface.withValues(alpha: 0.08),
              shape: BoxShape.circle,
            ),
            child: Icon(
              Icons.notifications_outlined,
              size: 20,
              color: cs.onSurface.withValues(alpha: 0.5),
            ),
          ),
        ),
      ],
    );
  }

  /// Shows relative time since last data fetch
  Widget _buildLastUpdated(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final accountState = ref.watch(accountTradingProvider);
    final lastUpdated = accountState.data?.portfolio?.lastUpdated;

    String label = 'مباشر';
    if (lastUpdated != null) {
      final dt = DateTime.tryParse(lastUpdated);
      if (dt != null) {
        final diff = DateTime.now().difference(dt).inSeconds + _secondsSinceUpdate;
        if (diff < 60) {
          label = 'آخر تحديث: منذ $diff ثوانٍ';
        } else if (diff < 3600) {
          label = 'آخر تحديث: منذ ${diff ~/ 60} دقائق';
        } else {
          label = 'آخر تحديث: منذ ${diff ~/ 3600} ساعات';
        }
      }
    }

    return Text(
      label,
      style: TypographyTokens.caption(
        cs.onSurface.withValues(alpha: 0.40),
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────
  //  HERO BALANCE CARD
  // ──────────────────────────────────────────────────────────────
  Widget _buildHeroBalanceCard(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final portfolio = ref.watch(portfolioProvider);
    final auth = ref.watch(authProvider);
    final portfolioMode = auth.isAdmin
        ? ref.watch(adminPortfolioModeProvider)
        : 'real';

    return portfolio.when(
      loading: () => const LoadingShimmer(itemCount: 1, itemHeight: 140),
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
        final hideBalance = ref.watch(balanceVisibilityProvider);
        final semantic = SemanticColors.of(context);
        final isPositive = p.totalPnl >= 0;

        return HeroMetricCard(
          label: 'الرصيد الحالي',
          value: hideBalance ? '••••••' : _formatCurrency(p.currentBalance),
          subtitle: hideBalance
              ? null
              : '${isPositive ? '+' : ''}${p.totalPnl.toStringAsFixed(2)} (${isPositive ? '+' : ''}${p.totalPnlPct.toStringAsFixed(2)}%)',
          badge: modeLabel,
          accentColor: isPositive ? semantic.positive : semantic.negative,
          trailing: Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: cs.primary.withValues(alpha: 0.12),
              shape: BoxShape.circle,
            ),
            child: Icon(
              Icons.account_balance_wallet_outlined,
              size: 18,
              color: cs.primary,
            ),
          ),
        );
      },
    );
  }

  // ──────────────────────────────────────────────────────────────
  //  DAILY PnL BAR — شريط أرباح اليوم
  // ──────────────────────────────────────────────────────────────
  Widget _buildDailyPnlBar(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final semantic = SemanticColors.of(context);
    final isDark = cs.brightness == Brightness.dark;
    final portfolio = ref.watch(portfolioProvider);
    final hideBalance = ref.watch(balanceVisibilityProvider);

    return portfolio.when(
      loading: () => const LoadingShimmer(itemCount: 1, itemHeight: 50),
      error: (_, __) => ErrorState(
        message: 'تعذر تحميل البيانات',
        onRetry: () => ref.invalidate(portfolioProvider),
      ),
      data: (p) {
        final isPositive = p.dailyPnl >= 0;
        final accent = isPositive ? semantic.positive : semantic.negative;
        final label = isPositive ? 'ربح اليوم' : 'خسارة اليوم';
        final sign = isPositive ? '+' : '';
        final amount = hideBalance
            ? '••••••'
            : '$sign\$${p.dailyPnl.abs().toStringAsFixed(2)}';
        final pct = hideBalance
            ? ''
            : ' ($sign${p.dailyPnlPct.abs().toStringAsFixed(2)}%)';

        return AppCard(
          padding: const EdgeInsets.symmetric(
            horizontal: SpacingTokens.md,
            vertical: SpacingTokens.sm + 2,
          ),
          backgroundColor: accent.withValues(alpha: isDark ? 0.18 : 0.10),
          borderColor: accent.withValues(alpha: 0.25),
          level: 1,
          child: Row(
            children: [
              Icon(
                isPositive ? Icons.trending_up_rounded : Icons.trending_down_rounded,
                size: 20,
                color: accent,
              ),
              const SizedBox(width: SpacingTokens.sm),
              Text(
                '$label: $amount',
                style: TypographyTokens.body(accent).copyWith(
                  fontWeight: FontWeight.w700,
                ),
              ),
              if (pct.isNotEmpty) ...[
                const SizedBox(width: 4),
                Text(
                  pct,
                  style: TypographyTokens.bodySmall(
                    accent.withValues(alpha: 0.75),
                  ).copyWith(fontWeight: FontWeight.w600),
                ),
              ],
              const Spacer(),
              Container(
                width: 8,
                height: 8,
                decoration: BoxDecoration(
                  color: accent,
                  shape: BoxShape.circle,
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  // ──────────────────────────────────────────────────────────────
  //  OPEN POSITIONS STRIP — شريط الصفقات المفتوحة
  // ──────────────────────────────────────────────────────────────
  Widget _buildOpenPositionsStrip(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final positionsState = ref.watch(activePositionsProvider);

    if (positionsState.isLoading) {
      return const LoadingShimmer(itemCount: 1, itemHeight: 54);
    }

    final positions = positionsState.data ?? [];

    if (positions.isEmpty) {
      return AppCard(
        padding: const EdgeInsets.all(SpacingTokens.md),
        level: 1,
        child: Row(
          children: [
            Icon(
              Icons.inventory_2_outlined,
              size: 16,
              color: cs.onSurface.withValues(alpha: 0.35),
            ),
            const SizedBox(width: SpacingTokens.sm),
            Text(
              'لا توجد صفقات مفتوحة حالياً',
              style: TypographyTokens.bodySmall(
                cs.onSurface.withValues(alpha: 0.4),
              ),
            ),
          ],
        ),
      );
    }

    final displayPositions = positions.take(5).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: SpacingTokens.xs),
          child: Text(
            'الصفقات المفتوحة (${positions.length})'.toUpperCase(),
            style: TypographyTokens.overline(
              cs.onSurface.withValues(alpha: 0.5),
            ).copyWith(letterSpacing: 1.0),
          ),
        ),
        SizedBox(
          height: 54,
          child: ListView.separated(
            scrollDirection: Axis.horizontal,
            itemCount: displayPositions.length,
            separatorBuilder: (_, __) => const SizedBox(width: SpacingTokens.sm),
            itemBuilder: (_, i) => _MiniPositionTile(
              trade: displayPositions[i],
              onTap: () => context.push(
                RouteNames.tradeDetail,
                extra: displayPositions[i],
              ),
            ),
          ),
        ),
      ],
    );
  }

  // ──────────────────────────────────────────────────────────────
  //  PERFORMANCE SECTION — Ring + Quick Stats
  // ──────────────────────────────────────────────────────────────
  Widget _buildPerformanceSection(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final stats = ref.watch(statsProvider);

    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.md),
      level: 1,
      child: Row(
        children: [
          // Status Ring
          stats.when(
            loading: () => const SizedBox(
              width: 100,
              height: 100,
              child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
            ),
            error: (_, __) => ErrorState(
              message: 'تعذر تحميل البيانات',
              onRetry: () => ref.invalidate(statsProvider),
            ),
            data: (s) {
              final winRate = s.winRate / 100;
              return StatusRing(
                percentage: winRate.clamp(0.0, 1.0),
                size: 100,
                strokeWidth: 10,
                centerText: '${s.winRate.toInt()}%',
                label: 'نسبة الفوز',
                color: winRate >= 0.5 ? cs.primary : cs.error,
              );
            },
          ),
          const SizedBox(width: SpacingTokens.md),
          // Quick Stats
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'إحصائيات سريعة'.toUpperCase(),
                  style: TypographyTokens.overline(
                    cs.onSurface.withValues(alpha: 0.5),
                  ).copyWith(letterSpacing: 1.5, fontSize: 10),
                ),
                const SizedBox(height: SpacingTokens.sm),
                stats.when(
                  loading: () =>
                      const LoadingShimmer(itemCount: 3, itemHeight: 24),
                  error: (_, __) => ErrorState(
                    message: 'تعذر تحميل البيانات',
                    onRetry: () => ref.invalidate(statsProvider),
                  ),
                  data: (s) => Column(
                    children: [
                      _QuickStatRow(
                        label: 'الصفقات',
                        value: '${s.totalTrades}',
                        subValue: '${s.activeTrades} نشطة',
                      ),
                      const SizedBox(height: SpacingTokens.xs),
                      _QuickStatRow(
                        label: 'الفائزة',
                        value: '${s.winningTrades}',
                        subValue: 'من ${s.closedTrades} مغلقة',
                      ),
                      const SizedBox(height: SpacingTokens.xs),
                      _QuickStatRow(
                        label: 'الخاسرة',
                        value: '${s.losingTrades}',
                        subValue: '',
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ──────────────────────────────────────────────────────────────
  //  CHART SECTION — بيانات حقيقية من صفقات المستخدم
  // ──────────────────────────────────────────────────────────────
  Widget _buildChartSection(BuildContext context, WidgetRef ref) {
    final portfolio = ref.watch(portfolioProvider);
    final trades = ref.watch(analyticsTradesProvider);
    final semantic = SemanticColors.of(context);

    return portfolio.when(
      loading: () => const LoadingShimmer(itemCount: 1, itemHeight: 200),
      error: (_, __) => ErrorState(
        message: 'تعذر تحميل البيانات',
        onRetry: () => ref.invalidate(portfolioProvider),
      ),
      data: (p) {
        final isPositive = p.dailyPnl >= 0;

        // بناء منحنى الأسهم من الصفقات الحقيقية المغلقة
        final chartData = trades.when(
          loading: () => <double>[],
          error: (_, __) => <double>[],
          data: (tradeList) => _buildEquityCurve(tradeList, p.initialBalance),
        );

        // عرض الرسالة إذا لم توجد بيانات
        if (chartData.isEmpty) {
          return AppCard(
            padding: const EdgeInsets.all(SpacingTokens.lg),
            level: 1,
            child: Center(
              child: Text(
                'لا توجد بيانات كافية للرسم البياني',
                style: TypographyTokens.bodySmall(
                  Theme.of(
                    context,
                  ).colorScheme.onSurface.withValues(alpha: 0.4),
                ),
              ),
            ),
          );
        }

        return ChartCard(
          title: 'منحنى الأسهم',
          data: chartData,
          labels: _generateTimeLabels(chartData.length),
          currentValue: _formatCurrency(p.currentBalance),
          change:
              '${isPositive ? '+' : ''}${p.dailyPnlPct.toStringAsFixed(2)}%',
          isPositive: isPositive,
          lineColor: isPositive ? semantic.positive : semantic.negative,
          height: 160,
        );
      },
    );
  }

  /// بناء منحنى الأسهم التراكمي من الصفقات الحقيقية
  List<double> _buildEquityCurve(
    List<TradeModel> trades,
    double initialBalance,
  ) {
    // تصفية الصفقات المغلقة فقط وترتيبها حسب وقت الخروج
    final closedTrades =
        trades.where((t) => t.isClosed && t.exitTime != null).toList()
          ..sort((a, b) => (a.exitTime ?? '').compareTo(b.exitTime ?? ''));

    if (closedTrades.isEmpty) return [];

    // حساب الرصيد التراكمي بعد كل صفقة
    final curve = <double>[initialBalance];
    double runningBalance = initialBalance;

    for (final trade in closedTrades) {
      runningBalance += (trade.pnl ?? 0);
      curve.add(runningBalance);
    }

    return curve;
  }

  /// توليد تسميات زمنية بناءً على عدد النقاط
  List<String> _generateTimeLabels(int count) {
    if (count <= 1) return ['البداية'];
    if (count <= 4) return ['البداية', '', '', 'النهاية'];
    if (count <= 7) {
      return ['البداية', '', 'الوسط', '', '', '', 'النهاية'];
    }
    // لعدد أكبر، نوزع التسميات بشكل متساوٍ
    final labels = <String>[];
    for (int i = 0; i < count; i++) {
      if (i == 0) {
        labels.add('البداية');
      } else if (i == count - 1) {
        labels.add('النهاية');
      } else if (i == count ~/ 2) {
        labels.add('الوسط');
      } else {
        labels.add('');
      }
    }
    return labels;
  }

  // ──────────────────────────────────────────────────────────────
  //  STATS GRID
  // ──────────────────────────────────────────────────────────────
  Widget _buildStatsGrid(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final portfolio = ref.watch(portfolioProvider);

    return Column(
      children: [
        // الصف الأول: رصيد متاح + رصيد محجوز
        Row(
          children: [
            Expanded(
              child: portfolio.when(
                loading: () =>
                    const LoadingShimmer(itemCount: 1, itemHeight: 100),
                error: (_, __) => ErrorState(
                  message: 'تعذر تحميل البيانات',
                  onRetry: () => ref.invalidate(portfolioProvider),
                ),
                data: (p) => MetricCard(
                  label: 'متاح',
                  value: _formatCurrency(p.availableBalance),
                  icon: Icons.account_balance_outlined,
                  accentColor: cs.primary,
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: portfolio.when(
                loading: () =>
                    const LoadingShimmer(itemCount: 1, itemHeight: 100),
                error: (_, __) => ErrorState(
                  message: 'تعذر تحميل البيانات',
                  onRetry: () => ref.invalidate(portfolioProvider),
                ),
                data: (p) => MetricCard(
                  label: 'محجوز',
                  value: _formatCurrency(p.reservedBalance),
                  icon: Icons.lock_outline,
                  accentColor: cs.secondary,
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        // الصف الثاني: ربح محقق + ربح غير محقق
        Row(
          children: [
            Expanded(
              child: portfolio.when(
                loading: () =>
                    const LoadingShimmer(itemCount: 1, itemHeight: 100),
                error: (_, __) => ErrorState(
                  message: 'تعذر تحميل البيانات',
                  onRetry: () => ref.invalidate(portfolioProvider),
                ),
                data: (p) => MetricCard(
                  label: 'ربح محقق',
                  value: _formatPnl(p.realizedPnl),
                  change: '${p.realizedPnlPct.toStringAsFixed(2)}%',
                  isPositive: p.realizedPnl >= 0,
                  icon: Icons.trending_up_outlined,
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: portfolio.when(
                loading: () =>
                    const LoadingShimmer(itemCount: 1, itemHeight: 100),
                error: (_, __) => ErrorState(
                  message: 'تعذر تحميل البيانات',
                  onRetry: () => ref.invalidate(portfolioProvider),
                ),
                data: (p) => MetricCard(
                  label: 'غير محقق',
                  value: _formatPnl(p.unrealizedPnl),
                  change: '${p.unrealizedPnlPct.toStringAsFixed(2)}%',
                  isPositive: p.unrealizedPnl >= 0,
                  icon: Icons.show_chart_outlined,
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  // ──────────────────────────────────────────────────────────────
  //  RECENT TRADES SECTION
  // ──────────────────────────────────────────────────────────────
  Widget _buildRecentTradesSection(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: SpacingTokens.sm),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'آخر الصفقات'.toUpperCase(),
                style: TypographyTokens.overline(
                  cs.onSurface.withValues(alpha: 0.5),
                ).copyWith(letterSpacing: 1.5, fontSize: 10),
              ),
              GestureDetector(
                onTap: () => context.go(RouteNames.trades),
                child: Text(
                  'عرض الكل',
                  style: TypographyTokens.bodySmall(
                    cs.primary,
                  ).copyWith(fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
        ),
        _buildRecentTrades(context, ref),
      ],
    );
  }

  Widget _buildRecentTrades(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final isDark = cs.brightness == Brightness.dark;
    final activeTrades = ref.watch(activePositionsProvider);
    final recentTrades = ref.watch(recentTradesProvider);

    if (recentTrades.isLoading) {
      return const LoadingShimmer(itemCount: 3, itemHeight: 60);
    }

    if (recentTrades.hasError) {
      return ErrorState(
        message: 'تعذر تحميل الصفقات',
        onRetry: () {
          ref.invalidate(recentTradesProvider);
          ref.invalidate(activePositionsProvider);
        },
      );
    }

    final allTrades = recentTrades.valueOrNull ?? const <TradeModel>[];
    final livePositions = activeTrades.data;
    final hasLiveData =
        livePositions != null &&
        !activeTrades.isLoading &&
        !activeTrades.isError;

    List<TradeModel> openList;
    if (hasLiveData) {
      final liveMap = {for (final t in livePositions) t.id: t};
      openList = allTrades
          .where((t) => t.isOpen)
          .map((t) => liveMap[t.id] ?? t)
          .toList();
    } else {
      openList = allTrades.where((t) => t.isOpen).toList();
    }

    final closedList = allTrades.where((t) => !t.isOpen).toList();
    final hybridItems = _buildHybridTradeItems(openList, closedList);

    if (hybridItems.isEmpty) {
      return AppCard(
        padding: const EdgeInsets.all(SpacingTokens.lg),
        level: 1,
        child: Center(
          child: Text(
            'لا توجد صفقات حديثة',
            style: TypographyTokens.bodySmall(
              cs.onSurface.withValues(alpha: 0.4),
            ),
          ),
        ),
      );
    }

    return AppCard(
      padding: EdgeInsets.zero,
      level: 1,
      child: Column(
        children: hybridItems.asMap().entries.map((entry) {
          final index = entry.key;
          final item = entry.value;
          return Column(
            children: [
              _HybridTradeTile(trade: item),
              if (index < hybridItems.length - 1)
                Divider(
                  color: cs.outline.withValues(alpha: isDark ? 0.08 : 0.06),
                  height: 1,
                  indent: SpacingTokens.md,
                  endIndent: SpacingTokens.md,
                ),
            ],
          );
        }).toList(),
      ),
    );
  }

  List<TradeModel> _buildHybridTradeItems(
    List<TradeModel> openTrades,
    List<TradeModel> closedTrades,
  ) {
    const maxItems = 5;
    final allTrades = [...openTrades, ...closedTrades];
    allTrades.sort((a, b) {
      final aTime = a.exitTime ?? a.entryTime;
      final bTime = b.exitTime ?? b.entryTime;
      if (aTime == null && bTime == null) return 0;
      if (aTime == null) return 1;
      if (bTime == null) return -1;
      return bTime.compareTo(aTime);
    });
    return allTrades.take(maxItems).toList();
  }

  // ──────────────────────────────────────────────────────────────
  //  HELPERS
  // ──────────────────────────────────────────────────────────────
  String _formatCurrency(double amount) {
    return '\$${amount.toStringAsFixed(2)}';
  }

  String _formatPnl(double amount) {
    final sign = amount >= 0 ? '+' : '';
    return '$sign\$${amount.abs().toStringAsFixed(2)}';
  }
}

// ──────────────────────────────────────────────────────────────
//  PRIVATE WIDGETS
// ──────────────────────────────────────────────────────────────

// ──────────────────────────────────────────────────────────────
//  PRIVATE WIDGETS
// ──────────────────────────────────────────────────────────────

class _MiniPositionTile extends StatelessWidget {
  final TradeModel trade;
  final VoidCallback? onTap;

  const _MiniPositionTile({required this.trade, this.onTap});

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
        : cs.onSurface.withValues(alpha: 0.5);
    final sign = pct > 0 ? '+' : '';

    return GestureDetector(
      onTap: onTap,
      child: AppCard(
        padding: const EdgeInsets.symmetric(
          horizontal: SpacingTokens.md,
          vertical: SpacingTokens.sm,
        ),
        borderRadius: SpacingTokens.radiusMd,
        level: 1,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              trade.symbol,
              style: TypographyTokens.bodySmall(
                cs.onSurface,
              ).copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 2),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 5,
                  height: 5,
                  decoration: BoxDecoration(color: tone, shape: BoxShape.circle),
                ),
                const SizedBox(width: 4),
                Text(
                  '$sign${pct.abs().toStringAsFixed(2)}%',
                  style: TypographyTokens.caption(
                    tone,
                  ).copyWith(fontWeight: FontWeight.w600),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _QuickStatRow extends StatelessWidget {
  final String label;
  final String value;
  final String subValue;

  const _QuickStatRow({
    required this.label,
    required this.value,
    required this.subValue,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: TypographyTokens.bodySmall(
            cs.onSurface.withValues(alpha: 0.5),
          ),
        ),
        Row(
          children: [
            Text(
              value,
              style: TypographyTokens.body(
                cs.onSurface,
              ).copyWith(fontWeight: FontWeight.w700),
            ),
            if (subValue.isNotEmpty) ...[
              const SizedBox(width: 4),
              Text(
                subValue,
                style: TypographyTokens.caption(
                  cs.onSurface.withValues(alpha: 0.35),
                ),
              ),
            ],
          ],
        ),
      ],
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
    final isOpen = trade.isOpen;
    final isProfit = (trade.pnl ?? 0) >= 0;
    final accentColor = isOpen
        ? semantic.info
        : (isProfit ? semantic.positive : semantic.negative);

    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => context.push(RouteNames.tradeDetail, extra: trade),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            vertical: SpacingTokens.sm,
            horizontal: SpacingTokens.md,
          ),
          child: Row(
            children: [
              Container(
                width: 3,
                height: 32,
                decoration: BoxDecoration(
                  color: accentColor,
                  borderRadius: BorderRadius.circular(SpacingTokens.xxs),
                ),
              ),
              const SizedBox(width: SpacingTokens.md),
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
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: accentColor.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(SpacingTokens.radiusFull),
                          ),
                          child: Text(
                            isOpen ? 'مفتوحة' : 'مغلقة',
                            style: TypographyTokens.caption(
                              accentColor,
                            ).copyWith(fontWeight: FontWeight.w600),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 2),
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            isOpen
                                ? trade.entryPrice.toStringAsFixed(2)
                                : (trade.exitPrice?.toStringAsFixed(2) ?? "-"),
                            style: TypographyTokens.caption(
                              cs.onSurface.withValues(alpha: 0.45),
                            ),
                          ),
                        ),
                        if (trade.strategy != null)
                          Text(
                            trade.strategy!,
                            style: TypographyTokens.caption(
                              cs.onSurface.withValues(alpha: 0.3),
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(width: SpacingTokens.md),
              SizedBox(
                width: 80,
                child: isOpen
                    ? _OpenTradeLiveIndicator(trade: trade)
                    : trade.pnl != null
                    ? FittedBox(
                        fit: BoxFit.scaleDown,
                        alignment: AlignmentDirectional.centerEnd,
                        child: _PnlCompact(
                          amount: trade.pnl!,
                          percentage: trade.pnlPct,
                        ),
                      )
                    : const SizedBox.shrink(),
              ),
            ],
          ),
        ),
      ),
    );
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
        borderRadius: BorderRadius.circular(SpacingTokens.radiusFull),
        border: Border.all(color: tone.withValues(alpha: 0.20), width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
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

class _PnlCompact extends StatelessWidget {
  final double amount;
  final double? percentage;

  const _PnlCompact({required this.amount, this.percentage});

  @override
  Widget build(BuildContext context) {
    final semantic = SemanticColors.of(context);
    final isPositive = amount >= 0;
    final tone = isPositive ? semantic.positive : semantic.negative;
    final sign = isPositive ? '+' : '-';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.end,
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '$sign\$${amount.abs().toStringAsFixed(2)}',
          style: TypographyTokens.bodySmall(
            tone,
          ).copyWith(fontWeight: FontWeight.w700),
        ),
        if (percentage != null)
          Text(
            '$sign${percentage!.toStringAsFixed(2)}%',
            style: TypographyTokens.caption(tone.withValues(alpha: 0.7)),
          ),
      ],
    );
  }
}


