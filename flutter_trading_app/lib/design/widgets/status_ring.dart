import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:trading_app/design/tokens/typography_tokens.dart';

/// Status Ring — حلقة نشاط دائرية
/// مستوحاة من Apple Watch Activity Rings
///
/// الاستخدام:
/// ```dart
/// StatusRing(
///   percentage: 0.82,
///   label: 'الأداء',
///   color: Colors.blue,
/// )
/// ```
class StatusRing extends StatelessWidget {
  final double percentage;
  final String? label;
  final Color? color;
  final double size;
  final double strokeWidth;
  final String? centerText;

  const StatusRing({
    super.key,
    required this.percentage,
    this.label,
    this.color,
    this.size = 120,
    this.strokeWidth = 8,
    this.centerText,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = cs.brightness == Brightness.dark;

    final ringColor = color ?? cs.primary;
    final trackColor = isDark
        ? cs.onSurface.withValues(alpha: 0.10)
        : cs.onSurface.withValues(alpha: 0.06);

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          CustomPaint(
            size: Size(size, size),
            painter: _RingPainter(
              percentage: percentage.clamp(0.0, 1.0),
              trackColor: trackColor,
              progressColor: ringColor,
              strokeWidth: strokeWidth,
            ),
          ),
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (centerText != null)
                Text(
                  centerText!,
                  style: TypographyTokens.h1(
                    cs.onSurface,
                  ).copyWith(fontWeight: FontWeight.w800, fontSize: 28),
                ),
              if (label != null) ...[
                const SizedBox(height: 2),
                Text(
                  label!,
                  style: TypographyTokens.caption(
                    cs.onSurface.withValues(alpha: 0.5),
                  ).copyWith(letterSpacing: 1.0),
                ),
              ],
            ],
          ),
        ],
      ),
    );
  }
}

/// Multi Ring — حلقات متعددة متداخلة
/// مثل Activity Rings في Apple Watch
class MultiStatusRing extends StatelessWidget {
  final List<RingData> rings;
  final double size;

  const MultiStatusRing({super.key, required this.rings, this.size = 140});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = cs.brightness == Brightness.dark;

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          for (int i = 0; i < rings.length; i++)
            CustomPaint(
              size: Size(size, size),
              painter: _RingPainter(
                percentage: rings[i].percentage.clamp(0.0, 1.0),
                trackColor: isDark
                    ? cs.onSurface.withValues(alpha: 0.08)
                    : cs.onSurface.withValues(alpha: 0.05),
                progressColor: rings[i].color,
                strokeWidth: 10,
                offset: i * 12, // مسافة بين الحلقات
              ),
            ),
          // النص في المنتصف
          Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                '${(rings.first.percentage * 100).toInt()}%',
                style: TypographyTokens.h1(
                  cs.onSurface,
                ).copyWith(fontWeight: FontWeight.w800, fontSize: 32),
              ),
              const SizedBox(height: 2),
              Text(
                'الأداء',
                style: TypographyTokens.caption(
                  cs.onSurface.withValues(alpha: 0.5),
                ).copyWith(letterSpacing: 1.0),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// بيانات حلقة فردية
class RingData {
  final double percentage;
  final Color color;
  final String? label;

  const RingData({required this.percentage, required this.color, this.label});
}

/// رسم الحلقة
class _RingPainter extends CustomPainter {
  final double percentage;
  final Color trackColor;
  final Color progressColor;
  final double strokeWidth;
  final double offset;

  _RingPainter({
    required this.percentage,
    required this.trackColor,
    required this.progressColor,
    required this.strokeWidth,
    this.offset = 0,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = (size.width / 2) - (strokeWidth / 2) - offset;

    // رسم المسار الخلفي
    final trackPaint = Paint()
      ..color = trackColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.round;

    canvas.drawCircle(center, radius, trackPaint);

    // رسم التقدم
    if (percentage > 0) {
      final progressPaint = Paint()
        ..color = progressColor
        ..style = PaintingStyle.stroke
        ..strokeWidth = strokeWidth
        ..strokeCap = StrokeCap.round;

      final sweepAngle = 2 * math.pi * percentage;

      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        -math.pi / 2, // نبدأ من الأعلى
        sweepAngle,
        false,
        progressPaint,
      );
    }
  }

  @override
  bool shouldRepaint(_RingPainter oldDelegate) {
    return oldDelegate.percentage != percentage ||
        oldDelegate.progressColor != progressColor;
  }
}
