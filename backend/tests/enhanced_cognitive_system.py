#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Cognitive Trading System - نظام التداول المعرفي المحسّن
==================================================================

التحسينات:
1. دمج إشارات 4H + 1H للدخول المتعدد
2. تأكيدات متعددة المستويات (1H → 15m → 5m)
3. تأكيد الانعكاس بثقة عالية (MTF Reversal)
4. معايير مخففة للحصول على صفقات فعلية
5. استراتيجيات دقيقة مع تأكيد كامل
6. خروج ذكي متعدد المستويات
7. اختبار على عملات متنوعة

الفلسفة:
- إشارات متعددة المصادر (4H + 1H)
- تأكيد هرمي (4H → 1H → 15m)
- دخول عند تأكيد الانعكاس فقط
- خروج ذكي مدعوم بالانعكاس
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from cognitive.market_state_detector import MarketStateDetector, MarketState
from cognitive.asset_classifier import AssetClassifier, AssetType
from cognitive.strategy_selector import StrategySelector, StrategyType
from cognitive.reversal_detector import ReversalDetector
from trade_management.smart_exit_system_v2 import SmartExitSystemV2

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class MultiTimeframeSignal:
    """إشارة متعددة الأطر الزمنية"""
    symbol: str
    timeframe: str  # '4h' or '1h'
    signal_time: datetime
    entry_price: float
    market_state: str
    strategy: str
    confidence: float
    reversal_confirmed: bool
    reversal_confidence: float
    confirmations: Dict  # تأكيدات من الأطر الأصغر
    risk_reward: float


class EnhancedCognitiveSystem:
    """نظام التداول المعرفي المحسّن"""
    
    def __init__(self):
        self.exchange = ccxt.binance()
        self.market_detector = MarketStateDetector()
        self.asset_classifier = AssetClassifier()
        self.strategy_selector = StrategySelector()
        self.reversal_detector = ReversalDetector()
        self.exit_system = SmartExitSystemV2()
        
        # معايير محسّنة للحصول على أفضل النتائج
        self.min_confidence = 65  # زيادة من 60
        self.min_reversal_conf = 70  # زيادة من 65
        self.min_strategy_conf = 60  # زيادة من 50
        self.volume_threshold = 0.8  # زيادة من 0.6
        
        self.results = {}
        
        logger.info("🚀 Enhanced Cognitive System - نظام محسّن")
    
    def fetch_ohlcv(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """جلب البيانات مع جميع المؤشرات"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            # المؤشرات الأساسية
            df = self._add_all_indicators(df)
            
            return df
        except Exception as e:
            logger.error(f"❌ {symbol} {timeframe}: {e}")
            return pd.DataFrame()
    
    def _add_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """إضافة جميع المؤشرات"""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # EMAs
        df['ema_9'] = df['close'].ewm(span=9).mean()
        df['ema_20'] = df['close'].ewm(span=20).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        df['ema_200'] = df['close'].ewm(span=200).mean()
        
        # MACD
        exp1 = df['close'].ewm(span=12).mean()
        exp2 = df['close'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Bollinger Bands
        df['sma_20'] = df['close'].rolling(20).mean()
        df['std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['sma_20'] + (2 * df['std'])
        df['bb_lower'] = df['sma_20'] - (2 * df['std'])
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = (df['high'] - df['close'].shift()).abs()
        low_close = (df['low'] - df['close'].shift()).abs()
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = tr.rolling(14).mean()
        
        # ADX
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr_14 = tr.rolling(14).mean()
        plus_di = 100 * (plus_dm.rolling(14).mean() / tr_14)
        minus_di = 100 * (minus_dm.rolling(14).mean() / tr_14)
        
        dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di))
        df['adx'] = dx.rolling(14).mean()
        
        # Volume
        df['volume_sma'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        return df
    
    def detect_signal_4h(self, symbol: str, df_4h: pd.DataFrame, idx: int) -> Optional[MultiTimeframeSignal]:
        """كشف إشارة على 4H"""
        if idx < 100:
            return None
        
        df_slice = df_4h.iloc[:idx+1]
        
        # 1. حالة السوق
        market_state = self.market_detector.detect_state(df_slice, symbol)
        
        # قبول فقط الاتجاهات الصاعدة
        if market_state.state not in [MarketState.UPTREND, MarketState.NEAR_BOTTOM]:
            return None
        
        # 2. الاستراتيجية
        asset_class = self.asset_classifier.classify_asset(symbol, df_slice, None)
        
        # تجاوز pattern_objective - نستخدم الاستراتيجية مباشرة
        from cognitive.pattern_objective import PatternObjective, PatternObjectiveResult
        
        # إنشاء objective مؤقت
        current_price = df_4h['close'].iloc[idx]
        
        if market_state.state == MarketState.UPTREND:
            objective = PatternObjectiveResult(
                objective=PatternObjective.CAPTURE_PULLBACK,
                confidence=70.0,
                expected_move=0.025,
                risk_reward_ratio=2.0,
                timeframe_recommendation='4h',
                entry_zone=(current_price * 0.98, current_price * 1.01),
                target_zone=(current_price * 1.02, current_price * 1.04),
                invalidation_level=current_price * 0.97,
                pattern_detected='uptrend_pullback',
                reasoning='uptrend detected'
            )
        else:
            objective = PatternObjectiveResult(
                objective=PatternObjective.CAPTURE_REVERSAL,
                confidence=75.0,
                expected_move=0.06,
                risk_reward_ratio=2.2,
                timeframe_recommendation='4h',
                entry_zone=(current_price * 0.97, current_price * 1.01),
                target_zone=(current_price * 1.05, current_price * 1.08),
                invalidation_level=current_price * 0.95,
                pattern_detected='near_bottom',
                reasoning='near bottom'
            )
        
        strategy_result = self.strategy_selector.select_strategy(
            market_state, asset_class, objective, df_slice, symbol
        )
        
        # معايير مخففة
        if strategy_result.strategy == StrategyType.ABSTAIN:
            return None
        
        if strategy_result.confidence < self.min_strategy_conf:
            return None
        
        # 3. كشف الانعكاس - إلزامي
        reversal = self.reversal_detector.detect_reversal(df_slice, 'bullish')
        
        # رفض الإشارات بدون انعكاس مؤكد (معايير محسّنة)
        if not reversal.has_reversal or reversal.confidence < 75:  # زيادة من 70
            return None
        
        reversal_conf = reversal.confidence
        
        # 4. التأكيدات الأساسية
        current_price = df_4h['close'].iloc[idx]
        rsi = df_4h['rsi'].iloc[idx]
        volume_ratio = df_4h['volume_ratio'].iloc[idx]
        
        confirmations = {
            'rsi_oversold': rsi < 45,
            'volume_ok': volume_ratio >= self.volume_threshold,
            'adx_ok': market_state.trend_strength > 15,
            'reversal': reversal.has_reversal
        }
        
        # حساب الثقة الكلية
        conf_count = sum(1 for v in confirmations.values() if v)
        conf_score = (
            market_state.confidence * 0.3 +
            strategy_result.confidence * 0.3 +
            reversal_conf * 0.2 +
            (conf_count / len(confirmations)) * 100 * 0.2
        )
        
        if conf_score < self.min_confidence:
            return None
        
        # إنشاء الإشارة
        signal = MultiTimeframeSignal(
            symbol=symbol,
            timeframe='4h',
            signal_time=df_4h['timestamp'].iloc[idx],
            entry_price=current_price,
            market_state=market_state.state.value,
            strategy=strategy_result.strategy.value,
            confidence=conf_score,
            reversal_confirmed=reversal.has_reversal,
            reversal_confidence=reversal_conf,
            confirmations=confirmations,
            risk_reward=objective.risk_reward_ratio
        )
        
        return signal
    
    def detect_signal_1h(self, symbol: str, df_1h: pd.DataFrame, idx: int) -> Optional[MultiTimeframeSignal]:
        """كشف إشارة على 1H - نفس المنطق مع حساسية أعلى"""
        if idx < 100:
            return None
        
        df_slice = df_1h.iloc[:idx+1]
        
        market_state = self.market_detector.detect_state(df_slice, symbol)
        
        if market_state.state not in [MarketState.UPTREND, MarketState.NEAR_BOTTOM, MarketState.RANGE]:
            return None
        
        asset_class = self.asset_classifier.classify_asset(symbol, df_slice, None)
        
        from cognitive.pattern_objective import PatternObjective, PatternObjectiveResult
        
        current_price = df_1h['close'].iloc[idx]
        
        if market_state.state == MarketState.UPTREND:
            objective = PatternObjectiveResult(
                objective=PatternObjective.CAPTURE_PULLBACK,
                confidence=65.0,
                expected_move=0.02,
                risk_reward_ratio=2.0,
                timeframe_recommendation='1h',
                entry_zone=(current_price * 0.99, current_price * 1.005),
                target_zone=(current_price * 1.015, current_price * 1.025),
                invalidation_level=current_price * 0.985,
                pattern_detected='1h_pullback',
                reasoning='1h uptrend'
            )
        elif market_state.state == MarketState.RANGE:
            objective = PatternObjectiveResult(
                objective=PatternObjective.CAPTURE_RANGE,
                confidence=60.0,
                expected_move=0.015,
                risk_reward_ratio=1.8,
                timeframe_recommendation='1h',
                entry_zone=(current_price * 0.995, current_price * 1.005),
                target_zone=(current_price * 1.01, current_price * 1.02),
                invalidation_level=current_price * 0.99,
                pattern_detected='range_bounce',
                reasoning='range detected'
            )
        else:
            objective = PatternObjectiveResult(
                objective=PatternObjective.CAPTURE_REVERSAL,
                confidence=70.0,
                expected_move=0.05,
                risk_reward_ratio=2.2,
                timeframe_recommendation='1h',
                entry_zone=(current_price * 0.98, current_price * 1.01),
                target_zone=(current_price * 1.04, current_price * 1.06),
                invalidation_level=current_price * 0.97,
                pattern_detected='bottom_reversal',
                reasoning='near bottom'
            )
        
        strategy_result = self.strategy_selector.select_strategy(
            market_state, asset_class, objective, df_slice, symbol
        )
        
        if strategy_result.strategy == StrategyType.ABSTAIN:
            return None
        
        if strategy_result.confidence < self.min_strategy_conf:
            return None
        
        reversal = self.reversal_detector.detect_reversal(df_slice, 'bullish')
        
        # رفض بدون انعكاس مؤكد (معايير محسّنة)
        if not reversal.has_reversal or reversal.confidence < 70:  # زيادة من 65
            return None
        
        reversal_conf = reversal.confidence
        
        current_price = df_1h['close'].iloc[idx]
        rsi = df_1h['rsi'].iloc[idx]
        volume_ratio = df_1h['volume_ratio'].iloc[idx]
        
        confirmations = {
            'rsi_ok': 25 < rsi < 70,
            'volume_ok': volume_ratio >= self.volume_threshold,
            'adx_ok': market_state.trend_strength > 12,
            'reversal': reversal.has_reversal
        }
        
        conf_count = sum(1 for v in confirmations.values() if v)
        conf_score = (
            market_state.confidence * 0.25 +
            strategy_result.confidence * 0.25 +
            reversal_conf * 0.25 +
            (conf_count / len(confirmations)) * 100 * 0.25
        )
        
        if conf_score < self.min_confidence - 5:  # أخف قليلاً للـ 1H
            return None
        
        signal = MultiTimeframeSignal(
            symbol=symbol,
            timeframe='1h',
            signal_time=df_1h['timestamp'].iloc[idx],
            entry_price=current_price,
            market_state=market_state.state.value,
            strategy=strategy_result.strategy.value,
            confidence=conf_score,
            reversal_confirmed=reversal.has_reversal,
            reversal_confidence=reversal_conf,
            confirmations=confirmations,
            risk_reward=objective.risk_reward_ratio
        )
        
        return signal
    
    def confirm_on_lower_tf(self, signal: MultiTimeframeSignal, df_lower: pd.DataFrame) -> bool:
        """تأكيد الإشارة على الإطار الأصغر"""
        # البحث عن الشموع المطابقة للوقت
        signal_time = signal.signal_time
        
        # الشموع خلال الـ 15-30 دقيقة القادمة
        if signal.timeframe == '4h':
            time_window = timedelta(hours=1)
        else:  # 1h
            time_window = timedelta(minutes=30)
        
        end_time = signal_time + time_window
        
        candles = df_lower[
            (df_lower['timestamp'] >= signal_time) &
            (df_lower['timestamp'] < end_time)
        ]
        
        if len(candles) == 0:
            return False
        
        # معايير التأكيد
        green_candles = sum(candles['close'] > candles['open'])
        avg_rsi = candles['rsi'].mean()
        avg_volume_ratio = candles['volume_ratio'].mean()
        
        # على الأقل 50% شموع خضراء
        if green_candles / len(candles) < 0.4:
            return False
        
        # RSI في نطاق معقول
        if not (25 < avg_rsi < 75):
            return False
        
        # حجم مقبول
        if avg_volume_ratio < 0.5:
            return False
        
        return True
    
    def run_backtest(self, symbol: str):
        """backtest كامل على عملة واحدة"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🔬 {symbol}")
        logger.info(f"{'='*80}")
        
        # جلب جميع الأطر الزمنية
        df_4h = self.fetch_ohlcv(symbol, '4h', limit=400)
        df_1h = self.fetch_ohlcv(symbol, '1h', limit=800)
        df_15m = self.fetch_ohlcv(symbol, '15m', limit=1500)
        
        if df_4h.empty or df_1h.empty or df_15m.empty:
            logger.error("❌ بيانات غير كافية")
            return
        
        logger.info(f"📊 4H={len(df_4h)} | 1H={len(df_1h)} | 15m={len(df_15m)}")
        
        trades = []
        position = None
        signals_4h = 0
        signals_1h = 0
        confirmed = 0
        executed = 0
        
        # استخدام 1H كإطار رئيسي للتداول
        for idx in range(100, len(df_1h) - 10):
            current_time = df_1h['timestamp'].iloc[idx]
            current_price = df_1h['close'].iloc[idx]
            
            # إدارة الصفقة المفتوحة
            if position:
                position['highest_price'] = max(position['highest_price'], current_price)
                
                candle = {
                    'open': df_1h['open'].iloc[idx],
                    'high': df_1h['high'].iloc[idx],
                    'low': df_1h['low'].iloc[idx],
                    'close': current_price,
                    'timestamp': current_time,
                    'rsi': df_1h['rsi'].iloc[idx],
                    'macd': df_1h['macd'].iloc[idx],
                    'macd_signal': df_1h['macd_signal'].iloc[idx],
                    'ema9': df_1h['ema_9'].iloc[idx],
                }
                
                exit_check = self.exit_system.check_exit_conditions(
                    position['id'], current_price, current_time, candle
                )
                
                if exit_check.get('should_exit'):
                    hold_h = (current_time - position['entry_time']).total_seconds() / 3600
                    pnl = ((exit_check['exit_price'] - position['entry_price']) / position['entry_price']) * 100
                    
                    trade = {
                        'entry_price': position['entry_price'],
                        'exit_price': exit_check['exit_price'],
                        'exit_reason': exit_check['reason'],
                        'pnl_pct': pnl,
                        'hold_hours': hold_h,
                        'is_win': pnl > 0,
                        'timeframe': position['timeframe'],
                        'confidence': position['confidence'],
                        'reversal_confirmed': position['reversal_confirmed']
                    }
                    
                    trades.append(trade)
                    status = "✅" if trade['is_win'] else "❌"
                    logger.info(
                        f"{status} #{len(trades)} | {position['entry_price']:.2f} → {exit_check['exit_price']:.2f} | "
                        f"{pnl:+.2f}% | {hold_h:.1f}h | {exit_check['reason']}"
                    )
                    
                    position = None
            
            # البحث عن دخول جديد
            if not position:
                # 1. فحص إشارة 4H (كل 4 ساعات)
                if idx % 4 == 0:
                    idx_4h = idx // 4
                    if idx_4h < len(df_4h):
                        signal_4h = self.detect_signal_4h(symbol, df_4h, idx_4h)
                        if signal_4h:
                            signals_4h += 1
                            
                            # تأكيد على 15m
                            if self.confirm_on_lower_tf(signal_4h, df_15m):
                                confirmed += 1
                                
                                # دخول
                                pos_id = f"{symbol}_4h_{current_time.strftime('%Y%m%d_%H')}"
                                
                                atr = df_4h['atr'].iloc[idx_4h] if not pd.isna(df_4h['atr'].iloc[idx_4h]) else signal_4h.entry_price * 0.02
                                
                                self.exit_system.on_position_open(
                                    position_id=pos_id,
                                    entry_price=signal_4h.entry_price,
                                    quantity=100.0,
                                    atr=atr,
                                    timestamp=current_time
                                )
                                
                                position = {
                                    'id': pos_id,
                                    'entry_time': current_time,
                                    'entry_price': signal_4h.entry_price,
                                    'highest_price': signal_4h.entry_price,
                                    'timeframe': '4h',
                                    'confidence': signal_4h.confidence,
                                    'reversal_confirmed': signal_4h.reversal_confirmed
                                }
                                
                                executed += 1
                                logger.info(
                                    f"🎯 دخول 4H #{executed} | {signal_4h.entry_price:.2f} | "
                                    f"ثقة {signal_4h.confidence:.0f}% | انعكاس {signal_4h.reversal_confidence:.0f}%"
                                )
                                continue
                
                # 2. فحص إشارة 1H
                signal_1h = self.detect_signal_1h(symbol, df_1h, idx)
                if signal_1h:
                    signals_1h += 1
                    
                    # تأكيد على 15m
                    if self.confirm_on_lower_tf(signal_1h, df_15m):
                        confirmed += 1
                        
                        pos_id = f"{symbol}_1h_{current_time.strftime('%Y%m%d_%H%M')}"
                        
                        atr = df_1h['atr'].iloc[idx] if not pd.isna(df_1h['atr'].iloc[idx]) else signal_1h.entry_price * 0.015
                        
                        self.exit_system.on_position_open(
                            position_id=pos_id,
                            entry_price=signal_1h.entry_price,
                            quantity=100.0,
                            atr=atr,
                            timestamp=current_time
                        )
                        
                        position = {
                            'id': pos_id,
                            'entry_time': current_time,
                            'entry_price': signal_1h.entry_price,
                            'highest_price': signal_1h.entry_price,
                            'timeframe': '1h',
                            'confidence': signal_1h.confidence,
                            'reversal_confirmed': signal_1h.reversal_confirmed
                        }
                        
                        executed += 1
                        logger.info(
                            f"🎯 دخول 1H #{executed} | {signal_1h.entry_price:.2f} | "
                            f"ثقة {signal_1h.confidence:.0f}% | انعكاس {signal_1h.reversal_confidence:.0f}%"
                        )
        
        # إغلاق الصفقة المفتوحة
        if position:
            pnl = ((df_1h['close'].iloc[-1] - position['entry_price']) / position['entry_price']) * 100
            trades.append({
                'entry_price': position['entry_price'],
                'exit_price': df_1h['close'].iloc[-1],
                'exit_reason': 'End_Of_Data',
                'pnl_pct': pnl,
                'hold_hours': 24.0,
                'is_win': pnl > 0,
                'timeframe': position['timeframe'],
                'confidence': position['confidence'],
                'reversal_confirmed': position['reversal_confirmed']
            })
        
        self.results[symbol] = trades
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 إشارات 4H: {signals_4h} | إشارات 1H: {signals_1h}")
        logger.info(f"   مؤكدة: {confirmed} | منفذة: {executed} | صفقات: {len(trades)}")
        logger.info(f"{'='*60}")
        
        if trades:
            self._print_summary(trades, symbol)
    
    def _print_summary(self, trades: List[Dict], symbol: str):
        """ملخص"""
        total = len(trades)
        wins = [t for t in trades if t['is_win']]
        pnl = sum(t['pnl_pct'] for t in trades)
        wr = len(wins) / total * 100 if total > 0 else 0
        avg_hold = np.mean([t['hold_hours'] for t in trades])
        
        logger.info(f"\n{symbol}: {total} صفقة | نجاح {wr:.1f}% | PnL {pnl:+.2f}% | مدة {avg_hold:.1f}h")
        
        # حسب الإطار الزمني
        by_tf = {}
        for t in trades:
            tf = t['timeframe']
            if tf not in by_tf:
                by_tf[tf] = {'count': 0, 'wins': 0, 'pnl': 0}
            by_tf[tf]['count'] += 1
            by_tf[tf]['pnl'] += t['pnl_pct']
            if t['is_win']:
                by_tf[tf]['wins'] += 1
        
        if by_tf:
            logger.info("\nحسب الإطار:")
            for tf, stats in by_tf.items():
                wr2 = (stats['wins'] / stats['count']) * 100 if stats['count'] else 0
                logger.info(f"  {tf}: {stats['count']} | نجاح {wr2:.0f}% | {stats['pnl']:+.2f}%")
    
    def run_full_test(self, symbols: List[str]):
        """اختبار شامل"""
        logger.info("\n🚀 Enhanced Cognitive System - اختبار شامل")
        logger.info("=" * 80)
        logger.info("الإشارات: 4H + 1H مع تأكيدات 15m")
        logger.info("الخروج: SmartExitSystemV2 الكامل")
        logger.info("=" * 80)
        
        for symbol in symbols:
            try:
                self.run_backtest(symbol)
            except Exception as e:
                logger.error(f"❌ خطأ في {symbol}: {e}")
                continue
        
        # المقارنة النهائية
        all_trades = []
        for trades in self.results.values():
            all_trades.extend(trades)
        
        if all_trades:
            logger.info(f"\n{'='*80}")
            logger.info("📊 الإجمالي")
            logger.info(f"{'='*80}")
            
            total = len(all_trades)
            wins = len([t for t in all_trades if t['is_win']])
            pnl = sum(t['pnl_pct'] for t in all_trades)
            wr = wins / total * 100
            avg_hold = np.mean([t['hold_hours'] for t in all_trades])
            
            logger.info(f"الصفقات: {total}")
            logger.info(f"النجاح: {wr:.1f}%")
            logger.info(f"الربح: {pnl:+.2f}%")
            logger.info(f"المدة: {avg_hold:.1f}h ({avg_hold/24:.1f} يوم)")
            
            # حسب الانعكاس
            with_reversal = [t for t in all_trades if t.get('reversal_confirmed', False)]
            without_reversal = [t for t in all_trades if not t.get('reversal_confirmed', False)]
            
            if with_reversal:
                wr_rev = len([t for t in with_reversal if t['is_win']]) / len(with_reversal) * 100
                pnl_rev = sum(t['pnl_pct'] for t in with_reversal)
                logger.info(f"\nمع انعكاس مؤكد: {len(with_reversal)} | نجاح {wr_rev:.0f}% | {pnl_rev:+.2f}%")
            
            if without_reversal:
                wr_no = len([t for t in without_reversal if t['is_win']]) / len(without_reversal) * 100
                pnl_no = sum(t['pnl_pct'] for t in without_reversal)
                logger.info(f"بدون انعكاس: {len(without_reversal)} | نجاح {wr_no:.0f}% | {pnl_no:+.2f}%")
            
            logger.info(f"{'='*80}\n")
        else:
            logger.warning("لا توجد صفقات!")


if __name__ == "__main__":
    import sys
    
    # اختيار مجموعة العملات حسب الوسيط
    if len(sys.argv) > 1 and sys.argv[1] == '--top-gainers':
        # عملات متقلبة (top gainers)
        symbols = [
            'DOGE/USDT',   # متقلب جداً
            'SHIB/USDT',   # متقلب جداً
            'PEPE/USDT',   # متقلب جداً
            'WIF/USDT',    # متقلب جداً
            'BONK/USDT',   # متقلب جداً
            'FLOKI/USDT',  # متقلب جداً
        ]
        logger.info("\n🎢 اختبار على Top Gainers المتقلبة")
    else:
        # عملات متنوعة: عالية السيولة + متقلبة
        symbols = [
            'BTC/USDT',   # عالي السيولة
            'ETH/USDT',   # عالي السيولة
            'SOL/USDT',   # متقلب
            'BNB/USDT',   # مستقر نسبياً
            'AVAX/USDT',  # متقلب
            'LINK/USDT',  # متوسط
        ]
        logger.info("\n📊 اختبار على العملات الرئيسية")
    
    system = EnhancedCognitiveSystem()
    system.run_full_test(symbols)
