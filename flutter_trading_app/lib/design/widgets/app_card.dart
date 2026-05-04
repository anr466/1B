import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';

/// App Card — Minimalist Borderless Design
///
/// تصميم صافي بدون حدود — يعتمد على المسافات والتايبوغرافي
///
/// [level] controls visual depth:
///   0 = borderless — no border, no shadow, subtle bg (default)
///   1 = subtle     — very subtle border, minimal shadow
///   2 = raised     — standard card with border + shadow
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
    this.level = 0,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final cs = theme.colorScheme;
    final isDark = cs.brightness == Brightness.dark;
    final radius = borderRadius ?? SpacingTokens.radiusMd;

    final borderAlpha = switch (level) {
      0 => 0.0,
      2 => isDark ? 0.22 : 0.18,
      _ => isDark ? 0.08 : 0.12,
    };
    final bgColor = switch (level) {
      0 =>
        backgroundColor ??
            (isDark ? cs.surfaceContainer : cs.surfaceContainerHigh),
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
              ]
            : <BoxShadow>[
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.12),
                  blurRadius: 20,
                  spreadRadius: -2,
                  offset: const Offset(0, 8),
                ),
              ],
      _ => <BoxShadow>[],
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
        border: borderAlpha > 0
            ? Border.all(
                color: borderColor ?? cs.outline.withValues(alpha: borderAlpha),
                width: level == 2 ? 1.2 : 0.5,
              )
            : null,
        boxShadow: shadows,
      ),
      child: child,
    );

    if (onTap != null) {
      return Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(radius),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(radius),
          child: content,
        ),
      );
    }

    return content;
  }
}
