/// App Constants — ثوابت التطبيق
/// هذا الملف لا يستورد Flutter — منطق صافي
class AppConstants {
  AppConstants._();

  // ─── App Info ───────────────────────────────────
  static const String appName = '1B Trading';
  static const String appVersion = '1.0.0';

  // ─── Token Config ───────────────────────────────
  static const int accessTokenExpirySeconds = 86400; // 24h
  static const int refreshTokenExpirySeconds = 2592000; // 30d

  // ─── Timeouts ───────────────────────────────────
  static const int connectTimeoutMs = 15000;
  static const int receiveTimeoutMs = 15000;
  static const int splashDurationMs = 2500;
  static const int splashTimeoutMs = 6000;

  // ─── OTP ────────────────────────────────────────
  static const int otpLength = 6;
  static const int otpResendSeconds = 60;
  static const int otpExpirySeconds = 300;
  static const int otpMaxAttempts = 5;

  // ─── Pagination ─────────────────────────────────
  static const int tradesPerPage = 20;
  static const int notificationsPerPage = 20;
  static const int adminUsersPerPage = 20;
  static const int adminLogsPerPage = 50;
  static const int dashboardRecentTrades = 5;

  // ─── Trading Settings Ranges ────────────────────
  static const double minPositionSizePct = 5.0;
  static const double maxPositionSizePct = 50.0;
  static const int minMaxPositions = 1;
  static const int maxMaxPositions = 10;
  static const double minStopLossPct = 0.5;
  static const double maxStopLossPct = 10.0;
  static const double minTakeProfitPct = 1.0;
  static const double maxTakeProfitPct = 50.0;

  // ─── Storage Keys ───────────────────────────────
  static const String keyAccessToken = 'access_token';
  static const String keyRefreshToken = 'refresh_token';
  static const String keyUserId = 'user_id';
  static const String keyUserType = 'user_type';
  static const String keyUsername = 'username';
  static const String keyUserData = 'user_data';
  static const String keySkinName = 'skin_name';
  static const String keyBiometricEnabled = 'biometric_enabled';
  static const String keyOnboardingDone = 'onboarding_done';
  static const String keyThemeMode = 'theme_mode';

  // ─── Micro-Interaction Durations (ms) ───────────
  static const int microShort = 1500;
  static const int microMedium = 2000;
  static const int microLong = 3000;
}
