import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/repositories/admin_repository.dart';
import 'package:trading_app/core/services/parsing_service.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/app_section_label.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/status_badge.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/demo_real_banner.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/widgets/error_state.dart';

Future<Map<String, dynamic>> _safeStatus(AdminRepository repo) async {
  try { return await repo.getBackgroundStatus(); } catch (_) { return {}; }
}
Future<Map<String, dynamic>> _safeSettings(AdminRepository repo) async {
  try { return await repo.getBackgroundSettings(); } catch (_) { return {}; }
}
Future<({List<Map<String, dynamic>> entries, int total})> _safeLogs(AdminRepository repo) async {
  try { return await repo.getBackgroundLogs(page: 1, perPage: 20); } catch (_) { return (entries: <Map<String, dynamic>>[], total: 0); }
}

final _backgroundStatusProvider = FutureProvider.autoDispose
    .family<Map<String, dynamic>, bool>((ref, _) async {
  final repo = ref.read(adminRepositoryProvider);
  final results = await Future.wait(<Future<Map<String, dynamic>>>[
    _safeStatus(repo),
    _safeSettings(repo),
  ]);
  final logs = await _safeLogs(repo);
  return {
    'status': results[0],
    'settings': results[1],
    'logs': logs.entries,
    'logsTotal': logs.total,
  };
});

class AdminBackgroundControlScreen extends ConsumerWidget {
  const AdminBackgroundControlScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final dataAsync = ref.watch(_backgroundStatusProvider(true));

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            children: [
              AppScreenHeader(title: 'التحكم بالخلفية', showBack: true),
              const DemoRealBanner(),
              Expanded(
                child: RefreshIndicator(
                  color: cs.primary,
                  onRefresh: () async {
                    ref.invalidate(_backgroundStatusProvider);
                  },
                  child: dataAsync.when(
                    loading: () => ListView(
                      padding: const EdgeInsets.all(SpacingTokens.base),
                      children: const [
                        LoadingShimmer(itemCount: 4, itemHeight: 80),
                      ],
                    ),
                    error: (e, _) => ErrorState(
                      message: e.toString(),
                      onRetry: () => ref.invalidate(_backgroundStatusProvider),
                    ),
                    data: (all) {
                      final status = ParsingService.asMap(all['status']);
                      final settings = ParsingService.asMap(all['settings']);
                      final logs = all['logs'] is List<Map<String, dynamic>>
                          ? all['logs'] as List<Map<String, dynamic>>
                          : <Map<String, dynamic>>[];
                      return ListView(
                        padding: const EdgeInsets.all(SpacingTokens.base),
                        children: [
                          _buildStatusCard(context, cs, status, ref),
                          const SizedBox(height: SpacingTokens.lg),
                          _buildControlsSection(context, cs, status, ref),
                          const SizedBox(height: SpacingTokens.lg),
                          _buildSettingsSection(cs, settings),
                          const SizedBox(height: SpacingTokens.lg),
                          _buildLogsSection(context, cs, logs),
                          const SizedBox(height: SpacingTokens.xl),
                        ],
                      );
                    },
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStatusCard(
    BuildContext context,
    ColorScheme cs,
    Map<String, dynamic> status,
    WidgetRef ref,
  ) {
    final running = status['running'] == true || status['status'] == 'running';
    final stateLabel = running ? 'يعمل' : 'متوقف';
    final uptime = status['uptime'] ?? '-';
    final lastCycle = status['last_cycle'] ?? status['last_run'] ?? '-';
    final cycleCount = ParsingService.asInt(status['cycle_count'] ?? 0);
    final errors = ParsingService.asInt(status['error_count'] ?? status['errors'] ?? 0);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionLabel(text: 'حالة المحرك الخلفي'),
        const SizedBox(height: SpacingTokens.sm),
        AppCard(
          padding: const EdgeInsets.all(SpacingTokens.md),
          child: Column(
            children: [
              Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      color: (running ? cs.primary : cs.error).withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
                    ),
                    child: Icon(
                      running ? Icons.settings_backup_restore : Icons.stop_circle,
                      color: running ? cs.primary : cs.error,
                      size: 28,
                    ),
                  ),
                  const SizedBox(width: SpacingTokens.md),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(stateLabel, style: TypographyTokens.h3(cs.onSurface)),
                        Text('مدة التشغيل: $uptime', style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.5))),
                      ],
                    ),
                  ),
                  StatusBadge(
                    text: running ? 'نشط' : 'متوقف',
                    type: running ? BadgeType.success : BadgeType.error,
                  ),
                ],
              ),
              const Divider(height: SpacingTokens.lg),
              Row(
                children: [
                  _miniStat(cs, 'الدورات', '$cycleCount'),
                  _miniStat(cs, 'أخطاء', '$errors'),
                  _miniStat(cs, 'آخر دورة', lastCycle.toString()),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _miniStat(ColorScheme cs, String label, String value) {
    return Expanded(
      child: Column(
        children: [
          Text(value, style: TypographyTokens.h3(cs.onSurface)),
          const SizedBox(height: SpacingTokens.xxs),
          Text(label, style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.5))),
        ],
      ),
    );
  }

  Widget _buildControlsSection(
    BuildContext context,
    ColorScheme cs,
    Map<String, dynamic> status,
    WidgetRef ref,
  ) {
    final running = status['running'] == true || status['status'] == 'running';
    final loading = ref.watch(_actionLoadingProvider);

    Future<void> action(String key, Future<Map<String, dynamic>> Function(AdminRepository) fn) async {
      ref.read(_actionLoadingProvider.notifier).state = key;
      try {
        await fn(ref.read(adminRepositoryProvider));
        ref.invalidate(_backgroundStatusProvider);
        if (context.mounted) AppSnackbar.show(context, message: 'تم بنجاح', type: SnackType.success);
      } catch (e) {
        if (context.mounted) AppSnackbar.show(context, message: e.toString(), type: SnackType.error);
      } finally {
        ref.read(_actionLoadingProvider.notifier).state = null;
      }
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionLabel(text: 'التحكم'),
        const SizedBox(height: SpacingTokens.sm),
        Row(
          children: [
            Expanded(
              child: _controlButton(
                cs: cs,
                icon: Icons.play_arrow,
                label: 'تشغيل',
                color: cs.primary,
                enabled: !running,
                loading: loading == 'start',
                onTap: () => action('start', (r) => r.startBackground()),
              ),
            ),
            const SizedBox(width: SpacingTokens.sm),
            Expanded(
              child: _controlButton(
                cs: cs,
                icon: Icons.stop,
                label: 'إيقاف',
                color: SemanticColors.of(context).warning,
                enabled: running,
                loading: loading == 'stop',
                onTap: () => action('stop', (r) => r.stopBackground()),
              ),
            ),
          ],
        ),
        const SizedBox(height: SpacingTokens.sm),
        _controlButton(
          cs: cs,
          icon: Icons.emergency,
          label: 'إيقاف طارئ',
          color: cs.error,
          enabled: running,
          loading: loading == 'emergency',
          onTap: () => action('emergency', (r) => r.emergencyStopBackground()),
          fullWidth: true,
        ),
      ],
    );
  }

  Widget _controlButton({
    required ColorScheme cs,
    required IconData icon,
    required String label,
    required Color color,
    required bool enabled,
    required bool loading,
    required VoidCallback onTap,
    bool fullWidth = false,
  }) {
    final child = AppButton(
      label: label,
      variant: AppButtonVariant.secondary,
      icon: icon,
      isFullWidth: fullWidth,
      isLoading: loading,
      onPressed: enabled && !loading ? onTap : null,
    );

    return child;
  }

  Widget _buildSettingsSection(ColorScheme cs, Map<String, dynamic> settings) {
    final interval = settings['cycle_interval'] ?? settings['interval'] ?? 60;
    final maxPositions = settings['max_positions'] ?? '-';
    final mode = settings['mode'] ?? 'auto';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionLabel(text: 'إعدادات الخلفية'),
        const SizedBox(height: SpacingTokens.sm),
        AppCard(
          padding: const EdgeInsets.all(SpacingTokens.md),
          child: Column(
            children: [
              _infoRow(cs, 'دورة المسح', '${interval}s'),
              _infoRow(cs, 'الحد الأقصى للصفقات', '$maxPositions'),
              _infoRow(cs, 'الوضع', mode.toString()),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildLogsSection(BuildContext context, ColorScheme cs, List<Map<String, dynamic>> logs) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionLabel(text: 'آخر السجلات'),
        const SizedBox(height: SpacingTokens.sm),
        if (logs.isEmpty)
          AppCard(
            padding: const EdgeInsets.all(SpacingTokens.md),
            child: Text('لا توجد سجلات', style: TypographyTokens.bodySmall(cs.onSurface.withValues(alpha: 0.4))),
          )
        else
          ...logs.take(10).map((entry) {
            final msg = entry['message'] ?? entry['event'] ?? '';
            final ts = entry['timestamp'] ?? '';
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
                      width: 8,
                      height: 8,
                      decoration: BoxDecoration(color: levelColor, shape: BoxShape.circle),
                    ),
                    const SizedBox(width: SpacingTokens.sm),
                    Expanded(
                      child: Text(msg.toString(), style: TypographyTokens.caption(cs.onSurface), maxLines: 2, overflow: TextOverflow.ellipsis),
                    ),
                    const SizedBox(width: SpacingTokens.sm),
                    Text(ts.toString(), style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.3))),
                  ],
                ),
              ),
            );
          }),
      ],
    );
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

final _actionLoadingProvider = StateProvider<String?>((ref) => null);
