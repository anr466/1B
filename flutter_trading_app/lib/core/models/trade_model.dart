import '../services/parsing_service.dart';

/// Trade Model — بيانات صفقة واحدة
/// منطق صافي — لا يستورد Flutter
class TradeModel {
  final int? id;
  final int userId;
  final String symbol;
  final String side;
  final String status;
  final double entryPrice;
  final double? currentPrice;
  final double? exitPrice;
  final double quantity;
  final double? positionSize;
  final double? pnl;
  final double? pnlPct;
  final double? priceChangePct;
  final String? entryTime;
  final String? exitTime;
  final double? stopLoss;
  final double? takeProfit;
  final String? strategy;
  final String? notes;
  final String? timeframe;
  final String? exitReason;
  final double? mlConfidence;

  const TradeModel({
    this.id,
    required this.userId,
    required this.symbol,
    this.side = 'BUY',
    this.status = 'open',
    required this.entryPrice,
    this.currentPrice,
    this.exitPrice,
    required this.quantity,
    this.positionSize,
    this.pnl,
    this.pnlPct,
    this.priceChangePct,
    this.entryTime,
    this.exitTime,
    this.stopLoss,
    this.takeProfit,
    this.strategy,
    this.notes,
    this.timeframe,
    this.exitReason,
    this.mlConfidence,
  });

  bool get isWin => (pnl ?? 0) > 0;
  bool get isOpen => status == 'open' || status == 'active';
  bool get isClosed => status == 'closed' || status == 'completed';
  bool get isBuy => side.toUpperCase() == 'BUY' || side.toUpperCase() == 'LONG';
  double get entryAmount => positionSize ?? (entryPrice * quantity);
  double? get stopLossPct => stopLoss != null && entryPrice > 0
      ? ((entryPrice - stopLoss!) / entryPrice) * (isBuy ? 100 : -100)
      : null;
  double? get takeProfitPct => takeProfit != null && entryPrice > 0
      ? ((takeProfit! - entryPrice) / entryPrice) * (isBuy ? 100 : -100)
      : null;

  factory TradeModel.fromJson(Map<String, dynamic> json) {
    final positionTypeRaw = json['positionType'] ?? json['position_type'];
    final exitPriceRaw = json['exitPrice'] ?? json['exit_price'];
    final currentPriceRaw = json['currentPrice'] ?? json['current_price'];
    final pnlRaw =
        json['pnl'] ??
        json['profitLoss'] ??
        json['profit_loss'] ??
        json['unrealizedPnl'];
    final pnlPctRaw =
        json['pnlPercentage'] ??
        json['pnl_pct'] ??
        json['profit_pct'] ??
        json['profitLossPercentage'] ??
        json['unrealizedPnlPct'];
    final stopLossRaw = json['stopLoss'] ?? json['stop_loss'];
    final takeProfitRaw = json['takeProfit'] ?? json['take_profit'];
    final entryTimeRaw =
        json['openedAt'] ??
        json['entryTime'] ??
        json['entry_time'] ??
        json['entryDate'];
    final exitTimeRaw =
        json['closedAt'] ??
        json['exitTime'] ??
        json['exit_time'] ??
        json['closed_at'] ??
        json['updatedAt'];
    final sideRaw = json['side'] ?? positionTypeRaw ?? 'BUY';
    final normalizedSide = switch ((sideRaw as String).toUpperCase()) {
      'LONG' => 'BUY',
      'BUY' => 'BUY',
      'SHORT' => 'SELL',
      'SELL' => 'SELL',
      _ => 'BUY',
    };

    return TradeModel(
      id: json['id'] == null ? null : ParsingService.asInt(json['id']),
      userId: ParsingService.asInt(json['user_id'] ?? json['userId'] ?? 0),
      symbol: json['symbol'] as String? ?? '',
      side: normalizedSide,
      status: json['status'] as String? ?? 'open',
      entryPrice: ParsingService.asDouble(
        json['entryPrice'] ?? json['entry_price'] ?? 0,
      ),
      currentPrice: ParsingService.asNullableDouble(currentPriceRaw),
      exitPrice: ParsingService.asNullableDouble(exitPriceRaw),
      quantity: ParsingService.asDouble(json['quantity'] ?? 0),
      positionSize: ParsingService.asNullableDouble(
        json['positionSize'] ?? json['position_size'] ?? json['entryAmount'],
      ),
      pnl: ParsingService.asNullableDouble(pnlRaw),
      pnlPct: ParsingService.asNullableDouble(pnlPctRaw),
      priceChangePct: ParsingService.asNullableDouble(
        json['priceChangePct'] ?? json['price_change_pct'],
      ),
      entryTime: entryTimeRaw?.toString(),
      exitTime: exitTimeRaw?.toString(),
      stopLoss: ParsingService.asNullableDouble(stopLossRaw),
      takeProfit: ParsingService.asNullableDouble(takeProfitRaw),
      strategy: (json['strategyName'] ?? json['strategy']) as String?,
      notes: json['notes'] as String?,
      timeframe: json['timeframe'] as String?,
      exitReason: (json['exitReason'] ?? json['exit_reason']) as String?,
      mlConfidence: ParsingService.asNullableDouble(
        json['mlConfidence'] ?? json['ml_confidence'],
      ),
    );
  }

  Map<String, dynamic> toJson() => {
    'id': id,
    'user_id': userId,
    'symbol': symbol,
    'side': side,
    'status': status,
    'entry_price': entryPrice,
    'current_price': currentPrice,
    'exit_price': exitPrice,
    'quantity': quantity,
    'position_size': positionSize,
    'pnl': pnl,
    'pnl_pct': pnlPct,
    'entry_time': entryTime,
    'exit_time': exitTime,
    'stop_loss': stopLoss,
    'take_profit': takeProfit,
    'strategy': strategy,
    'notes': notes,
    'timeframe': timeframe,
    'exit_reason': exitReason,
    'ml_confidence': mlConfidence,
  };
}
