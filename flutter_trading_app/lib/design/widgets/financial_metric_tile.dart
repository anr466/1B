import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_card.dart';

/// FinancialMetricTile — بلاطة مقياس مالي موحدة
///
/// Shows a labeled financial value with optional change indicator.
/// Used for key metrics like PnL, win rate, balance, etc.
class FinancialMetricTile extends StatelessWidget {
  final String label;
  final String value;

  /// Optional % change — shows up/down indicator if non-null
  final double? change;

  /// If true, uses semantic positive/negative colors for [value]
  final bool? isPositive;

  /// Card level: 0=flat, 1=default, 2=raised
  final int level;

  final VoidCallback? onTap;

  /// Optional footer widget — displayed below the value (e.g. progress bar)
  final Widget? footer;

  const FinancialMetricTile({
    super.key,
    required this.label,
    required this.value,
    this.change,
    this.isPositive,
    this.level = 1,
    this.onTap,
    this.footer,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final semantic = SemanticColors.of(context);

    final Color valueColor;
    if (isPositive == true) {
      valueColor = semantic.positive;
    } else if (isPositive == false) {
      valueColor = semantic.negative;
    } else {
      valueColor = cs.onSurface;
    }

    final hasChange = change != null;
    final changePositive = (change ?? 0) >= 0;
    final changeColor = changePositive ? semantic.positive : semantic.negative;
    final changeIcon = changePositive
        ? Icons.arrow_upward_rounded
        : Icons.arrow_downward_rounded;
    final changeText = hasChange
        ? '${changePositive ? '+' : ''}${change!.toStringAsFixed(1)}%'
        : '';

    return AppCard(
      level: level,
      onTap: onTap,
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.md,
        vertical: SpacingTokens.md,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: TypographyTokens.caption(cs.onSurfaceVariant),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: SpacingTokens.xs),
          Text(
            value,
            style: TypographyTokens.mono(
              valueColor,
              fontSize: 16,
            ).copyWith(fontWeight: FontWeight.w700),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          if (hasChange) ...[
            const SizedBox(height: SpacingTokens.xxs),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(changeIcon, size: 11, color: changeColor),
                const SizedBox(width: 2),
                Text(
                  changeText,
                  style: TypographyTokens.caption(
                    changeColor,
                  ).copyWith(fontWeight: FontWeight.w600, fontSize: 10),
                ),
              ],
            ),
          ],
          if (footer != null) ...[
            const SizedBox(height: SpacingTokens.sm),
            footer!,
          ],
        ],
      ),
    );
  }
}
