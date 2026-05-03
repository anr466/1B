import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_icon_button.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/error_state.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/demo_real_banner.dart';
import 'package:trading_app/design/widgets/status_badge.dart';

/// Error Details Provider
final _errorDetailsProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>, int>((ref, errorId) async {
      final repo = ref.watch(adminRepositoryProvider);
      return repo.getSystemErrorDetails(errorId);
    });

/// Error Details Screen — تفاصيل الخطأ
class ErrorDetailsScreen extends ConsumerStatefulWidget {
  final int errorId;

  const ErrorDetailsScreen({super.key, required this.errorId});

  @override
  ConsumerState<ErrorDetailsScreen> createState() => _ErrorDetailsScreenState();
}

class _ErrorDetailsScreenState extends ConsumerState<ErrorDetailsScreen> {
  bool _isResolving = false;
  bool _isRetrying = false;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final errorAsync = ref.watch(_errorDetailsProvider(widget.errorId));

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            children: [
              AppScreenHeader(
                title: 'تفاصيل الخطأ #${widget.errorId}',
                showBack: true,
                trailing: AppIconButton(
                  icon: Icons.refresh_rounded,
                  onTap: () => ref.invalidate(_errorDetailsProvider(widget.errorId)),
                ),
              ),
              const DemoRealBanner(),
              Expanded(
                child: errorAsync.when(
                  loading: () => const Padding(
                    padding: EdgeInsets.all(SpacingTokens.base),
                    child: LoadingShimmer(itemCount: 6, itemHeight: 100),
                  ),
                  error: (e, _) => ErrorState(
                    message: e.toString(),
                    onRetry: () =>
                        ref.invalidate(_errorDetailsProvider(widget.errorId)),
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
                        _buildActionsCard(context, cs, error),
                        const SizedBox(height: SpacingTokens.xl),
                      ],
                    ),
                  ),
                ),
              ),
            ],
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
    final sem = SemanticColors.of(context);
    final severity = (error['severity'] ?? 'medium') as String;
    final status = (error['status'] ?? 'new') as String;
    final requiresAdmin =
        error['requires_admin'] == 1 || error['requires_admin'] == true;

    final severityColor = switch (severity) {
      'critical' => cs.error,
      'high' => sem.warning,
      'medium' => cs.tertiary,
      _ => sem.info,
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
                  AppSnackbar.show(context, message: 'تم النسخ', type: SnackType.success);
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
                  AppSnackbar.show(context, message: 'تم النسخ', type: SnackType.success);
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
            constraints: const BoxConstraints(maxHeight: 250),
            child: SelectableText(
              error['traceback'].toString(),
              style: TypographyTokens.code(
                cs.onSurface,
              ).copyWith(fontSize: 11),
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
  ) {
    final sem = SemanticColors.of(context);
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
              onPressed: _isResolving ? null : _resolveError,
              icon: _isResolving ? null : Icons.check_circle,
              isLoading: _isResolving,
            ),
            const SizedBox(height: SpacingTokens.sm),
            if (canAutoFix)
              AppButton(
                label: 'إعادة محاولة الإصلاح التلقائي',
                onPressed: _isRetrying ? null : _retryAutoFix,
                icon: _isRetrying ? null : Icons.autorenew,
                isLoading: _isRetrying,
              ),
          ] else
            Container(
              padding: const EdgeInsets.all(SpacingTokens.md),
              decoration: BoxDecoration(
                color: sem.successContainer,
                borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
                border: Border.all(color: sem.success.withValues(alpha: 0.3)),
              ),
              child: Row(
                children: [
                  Icon(Icons.check_circle, color: sem.success),
                  const SizedBox(width: SpacingTokens.sm),
                  Text(
                    'تم حل هذا الخطأ',
                    style: TypographyTokens.body(sem.success),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  Future<void> _resolveError() async {
    final notes = await showDialog<String>(
      context: context,
      builder: (ctx) => _ResolveDialog(),
    );

    if (notes == null) return;

    setState(() => _isResolving = true);
    try {
      final repo = ref.read(adminRepositoryProvider);
      await repo.resolveSystemError(widget.errorId, notes: notes);

      if (mounted) {
        AppSnackbar.show(context, message: 'تم تعليم الخطأ كمحلول', type: SnackType.success);
        ref.invalidate(_errorDetailsProvider(widget.errorId));
        setState(() => _isResolving = false);
      }
    } catch (e) {
      if (mounted) {
        AppSnackbar.show(context, message: 'فشلت العملية: $e', type: SnackType.error);
        setState(() => _isResolving = false);
      }
    }
  }

  Future<void> _retryAutoFix() async {
    setState(() => _isRetrying = true);
    try {
      final repo = ref.read(adminRepositoryProvider);
      final result = await repo.retryAutoFix(widget.errorId);

      if (mounted) {
        final message = result['message'] ?? 'تمت العملية';
        final success = result['success'] == true;
        AppSnackbar.show(context, message: message, type: success ? SnackType.success : SnackType.error);
        ref.invalidate(_errorDetailsProvider(widget.errorId));
        setState(() => _isRetrying = false);
      }
    } catch (e) {
      if (mounted) {
        AppSnackbar.show(context, message: 'فشلت العملية: $e', type: SnackType.error);
        setState(() => _isRetrying = false);
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
          AppButton(
            label: 'إلغاء',
            variant: AppButtonVariant.text,
            isFullWidth: false,
            onPressed: () => Navigator.pop(context),
          ),
          AppButton(
            label: 'تأكيد',
            variant: AppButtonVariant.primary,
            isFullWidth: false,
            onPressed: () => Navigator.pop(context, _controller.text),
          ),
        ],
      ),
    );
  }
}
