import 'dart:convert';
import 'dart:typed_data';
import 'package:encrypt/encrypt.dart';

/// AES-256 encryption for sensitive credentials stored in SharedPreferences.
///
/// Security improvements over previous version:
/// - Random IV per encryption (not fixed zeros)
/// - IV stored alongside ciphertext
/// - AES-CBC mode (not CTR with fixed IV)
/// - Backward compatible: decrypts legacy formats transparently
///
/// NOTE: This is NOT equivalent to a hardware-backed keystore.
/// For production, migrate to flutter_secure_storage.
class CredentialEncryption {
  static const _prefix = 'enc_v2:';
  static const _legacyPrefix = 'enc_v1:';

  // 32-byte key for AES-256
  // TODO: In production, derive this from a device-specific identifier
  // using flutter_secure_storage or platform channel to Android Keystore.
  static final _key = Key.fromUtf8('1BTr4d1ngS3cur3K3y2024SecureApp!');

  /// Encrypt a plain-text value with random IV (AES-CBC).
  /// Returns: `enc_v2:<base64(iv[16] + ciphertext)>`
  static String encrypt(String plainText) {
    if (plainText.isEmpty) return '';
    try {
      final iv = IV.fromSecureRandom(16);
      final encrypter = Encrypter(AES(_key, mode: AESMode.cbc));
      final encrypted = encrypter.encrypt(plainText, iv: iv);

      // Prepend IV to ciphertext so we can decrypt later
      final combined = Uint8List.fromList([...iv.bytes, ...encrypted.bytes]);
      return '$_prefix${base64.encode(combined)}';
    } catch (_) {
      // Fallback: return plain text if encryption fails
      return plainText;
    }
  }

  /// Decrypt an encrypted value.
  /// Handles: v2 (random IV CBC), v1 (fixed IV CTR), legacy raw AES, plain text.
  static String decrypt(String value) {
    if (value.isEmpty) return '';

    // ── v2 format: enc_v2:<base64(iv[16] + ciphertext)> ──
    if (value.startsWith(_prefix)) {
      final decrypted = _decryptV2(value.substring(_prefix.length));
      if (decrypted != null) return decrypted;
    }

    // ── v1 format: enc_v1:<base64(ciphertext)> with fixed IV ──
    if (value.startsWith(_legacyPrefix)) {
      final decrypted = _decryptV1(value.substring(_legacyPrefix.length));
      if (decrypted != null) return decrypted;
    }

    // ── Legacy raw AES (no prefix) ──
    final legacyDecrypted = _decryptV1(value);
    if (legacyDecrypted != null && _isReadableText(legacyDecrypted)) {
      return legacyDecrypted;
    }

    // ── Plain text (not encrypted) ──
    return value;
  }

  /// Decrypt v2 format: base64(iv[16] + ciphertext) with AES-CBC
  static String? _decryptV2(String payload) {
    try {
      final combined = base64.decode(_normalizeBase64(payload));
      if (combined.length < 32) return null; // Too short

      final iv = IV(combined.sublist(0, 16));
      final cipherText = combined.sublist(16);
      final encrypter = Encrypter(AES(_key, mode: AESMode.cbc));
      final result = encrypter.decrypt(Encrypted(cipherText), iv: iv);
      return _isReadableText(result) ? result : null;
    } catch (_) {
      return null;
    }
  }

  /// Decrypt v1 format: base64(ciphertext) with fixed IV AES-CTR
  static String? _decryptV1(String payload) {
    try {
      final encrypter = Encrypter(AES(_key, mode: AESMode.ctr));
      return encrypter.decrypt64(
        _normalizeBase64(payload),
        iv: IV(Uint8List(16)),
      );
    } catch (_) {
      return null;
    }
  }

  /// Check if a value is encrypted with any known scheme.
  static bool isEncrypted(String value) =>
      value.startsWith(_prefix) || value.startsWith(_legacyPrefix);

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
  /// (no binary garbage from a wrong AES decrypt).
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
