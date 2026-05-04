import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// App Snackbar — رسائل Toast-style موحدة
/// تصميم صافي — لا يعتمد على أي منطق أعمال
enum SnackType { success, error, warning, info }

class AppSnackbar {
  AppSnackbar._();

  static void show(
    BuildContext context, {
    required String message,
    SnackType type = SnackType.info,
    Duration duration = const Duration(seconds: 3),
  }) {
    final colors = _snackColors(context, type);

    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Row(
            children: [
              Icon(colors.icon, color: colors.fg, size: 20),
              const SizedBox(width: SpacingTokens.sm),
              Expanded(
                child: Text(
                  message,
                  style: TypographyTokens.bodySmall(colors.fg),
                ),
              ),
            ],
          ),
          backgroundColor: colors.bg,
          behavior: SnackBarBehavior.floating,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
            side: BorderSide(color: colors.fg.withValues(alpha: 0.3)),
          ),
          duration: duration,
          margin: const EdgeInsets.all(SpacingTokens.base),
        ),
      );
  }

  static _SnackColors _snackColors(BuildContext context, SnackType type) {
    final sem = SemanticColors.of(context);
    final cs = Theme.of(context).colorScheme;
    switch (type) {
      case SnackType.success:
        return _SnackColors(
          sem.success,
          sem.successContainer,
          Icons.check_circle_outline_rounded,
        );
      case SnackType.error:
        return _SnackColors(
          cs.error,
          cs.errorContainer,
          Icons.error_outline_rounded,
        );
      case SnackType.warning:
        return _SnackColors(
          sem.warning,
          sem.warningContainer,
          Icons.warning_amber_rounded,
        );
      case SnackType.info:
        return _SnackColors(
          sem.info,
          sem.infoContainer,
          Icons.info_outline_rounded,
        );
    }
  }
}

class _SnackColors {
  final Color fg;
  final Color bg;
  final IconData icon;
  const _SnackColors(this.fg, this.bg, this.icon);
}
