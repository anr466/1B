#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
نظام تتبع الخسارة اليومية (Daily Loss Tracker)
يضمن عدم تجاوز المستخدم للحد الأقصى من الخسارة في يوم واحد
"""

import logging
from datetime import datetime, date
from typing import Dict, Tuple, Optional

class DailyLossTracker:
    """
    نظام هجين لحد الخسارة اليومي:
    - النظام يضع الحدود الصارمة (5%-15%)
    - المستخدم يختار ضمن هذه الحدود
    """
    
    # 🔒 الحدود الصارمة من النظام (لا يمكن تجاوزها)
    SYSTEM_MIN_DAILY_LOSS = 5.0   # الحد الأدنى (حماية من المجازفة الزائدة)
    SYSTEM_MAX_DAILY_LOSS = 15.0  # الحد الأقصى (حماية من الخسارة الكبيرة)
    SYSTEM_DEFAULT_DAILY_LOSS = 10.0  # القيمة الافتراضية (التوازن المثالي)
    
    def __init__(self, db_manager, user_id: int, logger=None):
        """
        تهيئة نظام تتبع الخسارة اليومية
        
        Args:
            db_manager: مدير قاعدة البيانات
            user_id: معرف المستخدم
            logger: مسجل الأحداث (اختياري)
        """
        self.db = db_manager
        self.user_id = user_id
        self.logger = logger or logging.getLogger(__name__)
        
        # جلب إعداد المستخدم من قاعدة البيانات
        user_settings = self.db.get_trading_settings(user_id)
        user_limit = user_settings.get('max_daily_loss_pct', self.SYSTEM_DEFAULT_DAILY_LOSS)
        
        # ✅ التحقق من الحدود (النظام يفرض الحدود)
        self.max_daily_loss_pct = self._validate_and_adjust_limit(user_limit)
        
        self.logger.info(
            f"✅ تم تهيئة Daily Loss Tracker للمستخدم {user_id}: "
            f"{self.max_daily_loss_pct}% (الحد: {self.SYSTEM_MIN_DAILY_LOSS}%-{self.SYSTEM_MAX_DAILY_LOSS}%)"
        )
    
    def _validate_and_adjust_limit(self, user_limit: float) -> float:
        """
        التحقق من حد المستخدم وتعديله إذا تجاوز حدود النظام
        
        Args:
            user_limit: الحد المطلوب من المستخدم
            
        Returns:
            الحد المعدل ضمن حدود النظام
        """
        original_limit = user_limit
        
        # التحقق من الحد الأدنى
        if user_limit < self.SYSTEM_MIN_DAILY_LOSS:
            self.logger.warning(
                f"⚠️ الحد المطلوب ({user_limit}%) أقل من الحد الأدنى "
                f"({self.SYSTEM_MIN_DAILY_LOSS}%). تم التعديل تلقائياً."
            )
            user_limit = self.SYSTEM_MIN_DAILY_LOSS
        
        # التحقق من الحد الأقصى
        if user_limit > self.SYSTEM_MAX_DAILY_LOSS:
            self.logger.warning(
                f"⚠️ الحد المطلوب ({user_limit}%) أكبر من الحد الأقصى "
                f"({self.SYSTEM_MAX_DAILY_LOSS}%). تم التعديل تلقائياً."
            )
            user_limit = self.SYSTEM_MAX_DAILY_LOSS
        
        # إذا تم التعديل، تحديث قاعدة البيانات
        if user_limit != original_limit:
            try:
                self.db.update_trading_settings(
                    self.user_id, 
                    {'max_daily_loss_pct': user_limit}
                )
                self.logger.info(f"✅ تم تحديث حد الخسارة في قاعدة البيانات: {user_limit}%")
            except Exception as e:
                self.logger.error(f"خطأ في تحديث حد الخسارة: {e}")
        
        return user_limit
    
    def get_today_loss(self) -> float:
        """
        حساب إجمالي الخسارة لليوم الحالي
        
        Returns:
            إجمالي الخسارة (قيمة موجبة)
        """
        try:
            today = date.today()
            
            # جلب جميع الصفقات المغلقة اليوم
            query = """
                SELECT profit_loss 
                FROM user_trades 
                WHERE user_id = ? 
                AND DATE(exit_time) = ? 
                AND status = 'closed'
            """
            
            trades = self.db.execute_query(query, (self.user_id, today))
            
            if not trades:
                return 0.0
            
            # حساب إجمالي الخسارة فقط (الأرباح لا تُحتسب)
            total_loss = sum([
                abs(float(trade['profit_loss'])) 
                for trade in trades 
                if float(trade.get('profit_loss', 0)) < 0
            ])
            
            return total_loss
            
        except Exception as e:
            self.logger.error(f"خطأ في حساب خسارة اليوم: {e}")
            return 0.0
    
    def get_today_profit(self) -> float:
        """
        حساب إجمالي الربح لليوم الحالي (للمعلومات فقط)
        
        Returns:
            إجمالي الربح
        """
        try:
            today = date.today()
            
            query = """
                SELECT profit_loss 
                FROM user_trades 
                WHERE user_id = ? 
                AND DATE(exit_time) = ? 
                AND status = 'closed'
            """
            
            trades = self.db.execute_query(query, (self.user_id, today))
            
            if not trades:
                return 0.0
            
            # حساب إجمالي الربح فقط
            total_profit = sum([
                float(trade['profit_loss']) 
                for trade in trades 
                if float(trade.get('profit_loss', 0)) > 0
            ])
            
            return total_profit
            
        except Exception as e:
            self.logger.error(f"خطأ في حساب ربح اليوم: {e}")
            return 0.0
    
    def get_today_net_pnl(self) -> float:
        """
        حساب صافي الربح/الخسارة لليوم
        
        Returns:
            صافي PnL (موجب = ربح، سالب = خسارة)
        """
        profit = self.get_today_profit()
        loss = self.get_today_loss()
        return profit - loss
    
    def can_trade_today(self, capital: float) -> Tuple[bool, str]:
        """
        فحص ما إذا كان المستخدم يمكنه التداول اليوم
        
        Args:
            capital: رأس المال الحالي
            
        Returns:
            Tuple[bool, str]: (يمكن التداول, السبب/الرسالة)
        """
        try:
            if capital <= 0:
                return False, "⛔ رأس المال غير صالح"
            
            # حساب خسارة اليوم
            today_loss = self.get_today_loss()
            loss_pct = (today_loss / capital) * 100
            
            # ✅ فحص الحد اليومي
            if loss_pct >= self.max_daily_loss_pct:
                return False, (
                    f"⛔ وصلت لحد الخسارة اليومي {loss_pct:.2f}% "
                    f"(الحد الأقصى: {self.max_daily_loss_pct}%)\n"
                    f"💰 الخسارة اليوم: {today_loss:.2f} USDT\n"
                    f"⏰ يمكنك التداول غداً"
                )
            
            # حساب المتبقي
            remaining_pct = self.max_daily_loss_pct - loss_pct
            remaining_amount = (capital * remaining_pct) / 100
            
            # رسالة تحذيرية إذا اقترب من الحد
            warning = ""
            if loss_pct >= (self.max_daily_loss_pct * 0.8):  # 80% من الحد
                warning = f"\n⚠️ تحذير: اقتربت من الحد اليومي!"
            
            return True, (
                f"✅ يمكن التداول\n"
                f"📊 الخسارة اليوم: {loss_pct:.2f}% ({today_loss:.2f} USDT)\n"
                f"🎯 متبقي: {remaining_pct:.2f}% ({remaining_amount:.2f} USDT)"
                f"{warning}"
            )
            
        except Exception as e:
            self.logger.error(f"خطأ في فحص إمكانية التداول: {e}")
            # في حالة الخطأ، نسمح بالتداول (للحفاظ على التشغيل)
            return True, "⚠️ فحص الحد غير متاح - يمكن التداول"
    
    def get_daily_summary(self, capital: float) -> Dict:
        """
        الحصول على ملخص شامل لليوم
        
        Args:
            capital: رأس المال الحالي
            
        Returns:
            قاموس يحتوي على ملخص اليوم
        """
        try:
            today_loss = self.get_today_loss()
            today_profit = self.get_today_profit()
            net_pnl = today_profit - today_loss
            
            loss_pct = (today_loss / capital) * 100 if capital > 0 else 0
            profit_pct = (today_profit / capital) * 100 if capital > 0 else 0
            net_pnl_pct = (net_pnl / capital) * 100 if capital > 0 else 0
            
            remaining_pct = max(0, self.max_daily_loss_pct - loss_pct)
            remaining_amount = (capital * remaining_pct) / 100
            
            can_trade, message = self.can_trade_today(capital)
            
            return {
                'date': str(date.today()),
                'capital': capital,
                'today_loss': today_loss,
                'today_loss_pct': round(loss_pct, 2),
                'today_profit': today_profit,
                'today_profit_pct': round(profit_pct, 2),
                'net_pnl': net_pnl,
                'net_pnl_pct': round(net_pnl_pct, 2),
                'max_daily_loss_pct': self.max_daily_loss_pct,
                'remaining_loss_pct': round(remaining_pct, 2),
                'remaining_loss_amount': round(remaining_amount, 2),
                'can_trade': can_trade,
                'message': message,
                'system_limits': {
                    'min': self.SYSTEM_MIN_DAILY_LOSS,
                    'max': self.SYSTEM_MAX_DAILY_LOSS,
                    'default': self.SYSTEM_DEFAULT_DAILY_LOSS
                }
            }
            
        except Exception as e:
            self.logger.error(f"خطأ في الحصول على ملخص اليوم: {e}")
            return {
                'error': str(e),
                'can_trade': True,
                'message': 'خطأ في جلب البيانات'
            }
    
    def reset_daily_limit(self) -> bool:
        """
        إعادة تعيين الحد اليومي (تُستخدم عند بداية يوم جديد)
        
        Returns:
            True إذا تمت العملية بنجاح
        """
        try:
            self.logger.info(f"🔄 إعادة تعيين حد الخسارة اليومي للمستخدم {self.user_id}")
            # لا يوجد شيء للحذف - البيانات تبقى للتاريخ
            # سيتم الحساب تلقائياً لليوم الجديد
            return True
        except Exception as e:
            self.logger.error(f"خطأ في إعادة تعيين الحد اليومي: {e}")
            return False


# ===== وظائف مساعدة للاستخدام السريع =====

def check_can_trade(db_manager, user_id: int, capital: float, logger=None) -> Tuple[bool, str]:
    """
    وظيفة سريعة للتحقق من إمكانية التداول
    
    Args:
        db_manager: مدير قاعدة البيانات
        user_id: معرف المستخدم
        capital: رأس المال
        logger: مسجل الأحداث
        
    Returns:
        Tuple[bool, str]: (يمكن التداول, الرسالة)
    """
    tracker = DailyLossTracker(db_manager, user_id, logger)
    return tracker.can_trade_today(capital)


def get_daily_loss_summary(db_manager, user_id: int, capital: float, logger=None) -> Dict:
    """
    وظيفة سريعة للحصول على ملخص الخسارة اليومية
    
    Args:
        db_manager: مدير قاعدة البيانات
        user_id: معرف المستخدم
        capital: رأس المال
        logger: مسجل الأحداث
        
    Returns:
        قاموس يحتوي على الملخص
    """
    tracker = DailyLossTracker(db_manager, user_id, logger)
    return tracker.get_daily_summary(capital)
