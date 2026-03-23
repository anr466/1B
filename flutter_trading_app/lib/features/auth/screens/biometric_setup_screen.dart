import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/design/icons/brand_icons.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/registration_stepper.dart';
import 'package:trading_app/main.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Biometric Setup Screen — إعداد البصمة بعد التسجيل
class BiometricSetupScreen extends ConsumerWidget {
  const BiometricSetupScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            children: [
              const RegistrationStepper(currentStep: 4),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(SpacingTokens.lg),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Spacer(),

                      // ─── Icon ────────────────────────────
                      Container(
                        width: 100,
                        height: 100,
                        decoration: BoxDecoration(
                          color: cs.primary.withValues(alpha: 0.1),
                          shape: BoxShape.circle,
                        ),
                        child: Center(
                          child: BrandIcon(
                            BrandIcons.shield,
                            size: 48,
                            color: cs.primary,
                          ),
                        ),
                      ),

                      const SizedBox(height: SpacingTokens.xl),

                      Text(
                        'تفعيل البصمة',
                        style: TypographyTokens.h2(cs.onSurface),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: SpacingTokens.md),
                      Text(
                        'سجّل دخولك بسرعة باستخدام بصمة الإصبع أو التعرف على الوجه',
                        style: TypographyTokens.body(
                          cs.onSurface.withValues(alpha: 0.6),
                        ),
                        textAlign: TextAlign.center,
                      ),

                      const Spacer(),

                      // ─── Enable Button ───────────────────
                      AppButton(
                        label: 'تفعيل البصمة',
                        isFullWidth: true,
                        onPressed: () async {
                          final bio = ref.read(biometricServiceProvider);
                          final available = await bio.isAvailable;
                          if (!context.mounted) return;
                          if (!available) {
                            AppSnackbar.show(
                              context,
                              message: 'الجهاز لا يدعم البصمة',
                              type: SnackType.error,
                            );
                            return;
                          }
                          final authenticated = await bio.authenticate(
                            reason: 'تأكيد تفعيل البصمة',
                          );
                          if (!context.mounted) return;
                          if (!authenticated) {
                            AppSnackbar.show(
                              context,
                              message: 'فشل التحقق من البصمة',
                              type: SnackType.error,
                            );
                            return;
                          }
                          final storage = ref.read(storageServiceProvider);
                          await storage.setBiometricEnabled(true);
                          final auth = ref.read(authProvider);
                          final user = auth.user;
                          if (user != null) {
                            ref
                                .read(authProvider.notifier)
                                .updateCurrentUser(
                                  user.copyWith(biometricEnabled: true),
                                );
                          }
                          if (!context.mounted) return;
                          AppSnackbar.show(
                            context,
                            message: 'تم تفعيل البصمة بنجاح',
                            type: SnackType.success,
                          );
                          context.go(RouteNames.dashboard);
                        },
                      ),
                      const SizedBox(height: SpacingTokens.md),

                      // ─── Skip ────────────────────────────
                      AppButton(
                        label: 'تخطي',
                        variant: AppButtonVariant.text,
                        isFullWidth: true,
                        onPressed: () => context.go(RouteNames.dashboard),
                      ),

                      const SizedBox(height: SpacingTokens.xl),
                    ],
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
