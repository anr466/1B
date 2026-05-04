import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_button.dart';

/// Error State — رسالة خطأ + زر "حاول مرة أخرى"
class ErrorState extends StatelessWidget {
  final String message;
  final VoidCallback? onRetry;

  const ErrorState({super.key, required this.message, this.onRetry});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(SpacingTokens.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.error_outline_rounded,
              size: 56,
              color: cs.error.withValues(alpha: 0.6),
            ),
            const SizedBox(height: SpacingTokens.base),
            Text(
              message,
              style: TypographyTokens.body(cs.onSurface.withValues(alpha: 0.7)),
              textAlign: TextAlign.center,
            ),
            if (onRetry != null) ...[
              const SizedBox(height: SpacingTokens.lg),
              AppButton(
                label: 'حاول مرة أخرى',
                onPressed: onRetry,
                variant: AppButtonVariant.outline,
                isFullWidth: false,
                height: 44,
              ),
            ],
          ],
        ),
      ),
    );
  }
}
