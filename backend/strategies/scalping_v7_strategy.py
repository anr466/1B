#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scalping V7 Strategy — Adapter لربط ScalpingV7Engine بـ BaseStrategy
====================================================================

هذا الملف يلف ScalpingV7Engine بواجهة BaseStrategy الموحدة.
المحرك الداخلي (scalping_v7_engine.py) لا يُعدَّل — هذا adapter فقط.

Usage:
    from backend.strategies.scalping_v7_strategy import ScalpingV7Strategy
    strategy = ScalpingV7Strategy()
    
    df = strategy.prepare_data(raw_df)
    entry = strategy.detect_entry(df, context={'trend': 'UP'})
    exit_sig = strategy.check_exit(df, position)
"""

import logging
import pandas as pd
from datetime import datetime
from typing import Dict, Optional

from backend.strategies.base_strategy import BaseStrategy
from backend.strategies.scalping_v7_engine import ScalpingV7Engine, V7_CONFIG


class ScalpingV7Strategy(BaseStrategy):
    """
    Adapter: يربط ScalpingV7Engine بواجهة BaseStrategy الموحدة.
    
    لا يغيّر أي منطق داخلي — يترجم فقط بين الواجهة الموحدة و V7 API.
    """

    name = "scalping_v7"
    version = "7.0"
    description = "Scalping V7 — trailing-only exit, PF=1.35, WR=51.3%"

    def __init__(self, config: Dict = None):
        super().__init__()
        self._engine = ScalpingV7Engine(config)
        self._config = self._engine.config

    # ===== 1. تحضير البيانات =====
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """إضافة مؤشرات V7 للبيانات"""
        return self._engine.prepare_data(df)

    # ===== 2. كشف إشارة الدخول =====
    def detect_entry(self, df: pd.DataFrame, context: Dict) -> Optional[Dict]:
        """
        كشف إشارة دخول V7.
        
        Args:
            df: DataFrame مع المؤشرات
            context: {'trend': 'UP'/'DOWN'/'NEUTRAL'}
        
        Returns:
            إشارة دخول أو None
        """
        trend = context.get('trend', 'NEUTRAL')
        signal = self._engine.detect_entry(df, trend)
        
        if signal is None:
            return None
        
        # توحيد شكل الإشارة مع BaseStrategy
        return {
            'signal': signal.get('side', 'LONG'),
            'side': signal.get('side', 'LONG'),
            'strategy': signal.get('strategy', self.name),
            'entry_price': signal.get('entry_price', 0),
            'stop_loss': signal.get('stop_loss', 0),
            'take_profit': 0,  # trailing-only — لا TP ثابت
            'score': signal.get('score', 0),
            'confidence': signal.get('confidence', 50),
            'reasons': signal.get('signals', []),
            'metadata': {
                'timing_count': signal.get('timing_count', 0),
                'signal_type': signal.get('signal_type', ''),
            },
            # حفظ الإشارة الأصلية للتوافق
            '_raw_signal': signal,
        }

    # ===== 3. فحص شروط الخروج =====
    def check_exit(self, df: pd.DataFrame, position: Dict) -> Dict:
        """
        فحص شروط خروج V7.
        
        Args:
            df: DataFrame مع المؤشرات
            position: بيانات الصفقة من DB
        
        Returns:
            نتيجة الفحص الموحدة
        """
        # بناء pos_data بالشكل الذي يتوقعه V7
        entry_price = position.get('entry_price', 0)
        position_type = position.get('position_type', 'long').upper()
        peak = position.get('highest_price', entry_price)
        trail = position.get('trailing_sl_price', 0) or 0
        sl = position.get('stop_loss', 0)
        
        # حساب ساعات الاحتفاز
        entry_time = position.get('created_at')
        hold_hours = 0
        if entry_time:
            if isinstance(entry_time, str):
                try:
                    entry_time = datetime.fromisoformat(entry_time.replace('Z', '+00:00')).replace(tzinfo=None)
                except Exception:
                    entry_time = datetime.now()
            hold_hours = (datetime.now() - entry_time).total_seconds() / 3600
        
        # تصحيح peak
        if position_type == 'SHORT':
            if peak == 0 or peak >= entry_price:
                peak = entry_price
        else:
            if peak == 0 or peak <= entry_price:
                peak = entry_price
        
        # SL الافتراضي إذا لم يكن محدداً
        if not sl or sl <= 0:
            if position_type == 'SHORT':
                sl = entry_price * (1 + self._config['sl_pct'])
            else:
                sl = entry_price * (1 - self._config['sl_pct'])
        
        pos_data = {
            'entry_price': entry_price,
            'side': position_type,
            'peak': peak,
            'trail': trail,
            'sl': sl,
            'entry_time': entry_time,
            'hold_hours': hold_hours,
        }
        
        result = self._engine.check_exit_signal(df, pos_data)
        
        # توحيد النتيجة
        return {
            'should_exit': result.get('should_exit', False),
            'reason': result.get('reason', 'HOLD'),
            'exit_price': result.get('exit_price', 0),
            'updated': result.get('updated', {}),
            'pnl_pct': result.get('pnl_pct', 0),
            'trail_level': result.get('trail_level', 0),
            'peak': result.get('peak', peak),
        }

    # ===== 4. إعدادات الاستراتيجية =====
    def get_config(self) -> Dict:
        """إرجاع إعدادات V7"""
        return {
            'name': self.name,
            'version': self.version,
            'timeframe': '1h',
            'sl_pct': self._config['sl_pct'],
            'trailing_activation': self._config['trailing_activation'],
            'trailing_distance': self._config['trailing_distance'],
            'max_positions': self._config['max_positions'],
            'max_hold_hours': 12,
            'stagnant_hours': 6,
            'min_confluence': self._config['min_confluence'],
            'min_timing': self._config.get('min_timing', 1),
        }

    # ===== 5. اتجاه السوق (V7 يستخدم 4H trend من 1H data) =====
    def get_market_trend(self, df: pd.DataFrame) -> str:
        """تحديد اتجاه 4H من بيانات 1H"""
        return self._engine.get_4h_trend(df)

    # ===== 6. استخراج مؤشرات الدخول =====
    def extract_entry_indicators(self, df: pd.DataFrame) -> Dict:
        """استخراج المؤشرات الفنية عند الدخول"""
        try:
            last_row = df.iloc[-2]  # آخر شمعة مكتملة
            return {
                'rsi': float(last_row.get('rsi', 50)) if not pd.isna(last_row.get('rsi')) else None,
                'macd': float(last_row.get('macd_l', 0)) if not pd.isna(last_row.get('macd_l')) else None,
                'bb_position': float(
                    (last_row['close'] - last_row.get('bbl', last_row['close'])) /
                    max(last_row.get('bbu', last_row['close']) - last_row.get('bbl', last_row['close']), 0.001)
                ) if not pd.isna(last_row.get('bbl')) else None,
                'volume_ratio': float(last_row.get('vol_r', 1.0)) if not pd.isna(last_row.get('vol_r')) else None,
                'ema_trend': 'up' if (
                    not pd.isna(last_row.get('ema8')) and
                    not pd.isna(last_row.get('ema21')) and
                    last_row['ema8'] > last_row['ema21']
                ) else 'down',
                'atr_pct': float(last_row.get('atr', 0) / last_row['close'] * 100) if not pd.isna(last_row.get('atr')) else None,
            }
        except Exception:
            return {}


# ============================================================
# SINGLETON
# ============================================================
_v7_strategy_instance = None


def get_scalping_v7_strategy(config: Dict = None) -> ScalpingV7Strategy:
    """Get singleton ScalpingV7Strategy instance"""
    global _v7_strategy_instance
    if _v7_strategy_instance is None:
        _v7_strategy_instance = ScalpingV7Strategy(config)
    return _v7_strategy_instance
