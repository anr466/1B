import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/status_badge.dart';

/// Error Details Provider
final _errorDetailsProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>, int>((ref, errorId) async {
      final repo = ref.watch(adminRepositoryProvider);
      return repo.getSystemErrorDetails(errorId);
    });

/// Error Details Screen — تفاصيل الخطأ
class ErrorDetailsScreen extends ConsumerWidget {
  final int errorId;

  const ErrorDetailsScreen({super.key, required this.errorId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final errorAsync = ref.watch(_errorDetailsProvider(errorId));

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        appBar: AppBar(
          title: Text(
            'تفاصيل الخطأ #$errorId',
            style: TypographyTokens.h3(cs.onSurface),
          ),
          actions: [
            IconButton(
              icon: const Icon(Icons.refresh),
              onPressed: () => ref.invalidate(_errorDetailsProvider(errorId)),
            ),
          ],
        ),
        body: errorAsync.when(
          loading: () => const Padding(
            padding: EdgeInsets.all(SpacingTokens.base),
            child: LoadingShimmer(itemCount: 6, itemHeight: 100),
          ),
          error: (e, _) => Center(
            child: Padding(
              padding: const EdgeInsets.all(SpacingTokens.base),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.error_outline, size: 64, color: cs.error),
                  const SizedBox(height: SpacingTokens.md),
                  Text(
                    'فشل تحميل التفاصيل',
                    style: TypographyTokens.h3(cs.error),
                  ),
                  const SizedBox(height: SpacingTokens.sm),
                  Text(
                    e.toString(),
                    style: TypographyTokens.body(
                      cs.onSurface.withValues(alpha: 0.6),
                    ),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
          ),
          data: (error) => SingleChildScrollView(
            padding: const EdgeInsets.all(SpacingTokens.base),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildHeaderCard(context, cs, error),
                const SizedBox(height: SpacingTokens.md),
                _buildMessageCard(context, cs, error),
                const SizedBox(height: SpacingTokens.md),
                _buildMetadataCard(context, cs, error),
                if (error['details'] != null &&
                    error['details'].toString().isNotEmpty) ...[
                  const SizedBox(height: SpacingTokens.md),
                  _buildDetailsCard(context, cs, error),
                ],
                if (error['traceback'] != null &&
                    error['traceback'].toString().isNotEmpty) ...[
                  const SizedBox(height: SpacingTokens.md),
                  _buildTracebackCard(context, cs, error),
                ],
                if (error['similar_count'] != null &&
                    error['similar_count'] > 0) ...[
                  const SizedBox(height: SpacingTokens.md),
                  _buildSimilarErrorsCard(context, cs, error),
                ],
                const SizedBox(height: SpacingTokens.md),
                _buildActionsCard(context, cs, error, ref),
                const SizedBox(height: SpacingTokens.xl),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeaderCard(
    BuildContext context,
    ColorScheme cs,
    Map<String, dynamic> error,
  ) {
    final severity = (error['severity'] ?? 'medium') as String;
    final status = (error['status'] ?? 'new') as String;
    final requiresAdmin =
        error['requires_admin'] == 1 || error['requires_admin'] == true;

    final severityColor = switch (severity) {
      'critical' => Colors.red,
      'high' => Colors.orange,
      'medium' => Colors.amber,
      _ => Colors.blue,
    };

    final statusBadgeType = switch (status) {
      'resolved' || 'auto_resolved' => BadgeType.success,
      'escalated' => BadgeType.error,
      _ => BadgeType.warning,
    };

    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: SpacingTokens.md,
                  vertical: SpacingTokens.sm,
                ),
                decoration: BoxDecoration(
                  color: severityColor.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
                  border: Border.all(color: severityColor),
                ),
                child: Text(
                  severity.toUpperCase(),
                  style: TypographyTokens.h4(
                    severityColor,
                  ).copyWith(fontWeight: FontWeight.bold),
                ),
              ),
              const SizedBox(width: SpacingTokens.sm),
              StatusBadge(text: status, type: statusBadgeType, showDot: true),
              if (requiresAdmin) ...[
                const SizedBox(width: SpacingTokens.sm),
                Chip(
                  label: const Text('يتطلب أدمن'),
                  backgroundColor: cs.error.withValues(alpha: 0.2),
                  labelStyle: TypographyTokens.caption(cs.error),
                  avatar: Icon(
                    Icons.admin_panel_settings,
                    size: 16,
                    color: cs.error,
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: SpacingTokens.md),
          Row(
            children: [
              Icon(
                Icons.label_outline,
                size: 16,
                color: cs.onSurface.withValues(alpha: 0.6),
              ),
              const SizedBox(width: SpacingTokens.xs),
              Text(
                'النوع: ${error['error_type'] ?? 'غير محدد'}',
                style: TypographyTokens.body(
                  cs.onSurface.withValues(alpha: 0.6),
                ),
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.xs),
          Row(
            children: [
              Icon(
                Icons.source,
                size: 16,
                color: cs.onSurface.withValues(alpha: 0.6),
              ),
              const SizedBox(width: SpacingTokens.xs),
              Text(
                'المصدر: ${error['source'] ?? 'غير محدد'}',
                style: TypographyTokens.body(
                  cs.onSurface.withValues(alpha: 0.6),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildMessageCard(
    BuildContext context,
    ColorScheme cs,
    Map<String, dynamic> error,
  ) {
    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.error_outline, color: cs.error, size: 20),
              const SizedBox(width: SpacingTokens.sm),
              Text('رسالة الخطأ', style: TypographyTokens.h4(cs.onSurface)),
            ],
          ),
          const SizedBox(height: SpacingTokens.md),
          SelectableText(
            error['error_message'] ?? 'لا توجد رسالة',
            style: TypographyTokens.body(cs.onSurface),
          ),
        ],
      ),
    );
  }

  Widget _buildMetadataCard(
    BuildContext context,
    ColorScheme cs,
    Map<String, dynamic> error,
  ) {
    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('معلومات إضافية', style: TypographyTokens.h4(cs.onSurface)),
          const SizedBox(height: SpacingTokens.md),
          _metadataRow(
            cs,
            'تاريخ الحدوث',
            error['created_at']?.toString().split('.').first ?? '-',
          ),
          if (error['resolved'] == 1) ...[
            const SizedBox(height: SpacingTokens.sm),
            _metadataRow(
              cs,
              'تاريخ الحل',
              error['resolved_at']?.toString().split('.').first ?? '-',
            ),
            const SizedBox(height: SpacingTokens.sm),
            _metadataRow(cs, 'تم الحل بواسطة', error['resolved_by'] ?? '-'),
          ],
          const SizedBox(height: SpacingTokens.sm),
          _metadataRow(
            cs,
            'عدد المحاولات',
            error['attempt_count']?.toString() ?? '0',
          ),
          if (error['last_attempt_at'] != null) ...[
            const SizedBox(height: SpacingTokens.sm),
            _metadataRow(
              cs,
              'آخر محاولة',
              error['last_attempt_at'].toString().split('.').first,
            ),
          ],
          if (error['auto_action'] != null &&
              error['auto_action'].toString().isNotEmpty) ...[
            const SizedBox(height: SpacingTokens.sm),
            _metadataRow(cs, 'إجراء تلقائي', error['auto_action'] ?? '-'),
          ],
        ],
      ),
    );
  }

  Widget _metadataRow(ColorScheme cs, String label, String value) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 120,
          child: Text(
            label,
            style: TypographyTokens.bodySmall(
              cs.onSurface.withValues(alpha: 0.6),
            ),
          ),
        ),
        Expanded(
          child: Text(value, style: TypographyTokens.bodySmall(cs.onSurface)),
        ),
      ],
    );
  }

  Widget _buildDetailsCard(
    BuildContext context,
    ColorScheme cs,
    Map<String, dynamic> error,
  ) {
    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text('التفاصيل', style: TypographyTokens.h4(cs.onSurface)),
              IconButton(
                icon: const Icon(Icons.copy, size: 18),
                onPressed: () {
                  Clipboard.setData(
                    ClipboardData(text: error['details'].toString()),
                  );
                  ScaffoldMessenger.of(
                    context,
                  ).showSnackBar(const SnackBar(content: Text('تم النسخ')));
                },
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.sm),
          Container(
            padding: const EdgeInsets.all(SpacingTokens.md),
            decoration: BoxDecoration(
              color: cs.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
            ),
            child: SelectableText(
              error['details'].toString(),
              style: TypographyTokens.code(cs.onSurface),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTracebackCard(
    BuildContext context,
    ColorScheme cs,
    Map<String, dynamic> error,
  ) {
    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Stack Trace (للمطورين)',
                style: TypographyTokens.h4(cs.onSurface),
              ),
              IconButton(
                icon: const Icon(Icons.copy, size: 18),
                onPressed: () {
                  Clipboard.setData(
                    ClipboardData(text: error['traceback'].toString()),
                  );
                  ScaffoldMessenger.of(
                    context,
                  ).showSnackBar(const SnackBar(content: Text('تم النسخ')));
                },
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.sm),
          Container(
            padding: const EdgeInsets.all(SpacingTokens.md),
            decoration: BoxDecoration(
              color: cs.surfaceContainerHighest,
              borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
            ),
            constraints: const BoxConstraints(maxHeight: 300),
            child: SingleChildScrollView(
              child: SelectableText(
                error['traceback'].toString(),
                style: TypographyTokens.code(
                  cs.onSurface,
                ).copyWith(fontSize: 11),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSimilarErrorsCard(
    BuildContext context,
    ColorScheme cs,
    Map<String, dynamic> error,
  ) {
    final count = error['similar_count'] ?? 0;
    final lastOccurrence =
        error['last_occurrence']?.toString().split('.').first ?? '-';

    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.copy_all, color: cs.primary, size: 20),
              const SizedBox(width: SpacingTokens.sm),
              Text('أخطاء مشابهة', style: TypographyTokens.h4(cs.onSurface)),
            ],
          ),
          const SizedBox(height: SpacingTokens.md),
          Container(
            padding: const EdgeInsets.all(SpacingTokens.md),
            decoration: BoxDecoration(
              color: cs.primaryContainer.withValues(alpha: 0.3),
              borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
              border: Border.all(color: cs.primary.withValues(alpha: 0.3)),
            ),
            child: Column(
              children: [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'عدد التكرارات:',
                      style: TypographyTokens.body(cs.onSurface),
                    ),
                    Text(
                      count.toString(),
                      style: TypographyTokens.h3(
                        cs.primary,
                      ).copyWith(fontWeight: FontWeight.bold),
                    ),
                  ],
                ),
                const SizedBox(height: SpacingTokens.sm),
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      'آخر ظهور:',
                      style: TypographyTokens.bodySmall(cs.onSurface),
                    ),
                    Text(
                      lastOccurrence,
                      style: TypographyTokens.bodySmall(
                        cs.onSurface.withValues(alpha: 0.7),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActionsCard(
    BuildContext context,
    ColorScheme cs,
    Map<String, dynamic> error,
    WidgetRef ref,
  ) {
    final status = error['status'] as String?;
    final autoAction = error['auto_action'] as String?;
    final isResolved = status == 'resolved' || status == 'auto_resolved';
    final canAutoFix =
        autoAction != null &&
        autoAction != 'manual_investigation' &&
        !isResolved;

    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text('إجراءات', style: TypographyTokens.h4(cs.onSurface)),
          const SizedBox(height: SpacingTokens.md),
          if (!isResolved) ...[
            AppButton(
              label: 'تعليم كمحلول',
              onPressed: () => _resolveError(context, ref),
              icon: Icons.check_circle,
            ),
            const SizedBox(height: SpacingTokens.sm),
            if (canAutoFix)
              AppButton(
                label: 'إعادة محاولة الإصلاح التلقائي',
                onPressed: () => _retryAutoFix(context, ref),
                icon: Icons.autorenew,
              ),
          ] else
            Container(
              padding: const EdgeInsets.all(SpacingTokens.md),
              decoration: BoxDecoration(
                color: Colors.green.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
                border: Border.all(color: Colors.green.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  Icon(Icons.check_circle, color: Colors.green),
                  const SizedBox(width: SpacingTokens.sm),
                  Text(
                    'تم حل هذا الخطأ',
                    style: TypographyTokens.body(Colors.green),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Future<void> _resolveError(BuildContext context, WidgetRef ref) async {
    final notes = await showDialog<String>(
      context: context,
      builder: (ctx) => _ResolveDialog(),
    );

    if (notes == null) return;

    try {
      final repo = ref.read(adminRepositoryProvider);
      await repo.resolveSystemError(errorId, notes: notes);

      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('تم تعليم الخطأ كمحلول')));
        ref.invalidate(_errorDetailsProvider(errorId));
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('فشلت العملية: $e')));
      }
    }
  }

  Future<void> _retryAutoFix(BuildContext context, WidgetRef ref) async {
    try {
      final repo = ref.read(adminRepositoryProvider);
      final result = await repo.retryAutoFix(errorId);

      if (context.mounted) {
        final message = result['message'] ?? 'تمت العملية';
        final success = result['success'] == true;
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(message),
            backgroundColor: success ? Colors.green : null,
          ),
        );
        ref.invalidate(_errorDetailsProvider(errorId));
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('فشلت العملية: $e')));
      }
    }
  }
}

class _ResolveDialog extends StatefulWidget {
  @override
  State<_ResolveDialog> createState() => _ResolveDialogState();
}

class _ResolveDialogState extends State<_ResolveDialog> {
  final _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Directionality(
      textDirection: TextDirection.rtl,
      child: AlertDialog(
        title: Text('تعليم كمحلول', style: TypographyTokens.h3(cs.onSurface)),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'هل تريد إضافة ملاحظات حول كيفية حل هذا الخطأ؟',
              style: TypographyTokens.body(cs.onSurface),
            ),
            const SizedBox(height: SpacingTokens.md),
            TextField(
              controller: _controller,
              decoration: const InputDecoration(
                labelText: 'ملاحظات (اختياري)',
                hintText: 'مثال: تم إصلاحه يدويًا من قاعدة البيانات',
                border: OutlineInputBorder(),
              ),
              maxLines: 3,
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('إلغاء'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, _controller.text),
            child: const Text('تأكيد'),
          ),
        ],
      ),
    );
  }
}
