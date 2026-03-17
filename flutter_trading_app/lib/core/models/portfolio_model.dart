import '../services/parsing_service.dart';

/// Portfolio Model — بيانات المحفظة
/// منطق صافي — لا يستورد Flutter
class PortfolioModel {
  final double currentBalance;
  final double initialBalance;
  final double totalPnl;
  final double totalPnlPct;
  final double dailyPnl;
  final double dailyPnlPct;
  final double availableBalance;
  final double reservedBalance;
  final String? lastUpdated;

  const PortfolioModel({
    required this.currentBalance,
    required this.initialBalance,
    this.totalPnl = 0,
    this.totalPnlPct = 0,
    this.dailyPnl = 0,
    this.dailyPnlPct = 0,
    this.availableBalance = 0,
    this.reservedBalance = 0,
    this.lastUpdated,
  });

  factory PortfolioModel.fromJson(Map<String, dynamic> json) {
    final current = ParsingService.asDouble(
      json['totalBalance'] ?? json['current_balance'] ?? json['balance'] ?? 0,
    );
    final initial = ParsingService.asDouble(
      json['initialBalance'] ?? json['initial_balance'] ?? 0,
    );
    final totalPnl = ParsingService.asDouble(
      json['totalPnL'] ??
          json['total_pnl'] ??
          json['totalProfitLoss'] ??
          json['total_profit_loss'] ??
          (current - initial),
    );

    return PortfolioModel(
      currentBalance: current,
      initialBalance: initial,
      totalPnl: totalPnl,
      totalPnlPct: (json['totalPnLPercentage'] ?? json['total_pnl_pct']) != null
          ? ParsingService.asDouble(
              json['totalPnLPercentage'] ?? json['total_pnl_pct'],
            )
          : (initial > 0 ? (totalPnl / initial) * 100 : 0),
      dailyPnl: ParsingService.asDouble(
        json['dailyPnL'] ?? json['daily_pnl'] ?? 0,
      ),
      dailyPnlPct: ParsingService.asDouble(
        json['dailyPnLPercentage'] ??
            json['daily_pnl_pct'] ??
            json['daily_pnl_percentage'] ??
            0,
      ),
      availableBalance: ParsingService.asDouble(
        json['availableBalance'] ?? json['available_balance'] ?? current,
      ),
      reservedBalance: ParsingService.asDouble(
        json['lockedBalance'] ??
            json['reserved_balance'] ??
            json['investedBalance'] ??
            json['invested_balance'] ??
            0,
      ),
      lastUpdated:
          (json['lastUpdate'] ?? json['last_updated'] ?? json['updated_at'])
              ?.toString(),
    );
  }

  Map<String, dynamic> toJson() => {
    'current_balance': currentBalance,
    'initial_balance': initialBalance,
    'total_pnl': totalPnl,
    'total_pnl_pct': totalPnlPct,
    'daily_pnl': dailyPnl,
    'daily_pnl_pct': dailyPnlPct,
    'available_balance': availableBalance,
    'reserved_balance': reservedBalance,
    'last_updated': lastUpdated,
  };
}
