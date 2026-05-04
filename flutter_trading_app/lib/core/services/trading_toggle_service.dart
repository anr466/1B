import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/providers/settings_provider.dart';

/// Unified Trading Toggle Service
/// Handles BOTH user self-toggle and admin toggle for another user.
/// Self-toggle → calls SettingsRepository.updateSettings with tradingEnabled
/// Admin toggle → calls AdminRepository.toggleUserTrading
class TradingToggleService {
  final Ref _ref;

  TradingToggleService(this._ref);

  /// Toggle trading for the CURRENT logged-in user (self-toggle)
  Future<bool> toggleSelf({
    required bool enabled,
    String? mode,
    Future<bool> Function(String reason)? biometricAuth,
    required void Function(String message, String type) showMessage,
  }) async {
    try {
      if (biometricAuth != null) {
        final authenticated = await biometricAuth(
          enabled ? 'Confirm start trading' : 'Confirm stop trading',
        );
        if (!authenticated) {
          showMessage('Authentication required', 'warning');
          return false;
        }
      }

      final auth = _ref.read(authProvider);
      final userId = auth.user?.id;
      if (userId == null) {
        showMessage('User not authenticated', 'error');
        return false;
      }

      final settingsRepo = _ref.read(settingsRepositoryProvider);
      final response = await settingsRepo.updateSettings(
        userId,
        {'tradingEnabled': enabled},
        mode: mode,
      );

      if (response['success'] == true) {
        _ref.invalidate(accountTradingProvider);
        await _ref.read(accountTradingProvider.notifier).fetch();
        _ref.invalidate(settingsDataProvider);
        showMessage(
          enabled ? 'Trading enabled' : 'Trading disabled',
          'success',
        );
        return true;
      } else {
        showMessage(response['message'] ?? 'Failed to update trading', 'error');
        return false;
      }
    } catch (e) {
      showMessage('Error: $e', 'error');
      return false;
    }
  }

  /// Toggle trading for ANOTHER user (admin action)
  Future<bool> toggleUser({
    required int targetUserId,
    required bool enabled,
    required void Function(String message, String type) showMessage,
  }) async {
    try {
      final adminRepo = _ref.read(adminRepositoryProvider);
      await adminRepo.toggleUserTrading(targetUserId, enabled);
      showMessage(
        enabled ? 'User trading enabled' : 'User trading disabled',
        'success',
      );
      return true;
    } catch (e) {
      showMessage('Error: $e', 'error');
      return false;
    }
  }
}

/// Provider for easy access
final tradingToggleServiceProvider = Provider<TradingToggleService>((ref) {
  return TradingToggleService(ref);
});
