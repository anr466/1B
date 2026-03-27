import 'package:trading_app/core/constants/api_endpoints.dart';
import 'package:trading_app/core/models/settings_model.dart';
import 'package:trading_app/core/services/api_service.dart';
import 'package:trading_app/core/services/api_cache.dart';
import 'package:trading_app/core/services/parsing_service.dart';

/// Settings Repository — data access for trading settings
/// منطق صافي — لا يستورد Flutter
class SettingsRepository {
  final ApiService _api;

  SettingsRepository(this._api);

  Map<String, dynamic> _normalizeSettingsPayload(
    Map<String, dynamic> settings,
  ) {
    final normalized = <String, dynamic>{};
    for (final entry in settings.entries) {
      switch (entry.key) {
        case 'trading_enabled':
          normalized['tradingEnabled'] = entry.value;
          break;
        case 'trade_amount':
          normalized['tradeAmount'] = entry.value;
          break;
        case 'position_size_percentage':
        case 'position_size_pct':
          normalized['positionSizePercentage'] = entry.value;
          break;
        case 'max_positions':
        case 'max_concurrent_trades':
          normalized['maxConcurrentTrades'] = entry.value;
          break;
        case 'stop_loss_pct':
        case 'stop_loss_percentage':
          normalized['stopLossPercentage'] = entry.value;
          break;
        case 'take_profit_pct':
        case 'take_profit_percentage':
          normalized['takeProfitPercentage'] = entry.value;
          break;
        case 'max_daily_loss_pct':
          normalized['maxDailyLossPct'] = entry.value;
          break;
        case 'risk_level':
          normalized['riskLevel'] = entry.value;
          break;
        case 'trading_mode':
          normalized['tradingMode'] = entry.value;
          break;
        case 'trailing_distance':
          normalized['trailingDistance'] = entry.value;
          break;
        default:
          normalized[entry.key] = entry.value;
      }
    }
    return normalized;
  }

  Future<SettingsModel> getSettings(int userId, {String? mode}) async {
    final cacheKey = CacheKeys.settings(userId, mode: mode);
    final response = await _api.get(
      ApiEndpoints.settings(userId, mode: mode),
      useCache: true,
      cacheTTL: CacheTTL.settings,
      cacheKey: cacheKey,
    );
    final data = response.data;
    if (data['success'] == true) {
      return SettingsModel.fromJson(
        data['settings'] ??
            ParsingService.asMap(data['data']) ??
            ParsingService.asMap(data),
      );
    }
    throw Exception(data['message'] ?? 'فشل تحميل الإعدادات');
  }

  Future<Map<String, dynamic>> updateSettings(
    int userId,
    Map<String, dynamic> settings, {
    String? mode,
  }) async {
    // Invalidate cache on update
    final cacheKey = CacheKeys.settings(userId, mode: mode);
    ApiCache().invalidate(cacheKey);

    final response = await _api.put(
      ApiEndpoints.updateSettings(userId, mode: mode),
      data: _normalizeSettingsPayload(settings),
    );
    return response.data;
  }

  Future<Map<String, dynamic>> validateBinanceKeys({
    required String apiKey,
    required String apiSecret,
  }) async {
    final response = await _api.post(
      ApiEndpoints.validateBinanceKeys,
      data: {'api_key': apiKey, 'api_secret': apiSecret},
    );
    return response.data;
  }

  Future<Map<String, dynamic>> saveBinanceKeys(
    int userId, {
    required String apiKey,
    required String apiSecret,
  }) async {
    final response = await _api.post(
      ApiEndpoints.saveBinanceKeys,
      data: {'apiKey': apiKey, 'apiSecret': apiSecret},
    );
    return response.data;
  }

  Future<Map<String, dynamic>> getTradingMode(int userId) async {
    final response = await _api.get(ApiEndpoints.tradingMode(userId));
    return response.data;
  }

  Future<Map<String, dynamic>> updateTradingMode(
    int userId,
    String mode,
  ) async {
    final response = await _api.put(
      ApiEndpoints.tradingMode(userId),
      data: {'mode': mode},
    );
    return response.data;
  }

  Future<Map<String, dynamic>> updateProfile(
    int userId, {
    String? fullName,
    String? phone,
  }) async {
    final response = await _api.put(
      ApiEndpoints.userProfile(userId),
      data: {
        if (fullName != null) 'fullName': fullName,
        if (phone != null) 'phoneNumber': phone,
      },
    );
    return response.data;
  }

  Future<Map<String, dynamic>> getDailyStatus(
    int userId, {
    String? mode,
  }) async {
    final cacheKey = CacheKeys.dailyStatus(userId, mode: mode);
    final response = await _api.get(
      ApiEndpoints.dailyStatus(userId, mode: mode),
      useCache: true,
      cacheTTL: CacheTTL.dailyStatus,
      cacheKey: cacheKey,
    );
    final data = response.data;
    if (data['success'] == true) {
      return ParsingService.asMap(data['data']);
    }
    throw Exception(
      data['message'] ?? data['error'] ?? 'فشل تحميل حالة المخاطرة اليومية',
    );
  }
}
