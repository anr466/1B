import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// Section Header — عنوان قسم مع رابط "عرض الكل" اختياري
class SectionHeader extends StatelessWidget {
  final String title;
  final String? actionText;
  final VoidCallback? onAction;

  const SectionHeader({
    super.key,
    required this.title,
    this.actionText,
    this.onAction,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.base,
        vertical: SpacingTokens.sm,
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(title, style: TypographyTokens.h3(cs.onSurface)),
          if (actionText != null && onAction != null)
            GestureDetector(
              onTap: onAction,
              child: Text(
                actionText!,
                style: TypographyTokens.bodySmall(cs.primary),
              ),
            ),
        ],
      ),
    );
  }
}
