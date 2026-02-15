#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Strategy Interface — العقد الموحد لجميع الاستراتيجيات
==========================================================

كل استراتيجية تداول يجب أن ترث من BaseStrategy وتطبق هذه الدوال.
النظام الأساسي (GroupBSystem) لا يعرف أي استراتيجية يشغّل —
يستدعي فقط الدوال المعرّفة هنا.

القانون:
    - تغيير استراتيجية = تغيير ملف الاستراتيجية فقط
    - إضافة استراتيجية = إضافة ملف جديد يرث BaseStrategy
    - النظام الأساسي لا يُعدَّل أبداً عند تغيير/إضافة استراتيجية

Usage:
    from backend.strategies.base_strategy import BaseStrategy

    class MyNewStrategy(BaseStrategy):
        name = "my_strategy_v1"
        ...
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd
import logging


class BaseStrategy(ABC):
    """
    واجهة موحدة لجميع استراتيجيات التداول.
    
    كل استراتيجية يجب أن تطبق:
    1. prepare_data() — إضافة المؤشرات للبيانات
    2. detect_entry() — كشف إشارات الدخول
    3. check_exit()  — فحص شروط الخروج
    4. get_config()  — إرجاع إعدادات الاستراتيجية
    """

    # ===== معرّف الاستراتيجية (يجب تعريفه في كل استراتيجية) =====
    name: str = "base"
    version: str = "0.0"
    description: str = ""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ===== 1. تحضير البيانات =====
    @abstractmethod
    def prepare_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        إضافة المؤشرات الفنية المطلوبة للبيانات الخام.
        
        Args:
            df: DataFrame بأعمدة OHLCV (open, high, low, close, volume)
        
        Returns:
            DataFrame مع المؤشرات المضافة
        """
        pass

    # ===== 2. كشف إشارة الدخول =====
    @abstractmethod
    def detect_entry(self, df: pd.DataFrame, context: Dict) -> Optional[Dict]:
        """
        كشف إشارة دخول جديدة.
        
        Args:
            df: DataFrame مع المؤشرات (من prepare_data)
            context: سياق إضافي (مثلاً: الاتجاه العام، حالة السوق)
        
        Returns:
            None إذا لا يوجد إشارة، أو dict بالمحتوى التالي:
            {
                'signal': 'LONG' أو 'SHORT',
                'side': 'LONG' أو 'SHORT',
                'strategy': اسم الاستراتيجية,
                'entry_price': سعر الدخول المقترح,
                'stop_loss': سعر وقف الخسارة,
                'take_profit': سعر جني الأرباح (0 = trailing only),
                'score': درجة الثقة (0-100),
                'reasons': [قائمة أسباب الدخول],
                'metadata': {} أي بيانات إضافية للاستراتيجية
            }
        """
        pass

    # ===== 3. فحص شروط الخروج =====
    @abstractmethod
    def check_exit(self, df: pd.DataFrame, position: Dict) -> Dict:
        """
        فحص ما إذا يجب إغلاق صفقة مفتوحة.
        
        Args:
            df: DataFrame مع المؤشرات (من prepare_data)
            position: بيانات الصفقة المفتوحة:
                {
                    'entry_price': سعر الدخول,
                    'side': 'LONG' أو 'SHORT',
                    'stop_loss': وقف الخسارة,
                    'highest_price': أعلى سعر وصلت إليه,
                    'trailing_sl_price': مستوى الـ trailing,
                    'created_at': وقت الفتح,
                    'position_type': 'long' أو 'short',
                }
        
        Returns:
            {
                'should_exit': bool,
                'reason': سبب الخروج (string),
                'exit_price': سعر الخروج,
                'updated': {  # تحديثات للصفقة (اختياري)
                    'peak': أعلى قيمة جديدة,
                    'trail': trailing جديد,
                },
                'pnl_pct': نسبة الربح/الخسارة,
                'trail_level': مستوى trailing الحالي,
                'peak': أعلى نقطة,
            }
        """
        pass

    # ===== 4. إعدادات الاستراتيجية =====
    @abstractmethod
    def get_config(self) -> Dict:
        """
        إرجاع إعدادات الاستراتيجية.
        
        Returns:
            {
                'name': اسم الاستراتيجية,
                'version': الإصدار,
                'timeframe': الإطار الزمني الرئيسي (مثلاً '1h'),
                'sl_pct': نسبة وقف الخسارة,
                'max_positions': أقصى عدد صفقات,
                'max_hold_hours': أقصى مدة احتفاظ,
                ... أي إعدادات خاصة بالاستراتيجية
            }
        """
        pass

    # ===== 5. تحديد اتجاه السوق (اختياري — override if needed) =====
    def get_market_trend(self, df: pd.DataFrame) -> str:
        """
        تحديد اتجاه السوق العام.
        القيمة الافتراضية: NEUTRAL
        
        Returns:
            'UP', 'DOWN', أو 'NEUTRAL'
        """
        return 'NEUTRAL'

    # ===== 6. استخراج مؤشرات الدخول للتعلم (اختياري) =====
    def extract_entry_indicators(self, df: pd.DataFrame) -> Dict:
        """
        استخراج المؤشرات الفنية عند الدخول (للتعلم التكيّفي).
        القيمة الافتراضية: dict فارغ
        """
        return {}

    # ===== معلومات الاستراتيجية =====
    def __repr__(self):
        return f"<{self.__class__.__name__} v{self.version}>"

    def get_info(self) -> Dict:
        """معلومات عامة عن الاستراتيجية"""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'config': self.get_config(),
        }
