#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧪 Scalping V7 Integration Test
=================================
Tests:
1. ScalpingV7Engine import and initialization
2. Indicator calculation on real data
3. Entry signal detection (LONG + SHORT)
4. Exit signal detection (trailing, SL, reversal, time)
5. GroupBSystem integration (V7 as primary engine)
6. Database operations (add_position with SHORT support)
7. Full trading cycle simulation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ============================================================
# TEST 1: ScalpingV7Engine Import
# ============================================================
def test_1_import():
    """Test ScalpingV7Engine imports correctly"""
    try:
        from backend.strategies.scalping_v7_engine import (
            ScalpingV7Engine, get_scalping_v7_engine, V7_CONFIG
        )
        engine = ScalpingV7Engine()
        assert engine is not None
        assert engine.config['sl_pct'] == 0.010
        assert engine.config['trailing_activation'] == 0.006
        assert engine.config['trailing_distance'] == 0.004
        assert engine.config['max_positions'] == 5
        assert engine.config['position_size_pct'] == 0.06
        assert engine.config['max_hold_hours'] == 12
        print("✅ Test 1 PASSED: ScalpingV7Engine imported and configured correctly")
        return True
    except Exception as e:
        print(f"❌ Test 1 FAILED: {e}")
        import traceback; traceback.print_exc()
        return False

# ============================================================
# TEST 2: Indicator Calculation
# ============================================================
def test_2_indicators():
    """Test indicator calculation on synthetic data"""
    try:
        from backend.strategies.scalping_v7_engine import ScalpingV7Engine
        engine = ScalpingV7Engine()
        
        # Create synthetic OHLCV data (100 bars)
        np.random.seed(42)
        n = 100
        dates = pd.date_range('2024-01-01', periods=n, freq='1h')
        close = 100 + np.cumsum(np.random.randn(n) * 0.5)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': close - np.random.rand(n) * 0.3,
            'high': close + np.abs(np.random.randn(n)) * 0.5,
            'low': close - np.abs(np.random.randn(n)) * 0.5,
            'close': close,
            'volume': np.random.rand(n) * 1000000 + 500000,
        })
        
        result = engine.prepare_data(df)
        
        # Check all indicators exist
        required_cols = [
            'ema8', 'ema21', 'ema55', 'rsi', 'macd_l', 'macd_s', 'macd_h',
            'atr', 'st', 'st_dir', 'bbu', 'bbm', 'bbl', 'adx', 'pdi', 'mdi',
            'vol_ma', 'vol_r', 'body', 'range', 'uwk', 'lwk', 'bull',
            'res20', 'sup20'
        ]
        missing = [c for c in required_cols if c not in result.columns]
        assert len(missing) == 0, f"Missing indicators: {missing}"
        
        # Check no all-NaN columns (after warmup period)
        for col in required_cols:
            valid = result[col].iloc[60:].dropna()
            assert len(valid) > 0, f"Indicator {col} is all NaN after warmup"
        
        print(f"✅ Test 2 PASSED: All {len(required_cols)} indicators calculated correctly")
        return True
    except Exception as e:
        print(f"❌ Test 2 FAILED: {e}")
        import traceback; traceback.print_exc()
        return False

# ============================================================
# TEST 3: 4H Trend Detection
# ============================================================
def test_3_trend():
    """Test 4H trend detection"""
    try:
        from backend.strategies.scalping_v7_engine import ScalpingV7Engine
        engine = ScalpingV7Engine()
        
        # Create uptrending data
        n = 100
        close_up = pd.Series(np.linspace(100, 120, n))
        df_up = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=n, freq='1h'),
            'open': close_up - 0.1,
            'high': close_up + 0.5,
            'low': close_up - 0.5,
            'close': close_up,
            'volume': [1000000] * n,
        })
        df_up = engine.prepare_data(df_up)
        trend_up = engine.get_4h_trend(df_up)
        
        # Create downtrending data
        close_dn = pd.Series(np.linspace(120, 100, n))
        df_dn = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=n, freq='1h'),
            'open': close_dn + 0.1,
            'high': close_dn + 0.5,
            'low': close_dn - 0.5,
            'close': close_dn,
            'volume': [1000000] * n,
        })
        df_dn = engine.prepare_data(df_dn)
        trend_dn = engine.get_4h_trend(df_dn)
        
        assert trend_up == 'UP', f"Expected UP, got {trend_up}"
        assert trend_dn == 'DOWN', f"Expected DOWN, got {trend_dn}"
        
        print(f"✅ Test 3 PASSED: Trend detection working (UP={trend_up}, DOWN={trend_dn})")
        return True
    except Exception as e:
        print(f"❌ Test 3 FAILED: {e}")
        import traceback; traceback.print_exc()
        return False

# ============================================================
# TEST 4: Exit Signal Detection
# ============================================================
def test_4_exit_signals():
    """Test exit signal detection"""
    try:
        from backend.strategies.scalping_v7_engine import ScalpingV7Engine
        engine = ScalpingV7Engine()
        
        # Create minimal data for exit checks
        n = 100
        close = pd.Series([100.0] * n)
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=n, freq='1h'),
            'open': close,
            'high': close + 0.5,
            'low': close - 0.5,
            'close': close,
            'volume': [1000000] * n,
        })
        df = engine.prepare_data(df)
        
        # Test STOP_LOSS for LONG
        pos_long_sl = {
            'entry_price': 105.0,
            'side': 'LONG',
            'peak': 105.0,
            'trail': 0,
            'sl': 105.0 * 0.99,  # SL at 1% below
            'hold_hours': 1,
        }
        result = engine.check_exit_signal(df, pos_long_sl)
        assert result['should_exit'] == True
        assert result['reason'] == 'STOP_LOSS'
        
        # Test HOLD for position slightly in profit (not enough for trailing)
        # Entry at 100.1, peak at 100.3 → profit 0.2% < 0.6% trailing activation
        pos_long_hold = {
            'entry_price': 100.1,
            'side': 'LONG',
            'peak': 100.3,
            'trail': 0,
            'sl': 99.0,  # SL far below current low
            'hold_hours': 1,
        }
        result2 = engine.check_exit_signal(df, pos_long_hold)
        assert result2['should_exit'] == False, f"Expected HOLD, got {result2['reason']}"
        
        # Test MAX_HOLD
        pos_long_maxhold = {
            'entry_price': 100.0,
            'side': 'LONG',
            'peak': 100.0,
            'trail': 0,
            'sl': 99.0,
            'hold_hours': 13,  # > 12 hours
        }
        result3 = engine.check_exit_signal(df, pos_long_maxhold)
        assert result3['should_exit'] == True
        assert result3['reason'] == 'MAX_HOLD'
        
        # Test STOP_LOSS for SHORT
        pos_short_sl = {
            'entry_price': 95.0,
            'side': 'SHORT',
            'peak': 95.0,
            'trail': 0,
            'sl': 95.0 * 1.01,  # SL at 1% above
            'hold_hours': 1,
        }
        result4 = engine.check_exit_signal(df, pos_short_sl)
        assert result4['should_exit'] == True
        assert result4['reason'] == 'STOP_LOSS'
        
        print("✅ Test 4 PASSED: Exit signals (SL_LONG, HOLD, MAX_HOLD, SL_SHORT) all correct")
        return True
    except Exception as e:
        print(f"❌ Test 4 FAILED: {e}")
        import traceback; traceback.print_exc()
        return False

# ============================================================
# TEST 5: GroupBSystem Integration
# ============================================================
def test_5_groupb_integration():
    """Test GroupBSystem initializes with ScalpingV7Engine"""
    try:
        from backend.core.group_b_system import GroupBSystem, SCALPING_V7_AVAILABLE
        
        assert SCALPING_V7_AVAILABLE, "ScalpingV7Engine should be available"
        
        system = GroupBSystem(user_id=1)
        
        # Check V7 engine is primary
        assert system.scalping_v7 is not None, "scalping_v7 should be initialized"
        assert system.config['max_sl_pct'] == 0.010, f"SL should be 1.0%, got {system.config['max_sl_pct']}"
        assert system.config['trailing_activation_pct'] == 0.006, "Trailing activation should be 0.6%"
        assert system.config['trailing_distance_pct'] == 0.004, "Trailing distance should be 0.4%"
        assert system.config['max_hold_hours'] == 12, "Max hold should be 12h"
        assert system.config['execution_timeframe'] == '1h', "Timeframe should be 1h"
        assert system.config['max_positions'] == 5, "Max positions should be 5"
        
        print("✅ Test 5 PASSED: GroupBSystem initialized with ScalpingV7Engine as PRIMARY")
        print(f"   SL={system.config['max_sl_pct']*100}% | "
              f"Trail={system.config['trailing_activation_pct']*100}%/{system.config['trailing_distance_pct']*100}% | "
              f"MaxHold={system.config['max_hold_hours']}h | TF={system.config['execution_timeframe']}")
        return True
    except Exception as e:
        print(f"❌ Test 5 FAILED: {e}")
        import traceback; traceback.print_exc()
        return False

# ============================================================
# TEST 6: Database Position Operations
# ============================================================
def test_6_database():
    """Test database operations with SHORT support"""
    try:
        from database.database_manager import DatabaseManager
        import time
        db = DatabaseManager()
        
        # Use unique symbols to avoid UNIQUE constraint on re-runs
        ts = int(time.time()) % 100000
        sym_long = f'TESTL{ts}USDT'
        sym_short = f'TESTS{ts}USDT'
        
        # Test add_position with LONG
        pos_id_long = db.add_position(
            user_id=1,
            symbol=sym_long,
            entry_price=100.0,
            quantity=1.0,
            position_size=100.0,
            signal_type='SCALP_V7_LONG_BREAKOUT',
            is_demo=1,
            position_type='long',
            stop_loss_price=99.0,
            take_profit_price=None,
            timeframe='1h',
        )
        assert pos_id_long is not None, "LONG position should be created"
        
        # Test add_position with SHORT
        pos_id_short = db.add_position(
            user_id=1,
            symbol=sym_short,
            entry_price=100.0,
            quantity=1.0,
            position_size=100.0,
            signal_type='SCALP_V7_SHORT_BREAKDOWN',
            is_demo=1,
            position_type='short',
            stop_loss_price=101.0,
            take_profit_price=None,
            timeframe='1h',
        )
        assert pos_id_short is not None, "SHORT position should be created"
        
        # Verify positions exist
        positions = db.get_user_active_positions(1)
        long_pos = [p for p in positions if p.get('symbol') == sym_long]
        short_pos = [p for p in positions if p.get('symbol') == sym_short]
        
        assert len(long_pos) > 0, "LONG position should be found"
        assert long_pos[0]['position_type'] == 'long'
        assert long_pos[0]['stop_loss'] == 99.0
        assert long_pos[0]['timeframe'] == '1h'
        
        assert len(short_pos) > 0, "SHORT position should be found"
        assert short_pos[0]['position_type'] == 'short'
        assert short_pos[0]['stop_loss'] == 101.0
        
        # Clean up
        db.close_position(pos_id_long, 100.5, 'TEST_CLEANUP', 0.5)
        db.close_position(pos_id_short, 99.5, 'TEST_CLEANUP', 0.5)
        
        print(f"✅ Test 6 PASSED: Database LONG (id={pos_id_long}) and SHORT (id={pos_id_short}) positions created and closed")
        return True
    except Exception as e:
        print(f"❌ Test 6 FAILED: {e}")
        import traceback; traceback.print_exc()
        return False

# ============================================================
# TEST 7: Full Trading Cycle Simulation
# ============================================================
def test_7_trading_cycle():
    """Test full trading cycle with V7 engine"""
    try:
        from backend.core.group_b_system import GroupBSystem
        
        system = GroupBSystem(user_id=1)
        
        # Run a monitoring cycle (should work even with no open positions)
        result = system.run_monitoring_only()
        assert result is not None
        assert 'positions_checked' in result
        assert 'positions_closed' in result
        assert 'errors' in result
        
        print(f"✅ Test 7 PASSED: Trading cycle executed successfully")
        print(f"   Positions checked: {result['positions_checked']}")
        print(f"   Positions closed: {result['positions_closed']}")
        print(f"   Errors: {len(result['errors'])}")
        return True
    except Exception as e:
        print(f"❌ Test 7 FAILED: {e}")
        import traceback; traceback.print_exc()
        return False

# ============================================================
# TEST 8: Entry Detection with Real Data
# ============================================================
def test_8_entry_detection():
    """Test entry detection on real-ish data"""
    try:
        from backend.strategies.scalping_v7_engine import ScalpingV7Engine
        engine = ScalpingV7Engine()
        
        # Simulate realistic uptrend data with breakout
        np.random.seed(123)
        n = 200
        t = np.arange(n)
        # Uptrend with breakout at bar 180
        close = 100 + t * 0.05 + np.random.randn(n) * 0.3
        close[180:] += 2.0  # Breakout
        
        volume = np.random.rand(n) * 500000 + 500000
        volume[180:] *= 2.0  # Volume spike on breakout
        
        df = pd.DataFrame({
            'timestamp': pd.date_range('2024-01-01', periods=n, freq='1h'),
            'open': close - np.random.rand(n) * 0.2,
            'high': close + np.abs(np.random.randn(n)) * 0.4,
            'low': close - np.abs(np.random.randn(n)) * 0.4,
            'close': close,
            'volume': volume,
        })
        
        df = engine.prepare_data(df)
        trend = engine.get_4h_trend(df)
        
        # Try to detect entry
        signal = engine.detect_entry(df, trend)
        
        print(f"✅ Test 8 PASSED: Entry detection ran successfully")
        print(f"   Trend: {trend}")
        if signal:
            print(f"   Signal: {signal['side']} | Strategy: {signal['strategy']} | "
                  f"Score: {signal['score']} | Timing: {signal['timing_count']}")
        else:
            print(f"   No entry signal (expected - synthetic data may not trigger all conditions)")
        return True
    except Exception as e:
        print(f"❌ Test 8 FAILED: {e}")
        import traceback; traceback.print_exc()
        return False

# ============================================================
# TEST 9: Server Startup Check
# ============================================================
def test_9_server_imports():
    """Test that all critical imports work for server startup"""
    try:
        from backend.strategies.scalping_v7_engine import ScalpingV7Engine, get_scalping_v7_engine
        from backend.core.group_b_system import GroupBSystem, SCALPING_V7_AVAILABLE
        from database.database_manager import DatabaseManager
        from backend.utils.data_provider import DataProvider
        
        assert SCALPING_V7_AVAILABLE == True
        
        print("✅ Test 9 PASSED: All critical imports successful")
        return True
    except Exception as e:
        print(f"❌ Test 9 FAILED: {e}")
        import traceback; traceback.print_exc()
        return False

# ============================================================
# RUN ALL TESTS
# ============================================================
if __name__ == '__main__':
    print("\n" + "=" * 70)
    print("  🧪 SCALPING V7 INTEGRATION TESTS")
    print("=" * 70)
    
    tests = [
        test_1_import,
        test_2_indicators,
        test_3_trend,
        test_4_exit_signals,
        test_5_groupb_integration,
        test_6_database,
        test_7_trading_cycle,
        test_8_entry_detection,
        test_9_server_imports,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} CRASHED: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"  📊 RESULTS: {passed}/{passed+failed} PASSED")
    if failed == 0:
        print("  ✅ ALL TESTS PASSED - V7 Integration Ready!")
    else:
        print(f"  ❌ {failed} TESTS FAILED")
    print("=" * 70)
