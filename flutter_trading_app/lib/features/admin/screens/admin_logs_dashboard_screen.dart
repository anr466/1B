import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/repositories/admin_repository.dart';
import 'package:trading_app/core/services/parsing_service.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/app_section_label.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/demo_real_banner.dart';
import 'package:trading_app/navigation/route_names.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';

Future<Map<String, dynamic>> _safeLogsStats(AdminRepository repo) async {
  try { return await repo.getLogsStatistics(); } catch (_) { return {}; }
}
Future<Map<String, dynamic>> _safeRetention(AdminRepository repo) async {
  try { return await repo.getLogsRetentionPolicy(); } catch (_) { return {}; }
}

final _logsStatsProvider = FutureProvider.autoDispose<
    ({Map<String, dynamic> stats, Map<String, dynamic> retention})>((ref) async {
  final repo = ref.read(adminRepositoryProvider);
  final results = await Future.wait(<Future<Map<String, dynamic>>>[
    _safeLogsStats(repo),
    _safeRetention(repo),
  ]);
  return (
    stats: ParsingService.asMap(results[0]),
    retention: ParsingService.asMap(results[1]),
  );
});

final _activityLogsProvider = FutureProvider.autoDispose
    .family<({List<Map<String, dynamic>> logs, int total}), int>((ref, page) {
  return ref.read(adminRepositoryProvider).getActivityLogs(page: page, perPage: 100);
});

final _auditLogsProvider = FutureProvider.autoDispose
    .family<({List<Map<String, dynamic>> logs, int total}), int>((ref, page) {
  return ref.read(adminRepositoryProvider).getSecurityAuditLog(page: page, perPage: 100);
});

final _systemErrorsProvider = FutureProvider.autoDispose
    .family<({List<Map<String, dynamic>> errors, int total, Map<String, dynamic> stats}), int>((ref, page) {
  return ref.read(adminRepositoryProvider).getSystemErrors(page: page, perPage: 100);
});

class AdminLogsDashboardScreen extends ConsumerStatefulWidget {
  const AdminLogsDashboardScreen({super.key});

  @override
  ConsumerState<AdminLogsDashboardScreen> createState() =>
      _AdminLogsDashboardScreenState();
}

class _AdminLogsDashboardScreenState
    extends ConsumerState<AdminLogsDashboardScreen> {
  int _selectedTab = 0;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            children: [
              AppScreenHeader(title: 'لوحة السجلات', showBack: true),
              const DemoRealBanner(),
              _buildTabBar(cs),
              Expanded(
                child: IndexedStack(
                  index: _selectedTab,
                  children: const [
                    _ActivityLogsTab(),
                    _AuditLogsTab(),
                    _SystemErrorsTab(),
                    _LogsManagementTab(),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTabBar(ColorScheme cs) {
    final tabs = const ['النشاط', 'التدقيق', 'الأخطاء', 'الإدارة'];
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: SpacingTokens.base),
      decoration: BoxDecoration(
        color: cs.onSurface.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
      ),
      child: Row(
        children: List.generate(tabs.length, (i) {
          final selected = _selectedTab == i;
          return Expanded(
            child: GestureDetector(
              onTap: () => setState(() => _selectedTab = i),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: SpacingTokens.sm),
                decoration: BoxDecoration(
                  color: selected ? cs.primary : Colors.transparent,
                  borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
                ),
                child: Text(
                  tabs[i],
                  textAlign: TextAlign.center,
                  style: TypographyTokens.bodySmall(
                    selected ? cs.onPrimary : cs.onSurface.withValues(alpha: 0.5),
                  ),
                ),
              ),
            ),
          );
        }),
      ),
    );
  }
}

class _ActivityLogsTab extends ConsumerWidget {
  const _ActivityLogsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final asyncData = ref.watch(_activityLogsProvider(1));

    return asyncData.when(
      loading: () => ListView(
        padding: const EdgeInsets.all(SpacingTokens.base),
        children: const [LoadingShimmer(itemCount: 6, itemHeight: 60)],
      ),
      error: (e, _) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, color: cs.error, size: 48),
            const SizedBox(height: SpacingTokens.md),
            Text(e.toString(), style: TypographyTokens.body(cs.error)),
            const SizedBox(height: SpacingTokens.md),
            AppButton(
              label: 'إعادة',
              variant: AppButtonVariant.text,
              isFullWidth: false,
              onPressed: () => ref.invalidate(_activityLogsProvider),
            ),
          ],
        ),
      ),
      data: (data) => RefreshIndicator(
        color: cs.primary,
        onRefresh: () async => ref.invalidate(_activityLogsProvider),
        child: ListView.builder(
          padding: const EdgeInsets.all(SpacingTokens.base),
          itemCount: data.logs.length,
          itemBuilder: (_, i) {
            final entry = data.logs[i];
            final level = entry['level'] ?? 'info';
            final levelColor = level == 'error'
                ? cs.error
                : level == 'warning'
                    ? SemanticColors.of(context).warning
                    : cs.primary;
            return Padding(
              padding: const EdgeInsets.only(bottom: SpacingTokens.xs),
              child: AppCard(
                padding: const EdgeInsets.all(SpacingTokens.sm),
                child: Row(
                  children: [
                    Container(
                      width: 8, height: 8,
                      decoration: BoxDecoration(color: levelColor, shape: BoxShape.circle),
                    ),
                    const SizedBox(width: SpacingTokens.sm),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            entry['message'] ?? '',
                            style: TypographyTokens.caption(cs.onSurface),
                            maxLines: 2, overflow: TextOverflow.ellipsis,
                          ),
                          Text(
                            entry['timestamp'] ?? '',
                            style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.3)),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _AuditLogsTab extends ConsumerWidget {
  const _AuditLogsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final asyncData = ref.watch(_auditLogsProvider(1));

    return asyncData.when(
      loading: () => ListView(
        padding: const EdgeInsets.all(SpacingTokens.base),
        children: const [LoadingShimmer(itemCount: 6, itemHeight: 60)],
      ),
      error: (e, _) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.shield_outlined, color: cs.error, size: 48),
            const SizedBox(height: SpacingTokens.md),
            Text(e.toString(), style: TypographyTokens.body(cs.error)),
            const SizedBox(height: SpacingTokens.md),
            AppButton(
              label: 'إعادة',
              variant: AppButtonVariant.text,
              isFullWidth: false,
              onPressed: () => ref.invalidate(_auditLogsProvider),
            ),
          ],
        ),
      ),
      data: (data) => RefreshIndicator(
        color: cs.primary,
        onRefresh: () async => ref.invalidate(_auditLogsProvider),
        child: ListView.builder(
          padding: const EdgeInsets.all(SpacingTokens.base),
          itemCount: data.logs.length,
          itemBuilder: (_, i) {
            final entry = data.logs[i];
            return Padding(
              padding: const EdgeInsets.only(bottom: SpacingTokens.xs),
              child: AppCard(
                padding: const EdgeInsets.all(SpacingTokens.sm),
                child: Row(
                  children: [
                    Icon(Icons.security, size: 16, color: cs.primary),
                    const SizedBox(width: SpacingTokens.sm),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            entry['action'] ?? entry['message'] ?? '',
                            style: TypographyTokens.caption(cs.onSurface),
                            maxLines: 2, overflow: TextOverflow.ellipsis,
                          ),
                          Text(
                            '${entry['user'] ?? ''} — ${entry['timestamp'] ?? ''}',
                            style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.3)),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            );
          },
        ),
      ),
    );
  }
}

class _SystemErrorsTab extends ConsumerWidget {
  const _SystemErrorsTab();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final asyncData = ref.watch(_systemErrorsProvider(1));

    return asyncData.when(
      loading: () => ListView(
        padding: const EdgeInsets.all(SpacingTokens.base),
        children: const [LoadingShimmer(itemCount: 6, itemHeight: 60)],
      ),
      error: (e, _) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.bug_report_outlined, color: cs.error, size: 48),
            const SizedBox(height: SpacingTokens.md),
            Text(e.toString(), style: TypographyTokens.body(cs.error)),
            const SizedBox(height: SpacingTokens.md),
            AppButton(
              label: 'إعادة',
              variant: AppButtonVariant.text,
              isFullWidth: false,
              onPressed: () => ref.invalidate(_systemErrorsProvider),
            ),
          ],
        ),
      ),
      data: (data) => RefreshIndicator(
        color: cs.primary,
        onRefresh: () async => ref.invalidate(_systemErrorsProvider),
        child: ListView(
          padding: const EdgeInsets.all(SpacingTokens.base),
          children: [
            Row(
              children: [
                _statChip(cs, 'الكل', '${data.total}', cs.primary),
                const SizedBox(width: SpacingTokens.sm),
                _statChip(cs, 'حرجة', '${data.stats['critical'] ?? 0}', cs.error),
                const SizedBox(width: SpacingTokens.sm),
                _statChip(cs, 'محلولة', '${data.stats['resolved'] ?? 0}', SemanticColors.of(context).positive),
              ],
            ),
            const SizedBox(height: SpacingTokens.sm),
            ...data.errors.map((e) {
              final severity = e['severity'] ?? 'info';
              final sevColor = severity == 'critical' ? cs.error : SemanticColors.of(context).warning;
              return Padding(
                padding: const EdgeInsets.only(bottom: SpacingTokens.xs),
                child: AppCard(
                  padding: const EdgeInsets.all(SpacingTokens.sm),
                  onTap: () {
                    context.push(RouteNames.errorDetails, extra: int.tryParse(e['id']?.toString() ?? '') ?? 0);
                  },
                  child: Row(
                    children: [
                      Container(width: 4, height: 40, decoration: BoxDecoration(
                        color: sevColor,
                        borderRadius: BorderRadius.circular(SpacingTokens.xxs),
                      )),
                      const SizedBox(width: SpacingTokens.sm),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(e['message'] ?? '', style: TypographyTokens.caption(cs.onSurface),
                              maxLines: 2, overflow: TextOverflow.ellipsis,
                            ),
                            Text('${e['source'] ?? ''} — ${e['created_at'] ?? ''}',
                              style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.3)),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }),
          ],
        ),
      ),
    );
  }

  Widget _statChip(ColorScheme cs, String label, String value, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: SpacingTokens.sm, vertical: SpacingTokens.xxs),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(SpacingTokens.radiusSm),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(value, style: TypographyTokens.caption(color)),
          const SizedBox(width: 4),
          Text(label, style: TypographyTokens.caption(color.withValues(alpha: 0.6))),
        ],
      ),
    );
  }
}

class _LogsManagementTab extends ConsumerStatefulWidget {
  const _LogsManagementTab();

  @override
  ConsumerState<_LogsManagementTab> createState() => _LogsManagementTabState();
}

class _LogsManagementTabState extends ConsumerState<_LogsManagementTab> {
  bool _isCleaning = false;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final statsAsync = ref.watch(_logsStatsProvider);

    return statsAsync.when(
      loading: () => ListView(
        padding: const EdgeInsets.all(SpacingTokens.base),
        children: const [LoadingShimmer(itemCount: 4, itemHeight: 80)],
      ),
      error: (e, _) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.error_outline, color: cs.error, size: 48),
            const SizedBox(height: SpacingTokens.md),
            Text(e.toString(), style: TypographyTokens.body(cs.error)),
            const SizedBox(height: SpacingTokens.md),
            AppButton(
              label: 'إعادة',
              variant: AppButtonVariant.text,
              isFullWidth: false,
              onPressed: () => ref.invalidate(_logsStatsProvider),
            ),
          ],
        ),
      ),
      data: (data) {
        final stats = data.stats;
        final retention = data.retention;
        return ListView(
          padding: const EdgeInsets.all(SpacingTokens.base),
          children: [
            _buildStatCard(context, cs, stats),
            const SizedBox(height: SpacingTokens.lg),
            _buildRetentionSection(context, cs, retention, ref),
            const SizedBox(height: SpacingTokens.lg),
            _buildCleanupSection(context, cs, ref),
          ],
        );
      },
    );
  }

  Widget _buildStatCard(BuildContext context, ColorScheme cs, Map<String, dynamic> stats) {
    final total = stats['total_logs'] ?? stats['total'] ?? '-';
    final errors = stats['error_count'] ?? stats['errors'] ?? '-';
    final size = stats['total_size'] ?? stats['size'] ?? '-';
    final oldest = stats['oldest_entry'] ?? stats['oldest'] ?? '-';
    final newest = stats['newest_entry'] ?? stats['newest'] ?? '-';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionLabel(text: 'إحصائيات السجلات'),
        const SizedBox(height: SpacingTokens.sm),
        AppCard(
          padding: const EdgeInsets.all(SpacingTokens.md),
          child: Column(
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      children: [
                        Text('$total', style: TypographyTokens.h2(cs.primary)),
                        Text('إجمالي السجلات', style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.5))),
                      ],
                    ),
                  ),
                  Expanded(
                    child: Column(
                      children: [
                        Text('$errors', style: TypographyTokens.h2(cs.error)),
                        Text('أخطاء', style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.5))),
                      ],
                    ),
                  ),
                  Expanded(
                    child: Column(
                      children: [
                        Text('$size', style: TypographyTokens.h2(cs.onSurface)),
                        Text('الحجم', style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.5))),
                      ],
                    ),
                  ),
                ],
              ),
              const Divider(height: SpacingTokens.lg),
              _infoRow(cs, 'أقدم سجل', oldest.toString()),
              _infoRow(cs, 'أحدث سجل', newest.toString()),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildRetentionSection(
    BuildContext context,
    ColorScheme cs,
    Map<String, dynamic> retention,
    WidgetRef ref,
  ) {
    final days = retention['days'] ?? retention['retention_days'] ?? 90;
    final enabled = retention['enabled'] != false;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionLabel(text: 'سياسة الاحتفاظ'),
        const SizedBox(height: SpacingTokens.sm),
        AppCard(
          padding: const EdgeInsets.all(SpacingTokens.md),
          child: Column(
            children: [
              _infoRow(cs, 'مدة الاحتفاظ', '$days يوم'),
              _infoRow(cs, 'الحالة', enabled ? 'مفعلة' : 'معطلة'),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildCleanupSection(BuildContext context, ColorScheme cs, WidgetRef ref) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionLabel(text: 'تنظيف السجلات'),
        const SizedBox(height: SpacingTokens.sm),
        AppCard(
          padding: const EdgeInsets.all(SpacingTokens.md),
          child: Column(
            children: [
              ListTile(
                leading: _isCleaning
                    ? const SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Icon(Icons.auto_delete, color: cs.primary),
                title: Text('حذف السجلات القديمة', style: TypographyTokens.body(cs.onSurface)),
                subtitle: Text('حذف السجلات الأقدم من 30 يوم', style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.5))),
                trailing: _isCleaning ? null : const Icon(Icons.chevron_left),
                onTap: _isCleaning ? null : () => _confirmCleanOldLogs(context, cs, ref),
              ),
              const Divider(),
              ListTile(
                leading: _isCleaning
                    ? const SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Icon(Icons.copy_all, color: SemanticColors.of(context).warning),
                title: Text('حذف المكرر', style: TypographyTokens.body(cs.onSurface)),
                subtitle: Text('إزالة السجلات المكررة', style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.5))),
                trailing: _isCleaning ? null : const Icon(Icons.chevron_left),
                onTap: _isCleaning ? null : () => _action(ref, 'تم حذف المكرر', (r) => r.cleanDuplicateLogs()),
              ),
              const Divider(),
              ListTile(
                leading: _isCleaning
                    ? const SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : Icon(Icons.delete_forever, color: cs.error),
                title: Text('مسح جميع السجلات', style: TypographyTokens.body(cs.onSurface)),
                subtitle: Text('حذف كافة السجلات بشكل دائم', style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.5))),
                trailing: _isCleaning ? null : const Icon(Icons.chevron_left),
                onTap: _isCleaning ? null : () => showDialog(
                  context: context,
                  builder: (ctx) => AlertDialog(
                    title: const Text('تأكيد'),
                    content: const Text('هل أنت متأكد من مسح جميع السجلات؟'),
                    actions: [
                      AppButton(
                        label: 'إلغاء',
                        variant: AppButtonVariant.text,
                        isFullWidth: false,
                        onPressed: () => Navigator.pop(ctx),
                      ),
                      AppButton(
                        label: 'مسح',
                        variant: AppButtonVariant.danger,
                        isFullWidth: false,
                        onPressed: () {
                          Navigator.pop(ctx);
                          _action(ref, 'تم مسح جميع السجلات', (r) => r.clearAllLogs());
                        },
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Future<void> _confirmCleanOldLogs(BuildContext context, ColorScheme cs, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('تأكيد'),
        content: const Text('هل أنت متأكد من حذف السجلات الأقدم من 30 يوم؟'),
        actions: [
          AppButton(
            label: 'إلغاء',
            variant: AppButtonVariant.text,
            isFullWidth: false,
            onPressed: () => Navigator.pop(ctx, false),
          ),
          AppButton(
            label: 'حذف',
            variant: AppButtonVariant.danger,
            isFullWidth: false,
            onPressed: () => Navigator.pop(ctx, true),
          ),
        ],
      ),
    );
    if (confirmed == true) {
      _action(ref, 'تم حذف السجلات القديمة', (r) => r.cleanOldLogs(olderThanDays: 30));
    }
  }

  Future<void> _action(
    WidgetRef ref,
    String successMsg,
    Future<Map<String, dynamic>> Function(AdminRepository) fn,
  ) async {
    setState(() => _isCleaning = true);
    try {
      await fn(ref.read(adminRepositoryProvider));
      ref.invalidate(_logsStatsProvider);
      if (mounted) {
        AppSnackbar.show(context, message: successMsg, type: SnackType.success);
        setState(() => _isCleaning = false);
      }
    } catch (e) {
      if (mounted) {
        AppSnackbar.show(context, message: e.toString(), type: SnackType.error);
        setState(() => _isCleaning = false);
      }
    }
  }

  Widget _infoRow(ColorScheme cs, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: SpacingTokens.xxs),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.5))),
          Text(value, style: TypographyTokens.bodySmall(cs.onSurface)),
        ],
      ),
    );
  }
}
