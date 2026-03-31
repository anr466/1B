import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/constants/ux_messages.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/design/icons/brand_icons.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_input.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/registration_stepper.dart';

/// Binance Keys Screen — حفظ مفاتيح API
class BinanceKeysScreen extends ConsumerStatefulWidget {
  const BinanceKeysScreen({super.key});

  @override
  ConsumerState<BinanceKeysScreen> createState() => _BinanceKeysScreenState();
}

class _BinanceKeysScreenState extends ConsumerState<BinanceKeysScreen> {
  final _formKey = GlobalKey<FormState>();
  final _apiKeyCtrl = TextEditingController();
  final _apiSecretCtrl = TextEditingController();
  bool _obscureKey = true;
  bool _obscureSecret = true;
  bool _isSaving = false;
  bool _isValidating = false;
  bool _isValidated = false;
  String? _validatedFingerprint;

  String _currentFingerprint() {
    return '${_apiKeyCtrl.text.trim()}::${_apiSecretCtrl.text.trim()}';
  }

  void _resetValidationIfChanged() {
    if (_validatedFingerprint == null) return;
    if (_validatedFingerprint != _currentFingerprint()) {
      setState(() {
        _isValidated = false;
        _validatedFingerprint = null;
      });
    }
  }

  @override
  void initState() {
    super.initState();
    _apiKeyCtrl.addListener(_resetValidationIfChanged);
    _apiSecretCtrl.addListener(_resetValidationIfChanged);
  }

  Future<void> _validateKeys() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isValidating = true);
    try {
      final repo = ref.read(settingsRepositoryProvider);
      final result = await repo.validateBinanceKeys(
        apiKey: _apiKeyCtrl.text.trim(),
        apiSecret: _apiSecretCtrl.text.trim(),
      );

      if (!mounted) return;
      final isValid = result['valid'] == true || result['success'] == true;
      setState(() {
        _isValidated = isValid;
        _validatedFingerprint = isValid ? _currentFingerprint() : null;
      });
      final message =
          (result['message'] ?? result['error'] ?? result['details'] ?? '')
              .toString()
              .trim();
      AppSnackbar.show(
        context,
        message: message.isNotEmpty
            ? message
            : (isValid ? 'المفاتيح صالحة وجاهزة' : 'المفاتيح غير صالحة'),
        type: isValid ? SnackType.success : SnackType.error,
      );
    } catch (_) {
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message: UxMessages.apiKeysValidateError,
        type: SnackType.error,
      );
    } finally {
      if (mounted) setState(() => _isValidating = false);
    }
  }

  @override
  void dispose() {
    _apiKeyCtrl.removeListener(_resetValidationIfChanged);
    _apiSecretCtrl.removeListener(_resetValidationIfChanged);
    _apiKeyCtrl.dispose();
    _apiSecretCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;

    if (!_isValidated || _validatedFingerprint != _currentFingerprint()) {
      AppSnackbar.show(
        context,
        message: 'يرجى التحقق من المفاتيح أولاً قبل الحفظ',
        type: SnackType.info,
      );
      return;
    }

    final auth = ref.read(authProvider);
    if (auth.user == null) return;

    setState(() => _isSaving = true);
    try {
      final repo = ref.read(settingsRepositoryProvider);
      final result = await repo.saveBinanceKeys(
        auth.user!.id,
        apiKey: _apiKeyCtrl.text.trim(),
        apiSecret: _apiSecretCtrl.text.trim(),
      );

      if (!mounted) return;
      if (result['success'] == true) {
        AppSnackbar.show(
          context,
          message: UxMessages.success,
          type: SnackType.success,
        );
        _apiKeyCtrl.clear();
        _apiSecretCtrl.clear();
        setState(() {
          _isValidated = false;
          _validatedFingerprint = null;
        });
      } else {
        AppSnackbar.show(
          context,
          message: result['error'] ?? UxMessages.apiKeysSaveError,
          type: SnackType.error,
        );
      }
    } catch (e) {
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message: UxMessages.networkError,
        type: SnackType.error,
      );
    } finally {
      if (mounted) setState(() => _isSaving = false);
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
              AppScreenHeader(title: 'مفاتيح Binance', showBack: true),
              const RegistrationStepper(currentStep: 2),
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.all(SpacingTokens.base),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // ─── Warning Card ──────────────────────
                        AppCard(
                          backgroundColor: cs.tertiary.withValues(alpha: 0.08),
                          padding: const EdgeInsets.all(SpacingTokens.md),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              BrandIcon(
                                BrandIcons.warning,
                                size: 20,
                                color: cs.tertiary,
                              ),
                              const SizedBox(width: SpacingTokens.sm),
                              Expanded(
                                child: Text(
                                  'تأكد من أن المفاتيح لا تمتلك صلاحية السحب (Withdrawal). '
                                  'فعّل فقط صلاحيات القراءة والتداول.',
                                  style: TypographyTokens.bodySmall(
                                    cs.onSurface.withValues(alpha: 0.7),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),

                        const SizedBox(height: SpacingTokens.lg),

                        // ─── API Key ───────────────────────────
                        AppInput(
                          controller: _apiKeyCtrl,
                          label: 'مفتاح API',
                          hint: 'أدخل مفتاح API',
                          obscureText: _obscureKey,
                          textInputAction: TextInputAction.next,
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscureKey
                                  ? Icons.visibility_off_outlined
                                  : Icons.visibility_outlined,
                              color: cs.onSurface.withValues(alpha: 0.4),
                              size: 20,
                            ),
                            onPressed: () =>
                                setState(() => _obscureKey = !_obscureKey),
                          ),
                          validator: (v) {
                            if (v == null || v.trim().isEmpty) return 'مطلوب';
                            if (v.trim().length < 20) return 'مفتاح قصير جداً';
                            return null;
                          },
                        ),

                        const SizedBox(height: SpacingTokens.md),

                        // ─── API Secret ────────────────────────
                        AppInput(
                          controller: _apiSecretCtrl,
                          label: 'المفتاح السري',
                          hint: 'أدخل المفتاح السري',
                          obscureText: _obscureSecret,
                          textInputAction: TextInputAction.done,
                          onSubmitted: (_) => _save(),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscureSecret
                                  ? Icons.visibility_off_outlined
                                  : Icons.visibility_outlined,
                              color: cs.onSurface.withValues(alpha: 0.4),
                              size: 20,
                            ),
                            onPressed: () => setState(
                              () => _obscureSecret = !_obscureSecret,
                            ),
                          ),
                          validator: (v) {
                            if (v == null || v.trim().isEmpty) return 'مطلوب';
                            if (v.trim().length < 20) return 'مفتاح قصير جداً';
                            return null;
                          },
                        ),

                        const SizedBox(height: SpacingTokens.xl),

                        // ─── Save Button ───────────────────────
                        Row(
                          children: [
                            Expanded(
                              child: AppButton(
                                label: 'تحقق من المفاتيح',
                                variant: AppButtonVariant.outline,
                                onPressed: _isSaving ? null : _validateKeys,
                                isLoading: _isValidating,
                              ),
                            ),
                            const SizedBox(width: SpacingTokens.sm),
                            Expanded(
                              child: AppButton(
                                label: 'حفظ المفاتيح',
                                onPressed: (_isValidating || !_isValidated)
                                    ? null
                                    : _save,
                                isLoading: _isSaving,
                              ),
                            ),
                          ],
                        ),

                        const SizedBox(height: SpacingTokens.lg),

                        // ─── Info ──────────────────────────────
                        AppCard(
                          padding: const EdgeInsets.all(SpacingTokens.md),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'معلومات مهمة',
                                style: TypographyTokens.label(cs.onSurface),
                              ),
                              const SizedBox(height: SpacingTokens.sm),
                              _infoLine(
                                cs,
                                'المفاتيح مشفرة بتقنية AES قبل الحفظ',
                              ),
                              _infoLine(
                                cs,
                                'لا يمكن استرجاع المفاتيح بعد الحفظ',
                              ),
                              _infoLine(cs, 'يمكنك تحديث المفاتيح في أي وقت'),
                            ],
                          ),
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

  Widget _infoLine(ColorScheme cs, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: SpacingTokens.xs),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('• ', style: TypographyTokens.bodySmall(cs.primary)),
          Expanded(
            child: Text(
              text,
              style: TypographyTokens.bodySmall(
                cs.onSurface.withValues(alpha: 0.5),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
