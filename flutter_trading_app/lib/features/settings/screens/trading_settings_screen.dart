import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/constants/ux_messages.dart';
import 'package:trading_app/core/providers/admin_provider.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/trades_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/providers/settings_provider.dart';
import 'package:trading_app/core/services/trading_toggle_service.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/error_state.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';
import 'package:trading_app/design/widgets/app_screen_header.dart';
import 'package:trading_app/design/widgets/app_button.dart';

/// Trading Settings Screen — إعدادات التداول (sliders + save)
class TradingSettingsScreen extends ConsumerStatefulWidget {
  const TradingSettingsScreen({super.key});

  @override
  ConsumerState<TradingSettingsScreen> createState() =>
      _TradingSettingsScreenState();
}

class _TradingSettingsScreenState extends ConsumerState<TradingSettingsScreen> {
  bool _isSwitchingMode = false;
  bool _saving = false;
  bool _saveSuccess = false;
  Timer? _debounce;
  Timer? _saveIndicatorTimer;

  double _positionSizePct = 10.0;
  bool _initialized = false;
  double _stopLossPct = 2.0;
  double _takeProfitPct = 5.0;
  double _maxDailyLossPct = 10.0;

  @override
  void dispose() {
    _debounce?.cancel();
    _saveIndicatorTimer?.cancel();
    super.dispose();
  }

  void _debouncedUpdate(int userId, Map<String, dynamic> fields) {
    _debounce?.cancel();
    setState(() {
      _saving = true;
      _saveSuccess = false;
    });
    _debounce = Timer(const Duration(milliseconds: 500), () async {
      try {
        final repo = ref.read(settingsRepositoryProvider);
        await repo.updateSettings(userId, fields);
        if (mounted) {
          setState(() {
            _saving = false;
            _saveSuccess = true;
          });
          _saveIndicatorTimer?.cancel();
          _saveIndicatorTimer = Timer(const Duration(seconds: 2), () {
            if (mounted) setState(() => _saveSuccess = false);
          });
        }
      } catch (_) {
        if (mounted) setState(() => _saving = false);
      }
    });
  }

  Future<void> _changeTradingMode(String mode) async {
    final cs = Theme.of(context).colorScheme;
    final isDemo = mode == 'demo';

    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          backgroundColor: cs.surfaceContainerHighest,
          title: Text(
            isDemo ? 'التبديل للتجريبي' : 'التبديل للحقيقي',
            style: TypographyTokens.h3(cs.onSurface),
          ),
          content: Text(
            isDemo
                ? 'سيتم عرض بيانات المحفظة التجريبية. هل تريد المتابعة؟'
                : 'سيتم عرض بيانات المحفظة الحقيقية. تأكد من وجود مفاتيح Binance. هل تريد المتابعة؟',
            style: TypographyTokens.body(cs.onSurface.withValues(alpha: 0.7)),
          ),
          actions: [
            AppButton(
              label: 'إلغاء',
              variant: AppButtonVariant.text,
              isFullWidth: false,
              onPressed: () => Navigator.of(ctx).pop(false),
            ),
            AppButton(
              label: 'تبديل',
              variant: AppButtonVariant.primary,
              isFullWidth: false,
              onPressed: () => Navigator.of(ctx).pop(true),
            ),
          ],
        ),
      ),
    );

    if (confirmed != true) return;

    setState(() => _isSwitchingMode = true);
    try {
      final repo = ref.read(settingsRepositoryProvider);
      final auth = ref.read(authProvider);
      if (auth.user == null) return;

      final result = await repo.updateTradingMode(auth.user!.id, mode);
      if (!mounted) return;
      if (result['success'] == true) {
        ref.read(adminPortfolioModeProvider.notifier).state = mode;
        ref.invalidate(portfolioProvider);
        ref.invalidate(statsProvider);
        ref.invalidate(activePositionsProvider);
        ref.invalidate(dailyStatusProvider);
        AppSnackbar.show(
          context,
          message: UxMessages.success,
          type: SnackType.success,
        );
      } else {
        AppSnackbar.show(
          context,
          message: UxMessages.modeSwitchError,
          type: SnackType.error,
        );
      }
    } catch (e) {
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message: UxMessages.networkError,
        type: SnackType.error,
      );
    } finally {
      if (mounted) setState(() => _isSwitchingMode = false);
    }
  }

  Future<void> _onTradingToggle(bool v) async {
    final cs = Theme.of(context).colorScheme;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => Directionality(
        textDirection: TextDirection.rtl,
        child: AlertDialog(
          backgroundColor: cs.surfaceContainerHighest,
          title: Text(
            v ? 'تفعيل التداول' : 'إيقاف التداول',
            style: TypographyTokens.h3(cs.onSurface),
          ),
          content: Text(
            v
                ? 'سيبدأ النظام بفتح صفقات جديدة تلقائياً. هل تريد المتابعة؟'
                : 'لن يفتح النظام صفقات جديدة. الصفقات المفتوحة ستُدار حتى الإغلاق. هل تريد المتابعة؟',
            style: TypographyTokens.body(cs.onSurface.withValues(alpha: 0.7)),
          ),
          actions: [
            AppButton(
              label: 'إلغاء',
              variant: AppButtonVariant.text,
              isFullWidth: false,
              onPressed: () => Navigator.of(ctx).pop(false),
            ),
            AppButton(
              label: v ? 'تفعيل' : 'إيقاف',
              variant: v ? AppButtonVariant.primary : AppButtonVariant.danger,
              isFullWidth: false,
              onPressed: () => Navigator.of(ctx).pop(true),
            ),
          ],
        ),
      ),
    );

    if (confirmed != true) return;

    final service = ref.read(tradingToggleServiceProvider);
    await service.toggleSelf(
      enabled: v,
      biometricAuth: (reason) =>
          ref.read(biometricServiceProvider).authenticate(reason: reason),
      showMessage: (message, type) {
        final snackType = switch (type) {
          'success' => SnackType.success,
          'error' => SnackType.error,
          'warning' => SnackType.warning,
          _ => SnackType.info,
        };
        AppSnackbar.show(context, message: message, type: snackType);
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final auth = ref.watch(authProvider);
    final settingsAsync = ref.watch(settingsDataProvider);

    return Directionality(
      textDirection: TextDirection.rtl,
      child: Scaffold(
        backgroundColor: cs.surface,
        body: SafeArea(
          child: Column(
            children: [
              AppScreenHeader(title: 'إعدادات التداول', showBack: true),
              Expanded(
                child: settingsAsync.when(
                  loading: () => const Padding(
                    padding: EdgeInsets.all(SpacingTokens.base),
                    child: LoadingShimmer(itemCount: 4, itemHeight: 80),
                  ),
                  error: (e, _) => ErrorState(
                    message: e.toString(),
                    onRetry: () => ref.invalidate(settingsDataProvider),
                  ),
                  data: (s) {
                    if (!_initialized) {
                      _initialized = true;
                      _positionSizePct =
                          s.positionSizePct > 0 ? s.positionSizePct : 10.0;
                      _stopLossPct = s.stopLossPct > 0 ? s.stopLossPct : 2.0;
                      _takeProfitPct =
                          s.takeProfitPct > 0 ? s.takeProfitPct : 5.0;
                      _maxDailyLossPct =
                          s.maxDailyLossPct > 0 ? s.maxDailyLossPct : 10.0;
                    }
                    return ListView(
                      padding: const EdgeInsets.all(SpacingTokens.base),
                      children: [
                        if (auth.isAdmin) ...[
                          _PortfolioModeSwitcher(
                            currentMode: s.activePortfolio,
                            hasBinanceKeys: s.hasBinanceKeys,
                            hasConfiguredDbKeys: s.hasConfiguredDbKeys,
                            keysRequiredForCurrentMode:
                                s.keysRequiredForCurrentMode,
                            isLoading: _isSwitchingMode,
                            onModeSelected: (mode) => _changeTradingMode(mode),
                          ),
                          const SizedBox(height: SpacingTokens.md),
                        ],
                        // ──────────────────────────────────────────────────────────────
                        // تفعيل التداول الشخصي - خاص بحساب المستخدم
                        // ملاحظة: هذا يختلف عن تشغيل النظام (خاص بالأدمن)
                        // ──────────────────────────────────────────────────────────
                        AppCard(
                          padding: const EdgeInsets.all(SpacingTokens.md),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          'تفعيل التداول التلقائي',
                                          style: TypographyTokens.body(
                                            cs.onSurface,
                                          ),
                                        ),
                                        const SizedBox(
                                          height: SpacingTokens.xxs,
                                        ),
                                        Text(
                                          s.tradingEnabled
                                              ? 'يفتح صفقات جديدة تلقائياً'
                                              : 'لن يفتح صفقات جديدة',
                                          style: TypographyTokens.caption(
                                            cs.onSurface.withValues(alpha: 0.5),
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  Switch.adaptive(
                                    value: s.tradingEnabled,
                                    onChanged:
                                        (!settingsAsync.isLoading &&
                                            !settingsAsync.hasError)
                                        ? _onTradingToggle
                                        : null,
                                  ),
                                ],
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: SpacingTokens.md),
                        // حالة المخاطرة اليومية
                        _DailyRiskCard(
                          dailyStatus: ref.watch(dailyStatusProvider),
                        ),
                        const SizedBox(height: SpacingTokens.md),
                        // ─── Risk Management Sliders ───────────
                        AppCard(
                          padding: const EdgeInsets.all(SpacingTokens.md),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  Icon(
                                    Icons.tune_rounded,
                                    color: cs.primary,
                                    size: 20,
                                  ),
                                  const SizedBox(width: SpacingTokens.sm),
                                  Text(
                                    'إدارة المخاطرة',
                                    style: TypographyTokens.h4(cs.onSurface),
                                  ),
                                  const Spacer(),
                                  if (_saving)
                                    SizedBox(
                                      width: 14,
                                      height: 14,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                        color: cs.primary,
                                      ),
                                    )
                                  else if (_saveSuccess)
                                    Icon(
                                      Icons.check_circle_rounded,
                                      size: 16,
                                      color: SemanticColors.of(context).positive,
                                    ),
                                ],
                              ),
                              const SizedBox(height: SpacingTokens.md),
                              _RiskSlider(
                                label: 'حجم الصفقة (% من الرصيد)',
                                caption:
                                    'النسبة المئوية من رصيد المحفظة لكل صفقة',
                                value: _positionSizePct,
                                min: 1,
                                max: 100,
                                suffix: '%',
                                fractionDigits: 0,
                                minLabel: '1%',
                                maxLabel: '100%',
                                onChanged: (v) {
                                  setState(() => _positionSizePct = v);
                                  _debouncedUpdate(auth.user!.id, {
                                    'position_size_percentage': v,
                                  });
                                },
                              ),
                              const SizedBox(height: SpacingTokens.sm),
                              _RiskSlider(
                                label: 'وقف الخسارة (%)',
                                caption: 'نسبة الخسارة القصوى قبل إغلاق الصفقة',
                                value: _stopLossPct,
                                min: 0.5,
                                max: 50,
                                suffix: '%',
                                fractionDigits: 1,
                                minLabel: '0.5%',
                                maxLabel: '50%',
                                onChanged: (v) {
                                  setState(() => _stopLossPct = v);
                                  _debouncedUpdate(auth.user!.id, {
                                    'stop_loss_pct': v,
                                  });
                                },
                              ),
                              const SizedBox(height: SpacingTokens.sm),
                              _RiskSlider(
                                label: 'جني الأرباح (%)',
                                caption: 'نسبة الربح المستهدفة لإغلاق الصفقة',
                                value: _takeProfitPct,
                                min: 1,
                                max: 100,
                                suffix: '%',
                                fractionDigits: 0,
                                minLabel: '1%',
                                maxLabel: '100%',
                                onChanged: (v) {
                                  setState(() => _takeProfitPct = v);
                                  _debouncedUpdate(auth.user!.id, {
                                    'take_profit_pct': v,
                                  });
                                },
                              ),
                              const SizedBox(height: SpacingTokens.sm),
                              _RiskSlider(
                                label: 'الحد الأقصى للخسارة اليومية (%)',
                                caption:
                                    'إيقاف التداول تلقائياً عند تجاوز هذه النسبة',
                                value: _maxDailyLossPct,
                                min: 1,
                                max: 50,
                                suffix: '%',
                                fractionDigits: 0,
                                minLabel: '1%',
                                maxLabel: '50%',
                                onChanged: (v) {
                                  setState(() => _maxDailyLossPct = v);
                                  _debouncedUpdate(auth.user!.id, {
                                    'max_daily_loss_pct': v,
                                  });
                                },
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: SpacingTokens.xl),
                      ],
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Portfolio Mode Switcher — التبديل بين المحفظة التجريبية والحقيقية
class _PortfolioModeSwitcher extends StatelessWidget {
  final String currentMode;
  final bool hasBinanceKeys;
  final bool hasConfiguredDbKeys;
  final bool keysRequiredForCurrentMode;
  final bool isLoading;
  final ValueChanged<String> onModeSelected;

  const _PortfolioModeSwitcher({
    required this.currentMode,
    required this.hasBinanceKeys,
    required this.hasConfiguredDbKeys,
    required this.keysRequiredForCurrentMode,
    required this.isLoading,
    required this.onModeSelected,
  });

  bool get _isDemo => currentMode != 'real';
  bool get _requiresBinanceKeys => keysRequiredForCurrentMode && !_isDemo;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    final sem = SemanticColors.of(context);
    final demoColor = sem.info;
    final realColor = sem.positive;

    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // ─── Header: اسم المحفظة النشطة ───────────────────────────────
          Row(
            children: [
              Container(
                width: 10,
                height: 10,
                decoration: BoxDecoration(
                  color: _isDemo ? demoColor : realColor,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: SpacingTokens.sm),
              Text(
                'المحفظة النشطة',
                style: TypographyTokens.caption(
                  cs.onSurface.withValues(alpha: 0.6),
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: (_isDemo ? demoColor : realColor).withValues(
                    alpha: 0.12,
                  ),
                  borderRadius: BorderRadius.circular(SpacingTokens.radiusFull),
                ),
                child: Text(
                  _isDemo ? 'تجريبية' : 'حقيقية',
                  style: TypographyTokens.caption(
                    _isDemo ? demoColor : realColor,
                  ).copyWith(fontWeight: FontWeight.bold),
                ),
              ),
            ],
          ),

          const SizedBox(height: SpacingTokens.md),

          // ─── Toggle Row: زر التبديل ───────────────────────────────────
          isLoading
              ? const Center(
                  child: Padding(
                    padding: EdgeInsets.symmetric(vertical: SpacingTokens.sm),
                    child: SizedBox(
                      width: 24,
                      height: 24,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  ),
                )
              : Row(
                  children: [
                    // زر التجريبي
                    Expanded(
                      child: _ModeButton(
                        label: 'تجريبي',
                        subtitle: 'محفظة آمنة',
                        icon: Icons.science_outlined,
                        isActive: _isDemo,
                        activeColor: demoColor,
                        onTap: _isDemo ? null : () => onModeSelected('demo'),
                      ),
                    ),
                    const SizedBox(width: SpacingTokens.sm),
                    // زر الحقيقي
                    Expanded(
                      child: _ModeButton(
                        label: 'حقيقي',
                        subtitle: hasConfiguredDbKeys
                            ? 'مفاتيح Binance محفوظة'
                            : hasBinanceKeys && !_requiresBinanceKeys
                            ? 'غير مطلوب في الوضع الحالي'
                            : 'يتطلب مفاتيح',
                        icon: hasConfiguredDbKeys
                            ? Icons.account_balance_wallet_outlined
                            : Icons.lock_outline,
                        isActive: !_isDemo,
                        activeColor: realColor,
                        onTap:
                            !_isDemo ||
                                (_requiresBinanceKeys && !hasConfiguredDbKeys)
                            ? null
                            : () => onModeSelected('real'),
                      ),
                    ),
                  ],
                ),

          // ─── تحذير: بدون مفاتيح Binance ─────────────────────────────
          if (_requiresBinanceKeys && !hasConfiguredDbKeys) ...[
            const SizedBox(height: SpacingTokens.sm),
            Container(
              padding: const EdgeInsets.all(SpacingTokens.sm),
              decoration: BoxDecoration(
                color: cs.errorContainer.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(SpacingTokens.radiusSm),
              ),
              child: Row(
                children: [
                  Icon(Icons.info_outline, size: 16, color: cs.error),
                  const SizedBox(width: SpacingTokens.xs),
                  Expanded(
                    child: Text(
                      'للتبديل للوضع الحقيقي، أضف مفاتيح Binance API أولاً',
                      style: TypographyTokens.caption(cs.error),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

/// زر الوضع الفردي (تجريبي / حقيقي)
class _ModeButton extends StatelessWidget {
  final String label;
  final String subtitle;
  final IconData icon;
  final bool isActive;
  final Color activeColor;
  final VoidCallback? onTap;

  const _ModeButton({
    required this.label,
    required this.subtitle,
    required this.icon,
    required this.isActive,
    required this.activeColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(
          horizontal: SpacingTokens.sm,
          vertical: SpacingTokens.md,
        ),
        decoration: BoxDecoration(
          color: isActive
              ? activeColor.withValues(alpha: 0.12)
              : cs.surfaceContainerHighest.withValues(alpha: 0.4),
          borderRadius: BorderRadius.circular(SpacingTokens.radiusMd),
          border: Border.all(
            color: isActive ? activeColor : cs.outline.withValues(alpha: 0.3),
            width: isActive ? 2 : 1,
          ),
        ),
        child: Column(
          children: [
            Icon(
              icon,
              size: 28,
              color: isActive
                  ? activeColor
                  : cs.onSurface.withValues(alpha: 0.4),
            ),
            const SizedBox(height: SpacingTokens.xs),
            Text(
              label,
              style:
                  TypographyTokens.body(
                    isActive
                        ? activeColor
                        : cs.onSurface.withValues(alpha: 0.5),
                  ).copyWith(
                    fontWeight: isActive ? FontWeight.bold : FontWeight.normal,
                  ),
            ),
            const SizedBox(height: 2),
            Text(
              subtitle,
              style: TypographyTokens.caption(
                isActive
                    ? activeColor.withValues(alpha: 0.7)
                    : cs.onSurface.withValues(alpha: 0.35),
              ),
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

/// Risk slider — reusable slider for risk management
class _RiskSlider extends StatelessWidget {
  final String label;
  final String caption;
  final double value;
  final double min;
  final double max;
  final String suffix;
  final int fractionDigits;
  final String minLabel;
  final String maxLabel;
  final ValueChanged<double> onChanged;

  const _RiskSlider({
    required this.label,
    required this.caption,
    required this.value,
    required this.min,
    required this.max,
    required this.suffix,
    required this.fractionDigits,
    required this.minLabel,
    required this.maxLabel,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Expanded(
              child: Text(label, style: TypographyTokens.body(cs.onSurface)),
            ),
            Text(
              '${value.toStringAsFixed(fractionDigits)}$suffix',
              style: TypographyTokens.mono(cs.primary, fontSize: 15),
            ),
          ],
        ),
        const SizedBox(height: SpacingTokens.xxs),
        Text(
          caption,
          style: TypographyTokens.caption(
            cs.onSurface.withValues(alpha: 0.5),
          ),
        ),
        Slider(
          value: value.clamp(min, max),
          min: min,
          max: max,
          label: '${value.toStringAsFixed(fractionDigits)}$suffix',
          onChanged: onChanged,
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              minLabel,
              style: TypographyTokens.caption(
                cs.onSurface.withValues(alpha: 0.4),
              ),
            ),
            Text(
              maxLabel,
              style: TypographyTokens.caption(
                cs.onSurface.withValues(alpha: 0.4),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

/// Daily risk card — shows daily loss limit usage with a progress bar
class _DailyRiskCard extends StatelessWidget {
  final AsyncValue<Map<String, dynamic>> dailyStatus;

  const _DailyRiskCard({required this.dailyStatus});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return dailyStatus.when(
      loading: () => const SizedBox.shrink(),
      error: (e, _) => _buildRiskWarning(
        context: context,
        message: 'تعذر تحميل حالة المخاطرة',
        isWarning: true,
      ),
      data: (d) {
        if (d.isEmpty) return const SizedBox.shrink();

        final usedPct = (d['daily_loss_used_pct'] as num?)?.toDouble() ?? 0.0;
        final maxPct = (d['max_daily_loss_pct'] as num?)?.toDouble() ?? 0.0;
        final remainingUsdt = (d['remaining_usdt'] as num?)?.toDouble() ?? 0.0;
        final dailyPnl = (d['daily_pnl'] as num?)?.toDouble() ?? 0.0;
        final breached = d['limit_breached'] == true;
        final tradesCount = (d['trades_today'] as num?)?.toInt() ?? 0;
        final progress = maxPct > 0 ? (usedPct / maxPct).clamp(0.0, 1.0) : 0.0;

        final sem = SemanticColors.of(context);
        final barColor = breached
            ? cs.error
            : usedPct > maxPct * 0.75
            ? sem.warning
            : cs.primary;

        return AppCard(
          padding: const EdgeInsets.all(SpacingTokens.md),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    breached ? Icons.warning_rounded : Icons.shield_outlined,
                    color: breached ? cs.error : cs.primary,
                    size: 20,
                  ),
                  const SizedBox(width: SpacingTokens.sm),
                  Text(
                    'حد الخسارة اليومي',
                    style: TypographyTokens.body(cs.onSurface),
                  ),
                  const Spacer(),
                  Text(
                    '${usedPct.toStringAsFixed(1)}% / ${maxPct.toStringAsFixed(0)}%',
                    style: TypographyTokens.mono(
                      breached ? cs.error : cs.onSurface,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: SpacingTokens.sm),
              ClipRRect(
                borderRadius: BorderRadius.circular(SpacingTokens.xs),
                child: LinearProgressIndicator(
                  value: progress,
                  backgroundColor: cs.surfaceContainerHighest,
                  color: barColor,
                  minHeight: 6,
                ),
              ),
              const SizedBox(height: SpacingTokens.sm),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    breached
                        ? 'تم إيقاف التداول — تجاوز الحد اليومي'
                        : 'متبقي: ${remainingUsdt.toStringAsFixed(2)} USDT',
                    style: TypographyTokens.caption(
                      breached ? cs.error : cs.onSurface.withValues(alpha: 0.6),
                    ),
                  ),
                  Text(
                    'اليوم: ${dailyPnl >= 0 ? '+' : ''}${dailyPnl.toStringAsFixed(2)} ($tradesCount صفقة)',
                    style: TypographyTokens.caption(
                      dailyPnl >= 0
                          ? sem.positive
                          : cs.onSurface.withValues(alpha: 0.5),
                    ),
                  ),
                ],
              ),
            ],
          ),
        );
      },
    );
  }

  static Widget _buildRiskWarning({
    required BuildContext context,
    required String message,
    bool isWarning = false,
  }) {
    final cs = Theme.of(context).colorScheme;
    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.md),
      child: Row(
        children: [
          Icon(
            isWarning ? Icons.warning_amber_rounded : Icons.shield_outlined,
            color: isWarning ? cs.error : cs.primary,
            size: 20,
          ),
          const SizedBox(width: SpacingTokens.sm),
          Text(
            message,
            style: TypographyTokens.caption(
              isWarning ? cs.error : cs.onSurface.withValues(alpha: 0.6),
            ),
          ),
        ],
      ),
    );
  }
}
