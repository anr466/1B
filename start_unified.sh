#!/bin/bash
# 🚀 Trading AI Bot - Unified Startup Script
# تشغيل النظام كاملاً بشكل موحد ومستقر

set -e

echo "════════════════════════════════════════════════════════════"
echo "🚀 Trading AI Bot - Unified System Startup"
echo "════════════════════════════════════════════════════════════"

# 1. التحقق من المتطلبات
echo ""
echo "1️⃣ Checking requirements..."
command -v python3 >/dev/null 2>&1 || { echo "❌ Python3 required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "❌ Node.js required"; exit 1; }
echo "✅ All requirements available"

# 2. تشغيل Backend Server
echo ""
echo "2️⃣ Starting Backend Server..."
python3 start_server.py > logs/backend.log 2>&1 &
BACKEND_PID=$!
echo "   PID: $BACKEND_PID"
sleep 5

# 3. فحص Backend
if curl -sf http://localhost:3002/health > /dev/null 2>&1; then
    echo "✅ Backend running on :3002"
else
    echo "❌ Backend failed to start"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# 4. تشغيل Metro Bundler
echo ""
echo "3️⃣ Starting Metro Bundler..."
cd mobile_app/TradingApp
npm start > ../../logs/metro.log 2>&1 &
METRO_PID=$!
cd ../..
echo "   PID: $METRO_PID"
sleep 3

# 5. إعداد ADB Port Forwarding (للمحاكي)
if command -v adb >/dev/null 2>&1; then
    if adb devices 2>/dev/null | grep -q "emulator"; then
        echo ""
        echo "4️⃣ Setting up ADB port forwarding..."
        adb reverse tcp:3002 tcp:3002 2>/dev/null || true
        adb reverse tcp:8081 tcp:8081 2>/dev/null || true
        echo "✅ ADB forwarding active"
    fi
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo "✅ System Ready!"
echo "════════════════════════════════════════════════════════════"
echo "📡 Backend:  http://localhost:3002"
echo "📡 Metro:    http://localhost:8081"
echo "📁 Logs:     logs/backend.log, logs/metro.log"
echo ""
echo "📝 Backend PID: $BACKEND_PID"
echo "📝 Metro PID:   $METRO_PID"
echo ""
echo "Press Ctrl+C to stop all services"
echo "════════════════════════════════════════════════════════════"

# معالج الإيقاف
cleanup() {
    echo ""
    echo "🛑 Stopping services..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $METRO_PID 2>/dev/null || true
    echo "✅ Cleanup complete"
    exit 0
}

trap cleanup INT TERM

# انتظار
wait
