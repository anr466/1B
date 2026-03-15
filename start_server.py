#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 Trading AI Bot - Unified Server
====================================
ملف الخادم الموحد الرئيسي للنظام الثلاثي
- Backend (FastAPI + Flask)
- Database (PostgreSQL)
- Mobile App Integration

المسار: start_server.py
الاستخدام: python start_server.py
البورت: 3002 (موحد)
"""

import sys
import os
import socket
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent
VENV_PYTHON = PROJECT_ROOT / '.venv' / 'bin' / 'python'
CURRENT_PYTHON = Path(sys.executable).resolve()
TARGET_VENV_PYTHON = VENV_PYTHON.resolve() if VENV_PYTHON.exists() else None

if TARGET_VENV_PYTHON and CURRENT_PYTHON != TARGET_VENV_PYTHON and not os.getenv('TRADING_AI_BOT_VENV_REEXEC'):
    env = os.environ.copy()
    env['TRADING_AI_BOT_VENV_REEXEC'] = '1'
    os.execve(str(TARGET_VENV_PYTHON), [str(TARGET_VENV_PYTHON), __file__, *sys.argv[1:]], env)

# تحميل متغيرات البيئة من .env
load_dotenv()

# إضافة المسار الجذري للمشروع
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'config'))
sys.path.insert(0, str(PROJECT_ROOT / 'database'))
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.wsgi import WSGIMiddleware
from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import uvicorn
import signal
import atexit

# ============================================================
# 🌐 كشف IP ذكي للمحاكي والأجهزة الخارجية
# ============================================================

def get_local_ip():
    """الحصول على IP الشبكة المحلية"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()
EMULATOR_IP = "10.0.2.2"  # IP خاص بمحاكي Android

# ============================================================
# إعداد نظام السجلات الموحد
# ============================================================

from config.logging_config import setup_logging, LOGS_DIR, LOG_FILE, ERROR_LOG_FILE, disable_print_in_production, is_production

# ✅ تعطيل print() في الإنتاج - يحول الرسائل إلى ملف logs/print_output.log
if disable_print_in_production():
    pass  # print معطل في الإنتاج

logger = setup_logging(__name__)

MANAGED_PROCESS_MARKERS = (
    'start_server.py',
    'uvicorn',
    'background_trading_manager.py',
)

# ============================================================
# 🔄 نظام إعادة تعيين الحدود اليومية
# ============================================================

try:
    from backend.core.daily_reset_scheduler import start_daily_reset_scheduler
    DAILY_RESET_AVAILABLE = True
    logger.info("✅ نظام إعادة التعيين اليومي متاح")
except ImportError as e:
    DAILY_RESET_AVAILABLE = False
    logger.warning(f"⚠️ نظام إعادة التعيين اليومي غير متاح: {e}")

# ============================================================
# 🧹 التنظيف التلقائي عند التشغيل
# ============================================================

def run_auto_cleanup():
    """تشغيل التنظيف التلقائي للملفات القديمة"""
    try:
        from backend.utils.auto_cleanup_manager import cleanup_on_startup
        result = cleanup_on_startup()
        if result and result.get('files_deleted', 0) > 0:
            logger.info(f"🧹 تنظيف تلقائي: {result['files_deleted']} ملف")
    except Exception as e:
        logger.debug(f"⚠️ التنظيف التلقائي: {e}")

# ============================================================
# دوال إدارة العمليات والمنافذ
# ============================================================

def kill_process_on_port(port):
    """قتل عملياتنا المدارة فقط على المنفذ المحدد (آمن)."""
    def _is_managed_process(pid: str) -> bool:
        try:
            cmd_result = subprocess.run(
                ['ps', '-p', pid, '-o', 'command='],
                capture_output=True,
                text=True,
                check=False,
            )
            command = (cmd_result.stdout or '').strip()
            user_result = subprocess.run(
                ['ps', '-p', pid, '-o', 'user='],
                capture_output=True,
                text=True,
                check=False,
            )
            process_user = (user_result.stdout or '').strip()
            current_user = os.getenv('USER', '').strip()
            has_marker = any(marker in command for marker in MANAGED_PROCESS_MARKERS)
            belongs_to_project = str(PROJECT_ROOT) in command
            is_background_manager = 'background_trading_manager.py' in command
            same_user = bool(current_user) and process_user == current_user
            return has_marker and (belongs_to_project or is_background_manager or same_user)
        except Exception:
            return False

    try:
        if sys.platform == 'darwin':  # macOS
            # البحث عن العملية على المنفذ
            result = subprocess.run(
                ['lsof', '-ti', f':{port}'],
                capture_output=True,
                text=True
            )
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    try:
                        if _is_managed_process(pid):
                            subprocess.run(['kill', '-15', pid], check=False)
                            logger.info(f"✅ تم إيقاف العملية المدارة {pid} على المنفذ {port}")
                        else:
                            logger.warning(f"⛔ تخطي PID {pid} على المنفذ {port} لأنه ليس عملية مدارة")
                    except Exception as e:
                        logger.warning(f"⚠️ فشل قتل العملية {pid}: {e}")
        elif sys.platform == 'linux':  # Linux
            result = subprocess.run(['lsof', '-ti', f':{port}'], capture_output=True, text=True, check=False)
            for pid in result.stdout.strip().split('\n'):
                if pid and _is_managed_process(pid):
                    subprocess.run(['kill', '-15', pid], check=False)
                    logger.info(f"✅ تم إيقاف العملية المدارة {pid} على المنفذ {port}")
        elif sys.platform == 'win32':  # Windows
            subprocess.run(
                f"netstat -ano | findstr :{port}",
                shell=True,
                capture_output=True
            )
    except Exception as e:
        logger.warning(f"⚠️ لم يتمكن من قتل العمليات على المنفذ {port}: {e}")


def is_port_available(port):
    """التحقق من توفر المنفذ"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result != 0
    except Exception as e:
        logger.error(f"❌ خطأ في فحص المنفذ: {e}")
        return False


def ensure_port_available(port, max_retries=3):
    """التأكد من توفر المنفذ مع إعادة المحاولة"""
    for attempt in range(max_retries):
        if is_port_available(port):
            logger.info(f"✅ المنفذ {port} متاح")
            return True
        
        logger.warning(f"⚠️ المنفذ {port} مشغول (محاولة {attempt + 1}/{max_retries})")
        kill_process_on_port(port)
        time.sleep(1)
    
    logger.error(f"❌ فشل تحرير المنفذ {port}")
    return False


def check_database_connection():
    """فحص اتصال قاعدة البيانات"""
    try:
        from database.database_manager import DatabaseManager
        db = DatabaseManager()
        with db.get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        logger.info("✅ قاعدة البيانات متصلة")
        return True
    except Exception as e:
        logger.error(f"❌ فشل الاتصال بقاعدة البيانات: {e}")
        return False


def start_background_services():
    """بدء الخدمات الخلفية (Daily Reset)"""
    try:
        # بدء المجدول لإعادة تعيين الحدود اليومية عند منتصف الليل
        if DAILY_RESET_AVAILABLE:
            start_daily_reset_scheduler(reset_time="00:00")
            logger.info("✅ تم بدء Daily Reset Scheduler (منتصف الليل)")
        else:
            logger.warning("⚠️ Daily Reset Scheduler غير متاح")
            
    except Exception as e:
        logger.error(f"❌ خطأ في بدء الخدمات الخلفية: {e}")


def cleanup_on_exit():
    """تنظيف الموارد عند الإيقاف"""
    def _safe_log(msg: str):
        try:
            logger.info(msg)
        except Exception:
            pass

    try:
        _safe_log("🧹 تنظيف الموارد...")
        from database.database_manager import DatabaseManager
        db = DatabaseManager()
        db.close()
        _safe_log("✅ تم إغلاق اتصالات قاعدة البيانات")
    except Exception as e:
        logger.debug(f"ℹ️ تنظيف: {e}")


# ============================================================
# إنشاء FastAPI App
# ============================================================

app = FastAPI(
    title="Trading AI Bot API",
    description="نظام التداول الآلي الذكي - النظام الثلاثي الموحد",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ============================================================
# API Versioning - إصدارات API
# ============================================================

API_VERSION = "v2"
API_PREFIX = f"/api/{API_VERSION}"

# معلومات الإصدار
API_INFO = {
    "current_version": "v2",
    "supported_versions": ["v1", "v2"],
    "deprecated_versions": [],
    "latest_version": "v2",
    "v1": {
        "status": "stable",
        "description": "النسخة الأساسية - للعملاء القدامى",
        "endpoints": 15,
        "features": ["auth", "email", "notifications", "system_health"]
    },
    "v2": {
        "status": "latest",
        "description": "النسخة المحسّنة - مع Caching و Pagination",
        "endpoints": 18,
        "features": ["auth", "email", "notifications", "system_health", "caching", "pagination", "admin_endpoints"]
    }
}

# ============================================================
# 🔒 CORS Configuration
# ============================================================

ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

if ENVIRONMENT == 'development':
    # التطوير: regex مرن لأي IP على المنافذ الصحيحة
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|10\.0\.2\.2|[\d\.]+):(3002|8081)$",
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
    )
    logger.info("✅ CORS: Development mode (flexible)")
else:
    # الإنتاج: قائمة محددة فقط
    PROD_ORIGINS = [
        "https://trading-ai-bot.app",
        "https://api.trading-ai-bot.app",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=PROD_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
    )
    logger.info(f"✅ CORS: Production mode ({len(PROD_ORIGINS)} origins)")

# ============================================================
# FastAPI Native Endpoints
# ============================================================

@app.get("/")
async def root():
    """الصفحة الرئيسية"""
    return {
        "message": "Trading AI Bot API v1.0.0",
        "status": "running",
        "system": "Unified Trading System",
        "api_version": API_VERSION,
        "docs": "/docs",
        "health": "/health",
        "versioned_api": f"{API_PREFIX}/"
    }


@app.get("/api/version")
@app.get("/api/v1/version")
async def api_version():
    """معلومات إصدار API"""
    return API_INFO


@app.get("/health")
async def health_check():
    """فحص صحة النظام"""
    try:
        from database.database_manager import DatabaseManager
        db = DatabaseManager()
        with db.get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        
        return {
            "status": "healthy",
            "database": "connected",
            "server": "unified",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e)
        }


@app.get("/api/connection/info")
async def get_connection_info():
    """معلومات الاتصال للتطبيق"""
    return {
        "server_ip": LOCAL_IP,
        "emulator_ip": EMULATOR_IP,
        "port": 3002,
        "urls": {
            "localhost": "http://localhost:3002",
            "emulator": f"http://{EMULATOR_IP}:3002",
            "network": f"http://{LOCAL_IP}:3002"
        },
        "endpoints": {
            "health": "/health",
            "admin_status": "/api/admin/system/status",
            "trading_state": "/api/admin/trading/state",
            "trading_start": "/api/admin/trading/start",
            "trading_stop": "/api/admin/trading/stop",
            "trading_emergency_stop": "/api/admin/trading/emergency-stop"
        }
    }


# ============================================================
# إنشاء Flask App وتسجيل Blueprints
# ============================================================

flask_app = Flask(__name__)
flask_app.config['JSON_AS_ASCII'] = False

# ============================================================
# 🔒 Flask CORS Configuration
# ============================================================

try:
    from flask_cors import CORS
    if ENVIRONMENT == 'development':
        CORS(flask_app, 
             origins=["*"], 
             supports_credentials=True,
             allow_headers=["*"],
             expose_headers=["*"],
             methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
        logger.info("✅ Flask-CORS enabled (Development - flexible)")
    else:
        CORS(flask_app, 
             origins=PROD_ORIGINS, 
             supports_credentials=True,
             allow_headers=["*"],
             expose_headers=["*"],
             methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])
        logger.info(f"✅ Flask-CORS enabled (Production - {len(PROD_ORIGINS)} origins)")
except ImportError:
    logger.warning("⚠️ flask_cors not installed - CORS may not work properly")

# ============================================================
# �🔴 معالجات الأخطاء الموحدة (JSON فقط)
# ============================================================

@flask_app.errorhandler(404)
def not_found_error(error):
    """معالج 404 - إرجاع JSON بدلاً من HTML"""
    from flask import jsonify
    return jsonify({
        'success': False,
        'error': 'المسار غير موجود',
        'code': 'NOT_FOUND'
    }), 404

@flask_app.errorhandler(500)
def internal_error(error):
    """معالج 500 - إرجاع JSON بدلاً من HTML"""
    from flask import jsonify
    logger.error(f"Internal Server Error: {error}")
    return jsonify({
        'success': False,
        'error': 'خطأ داخلي في الخادم',
        'code': 'INTERNAL_ERROR'
    }), 500

@flask_app.errorhandler(405)
def method_not_allowed(error):
    """معالج 405 - إرجاع JSON بدلاً من HTML"""
    from flask import jsonify
    return jsonify({
        'success': False,
        'error': 'الطريقة غير مسموحة',
        'code': 'METHOD_NOT_ALLOWED'
    }), 405

# ============================================================
# 🚦 إعداد Rate Limiting
# ============================================================

limiter = Limiter(
    app=flask_app,
    key_func=get_remote_address,
    default_limits=["100 per minute"],  # الحد الافتراضي: 100 طلب/دقيقة
    storage_uri="memory://"  # استخدام الذاكرة (يمكن تغييره لـ Redis للإنتاج)
)

logger.info("✅ Rate Limiter تم تفعيله بنجاح")
logger.info("   - الحد الافتراضي: 100 طلب/دقيقة")
logger.info("   - التخزين: الذاكرة")

blueprints_loaded = []
blueprints_failed = []

# تسجيل Mobile Endpoints (الإصدار الأساسي - يستخدمه التطبيق)
try:
    from backend.api.mobile_endpoints import mobile_bp
    flask_app.register_blueprint(mobile_bp)
    blueprints_loaded.append("Mobile Endpoints (الإصدار الأساسي + 18 endpoints)")
    logger.debug("✅ Mobile Endpoints loaded")
except Exception as e:
    blueprints_failed.append(f"Mobile Endpoints: {e}")
    logger.error(f"❌ Mobile Endpoints: {e}")

# تسجيل Auth Endpoints
try:
    from backend.api.auth_endpoints import auth_bp
    flask_app.register_blueprint(auth_bp)
    blueprints_loaded.append("Auth Endpoints (9 endpoints)")
    logger.debug("✅ Auth Endpoints loaded")
except Exception as e:
    blueprints_failed.append(f"Auth Endpoints: {e}")
    logger.error(f"❌ Auth Endpoints: {e}")

# تسجيل Admin Endpoints
try:
    from backend.api.admin_unified_api import admin_unified_bp
    flask_app.register_blueprint(admin_unified_bp)
    blueprints_loaded.append("Admin Endpoints (44 endpoints)")
    logger.debug("✅ Admin Endpoints loaded")
except Exception as e:
    blueprints_failed.append(f"Admin Endpoints: {e}")
    logger.error(f"❌ Admin Endpoints: {e}")

# تسجيل System Endpoints
try:
    from backend.api.system_endpoints import system_bp
    flask_app.register_blueprint(system_bp)
    blueprints_loaded.append("System Endpoints")
    logger.debug("✅ System Endpoints loaded")
except Exception as e:
    blueprints_failed.append(f"System Endpoints: {e}")
    logger.error(f"❌ System Endpoints: {e}")

# تسجيل Background Control
try:
    from backend.api.background_control import background_bp
    flask_app.register_blueprint(background_bp)
    blueprints_loaded.append("Background Control")
    logger.debug("✅ Background Control loaded")
except Exception as e:
    blueprints_failed.append(f"Background Control: {e}")
    logger.error(f"❌ Background Control: {e}")

# تسجيل Fast System API (نظام سريع بدون قاعدة البيانات)
try:
    from backend.api.system_fast_api import system_fast_bp
    flask_app.register_blueprint(system_fast_bp)
    blueprints_loaded.append("Fast System API")
    logger.debug("✅ Fast System API loaded")
except Exception as e:
    blueprints_failed.append(f"Fast System API: {e}")
    logger.error(f"❌ Fast System API: {e}")

# تسجيل Trading Control API (State Machine - المصدر الوحيد للحقيقة)
try:
    from backend.api.trading_control_api import trading_control_bp
    flask_app.register_blueprint(trading_control_bp)
    blueprints_loaded.append("Trading Control API (State Machine)")
    logger.debug("✅ Trading Control API loaded")
except Exception as e:
    blueprints_failed.append(f"Trading Control API: {e}")
    logger.error(f"❌ Trading Control API: {e}")

# تسجيل Smart Exit API
try:
    from backend.api.smart_exit_api import smart_exit_bp
    flask_app.register_blueprint(smart_exit_bp)
    blueprints_loaded.append("Smart Exit API")
    logger.debug("✅ Smart Exit API loaded")
except Exception as e:
    blueprints_failed.append(f"Smart Exit API: {e}")
    logger.error(f"❌ Smart Exit API: {e}")

# تسجيل Secure Actions Endpoints (نظام التحقق الموحد)
try:
    from backend.api.secure_actions_endpoints import secure_actions_bp
    flask_app.register_blueprint(secure_actions_bp)
    blueprints_loaded.append("Secure Actions (6 endpoints)")
    logger.debug("✅ Secure Actions Endpoints loaded")
except Exception as e:
    blueprints_failed.append(f"Secure Actions: {e}")
    logger.error(f"❌ Secure Actions: {e}")

# تسجيل FCM Endpoints
try:
    from backend.api.fcm_endpoints import fcm_bp
    flask_app.register_blueprint(fcm_bp)
    blueprints_loaded.append("FCM Endpoints")
    logger.debug("✅ FCM Endpoints loaded")
except Exception as e:
    blueprints_failed.append(f"FCM Endpoints: {e}")
    logger.error(f"❌ FCM Endpoints: {e}")

# تسجيل Login OTP Endpoints
try:
    from backend.api.login_otp_endpoints import login_otp_bp
    flask_app.register_blueprint(login_otp_bp)
    blueprints_loaded.append("Login OTP Endpoints (3 endpoints)")
    logger.debug("✅ Login OTP Endpoints loaded")
except Exception as e:
    blueprints_failed.append(f"Login OTP: {e}")
    logger.error(f"❌ Login OTP Endpoints: {e}")

# تسجيل Client Logs Endpoint
try:
    from backend.api.client_logs_endpoint import client_logs_bp
    flask_app.register_blueprint(client_logs_bp)
    blueprints_loaded.append("Client Logs Endpoint (2 endpoints)")
    logger.debug("✅ Client Logs Endpoint loaded")
except Exception as e:
    blueprints_failed.append(f"Client Logs: {e}")
    logger.error(f"❌ Client Logs Endpoint: {e}")

# تسجيل ML Status Endpoints
try:
    from backend.api.ml_status_endpoints import ml_status_bp
    flask_app.register_blueprint(ml_status_bp)
    blueprints_loaded.append("ML Status Endpoints (5 endpoints)")
    logger.debug("✅ ML Status Endpoints loaded")
except Exception as e:
    blueprints_failed.append(f"ML Status: {e}")
    logger.error(f"❌ ML Status Endpoints: {e}")

# تسجيل ML Learning Endpoints
try:
    from backend.api.ml_learning_endpoints import ml_learning_bp
    flask_app.register_blueprint(ml_learning_bp)
    blueprints_loaded.append("ML Learning Endpoints (6 endpoints)")
    logger.debug("✅ ML Learning Endpoints loaded")
except Exception as e:
    blueprints_failed.append(f"ML Learning: {e}")
    logger.error(f"❌ ML Learning Endpoints: {e}")

logger.info(f"✅ تم تحميل {len(blueprints_loaded)} Blueprints بنجاح")

# ============================================================
# ربط Flask مع FastAPI
# ============================================================

app.mount("/api", WSGIMiddleware(flask_app))
logger.debug("✅ Flask mounted على /api")

# ============================================================
# Request Logging Middleware
# ============================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """تسجيل الطلبات مع معالجة الأخطاء لضمان استمرارية الخادم"""
    from fastapi.responses import JSONResponse
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # تسجيل الطلبات المهمة فقط
        if request.url.path not in ["/health", "/"]:
            logger.debug(
                f"{request.method} {request.url.path} "
                f"- {response.status_code} ({process_time:.3f}s)"
            )
        
        return response
        
    except Exception as e:
        # ✅ معالجة أي خطأ غير متوقع - الخادم يستمر في العمل
        process_time = time.time() - start_time
        logger.error(
            f"❌ خطأ في معالجة الطلب: {request.method} {request.url.path} - {e}",
            exc_info=True
        )
        
        # إرجاع رد خطأ بدلاً من إيقاف الخادم
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "خطأ داخلي في الخادم",
                "message": "حدث خطأ غير متوقع. تم تسجيله للمراجعة."
            }
        )

# ============================================================
# خدمة الملخص اليومي
# ============================================================

def start_daily_summary_service():
    """تشغيل خدمة الملخص اليومي"""
    try:
        from backend.services.admin_notification_service import get_admin_notification_service
        notifier = get_admin_notification_service()
        if notifier:
            logger.info("✅ خدمة الإشعارات الإدارية نشطة")
            return True
        return False
    except Exception as e:
        logger.warning(f"⚠️ خدمة الإشعارات غير متاحة: {e}")
        return False

# ============================================================
# معالج الإشارات (Graceful Shutdown)
# ============================================================

def signal_handler(sig, frame):
    """معالج الإشارات للإيقاف الآمن"""
    logger.info("🛑 إيقاف الخادم بشكل آمن...")
    cleanup_on_exit()
    sys.exit(0)

# ============================================================
# التشغيل
# ============================================================

if __name__ == "__main__":
    # ============================================================
    # Production Startup - Minimal Output
    # ============================================================
    
    PORT = 3002

    # تشغيل التنظيف التلقائي فقط عند التشغيل الفعلي (وليس عند import)
    run_auto_cleanup()

    # تسجيل الإشارات فقط أثناء التشغيل الفعلي لتجنب side effects أثناء الاستيراد
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    atexit.register(cleanup_on_exit)
    
    # فحص المنفذ
    logger.info(f"Starting server on port {PORT}")
    if not is_port_available(PORT):
        logger.warning(f"Port {PORT} busy, killing previous processes...")
        kill_process_on_port(PORT)
        time.sleep(1)
    
    if not ensure_port_available(PORT):
        logger.error(f"Failed to free port {PORT}")
        sys.exit(1)
    
    # فحص قاعدة البيانات
    if not check_database_connection():
        logger.error("Database connection failed")
        sys.exit(1)
    
    # ✅ مزامنة حالة النظام في الخلفية (لا تحظر التشغيل)
    import threading
    def background_sync():
        try:
            from backend.api.system_recovery import get_recovery_system
            recovery_system = get_recovery_system()
            sync_result = recovery_system.force_sync()
            logger.info(f"✅ مزامنة الحالة: {sync_result}")
        except Exception as sync_error:
            logger.warning(f"⚠️ فشل مزامنة الحالة: {sync_error}")
    
    sync_thread = threading.Thread(target=background_sync, daemon=True)
    sync_thread.start()
    logger.info("🔄 بدء المزامنة في الخلفية...")
    
    # تسجيل المعلومات الأساسية فقط
    logger.info(f"Server: FastAPI + Flask on 0.0.0.0:{PORT}")
    logger.info(f"Blueprints loaded: {len(blueprints_loaded)}")
    
    if blueprints_failed:
        logger.warning(f"Failed blueprints: {len(blueprints_failed)}")
        for bp in blueprints_failed:
            logger.error(f"Blueprint failed: {bp}")
    
    # تشغيل الخدمات الإضافية
    start_daily_summary_service()
    start_background_services()  # ✅ بدء Daily Reset Scheduler
    
    # بدء مجدول تنظيف الإشعارات
    try:
        from backend.schedulers.notification_cleanup_scheduler import start_notification_scheduler
        notification_scheduler = start_notification_scheduler()
        if notification_scheduler:
            logger.info("✅ تم بدء مجدول تنظيف الإشعارات")
        else:
            logger.warning("⚠️ فشل بدء مجدول تنظيف الإشعارات")
    except Exception as e:
        logger.error(f"❌ خطأ في بدء مجدول تنظيف الإشعارات: {e}")
    
    # Startup confirmation with smart connection info
    print("")
    print("=" * 70)
    print("🚀 Trading AI Bot - Unified Server v1.0.0")
    print("=" * 70)
    print(f"✅ Server ready on http://0.0.0.0:{PORT}")
    print(f"📊 Blueprints: {len(blueprints_loaded)} loaded")
    print(f"📁 Logs: {LOG_FILE}")
    print("")
    print("📡 Connection URLs:")
    print(f"   Local:      http://localhost:{PORT}")
    print(f"   Network:    http://{LOCAL_IP}:{PORT}")
    print(f"   Emulator:   http://{EMULATOR_IP}:{PORT}")
    print("")
    print("📱 For Mobile App:")
    print(f"   • Android Emulator → Use: {EMULATOR_IP}")
    print(f"   • Real Device (WiFi) → Use: {LOCAL_IP}")
    print("")
    print(f"📋 API Docs: http://localhost:{PORT}/docs")
    print("=" * 70)
    print("")
    
    # ============================================================
    # تشغيل Uvicorn مع آلية إعادة التشغيل التلقائي
    # ============================================================
    
    MAX_RESTART_ATTEMPTS = 5
    RESTART_DELAY = 5  # ثواني
    restart_count = 0
    
    while restart_count < MAX_RESTART_ATTEMPTS:
        try:
            logger.info(f"🚀 بدء الخادم (المحاولة {restart_count + 1}/{MAX_RESTART_ATTEMPTS})")
            
            uvicorn.run(
                app,
                host="0.0.0.0",
                port=PORT,
                log_level="warning",
                access_log=False
            )
            
            # إذا وصلنا هنا، الخادم توقف بشكل طبيعي
            logger.info("🛑 الخادم توقف بشكل طبيعي")
            break
            
        except KeyboardInterrupt:
            logger.info("🛑 تم إيقاف الخادم من قبل المستخدم")
            break
            
        except SystemExit as e:
            # إيقاف مقصود
            logger.info(f"🛑 إيقاف النظام: {e}")
            break
            
        except Exception as e:
            restart_count += 1
            logger.error(f"❌ خطأ في الخادم: {e}", exc_info=True)
            
            if restart_count < MAX_RESTART_ATTEMPTS:
                logger.warning(f"🔄 إعادة التشغيل خلال {RESTART_DELAY} ثواني...")
                time.sleep(RESTART_DELAY)
                
                # إعادة فحص المنفذ
                if not ensure_port_available(PORT):
                    logger.error(f"❌ فشل تحرير المنفذ {PORT}")
                    break
            else:
                logger.critical(f"❌ فشل الخادم بعد {MAX_RESTART_ATTEMPTS} محاولات")
                sys.exit(1)
    
    logger.info("👋 انتهاء عمل الخادم")
