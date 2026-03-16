#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏆 نظام الخروج الموحد - Unified Exit System V4
==============================================

يجمع أفضل المزايا من:
1. SmartExitSystemV2 - الآليات الأساسية
2. GoldenExitSystem - الحماية المتقدمة
3. SmartExitStrategy - تصنيف العملات الذكي

المزايا الموحدة:
✅ تصنيف العملات حسب النوع (من smart_exit_strategy)
✅ Multi-Level TP ديناميكي (من golden_exit)
✅ Trailing Stop ذكي مع حماية الاتجاه (من smart_exit_v2)
✅ ATR-Based SL ديناميكي
✅ Time-Based Exit للصفقات الراكدة
✅ Reversal Detection متعدد الطرق
✅ Emergency Exit للحماية القصوى

تاريخ الإنشاء: 24 يناير 2026
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# ============================================================
# 1. التصنيفات والهياكل
# ============================================================

class AssetCategory(Enum):
    """تصنيف العملات حسب السلوك"""
    BLUE_CHIP = "blue_chip"       # BTC, ETH - استقرار عالي
    LARGE_CAP = "large_cap"       # BNB, XRP, SOL - سيولة عالية
    MID_CAP = "mid_cap"           # DOT, AVAX - تقلب متوسط
    SMALL_CAP = "small_cap"       # ARB, OP - تقلب عالي
    MEME = "meme"                 # PEPE, SHIB - مضاربة


class ExitReason(Enum):
    """أسباب الخروج"""
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT_1 = "tp1"
    TAKE_PROFIT_2 = "tp2"
    TAKE_PROFIT_3 = "tp3"
    TRAILING_STOP = "trailing"
    TIME_EXIT = "time_exit"
    REVERSAL = "reversal"
    BREAK_EVEN = "break_even"
    EMERGENCY = "emergency"
    STAGNANT = "stagnant"


@dataclass
class AssetProfile:
    """ملف تعريف العملة مع الإعدادات المُثلى"""
    category: AssetCategory
    volatility: float              # التقلب اليومي المتوسط
    optimal_sl_pct: float          # وقف الخسارة المُثلى
    optimal_tp_levels: List[float] # مستويات جني الأرباح [TP1, TP2, TP3]
    tp_close_pcts: List[float]     # نسب الإغلاق عند كل TP
    optimal_trailing_pct: float    # مسافة Trailing المُثلى
    hold_in_trend: bool            # هل نبقى مع الاتجاه؟
    max_hold_hours: int            # أقصى وقت للاحتفاظ


@dataclass
class PositionState:
    """حالة الصفقة الكاملة"""
    position_id: str
    symbol: str
    entry_price: float
    quantity: float
    remaining_quantity: float
    entry_time: datetime
    
    # Asset Profile
    asset_profile: AssetProfile = None
    
    # Stop Loss
    initial_sl: float = 0
    current_sl: float = 0
    sl_moved_to_be: bool = False
    
    # Take Profit
    tp_levels: List[Dict] = field(default_factory=list)
    tp_hit_count: int = 0
    
    # Trailing
    highest_price: float = 0
    trailing_active: bool = False
    trailing_stop: float = 0
    
    # Statistics
    realized_pnl: float = 0
    last_price: float = 0
    last_update: datetime = None
    last_movement_time: datetime = None


# ============================================================
# 2. قاعدة بيانات العملات المعروفة
# ============================================================

ASSET_PROFILES = {
    # === Blue Chip === (V7 - إعدادات النظام الأصلي الناجح)
    'BTCUSDT': AssetProfile(
        category=AssetCategory.BLUE_CHIP,
        volatility=0.025,
        optimal_sl_pct=0.020,  # SL 2% (النظام الأصلي)
        optimal_tp_levels=[0.030, 0.045, 0.060],  # TP 3%/4.5%/6% (R:R 1.5:1)
        tp_close_pcts=[0.50, 0.30, 0.20],  # خروج 50% عند TP1
        optimal_trailing_pct=0.010,
        hold_in_trend=True,
        max_hold_hours=48  # وقت أقل
    ),
    'ETHUSDT': AssetProfile(
        category=AssetCategory.BLUE_CHIP,
        volatility=0.03,
        optimal_sl_pct=0.020,  # SL 2%
        optimal_tp_levels=[0.030, 0.045, 0.060],  # TP 3%/4.5%/6%
        tp_close_pcts=[0.50, 0.30, 0.20],
        optimal_trailing_pct=0.010,
        hold_in_trend=True,
        max_hold_hours=48
    ),
    
    # === Large Cap === (V7 - إعدادات النظام الأصلي الناجح)
    'BNBUSDT': AssetProfile(
        category=AssetCategory.LARGE_CAP,
        volatility=0.035,
        optimal_sl_pct=0.020,  # SL 2%
        optimal_tp_levels=[0.030, 0.045, 0.060],  # TP 3%/4.5%/6%
        tp_close_pcts=[0.50, 0.30, 0.20],
        optimal_trailing_pct=0.010,
        hold_in_trend=True,
        max_hold_hours=48
    ),
    'SOLUSDT': AssetProfile(
        category=AssetCategory.LARGE_CAP,
        volatility=0.045,
        optimal_sl_pct=0.020,  # SL 2%
        optimal_tp_levels=[0.030, 0.045, 0.060],  # TP 3%/4.5%/6%
        tp_close_pcts=[0.50, 0.30, 0.20],
        optimal_trailing_pct=0.010,
        hold_in_trend=True,
        max_hold_hours=48
    ),
    'XRPUSDT': AssetProfile(
        category=AssetCategory.LARGE_CAP,
        volatility=0.04,
        optimal_sl_pct=0.020,  # SL 2%
        optimal_tp_levels=[0.030, 0.045, 0.060],  # TP 3%/4.5%/6%
        tp_close_pcts=[0.50, 0.30, 0.20],
        optimal_trailing_pct=0.010,
        hold_in_trend=True,
        max_hold_hours=48
    ),
    'MATICUSDT': AssetProfile(
        category=AssetCategory.LARGE_CAP,
        volatility=0.05,
        optimal_sl_pct=0.020,  # SL 2%
        optimal_tp_levels=[0.030, 0.045, 0.060],  # TP 3%/4.5%/6%
        tp_close_pcts=[0.50, 0.30, 0.20],
        optimal_trailing_pct=0.010,
        hold_in_trend=True,
        max_hold_hours=48
    ),
    
    # === Mid Cap (تقلب متوسط) ===
    'DOTUSDT': AssetProfile(
        category=AssetCategory.MID_CAP,
        volatility=0.05,
        optimal_sl_pct=0.025,
        optimal_tp_levels=[0.025, 0.045, 0.070],
        tp_close_pcts=[0.45, 0.35, 0.20],
        optimal_trailing_pct=0.020,
        hold_in_trend=False,
        max_hold_hours=48
    ),
    'AVAXUSDT': AssetProfile(
        category=AssetCategory.MID_CAP,
        volatility=0.055,
        optimal_sl_pct=0.028,
        optimal_tp_levels=[0.028, 0.050, 0.080],
        tp_close_pcts=[0.45, 0.35, 0.20],
        optimal_trailing_pct=0.022,
        hold_in_trend=False,
        max_hold_hours=48
    ),
    'ADAUSDT': AssetProfile(
        category=AssetCategory.MID_CAP,
        volatility=0.045,
        optimal_sl_pct=0.025,
        optimal_tp_levels=[0.025, 0.045, 0.070],
        tp_close_pcts=[0.45, 0.35, 0.20],
        optimal_trailing_pct=0.020,
        hold_in_trend=False,
        max_hold_hours=48
    ),
    
    # === Small Cap (تقلب عالي) ===
    'ARBUSDT': AssetProfile(
        category=AssetCategory.SMALL_CAP,
        volatility=0.06,
        optimal_sl_pct=0.030,
        optimal_tp_levels=[0.030, 0.055, 0.090],
        tp_close_pcts=[0.50, 0.30, 0.20],
        optimal_trailing_pct=0.025,
        hold_in_trend=False,
        max_hold_hours=36
    ),
    'OPUSDT': AssetProfile(
        category=AssetCategory.SMALL_CAP,
        volatility=0.06,
        optimal_sl_pct=0.030,
        optimal_tp_levels=[0.030, 0.055, 0.090],
        tp_close_pcts=[0.50, 0.30, 0.20],
        optimal_trailing_pct=0.025,
        hold_in_trend=False,
        max_hold_hours=36
    ),
    
    # === Meme (مضاربة سريعة) ===
    'PEPEUSDT': AssetProfile(
        category=AssetCategory.MEME,
        volatility=0.10,
        optimal_sl_pct=0.050,
        optimal_tp_levels=[0.050, 0.100, 0.200],
        tp_close_pcts=[0.60, 0.30, 0.10],
        optimal_trailing_pct=0.045,
        hold_in_trend=False,
        max_hold_hours=24
    ),
    'SHIBUSDT': AssetProfile(
        category=AssetCategory.MEME,
        volatility=0.08,
        optimal_sl_pct=0.045,
        optimal_tp_levels=[0.045, 0.090, 0.150],
        tp_close_pcts=[0.60, 0.30, 0.10],
        optimal_trailing_pct=0.040,
        hold_in_trend=False,
        max_hold_hours=24
    ),
    'DOGEUSDT': AssetProfile(
        category=AssetCategory.MEME,
        volatility=0.07,
        optimal_sl_pct=0.040,
        optimal_tp_levels=[0.040, 0.080, 0.140],
        tp_close_pcts=[0.60, 0.30, 0.10],
        optimal_trailing_pct=0.035,
        hold_in_trend=False,
        max_hold_hours=24
    ),
}


def get_default_profile() -> AssetProfile:
    """ملف تعريف افتراضي (متحفظ)"""
    return AssetProfile(
        category=AssetCategory.MID_CAP,
        volatility=0.04,
        optimal_sl_pct=0.025,
        optimal_tp_levels=[0.020, 0.035, 0.055],
        tp_close_pcts=[0.40, 0.35, 0.25],
        optimal_trailing_pct=0.018,
        hold_in_trend=False,
        max_hold_hours=48
    )


def get_asset_profile(symbol: str) -> AssetProfile:
    """الحصول على ملف تعريف العملة"""
    return ASSET_PROFILES.get(symbol, get_default_profile())


# ============================================================
# 3. النظام الموحد الرئيسي
# ============================================================

class UnifiedExitSystem:
    """
    🏆 نظام الخروج الموحد V4
    
    يدمج أفضل المزايا من جميع الأنظمة السابقة:
    1. تصنيف العملات الذكي
    2. SL/TP ديناميكي حسب نوع العملة
    3. Trailing Stop مع حماية الاتجاه
    4. Time-Based Exit
    5. Reversal Detection
    6. Emergency Protection
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.logger = logger
        self.config = config or self._default_config()
        self.positions: Dict[str, PositionState] = {}
        
        # إحصائيات
        self.stats = {
            'total_exits': 0,
            'exits_by_reason': {},
            'total_pnl': 0,
            'avg_hold_hours': 0
        }
    
    def _default_config(self) -> Dict:
        """الإعدادات الافتراضية المحسّنة V4"""
        return {
            # === Stop Loss ===
            'stop_loss': {
                'use_atr': True,
                'atr_multiplier': 2.0,
                'use_profile': True,  # استخدام ملف تعريف العملة
                'break_even_trigger': 0.012,  # نقل لـ BE عند +1.2%
                'min_sl_pct': 0.010,  # 1% حد أدنى
                'max_sl_pct': 0.050,  # 5% حد أقصى
            },
            
            # === Take Profit ===
            'take_profit': {
                'use_profile': True,  # استخدام ملف تعريف العملة
                'extend_in_strong_trend': True,
                'trend_extension_mult': 1.2,
            },
            
            # === Trailing Stop === (محسّن V5 - من النظام الأصلي)
            'trailing': {
                'activation_pct': 0.015,  # تفعيل عند +1.5%
                'use_profile': True,
                'default_distance_pct': 0.01,  # 1% كالنظام الأصلي
                'step_pct': 0.002,
                'trend_protection': True,  # البقاء مع الاتجاه
                'trend_expansion_mult': 1.5,  # توسيع 50% عند ارتداد طبيعي
                'min_profit_for_protection': 0.02,  # حماية فقط إذا ربح > 2%
                'max_drawdown_in_trend': 0.015,  # أقصى هبوط مسموح في الاتجاه 1.5%
                'min_profit_lock': 0.005,  # قفل 0.5% كحد أدنى
            },
            
            # === Time Exit === (محسّن V4.2)
            'time_exit': {
                'use_profile': True,
                'default_max_hours': 96,  # زيادة لإعطاء وقت أكثر
                'stagnant_hours': 36,  # زيادة من 24
                'stagnant_threshold': 0.005,  # زيادة الحد
                'profit_time_bonus': True,
            },
            
            # === Reversal Detection === (محسّن V5 - من النظام الأصلي)
            'reversal': {
                'enabled': True,
                'consecutive_red_candles': 4,  # 4 من 5 شموع هابطة
                'drop_threshold': 0.015,  # 1.5% = انعكاس حقيقي (أقل = تصحيح)
                'volume_spike': 2.0,
                'min_profit_to_check': 0.01,  # فقط إذا في ربح > 1%
                'ignore_small_corrections': True,  # تجاهل التصحيحات الصغيرة
            },
            
            # === Emergency Exit ===
            'emergency': {
                'enabled': True,
                'max_drawdown': 0.05,
                'flash_crash_pct': 0.03,
            }
        }
    
    # ============================================================
    # تسجيل صفقة جديدة
    # ============================================================
    
    def register_position(
        self,
        position_id: str,
        symbol: str,
        entry_price: float,
        quantity: float,
        atr: float = None,
        entry_time: datetime = None
    ) -> PositionState:
        """
        تسجيل صفقة جديدة مع إعدادات ذكية حسب نوع العملة
        """
        # الحصول على ملف تعريف العملة
        profile = get_asset_profile(symbol)
        
        # حساب SL
        if self.config['stop_loss']['use_profile']:
            sl_pct = profile.optimal_sl_pct
        elif atr and self.config['stop_loss']['use_atr']:
            sl_pct = (atr * self.config['stop_loss']['atr_multiplier']) / entry_price
        else:
            sl_pct = 0.025
        
        # تطبيق الحدود
        sl_pct = max(
            self.config['stop_loss']['min_sl_pct'],
            min(sl_pct, self.config['stop_loss']['max_sl_pct'])
        )
        initial_sl = entry_price * (1 - sl_pct)
        
        # حساب مستويات TP
        if self.config['take_profit']['use_profile']:
            tp_levels = self._create_tp_levels(entry_price, profile)
        else:
            tp_levels = self._create_default_tp_levels(entry_price)
        
        # إنشاء حالة الصفقة
        if isinstance(entry_time, pd.Timestamp):
            entry_time = entry_time.to_pydatetime()
        elif isinstance(entry_time, str):
            try:
                entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
            except Exception:
                entry_time = None

        entry_time = entry_time or datetime.now()
        now_dt = datetime.now(entry_time.tzinfo) if entry_time.tzinfo else datetime.now()
        state = PositionState(
            position_id=position_id,
            symbol=symbol,
            entry_price=entry_price,
            quantity=quantity,
            remaining_quantity=quantity,
            entry_time=entry_time,
            asset_profile=profile,
            initial_sl=initial_sl,
            current_sl=initial_sl,
            tp_levels=tp_levels,
            highest_price=entry_price,
            last_price=entry_price,
            last_update=now_dt,
            last_movement_time=entry_time
        )
        
        self.positions[position_id] = state
        
        # Log
        self.logger.info(f"📊 [{symbol}] صفقة جديدة - {profile.category.value}")
        self.logger.info(f"   Entry: ${entry_price:.4f}")
        self.logger.info(f"   SL: ${initial_sl:.4f} (-{sl_pct*100:.2f}%)")
        self.logger.info(f"   TP1: +{profile.optimal_tp_levels[0]*100:.1f}%")
        self.logger.info(f"   TP2: +{profile.optimal_tp_levels[1]*100:.1f}%")
        self.logger.info(f"   TP3: +{profile.optimal_tp_levels[2]*100:.1f}%")
        
        return state
    
    def _create_tp_levels(self, entry: float, profile: AssetProfile) -> List[Dict]:
        """إنشاء مستويات TP من ملف تعريف العملة"""
        levels = []
        names = ['TP1', 'TP2', 'TP3']
        
        for i, (tp_pct, close_pct) in enumerate(zip(
            profile.optimal_tp_levels, 
            profile.tp_close_pcts
        )):
            levels.append({
                'name': names[i],
                'pct': tp_pct,
                'price': entry * (1 + tp_pct),
                'close_pct': close_pct,
                'triggered': False
            })
        
        return levels
    
    def _create_default_tp_levels(self, entry: float) -> List[Dict]:
        """مستويات TP الافتراضية"""
        defaults = [
            {'name': 'TP1', 'pct': 0.018, 'close': 0.35},
            {'name': 'TP2', 'pct': 0.032, 'close': 0.35},
            {'name': 'TP3', 'pct': 0.050, 'close': 0.30},
        ]
        
        return [{
            'name': d['name'],
            'pct': d['pct'],
            'price': entry * (1 + d['pct']),
            'close_pct': d['close'],
            'triggered': False
        } for d in defaults]
    
    # ============================================================
    # فحص شروط الخروج
    # ============================================================
    
    def check_exit(
        self,
        position_id: str,
        current_price: float,
        timestamp: datetime = None,
        candle_data: Dict = None
    ) -> Optional[Dict]:
        """
        🎯 فحص شروط الخروج (الترتيب مهم!)
        
        ترتيب الفحص:
        1. Emergency Exit (فوري)
        2. Stop Loss
        3. Take Profit (متعدد المستويات)
        4. Trailing Stop
        5. Break Even Update
        6. Time Exit
        7. Reversal Detection
        """
        if position_id not in self.positions:
            return None
        
        state = self.positions[position_id]
        timestamp = timestamp or datetime.now()
        if isinstance(timestamp, pd.Timestamp):
            timestamp = timestamp.to_pydatetime()
        if state.entry_time.tzinfo and timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=state.entry_time.tzinfo)
        elif state.entry_time.tzinfo is None and timestamp.tzinfo is not None:
            timestamp = timestamp.replace(tzinfo=None)
        
        # تحديث الحالة
        state.last_price = current_price
        state.last_update = timestamp
        
        if current_price > state.highest_price:
            state.highest_price = current_price
            state.last_movement_time = timestamp
        
        entry = state.entry_price
        change_pct = (current_price - entry) / entry
        
        # ===== 1. Emergency Exit =====
        if self.config['emergency']['enabled']:
            emergency = self._check_emergency(state, current_price)
            if emergency:
                return emergency
        
        # ===== 2. Stop Loss =====
        sl_check = self._check_stop_loss(state, current_price)
        if sl_check:
            return sl_check
        
        # ===== 3. Take Profit =====
        tp_check = self._check_take_profit(state, current_price)
        if tp_check:
            return tp_check
        
        # ===== 4. Trailing Stop =====
        trailing_check = self._check_trailing_stop(state, current_price, candle_data)
        if trailing_check:
            return trailing_check
        
        # ===== 5. Break Even Update =====
        self._update_break_even(state, change_pct)
        
        # ===== 6. Time Exit =====
        time_check = self._check_time_exit(state, timestamp, change_pct)
        if time_check:
            return time_check
        
        # ===== 7. Reversal Detection =====
        if self.config['reversal']['enabled'] and candle_data:
            reversal_check = self._check_reversal(state, current_price, candle_data, change_pct)
            if reversal_check:
                return reversal_check
        
        return None
    
    # ============================================================
    # فحوصات الخروج الفردية
    # ============================================================
    
    def _check_emergency(self, state: PositionState, price: float) -> Optional[Dict]:
        """فحص الخروج الطارئ"""
        change = (price - state.entry_price) / state.entry_price
        
        if change <= -self.config['emergency']['max_drawdown']:
            return self._create_exit(
                state, price, ExitReason.EMERGENCY, 1.0,
                f"🚨 Emergency exit: {change*100:.2f}% loss"
            )
        
        return None
    
    def _check_stop_loss(self, state: PositionState, price: float) -> Optional[Dict]:
        """فحص Stop Loss"""
        if price <= state.current_sl:
            loss_pct = ((price - state.entry_price) / state.entry_price) * 100
            return self._create_exit(
                state, price, ExitReason.STOP_LOSS, 1.0,
                f"🛑 SL hit at ${state.current_sl:.4f} ({loss_pct:.2f}%)"
            )
        return None
    
    def _check_take_profit(self, state: PositionState, price: float) -> Optional[Dict]:
        """فحص Multi-Level TP"""
        for i, level in enumerate(state.tp_levels):
            if not level['triggered'] and price >= level['price']:
                level['triggered'] = True
                state.tp_hit_count += 1
                
                profit_pct = ((price - state.entry_price) / state.entry_price) * 100
                reason = ExitReason(f"tp{i+1}")
                
                return self._create_exit(
                    state, price, reason, level['close_pct'],
                    f"🎯 {level['name']} hit (+{profit_pct:.2f}%)"
                )
        
        return None
    
    def _check_trailing_stop(
        self, 
        state: PositionState, 
        price: float,
        candle_data: Dict = None
    ) -> Optional[Dict]:
        """فحص وتحديث Trailing Stop مع حماية الاتجاه"""
        entry = state.entry_price
        profit_pct = (price - entry) / entry
        
        # تحديد مسافة Trailing
        if self.config['trailing']['use_profile'] and state.asset_profile:
            trail_distance_pct = state.asset_profile.optimal_trailing_pct
        else:
            trail_distance_pct = self.config['trailing']['default_distance_pct']
        
        # تفعيل Trailing
        if not state.trailing_active:
            if profit_pct >= self.config['trailing']['activation_pct']:
                state.trailing_active = True
                state.trailing_stop = price * (1 - trail_distance_pct)
                self.logger.info(f"🎯 [{state.symbol}] Trailing مُفعّل عند +{profit_pct*100:.2f}%")
        
        # تحديث Trailing
        if state.trailing_active:
            if price > state.highest_price:
                new_trail = price * (1 - trail_distance_pct)
                min_profit = entry * (1 + self.config['trailing']['min_profit_lock'])
                state.trailing_stop = max(new_trail, min_profit)
            
            # فحص: هل ضرب Trailing?
            if price <= state.trailing_stop:
                # === حماية الاتجاه (V5 - من النظام الأصلي) ===
                if self.config['trailing']['trend_protection'] and candle_data:
                    drawdown = (state.highest_price - price) / state.highest_price
                    min_profit_for_protection = self.config['trailing'].get('min_profit_for_protection', 0.02)
                    max_drawdown_in_trend = self.config['trailing'].get('max_drawdown_in_trend', 0.015)
                    
                    # إذا الاتجاه صاعد + ربح جيد + هبوط صغير = نبقى
                    if self._is_trend_still_bullish(candle_data, state.asset_profile):
                        if profit_pct > min_profit_for_protection and drawdown < max_drawdown_in_trend:
                            # توسيع Trailing 50%
                            expansion = self.config['trailing'].get('trend_expansion_mult', 1.5)
                            state.trailing_stop = state.highest_price * (1 - trail_distance_pct * expansion)
                            return None  # نبقى في الصفقة
                
                # الخروج مع حد أدنى للربح
                actual_pnl = (price - entry) / entry
                min_lock = self.config['trailing'].get('min_profit_lock', 0.005)
                final_pnl = max(actual_pnl, min_lock) if actual_pnl > 0 else actual_pnl
                
                return self._create_exit(
                    state, price, ExitReason.TRAILING_STOP, 1.0,
                    f"📉 Trailing hit (+{final_pnl*100:.2f}%)"
                )
        
        return None
    
    def _update_break_even(self, state: PositionState, change_pct: float):
        """تحديث Break Even"""
        if not state.sl_moved_to_be:
            if change_pct >= self.config['stop_loss']['break_even_trigger']:
                # نقل SL لنقطة الدخول + هامش صغير
                state.current_sl = state.entry_price * 1.001
                state.sl_moved_to_be = True
                self.logger.info(f"✅ [{state.symbol}] SL نُقل لـ Break Even")
    
    def _check_time_exit(
        self, 
        state: PositionState, 
        timestamp: datetime,
        change_pct: float
    ) -> Optional[Dict]:
        """فحص Time-Based Exit"""
        # تحديد الحد الأقصى للوقت
        if self.config['time_exit']['use_profile'] and state.asset_profile:
            max_hours = state.asset_profile.max_hold_hours
        else:
            max_hours = self.config['time_exit']['default_max_hours']
        
        # بونس وقت للأرباح
        if self.config['time_exit']['profit_time_bonus'] and change_pct > 0.01:
            max_hours = int(max_hours * 1.5)
        
        hold_time = timestamp - state.entry_time
        hold_hours = hold_time.total_seconds() / 3600
        
        # تجاوز الحد الأقصى
        if hold_hours >= max_hours:
            return self._create_exit(
                state, state.last_price, ExitReason.TIME_EXIT, 1.0,
                f"⏰ Time exit: {hold_hours:.1f}h > {max_hours}h limit"
            )
        
        # فحص الركود
        if state.last_movement_time:
            stagnant_time = timestamp - state.last_movement_time
            stagnant_hours = stagnant_time.total_seconds() / 3600
            
            if stagnant_hours >= self.config['time_exit']['stagnant_hours']:
                # تحقق من الحركة
                if abs(change_pct) < self.config['time_exit']['stagnant_threshold']:
                    return self._create_exit(
                        state, state.last_price, ExitReason.STAGNANT, 1.0,
                        f"💤 Stagnant: {stagnant_hours:.1f}h without movement"
                    )
        
        return None
    
    def _check_reversal(
        self, 
        state: PositionState, 
        price: float,
        candle_data: Dict,
        change_pct: float
    ) -> Optional[Dict]:
        """كشف الانعكاس (V5 - من النظام الأصلي)"""
        # لا نفحص إلا إذا في ربح
        if change_pct < self.config['reversal']['min_profit_to_check']:
            return None
        
        drop = (state.highest_price - price) / state.highest_price
        drop_threshold = self.config['reversal']['drop_threshold']
        
        # === فحص إضافي: هل فعلاً انعكاس أم مجرد تصحيح؟ ===
        ignore_small = self.config['reversal'].get('ignore_small_corrections', True)
        if ignore_small and drop < drop_threshold:
            # هبوط < 1.5% = تصحيح فقط، نبقى
            return None
        
        # فحص الشموع الحمراء المتتالية
        consecutive_red = candle_data.get('consecutive_red', 0)
        if consecutive_red >= self.config['reversal']['consecutive_red_candles']:
            # تأكد من الهبوط الكبير
            if drop >= drop_threshold:
                # === الخروج فقط إذا في ربح ===
                actual_pnl = change_pct
                if actual_pnl > 0:
                    return self._create_exit(
                        state, price, ExitReason.REVERSAL, 1.0,
                        f"🔄 Reversal: {consecutive_red} red candles, -{drop*100:.2f}% drop (+{actual_pnl*100:.2f}%)"
                    )
        
        # فحص ارتفاع الحجم المفاجئ - فقط مع هبوط كبير
        if candle_data.get('volume_ratio', 1) >= self.config['reversal']['volume_spike']:
            if candle_data.get('is_bearish', False) and drop >= drop_threshold:
                actual_pnl = change_pct
                if actual_pnl > 0:
                    return self._create_exit(
                        state, price, ExitReason.REVERSAL, 1.0,
                        f"📊 Volume spike reversal: {candle_data['volume_ratio']:.1f}x (+{actual_pnl*100:.2f}%)"
                    )
        
        return None
    
    # ============================================================
    # دوال مساعدة
    # ============================================================
    
    def _is_trend_still_bullish(self, candle_data: Dict, profile: AssetProfile = None) -> bool:
        """
        هل الاتجاه لا يزال صاعد؟ (V5 - من النظام الأصلي)
        
        المعايير:
        1. السعر فوق المتوسط (أو قريب منه 1%)
        2. آخر شموع أغلبها صاعدة أو مستقرة
        3. لا يوجد هبوط حاد (> 2.5%)
        """
        # لا حماية للـ Meme coins
        if profile and profile.category == AssetCategory.MEME:
            return False
        
        # لا حماية إذا لم نكن نريد البقاء مع الاتجاه
        if profile and not profile.hold_in_trend:
            return False
        
        # فحص المؤشرات الأساسية
        bullish_signals = 0
        total_checks = 0
        
        # 1. EMA alignment
        ema_short = candle_data.get('ema_short', candle_data.get('ema_8', 0))
        ema_long = candle_data.get('ema_long', candle_data.get('ema_21', 0))
        if ema_short > 0 and ema_long > 0:
            total_checks += 1
            if ema_short > ema_long * 0.99:  # مسموح 1% تحت
                bullish_signals += 1
        
        # 2. RSI صحي
        rsi = candle_data.get('rsi', 50)
        total_checks += 1
        if rsi > 40:  # RSI فوق 40 = ليس ضعيف
            bullish_signals += 1
        
        # 3. MACD
        macd = candle_data.get('macd', 0)
        macd_signal = candle_data.get('macd_signal', 0)
        if macd != 0:
            total_checks += 1
            if macd > macd_signal * 0.95:  # MACD قريب من أو فوق Signal
                bullish_signals += 1
        
        # 4. الشمعة الحالية ليست هبوطية قوية
        total_checks += 1
        if not candle_data.get('is_bearish', False) or candle_data.get('body_pct', 0) < 0.02:
            bullish_signals += 1
        
        # الحكم: على الأقل نصف الإشارات صاعدة
        return bullish_signals >= (total_checks / 2)
    
    def _create_exit(
        self,
        state: PositionState,
        price: float,
        reason: ExitReason,
        close_pct: float,
        message: str
    ) -> Dict:
        """إنشاء قرار الخروج"""
        pnl = (price - state.entry_price) / state.entry_price * 100
        
        self.logger.info(f"🔔 [{state.symbol}] EXIT: {message}")
        
        # تحديث الإحصائيات
        self.stats['total_exits'] += 1
        self.stats['exits_by_reason'][reason.value] = \
            self.stats['exits_by_reason'].get(reason.value, 0) + 1
        
        return {
            'should_exit': True,
            'reason': reason.value,
            'message': message,
            'close_quantity_pct': close_pct,
            'exit_price': price,
            'pnl_pct': pnl,
            'position_id': state.position_id,
            'symbol': state.symbol
        }
    
    def remove_position(self, position_id: str):
        """إزالة صفقة من التتبع"""
        if position_id in self.positions:
            del self.positions[position_id]
    
    def get_position_state(self, position_id: str) -> Optional[PositionState]:
        """الحصول على حالة صفقة"""
        return self.positions.get(position_id)
    
    def get_stats(self) -> Dict:
        """الحصول على الإحصائيات"""
        return self.stats.copy()


# ============================================================
# Singleton Pattern
# ============================================================

_unified_exit_system = None

def get_unified_exit_system(config: Dict = None) -> UnifiedExitSystem:
    """الحصول على نسخة وحيدة من النظام"""
    global _unified_exit_system
    if _unified_exit_system is None:
        _unified_exit_system = UnifiedExitSystem(config)
    return _unified_exit_system
