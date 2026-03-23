import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/constants/ux_messages.dart';
import 'package:trading_app/core/constants/verification_types.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/services/api_service.dart';
import 'package:trading_app/design/icons/brand_icons.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_section_label.dart';
import 'package:trading_app/design/widgets/flow_stepper.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/main.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Security Settings Screen — الأمان (تغيير كلمة المرور + البصمة)
class SecuritySettingsScreen extends ConsumerStatefulWidget {
  const SecuritySettingsScreen({super.key});

  @override
  ConsumerState<SecuritySettingsScreen> createState() =>
      _SecuritySettingsScreenState();
}

class _SecuritySettingsScreenState
    extends ConsumerState<SecuritySettingsScreen> {
  bool _biometricEnabled = false;
  String _biometricTypeLabel = '...';
  bool _isBusy = false;

  @override
  void initState() {
    super.initState();
    _loadSecurityState();
    Future.microtask(() async {
      final bio = ref.read(biometricServiceProvider);
      final label = await bio.biometricTypeLabel;
      if (!mounted) return;
      setState(() => _biometricTypeLabel = label);
    });
  }

  void _loadSecurityState() {
    final storage = ref.read(storageServiceProvider);
    _biometricEnabled = storage.biometricEnabled;
  }

  Future<void> _sendChangePasswordOtp() async {
    final auth = ref.read(authProvider);
    final user = auth.user;
    if (user == null) return;

    String oldPassword = '';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          title: const Text('تغيير كلمة المرور'),
          content: TextField(
            obscureText: true,
            decoration: const InputDecoration(labelText: 'كلمة المرور الحالية'),
            onChanged: (value) => oldPassword = value,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('إلغاء'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('إرسال الرمز'),
            ),
          ],
        ),
      ),
    );

    if (confirmed != true) return;
    oldPassword = oldPassword.trim();
    if (oldPassword.isEmpty) {
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message: 'أدخل كلمة المرور الحالية',
        type: SnackType.error,
      );
      return;
    }

    try {
      setState(() => _isBusy = true);
      final authService = ref.read(authServiceProvider);
      final result = await authService.sendChangePasswordOtp(
        oldPassword: oldPassword,
      );

      if (!mounted) return;
      if (result['success'] == true) {
        AppSnackbar.show(
          context,
          message: 'تم إرسال رمز التحقق',
          type: SnackType.info,
        );
        final verified = await context.push<bool>(
          RouteNames.otpVerification,
          extra: VerificationFlowMetadata.changePassword.toExtra(
            additionalData: {'email': user.email, 'oldPassword': oldPassword},
          ),
        );
        if (!mounted) return;
        if (verified == true) {
          AppSnackbar.show(
            context,
            message: 'تم تغيير كلمة المرور بنجاح',
            type: SnackType.success,
          );
        }
      } else {
        AppSnackbar.show(
          context,
          message: result['error'] ?? result['message'] ?? UxMessages.error,
          type: SnackType.error,
        );
      }
    } catch (e) {
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message: ApiService.extractError(e),
        type: SnackType.error,
      );
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  Future<void> _sendChangeEmailOtp() async {
    final auth = ref.read(authProvider);
    final user = auth.user;
    if (user == null) return;

    String newEmail = '';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          title: const Text('تغيير البريد الإلكتروني'),
          content: TextField(
            keyboardType: TextInputType.emailAddress,
            decoration: const InputDecoration(
              labelText: 'البريد الإلكتروني الجديد',
            ),
            onChanged: (value) => newEmail = value,
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('إلغاء'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('إرسال الرمز'),
            ),
          ],
        ),
      ),
    );

    if (confirmed != true) return;
    newEmail = newEmail.trim();
    if (newEmail.isEmpty || !newEmail.contains('@')) {
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message: 'أدخل بريدًا إلكترونيًا صحيحًا',
        type: SnackType.error,
      );
      return;
    }

    try {
      setState(() => _isBusy = true);
      final authService = ref.read(authServiceProvider);
      final result = await authService.sendChangeEmailOtp(
        userId: user.id,
        newEmail: newEmail,
      );

      if (!mounted) return;
      if (result['success'] == true) {
        AppSnackbar.show(
          context,
          message: 'تم إرسال رمز التحقق',
          type: SnackType.info,
        );
        final verified = await context.push<bool>(
          RouteNames.otpVerification,
          extra: VerificationFlowMetadata.changeEmail.toExtra(
            additionalData: {
              'email': user.email,
              'newEmail': newEmail,
              'userId': user.id,
            },
          ),
        );
        if (!mounted) return;
        if (verified == true) {
          AppSnackbar.show(
            context,
            message: 'تم تغيير البريد الإلكتروني بنجاح',
            type: SnackType.success,
          );
        }
      } else {
        AppSnackbar.show(
          context,
          message: result['error'] ?? result['message'] ?? UxMessages.error,
          type: SnackType.error,
        );
      }
    } catch (e) {
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message: ApiService.extractError(e),
        type: SnackType.error,
      );
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  Future<void> _toggleBiometric(bool value) async {
    final bio = ref.read(biometricServiceProvider);
    final auth = ref.read(authProvider);
    final storage = ref.read(storageServiceProvider);
    final available = await bio.isAvailable;

    if (!available) {
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message: 'الجهاز لا يدعم البصمة',
        type: SnackType.error,
      );
      return;
    }

    // When enabling biometric, we need credentials saved
    if (value) {
      final (savedUser, savedPass) = storage.biometricCredentials;

      // If no credentials saved, prompt user to enter them
      if (savedUser == null || savedPass == null) {
        if (!mounted) return;
        final credentials = await _showCredentialDialog(
          'حفظ بيانات الدخول',
          'أدخل بيانات الدخول لحفظها وتسجيل الدخول بالبصمة مستقبلاً',
        );
        if (credentials == null) return;

        // Verify credentials
        final verifyResult = await ref
            .read(authServiceProvider)
            .login(
              emailOrUsername: credentials['email']!,
              password: credentials['password']!,
            );

        if (verifyResult['success'] != true) {
          if (!mounted) return;
          AppSnackbar.show(
            context,
            message: 'بيانات الدخول غير صحيحة',
            type: SnackType.error,
          );
          return;
        }

        // Save credentials for biometric
        await storage.saveBiometricCredentials(
          credentials['email']!,
          credentials['password']!,
        );
      }
    }

    try {
      setState(() => _isBusy = true);
      await storage.setBiometricEnabled(value);

      if (!value) {
        await storage.clearBiometricCredentials();
      }

      final currentUser = auth.user;
      if (currentUser != null) {
        ref
            .read(authProvider.notifier)
            .updateCurrentUser(currentUser.copyWith(biometricEnabled: value));
      }

      if (!mounted) return;
      setState(() {
        _biometricEnabled = value;
      });

      AppSnackbar.show(
        context,
        message: value ? 'تم تفعيل البصمة بنجاح' : 'تم تعطيل البصمة',
        type: SnackType.success,
      );
    } catch (e) {
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message: ApiService.extractError(e),
        type: SnackType.error,
      );
    } finally {
      if (mounted) setState(() => _isBusy = false);
    }
  }

  Future<Map<String, String>?> _showCredentialDialog(
    String title,
    String message,
  ) async {
    String email = '';
    String password = '';

    return showDialog<Map<String, String>>(
      context: context,
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          title: Text(title),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(message),
              const SizedBox(height: SpacingTokens.md),
              TextField(
                decoration: const InputDecoration(
                  labelText: 'البريد الإلكتروني أو المستخدم',
                ),
                onChanged: (v) => email = v.trim(),
              ),
              const SizedBox(height: SpacingTokens.sm),
              TextField(
                obscureText: true,
                decoration: const InputDecoration(labelText: 'كلمة المرور'),
                onChanged: (v) => password = v,
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: const Text('إلغاء'),
            ),
            TextButton(
              onPressed: () {
                if (email.isNotEmpty && password.isNotEmpty) {
                  Navigator.pop(ctx, {'email': email, 'password': password});
                }
              },
              child: const Text('حفظ'),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        appBar: AppBar(
          title: Text('الأمان', style: TypographyTokens.h3(cs.onSurface)),
        ),
        body: ListView(
          padding: const EdgeInsets.all(SpacingTokens.base),
          children: [
            FlowStepper(
              title: 'إعدادات الأمان',
              steps: const ['اختيار العملية', 'التحقق', 'الإتمام'],
              currentStep: 0,
            ),
            const SizedBox(height: SpacingTokens.lg),
            // ─── Biometric Toggle ────────────────────
            AppCard(
              padding: const EdgeInsets.symmetric(
                horizontal: SpacingTokens.base,
                vertical: SpacingTokens.sm,
              ),
              child: Row(
                children: [
                  BrandIcon(BrandIcons.shield, size: 22, color: cs.primary),
                  const SizedBox(width: SpacingTokens.md),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'تسجيل الدخول بالبصمة',
                          style: TypographyTokens.body(cs.onSurface),
                        ),
                        const SizedBox(height: SpacingTokens.xxs),
                        Text(
                          'دخول سريع بدون كلمة مرور • النوع: $_biometricTypeLabel',
                          style: TypographyTokens.caption(
                            cs.onSurface.withValues(alpha: 0.4),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Switch(
                    value: _biometricEnabled,
                    onChanged: _isBusy ? null : _toggleBiometric,
                    activeTrackColor: cs.primary,
                    thumbColor: WidgetStatePropertyAll(
                      _biometricEnabled
                          ? cs.onPrimary
                          : cs.onSurface.withValues(alpha: 0.3),
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: SpacingTokens.lg),
            const AppSectionLabel(text: 'إجراءات آمنة'),
            const SizedBox(height: SpacingTokens.sm),

            // ─── Change Password ─────────────────────
            _secureActionItem(
              cs,
              BrandIcons.lock,
              'تغيير كلمة المرور',
              'يتطلب كلمة المرور الحالية ثم رمز تحقق عبر البريد المرتبط بالحساب',
              _sendChangePasswordOtp,
            ),

            // ─── Change Email ────────────────────────
            _secureActionItem(
              cs,
              BrandIcons.key,
              'تغيير البريد الإلكتروني',
              'يتم إرسال رمز التحقق إلى البريد الإلكتروني الجديد',
              _sendChangeEmailOtp,
            ),

            const SizedBox(height: SpacingTokens.lg),
            const AppSectionLabel(text: 'الجلسات'),
            const SizedBox(height: SpacingTokens.sm),

            // ─── Active Sessions Info ────────────────
            AppCard(
              padding: const EdgeInsets.all(SpacingTokens.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      BrandIcon(BrandIcons.eye, size: 20, color: cs.primary),
                      const SizedBox(width: SpacingTokens.sm),
                      Text(
                        'الجلسة الحالية',
                        style: TypographyTokens.body(cs.onSurface),
                      ),
                    ],
                  ),
                  const SizedBox(height: SpacingTokens.sm),
                  Text(
                    'نشطة الآن',
                    style: TypographyTokens.bodySmall(cs.primary),
                  ),
                  const SizedBox(height: SpacingTokens.xs),
                  Text(
                    'بيانات الدخول تُدار تلقائيًا — فعّل "تذكرني" في شاشة الدخول لحفظها',
                    style: TypographyTokens.caption(
                      cs.onSurface.withValues(alpha: 0.45),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _secureActionItem(
    ColorScheme cs,
    BrandIconData icon,
    String title,
    String subtitle,
    VoidCallback onTap,
  ) {
    return Padding(
      padding: const EdgeInsets.only(bottom: SpacingTokens.sm),
      child: AppCard(
        onTap: onTap,
        padding: const EdgeInsets.symmetric(
          horizontal: SpacingTokens.base,
          vertical: SpacingTokens.md,
        ),
        child: Row(
          children: [
            BrandIcon(icon, size: 20, color: cs.primary),
            const SizedBox(width: SpacingTokens.md),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: TypographyTokens.body(cs.onSurface)),
                  const SizedBox(height: SpacingTokens.xxs),
                  Text(
                    subtitle,
                    style: TypographyTokens.caption(
                      cs.onSurface.withValues(alpha: 0.4),
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_left,
              color: cs.onSurface.withValues(alpha: 0.3),
              size: 20,
            ),
          ],
        ),
      ),
    );
  }
}
