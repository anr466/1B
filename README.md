# 🤖 Trading AI Bot - نظام التداول الآلي الذكي

<div dir="rtl">

## 📋 نظرة عامة

نظام تداول آلي ذكي متكامل يجمع بين:
- **Backend API** (Python/FastAPI + Flask)
- **Flutter Mobile App** (iOS/Android)
- **Machine Learning** (تحليل ذكي للأسواق)
- **Multi-Strategy Trading** (استراتيجيات تداول متعددة)

---

## 🏗️ البنية المعمارية

```
trading_ai_bot-1/
├── backend/              # Backend API (Python)
│   ├── api/             # Flask/FastAPI endpoints
│   ├── core/            # Group B Trading System
│   ├── services/        # Business logic
│   └── utils/           # Error logging, validators
├── flutter_trading_app/ # Flutter Mobile App
│   ├── lib/
│   │   ├── core/       # Services, repositories
│   │   ├── design/     # Design system, tokens
│   │   └── features/   # Screens (auth, portfolio, admin)
├── database/            # SQLite database
├── config/              # Configuration files
├── tests/               # Unit & integration tests
└── start_server.py      # Main entry point
```

---

## ✨ المميزات الرئيسية

### 🎯 نظام التداول
- ✅ تداول آلي على Binance
- ✅ استراتيجيات متعددة (SCALP_V8, MOMENTUM, etc.)
- ✅ إدارة مخاطر متقدمة (Kelly Criterion)
- ✅ Trailing Stop Loss ديناميكي
- ✅ Smart Money Flow Analysis
- ✅ Liquidity Filter & Market Regime Detection

### 🧠 Machine Learning
- ✅ تحليل ذكي للسوق
- ✅ Dynamic Blacklist للعملات السيئة
- ✅ Adaptive Symbol Selection
- ✅ ML Training Manager
- ✅ Performance Optimizer

### 📱 تطبيق الجوال
- ✅ مراقبة محفظة لحظية
- ✅ إدارة صفقات نشطة
- ✅ تنبيهات فورية
- ✅ لوحة تحكم للأدمن
- ✅ إدارة مستخدمين
- ✅ سجل أخطاء النظام متقدم

### 🛡️ الأمان
- ✅ JWT Authentication
- ✅ 2FA/OTP Support
- ✅ Biometric Authentication
- ✅ Secure Actions Verification
- ✅ Encrypted API Keys Storage

---

## 🚀 التثبيت السريع

### المتطلبات
- Python 3.9+
- Flutter 3.x
- SQLite3
- Binance API Keys

### 1️⃣ تثبيت Backend

```bash
# استنساخ المشروع
git clone <repository-url>
cd trading_ai_bot-1

# إنشاء بيئة افتراضية
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# تثبيت dependencies
pip install -r requirements.txt

# إعداد ملف البيئة
cp .env.example .env
# ✏️ عدّل .env وأضف Binance API keys

# تشغيل الخادم
python3 start_server.py
```

الخادم سيعمل على: `http://localhost:3002`

### 2️⃣ تثبيت Flutter App

```bash
cd flutter_trading_app

# تثبيت dependencies
flutter pub get

# تشغيل التطبيق
flutter run -d <device-id>
```

للأجهزة الحقيقية عبر USB:
```bash
# توجيه port 3002
adb -s <device-id> reverse tcp:3002 tcp:3002
flutter run -d <device-id>
```

---

## 🔧 الإعداد

### ملف `.env`

```env
# Binance API
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_api_secret_here

# Server
SERVER_PORT=3002
DEBUG_MODE=False

# Security
JWT_SECRET_KEY=your_secure_random_key_here
ENCRYPTION_KEY=your_32_byte_key_here

# Trading
DEFAULT_RISK_PERCENTAGE=1.0
MAX_POSITIONS_PER_USER=10
```

### حساب Admin الافتراضي

```
Email: admin@tradingbot.com
Password: admin123
```

⚠️ **مهم:** غيّر هذه البيانات فوراً بعد أول تسجيل دخول!

---

## 📊 استخدام النظام

### 1️⃣ تشغيل التداول
```bash
# من لوحة الأدمن في التطبيق
Admin Dashboard → Trading Control → Start Trading
```

### 2️⃣ مراقبة الصفقات
```bash
# من شاشة Portfolio
Portfolio → Active Positions
```

### 3️⃣ إدارة الأخطاء
```bash
# من لوحة الأدمن
Admin → System Logs → View Errors
```

---

## 🧪 الاختبارات

```bash
# اختبارات Backend
pytest tests/ -v

# اختبارات محددة
pytest tests/test_group_b_system.py -v

# اختبار مع coverage
pytest tests/ --cov=backend --cov-report=html
```

---

## 📝 البنية التقنية

### Backend Stack
- **FastAPI** - Modern async API framework
- **Flask** - Legacy endpoints compatibility
- **SQLite** - Lightweight database
- **APScheduler** - Background task scheduling
- **ccxt** - Cryptocurrency exchange integration
- **pandas/numpy** - Data analysis

### Flutter Stack
- **Riverpod** - State management
- **GoRouter** - Declarative routing
- **Dio** - HTTP client
- **shared_preferences** - Local storage
- **local_auth** - Biometric authentication

### Trading Components
- **Group B System** - Main trading engine
- **Strategy Interface** - Pluggable strategies
- **Risk Manager** - Position sizing & risk gates
- **Data Provider** - Historical data caching
- **ML Components** - Smart signal enhancement

---

## 🔐 الأمان

### Best Practices المطبقة:
- ✅ API Keys محفوظة encrypted في database
- ✅ JWT tokens مع expiration
- ✅ Rate limiting على endpoints حساسة
- ✅ Input validation شاملة
- ✅ SQL injection protection (parameterized queries)
- ✅ CORS configured properly
- ✅ Secure password hashing (bcrypt)

---

## 🐛 نظام حل الأخطاء

النظام يحتوي على **Error Logger** متقدم:

### الميزات:
- **Fingerprinting**: تجميع الأخطاء المتشابهة
- **Auto-Classification**: تصنيف تلقائي لنوع الخطأ
- **Self-Healing**: إصلاح تلقائي للأخطاء الشائعة
- **Escalation**: تصعيد للأدمن بعد محاولات فاشلة
- **Deduplication**: منع تكرار آلاف الأخطاء المتماثلة

### الاستخدام:
```python
from backend.utils.error_logger import ErrorLogger, ErrorLevel, ErrorSource

logger = ErrorLogger()
logger.log_error(
    level=ErrorLevel.ERROR,
    source=ErrorSource.GROUP_B,
    message="Failed to execute trade",
    details="Symbol: BTCUSDT, Reason: Insufficient balance",
    include_traceback=True
)
```

---

## 📈 الأداء والتحسينات

### Database Optimization
- Indexed queries على `system_errors`, `trades`, `active_positions`
- Connection pooling للـ concurrent requests
- Write-ahead logging (WAL) mode لـ SQLite

### Caching Strategy
- Historical data caching (60s TTL)
- User portfolio caching (30s TTL)
- Rate limit على Binance API

### Background Services
- Auto-cleanup للـ logs القديمة
- Daily database maintenance
- Position monitoring loop

---

## 🤝 المساهمة

راجع `CONTRIBUTING.md` لمعرفة كيفية المساهمة في المشروع.

---

## 📄 الترخيص

هذا المشروع خاص. جميع الحقوق محفوظة.

---

## 🆘 الدعم الفني

للدعم أو الاستفسارات:
- 📧 Email: support@tradingbot.com
- 📱 Telegram: @TradingBotSupport

---

## ⚠️ تنبيه قانوني

هذا النظام للأغراض التعليمية فقط. التداول في العملات الرقمية يحمل مخاطر عالية. استخدم المشروع على مسؤوليتك الخاصة.

</div>
