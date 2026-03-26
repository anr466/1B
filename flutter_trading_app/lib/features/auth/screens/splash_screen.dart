import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/constants/app_constants.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/main.dart';
import 'package:trading_app/navigation/route_names.dart';

/// Deep black background — matching brand hero section
const _deepBlack = Color(0xFF060810);

/// Titanium gradient colors & stops (matching final_brand.html)
const _titaniumColors = [
  Color(0xFFD4D4D4),
  Color(0xFFA0A0A0),
  Color(0xFF666666),
  Color(0xFF222222),
  Color(0xFF555555),
  Color(0xFF999999),
  Color(0xFFC0C0C0),
];
const _titaniumStops = [0.0, 0.2, 0.45, 0.50, 0.55, 0.80, 1.0];

/// Splash Screen — brand intro + first-run/auth routing
class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen>
    with TickerProviderStateMixin {
  late final AnimationController _timelineController;
  late final AnimationController _exitController;

  late final Animation<double> _markOpacity;
  late final Animation<double> _markRise;
  late final Animation<double> _wordOpacity;
  late final Animation<double> _wordSpacing;
  late final Animation<double> _exitOpacity;

  Timer? _timeoutTimer;
  bool _navigated = false;

  @override
  void initState() {
    super.initState();

    _timelineController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: AppConstants.splashDurationMs),
    );
    _exitController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 260),
    );

    // Mark: fade in + rise (0.0 → 0.45)
    _markOpacity = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _timelineController,
        curve: const Interval(0.0, 0.45, curve: Curves.easeOut),
      ),
    );
    _markRise = Tween<double>(begin: 18.0, end: 0.0).animate(
      CurvedAnimation(
        parent: _timelineController,
        curve: const Interval(0.0, 0.55, curve: Curves.easeOutCubic),
      ),
    );

    // Word TRADING: fade in + letter-spacing shrink (0.5 → 0.85)
    _wordOpacity = Tween<double>(begin: 0.0, end: 0.5).animate(
      CurvedAnimation(
        parent: _timelineController,
        curve: const Interval(0.5, 0.85, curve: Curves.easeOut),
      ),
    );
    _wordSpacing = Tween<double>(begin: 20.0, end: 10.0).animate(
      CurvedAnimation(
        parent: _timelineController,
        curve: const Interval(0.5, 0.85, curve: Curves.easeOut),
      ),
    );

    // Exit fade
    _exitOpacity = Tween<double>(
      begin: 1.0,
      end: 0.0,
    ).animate(CurvedAnimation(parent: _exitController, curve: Curves.easeOut));

    _timelineController.forward();

    // Start auth flow after animation window
    Future.delayed(
      const Duration(milliseconds: AppConstants.splashDurationMs),
      _startExitThenCheckAuth,
    );

    // Safety timeout
    _timeoutTimer = Timer(
      const Duration(milliseconds: AppConstants.splashTimeoutMs),
      _forceNavigate,
    );
  }

  Future<void> _startExitThenCheckAuth() async {
    if (!mounted || _navigated) return;
    await _exitController.forward();
    if (!mounted || _navigated) return;
    await _checkAuth();
  }

  Future<void> _checkAuth() async {
    if (_navigated) return;

    // Validate stored token with server - restore session if valid
    await ref.read(authProvider.notifier).checkAuth();
    if (!mounted || _navigated) return;

    final authState = ref.read(authProvider);
    if (authState.isAuthenticated) {
      // Check if biometric is enabled and requires verification
      final storage = ref.read(storageServiceProvider);
      final isBiometricEnabled = storage.biometricEnabled;
      final hasBiometricCredentials =
          storage.biometricCredentials.$1 != null &&
          storage.biometricCredentials.$2 != null;
      final trustNotifier = ref.read(biometricTrustProvider.notifier);
      final isTrusted = trustNotifier.isTrusted;

      // If biometric is enabled and NOT trusted, require biometric verification
      if (isBiometricEnabled && hasBiometricCredentials && !isTrusted) {
        // Go to login screen - it will prompt for biometric automatically
        _navigateToLogin();
      } else {
        // Valid session found - go directly to dashboard
        _navigateToDashboard();
      }
    } else {
      // No valid session - go to login
      _navigateToLogin();
    }
  }

  void _navigateToDashboard() {
    if (_navigated || !mounted) return;
    _navigated = true;
    _timeoutTimer?.cancel();

    SchedulerBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.go(RouteNames.dashboard);
    });
  }

  void _forceNavigate() {
    if (_navigated) return;
    _navigated = true;
    _timeoutTimer?.cancel();
    // Force timeout - go to login but don't clear tokens (allow retry)
    ref.read(authProvider.notifier).forceUnauthenticated(clearTokens: false);
    SchedulerBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.go(RouteNames.login);
    });
  }

  void _navigateToLogin({bool sessionExpired = false}) {
    if (_navigated || !mounted) return;
    _navigated = true;
    _timeoutTimer?.cancel();

    SchedulerBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (sessionExpired) {
        context.go('${RouteNames.login}?expired=true');
      } else {
        context.go(RouteNames.login);
      }
    });
  }

  @override
  void dispose() {
    _timeoutTimer?.cancel();
    _timelineController.dispose();
    _exitController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: const Key('splash_screen'),
      backgroundColor: _deepBlack,
      body: FadeTransition(
        opacity: _exitOpacity,
        child: Stack(
          children: [
            // === Subtle grid background ===
            Positioned.fill(child: CustomPaint(painter: _GridPainter())),
            // === Main content ===
            AnimatedBuilder(
              animation: _timelineController,
              builder: (_, __) => Center(
                child: Opacity(
                  opacity: _markOpacity.value,
                  child: Transform.translate(
                    offset: Offset(0, _markRise.value),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        // === THE MARK: 1B titanium gradient + precision cut ===
                        const _SplashBrandMark(fontSize: 160),
                        const SizedBox(height: 40),

                        // === TRADING wordmark ===
                        Opacity(
                          opacity: _wordOpacity.value,
                          child: Text(
                            'T  R  A  D  I  N  G',
                            style: TextStyle(
                              color: const Color(
                                0xFFC8C8C8,
                              ).withValues(alpha: 0.5),
                              fontSize: 14,
                              fontWeight: FontWeight.w600,
                              letterSpacing: _wordSpacing.value,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// The 1B Brand Mark — Titanium gradient with precision cut
class _SplashBrandMark extends StatelessWidget {
  final double fontSize;

  const _SplashBrandMark({required this.fontSize});

  @override
  Widget build(BuildContext context) {
    return ClipPath(
      clipper: _PrecisionCutClipper(),
      child: ShaderMask(
        blendMode: BlendMode.srcIn,
        shaderCallback: (bounds) {
          return const LinearGradient(
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
            letterSpacing: fontSize * -0.06,
            color: Colors.white,
          ),
        ),
      ),
    );
  }
}

/// Subtle grid pattern painter for the background
class _GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0x06FFFFFF)
      ..strokeWidth = 1;

    const step = 100.0;
    for (double x = 0; x < size.width; x += step) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (double y = 0; y < size.height; y += step) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
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
