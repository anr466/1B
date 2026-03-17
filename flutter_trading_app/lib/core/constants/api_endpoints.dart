/// API Endpoints — كل المسارات في مكان واحد
/// هذا الملف لا يستورد Flutter — منطق صافي
class ApiEndpoints {
  ApiEndpoints._();

  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:3002/api',
  );

  // ─── Auth ───────────────────────────────────────
  static const String login = '/auth/login';
  static const String register = '/auth/register';
  static const String registerWithPhone = '/auth/register-with-phone';
  static const String sendOtp = '/auth/send-otp';
  static const String verifyOtp = '/auth/verify-otp';
  static const String checkAvailability = '/auth/check-availability';
  static const String sendRegistrationOtp = '/auth/send-registration-otp';
  static const String verifyRegistrationOtp = '/auth/verify-registration-otp';
  static const String forgotPassword = '/auth/forgot-password';
  static const String verifyResetOtp = '/auth/verify-reset-otp';
  static const String resetPassword = '/auth/reset-password';
  static const String sendChangeEmailOtp = '/auth/send-change-email-otp';
  static const String verifyChangeEmailOtp = '/auth/verify-change-email-otp';
  static const String sendChangePasswordOtp = '/auth/send-change-password-otp';
  static const String verifyChangePasswordOtp =
      '/auth/verify-change-password-otp';
  static const String refreshToken = '/auth/refresh';
  static const String validateSession = '/auth/validate-session';
  static const String getVerificationMethods = '/auth/get-verification-methods';
  static const String deleteAccount = '/auth/delete-account';
  static const String sendLoginOtp = '/auth/login/send-otp';
  static const String verifyLoginOtp = '/auth/login/verify-otp';
  static const String resendLoginOtp = '/auth/login/resend-otp';

  // ─── User / Mobile ──────────────────────────────
  static String portfolio(int userId, {String? mode}) {
    var url = '/user/portfolio/$userId';
    if (mode != null) url += '?mode=$mode';
    return url;
  }

  static String stats(int userId, {String? mode}) {
    var url = '/user/stats/$userId';
    if (mode != null) url += '?mode=$mode';
    return url;
  }

  static String trades(int userId, {int? limit, String? mode}) {
    var url = '/user/trades/$userId';
    final query = <String>[];
    if (limit != null) query.add('limit=$limit');
    if (mode != null) query.add('mode=$mode');
    if (query.isNotEmpty) {
      url += '?${query.join('&')}';
    }
    return url;
  }

  static String settings(int userId, {String? mode}) {
    var url = '/user/settings/$userId';
    if (mode != null) url += '?mode=$mode';
    return url;
  }

  static String validateSettings(int userId) =>
      '/user/settings/$userId/validate';
  static String updateSettings(int userId) => '/user/settings/$userId';
  static String tradingMode(int userId) =>
      '/user/settings/trading-mode/$userId';
  static String binanceKeys(int userId) => '/user/binance-keys/$userId';
  static const String saveBinanceKeys = '/user/binance-keys';
  static const String validateBinanceKeys = '/user/binance-keys/validate';
  static String deleteBinanceKey(int keyId) => '/user/binance-keys/$keyId';
  static String activePositions(int userId, {String? mode}) {
    var url = '/user/active-positions/$userId';
    if (mode != null) url += '?mode=$mode';
    return url;
  }

  static String dailyPnl(int userId, {int days = 90, String? mode}) {
    var url = '/user/daily-pnl/$userId?days=$days';
    if (mode != null) url += '&mode=$mode';
    return url;
  }

  static String portfolioGrowth(int userId, {int days = 30, String? mode}) {
    var url = '/user/portfolio-growth/$userId?days=$days';
    if (mode != null) url += '&mode=$mode';
    return url;
  }

  static String userProfile(int userId) => '/user/profile/$userId';
  static String qualifiedCoins(int userId) => '/user/successful-coins/$userId';
  static String resetData(int userId) => '/user/reset-data/$userId';
  static String dailyStatus(int userId, {String? mode}) {
    var url = '/user/daily-status/$userId';
    if (mode != null) url += '?mode=$mode';
    return url;
  }

  static String notifications(int userId, {int? page, int? limit}) {
    var url = '/user/notifications/$userId';
    final query = <String>[];
    if (page != null) query.add('page=$page');
    if (limit != null) query.add('limit=$limit');
    if (query.isNotEmpty) {
      url += '?${query.join('&')}';
    }
    return url;
  }

  static String notificationsMarkAllRead(int userId) =>
      '/user/notifications/$userId/mark-all-read';
  static String notificationsStats(int userId) =>
      '/user/notifications/$userId/stats';
  static String notificationRead(int notificationId) =>
      '/user/notifications/$notificationId/read';
  static const String notificationSettings = '/user/notifications/settings';
  static const String fcmToken = '/user/fcm-token';
  static String tradeDetail(int tradeId) => '/user/trade/$tradeId';

  // ─── Secure Actions ─────────────────────────────
  static const String secureInitiate = '/user/secure/request-verification';
  static const String secureVerify = '/user/secure/verify-and-execute';

  // ─── Biometric ──────────────────────────────────
  static const String biometricVerify = '/user/biometric/verify';

  // ─── System ─────────────────────────────────────
  static const String systemStatus = '/system/status';

  // ─── Admin ──────────────────────────────────────
  static const String adminUsersAll = '/admin/users/all';
  static const String adminActivityLogs = '/admin/activity-logs';
  static const String adminMlStatus = '/admin/system/ml-status';
  static const String adminErrors = '/admin/errors';
  static const String adminErrorStats = '/admin/errors/stats';
  static const String adminSystemStats = '/admin/system/stats';
  static const String adminConfig = '/admin/config';
  static const String adminSecurityAuditLog = '/admin/security-audit-log';
  static const String adminTradesStats = '/admin/trades/stats';

  static String adminUserDetails(int userId) => '/admin/users/$userId';
  static const String adminCreateUser = '/admin/users/create';
  static String adminUpdateUser(int userId) => '/admin/users/$userId/update';
  static String adminDeleteUser(int userId) => '/admin/users/$userId/delete';
  static String adminToggleUserTrading(int userId) =>
      '/admin/users/$userId/toggle-trading';

  // ─── Admin Trading Control ──────────────────────
  static const String tradingState = '/admin/trading/state';
  static const String tradingStart = '/admin/trading/start';
  static const String tradingStop = '/admin/trading/stop';
  static const String tradingEmergencyStop = '/admin/trading/emergency-stop';
  static const String tradingResetError = '/admin/trading/reset-error';
  static const String adminDemoReset = '/admin/demo/reset';

  // ─── System Status ──────────────────────────────
  static const String systemPublicStatus = '/admin/system/public-status';
  static const String binanceStatus = '/admin/system/binance-status';
  static const String binanceRetry = '/admin/system/binance-retry';
  static const String circuitBreakers = '/admin/system/circuit-breakers';
  static const String circuitBreakersReset =
      '/admin/system/circuit-breakers/reset';

  // Backward-compatible aliases used in some repositories
  static const String adminTradingState = tradingState;
  static const String adminTradingStart = tradingStart;
  static const String adminTradingStop = tradingStop;
  static const String adminEmergencyStop = tradingEmergencyStop;
  static const String adminResetError = tradingResetError;
}
