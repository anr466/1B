import 'package:trading_app/core/constants/api_endpoints.dart';
import 'package:trading_app/core/constants/app_constants.dart';
import 'package:trading_app/core/models/trade_model.dart';
import 'package:trading_app/core/services/api_service.dart';
import 'package:trading_app/core/services/parsing_service.dart';

/// Trades Repository — data access for trades
/// منطق صافي — لا يستورد Flutter
class TradesRepository {
  final ApiService _api;

  TradesRepository(this._api);

  Future<({List<TradeModel> trades, int total, int pages})> getTrades(
    int userId, {
    int page = 1,
    int perPage = AppConstants.tradesPerPage,
    String? mode,
    String? status,
    String? dateFrom,
    String? dateTo,
  }) async {
    final params = <String, dynamic>{
      'page': page,
      'limit': perPage,
      if (mode != null) 'mode': mode,
      if (status != null) 'status': status,
      if (dateFrom != null) 'date_from': dateFrom,
      if (dateTo != null) 'date_to': dateTo,
    };

    final response = await _api.get(
      ApiEndpoints.trades(userId),
      queryParameters: params,
    );
    final data = response.data;

    if (data['success'] == true) {
      final payload = (data['data'] as Map<String, dynamic>?) ?? data;
      final tradesJson = (payload['trades'] as List?) ?? const [];
      final pagination =
          (payload['pagination'] as Map<String, dynamic>?) ?? const {};

      final trades = tradesJson
          .map((j) => TradeModel.fromJson(j as Map<String, dynamic>))
          .toList();

      return (
        trades: trades,
        total: ParsingService.asInt(
          pagination['total'],
          fallback: trades.length,
        ),
        pages: ParsingService.asInt(pagination['pages']),
      );
    }
    throw Exception(data['message'] ?? data['error'] ?? 'فشل تحميل الصفقات');
  }

  Future<List<TradeModel>> getRecentTrades(
    int userId, {
    int count = AppConstants.dashboardRecentTrades,
    String? mode,
  }) async {
    final result = await getTrades(userId, page: 1, perPage: count, mode: mode);
    return result.trades;
  }

  Future<TradeModel> getTradeById(int tradeId) async {
    final response = await _api.get(ApiEndpoints.tradeDetail(tradeId));
    final data = response.data;
    if (data['success'] == true && data['data'] is Map) {
      return TradeModel.fromJson(
        Map<String, dynamic>.from(data['data'] as Map),
      );
    }
    throw Exception(
      data['message'] ?? data['error'] ?? 'فشل تحميل تفاصيل الصفقة',
    );
  }
}
