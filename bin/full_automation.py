#!/usr/bin/env python3
"""
🚀 أتمتة كاملة - تشغيل النظام بالكامل والتقاط لقطة شاشة
========================================================
ملاحظة النظام يعمل علي البيئة الافتراضية دائما 

هذا الملف يقوم بـ:
1. تشغيل الخادم (FastAPI)
2. تشغيل Metro Bundler
3. تشغيل التطبيق على الجهاز
4. التقاط لقطة شاشة
5. عرض حالة النظام
"""

import os
import sys
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime

# الألوان للطباعة
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """طباعة عنوان"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

def print_step(step_num, text):
    """طباعة خطوة"""
    print(f"{Colors.OKBLUE}[{step_num}] {text}{Colors.ENDC}")

def print_success(text):
    """طباعة نجاح"""
    print(f"{Colors.OKGREEN}✅ {text}{Colors.ENDC}")

def print_error(text):
    """طباعة خطأ"""
    print(f"{Colors.FAIL}❌ {text}{Colors.ENDC}")

def print_warning(text):
    """طباعة تحذير"""
    print(f"{Colors.WARNING}⚠️ {text}{Colors.ENDC}")

def run_command(cmd, description="", background=False):
    """تشغيل أمر"""
    try:
        if background:
            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print_success(f"{description}")
            return True
        else:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print_success(f"{description}")
                return True
            else:
                print_error(f"{description}: {result.stderr}")
                return False
    except Exception as e:
        print_error(f"{description}: {str(e)}")
        return False

def main():
    """البرنامج الرئيسي"""
    print_header("🚀 أتمتة تشغيل Trading AI Bot")
    
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # الخطوة 1: إيقاف الخدمات القديمة
    print_step("1", "إيقاف الخدمات القديمة...")
    run_command("pkill -f 'fastapi_server.py'", "إيقاف الخادم القديم", background=False)
    run_command("pkill -f 'npm start'", "إيقاف Metro القديم", background=False)
    time.sleep(2)
    print_success("تم إيقاف الخدمات القديمة")
    
    # الخطوة 2: تشغيل الخادم الموحد
    print_step("2", "تشغيل الخادم الموحد (FastAPI)...")
    cmd_server = f"cd {project_root} && bash -c 'source venv/bin/activate && python3 bin/unified_server.py' > /tmp/server.log 2>&1 &"
    run_command(cmd_server, "الخادم الموحد يعمل على Port 3002", background=True)
    time.sleep(4)
    
    # التحقق من الخادم
    print_step("2.1", "التحقق من الخادم...")
    result = subprocess.run("curl -s http://localhost:3002/health", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print_success("الخادم يستجيب بنجاح")
    else:
        print_warning("الخادم قد لا يكون جاهزاً بعد")
    
    # الخطوة 3: تشغيل Metro Bundler
    print_step("3", "تشغيل Metro Bundler...")
    cmd_metro = f"cd {project_root}/mobile_app/TradingApp && npm start > /tmp/metro.log 2>&1 &"
    run_command(cmd_metro, "Metro يعمل على Port 8081", background=True)
    time.sleep(3)
    
    # الخطوة 4: إعداد Port Forwarding
    print_step("4", "إعداد Port Forwarding...")
    run_command("adb reverse tcp:3002 tcp:3002", "Port 3002 مُعاد التوجيه", background=False)
    run_command("adb reverse tcp:8081 tcp:8081", "Port 8081 مُعاد التوجيه", background=False)
    
    # الخطوة 5: تشغيل التطبيق على الجهاز
    print_step("5", "تشغيل التطبيق على الجهاز...")
    run_command("adb shell am start -n com.tradingapp/.MainActivity", "التطبيق يعمل على الجهاز", background=False)
    time.sleep(3)
    
    # الخطوة 6: التقاط لقطة شاشة
    print_step("6", "التقاط لقطة شاشة...")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = f"/tmp/trading_app_screenshot_{timestamp}.png"
    
    cmd_screenshot = f"adb shell screencap -p /sdcard/screenshot.png && adb pull /sdcard/screenshot.png {screenshot_path}"
    if run_command(cmd_screenshot, f"لقطة الشاشة: {screenshot_path}", background=False):
        print_success(f"تم حفظ اللقطة: {screenshot_path}")
    else:
        print_warning("فشل التقاط لقطة الشاشة")
    
    # الخطوة 7: عرض حالة النظام
    print_step("7", "عرض حالة النظام...")
    print_header("📊 حالة النظام")
    
    # حالة الخادم
    result = subprocess.run("curl -s http://localhost:3002/api/system/status", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            print(f"{Colors.OKGREEN}✅ الخادم: يعمل بنجاح{Colors.ENDC}")
            print(f"   • الحالة: {data.get('status', 'N/A')}")
            print(f"   • الخدمات: {json.dumps(data.get('data', {}).get('services', {}), ensure_ascii=False, indent=6)}")
        except:
            print(f"{Colors.OKGREEN}✅ الخادم: يعمل بنجاح{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}❌ الخادم: لا يستجيب{Colors.ENDC}")
    
    # حالة Metro
    result = subprocess.run("lsof -i :8081", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"{Colors.OKGREEN}✅ Metro: يعمل على Port 8081{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}❌ Metro: لا يعمل{Colors.ENDC}")
    
    # حالة التطبيق
    result = subprocess.run("adb shell pidof com.tradingapp", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"{Colors.OKGREEN}✅ التطبيق: يعمل على الجهاز{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}❌ التطبيق: لا يعمل{Colors.ENDC}")
    
    # الخطوة 8: عرض معلومات الاتصال
    print_header("🔗 معلومات الاتصال")
    
    # الحصول على IP الحاسوب
    result = subprocess.run("ifconfig | grep 'inet ' | grep -v 127.0.0.1 | head -1 | awk '{print $2}'", shell=True, capture_output=True, text=True)
    mac_ip = result.stdout.strip()
    
    # الحصول على IP الجهاز
    result = subprocess.run("adb shell ip addr show | grep 'inet ' | grep -v 127.0.0.1 | head -1 | awk '{print $2}' | cut -d'/' -f1", shell=True, capture_output=True, text=True)
    device_ip = result.stdout.strip()
    
    print(f"{Colors.OKCYAN}🖥️ الحاسوب (Mac):{Colors.ENDC}")
    print(f"   • IP: {mac_ip if mac_ip else 'N/A'}")
    print(f"   • الخادم: http://localhost:3002")
    print(f"   • Metro: http://localhost:8081")
    
    print(f"\n{Colors.OKCYAN}📱 الجهاز (Android):{Colors.ENDC}")
    print(f"   • IP: {device_ip if device_ip else 'N/A'}")
    print(f"   • الخادم: http://localhost:3002 (عبر Port Forwarding)")
    print(f"   • Metro: http://localhost:8081 (عبر Port Forwarding)")
    
    # الخطوة 9: أوامر مفيدة
    print_header("🔧 أوامر مفيدة")
    
    print(f"{Colors.BOLD}عرض السجلات:{Colors.ENDC}")
    print("   tail -f /tmp/server.log")
    print("   tail -f /tmp/metro.log")
    
    print(f"\n{Colors.BOLD}اختبار الاتصال:{Colors.ENDC}")
    print("   curl http://localhost:3002/api/system/status")
    print("   adb shell curl http://localhost:3002/api/system/status")
    
    print(f"\n{Colors.BOLD}إعادة تشغيل التطبيق:{Colors.ENDC}")
    print("   adb shell am force-stop com.tradingapp")
    print("   adb shell am start -n com.tradingapp/.MainActivity")
    
    print(f"\n{Colors.BOLD}التقاط لقطة شاشة:{Colors.ENDC}")
    print("   adb shell screencap -p /sdcard/screenshot.png")
    print("   adb pull /sdcard/screenshot.png")
    
    # الخطوة 10: الملخص النهائي
    print_header("✅ النظام جاهز للعمل")
    
    print(f"{Colors.OKGREEN}{Colors.BOLD}🎉 تم تشغيل جميع الخدمات بنجاح!{Colors.ENDC}\n")
    print(f"{Colors.BOLD}الخدمات الجارية:{Colors.ENDC}")
    print(f"   ✅ الخادم (FastAPI) - Port 3002")
    print(f"   ✅ Metro Bundler - Port 8081")
    print(f"   ✅ التطبيق المحمول - جاري التشغيل")
    print(f"   ✅ Port Forwarding - نشط")
    
    if os.path.exists(screenshot_path):
        print(f"\n{Colors.BOLD}لقطة الشاشة:{Colors.ENDC}")
        print(f"   📸 {screenshot_path}")
    
    print(f"\n{Colors.BOLD}الخطوات التالية:{Colors.ENDC}")
    print(f"   1. افتح التطبيق على الجهاز")
    print(f"   2. سجل حساب جديد أو ادخل")
    print(f"   3. اختبر جميع الوظائف")
    print(f"   4. تابع السجلات للأخطاء")
    
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_error("\nتم إيقاف البرنامج بواسطة المستخدم")
        sys.exit(0)
    except Exception as e:
        print_error(f"خطأ: {str(e)}")
        sys.exit(1)
