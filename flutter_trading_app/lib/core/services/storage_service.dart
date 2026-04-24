import 'dart:convert';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trading_app/core/constants/app_constants.dart';
import 'package:trading_app/core/models/user_model.dart';
import 'package:trading_app/core/services/credential_encryption.dart';

/// Storage Service — Hybrid: FlutterSecureStorage for sensitive data,
/// SharedPreferences for non-sensitive preferences.
/// منطق صافي — لا يستورد Flutter UI
class StorageService {
  SharedPreferences? _prefs;
  static const _secureStorage = FlutterSecureStorage(
    aOptions: AndroidOptions(
      encryptedSharedPreferences: true,
    ),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );

  static const _keyHideBalance = 'hide_balance';
  static const _keyRememberMe = 'remember_me';
  static const _keyRememberedUser = 'remembered_user';
  static const _keyRememberedPass = 'remembered_pass';

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
  }

  SharedPreferences get _p {
    if (_prefs == null) {
      throw StateError('StorageService not initialized. Call init() first.');
    }
    return _prefs!;
  }

  // ─── Tokens (Secure Storage) ───────────────────────
  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    // Double encryption: Secure Storage + App-level encryption
    await _secureStorage.write(
      key: AppConstants.keyAccessToken,
      value: CredentialEncryption.encrypt(accessToken),
    );
    await _secureStorage.write(
      key: AppConstants.keyRefreshToken,
      value: CredentialEncryption.encrypt(refreshToken),
    );
    _cachedAccessToken = accessToken;
    _cachedRefreshToken = refreshToken;
  }

  Future<String?> get accessToken async {
    final raw = await _secureStorage.read(key: AppConstants.keyAccessToken);
    if (raw == null || raw.isEmpty) return null;
    return CredentialEncryption.decrypt(raw);
  }

  Future<String?> get refreshToken async {
    final raw = await _secureStorage.read(key: AppConstants.keyRefreshToken);
    if (raw == null || raw.isEmpty) return null;
    return CredentialEncryption.decrypt(raw);
  }

  // Synchronous getters for providers that need immediate access
  // These will be null until the async read completes, which is acceptable for initial state
  String? _cachedAccessToken;
  String? _cachedRefreshToken;

  Future<void> loadCachedTokens() async {
    final access = await _secureStorage.read(key: AppConstants.keyAccessToken);
    final refresh = await _secureStorage.read(key: AppConstants.keyRefreshToken);
    if (access != null && access.isNotEmpty) _cachedAccessToken = CredentialEncryption.decrypt(access);
    if (refresh != null && refresh.isNotEmpty) _cachedRefreshToken = CredentialEncryption.decrypt(refresh);
  }

  String? get accessTokenSync => _cachedAccessToken;
  String? get refreshTokenSync => _cachedRefreshToken;

  Future<void> clearTokens() async {
    await _secureStorage.delete(key: AppConstants.keyAccessToken);
    await _secureStorage.delete(key: AppConstants.keyRefreshToken);
    _cachedAccessToken = null;
    _cachedRefreshToken = null;
  }

  // Backward-compatible alias
  Future<void> saveToken(String token) async {
    await _secureStorage.write(
      key: AppConstants.keyAccessToken,
      value: CredentialEncryption.encrypt(token),
    );
  }

  Future<String?> getToken() async => await accessToken;

  // ─── User Data (SharedPreferences - non-sensitive) ──
  Future<void> saveUserId(int userId) async {
    await _p.setInt(AppConstants.keyUserId, userId);
  }

  int? get userId => _p.getInt(AppConstants.keyUserId);

  Future<void> saveUserType(String userType) async {
    await _p.setString(AppConstants.keyUserType, userType);
  }

  String? get userType => _p.getString(AppConstants.keyUserType);

  Future<void> saveUsername(String username) async {
    await _p.setString(AppConstants.keyUsername, username);
  }

  String? get username => _p.getString(AppConstants.keyUsername);

  Future<void> saveUserData(Map<String, dynamic> data) async {
    await _p.setString(AppConstants.keyUserData, jsonEncode(data));
  }

  Map<String, dynamic>? get userData {
    final raw = _p.getString(AppConstants.keyUserData);
    if (raw == null) return null;
    return jsonDecode(raw) as Map<String, dynamic>;
  }

  Future<void> saveUser(UserModel user) async {
    await saveUserData(user.toJson());
    await saveUserId(user.id);
    await saveUserType(user.userType);
    if (user.username.isNotEmpty) {
      await saveUsername(user.username);
    }
  }

  Future<UserModel?> getUser() async {
    final data = userData;
    if (data == null) return null;
    return UserModel.fromJson(data);
  }

  // ─── Skin & Theme (SharedPreferences) ──────────────
  Future<void> saveSkin(String skinName) async {
    await _p.setString(AppConstants.keySkinName, skinName);
  }

  String get skinName =>
      _p.getString(AppConstants.keySkinName) ?? 'obsidian_titanium';

  String getActiveSkin() => skinName;

  Future<void> saveThemeMode(String mode) async {
    await _p.setString(AppConstants.keyThemeMode, mode);
  }

  String get themeMode => _p.getString(AppConstants.keyThemeMode) ?? 'dark';

  // ─── Biometric (SharedPreferences for flags, Secure for creds) ─
  Future<void> setBiometricEnabled(bool enabled) async {
    await _p.setBool(AppConstants.keyBiometricEnabled, enabled);
  }

  bool get biometricEnabled =>
      _p.getBool(AppConstants.keyBiometricEnabled) ?? false;

  // ─── Onboarding ─────────────────────────────────
  Future<void> setOnboardingDone(bool done) async {
    await _p.setBool(AppConstants.keyOnboardingDone, done);
  }

  bool get onboardingDone =>
      _p.getBool(AppConstants.keyOnboardingDone) ?? false;

  // ─── Biometric Credentials (Secure Storage) ─────
  static const _keyBioUser = 'bio_user';
  static const _keyBioPass = 'bio_pass';

  Future<void> saveBiometricCredentials(String user, String pass) async {
    await _secureStorage.write(key: _keyBioUser, value: CredentialEncryption.encrypt(user));
    await _secureStorage.write(key: _keyBioPass, value: CredentialEncryption.encrypt(pass));
  }

  Future<(String?, String?)> getBiometricCredentials() async {
    final rawUser = await _secureStorage.read(key: _keyBioUser);
    final rawPass = await _secureStorage.read(key: _keyBioPass);
    if (rawUser == null || rawPass == null) return (null, null);
    return (CredentialEncryption.decrypt(rawUser), CredentialEncryption.decrypt(rawPass));
  }

  Future<void> clearBiometricCredentials() async {
    await _secureStorage.delete(key: _keyBioUser);
    await _secureStorage.delete(key: _keyBioPass);
  }

  // ─── Remember Me Credentials (Secure Storage) ───
  Future<void> setRememberMeEnabled(bool enabled) async {
    await _p.setBool(_keyRememberMe, enabled);
  }

  bool get rememberMeEnabled => _p.getBool(_keyRememberMe) ?? false;

  Future<void> saveRememberedCredentials(String user, String pass) async {
    await _secureStorage.write(key: _keyRememberedUser, value: CredentialEncryption.encrypt(user));
    await _secureStorage.write(key: _keyRememberedPass, value: CredentialEncryption.encrypt(pass));
  }

  Future<(String?, String?)> getRememberedCredentials() async {
    final rawUser = await _secureStorage.read(key: _keyRememberedUser);
    final rawPass = await _secureStorage.read(key: _keyRememberedPass);
    if (rawUser == null || rawPass == null) return (null, null);
    return (CredentialEncryption.decrypt(rawUser), CredentialEncryption.decrypt(rawPass));
  }

  Future<void> clearRememberedCredentials() async {
    await _secureStorage.delete(key: _keyRememberedUser);
    await _secureStorage.delete(key: _keyRememberedPass);
  }

  // ─── Privacy ────────────────────────────────────
  Future<void> setBalanceHidden(bool hidden) async {
    await _p.setBool(_keyHideBalance, hidden);
  }

  bool get isBalanceHidden => _p.getBool(_keyHideBalance) ?? false;

  // ─── Generic Int Storage ───────────────────────
  int? getInt(String key) => _p.getInt(key);
  Future<void> setInt(String key, int value) async =>
      await _p.setInt(key, value);

  // ─── Generic String Storage ────────────────────
  String? getString(String key) => _p.getString(key);
  Future<void> saveString(String key, String value) async =>
      await _p.setString(key, value);

  // ─── Clear All ──────────────────────────────────
  Future<void> clearAll() async {
    final skin = skinName;
    final theme = themeMode;
    final hideBalance = isBalanceHidden;
    final rememberMe = rememberMeEnabled;
    final (rememberedUser, rememberedPass) = await getRememberedCredentials();

    await _p.clear();
    await _secureStorage.deleteAll();

    await saveSkin(skin);
    await saveThemeMode(theme);
    await setBalanceHidden(hideBalance);
    await setOnboardingDone(false);

    if (rememberMe && rememberedUser != null && rememberedPass != null) {
      await setRememberMeEnabled(true);
      await saveRememberedCredentials(rememberedUser, rememberedPass);
    }
  }

  Future<void> clearSessionPreservingLoginOptions() async {
    final skin = skinName;
    final theme = themeMode;
    final hideBalance = isBalanceHidden;
    final onboarding = onboardingDone;
    final rememberMe = rememberMeEnabled;
    final (rememberedUser, rememberedPass) = await getRememberedCredentials();

    await _secureStorage.delete(key: AppConstants.keyAccessToken);
    await _secureStorage.delete(key: AppConstants.keyRefreshToken);
    await _p.remove(AppConstants.keyUserData);
    await _p.remove(AppConstants.keyUserId);
    await _p.remove(AppConstants.keyUserType);
    await _p.remove(AppConstants.keyUsername);

    _cachedAccessToken = null;
    _cachedRefreshToken = null;

    await saveSkin(skin);
    await saveThemeMode(theme);
    await setBalanceHidden(hideBalance);
    await setOnboardingDone(onboarding);
    await setRememberMeEnabled(rememberMe);

    if (rememberMe && rememberedUser != null && rememberedPass != null) {
      await saveRememberedCredentials(rememberedUser, rememberedPass);
    }
  }

  Future<void> clearAuth() async {
    await clearTokens();
    await _p.remove(AppConstants.keyUserData);
    await _p.remove(AppConstants.keyUserId);
    await _p.remove(AppConstants.keyUserType);
    await _p.remove(AppConstants.keyUsername);
  }

  Future<bool> isLoggedIn() async {
    final token = await accessToken;
    return token != null && token.isNotEmpty;
  }
}
