#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧠 نظام الخروج الذكي المتكامل - Intelligent Exit System V1
============================================================

يجمع أفضل المزايا من:
1. UnifiedExitSystem - Multi-TP مع البيع الجزئي
2. AdvancedExitTiming - التوقيت الديناميكي
3. MTF Confirmation - تأكيد الأطر الزمنية الأصغر

المنطق الذكي:
✅ عند TP1: فحص الاتجاه - إذا صاعد → بيع جزئي | إذا هابط → بيع كامل
✅ فحص الأطر الأصغر (15m, 5m) قبل الخروج
✅ Trailing Stop مع حماية الأرباح
✅ التمييز بين الارتداد الصغير والانعكاس الحقيقي
✅ وقف خسارة متحرك ذكي

تاريخ الإنشاء: 2026-01-31
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import requests

logger = logging.getLogger(__name__)


# ============================================================
# 1. التصنيفات والهياكل
# ============================================================

class ExitDecision(Enum):
    """قرارات الخروج"""
    HOLD = "hold"                    # استمرار
    PARTIAL_EXIT = "partial_exit"    # بيع جزئي
    FULL_EXIT = "full_exit"          # بيع كامل


class TrendStatus(Enum):
    """حالة الاتجاه"""
    STRONG_BULLISH = "strong_bullish"
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"
    STRONG_BEARISH = "strong_bearish"


@dataclass
class ExitSignal:
    """إشارة خروج ذكية"""
    decision: ExitDecision
    exit_pct: float              # نسبة البيع (0-1)
    exit_price: float
    reason: str
    confidence: int
    trend_status: TrendStatus
    pnl_pct: float
    trailing_stop: Optional[float] = None
    next_tp: Optional[float] = None


@dataclass
class PositionTracker:
    """تتبع الصفقة"""
    symbol: str
    entry_price: float
    entry_time: datetime
    quantity: float
    remaining_quantity: float
    
    # TP Levels
    tp_levels: List[Dict] = field(default_factory=list)
    tp_hits: int = 0
    
    # Tracking
    highest_price: float = 0
    lowest_price: float = 0
    trailing_active: bool = False
    trailing_stop: float = 0
    
    # Realized
    realized_pnl: float = 0
    partial_exits: List[Dict] = field(default_factory=list)


# ============================================================
# 2. نظام الخروج الذكي
# ============================================================

class IntelligentExitSystem:
    """
    🧠 نظام الخروج الذكي المتكامل
    
    الفلسفة:
    - لا تخرج عند أول TP إذا الاتجاه لا يزال قوياً
    - افحص الأطر الأصغر للتأكد
    - استخدم Trailing لحماية الأرباح
    - ميّز بين التصحيح والانعكاس
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.logger = logger
        self.config = config or self._default_config()
        self.positions: Dict[str, PositionTracker] = {}
    
    def _default_config(self) -> Dict:
        """الإعدادات الافتراضية"""
        return {
            # === Take Profit Levels (متوافق مع Group B V8) ===
            'tp_levels': {
                'tp1': {'pct': 0.015, 'sell_if_bullish': 0.30, 'sell_if_bearish': 0.70},
                'tp2': {'pct': 0.030, 'sell_if_bullish': 0.40, 'sell_if_bearish': 1.0},
                'tp3': {'pct': 0.045, 'sell_if_bullish': 0.30, 'sell_if_bearish': 1.0},
            },
            
            # === Stop Loss (متوافق مع Group B V8) ===
            'stop_loss': {
                'initial_pct': 0.020,        # SL الأولي 2.0%
                'break_even_trigger': 0.015,  # نقل لـ BE عند +1.5%
                'trailing_activation': 0.015, # تفعيل Trailing عند +1.5%
                'trailing_distance': 0.008,   # مسافة Trailing 0.8%
            },
            
            # === Trend Confirmation ===
            'trend': {
                'ema_short': 8,
                'ema_long': 21,
                'rsi_bullish_min': 45,
                'rsi_bearish_max': 55,
                'macd_weight': 0.3,
                'volume_weight': 0.2,
            },
            
            # === Pullback vs Reversal ===
            'pullback': {
                'max_pullback_pct': 0.012,    # < 1.2% = تصحيح
                'reversal_threshold': 0.020,   # > 2.0% = انعكاس
                'confirm_candles': 3,          # عدد الشموع للتأكيد
            },
            
            # === Time Limits ===
            'time': {
                'max_hold_hours': 72,
                'stagnant_hours': 24,
                'stagnant_threshold': 0.005,
            }
        }
    
    # ============================================================
    # تسجيل صفقة جديدة
    # ============================================================
    
    def register_position(
        self,
        symbol: str,
        entry_price: float,
        quantity: float,
        entry_time: datetime = None
    ) -> PositionTracker:
        """تسجيل صفقة جديدة"""
        if isinstance(entry_time, pd.Timestamp):
            entry_time = entry_time.to_pydatetime()
        elif isinstance(entry_time, str):
            try:
                entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            except Exception:
                entry_time = None

        entry_time = entry_time or datetime.now()
        
        # إنشاء مستويات TP
        tp_levels = []
        for name, cfg in self.config['tp_levels'].items():
            tp_levels.append({
                'name': name.upper(),
                'price': entry_price * (1 + cfg['pct']),
                'pct': cfg['pct'],
                'sell_bullish': cfg['sell_if_bullish'],
                'sell_bearish': cfg['sell_if_bearish'],
                'triggered': False
            })
        
        tracker = PositionTracker(
            symbol=symbol,
            entry_price=entry_price,
            entry_time=entry_time,
            quantity=quantity,
            remaining_quantity=quantity,
            tp_levels=tp_levels,
            highest_price=entry_price,
            lowest_price=entry_price
        )
        
        self.positions[symbol] = tracker
        
        self.logger.info(f"📊 [{symbol}] صفقة جديدة @ ${entry_price:.4f}")
        self.logger.info(f"   TP1: +{self.config['tp_levels']['tp1']['pct']*100:.1f}%")
        self.logger.info(f"   TP2: +{self.config['tp_levels']['tp2']['pct']*100:.1f}%")
        self.logger.info(f"   TP3: +{self.config['tp_levels']['tp3']['pct']*100:.1f}%")
        
        return tracker
    
    # ============================================================
    # فحص الخروج الذكي
    # ============================================================
    
    def check_intelligent_exit(
        self,
        symbol: str,
        current_price: float,
        df: pd.DataFrame,
        idx: int,
        smaller_tf_data: Optional[pd.DataFrame] = None
    ) -> ExitSignal:
        """
        🎯 الفحص الذكي للخروج
        
        الخطوات:
        1. فحص SL
        2. فحص TP levels
        3. تحليل الاتجاه الحالي
        4. فحص الأطر الأصغر (إن وجدت)
        5. اتخاذ قرار ذكي
        """
        if symbol not in self.positions:
            return ExitSignal(
                decision=ExitDecision.HOLD,
                exit_pct=0,
                exit_price=current_price,
                reason="No position",
                confidence=0,
                trend_status=TrendStatus.NEUTRAL,
                pnl_pct=0
            )
        
        tracker = self.positions[symbol]
        entry = tracker.entry_price
        
        # تحديث أعلى/أدنى سعر
        if current_price > tracker.highest_price:
            tracker.highest_price = current_price
        if current_price < tracker.lowest_price:
            tracker.lowest_price = current_price
        
        # حساب PnL
        pnl_pct = ((current_price - entry) / entry) * 100
        
        # ===== 1. فحص Stop Loss =====
        sl_check = self._check_stop_loss(tracker, current_price, pnl_pct)
        if sl_check:
            return sl_check
        
        # ===== 2. تحليل الاتجاه =====
        trend = self._analyze_trend(df, idx, smaller_tf_data)
        
        # ===== 3. فحص Trailing Stop =====
        trailing_check = self._check_trailing_stop(tracker, current_price, pnl_pct, trend)
        if trailing_check:
            return trailing_check
        
        # ===== 4. فحص TP Levels مع منطق ذكي =====
        tp_check = self._check_tp_levels_smart(tracker, current_price, pnl_pct, trend, df, idx)
        if tp_check:
            return tp_check
        
        # ===== 5. فحص Time Exit =====
        time_check = self._check_time_exit(tracker, df, idx, pnl_pct, trend)
        if time_check:
            return time_check
        
        # ===== 6. فحص الانعكاس =====
        reversal_check = self._check_reversal(tracker, df, idx, pnl_pct, trend)
        if reversal_check:
            return reversal_check
        
        # === استمرار ===
        return ExitSignal(
            decision=ExitDecision.HOLD,
            exit_pct=0,
            exit_price=current_price,
            reason=f"Hold - Trend: {trend.value} | PnL: {pnl_pct:+.2f}%",
            confidence=0,
            trend_status=trend,
            pnl_pct=pnl_pct,
            trailing_stop=tracker.trailing_stop if tracker.trailing_active else None,
            next_tp=self._get_next_tp(tracker)
        )
    
    # ============================================================
    # فحوصات الخروج الفردية
    # ============================================================
    
    def _check_stop_loss(
        self, 
        tracker: PositionTracker, 
        price: float,
        pnl_pct: float
    ) -> Optional[ExitSignal]:
        """فحص Stop Loss"""
        sl_pct = self.config['stop_loss']['initial_pct'] * 100
        
        if pnl_pct <= -sl_pct:
            return ExitSignal(
                decision=ExitDecision.FULL_EXIT,
                exit_pct=1.0,
                exit_price=price,
                reason=f"🛑 Stop Loss ({pnl_pct:.2f}%)",
                confidence=100,
                trend_status=TrendStatus.BEARISH,
                pnl_pct=pnl_pct
            )
        
        return None
    
    def _check_trailing_stop(
        self,
        tracker: PositionTracker,
        price: float,
        pnl_pct: float,
        trend: TrendStatus
    ) -> Optional[ExitSignal]:
        """فحص وتحديث Trailing Stop"""
        cfg = self.config['stop_loss']
        activation_pct = cfg['trailing_activation'] * 100
        distance_pct = cfg['trailing_distance']
        
        # تفعيل Trailing
        if not tracker.trailing_active and pnl_pct >= activation_pct:
            tracker.trailing_active = True
            tracker.trailing_stop = price * (1 - distance_pct)
            self.logger.info(f"🎯 [{tracker.symbol}] Trailing مُفعّل @ +{pnl_pct:.2f}%")
        
        # تحديث Trailing
        if tracker.trailing_active:
            new_trail = price * (1 - distance_pct)
            if new_trail > tracker.trailing_stop:
                tracker.trailing_stop = new_trail
            
            # فحص: هل ضرب Trailing?
            if price <= tracker.trailing_stop:
                # === منطق ذكي: إذا الاتجاه لا يزال صاعد، توسيع قليلاً ===
                if trend in [TrendStatus.STRONG_BULLISH, TrendStatus.BULLISH]:
                    drawdown = (tracker.highest_price - price) / tracker.highest_price
                    if drawdown < self.config['pullback']['max_pullback_pct']:
                        # تصحيح صغير - توسيع Trailing
                        tracker.trailing_stop = tracker.highest_price * (1 - distance_pct * 1.5)
                        return None
                
                protected_pnl = ((tracker.trailing_stop - tracker.entry_price) / tracker.entry_price) * 100
                return ExitSignal(
                    decision=ExitDecision.FULL_EXIT,
                    exit_pct=1.0,
                    exit_price=tracker.trailing_stop,
                    reason=f"📉 Trailing Stop (Protected +{protected_pnl:.2f}%)",
                    confidence=90,
                    trend_status=trend,
                    pnl_pct=protected_pnl
                )
        
        return None
    
    def _check_tp_levels_smart(
        self,
        tracker: PositionTracker,
        price: float,
        pnl_pct: float,
        trend: TrendStatus,
        df: pd.DataFrame,
        idx: int
    ) -> Optional[ExitSignal]:
        """
        🎯 فحص TP مع منطق ذكي
        
        المنطق:
        - عند TP1 + اتجاه صاعد = بيع 30% فقط
        - عند TP1 + اتجاه هابط = بيع 100%
        - عند TP2 + اتجاه صاعد = بيع 40%
        - وهكذا...
        """
        for level in tracker.tp_levels:
            if not level['triggered'] and price >= level['price']:
                level['triggered'] = True
                tracker.tp_hits += 1
                
                # تحديد نسبة البيع حسب الاتجاه
                if trend in [TrendStatus.STRONG_BULLISH, TrendStatus.BULLISH]:
                    sell_pct = level['sell_bullish']
                    decision = ExitDecision.PARTIAL_EXIT if sell_pct < 1.0 else ExitDecision.FULL_EXIT
                    reason_suffix = "Trend ↑ - Partial sell"
                else:
                    sell_pct = level['sell_bearish']
                    decision = ExitDecision.FULL_EXIT
                    reason_suffix = "Trend ↓ - Full sell"
                
                # تحديث الكمية المتبقية
                sell_qty = tracker.remaining_quantity * sell_pct
                tracker.remaining_quantity -= sell_qty
                
                # تسجيل الخروج الجزئي
                tracker.partial_exits.append({
                    'level': level['name'],
                    'price': price,
                    'quantity': sell_qty,
                    'pnl_pct': pnl_pct,
                    'trend': trend.value
                })
                
                # حساب الربح المحقق
                tracker.realized_pnl += (price - tracker.entry_price) * sell_qty
                
                return ExitSignal(
                    decision=decision,
                    exit_pct=sell_pct,
                    exit_price=price,
                    reason=f"🎯 {level['name']} Hit (+{pnl_pct:.2f}%) - {reason_suffix}",
                    confidence=95,
                    trend_status=trend,
                    pnl_pct=pnl_pct,
                    next_tp=self._get_next_tp(tracker)
                )
        
        return None
    
    def _check_time_exit(
        self,
        tracker: PositionTracker,
        df: pd.DataFrame,
        idx: int,
        pnl_pct: float,
        trend: TrendStatus
    ) -> Optional[ExitSignal]:
        """فحص Time-Based Exit"""
        cfg = self.config['time']
        
        # حساب وقت الاحتفاظ
        if 'timestamp' in df.columns:
            current_time = df['timestamp'].iloc[idx]
        else:
            current_time = datetime.now(tracker.entry_time.tzinfo) if tracker.entry_time.tzinfo else datetime.now()
        if isinstance(current_time, pd.Timestamp):
            current_time = current_time.to_pydatetime()

        if isinstance(current_time, datetime):
            if tracker.entry_time.tzinfo and current_time.tzinfo is None:
                current_time = current_time.replace(tzinfo=tracker.entry_time.tzinfo)
            elif tracker.entry_time.tzinfo is None and current_time.tzinfo is not None:
                current_time = current_time.replace(tzinfo=None)
        
        hold_hours = (current_time - tracker.entry_time).total_seconds() / 3600
        
        # تجاوز الحد الأقصى
        if hold_hours >= cfg['max_hold_hours']:
            return ExitSignal(
                decision=ExitDecision.FULL_EXIT,
                exit_pct=1.0,
                exit_price=df['close'].iloc[idx],
                reason=f"⏰ Max Time ({hold_hours:.0f}h)",
                confidence=80,
                trend_status=trend,
                pnl_pct=pnl_pct
            )
        
        # راكد - لكن فقط إذا الاتجاه ليس صاعداً
        if hold_hours >= cfg['stagnant_hours']:
            if abs(pnl_pct) < cfg['stagnant_threshold'] * 100:
                if trend not in [TrendStatus.STRONG_BULLISH, TrendStatus.BULLISH]:
                    return ExitSignal(
                        decision=ExitDecision.FULL_EXIT,
                        exit_pct=1.0,
                        exit_price=df['close'].iloc[idx],
                        reason=f"💤 Stagnant ({hold_hours:.0f}h) + No trend",
                        confidence=75,
                        trend_status=trend,
                        pnl_pct=pnl_pct
                    )
        
        return None
    
    def _check_reversal(
        self,
        tracker: PositionTracker,
        df: pd.DataFrame,
        idx: int,
        pnl_pct: float,
        trend: TrendStatus
    ) -> Optional[ExitSignal]:
        """
        فحص الانعكاس الذكي
        
        التمييز بين:
        - التصحيح (< 1.5%) = استمرار
        - الانعكاس (> 2.5%) = خروج
        """
        if pnl_pct <= 0.5:  # لا نفحص إلا إذا في ربح
            return None
        
        cfg = self.config['pullback']
        
        # حساب الهبوط من القمة
        drawdown = (tracker.highest_price - df['close'].iloc[idx]) / tracker.highest_price
        
        # تصحيح صغير - استمرار
        if drawdown < cfg['max_pullback_pct']:
            return None
        
        # انعكاس محتمل - فحص إضافي
        if drawdown >= cfg['reversal_threshold']:
            # تأكيد بعدد الشموع الهابطة
            if idx >= cfg['confirm_candles']:
                recent = df.iloc[idx - cfg['confirm_candles']:idx + 1]
                bearish_count = sum(1 for _, r in recent.iterrows() if r['close'] < r['open'])
                
                if bearish_count >= cfg['confirm_candles'] - 1:
                    return ExitSignal(
                        decision=ExitDecision.FULL_EXIT,
                        exit_pct=1.0,
                        exit_price=df['close'].iloc[idx],
                        reason=f"🔄 Reversal Confirmed (-{drawdown*100:.1f}% from peak)",
                        confidence=85,
                        trend_status=TrendStatus.BEARISH,
                        pnl_pct=pnl_pct
                    )
        
        return None
    
    # ============================================================
    # تحليل الاتجاه
    # ============================================================
    
    def _analyze_trend(
        self,
        df: pd.DataFrame,
        idx: int,
        smaller_tf: Optional[pd.DataFrame] = None
    ) -> TrendStatus:
        """
        تحليل الاتجاه الشامل
        
        المعايير:
        1. EMA alignment (40%)
        2. RSI position (30%)
        3. MACD (20%)
        4. Volume (10%)
        """
        if idx < 30:
            return TrendStatus.NEUTRAL
        
        row = df.iloc[idx]
        score = 0
        max_score = 100
        
        # 1. EMA Alignment (40 points)
        ema_short = row.get('ema_8', row.get('ema_short', 0))
        ema_long = row.get('ema_21', row.get('ema_long', 0))
        
        if ema_short > 0 and ema_long > 0:
            ema_diff = (ema_short - ema_long) / ema_long * 100
            if ema_diff > 1:
                score += 40
            elif ema_diff > 0:
                score += 25
            elif ema_diff > -1:
                score += 10
        
        # 2. RSI (30 points)
        rsi = row.get('rsi', 50)
        if rsi > 60:
            score += 30
        elif rsi > 50:
            score += 20
        elif rsi > 40:
            score += 10
        
        # 3. MACD (20 points)
        macd = row.get('macd', 0)
        macd_signal = row.get('macd_signal', 0)
        macd_hist = row.get('macd_hist', macd - macd_signal)
        
        if macd_hist > 0:
            score += 20
        elif macd_hist > -0.0001:
            score += 10
        
        # 4. Price action (10 points)
        if row['close'] > row['open']:
            score += 10
        
        # === فحص الإطار الأصغر إن وجد ===
        if smaller_tf is not None and len(smaller_tf) > 0:
            stf_score = self._analyze_smaller_tf(smaller_tf)
            # متوسط مرجح: 70% للإطار الرئيسي، 30% للأصغر
            score = score * 0.7 + stf_score * 0.3
        
        # تحويل النتيجة لحالة الاتجاه
        if score >= 80:
            return TrendStatus.STRONG_BULLISH
        elif score >= 60:
            return TrendStatus.BULLISH
        elif score >= 40:
            return TrendStatus.NEUTRAL
        elif score >= 20:
            return TrendStatus.BEARISH
        else:
            return TrendStatus.STRONG_BEARISH
    
    def _analyze_smaller_tf(self, df: pd.DataFrame) -> float:
        """تحليل الإطار الزمني الأصغر"""
        if len(df) < 5:
            return 50
        
        score = 50
        last_5 = df.tail(5)
        
        # اتجاه آخر 5 شموع
        bullish = sum(1 for _, r in last_5.iterrows() if r['close'] > r['open'])
        score += (bullish - 2.5) * 10
        
        # اتجاه السعر
        price_change = (last_5['close'].iloc[-1] - last_5['close'].iloc[0]) / last_5['close'].iloc[0] * 100
        score += price_change * 10
        
        return max(0, min(100, score))
    
    # ============================================================
    # دوال مساعدة
    # ============================================================
    
    def _get_next_tp(self, tracker: PositionTracker) -> Optional[float]:
        """الحصول على TP التالي"""
        for level in tracker.tp_levels:
            if not level['triggered']:
                return level['price']
        return None
    
    def get_position(self, symbol: str) -> Optional[PositionTracker]:
        """الحصول على صفقة"""
        return self.positions.get(symbol)
    
    def close_position(self, symbol: str):
        """إغلاق صفقة"""
        if symbol in self.positions:
            del self.positions[symbol]


# ============================================================
# Singleton
# ============================================================

_intelligent_exit_system = None

def get_intelligent_exit_system(config: Optional[Dict] = None) -> IntelligentExitSystem:
    """Get singleton instance"""
    global _intelligent_exit_system
    if _intelligent_exit_system is None:
        _intelligent_exit_system = IntelligentExitSystem(config)
    return _intelligent_exit_system
