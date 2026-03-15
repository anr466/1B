#!/usr/bin/env python3
"""
خدمة إشعارات التداول
ترسل إشعارات للمستخدمين عند أحداث التداول المهمة
مرتبطة بإعدادات الإشعارات في user_notification_settings
"""

import sys
import os
import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime

# إضافة مسار المشروع
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.database_manager import DatabaseManager

# استيراد خدمة Firebase
try:
    from utils.firebase_notification_service import FirebaseNotificationService
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False


class TradingNotificationService:
    """
    خدمة إشعارات التداول
    
    أنواع الإشعارات:
    - trade_opened: فتح صفقة جديدة
    - trade_closed: إغلاق صفقة (ربح/خسارة)
    - trailing_stop_activated: تفعيل Trailing Stop
    - daily_loss_limit: الوصول لحد الخسارة اليومي
    - balance_low: رصيد منخفض
    - system_alert: تنبيهات النظام
    """
    
    # أنواع الإشعارات المدعومة
    NOTIFICATION_TYPES = {
        'trade_opened': {
            'title': '📈 صفقة جديدة',
            'setting_key': 'trade_notifications',
            'priority': 'high'
        },
        'trade_closed_profit': {
            'title': '💰 صفقة رابحة!',
            'setting_key': 'trade_notifications',
            'priority': 'high'
        },
        'trade_closed_loss': {
            'title': '📉 صفقة خاسرة',
            'setting_key': 'trade_notifications',
            'priority': 'high'
        },
        'trailing_stop_activated': {
            'title': '🔒 Trailing Stop مُفعّل',
            'setting_key': 'trade_notifications',
            'priority': 'normal'
        },
        'daily_loss_limit': {
            'title': '⚠️ حد الخسارة اليومي',
            'setting_key': 'alert_notifications',
            'priority': 'high'
        },
        'balance_low': {
            'title': '⚠️ رصيد منخفض',
            'setting_key': 'alert_notifications',
            'priority': 'high'
        },
        'system_alert': {
            'title': '🔔 تنبيه النظام',
            'setting_key': 'system_notifications',
            'priority': 'normal'
        },
        'market_update': {
            'title': '📊 تحديث السوق',
            'setting_key': 'market_notifications',
            'priority': 'low'
        }
    }
    
    def __init__(self, db_manager=None):
        """تهيئة خدمة الإشعارات
        
        Args:
            db_manager: مدير قاعدة البيانات (اختياري - سيتم إنشاؤه إذا لم يُمرر)
        """
        self.logger = logging.getLogger(__name__)
        self.db_manager = db_manager if db_manager else DatabaseManager()
        
        # تهيئة Firebase
        if FIREBASE_AVAILABLE:
            try:
                self.firebase_service = FirebaseNotificationService()
                self.logger.info("✅ Trading Notification Service مُفعّل")
            except Exception as e:
                self.firebase_service = None
                self.logger.warning(f"⚠️ Firebase غير متاح: {e}")
        else:
            self.firebase_service = None
            self.logger.warning("⚠️ Firebase غير متوفر")
    
    def is_available(self) -> bool:
        """فحص توفر الخدمة"""
        return self.firebase_service is not None and self.firebase_service.is_available()
    
    def get_user_notification_settings(self, user_id: int) -> Dict[str, bool]:
        """
        جلب إعدادات الإشعارات للمستخدم
        
        Returns:
            dict مع إعدادات الإشعارات
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT settings_data,
                           push_enabled,
                           trade_notifications,
                           price_alerts,
                           system_notifications,
                           notify_new_deal,
                           notify_deal_profit,
                           notify_deal_loss,
                           notify_daily_profit,
                           notify_daily_loss,
                           notify_low_balance
                    FROM user_notification_settings
                    WHERE user_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (user_id,))

                row = cursor.fetchone()
                default_settings = {
                    'push_enabled': True,
                    'trade_notifications': True,
                    'price_alerts': True,
                    'system_notifications': True,
                    'notify_new_deal': True,
                    'notify_deal_profit': True,
                    'notify_deal_loss': True,
                    'notify_daily_profit': True,
                    'notify_daily_loss': True,
                    'notify_low_balance': True,
                    'daily_summary': True,
                    'cumulative_loss_alert_enabled': True,
                    'cumulative_loss_threshold_usd': 100.0,
                    'end_of_day_report_enabled': True,
                    'end_of_day_report_time': '23:00',
                }

                if not row:
                    return default_settings

                settings_data = row[0]
                if settings_data:
                    try:
                        parsed = json.loads(settings_data) if isinstance(settings_data, str) else settings_data
                        default_settings.update({
                            'push_enabled': bool(parsed.get('pushEnabled', default_settings['push_enabled'])),
                            'trade_notifications': bool(parsed.get('tradeNotifications', default_settings['trade_notifications'])),
                            'price_alerts': bool(parsed.get('priceAlerts', default_settings['price_alerts'])),
                            'system_notifications': bool(parsed.get('notifySystemStatus', default_settings['system_notifications'])),
                            'notify_new_deal': bool(parsed.get('notifyNewDeal', default_settings['notify_new_deal'])),
                            'notify_deal_profit': bool(parsed.get('notifyDealProfit', default_settings['notify_deal_profit'])),
                            'notify_deal_loss': bool(parsed.get('notifyDealLoss', default_settings['notify_deal_loss'])),
                            'notify_daily_profit': bool(parsed.get('notifyDailyProfit', default_settings['notify_daily_profit'])),
                            'notify_daily_loss': bool(parsed.get('notifyDailyLoss', default_settings['notify_daily_loss'])),
                            'notify_low_balance': bool(parsed.get('notifyLowBalance', default_settings['notify_low_balance'])),
                            'daily_summary': bool(parsed.get('dailySummary', default_settings['daily_summary'])),
                            'cumulative_loss_alert_enabled': bool(parsed.get('cumulativeLossAlertEnabled', default_settings['cumulative_loss_alert_enabled'])),
                            'cumulative_loss_threshold_usd': float(parsed.get('cumulativeLossThresholdUsd', default_settings['cumulative_loss_threshold_usd'])),
                            'end_of_day_report_enabled': bool(parsed.get('endOfDayReportEnabled', default_settings['end_of_day_report_enabled'])),
                            'end_of_day_report_time': str(parsed.get('endOfDayReportTime', default_settings['end_of_day_report_time'])),
                        })
                        return default_settings
                    except Exception as parse_error:
                        self.logger.warning(f"فشل تحليل settings_data للمستخدم {user_id}: {parse_error}")

                # fallback للأعمدة القديمة
                return {
                    'push_enabled': bool(row[1]),
                    'trade_notifications': bool(row[2]),
                    'price_alerts': bool(row[3]),
                    'system_notifications': bool(row[4]),
                    'notify_new_deal': bool(row[5]),
                    'notify_deal_profit': bool(row[6]),
                    'notify_deal_loss': bool(row[7]),
                    'notify_daily_profit': bool(row[8]),
                    'notify_daily_loss': bool(row[9]),
                    'notify_low_balance': bool(row[10]),
                    'daily_summary': True,
                    'cumulative_loss_alert_enabled': bool(row[9]),
                    'cumulative_loss_threshold_usd': 100.0,
                    'end_of_day_report_enabled': True,
                    'end_of_day_report_time': '23:00',
                }
                    
        except Exception as e:
            self.logger.error(f"خطأ في جلب إعدادات الإشعارات: {e}")
            return {'push_enabled': True}  # افتراضي
    
    def is_quiet_hours(self, settings: Dict) -> bool:
        """فحص إذا كنا في ساعات الهدوء"""
        if not settings.get('quiet_hours_enabled'):
            return False
        
        try:
            now = datetime.now().time()
            start = datetime.strptime(settings.get('quiet_hours_start', '22:00'), '%H:%M').time()
            end = datetime.strptime(settings.get('quiet_hours_end', '08:00'), '%H:%M').time()
            
            if start <= end:
                return start <= now <= end
            else:
                # ساعات الهدوء تمتد لليوم التالي
                return now >= start or now <= end
                
        except Exception:
            return False
    
    def should_send_notification(self, user_id: int, notification_type: str) -> bool:
        """
        فحص إذا يجب إرسال الإشعار للمستخدم بناءً على إعداداته ومرحلته
        
        Args:
            user_id: معرف المستخدم
            notification_type: نوع الإشعار
            
        Returns:
            True إذا يجب الإرسال
        """
        # إشعارات التداول تتطلب أن يكون المستخدم فعّل التداول
        trading_notifications = [
            'trade_opened', 'trade_closed_profit', 'trade_closed_loss',
            'trailing_stop_activated', 'daily_loss_limit', 'daily_profit',
            'balance_low', 'price_alert', 'market_update'
        ]
        
        if notification_type in trading_notifications:
            # فحص: هل المستخدم فعّل التداول؟
            try:
                from backend.services.user_onboarding_service import get_onboarding_service
                onboarding = get_onboarding_service()
                if not onboarding.can_receive_trading_notifications(user_id):
                    return False
            except Exception as e:
                self.logger.warning(f"خطأ في فحص حالة المستخدم: {e}")
        
        settings = self.get_user_notification_settings(user_id)
        
        # فحص إذا الإشعارات مفعلة
        if not settings.get('push_enabled', True):
            return False
        
        # ربط أنواع الإشعارات بإعدادات المستخدم
        notification_settings_map = {
            'trade_opened': 'notify_new_deal',
            'trade_closed_profit': 'notify_deal_profit',
            'trade_closed_loss': 'notify_deal_loss',
            'trailing_stop_activated': 'trade_notifications',
            'daily_loss_limit': 'notify_daily_loss',
            'daily_profit': 'notify_daily_profit',
            'balance_low': 'notify_low_balance',
            'system_alert': 'system_notifications',
            'price_alert': 'price_alerts',
            'market_update': 'trade_notifications'
        }
        
        # جلب مفتاح الإعداد المناسب
        setting_key = notification_settings_map.get(notification_type, 'system_notifications')
        
        return settings.get(setting_key, True)

    def _get_today_cumulative_loss(self, user_id: int) -> float:
        """إجمالي الخسائر المغلقة اليوم (موجب كقيمة خسارة)."""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(ABS(profit_loss)), 0)
                    FROM active_positions
                    WHERE user_id = ?
                      AND DATE(COALESCE(closed_at, updated_at)) = DATE('now')
                      AND is_active = 0
                      AND profit_loss < 0
                    """,
                    (user_id,),
                )
                value = cursor.fetchone()[0]
                return float(value or 0.0)
        except Exception as e:
            self.logger.debug(f"خطأ في حساب الخسارة اليومية التراكمية: {e}")
            return 0.0
    
    def is_duplicate_notification(self, user_id: int, notification_type: str, 
                                   unique_key: str, cooldown_minutes: int = 5) -> bool:
        """
        ✅ فحص إذا الإشعار مكرر - منع إرسال نفس الإشعار مرتين
        
        Args:
            user_id: معرف المستخدم
            notification_type: نوع الإشعار
            unique_key: مفتاح فريد (مثل symbol أو trade_id)
            cooldown_minutes: فترة الانتظار قبل إرسال إشعار مشابه (بالدقائق)
            
        Returns:
            True إذا كان الإشعار مكرراً ويجب تجاهله
        """
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # فحص إذا أُرسل إشعار مشابه في الفترة المحددة
                cooldown = max(1, int(cooldown_minutes))
                cursor.execute("""
                    SELECT COUNT(*) FROM notification_history
                    WHERE user_id = ? 
                    AND type = ?
                    AND data LIKE ?
                    AND created_at > (CURRENT_TIMESTAMP - (? * INTERVAL '1 minute'))
                """, (user_id, notification_type, f'%{unique_key}%', cooldown))
                
                count = cursor.fetchone()[0]
                
                if count > 0:
                    self.logger.debug(f"⏳ تجاهل إشعار مكرر [{notification_type}] لـ {unique_key}")
                    return True
                    
                return False
                
        except Exception as e:
            self.logger.debug(f"خطأ في فحص تكرار الإشعار: {e}")
            return False  # في حالة الخطأ، نسمح بالإرسال
    
    def save_notification_to_history(self, user_id: int, notification_type: str, 
                                     title: str, body: str, data: Dict = None) -> bool:
        """حفظ الإشعار في السجل"""
        try:
            with self.db_manager.get_write_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO notification_history 
                    (user_id, type, title, message, data, status, created_at)
                    VALUES (?, ?, ?, ?, ?, 'sent', CURRENT_TIMESTAMP)
                """, (user_id, notification_type, title, body, str(data or {})))
                return True
                
        except Exception as e:
            self.logger.error(f"خطأ في حفظ الإشعار: {e}")
            return False
    
    # ═══════════════════════════════════════════════════════════════
    #                    دوال إرسال الإشعارات
    # ═══════════════════════════════════════════════════════════════
    
    def notify_trade_opened(self, user_id: int, symbol: str, position_type: str, 
                           entry_price: float, quantity: float, trade_id: int = None) -> bool:
        """
        إشعار فتح صفقة جديدة
        
        Args:
            user_id: معرف المستخدم
            symbol: رمز العملة (مثل BTCUSDT)
            position_type: نوع الصفقة (LONG/SHORT)
            entry_price: سعر الدخول
            quantity: الكمية
            trade_id: معرف الصفقة (لمنع التكرار)
        """
        if not self.should_send_notification(user_id, 'trade_opened'):
            return False
        
        # ✅ منع التكرار: إشعار فتح صفقة واحد فقط لكل trade_id أو symbol+price
        unique_key = str(trade_id) if trade_id else f"{symbol}_{entry_price}"
        if self.is_duplicate_notification(user_id, 'trade_opened', unique_key, cooldown_minutes=60):
            return False
        
        title = "📈 صفقة جديدة"
        body = f"تم فتح صفقة {position_type} على {symbol}\n💵 السعر: {entry_price:.4f}\n📊 الكمية: {quantity:.4f}"
        
        data = {
            'type': 'trade_opened',
            'symbol': symbol,
            'position_type': position_type,
            'entry_price': entry_price,
            'quantity': quantity,
            'trade_id': trade_id
        }
        
        # حفظ في السجل
        self.save_notification_to_history(user_id, 'trade_opened', title, body, data)
        
        # إرسال عبر Firebase
        if self.firebase_service:
            return self.firebase_service.send_to_user(user_id, title, body, data)
        
        return True
    
    def notify_trade_closed(self, user_id: int, symbol: str, profit_loss: float, 
                           profit_pct: float, exit_reason: str, trade_id: int = None) -> bool:
        """
        إشعار إغلاق صفقة
        
        Args:
            user_id: معرف المستخدم
            symbol: رمز العملة
            profit_loss: الربح/الخسارة بالـ USDT
            profit_pct: النسبة المئوية
            exit_reason: سبب الإغلاق (take_profit, stop_loss, trailing_stop, manual)
            trade_id: معرف الصفقة (لمنع التكرار)
        """
        is_profit = profit_loss >= 0
        notification_type = 'trade_closed_profit' if is_profit else 'trade_closed_loss'
        
        if not self.should_send_notification(user_id, notification_type):
            return False
        
        # ✅ منع التكرار: إشعار إغلاق واحد فقط لكل صفقة
        unique_key = str(trade_id) if trade_id else f"{symbol}_{profit_loss:.2f}"
        if self.is_duplicate_notification(user_id, notification_type, unique_key, cooldown_minutes=60):
            return False
        
        if is_profit:
            title = "💰 صفقة رابحة!"
            emoji = "🟢"
        else:
            title = "📉 صفقة خاسرة"
            emoji = "🔴"
        
        # ترجمة سبب الإغلاق
        exit_reasons = {
            'take_profit': 'جني الأرباح',
            'stop_loss': 'وقف الخسارة',
            'trailing_stop': 'Trailing Stop',
            'manual': 'إغلاق يدوي',
            'signal': 'إشارة بيع'
        }
        reason_text = exit_reasons.get(exit_reason, exit_reason)
        
        body = f"{emoji} {symbol}\n💵 {profit_loss:+.2f} USDT ({profit_pct:+.2f}%)\n📌 السبب: {reason_text}"
        
        data = {
            'type': notification_type,
            'symbol': symbol,
            'profit_loss': profit_loss,
            'profit_pct': profit_pct,
            'exit_reason': exit_reason,
            'trade_id': trade_id
        }
        
        self.save_notification_to_history(user_id, notification_type, title, body, data)
        
        if self.firebase_service:
            sent = self.firebase_service.send_to_user(user_id, title, body, data)
        else:
            sent = True

        # ✅ تنبيه الخسائر التراكمية اليومية (يتحكم به المستخدم من الإعدادات)
        if not is_profit:
            settings = self.get_user_notification_settings(user_id)
            if settings.get('cumulative_loss_alert_enabled', True):
                threshold = float(settings.get('cumulative_loss_threshold_usd', 100.0) or 100.0)
                cumulative_loss = self._get_today_cumulative_loss(user_id)
                if cumulative_loss >= threshold:
                    self.notify_daily_loss_limit(
                        user_id=user_id,
                        daily_loss=cumulative_loss,
                        daily_limit=threshold,
                    )

        return sent
    
    def notify_trailing_stop_activated(self, user_id: int, symbol: str, 
                                       new_stop_price: float, current_price: float) -> bool:
        """إشعار تفعيل Trailing Stop - مع منع التكرار"""
        if not self.should_send_notification(user_id, 'trailing_stop_activated'):
            return False
        
        # ✅ منع التكرار: إشعار واحد فقط لكل صفقة (لكل symbol)
        # فحص إذا أُرسل إشعار لهذا الـ symbol في آخر 30 دقيقة
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM notification_history
                    WHERE user_id = ? 
                    AND type = 'trailing_stop_activated'
                    AND data LIKE ?
                    AND created_at > (CURRENT_TIMESTAMP - INTERVAL '30 minutes')
                """, (user_id, f'%{symbol}%'))
                
                recent_count = cursor.fetchone()[0]
                if recent_count > 0:
                    self.logger.debug(f"⏳ تجاهل إشعار Trailing Stop لـ {symbol} - أُرسل مؤخراً")
                    return False
        except Exception as e:
            self.logger.debug(f"خطأ في فحص تكرار Trailing Stop: {e}")
        
        title = "🔒 Trailing Stop مُفعّل"
        body = f"{symbol}\n📊 السعر الحالي: {current_price:.4f}\n🛡️ وقف الخسارة الجديد: {new_stop_price:.4f}"
        
        data = {
            'type': 'trailing_stop_activated',
            'symbol': symbol,
            'new_stop_price': new_stop_price,
            'current_price': current_price
        }

        # حفظ في السجل فقط (بدون إشعار Push)
        self.save_notification_to_history(user_id, 'trailing_stop_activated', title, body, data)
        
        # لا يتم إرسال إشعار Push - النظام يتعامل تلقائياً
        return True
    
    def notify_daily_loss_limit(self, user_id: int, daily_loss: float, 
                                daily_limit: float) -> bool:
        """إشعار الوصول لحد الخسارة اليومي - يعمل تلقائياً بدون إشعار المستخدم"""
        if not self.should_send_notification(user_id, 'daily_loss_limit'):
            return False
        
        title = "⚠️ حد الخسارة اليومي"
        body = f"تم إيقاف التداول مؤقتاً\n📉 الخسارة اليومية: {daily_loss:.2f} USDT\n🛑 الحد المسموح: {daily_limit:.2f} USDT\n\nسيُستأنف التداول غداً تلقائياً"
        
        data = {
            'type': 'daily_loss_limit',
            'daily_loss': daily_loss,
            'daily_limit': daily_limit
        }

        # حفظ في السجل فقط (بدون إشعار Push)
        self.save_notification_to_history(user_id, 'daily_loss_limit', title, body, data)
        
        # لا يتم إرسال إشعار Push - النظام يتعامل تلقائياً
        return True
    
    def notify_balance_low(self, user_id: int, current_balance: float, 
                          min_required: float) -> bool:
        """إشعار رصيد منخفض - يعمل تلقائياً بدون إشعار المستخدم"""
        if not self.should_send_notification(user_id, 'balance_low'):
            return False
        
        title = "⚠️ رصيد منخفض"
        body = f"رصيدك الحالي: {current_balance:.2f} USDT\n💡 الحد الأدنى للتداول: {min_required:.2f} USDT\n\nيرجى إيداع المزيد لمتابعة التداول"
        
        data = {
            'type': 'balance_low',
            'current_balance': current_balance,
            'min_required': min_required
        }

        # حفظ في السجل فقط (بدون إشعار Push)
        self.save_notification_to_history(user_id, 'balance_low', title, body, data)
        
        # لا يتم إرسال إشعار Push - النظام يتعامل تلقائياً
        return True
    
    def notify_low_free_balance_simple(self, user_id: int, free_balance: float, 
                                       open_positions: int = 0) -> bool:
        """
        إشعار رصيد حر منخفض - مع توضيح السبب
        
        Args:
            user_id: معرف المستخدم
            free_balance: الرصيد الحر المتاح
            open_positions: عدد الصفقات المفتوحة
        """
        if not self.should_send_notification(user_id, 'balance_low'):
            return False
        
        title = "💡 الرصيد الحر منخفض"
        
        # ✅ رسالة واضحة توضح السبب والحالة
        if open_positions > 0:
            body = (
                f"💰 الرصيد الحر: {free_balance:.2f} USDT\n"
                f"📊 صفقات مفتوحة: {open_positions}\n\n"
                f"📌 السبب: جزء من رصيدك محجوز في الصفقات المفتوحة\n"
                f"✅ الإجراء: النظام يراقب صفقاتك الحالية\n"
                f"⏳ سيُستأنف فتح صفقات جديدة عند توفر رصيد كافٍ"
            )
        else:
            body = (
                f"💰 الرصيد الحر: {free_balance:.2f} USDT\n\n"
                f"📌 السبب: الرصيد أقل من الحد الأدنى للتداول\n"
                f"💡 الحل: إيداع المزيد في Binance لمتابعة التداول"
            )
        
        data = {
            'type': 'balance_low',
            'free_balance': free_balance,
            'open_positions': open_positions
        }
        
        # حفظ في السجل فقط (بدون إشعار Push)
        self.save_notification_to_history(user_id, 'balance_low', title, body, data)
        
        # لا يتم إرسال إشعار Push - النظام يتعامل تلقائياً
        return True
    
    def notify_system_alert(self, user_id: int, message: str, 
                           alert_type: str = 'info') -> bool:
        """إشعار تنبيه النظام"""
        if not self.should_send_notification(user_id, 'system_alert'):
            return False
        
        icons = {
            'info': 'ℹ️',
            'warning': '⚠️',
            'error': '❌',
            'success': '✅'
        }
        icon = icons.get(alert_type, 'ℹ️')
        
        title = f"{icon} تنبيه النظام"
        body = message
        
        data = {
            'type': 'system_alert',
            'alert_type': alert_type,
            'message': message
        }

        # حفظ في السجل فقط (بدون إشعار Push)
        self.save_notification_to_history(user_id, 'system_alert', title, body, data)
        
        # لا يتم إرسال إشعار Push - النظام يتعامل تلقائياً
        return True


# Singleton instance
_trading_notification_service = None

def get_trading_notification_service() -> TradingNotificationService:
    """الحصول على instance واحد من الخدمة"""
    global _trading_notification_service
    if _trading_notification_service is None:
        _trading_notification_service = TradingNotificationService()
    return _trading_notification_service


if __name__ == "__main__":
    # اختبار الخدمة
    service = TradingNotificationService()
    print(f"✅ الخدمة متاحة: {service.is_available()}")
    
    # اختبار إعدادات المستخدم
    settings = service.get_user_notification_settings(1)
    print(f"📌 إعدادات المستخدم 1: {settings}")
