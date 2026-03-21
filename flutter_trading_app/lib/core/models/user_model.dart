/// Unified User Model — بيانات المستخدم الموحّد
/// يدعم جميع الحقول من الباكند (camelCase + snake_case)
/// منطق صافي — لا يستورد Flutter
class UserModel {
  final int id;
  final String username;
  final String email;
  final String? name;
  final String? fullName;
  final String? phoneNumber;
  final String userType;
  final String tradingMode;
  final bool hasBinanceKeys;
  final bool tradingEnabled;
  final bool isActive;
  final bool emailVerified;
  final bool biometricEnabled;
  final String? createdAt;
  final String? lastLogin;

  const UserModel({
    required this.id,
    required this.username,
    required this.email,
    this.name,
    this.fullName,
    this.phoneNumber,
    this.userType = 'user',
    this.tradingMode = '',
    this.hasBinanceKeys = false,
    this.tradingEnabled = false,
    this.isActive = true,
    this.emailVerified = false,
    this.biometricEnabled = false,
    this.createdAt,
    this.lastLogin,
  });

  bool get isAdmin => userType == 'admin';
  String get displayName =>
      fullName ??
      name ??
      (username.isNotEmpty ? username : email.split('@').first);

  static int _asInt(dynamic value, {int fallback = 0}) {
    if (value is int) return value;
    if (value is num) return value.toInt();
    return int.tryParse('$value') ?? fallback;
  }

  factory UserModel.fromJson(Map<String, dynamic> json) {
    return UserModel(
      id: _asInt(json['id'] ?? json['userId'] ?? json['user_id']),
      username: (json['username'] ?? json['userName'] ?? '') as String,
      email: (json['email'] ?? '') as String,
      name: json['name'] as String?,
      fullName: json['fullName'] ?? json['full_name'],
      phoneNumber: json['phone_number'] ?? json['phoneNumber'] ?? json['phone'],
      userType: json['user_type'] ?? json['userType'] ?? json['role'] ?? 'user',
      tradingMode: json['trading_mode'] ?? json['tradingMode'] ?? '',
      hasBinanceKeys:
          json['has_binance_keys'] == true ||
          json['hasBinanceKeys'] == true ||
          json['has_binance_keys'] == 1 ||
          json['hasBinanceKeys'] == 1,
      tradingEnabled:
          json['trading_enabled'] == true ||
          json['tradingEnabled'] == true ||
          json['trading_enabled'] == 1 ||
          json['tradingEnabled'] == 1,
      isActive:
          json['is_active'] != false &&
          json['isActive'] != false &&
          json['is_active'] != 0 &&
          json['isActive'] != 0,
      emailVerified:
          json['email_verified'] == true || json['email_verified'] == 1,
      biometricEnabled:
          json['biometric_enabled'] == true || json['biometric_enabled'] == 1,
      createdAt: json['created_at'] ?? json['createdAt'],
      lastLogin: json['last_login'] ?? json['lastLogin'],
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'userId': id,
    'user_id': id,
    'username': username,
    'userName': username,
    'email': email,
    'name': name,
    'fullName': fullName,
    'full_name': fullName,
    'phoneNumber': phoneNumber,
    'phone_number': phoneNumber,
    'userType': userType,
    'user_type': userType,
    'tradingMode': tradingMode,
    'trading_mode': tradingMode,
    'hasBinanceKeys': hasBinanceKeys,
    'has_binance_keys': hasBinanceKeys,
    'tradingEnabled': tradingEnabled,
    'trading_enabled': tradingEnabled,
    'isActive': isActive,
    'is_active': isActive,
    'emailVerified': emailVerified,
    'email_verified': emailVerified,
    'biometricEnabled': biometricEnabled,
    'biometric_enabled': biometricEnabled,
    'createdAt': createdAt,
    'created_at': createdAt,
    'lastLogin': lastLogin,
    'last_login': lastLogin,
  };

  UserModel copyWith({
    String? email,
    String? name,
    String? fullName,
    String? phoneNumber,
    String? userType,
    String? tradingMode,
    bool? hasBinanceKeys,
    bool? tradingEnabled,
    bool? isActive,
    bool? emailVerified,
    bool? biometricEnabled,
    String? lastLogin,
  }) {
    return UserModel(
      id: id,
      username: username,
      email: email ?? this.email,
      name: name ?? this.name,
      fullName: fullName ?? this.fullName,
      phoneNumber: phoneNumber ?? this.phoneNumber,
      userType: userType ?? this.userType,
      tradingMode: tradingMode ?? this.tradingMode,
      hasBinanceKeys: hasBinanceKeys ?? this.hasBinanceKeys,
      tradingEnabled: tradingEnabled ?? this.tradingEnabled,
      isActive: isActive ?? this.isActive,
      emailVerified: emailVerified ?? this.emailVerified,
      biometricEnabled: biometricEnabled ?? this.biometricEnabled,
      createdAt: createdAt,
      lastLogin: lastLogin ?? this.lastLogin,
    );
  }
}
