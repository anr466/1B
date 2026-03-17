import 'package:flutter/material.dart';
import 'package:trading_app/design/icons/brand_icons.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// AppSettingTile — بطاقة إعداد موحدة مع أيقونة + عنوان + وصف + ذيل
/// تُستخدم في شاشة الحساب والإعدادات والإدارة
/// تصميم صافي — لا يعتمد على أي منطق أعمال
class AppSettingTile extends StatelessWidget {
  final dynamic icon; // IconData or BrandIconData
  final String label;
  final String? subtitle;
  final Widget? trailing;
  final VoidCallback? onTap;
  final Color? iconColor;
  final bool showChevron;
  final bool isDestructive;
  final EdgeInsetsGeometry? padding;

  const AppSettingTile({
    super.key,
    required this.icon,
    required this.label,
    this.subtitle,
    this.trailing,
    this.onTap,
    this.iconColor,
    this.showChevron = true,
    this.isDestructive = false,
    this.padding,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = cs.brightness == Brightness.dark;

    final effectiveIconColor = isDestructive
        ? cs.error
        : (iconColor ?? cs.primary);
    final labelColor = isDestructive ? cs.error : cs.onSurface;

    final effectivePadding =
        padding ??
        const EdgeInsets.symmetric(
          horizontal: SpacingTokens.base,
          vertical: SpacingTokens.md,
        );

    Widget tile = Padding(
      padding: effectivePadding,
      child: Row(
        children: [
          // ─── Icon Container ──────────────────────
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: effectiveIconColor.withValues(
                alpha: isDark ? 0.15 : 0.10,
              ),
              borderRadius: BorderRadius.circular(SpacingTokens.radiusSm),
            ),
            child: icon is BrandIconData
                ? BrandIcon(
                    icon as BrandIconData,
                    size: SpacingTokens.iconMd,
                    color: effectiveIconColor,
                  )
                : Icon(
                    icon as IconData,
                    size: SpacingTokens.iconMd,
                    color: effectiveIconColor,
                  ),
          ),
          const SizedBox(width: SpacingTokens.md),

          // ─── Label + Subtitle ────────────────────
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  label,
                  style: TypographyTokens.body(labelColor),
                ),
                if (subtitle != null) ...[
                  const SizedBox(height: SpacingTokens.xxs),
                  Text(
                    subtitle!,
                    style: TypographyTokens.caption(
                      cs.onSurface.withValues(alpha: 0.45),
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),

          // ─── Trailing / Chevron ──────────────────
          if (trailing != null)
            trailing!
          else if (showChevron)
            Icon(
              Icons.chevron_left_rounded,
              size: SpacingTokens.iconMd,
              color: cs.onSurface.withValues(alpha: 0.28),
            ),
        ],
      ),
    );

    if (onTap != null) {
      return InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(SpacingTokens.radiusLg),
        child: tile,
      );
    }

    return tile;
  }
}

/// AppSettingGroup — بطاقة تجمع عدة AppSettingTile مع فواصل
class AppSettingGroup extends StatelessWidget {
  final List<Widget> children;
  final EdgeInsetsGeometry? margin;

  const AppSettingGroup({
    super.key,
    required this.children,
    this.margin,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = cs.brightness == Brightness.dark;

    return Container(
      margin: margin,
      decoration: BoxDecoration(
        color: isDark ? cs.surfaceContainerHigh : cs.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(SpacingTokens.radiusLg),
        border: Border.all(
          color: cs.outline.withValues(alpha: isDark ? 0.18 : 0.12),
          width: 1,
        ),
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(SpacingTokens.radiusLg),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: _intersperse(children, context),
        ),
      ),
    );
  }

  List<Widget> _intersperse(List<Widget> items, BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final result = <Widget>[];
    for (int i = 0; i < items.length; i++) {
      result.add(items[i]);
      if (i < items.length - 1) {
        result.add(
          Divider(
            height: 1,
            thickness: 1,
            indent: SpacingTokens.base + 36 + SpacingTokens.md,
            color: cs.outline.withValues(alpha: 0.10),
          ),
        );
      }
    }
    return result;
  }
}
