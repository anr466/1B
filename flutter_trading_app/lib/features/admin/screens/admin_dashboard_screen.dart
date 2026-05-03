import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/providers/admin_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/trades_provider.dart';
import 'package:trading_app/design/icons/brand_icons.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/app_section_label.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/status_badge.dart';
import 'package:trading_app/design/widgets/demo_real_banner.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Admin Dashboard Screen — لوحة تحكم المدير
class AdminDashboardScreen extends ConsumerWidget {
  const AdminDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final statusAsync = ref.watch(tradingCycleLiveProvider);
    final statsAsync = ref.watch(systemStatsProvider);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            children: [
              AppScreenHeader(title: 'لوحة الإدارة', showBack: true),
              const DemoRealBanner(),
              Expanded(
                child: RefreshIndicator(
                  color: cs.primary,
                  onRefresh: () async {
                    bool hasError = false;
                    try {
                      ref.invalidate(systemStatusProvider);
                      ref.read(tradingCycleLiveProvider.notifier).refresh();
                      ref.invalidate(accountTradingProvider);
                      ref.invalidate(systemStatsProvider);
                      ref.invalidate(adminUsersProvider);
                      ref.invalidate(activePositionsProvider);
                      await Future.delayed(const Duration(milliseconds: 500));
                    } catch (e) {
                      hasError = true;
                    }

                    if (context.mounted) {
                      AppSnackbar.show(
                        context,
                        message: hasError
                            ? 'فشل تحديث البيانات'
                            : 'تم تحديث البيانات',
                        type: hasError ? SnackType.error : SnackType.success,
                      );
                    }
                  },
                  child: ListView(
                    padding: const EdgeInsets.all(SpacingTokens.base),
                    children: [
                      // ─── System Status ─────────────────────
                      statusAsync.when(
                        loading: () =>
                            const LoadingShimmer(itemCount: 1, itemHeight: 80),
                        error: (e, _) {
                          debugPrint('[AdminDashboard] status error: $e');
                          return _buildErrorCard(
                            cs,
                            'تعذر تحميل البيانات',
                            () => ref.invalidate(tradingCycleLiveProvider),
                          );
                        },
                        data: (s) => _buildStatusCard(context, cs, s),
                      ),
                      const SizedBox(height: SpacingTokens.lg),

                      // ─── Quick Stats ──────────────────────
                      const AppSectionLabel(text: 'إحصائيات سريعة'),
                      const SizedBox(height: SpacingTokens.sm),
                      statsAsync.when(
                        loading: () =>
                            const LoadingShimmer(itemCount: 3, itemHeight: 100),
                        error: (e, _) {
                          debugPrint('[AdminDashboard] stats error: $e');
                          return _buildErrorCard(
                            cs,
                            'تعذر تحميل البيانات',
                            () => ref.invalidate(systemStatsProvider),
                          );
                        },
                        data: (stats) => _buildStatsGrid(context, cs, stats),
                      ),
                      const SizedBox(height: SpacingTokens.lg),

                      // ─── Trading & Users ───────────────────
                      const AppSectionLabel(text: 'إجراءات سريعة'),
                      const SizedBox(height: SpacingTokens.sm),

                      _actionItem(
                        context,
                        cs,
                        BrandIcons.chart,
                        'التحكم بالنظام',
                        RouteNames.tradingControl,
                      ),

                      _actionItem(
                        context,
                        cs,
                        BrandIcons.user,
                        'إدارة المستخدمين',
                        RouteNames.userManagement,
                      ),

                      // المحفظة والصفقات متاحتان من التنقل السفلي (Bottom Nav)
                      // لا نكررهم هنا لتجنب الازدواجية
                      _actionItem(
                        context,
                        cs,
                        BrandIcons.history,
                        'سجلات النظام',
                        RouteNames.systemLogs,
                      ),

                      _actionItem(
                        context,
                        cs,
                        BrandIcons.settings,
                        'لوحة السجلات',
                        RouteNames.adminLogsDashboard,
                      ),

                      _actionItem(
                        context,
                        cs,
                        BrandIcons.chart,
                        'التحكم بالخلفية',
                        RouteNames.adminBackgroundControl,
                      ),

                      _actionItem(
                        context,
                        cs,
                        BrandIcons.memory,
                        'لوحة ML',
                        RouteNames.adminMlDashboard,
                      ),

                      const SizedBox(height: SpacingTokens.xl),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatusCard(
    BuildContext context,
    ColorScheme cs,
    dynamic status,
  ) {
    final isRunning = status.isEffectivelyRunning == true;
    final state = status.state?.toString().toUpperCase() ?? 'UNKNOWN';

    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.md),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: (isRunning ? cs.primary : cs.error).withValues(
                alpha: 0.12,
              ),
              borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
            ),
            child: Icon(
              isRunning ? Icons.play_circle : Icons.stop_circle,
              color: isRunning ? cs.primary : cs.error,
              size: 28,
            ),
          ),
          const SizedBox(width: SpacingTokens.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'حالة النظام', // changed from 'حالة التداول'
                  style: TypographyTokens.bodySmall(
                    cs.onSurface.withValues(alpha: 0.6),
                  ),
                ),
                const SizedBox(height: SpacingTokens.xxs),
                Text(
                  isRunning ? 'يعمل' : (state == 'ERROR' ? 'خطأ' : 'متوقف'),
                  style: TypographyTokens.h3(cs.onSurface),
                ),
              ],
            ),
          ),
          StatusBadge(
            text: isRunning ? 'نشط' : 'متوقف',
            type: isRunning ? BadgeType.success : BadgeType.error,
          ),
        ],
      ),
    );
  }

  Widget _buildStatsGrid(BuildContext context, ColorScheme cs, dynamic stats) {
    final totalTrades = (stats['trades'] ?? 0) as int;
    final winRate = (stats['win_rate'] ?? 0.0).toDouble();
    final totalProfit = (stats['total_profit'] ?? 0.0).toDouble();

    return Row(
      children: [
        Expanded(
          child: _buildStatCard(
            cs: cs,
            label: 'إجمالي الصفقات',
            value: totalTrades.toString(),
            icon: BrandIcons.history,
          ),
        ),
        const SizedBox(width: SpacingTokens.sm),
        Expanded(
          child: _buildStatCard(
            cs: cs,
            label: 'نسبة الربح',
            value: '${winRate.toStringAsFixed(1)}%',
            icon: BrandIcons.chart,
            valueColor: winRate >= 50 ? cs.primary : cs.error,
          ),
        ),
        const SizedBox(width: SpacingTokens.sm),
        Expanded(
          child: _buildStatCard(
            cs: cs,
            label: 'إجمالي الربح',
            value: '\$${totalProfit.toStringAsFixed(2)}',
            icon: BrandIcons.wallet,
            valueColor: totalProfit >= 0
                ? SemanticColors.of(context).positive
                : cs.error,
          ),
        ),
      ],
    );
  }

  Widget _buildStatCard({
    required ColorScheme cs,
    required String label,
    required String value,
    required BrandIconData icon,
    Color? valueColor,
  }) {
    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.md),
      child: Column(
        children: [
          BrandIcon(icon, size: 18, color: cs.primary),
          const SizedBox(height: SpacingTokens.xs),
          Text(value, style: TypographyTokens.h3(valueColor ?? cs.onSurface)),
          const SizedBox(height: SpacingTokens.xxs),
          Text(
            label,
            style: TypographyTokens.caption(
              cs.onSurface.withValues(alpha: 0.5),
            ),
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _actionItem(
    BuildContext context,
    ColorScheme cs,
    BrandIconData icon,
    String label,
    String route,
  ) {
    return Padding(
      padding: const EdgeInsets.only(bottom: SpacingTokens.sm),
      child: AppCard(
        onTap: () => context.push(route),
        padding: const EdgeInsets.symmetric(
          horizontal: SpacingTokens.base,
          vertical: SpacingTokens.md,
        ),
        child: Row(
          children: [
            BrandIcon(icon, size: 20, color: cs.primary),
            const SizedBox(width: SpacingTokens.md),
            Expanded(
              child: Text(label, style: TypographyTokens.body(cs.onSurface)),
            ),
            Icon(
              Icons.chevron_left_rounded,
              color: cs.onSurface.withValues(alpha: 0.3),
              size: 20,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildErrorCard(ColorScheme cs, String message, VoidCallback onRetry) {
    return AppCard(
      backgroundColor: cs.error.withValues(alpha: 0.08),
      padding: const EdgeInsets.all(SpacingTokens.md),
      child: Row(
        children: [
          Icon(Icons.error_outline, color: cs.error, size: 24),
          const SizedBox(width: SpacingTokens.md),
          Expanded(
            child: Text(message, style: TypographyTokens.bodySmall(cs.error)),
          ),
          AppButton(
            label: 'إعادة',
            variant: AppButtonVariant.text,
            isFullWidth: false,
            onPressed: onRetry,
          ),
        ],
      ),
    );
  }
}
