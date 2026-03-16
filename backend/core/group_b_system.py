#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Group B System - نظام التداول الموحد الرئيسي
=============================================

هذا هو الملف الرئيسي للتداول الآلي.
يدير:
- الصفقات المفتوحة
- إشارات الدخول الجديدة
- وقف الخسارة وجني الأرباح
- Trailing Stop
- التواصل مع قاعدة البيانات

الاستخدام:
    from backend.core.group_b_system import GroupBSystem
    system = GroupBSystem(user_id=1)
    result = system.run_trading_cycle()
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd
import logging
import math

from config.logging_config import get_logger
from database.database_manager import DatabaseManager
from backend.utils.trading_context import get_effective_is_demo
from backend.utils.data_provider import DataProvider
from backend.risk.kelly_position_sizer import KellyPositionSizer
from backend.risk.portfolio_heat_manager import PortfolioHeatManager
from backend.ml.training_manager import MLTrainingManager
from backend.selection.dynamic_blacklist import get_dynamic_blacklist
from backend.utils.trading_notification_service import get_trading_notification_service
from backend.analysis.liquidity_cognitive_filter import LiquidityCognitiveFilter

# ===== مدير Binance للتداول الحقيقي =====
try:
    from backend.utils.binance_manager import BinanceManager
    BINANCE_MANAGER_AVAILABLE = True
except ImportError as e:
    BINANCE_MANAGER_AVAILABLE = False
    logging.getLogger(__name__).warning(f"⚠️ BinanceManager not available: {e}")

# ===== التعلم التكيّفي (تحسين المعاملات إحصائياً) =====
try:
    from backend.learning.adaptive_optimizer import AdaptiveOptimizer, get_adaptive_optimizer
    ADAPTIVE_LEARNING_AVAILABLE = True
except ImportError as e:
    ADAPTIVE_LEARNING_AVAILABLE = False
    logging.getLogger(__name__).warning(f"⚠️ Adaptive Learning not available: {e}")

# ===== واجهة الاستراتيجية الموحدة =====
from backend.strategies.base_strategy import BaseStrategy

# ===== نظام السكالبينج V8 (المحرك المحسّن) =====
try:
    from backend.strategies.scalping_v8_strategy import ScalpingV8Strategy, get_scalping_v8_strategy
    SCALPING_V8_AVAILABLE = True
except ImportError as e:
    SCALPING_V8_AVAILABLE = False
    logging.getLogger(__name__).warning(f"⚠️ Scalping V8 Strategy not available: {e}")

# ===== نظام السكالبينج V7 (احتياطي) =====
try:
    from backend.strategies.scalping_v7_strategy import ScalpingV7Strategy, get_scalping_v7_strategy
    SCALPING_V7_AVAILABLE = True
except ImportError as e:
    SCALPING_V7_AVAILABLE = False
    logging.getLogger(__name__).warning(f"⚠️ Scalping V7 Strategy not available: {e}")

# ===== النظام المعرفي (احتياطي) =====
try:
    from backend.cognitive.cognitive_orchestrator import (
        CognitiveOrchestrator, CognitiveAction, CognitiveDecision,
        get_cognitive_orchestrator
    )
    from backend.cognitive.multi_exit_engine import (
        MultiExitEngine, ExitReason, ExitUrgency,
        get_multi_exit_engine
    )
    COGNITIVE_AVAILABLE = True
except ImportError as e:
    COGNITIVE_AVAILABLE = False
    logging.getLogger(__name__).warning(f"⚠️ Cognitive system not available: {e}")

from backend.core.position_manager import PositionManagerMixin
from backend.core.scanner_mixin import ScannerMixin
from backend.core.risk_manager_mixin import RiskManagerMixin

logger = get_logger(__name__)


DEFAULT_SYMBOLS_POOL = [
    # V8.1: Optimised pool — BTC/BNB/XRP/AVAX removed, WIF/DOGE/DOT/ADA added
    # Validated: Config E  WR=61.5%  PF=1.76  PnL=+$767  14/14 profitable
    'ETHUSDT',   # WR=57.8%  PF=1.57
    'SOLUSDT',   # WR=62.6%  PF=2.63  ← star
    'NEARUSDT',  # WR=62.4%  PF=1.85  ← star
    'SUIUSDT',   # WR=60.4%  PF=1.41
    'ARBUSDT',   # WR=61.1%  PF=1.45
    'APTUSDT',   # WR=59.8%  PF=1.49
    'INJUSDT',   # WR=59.2%  PF=1.56
    'LINKUSDT',  # WR=57.4%  PF=1.67
    'PEPEUSDT',  # WR=64.4%  PF=2.06  ← star
    'OPUSDT',    # WR=59.6%  PF=1.61
    'WIFUSDT',   # WR=72.3%  PF=2.32  ← #1 overall
    'DOGEUSDT',  # WR=64.5%  PF=1.76
    'DOTUSDT',   # WR=60.8%  PF=1.82
    'ADAUSDT',   # WR=61.5%  PF=1.82
]

STABLE_BASE_ASSETS = {
    'USDT', 'USDC', 'FDUSD', 'TUSD', 'BUSD', 'USDP', 'DAI', 'USDJ', 'USDD',
    'PYUSD', 'EUR', 'EURC', 'AEUR'
}


class GroupBSystem(PositionManagerMixin, ScannerMixin, RiskManagerMixin):
    """
    نظام التداول الموحد - Group B
    
    المسؤوليات:
    1. مراقبة الصفقات المفتوحة كل 60 ثانية
    2. فحص شروط الخروج (Stop Loss / Take Profit / Trailing)
    3. البحث عن فرص دخول جديدة
    4. تنفيذ الأوامر (وهمي أو حقيقي)
    5. تسجيل كل شيء في قاعدة البيانات
    """
    
    def __init__(self, user_id: int = 1):
        """
        تهيئة نظام التداول
        
        Args:
            user_id: معرف المستخدم
        """
        self.user_id = user_id
        self.logger = logger
        
        # قاعدة البيانات
        self.db = DatabaseManager()
        
        # جلب إعدادات المستخدم
        self.user_settings = self._load_user_settings()
        
        # تحديد نوع التداول (محفظتان منفصلتان للأدمن)
        self.is_demo_trading = self._determine_trading_mode()
        self.user_portfolio = self._load_user_portfolio()
        self.can_trade = self.user_settings.get('trading_enabled', False)
        
        # ===== المكونات النشطة فقط =====
        self.data_provider = DataProvider()
        self.dynamic_blacklist = get_dynamic_blacklist(self.db)
        self.dynamic_blacklist.load_from_database()
        self.kelly_sizer = KellyPositionSizer()
        self.heat_manager = PortfolioHeatManager(max_heat_pct=6.0)
        self.notification_service = get_trading_notification_service()
        self.ml_training_manager = MLTrainingManager()
        self.ml_training_manager.start_cycle()
        # فلتر السيولة/المعرفة فوق الاستراتيجية الأساسية (V7)
        self.liquidity_filter = None
        try:
            mode = self.user_settings.get('liquidity_filter_mode', 'balanced')
            self.liquidity_filter = LiquidityCognitiveFilter(self.data_provider, mode=mode)
            self.logger.info(f"💧 LiquidityCognitiveFilter initialized (mode={mode})")
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to initialize LiquidityCognitiveFilter: {e}")
        
        # ===== مدير Binance للتداول الحقيقي =====
        self.binance_manager = None
        if BINANCE_MANAGER_AVAILABLE and not self.is_demo_trading:
            try:
                self.binance_manager = BinanceManager()
                self.logger.info("💱 BinanceManager connected (Real Trading Ready)")
            except Exception as e:
                self.logger.warning(f"⚠️ BinanceManager init failed: {e}")
        
        # ===== التعلم التكيّفي =====
        self.optimizer = None
        if ADAPTIVE_LEARNING_AVAILABLE:
            try:
                self.optimizer = get_adaptive_optimizer()
                self.logger.info("📈 Adaptive Optimizer connected")
            except Exception as e:
                self.logger.warning(f"⚠️ Adaptive Optimizer init failed: {e}")
        
        # ===== الاستراتيجية النشطة (عبر واجهة BaseStrategy الموحدة) =====
        # القانون: النظام لا يعرف أي استراتيجية يشغّل — يستخدم الواجهة فقط
        self.strategy: Optional[BaseStrategy] = None
        
        if SCALPING_V8_AVAILABLE:
            try:
                self.strategy = get_scalping_v8_strategy()
                self.logger.info(f"🚀 Strategy loaded: ScalpingV8 (PRIMARY — PF=1.72 WR=62%)")
            except Exception as e:
                self.logger.warning(f"⚠️ Scalping V8 Strategy init failed: {e}")
        
        if not self.strategy and SCALPING_V7_AVAILABLE:
            try:
                self.strategy = get_scalping_v7_strategy()
                self.logger.info(f"🚀 Strategy loaded: ScalpingV7 (FALLBACK)")
            except Exception as e:
                self.logger.warning(f"⚠️ Scalping V7 Strategy init failed: {e}")
        
        # ===== النظام المعرفي (احتياطي فقط — إذا لم تتوفر استراتيجية) =====
        self.cognitive_orchestrator = None
        self.multi_exit_engine = None
        if COGNITIVE_AVAILABLE and not self.strategy:
            try:
                self.cognitive_orchestrator = get_cognitive_orchestrator({
                    'exit': {
                        'max_loss_pct': 0.02,
                        'max_hold_hours': 72
                    },
                    'min_opportunity_score': 55,
                    'max_risk_score': 65,
                    'min_entry_confidence': 60,
                })
                self.multi_exit_engine = get_multi_exit_engine({
                    'max_loss_pct': 0.02,
                    'max_hold_hours': 72
                })
                self.logger.info("🧠 Cognitive Trading Architecture initialized (FALLBACK)")
            except Exception as e:
                self.logger.warning(f"⚠️ Cognitive system init failed: {e}")
                self.cognitive_orchestrator = None
        
        # ===== Backward compatibility alias =====
        # TODO: إزالة هذا بعد اكتمال فصل الاستراتيجية
        self.scalping_v7 = self.strategy
        
        # ===== إعدادات التداول (تُقرأ من الاستراتيجية النشطة) =====
        strategy_cfg = self.strategy.get_config() if self.strategy else {}
        self.config = {
            'cycle_interval': 60,
            'execution_timeframe': strategy_cfg.get('timeframe', '1h'),
            'confirmation_timeframe': strategy_cfg.get('timeframe', '1h'),
            'use_smart_exit': True,
            'max_sl_pct': strategy_cfg.get('sl_pct', 0.010),
            'trailing_activation_pct': strategy_cfg.get('trailing_activation', 0.006),
            'trailing_distance_pct': strategy_cfg.get('trailing_distance', 0.004),
            'max_hold_hours': strategy_cfg.get('max_hold_hours', 12),
            'stagnant_hours': strategy_cfg.get('stagnant_hours', 6),
            'min_confluence': strategy_cfg.get('min_confluence', 4),
            'min_timing': strategy_cfg.get('min_timing', 1),
            'require_quality': True,
            'position_size_pct': 0.06,
            'max_positions': strategy_cfg.get('max_positions', 5),
            'symbols_pool': self._get_trading_symbols()
        }
        
        # ===== Phase 0+1: حماية رأس المال =====
        # حالة يومية للـ Self-Throttling و Cooldown
        self.daily_state = {
            'trades_today': 0,
            'losses_today': 0,
            'consecutive_losses': 0,
            'daily_pnl': 0.0,
            'last_reset': datetime.now().date(),
            'cooldown_until': None,          # system-wide cooldown
            'max_daily_trades': 10,           # حد يومي للصفقات
            'max_daily_loss_pct': 0.03,       # حد خسارة يومي 3%
            'max_consecutive_losses': 3,      # cooldown بعد 3 خسائر متتالية
            'cooldown_hours': 2,              # مدة cooldown بالساعات
            'max_same_direction': 3,          # أقصى 3 صفقات بنفس الاتجاه
        }
        # ✅ استعادة الحالة اليومية من DB (تنجو من إعادة التشغيل)
        self._restore_daily_state_from_db()
        
        self.logger.info(f"✅ GroupBSystem initialized for user {user_id}")
        self.logger.info(f"   Trading Mode: {'Demo' if self.is_demo_trading else 'Real'}")
        self.logger.info(f"   Can Trade: {self.can_trade}")
        self.logger.info(f"   🛡️ Risk Protection: Heat={self.heat_manager.max_heat_pct}% | DailyLimit={self.daily_state['max_daily_trades']} | MaxLoss={self.daily_state['max_daily_loss_pct']*100}%")
    
    def _load_user_settings(self) -> Dict:
        """جلب إعدادات المستخدم من قاعدة البيانات حسب المحفظة الفعلية."""
        try:
            effective_is_demo = get_effective_is_demo(self.db, self.user_id)
            settings = self.db.get_trading_settings(self.user_id, is_demo=effective_is_demo)
            return settings or {
                'trading_enabled': False,
                'trading_mode': 'demo' if effective_is_demo else 'real',
                'risk_level': 'medium'
            }
        except Exception as e:
            self.logger.error(f"Error loading user settings: {e}")
            return {'trading_enabled': False, 'trading_mode': 'real'}
    
    def _load_user_portfolio(self) -> Dict:
        """جلب محفظة المستخدم من الجدول الموحد portfolio"""
        try:
            portfolio = self.db.get_user_portfolio(self.user_id, is_demo=1 if self.is_demo_trading else 0)
            if portfolio and not portfolio.get('error'):
                balance = float(portfolio.get('balance', 0.0) or 0.0)
                return {
                    'balance': balance,
                    'total_value': balance,
                    'available_balance': balance,
                    'source': 'portfolio_unified'
                }
            return {'balance': 0.0, 'total_value': 0.0, 'available_balance': 0.0, 'source': 'default'}
        except Exception as e:
            self.logger.error(f"Error loading unified portfolio: {e}")
            return {'balance': 0.0, 'total_value': 0.0, 'available_balance': 0.0, 'source': 'error_fallback'}
    
    def _determine_trading_mode(self) -> bool:
        """
        تحديد نوع التداول
        ✅ الأدمن يختار محفظة واحدة فقط (Demo أو Real)
        ✅ المستخدمون العاديون: حقيقي فقط
        """
        return bool(get_effective_is_demo(self.db, self.user_id))
    
    # ===== Risk methods: see risk_manager_mixin.py =====
    # _calculate_position_size, _restore_daily_state_from_db, _reset_daily_state_if_needed
    # _check_risk_gates, _check_directional_stress, _record_trade_result
    
    def _check_binance_keys(self) -> bool:
        """فحص وجود مفاتيح Binance"""
        try:
            keys = self.db.get_binance_keys(self.user_id)
            return keys is not None and keys.get('api_key')
        except Exception as e:
            self.logger.debug(f"Error checking Binance keys: {e}")
            return False
    
    def _get_trading_symbols(self) -> List[str]:
        """
        الحصول على قائمة العملات للتداول من قاعدة البيانات
        
        ✅ يحمّل من successful_coins مع ترتيب محافظ وآمن
        ✅ لا يغير منطق الاستراتيجية — فقط يحسن universe selection
        """
        try:
            rows = self._load_successful_coin_rows()
            if not rows:
                self.logger.warning("⚠️ لا توجد عملات في DB - استخدام القائمة الافتراضية")
                return DEFAULT_SYMBOLS_POOL.copy()

            ranked_rows = self._rank_successful_coin_rows(rows)
            if not ranked_rows:
                self.logger.warning("⚠️ تعذر بناء ranked candidates - استخدام القائمة الافتراضية")
                return DEFAULT_SYMBOLS_POOL.copy()

            symbols = self._refine_trading_symbol_candidates(ranked_rows)
            self.logger.info(
                f"✅ تم اختيار {len(symbols)} عملة للتداول من successful_coins "
                f"(candidates={len(ranked_rows)})"
            )
            return symbols
        except Exception as e:
            self.logger.error(f"❌ خطأ في تحميل العملات: {e}")
            return DEFAULT_SYMBOLS_POOL.copy()

    def _load_successful_coin_rows(self) -> List[tuple]:
        with self.db.get_connection() as conn:
            cursor = conn.execute("""
                SELECT symbol, score, win_rate, total_trades, profit_pct, analysis_date
                FROM successful_coins 
                WHERE is_active = TRUE 
                ORDER BY score DESC
                LIMIT 50
            """)
            return cursor.fetchall()

    def _rank_successful_coin_rows(self, rows: List[tuple]) -> List[tuple]:
        ranked_rows = []
        seen = set()

        for row in rows:
            raw_symbol = row[0]
            symbol = self._normalize_trading_symbol(raw_symbol)
            if not symbol or symbol in seen:
                continue

            score = self._safe_float(row[1], 0.0)
            win_rate = self._safe_float(row[2], 0.0)
            total_trades = max(0, int(self._safe_float(row[3], 0.0)))
            profit_pct = self._safe_float(row[4], 0.0)
            freshness_bonus = self._successful_coin_freshness_bonus(row[5])

            composite_score = self._build_symbol_composite_score(
                score=score,
                win_rate=win_rate,
                total_trades=total_trades,
                profit_pct=profit_pct,
                freshness_bonus=freshness_bonus,
            )

            ranked_rows.append((symbol, composite_score, score, win_rate, total_trades))
            seen.add(symbol)

        ranked_rows.sort(key=lambda item: item[1], reverse=True)
        return ranked_rows

    def _build_symbol_composite_score(self, score: float, win_rate: float,
                                      total_trades: int, profit_pct: float,
                                      freshness_bonus: float) -> float:
        return (
            (score * 0.55) +
            (min(100.0, win_rate * 100.0) * 0.20) +
            (min(12.0, math.log1p(total_trades) * 4.0)) +
            (max(-8.0, min(8.0, profit_pct)) * 0.50) +
            freshness_bonus
        )

    def _normalize_trading_symbol(self, symbol: Optional[str]) -> str:
        """تطبيع الرمز إلى صيغة Binance الموحدة مثل ETHUSDT."""
        if not symbol:
            return ''
        return str(symbol).upper().replace('/', '').replace('-', '').strip()

    def _extract_base_asset(self, symbol: str) -> str:
        normalized = self._normalize_trading_symbol(symbol)
        for quote in ('USDT', 'BUSD', 'USDC', 'FDUSD', 'TUSD', 'USDP'):
            if normalized.endswith(quote) and len(normalized) > len(quote):
                return normalized[:-len(quote)]
        return normalized

    def _is_stable_like_symbol(self, symbol: str) -> bool:
        base_asset = self._extract_base_asset(symbol)
        return base_asset in STABLE_BASE_ASSETS

    def _passes_movement_filter(self, symbol: str) -> bool:
        provider = self._get_symbol_filter_data_provider()
        try:
            df = provider.get_historical_data(symbol, '1h', limit=96)
            if df is None or len(df) < 48:
                return True

            metrics = self._calculate_symbol_movement_metrics(df)
            if not metrics:
                return True

            range_pct = metrics['range_pct']
            atr_pct = metrics['atr_pct']

            if range_pct < 2.5:
                self.logger.info(f"⏭️ Excluding {symbol}: low movement range={range_pct:.2f}%")
                return False

            if atr_pct is not None and atr_pct < 0.35:
                self.logger.info(f"⏭️ Excluding {symbol}: low ATR={atr_pct:.2f}%")
                return False

            return True
        except Exception as e:
            self.logger.warning(f"⚠️ Movement filter skipped for {symbol}: {e}")
            return True

    def _get_symbol_filter_data_provider(self):
        return getattr(self, 'data_provider', None) or DataProvider()

    def _calculate_symbol_movement_metrics(self, df: pd.DataFrame) -> Optional[Dict[str, float]]:
        recent = df.tail(48)
        high = recent['high'].max()
        low = recent['low'].min()
        close = recent['close'].iloc[-1]

        if close <= 0 or low <= 0:
            return None

        range_pct = ((high - low) / close) * 100.0
        atr_pct = None
        if {'high', 'low', 'close'}.issubset(df.columns):
            tr = (df['high'] - df['low']).tail(24)
            atr = tr.mean() if not tr.empty else 0
            atr_pct = (atr / close) * 100.0 if close > 0 else 0.0

        return {
            'range_pct': range_pct,
            'atr_pct': atr_pct,
        }

    def _refine_trading_symbol_candidates(self, ranked_rows: List[tuple]) -> List[str]:
        selected: List[str] = []
        fallback: List[str] = []

        for symbol, *_ in ranked_rows[:24]:
            fallback.append(symbol)

            if self._is_stable_like_symbol(symbol):
                self.logger.info(f"⏭️ Excluding {symbol}: stable-like base asset")
                continue

            if not self._passes_movement_filter(symbol):
                continue

            selected.append(symbol)
            if len(selected) >= 18:
                break

        if len(selected) >= 8:
            return selected

        return fallback[:18] if fallback else DEFAULT_SYMBOLS_POOL.copy()

    def _safe_float(self, value, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _successful_coin_freshness_bonus(self, analysis_date) -> float:
        """مكافأة بسيطة للعملات التي تم تحليلها حديثاً بدون إفراط."""
        if not analysis_date:
            return 0.0
        try:
            raw = str(analysis_date).replace('Z', '+00:00')
            analyzed_at = datetime.fromisoformat(raw)
            if analyzed_at.tzinfo is not None:
                analyzed_at = analyzed_at.replace(tzinfo=None)
            age_hours = max(0.0, (datetime.now() - analyzed_at).total_seconds() / 3600)
            if age_hours <= 12:
                return 8.0
            if age_hours <= 24:
                return 5.0
            if age_hours <= 72:
                return 2.0
            return 0.0
        except Exception:
            return 0.0
    
    def load_successful_coins_from_database(self) -> bool:
        """
        تحميل العملات الناجحة من قاعدة البيانات
        
        Returns:
            True إذا تم تحميل عملات بنجاح
        """
        try:
            symbols = self._get_trading_symbols()
            if symbols:
                self.config['symbols_pool'] = symbols
                self.logger.info(f"✅ تم تحديث symbols_pool بعدد {len(symbols)} عملة")
                return True

            self.logger.debug("⚠️ لا توجد عملات ناجحة في قاعدة البيانات")
            return False
                    
        except Exception as e:
            self.logger.error(f"❌ خطأ في تحميل العملات من قاعدة البيانات: {e}")
            return False
    
    def load_successful_coins_from_file(self) -> bool:
        """
        DEPRECATED: لا يُستخدم — النظام يحمل من قاعدة البيانات فقط
        تم الاحتفاظ به للتوافق الخلفي فقط
        
        Returns:
            False دائماً — استخدم load_successful_coins_from_database()
        """
        self.logger.warning("⚠️ load_successful_coins_from_file deprecated — النظام يستخدم DB فقط")
        return False
    
    def run_monitoring_only(self) -> Dict:
        """
        مراقبة الصفقات المفتوحة فقط (بدون فتح صفقات جديدة)
        
        يُستخدم عندما يكون التداول معطلاً لكن لدى المستخدم صفقات مفتوحة
        يجب إدارتها حتى تُغلق
        
        Returns:
            نتائج المراقبة
        """
        result = {
            'timestamp': datetime.now().isoformat(),
            'user_id': self.user_id,
            'mode': 'monitoring_only',
            'positions_checked': 0,
            'positions_closed': 0,
            'actions': [],
            'errors': []
        }
        
        try:
            # 1. تحديث المحفظة
            self.user_portfolio = self._load_user_portfolio()
            
            # 2. إدارة الصفقات المفتوحة فقط (بدون فتح جديدة)
            open_positions = self._get_open_positions()
            result['positions_checked'] = len(open_positions)
            
            if not open_positions:
                self.logger.debug(f"👁️ User {self.user_id}: لا توجد صفقات مفتوحة للمراقبة")
                return result
            
            self.logger.debug(f"👁️ User {self.user_id}: مراقبة {len(open_positions)} صفقة مفتوحة")
            
            for position in open_positions:
                try:
                    action = self._manage_position(position)
                    if action:
                        result['actions'].append(action)
                        if action.get('type') == 'CLOSE':
                            result['positions_closed'] += 1
                except Exception as e:
                    result['errors'].append(f"Position {position.get('id')}: {e}")
            
            # ملاحظة: لا نفتح صفقات جديدة في وضع المراقبة
            
        except Exception as e:
            result['errors'].append(f"Monitoring error: {e}")
            self.logger.error(f"Monitoring error: {e}")
        
        return result
    
    def run_trading_cycle(self) -> Dict:
        """
        تشغيل دورة تداول واحدة
        
        Returns:
            نتائج الدورة
        """
        result = {
            'timestamp': datetime.now().isoformat(),
            'user_id': self.user_id,
            'positions_checked': 0,
            'positions_closed': 0,
            'new_positions': 0,
            'actions': [],
            'errors': []
        }
        
        try:
            # 1. تحديث المحفظة
            self.user_portfolio = self._load_user_portfolio()
            
            # 2. إدارة الصفقات المفتوحة
            open_positions = self._get_open_positions()
            result['positions_checked'] = len(open_positions)
            
            for position in open_positions:
                try:
                    action = self._manage_position(position)
                    if action:
                        result['actions'].append(action)
                        if action.get('type') == 'CLOSE':
                            result['positions_closed'] += 1
                except Exception as e:
                    result['errors'].append(f"Position {position.get('id')}: {e}")
            
            # 3. البحث عن فرص جديدة (إذا مسموح والرصيد يكفي والإعدادات مكتملة)
            available_balance = self.user_portfolio.get('balance', 0)
            position_size_pct = self.user_settings.get('position_size_percentage', 0)
            user_max_positions = self.user_settings.get('max_positions', 0)
            
            can_open_new = self.can_trade and position_size_pct > 0 and user_max_positions > 0 and available_balance > 0
            
            if can_open_new:
                position_size = self._calculate_position_size(available_balance)
                max_affordable = int(available_balance / position_size) if position_size > 0 else 0
                effective_max = min(user_max_positions, max_affordable)
                
                self.logger.info(f"🔍 Scan check: open={len(open_positions)}, max={effective_max}, can_scan={len(open_positions) < effective_max}")
                
                if len(open_positions) < effective_max:
                    self.logger.info(f"🚀 Starting scan for user {self.user_id}...")
                    new_entries = self._scan_for_entries()
                    self.logger.info(f"✅ Scan complete: {len(new_entries)} entries found")
                    for entry in new_entries:
                        result['actions'].append(entry)
                        result['new_positions'] += 1
                else:
                    self.logger.info(f"⏸️ Max positions reached ({len(open_positions)}/{effective_max})")
            elif self.can_trade and (position_size_pct <= 0 or user_max_positions <= 0):
                self.logger.warning(f"⚠️ User {self.user_id}: trading enabled but settings incomplete (size={position_size_pct}%, max={user_max_positions})")
            else:
                self.logger.debug(f"⏸️ Not scanning: can_trade={self.can_trade}, balance={available_balance}, size_pct={position_size_pct}, max_pos={user_max_positions}")
            
        except Exception as e:
            result['errors'].append(f"Cycle error: {e}")
            self.logger.error(f"Cycle error: {e}")
        
        return result
    
    # ===== Position/Scanner/Indicator methods: see position_manager.py, scanner_mixin.py =====
    # _get_open_positions, _manage_position, _close_position → PositionManagerMixin
    # _open_position, _get_current_price, _update_trailing_stop → PositionManagerMixin
    # _scan_for_entries, _check_market_regime, _add_indicators → ScannerMixin

    def get_status(self) -> Dict:
        """الحصول على حالة النظام"""
        return {
            'user_id': self.user_id,
            'is_demo': self.is_demo_trading,
            'can_trade': self.can_trade,
            'balance': self.user_portfolio.get('balance', 0),
            'open_positions': len(self._get_open_positions())
        }
