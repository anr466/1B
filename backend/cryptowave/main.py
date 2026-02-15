#!/usr/bin/env python3
"""
CryptoWave Hopper - Unified Trading System
Main entry point for the AI-powered multi-strategy trading bot.

Usage:
    python main.py --mode backtest     # Run backtest
    python main.py --mode paper        # Paper trading
    python main.py --mode live         # Live trading (requires API keys)
"""

import argparse
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cryptowave.cryptowave_hopper import CryptoWaveHopper
from cryptowave.unified_backtester import CryptoWaveBacktester
from cryptowave.ai_predictor import AIPredictor


def run_backtest(symbols: list, days: int = 14):
    """Run comprehensive backtest"""
    print("\n" + "=" * 60)
    print("🔬 CryptoWave Hopper - Backtest Mode")
    print("=" * 60)
    
    backtester = CryptoWaveBacktester()
    result, report = backtester.run_full_backtest(symbols, days)
    
    # Save report
    report_path = os.path.join(os.path.dirname(__file__), '..', '..', 'cryptowave_backtest_report.md')
    with open(report_path, 'w') as f:
        f.write(report)
    
    print(f"\n📄 Report saved to: {report_path}")
    return result


def run_paper_trading(symbols: list):
    """Run paper trading simulation"""
    print("\n" + "=" * 60)
    print("📝 CryptoWave Hopper - Paper Trading Mode")
    print("=" * 60)
    
    bot = CryptoWaveHopper({
        'symbols': symbols,
        'mode': 'paper',
        'loop_interval_seconds': 60,
    })
    
    print("Starting paper trading... (Press Ctrl+C to stop)")
    asyncio.run(bot.run())


def run_live_trading(symbols: list):
    """Run live trading (requires API keys)"""
    print("\n" + "=" * 60)
    print("🚀 CryptoWave Hopper - LIVE Trading Mode")
    print("=" * 60)
    print("\n⚠️  WARNING: This is LIVE trading with real money!")
    
    # Check for API keys
    api_key = os.environ.get('BINANCE_API_KEY')
    api_secret = os.environ.get('BINANCE_API_SECRET')
    
    if not api_key or not api_secret:
        print("❌ Error: BINANCE_API_KEY and BINANCE_API_SECRET must be set")
        print("   Export them in your .env file or environment")
        return
    
    confirmation = input("\nType 'CONFIRM' to start live trading: ")
    if confirmation != 'CONFIRM':
        print("Cancelled.")
        return
    
    bot = CryptoWaveHopper({
        'symbols': symbols,
        'mode': 'live',
        'api_key': api_key,
        'api_secret': api_secret,
        'loop_interval_seconds': 60,
    })
    
    asyncio.run(bot.run())


def main():
    parser = argparse.ArgumentParser(
        description='CryptoWave Hopper - AI-Powered Trading Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py --mode backtest --days 14
    python main.py --mode paper
    python main.py --mode live
        """
    )
    
    parser.add_argument(
        '--mode', '-m',
        choices=['backtest', 'paper', 'live'],
        default='backtest',
        help='Trading mode (default: backtest)'
    )
    
    parser.add_argument(
        '--days', '-d',
        type=int,
        default=14,
        help='Number of days for backtest (default: 14)'
    )
    
    parser.add_argument(
        '--symbols', '-s',
        nargs='+',
        default=None,
        help='List of symbols to trade (default: top 20)'
    )
    
    args = parser.parse_args()
    
    # Default symbols
    default_symbols = [
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'BNBUSDT', 'XRPUSDT',
        'ADAUSDT', 'AVAXUSDT', 'DOTUSDT', 'LINKUSDT', 'MATICUSDT',
        'LTCUSDT', 'UNIUSDT', 'ATOMUSDT', 'NEARUSDT', 'APTUSDT',
        'ARBUSDT', 'OPUSDT', 'INJUSDT', 'LDOUSDT', 'STXUSDT'
    ]
    
    symbols = args.symbols or default_symbols
    
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║           🌊 CryptoWave Hopper Trading Bot 🌊             ║
    ║       AI-Powered Multi-Strategy Trading System            ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    if args.mode == 'backtest':
        run_backtest(symbols, args.days)
    elif args.mode == 'paper':
        run_paper_trading(symbols)
    elif args.mode == 'live':
        run_live_trading(symbols)


if __name__ == '__main__':
    main()
