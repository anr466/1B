import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/design/skins/skin_manager.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/app_section_label.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/main.dart';

/// Skin Picker Screen — اختيار التصميم
class SkinPickerScreen extends ConsumerWidget {
  const SkinPickerScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final currentSkin = ref.watch(skinNameProvider);
    final allSkins = SkinManager.allSkins;

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              AppScreenHeader(title: 'التصميم', showBack: true),
              Expanded(
                child: ListView(
                  padding: const EdgeInsets.all(SpacingTokens.base),
          children: [
            Text(
              'اختر التصميم المفضل',
              style: TypographyTokens.body(cs.onSurface.withValues(alpha: 0.6)),
            ),
            const SizedBox(height: SpacingTokens.base),

            // ─── Theme Mode ──────────────────────────
            AppCard(
              padding: const EdgeInsets.all(SpacingTokens.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'وضع الثيم',
                    style: TypographyTokens.label(cs.onSurface),
                  ),
                  const SizedBox(height: SpacingTokens.md),
                  Row(
                    children: [
                      _themeModeChip(context, ref, cs, ThemeMode.dark, 'داكن'),
                      const SizedBox(width: SpacingTokens.sm),
                      _themeModeChip(context, ref, cs, ThemeMode.light, 'فاتح'),
                      const SizedBox(width: SpacingTokens.sm),
                      _themeModeChip(
                        context,
                        ref,
                        cs,
                        ThemeMode.system,
                        'تلقائي',
                      ),
                    ],
                  ),
                ],
              ),
            ),

            const SizedBox(height: SpacingTokens.lg),

            // ─── Skins ──────────────────────────────
            const AppSectionLabel(text: 'التصاميم'),
            const SizedBox(height: SpacingTokens.sm),

            ...allSkins.map((skin) {
              final isSelected = skin.name == currentSkin;
              final darkColors = skin.darkColors;

              return Padding(
                padding: const EdgeInsets.only(bottom: SpacingTokens.sm),
                child: AppCard(
                  onTap: () async {
                    ref.read(skinNameProvider.notifier).state = skin.name;
                    final storage = ref.read(storageServiceProvider);
                    await storage.saveSkin(skin.name);
                    if (context.mounted) {
                      AppSnackbar.show(
                        context,
                        message: 'تم تغيير التصميم إلى ${skin.displayNameAr}',
                        type: SnackType.success,
                      );
                    }
                  },
                  backgroundColor: isSelected
                      ? cs.primary.withValues(alpha: 0.08)
                      : null,
                  padding: const EdgeInsets.all(SpacingTokens.md),
                  child: Row(
                    children: [
                      // Color preview
                      Container(
                        width: 40,
                        height: 40,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(
                            SpacingTokens.radiusSm,
                          ),
                          gradient: LinearGradient(
                            colors: [darkColors.primary, darkColors.accent],
                          ),
                        ),
                      ),
                      const SizedBox(width: SpacingTokens.md),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              skin.displayNameAr,
                              style: TypographyTokens.body(cs.onSurface),
                            ),
                            Text(
                              skin.displayNameEn,
                              style: TypographyTokens.caption(
                                cs.onSurface.withValues(alpha: 0.4),
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (isSelected)
                        Icon(Icons.check_circle, color: cs.primary, size: 24),
                    ],
                  ),
                ),
              );
            }),
                ],
              ),
            ),
          ],
        ),
        ),
      ),
    );
  }

  Widget _themeModeChip(
    BuildContext context,
    WidgetRef ref,
    ColorScheme cs,
    ThemeMode mode,
    String label,
  ) {
    final current = ref.watch(themeModeProvider);
    final isSelected = current == mode;

    return Expanded(
      child: GestureDetector(
        onTap: () async {
          ref.read(themeModeProvider.notifier).state = mode;
          final storage = ref.read(storageServiceProvider);
          await storage.saveThemeMode(mode.name);
        },
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: SpacingTokens.sm),
          decoration: BoxDecoration(
            color: isSelected ? cs.primary : cs.surfaceContainerHighest,
            borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
            border: Border.all(
              color: isSelected ? cs.primary : cs.outline,
              width: 1,
            ),
          ),
          child: Center(
            child: Text(
              label,
              style: TypographyTokens.bodySmall(
                isSelected ? cs.onPrimary : cs.onSurface.withValues(alpha: 0.6),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
