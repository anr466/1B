import '../services/parsing_service.dart';

/// Settings Model — إعدادات التداول
/// منطق صافي — لا يستورد Flutter
class SettingsModel {
  final bool tradingEnabled;
  final double tradeAmount;
  final double positionSizePct;
  final int maxPositions;
  final double stopLossPct;
  final double takeProfitPct;
  final double trailingDistancePct;
  final double maxDailyLossPct;
  final String tradingMode;
  final String activePortfolio;
  final bool hasBinanceKeys;
  final bool hasConfiguredDbKeys;
  final bool usingEnvTestKeys;
  final bool keysRequiredForCurrentMode;
  final bool canToggle;
  final bool systemRunning;
  final String systemState;

  const SettingsModel({
    this.tradingEnabled = false,
    this.tradeAmount = 100.0,
    this.positionSizePct = 0,
    this.maxPositions = 0,
    this.stopLossPct = 0,
    this.takeProfitPct = 0,
    this.trailingDistancePct = 0,
    this.maxDailyLossPct = 0,
    this.tradingMode = '',
    this.activePortfolio = '',
    this.hasBinanceKeys = false,
    this.hasConfiguredDbKeys = false,
    this.usingEnvTestKeys = false,
    this.keysRequiredForCurrentMode = true,
    this.canToggle = false,
    this.systemRunning = false,
    this.systemState = 'UNKNOWN',
  });

  factory SettingsModel.fromJson(Map<String, dynamic> json) {
    return SettingsModel(
      tradingEnabled:
          json['trading_enabled'] == true ||
          json['trading_enabled'] == 1 ||
          json['tradingEnabled'] == true ||
          json['tradingEnabled'] == 1,
      tradeAmount: ParsingService.asDouble(
        json['trade_amount'] ?? json['tradeAmount'],
        fallback: 100.0,
      ),
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
      hasConfiguredDbKeys:
          json['has_configured_db_keys'] == true ||
          json['has_configured_db_keys'] == 1 ||
          json['hasConfiguredDbKeys'] == true ||
          json['hasConfiguredDbKeys'] == 1,
      usingEnvTestKeys:
          json['using_env_test_keys'] == true ||
          json['using_env_test_keys'] == 1 ||
          json['usingEnvTestKeys'] == true ||
          json['usingEnvTestKeys'] == 1,
      keysRequiredForCurrentMode:
          json['keys_required_for_current_mode'] == true ||
          json['keys_required_for_current_mode'] == 1 ||
          json['keysRequiredForCurrentMode'] == true ||
          json['keysRequiredForCurrentMode'] == 1,
      canToggle:
          json['can_toggle'] == true ||
          json['can_toggle'] == 1 ||
          json['canToggle'] == true ||
          json['canToggle'] == 1,
      systemRunning:
          json['system_running'] == true ||
          json['system_running'] == 1 ||
          json['systemRunning'] == true ||
          json['systemRunning'] == 1,
      systemState: (json['system_state'] ?? json['systemState'] ?? 'UNKNOWN')
          .toString()
          .toUpperCase(),
    );
  }

  Map<String, dynamic> toJson() => {
    'tradingEnabled': tradingEnabled,
    'tradeAmount': tradeAmount,
    'positionSizePercentage': positionSizePct,
    'maxConcurrentTrades': maxPositions,
    'stopLossPercentage': stopLossPct,
    'takeProfitPercentage': takeProfitPct,
    'trailingDistance': trailingDistancePct,
    'maxDailyLossPct': maxDailyLossPct,
    'tradingMode': tradingMode,
    'activePortfolio': activePortfolio,
    'hasBinanceKeys': hasBinanceKeys,
    'hasConfiguredDbKeys': hasConfiguredDbKeys,
    'usingEnvTestKeys': usingEnvTestKeys,
    'keysRequiredForCurrentMode': keysRequiredForCurrentMode,
    'canToggle': canToggle,
    'systemRunning': systemRunning,
    'systemState': systemState,
  };

  SettingsModel copyWith({
    bool? tradingEnabled,
    double? tradeAmount,
    double? positionSizePct,
    int? maxPositions,
    double? stopLossPct,
    double? takeProfitPct,
    double? trailingDistancePct,
    double? maxDailyLossPct,
    String? tradingMode,
    String? activePortfolio,
    bool? hasBinanceKeys,
    bool? hasConfiguredDbKeys,
    bool? usingEnvTestKeys,
    bool? keysRequiredForCurrentMode,
    bool? canToggle,
  }) {
    return SettingsModel(
      tradingEnabled: tradingEnabled ?? this.tradingEnabled,
      tradeAmount: tradeAmount ?? this.tradeAmount,
      positionSizePct: positionSizePct ?? this.positionSizePct,
      maxPositions: maxPositions ?? this.maxPositions,
      stopLossPct: stopLossPct ?? this.stopLossPct,
      takeProfitPct: takeProfitPct ?? this.takeProfitPct,
      trailingDistancePct: trailingDistancePct ?? this.trailingDistancePct,
      maxDailyLossPct: maxDailyLossPct ?? this.maxDailyLossPct,
      tradingMode: tradingMode ?? this.tradingMode,
      activePortfolio: activePortfolio ?? this.activePortfolio,
      hasBinanceKeys: hasBinanceKeys ?? this.hasBinanceKeys,
      hasConfiguredDbKeys: hasConfiguredDbKeys ?? this.hasConfiguredDbKeys,
      usingEnvTestKeys: usingEnvTestKeys ?? this.usingEnvTestKeys,
      keysRequiredForCurrentMode:
          keysRequiredForCurrentMode ?? this.keysRequiredForCurrentMode,
      canToggle: canToggle ?? this.canToggle,
    );
  }
}
