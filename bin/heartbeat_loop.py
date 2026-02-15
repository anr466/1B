#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Heartbeat Loop - دالة إضافية لـ BackgroundTradingManager
يتم دمجها في الملف الرئيسي
"""

def _run_heartbeat_loop(self):
    """
    حلقة إرسال نبضات النظام (Heartbeat)
    
    يتم تشغيلها كـ thread منفصل
    ترسل نبضة كل 15 ثانية لإثبات أن النظام حي
    """
    logger = self.logger if hasattr(self, 'logger') else logging.getLogger(__name__)
    logger.info("💓 بدء حلقة Heartbeat")
    
    while not self.stop_event.is_set():
        try:
            # إرسال نبضة عبر StateManager
            if self.state_manager:
                self.state_manager.send_heartbeat()
                logger.debug("💓 تم إرسال heartbeat")
            
            # انتظار قبل النبضة التالية
            self.stop_event.wait(self.heartbeat_interval)
            
        except Exception as e:
            logger.error(f"❌ خطأ في حلقة Heartbeat: {e}")
            self.stop_event.wait(self.heartbeat_interval)
    
    logger.info("💓 توقفت حلقة Heartbeat")


def _update_group_b_activity(self, total_cycles: int, active_trades: int):
    """
    تحديث نشاط Group B في StateManager
    
    Args:
        total_cycles: إجمالي عدد الدورات
        active_trades: عدد الصفقات النشطة
    """
    if self.state_manager:
        try:
            self.state_manager.update_activity(
                'group_b',
                total_cycles=total_cycles,
                active_trades=active_trades,
                last_cycle=datetime.now().isoformat()
            )
        except Exception as e:
            logger = self.logger if hasattr(self, 'logger') else logging.getLogger(__name__)
            logger.warning(f"⚠️ فشل تحديث نشاط Group B: {e}")
