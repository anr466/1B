import 'package:trading_app/core/constants/api_endpoints.dart';
import 'package:trading_app/core/models/system_status_model.dart';
import 'package:trading_app/core/services/api_service.dart';
import 'package:trading_app/core/services/parsing_service.dart';

/// Admin Repository — data access for admin operations
/// منطق صافي — لا يستورد Flutter
class AdminRepository {
  final ApiService _api;

  AdminRepository(this._api);

  bool _isSuccessfulResponse(Map<String, dynamic> data) {
    if (data['success'] == true) return true;
    if (data['success'] == false) return false;
    if (data.containsKey('trading_state') || data.containsKey('state')) {
      return true;
    }
    if (data.containsKey('data') && data['data'] is Map) {
      final nested = ParsingService.asMap(data['data']);
      if (nested['success'] == true) return true;
      if (nested['success'] == false) return false;
      return nested.containsKey('trading_state') || nested.containsKey('state');
    }
    return false;
  }

  Map<String, dynamic> _unwrapPayload(Map<String, dynamic> data) {
    if (data['data'] is Map) {
      final nested = ParsingService.asMap(data['data']);
      if (nested.isNotEmpty) return nested;
    }
    return data;
  }

  // ─── Trading State ──────────────────────────────
  Future<SystemStatusModel> getTradingState() async {
    final response = await _api.get(ApiEndpoints.tradingState);
    final data = response.data;
    if (_isSuccessfulResponse(data)) {
      final payload = _unwrapPayload(data);
      return SystemStatusModel.fromJson(payload);
    }
    throw Exception(data['message'] ?? 'فشل تحميل حالة النظام');
  }

  Future<SystemStatusModel> getPublicTradingState() async {
    final response = await _api.get(ApiEndpoints.systemPublicStatus);
    final data = ParsingService.asMap(response.data);
    if (_isSuccessfulResponse(data)) {
      final payload = _unwrapPayload(data);
      return SystemStatusModel.fromJson(payload);
    }
    throw Exception(data['message'] ?? 'فشل تحميل الحالة العامة للنظام');
  }

  Future<Map<String, dynamic>> startTrading() async {
    try {
      final response = await _api.post(ApiEndpoints.tradingStart);
      final data = ParsingService.asMap(response.data);
      return {'success': _isSuccessfulResponse(data), ...data};
    } catch (e) {
      return _handleApiError(e);
    }
  }

  Future<Map<String, dynamic>> stopTrading() async {
    try {
      final response = await _api.post(ApiEndpoints.tradingStop);
      final data = ParsingService.asMap(response.data);
      return {'success': _isSuccessfulResponse(data), ...data};
    } catch (e) {
      return _handleApiError(e);
    }
  }

  Future<Map<String, dynamic>> emergencyStop() async {
    try {
      final response = await _api.post(ApiEndpoints.tradingEmergencyStop);
      final data = ParsingService.asMap(response.data);
      return {'success': _isSuccessfulResponse(data), ...data};
    } catch (e) {
      return _handleApiError(e);
    }
  }

  Future<Map<String, dynamic>> resetError() async {
    try {
      final response = await _api.post(ApiEndpoints.tradingResetError);
      final data = ParsingService.asMap(response.data);
      return {'success': _isSuccessfulResponse(data), ...data};
    } catch (e) {
      return _handleApiError(e);
    }
  }

  Map<String, dynamic> _handleApiError(dynamic error) {
    String message = 'فشل الاتصال بالخادم';
    if (error.toString().contains('401')) {
      message = 'انتهت الجلسة، يرجى تسجيل الدخول مرة أخرى';
    } else if (error.toString().contains('403')) {
      message = 'غير مصرح بالوصول';
    } else if (error.toString().contains('500')) {
      message = 'خطأ في الخادم';
    } else if (error.toString().contains('timeout')) {
      message = 'انتهت مهلة الاتصال، حاول مرة أخرى';
    } else if (error.toString().contains('connection')) {
      message = 'فشل الاتصال بالإنترنت';
    }
    return {'success': false, 'message': message, 'error': error.toString()};
  }

  Future<Map<String, dynamic>> resetDemo({bool resetMl = false}) async {
    final response = await _api.post(
      ApiEndpoints.adminDemoReset,
      data: {'reset_ml': resetMl},
    );
    return response.data;
  }

  // ─── Binance Connection Status ──────────────────
  Future<Map<String, dynamic>> getBinanceStatus() async {
    final response = await _api.get(ApiEndpoints.binanceStatus);
    return response.data;
  }

  Future<Map<String, dynamic>> retryBinanceConnection() async {
    final response = await _api.post(ApiEndpoints.binanceRetry);
    return response.data;
  }

  Future<Map<String, dynamic>> getCircuitBreakers() async {
    final response = await _api.get(ApiEndpoints.circuitBreakers);
    return response.data;
  }

  Future<Map<String, dynamic>> resetCircuitBreakers() async {
    final response = await _api.post(ApiEndpoints.circuitBreakersReset);
    return response.data;
  }

  // ─── ML Status ──────────────────────────────────
  Future<Map<String, dynamic>> getMlStatus({String? mode}) async {
    final response = await _api.get(
      ApiEndpoints.adminMlStatus,
      queryParameters: {if (mode != null && mode.isNotEmpty) 'mode': mode},
    );
    final data = response.data;
    if (data is Map<String, dynamic>) {
      return data;
    }
    if (data is Map) {
      return Map<String, dynamic>.from(data);
    }
    throw Exception('فشل تحميل حالة ML');
  }

  // ─── Users ──────────────────────────────────────
  Future<List<Map<String, dynamic>>> getAllUsers() async {
    final response = await _api.get(ApiEndpoints.adminUsersAll);
    final data = response.data;
    if (data['success'] == true) {
      final nested = data['data'];
      final users = nested is Map ? (nested['users'] ?? []) : (nested ?? []);
      return List<Map<String, dynamic>>.from(users);
    }
    throw Exception(data['message'] ?? 'فشل تحميل المستخدمين');
  }

  Future<Map<String, dynamic>> getUserDetails(int userId) async {
    final response = await _api.get(ApiEndpoints.adminUserDetails(userId));
    final data = response.data;
    if (data['success'] == true) {
      final nested = data['data'];
      if (nested is Map) {
        return Map<String, dynamic>.from(nested);
      }
      throw Exception('بيانات المستخدم غير صالحة');
    }
    throw Exception(data['message'] ?? 'فشل تحميل تفاصيل المستخدم');
  }

  Future<void> toggleUserTrading(int userId, bool enabled) async {
    final response = await _api.post(
      ApiEndpoints.adminToggleUserTrading(userId),
      data: {'tradingEnabled': enabled},
    );
    final data = response.data;
    if (data['success'] != true) {
      throw Exception(data['error'] ?? 'فشل تحديث حالة التداول');
    }
  }

  Future<void> forceCloseUserPositions(int userId) async {
    final response = await _api.post(
      ApiEndpoints.adminForceCloseUserPositions(userId),
    );
    final data = response.data;
    if (data['success'] != true) {
      throw Exception(data['error'] ?? 'فشل إغلاق الصفقات');
    }
  }

  Future<void> closePosition(int positionId, {String? reason, double? exitPrice}) async {
    final response = await _api.post(
      ApiEndpoints.adminClosePosition(positionId),
      data: {
        if (reason != null) 'reason': reason,
        if (exitPrice != null) 'exit_price': exitPrice,
      },
    );
    final data = response.data;
    if (data['success'] != true) {
      throw Exception(data['message'] ?? data['error'] ?? 'فشل إغلاق الصفقة');
    }
  }

  // ─── Activity Logs ──────────────────────────────
  Future<({List<Map<String, dynamic>> logs, int total})> getActivityLogs({
    int page = 1,
    int perPage = 50,
    String? level,
  }) async {
    final statusFilter = switch (level?.toLowerCase()) {
      'error' => 'failed',
      'warning' => 'warning',
      'info' => 'success',
      _ => null,
    };

    final response = await _api.get(
      ApiEndpoints.adminActivityLogs,
      queryParameters: {
        'page': page,
        'limit': perPage,
        if (statusFilter != null) 'status': statusFilter,
      },
    );
    final data = response.data;
    if (data['success'] == true) {
      final nested = data['data'];
      final logsRaw = nested is Map
          ? (nested['logs'] ?? [])
          : (data['logs'] ?? []);
      final totalRaw = nested is Map
          ? (nested['total'] ?? 0)
          : (data['total'] ?? 0);

      final normalizedLogs = List<Map<String, dynamic>>.from(logsRaw).map((
        log,
      ) {
        final status = (log['status'] ?? '').toString().toLowerCase();
        final normalizedLevel = switch (status) {
          'failed' || 'error' => 'error',
          'warning' => 'warning',
          _ => 'info',
        };

        final message = (log['message'] ?? log['action'] ?? '').toString();
        final timestamp = (log['timestamp'] ?? log['created_at'])?.toString();

        return {
          ...log,
          'level': normalizedLevel,
          'message': message,
          'timestamp': timestamp,
        };
      }).toList();

      return (
        logs: normalizedLogs,
        total: (totalRaw is int
            ? totalRaw
            : int.tryParse(totalRaw.toString()) ?? 0),
      );
    }
    throw Exception(data['message'] ?? 'فشل تحميل السجلات');
  }

  Future<({List<Map<String, dynamic>> logs, int total})> getSecurityAuditLog({
    int page = 1,
    int perPage = 50,
  }) async {
    final response = await _api.get(
      ApiEndpoints.adminSecurityAuditLog,
      queryParameters: {'page': page, 'limit': perPage},
    );
    final data = response.data;
    if (data['success'] == true) {
      final nested = data['data'];
      final logsRaw = nested is Map ? (nested['logs'] ?? []) : [];
      final totalRaw = nested is Map ? (nested['total'] ?? 0) : 0;
      return (
        logs: List<Map<String, dynamic>>.from(logsRaw),
        total: totalRaw is int
            ? totalRaw
            : int.tryParse(totalRaw.toString()) ?? 0,
      );
    }
    throw Exception(data['message'] ?? 'فشل تحميل سجل الأمان');
  }

  // ─── System Errors ──────────────────────────────
  Future<
    ({List<Map<String, dynamic>> errors, int total, Map<String, dynamic> stats})
  >
  getSystemErrors({
    int page = 1,
    int perPage = 50,
    String? severity,
    String? source,
    String? status,
    bool? requiresAdmin,
  }) async {
    final response = await _api.get(
      ApiEndpoints.systemErrors(page: page, limit: perPage),
      queryParameters: {
        if (severity != null) 'severity': severity,
        if (source != null) 'source': source,
        if (status != null) 'status': status,
        if (requiresAdmin != null) 'requires_admin': requiresAdmin.toString(),
      },
    );
    final data = response.data;
    if (data['success'] == true) {
      final nested = ParsingService.asMap(data['data']);
      final errorsRaw = nested['errors'] ?? data['errors'] ?? [];
      final totalRaw = nested['total'] ?? data['total'] ?? 0;
      final statsRaw = nested['stats'] ?? data['stats'] ?? {};

      return (
        errors: List<Map<String, dynamic>>.from(errorsRaw),
        total: ParsingService.asInt(totalRaw),
        stats: ParsingService.asMap(statsRaw),
      );
    }
    throw Exception(data['message'] ?? data['error'] ?? 'فشل تحميل الأخطاء');
  }

  Future<Map<String, dynamic>> getSystemErrorDetails(int errorId) async {
    final response = await _api.get(ApiEndpoints.systemErrorDetails(errorId));
    final data = response.data;
    if (data['success'] == true) {
      return Map<String, dynamic>.from(data['data'] ?? {});
    }
    throw Exception(data['message'] ?? 'فشل تحميل تفاصيل الخطأ');
  }

  Future<Map<String, dynamic>> resolveSystemError(
    int errorId, {
    String? notes,
  }) async {
    final response = await _api.post(
      ApiEndpoints.resolveSystemError(errorId),
      data: {
        'resolved_by': 'admin',
        if (notes != null && notes.isNotEmpty) 'notes': notes,
      },
    );
    return response.data;
  }

  Future<Map<String, dynamic>> retryAutoFix(int errorId) async {
    final response = await _api.post(ApiEndpoints.retrySystemError(errorId));
    return response.data;
  }

  Future<int> clearResolvedErrors() async {
    final response = await _api.delete(ApiEndpoints.clearResolvedErrors);
    final data = response.data;
    if (data['success'] == true) {
      return ParsingService.asInt(
        data['deleted'] ?? data['data']?['deleted'] ?? 0,
      );
    }
    throw Exception(data['message'] ?? data['error'] ?? 'فشل تنظيف السجلات');
  }

  Future<List<Map<String, dynamic>>> getActivePositionsForUser(int userId) async {
    final response = await _api.get(ApiEndpoints.activePositions(userId));
    final data = response.data;
    if (_isSuccessfulResponse(data)) {
      final payload = _unwrapPayload(data);
      final positions = payload['positions'] ?? payload['data'] ?? [];
      if (positions is List) {
        return positions.map((p) => ParsingService.asMap(p)).toList();
      }
      return [];
    }
    throw Exception(data['message'] ?? data['error'] ?? 'فشل تحميل المراكز');
  }

  Future<Map<String, dynamic>> getDailyStatus(String date) async {
    final response = await _api.get(ApiEndpoints.dailyStatus(0, mode: date));
    final data = response.data;
    if (_isSuccessfulResponse(data)) {
      return _unwrapPayload(data);
    }
    throw Exception(data['message'] ?? data['error'] ?? 'فشل تحميل الحالة اليومية');
  }

  // ─── ML ──────────────────────────────────────────
  Future<Map<String, dynamic>> getMlBacktestStatus() async {
    final response = await _api.get(ApiEndpoints.mlBacktestStatus);
    final data = response.data;
    if (data is Map<String, dynamic>) return data;
    if (data is Map) return Map<String, dynamic>.from(data);
    throw Exception('فشل تحميل حالة الباك تست');
  }

  Future<Map<String, dynamic>> getMlReliability() async {
    final response = await _api.get(ApiEndpoints.mlReliability);
    final data = response.data;
    if (data is Map<String, dynamic>) return data;
    if (data is Map) return Map<String, dynamic>.from(data);
    throw Exception('فشل تحميل موثوقية ML');
  }

  Future<Map<String, dynamic>> getMlProgress() async {
    final response = await _api.get(ApiEndpoints.mlProgress);
    final data = response.data;
    if (data is Map<String, dynamic>) return data;
    if (data is Map) return Map<String, dynamic>.from(data);
    throw Exception('فشل تحميل تقدم ML');
  }

  Future<Map<String, dynamic>> getMlQualityMetrics() async {
    final response = await _api.get(ApiEndpoints.mlQualityMetrics);
    final data = response.data;
    if (data is Map<String, dynamic>) return data;
    if (data is Map) return Map<String, dynamic>.from(data);
    throw Exception('فشل تحميل مقاييس الجودة');
  }

  Future<Map<String, dynamic>> getAdminNotificationSettings() async {
    final response = await _api.get(ApiEndpoints.adminNotificationSettings);
    final data = response.data;
    if (data is Map<String, dynamic>) return data;
    if (data is Map) return Map<String, dynamic>.from(data);
    throw Exception('فشل تحميل إعدادات الإشعارات');
  }

  Future<Map<String, dynamic>> updateAdminNotificationSettings(
    Map<String, dynamic> settings,
  ) async {
    final response = await _api.put(
      ApiEndpoints.adminNotificationSettings,
      data: settings,
    );
    return response.data;
  }

  // ─── Background Control ──────────────────────────
  Future<Map<String, dynamic>> getBackgroundStatus() async {
    final response = await _api.get(ApiEndpoints.backgroundStatus);
    final data = response.data;
    if (data is Map<String, dynamic>) return data;
    if (data is Map) return Map<String, dynamic>.from(data);
    throw Exception('فشل تحميل حالة الخلفية');
  }

  Future<Map<String, dynamic>> startBackground() async {
    final response = await _api.post(ApiEndpoints.backgroundStart);
    return response.data;
  }

  Future<Map<String, dynamic>> stopBackground() async {
    final response = await _api.post(ApiEndpoints.backgroundStop);
    return response.data;
  }

  Future<Map<String, dynamic>> emergencyStopBackground() async {
    final response = await _api.post(ApiEndpoints.backgroundEmergencyStop);
    return response.data;
  }

  Future<Map<String, dynamic>> getBackgroundSettings() async {
    final response = await _api.get(ApiEndpoints.backgroundSettings);
    final data = response.data;
    if (data is Map<String, dynamic>) return data;
    if (data is Map) return Map<String, dynamic>.from(data);
    throw Exception('فشل تحميل إعدادات الخلفية');
  }

  Future<Map<String, dynamic>> updateBackgroundSettings(
    Map<String, dynamic> settings,
  ) async {
    final response = await _api.put(
      ApiEndpoints.backgroundSettings,
      data: settings,
    );
    return response.data;
  }

  Future<({List<Map<String, dynamic>> entries, int total})> getBackgroundLogs({
    int page = 1,
    int perPage = 50,
  }) async {
    final response = await _api.get(
      ApiEndpoints.backgroundLogs,
      queryParameters: {'page': page, 'limit': perPage},
    );
    final data = response.data;
    if (data['success'] == true) {
      final nested = data['data'] ?? data;
      return (
        entries: List<Map<String, dynamic>>.from(nested['entries'] ?? []),
        total: ParsingService.asInt(nested['total'] ?? 0),
      );
    }
    return (entries: <Map<String, dynamic>>[], total: 0);
  }

  // ─── Logs ────────────────────────────────────────
  Future<Map<String, dynamic>> getLogsStatistics() async {
    final response = await _api.get(ApiEndpoints.logsStatistics);
    final data = response.data;
    if (data is Map<String, dynamic>) return data;
    if (data is Map) return Map<String, dynamic>.from(data);
    throw Exception('فشل تحميل إحصائيات السجلات');
  }

  Future<Map<String, dynamic>> getLogsRetentionPolicy() async {
    final response = await _api.get(ApiEndpoints.logsRetentionPolicy);
    final data = response.data;
    if (data is Map<String, dynamic>) return data;
    if (data is Map) return Map<String, dynamic>.from(data);
    throw Exception('فشل تحميل سياسة الاحتفاظ');
  }

  Future<Map<String, dynamic>> updateLogsRetentionPolicy(
    Map<String, dynamic> policy,
  ) async {
    final response = await _api.put(
      ApiEndpoints.logsRetentionPolicy,
      data: policy,
    );
    return response.data;
  }

  Future<Map<String, dynamic>> cleanOldLogs({int? olderThanDays}) async {
    final response = await _api.post(
      ApiEndpoints.logsCleanupOld,
      data: {if (olderThanDays != null) 'older_than_days': olderThanDays},
    );
    return response.data;
  }

  Future<Map<String, dynamic>> cleanDuplicateLogs() async {
    final response = await _api.post(ApiEndpoints.logsCleanupDuplicate);
    return response.data;
  }

  Future<Map<String, dynamic>> clearAllLogs() async {
    final response = await _api.post(ApiEndpoints.logsClear);
    return response.data;
  }

  // ─── Wallet / PnL / Top Traders ──────────────────
  Future<Map<String, dynamic>> getAdminWallet() async {
    final response = await _api.get(ApiEndpoints.adminWallet);
    final data = response.data;
    if (data is Map<String, dynamic>) return data;
    if (data is Map) return Map<String, dynamic>.from(data);
    throw Exception('فشل تحميل المحفظة');
  }

  Future<Map<String, dynamic>> getAdminPnl() async {
    final response = await _api.get(ApiEndpoints.adminPnl);
    final data = response.data;
    if (data is Map<String, dynamic>) return data;
    if (data is Map) return Map<String, dynamic>.from(data);
    throw Exception('فشل تحميل الأرباح والخسائر');
  }

  Future<List<Map<String, dynamic>>> getAdminTopTraders() async {
    final response = await _api.get(ApiEndpoints.adminTopTraders);
    final data = response.data;
    if (data['success'] == true) {
      final nested = data['data'] ?? data;
      return List<Map<String, dynamic>>.from(nested['traders'] ?? []);
    }
    throw Exception('فشل تحميل كبار المتداولين');
  }

  Future<Map<String, dynamic>> getSystemStats() async {
    final response = await _api.get(ApiEndpoints.adminSystemStats);
    final data = response.data;
    if (data is Map<String, dynamic> && data['success'] == true) {
      return Map<String, dynamic>.from(data['data'] as Map);
    }
    if (data is Map && data['success'] == true) {
      return Map<String, dynamic>.from(data['data'] as Map);
    }
    throw Exception('فشل تحميل إحصائيات النظام');
  }
}
