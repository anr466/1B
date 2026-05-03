import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/providers/admin_provider.dart';
import 'package:trading_app/design/icons/brand_icons.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/empty_state.dart';
import 'package:trading_app/design/widgets/error_state.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/status_badge.dart';
import 'package:trading_app/design/widgets/trading_toggle_button.dart';
import 'package:trading_app/design/widgets/demo_real_banner.dart';
import 'package:trading_app/navigation/route_names.dart';

/// User Management Screen — إدارة المستخدمين
class UserManagementScreen extends ConsumerStatefulWidget {
  const UserManagementScreen({super.key});

  @override
  ConsumerState<UserManagementScreen> createState() =>
      _UserManagementScreenState();
}

class _UserManagementScreenState extends ConsumerState<UserManagementScreen> {
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final usersAsync = ref.watch(adminUsersProvider);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            children: [
              AppScreenHeader(title: 'إدارة المستخدمين', showBack: true),
              const DemoRealBanner(),
              Expanded(
                child: RefreshIndicator(
                  color: cs.primary,
                  onRefresh: () async => ref.invalidate(adminUsersProvider),
                  child: usersAsync.when(
                    loading: () => const Padding(
                      padding: EdgeInsets.all(SpacingTokens.base),
                      child: LoadingShimmer(itemCount: 5, itemHeight: 72),
                    ),
                    error: (e, _) => ErrorState(
                      message: e.toString(),
                      onRetry: () => ref.invalidate(adminUsersProvider),
                    ),
                    data: (users) {
                      if (users.isEmpty) {
                        return const EmptyState(message: 'لا يوجد مستخدمون');
                      }

                      return ListView.builder(
                        padding: const EdgeInsets.all(SpacingTokens.base),
                        itemCount: users.length,
                        itemBuilder: (_, i) {
                          final u = users[i];
                          final userId = u['id'] as int? ?? 0;
                          final isAdmin =
                              (u['userType'] ?? u['user_type'] ?? u['type']) ==
                              'admin';
                          final tradingEnabled =
                              u['tradingEnabled'] == true ||
                              u['tradingEnabled'] == 1 ||
                              u['trading_enabled'] == true ||
                              u['trading_enabled'] == 1;
                          return Padding(
                            padding: const EdgeInsets.only(
                              bottom: SpacingTokens.sm,
                            ),
                            child: AppCard(
                              padding: const EdgeInsets.all(SpacingTokens.md),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  GestureDetector(
                                    onTap: () => context.push(
                                      RouteNames.adminUserDetail,
                                      extra: u,
                                    ),
                                    child: Row(
                                      children: [
                                        // Avatar
                                        Container(
                                          width: 44,
                                          height: 44,
                                          decoration: BoxDecoration(
                                            color: isAdmin
                                                ? cs.primary.withValues(
                                                    alpha: 0.12,
                                                  )
                                                : cs.surfaceContainerHighest,
                                            shape: BoxShape.circle,
                                          ),
                                          child: Center(
                                            child: BrandIcon(
                                              isAdmin
                                                  ? BrandIcons.shield
                                                  : BrandIcons.user,
                                              size: 20,
                                              color: isAdmin
                                                  ? cs.primary
                                                  : cs.onSurface.withValues(
                                                      alpha: 0.5,
                                                    ),
                                            ),
                                          ),
                                        ),
                                        const SizedBox(width: SpacingTokens.md),

                                        // Info
                                        Expanded(
                                          child: Column(
                                            crossAxisAlignment:
                                                CrossAxisAlignment.start,
                                            children: [
                                              Text(
                                                u['fullName'] ??
                                                    u['full_name'] ??
                                                    u['name'] ??
                                                    u['username'] ??
                                                    'مستخدم',
                                                style:
                                                    TypographyTokens.body(
                                                      cs.onSurface,
                                                    ).copyWith(
                                                      fontWeight: FontWeight.w600,
                                                    ),
                                              ),
                                              const SizedBox(
                                                height: SpacingTokens.xxs,
                                              ),
                                              Text(
                                                u['email'] ?? '',
                                                style: TypographyTokens.caption(
                                                  cs.onSurface.withValues(
                                                    alpha: 0.4,
                                                  ),
                                                ),
                                              ),
                                              const SizedBox(
                                                height: SpacingTokens.xxs,
                                              ),
                                              StatusBadge(
                                                text: tradingEnabled
                                                    ? 'مفعّل'
                                                    : 'متوقف',
                                                type: tradingEnabled
                                                    ? BadgeType.success
                                                    : BadgeType.warning,
                                                showDot: tradingEnabled,
                                              ),
                                            ],
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),

                                  // Trading toggle row
                                  if (!isAdmin) ...[
                                    const Divider(height: SpacingTokens.lg),
                                    TradingToggleButton(
                                      targetUserId: userId,
                                      value: tradingEnabled,
                                      subtitle: tradingEnabled
                                          ? 'يفتح صفقات جديدة'
                                          : 'لن يفتح صفقات جديدة',
                                      onChanged: (_) {
                                        ref.invalidate(adminUsersProvider);
                                      },
                                    ),
                                  ],
                                ],
                              ),
                            ),
                          );
                        },
                      );
                    },
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

}
