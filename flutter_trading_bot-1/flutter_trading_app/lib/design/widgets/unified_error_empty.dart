import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

enum ErrorSeverity { low, medium, high, critical }

class UnifiedError extends StatelessWidget {
  final String message;
  final ErrorSeverity severity;
  final VoidCallback? onRetry;
  final VoidCallback? onDismiss;
  final IconData? icon;

  const UnifiedError({
    super.key,
    required this.message,
    this.severity = ErrorSeverity.medium,
    this.onRetry,
    this.onDismiss,
    this.icon,
  });

  factory UnifiedError.network({
    VoidCallback? onRetry,
    VoidCallback? onDismiss,
  }) => const UnifiedError(
    message: 'خطأ في الاتصال بالإنترنت',
    severity: ErrorSeverity.medium,
    icon: Icons.wifi_off_rounded,
    onRetry: onRetry,
    onDismiss: onDismiss,
  );

  factory UnifiedError.server({
    VoidCallback? onRetry,
    VoidCallback? onDismiss,
  }) => const UnifiedError(
    message: 'خطأ في الخادم، يرجى المحاولة لاحقاً',
    severity: ErrorSeverity.high,
    icon: Icons.cloud_off_rounded,
    onRetry: onRetry,
    onDismiss: onDismiss,
  );

  factory UnifiedError.auth({
    VoidCallback? onRetry,
    VoidCallback? onDismiss,
  }) => const UnifiedError(
    message: 'انتهت الجلسة، يرجى تسجيل الدخول مرة أخرى',
    severity: ErrorSeverity.high,
    icon: Icons.lock_outline_rounded,
    onRetry: onRetry,
    onDismiss: onDismiss,
  );

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = _getColors(theme);

    return Container(
      padding: const EdgeInsets.all(SpacingTokens.md),
      decoration: BoxDecoration(
        color: colors.bg,
        borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
        border: Border.all(color: colors.border),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon ?? Icons.error_outline_rounded, 
               color: colors.icon, size: 48),
          const SizedBox(height: SpacingTokens.md),
          Text(
            message,
            style: TypographyTokens.bodyMedium(colors.text),
            textAlign: TextAlign.center,
          ),
          if (onRetry != null || onDismiss != null) ...[
            const SizedBox(height: SpacingTokens.md),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (onRetry != null)
                  FilledButton.icon(
                    onPressed: onRetry,
                    icon: const Icon(Icons.refresh_rounded, size: 18),
                    label: const Text('إعادة المحاولة'),
                  ),
                if (onDismiss != null) ...[
                  if (onRetry != null) const SizedBox(width: SpacingTokens.sm),
                  TextButton(
                    onPressed: onDismiss,
                    child: const Text('إغلاق'),
                  ),
                ],
              ],
            ),
          ],
        ],
      ),
    );
  }

  _ErrorColors _getColors(ThemeData theme) {
    switch (severity) {
      case ErrorSeverity.low:
        return _ErrorColors(
          bg: ColorsTokens.surfaceContainerHighest,
          text: theme.colorScheme.onSurface,
          icon: ColorsTokens.info,
          border: ColorsTokens.info.withValues(alpha: 0.3),
        );
      case ErrorSeverity.medium:
        return _ErrorColors(
          bg: ColorsTokens.warningContainer,
          text: ColorsTokens.onWarningContainer,
          icon: ColorsTokens.warning,
          border: ColorsTokens.warning.withValues(alpha: 0.3),
        );
      case ErrorSeverity.high:
      case ErrorSeverity.critical:
        return _ErrorColors(
          bg: ColorsTokens.errorContainer,
          text: ColorsTokens.onErrorContainer,
          icon: ColorsTokens.error,
          border: ColorsTokens.error.withValues(alpha: 0.3),
        );
    }
  }
}

class _ErrorColors {
  final Color bg;
  final Color text;
  final Color icon;
  final Color border;
  const _ErrorColors({
    required this.bg,
    required this.text,
    required this.icon,
    required this.border,
  });
}

class UnifiedEmpty extends StatelessWidget {
  final String title;
  final String? subtitle;
  final IconData icon;
  final Widget? action;

  const UnifiedEmpty({
    super.key,
    required this.title,
    this.subtitle,
    this.icon = Icons.inbox_rounded,
    this.action,
  });

  factory UnifiedEmpty.noData({String? actionLabel, VoidCallback? onAction}) => 
    UnifiedEmpty(
      title: 'لا توجد بيانات',
      subtitle: 'سيظهر هنا عند توفر البيانات',
      icon: Icons.table_rows_rounded,
      action: actionLabel != null
        ? FilledButton.icon(
            onPressed: onAction,
            icon: const Icon(Icons.add_rounded, size: 18),
            label: Text(actionLabel),
          )
        : null,
    );

  factory UnifiedEmpty.noTrades({VoidCallback? onRefresh}) => UnifiedEmpty(
    title: 'لا توجد صفقات',
    subtitle: 'لم تقم بأي صفقة بعد',
    icon: Icons.swap_horiz_rounded,
    action: onRefresh != null
      ? FilledButton.icon(
          onPressed: onRefresh,
          icon: const Icon(Icons.refresh_rounded, size: 18),
          label: const Text('تحديث'),
        )
      : null,
  );

  factory UnifiedEmpty.noNotifications() => const UnifiedEmpty(
    title: 'لا توجد إشعارات',
    subtitle: 'ستظهر الإشعارات هنا عند وصولها',
    icon: Icons.notifications_none_rounded,
  );

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(SpacingTokens.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 64,
              color: theme.colorScheme.onSurfaceVariant.withValues(alpha: 0.5),
            ),
            const SizedBox(height: SpacingTokens.md),
            Text(
              title,
              style: TypographyTokens.titleMedium(theme.colorScheme.onSurface),
              textAlign: TextAlign.center,
            ),
            if (subtitle != null) ...[
              const SizedBox(height: SpacingTokens.xs),
              Text(
                subtitle!,
                style: TypographyTokens.bodySmall(
                  theme.colorScheme.onSurfaceVariant,
                ),
                textAlign: TextAlign.center,
              ),
            ],
            if (action != null) ...[
              const SizedBox(height: SpacingTokens.lg),
              action!,
            ],
          ],
        ),
      ),
    );
  }
}
