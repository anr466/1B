# 🚀 Trading AI Bot - نظام التداول الذكي المتكامل

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![React Native](https://img.shields.io/badge/React%20Native-0.70+-green.svg)](https://reactnative.dev)
[![Flask](https://img.shields.io/badge/Flask-2.0+-red.svg)](https://flask.palletsprojects.com)
[![SQLite](https://img.shields.io/badge/SQLite-3.0+-yellow.svg)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-Proprietary-purple.svg)]()

## 📋 نظرة عامة

نظام تداول ذكي متكامل يجمع بين الذكاء الاصطناعي وتحليل البيانات المالية لتوفير حلول تداول احترافية. يتضمن النظام تطبيق محمول باللغة العربية، نظام خلفية قوي، وآليات تعلم آلي متطورة.

### ✨ المميزات الرئيسية

- 🤖 **تداول ذكي**: نظام تداول مؤتمت مع خوارزميات متطورة
- 📱 **تطبيق محمول**: واجهة عربية بالكامل مع UX متطور
- 🛡️ **أمان متقدم**: تشفير البيانات، JWT، ومصادقة بيومترية
- 📊 **تحليل ذكي**: تحليل فني متطور مع مؤشرات مخصصة
- 🔄 **تعلم آلي**: نظام تعلم تكيفي يحسن الأداء مع الوقت
- 🌐 **API شامل**: واجهات برمجية موثقة بالكامل
- 💾 **قاعدة بيانات محسنة**: SQLite مع تحسينات خاصة بالتداول

## 🏗️ المعمارية العامة

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Mobile App    │    │   Backend API   │    │   ML Engine     │
│  (React Native) │◄──►│    (Flask)      │◄──►│   (Python)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        │                       ▼                       │
        │              ┌─────────────────┐               │
        └──────────────►│  SQLite DB      │◄──────────────┘
                       │  (Optimized)    │
                       └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   Binance API   │
                    │   Integration   │
                    └─────────────────┘
```

## 📁 هيكل المشروع

```
trading_ai_bot/
├── 🐍 backend/                 # خدمات الخلفية
│   ├── api/                   # نقاط النهاية REST API
│   ├── core/                  # منطق التداول الأساسي
│   ├── cognitive/             # نظام التحليل المعرفي
│   ├── learning/              # خوارزميات التعلم الآلي
│   ├── strategies/            # استراتيجيات التداول
│   └── utils/                 # أدوات مشتركة
├── 📱 mobile_app/             # التطبيق المحمول
│   └── TradingApp/           # React Native App
├── 🗃️ database/              # قاعدة البيانات والهجرات
├── ⚙️ config/                # ملفات التكوين
├── 🔧 bin/                   # نصوص التشغيل والأتمتة
└── 📊 utils/                 # أدوات النظام
```

## 🚀 التشغيل السريع

### المتطلبات المسبقة

- Python 3.8+
- Node.js 16+
- React Native CLI
- Android Studio / Xcode
- SQLite 3

### 1. إعداد البيئة

```bash
# استنساخ المشروع
git clone <repository-url>
cd trading_ai_bot

# إنشاء البيئة الافتراضية
python -m venv venv
source venv/bin/activate  # Linux/Mac
# أو venv\Scripts\activate  # Windows

# تثبيت المتطلبات
pip install -r requirements.txt
```

### 2. تكوين البيئة

```bash
# نسخ ملف التكوين
cp .env.example .env

# تحرير المتغيرات (مطلوب!)
nano .env
```

### 3. إعداد قاعدة البيانات

```bash
# تشغيل الهجرات
python -c "from database.database_manager import DatabaseManager; DatabaseManager()._apply_migrations()"
```

### 4. تشغيل النظام

```bash
# تشغيل الخادم الخلفي
python start_server.py

# في terminal منفصل - تشغيل التطبيق المحمول
cd mobile_app/TradingApp
npm install
npx react-native run-android  # أو run-ios
```

## 🔧 التكوين المتقدم

### متغيرات البيئة الهامة

| المتغير | الوصف | المثال |
|---------|--------|---------|
| `JWT_SECRET_KEY` | مفتاح تشفير JWT | `your-secret-key` |
| `BINANCE_BACKEND_API_KEY` | مفتاح Binance API | `your-api-key` |
| `ENCRYPTION_KEY` | مفتاح تشفير البيانات | `fernet-key` |
| `DATABASE_PATH` | مسار قاعدة البيانات | `database/trading.db` |

### أوضاع التشغيل

- **Development**: للتطوير والاختبار
- **Production**: للبيئة الإنتاجية
- **Testing**: لتشغيل الاختبارات

## 🏛️ المكونات الرئيسية

### 1. نظام التداول (`backend/core/`)
- **GroupBSystem**: محرك التداول الرئيسي
- **TradingStateMachine**: إدارة حالات النظام
- **PositionManager**: إدارة المراكز المفتوحة
- **ScalpingEngine**: استراتيجية Scalping V7

### 2. النظام المعرفي (`backend/cognitive/`)
- **CognitiveOrchestrator**: المنسق الرئيسي للذكاء
- **MarketSurveillance**: مراقبة السوق المستمرة
- **MultiExitEngine**: نظام خروج متعدد المستويات

### 3. التعلم الآلي (`backend/learning/`)
- **AdaptiveOptimizer**: محسن تكيفي للمعاملات
- **DynamicBlacklist**: قائمة سوداء ديناميكية
- **SignalClassifier**: مصنف الإشارات الذكي

### 4. الواجهات (`backend/api/`)
- **AuthEndpoints**: مصادقة وتسجيل الدخول
- **TradingAPI**: عمليات التداول
- **AdminAPI**: لوحة تحكم المدير
- **MobileEndpoints**: واجهات التطبيق المحمول

## 📊 نظام قاعدة البيانات

### الجداول الرئيسية

- `users`: بيانات المستخدمين وإعدادات الحساب
- `active_positions`: المراكز المفتوحة الحالية
- `user_trades`: سجل التداولات المكتملة
- `portfolio`: أرصدة المحافظ الاستثمارية
- `system_status`: حالة النظام العامة
- `learning_validation_log`: سجل التعلم والتحقق

## 🔒 الأمان والخصوصية

### طبقات الحماية

1. **تشفير البيانات**: Fernet encryption للبيانات الحساسة
2. **JWT Tokens**: للمصادقة والتخويل
3. **bcrypt Hashing**: لكلمات المرور
4. **CORS Protection**: حماية من الطلبات الضارة
5. **Rate Limiting**: منع الهجمات بالفيض
6. **SQL Injection**: حماية من حقن SQL

### إدارة المفاتيح

- مفاتيح Binance مشفرة في قاعدة البيانات
- JWT keys في متغيرات البيئة
- Firebase credentials في ملفات منفصلة

## 📈 المراقبة والسجلات

### نظام السجلات

```
logs/
├── server.log      # سجلات الخادم العامة
├── trading.log     # عمليات التداول
├── errors.log      # الأخطاء والاستثناءات
└── audit.log       # سجل التدقيق الأمني
```

### المقاييس الرئيسية

- **نسبة النجاح**: معدل الصفقات الرابحة
- **عامل الربح**: إجمالي الأرباح / إجمالي الخسائر  
- **السحب الأقصى**: أكبر انخفاض في رأس المال
- **حجم المخاطرة**: نسبة المخاطرة لكل صفقة

## 🧪 الاختبار والجودة

### أنواع الاختبارات

```bash
# اختبارات الوحدة
python -m pytest backend/tests/unit/

# اختبارات التكامل  
python -m pytest backend/tests/integration/

# اختبارات النهاية للنهاية
python -m pytest backend/tests/e2e/

# اختبارات الأداء
python -m pytest backend/tests/performance/
```

### تقارير الجودة

- تغطية الكود: 85%+
- اختبارات مؤتمتة: 300+ اختبار
- فحص الأمان: دوري

## 📚 الوثائق التفصيلية

- [📖 دليل API](docs/API.md)
- [🏗️ معمارية النظام](docs/ARCHITECTURE.md)
- [🛡️ دليل الأمان](docs/SECURITY.md)
- [🚀 دليل النشر](docs/DEPLOYMENT.md)
- [🔧 استكشاف الأخطاء](docs/TROUBLESHOOTING.md)

## 🤝 المساهمة في المشروع

### قواعد المساهمة

1. Fork المشروع
2. إنشاء branch للميزة الجديدة
3. كتابة اختبارات شاملة
4. تحديث الوثائق
5. إرسال Pull Request

### معايير الكود

- Python: PEP 8 compliance
- JavaScript: ESLint + Prettier
- Git: Conventional Commits
- Tests: 90%+ coverage

## 📄 الترخيص

هذا المشروع محمي بحقوق الطبع والنشر. جميع الحقوق محفوظة.

## 🆘 الدعم والمساعدة

- 📧 Email: support@tradingbot.com  
- 📞 الدعم الفني: متوفر 24/7
- 📖 الوثائق: [docs.tradingbot.com](https://docs.tradingbot.com)
- 🐛 تقارير الأخطاء: GitHub Issues

---

**⚠️ تحذير مهم**: هذا نظام تداول حقيقي يتعامل مع أموال فعلية. تأكد من اختبار جميع الوظائف في البيئة التجريبية قبل التشغيل المباشر.

*آخر تحديث: فبراير 2026*
