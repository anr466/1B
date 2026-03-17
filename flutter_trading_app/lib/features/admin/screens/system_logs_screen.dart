import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/empty_state.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Only loads errors that require admin intervention and are NOT yet resolved
final _activeErrorsProvider =
    FutureProvider.autoDispose<List<Map<String, dynamic>>>((ref) async {
      final repo = ref.watch(adminRepositoryProvider);
      final result = await repo.getSystemErrors(
        page: 1,
        perPage: 50,
        requiresAdmin: true,
        status: null,
      );
      return result.errors.where((e) {
        final s = (e['status'] ?? '').toString();
        return s != 'resolved' && s != 'auto_resolved';
      }).toList();
    });

class SystemLogsScreen extends ConsumerWidget {
  const SystemLogsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final errorsAsync = ref.watch(_activeErrorsProvider);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        appBar: AppBar(
          title: Text(
            'أخطاء تحتاج تدخل',
            style: TypographyTokens.h3(cs.onSurface),
          ),
          actions: [
            _ClearResolvedButton(
              onDone: () => ref.invalidate(_activeErrorsProvider),
            ),
            const SizedBox(width: SpacingTokens.sm),
          ],
        ),
        body: RefreshIndicator(
          color: cs.primary,
          onRefresh: () async => ref.invalidate(_activeErrorsProvider),
          child: errorsAsync.when(
            loading: () => const Padding(
              padding: EdgeInsets.all(SpacingTokens.base),
              child: LoadingShimmer(itemCount: 5, itemHeight: 80),
            ),
            error: (e, _) => Center(
              child: Text(e.toString(), style: TypographyTokens.body(cs.error)),
            ),
            data: (errors) {
              if (errors.isEmpty) {
                return const EmptyState(message: 'لا توجد أخطاء نشطة');
              }
              return ListView.builder(
                padding: const EdgeInsets.all(SpacingTokens.base),
                itemCount: errors.length,
                itemBuilder: (_, i) => _ErrorCard(error: errors[i], ref: ref),
              );
            },
          ),
        ),
      ),
    );
  }
}

// ─── Clear Resolved Button ────────────────────────────────────────────────────

class _ClearResolvedButton extends ConsumerWidget {
  final VoidCallback onDone;
  const _ClearResolvedButton({required this.onDone});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    return IconButton(
      tooltip: 'مسح السجلات المحلولة',
      icon: Icon(
        Icons.delete_sweep_outlined,
        color: cs.onSurface.withValues(alpha: 0.6),
      ),
      onPressed: () async {
        final confirmed = await showDialog<bool>(
          context: context,
          builder: (_) => Directionality(
            textDirection: TextDirection.rtl,
            child: AlertDialog(
              title: const Text('مسح السجلات المحلولة'),
              content: const Text(
                'سيتم حذف جميع الأخطاء المحلولة. هل تريد المتابعة؟',
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: const Text('إلغاء'),
                ),
                TextButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: Text('مسح', style: TextStyle(color: cs.error)),
                ),
              ],
            ),
          ),
        );
        if (confirmed != true) return;
        try {
          final repo = ref.read(adminRepositoryProvider);
          final deleted = await repo.clearResolvedErrors();
          onDone();
          if (context.mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('تم حذف $deleted سجل'),
                behavior: SnackBarBehavior.floating,
              ),
            );
          }
        } catch (_) {
          if (context.mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(
                content: Text('تعذر إتمام العملية'),
                behavior: SnackBarBehavior.floating,
              ),
            );
          }
        }
      },
    );
  }
}

// ─── Error Card ───────────────────────────────────────────────────────────────

class _ErrorCard extends ConsumerWidget {
  final Map<String, dynamic> error;
  final WidgetRef ref;
  const _ErrorCard({required this.error, required this.ref});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final severity = (error['severity'] ?? 'medium').toString();
    final source = (error['source'] ?? '').toString();
    final message = (error['error_message'] ?? 'خطأ غير محدد').toString();
    final createdAt = (error['created_at'] ?? '').toString().split('.').first;

    final severityColor = switch (severity) {
      'critical' => Colors.red,
      'high' => Colors.orange,
      _ => Colors.amber,
    };

    return Padding(
      padding: const EdgeInsets.only(bottom: SpacingTokens.sm),
      child: AppCard(
        padding: EdgeInsets.zero,
        onTap: () =>
            context.push(RouteNames.errorDetails, extra: error['id'] as int),
        child: IntrinsicHeight(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Severity bar
              Container(
                width: 4,
                decoration: BoxDecoration(
                  color: severityColor,
                  borderRadius: const BorderRadius.only(
                    topRight: Radius.circular(SpacingTokens.radiusMd),
                    bottomRight: Radius.circular(SpacingTokens.radiusMd),
                  ),
                ),
              ),
              const SizedBox(width: SpacingTokens.md),
              // Content
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    vertical: SpacingTokens.md,
                    horizontal: SpacingTokens.sm,
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: SpacingTokens.sm,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: severityColor.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(
                                SpacingTokens.radiusFull,
                              ),
                            ),
                            child: Text(
                              severity.toUpperCase(),
                              style: TypographyTokens.caption(
                                severityColor,
                              ).copyWith(fontWeight: FontWeight.bold),
                            ),
                          ),
                          if (source.isNotEmpty) ...[
                            const SizedBox(width: SpacingTokens.sm),
                            Text(
                              source,
                              style: TypographyTokens.caption(
                                cs.onSurface.withValues(alpha: 0.4),
                              ),
                            ),
                          ],
                          const Spacer(),
                          _ResolveButton(
                            errorId: error['id'] as int,
                            onResolved: () =>
                                ref.invalidate(_activeErrorsProvider),
                          ),
                        ],
                      ),
                      const SizedBox(height: SpacingTokens.xs),
                      Text(
                        message,
                        style: TypographyTokens.bodySmall(cs.onSurface),
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                      ),
                      if (createdAt.isNotEmpty) ...[
                        const SizedBox(height: SpacingTokens.xs),
                        Text(
                          createdAt,
                          style: TypographyTokens.caption(
                            cs.onSurface.withValues(alpha: 0.35),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(width: SpacingTokens.sm),
            ],
          ),
        ),
      ),
    );
  }
}

// ─── Inline Resolve Button ────────────────────────────────────────────────────

class _ResolveButton extends ConsumerStatefulWidget {
  final int errorId;
  final VoidCallback onResolved;
  const _ResolveButton({required this.errorId, required this.onResolved});

  @override
  ConsumerState<_ResolveButton> createState() => _ResolveButtonState();
}

class _ResolveButtonState extends ConsumerState<_ResolveButton> {
  bool _loading = false;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    if (_loading) {
      return const SizedBox(
        width: 18,
        height: 18,
        child: CircularProgressIndicator(strokeWidth: 2),
      );
    }
    return GestureDetector(
      onTap: () async {
        setState(() => _loading = true);
        try {
          final repo = ref.read(adminRepositoryProvider);
          await repo.resolveSystemError(widget.errorId);
          widget.onResolved();
        } catch (_) {
          if (mounted) setState(() => _loading = false);
        }
      },
      child: Container(
        padding: const EdgeInsets.symmetric(
          horizontal: SpacingTokens.sm,
          vertical: 4,
        ),
        decoration: BoxDecoration(
          color: cs.primaryContainer.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(SpacingTokens.radiusFull),
        ),
        child: Text(
          'تم الحل',
          style: TypographyTokens.caption(
            cs.primary,
          ).copyWith(fontWeight: FontWeight.w600),
        ),
      ),
    );
  }
}
