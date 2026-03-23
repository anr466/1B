import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/constants/ux_messages.dart';
import 'package:trading_app/core/models/settings_model.dart';
import 'package:trading_app/core/providers/admin_provider.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/providers/trades_provider.dart';
import 'package:trading_app/design/tokens/semantic_colors.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';
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

/// Trading Settings Screen — إعدادات التداول (sliders + save)
class TradingSettingsScreen extends ConsumerStatefulWidget {
  const TradingSettingsScreen({super.key});

  @override
  ConsumerState<TradingSettingsScreen> createState() =>
      _TradingSettingsScreenState();
}

class _TradingSettingsScreenState extends ConsumerState<TradingSettingsScreen> {
  bool _isSwitchingMode = false;

  bool get _isTradingSettingsValid {
    return true;
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
        ref.read(adminPortfolioModeProvider.notifier).state = mode;
        ref.invalidate(settingsDataProvider);
        ref.invalidate(dailyStatusProvider);
        ref.invalidate(portfolioProvider);
        ref.invalidate(statsProvider);
        ref.invalidate(activePositionsProvider);
        ref.invalidate(successfulCoinsProvider);
        ref.invalidate(recentTradesProvider);
        ref.invalidate(tradesListProvider);
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
    await toggleTradingWithBiometric(
      ref: ref,
      enabled: v,
      biometricAuth: (reason) =>
          ref.read(biometricServiceProvider).authenticate(reason: reason),
      showMessage: (message, type) =>
          AppSnackbar.show(context, message: message, type: type),
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
            return ListView(
              padding: const EdgeInsets.all(SpacingTokens.base),
              children: [
                if (auth.isAdmin) ...[
                  _PortfolioModeSwitcher(
                    currentMode: s.activePortfolio,
                    hasBinanceKeys: s.hasBinanceKeys,
                    hasConfiguredDbKeys: s.hasConfiguredDbKeys,
                    keysRequiredForCurrentMode: s.keysRequiredForCurrentMode,
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
                                  s.tradingEnabled
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
                            value: s.tradingEnabled,
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
                _DailyRiskCard(dailyStatus: ref.watch(dailyStatusProvider)),
                const SizedBox(height: SpacingTokens.md),

                AppCard(
                  padding: const EdgeInsets.all(SpacingTokens.md),
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.auto_awesome, color: cs.primary, size: 24),
                      const SizedBox(width: SpacingTokens.md),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'ملخص التحكم',
                              style: TypographyTokens.body(cs.onSurface),
                            ),
                            const SizedBox(height: SpacingTokens.xxs),
                            Text(
                              'هذه الشاشة مخصصة فقط لتفعيل التداول واختيار المحفظة النشطة ومراجعة حالة المخاطرة اليومية.',
                              style: TypographyTokens.caption(
                                cs.onSurface.withValues(alpha: 0.5),
                              ),
                            ),
                            const SizedBox(height: SpacingTokens.xs),
                            Text(
                              'الدخول والخروج وحجم الصفقة وإدارة المخاطر التفصيلية تُدار من محرك التداول الخلفي والاستراتيجية النشطة لتجنب التعارض أو السلوك المضلل.',
                              style: TypographyTokens.caption(
                                cs.onSurface.withValues(alpha: 0.45),
                              ),
                            ),
                          ],
                        ),
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
// ignore: unused_element
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
}
