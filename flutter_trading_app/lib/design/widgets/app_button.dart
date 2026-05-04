import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// App Button — primary, secondary, text variants
/// تصميم صافي — لا يعتمد على أي منطق أعمال
enum AppButtonVariant { primary, secondary, outline, text, danger }

class AppButton extends StatelessWidget {
  final String label;
  final VoidCallback? onPressed;
  final AppButtonVariant variant;
  final bool isLoading;
  final bool isFullWidth;
  final IconData? icon;
  final double? height;

  const AppButton({
    super.key,
    required this.label,
    this.onPressed,
    this.variant = AppButtonVariant.primary,
    this.isLoading = false,
    this.isFullWidth = true,
    this.icon,
    this.height,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final h = height ?? SpacingTokens.buttonHeight;
    final foregroundColor = switch (variant) {
      AppButtonVariant.primary => cs.onPrimary,
      AppButtonVariant.secondary => cs.primary,
      AppButtonVariant.outline => cs.primary,
      AppButtonVariant.text => cs.primary,
      AppButtonVariant.danger => cs.onError,
    };
    final labelStyle = TypographyTokens.button(foregroundColor);

    Widget child = isLoading
        ? SizedBox(
            width: 22,
            height: 22,
            child: CircularProgressIndicator(
              strokeWidth: 2.5,
              color: foregroundColor,
            ),
          )
        : Row(
            mainAxisSize: isFullWidth ? MainAxisSize.max : MainAxisSize.min,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              if (icon != null) ...[
                Icon(icon, size: 20, color: foregroundColor),
                const SizedBox(width: SpacingTokens.sm),
              ],
              Text(label, style: labelStyle),
            ],
          );

    final minSize = isFullWidth ? Size(double.infinity, h) : Size(0, h);

    switch (variant) {
      case AppButtonVariant.primary:
        return ElevatedButton(
          onPressed: isLoading ? null : onPressed,
          style: ElevatedButton.styleFrom(
            minimumSize: minSize,
            backgroundColor: cs.primary,
            foregroundColor: cs.onPrimary,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(SpacingTokens.radiusLg),
            ),
            elevation: 0,
          ),
          child: child,
        );

      case AppButtonVariant.secondary:
        return ElevatedButton(
          onPressed: isLoading ? null : onPressed,
          style: ElevatedButton.styleFrom(
            minimumSize: minSize,
            backgroundColor: cs.primary.withValues(alpha: 0.12),
            foregroundColor: cs.primary,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(SpacingTokens.radiusLg),
            ),
            elevation: 0,
          ),
          child: child,
        );

      case AppButtonVariant.outline:
        return OutlinedButton(
          onPressed: isLoading ? null : onPressed,
          style: OutlinedButton.styleFrom(
            minimumSize: minSize,
            foregroundColor: cs.primary,
            side: BorderSide(color: cs.primary),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(SpacingTokens.radiusLg),
            ),
          ),
          child: child,
        );

      case AppButtonVariant.text:
        return TextButton(
          onPressed: isLoading ? null : onPressed,
          style: TextButton.styleFrom(
            minimumSize: minSize,
            foregroundColor: cs.primary,
          ),
          child: child,
        );

      case AppButtonVariant.danger:
        return ElevatedButton(
          onPressed: isLoading ? null : onPressed,
          style: ElevatedButton.styleFrom(
            minimumSize: minSize,
            backgroundColor: cs.error,
            foregroundColor: cs.onError,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(SpacingTokens.radiusLg),
            ),
            elevation: 0,
          ),
          child: child,
        );
    }
  }
}
