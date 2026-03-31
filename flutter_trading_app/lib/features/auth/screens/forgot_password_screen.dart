import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/constants/ux_messages.dart';
import 'package:trading_app/core/constants/verification_types.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/app_input.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/flow_stepper.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Forgot Password Screen — إدخال email → إرسال OTP
class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() =>
      _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  bool _isLoading = false;
  String _method = 'email';

  @override
  void dispose() {
    _emailCtrl.dispose();
    _phoneCtrl.dispose();
    super.dispose();
  }

  Future<void> _sendOtp() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      final authService = ref.read(authServiceProvider);
      final result = await authService.forgotPassword(
        _emailCtrl.text.trim(),
        method: _method,
        phone: _method == 'sms' ? _phoneCtrl.text.trim() : null,
      );

      if (!mounted) return;

      if (result['success'] == true) {
        final effectiveMethod = result['method']?.toString() ?? _method;
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
          extra: VerificationFlowMetadata.forgotPassword.toExtra(
            additionalData: {
              'email': _emailCtrl.text.trim(),
              'verification_method': effectiveMethod,
              if (effectiveMethod == 'sms') 'phone': _phoneCtrl.text.trim(),
              if (maskedTarget != null && maskedTarget.isNotEmpty)
                'masked_target': maskedTarget,
            },
          ),
        );
      } else {
        AppSnackbar.show(
          context,
          message: UxMessages.error,
          type: SnackType.error,
        );
      }
    } catch (e) {
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message: UxMessages.error,
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
              AppScreenHeader(title: 'نسيت كلمة المرور', showBack: true),
              Expanded(
                child: Column(
                  children: [
                    FlowStepper(
                      title: 'استعادة كلمة المرور',
                      steps: const [
                        'إدخال البريد',
                        'رمز التحقق',
                        'كلمة المرور الجديدة',
                      ],
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
                              const SizedBox(height: SpacingTokens.xl),
                              Text(
                                'اختر طريقة الاستعادة ثم أدخل بياناتك',
                                style: TypographyTokens.body(
                                  cs.onSurface.withValues(alpha: 0.6),
                                ),
                                textAlign: TextAlign.center,
                              ),
                              const SizedBox(height: SpacingTokens.xl),
                              SegmentedButton<String>(
                                segments: const [
                                  ButtonSegment(
                                    value: 'email',
                                    label: Text('البريد الإلكتروني'),
                                  ),
                                  ButtonSegment(
                                    value: 'sms',
                                    label: Text('رسالة SMS'),
                                  ),
                                ],
                                selected: {_method},
                                onSelectionChanged: (v) {
                                  if (v.isEmpty) return;
                                  setState(() => _method = v.first);
                                },
                              ),
                              const SizedBox(height: SpacingTokens.md),
                              AppInput(
                                controller: _emailCtrl,
                                label: 'البريد الإلكتروني',
                                keyboardType: TextInputType.emailAddress,
                                textInputAction: TextInputAction.done,
                                onSubmitted: (_) =>
                                    _method == 'sms' ? null : _sendOtp(),
                                validator: (v) {
                                  if (v == null || v.trim().isEmpty) {
                                    return 'مطلوب';
                                  }
                                  if (!v.contains('@')) {
                                    return 'بريد إلكتروني غير صالح';
                                  }
                                  return null;
                                },
                              ),
                              if (_method == 'sms') ...[
                                const SizedBox(height: SpacingTokens.md),
                                AppInput(
                                  controller: _phoneCtrl,
                                  label: 'رقم الجوال (اختياري)',
                                  keyboardType: TextInputType.phone,
                                  textInputAction: TextInputAction.done,
                                  onSubmitted: (_) => _sendOtp(),
                                ),
                              ],
                              const SizedBox(height: SpacingTokens.lg),
                              AppButton(
                                label: 'إرسال رمز التحقق',
                                onPressed: _sendOtp,
                                isLoading: _isLoading,
                              ),
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
