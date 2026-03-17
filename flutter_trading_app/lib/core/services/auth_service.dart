import 'package:trading_app/core/constants/api_endpoints.dart';
import 'package:trading_app/core/services/api_service.dart';
import 'package:trading_app/core/services/storage_service.dart';

/// Auth Service — Token management + login/register/logout
/// منطق صافي — لا يستورد Flutter UI
class AuthService {
  final ApiService _api;
  final StorageService _storage;

  AuthService(this._api, this._storage);

  // ─── Login ──────────────────────────────────────
  Future<Map<String, dynamic>> login({
    required String emailOrUsername,
    required String password,
  }) async {
    final identifier = emailOrUsername.trim();
    final isEmail = identifier.contains('@');
    final response = await _api.post(
      ApiEndpoints.login,
      data: {
        if (isEmail) 'email': identifier else 'username': identifier,
        'password': password,
      },
    );
    final data = response.data;
    if (data['success'] == true) {
      await _saveAuthData(data);
    }
    return data;
  }

  // ─── Register (Step 1: Send OTP) ────────────────
  Future<Map<String, dynamic>> sendRegistrationOtp({
    required String email,
    required String username,
    required String password,
    required String phoneNumber,
    required String name,
  }) async {
    final response = await _api.post(
      ApiEndpoints.sendRegistrationOtp,
      data: {'email': email, 'phone': phoneNumber, 'method': 'email'},
    );
    return response.data;
  }

  // ─── Register (Step 2: Verify OTP) ──────────────
  Future<Map<String, dynamic>> verifyRegistrationOtp({
    required String email,
    required String code,
    required String username,
    required String password,
    required String phoneNumber,
    required String name,
  }) async {
    final response = await _api.post(
      ApiEndpoints.verifyRegistrationOtp,
      data: {
        'email': email,
        'otp_code': code,
        'username': username,
        'password': password,
        'phone': phoneNumber,
        'fullName': name,
      },
    );
    final data = response.data;
    if (data['success'] == true) {
      await _saveAuthData(data);
    }
    return data;
  }

  // ─── Check Availability ─────────────────────────
  Future<Map<String, dynamic>> checkAvailability({
    String? email,
    String? username,
    String? phone,
  }) async {
    final response = await _api.post(
      ApiEndpoints.checkAvailability,
      data: {
        if (email != null) 'email': email,
        if (username != null) 'username': username,
        if (phone != null) 'phone': phone,
      },
    );
    return response.data;
  }

  // ─── Forgot Password ───────────────────────────
  Future<Map<String, dynamic>> forgotPassword(
    String email, {
    String method = 'email',
    String? phone,
  }) async {
    final response = await _api.post(
      ApiEndpoints.forgotPassword,
      data: {
        'email': email,
        'method': method,
        if (phone != null && phone.trim().isNotEmpty) 'phone': phone.trim(),
      },
    );
    return response.data;
  }

  Future<Map<String, dynamic>> sendChangePasswordOtp({
    required String oldPassword,
  }) async {
    final response = await _api.post(
      ApiEndpoints.sendChangePasswordOtp,
      data: {'oldPassword': oldPassword, 'old_password': oldPassword},
    );
    return response.data;
  }

  Future<Map<String, dynamic>> sendChangeEmailOtp({
    required int userId,
    required String newEmail,
  }) async {
    final response = await _api.post(
      ApiEndpoints.sendChangeEmailOtp,
      data: {
        'userId': userId,
        'user_id': userId,
        'newEmail': newEmail,
        'new_email': newEmail,
      },
    );
    return response.data;
  }

  // ─── Reset Password ────────────────────────────
  Future<Map<String, dynamic>> resetPassword({
    required String resetToken,
    required String newPassword,
  }) async {
    final response = await _api.post(
      ApiEndpoints.resetPassword,
      data: {
        'resetToken': resetToken,
        'newPassword': newPassword,
        'reset_token': resetToken,
        'new_password': newPassword,
      },
    );
    return response.data;
  }

  Future<Map<String, dynamic>> verifyResetOtp({
    required String email,
    required String otp,
  }) async {
    final response = await _api.post(
      ApiEndpoints.verifyResetOtp,
      data: {'email': email, 'otp': otp},
    );
    return response.data;
  }

  // ─── Verify Change Password OTP ────────────────
  Future<Map<String, dynamic>> verifyChangePasswordOtp({
    required String otp,
    required String newPassword,
  }) async {
    final response = await _api.post(
      ApiEndpoints.verifyChangePasswordOtp,
      data: {
        'otp': otp,
        'otp_code': otp,
        'newPassword': newPassword,
        'new_password': newPassword,
      },
    );
    return response.data;
  }

  // ─── Verify Change Email OTP ──────────────────
  Future<Map<String, dynamic>> verifyChangeEmailOtp({
    required int userId,
    required String otp,
    required String newEmail,
  }) async {
    final response = await _api.post(
      ApiEndpoints.verifyChangeEmailOtp,
      data: {
        'userId': userId,
        'user_id': userId,
        'otp': otp,
        'otp_code': otp,
        'newEmail': newEmail,
        'new_email': newEmail,
      },
    );
    return response.data;
  }

  // ─── Validate Session ──────────────────────────
  Future<Map<String, dynamic>> validateSession() async {
    final response = await _api.get(ApiEndpoints.validateSession);
    return response.data;
  }

  Future<Map<String, dynamic>> restoreSession() async {
    final accessToken = _storage.accessToken;
    if (accessToken == null || accessToken.isEmpty) {
      return {'success': false, 'message': 'لا توجد جلسة محفوظة'};
    }

    try {
      final data = await validateSession();
      if (data['success'] == true) {
        await _saveAuthData(data);
        return data;
      }
      await _storage.clearAuth();
      return data;
    } catch (_) {
      rethrow;
    }
  }

  // ─── Secure Actions (OTP protected) ────────────
  Future<Map<String, dynamic>> requestSecureVerification({
    required String action,
    String method = 'email',
    dynamic newValue,
    String? oldPassword,
  }) async {
    final response = await _api.post(
      ApiEndpoints.secureInitiate,
      data: {
        'action': action,
        'method': method,
        if (newValue != null) 'newValue': newValue,
        if (oldPassword != null && oldPassword.isNotEmpty)
          'oldPassword': oldPassword,
      },
    );
    return response.data;
  }

  Future<Map<String, dynamic>> verifySecureAction({
    required String action,
    required String otp,
    dynamic newValue,
  }) async {
    final response = await _api.post(
      ApiEndpoints.secureVerify,
      data: {
        'action': action,
        'otp': otp,
        if (newValue != null) 'newValue': newValue,
      },
    );
    return response.data;
  }

  // ─── Biometric Verify ──────────────────────────
  Future<Map<String, dynamic>> biometricVerify({
    required int userId,
    required String biometricToken,
    required String deviceId,
  }) async {
    final response = await _api.post(
      ApiEndpoints.biometricVerify,
      data: {
        // Backend current contract expects biometric_data + type.
        // Keep legacy keys too for backward compatibility.
        'biometric_data': biometricToken,
        'type': 'fingerprint',
        'user_id': userId,
        'biometric_token': biometricToken,
        'device_id': deviceId,
      },
    );
    final data = response.data;
    if (data['success'] == true && data['tokens'] != null) {
      await _storage.saveTokens(
        accessToken: data['tokens']['access_token'],
        refreshToken: data['tokens']['refresh_token'],
      );
    }
    return data;
  }

  // ─── Send OTP (generic) ────────────────────────
  Future<Map<String, dynamic>> sendOtp({
    required String email,
    required String type,
    String method = 'email',
  }) async {
    final operationType = type == 'forgot_password' ? 'reset_password' : type;
    final response = await _api.post(
      ApiEndpoints.sendOtp,
      data: {'email': email, 'operation_type': operationType, 'method': method},
    );
    return response.data;
  }

  // ─── Verify OTP (generic) ──────────────────────
  Future<Map<String, dynamic>> verifyOtp({
    required String email,
    required String code,
    required String type,
  }) async {
    final operationType = type == 'forgot_password' ? 'reset_password' : type;
    final response = await _api.post(
      ApiEndpoints.verifyOtp,
      data: {'email': email, 'otp': code, 'operation_type': operationType},
    );
    return response.data;
  }

  // ─── Delete Account ─────────────────────────────
  Future<Map<String, dynamic>> deleteAccount({
    required String password,
    required String confirmation,
  }) async {
    final response = await _api.delete(
      ApiEndpoints.deleteAccount,
      data: {'password': password, 'confirmation': confirmation},
    );
    final data = response.data;
    if (data['success'] == true) {
      await _storage.clearAll();
    }
    return data;
  }

  // ─── Logout ─────────────────────────────────────
  Future<void> logout() async {
    // Invalidate server-side session before clearing local data
    try {
      await _api.post('/auth/logout');
    } catch (_) {
      // Silent — network failure should not block local logout
    }
    await _storage.clearSessionPreservingLoginOptions();
  }

  // ─── Biometric Credentials ────────────────────
  /// Save login credentials locally for explicit biometric sign-in.
  Future<void> saveCredentialsForBiometric(
    String emailOrUsername,
    String password,
  ) async {
    await _storage.saveBiometricCredentials(emailOrUsername, password);
  }

  /// Get saved credentials for explicit biometric sign-in.
  (String?, String?) get biometricCredentials => _storage.biometricCredentials;

  // ─── Session Check ──────────────────────────────
  bool get hasToken =>
      _storage.accessToken != null && _storage.accessToken!.isNotEmpty;

  int? get currentUserId => _storage.userId;
  String? get currentUserType => _storage.userType;
  bool get isAdmin => _storage.userType == 'admin';

  // ─── Private Helpers ────────────────────────────
  Future<void> _saveAuthData(Map<String, dynamic> data) async {
    if (data['tokens'] != null) {
      await _storage.saveTokens(
        accessToken: data['tokens']['access_token'],
        refreshToken: data['tokens']['refresh_token'],
      );
    } else {
      final accessToken = (data['token'] ?? data['access_token'])?.toString();
      final refreshToken = data['refresh_token']?.toString() ?? '';
      if (accessToken != null && accessToken.isNotEmpty) {
        await _storage.saveTokens(
          accessToken: accessToken,
          refreshToken: refreshToken,
        );
      }
    }
    if (data['user'] != null) {
      final user = data['user'];
      await _storage.saveUserId(user['id']);
      await _storage.saveUserType(
        (user['userType'] ?? user['user_type'] ?? 'user').toString(),
      );
      if (user['username'] != null) {
        await _storage.saveUsername(user['username']);
      }
      await _storage.saveUserData(user);
    } else if (data['userId'] != null || data['user_id'] != null) {
      final userId = data['userId'] ?? data['user_id'];
      if (userId is num) {
        await _storage.saveUserId(userId.toInt());
      }
    }
  }
}
