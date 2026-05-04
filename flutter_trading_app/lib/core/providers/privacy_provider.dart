import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:trading_app/main.dart';

/// Balance visibility provider (global + persisted)
class BalanceVisibilityNotifier extends StateNotifier<bool> {
  final Ref _ref;

  BalanceVisibilityNotifier(this._ref) : super(false) {
    _loadPreference();
  }

  void _loadPreference() {
    final storage = _ref.read(storageServiceProvider);
    state = storage.isBalanceHidden;
  }

  Future<void> toggle() async {
    final storage = _ref.read(storageServiceProvider);
    final next = !state;
    state = next;
    await storage.setBalanceHidden(next);
  }
}

final balanceVisibilityProvider =
    StateNotifierProvider<BalanceVisibilityNotifier, bool>((ref) {
      return BalanceVisibilityNotifier(ref);
    });
