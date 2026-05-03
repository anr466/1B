import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/services/parsing_service.dart';
import 'package:trading_app/design/icons/brand_icons.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/app_section_label.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/status_badge.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/demo_real_banner.dart';

Future<Map<String, dynamic>> _safeGet(Future<Map<String, dynamic>> Function() fn) async {
  try { return await fn(); } catch (_) { return {}; }
}

final _mlDataProvider = FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
  final repo = ref.read(adminRepositoryProvider);
  final results = await Future.wait(<Future<Map<String, dynamic>>>[
    _safeGet(() => repo.getMlStatus()),
    _safeGet(() => repo.getMlBacktestStatus()),
    _safeGet(() => repo.getMlReliability()),
    _safeGet(() => repo.getMlProgress()),
    _safeGet(() => repo.getMlQualityMetrics()),
    _safeGet(() => repo.getAdminNotificationSettings()),
  ]);
  return {
    'status': results[0],
    'backtest': results[1],
    'reliability': results[2],
    'progress': results[3],
    'quality': results[4],
    'notifications': results[5],
  };
});

class AdminMLDashboardScreen extends ConsumerWidget {
  const AdminMLDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final mlAsync = ref.watch(_mlDataProvider);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            children: [
              AppScreenHeader(title: 'لوحة ML', showBack: true),
              const DemoRealBanner(),
              Expanded(
                child: RefreshIndicator(
                  color: cs.primary,
                  onRefresh: () async {
                    ref.invalidate(_mlDataProvider);
                  },
                  child: mlAsync.when(
                    loading: () => _buildLoadingSection(cs),
                    error: (e, _) => _buildErrorSection(cs, e.toString(), () {
                      ref.invalidate(_mlDataProvider);
                    }),
                    data: (all) => ListView(
                      padding: const EdgeInsets.all(SpacingTokens.base),
                      children: [
                        _buildStatusSection(context, cs, ParsingService.asMap(all['status'])),
                        const SizedBox(height: SpacingTokens.lg),
                        _buildProgressSection(cs, ParsingService.asMap(all['progress'])),
                        const SizedBox(height: SpacingTokens.lg),
                        _buildMetricsGrid(context, cs, ParsingService.asMap(all['quality'])),
                        const SizedBox(height: SpacingTokens.lg),
                        _buildBacktestSection(cs, ParsingService.asMap(all['backtest'])),
                        const SizedBox(height: SpacingTokens.lg),
                        _buildReliabilitySection(cs, ParsingService.asMap(all['reliability'])),
                        const SizedBox(height: SpacingTokens.lg),
                        _buildNotificationSettings(context, cs, ParsingService.asMap(all['notifications'])),
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

  Widget _buildLoadingSection(ColorScheme cs) {
    return ListView(
      padding: const EdgeInsets.all(SpacingTokens.base),
      children: const [
        LoadingShimmer(itemCount: 6, itemHeight: 100),
      ],
    );
  }

  Widget _buildErrorSection(ColorScheme cs, String message, VoidCallback onRetry) {
    return ListView(
      padding: const EdgeInsets.all(SpacingTokens.base),
      children: [
        AppCard(
          backgroundColor: cs.error.withValues(alpha: 0.08),
          padding: const EdgeInsets.all(SpacingTokens.lg),
          child: Column(
            children: [
              Icon(Icons.error_outline, color: cs.error, size: 48),
              const SizedBox(height: SpacingTokens.md),
              Text(message, style: TypographyTokens.body(cs.error), textAlign: TextAlign.center),
              const SizedBox(height: SpacingTokens.md),
              AppButton(
                label: 'إعادة المحاولة',
                variant: AppButtonVariant.text,
                isFullWidth: false,
                icon: Icons.refresh,
                onPressed: onRetry,
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildStatusSection(BuildContext context, ColorScheme cs, Map<String, dynamic> data) {
    final active = data['active'] == true || data['status'] == 'active';
    final modelName = data['model'] ?? data['model_name'] ?? 'غير معروف';
    final version = data['version'] ?? '-';
    final lastUpdate = data['last_update'] ?? data['updated_at'] ?? '-';

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionLabel(text: 'حالة نظام ML'),
        const SizedBox(height: SpacingTokens.sm),
        AppCard(
          padding: const EdgeInsets.all(SpacingTokens.md),
          child: Column(
            children: [
              Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: (active ? cs.primary : cs.error).withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
                    ),
                    child: Icon(
                      Icons.memory,
                      color: active ? cs.primary : cs.error,
                      size: 22,
                    ),
                  ),
                  const SizedBox(width: SpacingTokens.md),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(modelName.toString(), style: TypographyTokens.h3(cs.onSurface)),
                        Text('v$version', style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.5))),
                      ],
                    ),
                  ),
                  StatusBadge(
                    text: active ? 'نشط' : 'غير نشط',
                    type: active ? BadgeType.success : BadgeType.error,
                  ),
                ],
              ),
              if (data['learning_mode'] != null) ...[
                const SizedBox(height: SpacingTokens.sm),
                _infoRow(cs, 'وضع التعلم', data['learning_mode'].toString()),
              ],
              if (data['phase'] != null) ...[
                const SizedBox(height: SpacingTokens.xxs),
                _infoRow(cs, 'المرحلة', data['phase'].toString()),
              ],
              _infoRow(cs, 'آخر تحديث', lastUpdate.toString()),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildProgressSection(ColorScheme cs, Map<String, dynamic> data) {
    final trainingProgress = ParsingService.asDouble(data['training_progress'] ?? data['progress'] ?? 0);
    final realTrades = ParsingService.asInt(data['real_trades'] ?? 0);
    final phaseBacktest = ParsingService.asDouble(data['phase_backtest_weight'] ?? 0);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionLabel(text: 'تقدم التدريب'),
        const SizedBox(height: SpacingTokens.sm),
        AppCard(
          padding: const EdgeInsets.all(SpacingTokens.md),
          child: Column(
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text('التقدم', style: TypographyTokens.bodySmall(cs.onSurface)),
                  Text('${(trainingProgress * 100).toStringAsFixed(1)}%', style: TypographyTokens.h3(cs.primary)),
                ],
              ),
              const SizedBox(height: SpacingTokens.xs),
              ClipRRect(
                borderRadius: BorderRadius.circular(SpacingTokens.radiusSm),
                child: LinearProgressIndicator(
                  value: trainingProgress.clamp(0.0, 1.0),
                  backgroundColor: cs.onSurface.withValues(alpha: 0.08),
                  minHeight: 8,
                ),
              ),
              const SizedBox(height: SpacingTokens.sm),
              _infoRow(cs, 'صفقات حقيقية', '$realTrades'),
              _infoRow(cs, 'وزن الباك تست', '${(phaseBacktest * 100).toStringAsFixed(0)}%'),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildMetricsGrid(BuildContext context, ColorScheme cs, Map<String, dynamic> data) {
    final precision = ParsingService.asDouble(data['precision'] ?? 0);
    final recall = ParsingService.asDouble(data['recall'] ?? 0);
    final f1 = ParsingService.asDouble(data['f1_score'] ?? 0);
    final accuracy = ParsingService.asDouble(data['accuracy'] ?? 0);
    final totalPredictions = ParsingService.asInt(data['total_predictions'] ?? 0);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionLabel(text: 'مقاييس الجودة'),
        const SizedBox(height: SpacingTokens.sm),
        Row(
          children: [
            Expanded(
              child: _metricCard(context, 'الدقة', '${(precision * 100).toStringAsFixed(1)}%', BrandIcons.chart),
            ),
            const SizedBox(width: SpacingTokens.sm),
            Expanded(
              child: _metricCard(context, 'الاستدعاء', '${(recall * 100).toStringAsFixed(1)}%', BrandIcons.search),
            ),
          ],
        ),
        const SizedBox(height: SpacingTokens.sm),
        Row(
          children: [
            Expanded(
              child: _metricCard(context, 'F1 Score', '${(f1 * 100).toStringAsFixed(1)}%', BrandIcons.trophy),
            ),
            const SizedBox(width: SpacingTokens.sm),
            Expanded(
              child: _metricCard(context, 'التوقعات', '$totalPredictions', BrandIcons.history),
            ),
          ],
        ),
        if (accuracy > 0) ...[
          const SizedBox(height: SpacingTokens.sm),
          AppCard(
            padding: const EdgeInsets.all(SpacingTokens.md),
            child: _infoRow(cs, 'الدقة الإجمالية', '${(accuracy * 100).toStringAsFixed(1)}%'),
          ),
        ],
      ],
    );
  }

  Widget _metricCard(BuildContext context, String label, String value, BrandIconData icon) {
    final cs = Theme.of(context).colorScheme;
    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.md),
      child: Column(
        children: [
          BrandIcon(icon, size: 18, color: cs.primary),
          const SizedBox(height: SpacingTokens.xs),
          Text(value, style: TypographyTokens.h3(cs.onSurface)),
          const SizedBox(height: SpacingTokens.xxs),
          Text(label, style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.5))),
        ],
      ),
    );
  }

  Widget _buildBacktestSection(ColorScheme cs, Map<String, dynamic> data) {
    final running = data['running'] == true;
    final progress = ParsingService.asDouble(data['progress'] ?? 0);
    final totalTrades = ParsingService.asInt(data['total_trades'] ?? 0);
    final winRate = ParsingService.asDouble(data['win_rate'] ?? 0);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionLabel(text: 'حالة الباك تست'),
        const SizedBox(height: SpacingTokens.sm),
        AppCard(
          padding: const EdgeInsets.all(SpacingTokens.md),
          child: Column(
            children: [
              Row(
                children: [
                  StatusBadge(
                    text: running ? 'يعمل' : 'متوقف',
                    type: running ? BadgeType.success : BadgeType.info,
                  ),
                  const Spacer(),
                  if (running)
                    Text('${(progress * 100).toStringAsFixed(1)}%', style: TypographyTokens.body(cs.primary)),
                ],
              ),
              if (running) ...[
                const SizedBox(height: SpacingTokens.xs),
                ClipRRect(
                  borderRadius: BorderRadius.circular(SpacingTokens.radiusSm),
                  child: LinearProgressIndicator(
                    value: progress.clamp(0.0, 1.0),
                    backgroundColor: cs.onSurface.withValues(alpha: 0.08),
                    minHeight: 6,
                  ),
                ),
              ],
              const SizedBox(height: SpacingTokens.sm),
              _infoRow(cs, 'صفقات', '$totalTrades'),
              _infoRow(cs, 'نسبة الربح', '${(winRate * 100).toStringAsFixed(1)}%'),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildReliabilitySection(ColorScheme cs, Map<String, dynamic> data) {
    final score = ParsingService.asDouble(data['score'] ?? data['reliability'] ?? 0);
    final confidence = ParsingService.asDouble(data['confidence'] ?? 0);
    final stable = data['stable'] == true;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionLabel(text: 'موثوقية النظام'),
        const SizedBox(height: SpacingTokens.sm),
        AppCard(
          padding: const EdgeInsets.all(SpacingTokens.md),
          child: Column(
            children: [
              Row(
                children: [
                  Text('مؤشر الموثوقية', style: TypographyTokens.bodySmall(cs.onSurface)),
                  const Spacer(),
                  Text('${(score * 100).toStringAsFixed(1)}%', style: TypographyTokens.h3(cs.primary)),
                ],
              ),
              const SizedBox(height: SpacingTokens.xs),
              ClipRRect(
                borderRadius: BorderRadius.circular(SpacingTokens.radiusSm),
                child: LinearProgressIndicator(
                  value: score.clamp(0.0, 1.0),
                  backgroundColor: cs.onSurface.withValues(alpha: 0.08),
                  color: score >= 0.7 ? cs.primary : (score >= 0.4 ? Colors.orange : cs.error),
                  minHeight: 8,
                ),
              ),
              const SizedBox(height: SpacingTokens.sm),
              _infoRow(cs, 'مستوى الثقة', '${(confidence * 100).toStringAsFixed(1)}%'),
              _infoRow(cs, 'حالة الاستقرار', stable ? 'مستقر' : 'متغير'),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildNotificationSettings(BuildContext context, ColorScheme cs, Map<String, dynamic> data) {
    final enabled = data['enabled'] == true;
    final channels = data['channels'] ?? [];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const AppSectionLabel(text: 'إعدادات إشعارات ML'),
        const SizedBox(height: SpacingTokens.sm),
        AppCard(
          padding: const EdgeInsets.all(SpacingTokens.md),
          child: Column(
            children: [
              Row(
                children: [
                  Icon(
                    enabled ? Icons.notifications_active : Icons.notifications_off,
                    color: enabled ? cs.primary : cs.onSurface.withValues(alpha: 0.4),
                  ),
                  const SizedBox(width: SpacingTokens.md),
                  Expanded(
                    child: Text(
                      enabled ? 'الإشعارات مفعلة' : 'الإشعارات معطلة',
                      style: TypographyTokens.body(cs.onSurface),
                    ),
                  ),
                  StatusBadge(
                    text: enabled ? 'مفعل' : 'معطل',
                    type: enabled ? BadgeType.success : BadgeType.info,
                  ),
                ],
              ),
              if (channels is List && channels.isNotEmpty) ...[
                const SizedBox(height: SpacingTokens.sm),
                Wrap(
                  spacing: 4,
                  children: channels.map<Widget>((c) {
                    return Chip(
                      label: Text(c.toString(), style: TypographyTokens.caption(cs.primary)),
                      backgroundColor: cs.primary.withValues(alpha: 0.08),
                    );
                  }).toList(),
                ),
              ],
              if (data['ml_alerts'] != null) ...[
                const SizedBox(height: SpacingTokens.sm),
                _infoRow(cs, 'تنبيهات ML', data['ml_alerts'] == true ? 'مفعلة' : 'معطلة'),
              ],
            ],
          ),
        ),
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
