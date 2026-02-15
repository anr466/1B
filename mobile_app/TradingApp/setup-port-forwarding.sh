#!/bin/bash

# 🔌 سكريبت توجيه المنافذ الذكي
# يوجه المنافذ من الجهاز إلى الكمبيوتر تلقائياً

set -e

echo ""
echo "🔌 إعداد توجيه المنافذ (Port Forwarding)"
echo "=========================================="
echo ""

# 1️⃣ التحقق من الجهاز
echo "1️⃣ البحث عن الجهاز المتصل..."
DEVICE=$(adb devices | grep -v "List of" | grep "device$" | head -1 | awk '{print $1}')

if [ -z "$DEVICE" ]; then
  echo "❌ لا يوجد جهاز متصل!"
  echo "   تأكد من توصيل الجهاز عبر USB"
  exit 1
fi

echo "✅ الجهاز المتصل: $DEVICE"
echo ""

# 2️⃣ إزالة التوجيهات القديمة
echo "2️⃣ إزالة التوجيهات القديمة..."
adb forward --remove-all 2>/dev/null || true
sleep 1
echo "✅ تم إزالة التوجيهات القديمة"
echo ""

# 3️⃣ إعداد توجيه المنافذ الجديدة
echo "3️⃣ إعداد توجيه المنافذ الجديدة..."
echo ""

# Backend (3002)
echo "   📡 Backend: localhost:3002 → device:3002"
adb forward tcp:3002 tcp:3002
echo "   ✅ تم توجيه المنفذ 3002"

# Metro (8081)
echo "   📡 Metro: localhost:8081 → device:8081"
adb forward tcp:8081 tcp:8081
echo "   ✅ تم توجيه المنفذ 8081"

echo ""

# 4️⃣ التحقق من التوجيهات
echo "4️⃣ التحقق من التوجيهات..."
echo ""
adb forward --list
echo ""

# 5️⃣ اختبار الاتصال
echo "5️⃣ اختبار الاتصال..."
echo ""

echo "   🧪 اختبار Backend..."
if adb shell curl -s http://localhost:3002/health > /dev/null 2>&1; then
  echo "   ✅ Backend متصل"
else
  echo "   ⚠️ Backend غير متصل (تأكد من تشغيل الخادم)"
fi

echo "   🧪 اختبار Metro..."
if adb shell curl -s http://localhost:8081/status > /dev/null 2>&1; then
  echo "   ✅ Metro متصل"
else
  echo "   ⚠️ Metro غير متصل (تأكد من تشغيل Metro)"
fi

echo ""
echo "✅ تم إعداد توجيه المنافذ بنجاح!"
echo ""
echo "📋 الآن يمكن للتطبيق الاتصال بـ:"
echo "   - Backend: http://localhost:3002"
echo "   - Metro: http://localhost:8081"
echo ""
