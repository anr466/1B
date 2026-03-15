---
description: دليل استخدام Chrome DevTools MCP Server لفحص وتصحيح التطبيقات
---

# Chrome DevTools MCP Server Guide

**Source**: https://github.com/ChromeDevTools/chrome-devtools-mcp
**Status**: ✅ مُفعّل في المشروع

---

## 🎯 ما هو Chrome DevTools MCP؟

أداة قوية تتيح للـ AI فحص وتصحيح التطبيقات Web/Mobile عبر Chrome DevTools Protocol:
- فحص العناصر وتعديل CSS مباشرة
- تتبع Network requests وتحليل الأداء
- تنفيذ JavaScript في سياق الصفحة
- أخذ Screenshots والتفاعل مع العناصر
- مراقبة Console logs والأخطاء

---

## 🔧 الإعدادات الحالية

تم تفعيل وضعين في `mcp_config_professional.json`:

### 1. Chrome Desktop (Headless Mode)
```json
"chrome-devtools": {
  "command": "npx",
  "args": [
    "-y",
    "chrome-devtools-mcp@latest",
    "--headless=true",
    "--isolated=true",
    "--executablePath=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  ]
}
```

### 2. Chrome Android (Remote Debugging)
```json
"chrome-devtools-android": {
  "command": "npx",
  "args": [
    "-y",
    "chrome-devtools-mcp@latest",
    "--browserUrl=http://127.0.0.1:9222"
  ]
}
```

---

## 📱 كيفية الاستخدام مع React Native

### السيناريو 1: فحص Web Prototypes
```bash
# فتح Minimal Light prototype
cd /Users/anr/Desktop/trading_ai_bot-1/web_prototypes
open concept2_minimal_light.html

# طلب من AI فحص التصميم
"افحص صفحة Minimal Light واكتشف أي مشاكل في CSS أو Performance"
```

### السيناريو 2: فحص Expo Web Build
```bash
# في مجلد التطبيق
cd mobile_app/TradingApp
npx expo start --web

# ثم اطلب من AI
"افحص التطبيق على http://localhost:19006 وتحقق من أداء الـ charts"
```

### السيناريو 3: Remote Debugging للجوال
```bash
# على Android مع Chrome Remote Debugging
adb forward tcp:9222 localabstract:chrome_devtools_remote

# ثم اطلب من AI
"افحص التطبيق على الجهاز المتصل وراقب Network requests"
```

---

## 🚀 حالات الاستخدام الشائعة

### 1. تحليل الأداء
```
"افحص صفحة Dashboard وقس:
- وقت تحميل الصفحة
- حجم الـ bundle
- عدد الـ re-renders
- استهلاك الذاكرة"
```

### 2. فحص التوافقية
```
"افحص التطبيق على:
- iOS Safari simulation
- Android Chrome simulation
- Desktop Chrome
وأبلغني بأي اختلافات في العرض"
```

### 3. تصحيح الأخطاء
```
"افحص Console errors في صفحة Portfolio واكتشف:
- JavaScript errors
- Failed network requests
- Warning messages
- Performance bottlenecks"
```

### 4. تحسين CSS
```
"افحص تطبيق Minimal Light واقترح تحسينات لـ:
- Dark mode contrast
- Mobile responsiveness
- Animation performance
- Layout shifts (CLS)"
```

---

## ⚙️ الأوامر المتاحة

### Browser Navigation
- `browser_navigate(url)` - الانتقال لصفحة
- `browser_navigate_back()` - الرجوع للخلف
- `browser_tabs(action)` - إدارة التبويبات

### Inspection
- `browser_snapshot()` - التقاط snapshot للصفحة
- `browser_take_screenshot()` - أخذ screenshot
- `browser_console_messages()` - قراءة رسائل Console
- `browser_network_requests()` - عرض Network activity

### Interaction
- `browser_click(selector)` - النقر على عنصر
- `browser_type(selector, text)` - كتابة نص
- `browser_evaluate(code)` - تنفيذ JavaScript

### Performance
- `browser_wait_for(condition)` - الانتظار حتى شرط معين
- `browser_resize(width, height)` - تغيير حجم النافذة

---

## 💡 أمثلة عملية

### مثال 1: فحص Minimal Light Performance
```
اطلب من AI:
"افتح web_prototypes/concept2_minimal_light.html وقس:
1. وقت تحميل جميع الـ charts
2. حجم الـ JavaScript bundle
3. عدد الـ DOM nodes
4. استهلاك الذاكرة عند التبديل بين الـ tabs"
```

### مثال 2: اختبار Dark Mode
```
اطلب من AI:
"افتح Minimal Light وقم بـ:
1. التقاط screenshot في Light mode
2. التبديل إلى Dark mode
3. التقاط screenshot في Dark mode
4. المقارنة بين الوضعين واكتشاف أي مشاكل في Contrast"
```

### مثال 3: فحص Mobile Responsiveness
```
اطلب من AI:
"افتح Minimal Light في أحجام شاشة مختلفة:
- iPhone SE (375x667)
- iPhone 14 Pro (393x852)
- iPad (768x1024)
وتحقق من أن جميع العناصر تُعرض بشكل صحيح"
```

---

## 🔍 تصحيح مشاكل شائعة

### المشكلة: "Browser not found"
```bash
# تأكد من تثبيت Chrome
# macOS:
ls "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# إذا كان المسار مختلف، حدّث mcp_config_professional.json
```

### المشكلة: "Port 9222 already in use"
```bash
# أوقف Chrome instances القديمة
pkill -9 "Google Chrome"

# أو استخدم port مختلف
--browserUrl=http://127.0.0.1:9223
```

### المشكلة: "Cannot connect to Android device"
```bash
# تحقق من ADB connection
adb devices

# أعد توجيه Port
adb forward tcp:9222 localabstract:chrome_devtools_remote
```

---

## 📚 Resources

- **Official Repo**: https://github.com/ChromeDevTools/chrome-devtools-mcp
- **Chrome DevTools Protocol**: https://chromedevtools.github.io/devtools-protocol/
- **MCP Documentation**: https://modelcontextprotocol.io/

---

## ✅ Checklist قبل الاستخدام

- [ ] Chrome مثبت على النظام
- [ ] `mcp_config_professional.json` يحتوي على الإعدادات الصحيحة
- [ ] التطبيق/الصفحة المراد فحصها متاحة ومفتوحة
- [ ] Windsurf متصل بـ MCP servers (تحقق من Settings)
- [ ] لا توجد Chrome instances قديمة تعيق الاتصال

---

**ملاحظة**: هذه الأداة قوية جداً لفحص Web prototypes (مثل Minimal Light) وتطبيقات Expo Web. استخدمها بانتظام لضمان الجودة والأداء.
