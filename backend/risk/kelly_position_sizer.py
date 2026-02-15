"""
Kelly Criterion Position Sizer - حجم صفقة مثالي
يستخدم Kelly Criterion لحساب الحجم الأمثل
"""

import logging
from typing import Dict

logger = logging.getLogger(__name__)


class KellyPositionSizer:
    """
    حساب حجم الصفقة المثالي باستخدام Kelly Criterion
    
    Kelly % = (Win Rate * Avg Win - Loss Rate * Avg Loss) / Avg Win
    """
    
    def __init__(self, initial_balance: float = 10000):
        self.logger = logger
        self.initial_balance = initial_balance
        
        # حدود الأمان
        self.min_position_pct = 0.01  # 1% حد أدنى
        self.max_position_pct = 0.15  # 15% حد أقصى
        
        # افتراضات إذا لا توجد بيانات تاريخية
        self.default_win_rate = 0.55
        self.default_avg_win = 0.03
        self.default_avg_loss = 0.015
    
    def calculate_position_size(self, balance: float,
                               max_position_pct: float = 0.10,
                               symbol: str = None,
                               historical_performance: Dict = None) -> Dict:
        """
        حساب حجم الصفقة باستخدام Kelly Criterion
        
        Args:
            balance: الرصيد الحالي
            max_position_pct: الحد الأقصى كنسبة عشرية (0.10 = 10%)
            symbol: رمز العملة (للاستخدام المستقبلي مع بيانات لكل عملة)
            historical_performance: أداء تاريخي للاستراتيجية (اختياري)
        
        Returns:
            Dict مع kelly_pct (عشري), win_rate, avg_rr, confidence
        """
        try:
            # حساب Kelly %
            if historical_performance and historical_performance.get('total_trades', 0) >= 20:
                raw_kelly = self._calculate_kelly_from_history(historical_performance)
                win_rate = historical_performance.get('winning_trades', 0) / max(historical_performance.get('total_trades', 1), 1)
                avg_win = historical_performance.get('avg_win_pct', self.default_avg_win)
                avg_loss = abs(historical_performance.get('avg_loss_pct', self.default_avg_loss))
                avg_rr = avg_win / max(avg_loss, 0.001)
                confidence = 'HIGH'
            else:
                raw_kelly = self._calculate_kelly_default()
                win_rate = self.default_win_rate
                avg_rr = self.default_avg_win / max(self.default_avg_loss, 0.001)
                confidence = 'LOW'
            
            # Half Kelly للأمان
            kelly_pct = raw_kelly * 0.5
            
            # تطبيق الحدود (min_position_pct و max_position_pct كلاهما عشري)
            effective_max = min(self.max_position_pct, max_position_pct)
            kelly_pct = max(self.min_position_pct, min(kelly_pct, effective_max))
            
            return {
                'kelly_pct': kelly_pct,
                'win_rate': win_rate,
                'avg_rr': avg_rr,
                'confidence': confidence,
                'raw_kelly': raw_kelly,
                'symbol': symbol,
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating position size: {e}")
            return self._get_default_size(balance, max_position_pct)
    
    def _calculate_kelly_from_history(self, perf: Dict) -> float:
        """حساب Kelly من الأداء التاريخي"""
        try:
            total_trades = perf.get('total_trades', 0)
            winning_trades = perf.get('winning_trades', 0)
            
            if total_trades == 0:
                return self._calculate_kelly_default()
            
            win_rate = winning_trades / total_trades
            loss_rate = 1 - win_rate
            
            avg_win_pct = perf.get('avg_win_pct', self.default_avg_win)
            avg_loss_pct = abs(perf.get('avg_loss_pct', self.default_avg_loss))
            
            # Kelly Formula
            if avg_win_pct == 0:
                return 0.02
            
            kelly = (win_rate * avg_win_pct - loss_rate * avg_loss_pct) / avg_win_pct
            
            # التأكد من قيمة موجبة
            kelly = max(0.01, kelly)
            
            return kelly
            
        except Exception as e:
            self.logger.error(f"Error in Kelly calculation: {e}")
            return self._calculate_kelly_default()
    
    def _calculate_kelly_default(self) -> float:
        """Kelly افتراضي عند عدم وجود بيانات"""
        win_rate = self.default_win_rate
        loss_rate = 1 - win_rate
        avg_win = self.default_avg_win
        avg_loss = self.default_avg_loss
        
        kelly = (win_rate * avg_win - loss_rate * avg_loss) / avg_win
        return max(0.02, kelly)  # حد أدنى 2%
    
    def _get_default_size(self, balance: float, max_position_pct: float = 0.10) -> Dict:
        """حجم افتراضي آمن — يُرجع kelly_pct كنسبة عشرية"""
        default_pct = 0.02  # 2%
        return {
            'kelly_pct': default_pct,
            'win_rate': self.default_win_rate,
            'avg_rr': self.default_avg_win / max(self.default_avg_loss, 0.001),
            'confidence': 'DEFAULT',
            'raw_kelly': 0.04,
            'symbol': None,
        }
