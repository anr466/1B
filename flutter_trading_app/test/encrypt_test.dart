import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:encrypt/encrypt.dart';

void main() {
  test('encrypt package with fixed zero IV', () {
    final key = Key.fromUtf8('1BTr4d1ngS3cur3K3y2024SecureApp!');
    // Fixed IV (16 zero bytes) - same as CredentialEncryption
    final iv = IV(Uint8List(16));
    final encrypter = Encrypter(AES(key));
    
    final plainText = 'skaka466@gmail.com';
    final encrypted = encrypter.encrypt(plainText, iv: iv);
    
    // ignore: avoid_print
    print('Plain: $plainText');
    // ignore: avoid_print
    print('Encrypted base64: ${encrypted.base64}');
    // ignore: avoid_print
    print('Encrypted bytes length: ${encrypted.bytes.length}');
    // ignore: avoid_print
    print('IV is zeros: ${iv.bytes.every((b) => b == 0)}');
    
    // Test decrypt
    final decrypted = encrypter.decrypt(encrypted, iv: iv);
    // ignore: avoid_print
    print('Decrypted: $decrypted');
    
    // Test decrypt64
    final decrypted2 = encrypter.decrypt64(encrypted.base64, iv: iv);
    // ignore: avoid_print
    print('Decrypt64: $decrypted2');
    
    expect(decrypted, equals(plainText));
    expect(decrypted2, equals(plainText));
    
    // Test deterministic encryption - same input should produce same output
    final encrypted2 = encrypter.encrypt(plainText, iv: iv);
    // ignore: avoid_print
    print('Encrypted again: ${encrypted2.base64}');
    expect(encrypted.base64, equals(encrypted2.base64));
  });
  
  test('decrypt legacy stored data', () {
    // The actual stored data from SharedPreferences
    final key = Key.fromUtf8('1BTr4d1ngS3cur3K3y2024SecureApp!');
    final iv = IV(Uint8List(16));
    final encrypter = Encrypter(AES(key));
    
    // Stored encrypted email (without prefix)
    final storedEmail = 'iKbch4H/lFxC4fyfystFftIwe2kmNBVZrCtijipmJSnkQaQGdtwVQqlw8u0MzHvVYkBOkYeSxqKuFwwHRrJoaA==';
    
    // Try to decrypt with zero IV
    try {
      final decrypted = encrypter.decrypt64(storedEmail, iv: iv);
      // ignore: avoid_print
      print('Decrypted stored email: $decrypted');
    } catch (e) {
      // ignore: avoid_print
      print('Failed to decrypt with zero IV: $e');
      
      // Try extracting IV from first 16 bytes
      final encrypted = Encrypted.fromBase64(storedEmail);
      final data = encrypted.bytes;
      // ignore: avoid_print
      print('Stored data length: ${data.length}');
      
      if (data.length >= 48) {
        final extractedIv = IV(data.sublist(0, 16));
        final cipherText = data.sublist(16);
        try {
          final decrypter = Encrypter(AES(key));
          final result = decrypter.decrypt(Encrypted(cipherText), iv: extractedIv);
          // ignore: avoid_print
          print('Decrypted with extracted IV: $result');
        } catch (e2) {
          // ignore: avoid_print
          print('Failed with extracted IV: $e2');
        }
      }
    }
  });
}
