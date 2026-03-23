import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/constants/app_constants.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/design/icons/brand_icons.dart';
import 'package:trading_app/design/icons/brand_logo.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/utils/responsive_utils.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/app_setting_tile.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/trading_status_strip.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Profile Screen — الحساب / الإعدادات
class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  Future<void> _toggleTrading(bool newValue) async {
    await toggleTradingWithBiometric(
      ref: ref,
      enabled: newValue,
      biometricAuth: (reason) =>
          ref.read(biometricServiceProvider).authenticate(reason: reason),
      showMessage: (message, type) =>
          AppSnackbar.show(context, message: message, type: type),
    );
  }

  Future<void> _showEditProfileDialog(BuildContext context) async {
    final auth = ref.read(authProvider);
    final user = auth.user;
    if (user == null) return;
    final cs = Theme.of(context).colorScheme;

    final nameCtrl = TextEditingController(text: user.name ?? user.username);
    final phoneCtrl = TextEditingController(text: user.phoneNumber ?? '');
    bool saving = false;

    await showDialog<void>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setDlgState) => Directionality(
          textDirection: TextDirection.rtl,
          child: AlertDialog(
            backgroundColor: cs.surfaceContainerHighest,
            title: Text(
              'تعديل الملف الشخصي',
              style: TypographyTokens.h3(cs.onSurface),
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: nameCtrl,
                  textDirection: TextDirection.rtl,
                  decoration: InputDecoration(
                    labelText: 'الاسم الكامل',
                    labelStyle: TypographyTokens.bodySmall(
                      cs.onSurface.withValues(alpha: 0.6),
                    ),
                  ),
                  style: TypographyTokens.body(cs.onSurface),
                ),
                const SizedBox(height: SpacingTokens.md),
                TextField(
                  controller: phoneCtrl,
                  keyboardType: TextInputType.phone,
                  textDirection: TextDirection.rtl,
                  decoration: InputDecoration(
                    labelText: 'رقم الهاتف (اختياري)',
                    labelStyle: TypographyTokens.bodySmall(
                      cs.onSurface.withValues(alpha: 0.6),
                    ),
                  ),
                  style: TypographyTokens.body(cs.onSurface),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: saving ? null : () => Navigator.of(ctx).pop(),
                child: Text(
                  'إلغاء',
                  style: TextStyle(color: cs.onSurface.withValues(alpha: 0.6)),
                ),
              ),
              TextButton(
                onPressed: saving
                    ? null
                    : () async {
                        setDlgState(() => saving = true);
                        final nav = Navigator.of(ctx);
                        try {
                          final repo = ref.read(settingsRepositoryProvider);
                          final name = nameCtrl.text.trim();
                          final phone = phoneCtrl.text.trim();
                          await repo.updateProfile(
                            user.id,
                            fullName: name.isEmpty ? null : name,
                            phone: phone.isEmpty ? null : phone,
                          );
                          final updatedUser = user.copyWith(
                            name: name.isEmpty ? null : name,
                            fullName: name.isEmpty ? null : name,
                            phoneNumber: phone.isEmpty ? null : phone,
                          );
                          ref
                              .read(authProvider.notifier)
                              .updateCurrentUser(updatedUser);
                          if (ctx.mounted) nav.pop();
                          if (context.mounted) {
                            AppSnackbar.show(
                              context,
                              message: 'تم تحديث الملف الشخصي',
                              type: SnackType.success,
                            );
                          }
                        } catch (e) {
                          if (context.mounted) {
                            AppSnackbar.show(
                              context,
                              message: 'تعذر تحديث الملف الشخصي',
                              type: SnackType.error,
                            );
                          }
                        } finally {
                          setDlgState(() => saving = false);
                        }
                      },
                child: saving
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Text('حفظ', style: TextStyle(color: cs.primary)),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final auth = ref.watch(authProvider);
    final tradingState = ref.watch(accountTradingProvider);
    final user = auth.user;
    final pagePadding = ResponsiveUtils.pageHorizontalPadding(context);
    final maxWidth = ResponsiveUtils.maxContentWidth(context);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
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
                  AppScreenHeader(title: 'الحساب', padding: EdgeInsets.zero),
                  const SizedBox(height: SpacingTokens.lg),

                  // ─── User Info Card ────────────────────
                  AppCard(
                    padding: const EdgeInsets.all(SpacingTokens.lg),
                    child: Row(
                      children: [
                        Container(
                          width: 56,
                          height: 56,
                          decoration: BoxDecoration(
                            color: cs.primary.withValues(alpha: 0.12),
                            shape: BoxShape.circle,
                          ),
                          child: Center(
                            child: BrandIcon(
                              BrandIcons.user,
                              size: 28,
                              color: cs.primary,
                            ),
                          ),
                        ),
                        const SizedBox(width: SpacingTokens.base),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                user?.name ?? user?.username ?? 'مستخدم',
                                style: TypographyTokens.h3(cs.onSurface),
                              ),
                              const SizedBox(height: SpacingTokens.xxs),
                              Text(
                                user?.email ?? '',
                                style: TypographyTokens.bodySmall(
                                  cs.onSurface.withValues(alpha: 0.5),
                                ),
                              ),
                              if (auth.isAdmin) ...[
                                const SizedBox(height: SpacingTokens.xs),
                                Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 8,
                                    vertical: 2,
                                  ),
                                  decoration: BoxDecoration(
                                    color: cs.primary.withValues(alpha: 0.12),
                                    borderRadius: BorderRadius.circular(
                                      SpacingTokens.radiusBadge,
                                    ),
                                  ),
                                  child: Text(
                                    'مدير',
                                    style: TypographyTokens.caption(cs.primary),
                                  ),
                                ),
                              ],
                            ],
                          ),
                        ),
                        IconButton(
                          icon: Icon(
                            Icons.edit_outlined,
                            color: cs.primary,
                            size: 20,
                          ),
                          tooltip: 'تعديل',
                          onPressed: () => _showEditProfileDialog(context),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: SpacingTokens.lg),

                  // ─── Trading Toggle ────────────────────
                  TradingStatusStrip(
                    enabled: tradingState.enabled,
                    isLoading: tradingState.isLoading,
                    onChanged: tradingState.enabled == null
                        ? null
                        : _toggleTrading,
                  ),

                  const SizedBox(height: SpacingTokens.lg),

                  // ─── Settings Section ──────────────────
                  _ProfileSectionTitle(title: 'الإعدادات'),
                  const SizedBox(height: SpacingTokens.sm),

                  AppSettingGroup(
                    margin: const EdgeInsets.only(bottom: SpacingTokens.lg),
                    children: [
                      AppSettingTile(
                        icon: BrandIcons.key,
                        label: 'مفاتيح Binance',
                        onTap: () => context.push(RouteNames.binanceKeys),
                      ),
                      AppSettingTile(
                        icon: BrandIcons.shield,
                        label: 'الأمان',
                        onTap: () => context.push(RouteNames.securitySettings),
                      ),
                      AppSettingTile(
                        icon: BrandIcons.info,
                        label: 'دليل الاستخدام',
                        onTap: () => context.push(RouteNames.onboarding),
                      ),
                      AppSettingTile(
                        icon: BrandIcons.eye,
                        label: 'التصميم',
                        onTap: () => context.push(RouteNames.skinPicker),
                      ),
                      AppSettingTile(
                        icon: BrandIcons.bell,
                        label: 'الإشعارات',
                        onTap: () =>
                            context.push(RouteNames.notificationSettings),
                      ),
                    ],
                  ),

                  // ─── Admin Section ─────────────────────
                  if (auth.isAdmin) ...[
                    const SizedBox(height: SpacingTokens.lg),
                    _ProfileSectionTitle(
                      title: 'الإدارة',
                      color: cs.primary.withValues(alpha: 0.7),
                      icon: BrandIcons.shield,
                    ),
                    const SizedBox(height: SpacingTokens.sm),
                    AppSettingGroup(
                      margin: const EdgeInsets.only(bottom: SpacingTokens.lg),
                      children: [
                        AppSettingTile(
                          icon: BrandIcons.chart,
                          label: 'لوحة الإدارة',
                          iconColor: cs.primary,
                          onTap: () => context.push(RouteNames.adminDashboard),
                        ),
                        AppSettingTile(
                          icon: BrandIcons.history,
                          label: 'سجلات النظام',
                          iconColor: cs.primary,
                          onTap: () => context.push(RouteNames.systemLogs),
                        ),
                      ],
                    ),
                  ],

                  const SizedBox(height: SpacingTokens.xl),

                  // ─── App Info ──────────────────────────
                  Center(child: BrandLogo.mini(size: 28)),
                  const SizedBox(height: SpacingTokens.xs),
                  Center(
                    child: Text(
                      'الإصدار ${AppConstants.appVersion}',
                      style: TypographyTokens.caption(
                        cs.onSurface.withValues(alpha: 0.3),
                      ),
                    ),
                  ),

                  const SizedBox(height: SpacingTokens.lg),

                  AppCard(
                    onTap: auth.isLoading
                        ? null
                        : () async => _showDeleteAccountDialog(context),
                    padding: const EdgeInsets.symmetric(
                      horizontal: SpacingTokens.base,
                      vertical: SpacingTokens.md,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.center,
                      children: [
                        Text(
                          'حذف الحساب نهائيًا',
                          style: TypographyTokens.body(
                            cs.error,
                          ).copyWith(fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: SpacingTokens.xxs),
                        Text(
                          'يتطلب كلمة المرور وكتابة DELETE وسيؤدي إلى حذف بياناتك نهائيًا',
                          textAlign: TextAlign.center,
                          style: TypographyTokens.caption(
                            cs.onSurface.withValues(alpha: 0.45),
                          ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: SpacingTokens.md),

                  // ─── Logout ────────────────────────────
                  AppCard(
                    onTap: () async => _showLogoutDialog(context),
                    padding: const EdgeInsets.symmetric(
                      horizontal: SpacingTokens.base,
                      vertical: SpacingTokens.md,
                    ),
                    child: Center(
                      child: Text(
                        'تسجيل الخروج',
                        style: TypographyTokens.body(
                          cs.error,
                        ).copyWith(fontWeight: FontWeight.w600),
                      ),
                    ),
                  ),

                  const SizedBox(height: SpacingTokens.xl),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _showLogoutDialog(BuildContext context) async {
    final cs = Theme.of(context).colorScheme;
    final shouldLogout = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          backgroundColor: cs.surfaceContainerHighest,
          title: Text('تسجيل الخروج', style: TypographyTokens.h3(cs.onSurface)),
          content: Text(
            'هل تريد تسجيل الخروج؟',
            style: TypographyTokens.body(cs.onSurface.withValues(alpha: 0.7)),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(false),
              child: Text('إلغاء', style: TextStyle(color: cs.primary)),
            ),
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(true),
              child: Text('خروج', style: TextStyle(color: cs.error)),
            ),
          ],
        ),
      ),
    );

    if (shouldLogout == true) {
      await ref.read(authProvider.notifier).logout();
    }
  }

  Future<void> _showDeleteAccountDialog(BuildContext context) async {
    final cs = Theme.of(context).colorScheme;
    final passwordCtrl = TextEditingController();
    final confirmationCtrl = TextEditingController();
    bool isSubmitting = false;

    try {
      final deleted = await showDialog<bool>(
        context: context,
        barrierDismissible: !isSubmitting,
        builder: (dialogContext) => StatefulBuilder(
          builder: (dialogContext, setDialogState) => Directionality(
            textDirection: TextDirection.rtl,
            child: AlertDialog(
              backgroundColor: cs.surfaceContainerHighest,
              title: Text(
                'حذف الحساب نهائيًا',
                style: TypographyTokens.h3(cs.error),
              ),
              content: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'سيتم حذف حسابك وبياناته نهائيًا. للتأكيد أدخل كلمة المرور ثم اكتب DELETE كما هي.',
                    style: TypographyTokens.body(
                      cs.onSurface.withValues(alpha: 0.75),
                    ),
                  ),
                  const SizedBox(height: SpacingTokens.md),
                  TextField(
                    controller: passwordCtrl,
                    obscureText: true,
                    enabled: !isSubmitting,
                    decoration: const InputDecoration(
                      labelText: 'كلمة المرور الحالية',
                    ),
                  ),
                  const SizedBox(height: SpacingTokens.sm),
                  TextField(
                    controller: confirmationCtrl,
                    enabled: !isSubmitting,
                    decoration: const InputDecoration(
                      labelText: 'اكتب DELETE للتأكيد',
                    ),
                  ),
                ],
              ),
              actions: [
                TextButton(
                  onPressed: isSubmitting
                      ? null
                      : () => Navigator.of(dialogContext).pop(false),
                  child: Text('إلغاء', style: TextStyle(color: cs.primary)),
                ),
                TextButton(
                  onPressed: isSubmitting
                      ? null
                      : () async {
                          final password = passwordCtrl.text.trim();
                          final confirmation = confirmationCtrl.text.trim();

                          if (password.isEmpty) {
                            AppSnackbar.show(
                              context,
                              message: 'أدخل كلمة المرور الحالية',
                              type: SnackType.error,
                            );
                            return;
                          }
                          if (confirmation != 'DELETE') {
                            AppSnackbar.show(
                              context,
                              message: 'اكتب DELETE للتأكيد النهائي',
                              type: SnackType.error,
                            );
                            return;
                          }

                          setDialogState(() => isSubmitting = true);
                          final result = await ref
                              .read(authProvider.notifier)
                              .deleteAccount(
                                password: password,
                                confirmation: confirmation,
                              );
                          if (!context.mounted) return;

                          if (result['success'] == true) {
                            if (dialogContext.mounted) {
                              Navigator.of(dialogContext).pop(true);
                            }
                            AppSnackbar.show(
                              context,
                              message:
                                  result['message']?.toString() ??
                                  'تم حذف الحساب نهائيًا',
                              type: SnackType.success,
                            );
                          } else {
                            setDialogState(() => isSubmitting = false);
                            AppSnackbar.show(
                              context,
                              message:
                                  result['error']?.toString() ??
                                  result['message']?.toString() ??
                                  'تعذر حذف الحساب',
                              type: SnackType.error,
                            );
                          }
                        },
                  child: isSubmitting
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : Text('حذف نهائي', style: TextStyle(color: cs.error)),
                ),
              ],
            ),
          ),
        ),
      );

      if (deleted == true && context.mounted) {
        context.go(RouteNames.login);
      }
    } finally {
      passwordCtrl.dispose();
      confirmationCtrl.dispose();
    }
  }
}

class _ProfileSectionTitle extends StatelessWidget {
  final String title;
  final Color? color;
  final BrandIconData? icon;

  const _ProfileSectionTitle({required this.title, this.color, this.icon});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final resolvedColor = color ?? cs.onSurface.withValues(alpha: 0.5);

    return Row(
      children: [
        if (icon != null) ...[
          BrandIcon(icon!, size: 14, color: resolvedColor),
          const SizedBox(width: SpacingTokens.xs),
        ],
        Text(title, style: TypographyTokens.label(resolvedColor)),
      ],
    );
  }
}
