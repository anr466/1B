import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// Registration Progress Stepper — 6 مراحل إعداد الحساب
/// يُعرض في أعلى شاشات: التسجيل، التوثيق، المفاتيح، التداول، البصمة، لوحة التحكم
class RegistrationStepper extends StatelessWidget {
  /// الخطوة الحالية (0-based)
  /// 0 = تسجيل, 1 = توثيق, 2 = مفاتيح, 3 = التداول, 4 = البصمة, 5 = لوحة التحكم
  final int currentStep;

  const RegistrationStepper({super.key, required this.currentStep});

  static const _labels = [
    'تسجيل',
    'توثيق',
    'مفاتيح',
    'التداول',
    'البصمة',
    'لوحة\nالتحكم',
  ];

  static const int _stepCount = 6;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    const fontFamily = 'BarlowCondensed';

    final activeColor = cs.primary;
    final inactiveColor = cs.onSurface.withValues(alpha: 0.14);
    final activeTextColor = cs.primary;
    final inactiveTextColor = cs.onSurface.withValues(alpha: 0.32);
    final doneLineColor = cs.primary.withValues(alpha: 0.7);

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: SpacingTokens.base,
        vertical: SpacingTokens.md,
      ),
      decoration: BoxDecoration(
        color: cs.surfaceContainerLowest,
        border: Border(
          bottom: BorderSide(
            color: cs.outline.withValues(alpha: 0.12),
            width: 1,
          ),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          // ─── Header ──────────────────────────────────
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'إعداد الحساب',
                style: TypographyTokens.caption(
                  cs.onSurface.withValues(alpha: 0.5),
                ),
              ),
              Text(
                'خطوة ${currentStep + 1} من $_stepCount',
                style: TypographyTokens.caption(activeColor),
              ),
            ],
          ),
          const SizedBox(height: SpacingTokens.sm),

          // ─── Steps Row ───────────────────────────────
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (int i = 0; i < _stepCount; i++) ...[
                if (i > 0)
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.only(bottom: 26, top: 10),
                      child: Container(
                        height: 2,
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(1),
                          gradient: i <= currentStep
                              ? LinearGradient(
                                  colors: [doneLineColor, doneLineColor],
                                )
                              : null,
                          color: i <= currentStep ? null : inactiveColor,
                        ),
                      ),
                    ),
                  ),
                _StepNode(
                  index: i,
                  currentStep: currentStep,
                  label: _labels[i],
                  activeColor: activeColor,
                  inactiveColor: inactiveColor,
                  activeTextColor: activeTextColor,
                  inactiveTextColor: inactiveTextColor,
                  fontFamily: fontFamily,
                  onPrimary: cs.onPrimary,
                  surfaceContainerHighest: cs.surfaceContainerHighest,
                ),
              ],
            ],
          ),

          // ─── Progress Bar ─────────────────────────────
          const SizedBox(height: SpacingTokens.xs),
          ClipRRect(
            borderRadius: BorderRadius.circular(SpacingTokens.radiusFull),
            child: LinearProgressIndicator(
              value: (currentStep + 1) / _stepCount,
              backgroundColor: inactiveColor,
              color: activeColor,
              minHeight: 3,
            ),
          ),
        ],
      ),
    );
  }
}

class _StepNode extends StatelessWidget {
  final int index;
  final int currentStep;
  final String label;
  final Color activeColor;
  final Color inactiveColor;
  final Color activeTextColor;
  final Color inactiveTextColor;
  final Color onPrimary;
  final Color surfaceContainerHighest;
  final String fontFamily;

  const _StepNode({
    required this.index,
    required this.currentStep,
    required this.label,
    required this.activeColor,
    required this.inactiveColor,
    required this.activeTextColor,
    required this.inactiveTextColor,
    required this.onPrimary,
    required this.surfaceContainerHighest,
    required this.fontFamily,
  });

  bool get _isDone => index < currentStep;
  bool get _isActive => index == currentStep;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        // ─── Circle ────────────────────────────────
        AnimatedContainer(
          duration: const Duration(milliseconds: 300),
          curve: Curves.easeInOut,
          width: 22,
          height: 22,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: (_isDone || _isActive)
                ? activeColor
                : surfaceContainerHighest,
            border: Border.all(
              color: (_isDone || _isActive) ? activeColor : inactiveColor,
              width: 1.5,
            ),
            boxShadow: _isActive
                ? [
                    BoxShadow(
                      color: activeColor.withValues(alpha: 0.30),
                      blurRadius: 6,
                      spreadRadius: 1,
                    ),
                  ]
                : null,
          ),
          child: Center(
            child: _isDone
                ? Icon(Icons.check_rounded, size: 12, color: onPrimary)
                : Text(
                    '${index + 1}',
                    style: TextStyle(
                      fontFamily: fontFamily,
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      color: _isActive ? onPrimary : inactiveTextColor,
                    ),
                  ),
          ),
        ),

        const SizedBox(height: 4),

        // ─── Label ─────────────────────────────────
        SizedBox(
          width: 42,
          child: Text(
            label,
            style: TextStyle(
              fontFamily: fontFamily,
              fontSize: 9,
              fontWeight: _isActive ? FontWeight.w600 : FontWeight.w400,
              color: (_isDone || _isActive)
                  ? activeTextColor
                  : inactiveTextColor,
              height: 1.3,
            ),
            textAlign: TextAlign.center,
            maxLines: 2,
          ),
        ),
      ],
    );
  }
}
