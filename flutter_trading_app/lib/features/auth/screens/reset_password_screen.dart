import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/constants/ux_messages.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/services/api_service.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/app_input.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/flow_stepper.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Reset Password Screen — OTP verified, set new password
class ResetPasswordScreen extends ConsumerStatefulWidget {
  final Map<String, dynamic>? extra;
  const ResetPasswordScreen({super.key, this.extra});

  @override
  ConsumerState<ResetPasswordScreen> createState() =>
      _ResetPasswordScreenState();
}

class _ResetPasswordScreenState extends ConsumerState<ResetPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _passwordCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  bool _obscure1 = true;
  bool _obscure2 = true;
  bool _isLoading = false;

  bool _isStrongPassword(String value) {
    if (value.length < 8) return false;
    final hasUpper = RegExp(r'[A-Z]').hasMatch(value);
    final hasLower = RegExp(r'[a-z]').hasMatch(value);
    final hasDigit = RegExp(r'\d').hasMatch(value);
    return hasUpper && hasLower && hasDigit;
  }

  String get _resetToken => widget.extra?['resetToken'] ?? '';

  @override
  void dispose() {
    _passwordCtrl.dispose();
    _confirmCtrl.dispose();
    super.dispose();
  }

  Future<void> _resetPassword() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      final authService = ref.read(authServiceProvider);
      final result = await authService.resetPassword(
        resetToken: _resetToken,
        newPassword: _passwordCtrl.text,
      );

      if (!mounted) return;

      if (result['success'] == true) {
        AppSnackbar.show(
          context,
          message: UxMessages.success,
          type: SnackType.success,
        );
        context.go(RouteNames.login);
      } else {
        AppSnackbar.show(
          context,
          message: result['error']?.toString() ?? UxMessages.error,
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
        appBar: AppBar(
          title: Text(
            'كلمة مرور جديدة',
            style: TypographyTokens.h3(cs.onSurface),
          ),
        ),
        body: SafeArea(
          child: Column(
            children: [
              FlowStepper(
                title: 'استعادة كلمة المرور',
                steps: const [
                  'إدخال البريد',
                  'رمز التحقق',
                  'كلمة المرور الجديدة',
                ],
                currentStep: 2,
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
                          'أدخل كلمة المرور الجديدة',
                          style: TypographyTokens.body(
                            cs.onSurface.withValues(alpha: 0.6),
                          ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: SpacingTokens.xl),

                        AppInput(
                          controller: _passwordCtrl,
                          label: 'كلمة المرور الجديدة',
                          obscureText: _obscure1,
                          textInputAction: TextInputAction.next,
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscure1
                                  ? Icons.visibility_off_outlined
                                  : Icons.visibility_outlined,
                              color: cs.onSurface.withValues(alpha: 0.4),
                              size: 20,
                            ),
                            onPressed: () =>
                                setState(() => _obscure1 = !_obscure1),
                          ),
                          validator: (v) {
                            if (v == null || v.isEmpty) return 'مطلوب';
                            if (!_isStrongPassword(v)) {
                              return '8 أحرف على الأقل وتحتوي حرف كبير وصغير ورقم';
                            }
                            return null;
                          },
                        ),
                        const SizedBox(height: SpacingTokens.md),

                        AppInput(
                          controller: _confirmCtrl,
                          label: 'تأكيد كلمة المرور',
                          obscureText: _obscure2,
                          textInputAction: TextInputAction.done,
                          onSubmitted: (_) => _resetPassword(),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscure2
                                  ? Icons.visibility_off_outlined
                                  : Icons.visibility_outlined,
                              color: cs.onSurface.withValues(alpha: 0.4),
                              size: 20,
                            ),
                            onPressed: () =>
                                setState(() => _obscure2 = !_obscure2),
                          ),
                          validator: (v) {
                            if (v == null || v.isEmpty) return 'مطلوب';
                            if (v != _passwordCtrl.text) {
                              return 'كلمة المرور غير متطابقة';
                            }
                            return null;
                          },
                        ),

                        const SizedBox(height: SpacingTokens.lg),

                        AppButton(
                          label: 'تغيير كلمة المرور',
                          onPressed: _resetPassword,
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
      ),
    );
  }
}
