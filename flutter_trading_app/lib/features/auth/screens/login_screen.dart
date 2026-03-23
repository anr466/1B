import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/design/icons/brand_logo.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/app_input.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/main.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Login Screen — email_or_username + password + biometric
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen>
    with WidgetsBindingObserver {
  final _formKey = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  bool _obscurePassword = true;
  bool _rememberMe = false;
  bool _biometricAvailable = false;
  bool _biometricConfigured = false;
  bool _isBiometricLoading = true;
  bool _isBiometricLoginInProgress = false;
  bool _didAutoPromptBiometric = false;
  Timer? _biometricAutoPromptTimer;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    final storage = ref.read(storageServiceProvider);
    _rememberMe = storage.rememberMeEnabled;
    if (_rememberMe) {
      final (savedUser, savedPass) = storage.rememberedCredentials;
      if (savedUser != null) _emailCtrl.text = savedUser;
      if (savedPass != null) _passwordCtrl.text = savedPass;
    }
    // Disabled auto-prompt - user must explicitly tap biometric button
    _initializeBiometricLogin(allowAutoPrompt: false);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      _initializeBiometricLogin(allowAutoPrompt: false);
    }
  }

  Future<void> _initializeBiometricLogin({bool allowAutoPrompt = true}) async {
    final storage = ref.read(storageServiceProvider);
    final bio = ref.read(biometricServiceProvider);
    final (savedUser, savedPass) = storage.biometricCredentials;
    final isConfigured =
        storage.biometricEnabled && savedUser != null && savedPass != null;
    final isAvailable = isConfigured ? await bio.isAvailable : false;

    if (!mounted) return;
    setState(() {
      _biometricConfigured = isConfigured;
      _biometricAvailable = isAvailable;
      _isBiometricLoading = false;
    });

    if (allowAutoPrompt &&
        isConfigured &&
        isAvailable &&
        !_didAutoPromptBiometric) {
      _didAutoPromptBiometric = true;
      _biometricAutoPromptTimer?.cancel();
      _biometricAutoPromptTimer = Timer(const Duration(milliseconds: 350), () {
        if (!mounted) return;
        final lifecycleState = WidgetsBinding.instance.lifecycleState;
        final appIsActive =
            lifecycleState == null ||
            lifecycleState == AppLifecycleState.resumed;
        if (!appIsActive ||
            ref.read(authProvider).isLoading ||
            _isBiometricLoginInProgress) {
          _didAutoPromptBiometric = false;
          return;
        }
        _biometricLogin(autoTriggered: true);
      });
    }
  }

  @override
  void dispose() {
    _biometricAutoPromptTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    _emailCtrl.dispose();
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (_isBiometricLoginInProgress || ref.read(authProvider).isLoading) return;
    if (!_formKey.currentState!.validate()) return;

    final email = _emailCtrl.text.trim();
    final password = _passwordCtrl.text;

    await ref
        .read(authProvider.notifier)
        .login(emailOrUsername: email, password: password);

    if (!mounted) return;
    final auth = ref.read(authProvider);
    if (auth.isAuthenticated) {
      final storage = ref.read(storageServiceProvider);
      await storage.setRememberMeEnabled(_rememberMe);
      if (_rememberMe) {
        await storage.saveRememberedCredentials(email, password);
      } else {
        await storage.clearRememberedCredentials();
      }

      // Always save credentials for biometric (user may enable it later)
      await ref
          .read(authServiceProvider)
          .saveCredentialsForBiometric(email, password);

      if (!mounted) return;
      context.go(RouteNames.dashboard);
      return;
    }

    if (auth.error != null) {
      AppSnackbar.show(context, message: auth.error!, type: SnackType.error);
      ref.read(authProvider.notifier).clearError();
    }
  }

  Future<void> _biometricLogin({bool autoTriggered = false}) async {
    if (_isBiometricLoginInProgress || ref.read(authProvider).isLoading) return;
    final storage = ref.read(storageServiceProvider);
    final (savedUser, savedPass) = storage.biometricCredentials;
    if (savedUser == null || savedPass == null) {
      if (!mounted) return;
      if (!autoTriggered) {
        AppSnackbar.show(
          context,
          message: 'سجّل الدخول أولاً لتفعيل البصمة',
          type: SnackType.info,
        );
      }
      return;
    }

    final bio = ref.read(biometricServiceProvider);
    final isAvailable = await bio.isAvailable;
    if (!isAvailable) {
      if (!mounted) return;
      setState(() {
        _biometricAvailable = false;
        _isBiometricLoginInProgress = false;
      });
      return;
    }

    setState(() => _isBiometricLoginInProgress = true);
    final authenticated = await bio.authenticate(
      reason: 'سجّل دخولك باستخدام البصمة',
    );
    if (!mounted) return;
    if (!authenticated) {
      setState(() => _isBiometricLoginInProgress = false);
      return;
    }

    await ref
        .read(authProvider.notifier)
        .login(emailOrUsername: savedUser, password: savedPass);
    if (!mounted) return;
    final auth = ref.read(authProvider);
    if (auth.isAuthenticated) {
      setState(() => _isBiometricLoginInProgress = false);
      context.go(RouteNames.dashboard);
    } else if (auth.error != null) {
      await storage.clearBiometricCredentials();
      setState(() {
        _isBiometricLoginInProgress = false;
        _biometricConfigured = false;
      });
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message: 'تعذر إتمام العملية، حاول مرة أخرى',
        type: SnackType.error,
      );
      ref.read(authProvider.notifier).clearError();
    } else {
      setState(() => _isBiometricLoginInProgress = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final auth = ref.watch(authProvider);
    final showBiometricAction =
        !_isBiometricLoading && _biometricConfigured && _biometricAvailable;
    final isAnyAuthLoading = auth.isLoading || _isBiometricLoginInProgress;

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        key: const Key('login_screen'),
        backgroundColor: cs.surface,
        body: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: SpacingTokens.lg),
            child: Form(
              key: _formKey,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: SpacingTokens.xxl),

                  // ─── Logo ────────────────────────────
                  const Center(child: BrandLogo(size: 80)),
                  const SizedBox(height: SpacingTokens.base),
                  Center(
                    child: Text(
                      'تسجيل الدخول',
                      style: TypographyTokens.h2(cs.onSurface),
                    ),
                  ),
                  const SizedBox(height: SpacingTokens.lg),

                  // ─── Email / Username ────────────────
                  AppInput(
                    controller: _emailCtrl,
                    label: 'البريد أو المستخدم',
                    hint: 'example@email.com',
                    keyboardType: TextInputType.emailAddress,
                    textInputAction: TextInputAction.next,
                    validator: (v) {
                      if (v == null || v.trim().isEmpty) {
                        return 'مطلوب';
                      }
                      return null;
                    },
                  ),

                  const SizedBox(height: SpacingTokens.base),

                  // ─── Password ────────────────────────
                  AppInput(
                    controller: _passwordCtrl,
                    label: 'كلمة المرور',
                    obscureText: _obscurePassword,
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => _login(),
                    suffixIcon: IconButton(
                      icon: Icon(
                        _obscurePassword
                            ? Icons.visibility_off_outlined
                            : Icons.visibility_outlined,
                        color: cs.onSurface.withValues(alpha: 0.4),
                        size: 20,
                      ),
                      onPressed: () =>
                          setState(() => _obscurePassword = !_obscurePassword),
                    ),
                    validator: (v) {
                      if (v == null || v.isEmpty) {
                        return 'مطلوب';
                      }
                      return null;
                    },
                  ),

                  const SizedBox(height: SpacingTokens.sm),

                  Material(
                    color: Colors.transparent,
                    child: InkWell(
                      onTap: () => setState(() => _rememberMe = !_rememberMe),
                      borderRadius: BorderRadius.circular(
                        SpacingTokens.radiusMd,
                      ),
                      child: Padding(
                        padding: const EdgeInsets.symmetric(
                          vertical: SpacingTokens.xs,
                        ),
                        child: Row(
                          children: [
                            Checkbox(
                              value: _rememberMe,
                              onChanged: (value) {
                                setState(() => _rememberMe = value ?? false);
                              },
                            ),
                            const SizedBox(width: SpacingTokens.xs),
                            Expanded(
                              child: Text(
                                'تذكرني / حفظ بيانات الدخول',
                                style: TypographyTokens.bodySmall(
                                  cs.onSurface.withValues(alpha: 0.82),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),

                  // ─── Forgot Password ─────────────────
                  Align(
                    alignment: AlignmentDirectional.centerStart,
                    child: TextButton(
                      onPressed: () => context.push(RouteNames.forgotPassword),
                      child: Text(
                        'نسيت كلمة المرور؟',
                        style: TypographyTokens.bodySmall(cs.primary),
                      ),
                    ),
                  ),

                  const SizedBox(height: SpacingTokens.lg),

                  // ─── Login Button ────────────────────
                  AppButton(
                    key: const Key('login_submit_button'),
                    label: 'تسجيل الدخول',
                    onPressed: isAnyAuthLoading ? null : _login,
                    isLoading: auth.isLoading,
                  ),

                  if (showBiometricAction)
                    const SizedBox(height: SpacingTokens.sm),

                  // ─── Biometric Login ─────────────────
                  Builder(
                    builder: (_) {
                      if (!showBiometricAction) {
                        return const SizedBox.shrink();
                      }

                      return Column(
                        children: [
                          SizedBox(
                            width: double.infinity,
                            height: 46,
                            child: TextButton.icon(
                              onPressed: isAnyAuthLoading
                                  ? null
                                  : () => _biometricLogin(),
                              icon: Icon(
                                Icons.fingerprint,
                                color: cs.primary,
                                size: 24,
                              ),
                              label: Text(
                                _isBiometricLoginInProgress
                                    ? 'جاري التحقق بالبصمة...'
                                    : 'الدخول بالبصمة',
                                style: TypographyTokens.body(cs.primary),
                              ),
                              style: TextButton.styleFrom(
                                backgroundColor: cs.primary.withValues(
                                  alpha: 0.06,
                                ),
                                foregroundColor: cs.primary,
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(
                                    SpacingTokens.radiusMd,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ],
                      );
                    },
                  ),

                  const SizedBox(height: SpacingTokens.base),

                  // ─── Register Link ───────────────────
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        'ليس لديك حساب؟',
                        style: TypographyTokens.bodySmall(
                          cs.onSurface.withValues(alpha: 0.65),
                        ),
                      ),
                      TextButton(
                        onPressed: () => context.push(RouteNames.register),
                        style: TextButton.styleFrom(
                          padding: const EdgeInsets.symmetric(
                            horizontal: SpacingTokens.sm,
                            vertical: SpacingTokens.xs,
                          ),
                          minimumSize: const Size(48, 40),
                          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                        ),
                        child: Text(
                          'إنشاء حساب',
                          style: TypographyTokens.bodySmall(
                            cs.primary,
                          ).copyWith(fontWeight: FontWeight.w700),
                        ),
                      ),
                    ],
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
}
