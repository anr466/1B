"""
حزمة استراتيجيات التداول
تحتوي على مجموعة متنوعة من استراتيجيات التداول المتخصصة لمختلف ظروف السوق
"""

# استيراد الاستراتيجيات المتاحة
try:
    from backend.strategies.trend_following import TrendFollowingStrategy
except ImportError:
    TrendFollowingStrategy = None

try:
    from backend.strategies.mean_reversion import MeanReversionStrategy
except ImportError:
    MeanReversionStrategy = None

try:
    from backend.strategies.momentum_breakout import MomentumBreakoutStrategy
except ImportError:
    MomentumBreakoutStrategy = None

try:
    from backend.strategies.peak_valley_scalping import (
        PeakValleyScalpingStrategy,
    )
except ImportError:
    PeakValleyScalpingStrategy = None

try:
    from backend.strategies.scalping_ema import ScalpingEMAStrategy
except ImportError:
    ScalpingEMAStrategy = None

try:
    from backend.strategies.rsi_divergence import RSIDivergenceStrategy
except ImportError:
    RSIDivergenceStrategy = None

try:
    from backend.strategies.volume_price_trend import VolumePriceTrendStrategy
except ImportError:
    VolumePriceTrendStrategy = None

try:
    from backend.strategies.mtfa_optimized import MTFAOptimizedStrategy
except ImportError:
    MTFAOptimizedStrategy = None

# قاموس الاستراتيجيات المتاحة
AVAILABLE_STRATEGIES = {}

if TrendFollowingStrategy:
    AVAILABLE_STRATEGIES["trend_following"] = TrendFollowingStrategy
if MeanReversionStrategy:
    AVAILABLE_STRATEGIES["mean_reversion"] = MeanReversionStrategy
if MomentumBreakoutStrategy:
    AVAILABLE_STRATEGIES["momentum_breakout"] = MomentumBreakoutStrategy
if PeakValleyScalpingStrategy:
    AVAILABLE_STRATEGIES["peak_valley_scalping"] = PeakValleyScalpingStrategy
if ScalpingEMAStrategy:
    AVAILABLE_STRATEGIES["scalping_ema"] = ScalpingEMAStrategy
if RSIDivergenceStrategy:
    AVAILABLE_STRATEGIES["rsi_divergence"] = RSIDivergenceStrategy
if VolumePriceTrendStrategy:
    AVAILABLE_STRATEGIES["volume_price_trend"] = VolumePriceTrendStrategy
if MTFAOptimizedStrategy:
    AVAILABLE_STRATEGIES["mtfa_optimized"] = MTFAOptimizedStrategy

__all__ = [
    "AVAILABLE_STRATEGIES",
    "TrendFollowingStrategy",
    "MeanReversionStrategy",
    "MomentumBreakoutStrategy",
    "PeakValleyScalpingStrategy",
    "ScalpingEMAStrategy",
    "RSIDivergenceStrategy",
    "VolumePriceTrendStrategy",
    "MTFAOptimizedStrategy",
]
