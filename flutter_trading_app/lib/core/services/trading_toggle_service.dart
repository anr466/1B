import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/providers/portfolio_provider.dart';

/// Toggle trading with biometric authentication gate
Future<void> toggleTradingWithBiometric({
  required WidgetRef ref,
  required bool enabled,
  required Future<bool> Function(String reason) biometricAuth,
  required void Function(String message, dynamic type) showMessage,
}) async {
  try {
    final authenticated = await biometricAuth(
      enabled ? 'Confirm start trading' : 'Confirm stop trading',
    );
    if (!authenticated) {
      showMessage('Authentication required', 'warning');
      return;
    }

    // Refresh account trading state
    ref.invalidate(accountTradingProvider);
    await ref.read(accountTradingProvider.notifier).fetch();

    showMessage(
      enabled ? 'Trading started' : 'Trading stopped',
      'success',
    );
  } catch (e) {
    showMessage('Error: $e', 'error');
  }
}
