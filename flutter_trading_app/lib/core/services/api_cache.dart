import 'dart:async';

/// Response Cache Entry — stores cached response with TTL
class _CacheEntry<T> {
  final T data;
  final DateTime expiresAt;

  _CacheEntry({required this.data, required this.expiresAt});

  bool get isExpired => DateTime.now().isAfter(expiresAt);
}

/// Unified API Response Cache — prevents redundant server requests
///
/// Features:
/// - TTL-based expiration
/// - Per-endpoint cache keys
/// - Background refresh before expiry
/// - Cache invalidation
///
/// Usage:
/// ```dart
/// final cache = ApiCache();
///
/// // Try cache first
/// final cached = cache.get<PortfolioModel>('portfolio_123');
/// if (cached != null) return cached;
///
/// // Fetch and cache
/// final data = await api.getPortfolio();
/// cache.set('portfolio_123', data, ttl: Duration(seconds: 30));
/// ```
class ApiCache {
  static final ApiCache _instance = ApiCache._internal();
  factory ApiCache() => _instance;
  ApiCache._internal();

  final Map<String, _CacheEntry<dynamic>> _cache = {};
  final Map<String, Timer> _refreshTimers = {};

  /// Get cached value if not expired
  /// Returns null if not found or expired
  T? get<T>(String key) {
    final entry = _cache[key];
    if (entry == null) return null;
    if (entry.isExpired) {
      _cache.remove(key);
      _cancelRefresh(key);
      return null;
    }
    return entry.data as T;
  }

  /// Get cached value or compute default, but still return cached if exists
  /// Use this for avoiding cache stampede
  T getOrCompute<T>(String key, T Function() compute) {
    final cached = get<T>(key);
    if (cached != null) return cached;
    final computed = compute();
    return computed;
  }

  /// Set a value in cache with TTL
  /// Background refresh will trigger [onRefresh] callback before expiry if provided
  void set<T>(
    String key,
    T data, {
    required Duration ttl,
    void Function()? onRefresh,
  }) {
    _cache[key] = _CacheEntry(data: data, expiresAt: DateTime.now().add(ttl));

    // Schedule background refresh if callback provided
    _cancelRefresh(key);
    if (onRefresh != null) {
      // Refresh 5 seconds before expiry
      final refreshIn = ttl - const Duration(seconds: 5);
      if (refreshIn.isNegative) {
        onRefresh();
      } else {
        _refreshTimers[key] = Timer(refreshIn, () {
          _cancelRefresh(key);
          onRefresh();
        });
      }
    }
  }

  /// Check if key exists and is not expired
  bool contains(String key) {
    final entry = _cache[key];
    if (entry == null) return false;
    if (entry.isExpired) {
      _cache.remove(key);
      _cancelRefresh(key);
      return false;
    }
    return true;
  }

  /// Invalidate a specific cache entry
  void invalidate(String key) {
    _cache.remove(key);
    _cancelRefresh(key);
  }

  /// Invalidate multiple entries by prefix
  void invalidatePrefix(String prefix) {
    final keysToRemove = _cache.keys
        .where((k) => k.startsWith(prefix))
        .toList();
    for (final key in keysToRemove) {
      _cache.remove(key);
      _cancelRefresh(key);
    }
  }

  /// Invalidate all cache entries matching a predicate
  void invalidateWhere(bool Function(String key, dynamic value) predicate) {
    final keysToRemove = <String>[];
    for (final entry in _cache.entries) {
      if (predicate(entry.key, entry.value.data)) {
        keysToRemove.add(entry.key);
      }
    }
    for (final key in keysToRemove) {
      _cache.remove(key);
      _cancelRefresh(key);
    }
  }

  /// Clear all cache
  void clear() {
    _cache.clear();
    for (final timer in _refreshTimers.values) {
      timer.cancel();
    }
    _refreshTimers.clear();
  }

  /// Get time remaining until expiry
  Duration? getTimeRemaining(String key) {
    final entry = _cache[key];
    if (entry == null) return null;
    if (entry.isExpired) return Duration.zero;
    return entry.expiresAt.difference(DateTime.now());
  }

  /// Pre-warm cache for known endpoints
  /// Call this on app start for critical data
  void prewarm(String key, dynamic data, {required Duration ttl}) {
    if (!contains(key)) {
      set(key, data, ttl: ttl);
    }
  }

  void _cancelRefresh(String key) {
    _refreshTimers[key]?.cancel();
    _refreshTimers.remove(key);
  }

  /// Get cache statistics for debugging
  Map<String, dynamic> get stats {
    int expired = 0;
    int valid = 0;
    for (final entry in _cache.values) {
      if (entry.isExpired) {
        expired++;
      } else {
        valid++;
      }
    }
    return {
      'totalEntries': _cache.length,
      'validEntries': valid,
      'expiredEntries': expired,
      'activeRefreshTimers': _refreshTimers.length,
    };
  }
}

/// Cache key builder — ensures consistent cache keys across the app
class CacheKeys {
  CacheKeys._();

  static String portfolio(int userId, {String? mode}) =>
      'portfolio_${userId}_${mode ?? 'real'}';

  static String stats(int userId, {String? mode}) =>
      'stats_${userId}_${mode ?? 'real'}';

  static String settings(int userId, {String? mode}) =>
      'settings_${userId}_${mode ?? 'real'}';

  static String activePositions(int userId, {String? mode}) =>
      'positions_${userId}_${mode ?? 'real'}';

  static String dailyStatus(int userId, {String? mode}) =>
      'daily_${userId}_${mode ?? 'real'}';

  static String systemStatus() => 'system_status';

  static String mlStatus({String? mode}) => 'ml_status_${mode ?? 'all'}';

  static String tradesList(int userId, {int page = 1, String? filter}) =>
      'trades_${userId}_page${page}_${filter ?? 'all'}';

  static String notifications(int userId, {int page = 1}) =>
      'notifications_${userId}_page$page';

  static String successfulCoins(int userId, {String? mode}) =>
      'coins_${userId}_${mode ?? 'real'}';

  static String portfolioGrowth(int userId, String period, {String? mode}) =>
      'growth_${userId}_${period}_${mode ?? 'real'}';
}

/// Default TTL values for different endpoint types
class CacheTTL {
  CacheTTL._();

  static const portfolio = Duration(seconds: 30);
  static const stats = Duration(seconds: 30);
  static const settings = Duration(minutes: 5);
  static const activePositions = Duration(seconds: 15);
  static const dailyStatus = Duration(minutes: 1);
  static const systemStatus = Duration(seconds: 30);
  static const mlStatus = Duration(minutes: 2);
  static const tradesList = Duration(minutes: 1);
  static const notifications = Duration(minutes: 2);
  static const successfulCoins = Duration(minutes: 10);
  static const portfolioGrowth = Duration(minutes: 5);
}
