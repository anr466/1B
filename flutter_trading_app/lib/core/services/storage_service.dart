import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:trading_app/core/constants/app_constants.dart';
import 'package:trading_app/core/models/user_model.dart';
import 'package:trading_app/core/services/credential_encryption.dart';

/// Storage Service — SharedPreferences wrapper
/// منطق صافي — لا يستورد Flutter UI
class StorageService {
  SharedPreferences? _prefs;
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

  // ─── Tokens (encrypted) ───────────────────────
  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    await _p.setString(
      AppConstants.keyAccessToken,
      CredentialEncryption.encrypt(accessToken),
    );
    await _p.setString(
      AppConstants.keyRefreshToken,
      CredentialEncryption.encrypt(refreshToken),
    );
  }

  String? get accessToken {
    final raw = _p.getString(AppConstants.keyAccessToken);
    if (raw == null || raw.isEmpty) return null;
    return CredentialEncryption.decrypt(raw);
  }

  String? get refreshToken {
    final raw = _p.getString(AppConstants.keyRefreshToken);
    if (raw == null || raw.isEmpty) return null;
    return CredentialEncryption.decrypt(raw);
  }

  Future<void> clearTokens() async {
    await _p.remove(AppConstants.keyAccessToken);
    await _p.remove(AppConstants.keyRefreshToken);
  }

  // Backward-compatible alias used by older auth repository code.
  Future<void> saveToken(String token) async {
    await _p.setString(
      AppConstants.keyAccessToken,
      CredentialEncryption.encrypt(token),
    );
  }

  // Backward-compatible alias used by older auth repository code.
  Future<String?> getToken() async => accessToken;

  // ─── User Data ──────────────────────────────────
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

  // Backward-compatible helper for repositories working with UserModel.
  Future<void> saveUser(UserModel user) async {
    await saveUserData(user.toJson());
    await saveUserId(user.id);
    await saveUserType(user.userType);
    if (user.username.isNotEmpty) {
      await saveUsername(user.username);
    }
  }

  // Backward-compatible helper for repositories working with UserModel.
  Future<UserModel?> getUser() async {
    final data = userData;
    if (data == null) return null;
    return UserModel.fromJson(data);
  }

  // ─── Skin ───────────────────────────────────────
  Future<void> saveSkin(String skinName) async {
    await _p.setString(AppConstants.keySkinName, skinName);
  }

  String get skinName =>
      _p.getString(AppConstants.keySkinName) ?? 'obsidian_titanium';

  // Backward-compatible alias used by older skin provider code.
  String getActiveSkin() => skinName;

  // ─── Theme Mode ─────────────────────────────────
  Future<void> saveThemeMode(String mode) async {
    await _p.setString(AppConstants.keyThemeMode, mode);
  }

  String get themeMode => _p.getString(AppConstants.keyThemeMode) ?? 'dark';

  // ─── Biometric ──────────────────────────────────
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

  // ─── Biometric Credentials ────────────────────
  static const _keyBioUser = 'bio_user';
  static const _keyBioPass = 'bio_pass';

  Future<void> saveBiometricCredentials(String user, String pass) async {
    await _saveCredentials(_keyBioUser, _keyBioPass, user, pass);
  }

  (String?, String?) get biometricCredentials {
    return _getCredentials(_keyBioUser, _keyBioPass);
  }

  Future<void> clearBiometricCredentials() async {
    await _p.remove(_keyBioUser);
    await _p.remove(_keyBioPass);
  }

  // ─── Remember Me Credentials ──────────────────
  Future<void> setRememberMeEnabled(bool enabled) async {
    await _p.setBool(_keyRememberMe, enabled);
  }

  bool get rememberMeEnabled => _p.getBool(_keyRememberMe) ?? false;

  Future<void> saveRememberedCredentials(String user, String pass) async {
    await _saveCredentials(_keyRememberedUser, _keyRememberedPass, user, pass);
  }

  (String?, String?) get rememberedCredentials {
    return _getCredentials(_keyRememberedUser, _keyRememberedPass);
  }

  // ─── Shared credential helpers ─────────────────
  Future<void> _saveCredentials(
    String userKey,
    String passKey,
    String user,
    String pass,
  ) async {
    final userToSave = CredentialEncryption.encrypt(user);
    final passToSave = CredentialEncryption.encrypt(pass);
    await _p.setString(userKey, userToSave);
    await _p.setString(passKey, passToSave);
  }

  (String?, String?) _getCredentials(String userKey, String passKey) {
    final rawUser = _p.getString(userKey);
    final rawPass = _p.getString(passKey);
    if (rawUser == null || rawPass == null) return (null, null);
    final user = CredentialEncryption.decrypt(rawUser);
    final pass = CredentialEncryption.decrypt(rawPass);
    return (user, pass);
  }

  Future<void> clearRememberedCredentials() async {
    await _p.remove(_keyRememberedUser);
    await _p.remove(_keyRememberedPass);
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
    final (rememberedUser, rememberedPass) = rememberedCredentials;

    await _p.clear();

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
    final biometric = biometricEnabled;
    final (rememberedUser, rememberedPass) = rememberedCredentials;
    final (bioUser, bioPass) = biometricCredentials;

    await _p.clear();

    await saveSkin(skin);
    await saveThemeMode(theme);
    await setBalanceHidden(hideBalance);
    await setOnboardingDone(onboarding);
    await setRememberMeEnabled(rememberMe);
    await setBiometricEnabled(biometric);

    if (rememberMe && rememberedUser != null && rememberedPass != null) {
      await saveRememberedCredentials(rememberedUser, rememberedPass);
    }

    if (biometric && bioUser != null && bioPass != null) {
      await saveBiometricCredentials(bioUser, bioPass);
    }
  }

  // Backward-compatible auth cleanup used by older auth repository code.
  Future<void> clearAuth() async {
    await clearTokens();
    await _p.remove(AppConstants.keyUserData);
    await _p.remove(AppConstants.keyUserId);
    await _p.remove(AppConstants.keyUserType);
    await _p.remove(AppConstants.keyUsername);
  }

  // Backward-compatible auth state check used by older auth repository code.
  Future<bool> isLoggedIn() async {
    final token = accessToken;
    return token != null && token.isNotEmpty;
  }
}
