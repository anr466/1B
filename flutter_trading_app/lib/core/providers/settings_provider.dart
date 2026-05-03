import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/core/models/settings_model.dart';
import 'package:trading_app/core/providers/admin_provider.dart';
import 'package:trading_app/core/providers/auth_provider.dart';
import 'package:trading_app/core/providers/service_providers.dart';

final settingsDataProvider = FutureProvider.autoDispose<SettingsModel>((
  ref,
) async {
  final auth = ref.watch(authProvider);
  if (!auth.isAuthenticated || auth.user == null) throw Exception('غير مصادق');
  final mode = auth.isAdmin ? ref.watch(adminPortfolioModeProvider) : null;
  final repo = ref.watch(settingsRepositoryProvider);
  return repo.getSettings(auth.user!.id, mode: mode);
});
