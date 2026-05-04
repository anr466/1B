import 'package:flutter_test/flutter_test.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/models/user_model.dart';

void main() {
  group('AuthState', () {
    test('initial state has correct defaults', () {
      const state = AuthState();

      expect(state.status, AuthStatus.initial);
      expect(state.user, null);
      expect(state.error, null);
    });

    test('isAuthenticated returns true only when authenticated', () {
      const initial = AuthState();
      const authenticated = AuthState(status: AuthStatus.authenticated);
      const unauthenticated = AuthState(status: AuthStatus.unauthenticated);
      const loading = AuthState(status: AuthStatus.loading);

      expect(initial.isAuthenticated, false);
      expect(authenticated.isAuthenticated, true);
      expect(unauthenticated.isAuthenticated, false);
      expect(loading.isAuthenticated, false);
    });

    test('isLoading returns true only when loading', () {
      const initial = AuthState();
      const authenticated = AuthState(status: AuthStatus.authenticated);
      const unauthenticated = AuthState(status: AuthStatus.unauthenticated);
      const loading = AuthState(status: AuthStatus.loading);

      expect(initial.isLoading, false);
      expect(authenticated.isLoading, false);
      expect(unauthenticated.isLoading, false);
      expect(loading.isLoading, true);
    });

    test('isAdmin returns user.isAdmin', () {
      final adminUser = UserModel(
        id: 1,
        username: 'admin',
        email: 'admin@test.com',
        userType: 'admin',
      );

      final normalUser = UserModel(
        id: 2,
        username: 'user',
        email: 'user@test.com',
        userType: 'user',
      );

      final stateWithAdmin = AuthState(
        status: AuthStatus.authenticated,
        user: adminUser,
      );
      final stateWithUser = AuthState(
        status: AuthStatus.authenticated,
        user: normalUser,
      );

      expect(stateWithAdmin.isAdmin, true);
      expect(stateWithUser.isAdmin, false);
    });

    test('isAdmin returns false when user is null', () {
      const state = AuthState(status: AuthStatus.authenticated);
      expect(state.isAdmin, false);
    });

    test('copyWith preserves unchanged fields', () {
      final originalUser = UserModel(
        id: 1,
        username: 'test',
        email: 'test@test.com',
      );

      final state = AuthState(
        status: AuthStatus.authenticated,
        user: originalUser,
        error: 'Some error',
      );

      final updated = state.copyWith(error: null);

      expect(updated.status, AuthStatus.authenticated);
      expect(updated.user, originalUser);
      expect(updated.error, null);
    });

    test('copyWith allows changing status', () {
      const state = AuthState(status: AuthStatus.loading);

      final updated = state.copyWith(status: AuthStatus.authenticated);

      expect(updated.status, AuthStatus.authenticated);
    });

    test('copyWith allows changing user', () {
      final user1 = UserModel(
        id: 1,
        username: 'user1',
        email: 'user1@test.com',
      );
      final user2 = UserModel(
        id: 2,
        username: 'user2',
        email: 'user2@test.com',
      );

      final state = AuthState(status: AuthStatus.authenticated, user: user1);

      final updated = state.copyWith(user: user2);

      expect(updated.user, user2);
      expect(updated.status, AuthStatus.authenticated);
    });

    test('copyWith with null user preserves original', () {
      final user = UserModel(id: 1, username: 'test', email: 'test@test.com');

      final state = AuthState(status: AuthStatus.authenticated, user: user);

      final updated = state.copyWith(user: null);

      expect(updated.user, user);
    });
  });

  group('AuthStatus enum', () {
    test('has all expected values', () {
      expect(AuthStatus.values, contains(AuthStatus.initial));
      expect(AuthStatus.values, contains(AuthStatus.authenticated));
      expect(AuthStatus.values, contains(AuthStatus.unauthenticated));
      expect(AuthStatus.values, contains(AuthStatus.loading));
      expect(AuthStatus.values.length, 4);
    });
  });
}
