import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trading_app/core/services/storage_service.dart';
import 'package:trading_app/features/auth/screens/login_screen.dart';
import 'package:trading_app/main.dart';

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

  Widget buildSubject(StorageService storage) {
    return ProviderScope(
      overrides: [storageServiceProvider.overrideWithValue(storage)],
      child: const MaterialApp(home: LoginScreen()),
    );
  }

  testWidgets(
    'does not show biometric login action when biometric credentials are unavailable',
    (tester) async {
      final storage = await createStorage({});

      await tester.pumpWidget(buildSubject(storage));
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

      await tester.pumpWidget(buildSubject(storage));
      await tester.pumpAndSettle();

      expect(find.text('الدخول بالبصمة'), findsOneWidget);
    },
  );
}
