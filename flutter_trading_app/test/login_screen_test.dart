import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trading_app/core/providers/service_providers.dart';
import 'package:trading_app/core/services/biometric_service.dart';
import 'package:trading_app/core/services/storage_service.dart';
import 'package:trading_app/features/auth/screens/login_screen.dart';
import 'package:trading_app/main.dart';

class _FakeBiometricService extends BiometricService {
  _FakeBiometricService(this._available);

  final bool _available;

  @override
  Future<bool> get isAvailable async => _available;

  @override
  Future<bool> authenticate({
    String reason = 'سجّل دخولك باستخدام البصمة',
  }) async {
    return _available;
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Future<StorageService> createStorage(
    Map<String, Object> initialValues,
  ) async {
    SharedPreferences.setMockInitialValues(initialValues);
    final storage = StorageService();
    await storage.init();
    return storage;
  }

  Widget buildSubject(
    StorageService storage, {
    required bool biometricAvailable,
  }) {
    return ProviderScope(
      overrides: [
        storageServiceProvider.overrideWithValue(storage),
        biometricServiceProvider.overrideWithValue(
          _FakeBiometricService(biometricAvailable),
        ),
      ],
      child: const MaterialApp(home: LoginScreen()),
    );
  }

  testWidgets(
    'does not show biometric login action when biometric credentials are unavailable',
    (tester) async {
      final storage = await createStorage({});

      await tester.pumpWidget(
        buildSubject(storage, biometricAvailable: false),
      );
      await tester.pumpAndSettle();

      expect(find.text('الدخول بالبصمة'), findsNothing);
    },
  );

  testWidgets(
    'shows biometric login action when biometric is enabled and credentials are stored',
    (tester) async {
      final storage = await createStorage({});
      await storage.setBiometricEnabled(true);
      await storage.saveBiometricCredentials('user@example.com', 'Password123');

      await tester.pumpWidget(
        buildSubject(storage, biometricAvailable: true),
      );
      await tester.pumpAndSettle();

      expect(find.text('الدخول بالبصمة'), findsOneWidget);
    },
  );
}
