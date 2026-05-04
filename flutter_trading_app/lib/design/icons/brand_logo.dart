import 'package:flutter/material.dart';

/// Brand Logo — 1B Trading Final Identity
/// Barlow Condensed Black + Titanium Gradient + Precision Cut
enum LogoVariant { full, mini, mono, outline }

/// Titanium gradient
const _titaniumStops = [0.0, 0.2, 0.45, 0.50, 0.55, 0.80, 1.0];
const _titaniumColors = [
  Color(0xFFD4D4D4),
  Color(0xFFA0A0A0),
  Color(0xFF666666),
  Color(0xFF222222),
  Color(0xFF555555),
  Color(0xFF999999),
  Color(0xFFC0C0C0),
];

class BrandLogo extends StatelessWidget {
  final LogoVariant variant;
  final double size;
  final Color? monoColor;

  const BrandLogo({
    super.key,
    this.variant = LogoVariant.full,
    this.size = 80,
    this.monoColor,
  });

  const BrandLogo.mini({super.key, this.size = 32})
    : variant = LogoVariant.mini,
      monoColor = null;

  const BrandLogo.mono({super.key, this.size = 80, this.monoColor})
    : variant = LogoVariant.mono;

  const BrandLogo.outline({super.key, this.size = 80})
    : variant = LogoVariant.outline,
      monoColor = null;

  @override
  Widget build(BuildContext context) {
    final fontSize = size * 0.85;

    switch (variant) {
      case LogoVariant.full:
        return _buildTitaniumMark(fontSize);
      case LogoVariant.mini:
        return _buildTitaniumMark(fontSize);
      case LogoVariant.mono:
        return _buildMonoMark(
          fontSize,
          monoColor ?? Theme.of(context).colorScheme.onSurface,
        );
      case LogoVariant.outline:
        return Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(size * 0.24),
            border: Border.all(
              color: (monoColor ?? Theme.of(context).colorScheme.primary)
                  .withValues(alpha: 0.6),
              width: 1,
            ),
          ),
          child: Center(child: _buildMonoMark(fontSize * 0.7, Colors.white)),
        );
    }
  }

  double _logoLetterSpacing(double fontSize) => fontSize * -0.06;

  Widget _buildTitaniumMark(double fontSize) {
    return ClipPath(
      clipper: _PrecisionCutClipper(),
      child: ShaderMask(
        blendMode: BlendMode.srcIn,
        shaderCallback: (bounds) {
          return LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: _titaniumColors,
            stops: _titaniumStops,
          ).createShader(bounds);
        },
        child: Text(
          '1B',
          textDirection: TextDirection.ltr,
          style: TextStyle(
            fontFamily: 'BarlowCondensed',
            fontSize: fontSize,
            fontWeight: FontWeight.w900,
            height: 1.0,
            letterSpacing: _logoLetterSpacing(fontSize),
            color: Colors.white,
          ),
        ),
      ),
    );
  }

  Widget _buildMonoMark(double fontSize, Color color) {
    return ClipPath(
      clipper: _PrecisionCutClipper(),
      child: Text(
        '1B',
        textDirection: TextDirection.ltr,
        style: TextStyle(
          fontFamily: 'BarlowCondensed',
          fontSize: fontSize,
          fontWeight: FontWeight.w900,
          height: 1.0,
          letterSpacing: _logoLetterSpacing(fontSize),
          color: color,
        ),
      ),
    );
  }
}

/// Precision cut — angled clip on bottom-right corner
class _PrecisionCutClipper extends CustomClipper<Path> {
  @override
  Path getClip(Size size) {
    final cutX = size.width * 0.92;
    final cutY = size.height * 0.78;
    return Path()
      ..moveTo(0, 0)
      ..lineTo(size.width, 0)
      ..lineTo(size.width, cutY)
      ..lineTo(cutX, size.height)
      ..lineTo(0, size.height)
      ..close();
  }

  @override
  bool shouldReclip(covariant CustomClipper<Path> oldClipper) => false;
}
