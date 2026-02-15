#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔧 Unified State Manager - مدير الحالة الموحد
================================================

Single Source of Truth لحالة النظام
- JSON file only (no database duplication)
- Atomic writes
- Audit trail
- Thread-safe

Author: System Unification Team
Date: 2026-02-01
"""

import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

class StateManager:
    """
    مدير الحالة الموحد - Single Source of Truth
    
    Features:
    - JSON file storage
    - Atomic writes (no corruption)
    - Thread-safe operations
    - Audit trail logging
    - State validation
    """
    
    def __init__(self, state_file: str = 'tmp/system_state.json'):
        self.state_file = Path(state_file)
        self.lock = threading.RLock()
        self.audit_log = Path('logs/audit/state_changes.jsonl')
        
        # Ensure directories exist
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.audit_log.parent.mkdir(parents=True, exist_ok=True)
    
    def read_state(self) -> Dict[str, Any]:
        """
        قراءة الحالة الحالية
        
        Returns:
            dict: الحالة الحالية
        """
        with self.lock:
            if not self.state_file.exists():
                return self._get_default_state()
            
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                    return self._validate_state(state)
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️ خطأ في قراءة الحالة: {e}")
                return self._get_default_state()
    
    def write_state(self, state_data: Dict[str, Any], user: Optional[str] = None) -> bool:
        """
        كتابة الحالة مع atomic write وaudit trail
        
        Args:
            state_data: البيانات الجديدة
            user: المستخدم الذي قام بالتغيير (optional)
        
        Returns:
            bool: True if successful
        """
        with self.lock:
            # Get old state for audit
            old_state = self.read_state() if self.state_file.exists() else {}
            
            # Add timestamp
            state_data['updated_at'] = datetime.now().isoformat()
            
            # Validate state
            state_data = self._validate_state(state_data)
            
            try:
                # Atomic write using temp file
                temp_file = self.state_file.with_suffix('.tmp')
                
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(state_data, f, ensure_ascii=False, indent=2)
                
                # Atomic rename (replaces old file)
                temp_file.replace(self.state_file)
                
                # Log to audit trail
                self._log_audit(old_state, state_data, user)
                
                return True
                
            except (IOError, OSError) as e:
                print(f"❌ فشل كتابة الحالة: {e}")
                # Clean up temp file if exists
                if temp_file.exists():
                    temp_file.unlink()
                return False
    
    def update_state(self, **kwargs) -> bool:
        """
        تحديث حقول محددة في الحالة
        
        Args:
            **kwargs: الحقول المراد تحديثها
        
        Returns:
            bool: True if successful
        """
        state = self.read_state()
        state.update(kwargs)
        return self.write_state(state)
    
    def send_heartbeat(self) -> bool:
        """
        إرسال نبضة (heartbeat) لإثبات أن النظام حي
        
        Returns:
            bool: True if successful
        """
        state = self.read_state()
        if 'heartbeat' not in state:
            state['heartbeat'] = {'last_beat': None, 'beats_count': 0, 'missed_beats': 0}
        
        state['heartbeat']['last_beat'] = datetime.now().isoformat()
        state['heartbeat']['beats_count'] = state['heartbeat'].get('beats_count', 0) + 1
        state['heartbeat']['missed_beats'] = 0  # Reset missed beats
        
        return self.write_state(state, user='heartbeat')
    
    def update_activity(self, component: str, **kwargs) -> bool:
        """
        تحديث آخر نشاط لمكون معين
        
        Args:
            component: اسم المكون (group_b, ml)
            **kwargs: البيانات المراد تحديثها
        
        Returns:
            bool: True if successful
        """
        state = self.read_state()
        if 'activity' not in state:
            state['activity'] = {}
        if component not in state['activity']:
            state['activity'][component] = {}
        
        # Update last_activity timestamp
        state['activity'][component]['last_activity'] = datetime.now().isoformat()
        
        # Update other fields
        state['activity'][component].update(kwargs)
        
        return self.write_state(state, user=f'{component}_activity')
    
    def get_seconds_since_heartbeat(self) -> Optional[int]:
        """
        حساب عدد الثواني منذ آخر نبضة
        
        Returns:
            int: عدد الثواني، أو None إذا لم توجد نبضة
        """
        state = self.read_state()
        last_beat = state.get('heartbeat', {}).get('last_beat')
        
        if not last_beat:
            return None
        
        try:
            last_beat_time = datetime.fromisoformat(last_beat)
            delta = datetime.now() - last_beat_time
            return int(delta.total_seconds())
        except Exception:
            return None
    
    def get_seconds_since_activity(self, component: str) -> Optional[int]:
        """
        حساب عدد الثواني منذ آخر نشاط لمكون
        
        Args:
            component: اسم المكون (group_b, ml)
        
        Returns:
            int: عدد الثواني، أو None إذا لم يوجد نشاط
        """
        state = self.read_state()
        last_activity = state.get('activity', {}).get(component, {}).get('last_activity')
        
        if not last_activity:
            return None
        
        try:
            last_activity_time = datetime.fromisoformat(last_activity)
            delta = datetime.now() - last_activity_time
            return int(delta.total_seconds())
        except Exception:
            return None
    
    def reset_monitoring_data(self):
        """
        تصفير بيانات المراقبة عند بدء تشغيل جديد
        
        يتم استدعاؤها عند start_system() لضمان بدء نظيف
        """
        state = self.read_state()
        
        # تصفير heartbeat
        state['heartbeat'] = {
            'last_beat': None,
            'beats_count': 0,
            'missed_beats': 0
        }
        
        # تصفير activity لجميع المكونات
        state['activity'] = {
            'group_b': {
                'last_activity': None,
                'last_cycle': None,
                'total_cycles': 0,
                'active_trades': 0
            },
            'ml': {
                'last_activity': None,
                'total_samples': 0
            }
        }
        
        # تحديث الحالة
        return self.write_state(state, user='system_start')
    
    def _get_default_state(self) -> Dict[str, Any]:
        """الحالة الافتراضية"""
        return {
            'status': 'stopped',
            'is_running': False,
            'pid': None,
            'started_at': None,
            'uptime': 0,
            'message': 'النظام متوقف',
            'updated_at': datetime.now().isoformat(),
            'version': '2.0.0',  # Unified version
            # ===== Live Monitoring =====
            'heartbeat': {
                'last_beat': None,
                'beats_count': 0,
                'missed_beats': 0
            },
            'activity': {
                'group_b': {
                    'last_activity': None,
                    'last_cycle': None,
                    'total_cycles': 0,
                    'active_trades': 0
                },
                'ml': {
                    'last_activity': None,
                    'total_samples': 0
                }
            }
        }
    
    def _validate_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        التحقق من وتصحيح الحالة
        
        Args:
            state: الحالة المراد التحقق منها
        
        Returns:
            dict: الحالة المُحققة
        """
        default = self._get_default_state()
        
        # Ensure required fields exist
        for key, value in default.items():
            if key not in state:
                state[key] = value
        
        # Validate status values
        valid_statuses = ['stopped', 'starting', 'running', 'stopping', 'error']
        if state.get('status') not in valid_statuses:
            state['status'] = 'stopped'
        
        # Ensure is_running matches status
        state['is_running'] = state['status'] in ['starting', 'running']
        
        return state
    
    def _log_audit(self, old_state: Dict, new_state: Dict, user: Optional[str] = None):
        """
        تسجيل التغيير في audit trail
        
        Args:
            old_state: الحالة القديمة
            new_state: الحالة الجديدة
            user: المستخدم (optional)
        """
        try:
            audit_entry = {
                'timestamp': datetime.now().isoformat(),
                'user': user or 'system',
                'old_status': old_state.get('status', 'unknown'),
                'new_status': new_state.get('status'),
                'old_pid': old_state.get('pid'),
                'new_pid': new_state.get('pid'),
                'changes': self._get_changes(old_state, new_state)
            }
            
            # Append to audit log (JSONL format)
            with open(self.audit_log, 'a', encoding='utf-8') as f:
                f.write(json.dumps(audit_entry, ensure_ascii=False) + '\n')
                
        except Exception as e:
            print(f"⚠️ فشل تسجيل audit: {e}")
    
    def _get_changes(self, old: Dict, new: Dict) -> Dict:
        """استخراج التغييرات بين الحالتين"""
        changes = {}
        for key in set(old.keys()) | set(new.keys()):
            old_val = old.get(key)
            new_val = new.get(key)
            if old_val != new_val:
                changes[key] = {'old': old_val, 'new': new_val}
        return changes
    
    def get_audit_trail(self, limit: int = 100) -> list:
        """
        جلب آخر التغييرات من audit trail
        
        Args:
            limit: عدد السجلات المراد جلبها
        
        Returns:
            list: قائمة السجلات
        """
        if not self.audit_log.exists():
            return []
        
        try:
            with open(self.audit_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Get last N lines
            recent_lines = lines[-limit:] if len(lines) > limit else lines
            
            # Parse JSON
            entries = []
            for line in recent_lines:
                try:
                    entries.append(json.loads(line.strip()))
                except Exception:
                    continue
            
            return entries
            
        except Exception as e:
            print(f"⚠️ فشل قراءة audit trail: {e}")
            return []


# Global instance للاستخدام السريع
_state_manager_instance = None

def get_state_manager() -> StateManager:
    """Get or create global StateManager instance"""
    global _state_manager_instance
    if _state_manager_instance is None:
        _state_manager_instance = StateManager()
    return _state_manager_instance


if __name__ == '__main__':
    # اختبار سريع
    print("🧪 اختبار StateManager...")
    
    sm = StateManager('tmp/test_state.json')
    
    # Test write
    print("\n1️⃣ كتابة حالة جديدة...")
    sm.write_state({'status': 'running', 'pid': 12345}, user='test_user')
    
    # Test read
    print("2️⃣ قراءة الحالة...")
    state = sm.read_state()
    print(f"   الحالة: {state}")
    
    # Test update
    print("3️⃣ تحديث الحالة...")
    sm.update_state(message='اختبار ناجح')
    
    # Test audit trail
    print("4️⃣ Audit trail:")
    for entry in sm.get_audit_trail(limit=5):
        print(f"   {entry['timestamp']}: {entry['old_status']} → {entry['new_status']}")
    
    print("\n✅ الاختبار ناجح!")
