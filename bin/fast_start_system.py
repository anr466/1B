#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 نظام تشغيل النظام الخلفي المُحسّن
=====================================

المميزات:
- ملف حالة خفيف (JSON) للاستجابة السريعة
- تحديث فوري بدون قاعدة البيانات
- polling سريع من التطبيق
- تحسين تجربة المستخدم

Usage:
    python3 fast_start_system.py --start
    python3 fast_start_system.py --stop
    python3 fast_start_system.py --status
"""

import os
import sys
import json
import time
import signal
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from pathlib import Path

# إضافة المسارات
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# مسار ملف الحالة
STATUS_FILE = PROJECT_ROOT / 'tmp' / 'system_status.json'
PID_FILE = PROJECT_ROOT / 'tmp' / 'background_manager.pid'
LOG_FILE = PROJECT_ROOT / 'logs' / 'background_trading.log'


def ensure_tmp_dir():
    """إنشاء مجلد tmp إذا لم يكن موجوداً"""
    STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)


def read_status():
    """قراءة حالة النظام من ملف JSON"""
    ensure_tmp_dir()
    if STATUS_FILE.exists():
        try:
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return get_default_status()


def write_status(status_data):
    """كتابة حالة النظام إلى ملف JSON"""
    ensure_tmp_dir()
    status_data['updated_at'] = datetime.now().isoformat()
    with open(STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(status_data, f, ensure_ascii=False, indent=2)


def get_default_status():
    """الحالة الافتراضية"""
    return {
        'status': 'stopped',
        'is_running': False,
        'pid': None,
        'started_at': None,
        'uptime': 0,
        'message': 'النظام متوقف',
        'group_b': {'running': False, 'last_run': None},
        'updated_at': datetime.now().isoformat()
    }


def get_pid():
    """جلب PID من الملف"""
    if PID_FILE.exists():
        try:
            with open(PID_FILE, 'r') as f:
                return int(f.read().strip())
        except:
            pass
    return None


def write_pid(pid):
    """كتابة PID إلى الملف"""
    ensure_tmp_dir()
    with open(PID_FILE, 'w') as f:
        f.write(str(pid))


def clear_pid():
    """حذف ملف PID"""
    if PID_FILE.exists():
        PID_FILE.unlink()


def is_process_running(pid):
    """التحقق من أن العملية تعمل"""
    try:
        result = subprocess.run(
            ['ps', '-p', str(pid)],
            capture_output=True,
            text=True,
            timeout=2
        )
        return result.returncode == 0
    except:
        return False


def kill_process(pid):
    """إيقاف عملية"""
    try:
        subprocess.run(['kill', '-15', str(pid)], timeout=5)
        time.sleep(1)
        subprocess.run(['kill', '-9', str(pid)], timeout=5)
        return True
    except:
        return False


def start_system():
    """بدء النظام الخلفي"""
    print("\n🚀 بدء النظام الخلفي...")
    
    # التحقق من وجود عملية سابقة
    existing_pid = get_pid()
    if existing_pid and is_process_running(existing_pid):
        print(f"⚠️ النظام يعمل بالفعل (PID: {existing_pid})")
        return {
            'success': False,
            'error': 'النظام يعمل بالفعل',
            'pid': existing_pid
        }
    
    # قتل العمليات السابقة إن وجدت
    try:
        subprocess.run(['pkill', '-9', '-f', 'background_trading_manager.py'], 
                      capture_output=True, timeout=5)
        time.sleep(0.5)
    except:
        pass
    
    # تحديث الحالة إلى starting
    status = read_status()
    status['status'] = 'starting'
    status['is_running'] = False
    status['message'] = 'جاري بدء النظام...'
    write_status(status)
    
    # بدء العملية
    env = os.environ.copy()
    env['PYTHONPATH'] = str(PROJECT_ROOT)
    
    process = subprocess.Popen(
        [sys.executable, str(PROJECT_ROOT / 'bin' / 'background_trading_manager.py'), '--start'],
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        env=env
    )
    
    write_pid(process.pid)
    print(f"✅ تم بدء العملية (PID: {process.pid})")
    
    # تحديث الحالة فوراً
    status = read_status()
    status['status'] = 'running'
    status['is_running'] = True
    status['pid'] = process.pid
    status['started_at'] = datetime.now().isoformat()
    status['message'] = 'النظام يعمل'
    write_status(status)
    
    return {
        'success': True,
        'message': 'تم بدء النظام بنجاح',
        'pid': process.pid,
        'status': 'running'
    }


def stop_system():
    """إيقاف النظام الخلفي"""
    print("\n⏹️ إيقاف النظام الخلفي...")
    
    pid = get_pid()
    if not pid or not is_process_running(pid):
        print("⚠️ النظام ليس يعمل")
        status = read_status()
        status['status'] = 'stopped'
        status['is_running'] = False
        status['pid'] = None
        status['message'] = 'النظام متوقف'
        write_status(status)
        return {
            'success': False,
            'error': 'النظام ليس يعمل'
        }
    
    # إيقاف العملية
    kill_process(pid)
    clear_pid()
    
    # تحديث الحالة
    status = read_status()
    status['status'] = 'stopped'
    status['is_running'] = False
    status['pid'] = None
    status['started_at'] = None
    status['uptime'] = 0
    status['message'] = 'النظام متوقف'
    write_status(status)
    
    print("✅ تم إيقاف النظام")
    return {
        'success': True,
        'message': 'تم إيقاف النظام بنجاح'
    }


def get_status():
    """الحصول على حالة النظام"""
    pid = get_pid()
    
    status = read_status()
    
    # التحقق من العملية الحية
    if pid and is_process_running(pid):
        status['is_running'] = True
        status['pid'] = pid
        if status['status'] != 'running':
            status['status'] = 'running'
            status['message'] = 'النظام يعمل'
    else:
        status['is_running'] = False
        status['pid'] = None
        status['status'] = 'stopped'
        status['message'] = 'النظام متوقف'
    
    # حساب uptime
    if status['is_running'] and status.get('started_at'):
        try:
            started = datetime.fromisoformat(status['started_at'])
            status['uptime'] = int((datetime.now() - started).total_seconds())
        except:
            pass
    
    return status


def format_uptime(seconds):
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


def main():
    """النقطة الرئيسية"""
    import argparse
    
    parser = argparse.ArgumentParser(description='نظام إدارة التداول الخلفي - السريع')
    parser.add_argument('--start', action='store_true', help='بدء النظام')
    parser.add_argument('--stop', action='store_true', help='إيقاف النظام')
    parser.add_argument('--status', action='store_true', help='عرض حالة النظام')
    
    args = parser.parse_args()
    
    if args.start:
        result = start_system()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.stop:
        result = stop_system()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    
    elif args.status:
        status = get_status()
        print(json.dumps(status, ensure_ascii=False, indent=2))
    
    else:
        # عرض حالة النظام
        status = get_status()
        print("\n📊 حالة النظام:")
        print(f"  الحالة: {status['status']}")
        print(f"  يعمل: {'نعم' if status['is_running'] else 'لا'}")
        print(f"  PID: {status.get('pid') or 'لا يوجد'}")
        print(f"  رسالة: {status['message']}")
        print(f"  uptime: {format_uptime(status.get('uptime', 0))}")


if __name__ == '__main__':
    main()
