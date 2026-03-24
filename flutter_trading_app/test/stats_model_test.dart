import 'package:flutter_test/flutter_test.dart';
import 'package:trading_app/core/models/stats_model.dart';

void main() {
  group('StatsModel', () {
    test('creates with default values', () {
      final stats = StatsModel();

      expect(stats.totalTrades, 0);
      expect(stats.winRate, 0.0);
      expect(stats.totalPnl, 0.0);
      expect(stats.unrealizedPnl, 0.0);
      expect(stats.profitFactor, 0.0);
    });

    test('creates with custom values', () {
      final stats = StatsModel(
        totalTrades: 100,
        closedTrades: 80,
        activeTrades: 20,
        winRate: 65.5,
        totalPnl: 1250.75,
        unrealizedPnl: 350.20,
        bestTrade: 150.0,
        worstTrade: -50.0,
      );

      expect(stats.totalTrades, 100);
      expect(stats.closedTrades, 80);
      expect(stats.activeTrades, 20);
      expect(stats.winRate, 65.5);
      expect(stats.totalPnl, 1250.75);
      expect(stats.unrealizedPnl, 350.20);
      expect(stats.bestTrade, 150.0);
      expect(stats.worstTrade, -50.0);
    });

    test('fromJson parses camelCase correctly', () {
      final json = {
        'totalTrades': 50,
        'winRate': 60.0,
        'totalProfit': 500.0,
        'unrealizedPnL': 100.0,
      };

      final stats = StatsModel.fromJson(json);

      expect(stats.totalTrades, 50);
      expect(stats.winRate, 60.0);
      expect(stats.totalPnl, 500.0);
      expect(stats.unrealizedPnl, 100.0);
    });

    test('fromJson parses snake_case correctly', () {
      final json = {
        'total_trades': 75,
        'win_rate': 55.0,
        'total_pnl': 800.0,
        'unrealized_pnl': 200.0,
      };

      final stats = StatsModel.fromJson(json);

      expect(stats.totalTrades, 75);
      expect(stats.winRate, 55.0);
      expect(stats.totalPnl, 800.0);
      expect(stats.unrealizedPnl, 200.0);
    });

    test('toJson converts correctly', () {
      final stats = StatsModel(totalTrades: 75, winRate: 55.0, totalPnl: 800.0);

      final json = stats.toJson();

      expect(json['total_trades'], 75);
      expect(json['win_rate'], 55.0);
      expect(json['total_pnl'], 800.0);
    });

    test('calculates winRate when not provided', () {
      final json = {'totalTrades': 40, 'closedTrades': 20, 'winningTrades': 12};

      final stats = StatsModel.fromJson(json);

      expect(stats.winRate, 60.0);
    });

    test('handles missing values gracefully', () {
      final json = <String, dynamic>{};

      final stats = StatsModel.fromJson(json);

      expect(stats.totalTrades, 0);
      expect(stats.winRate, 0.0);
      expect(stats.totalPnl, 0.0);
    });
  });
}
