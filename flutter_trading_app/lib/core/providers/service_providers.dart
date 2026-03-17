import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/repositories/admin_repository.dart';
import 'package:trading_app/core/repositories/notifications_repository.dart';
import 'package:trading_app/core/repositories/portfolio_repository.dart';
import 'package:trading_app/core/repositories/settings_repository.dart';
import 'package:trading_app/core/repositories/trades_repository.dart';
import 'package:trading_app/core/services/api_service.dart';
import 'package:trading_app/core/services/auth_service.dart';
import 'package:trading_app/core/services/biometric_service.dart';
import 'package:trading_app/core/services/push_notification_service.dart';
import 'package:trading_app/main.dart';

/// Service & Repository Providers — مركزية لجميع الخدمات
/// يعتمد على storageServiceProvider المُعرَّف في main.dart

// ─── Services ─────────────────────────────────────
final apiServiceProvider = Provider<ApiService>((ref) {
  final storage = ref.watch(storageServiceProvider);
  return ApiService(storage);
});

final authServiceProvider = Provider<AuthService>((ref) {
  final api = ref.watch(apiServiceProvider);
  final storage = ref.watch(storageServiceProvider);
  return AuthService(api, storage);
});

final biometricServiceProvider = Provider<BiometricService>((ref) {
  return BiometricService();
});

final pushNotificationServiceProvider = Provider<PushNotificationService>((
  ref,
) {
  final api = ref.watch(apiServiceProvider);
  final storage = ref.watch(storageServiceProvider);
  final service = PushNotificationService(api, storage);
  ref.onDispose(service.dispose);
  return service;
});

// ─── Repositories ─────────────────────────────────
final portfolioRepositoryProvider = Provider<PortfolioRepository>((ref) {
  return PortfolioRepository(ref.watch(apiServiceProvider));
});

final tradesRepositoryProvider = Provider<TradesRepository>((ref) {
  return TradesRepository(ref.watch(apiServiceProvider));
});

final settingsRepositoryProvider = Provider<SettingsRepository>((ref) {
  return SettingsRepository(ref.watch(apiServiceProvider));
});

final notificationsRepositoryProvider = Provider<NotificationsRepository>((
  ref,
) {
  return NotificationsRepository(ref.watch(apiServiceProvider));
});

final adminRepositoryProvider = Provider<AdminRepository>((ref) {
  return AdminRepository(ref.watch(apiServiceProvider));
});
