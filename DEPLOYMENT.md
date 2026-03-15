# 🚀 دليل النشر - Deployment Guide

<div dir="rtl">

## 📋 جدول المحتويات

1. [متطلبات النشر](#متطلبات-النشر)
2. [نشر Backend](#نشر-backend)
3. [نشر Flutter App](#نشر-flutter-app)
4. [إعداد قاعدة البيانات](#إعداد-قاعدة-البيانات)
5. [إعداد SSL/TLS](#إعداد-ssltls)
6. [المراقبة والصيانة](#المراقبة-والصيانة)
7. [استكشاف الأخطاء](#استكشاف-الأخطاء)

---

## 🔧 متطلبات النشر

### خادم الإنتاج (Production Server)
- **OS**: Ubuntu 20.04+ / Debian 11+
- **RAM**: 2GB minimum, 4GB recommended
- **CPU**: 2 cores minimum
- **Storage**: 20GB SSD
- **Python**: 3.9+
- **Domain**: اسم نطاق مع SSL certificate

### متطلبات إضافية
- Nginx (reverse proxy)
- Supervisor (process management)
- Let's Encrypt (SSL certificates)
- Binance API Keys (production)

---

## 🐍 نشر Backend

### 1️⃣ إعداد الخادم

```bash
# تحديث النظام
sudo apt update && sudo apt upgrade -y

# تثبيت Dependencies
sudo apt install -y python3.9 python3.9-venv python3-pip nginx supervisor git sqlite3

# إنشاء مستخدم للتطبيق
sudo useradd -m -s /bin/bash tradingbot
sudo su - tradingbot
```

### 2️⃣ نسخ المشروع

```bash
# استنساخ المشروع
cd /home/tradingbot
git clone <repository-url> trading_ai_bot
cd trading_ai_bot

# إنشاء بيئة افتراضية
python3.9 -m venv .venv
source .venv/bin/activate

# تثبيت dependencies الإنتاج
pip install --upgrade pip
pip install -r requirements-prod.txt
```

### 3️⃣ إعداد ملف البيئة

```bash
# نسخ ملف البيئة
cp .env.example .env

# تعديل القيم
nano .env
```

**ملف `.env` للإنتاج:**
```env
# Binance API (PRODUCTION)
BINANCE_API_KEY=your_production_api_key
BINANCE_API_SECRET=your_production_api_secret
BINANCE_TESTNET=False

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=3002
DEBUG_MODE=False
LOG_LEVEL=INFO

# Security
JWT_SECRET_KEY=<generate-random-64-char-string>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
ENCRYPTION_KEY=<generate-random-32-byte-key>

# Database
DB_PATH=/home/tradingbot/trading_ai_bot/database/trading_database.db
DB_BACKUP_PATH=/home/tradingbot/backups/

# Trading Settings
DEFAULT_RISK_PERCENTAGE=0.5
MAX_POSITIONS_PER_USER=10
TRADING_ENABLED=True

# Rate Limiting
RATE_LIMIT_ENABLED=True
MAX_REQUESTS_PER_MINUTE=60

# Monitoring
ENABLE_PROMETHEUS=True
METRICS_PORT=9090
```

### 4️⃣ إنشاء مفاتيح آمنة

```python
# توليد JWT Secret Key
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# توليد Encryption Key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 5️⃣ إعداد Database

```bash
# إنشاء مجلد database
mkdir -p /home/tradingbot/trading_ai_bot/database
mkdir -p /home/tradingbot/backups

# تشغيل migrations
python3 -c "
from database.database_manager import DatabaseManager
db = DatabaseManager()
db._apply_migrations()
print('✅ Migrations applied')
"

# إنشاء admin user
python3 -c "
from database.database_manager import DatabaseManager
import bcrypt
db = DatabaseManager()
with db.get_write_connection() as conn:
    hashed = bcrypt.hashpw(b'YOUR_SECURE_PASSWORD', bcrypt.gensalt()).decode()
    conn.execute('''
        INSERT OR REPLACE INTO users (id, username, email, password_hash, is_admin, trading_enabled)
        VALUES (1, 'admin', 'admin@yourdomain.com', ?, 1, 1)
    ''', (hashed,))
print('✅ Admin user created')
"
```

### 6️⃣ إعداد Supervisor

```bash
# إنشاء ملف supervisor config
sudo nano /etc/supervisor/conf.d/tradingbot.conf
```

**محتوى الملف:**
```ini
[program:tradingbot]
command=/home/tradingbot/trading_ai_bot/.venv/bin/python3 /home/tradingbot/trading_ai_bot/start_server.py
directory=/home/tradingbot/trading_ai_bot
user=tradingbot
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/tradingbot/trading_ai_bot/logs/supervisor.log
stderr_logfile=/home/tradingbot/trading_ai_bot/logs/supervisor_error.log
environment=HOME="/home/tradingbot",USER="tradingbot"

[program:tradingbot_background]
command=/home/tradingbot/trading_ai_bot/.venv/bin/python3 /home/tradingbot/trading_ai_bot/bin/background_trading_manager.py
directory=/home/tradingbot/trading_ai_bot
user=tradingbot
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/home/tradingbot/trading_ai_bot/logs/background.log
stderr_logfile=/home/tradingbot/trading_ai_bot/logs/background_error.log
```

```bash
# تحديث supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start tradingbot
sudo supervisorctl start tradingbot_background

# التحقق من الحالة
sudo supervisorctl status
```

### 7️⃣ إعداد Nginx

```bash
sudo nano /etc/nginx/sites-available/tradingbot
```

**محتوى الملف:**
```nginx
upstream tradingbot_backend {
    server 127.0.0.1:3002;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    # إعادة توجيه HTTP إلى HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL Configuration (سيتم إضافتها بواسطة Certbot)
    # ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000" always;

    # Logging
    access_log /var/log/nginx/tradingbot_access.log;
    error_log /var/log/nginx/tradingbot_error.log;

    # Client Body Size (for file uploads)
    client_max_body_size 10M;

    # Timeouts
    proxy_connect_timeout 600;
    proxy_send_timeout 600;
    proxy_read_timeout 600;
    send_timeout 600;

    location / {
        proxy_pass http://tradingbot_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket Support
    location /ws {
        proxy_pass http://tradingbot_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Health Check Endpoint (لا يحتاج authentication)
    location /health {
        proxy_pass http://tradingbot_backend;
        access_log off;
    }
}
```

```bash
# تفعيل الموقع
sudo ln -s /etc/nginx/sites-available/tradingbot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 8️⃣ إعداد SSL مع Let's Encrypt

```bash
# تثبيت Certbot
sudo apt install -y certbot python3-certbot-nginx

# الحصول على شهادة SSL
sudo certbot --nginx -d api.yourdomain.com

# التجديد التلقائي (يتم إعداده تلقائياً)
sudo certbot renew --dry-run
```

---

## 📱 نشر Flutter App

### 1️⃣ إعداد ملف الإنتاج

```bash
cd flutter_trading_app
nano lib/core/constants/api_endpoints.dart
```

**تحديث baseUrl للإنتاج:**
```dart
class ApiEndpoints {
  static const String baseUrl = 'https://api.yourdomain.com/api';
  // ... باقي الـ endpoints
}
```

### 2️⃣ بناء APK للأندرويد

```bash
# Clean build
flutter clean
flutter pub get

# Build production APK
flutter build apk --release --split-per-abi

# أو build App Bundle للـ Play Store
flutter build appbundle --release
```

**الملفات الناتجة:**
```
build/app/outputs/flutter-apk/
├── app-armeabi-v7a-release.apk  (32-bit ARM)
├── app-arm64-v8a-release.apk    (64-bit ARM)
└── app-x86_64-release.apk       (Intel x64)
```

### 3️⃣ بناء IPA للـ iOS

```bash
# تنظيف
flutter clean
flutter pub get

# Build iOS (يتطلب macOS + Xcode)
flutter build ios --release

# فتح Xcode للأرشفة
open ios/Runner.xcworkspace
```

**في Xcode:**
1. Product → Archive
2. Distribute App
3. اختر App Store Connect أو Ad Hoc
4. اتبع خطوات التوزيع

### 4️⃣ توقيع التطبيق

**للأندرويد:**
```bash
# إنشاء keystore (مرة واحدة فقط)
keytool -genkey -v -keystore upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload

# حفظ في android/key.properties
nano android/key.properties
```

```properties
storePassword=<your-store-password>
keyPassword=<your-key-password>
keyAlias=upload
storeFile=../upload-keystore.jks
```

⚠️ **مهم:** لا ترفع `key.properties` أو `.jks` إلى Git!

### 5️⃣ نشر على المتاجر

**Google Play Store:**
1. إنشاء حساب Google Play Developer
2. رفع `app-release.aab`
3. إكمال صفحة التطبيق
4. إرسال للمراجعة

**Apple App Store:**
1. إنشاء حساب Apple Developer
2. استخدام Xcode لرفع IPA
3. إكمال App Store Connect
4. إرسال للمراجعة

---

## 🗄️ إعداد قاعدة البيانات

### Backup التلقائي

```bash
# إنشاء script للنسخ الاحتياطي
nano /home/tradingbot/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/tradingbot/backups"
DB_PATH="/home/tradingbot/trading_ai_bot/database/trading_database.db"
DATE=$(date +%Y%m%d_%H%M%S)

# إنشاء نسخة احتياطية
sqlite3 $DB_PATH ".backup $BACKUP_DIR/db_backup_$DATE.db"

# حذف النسخ الأقدم من 7 أيام
find $BACKUP_DIR -name "db_backup_*.db" -mtime +7 -delete

echo "✅ Backup completed: db_backup_$DATE.db"
```

```bash
# جعل الـ script قابل للتنفيذ
chmod +x /home/tradingbot/backup.sh

# إضافة إلى crontab (كل 6 ساعات)
crontab -e
```

```cron
0 */6 * * * /home/tradingbot/backup.sh >> /home/tradingbot/logs/backup.log 2>&1
```

### تحسين الأداء

```sql
-- تشغيل من sqlite3 console
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
PRAGMA temp_store=memory;
PRAGMA mmap_size=30000000000;
```

---

## 🔐 إعداد SSL/TLS

### تثبيت شهادة SSL

```bash
# باستخدام Let's Encrypt (مجاني)
sudo certbot --nginx -d api.yourdomain.com

# التجديد التلقائي
sudo certbot renew --dry-run
```

### Force HTTPS

في `start_server.py`، تأكد من:
```python
if not DEBUG_MODE:
    # Force HTTPS in production
    app.add_middleware(
        HTTPSRedirectMiddleware
    )
```

---

## 📊 المراقبة والصيانة

### 1️⃣ Log Monitoring

```bash
# مراقبة logs الرئيسية
tail -f /home/tradingbot/trading_ai_bot/logs/supervisor.log

# مراقبة background trading
tail -f /home/tradingbot/trading_ai_bot/logs/background.log

# مراقبة nginx
tail -f /var/log/nginx/tradingbot_error.log
```

### 2️⃣ System Health Checks

```bash
# التحقق من صحة Backend
curl https://api.yourdomain.com/health

# التحقق من Supervisor
sudo supervisorctl status

# التحقق من Nginx
sudo nginx -t
sudo systemctl status nginx

# استخدام الذاكرة
free -h

# استخدام المساحة
df -h
```

### 3️⃣ تنظيف Logs التلقائي

```bash
# إضافة إلى crontab
crontab -e
```

```cron
# تنظيف logs أقدم من 30 يوم (كل يوم الساعة 2 صباحاً)
0 2 * * * find /home/tradingbot/trading_ai_bot/logs -name "*.log" -mtime +30 -delete
```

### 4️⃣ إعداد Alerts

استخدام Telegram Bot للتنبيهات:

```python
# في config/config.json
{
  "telegram": {
    "enabled": true,
    "bot_token": "YOUR_BOT_TOKEN",
    "admin_chat_ids": [123456789]
  }
}
```

---

## 🐛 استكشاف الأخطاء

### Backend لا يعمل

```bash
# التحقق من logs
tail -100 /home/tradingbot/trading_ai_bot/logs/supervisor.log

# إعادة تشغيل
sudo supervisorctl restart tradingbot

# التحقق من المنفذ
sudo netstat -tulpn | grep 3002
```

### Database مقفلة

```bash
# التحقق من العمليات المفتوحة
fuser /home/tradingbot/trading_ai_bot/database/trading_database.db

# إغلاق العمليات العالقة
sudo supervisorctl restart tradingbot
sudo supervisorctl restart tradingbot_background
```

### Nginx 502 Bad Gateway

```bash
# التحقق من Backend
curl http://127.0.0.1:3002/health

# التحقق من Nginx config
sudo nginx -t

# إعادة تشغيل
sudo systemctl restart nginx
```

### SSL Certificate منتهية

```bash
# تجديد يدوي
sudo certbot renew

# إعادة تحميل Nginx
sudo systemctl reload nginx
```

---

## 🔄 تحديث التطبيق

### Backend Update

```bash
# إيقاف الخدمات
sudo supervisorctl stop tradingbot
sudo supervisorctl stop tradingbot_background

# جلب التحديثات
cd /home/tradingbot/trading_ai_bot
git pull origin main

# تحديث dependencies
source .venv/bin/activate
pip install -r requirements-prod.txt --upgrade

# تشغيل migrations
python3 -c "from database.database_manager import DatabaseManager; DatabaseManager()._apply_migrations()"

# إعادة تشغيل
sudo supervisorctl start tradingbot
sudo supervisorctl start tradingbot_background

# التحقق
sudo supervisorctl status
```

### Flutter App Update

```bash
cd flutter_trading_app
git pull origin main
flutter pub get
flutter build apk --release
# ثم رفع إلى Play Store/App Store
```

---

## 📈 مقاييس الأداء

### Monitoring Checklist

- [ ] CPU Usage < 70%
- [ ] RAM Usage < 80%
- [ ] Disk Space > 20% free
- [ ] Response time < 500ms
- [ ] Error rate < 1%
- [ ] Database size manageable
- [ ] Logs rotating properly
- [ ] Backups running daily
- [ ] SSL certificate valid
- [ ] All services running

---

## 🆘 جهات الاتصال للدعم

- **Backend Issues**: backend-team@yourdomain.com
- **Flutter Issues**: mobile-team@yourdomain.com
- **Infrastructure**: devops@yourdomain.com
- **Emergency**: +XX XXX XXX XXXX

---

## ✅ Production Checklist

قبل النشر للإنتاج، تأكد من:

- [ ] تغيير جميع كلمات المرور الافتراضية
- [ ] تفعيل SSL/TLS
- [ ] إعداد backup تلقائي
- [ ] تكوين monitoring & alerts
- [ ] اختبار disaster recovery
- [ ] مراجعة أذونات الملفات
- [ ] تأمين API keys
- [ ] إعداد rate limiting
- [ ] اختبار load testing
- [ ] توثيق الإعدادات

</div>
