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
    final response = await _api.post(ApiEndpoints.tradingStart);
    final data = ParsingService.asMap(response.data);
    return {'success': _isSuccessfulResponse(data), ...data};
  }

  Future<Map<String, dynamic>> stopTrading() async {
    final response = await _api.post(ApiEndpoints.tradingStop);
    final data = ParsingService.asMap(response.data);
    return {'success': _isSuccessfulResponse(data), ...data};
  }

  Future<Map<String, dynamic>> emergencyStop() async {
    final response = await _api.post(ApiEndpoints.tradingEmergencyStop);
    final data = ParsingService.asMap(response.data);
    return {'success': _isSuccessfulResponse(data), ...data};
  }

  Future<Map<String, dynamic>> resetError() async {
    final response = await _api.post(ApiEndpoints.tradingResetError);
    final data = ParsingService.asMap(response.data);
    return {'success': _isSuccessfulResponse(data), ...data};
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
}
