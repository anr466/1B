import 'dart:async';

/// Unified Debounce Utility — prevents rapid-fire API calls from user interactions
///
/// Usage:
/// ```dart
/// // Simple debounced callback
/// final debouncer = Debouncer(duration: Duration(milliseconds: 500));
/// debouncer.run(() => myApiCall());
///
/// // Debounced Future (waits for completion)
/// await debouncer.runFuture(() => myApiCall());
///
/// // Fire-and-forget with latest value
/// debouncer.queue(() => apiCall(value));
///
/// // Cancel pending
/// debouncer.cancel();
/// ```
class Debouncer {
  final Duration duration;
  Timer? _timer;
  Future<void>? _pendingFuture;
  void Function()? _pendingCallback;

  Debouncer({required this.duration});

  /// Returns true if a debounce is currently pending
  bool get isPending => _timer != null || _pendingFuture != null;

  /// Run a synchronous callback after debounce delay
  /// Subsequent calls cancel the previous timer
  void run(void Function() callback) {
    _pendingCallback = callback;
    _pendingFuture = null;
    _timer?.cancel();
    _timer = Timer(duration, () {
      _pendingCallback?.call();
      _pendingCallback = null;
      _timer = null;
    });
  }

  /// Run an async callback after debounce delay
  /// Returns Future that completes when callback completes
  /// Subsequent calls cancel the previous timer and start fresh
  Future<T> runFuture<T>(Future<T> Function() callback) async {
    // Cancel any existing timer
    _timer?.cancel();
    _timer = null;

    // Create a new completer for this call
    final completer = Completer<T>();

    _timer = Timer(duration, () async {
      _timer = null;
      try {
        final result = await callback();
        if (!completer.isCompleted) completer.complete(result);
      } catch (e) {
        if (!completer.isCompleted) completer.completeError(e);
      }
    });

    return completer.future;
  }

  /// Queue a callback to run after delay (replaces any pending)
  /// Does NOT wait for previous calls
  void queue(void Function() callback) {
    _pendingCallback = callback;
    _pendingFuture = null;
    _timer?.cancel();
    _timer = Timer(duration, () {
      _pendingCallback?.call();
      _pendingCallback = null;
      _timer = null;
    });
  }

  /// Cancel any pending debounce
  void cancel() {
    _timer?.cancel();
    _timer = null;
    _pendingFuture = null;
    _pendingCallback = null;
  }

  /// Dispose and cancel
  void dispose() {
    cancel();
  }
}

/// Extension to add debounce to any void Function() callback
extension DebounceExtension on void Function() {
  /// Creates a debounced version of this callback
  void Function() debounced(Duration duration) {
    final debouncer = Debouncer(duration: duration);
    return () => debouncer.run(this);
  }
}

/// Debounce helper for Riverpod providers
/// Wraps a FutureProvider-like async operation with debouncing
class DebouncedAsync<T> {
  final Duration duration;
  Timer? _debounceTimer;
  Future<T>? _lastResult;

  DebouncedAsync({this.duration = const Duration(milliseconds: 300)});

  Future<T> run(Future<T> Function() operation) async {
    _debounceTimer?.cancel();
    _debounceTimer = Timer(duration, () {
      _lastResult = operation();
    });
    return _lastResult ?? operation();
  }

  void cancel() {
    _debounceTimer?.cancel();
    _debounceTimer = null;
  }

  void dispose() {
    cancel();
    _lastResult = null;
  }
}
