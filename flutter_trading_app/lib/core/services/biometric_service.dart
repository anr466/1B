import 'package:local_auth/local_auth.dart';

/// Biometric Service — wrapper around local_auth
/// منطق صافي — لا يستورد Flutter UI
class BiometricService {
  final LocalAuthentication _auth = LocalAuthentication();

  /// Human-friendly biometric type detected on this device.
  Future<String> get biometricTypeLabel async {
    final types = await availableTypes;
    if (types.contains(BiometricType.face)) return 'Face';
    if (types.contains(BiometricType.fingerprint)) return 'Fingerprint';
    if (types.contains(BiometricType.iris)) return 'Iris';
    if (types.contains(BiometricType.strong)) return 'Strong Biometric';
    if (types.contains(BiometricType.weak)) return 'Weak Biometric';
    final available = await isAvailable;
    return available ? 'Biometric' : 'Not Supported';
  }

  /// Check if device supports AND has enrolled biometric authentication
  Future<bool> get isAvailable async {
    try {
      final canCheck = await _auth.canCheckBiometrics;
      if (!canCheck) return false;
      final types = await _auth.getAvailableBiometrics();
      return types.isNotEmpty;
    } catch (_) {
      return false;
    }
  }

  /// Get available biometric types
  Future<List<BiometricType>> get availableTypes async {
    try {
      return await _auth.getAvailableBiometrics();
    } catch (_) {
      return [];
    }
  }

  /// Prompt user for biometric authentication
  /// Returns true if authentication succeeded
  Future<bool> authenticate({
    String reason = 'سجّل دخولك باستخدام البصمة',
  }) async {
    try {
      final available = await isAvailable;
      if (!available) return false;

      return await _auth.authenticate(
        localizedReason: reason,
        options: const AuthenticationOptions(
          stickyAuth: true,
          biometricOnly: true,
        ),
      );
    } catch (_) {
      return false;
    }
  }
}
