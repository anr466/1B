import '../services/parsing_service.dart';

/// Settings Model — إعدادات التداول
/// منطق صافي — لا يستورد Flutter
class SettingsModel {
  final bool tradingEnabled;
  final double positionSizePct;
  final int maxPositions;
  final double stopLossPct;
  final double takeProfitPct;
  final double trailingDistancePct;
  final double maxDailyLossPct;
  final String tradingMode;
  final String activePortfolio;
  final bool hasBinanceKeys;
  final bool canToggle;

  const SettingsModel({
    this.tradingEnabled = false,
    this.positionSizePct = 0,
    this.maxPositions = 0,
    this.stopLossPct = 0,
    this.takeProfitPct = 0,
    this.trailingDistancePct = 0,
    this.maxDailyLossPct = 0,
    this.tradingMode = '',
    this.activePortfolio = '',
    this.hasBinanceKeys = false,
    this.canToggle = false,
  });

  factory SettingsModel.fromJson(Map<String, dynamic> json) {
    return SettingsModel(
      tradingEnabled:
          json['trading_enabled'] == true ||
          json['trading_enabled'] == 1 ||
          json['tradingEnabled'] == true ||
          json['tradingEnabled'] == 1,
      positionSizePct: ParsingService.asDouble(
        json['position_size_pct'] ??
            json['position_size_percentage'] ??
            json['positionSizePct'] ??
            json['positionSizePercentage'],
      ),
      maxPositions: ParsingService.asInt(
        json['max_positions'] ??
            json['maxPositions'] ??
            json['maxConcurrentTrades'],
      ),
      stopLossPct: ParsingService.asDouble(
        json['stop_loss_pct'] ??
            json['stop_loss_percentage'] ??
            json['stopLossPct'] ??
            json['stopLossPercentage'],
      ),
      takeProfitPct: ParsingService.asDouble(
        json['take_profit_pct'] ??
            json['take_profit_percentage'] ??
            json['takeProfitPct'] ??
            json['takeProfitPercentage'],
      ),
      trailingDistancePct: ParsingService.asDouble(
        json['trailing_distance'] ??
            json['trailingDistance'] ??
            json['trailingDistancePct'],
      ),
      maxDailyLossPct: ParsingService.asDouble(
        json['max_daily_loss_pct'] ?? json['maxDailyLossPct'],
      ),
      tradingMode: (json['trading_mode'] ?? json['tradingMode'] ?? '')
          .toString(),
      activePortfolio:
          (json['active_portfolio'] ??
                  json['activePortfolio'] ??
                  json['trading_mode'] ??
                  json['tradingMode'] ??
                  '')
              .toString(),
      hasBinanceKeys:
          json['has_binance_keys'] == true ||
          json['has_binance_keys'] == 1 ||
          json['hasBinanceKeys'] == true ||
          json['hasBinanceKeys'] == 1,
      canToggle:
          json['can_toggle'] == true ||
          json['can_toggle'] == 1 ||
          json['canToggle'] == true ||
          json['canToggle'] == 1,
    );
  }

  Map<String, dynamic> toJson() => {
    'tradingEnabled': tradingEnabled,
    'positionSizePercentage': positionSizePct,
    'maxConcurrentTrades': maxPositions,
    'stopLossPercentage': stopLossPct,
    'takeProfitPercentage': takeProfitPct,
    'trailingDistance': trailingDistancePct,
    'maxDailyLossPct': maxDailyLossPct,
    'tradingMode': tradingMode,
    'activePortfolio': activePortfolio,
    'hasBinanceKeys': hasBinanceKeys,
    'canToggle': canToggle,
  };

  SettingsModel copyWith({
    bool? tradingEnabled,
    double? positionSizePct,
    int? maxPositions,
    double? stopLossPct,
    double? takeProfitPct,
    double? trailingDistancePct,
    double? maxDailyLossPct,
    String? tradingMode,
    String? activePortfolio,
    bool? hasBinanceKeys,
    bool? canToggle,
  }) {
    return SettingsModel(
      tradingEnabled: tradingEnabled ?? this.tradingEnabled,
      positionSizePct: positionSizePct ?? this.positionSizePct,
      maxPositions: maxPositions ?? this.maxPositions,
      stopLossPct: stopLossPct ?? this.stopLossPct,
      takeProfitPct: takeProfitPct ?? this.takeProfitPct,
      trailingDistancePct: trailingDistancePct ?? this.trailingDistancePct,
      maxDailyLossPct: maxDailyLossPct ?? this.maxDailyLossPct,
      tradingMode: tradingMode ?? this.tradingMode,
      activePortfolio: activePortfolio ?? this.activePortfolio,
      hasBinanceKeys: hasBinanceKeys ?? this.hasBinanceKeys,
      canToggle: canToggle ?? this.canToggle,
    );
  }
}
