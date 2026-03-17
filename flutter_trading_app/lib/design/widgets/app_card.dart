import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';

/// App Card — بطاقة موحدة بزوايا دائرية وحدود خفيفة
/// تصميم صافي — لا يعتمد على أي منطق أعمال
///
/// [level] controls visual depth:
///   0 = flat    — minimal border, no shadow, subtle bg
///   1 = default — standard card (default)
///   2 = raised  — stronger border + shadow, more prominent
class AppCard extends StatelessWidget {
  final Widget child;
  final EdgeInsetsGeometry? padding;
  final EdgeInsetsGeometry? margin;
  final VoidCallback? onTap;
  final List<Color>? gradientColors;
  final Color? backgroundColor;
  final Color? borderColor;
  final double? borderRadius;
  final int level;

  const AppCard({
    super.key,
    required this.child,
    this.padding,
    this.margin,
    this.onTap,
    this.gradientColors,
    this.backgroundColor,
    this.borderColor,
    this.borderRadius,
    this.level = 1,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final isDark = cs.brightness == Brightness.dark;
    final radius = borderRadius ?? SpacingTokens.radiusXl;

    // Level-driven visual tokens
    final borderAlpha = switch (level) {
      0 => isDark ? 0.08 : 0.12,
      2 => isDark ? 0.45 : 0.25,
      _ => isDark ? 0.22 : 0.18,
    };
    final bgColor = switch (level) {
      0 =>
        backgroundColor ??
            (isDark ? cs.surfaceContainerLow : cs.surfaceContainerLow),
      2 =>
        backgroundColor ??
            (isDark ? cs.surfaceContainerHighest : cs.surfaceContainerHighest),
      _ =>
        backgroundColor ??
            (isDark ? cs.surfaceContainerHigh : cs.surfaceContainerHigh),
    };
    final shadows = switch (level) {
      0 => <BoxShadow>[],
      2 =>
        isDark
            ? <BoxShadow>[
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.45),
                  blurRadius: 24,
                  spreadRadius: -4,
                  offset: const Offset(0, 12),
                ),
                BoxShadow(
                  color: cs.primary.withValues(alpha: 0.08),
                  blurRadius: 12,
                  spreadRadius: 2,
                  offset: const Offset(0, 0),
                ),
              ]
            : <BoxShadow>[
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.12),
                  blurRadius: 20,
                  spreadRadius: -2,
                  offset: const Offset(0, 8),
                ),
              ],
      _ =>
        isDark
            ? <BoxShadow>[
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.2),
                  blurRadius: 8,
                  offset: const Offset(0, 4),
                ),
              ]
            : <BoxShadow>[
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.04),
                  blurRadius: 8,
                  offset: const Offset(0, 2),
                ),
              ],
    };

    Widget content = Container(
      padding: padding ?? const EdgeInsets.all(SpacingTokens.base),
      margin: margin,
      decoration: BoxDecoration(
        color: gradientColors == null ? bgColor : null,
        gradient: gradientColors != null
            ? LinearGradient(
                colors: gradientColors!,
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              )
            : null,
        borderRadius: BorderRadius.circular(radius),
        border: Border.all(
          color: borderColor ?? cs.outline.withValues(alpha: borderAlpha),
          width: level == 2 ? 1.2 : 1,
        ),
        boxShadow: shadows,
      ),
      child: child,
    );

    if (onTap != null) {
      return GestureDetector(onTap: onTap, child: content);
    }

    return content;
  }
}
