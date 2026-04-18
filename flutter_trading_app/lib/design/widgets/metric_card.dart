import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';

/// Metric Card — بطاقة عرض مقياس مالي
/// تصميم ناعم بدون حواف حادة
///
/// الاستخدام:
/// ```dart
/// MetricCard(
///   label: 'إجمالي الربح',
///   value: '\$1,234',
///   change: '+5.2%',
///   isPositive: true,
///   accentColor: Colors.green,
/// )
/// ```
class MetricCard extends StatelessWidget {
  final String label;
  final String value;
  final String? change;
  final bool? isPositive;
  final Color? accentColor;
  final IconData? icon;
  final VoidCallback? onTap;
  final double? height;

  const MetricCard({
    super.key,
    required this.label,
    required this.value,
    this.change,
    this.isPositive,
    this.accentColor,
    this.icon,
    this.onTap,
    this.height,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final semantic = SemanticColors.of(context);
    final isDark = cs.brightness == Brightness.dark;

    final effectiveAccent =
        accentColor ??
        (isPositive == true
            ? semantic.positive
            : isPositive == false
            ? semantic.negative
            : cs.primary);

    final card = Container(
      height: height,
      padding: const EdgeInsets.all(SpacingTokens.md),
      decoration: BoxDecoration(
        color: isDark ? cs.surfaceContainerHigh : cs.surfaceContainerLow,
        borderRadius: BorderRadius.circular(SpacingTokens.radiusLg),
        border: Border.all(
          color: effectiveAccent.withValues(alpha: 0.15),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          // Header: icon + label
          Row(
            children: [
              if (icon != null) ...[
                Icon(icon, size: 16, color: effectiveAccent),
                const SizedBox(width: SpacingTokens.xs),
              ],
              Expanded(
                child: Text(
                  label.toUpperCase(),
                  style: TypographyTokens.overline(
                    cs.onSurface.withValues(alpha: 0.5),
                  ).copyWith(letterSpacing: 1.5, fontSize: 10),
                ),
              ),
              if (change != null)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: effectiveAccent.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    change!,
                    style: TypographyTokens.caption(
                      effectiveAccent,
                    ).copyWith(fontWeight: FontWeight.w600),
                  ),
                ),
            ],
          ),
          const SizedBox(height: SpacingTokens.sm),
          // Value
          Text(
            value,
            style: TypographyTokens.hero(
              cs.onSurface,
            ).copyWith(fontWeight: FontWeight.w800, letterSpacing: -0.5),
          ),
        ],
      ),
    );

    if (onTap != null) {
      return GestureDetector(onTap: onTap, child: card);
    }

    return card;
  }
}

/// Hero Metric Card — بطاقة كبيرة للرقم الرئيسي
/// مثل رصيد المحفظة
class HeroMetricCard extends StatelessWidget {
  final String label;
  final String value;
  final String? subtitle;
  final String? badge;
  final Color? accentColor;
  final Widget? trailing;

  const HeroMetricCard({
    super.key,
    required this.label,
    required this.value,
    this.subtitle,
    this.badge,
    this.accentColor,
    this.trailing,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = cs.brightness == Brightness.dark;

    return Container(
      padding: const EdgeInsets.all(SpacingTokens.lg),
      decoration: BoxDecoration(
        color: isDark ? cs.surfaceContainerHigh : cs.surfaceContainerLow,
        borderRadius: BorderRadius.circular(SpacingTokens.radiusXl),
        border: Border.all(
          color: cs.outline.withValues(alpha: isDark ? 0.10 : 0.08),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          Row(
            children: [
              Expanded(
                child: Text(
                  label.toUpperCase(),
                  style: TypographyTokens.overline(
                    cs.onSurface.withValues(alpha: 0.5),
                  ).copyWith(letterSpacing: 1.5, fontSize: 10),
                ),
              ),
              if (badge != null)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 5,
                  ),
                  decoration: BoxDecoration(
                    color: (accentColor ?? cs.primary).withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    badge!,
                    style: TypographyTokens.caption(
                      accentColor ?? cs.primary,
                    ).copyWith(fontWeight: FontWeight.w600),
                  ),
                ),
              if (trailing != null) ...[
                const SizedBox(width: SpacingTokens.sm),
                trailing!,
              ],
            ],
          ),
          const SizedBox(height: SpacingTokens.sm),
          // Value
          Text(
            value,
            style: TypographyTokens.hero(
              cs.onSurface,
            ).copyWith(fontWeight: FontWeight.w900, letterSpacing: -1),
          ),
          if (subtitle != null) ...[
            const SizedBox(height: SpacingTokens.xs),
            Text(
              subtitle!,
              style: TypographyTokens.bodySmall(
                cs.onSurface.withValues(alpha: 0.45),
              ),
            ),
          ],
        ],
      ),
    );
  }
}
