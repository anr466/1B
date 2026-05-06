import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pin_code_fields/pin_code_fields.dart';
import 'package:trading_app/core/constants/verification_types.dart';
import 'package:trading_app/core/models/user_model.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/core/services/api_service.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/flow_stepper.dart';
import 'package:trading_app/navigation/route_names.dart';
import 'package:trading_app/features/auth/widgets/countdown_timer.dart';

/// OTP Verification Screen — 6 خانات + عداد 60s + إعادة إرسال
class OtpVerificationScreen extends ConsumerStatefulWidget {
  final Map<String, dynamic>? extra;
  const OtpVerificationScreen({super.key, this.extra});

  @override
  ConsumerState<OtpVerificationScreen> createState() =>
      _OtpVerificationScreenState();
}

class _OtpVerificationScreenState extends ConsumerState<OtpVerificationScreen> {
  String _otpCode = '';
  bool _isLoading = false;
  bool _canResend = false;
  bool _isResending = false;
  int _resendKey = 0;

  String get _screenTitle {
    final title = widget.extra?['flow_title']?.toString();
    if (title != null && title.isNotEmpty) return title;

    switch (_type) {
      case 'change_password':
        return 'تغيير كلمة المرور';
      case 'change_email':
        return 'تغيير البريد الإلكتروني';
      case 'change_biometric':
        return 'تفعيل البصمة';
      case 'forgot_password':
        return 'استعادة كلمة المرور';
      default:
        return 'التحقق';
    }
  }

  String get _screenSubtitle {
    final customSubtitle = widget.extra?['subtitle']?.toString();
    if (customSubtitle != null && customSubtitle.isNotEmpty) {
      return customSubtitle;
    }

    final maskedTarget = widget.extra?['masked_target']?.toString();
    final verificationMethod =
        widget.extra?['verification_method']?.toString() ?? 'email';
    final newEmail =
        widget.extra?['newEmail']?.toString() ??
        widget.extra?['new_email']?.toString() ??
        '';

    switch (_type) {
      case 'change_password':
        return 'أدخل الرمز المرسل إلى البريد المرتبط بحسابك ثم حدّد كلمة المرور الجديدة.';
      case 'change_email':
        if (newEmail.isNotEmpty) {
          return 'أدخل الرمز المرسل إلى $newEmail لتأكيد البريد الإلكتروني الجديد.';
        }
        return 'أدخل الرمز المرسل إلى البريد الإلكتروني الجديد لتأكيد التحديث.';
      case 'change_biometric':
        return 'أدخل رمز التحقق لإكمال تفعيل البصمة على هذا الجهاز.';
      case 'forgot_password':
        if (maskedTarget != null && maskedTarget.isNotEmpty) {
          return 'أدخل الرمز المرسل إلى ${verificationMethod == 'sms' ? 'الهاتف' : 'البريد'} $maskedTarget للمتابعة.';
        }
        return 'أدخل الرمز الذي وصلك للمتابعة إلى إعادة تعيين كلمة المرور.';
      default:
        if (maskedTarget != null && maskedTarget.isNotEmpty) {
          return 'تم إرسال رمز مكون من 6 أرقام إلى\n$maskedTarget';
        }
        return 'تم إرسال رمز مكون من 6 أرقام إلى\n$_email';
    }
  }

  String get _email => widget.extra?['email'] ?? '';
  String get _type => widget.extra?['type'] ?? 'registration';
  String get _oldPassword =>
      widget.extra?['oldPassword'] ?? widget.extra?['old_password'] ?? '';

  bool _isStrongPassword(String value) {
    if (value.length < 8) return false;
    final hasUpper = RegExp(r'[A-Z]').hasMatch(value);
    final hasLower = RegExp(r'[a-z]').hasMatch(value);
    final hasDigit = RegExp(r'\d').hasMatch(value);
    return hasUpper && hasLower && hasDigit;
  }

  Future<void> _verifyOtp() async {
    if (_otpCode.length < 6) return;

    setState(() => _isLoading = true);

    try {
      final authService = ref.read(authServiceProvider);

      Map<String, dynamic> result;

      if (_type == 'registration') {
        result = await authService.verifyRegistrationOtp(
          email: _email,
          code: _otpCode,
          username: widget.extra?['username'] ?? '',
          password: widget.extra?['password'] ?? '',
          phoneNumber:
              widget.extra?['phoneNumber'] ?? widget.extra?['phone'] ?? '',
          name: widget.extra?['fullName'] ?? widget.extra?['name'] ?? '',
        );
      } else if (_type == 'forgot_password') {
        result = await authService.verifyResetOtp(email: _email, otp: _otpCode);
      } else if (_type == 'change_password') {
        // Show new password dialog then verify+apply
        final newPassword = await _showNewPasswordDialog();
        if (newPassword == null || newPassword.isEmpty) return;
        result = await authService.verifyChangePasswordOtp(
          otp: _otpCode,
          newPassword: newPassword,
        );
        if (result['success'] == true) {
          final storage = ref.read(storageServiceProvider);
          final (bioUser, _) = await storage.getBiometricCredentials();
          if (bioUser != null && bioUser.isNotEmpty) {
            await storage.saveBiometricCredentials(bioUser, newPassword);
          }

          if (storage.rememberMeEnabled) {
            final (rememberedUser, _) = await storage.getRememberedCredentials();
            if (rememberedUser != null && rememberedUser.isNotEmpty) {
              await storage.saveRememberedCredentials(
                rememberedUser,
                newPassword,
              );
            }
          }
        }
      } else if (_type == 'change_email') {
        final newEmail =
            widget.extra?['newEmail'] ?? widget.extra?['new_email'] ?? '';
        final userId = widget.extra?['userId'] ?? widget.extra?['user_id'] ?? 0;
        result = await authService.verifyChangeEmailOtp(
          userId: userId is int ? userId : int.tryParse(userId.toString()) ?? 0,
          otp: _otpCode,
          newEmail: newEmail,
        );
        if (result['success'] == true) {
          final auth = ref.read(authProvider);
          final currentUser = auth.user;
          if (currentUser != null) {
            final updatedUser = currentUser.copyWith(
              email: newEmail,
              emailVerified: true,
            );
            ref.read(authProvider.notifier).updateCurrentUser(updatedUser);

            final storage = ref.read(storageServiceProvider);
            final (bioUser, bioPass) = await storage.getBiometricCredentials();
            if (bioUser != null &&
                bioPass != null &&
                bioUser == currentUser.email) {
              await storage.saveBiometricCredentials(newEmail, bioPass);
            }

            if (storage.rememberMeEnabled) {
              final (rememberedUser, rememberedPass) =
                  await storage.getRememberedCredentials();
              if (rememberedUser != null &&
                  rememberedPass != null &&
                  rememberedUser == currentUser.email) {
                await storage.saveRememberedCredentials(
                  newEmail,
                  rememberedPass,
                );
              }
            }
          }
        }
      } else if (_type == 'change_biometric') {
        final action =
            widget.extra?['secure_action']?.toString() ?? 'change_biometric';
        final newValue =
            widget.extra?['newValue'] ?? widget.extra?['new_value'];
        result = await authService.verifySecureAction(
          action: action,
          otp: _otpCode,
          newValue: newValue,
        );
        if (result['success'] == true && action == 'change_biometric') {
          final enabled = newValue == 'enable';
          final storage = ref.read(storageServiceProvider);
          await storage.setBiometricEnabled(enabled);
          if (!enabled) {
            await storage.clearBiometricCredentials();
          }

          final auth = ref.read(authProvider);
          final currentUser = auth.user;
          if (currentUser != null) {
            ref
                .read(authProvider.notifier)
                .updateCurrentUser(
                  currentUser.copyWith(biometricEnabled: enabled),
                );
          }
        }
      } else {
        result = await authService.verifyOtp(
          email: _email,
          code: _otpCode,
          type: _type,
        );
      }

      if (!mounted) return;

      if (result['success'] == true) {
        if (_type == 'registration') {
          // Auto-login: tokens already saved by AuthService._saveAuthData
          final userData = result['user'];
          if (userData != null && userData is Map<String, dynamic>) {
            final user = UserModel.fromJson(userData);
            ref.read(authProvider.notifier).setAuthenticated(user);
            AppSnackbar.show(
              context,
              message: 'تم إنشاء الحساب بنجاح',
              type: SnackType.success,
            );
            context.go(RouteNames.dashboard);
          } else {
            AppSnackbar.show(
              context,
              message: 'اكتمل التحقق لكن استجابة التسجيل غير مكتملة',
              type: SnackType.error,
            );
            return;
          }
        } else if (_type == 'forgot_password') {
          final resetToken = result['reset_token']?.toString();
          if (resetToken == null || resetToken.isEmpty) {
            AppSnackbar.show(
              context,
              message: 'تعذر إنشاء رمز إعادة التعيين',
              type: SnackType.error,
            );
            return;
          }
          context.pushReplacement(
            RouteNames.resetPassword,
            extra: {'email': _email, 'resetToken': resetToken},
          );
        } else if (_type == 'change_password' ||
            _type == 'change_email' ||
            _type == 'change_biometric') {
          context.pop(true);
        } else {
          context.pop(true);
        }
      } else {
        AppSnackbar.show(
          context,
          message:
              result['error'] ?? result['message'] ?? 'رمز التحقق غير صحيح',
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

  Future<String?> _showNewPasswordDialog() async {
    String newPass = '';
    String confirmPass = '';
    final result = await showDialog<String>(
      context: context,
      barrierDismissible: false,
      builder: (_) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          title: const Text('كلمة المرور الجديدة'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextField(
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'كلمة المرور الجديدة',
                ),
                onChanged: (v) => newPass = v,
              ),
              const SizedBox(height: SpacingTokens.md),
              TextField(
                obscureText: true,
                decoration: const InputDecoration(
                  labelText: 'تأكيد كلمة المرور',
                ),
                onChanged: (v) => confirmPass = v,
              ),
            ],
          ),
          actions: [
            AppButton(
              label: 'إلغاء',
              variant: AppButtonVariant.text,
              isFullWidth: false,
              onPressed: () => Navigator.pop(context, null),
            ),
            AppButton(
              label: 'تأكيد',
              variant: AppButtonVariant.primary,
              isFullWidth: false,
              onPressed: () {
                if (!_isStrongPassword(newPass)) {
                  AppSnackbar.show(
                    context,
                    message:
                        'كلمة المرور يجب أن تكون 8 أحرف على الأقل وتحتوي على حرف كبير وصغير ورقم',
                    type: SnackType.error,
                  );
                  return;
                }
                if (newPass != confirmPass) {
                  AppSnackbar.show(
                    context,
                    message: 'كلمة المرور غير متطابقة',
                    type: SnackType.error,
                  );
                  return;
                }
              Navigator.pop(context, newPass);
            },
          ),
          ],
        ),
      ),
    );
    return result;
  }

  Future<void> _resendOtp() async {
    if (!_canResend || _isResending) return;

    setState(() => _isResending = true);
    try {
      final authService = ref.read(authServiceProvider);
      if (_type == 'registration') {
        await authService.sendRegistrationOtp(
          email: _email,
          username: widget.extra?['username'] ?? '',
          password: widget.extra?['password'] ?? '',
          phoneNumber:
              widget.extra?['phoneNumber'] ?? widget.extra?['phone'] ?? '',
          name: widget.extra?['fullName'] ?? widget.extra?['name'] ?? '',
        );
      } else if (_type == 'forgot_password') {
        final method =
            widget.extra?['verification_method']?.toString() ?? 'email';
        final phone = widget.extra?['phone']?.toString();
        await authService.forgotPassword(_email, method: method, phone: phone);
      } else if (_type == 'change_email') {
        final userId = widget.extra?['userId'] ?? widget.extra?['user_id'] ?? 0;
        final newEmail =
            widget.extra?['newEmail'] ?? widget.extra?['new_email'] ?? '';
        await authService.sendChangeEmailOtp(
          userId: userId is int ? userId : int.tryParse(userId.toString()) ?? 0,
          newEmail: newEmail,
        );
      } else if (_type == 'change_password') {
        if (_oldPassword.isEmpty) {
          if (!mounted) return;
          AppSnackbar.show(
            context,
            message: 'تعذر إعادة إرسال الرمز، أعد بدء عملية تغيير كلمة المرور',
            type: SnackType.error,
          );
          return;
        }
        await authService.sendChangePasswordOtp(oldPassword: _oldPassword);
      } else if (_type == 'change_biometric') {
        final action =
            widget.extra?['secure_action']?.toString() ?? 'change_biometric';
        final newValue =
            widget.extra?['newValue'] ?? widget.extra?['new_value'];
        final method =
            widget.extra?['verification_method']?.toString() ?? 'email';
        await authService.requestSecureVerification(
          action: action,
          method: method,
          newValue: newValue,
        );
      } else {
        await authService.sendOtp(email: _email, type: _type);
      }

      if (!mounted) return;
      setState(() {
        _canResend = false;
        _isResending = false;
        _resendKey++;
      });
      AppSnackbar.show(
        context,
        message: 'تم إرسال رمز جديد',
        type: SnackType.success,
      );
    } catch (e) {
      if (!mounted) return;
      setState(() => _isResending = false);
      AppSnackbar.show(
        context,
        message: ApiService.extractError(e),
        type: SnackType.error,
      );
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
              AppScreenHeader(title: _screenTitle, showBack: true),
              Expanded(
                child: Column(
                  children: [
                    if (_type == 'registration')
                      FlowStepper(
                        title: VerificationFlowMetadata.registration.title,
                        steps: VerificationFlowMetadata.registration.steps,
                        currentStep: 1,
                      ),
                    Expanded(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                          horizontal: SpacingTokens.lg,
                        ),
                        child: SingleChildScrollView(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              const SizedBox(height: SpacingTokens.xl),
                              // ─── Instructions ──────────────────────
                              Text(
                                'أدخل رمز التحقق',
                                style: TypographyTokens.h2(cs.onSurface),
                                textAlign: TextAlign.center,
                              ),
                              const SizedBox(height: SpacingTokens.sm),
                              Text(
                                _screenSubtitle,
                                style: TypographyTokens.bodySmall(
                                  cs.onSurface.withValues(alpha: 0.5),
                                ),
                                textAlign: TextAlign.center,
                              ),

                              const SizedBox(height: SpacingTokens.xl),

                              // ─── OTP Input ─────────────────────────
                              Directionality(
                                textDirection: TextDirection.ltr,
                                child: PinCodeTextField(
                                  appContext: context,
                                  length: 6,
                                  onChanged: (value) => _otpCode = value,
                                  onCompleted: (_) => _verifyOtp(),
                                  keyboardType: TextInputType.number,
                                  animationType: AnimationType.fade,
                                  pinTheme: PinTheme(
                                    shape: PinCodeFieldShape.box,
                                    borderRadius: BorderRadius.circular(
                                      SpacingTokens.radiusMd,
                                    ),
                                    fieldHeight: 56,
                                    fieldWidth: 48,
                                    activeFillColor: cs.surfaceContainerHighest,
                                    inactiveFillColor:
                                        cs.surfaceContainerHighest,
                                    selectedFillColor:
                                        cs.surfaceContainerHighest,
                                    activeColor: cs.primary,
                                    inactiveColor: cs.outline,
                                    selectedColor: cs.primary,
                                  ),
                                  enableActiveFill: true,
                                  cursorColor: cs.primary,
                                  textStyle: TypographyTokens.h2(cs.onSurface),
                                ),
                              ),

                              const SizedBox(height: SpacingTokens.lg),

                              // ─── Verify Button ─────────────────────
                              AppButton(
                                label: 'تحقق',
                                onPressed: _otpCode.length == 6
                                    ? _verifyOtp
                                    : null,
                                isLoading: _isLoading,
                              ),

                              const SizedBox(height: SpacingTokens.lg),

                              // ─── Resend ────────────────────────────
                              Center(
                                child: _isResending
                                    ? const SizedBox(
                                        width: 24,
                                        height: 24,
                                        child: CircularProgressIndicator(strokeWidth: 2),
                                      )
                                    : _canResend
                                        ? AppButton(
                                            label: 'إعادة إرسال الرمز',
                                            variant: AppButtonVariant.text,
                                            isFullWidth: false,
                                            onPressed: _resendOtp,
                                          )
                                        : CountdownTimer(
                                            key: ValueKey(_resendKey),
                                            seconds: 60,
                                            onFinished: () =>
                                                setState(() => _canResend = true),
                                          ),
                              ),
                              const SizedBox(height: SpacingTokens.md),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
