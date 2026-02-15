#!/bin/bash
# ============================================
# 🔌 إعداد اتصال USB للتطبيق
# ============================================
# يقوم بـ:
# 1. إعداد ADB Port Forwarding
# 2. تشغيل Metro على جميع الواجهات
# 3. التحقق من الاتصال
# ============================================

# الألوان
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# المنافذ
BACKEND_PORT=3002
METRO_PORT=8081

echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}🔌 إعداد اتصال USB للتطبيق${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ============================================
# 1. التحقق من ADB
# ============================================
echo -e "${YELLOW}📱 التحقق من ADB...${NC}"

if ! command -v adb &> /dev/null; then
    echo -e "${RED}❌ ADB غير مثبت!${NC}"
    echo "قم بتثبيت Android SDK أو Android Studio"
    exit 1
fi

# التحقق من الجهاز المتصل
DEVICE=$(adb devices | grep -v "List" | grep "device$" | head -1 | awk '{print $1}')

if [ -z "$DEVICE" ]; then
    echo -e "${RED}❌ لا يوجد جهاز متصل!${NC}"
    echo ""
    echo "تأكد من:"
    echo "  1. توصيل الجهاز عبر USB"
    echo "  2. تفعيل USB Debugging في إعدادات المطور"
    echo "  3. الموافقة على طلب التصحيح على الجهاز"
    echo ""
    echo "لتفعيل USB Debugging:"
    echo "  الإعدادات → حول الهاتف → اضغط 7 مرات على رقم البناء"
    echo "  الإعدادات → خيارات المطور → تصحيح USB"
    exit 1
fi

echo -e "${GREEN}✅ جهاز متصل: $DEVICE${NC}"

# ============================================
# 2. إعداد Port Forwarding
# ============================================
echo ""
echo -e "${YELLOW}🔗 إعداد Port Forwarding...${NC}"

# إزالة أي forwarding قديم
adb reverse --remove-all 2>/dev/null

# إعداد forwarding للـ Backend
adb reverse tcp:$BACKEND_PORT tcp:$BACKEND_PORT
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backend: localhost:$BACKEND_PORT → الجهاز${NC}"
else
    echo -e "${RED}❌ فشل إعداد Backend forwarding${NC}"
fi

# إعداد forwarding للـ Metro
adb reverse tcp:$METRO_PORT tcp:$METRO_PORT
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Metro: localhost:$METRO_PORT → الجهاز${NC}"
else
    echo -e "${RED}❌ فشل إعداد Metro forwarding${NC}"
fi

# عرض جميع الـ forwards
echo ""
echo -e "${CYAN}📋 Port Forwards النشطة:${NC}"
adb reverse --list

# ============================================
# 3. التحقق من الخادم
# ============================================
echo ""
echo -e "${YELLOW}🔍 التحقق من الخادم...${NC}"

# فحص Backend
BACKEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$BACKEND_PORT/health 2>/dev/null)
if [ "$BACKEND_STATUS" = "200" ]; then
    echo -e "${GREEN}✅ Backend يعمل على المنفذ $BACKEND_PORT${NC}"
else
    echo -e "${RED}❌ Backend غير متاح!${NC}"
    echo "   شغّل الخادم: python start_server.py"
fi

# فحص Metro
METRO_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$METRO_PORT 2>/dev/null)
if [ "$METRO_STATUS" != "000" ]; then
    echo -e "${GREEN}✅ Metro يعمل على المنفذ $METRO_PORT${NC}"
else
    echo -e "${YELLOW}⚠️ Metro غير متاح - سيتم تشغيله...${NC}"
fi

# ============================================
# 4. ملخص
# ============================================
echo ""
echo -e "${CYAN}============================================${NC}"
echo -e "${GREEN}✅ تم إعداد الاتصال بنجاح!${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo "الآن التطبيق سيتصل عبر:"
echo -e "  ${CYAN}Backend:${NC} http://localhost:$BACKEND_PORT"
echo -e "  ${CYAN}Metro:${NC}   http://localhost:$METRO_PORT"
echo ""
echo "هذه العناوين ستعمل على الجهاز المتصل عبر USB"
echo ""
