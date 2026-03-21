import '../services/parsing_service.dart';

/// Stats Model — إحصائيات التداول
/// منطق صافي — لا يستورد Flutter
class StatsModel {
  final int totalTrades;
  final int closedTrades;
  final int activeTrades;
  final int winningTrades;
  final int losingTrades;
  final double winRate;
  final double bestTrade;
  final double worstTrade;
  final double averagePnl;
  final double totalPnl;
  final double realizedPnl;
  final double unrealizedPnl;
  final double profitFactor;

  const StatsModel({
    this.totalTrades = 0,
    this.closedTrades = 0,
    this.activeTrades = 0,
    this.winningTrades = 0,
    this.losingTrades = 0,
    this.winRate = 0,
    this.bestTrade = 0,
    this.worstTrade = 0,
    this.averagePnl = 0,
    this.totalPnl = 0,
    this.realizedPnl = 0,
    this.unrealizedPnl = 0,
    this.profitFactor = 0,
  });

  factory StatsModel.fromJson(Map<String, dynamic> json) {
    final total = ParsingService.asInt(
      json['totalTrades'] ?? json['total_trades'] ?? 0,
    );
    final closed = ParsingService.asInt(
      json['closedTrades'] ?? json['closed_trades'] ?? total,
    );
    final active = ParsingService.asInt(
      json['activeTrades'] ?? json['active_trades'] ?? 0,
    );
    final wins = ParsingService.asInt(
      json['winningTrades'] ?? json['winning_trades'] ?? 0,
    );

    return StatsModel(
      totalTrades: total,
      closedTrades: closed,
      activeTrades: active,
      winningTrades: wins,
      losingTrades: ParsingService.asInt(
        json['losingTrades'] ?? json['losing_trades'] ?? closed - wins,
      ),
      winRate: ParsingService.asDouble(
        json['winRate'] ??
            json['win_rate'] ??
            (closed > 0 ? wins / closed * 100 : 0),
      ),
      bestTrade: ParsingService.asDouble(
        json['bestTrade'] ?? json['best_trade'] ?? 0,
      ),
      worstTrade: ParsingService.asDouble(
        json['worstTrade'] ?? json['worst_trade'] ?? 0,
      ),
      averagePnl: ParsingService.asDouble(
        json['averageProfit'] ??
            json['avg_profit'] ??
            json['average_pnl'] ??
            json['avg_pnl'] ??
            0,
      ),
      totalPnl: ParsingService.asDouble(
        json['totalProfit'] ??
            json['totalProfitLoss'] ??
            json['total_profit_loss'] ??
            json['total_pnl'] ??
            0,
      ),
      realizedPnl: ParsingService.asDouble(
        json['realizedPnL'] ?? json['realized_pnl'] ?? 0,
      ),
      unrealizedPnl: ParsingService.asDouble(
        json['unrealizedPnL'] ?? json['unrealized_pnl'] ?? 0,
      ),
      profitFactor: ParsingService.asDouble(
        json['profitFactor'] ?? json['profit_factor'] ?? 0,
      ),
    );
  }

  Map<String, dynamic> toJson() => {
    'total_trades': totalTrades,
    'closed_trades': closedTrades,
    'active_trades': activeTrades,
    'winning_trades': winningTrades,
    'losing_trades': losingTrades,
    'win_rate': winRate,
    'best_trade': bestTrade,
    'worst_trade': worstTrade,
    'average_pnl': averagePnl,
    'total_pnl': totalPnl,
    'realized_pnl': realizedPnl,
    'unrealized_pnl': unrealizedPnl,
    'profit_factor': profitFactor,
  };
}
