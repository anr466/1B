# 🔥 إعداد Firebase Service Account

## 📋 الخطوات المطلوبة

### 1️⃣ إنشاء مشروع Firebase

1. اذهب إلى [Firebase Console](https://console.firebase.google.com/)
2. اضغط على **Add project** أو **إضافة مشروع**
3. أدخل اسم المشروع (مثلاً: `trading-ai-bot`)
4. اتبع الخطوات حتى إنشاء المشروع

---

### 2️⃣ تفعيل Cloud Messaging

1. في لوحة Firebase، اذهب إلى **Project Settings** (⚙️ الإعدادات)
2. اذهب إلى تبويب **Cloud Messaging**
3. تأكد من تفعيل **Firebase Cloud Messaging API (V1)**

---

### 3️⃣ إنشاء Service Account

1. في **Project Settings** → **Service accounts**
2. اضغط على **Generate new private key**
3. سيتم تنزيل ملف JSON (احتفظ به بشكل آمن)

---

### 4️⃣ إضافة الملف للمشروع

**الطريقة 1: النسخ المباشر (موصى به)**
```bash
# انسخ الملف الذي تم تنزيله إلى المشروع
cp ~/Downloads/your-project-xxxx.json config/security/firebase-service-account.json
```

**الطريقة 2: استخدام المثال**
```bash
# انسخ الملف النموذجي وعدّله
cp config/security/firebase-service-account.example.json config/security/firebase-service-account.json

# ثم عدّل الملف بمحرر النصوص وأضف بياناتك الفعلية
nano config/security/firebase-service-account.json
```

---

### 5️⃣ حماية الملف

```bash
# تأكد من أن الملف غير مدرج في git
echo "config/security/firebase-service-account.json" >> .gitignore

# تعيين صلاحيات محدودة
chmod 600 config/security/firebase-service-account.json
```

---

### 6️⃣ التحقق من التكوين

```bash
# اختبار Firebase Service
python -c "
from utils.firebase_notification_service import FirebaseNotificationService
service = FirebaseNotificationService()
print('✅ Firebase متصل' if service.is_available() else '❌ Firebase غير متصل')
"
```

---

## 🔐 الأمان

### ⚠️ تحذيرات مهمة:

1. **لا تشارك ملف Service Account مع أحد**
2. **لا ترفع الملف على GitHub أو أي مستودع عام**
3. **استخدم `.gitignore` دائماً**
4. **قم بتدوير المفاتيح كل 90 يوم** (من Firebase Console)

### ✅ أفضل الممارسات:

- احفظ نسخة احتياطية في مكان آمن ومشفر
- استخدم متغيرات البيئة في الإنتاج (Production)
- راقب استخدام Firebase من لوحة التحكم

---

## 📱 اختبار Push Notifications

بعد إضافة الملف، يمكنك اختبار الإشعارات:

```python
from utils.firebase_notification_service import FirebaseNotificationService

# تهيئة الخدمة
service = FirebaseNotificationService()

# إرسال إشعار تجريبي
if service.is_available():
    # ستحتاج FCM Token من التطبيق
    service.send_notification(
        user_id=1,
        title="اختبار الإشعار",
        body="هذا إشعار تجريبي من النظام",
        data={"type": "test"}
    )
    print("✅ تم إرسال الإشعار")
else:
    print("❌ Firebase غير متاح")
```

---

## 🔧 استكشاف الأخطاء

### المشكلة: "Service Account غير موجود"
**الحل:** تأكد من وجود الملف في المسار الصحيح:
```
config/security/firebase-service-account.json
```

### المشكلة: "Firebase Admin SDK غير متوفر"
**الحل:** تثبيت المكتبة:
```bash
pip install firebase-admin
```

### المشكلة: "Invalid private key"
**الحل:** تأكد من نسخ المفتاح الخاص بشكل صحيح مع جميع الأسطر والمسافات

---

## 📊 الحد الأقصى للاستخدام

Firebase Cloud Messaging مجاني للاستخدام العادي:
- **رسائل غير محدودة** للأجهزة المسجلة
- **لا توجد رسوم** على الإشعارات العادية

---

## 🆘 الدعم

إذا واجهت أي مشكلة:
1. راجع [Firebase Documentation](https://firebase.google.com/docs/admin/setup)
2. تحقق من Logs: `logs/server.log`
3. تأكد من صلاحيات Service Account في Firebase Console
