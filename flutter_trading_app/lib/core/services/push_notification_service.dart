import 'dart:async';
import 'dart:ui' show Color;
import 'package:flutter/foundation.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:trading_app/core/constants/api_endpoints.dart';
import 'package:trading_app/core/services/api_service.dart';
import 'package:trading_app/core/services/storage_service.dart';

/// Notification settings check callback type
typedef NotificationSettingsChecker = Future<Map<String, dynamic>> Function();

/// Push Notification Service — manages Firebase FCM + polling fallback
class PushNotificationService {
  final ApiService _api;
  final StorageService _storage;
  final FirebaseMessaging _messaging = FirebaseMessaging.instance;
  final FlutterLocalNotificationsPlugin _localNotifs =
      FlutterLocalNotificationsPlugin();
  Timer? _pollingTimer;
  StreamSubscription<RemoteMessage>? _onMessageSub;
  StreamSubscription<RemoteMessage>? _onMessageOpenedSub;
  StreamSubscription<String>? _onTokenRefreshSub;
  void Function(Map<String, dynamic> notification)? onNotificationReceived;
  void Function(Map<String, dynamic> data)? onNotificationTapped;
  NotificationSettingsChecker? getNotificationSettings;
  bool _fcmInitialized = false;
  int? _pollingUserId;
  bool _isCheckingNotifications = false;
  DateTime? _lastCheckAt;
  Map<String, dynamic>? _cachedSettings;

  /// ✅ Deduplication set to prevent showing same notification twice
  /// (from both FCM and polling)
  final Set<String> _seenNotificationIds = {};
  static const int _maxSeenIds = 100; // Limit memory usage

  static const _keyLastNotifId = 'last_notif_id';
  static const _keyFcmToken = 'fcm_token';
  static const Duration _pollInterval = Duration(seconds: 10);
  static const Duration _minimumCheckGap = Duration(seconds: 5);

  PushNotificationService(this._api, this._storage);

  Future<void> start(int userId) async {
    if (_pollingUserId == userId && _pollingTimer?.isActive == true) {
      return;
    }
    await _initializeFcm();
    startPolling(userId);
  }

  /// Check if a notification type is enabled based on user settings
  bool _isNotificationTypeEnabled(String? type) {
    final settings = _cachedSettings;
    if (settings == null) return true;

    // If push is disabled globally, don't show any notifications
    if (settings['pushEnabled'] == false) return false;

    final typeStr = type?.toString().toLowerCase() ?? '';

    // Check specific notification type settings
    if (typeStr.contains('trade_opened') || typeStr.contains('new_trade')) {
      return settings['tradeOpenedEnabled'] != false;
    }
    if (typeStr.contains('trade_closed') ||
        typeStr.contains('closed_profit') ||
        typeStr.contains('closed_loss')) {
      return settings['tradeClosedEnabled'] != false;
    }
    if (typeStr.contains('daily') || typeStr.contains('report')) {
      return settings['dailyReportEnabled'] != false;
    }
    if (typeStr.contains('system') || typeStr.contains('alert')) {
      return settings['systemAlertsEnabled'] != false;
    }

    // Default: allow all if settings exist but type doesn't match known types
    return true;
  }

  /// Update cached notification settings
  Future<void> updateSettings(Map<String, dynamic> settings) async {
    _cachedSettings = settings;
  }

  /// Invalidate cached settings - call this when user changes notification settings
  /// to ensure next notification check fetches fresh settings
  void invalidateSettingsCache() {
    _cachedSettings = null;
  }

  /// Force refresh settings from provider - call this to sync with latest settings
  Future<void> refreshSettings() async {
    if (getNotificationSettings != null) {
      _cachedSettings = await getNotificationSettings!();
    }
  }

  /// ✅ Add notification ID to seen set with memory limit
  void _addToSeenIds(String id) {
    _seenNotificationIds.add(id);
    // Limit memory usage by removing oldest entries when exceeding limit
    while (_seenNotificationIds.length > _maxSeenIds) {
      _seenNotificationIds.remove(_seenNotificationIds.first);
    }
  }

  /// Start polling for new notifications (fallback + local list freshness)
  void startPolling(int userId) {
    if (_pollingUserId == userId && _pollingTimer?.isActive == true) {
      return;
    }
    _pollingTimer?.cancel();
    _pollingUserId = userId;
    _pollingTimer = Timer.periodic(
      _pollInterval,
      (_) => _checkNewNotifications(userId),
    );
    // Immediate first check
    _checkNewNotifications(userId);
  }

  /// Stop polling
  void stopPolling() {
    _pollingTimer?.cancel();
    _pollingTimer = null;
    _pollingUserId = null;
    _isCheckingNotifications = false;
    _lastCheckAt = null;
    _onMessageSub?.cancel();
    _onMessageOpenedSub?.cancel();
    _onTokenRefreshSub?.cancel();
    _onMessageSub = null;
    _onMessageOpenedSub = null;
    _onTokenRefreshSub = null;
    _fcmInitialized = false;
  }

  Future<void> _initializeFcm() async {
    if (_fcmInitialized) return;

    try {
      await _messaging.requestPermission(alert: true, badge: true, sound: true);

      final token = await _messaging.getToken();
      if (token != null && token.isNotEmpty) {
        await _storage.saveString(_keyFcmToken, token);
        final registered = await registerFcmToken(token);
        // ignore: avoid_print
        print(
          '[FCM] token=${token.substring(0, token.length > 16 ? 16 : token.length)}... registered=$registered',
        );
      }

      _onTokenRefreshSub = _messaging.onTokenRefresh.listen((newToken) async {
        await _storage.saveString(_keyFcmToken, newToken);
        await registerFcmToken(newToken);
      });

      _onMessageSub = FirebaseMessaging.onMessage.listen((message) {
        final data = Map<String, dynamic>.from(message.data);
        final title =
            message.notification?.title ??
            data['title'] as String? ??
            '1B Trading';
        final body =
            message.notification?.body ?? data['body'] as String? ?? '';
        data['title'] = title;
        data['body'] = body;

        // ✅ Deduplication: Use trade_id + type for consistent key across FCM and Polling
        final notifId = data['trade_id'] != null && data['type'] != null
            ? '${data['trade_id']}_${data['type']}'
            : data['id']?.toString() ?? '${data['timestamp']}_${data['type']}';
        if (_seenNotificationIds.contains(notifId)) {
          return; // Already shown via polling
        }
        _addToSeenIds(notifId);

        // Show heads-up local notification while app is in foreground
        _showLocalNotification(title, body, data);

        onNotificationReceived?.call(data);
      });

      _onMessageOpenedSub = FirebaseMessaging.onMessageOpenedApp.listen((
        message,
      ) {
        final data = Map<String, dynamic>.from(message.data);
        onNotificationTapped?.call(data);
      });

      final initialMessage = await _messaging.getInitialMessage();
      if (initialMessage != null) {
        onNotificationTapped?.call(
          Map<String, dynamic>.from(initialMessage.data),
        );
      }

      _fcmInitialized = true;
    } catch (e) {
      if (kDebugMode) {
        final message = '$e';
        final recoverable =
            message.contains('SERVICE_NOT_AVAILABLE') ||
            message.contains('firebase_messaging/unknown') ||
            message.contains('MissingPluginException');
        print(
          recoverable
              ? '[FCM] disabled for current runtime, polling fallback remains active: $e'
              : '[FCM] init failed: $e',
        );
      }
    }
  }

  /// Check for new notifications from backend
  Future<void> _checkNewNotifications(int userId) async {
    final now = DateTime.now();
    final lastCheckAt = _lastCheckAt;

    // Use atomic check-and-set pattern
    if (_isCheckingNotifications) return;
    if (lastCheckAt != null && now.difference(lastCheckAt) < _minimumCheckGap) {
      return;
    }

    _isCheckingNotifications = true;
    _lastCheckAt = now;

    try {
      final response = await _api.get(
        ApiEndpoints.notifications(userId),
        queryParameters: {'page': 1, 'limit': 5},
      );

      final data = response.data;
      if (data['success'] != true) return;

      final nested = data['data'];
      final notifications =
          (nested is Map ? nested['notifications'] : data['notifications'])
              as List? ??
          [];
      if (notifications.isEmpty) return;

      final lastSeenId = _storage.getInt(_keyLastNotifId) ?? 0;
      int newestId = lastSeenId;

      for (final notif in notifications) {
        final id = notif['id'] is int
            ? notif['id'] as int
            : int.tryParse('${notif['id']}') ?? 0;
        if (id > lastSeenId) {
          // ✅ Deduplication: Use same key as FCM (trade_id + type)
          final tradeId = notif['data']?['trade_id']?.toString();
          final notifType =
              notif['type']?.toString() ?? notif['data']?['type']?.toString();
          final notifId = (tradeId != null && notifType != null)
              ? '${tradeId}_$notifType'
              : '${notif['id'] ?? id}';
          if (_seenNotificationIds.contains(notifId)) {
            continue; // Already shown via FCM
          }
          _addToSeenIds(notifId);

          // Check user notification settings before showing
          if (!_isNotificationTypeEnabled(notifType)) {
            continue; // Skip this notification if disabled by user
          }

          // Show system notification for new items
          final title = notif['title']?.toString() ?? 'إشعار جديد';
          final body =
              notif['message']?.toString() ?? notif['body']?.toString() ?? '';
          final notifData = Map<String, dynamic>.from(notif);

          // Show local notification
          _showLocalNotification(title, body, notifData);

          // Notify app (invalidate providers)
          onNotificationReceived?.call(notifData);

          if (id > newestId) newestId = id;
        }
      }

      if (newestId > lastSeenId) {
        await _storage.setInt(_keyLastNotifId, newestId);
      }
    } catch (_) {
      // Silent fail — polling continues
    } finally {
      _isCheckingNotifications = false;
    }
  }

  /// Show a heads-up local notification while the app is in the foreground
  Future<void> _showLocalNotification(
    String title,
    String body,
    Map<String, dynamic> data,
  ) async {
    try {
      // Determine notification type for better display
      final type =
          data['type']?.toString() ??
          data['notification_type']?.toString() ??
          '';

      String channelId = 'trading_alerts';
      String channelName = '1B Trading Alerts';
      Color color = const Color(0xFF1565C0);

      // Customize based on notification type
      if (type.contains('profit') || type.contains('win')) {
        color = const Color(0xFF4CAF50); // Green for profit
      } else if (type.contains('loss') || type.contains('error')) {
        color = const Color(0xFFF44336); // Red for loss
      } else if (type.contains('trade')) {
        color = const Color(0xFF2196F3); // Blue for trades
      }

      final id = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      await _localNotifs.show(
        id,
        title,
        body,
        NotificationDetails(
          android: AndroidNotificationDetails(
            channelId,
            channelName,
            channelDescription: 'إشعارات الصفقات والتنبيهات',
            importance: Importance.high,
            priority: Priority.high,
            icon: '@mipmap/ic_launcher',
            color: color,
            playSound: true,
            enableVibration: true,
            styleInformation: BigTextStyleInformation(body),
          ),
        ),
      );
    } catch (_) {
      // Silent — foreground notification display is best-effort
    }
  }

  /// Register FCM token with backend
  Future<bool> registerFcmToken(String fcmToken) async {
    try {
      final response = await _api.post(
        ApiEndpoints.fcmToken,
        data: {'fcm_token': fcmToken, 'platform': 'android'},
      );
      return response.data['success'] == true;
    } catch (_) {
      return false;
    }
  }

  /// Unregister FCM token from backend
  Future<bool> unregisterFcmToken(String fcmToken) async {
    try {
      await _api.delete(ApiEndpoints.fcmToken, data: {'fcm_token': fcmToken});
      return true;
    } catch (_) {
      return false;
    }
  }

  /// Parse notification data for routing
  static NotificationAction parseAction(Map<String, dynamic> data) {
    final type =
        data['type']?.toString() ?? data['notification_type']?.toString() ?? '';
    final entityId =
        data['entity_id']?.toString() ?? data['trade_id']?.toString();

    switch (type) {
      case 'trade_opened':
      case 'trade_signal':
        return const NotificationAction(routeName: 'trades');
      case 'trade_closed':
      case 'trade_completed':
      case 'trade_closed_profit':
      case 'trade_closed_loss':
        return NotificationAction(
          routeName: 'trade_detail',
          params: entityId != null ? {'tradeId': entityId} : {},
        );
      case 'portfolio_update':
      case 'balance_update':
        return const NotificationAction(routeName: 'portfolio');
      case 'system_alert':
      case 'alert':
        return const NotificationAction(routeName: 'notifications');
      default:
        return const NotificationAction(routeName: 'notifications');
    }
  }

  void dispose() {
    stopPolling();
  }
}

/// Represents a navigation action from a notification
class NotificationAction {
  final String routeName;
  final Map<String, String> params;

  const NotificationAction({required this.routeName, this.params = const {}});
}
