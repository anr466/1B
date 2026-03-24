import 'package:flutter/material.dart';
import 'package:trading_app/design/icons/brand_icons.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/status_badge.dart';

/// Unified Trading Status Strip — shows trading enabled/disabled state
/// تصميم صافي — لا يعتمد على منطق أعمال محدد
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
    final isDark = cs.brightness == Brightness.dark;
    final isLoadingState = isLoading || enabled == null;
    final active = enabled ?? false;
    final statusTone = active ? cs.primary : cs.tertiary;
    final badgeType = active ? BadgeType.success : BadgeType.warning;
    final subtitle = active
        ? 'النظام ينفذ صفقات جديدة'
        : 'النظام يراقب الصفقات المفتوحة فقط';

    return IntrinsicHeight(
      child: Container(
        decoration: BoxDecoration(
          color: isDark ? cs.surfaceContainerHigh : cs.surfaceContainerLow,
          borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
          border: Border.all(
            color: cs.outline.withValues(alpha: isDark ? 0.18 : 0.12),
            width: 1,
          ),
        ),
        child: Row(
          children: [
            Container(
              width: 4,
              decoration: BoxDecoration(
                color: statusTone,
                borderRadius: const BorderRadius.only(
                  topRight: Radius.circular(SpacingTokens.radiusMd),
                  bottomRight: Radius.circular(SpacingTokens.radiusMd),
                ),
              ),
            ),
            const SizedBox(width: SpacingTokens.sm),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: SpacingTokens.md),
              child: isLoadingState
                  ? SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: cs.onSurface.withValues(alpha: 0.4),
                      ),
                    )
                  : BrandIcon(BrandIcons.shield, size: 16, color: statusTone),
            ),
            const SizedBox(width: SpacingTokens.xs),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: SpacingTokens.md),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: SpacingTokens.xs,
                      runSpacing: 4,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        Text(
                          'حالة التداول',
                          style: TypographyTokens.bodySmall(
                            cs.onSurface.withValues(alpha: 0.8),
                          ).copyWith(fontWeight: FontWeight.w600),
                        ),
                        if (!isLoadingState)
                          StatusBadge(
                            text: active ? 'مفعل' : 'متوقف',
                            type: badgeType,
                          ),
                      ],
                    ),
                    const SizedBox(height: 2),
                    Text(
                      isLoadingState ? 'جارٍ التحديث...' : subtitle,
                      style: TypographyTokens.caption(
                        cs.onSurface.withValues(alpha: 0.45),
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: SpacingTokens.sm),
              child: SizedBox(
                width: 50,
                child: isLoadingState
                    ? const SizedBox.shrink()
                    : Switch(
                        value: active,
                        onChanged: onChanged,
                        activeThumbColor: cs.primary,
                      ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
