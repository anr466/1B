import 'package:flutter_test/flutter_test.dart';
import 'package:trading_app/core/models/user_model.dart';

void main() {
  group('UserModel', () {
    test('fromJson parses all fields correctly', () {
      final json = {
        'id': 1,
        'username': 'testuser',
        'email': 'test@example.com',
        'name': 'Test Name',
        'fullName': 'Test Full Name',
        'phone_number': '+1234567890',
        'user_type': 'admin',
        'trading_mode': 'demo',
        'has_binance_keys': true,
        'trading_enabled': true,
        'is_active': true,
        'email_verified': true,
        'biometric_enabled': false,
        'created_at': '2024-01-01T00:00:00Z',
        'last_login': '2024-01-02T00:00:00Z',
      };

      final user = UserModel.fromJson(json);

      expect(user.id, 1);
      expect(user.username, 'testuser');
      expect(user.email, 'test@example.com');
      expect(user.name, 'Test Name');
      expect(user.fullName, 'Test Full Name');
      expect(user.phoneNumber, '+1234567890');
      expect(user.userType, 'admin');
      expect(user.tradingMode, 'demo');
      expect(user.hasBinanceKeys, true);
      expect(user.tradingEnabled, true);
      expect(user.isActive, true);
      expect(user.emailVerified, true);
      expect(user.biometricEnabled, false);
      expect(user.isAdmin, true);
    });

    test('fromJson handles camelCase field names', () {
      final json = {
        'id': 2,
        'userName': 'testuser2',
        'email': 'test2@example.com',
        'userType': 'user',
        'tradingMode': 'real',
        'hasBinanceKeys': false,
        'tradingEnabled': false,
      };

      final user = UserModel.fromJson(json);

      expect(user.id, 2);
      expect(user.username, 'testuser2');
      expect(user.userType, 'user');
      expect(user.tradingMode, 'real');
      expect(user.hasBinanceKeys, false);
      expect(user.isAdmin, false);
    });

    test('fromJson handles snake_case field names', () {
      final json = {
        'user_id': 3,
        'username': 'testuser3',
        'email': 'test3@example.com',
        'user_type': 'admin',
        'trading_mode': 'demo',
        'has_binance_keys': 1,
        'trading_enabled': 1,
        'email_verified': 1,
        'biometric_enabled': 0,
      };

      final user = UserModel.fromJson(json);

      expect(user.id, 3);
      expect(user.username, 'testuser3');
      expect(user.userType, 'admin');
      expect(user.tradingMode, 'demo');
      expect(user.hasBinanceKeys, true);
      expect(user.tradingEnabled, true);
      expect(user.emailVerified, true);
      expect(user.biometricEnabled, false);
    });

    test('toJson outputs all fields with both naming conventions', () {
      final user = UserModel(
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        name: 'Test',
        fullName: 'Test Full',
        phoneNumber: '+1234567890',
        userType: 'admin',
        tradingMode: 'demo',
        hasBinanceKeys: true,
        tradingEnabled: true,
        isActive: true,
        emailVerified: true,
        biometricEnabled: false,
        createdAt: '2024-01-01T00:00:00Z',
        lastLogin: '2024-01-02T00:00:00Z',
      );

      final json = user.toJson();

      expect(json['id'], 1);
      expect(json['userId'], 1);
      expect(json['user_id'], 1);
      expect(json['username'], 'testuser');
      expect(json['fullName'], 'Test Full');
      expect(json['full_name'], 'Test Full');
      expect(json['phoneNumber'], '+1234567890');
      expect(json['phone_number'], '+1234567890');
      expect(json['userType'], 'admin');
      expect(json['user_type'], 'admin');
      expect(json['tradingMode'], 'demo');
      expect(json['trading_mode'], 'demo');
      expect(json['hasBinanceKeys'], true);
      expect(json['has_binance_keys'], true);
    });

    test('copyWith preserves unchanged fields', () {
      final user = UserModel(
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        userType: 'user',
        tradingMode: 'demo',
        hasBinanceKeys: false,
        tradingEnabled: false,
        isActive: true,
        emailVerified: false,
        biometricEnabled: false,
      );

      final updated = user.copyWith(
        emailVerified: true,
        biometricEnabled: true,
      );

      expect(updated.id, 1);
      expect(updated.username, 'testuser');
      expect(updated.email, 'test@example.com');
      expect(updated.emailVerified, true);
      expect(updated.biometricEnabled, true);
      expect(updated.userType, 'user');
    });

    test('displayName returns correct priority', () {
      final user1 = UserModel(
        id: 1,
        username: 'testuser',
        email: 'test@example.com',
        name: 'Name',
        fullName: 'Full Name',
      );
      expect(user1.displayName, 'Full Name');

      final user2 = UserModel(
        id: 2,
        username: 'testuser2',
        email: 'test@example.com',
        name: 'Name2',
        fullName: null,
      );
      expect(user2.displayName, 'Name2');

      final user3 = UserModel(
        id: 3,
        username: 'testuser3',
        email: 'test@example.com',
        name: null,
        fullName: null,
      );
      expect(user3.displayName, 'testuser3');
    });

    test('isAdmin returns true only for admin users', () {
      final adminUser = UserModel(
        id: 1,
        username: 'admin',
        email: 'admin@example.com',
        userType: 'admin',
      );
      expect(adminUser.isAdmin, true);

      final normalUser = UserModel(
        id: 2,
        username: 'user',
        email: 'user@example.com',
        userType: 'user',
      );
      expect(normalUser.isAdmin, false);
    });

    test('fromJson handles missing optional fields gracefully', () {
      final minimalJson = {
        'id': 1,
        'username': 'testuser',
        'email': 'test@example.com',
      };

      final user = UserModel.fromJson(minimalJson);

      expect(user.id, 1);
      expect(user.username, 'testuser');
      expect(user.email, 'test@example.com');
      expect(user.name, null);
      expect(user.fullName, null);
      expect(user.phoneNumber, null);
      expect(user.userType, 'user');
      expect(user.tradingMode, '');
      expect(user.hasBinanceKeys, false);
      expect(user.tradingEnabled, false);
    });

    test('fromJson handles numeric boolean values (1/0)', () {
      final json = {
        'id': 1,
        'username': 'testuser',
        'email': 'test@example.com',
        'has_binance_keys': 1,
        'trading_enabled': 0,
        'email_verified': 1,
        'biometric_enabled': 0,
        'is_active': 1,
      };

      final user = UserModel.fromJson(json);

      expect(user.hasBinanceKeys, true);
      expect(user.tradingEnabled, false);
      expect(user.emailVerified, true);
      expect(user.biometricEnabled, false);
      expect(user.isActive, true);
    });
  });
}
