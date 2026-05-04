import 'dart:convert';

import '../services/parsing_service.dart';

/// Notification Model — بيانات إشعار واحد
/// منطق صافي — لا يستورد Flutter
class NotificationModel {
  final int id;
  final int userId;
  final String title;
  final String message;
  final String type;
  final bool isRead;
  final String? createdAt;
  final Map<String, dynamic>? data;

  const NotificationModel({
    required this.id,
    required this.userId,
    required this.title,
    required this.message,
    this.type = 'info',
    this.isRead = false,
    this.createdAt,
    this.data,
  });

  factory NotificationModel.fromJson(Map<String, dynamic> json) {
    final rawData = json['data'];
    Map<String, dynamic>? parsedData;
    if (rawData is Map<String, dynamic>) {
      parsedData = rawData;
    } else if (rawData is Map) {
      parsedData = Map<String, dynamic>.from(rawData);
    } else if (rawData is String && rawData.isNotEmpty) {
      try {
        final decoded = jsonDecode(rawData);
        if (decoded is Map<String, dynamic>) {
          parsedData = decoded;
        } else if (decoded is Map) {
          parsedData = Map<String, dynamic>.from(decoded);
        }
      } catch (_) {}
    }

    return NotificationModel(
      id: ParsingService.asInt(json['id']),
      userId: ParsingService.asInt(json['user_id'] ?? json['userId'] ?? 0),
      title: json['title'] as String? ?? '',
      message: json['message'] as String? ?? '',
      type: json['type'] as String? ?? 'info',
      isRead: json['is_read'] == true || json['is_read'] == 1,
      createdAt: (json['created_at'] ?? json['createdAt'])?.toString(),
      data: parsedData,
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'user_id': userId,
    'title': title,
    'message': message,
    'type': type,
    'is_read': isRead,
    'created_at': createdAt,
    'data': data,
  };
}
