# 🛠️ Trading AI Bot - المهارات والأدوات المتاحة

دليل شامل لجميع المهارات (Skills) وخوادم MCP المُفعّلة في المشروع.

---

## 📚 Skills (المهارات)

### 1. Frontend Design Skill ⭐
**المصدر**: https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md  
**الملف المحلي**: `.windsurf/workflows/frontend-design-skill.md`  
**الاستخدام**: `/frontend-design-skill`

#### متى تستخدمها؟
- تصميم أو تحسين واجهات React Native
- إنشاء مكونات UI جديدة بتصميم مميز
- تجنب التصاميم العامة والمملة
- إضافة حركات وتأثيرات بصرية احترافية

#### النقاط الرئيسية:
- ✅ اختيار اتجاه تصميمي جريء ومميز
- ✅ Typography مميز مع استخدام أوزان خطوط غير تقليدية
- ✅ ألوان قوية مع gradients وتأثيرات بصرية
- ✅ حركات وتفاعلات دقيقة باستخدام Reanimated
- ❌ ممنوع تعديل components/charts/*
- ❌ ممنوع تعديل services/* أو context/*

---

### 2. React Best Practices ⭐
**المصدر**: https://github.com/vercel-labs/agent-skills/tree/main/skills/react-best-practices  
**الملف المحلي**: `.windsurf/workflows/react-best-practices.md`  
**الاستخدام**: `/react-best-practices`

#### متى تستخدمها؟
- تحسين الأداء (Performance Optimization)
- حل مشاكل Re-rendering
- تحسين حجم Bundle Size
- تنظيم Data Fetching
- تحسين useEffect Dependencies

#### الأولويات:
1. **CRITICAL**: Eliminating Waterfalls (استخدام Promise.all)
2. **CRITICAL**: Bundle Size (تجنب barrel imports)
3. **HIGH**: Re-render Optimization (useMemo, useCallback بحكمة)
4. **MEDIUM**: useEffect Dependencies (تحديد الـ deps بدقة)

#### Checklist سريع:
```javascript
// ✅ GOOD: Parallel API calls
const [user, trades] = await Promise.all([getUser(), getTrades()]);

// ✅ GOOD: Direct imports
import Button from '@/components/Button';

// ✅ GOOD: Memoize expensive calculations
const sorted = useMemo(() => data.sort(), [data]);

// ✅ GOOD: Check mounted before setState
if (!isMountedRef.current) return;
```

---

### 3. File Cleanup Management Skill
**الملف المحلي**: `.windsurf/workflows/file-cleanup-skill.md`  
**الاستخدام**: `/file-cleanup-skill`

#### متى تستخدمها؟
- تنظيف الملفات الزائدة والتكرارات
- حذف Logs والملفات المؤقتة
- تحسين بنية المشروع

---

### 4. Testing Framework
**الملف المحلي**: `.windsurf/workflows/testing-framework.md`  
**الاستخدام**: `/testing-framework`

#### متى تستخدمها؟
- كتابة اختبارات شاملة للتطبيق
- اختبار Components، APIs، وLogic
- ضمان Zero Defects

---

### 5. Spec Kit (مجموعة Specification)
مجموعة من المهارات لإدارة دورة حياة المشروع:

- `/spec-init` - تهيئة مشروع جديد
- `/spec-create` - كتابة مواصفات تفصيلية
- `/spec-plan` - تخطيط البنية التقنية
- `/spec-tasks` - تقسيم المهام
- `/spec-review` - مراجعة وتحسين المواصفات

---

## 🔌 MCP Servers (خوادم البروتوكول)

### 1. Chrome DevTools MCP ⭐ NEW
**المصدر**: https://github.com/ChromeDevTools/chrome-devtools-mcp  
**الدليل**: `.windsurf/workflows/chrome-devtools-guide.md`  
**الحالة**: ✅ مُفعّل

#### الاستخدام:
- فحص Web Prototypes (مثل Minimal Light)
- تصحيح أخطاء CSS وJavaScript
- قياس الأداء (Performance metrics)
- أخذ Screenshots ومقارنة التصاميم
- فحص Network requests

#### الأوضاع المتاحة:
1. **Desktop Headless**: للفحص الآلي
2. **Android Remote**: للفحص على الجوال

```bash
# مثال: فحص Minimal Light
"افتح web_prototypes/concept2_minimal_light.html وقس الأداء"
```

---

### 2. GitHub MCP
**الدليل**: `.windsurf/workflows/github-mcp-guide.md`  
**الحالة**: ✅ مُفعّل

#### الاستخدام:
- إدارة Issues و Pull Requests
- البحث في الكود عبر GitHub
- قراءة وتعديل الملفات مباشرة
- إنشاء Branches و Commits

---

### 3. DeepWiki MCP
**الحالة**: ✅ مُفعّل

#### الاستخدام:
- قراءة توثيق المكتبات من GitHub
- الحصول على أمثلة كود من repos شهيرة
- طرح أسئلة عن مكتبات معينة

---

### 4. Figma Remote MCP
**الحالة**: ✅ مُفعّل

#### الاستخدام:
- استيراد تصاميم من Figma
- تحويل Designs إلى Code
- إنشاء Diagrams في FigJam

---

### 5. Claude-Mem (الذاكرة الدائمة)
**الدليل**: `.windsurf/workflows/claude-mem-guide.md`  
**الحالة**: ✅ مُفعّل

#### الاستخدام:
- حفظ معلومات مهمة عن المشروع
- تذكر القرارات التصميمية
- الاحتفاظ بالسياق عبر الجلسات

---

### 6. Playwright & Puppeteer MCP
**الحالة**: ✅ مُفعّل

#### الاستخدام:
- Browser automation للاختبارات
- End-to-end testing
- Scraping وتفاعل تلقائي مع صفحات Web

---

### 7. React Native MCP
**الحالة**: ✅ مُفعّل

#### الاستخدام:
- مساعدات خاصة بـ React Native
- Expo utilities
- Mobile development best practices

---

### 8. Magic UI MCP
**الحالة**: ✅ مُفعّل

#### الاستخدام:
- مكونات UI جاهزة وجميلة
- Animations وتأثيرات احترافية

---

### 9. Sequential Thinking MCP
**الحالة**: ✅ مُفعّل

#### الاستخدام:
- حل المشاكل المعقدة خطوة بخطوة
- تحليل منطقي متسلسل
- التفكير العميق قبل التنفيذ

---

## 🚀 سيناريوهات الاستخدام

### السيناريو 1: تحسين شاشة Dashboard
```
1. استخدم /frontend-design-skill لتحسين التصميم
2. استخدم /react-best-practices للتحقق من الأداء
3. استخدم Chrome DevTools MCP لقياس النتائج
```

### السيناريو 2: إنشاء Feature جديد
```
1. استخدم /spec-create لكتابة المواصفات
2. استخدم /spec-plan للتخطيط التقني
3. استخدم /spec-tasks لتقسيم المهام
4. استخدم /frontend-design-skill + /react-best-practices للتنفيذ
5. استخدم /testing-framework للاختبار
```

### السيناريو 3: فحص Web Prototypes
```
1. افتح الـ prototype في المتصفح
2. استخدم Chrome DevTools MCP للفحص:
   - قياس الأداء
   - فحص Console errors
   - اختبار Responsiveness
   - أخذ Screenshots للمقارنة
```

### السيناريو 4: تحسين الأداء
```
1. استخدم /react-best-practices لتحديد المشاكل
2. استخدم Chrome DevTools MCP لقياس Before/After
3. استخدم Sequential Thinking للتحليل العميق
```

---

## 📊 إحصائيات المشروع

```
المهارات المتاحة: 12 skill
MCP Servers النشطة: 14 server
Protected Components: 7 chart components
API Services: 8 services
Context Providers: 4 contexts
```

---

## 🎯 أفضل الممارسات

### 1. قبل تعديل أي UI:
- [ ] اقرأ `/frontend-design-skill`
- [ ] اقرأ `/react-best-practices`
- [ ] تأكد من عدم تعديل Protected zones

### 2. قبل إضافة Feature:
- [ ] اكتب Spec باستخدام `/spec-create`
- [ ] خطط باستخدام `/spec-plan`
- [ ] قسّم المهام باستخدام `/spec-tasks`

### 3. قبل Merge أي Code:
- [ ] تحقق من الأداء (React Best Practices)
- [ ] تحقق من التصميم (Frontend Design)
- [ ] افحص بـ Chrome DevTools
- [ ] اكتب Tests باستخدام `/testing-framework`

---

## 📞 الدعم والمساعدة

- **للمهارات**: اقرأ الملفات في `.windsurf/workflows/`
- **لـ MCP Servers**: راجع `mcp_config_professional.json`
- **للأسئلة**: استخدم Claude-Mem لحفظ المعلومات المهمة

---

**آخر تحديث**: 2026-02-21  
**الحالة**: ✅ جميع المهارات والأدوات جاهزة للاستخدام
