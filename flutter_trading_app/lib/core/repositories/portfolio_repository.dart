import 'package:trading_app/core/constants/api_endpoints.dart';
import 'package:trading_app/core/models/portfolio_model.dart';
import 'package:trading_app/core/models/stats_model.dart';
import 'package:trading_app/core/models/trade_model.dart';
import 'package:trading_app/core/services/api_service.dart';
import 'package:trading_app/core/services/api_cache.dart';
import 'package:trading_app/core/services/parsing_service.dart';

/// Portfolio Repository — data access for portfolio + stats
/// منطق صافي — لا يستورد Flutter
class PortfolioRepository {
  final ApiService _api;

  PortfolioRepository(this._api);

  Future<PortfolioModel> getPortfolio(int userId, {String? mode}) async {
    final cacheKey = CacheKeys.portfolio(userId, mode: mode);
    final response = await _api.get(
      ApiEndpoints.portfolio(userId, mode: mode),
      useCache: true,
      cacheTTL: CacheTTL.portfolio,
      cacheKey: cacheKey,
    );
    final data = response.data;
    if (data['success'] == true) {
      return PortfolioModel.fromJson(
        ParsingService.asMap(data['portfolio'] ?? data['data'] ?? data),
      );
    }
    throw Exception(data['message'] ?? data['error'] ?? 'فشل تحميل المحفظة');
  }

  Future<StatsModel> getStats(int userId, {String? mode}) async {
    final cacheKey = CacheKeys.stats(userId, mode: mode);
    final response = await _api.get(
      ApiEndpoints.stats(userId, mode: mode),
      useCache: true,
      cacheTTL: CacheTTL.stats,
      cacheKey: cacheKey,
    );
    final data = response.data;
    if (data['success'] == true) {
      return StatsModel.fromJson(
        ParsingService.asMap(data['stats'] ?? data['data'] ?? data),
      );
    }
    throw Exception(data['message'] ?? data['error'] ?? 'فشل تحميل الإحصائيات');
  }

  Future<List<Map<String, dynamic>>> getSuccessfulCoins(
    int userId, {
    String? mode,
  }) async {
    final cacheKey = CacheKeys.successfulCoins(userId, mode: mode);
    final response = await _api.get(
      ApiEndpoints.qualifiedCoins(userId, mode: mode),
      useCache: true,
      cacheTTL: CacheTTL.successfulCoins,
      cacheKey: cacheKey,
    );
    final data = response.data;
    if (data['success'] == true) {
      final nested = ParsingService.asMap(data['data']);
      final coins = nested['coins'];
      if (coins is List) {
        return List<Map<String, dynamic>>.from(coins);
      }
      throw Exception(
        data['message'] ??
            data['error'] ??
            'تنسيق بيانات العملات المؤهلة غير صالح',
      );
    }
    throw Exception(
      data['message'] ?? data['error'] ?? 'فشل تحميل العملات المؤهلة',
    );
  }

  Future<List<TradeModel>> getActivePositions(
    int userId, {
    String? mode,
  }) async {
    final cacheKey = CacheKeys.activePositions(userId, mode: mode);
    final response = await _api.get(
      ApiEndpoints.activePositions(userId, mode: mode),
      useCache: true,
      cacheTTL: CacheTTL.activePositions,
      cacheKey: cacheKey,
    );
    final data = response.data;
    if (data['success'] == true) {
      final payload = (data['data'] as Map<String, dynamic>?) ?? data;
      final positionsJson = (payload['positions'] as List?) ?? const [];
      return positionsJson
          .map(
            (j) => TradeModel.fromJson({
              ...(j as Map<String, dynamic>),
              'user_id': userId,
            }),
          )
          .toList();
    }
    throw Exception(data['message'] ?? 'فشل تحميل الصفقات المفتوحة');
  }

  Future<List<Map<String, dynamic>>> getPortfolioGrowth(
    int userId, {
    String period = '30d',
    String? mode,
  }) async {
    final days = int.tryParse(period.replaceAll(RegExp(r'[^0-9]'), '')) ?? 30;
    final cacheKey = CacheKeys.portfolioGrowth(userId, period, mode: mode);
    final response = await _api.get(
      ApiEndpoints.portfolioGrowth(userId, days: days, mode: mode),
      useCache: true,
      cacheTTL: CacheTTL.portfolioGrowth,
      cacheKey: cacheKey,
    );
    final data = response.data;
    final growthData = data['growth'] ?? data['data']?['growth'];
    if (data['success'] == true) {
      if (growthData is List) {
        return List<Map<String, dynamic>>.from(growthData);
      }
      throw Exception(
        data['message'] ?? data['error'] ?? 'تنسيق بيانات نمو المحفظة غير صالح',
      );
    }
    throw Exception(
      data['message'] ?? data['error'] ?? 'فشل تحميل نمو المحفظة',
    );
  }
}
