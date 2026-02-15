"""
طبقة تحليل جودة العملة المستقبلية
تقوم بتحليل العوامل التي تؤثر على جودة العملة مستقبلياً قبل التداول الفعلي
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
from datetime import datetime, timedelta
try:
    import pandas_ta as ta
except ImportError:
    try:
        import ta
    except ImportError:
        ta = None

logger = logging.getLogger(__name__)

class CoinQualityAnalyzer:
    """
    محلل جودة العملة المستقبلية
    يقيس العوامل التي تؤثر على استمرارية نجاح العملة
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # معايير تحليل الجودة المستقبلية
        self.quality_criteria = {
            # 1. استقرار الأداء
            "performance_stability": {
                "weight": 0.25,
                "min_consistency_score": 0.6,
                "lookback_periods": [7, 14, 30]  # أيام
            },
            
            # 2. قوة الاتجاه
            "trend_strength": {
                "weight": 0.20,
                "min_trend_score": 0.5,
                "trend_indicators": ["ADX", "MACD", "EMA_alignment"]
            },
            
            # 3. جودة السيولة
            "liquidity_quality": {
                "weight": 0.15,
                "min_volume_consistency": 0.7,
                "min_spread_quality": 0.8
            },
            
            # 4. استقرار التقلبات
            "volatility_stability": {
                "weight": 0.15,
                "optimal_volatility_range": (0.02, 0.08),  # 2%-8% يومياً
                "max_volatility_deviation": 0.5
            },
            
            # 5. قوة الدعم والمقاومة
            "support_resistance": {
                "weight": 0.10,
                "min_level_strength": 0.6,
                "max_breakout_frequency": 0.3
            },
            
            # 6. التوافق مع السوق العام
            "market_correlation": {
                "weight": 0.10,
                "optimal_correlation_range": (0.3, 0.7),  # ليس مستقل تماماً وليس تابع تماماً
                "btc_correlation_weight": 0.6
            },
            
            # 7. استمرارية الإشارات
            "signal_continuity": {
                "weight": 0.05,
                "min_signal_consistency": 0.7,
                "signal_degradation_threshold": 0.2
            }
        }
    
    def analyze_coin_quality(self, symbol: str, historical_data: pd.DataFrame, 
                           strategy_performance: Dict[str, Any]) -> Dict[str, Any]:
        """
        تحليل شامل لجودة العملة المستقبلية
        
        Args:
            symbol: رمز العملة
            historical_data: البيانات التاريخية
            strategy_performance: أداء الاستراتيجية التاريخي
            
        Returns:
            تقرير شامل عن جودة العملة المستقبلية
        """
        try:
            self.logger.info(f"🔍 بدء تحليل جودة العملة المستقبلية لـ {symbol}")
            
            analysis_results = {
                "symbol": symbol,
                "analysis_timestamp": datetime.now().isoformat(),
                "overall_quality_score": 0.0,
                "quality_grade": "Unknown",
                "recommendations": [],
                "risk_factors": [],
                "detailed_analysis": {}
            }
            
            # 1. تحليل استقرار الأداء
            performance_analysis = self._analyze_performance_stability(
                historical_data, strategy_performance
            )
            analysis_results["detailed_analysis"]["performance_stability"] = performance_analysis
            
            # 2. تحليل قوة الاتجاه
            trend_analysis = self._analyze_trend_strength(historical_data)
            analysis_results["detailed_analysis"]["trend_strength"] = trend_analysis
            
            # 3. تحليل جودة السيولة
            liquidity_analysis = self._analyze_liquidity_quality(historical_data)
            analysis_results["detailed_analysis"]["liquidity_quality"] = liquidity_analysis
            
            # 4. تحليل استقرار التقلبات
            volatility_analysis = self._analyze_volatility_stability(historical_data)
            analysis_results["detailed_analysis"]["volatility_stability"] = volatility_analysis
            
            # 5. تحليل الدعم والمقاومة
            support_resistance_analysis = self._analyze_support_resistance(historical_data)
            analysis_results["detailed_analysis"]["support_resistance"] = support_resistance_analysis
            
            # 6. تحليل التوافق مع السوق
            market_correlation_analysis = self._analyze_market_correlation(symbol, historical_data)
            analysis_results["detailed_analysis"]["market_correlation"] = market_correlation_analysis
            
            # 7. تحليل استمرارية الإشارات
            signal_continuity_analysis = self._analyze_signal_continuity(
                historical_data, strategy_performance
            )
            analysis_results["detailed_analysis"]["signal_continuity"] = signal_continuity_analysis
            
            # حساب النتيجة الإجمالية
            overall_score = self._calculate_overall_quality_score(analysis_results["detailed_analysis"])
            analysis_results["overall_quality_score"] = overall_score
            analysis_results["quality_grade"] = self._get_quality_grade(overall_score)
            
            # توليد التوصيات وعوامل المخاطرة
            analysis_results["recommendations"] = self._generate_recommendations(analysis_results)
            analysis_results["risk_factors"] = self._identify_risk_factors(analysis_results)
            
            self.logger.info(f"✅ تم تحليل {symbol} - النتيجة: {overall_score:.2f} ({analysis_results['quality_grade']})")
            
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"❌ خطأ في تحليل جودة العملة {symbol}: {e}")
            return {"error": str(e), "symbol": symbol}
    
    def _analyze_performance_stability(self, data: pd.DataFrame, 
                                     strategy_performance: Dict[str, Any]) -> Dict[str, Any]:
        """تحليل استقرار الأداء عبر فترات زمنية مختلفة"""
        try:
            # حساب العوائد اليومية
            data['daily_return'] = data['close'].pct_change()
            
            stability_scores = []
            
            # تحليل الاستقرار عبر فترات مختلفة
            for period in self.quality_criteria["performance_stability"]["lookback_periods"]:
                if len(data) >= period:
                    recent_data = data.tail(period)
                    
                    # حساب معامل الاختلاف (Coefficient of Variation)
                    returns_std = recent_data['daily_return'].std()
                    returns_mean = abs(recent_data['daily_return'].mean())
                    
                    if returns_mean > 0:
                        cv = returns_std / returns_mean
                        stability_score = max(0, 1 - cv)  # كلما قل التذبذب، زاد الاستقرار
                    else:
                        stability_score = 0.5
                    
                    stability_scores.append(stability_score)
            
            avg_stability = np.mean(stability_scores) if stability_scores else 0
            
            return {
                "stability_score": avg_stability,
                "period_scores": stability_scores,
                "is_stable": avg_stability >= self.quality_criteria["performance_stability"]["min_consistency_score"],
                "volatility_coefficient": data['daily_return'].std() if len(data) > 1 else 0
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل استقرار الأداء: {e}")
            return {"stability_score": 0, "error": str(e)}
    
    def _analyze_trend_strength(self, data: pd.DataFrame) -> Dict[str, Any]:
        """تحليل قوة الاتجاه الحالي"""
        try:
            # حساب مؤشرات الاتجاه
            data['adx'] = ta.trend.adx(data['high'], data['low'], data['close'], window=14)
            data['macd'] = ta.trend.macd_diff(data['close'])
            data['ema_9'] = ta.trend.ema_indicator(data['close'], window=9)
            data['ema_21'] = ta.trend.ema_indicator(data['close'], window=21)
            data['ema_50'] = ta.trend.ema_indicator(data['close'], window=50)
            
            # تقييم قوة الاتجاه
            latest_adx = data['adx'].iloc[-1] if not pd.isna(data['adx'].iloc[-1]) else 0
            latest_macd = data['macd'].iloc[-1] if not pd.isna(data['macd'].iloc[-1]) else 0
            
            # تحليل ترتيب المتوسطات المتحركة
            latest_close = data['close'].iloc[-1]
            latest_ema_9 = data['ema_9'].iloc[-1]
            latest_ema_21 = data['ema_21'].iloc[-1]
            latest_ema_50 = data['ema_50'].iloc[-1]
            
            # تحديد اتجاه المتوسطات
            ema_alignment_score = 0
            if latest_ema_9 > latest_ema_21 > latest_ema_50:  # اتجاه صاعد
                ema_alignment_score = 1.0
            elif latest_ema_9 < latest_ema_21 < latest_ema_50:  # اتجاه هابط
                ema_alignment_score = 0.8
            else:  # اتجاه مختلط
                ema_alignment_score = 0.4
            
            # حساب نتيجة قوة الاتجاه الإجمالية
            adx_score = min(latest_adx / 50, 1.0)  # تطبيع ADX
            macd_score = 0.5 + (latest_macd * 0.1)  # تطبيع MACD
            macd_score = max(0, min(1, macd_score))
            
            trend_strength_score = (adx_score * 0.4 + macd_score * 0.3 + ema_alignment_score * 0.3)
            
            return {
                "trend_strength_score": trend_strength_score,
                "adx_value": latest_adx,
                "macd_value": latest_macd,
                "ema_alignment": ema_alignment_score,
                "trend_direction": "صاعد" if ema_alignment_score == 1.0 else "هابط" if ema_alignment_score == 0.8 else "مختلط",
                "is_strong_trend": trend_strength_score >= self.quality_criteria["trend_strength"]["min_trend_score"]
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل قوة الاتجاه: {e}")
            return {"trend_strength_score": 0, "error": str(e)}
    
    def _analyze_liquidity_quality(self, data: pd.DataFrame) -> Dict[str, Any]:
        """تحليل جودة السيولة واستقرارها"""
        try:
            # حساب متوسط الحجم ومعامل الاختلاف
            avg_volume = data['volume'].mean()
            volume_std = data['volume'].std()
            volume_cv = volume_std / avg_volume if avg_volume > 0 else float('inf')
            
            # تقييم استقرار الحجم (كلما قل التذبذب، زادت الجودة)
            volume_consistency = max(0, 1 - min(volume_cv, 2) / 2)
            
            # تحليل اتجاه الحجم (هل يتزايد أم يتناقص؟)
            recent_volume = data['volume'].tail(10).mean()
            older_volume = data['volume'].head(10).mean()
            volume_trend = (recent_volume - older_volume) / older_volume if older_volume > 0 else 0
            
            # تقدير جودة السبريد (بناءً على التقلبات قصيرة المدى)
            data['price_change'] = data['close'].pct_change().abs()
            avg_price_change = data['price_change'].tail(20).mean()
            spread_quality = max(0, 1 - min(avg_price_change * 100, 1))  # تطبيع
            
            liquidity_score = (volume_consistency * 0.6 + spread_quality * 0.4)
            
            return {
                "liquidity_score": liquidity_score,
                "volume_consistency": volume_consistency,
                "spread_quality": spread_quality,
                "volume_trend": volume_trend,
                "avg_volume": avg_volume,
                "is_liquid": liquidity_score >= self.quality_criteria["liquidity_quality"]["min_volume_consistency"]
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل جودة السيولة: {e}")
            return {"liquidity_score": 0, "error": str(e)}
    
    def _analyze_volatility_stability(self, data: pd.DataFrame) -> Dict[str, Any]:
        """تحليل استقرار التقلبات"""
        try:
            # حساب التقلبات اليومية
            data['daily_volatility'] = data['close'].pct_change().rolling(window=20).std()
            
            avg_volatility = data['daily_volatility'].mean()
            volatility_std = data['daily_volatility'].std()
            
            # تحديد ما إذا كانت التقلبات ضمن النطاق المثالي
            optimal_min, optimal_max = self.quality_criteria["volatility_stability"]["optimal_volatility_range"]
            
            if optimal_min <= avg_volatility <= optimal_max:
                volatility_optimality = 1.0
            else:
                # حساب المسافة من النطاق المثالي
                if avg_volatility < optimal_min:
                    distance = optimal_min - avg_volatility
                else:
                    distance = avg_volatility - optimal_max
                volatility_optimality = max(0, 1 - distance / optimal_max)
            
            # تقييم استقرار التقلبات
            volatility_stability = max(0, 1 - min(volatility_std / avg_volatility, 1)) if avg_volatility > 0 else 0
            
            volatility_score = (volatility_optimality * 0.6 + volatility_stability * 0.4)
            
            return {
                "volatility_score": volatility_score,
                "avg_volatility": avg_volatility,
                "volatility_stability": volatility_stability,
                "is_optimal_volatility": volatility_optimality >= 0.8,
                "volatility_trend": "مستقر" if volatility_stability > 0.7 else "متذبذب"
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل استقرار التقلبات: {e}")
            return {"volatility_score": 0, "error": str(e)}
    
    def _analyze_support_resistance(self, data: pd.DataFrame) -> Dict[str, Any]:
        """تحليل قوة مستويات الدعم والمقاومة"""
        try:
            # تحديد القمم والقيعان
            from scipy.signal import find_peaks
            
            # البحث عن القمم والقيعان
            peaks, _ = find_peaks(data['high'].values, distance=5)
            troughs, _ = find_peaks(-data['low'].values, distance=5)
            
            # تحليل قوة المستويات
            support_levels = data['low'].iloc[troughs].values if len(troughs) > 0 else []
            resistance_levels = data['high'].iloc[peaks].values if len(peaks) > 0 else []
            
            # حساب قوة المستويات بناءً على عدد مرات الاختبار
            current_price = data['close'].iloc[-1]
            
            # تقييم قوة الدعم والمقاومة
            support_strength = self._calculate_level_strength(support_levels, current_price, "support")
            resistance_strength = self._calculate_level_strength(resistance_levels, current_price, "resistance")
            
            overall_strength = (support_strength + resistance_strength) / 2
            
            return {
                "support_resistance_score": overall_strength,
                "support_strength": support_strength,
                "resistance_strength": resistance_strength,
                "support_levels_count": len(support_levels),
                "resistance_levels_count": len(resistance_levels),
                "is_strong_levels": overall_strength >= self.quality_criteria["support_resistance"]["min_level_strength"]
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل الدعم والمقاومة: {e}")
            return {"support_resistance_score": 0, "error": str(e)}
    
    def _calculate_level_strength(self, levels: np.ndarray, current_price: float, level_type: str) -> float:
        """حساب قوة مستويات الدعم أو المقاومة"""
        if len(levels) == 0:
            return 0
        
        # تجميع المستويات المتقاربة
        tolerance = current_price * 0.02  # 2% tolerance
        unique_levels = []
        level_counts = []
        
        for level in levels:
            found_similar = False
            for i, unique_level in enumerate(unique_levels):
                if abs(level - unique_level) <= tolerance:
                    level_counts[i] += 1
                    found_similar = True
                    break
            
            if not found_similar:
                unique_levels.append(level)
                level_counts.append(1)
        
        # حساب قوة المستويات بناءً على عدد مرات الاختبار
        if len(level_counts) == 0:
            return 0
        
        max_tests = max(level_counts)
        avg_tests = np.mean(level_counts)
        
        # تطبيع النتيجة
        strength = min(avg_tests / 3, 1.0)  # 3 اختبارات = قوة كاملة
        
        return strength
    
    def _analyze_market_correlation(self, symbol: str, data: pd.DataFrame) -> Dict[str, Any]:
        """تحليل التوافق مع السوق العام"""
        try:
            # هذا تحليل مبسط - في التطبيق الحقيقي نحتاج بيانات BTC والسوق العام
            
            # حساب الارتباط الذاتي كمؤشر على استقلالية العملة
            returns = data['close'].pct_change().dropna()
            
            # حساب الارتباط مع المتوسط المتحرك كمؤشر على الاتجاه
            data['sma_20'] = data['close'].rolling(window=20).mean()
            correlation_with_trend = returns.corr(data['sma_20'].pct_change().dropna())
            
            if pd.isna(correlation_with_trend):
                correlation_with_trend = 0
            
            # تقدير جودة الارتباط
            optimal_min, optimal_max = self.quality_criteria["market_correlation"]["optimal_correlation_range"]
            
            if optimal_min <= abs(correlation_with_trend) <= optimal_max:
                correlation_quality = 1.0
            else:
                distance = min(abs(abs(correlation_with_trend) - optimal_min), 
                             abs(abs(correlation_with_trend) - optimal_max))
                correlation_quality = max(0, 1 - distance / optimal_max)
            
            return {
                "market_correlation_score": correlation_quality,
                "trend_correlation": correlation_with_trend,
                "correlation_quality": correlation_quality,
                "independence_level": 1 - abs(correlation_with_trend),
                "is_optimal_correlation": correlation_quality >= 0.7
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل التوافق مع السوق: {e}")
            return {"market_correlation_score": 0.5, "error": str(e)}
    
    def _analyze_signal_continuity(self, data: pd.DataFrame, 
                                 strategy_performance: Dict[str, Any]) -> Dict[str, Any]:
        """تحليل استمرارية الإشارات"""
        try:
            # تحليل مبسط لاستمرارية الإشارات
            # في التطبيق الحقيقي، نحتاج تشغيل الاستراتيجية على فترات مختلفة
            
            # حساب استقرار الأداء عبر الوقت
            window_size = max(50, len(data) // 4)
            
            if len(data) < window_size * 2:
                return {"signal_continuity_score": 0.5, "insufficient_data": True}
            
            # تقسيم البيانات إلى فترات
            mid_point = len(data) // 2
            early_data = data.iloc[:mid_point]
            recent_data = data.iloc[mid_point:]
            
            # حساب الأداء في كل فترة (مبسط)
            early_performance = early_data['close'].iloc[-1] / early_data['close'].iloc[0] - 1
            recent_performance = recent_data['close'].iloc[-1] / recent_data['close'].iloc[0] - 1
            
            # تقييم الاستمرارية
            performance_consistency = 1 - abs(early_performance - recent_performance) / max(abs(early_performance), abs(recent_performance), 0.01)
            performance_consistency = max(0, min(1, performance_consistency))
            
            return {
                "signal_continuity_score": performance_consistency,
                "early_performance": early_performance,
                "recent_performance": recent_performance,
                "performance_consistency": performance_consistency,
                "is_consistent": performance_consistency >= self.quality_criteria["signal_continuity"]["min_signal_consistency"]
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في تحليل استمرارية الإشارات: {e}")
            return {"signal_continuity_score": 0.5, "error": str(e)}
    
    def _calculate_overall_quality_score(self, detailed_analysis: Dict[str, Any]) -> float:
        """حساب النتيجة الإجمالية لجودة العملة"""
        total_score = 0
        total_weight = 0
        
        for criterion, weight_info in self.quality_criteria.items():
            weight = weight_info["weight"]
            
            if criterion in detailed_analysis:
                analysis = detailed_analysis[criterion]
                score_key = f"{criterion}_score"
                
                if score_key in analysis and not pd.isna(analysis[score_key]):
                    total_score += analysis[score_key] * weight
                    total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 0
    
    def _get_quality_grade(self, score: float) -> str:
        """تحديد درجة الجودة بناءً على النتيجة"""
        if score >= 0.85:
            return "ممتاز"
        elif score >= 0.70:
            return "جيد جداً"
        elif score >= 0.55:
            return "جيد"
        elif score >= 0.40:
            return "مقبول"
        else:
            return "ضعيف"
    
    def _generate_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """توليد التوصيات بناءً على التحليل"""
        recommendations = []
        detailed = analysis_results["detailed_analysis"]
        
        # توصيات بناءً على كل معيار
        if detailed.get("performance_stability", {}).get("stability_score", 0) < 0.6:
            recommendations.append("⚠️ الأداء غير مستقر - يُنصح بمراقبة إضافية")
        
        if detailed.get("trend_strength", {}).get("trend_strength_score", 0) < 0.5:
            recommendations.append("📉 الاتجاه ضعيف - قد تحتاج لاستراتيجيات مختلفة")
        
        if detailed.get("liquidity_quality", {}).get("liquidity_score", 0) < 0.7:
            recommendations.append("💧 السيولة منخفضة - احذر من الانزلاق السعري")
        
        if detailed.get("volatility_stability", {}).get("volatility_score", 0) < 0.6:
            recommendations.append("📊 التقلبات غير مثالية - اضبط إدارة المخاطر")
        
        if analysis_results["overall_quality_score"] >= 0.8:
            recommendations.append("✅ جودة ممتازة - مناسبة للتداول")
        elif analysis_results["overall_quality_score"] >= 0.6:
            recommendations.append("⚡ جودة جيدة - مناسبة مع مراقبة")
        else:
            recommendations.append("⛔ جودة منخفضة - تجنب التداول أو قلل المخاطرة")
        
        return recommendations
    
    def _identify_risk_factors(self, analysis_results: Dict[str, Any]) -> List[str]:
        """تحديد عوامل المخاطرة"""
        risk_factors = []
        detailed = analysis_results["detailed_analysis"]
        
        # تحديد المخاطر بناءً على كل معيار
        if detailed.get("performance_stability", {}).get("volatility_coefficient", 0) > 0.1:
            risk_factors.append("تقلبات عالية في الأداء")
        
        if detailed.get("liquidity_quality", {}).get("volume_trend", 0) < -0.2:
            risk_factors.append("انخفاض في السيولة")
        
        if detailed.get("trend_strength", {}).get("trend_direction") == "مختلط":
            risk_factors.append("عدم وضوح الاتجاه")
        
        if detailed.get("support_resistance", {}).get("support_levels_count", 0) < 2:
            risk_factors.append("ضعف مستويات الدعم")
        
        if analysis_results["overall_quality_score"] < 0.4:
            risk_factors.append("جودة إجمالية منخفضة")
        
        return risk_factors

    def should_proceed_with_trading(self, analysis_results: Dict[str, Any], 
                                  min_quality_threshold: float = 0.6) -> Tuple[bool, str]:
        """
        تحديد ما إذا كان يجب المتابعة بالتداول أم لا
        
        Returns:
            Tuple[bool, str]: (هل يجب التداول, السبب)
        """
        score = analysis_results.get("overall_quality_score", 0)
        grade = analysis_results.get("quality_grade", "Unknown")
        
        if score >= min_quality_threshold:
            return True, f"جودة مقبولة ({grade}) - نتيجة: {score:.2f}"
        else:
            return False, f"جودة منخفضة ({grade}) - نتيجة: {score:.2f}"
