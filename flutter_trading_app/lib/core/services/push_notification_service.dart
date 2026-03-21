import 'dart:async';
import 'dart:ui' show Color;
import 'package:flutter/foundation.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:trading_app/core/constants/api_endpoints.dart';
import 'package:trading_app/core/services/api_service.dart';
import 'package:trading_app/core/services/storage_service.dart';

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
  bool _fcmInitialized = false;
  int? _pollingUserId;
  bool _isCheckingNotifications = false;
  DateTime? _lastCheckAt;

  static const _keyLastNotifId = 'last_notif_id';
  static const _keyFcmToken = 'fcm_token';
  static const Duration _pollInterval = Duration(seconds: 30);
  static const Duration _minimumCheckGap = Duration(seconds: 20);

  PushNotificationService(this._api, this._storage);

  Future<void> start(int userId) async {
    if (_pollingUserId == userId && _pollingTimer?.isActive == true) {
      return;
    }
    await _initializeFcm();
    startPolling(userId);
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
        final title = message.notification?.title ?? data['title'] as String? ?? '1B Trading';
        final body = message.notification?.body ?? data['body'] as String? ?? '';
        data['title'] = title;
        data['body'] = body;

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
        final recoverable = message.contains('SERVICE_NOT_AVAILABLE') ||
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
    if (_isCheckingNotifications) return;
    final now = DateTime.now();
    final lastCheckAt = _lastCheckAt;
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
          onNotificationReceived?.call(Map<String, dynamic>.from(notif));
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
      final id = DateTime.now().millisecondsSinceEpoch ~/ 1000;
      await _localNotifs.show(
        id,
        title,
        body,
        const NotificationDetails(
          android: AndroidNotificationDetails(
            'trading_alerts',
            '1B Trading Alerts',
            channelDescription: 'إشعارات الصفقات والتنبيهات',
            importance: Importance.high,
            priority: Priority.high,
            icon: '@drawable/ic_notification',
            color: Color(0xFF1565C0),
            playSound: true,
            enableVibration: true,
            styleInformation: BigTextStyleInformation(''),
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
