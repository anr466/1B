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
import 'package:trading_app/design/widgets/app_info_row.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/app_section_label.dart';
import 'package:trading_app/design/widgets/error_state.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/status_badge.dart';

/// Trading Control Screen — التحكم بالتداول (تشغيل/إيقاف/طوارئ/ML)
final _tradingControlActionBusyProvider = StateProvider.autoDispose<bool>(
  (ref) => false,
);

class TradingControlScreen extends ConsumerWidget {
  const TradingControlScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cs = Theme.of(context).colorScheme;
    final statusAsync = ref.watch(tradingCycleLiveProvider);
    final mlStatus = ref.watch(mlStatusProvider);
    final isActionBusy = ref.watch(_tradingControlActionBusyProvider);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            children: [
              AppScreenHeader(title: 'التحكم بالتداول', showBack: true),
              Expanded(
                child: RefreshIndicator(
                  color: cs.primary,
                  onRefresh: () async {
                    await ref.read(tradingCycleLiveProvider.notifier).refresh();
                    ref.invalidate(systemStatusProvider);
                    ref.invalidate(mlStatusProvider);
                  },
                  child: ListView(
                    padding: const EdgeInsets.all(SpacingTokens.base),
                    children: [
                      // ─── System Status ─────────────────────
                      statusAsync.when(
                        loading: () =>
                            const LoadingShimmer(itemCount: 1, itemHeight: 120),
                        error: (e, _) => ErrorState(
                          message: e.toString(),
                          onRetry: () {
                            ref.invalidate(tradingCycleLiveProvider);
                            ref.invalidate(systemStatusProvider);
                          },
                        ),
                        data: (s) =>
                            _statusSection(context, ref, cs, s, isActionBusy),
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

                      const SizedBox(height: SpacingTokens.lg),

                      const AppSectionLabel(text: 'الحساب التجريبي'),
                      const SizedBox(height: SpacingTokens.sm),
                      _demoResetSection(context, ref, cs, isActionBusy),

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

  Widget _statusSection(
    BuildContext context,
    WidgetRef ref,
    ColorScheme cs,
    dynamic s,
    bool isActionBusy,
  ) {
    final rawState = s.state.toString().toUpperCase();
    final isStarting = rawState == 'STARTING';
    final isStopping = rawState == 'STOPPING';
    final isTransitioning = isStarting || isStopping;
    final isBusy = isActionBusy || isTransitioning;

    final isRunning = rawState == 'RUNNING';
    final isStopped = rawState == 'STOPPED';
    final isError = rawState == 'ERROR' || rawState == 'ERROR_STOPPED';
    final effectivelyRunning = s.isEffectivelyRunning == true;

    final badgeType = effectivelyRunning
        ? BadgeType.success
        : isRunning
        ? BadgeType.warning
        : isError
        ? BadgeType.error
        : BadgeType.warning;

    final stateLabel = effectivelyRunning
        ? 'يعمل'
        : isRunning
        ? 'جارٍ التفعيل...'
        : isError
        ? 'خطأ'
        : 'متوقف';

    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.base),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                effectivelyRunning
                    ? Icons.check_circle
                    : isError
                    ? Icons.error
                    : Icons.warning,
                size: 24,
                color: effectivelyRunning
                    ? cs.primary
                    : isError
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

          AppInfoRow(
            label: 'الوضع',
            value: s.tradingMode == 'real' ? 'حقيقي' : 'تجريبي',
          ),
          AppInfoRow(label: 'الحالة', value: s.state),
          AppInfoRow(
            label: 'التحقق التشغيلي',
            value: s.runtimeVerificationLabel.toString(),
          ),
          if (s.errorCount > 0)
            AppInfoRow(label: 'عدد الأخطاء', value: '${s.errorCount}'),
          if (s.lastError != null)
            AppInfoRow(label: 'آخر خطأ', value: s.lastError!),

          const SizedBox(height: SpacingTokens.lg),

          // ─── Action Buttons ────────────────────
          Row(
            children: [
              Expanded(
                child: AppButton(
                  label: isTransitioning
                      ? 'جارٍ التنفيذ...'
                      : (isRunning ? 'إيقاف' : 'تشغيل'),
                  variant: isRunning
                      ? AppButtonVariant.outline
                      : AppButtonVariant.primary,
                  height: 44,
                  onPressed: isBusy
                      ? null
                      : () => _toggleTrading(context, ref, isRunning),
                ),
              ),
              const SizedBox(width: SpacingTokens.sm),
              Expanded(
                child: AppButton(
                  label: 'إيقاف طوارئ',
                  variant: AppButtonVariant.danger,
                  height: 44,
                  onPressed: (isStopped || isBusy)
                      ? null
                      : () => _emergencyStop(context, ref),
                ),
              ),
            ],
          ),
          if (isError) ...[
            const SizedBox(height: SpacingTokens.sm),
            AppButton(
              label: 'إعادة تعيين الخطأ',
              variant: AppButtonVariant.outline,
              isFullWidth: true,
              height: 44,
              onPressed: isBusy ? null : () => _resetError(context, ref),
            ),
          ],
        ],
      ),
    );
  }

  Widget _demoResetSection(
    BuildContext context,
    WidgetRef ref,
    ColorScheme cs,
    bool isActionBusy,
  ) {
    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.base),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              BrandIcon(BrandIcons.refresh, size: 20, color: cs.tertiary),
              const SizedBox(width: SpacingTokens.sm),
              Text(
                'إعادة ضبط الحساب التجريبي',
                style: TypographyTokens.body(
                  cs.onSurface,
                ).copyWith(fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.xs),
          Text(
            'تصفير جميع الصفقات والأرصدة والسجلات التجريبية. لا يؤثر على الحساب الحقيقي أبداً.',
            style: TypographyTokens.caption(
              cs.onSurface.withValues(alpha: 0.55),
            ),
          ),
          const SizedBox(height: SpacingTokens.md),
          AppButton(
            label: 'إعادة ضبط الحساب التجريبي',
            variant: AppButtonVariant.outline,
            isFullWidth: true,
            height: 44,
            onPressed: isActionBusy
                ? null
                : () => _resetDemoAccount(context, ref),
          ),
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
      padding: const EdgeInsets.all(SpacingTokens.base),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              BrandIcon(BrandIcons.chart, size: 20, color: cs.primary),
              const SizedBox(width: SpacingTokens.sm),
              Text('نموذج ML', style: TypographyTokens.body(cs.onSurface)),
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
          AppInfoRow(label: 'الحالة', value: statusText),
          AppInfoRow(
            label: 'الجاهزية',
            value: isReady ? 'جاهز للتصفية' : 'قيد التدريب',
          ),
          AppInfoRow(
            label: 'التقدم',
            value: '${progressPct.toStringAsFixed(1)}%',
          ),
          AppInfoRow(
            label: 'البيانات',
            value: '${totalSamples.toInt()} / ${requiredSamples.toInt()}',
          ),
          AppInfoRow(
            label: 'الدقة',
            value: '${(accuracy * 100).toStringAsFixed(1)}%',
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
    if (ref.read(_tradingControlActionBusyProvider)) return;

    // ✅ Confirmation dialog for Start/Stop trading
    if (!context.mounted) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          title: Text(isRunning ? 'إيقاف التداول' : 'تشغيل التداول'),
          content: Text(
            isRunning
                ? 'سيتوقف النظام عن فتح صفقات جديدة. الصفقات المفتوحة ستستمر.'
                : 'سيبدأ النظام في فتح صفقات جديدة تلقائياً.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('إلغاء'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: Text(isRunning ? 'إيقاف' : 'تشغيل'),
            ),
          ],
        ),
      ),
    );
    if (confirmed != true) return;

    ref.read(_tradingControlActionBusyProvider.notifier).state = true;

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
        ref.read(_tradingControlActionBusyProvider.notifier).state = false;
        return;
      }
    }
    try {
      final repo = ref.read(adminRepositoryProvider);
      final result = isRunning
          ? await repo.stopTrading()
          : await repo.startTrading();

      // ✅ FIX: Check success AND valid response (not just state matching)
      final success = result['success'] == true;
      final state =
          (result['trading_state'] ??
                  result['state'] ??
                  result['data']?['trading_state'] ??
                  result['data']?['state'] ??
                  '')
              .toString()
              .toUpperCase();

      // ✅ For stop: accept STOPPED, STOPPING, or success flag
      // ✅ For start: accept RUNNING, STARTING, or success flag
      final applied = isRunning
          ? (state == 'STOPPED' || state == 'STOPPING' || success)
          : (state == 'RUNNING' || state == 'STARTING' || success);

      if (!context.mounted) return;
      ref.read(tradingCycleLiveProvider.notifier).refresh();
      ref.invalidate(systemStatusProvider);
      ref.invalidate(mlStatusProvider);
      ref.invalidate(accountTradingProvider);
      ref.invalidate(portfolioProvider);
      ref.invalidate(statsProvider);
      ref.invalidate(activePositionsProvider);
      ref.invalidate(recentTradesProvider);
      ref.invalidate(dailyStatusProvider);
      if (!context.mounted) return;

      final backendMessage =
          (result['message'] ?? result['data']?['message'] ?? '').toString();

      // Show success if either the API returned success OR we have a valid state
      AppSnackbar.show(
        context,
        message: (success || applied)
            ? (backendMessage.isNotEmpty ? backendMessage : UxMessages.success)
            : (backendMessage.isNotEmpty ? backendMessage : UxMessages.error),
        type: (success || applied) ? SnackType.success : SnackType.error,
      );
    } catch (e) {
      // Even if API call failed, verify actual state
      final mounted = context.mounted;
      if (!mounted) return;
      try {
        final repo = ref.read(adminRepositoryProvider);
        final actualState = await repo.getTradingState();
        final actualRunning =
            actualState.isEffectivelyRunning || actualState.isRunning;

        // Check if operation actually succeeded despite exception
        final operationSucceeded = isRunning ? !actualRunning : actualRunning;
        if (mounted && operationSucceeded) {
          ref.read(tradingCycleLiveProvider.notifier).refresh();
          ref.invalidate(systemStatusProvider);
          AppSnackbar.show(
            context,
            message: isRunning ? 'تم إيقاف التداول' : 'تم تشغيل التداول',
            type: SnackType.success,
          );
          return;
        }
      } catch (_) {}

      // Show detailed error message from repository
      if (mounted) {
        AppSnackbar.show(
          context,
          message: 'تعذر الاتصال بالخادم. تحقق من الاتصال بالإنترنت.',
          type: SnackType.error,
        );
      }
    } finally {
      ref.read(_tradingControlActionBusyProvider.notifier).state = false;
    }
  }

  Future<void> _emergencyStop(BuildContext context, WidgetRef ref) async {
    if (ref.read(_tradingControlActionBusyProvider)) return;
    ref.read(_tradingControlActionBusyProvider.notifier).state = true;

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
        ref.read(_tradingControlActionBusyProvider.notifier).state = false;
        return;
      }
    }
    if (!context.mounted) {
      ref.read(_tradingControlActionBusyProvider.notifier).state = false;
      return;
    }
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

    if (confirmed != true || !context.mounted) {
      ref.read(_tradingControlActionBusyProvider.notifier).state = false;
      return;
    }

    try {
      final repo = ref.read(adminRepositoryProvider);
      final result = await repo.emergencyStop();

      // ✅ FIX: More flexible success check
      final success = result['success'] == true;
      final state =
          (result['trading_state'] ??
                  result['state'] ??
                  result['data']?['trading_state'] ??
                  '')
              .toString()
              .toUpperCase();
      final applied =
          success ||
          state == 'STOPPED' ||
          state == 'STOPPING' ||
          state == 'ERROR';

      ref.read(tradingCycleLiveProvider.notifier).refresh();
      ref.invalidate(systemStatusProvider);
      ref.invalidate(accountTradingProvider);
      ref.invalidate(portfolioProvider);
      ref.invalidate(statsProvider);
      ref.invalidate(activePositionsProvider);
      ref.invalidate(recentTradesProvider);
      ref.invalidate(dailyStatusProvider);
      if (!context.mounted) return;
      final backendMessage =
          (result['message'] ??
                  result['error'] ??
                  result['data']?['message'] ??
                  '')
              .toString();
      AppSnackbar.show(
        context,
        message: applied
            ? (backendMessage.isNotEmpty
                  ? backendMessage
                  : 'تم الإيقاف الطارئ بنجاح')
            : (backendMessage.isNotEmpty ? backendMessage : UxMessages.error),
        type: applied ? SnackType.warning : SnackType.error,
      );
    } catch (e) {
      // Even if API call failed, verify actual state
      final mounted = context.mounted;
      if (!mounted) return;
      try {
        final repo = ref.read(adminRepositoryProvider);
        final actualState = await repo.getTradingState();
        if (mounted &&
            !actualState.isEffectivelyRunning &&
            !actualState.isRunning) {
          ref.read(tradingCycleLiveProvider.notifier).refresh();
          ref.invalidate(systemStatusProvider);
          AppSnackbar.show(
            context,
            message: 'تم الإيقاف الطارئ بنجاح',
            type: SnackType.warning,
          );
          return;
        }
      } catch (_) {}

      if (mounted) {
        AppSnackbar.show(
          context,
          message: 'تعذر الاتصال بالخادم. تحقق من الاتصال بالإنترنت.',
          type: SnackType.error,
        );
      }
    } finally {
      ref.read(_tradingControlActionBusyProvider.notifier).state = false;
    }
  }

  Future<void> _resetDemoAccount(BuildContext context, WidgetRef ref) async {
    if (ref.read(_tradingControlActionBusyProvider)) return;
    ref.read(_tradingControlActionBusyProvider.notifier).state = true;

    if (!context.mounted) {
      ref.read(_tradingControlActionBusyProvider.notifier).state = false;
      return;
    }
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          title: Text(
            'إعادة ضبط الحساب التجريبي',
            style: TypographyTokens.h3(Theme.of(context).colorScheme.onSurface),
          ),
          content: const Text(
            'سيتم حذف جميع الصفقات التجريبية وإعادة ضبط الرصيد التجريبي إلى الوضع الافتراضي. لا يؤثر على الحساب الحقيقي. هل أنت متأكد؟',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('إلغاء'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: Text(
                'إعادة الضبط',
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
          ],
        ),
      ),
    );

    if (confirmed != true || !context.mounted) {
      ref.read(_tradingControlActionBusyProvider.notifier).state = false;
      return;
    }

    try {
      final repo = ref.read(adminRepositoryProvider);
      final result = await repo.resetDemo();
      ref.invalidate(mlStatusProvider);
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
        message: result['success'] == true
            ? (backendMessage.isNotEmpty
                  ? backendMessage
                  : 'تمت إعادة ضبط الحساب التجريبي بنجاح')
            : (backendMessage.isNotEmpty ? backendMessage : UxMessages.error),
        type: result['success'] == true ? SnackType.success : SnackType.error,
      );
    } catch (e) {
      if (!context.mounted) return;
      AppSnackbar.show(
        context,
        message: UxMessages.error,
        type: SnackType.error,
      );
    } finally {
      ref.read(_tradingControlActionBusyProvider.notifier).state = false;
    }
  }

  Future<void> _resetError(BuildContext context, WidgetRef ref) async {
    if (ref.read(_tradingControlActionBusyProvider)) return;
    ref.read(_tradingControlActionBusyProvider.notifier).state = true;

    try {
      final repo = ref.read(adminRepositoryProvider);
      final result = await repo.resetError();

      // ✅ FIX: More flexible success check
      final success = result['success'] == true;
      final state =
          (result['trading_state'] ??
                  result['state'] ??
                  result['data']?['trading_state'] ??
                  '')
              .toString()
              .toUpperCase();
      final applied =
          success ||
          state == 'STOPPED' ||
          state == 'RUNNING' ||
          state == 'ERROR';

      ref.read(tradingCycleLiveProvider.notifier).refresh();
      ref.invalidate(systemStatusProvider);
      ref.invalidate(mlStatusProvider);
      ref.invalidate(accountTradingProvider);
      ref.invalidate(portfolioProvider);
      ref.invalidate(statsProvider);
      ref.invalidate(activePositionsProvider);
      ref.invalidate(recentTradesProvider);
      ref.invalidate(tradesListProvider);
      ref.invalidate(dailyStatusProvider);
      if (!context.mounted) return;
      final backendMessage =
          (result['message'] ??
                  result['error'] ??
                  result['data']?['message'] ??
                  '')
              .toString();
      AppSnackbar.show(
        context,
        message: applied
            ? (backendMessage.isNotEmpty
                  ? backendMessage
                  : 'تم إعادة تعيين الخطأ بنجاح')
            : (backendMessage.isNotEmpty ? backendMessage : UxMessages.error),
        type: applied ? SnackType.success : SnackType.error,
      );
    } catch (e) {
      // Even if API call failed, verify actual state
      final mounted = context.mounted;
      if (!mounted) return;
      try {
        final repo = ref.read(adminRepositoryProvider);
        final actualState = await repo.getTradingState();
        if (mounted && !actualState.isError) {
          ref.read(tradingCycleLiveProvider.notifier).refresh();
          ref.invalidate(systemStatusProvider);
          AppSnackbar.show(
            context,
            message: 'تم إعادة تعيين الخطأ بنجاح',
            type: SnackType.success,
          );
          return;
        }
      } catch (_) {}

      if (mounted) {
        AppSnackbar.show(
          context,
          message: 'تعذر الاتصال بالخادم. تحقق من الاتصال بالإنترنت.',
          type: SnackType.error,
        );
      }
    } finally {
      ref.read(_tradingControlActionBusyProvider.notifier).state = false;
    }
  }
}
