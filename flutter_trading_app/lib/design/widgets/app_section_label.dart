import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// AppSectionLabel — عنوان قسم صغير مُعتم (بديل لـ Text inline)
/// يُستخدم لتصنيف المجموعات داخل الشاشة
/// تصميم صافي — لا يعتمد على أي منطق أعمال
class AppSectionLabel extends StatelessWidget {
  final String text;
  final EdgeInsetsGeometry? padding;
  final Color? color;

  const AppSectionLabel({
    super.key,
    required this.text,
    this.padding,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final effectivePadding =
        padding ??
        const EdgeInsets.only(
          bottom: SpacingTokens.sm,
        );

    return Padding(
      padding: effectivePadding,
      child: Text(
        text,
        style: TypographyTokens.overline(
          color ?? cs.onSurface.withValues(alpha: 0.45),
        ).copyWith(letterSpacing: 0),
      ),
    );
  }
}
