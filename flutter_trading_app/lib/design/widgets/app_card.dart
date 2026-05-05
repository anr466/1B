import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';

/// App Card — Premium Dark Integrated Design
///
/// التصميم الجديد: البطاقات تندمج مع الخلفية بدون حواف مرئية.
/// المسافات والظلال الخفيفة هي الفواصل الوحيدة.
///
/// [level] controls visual depth:
///   0 = integrated  — same bg + subtle highlight (default)
///   1 = subtle      — slight background lift
///   2 = elevated    — shadow + blur for floating cards
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
    final cs = Theme.of(context).colorScheme;
    final radius = borderRadius ?? SpacingTokens.radiusLg;

    final bgColor = switch (level) {
      0 => backgroundColor ?? cs.surfaceContainerLow,
      1 => backgroundColor ?? cs.surfaceContainer,
      2 => backgroundColor ?? cs.surfaceContainerHigh,
      _ => backgroundColor ?? cs.surfaceContainerLow,
    };

    // Only level 2 has visible border (subtle)
    final border = level >= 2
        ? Border.all(
            color: borderColor ?? cs.outline.withValues(alpha: 0.06),
            width: 0.5,
          )
        : null;

    // Only level 2 has shadow
    final shadows = level >= 2
        ? [
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.20),
              blurRadius: 24,
              spreadRadius: -4,
              offset: const Offset(0, 12),
            ),
          ]
        : <BoxShadow>[];

    Widget content = Container(
      padding: padding ?? const EdgeInsets.all(SpacingTokens.base),
      margin: margin,
      decoration: BoxDecoration(
        color: gradientColors != null ? null : bgColor,
        gradient: gradientColors != null
            ? LinearGradient(
                colors: gradientColors!,
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              )
            : null,
        borderRadius: BorderRadius.circular(radius),
        border: border,
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
