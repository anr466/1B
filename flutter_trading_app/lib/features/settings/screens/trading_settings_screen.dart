import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/constants/ux_messages.dart';
import 'package:trading_app/core/models/settings_model.dart';
import 'package:trading_app/core/providers/admin_provider.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/providers/trades_provider.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
import 'package:trading_app/design/widgets/app_button.dart';
import 'package:trading_app/design/widgets/app_card.dart';
import 'package:trading_app/design/widgets/app_snackbar.dart';
import 'package:trading_app/design/widgets/loading_shimmer.dart';

/// Settings Provider
final settingsDataProvider = FutureProvider.autoDispose<SettingsModel>((
  ref,
) async {
  final auth = ref.watch(authProvider);
  if (!auth.isAuthenticated || auth.user == null) throw Exception('غير مصادق');
  final mode = auth.isAdmin ? ref.watch(adminPortfolioModeProvider) : null;
  final repo = ref.watch(settingsRepositoryProvider);
  return repo.getSettings(auth.user!.id, mode: mode);
});

/// Daily risk status provider
final dailyRiskStatusProvider =
    FutureProvider.autoDispose<Map<String, dynamic>>((ref) async {
      final auth = ref.watch(authProvider);
      if (!auth.isAuthenticated || auth.user == null) return {};
      final mode = auth.isAdmin ? ref.watch(adminPortfolioModeProvider) : null;
      final repo = ref.watch(settingsRepositoryProvider);
      return repo.getDailyStatus(auth.user!.id, mode: mode);
    });

/// Trading Settings Screen — إعدادات التداول (sliders + save)
class TradingSettingsScreen extends ConsumerStatefulWidget {
  const TradingSettingsScreen({super.key});

  @override
  ConsumerState<TradingSettingsScreen> createState() =>
      _TradingSettingsScreenState();
}

class _TradingSettingsScreenState extends ConsumerState<TradingSettingsScreen> {
  SettingsModel? _settings;
  String _tradingMode = 'demo';
  bool _tradingEnabled = false;
  double _positionSize = 10;
  int _maxPositions = 3;
  double _stopLoss = 2.0;
  double _takeProfit = 4.0;
  double _trailingDistance = 3.0;
  double _maxDailyLoss = 10;
  bool _isSaving = false;
  bool _isSwitchingMode = false;
  bool _hasChanges = false;

  // التحقق من اكتمال إعدادات التداول - النظام يديرها تلقائياً الآن
  bool get _isTradingSettingsValid {
    // النظام يحدد القيم تلقائياً، التحقق يكون فقط من الرصيد
    return true;
  }

  void _initFromSettings(SettingsModel s) {
    if (_settings != null) return;
    _settings = s;
    _tradingMode = s.tradingMode;
    _tradingEnabled = s.tradingEnabled;
    _positionSize = s.positionSizePct;
    _maxPositions = s.maxPositions;
    _stopLoss = s.stopLossPct.clamp(0.5, 10.0);
    _takeProfit = s.takeProfitPct.clamp(1.0, 20.0);
    _trailingDistance = s.trailingDistancePct.clamp(0.5, 5.0);
    _maxDailyLoss = s.maxDailyLossPct.clamp(5.0, 15.0);
    ref.read(adminPortfolioModeProvider.notifier).state = s.activePortfolio;
  }

  Future<void> _changeTradingMode(String mode) async {
    final auth = ref.read(authProvider);
    if (auth.user == null || !auth.isAdmin) return;

    setState(() => _isSwitchingMode = true);
    try {
      final repo = ref.read(settingsRepositoryProvider);
      final result = await repo.updateTradingMode(auth.user!.id, mode);
      if (!mounted) return;

      if (result['success'] == true) {
        setState(() => _tradingMode = mode);
        ref.read(adminPortfolioModeProvider.notifier).state = mode;
        ref.invalidate(settingsDataProvider);
        ref.invalidate(dailyRiskStatusProvider);
        ref.invalidate(portfolioProvider);
        ref.invalidate(statsProvider);
        ref.invalidate(activePositionsProvider);
        ref.invalidate(recentTradesProvider);
        ref.invalidate(accountTradingProvider);
        ref.invalidate(mlStatusProvider);
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
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message: UxMessages.error,
        type: SnackType.error,
      );
    } finally {
      if (mounted) setState(() => _isSwitchingMode = false);
    }
  }

  Future<void> _onTradingToggle(bool v) async {
    final bio = ref.read(biometricServiceProvider);
    if (await bio.isAvailable) {
      final label = v ? 'تأكيد تفعيل التداول' : 'تأكيد إيقاف التداول';
      final ok = await bio.authenticate(reason: label);
      if (!mounted) return;
      if (!ok) {
        AppSnackbar.show(
          context,
          message: 'فشل التحقق من البصمة',
          type: SnackType.error,
        );
        return;
      }
    }
    if (!mounted) return;
    setState(() {
      _tradingEnabled = v;
      _hasChanges = true;
    });
    await _save();
  }

  Future<void> _save() async {
    final auth = ref.read(authProvider);
    if (auth.user == null) return;

    setState(() => _isSaving = true);
    try {
      final repo = ref.read(settingsRepositoryProvider);
      final result = await repo.updateSettings(auth.user!.id, {
        'tradingEnabled': _tradingEnabled,
        'positionSizePercentage': _positionSize,
        'maxConcurrentTrades': _maxPositions,
        'stopLossPercentage': _stopLoss,
        'takeProfitPercentage': _takeProfit,
        'trailingDistance': _trailingDistance,
        'maxDailyLoss': _maxDailyLoss,
      });

      if (!mounted) return;
      if (result['success'] == true) {
        setState(() => _hasChanges = false);
        ref.read(accountTradingProvider.notifier).load();
        AppSnackbar.show(
          context,
          message: UxMessages.success,
          type: SnackType.success,
        );
        ref.invalidate(settingsDataProvider);
        ref.invalidate(dailyRiskStatusProvider);
        ref.invalidate(dailyStatusProvider);
        ref.invalidate(portfolioProvider);
        ref.invalidate(statsProvider);
        ref.invalidate(activePositionsProvider);
        ref.invalidate(recentTradesProvider);
      } else {
        AppSnackbar.show(
          context,
          message: UxMessages.error,
          type: SnackType.error,
        );
      }
    } catch (e) {
      if (!mounted) return;
      AppSnackbar.show(
        context,
        message: UxMessages.error,
        type: SnackType.error,
      );
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
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
        appBar: AppBar(
          title: Text(
            'إعدادات التداول',
            style: TypographyTokens.h3(cs.onSurface),
          ),
        ),
        body: settingsAsync.when(
          loading: () => const Padding(
            padding: EdgeInsets.all(SpacingTokens.base),
            child: LoadingShimmer(itemCount: 4, itemHeight: 80),
          ),
          error: (e, _) => Center(
            child: Text('خطأ: $e', style: TypographyTokens.body(cs.error)),
          ),
          data: (s) {
            _initFromSettings(s);
            return ListView(
              padding: const EdgeInsets.all(SpacingTokens.base),
              children: [
                if (auth.isAdmin) ...[
                  _PortfolioModeSwitcher(
                    currentMode: _tradingMode,
                    hasBinanceKeys: s.hasBinanceKeys,
                    isLoading: _isSwitchingMode,
                    onModeSelected: (mode) => _changeTradingMode(mode),
                  ),
                  const SizedBox(height: SpacingTokens.md),
                ],

                // تفعيل التداول - مرتبط بإعدادات التداول
                AppCard(
                  padding: const EdgeInsets.all(SpacingTokens.md),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  'تفعيل التداول',
                                  style: TypographyTokens.body(cs.onSurface),
                                ),
                                const SizedBox(height: SpacingTokens.xxs),
                                Text(
                                  _tradingEnabled
                                      ? 'النظام يفتح صفقات جديدة تلقائياً'
                                      : 'التداول متوقف حالياً',
                                  style: TypographyTokens.caption(
                                    cs.onSurface.withValues(alpha: 0.5),
                                  ),
                                ),
                              ],
                            ),
                          ),
                          Switch.adaptive(
                            value: _tradingEnabled,
                            onChanged: _isTradingSettingsValid
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
                _DailyRiskCard(dailyStatus: ref.watch(dailyRiskStatusProvider)),
                const SizedBox(height: SpacingTokens.md),

                // حد الخسارة اليومية
                AppCard(
                  padding: const EdgeInsets.all(SpacingTokens.md),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            'حد الخسارة اليومية',
                            style: TypographyTokens.body(cs.onSurface),
                          ),
                          Text(
                            '${_maxDailyLoss.toStringAsFixed(0)}%',
                            style: TypographyTokens.body(
                              cs.primary,
                            ).copyWith(fontWeight: FontWeight.bold),
                          ),
                        ],
                      ),
                      const SizedBox(height: SpacingTokens.xs),
                      Text(
                        'يوقف التداول تلقائياً عند تجاوز هذه النسبة من رصيدك',
                        style: TypographyTokens.caption(
                          cs.onSurface.withValues(alpha: 0.5),
                        ),
                      ),
                      Slider(
                        value: _maxDailyLoss,
                        min: 5,
                        max: 15,
                        divisions: 10,
                        label: '${_maxDailyLoss.toStringAsFixed(0)}%',
                        onChanged: (v) => setState(() {
                          _maxDailyLoss = v;
                          _hasChanges = true;
                        }),
                      ),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            '5% (حماية)',
                            style: TypographyTokens.caption(
                              cs.onSurface.withValues(alpha: 0.4),
                            ),
                          ),
                          Text(
                            '15% (مرونة)',
                            style: TypographyTokens.caption(
                              cs.onSurface.withValues(alpha: 0.4),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: SpacingTokens.md),

                // وقف الخسارة
                _SliderCard(
                  label: 'وقف الخسارة',
                  caption: 'يُغلق الصفقة تلقائياً عند الوصول لهذه الخسارة',
                  value: _stopLoss,
                  min: 0.5,
                  max: 10.0,
                  divisions: 19,
                  suffix: '%',
                  fractionDigits: 1,
                  minLabel: '0.5%',
                  maxLabel: '10%',
                  onChanged: (v) => setState(() {
                    _stopLoss = v;
                    _hasChanges = true;
                  }),
                ),
                const SizedBox(height: SpacingTokens.md),

                // جني الأرباح
                _SliderCard(
                  label: 'جني الأرباح',
                  caption: 'يُغلق الصفقة تلقائياً عند تحقيق هذا الربح',
                  value: _takeProfit,
                  min: 1.0,
                  max: 20.0,
                  divisions: 38,
                  suffix: '%',
                  fractionDigits: 1,
                  minLabel: '1%',
                  maxLabel: '20%',
                  onChanged: (v) => setState(() {
                    _takeProfit = v;
                    _hasChanges = true;
                  }),
                ),
                const SizedBox(height: SpacingTokens.md),

                // الوقف المتحرك
                _SliderCard(
                  label: 'الوقف المتحرك (Trailing)',
                  caption: 'مسافة الوقف المتحرك من السعر الحالي',
                  value: _trailingDistance,
                  min: 0.5,
                  max: 5.0,
                  divisions: 9,
                  suffix: '%',
                  fractionDigits: 1,
                  minLabel: '0.5%',
                  maxLabel: '5%',
                  onChanged: (v) => setState(() {
                    _trailingDistance = v;
                    _hasChanges = true;
                  }),
                ),
                const SizedBox(height: SpacingTokens.md),

                // ملاحظة: حجم الصفقة وعدد الصفقات يحددهم النظام تلقائياً
                // بناءً على تحليل المخاطر والعائد
                AppCard(
                  padding: const EdgeInsets.all(SpacingTokens.md),
                  child: Row(
                    children: [
                      Icon(Icons.auto_awesome, color: cs.primary, size: 24),
                      const SizedBox(width: SpacingTokens.md),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'إدارة المخاطر تلقائية',
                              style: TypographyTokens.body(cs.onSurface),
                            ),
                            const SizedBox(height: SpacingTokens.xxs),
                            Text(
                              'النظام يستخدم هذه الحدود ضمن إدارة المخاطر الذكية ولا يعتمد عليها وحدها',
                              style: TypographyTokens.caption(
                                cs.onSurface.withValues(alpha: 0.5),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: SpacingTokens.xl),

                // Save
                AppButton(
                  label: 'حفظ الإعدادات',
                  onPressed: _hasChanges ? _save : null,
                  isLoading: _isSaving,
                ),
                const SizedBox(height: SpacingTokens.xl),
              ],
            );
          },
        ),
      ),
    );
  }
}

/// Portfolio Mode Switcher — التبديل بين المحفظة التجريبية والحقيقية
class _PortfolioModeSwitcher extends StatelessWidget {
  final String currentMode;
  final bool hasBinanceKeys;
  final bool isLoading;
  final ValueChanged<String> onModeSelected;

  const _PortfolioModeSwitcher({
    required this.currentMode,
    required this.hasBinanceKeys,
    required this.isLoading,
    required this.onModeSelected,
  });

  bool get _isDemo => currentMode != 'real';

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    final demoColor = const Color(0xFF2563EB);
    final realColor = const Color(0xFF059669);

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
                  borderRadius: BorderRadius.circular(20),
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
                        subtitle: hasBinanceKeys
                            ? 'Binance متصل'
                            : 'يتطلب مفاتيح',
                        icon: hasBinanceKeys
                            ? Icons.account_balance_wallet_outlined
                            : Icons.lock_outline,
                        isActive: !_isDemo,
                        activeColor: realColor,
                        onTap: !_isDemo || !hasBinanceKeys
                            ? null
                            : () => onModeSelected('real'),
                      ),
                    ),
                  ],
                ),

          // ─── تحذير: بدون مفاتيح Binance ─────────────────────────────
          if (!hasBinanceKeys) ...[
            const SizedBox(height: SpacingTokens.sm),
            Container(
              padding: const EdgeInsets.all(SpacingTokens.sm),
              decoration: BoxDecoration(
                color: cs.errorContainer.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(8),
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
          borderRadius: BorderRadius.circular(12),
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

/// Reusable slider card for trading settings
class _SliderCard extends StatelessWidget {
  final String label;
  final String caption;
  final double value;
  final double min;
  final double max;
  final int divisions;
  final String suffix;
  final int fractionDigits;
  final String minLabel;
  final String maxLabel;
  final ValueChanged<double> onChanged;

  const _SliderCard({
    required this.label,
    required this.caption,
    required this.value,
    required this.min,
    required this.max,
    required this.divisions,
    required this.suffix,
    required this.fractionDigits,
    required this.minLabel,
    required this.maxLabel,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return AppCard(
      padding: const EdgeInsets.all(SpacingTokens.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(label, style: TypographyTokens.body(cs.onSurface)),
              Text(
                '${value.toStringAsFixed(fractionDigits)}$suffix',
                style: TypographyTokens.body(
                  cs.primary,
                ).copyWith(fontWeight: FontWeight.bold),
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
            value: value,
            min: min,
            max: max,
            divisions: divisions,
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
      ),
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
      error: (_, __) => const SizedBox.shrink(),
      data: (d) {
        if (d.isEmpty) return const SizedBox.shrink();

        final usedPct = (d['daily_loss_used_pct'] as num?)?.toDouble() ?? 0.0;
        final maxPct = (d['max_daily_loss_pct'] as num?)?.toDouble() ?? 0.0;
        final remainingUsdt = (d['remaining_usdt'] as num?)?.toDouble() ?? 0.0;
        final dailyPnl = (d['daily_pnl'] as num?)?.toDouble() ?? 0.0;
        final breached = d['limit_breached'] == true;
        final tradesCount = (d['trades_today'] as num?)?.toInt() ?? 0;
        final progress = maxPct > 0 ? (usedPct / maxPct).clamp(0.0, 1.0) : 0.0;

        final barColor = breached
            ? cs.error
            : usedPct > maxPct * 0.75
            ? Colors.orange
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
                borderRadius: BorderRadius.circular(4),
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
                          ? Colors.green
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
}
