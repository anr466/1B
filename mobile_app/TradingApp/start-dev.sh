#!/bin/bash
# ============================================
# 🚀 تشغيل بيئة التطوير الكاملة
# ============================================
# يقوم بـ:
# 1. تشغيل الخادم (Backend)
# 2. إعداد USB Port Forwarding
# 3. تشغيل Metro Bundler
# ============================================

# الألوان
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# المسارات
PROJECT_ROOT="/Users/anr/Desktop/trading_ai_bot"
APP_ROOT="$PROJECT_ROOT/mobile_app/TradingApp"

# المنافذ
BACKEND_PORT=3002
METRO_PORT=8081

clear
echo -e "${CYAN}${BOLD}============================================${NC}"
echo -e "${CYAN}${BOLD}🚀 Trading AI Bot - بيئة التطوير${NC}"
echo -e "${CYAN}${BOLD}============================================${NC}"
echo ""

# ============================================
# 1. تشغيل الخادم (Backend)
# ============================================
echo -e "${YELLOW}📦 [1/3] فحص الخادم...${NC}"

# فحص إذا كان الخادم يعمل
BACKEND_PID=$(lsof -ti:$BACKEND_PORT 2>/dev/null)

if [ -n "$BACKEND_PID" ]; then
    echo -e "${GREEN}✅ الخادم يعمل بالفعل (PID: $BACKEND_PID)${NC}"
else
    echo -e "${YELLOW}🔄 تشغيل الخادم...${NC}"
    cd "$PROJECT_ROOT"
    source venv/bin/activate 2>/dev/null
    python3 start_server.py &
    sleep 3
    
    # التحقق
    if curl -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ الخادم يعمل الآن${NC}"
    else
        echo -e "${RED}❌ فشل تشغيل الخادم${NC}"
    fi
fi

# ============================================
# 2. إعداد USB Port Forwarding
# ============================================
echo ""
echo -e "${YELLOW}🔌 [2/3] إعداد USB Port Forwarding...${NC}"

# التحقق من ADB
if command -v adb &> /dev/null; then
    DEVICE=$(adb devices | grep -v "List" | grep "device$" | head -1 | awk '{print $1}')
    
    if [ -n "$DEVICE" ]; then
        echo -e "${GREEN}📱 جهاز متصل: $DEVICE${NC}"
        
        # إعداد Port Forwarding
        adb reverse --remove-all 2>/dev/null
        adb reverse tcp:$BACKEND_PORT tcp:$BACKEND_PORT 2>/dev/null
        adb reverse tcp:$METRO_PORT tcp:$METRO_PORT 2>/dev/null
        
        echo -e "${GREEN}✅ Port Forwarding جاهز:${NC}"
        echo -e "   Backend: localhost:$BACKEND_PORT"
        echo -e "   Metro:   localhost:$METRO_PORT"
    else
        echo -e "${YELLOW}⚠️ لا يوجد جهاز متصل عبر USB${NC}"
        echo -e "   سيتم استخدام الشبكة المحلية بدلاً من ذلك"
    fi
else
    echo -e "${YELLOW}⚠️ ADB غير متاح${NC}"
fi

# ============================================
# 3. تشغيل Metro Bundler
# ============================================
echo ""
echo -e "${YELLOW}📱 [3/3] فحص Metro Bundler...${NC}"

METRO_PID=$(lsof -ti:$METRO_PORT 2>/dev/null)

if [ -n "$METRO_PID" ]; then
    echo -e "${GREEN}✅ Metro يعمل بالفعل (PID: $METRO_PID)${NC}"
else
    echo -e "${YELLOW}🔄 تشغيل Metro...${NC}"
    cd "$APP_ROOT"
    npx metro serve --host 0.0.0.0 --port $METRO_PORT &
    sleep 5
    
    if lsof -ti:$METRO_PORT > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Metro يعمل الآن${NC}"
    else
        echo -e "${RED}❌ فشل تشغيل Metro${NC}"
    fi
fi

# ============================================
# 4. ملخص
# ============================================
echo ""
echo -e "${CYAN}${BOLD}============================================${NC}"
echo -e "${GREEN}${BOLD}✅ بيئة التطوير جاهزة!${NC}"
echo -e "${CYAN}${BOLD}============================================${NC}"
echo ""
echo -e "${BOLD}الخدمات:${NC}"
echo -e "  ${CYAN}Backend:${NC} http://localhost:$BACKEND_PORT"
echo -e "  ${CYAN}Metro:${NC}   http://localhost:$METRO_PORT"
echo ""

# الحصول على IP المحلي
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')
if [ -n "$LOCAL_IP" ]; then
    echo -e "${BOLD}للاتصال عبر WiFi:${NC}"
    echo -e "  ${CYAN}Backend:${NC} http://$LOCAL_IP:$BACKEND_PORT"
    echo -e "  ${CYAN}Metro:${NC}   http://$LOCAL_IP:$METRO_PORT"
    echo ""
fi

echo -e "${BOLD}الأوامر المتاحة:${NC}"
echo -e "  ${CYAN}./setup-usb-connection.sh${NC} - إعادة إعداد USB"
echo -e "  ${CYAN}adb reverse --list${NC}        - عرض Port Forwards"
echo -e "  ${CYAN}npx react-native run-android${NC} - تثبيت التطبيق"
echo ""
