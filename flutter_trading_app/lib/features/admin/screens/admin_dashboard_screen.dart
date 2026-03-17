import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
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
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/app_section_label.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/status_badge.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Admin Dashboard Screen — لوحة تحكم المدير
class AdminDashboardScreen extends ConsumerWidget {
  const AdminDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final status = ref.watch(tradingCycleLiveProvider);
    final mlStatus = ref.watch(mlStatusProvider);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            children: [
              AppScreenHeader(title: 'لوحة الإدارة', showBack: true),
              Expanded(
                child: RefreshIndicator(
          color: cs.primary,
          onRefresh: () async {
            ref.invalidate(tradingCycleLiveProvider);
            ref.invalidate(mlStatusProvider);
          },
          child: ListView(
            padding: const EdgeInsets.all(SpacingTokens.base),
            children: [
              // ─── System Status ─────────────────────
              status.when(
                loading: () =>
                    const LoadingShimmer(itemCount: 1, itemHeight: 160),
                error: (e, _) => AppCard(
                  child: Center(
                    child: Text(
                      'خطأ: $e',
                      style: TypographyTokens.bodySmall(cs.error),
                    ),
                  ),
                ),
                data: (s) => _buildStatusCard(context, ref, cs, s),
              ),
              const SizedBox(height: SpacingTokens.base),

              // ─── ML Status ─────────────────────────
              const AppSectionLabel(text: 'نموذج الذكاء الاصطناعي'),
              const SizedBox(height: SpacingTokens.sm),
              mlStatus.when(
                loading: () =>
                    const LoadingShimmer(itemCount: 1, itemHeight: 90),
                error: (_, __) => AppCard(
                  padding: const EdgeInsets.all(SpacingTokens.md),
                  child: Text(
                    'غير متاح',
                    style: TypographyTokens.bodySmall(
                      cs.onSurface.withValues(alpha: 0.5),
                    ),
                  ),
                ),
                data: (ml) => _buildMlCard(cs, ml),
              ),

              const SizedBox(height: SpacingTokens.base),

              // ─── Quick Actions ─────────────────────
              const AppSectionLabel(text: 'إجراءات سريعة'),
              const SizedBox(height: SpacingTokens.sm),

              _actionItem(
                context,
                cs,
                BrandIcons.chart,
                'التحكم في التداول',
                RouteNames.tradingControl,
              ),

              const SizedBox(height: SpacingTokens.sm),

              _actionItem(
                context,
                cs,
                BrandIcons.history,
                'سجلات النظام',
                RouteNames.systemLogs,
              ),

              const SizedBox(height: SpacingTokens.xl),
            ],
          ),
        ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildMlCard(ColorScheme cs, Map<String, dynamic> ml) {
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
    final phaseDesc = mlData['phase_description']?.toString() ?? '';
    final backtestWeight = ((mlData['backtest_weight'] ?? 0) as num).toDouble();
    final realWeight = ((mlData['real_weight'] ?? 0) as num).toDouble();
    final progress = (progressPct / 100).clamp(0.0, 1.0).toDouble();

    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
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
          if (phaseDesc.isNotEmpty) _infoRow(cs, 'المرحلة', phaseDesc),
          _infoRow(
            cs,
            'البيانات',
            '${totalSamples.toInt()} / ${requiredSamples.toInt()}',
          ),
          if (accuracy > 0)
            _infoRow(cs, 'الدقة', '${(accuracy * 100).toStringAsFixed(1)}%'),
          const SizedBox(height: SpacingTokens.sm),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'تقدم التعلم',
                style: TypographyTokens.caption(
                  cs.onSurface.withValues(alpha: 0.55),
                ),
              ),
              Text(
                '${progressPct.toStringAsFixed(1)}%',
                style: TypographyTokens.caption(
                  cs.primary,
                ).copyWith(fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: progress,
              backgroundColor: cs.surfaceContainerHighest,
              color: isReady ? cs.primary : cs.tertiary,
              minHeight: 5,
            ),
          ),
          if (isEnabled) ...[
            const SizedBox(height: SpacingTokens.xs),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  'اختبار: ${(backtestWeight * 100).toStringAsFixed(0)}%',
                  style: TypographyTokens.caption(
                    cs.onSurface.withValues(alpha: 0.45),
                  ),
                ),
                Text(
                  'حقيقي: ${(realWeight * 100).toStringAsFixed(0)}%',
                  style: TypographyTokens.caption(
                    cs.onSurface.withValues(alpha: 0.45),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }

  Widget _statusMetricCard(
    ColorScheme cs, {
    required String title,
    required String value,
    Color? valueColor,
    Color? backgroundColor,
    Color? borderColor,
    Color? labelColor,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(
        horizontal: SpacingTokens.sm,
        vertical: SpacingTokens.sm,
      ),
      decoration: BoxDecoration(
        color:
            backgroundColor ??
            cs.surfaceContainerHighest.withValues(alpha: 0.42),
        borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
        border: Border.all(
          color: borderColor ?? cs.outline.withValues(alpha: 0.18),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TypographyTokens.caption(
              labelColor ?? cs.onSurface.withValues(alpha: 0.5),
            ),
          ),
          const SizedBox(height: 2),
          Text(
            value,
            style: TypographyTokens.bodySmall(valueColor ?? cs.onSurface),
            overflow: TextOverflow.ellipsis,
            maxLines: 1,
          ),
        ],
      ),
    );
  }

  Widget _infoRow(ColorScheme cs, String label, String value) {
    // keep
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

  Widget _buildStatusCard(
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
    final modeLabel = s.tradingMode == 'real' ? 'حقيقي' : 'تجريبي';
    final isDark = cs.brightness == Brightness.dark;
    final statusTone = switch (badgeType) {
      BadgeType.success => cs.primary,
      BadgeType.error => cs.error,
      BadgeType.warning => cs.tertiary,
      BadgeType.info => cs.secondary,
    };
    final cardStart = isDark
        ? Color.alphaBlend(
            cs.primaryContainer.withValues(alpha: 0.25),
            cs.surfaceContainerHigh,
          )
        : Color.alphaBlend(
            cs.primaryContainer.withValues(alpha: 0.15),
            cs.surface,
          );
    final cardEnd = isDark ? cs.surfaceContainerLow : cs.surfaceContainerLowest;
    final cardBorder = Color.alphaBlend(
      statusTone.withValues(alpha: isDark ? 0.30 : 0.20),
      cs.outline,
    );
    final metricBg = isDark ? cs.surfaceContainerLow : cs.surfaceContainerLow;
    final metricBorder = cs.outline.withValues(alpha: isDark ? 0.15 : 0.10);
    final metricLabelColor = cs.onSurface.withValues(alpha: 0.5);

    return AppCard(
      level: 1,
      borderColor: cardBorder,
      gradientColors: [cardStart, cardEnd],
      padding: const EdgeInsets.all(SpacingTokens.lg),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              _AnimatedPulseDot(color: statusTone),
              const SizedBox(width: SpacingTokens.sm),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('حالة النظام', style: TypographyTokens.h4(cs.onSurface)),
                  const SizedBox(height: 2),
                  Text(
                    'مراقبة التشغيل الذكي',
                    style: TypographyTokens.caption(
                      cs.onSurface.withValues(alpha: 0.4),
                    ),
                  ),
                ],
              ),
              const Spacer(),
              StatusBadge(text: stateLabel, type: badgeType),
            ],
          ),
          const SizedBox(height: SpacingTokens.base),

          Row(
            children: [
              Expanded(
                child: _statusMetricCard(
                  cs,
                  title: 'الوضع',
                  value: modeLabel,
                  valueColor: modeLabel == 'حقيقي' ? cs.error : cs.primary,
                  backgroundColor: metricBg,
                  borderColor: metricBorder,
                  labelColor: metricLabelColor,
                ),
              ),
              const SizedBox(width: SpacingTokens.sm),
              Expanded(
                child: _statusMetricCard(
                  cs,
                  title: 'مدة التشغيل',
                  value: s.uptimeLabel,
                  backgroundColor: metricBg,
                  borderColor: metricBorder,
                  labelColor: metricLabelColor,
                ),
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.sm),
          Row(
            children: [
              Expanded(
                child: _statusMetricCard(
                  cs,
                  title: 'النبضات',
                  value: '${s.heartbeatLabel} • ${s.heartbeatStatusLabel}',
                  backgroundColor: metricBg,
                  borderColor: metricBorder,
                  labelColor: metricLabelColor,
                ),
              ),
              const SizedBox(width: SpacingTokens.sm),
              Expanded(
                child: _statusMetricCard(
                  cs,
                  title: 'عدد الدورات',
                  value: '${s.totalCycles}',
                  backgroundColor: metricBg,
                  borderColor: metricBorder,
                  labelColor: metricLabelColor,
                ),
              ),
            ],
          ),

          const SizedBox(height: SpacingTokens.md),
          _CycleProgressWidget(status: s),

          const SizedBox(height: SpacingTokens.sm),
          _infoRow(
            cs,
            'التحقق التشغيلي',
            s.runtimeVerificationLabel.toString(),
          ),

          if (s.errorCount > 0) ...[
            const SizedBox(height: SpacingTokens.sm),
            Text(
              'أخطاء: ${s.errorCount}',
              style: TypographyTokens.bodySmall(cs.error),
            ),
          ],

          if ((s.lastUpdated ?? '').isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: SpacingTokens.sm),
              child: _infoRow(cs, 'آخر تحديث', s.lastUpdated.toString()),
            ),

          // ─── Trading Controls ──────────────────
          const SizedBox(height: SpacingTokens.md),
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
              if (s.isError) ...[
                const SizedBox(width: SpacingTokens.sm),
                Expanded(
                  child: AppButton(
                    label: 'إعادة تعيين',
                    variant: AppButtonVariant.secondary,
                    height: 44,
                    onPressed: () => _resetError(context, ref),
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: SpacingTokens.sm),
          Column(
            children: [
              AppButton(
                label: 'ضبط الحساب التجريبي',
                variant: AppButtonVariant.secondary,
                height: 42,
                onPressed: () => _resetDemoData(context, ref, resetMl: false),
              ),
              const SizedBox(height: SpacingTokens.sm),
              AppButton(
                label: 'إعادة ضبط التعلم',
                variant: AppButtonVariant.outline,
                height: 42,
                onPressed: () => _resetDemoData(context, ref, resetMl: true),
              ),
            ],
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
      if (result['success'] == true && applied) {
        ref.invalidate(systemStatusProvider);
        ref.invalidate(tradingCycleLiveProvider);
        ref.invalidate(accountTradingProvider);
        ref.invalidate(portfolioProvider);
        ref.invalidate(statsProvider);
        ref.invalidate(activePositionsProvider);
        ref.invalidate(recentTradesProvider);
        ref.invalidate(dailyStatusProvider);
        AppSnackbar.show(
          context,
          message: UxMessages.success,
          type: SnackType.success,
        );
      } else {
        AppSnackbar.show(
          context,
          message: UxMessages.error,
          type: SnackType.error,
        );
      }
    } catch (e) {
      if (!context.mounted) return;
      AppSnackbar.show(
        context,
        message: UxMessages.error,
        type: SnackType.error,
      );
    }
  }

  Future<void> _resetDemoData(
    BuildContext context,
    WidgetRef ref, {
    required bool resetMl,
  }) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        final cs = Theme.of(dialogContext).colorScheme;
        return Directionality(
          textDirection: TextDirection.rtl,
          child: AlertDialog(
            backgroundColor: cs.surface,
            title: Text(
              resetMl ? 'تأكيد إعادة ضبط التعلم' : 'تأكيد إعادة ضبط الحساب',
              style: TypographyTokens.h3(cs.onSurface),
            ),
            content: Text(
              resetMl
                  ? 'سيتم تصفير الحساب التجريبي ومسح بيانات التعلم ML. هل أنت متأكد؟'
                  : 'سيتم تصفير الحساب التجريبي فقط. هل تريد المتابعة؟',
              style: TypographyTokens.bodySmall(
                cs.onSurface.withValues(alpha: 0.75),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(false),
                child: Text('إلغاء', style: TextStyle(color: cs.primary)),
              ),
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(true),
                child: Text('تأكيد', style: TextStyle(color: cs.error)),
              ),
            ],
          ),
        );
      },
    );

    if (confirm != true || !context.mounted) return;

    try {
      final repo = ref.read(adminRepositoryProvider);
      final result = await repo.resetDemo(resetMl: resetMl);
      if (!context.mounted) return;
      if (result['success'] == true) {
        ref.invalidate(systemStatusProvider);
        ref.invalidate(tradingCycleLiveProvider);
        ref.invalidate(mlStatusProvider);
        ref.invalidate(portfolioProvider);
        ref.invalidate(statsProvider);
        ref.invalidate(activePositionsProvider);
        ref.invalidate(recentTradesProvider);
        ref.invalidate(dailyStatusProvider);
        AppSnackbar.show(
          context,
          message: (result['message'] ?? UxMessages.success).toString(),
          type: SnackType.success,
        );
      } else {
        AppSnackbar.show(
          context,
          message: (result['message'] ?? UxMessages.error).toString(),
          type: SnackType.error,
        );
      }
    } catch (_) {
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
      AppSnackbar.show(
        context,
        message: (result['success'] == true && applied)
            ? UxMessages.success
            : UxMessages.error,
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

  Widget _actionItem(
    BuildContext context,
    ColorScheme cs,
    BrandIconData icon,
    String label,
    String route,
  ) {
    return Padding(
      padding: const EdgeInsets.only(bottom: SpacingTokens.sm),
      child: AppCard(
        onTap: () => context.push(route),
        padding: const EdgeInsets.symmetric(
          horizontal: SpacingTokens.base,
          vertical: SpacingTokens.md,
        ),
        child: Row(
          children: [
            BrandIcon(icon, size: 20, color: cs.primary),
            const SizedBox(width: SpacingTokens.md),
            Expanded(
              child: Text(label, style: TypographyTokens.body(cs.onSurface)),
            ),
            Icon(
              Icons.chevron_left,
              color: cs.onSurface.withValues(alpha: 0.3),
              size: 20,
            ),
          ],
        ),
      ),
    );
  }
}

class _AnimatedPulseDot extends StatefulWidget {
  final Color color;
  const _AnimatedPulseDot({required this.color});

  @override
  State<_AnimatedPulseDot> createState() => _AnimatedPulseDotState();
}

class _AnimatedPulseDotState extends State<_AnimatedPulseDot>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: widget.color,
            boxShadow: [
              BoxShadow(
                color: widget.color.withValues(alpha: 0.4 * _controller.value),
                blurRadius: 8 * _controller.value,
                spreadRadius: 2 * _controller.value,
              ),
            ],
          ),
        );
      },
    );
  }
}

// ─────────────────────────────────────────────────────────────────
/// Trading Cycle Progress — يتحرك بشكل متزامن مع دورة التداول الخلفية
/// يستخدم Timer.periodic لتحريك المراحل كل 8 ثوانٍ أثناء التشغيل
/// ويرصد groupBSecondsAgo لإعادة المزامنة عند كل دورة جديدة
// ─────────────────────────────────────────────────────────────────
class _CycleProgressWidget extends StatefulWidget {
  final dynamic status;
  const _CycleProgressWidget({required this.status});

  @override
  State<_CycleProgressWidget> createState() => _CycleProgressState();
}

class _CycleProgressState extends State<_CycleProgressWidget> {
  static const _stepLabels = ['الاتصال', 'المسح', 'التحليل', 'التنفيذ'];
  static const _stepCount = 4;
  // Approximate duration per backend scan phase (seconds)
  static const _tickSeconds = 8;

  Timer? _timer;
  int _animStep = -1;
  int _lastTotalCycles = 0;

  @override
  void initState() {
    super.initState();
    _initStep();
    _startTimer();
  }

  @override
  void didUpdateWidget(_CycleProgressWidget old) {
    super.didUpdateWidget(old);

    final s = widget.status;
    final isRunning = s.isRunning as bool? ?? false;
    final wasRunning = old.status.isRunning as bool? ?? false;
    final totalCycles = s.totalCycles as int? ?? 0;
    final activeTrades = s.activePositions as int? ?? 0;

    // System started/stopped
    if (isRunning != wasRunning) {
      if (isRunning) {
        _initStep();
        _startTimer();
      } else {
        _timer?.cancel();
        setState(() => _animStep = -1);
      }
      return;
    }

    // New backend cycle completed — reset to scan phase
    if (totalCycles != _lastTotalCycles) {
      _lastTotalCycles = totalCycles;
      if (isRunning) setState(() => _animStep = 1);
      return;
    }

    // Active trade opened/closed — snap to execution phase
    if (activeTrades > 0 && _animStep != 3) {
      setState(() => _animStep = 3);
    } else if (activeTrades == 0 && _animStep == 3) {
      setState(() => _animStep = 1);
    }
  }

  void _initStep() {
    final s = widget.status;
    final isRunning = s.isRunning as bool? ?? false;
    final isConnected = s.binanceConnected as bool? ?? true;
    final totalCycles = s.totalCycles as int? ?? 0;
    final activeTrades = s.activePositions as int? ?? 0;
    final gbSecondsAgo = s.groupBSecondsAgo as int? ?? -1;

    _lastTotalCycles = totalCycles;

    if (!isRunning) {
      _animStep = -1;
    } else if (!isConnected) {
      _animStep = 0;
    } else if (activeTrades > 0) {
      _animStep = 3;
    } else if (totalCycles == 0) {
      _animStep = 1;
    } else {
      // Infer phase from time elapsed since last cycle
      // Backend cycle ≈ 60s: 0-15s → scan (1), 15-45s → analyze (2), 45+s → next scan
      final ago = gbSecondsAgo < 0 ? 0 : gbSecondsAgo;
      if (ago < 15) {
        _animStep = 3; // just finished, execution just completed
      } else if (ago < 40) {
        _animStep = 2; // mid-cycle, analyzing
      } else {
        _animStep = 1; // cycle nearly done or restarting, scanning
      }
    }
  }

  void _startTimer() {
    _timer?.cancel();
    final isRunning = widget.status.isRunning as bool? ?? false;
    if (!isRunning) return;

    _timer = Timer.periodic(const Duration(seconds: _tickSeconds), (_) {
      if (!mounted) return;
      final s = widget.status;
      final activeTrades = s.activePositions as int? ?? 0;
      final isConnected = s.binanceConnected as bool? ?? true;

      if (!(s.isRunning as bool? ?? false)) return;

      setState(() {
        if (activeTrades > 0) {
          _animStep = 3; // snap to execution when trade is open
        } else if (!isConnected) {
          _animStep = 0;
        } else {
          // Advance: 1 → 2 → 3 → 1 → 2 → ...
          // Skip 0 (connection) after initial connect
          final next = _animStep >= 3 ? 1 : (_animStep < 1 ? 1 : _animStep + 1);
          _animStep = next;
        }
      });
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final activeColor = cs.primary;
    final inactiveColor = cs.onSurface.withValues(alpha: 0.15);
    final activeTextColor = cs.primary;
    final inactiveTextColor = cs.onSurface.withValues(alpha: 0.35);
    final totalCycles = widget.status.totalCycles as int? ?? 0;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'مراحل دورة التداول',
          style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.5)),
        ),
        const SizedBox(height: SpacingTokens.sm),

        // ── Stepper ──────────────────────────────
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            for (int i = 0; i < _stepCount; i++) ...[
              if (i > 0)
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.only(bottom: 22, top: 13),
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 500),
                      height: 2,
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(1),
                        color: (_animStep >= 0 && i <= _animStep)
                            ? activeColor
                            : inactiveColor,
                      ),
                    ),
                  ),
                ),
              Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  AnimatedContainer(
                    duration: const Duration(milliseconds: 400),
                    width: 28,
                    height: 28,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: (_animStep >= 0 && i <= _animStep)
                          ? activeColor
                          : cs.surfaceContainerHighest,
                      border: Border.all(
                        color: (_animStep >= 0 && i <= _animStep)
                            ? activeColor
                            : inactiveColor,
                        width: 1.5,
                      ),
                    ),
                    child: Center(
                      child: (_animStep >= 0 && i < _animStep)
                          ? Icon(
                              Icons.check_rounded,
                              size: 14,
                              color: cs.onPrimary,
                            )
                          : Text(
                              '${i + 1}',
                              style: TextStyle(
                                fontSize: 11,
                                fontWeight: FontWeight.bold,
                                color: (_animStep >= 0 && i == _animStep)
                                    ? cs.onPrimary
                                    : inactiveTextColor,
                              ),
                            ),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _stepLabels[i],
                    style: TypographyTokens.caption(
                      (_animStep >= 0 && i <= _animStep)
                          ? activeTextColor
                          : inactiveTextColor,
                    ),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ],
          ],
        ),

        const SizedBox(height: SpacingTokens.sm),

        // ── Animated Progress Bar ────────────────
        ClipRRect(
          borderRadius: BorderRadius.circular(SpacingTokens.radiusFull),
          child: TweenAnimationBuilder<double>(
            tween: Tween<double>(
              begin: 0,
              end: _animStep < 0 ? 0.0 : (_animStep + 1) / _stepCount,
            ),
            duration: const Duration(milliseconds: 600),
            curve: Curves.easeInOut,
            builder: (_, value, __) => LinearProgressIndicator(
              value: value,
              backgroundColor: inactiveColor,
              color: activeColor,
              minHeight: 4,
            ),
          ),
        ),

        const SizedBox(height: 4),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            AnimatedSwitcher(
              duration: const Duration(milliseconds: 300),
              child: Text(
                key: ValueKey(_animStep),
                _animStep < 0 ? 'متوقف' : _stepLabels[_animStep],
                style: TypographyTokens.caption(
                  _animStep < 0 ? inactiveTextColor : activeColor,
                ),
              ),
            ),
            Text(
              'دورات: $totalCycles',
              style: TypographyTokens.caption(
                cs.onSurface.withValues(alpha: 0.5),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
