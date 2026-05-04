import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// AppInfoRow — صف مفتاح/قيمة موحد لعرض البيانات داخل البطاقات
/// تصميم صافي — لا يعتمد على أي منطق أعمال
class AppInfoRow extends StatelessWidget {
  final String label;
  final String? value;
  final Widget? valueWidget;
  final Color? valueColor;
  final bool isMonospace;
  final EdgeInsetsGeometry? padding;

  const AppInfoRow({
    super.key,
    required this.label,
    this.value,
    this.valueWidget,
    this.valueColor,
    this.isMonospace = true,
    this.padding,
  }) : assert(value != null || valueWidget != null);

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final effectivePadding =
        padding ??
        const EdgeInsets.only(bottom: SpacingTokens.sm);

    final vColor = valueColor ?? cs.onSurface;
    final valueStyle = isMonospace
        ? TypographyTokens.mono(vColor, fontSize: 14)
        : TypographyTokens.bodySmall(vColor);

    return Padding(
      padding: effectivePadding,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Text(
            label,
            style: TypographyTokens.bodySmall(
              cs.onSurface.withValues(alpha: 0.5),
            ),
          ),
          Flexible(
            child: valueWidget ??
                Text(
                  value!,
                  style: valueStyle,
                  textAlign: TextAlign.end,
                  overflow: TextOverflow.ellipsis,
                ),
          ),
        ],
      ),
    );
  }
}

/// AppInfoDivider — فاصل خفيف بين صفوف المعلومات
class AppInfoDivider extends StatelessWidget {
  const AppInfoDivider({super.key});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Divider(
      height: SpacingTokens.lg,
      thickness: 1,
      color: cs.outline.withValues(alpha: 0.15),
    );
  }
}
