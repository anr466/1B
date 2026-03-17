import 'package:flutter/material.dart';

/// Gradient Background — خلفية متدرجة مشتركة
class GradientBackground extends StatelessWidget {
  final Widget child;
  final List<Color>? colors;
  final AlignmentGeometry begin;
  final AlignmentGeometry end;

  const GradientBackground({
    super.key,
    required this.child,
    this.colors,
    this.begin = Alignment.topCenter,
    this.end = Alignment.bottomCenter,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final gradientColors =
        colors ??
        [
          cs.surface,
          cs.surfaceContainerHighest.withValues(alpha: 0.3),
          cs.surface,
        ];

    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: gradientColors,
          begin: begin,
          end: end,
        ),
      ),
      child: child,
    );
  }
}
