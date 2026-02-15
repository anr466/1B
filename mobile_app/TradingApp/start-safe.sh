#!/bin/bash

# 🚀 سكريبت بدء آمن للتطبيق
# يحل مشاكل Metro والاتصال تلقائياً

set -e

echo ""
echo "🚀 بدء التطبيق بشكل آمن"
echo "=========================="
echo ""

# 1️⃣ إيقاف جميع عمليات Metro القديمة
echo "1️⃣ إيقاف عمليات Metro القديمة..."
pkill -9 -f "metro start" 2>/dev/null || true
pkill -9 -f "npm start" 2>/dev/null || true
sleep 2
echo "✅ تم إيقاف العمليات القديمة"
echo ""

# 2️⃣ تنظيف Cache
echo "2️⃣ تنظيف Cache..."
rm -rf node_modules/.cache 2>/dev/null || true
rm -rf /tmp/metro-* 2>/dev/null || true
echo "✅ تم تنظيف Cache"
echo ""

# 3️⃣ إعداد الاتصال الذكي
echo "3️⃣ إعداد الاتصال الذكي..."
node setup-connection.js
echo ""

# 4️⃣ بدء Metro
echo "4️⃣ بدء Metro Bundler..."
echo "   المنفذ: 8081"
echo "   الـ Reset: نعم"
echo ""

npm start -- --reset-cache

