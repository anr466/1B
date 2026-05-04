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
    _loadSavedCredentials();
    // Auto-prompt biometric if credentials are saved (restored from previous session)
    _initializeBiometricLogin(allowAutoPrompt: true);

    // Check for session expiry from navigation
    WidgetsBinding.instance.addPostFrameCallback((_) {
      try {
        final uri = GoRouterState.of(context).uri;
        if (uri.queryParameters['expired'] == 'true') {
          if (mounted) {
            AppSnackbar.show(
              context,
              message: 'انتهت جلستك، سجّل دخولك مرة أخرى',
              type: SnackType.warning,
            );
          }
        }
      } catch (_) {
        // GoRouter not available (e.g., in tests)
      }
    });
  }

  Future<void> _loadSavedCredentials() async {
    final storage = ref.read(storageServiceProvider);
    // Load cached tokens for sync access
    await storage.loadCachedTokens();
    _rememberMe = storage.rememberMeEnabled;
    if (_rememberMe) {
      final (savedUser, savedPass) = await storage.getRememberedCredentials();
      if (savedUser != null) _emailCtrl.text = savedUser;
      if (savedPass != null) _passwordCtrl.text = savedPass;
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      // ✅ Auto-prompt biometric on app resume for better UX
      _initializeBiometricLogin(allowAutoPrompt: true);
    }
  }

  Future<void> _initializeBiometricLogin({bool allowAutoPrompt = true}) async {
    if (_isBiometricLoginInProgress) return;
    final storage = ref.read(storageServiceProvider);
    final bio = ref.read(biometricServiceProvider);

    // Get saved credentials (async)
    final (savedUser, savedPass) = await storage.getBiometricCredentials();

    // Check if biometric is enabled in settings AND credentials are saved
    final isBiometricEnabled = storage.biometricEnabled;
    final hasCredentials = savedUser != null && savedPass != null;
    final isConfigured = isBiometricEnabled && hasCredentials;

    // Check if device supports biometric
    final isAvailable = await bio.isAvailable;

    if (!mounted) return;
    setState(() {
      _biometricConfigured = isConfigured;
      _biometricAvailable = isConfigured && isAvailable;
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
      if (!mounted) return;
      final storage = ref.read(storageServiceProvider);
      await storage.setRememberMeEnabled(_rememberMe);
      if (_rememberMe) {
        await storage.saveRememberedCredentials(email, password);
      } else {
        await storage.clearRememberedCredentials();
      }

      // Save biometric credentials only when biometric is explicitly enabled in settings
      if (!mounted) return;
      if (storage.biometricEnabled) {
        await ref
            .read(authServiceProvider)
            .saveCredentialsForBiometric(email, password);
      }

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
    final (savedUser, savedPass) = await storage.getBiometricCredentials();
    final isBiometricEnabled = storage.biometricEnabled;

    // Check if biometric is enabled in settings
    if (!isBiometricEnabled) {
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message:
            'البصمة غير مُفعّلة. فعّلها من: الإعدادات > الأمان > تسجيل الدخول بالبصمة',
        type: SnackType.warning,
        duration: const Duration(seconds: 4),
      );
      return;
    }

    // Check if credentials are saved
    if (savedUser == null || savedPass == null) {
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message:
            'بيانات الدخول غير محفوظة. سجّل دخولك مرة واحدة لحفظ البيانات.',
        type: SnackType.warning,
        duration: const Duration(seconds: 4),
      );
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
      AppSnackbar.show(
        context,
        message: 'البصمة غير متاحة على هذا الجهاز',
        type: SnackType.error,
      );
      return;
    }

    setState(() => _isBiometricLoginInProgress = true);

    final authenticated = await bio.authenticate(
      reason: 'المصادقة مطلوبة للوصول للحساب',
    );

    if (!mounted) return;

    if (!authenticated) {
      setState(() => _isBiometricLoginInProgress = false);
      // Clear tokens and force logout on biometric fail per security spec
      await ref.read(authProvider.notifier).forceUnauthenticated();
      await ref.read(storageServiceProvider).clearBiometricCredentials();
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message: 'فشل التحقق من البصمة. تم تسجيل الخروج للأمان.',
        type: SnackType.error,
      );
      return;
    }

    await ref
        .read(authProvider.notifier)
        .login(emailOrUsername: savedUser, password: savedPass);
    if (!mounted) return;
    final auth = ref.read(authProvider);
    if (auth.isAuthenticated) {
      // Re-save credentials in case they changed
      final storage = ref.read(storageServiceProvider);
      if (storage.rememberMeEnabled) {
        await storage.saveRememberedCredentials(savedUser, savedPass);
      }
      if (storage.biometricEnabled) {
        await ref
            .read(authServiceProvider)
            .saveCredentialsForBiometric(savedUser, savedPass);
      }
      // Mark biometric as trusted after successful authentication
      ref.read(biometricTrustProvider.notifier).markTrusted();
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
                    textDirection: TextDirection.ltr,
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
                    label: 'كلمة مرور',
                    obscureText: _obscurePassword,
                    textInputAction: TextInputAction.done,
                    onSubmitted: (_) => _login(),
                    textDirection: TextDirection.ltr,
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

                  Padding(
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

                  // ─── Forgot Password ─────────────────
                  Align(
                    alignment: AlignmentDirectional.centerEnd,
                    child: AppButton(
                      label: 'نسيت كلمة المرور؟',
                      variant: AppButtonVariant.text,
                      isFullWidth: false,
                      onPressed: () => context.push(RouteNames.forgotPassword),
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
                          AppButton(
                            label: _isBiometricLoginInProgress
                                ? 'جاري التحقق بالبصمة...'
                                : 'الدخول بالبصمة',
                            variant: AppButtonVariant.text,
                            icon: Icons.fingerprint,
                            isFullWidth: true,
                            height: 46,
                            onPressed: isAnyAuthLoading
                                ? null
                                : () => _biometricLogin(),
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
                      AppButton(
                        label: 'تسجيل حساب جديد',
                        variant: AppButtonVariant.outline,
                        isFullWidth: false,
                        onPressed: () => context.push(RouteNames.register),
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
