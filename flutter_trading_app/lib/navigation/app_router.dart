import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:trading_app/core/models/trade_model.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/features/admin/screens/admin_background_control_screen.dart';
import 'package:trading_app/features/admin/screens/admin_dashboard_screen.dart';
import 'package:trading_app/features/admin/screens/admin_logs_dashboard_screen.dart';
import 'package:trading_app/features/admin/screens/admin_ml_dashboard_screen.dart';
import 'package:trading_app/features/admin/screens/error_details_screen.dart';
import 'package:trading_app/features/admin/screens/system_logs_screen.dart';
import 'package:trading_app/features/admin/screens/trading_control_screen.dart';
import 'package:trading_app/features/analytics/screens/analytics_screen.dart';
import 'package:trading_app/features/auth/screens/forgot_password_screen.dart';
import 'package:trading_app/features/auth/screens/login_screen.dart';
import 'package:trading_app/features/auth/screens/otp_verification_screen.dart';
import 'package:trading_app/features/auth/screens/register_screen.dart';
import 'package:trading_app/features/auth/screens/reset_password_screen.dart';
import 'package:trading_app/features/auth/screens/splash_screen.dart';
import 'package:trading_app/features/dashboard/screens/dashboard_screen.dart';
import 'package:trading_app/features/notifications/screens/notifications_screen.dart';
import 'package:trading_app/features/notifications/screens/notification_settings_screen.dart';
import 'package:trading_app/features/onboarding/screens/onboarding_screen.dart';
import 'package:trading_app/features/portfolio/screens/portfolio_screen.dart';
import 'package:trading_app/features/profile/screens/profile_screen.dart';
import 'package:trading_app/features/settings/screens/binance_keys_screen.dart';
import 'package:trading_app/features/settings/screens/security_settings_screen.dart';
import 'package:trading_app/features/settings/screens/skin_picker_screen.dart';
import 'package:trading_app/features/settings/screens/trading_settings_screen.dart';
import 'package:trading_app/features/trades/screens/trade_detail_screen.dart';
import 'package:trading_app/features/trades/screens/trades_screen.dart';
import 'package:trading_app/navigation/main_shell.dart';
import 'package:trading_app/navigation/route_names.dart';

// ─── Auth Notifier Listenable Bridge ─────────────────
class _AuthNotifierListenable extends ChangeNotifier {
  _AuthNotifierListenable(Ref ref) {
    ref.listen<AuthState>(authProvider, (_, __) {
      notifyListeners();
    });
  }
}

/// Stable navigator key — created once, reused across rebuilds
final _rootNavigatorKey = GlobalKey<NavigatorState>(debugLabel: 'root');

/// App Router Provider — جميع المسارات مربوطة بشاشات حقيقية
final appRouterProvider = Provider<GoRouter>((ref) {
  final authListenable = _AuthNotifierListenable(ref);

  return GoRouter(
    navigatorKey: _rootNavigatorKey,
    initialLocation: RouteNames.splash,
    refreshListenable: authListenable,
    debugLogDiagnostics: false,

    // ─── Redirect Logic ───────────────────────────
    redirect: (context, state) {
      final auth = ref.read(authProvider);
      final isAuth = auth.isAuthenticated;
      final isAdmin = auth.isAdmin;
      final currentPath = state.matchedLocation;
      final isAuthRoute = RouteNames.authRoutes.contains(currentPath);
      final isOnboardingRoute = currentPath == RouteNames.onboarding;
      final isAdminRoute = currentPath.startsWith('/admin');

      // Don't redirect during initial/loading — stay on current page
      if (auth.status == AuthStatus.initial ||
          auth.status == AuthStatus.loading) {
        return null;
      }

      if (isAuth && isAuthRoute && !isOnboardingRoute) {
        return RouteNames.dashboard;
      }

      // Unauthenticated on splash → login (splash is in authRoutes)
      if (!isAuth && currentPath == RouteNames.splash) {
        return RouteNames.login;
      }

      // Unauthenticated on protected route → login
      if (!isAuth && !isAuthRoute) {
        return RouteNames.login;
      }

      // Authenticated non-admin on admin routes → dashboard
      if (isAuth && isAdminRoute && !isAdmin) {
        return RouteNames.dashboard;
      }

      return null;
    },

    // ─── Routes ───────────────────────────────────
    routes: [
      // ═══ Auth routes ══════════════════════════════
      GoRoute(
        path: RouteNames.splash,
        builder: (_, __) => const SplashScreen(),
      ),
      GoRoute(path: RouteNames.login, builder: (_, __) => const LoginScreen()),
      GoRoute(
        path: RouteNames.register,
        builder: (_, __) => const RegisterScreen(),
      ),
      GoRoute(
        path: RouteNames.otpVerification,
        builder: (_, state) =>
            OtpVerificationScreen(extra: state.extra as Map<String, dynamic>?),
      ),
      GoRoute(
        path: RouteNames.forgotPassword,
        builder: (_, __) => const ForgotPasswordScreen(),
      ),
      GoRoute(
        path: RouteNames.resetPassword,
        builder: (_, state) =>
            ResetPasswordScreen(extra: state.extra as Map<String, dynamic>?),
      ),
      GoRoute(
        path: RouteNames.onboarding,
        builder: (_, __) => const OnboardingScreen(),
      ),

      // ═══ Main shell with bottom navigation ═══════
      ShellRoute(
        builder: (_, __, child) => MainShell(child: child),
        routes: [
          GoRoute(
            path: RouteNames.dashboard,
            pageBuilder: (_, __) =>
                const NoTransitionPage(child: DashboardScreen()),
          ),
          GoRoute(
            path: RouteNames.portfolio,
            name: 'portfolio',
            pageBuilder: (_, __) =>
                const NoTransitionPage(child: PortfolioScreen()),
          ),
          GoRoute(
            path: RouteNames.trades,
            name: 'trades',
            pageBuilder: (_, __) =>
                const NoTransitionPage(child: TradesScreen()),
          ),
          GoRoute(
            path: RouteNames.analytics,
            pageBuilder: (_, __) =>
                const NoTransitionPage(child: AnalyticsScreen()),
          ),
          GoRoute(
            path: RouteNames.profile,
            pageBuilder: (_, __) =>
                const NoTransitionPage(child: ProfileScreen()),
          ),
        ],
      ),

      // ═══ Non-shell routes (push on top) ══════════
      GoRoute(
        path: RouteNames.tradeDetail,
        name: 'trade_detail',
        builder: (_, state) => TradeDetailScreen(
          trade: state.extra is TradeModel ? state.extra as TradeModel : null,
          tradeId: int.tryParse(state.uri.queryParameters['tradeId'] ?? ''),
        ),
      ),
      GoRoute(
        path: RouteNames.tradingSettings,
        builder: (_, __) => const TradingSettingsScreen(),
      ),
      GoRoute(
        path: RouteNames.binanceKeys,
        builder: (_, __) => const BinanceKeysScreen(),
      ),
      GoRoute(
        path: RouteNames.notifications,
        name: 'notifications',
        builder: (_, __) => const NotificationsScreen(),
      ),
      GoRoute(
        path: RouteNames.notificationSettings,
        builder: (_, __) => const NotificationSettingsScreen(),
      ),
      GoRoute(
        path: RouteNames.securitySettings,
        builder: (_, __) => const SecuritySettingsScreen(),
      ),
      GoRoute(
        path: RouteNames.skinPicker,
        builder: (_, __) => const SkinPickerScreen(),
      ),
      GoRoute(
        path: RouteNames.adminDashboard,
        builder: (_, __) => const AdminDashboardScreen(),
      ),
      GoRoute(
        path: RouteNames.tradingControl,
        builder: (_, __) => const TradingControlScreen(),
      ),
      GoRoute(
        path: RouteNames.systemLogs,
        builder: (_, __) => const SystemLogsScreen(),
      ),
      GoRoute(
        path: RouteNames.errorDetails,
        builder: (_, state) => ErrorDetailsScreen(
          errorId: state.extra is int ? state.extra as int : 0,
        ),
      ),
      GoRoute(
        path: RouteNames.adminMlDashboard,
        builder: (_, __) => const AdminMLDashboardScreen(),
      ),
      GoRoute(
        path: RouteNames.adminBackgroundControl,
        builder: (_, __) => const AdminBackgroundControlScreen(),
      ),
      GoRoute(
        path: RouteNames.adminLogsDashboard,
        builder: (_, __) => const AdminLogsDashboardScreen(),
      ),
    ],
  );
});
