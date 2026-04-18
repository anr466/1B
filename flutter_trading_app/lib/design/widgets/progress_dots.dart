import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/spacing_tokens.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// Progress Dots — نقاط تقدم دائرية
/// مستوحاة من Recovery indicator في التصميم المرجعي
///
/// الاستخدام:
/// ```dart
/// ProgressDots(
///   filledCount: 4,
///   totalCount: 5,
///   label: 'PEAK FORM',
///   color: Colors.green,
/// )
/// ```
class ProgressDots extends StatelessWidget {
  final int filledCount;
  final int totalCount;
  final String? label;
  final Color? color;
  final double dotSize;
  final double spacing;

  const ProgressDots({
    super.key,
    required this.filledCount,
    required this.totalCount,
    this.label,
    this.color,
    this.dotSize = 24,
    this.spacing = 8,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = cs.brightness == Brightness.dark;

    final dotColor = color ?? cs.primary;
    final emptyColor = isDark
        ? cs.onSurface.withValues(alpha: 0.10)
        : cs.onSurface.withValues(alpha: 0.08);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // النقاط
        Row(
          mainAxisSize: MainAxisSize.min,
          children: List.generate(totalCount, (index) {
            final isFilled = index < filledCount;
            return Padding(
              padding: EdgeInsets.only(
                right: index < totalCount - 1 ? spacing : 0,
              ),
              child: Container(
                width: dotSize,
                height: dotSize,
                decoration: BoxDecoration(
                  color: isFilled ? dotColor : emptyColor,
                  shape: BoxShape.circle,
                ),
              ),
            );
          }),
        ),
        if (label != null) ...[
          const SizedBox(height: SpacingTokens.xs),
          Text(
            label!.toUpperCase(),
            style: TypographyTokens.overline(
              cs.onSurface.withValues(alpha: 0.5),
            ).copyWith(letterSpacing: 1.5, fontSize: 10),
          ),
        ],
      ],
    );
  }
}

/// Sleep Dots — نقاط النوم المستوحاة من Sleep Score card
/// تمثل مراحل النوم المختلفة
class SleepDots extends StatelessWidget {
  final List<SleepPhase> phases;
  final String duration;
  final Color? color;

  const SleepDots({
    super.key,
    required this.phases,
    required this.duration,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = cs.brightness == Brightness.dark;

    final baseColor = color ?? cs.primary;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // النقاط
        Row(
          mainAxisSize: MainAxisSize.min,
          children: phases.map((phase) {
            return Padding(
              padding: const EdgeInsets.only(right: 4),
              child: Container(
                width: 20,
                height: 20,
                decoration: BoxDecoration(
                  color: phase.isActive
                      ? baseColor
                      : isDark
                      ? cs.onSurface.withValues(alpha: 0.15)
                      : cs.onSurface.withValues(alpha: 0.10),
                  shape: BoxShape.circle,
                ),
              ),
            );
          }).toList(),
        ),
        const SizedBox(height: SpacingTokens.xs),
        Text(
          duration,
          style: TypographyTokens.caption(cs.onSurface.withValues(alpha: 0.5)),
        ),
      ],
    );
  }
}

/// مرحلة نوم
class SleepPhase {
  final bool isActive;

  const SleepPhase({required this.isActive});
}
