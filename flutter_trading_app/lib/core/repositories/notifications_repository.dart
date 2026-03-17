import 'package:trading_app/core/constants/api_endpoints.dart';
import 'package:trading_app/core/constants/app_constants.dart';
import 'package:trading_app/core/models/notification_model.dart';
import 'package:trading_app/core/models/notification_settings_model.dart';
import 'package:trading_app/core/services/api_service.dart';
import 'package:trading_app/core/services/parsing_service.dart';

/// Notifications Repository — data access for notifications
/// منطق صافي — لا يستورد Flutter
class NotificationsRepository {
  final ApiService _api;

  NotificationsRepository(this._api);

  Future<({List<NotificationModel> notifications, int total})> getNotifications(
    int userId, {
    int page = 1,
    int perPage = AppConstants.notificationsPerPage,
  }) async {
    final response = await _api.get(
      ApiEndpoints.notifications(userId),
      queryParameters: {'page': page, 'limit': perPage},
    );
    final data = response.data;
    if (data['success'] == true) {
      final nested = data['data'];
      List rawList;
      int rawTotal;
      if (nested is Map) {
        rawList = (nested['notifications'] ?? []) as List;
        rawTotal = ParsingService.asInt(
          nested['total'],
          fallback: rawList.length,
        );
      } else {
        rawList = (data['notifications'] ?? nested ?? []) as List;
        rawTotal = ParsingService.asInt(
          data['total'],
          fallback: rawList.length,
        );
      }
      final notifications = rawList
          .map((j) => NotificationModel.fromJson(j as Map<String, dynamic>))
          .toList();
      return (notifications: notifications, total: rawTotal);
    }
    throw Exception(data['message'] ?? 'فشل تحميل الإشعارات');
  }

  Future<int> getUnreadCount(int userId) async {
    final response = await _api.get(ApiEndpoints.notificationsStats(userId));
    final data = response.data;
    if (data['success'] == true) {
      final stats = data['stats'] ?? data['data'];
      if (stats is Map) {
        return ParsingService.asInt(stats['unread'] ?? stats['total']);
      }
      return ParsingService.asInt(data['unread_count'] ?? data['unread']);
    }
    throw Exception(
      data['message'] ??
          data['error'] ??
          'فشل تحميل عدد الإشعارات غير المقروءة',
    );
  }

  Future<void> markAllRead(int userId) async {
    final response = await _api.post(
      ApiEndpoints.notificationsMarkAllRead(userId),
    );
    final data = ParsingService.asMap(response.data);
    if (data['success'] != true) {
      throw Exception(
        data['message'] ?? data['error'] ?? 'فشل تحديد جميع الإشعارات كمقروءة',
      );
    }
  }

  Future<void> markOneRead(int notificationId) async {
    final response = await _api.put(
      ApiEndpoints.notificationRead(notificationId),
    );
    final data = ParsingService.asMap(response.data);
    if (data['success'] != true) {
      throw Exception(data['message'] ?? data['error'] ?? 'فشل تحديث الإشعار');
    }
  }

  Future<NotificationSettingsModel> getNotificationSettings() async {
    final response = await _api.get(ApiEndpoints.notificationSettings);
    final data = response.data;
    if (data['success'] == true) {
      final settings = data['data'] ?? data['settings'];
      if (settings is Map) {
        return NotificationSettingsModel.fromJson(
          ParsingService.asMap(settings),
        );
      }
      throw Exception(
        data['message'] ?? data['error'] ?? 'تنسيق إعدادات الإشعارات غير صالح',
      );
    }
    throw Exception(data['message'] ?? 'فشل تحميل إعدادات الإشعارات');
  }

  Future<NotificationSettingsModel> updateNotificationSettings(
    NotificationSettingsModel settings,
  ) async {
    final response = await _api.put(
      ApiEndpoints.notificationSettings,
      data: settings.toJson(),
    );
    final data = response.data;
    if (data['success'] == true) {
      final next = data['data'] ?? data['settings'];
      if (next is Map) {
        return NotificationSettingsModel.fromJson(ParsingService.asMap(next));
      }
      throw Exception(
        data['message'] ?? data['error'] ?? 'تنسيق استجابة حفظ الإعدادات غير صالح',
      );
    }
    throw Exception(data['message'] ?? 'فشل حفظ إعدادات الإشعارات');
  }
}
