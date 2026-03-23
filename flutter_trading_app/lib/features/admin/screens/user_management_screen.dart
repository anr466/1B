import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/providers/admin_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/providers/trades_provider.dart';
import 'package:trading_app/design/icons/brand_icons.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/empty_state.dart';
import 'package:trading_app/design/widgets/error_state.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/status_badge.dart';

/// User Management Screen — إدارة المستخدمين
class UserManagementScreen extends ConsumerStatefulWidget {
  const UserManagementScreen({super.key});

  @override
  ConsumerState<UserManagementScreen> createState() =>
      _UserManagementScreenState();
}

class _UserManagementScreenState extends ConsumerState<UserManagementScreen> {
  final Set<int> _toggling = {};

  Future<void> _toggleTrading(int userId, bool currentEnabled) async {
    if (_toggling.contains(userId)) return;
    setState(() => _toggling.add(userId));
    try {
      final repo = ref.read(adminRepositoryProvider);
      await repo.toggleUserTrading(userId, !currentEnabled);
      ref.invalidate(adminUsersProvider);
      ref.invalidate(portfolioProvider);
      ref.invalidate(statsProvider);
      ref.invalidate(activePositionsProvider);
      ref.invalidate(recentTradesProvider);
      ref.invalidate(dailyStatusProvider);
      ref.invalidate(tradingCycleLiveProvider);
      ref.invalidate(systemStatusProvider);
    } catch (e) {
      if (mounted) {
        AppSnackbar.show(
          context,
          message: 'تعذر إتمام العملية، حاول مرة أخرى',
          type: SnackType.error,
        );
      }
    } finally {
      if (mounted) setState(() => _toggling.remove(userId));
    }
  }

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
                          final isActive =
                              u['isActive'] == true ||
                              u['isActive'] == 1 ||
                              u['is_active'] == true ||
                              u['is_active'] == 1 ||
                              u['emailVerified'] == true ||
                              u['emailVerified'] == 1 ||
                              u['email_verified'] == true ||
                              u['email_verified'] == 1;
                          final tradingEnabled =
                              u['tradingEnabled'] == true ||
                              u['tradingEnabled'] == 1 ||
                              u['trading_enabled'] == true ||
                              u['trading_enabled'] == 1;
                          final tradingMode =
                              (u['tradingMode'] ?? u['trading_mode'] ?? '')
                                  .toString();
                          final isToggling = _toggling.contains(userId);

                          return Padding(
                            padding: const EdgeInsets.only(
                              bottom: SpacingTokens.sm,
                            ),
                            child: AppCard(
                              padding: const EdgeInsets.all(SpacingTokens.md),
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
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
                                            Row(
                                              children: [
                                                StatusBadge(
                                                  text: tradingEnabled
                                                      ? 'تداول مفعّل'
                                                      : 'تداول متوقف',
                                                  type: tradingEnabled
                                                      ? BadgeType.success
                                                      : BadgeType.warning,
                                                  showDot: tradingEnabled,
                                                ),
                                                if (tradingEnabled) ...[
                                                  const SizedBox(
                                                    width: SpacingTokens.xs,
                                                  ),
                                                  StatusBadge(
                                                    text: tradingMode == 'real'
                                                        ? 'حقيقي'
                                                        : 'تجريبي',
                                                    type: tradingMode == 'real'
                                                        ? BadgeType.warning
                                                        : BadgeType.info,
                                                    showDot: false,
                                                  ),
                                                ],
                                              ],
                                            ),
                                          ],
                                        ),
                                      ),

                                      // Status badges
                                      Column(
                                        crossAxisAlignment:
                                            CrossAxisAlignment.end,
                                        children: [
                                          if (isAdmin)
                                            StatusBadge(
                                              text: 'مدير',
                                              type: BadgeType.info,
                                              showDot: false,
                                            ),
                                          const SizedBox(
                                            height: SpacingTokens.xs,
                                          ),
                                          StatusBadge(
                                            text: isActive
                                                ? 'مفعّل'
                                                : 'غير مفعّل',
                                            type: isActive
                                                ? BadgeType.success
                                                : BadgeType.warning,
                                            showDot: false,
                                          ),
                                        ],
                                      ),
                                    ],
                                  ),

                                  // Trading toggle row
                                  if (!isAdmin) ...[
                                    const Divider(height: SpacingTokens.lg),
                                    Row(
                                      mainAxisAlignment:
                                          MainAxisAlignment.spaceBetween,
                                      children: [
                                        Text(
                                          'تفعيل التداول',
                                          style: TypographyTokens.bodySmall(
                                            cs.onSurface.withValues(alpha: 0.7),
                                          ),
                                        ),
                                        isToggling
                                            ? const SizedBox(
                                                width: 24,
                                                height: 24,
                                                child:
                                                    CircularProgressIndicator(
                                                      strokeWidth: 2,
                                                    ),
                                              )
                                            : Switch.adaptive(
                                                value: tradingEnabled,
                                                onChanged: (_) =>
                                                    _toggleTrading(
                                                      userId,
                                                      tradingEnabled,
                                                    ),
                                              ),
                                      ],
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
