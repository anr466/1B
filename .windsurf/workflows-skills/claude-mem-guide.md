---
description: دليل استخدام Claude-Mem للذاكرة الدائمة عبر الجلسات
---

# 🧠 Claude-Mem Integration Guide

## نظرة عامة

Claude-Mem هي أداة ذكية تحفظ سياق المحادثات والأكواد عبر الجلسات، مما يمكن الـ AI من تذكر ما عملت عليه سابقاً.

## المكونات الأساسية

### 1. Worker Service
- **المنفذ**: `http://127.0.0.1:37777`
- **الوظيفة**: يدير قاعدة البيانات والذاكرة
- **التحكم**: 
  ```bash
  ./start_claude_mem.sh  # تشغيل تلقائي
  ~/.bun/bin/bun claude-mem/plugin/scripts/worker-service.cjs status
  ```

### 2. MCP Server
- **التكوين**: `mcp_config_professional.json`
- **الأدوات المتاحة**:
  - `search`: البحث في الذاكرة
  - `timeline`: عرض السياق الزمني
  - `get_observations`: جلب التفاصيل الكاملة
  - `save_memory`: حفظ معلومات مهمة

## سير العمل الثلاثي (3-Layer Workflow)

### المستوى 1: البحث
```
search(query="authentication bug", limit=20)
```
يعيد: جدول بالنتائج مع IDs (~50-100 token لكل نتيجة)

### المستوى 2: السياق الزمني
```
timeline(anchor=123, depth_before=3, depth_after=3)
```
يعيد: ما حدث قبل وبعد هذه الملاحظة

### المستوى 3: التفاصيل الكاملة
```
get_observations(ids=[123, 456, 789])
```
يعيد: التفاصيل الكاملة (~500-1000 token لكل نتيجة)

## الإعدادات

### موقع الملفات
- **الإعدادات**: `~/.claude-mem/settings.json`
- **قاعدة البيانات**: `~/.claude-mem/`
- **السجلات**: `~/.claude-mem/logs/`

### الإعدادات الرئيسية
```json
{
  "CLAUDE_MEM_WORKER_PORT": "37777",
  "CLAUDE_MEM_WORKER_HOST": "127.0.0.1",
  "CLAUDE_MEM_MODEL": "claude-sonnet-4-5",
  "CLAUDE_MEM_CONTEXT_OBSERVATIONS": "50"
}
```

## أمثلة الاستخدام

### حفظ معلومة مهمة
```typescript
save_memory({
  text: "API requires auth header X-API-Key",
  title: "API Authentication",
  project: "trading_ai_bot"
})
```

### البحث عن Bug سابق
```typescript
// 1. ابحث
search({
  query: "websocket connection error",
  type: "bugfix",
  project: "trading_ai_bot"
})

// 2. احصل على السياق
timeline({ anchor: 456 })

// 3. اجلب التفاصيل
get_observations({ ids: [456, 457, 458] })
```

## التشغيل التلقائي

### عند بدء المشروع
```bash
./start_claude_mem.sh
```

### التحقق من الحالة
```bash
curl http://127.0.0.1:37777/api/health
```

### إعادة التشغيل
```bash
~/.bun/bin/bun claude-mem/plugin/scripts/worker-service.cjs restart
```

## الواجهة الويب

افتح في المتصفح: `http://localhost:37777`

### الميزات:
- عرض جميع الجلسات
- البحث في الملاحظات
- إدارة الإعدادات
- عرض الإحصائيات

## استكشاف الأخطاء

### Worker لا يعمل
```bash
~/.bun/bin/bun claude-mem/plugin/scripts/worker-service.cjs status
~/.bun/bin/bun claude-mem/plugin/scripts/worker-service.cjs restart
```

### MCP Server لا يستجيب
```bash
# تحقق من المسار في mcp_config_professional.json
node /Users/anr/Desktop/trading_ai_bot-1/claude-mem/plugin/scripts/mcp-server.cjs
```

### عرض السجلات
```bash
tail -f ~/.claude-mem/logs/worker-$(date +%Y-%m-%d).log
```

## أفضل الممارسات

1. **دائماً استخدم 3-Layer Workflow** - وفر 10x من الـ tokens
2. **اجمع IDs في طلب واحد** - استخدم `get_observations([1,2,3])` بدلاً من طلبات متعددة
3. **احفظ القرارات المهمة** - استخدم `save_memory` للمعلومات الحرجة
4. **حدد المشروع** - استخدم `project` parameter للتنظيم

## الفوائد الرئيسية

✅ **ذاكرة دائمة** - لا تفقد السياق بين الجلسات
✅ **بحث ذكي** - Vector search + keyword search
✅ **توفير tokens** - 10x عبر Progressive disclosure
✅ **تنظيم أفضل** - تصنيف حسب المشروع والنوع
✅ **تكامل سلس** - يعمل تلقائياً في الخلفية

## الدعم والمساعدة

- **المستودع**: https://github.com/thedotmack/claude-mem
- **الوثائق**: https://docs.claude-mem.ai/
- **الإعدادات المحلية**: ~/.claude-mem/settings.json
