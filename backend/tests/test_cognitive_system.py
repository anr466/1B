#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test the new Cognitive Trading Architecture"""
import sys, os
sys.path.insert(0, '/Users/anr/Desktop/trading_ai_bot-1')
os.chdir('/Users/anr/Desktop/trading_ai_bot-1')
from dotenv import load_dotenv
load_dotenv()

print('=' * 60)
print('COGNITIVE TRADING ARCHITECTURE - COMPREHENSIVE TEST')
print('=' * 60)

errors = []
passed = 0
total = 0

# 1. Import MarketSurveillanceEngine
total += 1
try:
    from backend.cognitive.market_surveillance_engine import (
        MarketSurveillanceEngine, MarketQuality, MarketPhase,
        BehaviorSignal, get_surveillance_engine
    )
    engine = get_surveillance_engine()
    assert engine is not None
    print('  1. MarketSurveillanceEngine import OK')
    passed += 1
except Exception as e:
    print(f'  1. FAIL: {e}'); errors.append(str(e))

# 2. Import MultiExitEngine
total += 1
try:
    from backend.cognitive.multi_exit_engine import (
        MultiExitEngine, ExitReason, ExitUrgency,
        MultiExitDecision, get_multi_exit_engine
    )
    exit_engine = get_multi_exit_engine()
    assert exit_engine is not None
    print('  2. MultiExitEngine import OK (5 engines)')
    passed += 1
except Exception as e:
    print(f'  2. FAIL: {e}'); errors.append(str(e))

# 3. Import CognitiveOrchestrator
total += 1
try:
    from backend.cognitive.cognitive_orchestrator import (
        CognitiveOrchestrator, CognitiveAction, EntryStrategy,
        CognitiveDecision, get_cognitive_orchestrator
    )
    orchestrator = get_cognitive_orchestrator()
    assert orchestrator is not None
    print('  3. CognitiveOrchestrator import OK')
    passed += 1
except Exception as e:
    print(f'  3. FAIL: {e}'); errors.append(str(e))

# 4. GroupBSystem with cognitive integration
total += 1
try:
    from backend.core.group_b_system import GroupBSystem, COGNITIVE_AVAILABLE
    gs = GroupBSystem(user_id=1)
    assert COGNITIVE_AVAILABLE, "Cognitive system not available"
    assert gs.cognitive_orchestrator is not None, "Orchestrator not initialized"
    assert gs.multi_exit_engine is not None, "MultiExitEngine not initialized"
    print('  4. GroupBSystem + Cognitive: INTEGRATED')
    passed += 1
except Exception as e:
    print(f'  4. FAIL: {e}'); errors.append(str(e))

# 5. Test MarketSurveillanceEngine with real data
total += 1
try:
    from backend.utils.data_provider import DataProvider
    dp = DataProvider()
    df_btc = dp.get_historical_data('BTCUSDT', '4h', limit=100)
    assert df_btc is not None and len(df_btc) > 50

    report = engine.survey('BTCUSDT', df_btc)
    assert report is not None
    assert report.market_quality in [MarketQuality.EXCELLENT, MarketQuality.GOOD,
                                      MarketQuality.FAIR, MarketQuality.POOR, MarketQuality.DANGEROUS]
    print(f'  5. Surveillance BTC: {report.market_quality.value} | '
          f'Phase: {report.market_phase.value} | '
          f'Opp: {report.opportunity_score:.0f}% | Risk: {report.risk_score:.0f}% | '
          f'Trade: {"YES" if report.is_tradeable else "NO"}')
    passed += 1
except Exception as e:
    print(f'  5. FAIL: {e}'); errors.append(str(e))

# 6. Test MultiExitEngine with real data
total += 1
try:
    df_eth = dp.get_historical_data('ETHUSDT', '1h', limit=200)
    assert df_eth is not None

    pos = {'entry_price': df_eth['close'].iloc[-1] * 0.99, 'hold_hours': 10}
    decision = exit_engine.evaluate_exit(df_eth, pos)
    assert decision is not None

    active = [s for s in decision.signals if s.reason.value != 'hold']
    print(f'  6. MultiExitEngine ETH: should_exit={decision.should_exit} | '
          f'Active engines: {len(active)}/5 | '
          f'Primary: {decision.primary_reason.value}')
    passed += 1
except Exception as e:
    print(f'  6. FAIL: {e}'); errors.append(str(e))

# 7. Test CognitiveOrchestrator entry analysis
total += 1
try:
    df_4h = dp.get_historical_data('ETHUSDT', '4h', limit=100)
    df_1h = dp.get_historical_data('ETHUSDT', '1h', limit=50)

    cog_decision = orchestrator.analyze_entry('ETHUSDT', df_4h, df_1h)
    assert cog_decision is not None
    assert cog_decision.action in [CognitiveAction.ENTER, CognitiveAction.STAY_OUT]

    print(f'  7. Cognitive Entry ETH: {cog_decision.action.value} | '
          f'Strategy: {cog_decision.entry_strategy.value} | '
          f'Conf: {cog_decision.confidence:.0f}% | '
          f'Market: {cog_decision.market_state} | '
          f'Phase: {cog_decision.market_phase}')
    passed += 1
except Exception as e:
    print(f'  7. FAIL: {e}'); errors.append(str(e))

# 8. Test CognitiveOrchestrator exit analysis
total += 1
try:
    pos = {
        'entry_price': df_eth['close'].iloc[-1] * 0.99,
        'hold_hours': 24,
        'quantity': 0.5,
        'created_at': '2025-02-06T00:00:00'
    }
    exit_dec = orchestrator.analyze_exit('ETHUSDT', df_eth, pos)
    assert exit_dec is not None

    print(f'  8. Cognitive Exit ETH: {exit_dec.action.value} | '
          f'Risk: {exit_dec.risk_score:.0f}% | '
          f'{exit_dec.reasoning[:60]}')
    passed += 1
except Exception as e:
    print(f'  8. FAIL: {e}'); errors.append(str(e))

# 9. Test full trading cycle with cognitive system
total += 1
try:
    cycle = gs.run_trading_cycle()
    assert 'errors' in cycle
    assert 'positions_checked' in cycle

    print(f'  9. Full Cycle: checked={cycle.get("positions_checked", 0)} | '
          f'closed={cycle.get("positions_closed", 0)} | '
          f'new={cycle.get("new_positions", 0)} | '
          f'errors={len(cycle.get("errors", []))}')
    passed += 1
except Exception as e:
    print(f'  9. FAIL: {e}'); errors.append(str(e))

# 10. Scan multiple coins with cognitive analysis
total += 1
try:
    coins = ['SOLUSDT', 'BNBUSDT', 'AVAXUSDT']
    results = []
    for coin in coins:
        df = dp.get_historical_data(coin, '4h', limit=100)
        if df is not None and len(df) > 50:
            r = engine.survey(coin, df)
            results.append(f'{coin[:3]}:{r.market_quality.value}({r.opportunity_score:.0f}%)')

    print(f'  10. Multi-coin scan: {" | ".join(results)}')
    passed += 1
except Exception as e:
    print(f'  10. FAIL: {e}'); errors.append(str(e))

print()
print('=' * 60)
if passed == total:
    print(f'  ALL {total}/{total} COGNITIVE TESTS PASSED')
else:
    print(f'  {passed}/{total} passed')
    for e in errors:
        print(f'    FAIL: {e}')
print('=' * 60)
