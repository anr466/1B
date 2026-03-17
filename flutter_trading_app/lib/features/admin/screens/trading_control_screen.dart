import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/constants/ux_messages.dart';
import 'package:trading_app/core/providers/admin_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/providers/trades_provider.dart';
import 'package:trading_app/design/icons/brand_icons.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/app_section_label.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/status_badge.dart';

/// Trading Control Screen — التحكم بالتداول (تشغيل/إيقاف/طوارئ/ML)
class TradingControlScreen extends ConsumerWidget {
  const TradingControlScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final status = ref.watch(systemStatusProvider);
    final mlStatus = ref.watch(mlStatusProvider);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        appBar: AppBar(
          title: Text(
            'التحكم بالتداول',
            style: TypographyTokens.h3(cs.onSurface),
          ),
        ),
        body: RefreshIndicator(
          color: cs.primary,
          onRefresh: () async {
            ref.invalidate(systemStatusProvider);
            ref.invalidate(mlStatusProvider);
          },
          child: ListView(
            padding: const EdgeInsets.all(SpacingTokens.base),
            children: [
              // ─── System Status ─────────────────────
              status.when(
                loading: () =>
                    const LoadingShimmer(itemCount: 1, itemHeight: 120),
                error: (e, _) => AppCard(
                  child: Center(
                    child: Text(
                      'خطأ: $e',
                      style: TypographyTokens.bodySmall(cs.error),
                    ),
                  ),
                ),
                data: (s) => _statusSection(context, ref, cs, s),
              ),

              const SizedBox(height: SpacingTokens.lg),

              const AppSectionLabel(text: 'نموذج الذكاء الاصطناعي'),
              const SizedBox(height: SpacingTokens.sm),
              mlStatus.when(
                loading: () =>
                    const LoadingShimmer(itemCount: 1, itemHeight: 80),
                error: (_, __) => AppCard(
                  padding: const EdgeInsets.all(SpacingTokens.md),
                  child: Text(
                    'غير متاح',
                    style: TypographyTokens.bodySmall(
                      cs.onSurface.withValues(alpha: 0.5),
                    ),
                  ),
                ),
                data: (ml) => _mlSection(cs, ml),
              ),

              const SizedBox(height: SpacingTokens.xl),
            ],
          ),
        ),
      ),
    );
  }

  Widget _statusSection(
    BuildContext context,
    WidgetRef ref,
    ColorScheme cs,
    dynamic s,
  ) {
    final effectivelyRunning = s.isEffectivelyRunning == true;
    final badgeType = effectivelyRunning
        ? BadgeType.success
        : s.isRunning
        ? BadgeType.warning
        : s.isError
        ? BadgeType.error
        : BadgeType.warning;
    final stateLabel = effectivelyRunning
        ? 'يعمل فعلياً'
        : s.isRunning
        ? 'تشغيل غير مؤكد'
        : s.isError
        ? 'خطأ'
        : 'متوقف';

    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              BrandIcon(
                effectivelyRunning
                    ? BrandIcons.checkCircle
                    : BrandIcons.warning,
                size: 24,
                color: effectivelyRunning
                    ? cs.primary
                    : s.isError
                    ? cs.error
                    : cs.tertiary,
              ),
              const SizedBox(width: SpacingTokens.md),
              Text('حالة التداول', style: TypographyTokens.h3(cs.onSurface)),
              const SizedBox(width: SpacingTokens.sm),
              StatusBadge(text: stateLabel, type: badgeType),
            ],
          ),
          const SizedBox(height: SpacingTokens.md),

          _infoRow(cs, 'الوضع', s.tradingMode == 'real' ? 'حقيقي' : 'تجريبي'),
          _infoRow(cs, 'الحالة', s.state),
          _infoRow(
            cs,
            'التحقق التشغيلي',
            s.runtimeVerificationLabel.toString(),
          ),
          if (s.errorCount > 0) _infoRow(cs, 'عدد الأخطاء', '${s.errorCount}'),
          if (s.lastError != null) _infoRow(cs, 'آخر خطأ', s.lastError!),

          const SizedBox(height: SpacingTokens.lg),

          // ─── Action Buttons ────────────────────
          Row(
            children: [
              Expanded(
                child: AppButton(
                  label: s.isRunning ? 'إيقاف' : 'تشغيل',
                  variant: s.isRunning
                      ? AppButtonVariant.outline
                      : AppButtonVariant.primary,
                  height: 44,
                  onPressed: () => _toggleTrading(context, ref, s.isRunning),
                ),
              ),
              const SizedBox(width: SpacingTokens.sm),
              Expanded(
                child: AppButton(
                  label: 'إيقاف طوارئ',
                  variant: AppButtonVariant.danger,
                  height: 44,
                  onPressed: s.isStopped
                      ? null
                      : () => _emergencyStop(context, ref),
                ),
              ),
            ],
          ),
          if (s.isError) ...[
            const SizedBox(height: SpacingTokens.sm),
            AppButton(
              label: 'إعادة تعيين الخطأ',
              variant: AppButtonVariant.outline,
              isFullWidth: true,
              height: 44,
              onPressed: () => _resetError(context, ref),
            ),
          ],
        ],
      ),
    );
  }

  Widget _mlSection(ColorScheme cs, Map<String, dynamic> ml) {
    final rawMl = ml['ml'];
    final mlData = rawMl is Map
        ? Map<String, dynamic>.from(rawMl)
        : Map<String, dynamic>.from(ml);

    final isEnabled = mlData['enabled'] == true;
    final isReady = mlData['is_ready'] == true;
    final totalSamples = (mlData['total_samples'] ?? 0) as num;
    final requiredSamples = (mlData['required_samples'] ?? 0) as num;
    final progressPct = (mlData['progress_pct'] ?? 0) as num;
    final accuracy = (mlData['accuracy'] ?? 0) as num;
    final statusText =
        mlData['status_text']?.toString() ?? (isReady ? 'جاهز' : 'قيد التجهيز');

    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              BrandIcon(BrandIcons.chart, size: 20, color: cs.primary),
              const SizedBox(width: SpacingTokens.sm),
              Text('ML Model', style: TypographyTokens.body(cs.onSurface)),
              const Spacer(),
              StatusBadge(
                text: !isEnabled ? 'غير متاح' : (isReady ? 'جاهز' : 'يتعلم'),
                type: !isEnabled
                    ? BadgeType.warning
                    : (isReady ? BadgeType.success : BadgeType.info),
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.sm),
          _infoRow(cs, 'الحالة', statusText),
          _infoRow(cs, 'الجاهزية', isReady ? 'جاهز للتصفية' : 'قيد التدريب'),
          _infoRow(cs, 'التقدم', '${progressPct.toStringAsFixed(1)}%'),
          _infoRow(
            cs,
            'البيانات',
            '${totalSamples.toInt()} / ${requiredSamples.toInt()}',
          ),
          _infoRow(cs, 'الدقة', '${(accuracy * 100).toStringAsFixed(1)}%'),
        ],
      ),
    );
  }

  Widget _infoRow(ColorScheme cs, String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: SpacingTokens.xs),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TypographyTokens.bodySmall(
              cs.onSurface.withValues(alpha: 0.5),
            ),
          ),
          Flexible(
            child: Text(
              value,
              style: TypographyTokens.mono(cs.onSurface, fontSize: 13),
              textAlign: TextAlign.end,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ],
      ),
    );
  }

  Future<void> _toggleTrading(
    BuildContext context,
    WidgetRef ref,
    bool isRunning,
  ) async {
    final bio = ref.read(biometricServiceProvider);
    if (await bio.isAvailable) {
      final label = isRunning ? 'تأكيد إيقاف التداول' : 'تأكيد تشغيل التداول';
      final ok = await bio.authenticate(reason: label);
      if (!ok) {
        if (!context.mounted) return;
        AppSnackbar.show(
          context,
          message: 'فشل التحقق من البصمة',
          type: SnackType.error,
        );
        return;
      }
    }
    try {
      final repo = ref.read(adminRepositoryProvider);
      final result = isRunning
          ? await repo.stopTrading()
          : await repo.startTrading();
      final state = (result['trading_state'] ?? result['state'] ?? '')
          .toString()
          .toUpperCase();
      final applied = isRunning
          ? (state == 'STOPPED' || state == 'STOPPING')
          : (state == 'RUNNING' || state == 'STARTING');
      if (!context.mounted) return;
      ref.invalidate(systemStatusProvider);
      ref.invalidate(tradingCycleLiveProvider);
      ref.invalidate(accountTradingProvider);
      ref.invalidate(portfolioProvider);
      ref.invalidate(statsProvider);
      ref.invalidate(activePositionsProvider);
      ref.invalidate(recentTradesProvider);
      ref.invalidate(dailyStatusProvider);
      final backendMessage = (result['message'] ?? result['error'] ?? '')
          .toString();
      AppSnackbar.show(
        context,
        message: (result['success'] == true && applied)
            ? (backendMessage.isNotEmpty ? backendMessage : UxMessages.success)
            : (backendMessage.isNotEmpty ? backendMessage : UxMessages.error),
        type: (result['success'] == true && applied)
            ? SnackType.success
            : SnackType.error,
      );
    } catch (e) {
      if (!context.mounted) return;
      AppSnackbar.show(
        context,
        message: UxMessages.error,
        type: SnackType.error,
      );
    }
  }

  Future<void> _emergencyStop(BuildContext context, WidgetRef ref) async {
    final bio = ref.read(biometricServiceProvider);
    if (await bio.isAvailable) {
      final ok = await bio.authenticate(reason: 'تأكيد إيقاف الطوارئ');
      if (!ok) {
        if (!context.mounted) return;
        AppSnackbar.show(
          context,
          message: 'فشل التحقق من البصمة',
          type: SnackType.error,
        );
        return;
      }
    }
    if (!context.mounted) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          title: Text(
            'إيقاف طوارئ',
            style: TypographyTokens.h3(Theme.of(context).colorScheme.error),
          ),
          content: const Text(
            'سيتم إيقاف جميع عمليات التداول فوراً وإغلاق جميع الصفقات المفتوحة. هل أنت متأكد؟',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('إلغاء'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: Text(
                'إيقاف طوارئ',
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          ],
        ),
      ),
    );

    if (confirmed != true || !context.mounted) return;

    try {
      final repo = ref.read(adminRepositoryProvider);
      final result = await repo.emergencyStop();
      final state = (result['trading_state'] ?? result['state'] ?? '')
          .toString()
          .toUpperCase();
      final applied = state == 'STOPPED' || state == 'ERROR';
      ref.invalidate(systemStatusProvider);
      ref.invalidate(tradingCycleLiveProvider);
      ref.invalidate(accountTradingProvider);
      ref.invalidate(portfolioProvider);
      ref.invalidate(statsProvider);
      ref.invalidate(activePositionsProvider);
      ref.invalidate(recentTradesProvider);
      ref.invalidate(dailyStatusProvider);
      if (!context.mounted) return;
      final backendMessage = (result['message'] ?? result['error'] ?? '')
          .toString();
      AppSnackbar.show(
        context,
        message: (result['success'] == true && applied)
            ? (backendMessage.isNotEmpty ? backendMessage : UxMessages.success)
            : (backendMessage.isNotEmpty ? backendMessage : UxMessages.error),
        type: (result['success'] == true && applied)
            ? SnackType.warning
            : SnackType.error,
      );
    } catch (e) {
      if (!context.mounted) return;
      AppSnackbar.show(
        context,
        message: UxMessages.error,
        type: SnackType.error,
      );
    }
  }

  Future<void> _resetError(BuildContext context, WidgetRef ref) async {
    try {
      final repo = ref.read(adminRepositoryProvider);
      final result = await repo.resetError();
      final state = (result['trading_state'] ?? result['state'] ?? '')
          .toString()
          .toUpperCase();
      final applied = state == 'STOPPED' || state == 'RUNNING';
      ref.invalidate(systemStatusProvider);
      ref.invalidate(tradingCycleLiveProvider);
      ref.invalidate(accountTradingProvider);
      ref.invalidate(portfolioProvider);
      ref.invalidate(statsProvider);
      ref.invalidate(activePositionsProvider);
      ref.invalidate(recentTradesProvider);
      ref.invalidate(dailyStatusProvider);
      if (!context.mounted) return;
      final backendMessage = (result['message'] ?? result['error'] ?? '')
          .toString();
      AppSnackbar.show(
        context,
        message: (result['success'] == true && applied)
            ? (backendMessage.isNotEmpty ? backendMessage : UxMessages.success)
            : (backendMessage.isNotEmpty ? backendMessage : UxMessages.error),
        type: (result['success'] == true && applied)
            ? SnackType.success
            : SnackType.error,
      );
    } catch (e) {
      if (!context.mounted) return;
      AppSnackbar.show(
        context,
        message: UxMessages.error,
        type: SnackType.error,
      );
    }
  }
}
