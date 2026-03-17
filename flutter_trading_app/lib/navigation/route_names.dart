/// Route Names — كل أسماء المسارات في مكان واحد
class RouteNames {
  RouteNames._();

  // ─── Auth ───────────────────────────────────────
  static const String splash = '/splash';
  static const String login = '/login';
  static const String register = '/register';
  static const String otpVerification = '/otp-verification';
  static const String forgotPassword = '/forgot-password';
  static const String resetPassword = '/reset-password';

  // ─── Main (Shell) ───────────────────────────────
  static const String dashboard = '/dashboard';
  static const String portfolio = '/portfolio';
  static const String trades = '/trades';
  static const String analytics = '/analytics';
  static const String profile = '/profile';

  // ─── User ───────────────────────────────────────
  static const String tradeDetail = '/trades/detail';
  static const String tradingSettings = '/settings/trading';
  static const String binanceKeys = '/settings/binance-keys';
  static const String notifications = '/notifications';
  static const String notificationSettings = '/settings/notifications';
  static const String securitySettings = '/settings/security';
  static const String skinPicker = '/settings/skin';

  // ─── Admin ──────────────────────────────────────
  static const String adminDashboard = '/admin/dashboard';
  static const String tradingControl = '/admin/trading-control';
  static const String userManagement = '/admin/users';
  static const String systemLogs = '/admin/logs';
  static const String errorDetails = '/admin/logs/error';

  // ─── Onboarding ─────────────────────────────────
  static const String onboarding = '/onboarding';

  /// Auth routes that don't require authentication
  static const Set<String> authRoutes = {
    splash,
    onboarding,
    login,
    register,
    otpVerification,
    forgotPassword,
    resetPassword,
  };
}
