#!/bin/bash
# Script to start the complete trading system

echo "🚀 Starting Trading AI Bot System..."
echo "===================================="

# 1. Start Backend Server
echo "1️⃣ Starting Backend Server..."
cd /Users/anr/Desktop/trading_ai_bot-1
source venv/bin/activate
python3 scripts/start.py > /tmp/server.log 2>&1 &
SERVER_PID=$!
echo "   Server PID: $SERVER_PID"
sleep 5

# 2. Check if server is running
if curl -s http://localhost:3002/health > /dev/null; then
    echo "   ✅ Server is running on port 3002"
else
    echo "   ❌ Server failed to start"
    exit 1
fi

# 3. Setup port forwarding for emulator
echo ""
echo "2️⃣ Setting up port forwarding..."
adb reverse tcp:3002 tcp:3002
echo "   ✅ Port forwarding: 3002 -> 3002"

# 4. Start Metro
echo ""
echo "3️⃣ Starting Metro bundler..."
cd /Users/anr/Desktop/trading_ai_bot-1/mobile_app/TradingApp
npx react-native start --reset-cache > /tmp/metro.log 2>&1 &
METRO_PID=$!
echo "   Metro PID: $METRO_PID"
sleep 10

# 5. Launch Android emulator
echo ""
echo "4️⃣ Launching Android app..."
npx react-native run-android > /tmp/android.log 2>&1 &
ANDROID_PID=$!
echo "   Android build PID: $ANDROID_PID"

echo ""
echo "===================================="
echo "✅ All services starting..."
echo ""
echo "📊 Status:"
echo "   Server: http://localhost:3002"
echo "   Metro: http://localhost:8081"
echo "   App: Launching on emulator..."
echo ""
echo "📋 Logs:"
echo "   Server: tail -f /tmp/server.log"
echo "   Metro:  tail -f /tmp/metro.log"
echo "   Android: tail -f /tmp/android.log"
echo ""
echo "Press Ctrl+C to stop all services"
echo "===================================="

# Wait for interrupt
trap "echo 'Stopping services...'; kill $SERVER_PID $METRO_PID 2>/dev/null; exit" INT
wait
