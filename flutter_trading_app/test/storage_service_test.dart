import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trading_app/core/services/storage_service.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('StorageService', () {
    test('persists onboarding completion state', () async {
      SharedPreferences.setMockInitialValues({});
      final storage = StorageService();
      await storage.init();

      expect(storage.onboardingDone, isFalse);

      await storage.setOnboardingDone(true);

      expect(storage.onboardingDone, isTrue);
    });

    test(
      'clearAll preserves remember-me credentials but clears onboarding state',
      () async {
        SharedPreferences.setMockInitialValues({});
        final storage = StorageService();
        await storage.init();

        await storage.setRememberMeEnabled(true);
        await storage.saveRememberedCredentials(
          'user@example.com',
          'Password123',
        );
        await storage.setOnboardingDone(true);

        await storage.clearAll();

        final (user, pass) = await storage.getRememberedCredentials();
        expect(storage.rememberMeEnabled, isTrue);
        expect(user, 'user@example.com');
        expect(pass, 'Password123');
        expect(storage.onboardingDone, isFalse);
      },
    );
  });
}
