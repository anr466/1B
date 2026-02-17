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

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pandas as pd

from database.database_manager import DatabaseManager
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

# ===== نظام السكالبينج V7 (المحرك الأساسي للتداول) =====
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

logger = logging.getLogger(__name__)


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
        self.user_portfolio = self._load_user_portfolio()
        
        # تحديد نوع التداول (محفظتان منفصلتان للأدمن)
        self.is_demo_trading = self._determine_trading_mode()
        self.can_trade = self.user_settings.get('trading_enabled', False)
        
        # ===== المكونات النشطة فقط =====
        self.data_provider = DataProvider()
        self.dynamic_blacklist = get_dynamic_blacklist(self.db)
        self.dynamic_blacklist.load_from_database()
        self.kelly_sizer = KellyPositionSizer()
        self.heat_manager = PortfolioHeatManager(max_heat_pct=6.0)
        self.notification_service = get_trading_notification_service()
        self.ml_training_manager = MLTrainingManager()
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
        
        if SCALPING_V7_AVAILABLE:
            try:
                self.strategy = get_scalping_v7_strategy()
                self.logger.info(f"🚀 Strategy loaded: {self.strategy} (PRIMARY)")
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
        """جلب إعدادات المستخدم من قاعدة البيانات"""
        try:
            settings = self.db.get_trading_settings(self.user_id)
            return settings or {
                'trading_enabled': False,
                'trading_mode': 'real',
                'risk_level': 'medium'
            }
        except Exception as e:
            self.logger.error(f"Error loading user settings: {e}")
            return {'trading_enabled': False, 'trading_mode': 'real'}
    
    def _load_user_portfolio(self) -> Dict:
        """جلب محفظة المستخدم من الجدول الموحد portfolio"""
        try:
            portfolio = self.db.get_user_portfolio(self.user_id)
            if portfolio and not portfolio.get('error'):
                return {
                    'balance': portfolio.get('balance', 1000.0),
                    'total_value': portfolio.get('balance', 1000.0),
                    'available_balance': portfolio.get('balance', 1000.0),
                    'source': 'portfolio_unified'
                }
            return {'balance': 1000.0, 'total_value': 1000.0, 'available_balance': 1000.0, 'source': 'default'}
        except Exception as e:
            self.logger.error(f"Error loading unified portfolio: {e}")
            return {'balance': 1000.0, 'total_value': 1000.0, 'available_balance': 1000.0, 'source': 'error_fallback'}
    
    def _determine_trading_mode(self) -> bool:
        """
        تحديد نوع التداول
        ✅ الأدمن يختار محفظة واحدة فقط (Demo أو Real)
        ✅ المستخدمون العاديون: حقيقي فقط
        """
        user = self.db.get_user_by_id(self.user_id)
        
        if user and user.get('user_type') == 'admin':
            trading_mode = self.user_settings.get('trading_mode', 'auto')
            # الأدمن: يختار محفظة واحدة فقط
            return trading_mode == 'demo'
        
        # المستخدم العادي: حقيقي فقط (لا يوجد تداول وهمي)
        return False
    
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
        الحصول على قائمة العملات للتداول
        
        ===== الخوارزمية الذهبية V4 - مُحدّث فبراير 2026 =====
        
        ✅ Tier 1 - سيولة عالية وأداء مستقر:
           ETHUSDT, BNBUSDT
        
        ✅ Tier 2 - تقلب متوسط مع فرص جيدة:
           SOLUSDT, AVAXUSDT, NEARUSDT, SUIUSDT
        
        ✅ Tier 3 - فرص انعكاس وتنويع:
           ARBUSDT, APTUSDT, INJUSDT, LINKUSDT
        
        المبادئ:
        - تنويع عبر قطاعات مختلفة (L1, L2, DeFi)
        - حجم تداول يومي > $50M
        - القائمة السوداء الديناميكية تتولى استبعاد الأسوأ تلقائياً
        """
        return [
            # === Tier 1: سيولة عالية + أداء مستقر ===
            'ETHUSDT',    # ETH - ثاني أكبر عملة، اتجاهات واضحة
            'BNBUSDT',    # BNB - سيولة عالية، تقلب معتدل
            
            # === Tier 2: تقلب متوسط مع فرص جيدة ===
            'SOLUSDT',    # SOL - L1 سريع، حجم تداول ضخم
            'AVAXUSDT',   # AVAX - L1 مع تقلب جيد
            'NEARUSDT',   # NEAR - AI + L1، زخم قوي
            'SUIUSDT',    # SUI - L1 جديد، تقلب مناسب للتداول
            
            # === Tier 3: تنويع وفرص انعكاس ===
            'ARBUSDT',    # ARB - L2 رائد
            'APTUSDT',    # APT - L1 Move-based
            'INJUSDT',    # INJ - DeFi derivatives
            'LINKUSDT',   # LINK - Oracle leader
        ]
    
    def load_successful_coins_from_database(self) -> bool:
        """
        تحميل العملات الناجحة من قاعدة البيانات
        
        Returns:
            True إذا تم تحميل عملات بنجاح
        """
        try:
            # جلب العملات الناجحة من جدول successful_coins
            with self.db.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT symbol, strategy, score
                    FROM successful_coins 
                    WHERE is_active = 1 
                    ORDER BY score DESC
                    LIMIT 20
                """)
                rows = cursor.fetchall()
                
                if rows:
                    # تحديث قائمة العملات للتداول
                    symbols = [row[0] for row in rows]
                    self.config['symbols_pool'] = symbols
                    self.logger.info(f"✅ تم تحميل {len(symbols)} عملة ناجحة من قاعدة البيانات")
                    return True
                else:
                    self.logger.debug("⚠️ لا توجد عملات ناجحة في قاعدة البيانات")
                    return False
                    
        except Exception as e:
            self.logger.error(f"❌ خطأ في تحميل العملات من قاعدة البيانات: {e}")
            return False
    
    def load_successful_coins_from_file(self) -> bool:
        """
        تحميل العملات الناجحة من ملف JSON (احتياطي)
        
        Returns:
            True إذا تم تحميل عملات بنجاح
        """
        import json
        from pathlib import Path
        
        try:
            # البحث عن ملف العملات الناجحة
            file_path = Path(__file__).parent.parent.parent / 'data' / 'successful_coins.json'
            
            if not file_path.exists():
                # محاولة المسار البديل
                file_path = Path(__file__).parent.parent.parent / 'successful_coins.json'
            
            if file_path.exists():
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                if data and 'coins' in data:
                    symbols = [coin.get('symbol') for coin in data['coins'] if coin.get('symbol')]
                    if symbols:
                        self.config['symbols_pool'] = symbols
                        self.logger.info(f"✅ تم تحميل {len(symbols)} عملة من الملف")
                        return True
            
            # استخدام القائمة الافتراضية
            self.logger.debug("⚠️ استخدام القائمة الافتراضية للعملات")
            return len(self.config.get('symbols_pool', [])) > 0
            
        except Exception as e:
            self.logger.error(f"❌ خطأ في تحميل العملات من الملف: {e}")
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
                
                if len(open_positions) < effective_max:
                    new_entries = self._scan_for_entries()
                    for entry in new_entries:
                        result['actions'].append(entry)
                        result['new_positions'] += 1
            elif self.can_trade and (position_size_pct <= 0 or user_max_positions <= 0):
                self.logger.warning(f"⚠️ User {self.user_id}: trading enabled but settings incomplete (size={position_size_pct}%, max={user_max_positions})")
            
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
