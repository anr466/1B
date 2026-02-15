"""
CryptoWave API Endpoints
Exposes CryptoWave trading system to mobile app via REST API.
"""

from flask import Blueprint, request, jsonify, g
from datetime import datetime
import sys
import os

# Add project paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import CryptoWave components
try:
    from backend.cryptowave.db_integration import CryptoWaveDBIntegration
    from backend.cryptowave.unified_backtester import CryptoWaveBacktester
    CRYPTOWAVE_AVAILABLE = True
except ImportError as e:
    CRYPTOWAVE_AVAILABLE = False
    print(f"[WARN] CryptoWave import error: {e}")

# Create Blueprint
cryptowave_bp = Blueprint('cryptowave', __name__, url_prefix='/cryptowave')


def get_user_id():
    """Get current user ID from request context"""
    return getattr(g, 'current_user_id', 1)


@cryptowave_bp.route('/status', methods=['GET'])
def get_system_status():
    """
    Get CryptoWave system status
    
    Returns:
        System health, active strategies, and performance summary
    """
    try:
        user_id = get_user_id()
        integration = CryptoWaveDBIntegration(user_id=user_id)
        
        sync_data = integration.sync_with_mobile_app()
        
        return jsonify({
            'success': True,
            'data': {
                'system': 'CryptoWave Hopper',
                'status': 'running',
                'strategies': ['Scalping', 'DCA', 'Trend Following', 'Grid', 'Arbitrage'],
                'active_positions': len(sync_data.get('active_positions', [])),
                'performance': sync_data.get('performance', {}),
                'last_update': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cryptowave_bp.route('/positions', methods=['GET'])
def get_active_positions():
    """
    Get all active CryptoWave positions for user
    
    Returns:
        List of active positions with entry, SL, TP
    """
    try:
        user_id = get_user_id()
        integration = CryptoWaveDBIntegration(user_id=user_id)
        
        positions = integration.get_active_positions()
        
        return jsonify({
            'success': True,
            'data': {
                'positions': positions,
                'count': len(positions)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cryptowave_bp.route('/performance', methods=['GET'])
def get_performance():
    """
    Get CryptoWave performance metrics
    
    Returns:
        Win rate, total PnL, trade count, etc.
    """
    try:
        user_id = get_user_id()
        integration = CryptoWaveDBIntegration(user_id=user_id)
        
        performance = integration.get_performance_summary()
        
        return jsonify({
            'success': True,
            'data': performance
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cryptowave_bp.route('/backtest', methods=['POST'])
def run_backtest():
    """
    Run CryptoWave backtest
    
    Request body:
        {
            "symbols": ["BTCUSDT", "ETHUSDT"],
            "days": 14
        }
    
    Returns:
        Backtest results with metrics
    """
    try:
        data = request.get_json() or {}
        
        symbols = data.get('symbols', [
            'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT'
        ])
        days = min(data.get('days', 14), 30)  # Max 30 days
        
        backtester = CryptoWaveBacktester()
        result, report = backtester.run_full_backtest(symbols, days)
        
        return jsonify({
            'success': True,
            'data': {
                'total_trades': len(result.trades),
                'win_rate': result.win_rate,
                'total_pnl': result.total_pnl,
                'profit_factor': result.profit_factor,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown': result.max_drawdown,
                'trades_per_day': result.trades_per_day,
                'avg_hold_time_mins': result.avg_hold_time_mins
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@cryptowave_bp.route('/strategies', methods=['GET'])
def get_strategies():
    """
    Get available CryptoWave strategies
    
    Returns:
        List of strategies with their suitability
    """
    return jsonify({
        'success': True,
        'data': {
            'strategies': [
                {
                    'name': 'Scalping',
                    'description': 'RSI + Bollinger Bands reversal trades',
                    'timeframe': 'M5-M15',
                    'risk_level': 'medium',
                    'win_rate': 59.3
                },
                {
                    'name': 'DCA',
                    'description': 'Dollar Cost Averaging on dips',
                    'timeframe': 'H1-H4',
                    'risk_level': 'low',
                    'win_rate': 75.0
                },
                {
                    'name': 'Trend Following',
                    'description': 'AI-powered trend continuation',
                    'timeframe': 'M15-H1',
                    'risk_level': 'medium',
                    'win_rate': 55.0
                },
                {
                    'name': 'Grid Trading',
                    'description': 'Automated grid orders',
                    'timeframe': 'M15',
                    'risk_level': 'low',
                    'win_rate': 65.0
                },
                {
                    'name': 'Arbitrage',
                    'description': 'Cross-exchange price differences',
                    'timeframe': 'M1',
                    'risk_level': 'low',
                    'win_rate': 85.0
                }
            ]
        }
    })


@cryptowave_bp.route('/sync', methods=['GET'])
def sync_mobile():
    """
    Full sync endpoint for mobile app
    
    Returns:
        All CryptoWave data for mobile display
    """
    try:
        user_id = get_user_id()
        integration = CryptoWaveDBIntegration(user_id=user_id)
        
        sync_data = integration.sync_with_mobile_app()
        
        return jsonify({
            'success': True,
            'data': sync_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Register with main app
def register_cryptowave_api(app):
    """Register CryptoWave API blueprint with Flask app"""
    app.register_blueprint(cryptowave_bp)
    print("✅ CryptoWave API registered at /api/cryptowave")
