#!/bin/bash

# 📱 سكريبت تشغيل التطبيق على الجهاز المتصل
# يتحقق من كل شيء ويشغل التطبيق بأمان

set -e

echo ""
echo "📱 تشغيل التطبيق على الجهاز المتصل"
echo "======================================"
echo ""

# 1️⃣ التحقق من الجهاز
echo "1️⃣ التحقق من الجهاز المتصل..."
DEVICE=$(adb devices | grep -v "List of" | grep "device$" | head -1 | awk '{print $1}')

if [ -z "$DEVICE" ]; then
  echo "❌ لا يوجد جهاز متصل!"
  echo "   تأكد من توصيل الجهاز عبر USB"
  exit 1
fi

echo "✅ الجهاز المتصل: $DEVICE"
echo ""

# 2️⃣ التحقق من الخادم
echo "2️⃣ التحقق من الخادم..."
if ! curl -s http://localhost:3002/health > /dev/null 2>&1; then
  echo "❌ الخادم غير متصل على http://localhost:3002"
  echo "   تأكد من تشغيل الخادم: python3 bin/unified_server.py"
  exit 1
fi

echo "✅ الخادم يعمل على http://localhost:3002"
echo ""

# 3️⃣ التحقق من Metro
echo "3️⃣ التحقق من Metro..."
if ! curl -s http://localhost:8081/status > /dev/null 2>&1; then
  echo "⚠️ Metro لم يبدأ بعد - سيتم بدؤه الآن..."
  bash start-safe.sh &
  METRO_PID=$!
  sleep 15
  echo "✅ Metro بدأ بـ PID: $METRO_PID"
else
  echo "✅ Metro يعمل على http://localhost:8081"
fi

echo ""

# 4️⃣ بناء وتثبيت التطبيق
echo "4️⃣ بناء وتثبيت التطبيق على الجهاز..."
cd /Users/anr/Desktop/trading_ai_bot/mobile_app/TradingApp

npx react-native run-android \
  --deviceId="$DEVICE" \
  --verbose

echo ""
echo "✅ تم تشغيل التطبيق بنجاح!"
echo ""
echo "📊 معلومات الاتصال:"
echo "   - الجهاز: $DEVICE"
echo "   - الخادم: http://localhost:3002"
echo "   - Metro: http://localhost:8081"
echo ""
