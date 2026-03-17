import 'dart:typed_data';
import 'package:encrypt/encrypt.dart';

/// AES-256 encryption for sensitive credentials stored in SharedPreferences.
/// Uses a fixed app-level key derived from a constant salt.
/// This is NOT equivalent to a hardware-backed keystore, but prevents
/// plain-text credential exposure on device storage.
class CredentialEncryption {
  static const _prefix = 'enc_v1:';

  // 32-byte key for AES-256 (app-specific, not user-specific)
  static final _key = Key.fromUtf8('1BTr4d1ngS3cur3K3y2024SecureApp!');
  // Fixed IV (16 zero bytes) for deterministic encryption
  static final _iv = IV(Uint8List(16));
  static final _encrypter = Encrypter(AES(_key));

  /// Encrypt a plain-text value. Returns prefixed base64-encoded ciphertext.
  static String encrypt(String plainText) {
    if (plainText.isEmpty) return '';
    final encrypted = _encrypter.encrypt(plainText, iv: _iv);
    return '$_prefix${encrypted.base64}';
  }

  /// Decrypt an encrypted value. Returns plain text.
  /// Handles: new prefixed format, legacy raw AES, and plain text pass-through.
  static String decrypt(String value) {
    if (value.isEmpty) return '';

    // ── New format: enc_v1:<base64> ──
    if (value.startsWith(_prefix)) {
      final decrypted = _decryptBase64Payload(value.substring(_prefix.length));
      return decrypted ?? value;
    }

    // ── Legacy format: raw AES-CTR base64 (no prefix) ──
    // AES-CTR never throws, so we validate the result is readable text.
    final legacyDecrypted = _decryptBase64Payload(value);
    if (legacyDecrypted != null && _isReadableText(legacyDecrypted)) {
      return legacyDecrypted;
    }

    // ── Plain text (not encrypted) ──
    return value;
  }

  /// Check if a value is encrypted with the current scheme.
  static bool isEncrypted(String value) => value.startsWith(_prefix);

  static String? _decryptBase64Payload(String payload) {
    try {
      final encrypted = Encrypted.fromBase64(payload);
      final data = encrypted.bytes;

      // Case 1: Data with IV prepended (64+ bytes) - legacy format
      // Case 2: Data without IV (32-48 bytes) - encrypt package format, use zero IV

      if (data.length >= 48 && data.length > 32) {
        // Legacy format: IV (16 bytes) + ciphertext
        try {
          final iv = IV(data.sublist(0, 16));
          final cipherText = data.sublist(16);
          final encrypter = Encrypter(AES(_key));
          final result = encrypter.decrypt(Encrypted(cipherText), iv: iv);
          if (_isReadableText(result)) return result;
        } catch (_) {}
      }

      // Case 2: encrypt package format - use the IV we encrypted with
      // The encrypt package uses random IV, but we need to try with zero IV
      // for backward compatibility with our original implementation
      try {
        final encrypter = Encrypter(AES(_key));
        return encrypter.decrypt64(payload, iv: _iv);
      } catch (_) {}

      return null;
    } catch (_) {
      // retry with normalized base64
      try {
        final normalized = _normalizeBase64(payload);
        return _decryptBase64Payload(normalized);
      } catch (_) {
        return null;
      }
    }
  }

  static String _normalizeBase64(String value) {
    var normalized = value.trim().replaceAll('-', '+').replaceAll('_', '/');
    final remainder = normalized.length % 4;
    if (remainder != 0) {
      normalized = normalized.padRight(
        normalized.length + (4 - remainder),
        '=',
      );
    }
    return normalized;
  }

  /// Returns true if every character is a printable Unicode character
  /// (no binary garbage from a wrong AES-CTR decrypt).
  static bool _isReadableText(String s) {
    if (s.isEmpty) return false;
    for (final c in s.codeUnits) {
      // allow tab, LF, CR; reject other control chars and DEL
      if (c < 32 && c != 9 && c != 10 && c != 13) return false;
      if (c == 127) return false;
    }
    return true;
  }
}
