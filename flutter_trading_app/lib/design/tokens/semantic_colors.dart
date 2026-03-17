import 'package:flutter/material.dart';

/// Semantic Colors — ThemeExtension للألوان الدلالية والمالية
/// يُرفق بالـ ThemeData عبر buildSkinTheme ويُستهلك من أي widget
@immutable
class SemanticColors extends ThemeExtension<SemanticColors> {
  // ─── Financial ────────────────────────────────────
  final Color positive;
  final Color negative;

  /// Universal accent gold — used for premium/highlight labels, star metrics
  static const Color accentGold = Color(0xFFD4A017);

  // ─── UI Feedback ──────────────────────────────────
  final Color success;
  final Color successContainer;
  final Color warning;
  final Color warningContainer;
  final Color info;
  final Color infoContainer;

  const SemanticColors({
    required this.positive,
    required this.negative,
    required this.success,
    required this.successContainer,
    required this.warning,
    required this.warningContainer,
    required this.info,
    required this.infoContainer,
  });

  /// Helper — الوصول السريع من أي widget
  static SemanticColors of(BuildContext context) =>
      Theme.of(context).extension<SemanticColors>()!;

  /// Gold container — 12% alpha gold for chip backgrounds
  static Color get accentGoldSubtle => accentGold.withValues(alpha: 0.12);

  @override
  SemanticColors copyWith({
    Color? positive,
    Color? negative,
    Color? success,
    Color? successContainer,
    Color? warning,
    Color? warningContainer,
    Color? info,
    Color? infoContainer,
  }) {
    return SemanticColors(
      positive: positive ?? this.positive,
      negative: negative ?? this.negative,
      success: success ?? this.success,
      successContainer: successContainer ?? this.successContainer,
      warning: warning ?? this.warning,
      warningContainer: warningContainer ?? this.warningContainer,
      info: info ?? this.info,
      infoContainer: infoContainer ?? this.infoContainer,
    );
  }

  @override
  SemanticColors lerp(covariant SemanticColors? other, double t) {
    if (other == null) return this;
    return SemanticColors(
      positive: Color.lerp(positive, other.positive, t)!,
      negative: Color.lerp(negative, other.negative, t)!,
      success: Color.lerp(success, other.success, t)!,
      successContainer: Color.lerp(
        successContainer,
        other.successContainer,
        t,
      )!,
      warning: Color.lerp(warning, other.warning, t)!,
      warningContainer: Color.lerp(
        warningContainer,
        other.warningContainer,
        t,
      )!,
      info: Color.lerp(info, other.info, t)!,
      infoContainer: Color.lerp(infoContainer, other.infoContainer, t)!,
    );
  }
}
