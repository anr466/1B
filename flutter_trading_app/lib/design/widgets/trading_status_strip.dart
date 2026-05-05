import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// Trading Status — زر موحد لتفعيل/إيقاف التداول الشخصي
/// العنصر الوحيد المسؤول عن هذه الوظيفة في كامل التطبيق
class TradingStatusStrip extends StatelessWidget {
  final bool? enabled;
  final bool isLoading;
  final ValueChanged<bool>? onChanged;

  const TradingStatusStrip({
    super.key,
    this.enabled,
    this.isLoading = false,
    this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final sem = SemanticColors.of(context);
    final active = enabled ?? false;

    return Container(
      padding: const EdgeInsets.all(SpacingTokens.lg),
      decoration: BoxDecoration(
        color: active
            ? sem.positive.withValues(alpha: 0.06)
            : cs.surfaceContainerLow,
        borderRadius: BorderRadius.circular(SpacingTokens.radiusXl),
      ),
      child: Row(
        children: [
          Container(
            width: 48, height: 48,
            decoration: BoxDecoration(
              color: active
                  ? sem.positive.withValues(alpha: 0.15)
                  : cs.surfaceContainer,
              borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
            ),
            child: Center(
              child: Icon(
                active ? Icons.flash_on_rounded : Icons.flash_off_rounded,
                color: active ? sem.positive : cs.onSurface.withValues(alpha: 0.3),
                size: 24,
              ),
            ),
          ),
          const SizedBox(width: SpacingTokens.md),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  active ? 'التداول مفعّل' : 'التداول معطّل',
                  style: TypographyTokens.body(cs.onSurface)
                      .copyWith(fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: SpacingTokens.xxs),
                Text(
                  isLoading
                      ? 'جارٍ التحديث...'
                      : active
                          ? 'المحرك يفتح صفقات جديدة تلقائياً'
                          : 'لن يفتح المحرك صفقات جديدة',
                  style: TypographyTokens.caption(
                    active
                        ? sem.positive.withValues(alpha: 0.7)
                        : cs.onSurface.withValues(alpha: 0.4),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: SpacingTokens.sm),
          if (isLoading)
            const SizedBox(
              width: 24, height: 24,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
          else
            Switch(
              value: active,
              onChanged: onChanged,
              activeColor: sem.positive,
              activeTrackColor: sem.positive.withValues(alpha: 0.3),
            ),
        ],
      ),
    );
  }
}
