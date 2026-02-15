#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام فلترة ذكي للعملات - يكشف العملات الخاسرة قبل الدخول
يستخدم تحليل متعدد المستويات لتجنب العملات الضعيفة
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class IntelligentCoinFilter:
    """
    نظام فلترة ذكي متعدد المستويات
    
    يفحص:
    1. الأداء التاريخي (هل العملة رابحة أم خاسرة؟)
    2. جودة الاتجاه (هل الاتجاه صحي؟)
    3. استقرار السعر (هل هناك تلاعب؟)
    4. السيولة (هل الحجم كافٍ؟)
    5. Risk/Reward التاريخي (هل نسبة الربح/الخسارة جيدة؟)
    """
    
    def __init__(self):
        self.logger = logger
        
        # معايير الفلترة (معدّلة بناءً على البيانات الفعلية)
        self.criteria = {
            # الأداء التاريخي
            'min_profitable_periods': 0.40,  # 40% (معدّل من 45%)
            'min_avg_return': -0.001,  # نقبل حتى الثابت (معدّل من 0.5%)
            'max_drawdown': 0.40,  # 40% (معدّل من 35%)
            
            # جودة الاتجاه
            'min_trend_consistency': 0.30,  # 30% (معدّل من 40%)
            'min_higher_highs': 2,  # 2 قمم (معدّل من 3)
            
            # السيولة
            'min_volume_usd': 500_000,  # 500K$ (معدّل من 2M$)
            'min_volume_consistency': 0.30,  # 30% (معدّل من 40%)
            
            # التقلب
            'min_volatility': 0.003,  # 0.3% (معدّل من 1.5%) - أكثر واقعية
            'max_volatility': 0.15,  # 15% (معدّل من 12%)
            
            # Risk/Reward
            'min_win_rate_historical': 0.48,  # 48% (معدّل من 50%)
            'min_profit_factor': 0.95,  # 0.95 (معدّل من 1.2) - أكثر واقعية
            
            # الاستقرار
            'max_manipulation_score': 0.20,  # 20% (معدّل من 15%)
            'min_data_quality': 0.85  # 85% (معدّل من 90%)
        }
        
        # Blacklist: عملات خاسرة من الاختبارات (محدّث)
        self.blacklist = [
            'ADA/USDT',   # -$15.69 من الاختبار الأول
            'UNI/USDT',   # -$9.89 من الاختبار الأول
            'DOT/USDT',   # -$8.86 من الاختبار الأول
            'BNB/USDT',   # -$8.15 من الاختبار المحسّن (Win Rate 40%)
            'ETH/USDT',   # -$1.91 من الاختبار المحسّن (Win Rate 33%)
            'MATIC/USDT'  # احتياطي
        ]
    
    def filter_coin(self, symbol: str, df: pd.DataFrame) -> Tuple[bool, Dict, str]:
        """
        فلترة عملة واحدة
        
        Args:
            symbol: رمز العملة
            df: بيانات السعر
            
        Returns:
            (passed: bool, scores: Dict, reason: str)
        """
        # فحص Blacklist أولاً
        if symbol in self.blacklist:
            return False, {}, f"⛔ في القائمة السوداء (خاسرة سابقاً)"
        
        if df is None or len(df) < 90:
            return False, {}, "بيانات غير كافية"
        
        scores = {}
        reasons = []
        
        try:
            # 1. تحليل الأداء التاريخي
            perf_score, perf_passed, perf_reason = self._analyze_performance(df)
            scores['performance'] = perf_score
            if not perf_passed:
                reasons.append(perf_reason)
            
            # 2. تحليل جودة الاتجاه
            trend_score, trend_passed, trend_reason = self._analyze_trend_quality(df)
            scores['trend'] = trend_score
            if not trend_passed:
                reasons.append(trend_reason)
            
            # 3. تحليل السيولة
            liquidity_score, liquidity_passed, liquidity_reason = self._analyze_liquidity(df)
            scores['liquidity'] = liquidity_score
            if not liquidity_passed:
                reasons.append(liquidity_reason)
            
            # 4. تحليل التقلب
            volatility_score, volatility_passed, volatility_reason = self._analyze_volatility(df)
            scores['volatility'] = volatility_score
            if not volatility_passed:
                reasons.append(volatility_reason)
            
            # 5. تحليل الاستقرار
            stability_score, stability_passed, stability_reason = self._analyze_stability(df)
            scores['stability'] = stability_score
            if not stability_passed:
                reasons.append(stability_reason)
            
            # 6. تحليل Risk/Reward التاريخي
            rr_score, rr_passed, rr_reason = self._analyze_risk_reward(df)
            scores['risk_reward'] = rr_score
            if not rr_passed:
                reasons.append(rr_reason)
            
            # حساب النقاط الإجمالية
            total_score = sum(scores.values()) / len(scores) * 100
            scores['total'] = total_score
            
            # القرار: يجب اجتياز جميع المعايير
            passed = (perf_passed and trend_passed and liquidity_passed and 
                     volatility_passed and stability_passed and rr_passed)
            
            if passed:
                return True, scores, "✅ اجتاز جميع المعايير"
            else:
                return False, scores, " | ".join(reasons)
            
        except Exception as e:
            self.logger.error(f"خطأ في فلترة {symbol}: {e}")
            return False, {}, f"خطأ: {str(e)}"
    
    def _analyze_performance(self, df: pd.DataFrame) -> Tuple[float, bool, str]:
        """تحليل الأداء التاريخي"""
        # حساب العوائد اليومية
        daily_returns = df['close'].pct_change().dropna()
        
        # 1. نسبة الفترات الإيجابية
        positive_periods = (daily_returns > 0).sum() / len(daily_returns)
        
        # 2. متوسط العائد
        avg_return = daily_returns.mean()
        
        # 3. Max Drawdown
        cumulative = (1 + daily_returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = abs(drawdown.min())
        
        # الدرجة (0-1)
        score = 0
        score += (positive_periods / self.criteria['min_profitable_periods']) * 0.4
        score += (avg_return / self.criteria['min_avg_return']) * 0.3
        score += (1 - max_drawdown / self.criteria['max_drawdown']) * 0.3
        score = min(1.0, max(0, score))
        
        # الاجتياز
        passed = (positive_periods >= self.criteria['min_profitable_periods'] and
                 avg_return >= self.criteria['min_avg_return'] and
                 max_drawdown <= self.criteria['max_drawdown'])
        
        reason = ""
        if not passed:
            if positive_periods < self.criteria['min_profitable_periods']:
                reason = f"أيام إيجابية قليلة ({positive_periods:.1%})"
            elif avg_return < self.criteria['min_avg_return']:
                reason = f"عائد ضعيف ({avg_return:.2%})"
            else:
                reason = f"هبوط كبير ({max_drawdown:.1%})"
        
        return score, passed, reason
    
    def _analyze_trend_quality(self, df: pd.DataFrame) -> Tuple[float, bool, str]:
        """تحليل جودة الاتجاه"""
        # حساب SMAs
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        
        # 1. اتساق الاتجاه (نسبة الأيام SMA20 > SMA50)
        valid_data = df[['sma_20', 'sma_50']].dropna()
        if len(valid_data) == 0:
            return 0, False, "بيانات غير كافية للاتجاه"
        
        trend_consistency = (valid_data['sma_20'] > valid_data['sma_50']).sum() / len(valid_data)
        
        # 2. عدد القمم الصاعدة (Higher Highs)
        highs = df['high'].rolling(5).max()
        higher_highs = (highs.diff() > 0).sum()
        
        # الدرجة
        score = 0
        score += (trend_consistency / self.criteria['min_trend_consistency']) * 0.6
        score += (min(higher_highs, 10) / 10) * 0.4
        score = min(1.0, max(0, score))
        
        # الاجتياز
        passed = (trend_consistency >= self.criteria['min_trend_consistency'] and
                 higher_highs >= self.criteria['min_higher_highs'])
        
        reason = ""
        if not passed:
            if trend_consistency < self.criteria['min_trend_consistency']:
                reason = f"اتجاه ضعيف ({trend_consistency:.1%})"
            else:
                reason = f"قمم صاعدة قليلة ({higher_highs})"
        
        return score, passed, reason
    
    def _analyze_liquidity(self, df: pd.DataFrame) -> Tuple[float, bool, str]:
        """تحليل السيولة"""
        if 'volume' not in df.columns:
            return 0, False, "لا توجد بيانات حجم"
        
        # حجم التداول بالدولار (تقريبي)
        avg_volume_usd = (df['volume'] * df['close']).mean()
        
        # اتساق الحجم
        days_above_threshold = (df['volume'] * df['close'] > self.criteria['min_volume_usd']).sum()
        volume_consistency = days_above_threshold / len(df)
        
        # الدرجة
        score = 0
        score += (avg_volume_usd / self.criteria['min_volume_usd']) * 0.6
        score += (volume_consistency / self.criteria['min_volume_consistency']) * 0.4
        score = min(1.0, max(0, score))
        
        # الاجتياز
        passed = (avg_volume_usd >= self.criteria['min_volume_usd'] and
                 volume_consistency >= self.criteria['min_volume_consistency'])
        
        reason = ""
        if not passed:
            if avg_volume_usd < self.criteria['min_volume_usd']:
                reason = f"حجم منخفض (${avg_volume_usd/1e6:.1f}M)"
            else:
                reason = f"حجم غير متسق ({volume_consistency:.1%})"
        
        return score, passed, reason
    
    def _analyze_volatility(self, df: pd.DataFrame) -> Tuple[float, bool, str]:
        """تحليل التقلب"""
        daily_returns = df['close'].pct_change().dropna()
        volatility = daily_returns.std()
        
        # الدرجة (التقلب المثالي بين 2-5%)
        if 0.02 <= volatility <= 0.05:
            score = 1.0
        elif 0.015 <= volatility <= 0.08:
            score = 0.7
        elif self.criteria['min_volatility'] <= volatility <= self.criteria['max_volatility']:
            score = 0.5
        else:
            score = 0.2
        
        # الاجتياز
        passed = (self.criteria['min_volatility'] <= volatility <= 
                 self.criteria['max_volatility'])
        
        reason = ""
        if not passed:
            if volatility < self.criteria['min_volatility']:
                reason = f"تقلب منخفض جداً ({volatility:.2%})"
            else:
                reason = f"تقلب عالي جداً ({volatility:.2%})"
        
        return score, passed, reason
    
    def _analyze_stability(self, df: pd.DataFrame) -> Tuple[float, bool, str]:
        """تحليل الاستقرار (كشف التلاعب)"""
        daily_returns = df['close'].pct_change().dropna()
        
        # 1. تحركات شاذة (> 20% يومياً)
        extreme_moves = (abs(daily_returns) > 0.20).sum()
        manipulation_score = extreme_moves / len(daily_returns)
        
        # 2. جودة البيانات (عدم وجود قيم شاذة)
        missing_data = df[['open', 'high', 'low', 'close']].isna().sum().sum()
        data_quality = 1 - (missing_data / (len(df) * 4))
        
        # الدرجة
        score = 0
        score += (1 - manipulation_score / self.criteria['max_manipulation_score']) * 0.5
        score += data_quality * 0.5
        score = min(1.0, max(0, score))
        
        # الاجتياز
        passed = (manipulation_score <= self.criteria['max_manipulation_score'] and
                 data_quality >= self.criteria['min_data_quality'])
        
        reason = ""
        if not passed:
            if manipulation_score > self.criteria['max_manipulation_score']:
                reason = f"تحركات شاذة ({manipulation_score:.1%})"
            else:
                reason = f"بيانات ناقصة ({data_quality:.1%})"
        
        return score, passed, reason
    
    def _analyze_risk_reward(self, df: pd.DataFrame) -> Tuple[float, bool, str]:
        """تحليل Risk/Reward التاريخي"""
        daily_returns = df['close'].pct_change().dropna()
        
        # 1. Win Rate التاريخي
        wins = (daily_returns > 0).sum()
        win_rate = wins / len(daily_returns)
        
        # 2. Profit Factor (متوسط الربح / متوسط الخسارة)
        avg_win = daily_returns[daily_returns > 0].mean()
        avg_loss = abs(daily_returns[daily_returns < 0].mean())
        
        if avg_loss == 0 or pd.isna(avg_loss):
            profit_factor = 2.0
        else:
            profit_factor = avg_win / avg_loss
        
        # الدرجة
        score = 0
        score += (win_rate / self.criteria['min_win_rate_historical']) * 0.5
        score += (profit_factor / self.criteria['min_profit_factor']) * 0.5
        score = min(1.0, max(0, score))
        
        # الاجتياز
        passed = (win_rate >= self.criteria['min_win_rate_historical'] and
                 profit_factor >= self.criteria['min_profit_factor'])
        
        reason = ""
        if not passed:
            if win_rate < self.criteria['min_win_rate_historical']:
                reason = f"Win rate ضعيف ({win_rate:.1%})"
            else:
                reason = f"Profit factor ضعيف ({profit_factor:.2f})"
        
        return score, passed, reason
    
    def get_coin_characteristics(self, df: pd.DataFrame) -> Dict:
        """
        تحديد خصائص العملة لاستخدامها في المعايير المتكيفة
        
        Returns:
            Dict مع خصائص العملة
        """
        daily_returns = df['close'].pct_change().dropna()
        volatility = daily_returns.std()
        
        # تصنيف التقلب
        if volatility < 0.02:
            volatility_class = 'LOW'
        elif volatility < 0.04:
            volatility_class = 'MEDIUM'
        else:
            volatility_class = 'HIGH'
        
        # حجم التداول
        avg_volume = df['volume'].mean() if 'volume' in df.columns else 0
        
        if avg_volume > 1_000_000:
            volume_class = 'HIGH'
        elif avg_volume > 100_000:
            volume_class = 'MEDIUM'
        else:
            volume_class = 'LOW'
        
        # السعر
        avg_price = df['close'].mean()
        
        if avg_price > 1000:
            price_class = 'HIGH'  # BTC-like
        elif avg_price > 100:
            price_class = 'MEDIUM'  # ETH-like
        else:
            price_class = 'LOW'  # Altcoins
        
        return {
            'volatility': volatility,
            'volatility_class': volatility_class,
            'avg_volume': avg_volume,
            'volume_class': volume_class,
            'avg_price': avg_price,
            'price_class': price_class,
            'market_cap_estimate': avg_volume * avg_price  # تقريبي
        }
