import 'package:flutter_test/flutter_test.dart';
import 'package:trading_app/core/services/credential_encryption.dart';

void main() {
  group('CredentialEncryption', () {
    test('encrypt and decrypt roundtrip works correctly', () {
      const plainText = 'mySecretPassword123!@#';

      final encrypted = CredentialEncryption.encrypt(plainText);
      expect(encrypted.isNotEmpty, true);
      expect(encrypted.startsWith('enc_v1:'), true);
      expect(encrypted, isNot(equals(plainText)));

      final decrypted = CredentialEncryption.decrypt(encrypted);
      expect(decrypted, equals(plainText));
    });

    test('encrypt produces consistent output for same input', () {
      const plainText = 'test@example.com';

      final encrypted1 = CredentialEncryption.encrypt(plainText);
      final encrypted2 = CredentialEncryption.encrypt(plainText);

      expect(encrypted1, equals(encrypted2));
    });

    test('decrypt handles legacy encrypted format', () {
      const plainText = 'legacyPassword456';
      final encrypted = CredentialEncryption.encrypt(plainText);

      final decrypted = CredentialEncryption.decrypt(encrypted);
      expect(decrypted, equals(plainText));
    });

    test('decrypt handles plain text (no encryption)', () {
      const plainText = 'plainTextPassword789';

      final decrypted = CredentialEncryption.decrypt(plainText);
      expect(decrypted, equals(plainText));
    });

    test('encrypt handles empty string', () {
      final encrypted = CredentialEncryption.encrypt('');
      expect(encrypted, equals(''));
    });

    test('decrypt handles empty string', () {
      final decrypted = CredentialEncryption.decrypt('');
      expect(decrypted, equals(''));
    });

    test('isEncrypted returns correct values', () {
      const plainText = 'test';
      const encrypted = 'enc_v1:ABC123';

      expect(CredentialEncryption.isEncrypted(plainText), false);
      expect(CredentialEncryption.isEncrypted(encrypted), true);
    });

    test('encrypt handles unicode characters', () {
      const unicodeText = 'كلمة مرور عربية 123!@#';

      final encrypted = CredentialEncryption.encrypt(unicodeText);
      final decrypted = CredentialEncryption.decrypt(encrypted);

      expect(decrypted, equals(unicodeText));
    });

    test('encrypt handles special characters', () {
      const specialChars = '!@#\$%^&*()_+-=[]{}|;:,.<>?/~`';

      final encrypted = CredentialEncryption.encrypt(specialChars);
      final decrypted = CredentialEncryption.decrypt(encrypted);

      expect(decrypted, equals(specialChars));
    });

    test('encrypt handles long passwords', () {
      final longPassword = List.generate(100, (i) => 'a').join();

      final encrypted = CredentialEncryption.encrypt(longPassword);
      final decrypted = CredentialEncryption.decrypt(encrypted);

      expect(decrypted, equals(longPassword));
    });

    test('encrypt handles email addresses', () {
      const email = 'user.name+tag@example-domain.co.uk';

      final encrypted = CredentialEncryption.encrypt(email);
      final decrypted = CredentialEncryption.decrypt(encrypted);

      expect(decrypted, equals(email));
    });

    test('encrypt handles API keys', () {
      const apiKey = 'ABC123XYZ789def456ghi012jkl345mno678pqr901stu234';

      final encrypted = CredentialEncryption.encrypt(apiKey);
      final decrypted = CredentialEncryption.decrypt(encrypted);

      expect(decrypted, equals(apiKey));
    });
  });
}
