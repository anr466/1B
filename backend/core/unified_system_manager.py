#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 Unified System Manager - مدير النظام الموحد
=================================================

مدير شامل للنظام الخلفي مع:
- Transaction safety (rollback on failure)
- Health checking
- Process management
- File locking (prevent race conditions)
- Single Source of Truth

Author: System Unification Team  
Date: 2026-02-01
"""

import os
import sys
import signal
import subprocess
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# Optional: psutil for advanced process checking
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("⚠️ psutil not installed - using basic process checking")

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.state_manager import StateManager


class SystemAlreadyRunningError(Exception):
    """النظام يعمل بالفعل"""
    pass


class SystemNotRunningError(Exception):
    """النظام ليس يعمل"""
    pass


class FileLock:
    """File-based lock لمنع race conditions"""
    
    def __init__(self, lock_file: Path):
        self.lock_file = lock_file
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        self.fd = None
    
    def __enter__(self):
        import fcntl
        self.fd = open(self.lock_file, 'w')
        try:
            fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            raise SystemAlreadyRunningError("عملية أخرى تقوم بالتشغيل حالياً")
        return self
    
    def __exit__(self, *args):
        if self.fd:
            import fcntl
            fcntl.flock(self.fd, fcntl.LOCK_UN)
            self.fd.close()


class UnifiedSystemManager:
    """
    مدير النظام الموحد - Single Point of Control
    
    Features:
    - Transaction safety with rollback
    - Health checking and monitoring
    - Process management
    - Zombie cleanup
    - State reconciliation
    """
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        self.state_manager = StateManager()
        self.pid_file = Path('tmp/system.pid')
        self.lock_file = Path('tmp/system.lock')
        
        # Ensure directories
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)
    
    def start_system(self, user: Optional[str] = None) -> Dict[str, Any]:
        """
        بدء النظام مع transaction safety
        
        Args:
            user: المستخدم الذي قام بالتشغيل
        
        Returns:
            dict: معلومات النظام المُشغّل
        
        Raises:
            SystemAlreadyRunningError: إذا كان النظام يعمل
        """
        # File lock لمنع race conditions
        with FileLock(self.lock_file):
            # Check if already running
            if self.is_running():
                pid = self.get_pid()
                raise SystemAlreadyRunningError(f"النظام يعمل بالفعل (PID: {pid})")
            
            # Save old state for rollback
            old_state = self.state_manager.read_state()
            
            try:
                # Step 1: Update state to 'starting'
                self.state_manager.write_state({
                    'status': 'starting',
                    'is_running': False,
                    'message': 'جاري بدء النظام...',
                    'pid': None
                }, user=user)
                
                # Step 1.5: ✅ تشغيل بيانات المراقبة (بدء نظيف)
                print("✅ تصفير بيانات المراقبة من التشغيل السابق...")
                self.state_manager.reset_monitoring_data()
                
                # Step 2: Kill any previous processes
                self._cleanup_previous_processes()
                
                # Step 3: Start the background process
                process = self._start_background_process()
                
                # Step 4: Save PID
                self._write_pid(process.pid)
                
                # Step 5: Update state to 'running'
                self.state_manager.write_state({
                    'status': 'running',
                    'is_running': True,
                    'pid': process.pid,
                    'started_at': datetime.now().isoformat(),
                    'message': 'النظام يعمل'
                }, user=user)
                
                return {
                    'success': True,
                    'message': 'تم بدء النظام بنجاح',
                    'pid': process.pid,
                    'status': 'running',
                    'uptime': 0
                }
                
            except Exception as e:
                # Rollback on failure
                print(f"❌ فشل بدء النظام: {e}")
                self.state_manager.write_state(old_state, user='system')
                self._clear_pid()
                raise
    
    def stop_system(self, user: Optional[str] = None) -> Dict[str, Any]:
        """
        إيقاف النظام مع cleanup كامل
        
        Args:
            user: المستخدم الذي قام بالإيقاف
        
        Returns:
            dict: تأكيد الإيقاف
        
        Raises:
            SystemNotRunningError: إذا كان النظام متوقف
        """
        with FileLock(self.lock_file):
            if not self.is_running():
                raise SystemNotRunningError("النظام ليس يعمل")
            
            try:
                # Get PID
                pid = self.get_pid()
                
                # Update state to 'stopping'
                self.state_manager.write_state({
                    'status': 'stopping',
                    'message': 'جاري إيقاف النظام...'
                }, user=user)
                
                # Kill process
                self._kill_process(pid)
                
                # Cleanup zombies
                self._cleanup_zombies()
                
                # Clear PID
                self._clear_pid()
                
                # Update state to 'stopped'
                self.state_manager.write_state({
                    'status': 'stopped',
                    'is_running': False,
                    'pid': None,
                    'started_at': None,
                    'uptime': 0,
                    'message': 'النظام متوقف'
                }, user=user)
                
                return {
                    'success': True,
                    'message': 'تم إيقاف النظام بنجاح'
                }
                
            except Exception as e:
                print(f"❌ فشل إيقاف النظام: {e}")
                raise
    
    def get_status(self) -> Dict[str, Any]:
        """
        جلب حالة النظام مع health check
        
        Returns:
            dict: الحالة الحالية
        """
        # Reconcile state first
        self.reconcile_state()
        
        # Get current state
        state = self.state_manager.read_state()
        
        # Calculate uptime if running
        if state.get('is_running') and state.get('started_at'):
            try:
                started = datetime.fromisoformat(state['started_at'])
                uptime = int((datetime.now() - started).total_seconds())
                state['uptime'] = uptime
                state['uptime_formatted'] = self._format_uptime(uptime)
            except Exception:
                state['uptime'] = 0
                state['uptime_formatted'] = '0 ثانية'
        
        return {
            'success': True,
            'data': state
        }
    
    def is_running(self) -> bool:
        """
        التحقق من أن النظام يعمل (مع health check)
        
        Returns:
            bool: True if running
        """
        pid = self.get_pid()
        if not pid:
            return False
        
        return self._is_process_alive(pid)
    
    def get_pid(self) -> Optional[int]:
        """جلب PID من الملف"""
        if not self.pid_file.exists():
            return None
        
        try:
            with open(self.pid_file, 'r') as f:
                return int(f.read().strip())
        except Exception:
            return None
    
    def _sync_db_status(self, status: str, is_running: bool, message: str = ''):
        """مزامنة حالة النظام مع جدول system_status في DB"""
        try:
            from database.database_manager import DatabaseManager
            db = DatabaseManager()
            with db.get_write_connection() as conn:
                conn.execute("""
                    UPDATE system_status 
                    SET status = %s, is_running = %s, last_update = CURRENT_TIMESTAMP, message = %s
                    WHERE id = 1
                """, (status, 1 if is_running else 0, message))
        except Exception as e:
            print(f"⚠️ فشل مزامنة DB status: {e}")
    
    def reconcile_state(self):
        """
        مطابقة الحالة مع الواقع (State Reconciliation)
        
        يستخدم عند:
        - بدء الخادم
        - Health check
        - جلب الحالة
        
        ✅ FIX: يمزامن JSON + DB معاً
        """
        state = self.state_manager.read_state()
        pid = state.get('pid')
        
        if pid and not self._is_process_alive(pid):
            # Process dead but state says running
            print(f"⚠️ العملية {pid} ماتت - تحديث الحالة")
            
            try:
                from backend.utils.error_logger import ErrorLogger, ErrorLevel, ErrorSource
                error_logger = ErrorLogger()
                error_logger.log_error(
                    level=ErrorLevel.CRITICAL,
                    source=ErrorSource.BACKGROUND,
                    message=f'النظام الخلفي توقف بشكل غير متوقع',
                    details=f'PID {pid} مات بشكل غير متوقع. يجب فحص السجلات.',
                    include_traceback=False
                )
            except Exception as e:
                print(f"⚠️ فشل تسجيل الخطأ: {e}")
            
            self.state_manager.write_state({
                'status': 'stopped',
                'is_running': False,
                'pid': None,
                'started_at': None,
                'uptime': 0,
                'message': 'العملية توقفت بشكل غير متوقع'
            }, user='system')
            self._clear_pid()
            # ✅ FIX: مزامنة DB أيضاً
            self._sync_db_status('stopped', False, 'العملية توقفت بشكل غير متوقع')
            
        elif not pid and state.get('is_running'):
            # No PID but state says running — check heartbeat before resetting
            heartbeat_seconds = self.state_manager.get_seconds_since_heartbeat()
            if heartbeat_seconds is not None and heartbeat_seconds < 60:
                # Heartbeat is fresh — system IS running, just missing PID
                print(f"ℹ️ لا يوجد PID لكن النبضات حية ({heartbeat_seconds}s) - النظام يعمل")
            else:
                # No PID AND no fresh heartbeat — truly stopped
                print(f"⚠️ لا يوجد PID ولا نبضات حية - تحديث الحالة إلى stopped")
                
                try:
                    from backend.utils.error_logger import ErrorLogger, ErrorLevel, ErrorSource
                    error_logger = ErrorLogger()
                    error_logger.log_error(
                        level=ErrorLevel.ERROR,
                        source=ErrorSource.SYSTEM,
                        message='حالة غير متسقة: لا يوجد PID ولا نبضات حية',
                        details='النظام يعتقد أنه يعمل لكن لا توجد عملية ولا نبضات',
                        include_traceback=False
                    )
                except Exception as e:
                    print(f"⚠️ فشل تسجيل الخطأ: {e}")
                self.state_manager.write_state({
                    'status': 'stopped',
                    'is_running': False,
                    'message': 'تم تصحيح الحالة'
                }, user='system')
        
        elif not state.get('is_running'):
            # State says stopped — but check if heartbeat is fresh (system may actually be running)
            heartbeat_seconds = self.state_manager.get_seconds_since_heartbeat()
            if heartbeat_seconds is not None and heartbeat_seconds < 60:
                # Heartbeat proves system IS running — correct the state
                print(f"🔄 الحالة stopped لكن النبضات حية ({heartbeat_seconds}s) - تصحيح إلى running")
                self.state_manager.write_state({
                    'status': 'running',
                    'is_running': True,
                    'message': 'تم تصحيح الحالة - النظام يعمل (كُشف عبر النبضات)'
                }, user='system')
    
    # ==================== Helper Methods ====================
    
    def _start_background_process(self) -> subprocess.Popen:
        """بدء عملية background_trading_manager"""
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.project_root)
        
        process = subprocess.Popen(
            [sys.executable, str(self.project_root / 'bin' / 'background_trading_manager.py'), '--start'],
            cwd=str(self.project_root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env
        )
        
        # انتظار قصير للتأكد من البدء
        time.sleep(0.5)
        
        return process
    
    def _is_process_alive(self, pid: int) -> bool:
        """
        التحقق من أن العملية حية وتعمل
        
        Args:
            pid: رقم العملية
        
        Returns:
            bool: True if alive and healthy
        """
        if HAS_PSUTIL:
            # Advanced checking with psutil
            try:
                process = psutil.Process(pid)
                
                # Check if it's our process
                cmdline = ' '.join(process.cmdline())
                if 'background_trading_manager' not in cmdline:
                    return False
                
                # Check if process is running (not zombie)
                if process.status() == psutil.STATUS_ZOMBIE:
                    return False
                
                return True
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return False
        else:
            # Basic checking without psutil
            try:
                # Check if process exists using os.kill with signal 0
                os.kill(pid, 0)
                
                # Check if it's our process using ps
                result = subprocess.run(
                    ['ps', '-p', str(pid), '-o', 'command='],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                
                if result.returncode != 0:
                    return False
                
                # Check if it's our process
                if 'background_trading_manager' not in result.stdout:
                    return False
                
                return True
                
            except (OSError, subprocess.TimeoutExpired):
                return False
    
    def _kill_process(self, pid: int):
        """إيقاف عملية بشكل آمن"""
        if HAS_PSUTIL:
            # Advanced killing with psutil
            try:
                process = psutil.Process(pid)
                process.terminate()
                try:
                    process.wait(timeout=5)
                except psutil.TimeoutExpired:
                    process.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        else:
            # Basic killing without psutil
            try:
                # Try graceful shutdown first (SIGTERM)
                os.kill(pid, signal.SIGTERM)
                
                # Wait up to 5 seconds
                for _ in range(50):
                    time.sleep(0.1)
                    try:
                        os.kill(pid, 0)  # Check if still alive
                    except OSError:
                        return  # Process is gone
                
                # Force kill if not responding (SIGKILL)
                os.kill(pid, signal.SIGKILL)
                
            except OSError:
                pass
    
    def _cleanup_previous_processes(self):
        """قتل جميع العمليات السابقة"""
        try:
            subprocess.run(
                ['pkill', '-9', '-f', 'background_trading_manager.py'],
                capture_output=True,
                timeout=5
            )
            time.sleep(0.5)
        except Exception:
            pass
    
    def _cleanup_zombies(self):
        """تنظيف zombie processes"""
        try:
            os.waitpid(-1, os.WNOHANG)
        except Exception:
            pass
    
    def _write_pid(self, pid: int):
        """كتابة PID إلى الملف"""
        with open(self.pid_file, 'w') as f:
            f.write(str(pid))
    
    def _clear_pid(self):
        """حذف ملف PID"""
        if self.pid_file.exists():
            self.pid_file.unlink()
    
    def _format_uptime(self, seconds: int) -> str:
        """تنسيق uptime للعرض"""
        if seconds <= 0:
            return "0 ثانية"
        
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        minutes = (seconds % 3600) // 60
        
        if days > 0:
            return f"{days} يوم {hours} ساعة"
        elif hours > 0:
            return f"{hours} ساعة {minutes} دقيقة"
        elif minutes > 0:
            return f"{minutes} دقيقة"
        else:
            return f"{seconds} ثانية"


# Global instance
_unified_manager_instance = None

def get_unified_manager() -> UnifiedSystemManager:
    """Get or create global UnifiedSystemManager instance"""
    global _unified_manager_instance
    if _unified_manager_instance is None:
        _unified_manager_instance = UnifiedSystemManager()
    return _unified_manager_instance


if __name__ == '__main__':
    # اختبار سريع
    print("🧪 اختبار UnifiedSystemManager...")
    
    manager = UnifiedSystemManager()
    
    try:
        print("\n1️⃣ جلب الحالة...")
        status = manager.get_status()
        print(f"   الحالة: {status['data']['status']}")
        
        print("\n2️⃣ بدء النظام...")
        result = manager.start_system(user='test')
        print(f"   PID: {result['pid']}")
        
        print("\n3️⃣ جلب الحالة...")
        status = manager.get_status()
        print(f"   الحالة: {status['data']['status']}")
        print(f"   PID: {status['data']['pid']}")
        
        print("\n4️⃣ إيقاف النظام...")
        manager.stop_system(user='test')
        
        print("\n5️⃣ جلب الحالة...")
        status = manager.get_status()
        print(f"   الحالة: {status['data']['status']}")
        
        print("\n✅ الاختبار ناجح!")
        
    except Exception as e:
        print(f"\n❌ خطأ: {e}")
