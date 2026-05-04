import 'package:flutter/material.dart';

/// BrandIcons — أيقونات مخصصة CustomPainter
/// المرحلة الأولى: 15 أيقونة أساسية (nav 5 + auth 4 + status 4 + logo 2)
/// المرحلة التالية: باقي الـ 40+ أيقونة
///
/// الاستخدام:
///   BrandIcon(BrandIcons.home, size: 24, color: theme.primary)
class BrandIcon extends StatelessWidget {
  final BrandIconData iconData;
  final double size;
  final Color? color;

  const BrandIcon(this.iconData, {super.key, this.size = 24, this.color});

  @override
  Widget build(BuildContext context) {
    final iconColor = color ?? Theme.of(context).colorScheme.onSurface;
    return SizedBox(
      width: size,
      height: size,
      child: CustomPaint(painter: _BrandIconPainter(iconData, iconColor)),
    );
  }
}

/// Icon data — كل أيقونة هي دالة ترسم على Canvas
typedef BrandIconData = void Function(Canvas canvas, Size size, Paint paint);

class _BrandIconPainter extends CustomPainter {
  final BrandIconData iconData;
  final Color color;

  _BrandIconPainter(this.iconData, this.color);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..style = PaintingStyle.stroke
      ..strokeWidth = size.width * 0.08
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;
    iconData(canvas, size, paint);
  }

  @override
  bool shouldRepaint(covariant _BrandIconPainter old) => color != old.color;
}

/// أيقونات البراند — كل أيقونة هي static method
class BrandIcons {
  BrandIcons._();

  // ═══════════════════════════════════════════════════
  // ─── التنقل (Navigation) — 5 أيقونات ────────────
  // ═══════════════════════════════════════════════════

  static void home(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    final path = Path()
      ..moveTo(w * 0.1, h * 0.45)
      ..lineTo(w * 0.5, h * 0.12)
      ..lineTo(w * 0.9, h * 0.45)
      ..moveTo(w * 0.22, h * 0.4)
      ..lineTo(w * 0.22, h * 0.85)
      ..lineTo(w * 0.78, h * 0.85)
      ..lineTo(w * 0.78, h * 0.4);
    c.drawPath(path, p);
  }

  static void wallet(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    final rect = RRect.fromRectAndRadius(
      Rect.fromLTWH(w * 0.08, h * 0.2, w * 0.84, h * 0.6),
      Radius.circular(w * 0.1),
    );
    c.drawRRect(rect, p);
    c.drawCircle(
      Offset(w * 0.72, h * 0.5),
      w * 0.06,
      p..style = PaintingStyle.fill,
    );
    p.style = PaintingStyle.stroke;
    c.drawLine(Offset(w * 0.08, h * 0.35), Offset(w * 0.92, h * 0.35), p);
  }

  static void history(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    c.drawCircle(Offset(w * 0.5, h * 0.5), w * 0.38, p);
    c.drawLine(Offset(w * 0.5, h * 0.25), Offset(w * 0.5, h * 0.5), p);
    c.drawLine(Offset(w * 0.5, h * 0.5), Offset(w * 0.68, h * 0.62), p);
  }

  static void chart(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    final path = Path()
      ..moveTo(w * 0.08, h * 0.75)
      ..lineTo(w * 0.3, h * 0.45)
      ..lineTo(w * 0.55, h * 0.58)
      ..lineTo(w * 0.75, h * 0.25)
      ..lineTo(w * 0.92, h * 0.35);
    c.drawPath(path, p);
    c.drawLine(Offset(w * 0.08, h * 0.88), Offset(w * 0.92, h * 0.88), p);
  }

  static void user(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    c.drawCircle(Offset(w * 0.5, h * 0.32), w * 0.18, p);
    final bodyPath = Path()
      ..moveTo(w * 0.15, h * 0.88)
      ..quadraticBezierTo(w * 0.15, h * 0.6, w * 0.5, h * 0.6)
      ..quadraticBezierTo(w * 0.85, h * 0.6, w * 0.85, h * 0.88);
    c.drawPath(bodyPath, p);
  }

  // ═══════════════════════════════════════════════════
  // ─── المصادقة (Auth) — 4 أيقونات ────────────────
  // ═══════════════════════════════════════════════════

  static void lock(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    final rect = RRect.fromRectAndRadius(
      Rect.fromLTWH(w * 0.18, h * 0.42, w * 0.64, h * 0.48),
      Radius.circular(w * 0.08),
    );
    c.drawRRect(rect, p);
    final archPath = Path()
      ..moveTo(w * 0.3, h * 0.42)
      ..lineTo(w * 0.3, h * 0.3)
      ..quadraticBezierTo(w * 0.3, h * 0.1, w * 0.5, h * 0.1)
      ..quadraticBezierTo(w * 0.7, h * 0.1, w * 0.7, h * 0.3)
      ..lineTo(w * 0.7, h * 0.42);
    c.drawPath(archPath, p);
  }

  static void shield(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    final path = Path()
      ..moveTo(w * 0.5, h * 0.08)
      ..lineTo(w * 0.88, h * 0.25)
      ..lineTo(w * 0.88, h * 0.55)
      ..quadraticBezierTo(w * 0.88, h * 0.82, w * 0.5, h * 0.95)
      ..quadraticBezierTo(w * 0.12, h * 0.82, w * 0.12, h * 0.55)
      ..lineTo(w * 0.12, h * 0.25)
      ..close();
    c.drawPath(path, p);
  }

  static void eye(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    final path = Path()
      ..moveTo(w * 0.05, h * 0.5)
      ..quadraticBezierTo(w * 0.5, h * 0.15, w * 0.95, h * 0.5)
      ..quadraticBezierTo(w * 0.5, h * 0.85, w * 0.05, h * 0.5);
    c.drawPath(path, p);
    c.drawCircle(Offset(w * 0.5, h * 0.5), w * 0.12, p);
  }

  static void key(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    c.drawCircle(Offset(w * 0.35, h * 0.35), w * 0.2, p);
    c.drawLine(Offset(w * 0.5, h * 0.48), Offset(w * 0.85, h * 0.82), p);
    c.drawLine(Offset(w * 0.72, h * 0.68), Offset(w * 0.82, h * 0.58), p);
    c.drawLine(Offset(w * 0.62, h * 0.58), Offset(w * 0.72, h * 0.48), p);
  }

  // ═══════════════════════════════════════════════════
  // ─── الحالات (Status) — 4 أيقونات ───────────────
  // ═══════════════════════════════════════════════════

  static void checkCircle(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    c.drawCircle(Offset(w * 0.5, h * 0.5), w * 0.4, p);
    final checkPath = Path()
      ..moveTo(w * 0.3, h * 0.5)
      ..lineTo(w * 0.45, h * 0.65)
      ..lineTo(w * 0.72, h * 0.35);
    c.drawPath(checkPath, p);
  }

  static void warning(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    final path = Path()
      ..moveTo(w * 0.5, h * 0.1)
      ..lineTo(w * 0.92, h * 0.88)
      ..lineTo(w * 0.08, h * 0.88)
      ..close();
    c.drawPath(path, p);
    c.drawLine(Offset(w * 0.5, h * 0.38), Offset(w * 0.5, h * 0.62), p);
    c.drawCircle(
      Offset(w * 0.5, h * 0.74),
      w * 0.025,
      p..style = PaintingStyle.fill,
    );
    p.style = PaintingStyle.stroke;
  }

  static void info(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    c.drawCircle(Offset(w * 0.5, h * 0.5), w * 0.4, p);
    c.drawLine(Offset(w * 0.5, h * 0.42), Offset(w * 0.5, h * 0.68), p);
    c.drawCircle(
      Offset(w * 0.5, h * 0.32),
      w * 0.03,
      p..style = PaintingStyle.fill,
    );
    p.style = PaintingStyle.stroke;
  }

  static void refresh(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    final rect = Rect.fromCenter(
      center: Offset(w * 0.5, h * 0.5),
      width: w * 0.7,
      height: h * 0.7,
    );
    c.drawArc(rect, -0.5, 4.5, false, p);
    // Arrow head
    final path = Path()
      ..moveTo(w * 0.68, h * 0.18)
      ..lineTo(w * 0.78, h * 0.32)
      ..lineTo(w * 0.58, h * 0.32);
    c.drawPath(path, p);
  }

  // ═══════════════════════════════════════════════════
  // ─── الإشعارات — 2 أيقونة ───────────────────────
  // ═══════════════════════════════════════════════════

  static void bell(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    final path = Path()
      ..moveTo(w * 0.2, h * 0.65)
      ..lineTo(w * 0.2, h * 0.42)
      ..quadraticBezierTo(w * 0.2, h * 0.12, w * 0.5, h * 0.12)
      ..quadraticBezierTo(w * 0.8, h * 0.12, w * 0.8, h * 0.42)
      ..lineTo(w * 0.8, h * 0.65)
      ..lineTo(w * 0.88, h * 0.72)
      ..lineTo(w * 0.12, h * 0.72)
      ..close();
    c.drawPath(path, p);
    // clapper
    c.drawLine(Offset(w * 0.5, h * 0.05), Offset(w * 0.5, h * 0.12), p);
    // bottom arc
    final bottomPath = Path()
      ..moveTo(w * 0.38, h * 0.76)
      ..quadraticBezierTo(w * 0.38, h * 0.9, w * 0.5, h * 0.9)
      ..quadraticBezierTo(w * 0.62, h * 0.9, w * 0.62, h * 0.76);
    c.drawPath(bottomPath, p);
  }

  static void settings(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    c.drawCircle(Offset(w * 0.5, h * 0.5), w * 0.15, p);
    // 6 gear teeth
    for (int i = 0; i < 6; i++) {
      final angle = i * 3.14159 / 3;
      final cos = _cos(angle);
      final sin = _sin(angle);
      c.drawLine(
        Offset(w * 0.5 + w * 0.22 * cos, h * 0.5 + h * 0.22 * sin),
        Offset(w * 0.5 + w * 0.36 * cos, h * 0.5 + h * 0.36 * sin),
        p..strokeWidth = s.width * 0.1,
      );
    }
    p.strokeWidth = s.width * 0.08;
    c.drawCircle(Offset(w * 0.5, h * 0.5), w * 0.32, p);
  }

  static void memory(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    // Chip body
    final rect = RRect.fromRectAndRadius(
      Rect.fromLTWH(w * 0.1, h * 0.15, w * 0.8, h * 0.7),
      Radius.circular(w * 0.06),
    );
    c.drawRRect(rect, p);
    // inner lines
    c.drawLine(Offset(w * 0.25, h * 0.3), Offset(w * 0.75, h * 0.3), p);
    c.drawLine(Offset(w * 0.25, h * 0.45), Offset(w * 0.75, h * 0.45), p);
    c.drawLine(Offset(w * 0.25, h * 0.6), Offset(w * 0.75, h * 0.6), p);
    // pins left
    for (int i = 0; i < 4; i++) {
      c.drawLine(
        Offset(w * 0.1, h * 0.22 + h * 0.14 * i),
        Offset(w * 0.18, h * 0.22 + h * 0.14 * i),
        p,
      );
    }
    // pins right
    for (int i = 0; i < 4; i++) {
      c.drawLine(
        Offset(w * 0.9, h * 0.22 + h * 0.14 * i),
        Offset(w * 0.82, h * 0.22 + h * 0.14 * i),
        p,
      );
    }
  }

  static void search(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    c.drawCircle(Offset(w * 0.38, h * 0.38), w * 0.22, p);
    c.drawLine(Offset(w * 0.55, h * 0.55), Offset(w * 0.85, h * 0.85), p);
  }

  static void trophy(Canvas c, Size s, Paint p) {
    final w = s.width, h = s.height;
    final path = Path()
      ..moveTo(w * 0.3, h * 0.15)
      ..lineTo(w * 0.7, h * 0.15)
      ..lineTo(w * 0.7, h * 0.3)
      ..lineTo(w * 0.82, h * 0.3)
      ..lineTo(w * 0.82, h * 0.55)
      ..quadraticBezierTo(w * 0.82, h * 0.75, w * 0.6, h * 0.75)
      ..quadraticBezierTo(w * 0.53, h * 0.7, w * 0.5, h * 0.7)
      ..quadraticBezierTo(w * 0.47, h * 0.7, w * 0.4, h * 0.75)
      ..quadraticBezierTo(w * 0.18, h * 0.75, w * 0.18, h * 0.55)
      ..lineTo(w * 0.18, h * 0.3)
      ..lineTo(w * 0.3, h * 0.3)
      ..close();
    c.drawPath(path, p);
    // handles
    c.drawLine(Offset(w * 0.25, h * 0.85), Offset(w * 0.25, h * 0.7), p);
    c.drawLine(Offset(w * 0.75, h * 0.85), Offset(w * 0.75, h * 0.7), p);
  }

  static double _cos(double a) {
    // Using Taylor series approximation to avoid dart:math import in icons
    // Actually let's just use a lookup since we only have 6 angles
    final normalized = a % (2 * 3.14159265);
    return _cosApprox(normalized);
  }

  static double _sin(double a) {
    return _cos(a - 3.14159265 / 2);
  }

  static double _cosApprox(double x) {
    // Bhaskara I's cosine approximation
    final x2 = x * x;
    final pi2 = 3.14159265 * 3.14159265;
    return (pi2 - 4 * x2) / (pi2 + x2);
  }
}
