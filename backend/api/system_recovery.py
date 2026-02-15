"""
نظام استرجاع الحالة (State Recovery System)
يضمن مزامنة الحالة الفعلية للنظام مع قاعدة البيانات
"""

import subprocess
from pathlib import Path
from datetime import datetime
import logging
import sys

# ✅ FIX: إضافة استيراد DatabaseManager
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from database.database_manager import DatabaseManager

logger = logging.getLogger(__name__)

class SystemStateRecovery:
    """
    نظام استرجاع ومزامنة حالة النظام
    """
    
    def __init__(self):
        self.db_path = Path(__file__).parent.parent.parent / 'database' / 'trading_database.db'
        self.db_manager = DatabaseManager()
    
    def check_and_sync_state(self):
        """
        فحص ومزامنة حالة النظام
        Returns: dict مع الحالة الفعلية
        """
        try:
            # 1. فحص العملية الفعلية
            actual_running = self._check_process_running()
            
            # 2. جلب حالة قاعدة البيانات
            db_state = self._get_db_state()
            
            # 3. المزامنة إذا كان هناك اختلاف
            if actual_running != db_state['is_running']:
                logger.warning(f"⚠️ اكتشاف عدم تطابق: Process={actual_running}, DB={db_state['is_running']}")
                self._sync_state(actual_running)
                return {
                    'synced': True,
                    'was_running': db_state['is_running'],
                    'is_running': actual_running,
                    'action': 'synced_to_reality'
                }
            
            return {
                'synced': False,
                'is_running': actual_running,
                'action': 'no_sync_needed'
            }
            
        except Exception as e:
            logger.error(f"❌ خطأ في فحص/مزامنة الحالة: {e}")
            return {
                'synced': False,
                'error': str(e),
                'action': 'error'
            }
    
    def _check_process_running(self):
        """فحص ما إذا كانت العملية تعمل فعلياً"""
        try:
            result = subprocess.run(
                ['pgrep', '-f', 'background_trading_manager.py'],
                capture_output=True,
                text=True,
                timeout=2
            )
            return result.returncode == 0 and bool(result.stdout.strip())
        except Exception as e:
            logger.warning(f"⚠️ فشل فحص العملية: {e}")
            return False
    
    def _get_db_state(self):
        """جلب حالة النظام من قاعدة البيانات"""
        try:
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            with self.db_manager.get_connection() as conn:
                row = conn.execute(
                    "SELECT status, is_running, last_update FROM system_status WHERE id = 1"
                ).fetchone()
            
            if row:
                return {
                    'status': row[0],
                    'is_running': bool(row[1]),
                    'last_update': row[2]
                }
            else:
                return {'status': 'unknown', 'is_running': False, 'last_update': None}
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب حالة DB: {e}")
            return {'status': 'error', 'is_running': False, 'last_update': None}
    
    def _sync_state(self, actual_running):
        """مزامنة حالة قاعدة البيانات مع الحالة الفعلية"""
        try:
            # ✅ FIX: استخدام DatabaseManager بدلاً من sqlite3.connect
            with self.db_manager.get_write_connection() as conn:
                if actual_running:
                    status = 'running'
                    trading_state = 'RUNNING'
                    is_running = 1
                    message = 'تم المزامنة: النظام يعمل'
                else:
                    status = 'stopped'
                    trading_state = 'STOPPED'
                    is_running = 0
                    message = 'تم المزامنة: النظام متوقف'
                
                conn.execute("""
                    UPDATE system_status 
                    SET status = ?, trading_state = ?, is_running = ?, last_update = datetime('now'), message = ?
                    WHERE id = 1
                """, (status, trading_state, is_running, message))
            
            logger.info(f"✅ تم مزامنة حالة DB: {status} (trading_state={trading_state})")
            
        except Exception as e:
            logger.error(f"❌ فشل مزامنة الحالة: {e}")
    
    def force_sync(self):
        """
        إجبار المزامنة (للاستخدام عند بدء الخادم)
        """
        logger.info("🔄 بدء المزامنة الإجبارية...")
        result = self.check_and_sync_state()
        logger.info(f"✅ نتيجة المزامنة: {result}")
        return result


# Singleton instance
_recovery_system = None

def get_recovery_system():
    """الحصول على نسخة واحدة من نظام الاسترجاع"""
    global _recovery_system
    if _recovery_system is None:
        _recovery_system = SystemStateRecovery()
    return _recovery_system
