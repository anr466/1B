import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/providers/admin_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/design/icons/brand_icons.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/app_section_label.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Admin Dashboard Screen — لوحة تحكم المدير
/// Quick-links only; system status & ML details live in TradingControlScreen.
class AdminDashboardScreen extends ConsumerWidget {
  const AdminDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            children: [
              AppScreenHeader(title: 'لوحة الإدارة', showBack: true),
              Expanded(
                child: RefreshIndicator(
                  color: cs.primary,
                  onRefresh: () async {
                    bool hasError = false;
                    try {
                      // Invalidate all data providers
                      ref.invalidate(systemStatusProvider);
                      ref.read(tradingCycleLiveProvider.notifier).refresh();
                      ref.invalidate(portfolioProvider);
                      ref.invalidate(statsProvider);
                      ref.invalidate(adminUsersProvider);

                      // Wait for data to load
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
                      // ─── Quick Actions ─────────────────────
                      const AppSectionLabel(text: 'إجراءات سريعة'),
                      const SizedBox(height: SpacingTokens.sm),

                      _actionItem(
                        context,
                        cs,
                        BrandIcons.chart,
                        'التحكم في التداول',
                        RouteNames.tradingControl,
                      ),

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
                        BrandIcons.user,
                        'إدارة المستخدمين',
                        RouteNames.userManagement,
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
}
