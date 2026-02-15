#!/bin/bash

echo "🔍 تشخيص شامل لمشاكل التطبيق الجوال"
echo "=========================================="

# 1. فحص Node.js
echo ""
echo "1️⃣ فحص Node.js:"
node --version
npm --version

# 2. فحص React Native
echo ""
echo "2️⃣ فحص React Native:"
npx react-native --version

# 3. فحص المكتبات
echo ""
echo "3️⃣ فحص المكتبات المثبتة:"
if [ -d "node_modules" ]; then
    echo "✅ node_modules موجود"
    ls -lh node_modules | head -5
else
    echo "❌ node_modules غير موجود - تحتاج npm install"
fi

# 4. فحص Metro Bundler
echo ""
echo "4️⃣ فحص Metro Bundler:"
lsof -ti:8081 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Metro Bundler يعمل على المنفذ 8081"
else
    echo "⚠️ Metro Bundler متوقف"
fi

# 5. فحص الخادم الخلفي
echo ""
echo "5️⃣ فحص الخادم الخلفي (Port 3002):"
nc -z localhost 3002 > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ الخادم يعمل على المنفذ 3002"
    curl -s http://localhost:3002/health | head -3
else
    echo "❌ الخادم متوقف - تحتاج تشغيل: python3 bin/unified_server.py"
fi

# 6. فحص Android Environment
echo ""
echo "6️⃣ فحص Android Environment:"
if [ -n "$ANDROID_HOME" ]; then
    echo "✅ ANDROID_HOME = $ANDROID_HOME"
else
    echo "⚠️ ANDROID_HOME غير معرّف"
fi

# 7. فحص Java
echo ""
echo "7️⃣ فحص Java:"
java -version 2>&1 | head -1

# 8. فحص الأجهزة المتصلة
echo ""
echo "8️⃣ فحص الأجهزة المتصلة:"
adb devices 2>&1 | tail -n +2

# 9. فحص الملفات الحرجة
echo ""
echo "9️⃣ فحص الملفات الحرجة:"
files=(
    "package.json"
    "babel.config.js"
    "metro.config.js"
    "index.js"
    "App.js"
    ".eslintrc.js"
    "android/app/build.gradle"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ $file غير موجود"
    fi
done

# 10. فحص Cache
echo ""
echo "🔟 فحص Cache:"
if [ -d "android/app/build" ]; then
    echo "✅ android/app/build موجود"
else
    echo "⚠️ android/app/build غير موجود"
fi

echo ""
echo "=========================================="
echo "✅ انتهى التشخيص"
echo ""
echo "📋 الخطوات التالية:"
echo "  1. إذا كان Metro متوقف: npm start"
echo "  2. إذا كان الخادم متوقف: cd ../.. && python3 bin/unified_server.py"
echo "  3. إذا كانت المكتبات ناقصة: npm install"
echo "  4. لتنظيف Cache: npm run clean && npm start --reset-cache"
echo "  5. لإعادة البناء: cd android && ./gradlew clean && cd .. && npx react-native run-android"
