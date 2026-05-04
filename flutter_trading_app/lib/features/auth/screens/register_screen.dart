import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/constants/verification_types.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/services/api_service.dart';
import 'package:trading_app/design/icons/brand_logo.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/app_input.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/flow_stepper.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Register Screen — name + email + username + password + phone → OTP
class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _nameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _usernameCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  bool _obscurePassword = true;
  bool _isLoading = false;

  bool _isStrongPassword(String value) {
    if (value.length < 8) return false;
    final hasUpper = RegExp(r'[A-Z]').hasMatch(value);
    final hasLower = RegExp(r'[a-z]').hasMatch(value);
    final hasDigit = RegExp(r'\d').hasMatch(value);
    return hasUpper && hasLower && hasDigit;
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _emailCtrl.dispose();
    _usernameCtrl.dispose();
    _passwordCtrl.dispose();
    _phoneCtrl.dispose();
    super.dispose();
  }

  Future<void> _register() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      final authService = ref.read(authServiceProvider);
      final result = await authService.sendRegistrationOtp(
        name: _nameCtrl.text.trim(),
        email: _emailCtrl.text.trim(),
        username: _usernameCtrl.text.trim(),
        password: _passwordCtrl.text,
        phoneNumber: _phoneCtrl.text.trim(),
      );

      if (!mounted) return;

      if (result['success'] == true) {
        final effectiveMethod = result['method']?.toString() ?? 'email';
        final maskedTarget = result['masked_target']?.toString();
        final successMessage = maskedTarget != null && maskedTarget.isNotEmpty
            ? 'تم إرسال رمز التحقق إلى ${effectiveMethod == 'sms' ? 'الهاتف' : 'البريد'} $maskedTarget'
            : 'تم إرسال رمز التحقق';
        AppSnackbar.show(
          context,
          message: successMessage,
          type: SnackType.success,
        );
        context.push(
          RouteNames.otpVerification,
          extra: VerificationFlowMetadata.registration.toExtra(
            additionalData: {
              'email': _emailCtrl.text.trim(),
              'username': _usernameCtrl.text.trim(),
              'password': _passwordCtrl.text,
              'phone': _phoneCtrl.text.trim(),
              'name': _nameCtrl.text.trim(),
              'verification_method': effectiveMethod,
              if (maskedTarget != null && maskedTarget.isNotEmpty)
                'masked_target': maskedTarget,
            },
          ),
        );
      } else {
        AppSnackbar.show(
          context,
          message:
              result['error']?.toString() ??
              result['message']?.toString() ??
              'فشل التسجيل',
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
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            children: [
              AppScreenHeader(title: 'حساب جديد', showBack: true),
              FlowStepper(
                title: VerificationFlowMetadata.registration.title,
                steps: VerificationFlowMetadata.registration.steps,
                currentStep: 0,
              ),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(
                    horizontal: SpacingTokens.lg,
                  ),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        const SizedBox(height: SpacingTokens.base),
                        const Center(child: BrandLogo.mini(size: 48)),
                        const SizedBox(height: SpacingTokens.lg),

                        // ─── Name ──────────────────────────────
                        AppInput(
                          controller: _nameCtrl,
                          label: 'الاسم الكامل',
                          textInputAction: TextInputAction.next,
                          validator: (v) =>
                              v == null || v.trim().isEmpty ? 'مطلوب' : null,
                        ),
                        const SizedBox(height: SpacingTokens.md),

                        // ─── Email ─────────────────────────────
                        AppInput(
                          controller: _emailCtrl,
                          label: 'البريد الإلكتروني',
                          keyboardType: TextInputType.emailAddress,
                          textInputAction: TextInputAction.next,
                          validator: (v) {
                            if (v == null || v.trim().isEmpty) return 'مطلوب';
                            if (!v.contains('@') || !v.contains('.')) {
                              return 'بريد إلكتروني غير صالح';
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: SpacingTokens.md),

                        // ─── Username ──────────────────────────
                        AppInput(
                          controller: _usernameCtrl,
                          label: 'اسم المستخدم',
                          textInputAction: TextInputAction.next,
                          validator: (v) {
                            if (v == null || v.trim().isEmpty) return 'مطلوب';
                            if (v.trim().length < 3) return '3 أحرف على الأقل';
                            return null;
                          },
                        ),
                        const SizedBox(height: SpacingTokens.md),

                        // ─── Phone ─────────────────────────────
                        AppInput(
                          controller: _phoneCtrl,
                          label: 'رقم الجوال',
                          keyboardType: TextInputType.phone,
                          textInputAction: TextInputAction.next,
                          validator: (v) =>
                              v == null || v.trim().isEmpty ? 'مطلوب' : null,
                        ),
                        const SizedBox(height: SpacingTokens.md),

                        // ─── Password ──────────────────────────
                        AppInput(
                          controller: _passwordCtrl,
                          label: 'كلمة المرور',
                          obscureText: _obscurePassword,
                          textInputAction: TextInputAction.done,
                          onSubmitted: (_) => _register(),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscurePassword
                                  ? Icons.visibility_off_outlined
                                  : Icons.visibility_outlined,
                              color: cs.onSurface.withValues(alpha: 0.4),
                              size: 20,
                            ),
                            onPressed: () => setState(
                              () => _obscurePassword = !_obscurePassword,
                            ),
                          ),
                          validator: (v) {
                            if (v == null || v.isEmpty) return 'مطلوب';
                            if (!_isStrongPassword(v)) {
                              return '8 أحرف على الأقل وتحتوي حرف كبير وصغير ورقم';
                            }
                            return null;
                          },
                        ),

                        const SizedBox(height: SpacingTokens.lg),

                        // ─── Register Button ───────────────────
                        AppButton(
                          label: 'إنشاء حساب',
                          onPressed: _register,
                          isLoading: _isLoading,
                        ),

                        const SizedBox(height: SpacingTokens.base),

                        // ─── Login Link ────────────────────────
                        Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              'لديك حساب؟',
                              style: TypographyTokens.bodySmall(
                                cs.onSurface.withValues(alpha: 0.5),
                              ),
                            ),
                            AppButton(
                              label: 'تسجيل الدخول',
                              variant: AppButtonVariant.text,
                              isFullWidth: false,
                              onPressed: () => context.pop(),
                            ),
                          ],
                        ),
                        const SizedBox(height: SpacingTokens.xl),
                      ],
                    ),
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
