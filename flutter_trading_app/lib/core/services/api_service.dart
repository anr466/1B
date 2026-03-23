import 'dart:async';
import 'package:dio/dio.dart';
import 'package:trading_app/core/constants/api_endpoints.dart';
import 'package:trading_app/core/constants/app_constants.dart';
import 'package:trading_app/core/services/storage_service.dart';

/// API Service — Dio HTTP client + interceptors + auto-refresh
/// منطق صافي — لا يستورد Flutter UI
class ApiService {
  late final Dio _dio;
  final StorageService _storage;
  bool _isRefreshing = false;
  bool _isRecoveringConnection = false;

  /// Callback invoked when session expires (refresh token fails).
  /// Set by AuthNotifier to trigger forced logout.
  void Function()? onSessionExpired;

  ApiService(this._storage) {
    _dio = Dio(
      BaseOptions(
        baseUrl: ApiEndpoints.baseUrl,
        connectTimeout: const Duration(
          milliseconds: AppConstants.connectTimeoutMs,
        ),
        receiveTimeout: const Duration(
          milliseconds: AppConstants.receiveTimeoutMs,
        ),
        headers: {'Content-Type': 'application/json'},
      ),
    );

    _dio.interceptors.add(
      InterceptorsWrapper(onRequest: _onRequest, onError: _onError),
    );
  }

  Dio get dio => _dio;

  // ─── Request Interceptor ────────────────────────
  void _onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    final token = _storage.accessToken;
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  // ─── Error Interceptor (auto-refresh on 401) ────
  Future<void> _onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    if (_isRecoverableConnectionError(err) && !_isRecoveringConnection) {
      _isRecoveringConnection = true;
      try {
        final switched = await _switchToReachableBaseUrl();
        if (switched && _isSafeRetryMethod(err.requestOptions.method)) {
          final retryOptions = err.requestOptions;
          retryOptions.baseUrl = _dio.options.baseUrl;
          retryOptions.extra['_network_retried'] = true;
          final response = await _dio.fetch(retryOptions);
          return handler.resolve(response);
        }
      } catch (_) {
        // keep original error path
      } finally {
        _isRecoveringConnection = false;
      }
    }

    if (err.response?.statusCode == 401 && !_isRefreshing) {
      _isRefreshing = true;
      try {
        final refreshed = await _refreshToken();
        if (refreshed) {
          final retryOptions = err.requestOptions;
          retryOptions.headers['Authorization'] =
              'Bearer ${_storage.accessToken}';
          final response = await _dio.fetch(retryOptions);
          _isRefreshing = false;
          return handler.resolve(response);
        }
      } catch (_) {
        // refresh failed
      }
      _isRefreshing = false;
      // Token refresh failed — force session expiry
      await _storage.clearAuth();
      try {
        onSessionExpired?.call();
      } catch (e) {
        // Log error but don't crash
      }
    }
    handler.next(err);
  }

  bool _isSafeRetryMethod(String method) {
    // GET is always safe to retry
    // POST is safe to retry for connection errors (idempotent trading operations)
    final m = method.toUpperCase();
    return m == 'GET' || m == 'POST';
  }

  bool _isRecoverableConnectionError(DioException err) {
    if (err.requestOptions.extra['_network_retried'] == true) return false;
    if (err.response != null) return false;
    return err.type == DioExceptionType.connectionError ||
        err.type == DioExceptionType.connectionTimeout ||
        err.type == DioExceptionType.receiveTimeout ||
        err.type == DioExceptionType.sendTimeout;
  }

  Future<bool> _switchToReachableBaseUrl() async {
    final current = _dio.options.baseUrl;
    final currentUri = Uri.tryParse(current);
    if (currentUri == null) return false;

    final candidates = <String>{
      current,
      currentUri.replace(host: '10.0.2.2').toString(),
      currentUri.replace(host: '127.0.0.1').toString(),
      currentUri.replace(host: 'localhost').toString(),
    };

    for (final candidate in candidates) {
      final ok = await _isBaseUrlReachable(candidate);
      if (ok) {
        _dio.options.baseUrl = candidate;
        return true;
      }
    }
    return false;
  }

  Future<bool> _isBaseUrlReachable(String baseUrl) async {
    try {
      final probe = Dio(
        BaseOptions(
          baseUrl: baseUrl,
          connectTimeout: const Duration(seconds: 3),
          receiveTimeout: const Duration(seconds: 3),
          headers: {'Content-Type': 'application/json'},
        ),
      );
      final response = await probe.get(ApiEndpoints.systemStatus);
      return (response.statusCode ?? 500) < 500;
    } catch (_) {
      return false;
    }
  }

  // ─── Token Refresh ──────────────────────────────
  Future<bool> _refreshToken() async {
    final refresh = _storage.refreshToken;
    if (refresh == null || refresh.isEmpty) return false;

    try {
      final response = await Dio(
        BaseOptions(
          baseUrl: _dio.options.baseUrl,
          connectTimeout: const Duration(
            milliseconds: AppConstants.connectTimeoutMs,
          ),
          receiveTimeout: const Duration(
            milliseconds: AppConstants.receiveTimeoutMs,
          ),
        ),
      ).post(ApiEndpoints.refreshToken, data: {'refresh_token': refresh});

      if (response.statusCode == 200 && response.data['success'] == true) {
        final data = response.data as Map<String, dynamic>;
        final tokens = (data['tokens'] is Map)
            ? Map<String, dynamic>.from(data['tokens'] as Map)
            : data;
        final accessToken = (tokens['access_token'] ?? tokens['token'])
            ?.toString();
        final refreshToken = (tokens['refresh_token'] ?? data['refresh_token'])
            ?.toString();
        if (accessToken == null || accessToken.isEmpty) {
          return false;
        }
        await _storage.saveTokens(
          accessToken: accessToken,
          refreshToken: refreshToken ?? '',
        );
        return true;
      }
    } catch (_) {
      // silent fail — caller handles
    }
    return false;
  }

  // ─── Convenience Methods ────────────────────────
  Future<Response> get(String path, {Map<String, dynamic>? queryParameters}) =>
      _dio.get(path, queryParameters: queryParameters);

  Future<Response> post(String path, {dynamic data}) =>
      _dio.post(path, data: data);

  Future<Response> put(String path, {dynamic data}) =>
      _dio.put(path, data: data);

  Future<Response> patch(String path, {dynamic data}) =>
      _dio.patch(path, data: data);

  Future<Response> delete(String path, {dynamic data}) =>
      _dio.delete(path, data: data);

  // ─── Error Message Extraction ───────────────────
  static String extractError(dynamic error) {
    if (error is DioException) {
      if (error.response?.data is Map) {
        return error.response!.data['message']?.toString() ??
            error.response!.data['error']?.toString() ??
            _dioErrorMessage(error);
      }
      return _dioErrorMessage(error);
    }
    return error.toString();
  }

  static String _dioErrorMessage(DioException e) {
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return 'تحقق من الاتصال بالإنترنت';
      case DioExceptionType.connectionError:
        return 'لا يوجد اتصال بالسيرفر';
      case DioExceptionType.badResponse:
        final code = e.response?.statusCode;
        if (code == 403) return 'غير مصرح بالوصول';
        if (code == 404) return 'المورد غير موجود';
        if (code == 422) return 'بيانات غير صالحة';
        if (code == 429) return 'طلبات كثيرة، حاول لاحقاً';
        if (code != null && code >= 500) return 'خطأ في السيرفر';
        return 'خطأ غير متوقع ($code)';
      default:
        return 'خطأ في الاتصال';
    }
  }
}
