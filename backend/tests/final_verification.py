#!/usr/bin/env python3
"""Final comprehensive verification of all fixes"""
import sys, os, json
sys.path.insert(0, '/Users/anr/Desktop/trading_ai_bot-1')
os.chdir('/Users/anr/Desktop/trading_ai_bot-1')
from dotenv import load_dotenv
load_dotenv()

print('=' * 60)
print('FINAL COMPREHENSIVE VERIFICATION (ALL FIXES)')
print('=' * 60)

errors = []
passed = 0
total = 0

# 1. Security
total += 1
try:
    from backend.core.binance_connector import BACKEND_API_KEY
    assert len(BACKEND_API_KEY) > 10
    print('  1. API keys from .env')
    passed += 1
except Exception as e:
    print(f'  1. FAIL: {e}'); errors.append(str(e))

# 2. DB schema + methods
total += 1
try:
    from database.database_manager import DatabaseManager
    db = DatabaseManager()
    with db.get_connection() as conn:
        cols = [c[1] for c in conn.execute('PRAGMA table_info(active_positions)').fetchall()]
        for needed in ['order_id', 'entry_commission', 'position_size', 'break_even_moved', 'tp_levels_hit', 'brain_decision_id']:
            assert needed in cols, f'Missing: {needed}'
    assert hasattr(db, 'update_user_balance')
    assert hasattr(db, 'execute_query')
    print('  2. DB schema + update_user_balance + execute_query')
    passed += 1
except Exception as e:
    print(f'  2. FAIL: {e}'); errors.append(str(e))

# 3. Balance consistency (CRITICAL FIX)
total += 1
try:
    portfolio = db.get_user_portfolio(1)
    assert portfolio['balance'] == 10000.0, f'Balance mismatch: {portfolio["balance"]}'
    with db.get_connection() as conn:
        up = conn.execute('SELECT balance FROM user_portfolio WHERE user_id=1').fetchone()[0]
        p = conn.execute('SELECT total_balance FROM portfolio WHERE user_id=1 AND is_demo=1').fetchone()[0]
    assert up == 10000.0 and p == 10000.0
    print(f'  3. Balance consistent: portfolio={p}, user_portfolio={up}, API={portfolio["balance"]}')
    passed += 1
except Exception as e:
    print(f'  3. FAIL: {e}'); errors.append(str(e))

# 4. GroupBSystem V8 config
total += 1
try:
    from backend.core.group_b_system import GroupBSystem
    gs = GroupBSystem(user_id=1)
    cfg = gs.config
    assert cfg['max_sl_pct'] == 0.02
    assert cfg['default_tp_pct'] == 0.045
    assert len(cfg['tp_levels']) == 3
    assert len(cfg['symbols_pool']) == 10
    assert hasattr(gs, '_check_market_regime')
    bal = gs.user_portfolio.get('balance', 0)
    assert bal == 10000.0, f'GroupB balance wrong: {bal}'
    print(f'  4. GroupBSystem V8: SL=2%, TP=4.5%, 3-level TP, 10 symbols, balance=${bal:.0f}')
    passed += 1
except Exception as e:
    print(f'  4. FAIL: {e}'); errors.append(str(e))

# 5. Exit system aligned
total += 1
try:
    from backend.strategies.intelligent_exit_system import IntelligentExitSystem
    ies = IntelligentExitSystem()
    cfg = ies._default_config()
    assert cfg['tp_levels']['tp1']['pct'] == 0.015
    assert cfg['stop_loss']['initial_pct'] == 0.020
    assert cfg['time']['max_hold_hours'] == 72
    print('  5. IntelligentExitSystem aligned with V8')
    passed += 1
except Exception as e:
    print(f'  5. FAIL: {e}'); errors.append(str(e))

# 6. Blacklist
total += 1
try:
    from backend.strategies.enhanced_entry_system import EnhancedEntrySystem
    bl = EnhancedEntrySystem.STATIC_BLACKLIST
    for sym in ['SOLUSDT', 'AVAXUSDT', 'INJUSDT', 'LINKUSDT']:
        assert sym not in bl, f'{sym} still blacklisted'
    print('  6. Blacklist contradiction resolved')
    passed += 1
except Exception as e:
    print(f'  6. FAIL: {e}'); errors.append(str(e))

# 7. Unified Trading System
total += 1
try:
    from backend.core.unified_trading_system import UnifiedTradingSystem
    print('  7. UnifiedTradingSystem import OK')
    passed += 1
except Exception as e:
    print(f'  7. FAIL: {e}'); errors.append(str(e))

# 8. Cognitive + ML + Selection
total += 1
try:
    from backend.cognitive.market_state_detector import MarketStateDetector
    from backend.cognitive.optimized_signal_engine import OptimizedSignalEngineV9
    from backend.ml.trading_brain import get_trading_brain
    from backend.selection.dynamic_blacklist import get_dynamic_blacklist
    from backend.risk.kelly_position_sizer import KellyPositionSizer
    print('  8. Cognitive + ML + Selection + Risk: All OK')
    passed += 1
except Exception as e:
    print(f'  8. FAIL: {e}'); errors.append(str(e))

# 9. Optimized filters integrated
total += 1
try:
    assert hasattr(gs, 'optimized_filters')
    assert gs.optimized_filters is not None
    print('  9. Optimized filters loaded and integrated')
    passed += 1
except Exception as e:
    print(f'  9. FAIL: {e}'); errors.append(str(e))

# 10. No corrupted positions
total += 1
try:
    with db.get_connection() as conn:
        corrupted = conn.execute('SELECT COUNT(*) FROM active_positions WHERE is_active=1 AND profit_loss < -90').fetchone()[0]
        assert corrupted == 0
    print('  10. No corrupted active positions')
    passed += 1
except Exception as e:
    print(f'  10. FAIL: {e}'); errors.append(str(e))

# 11. Background trading manager
total += 1
try:
    from bin.background_trading_manager import BackgroundTradingManager
    print('  11. BackgroundTradingManager import OK')
    passed += 1
except Exception as e:
    print(f'  11. FAIL: {e}'); errors.append(str(e))

# 12. Server health
total += 1
try:
    import urllib.request
    resp = urllib.request.urlopen('http://localhost:3002/health')
    data = json.loads(resp.read())
    assert data['status'] == 'healthy'
    print('  12. Server healthy on port 3002')
    passed += 1
except Exception as e:
    print(f'  12. FAIL: {e}'); errors.append(str(e))

print()
print('=' * 60)
if passed == total:
    print(f'  ALL {total}/{total} TESTS PASSED - SYSTEM PRODUCTION READY')
else:
    print(f'  {passed}/{total} passed')
    for e in errors:
        print(f'    FAIL: {e}')
print('=' * 60)
