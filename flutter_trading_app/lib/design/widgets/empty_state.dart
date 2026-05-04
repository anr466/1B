import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// Empty State — رسالة + أيقونة توضيحية عند عدم وجود بيانات
class EmptyState extends StatelessWidget {
  final String message;
  final String? subtitle;
  final IconData? icon;

  const EmptyState({
    super.key,
    required this.message,
    this.subtitle,
    this.icon,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(SpacingTokens.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (icon != null)
              Icon(icon, size: 64, color: cs.onSurface.withValues(alpha: 0.2)),
            if (icon != null) const SizedBox(height: SpacingTokens.base),
            Text(
              message,
              style: TypographyTokens.h3(cs.onSurface.withValues(alpha: 0.5)),
              textAlign: TextAlign.center,
            ),
            if (subtitle != null) ...[
              const SizedBox(height: SpacingTokens.sm),
              Text(
                subtitle!,
                style: TypographyTokens.bodySmall(
                  cs.onSurface.withValues(alpha: 0.35),
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
