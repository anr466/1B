import 'dart:async';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:trading_app/core/constants/api_endpoints.dart';
import 'package:trading_app/core/constants/app_constants.dart';
import 'package:trading_app/core/services/storage_service.dart';
import 'package:trading_app/core/services/api_cache.dart';

/// API Service — Dio HTTP client + interceptors + auto-refresh
/// منطق صافي — لا يستورد Flutter UI
class _PendingRequest {
  final RequestOptions request;
  final ErrorInterceptorHandler handler;
  _PendingRequest(this.request, this.handler);
}

class ApiService {
  late final Dio _dio;
  final StorageService _storage;
  final ApiCache _cache = ApiCache();
  bool _isRefreshing = false;
  Completer<bool>? _refreshCompleter;
  final List<_PendingRequest> _pendingRequests = [];
  bool _isRecoveringConnection = false;

  // 429 retry configuration
  static const int _maxRetries = 3;
  static const Duration _baseRetryDelay = Duration(seconds: 2);

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
    // Use sync getter for token (cached after initial load)
    final token = _storage.accessTokenSync;
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  // ─── Error Interceptor (auto-refresh on 401 + 429 retry) ────
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
      } catch (e) {
        debugPrint('[ApiService] connection recovery error: $e');
      } finally {
        _isRecoveringConnection = false;
      }
    }

    // ─── 429 Retry with Exponential Backoff ────
    if (err.response?.statusCode == 429) {
      final retryCount = err.requestOptions.extra['_retry_count'] ?? 0;
      if (retryCount < _maxRetries &&
          _isSafeRetryMethod(err.requestOptions.method)) {
        // Calculate exponential backoff delay
        final delay =
            _baseRetryDelay * (1 << retryCount); // 2^retryCount seconds
        await Future.delayed(delay);

        // Clone request with incremented retry count
        final retryOptions = err.requestOptions;
        retryOptions.extra['_retry_count'] = retryCount + 1;
        retryOptions.extra['_429_retry'] = true;

        try {
          final response = await _dio.fetch(retryOptions);
          return handler.resolve(response);
        } catch (retryErr) {
          // If retry also fails, let it flow to next error handler
          return handler.next(retryErr as DioException);
        }
      }
      // Max retries exceeded or unsafe method — return rate limit error
      return handler.next(err);
    }

    if (err.response?.statusCode == 401) {
      // If already refreshing, queue this request
      if (_isRefreshing && _refreshCompleter != null) {
        _pendingRequests.add(_PendingRequest(err.requestOptions, handler));
        return;
      }

      // Start refresh and queue this request
      _isRefreshing = true;
      _refreshCompleter = Completer<bool>();

      try {
        final refreshed = await _refreshToken();
        _refreshCompleter!.complete(refreshed);

        if (refreshed) {
          // Retry all pending requests with new token
          for (final pending in _pendingRequests) {
            pending.request.headers['Authorization'] =
                'Bearer ${_storage.accessToken}';
            try {
              final response = await _dio.fetch(pending.request);
              pending.handler.resolve(response);
            } catch (e) {
              pending.handler.next(e as DioException);
            }
          }
          _pendingRequests.clear();

          // Retry the current request
          err.requestOptions.headers['Authorization'] =
              'Bearer ${_storage.accessToken}';
          final response = await _dio.fetch(err.requestOptions);
          return handler.resolve(response);
        }
      } catch (e) {
        debugPrint('[ApiService] token refresh error: $e');
        _refreshCompleter!.complete(false);
      }

      _isRefreshing = false;
      _refreshCompleter = null;

      // Token refresh failed — queue pending requests for session expiry
      for (final pending in _pendingRequests) {
        pending.handler.next(err);
      }
      _pendingRequests.clear();

      // Force session expiry
      await _storage.clearAuth();
      try {
        onSessionExpired?.call();
      } catch (e) {
        // Log error but don't crash
      }
      return;
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

    // Only try localhost variants if the current URL is already a localhost variant.
    // On real devices, switching to 127.0.0.1/localhost would break connectivity
    // by routing traffic to the device itself instead of the actual server.
    final isLocalhost =
        currentUri.host == 'localhost' ||
        currentUri.host == '127.0.0.1' ||
        currentUri.host == '10.0.2.2';

    final candidates = <String>{
      current,
      if (isLocalhost) ...[
        currentUri.replace(host: '10.0.2.2').toString(),
        currentUri.replace(host: '127.0.0.1').toString(),
        currentUri.replace(host: 'localhost').toString(),
      ],
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
    final refresh = _storage.refreshTokenSync;
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
    } catch (e) {
      debugPrint('[ApiService] _refreshToken error: $e');
    }
    return false;
  }

  // ─── Convenience Methods (with optional caching) ────
  Future<Response> get(
    String path, {
    Map<String, dynamic>? queryParameters,
    bool useCache = false,
    Duration cacheTTL = const Duration(seconds: 30),
    String? cacheKey,
  }) async {
    // Try cache first for GET requests
    if (useCache && cacheKey != null) {
      final cached = _cache.get<Map<String, dynamic>>(cacheKey);
      if (cached != null) {
        // Return cached response as a fake Response object
        return Response(
          requestOptions: RequestOptions(path: path),
          statusCode: 200,
          data: cached,
        );
      }
    }

    final response = await _dio.get(path, queryParameters: queryParameters);

    // Cache successful GET responses
    if (useCache && cacheKey != null && response.statusCode == 200) {
      _cache.set(cacheKey, response.data, ttl: cacheTTL);
    }

    return response;
  }

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
