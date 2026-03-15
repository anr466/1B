---
description: نظام اختبار React Native الشامل — 7 طبقات لضمان Zero Defects
---

# 🧪 React Native Testing Framework

## التشغيل السريع

```bash
cd mobile_app/TradingApp

# تشغيل جميع الاختبارات
npm run test:all

# طبقات محددة
npm run test:unit          # Layer 1: Utils
npm run test:components    # Layer 2: Components & Screens
npm run test:api           # Layer 4: API Services
npm run test:integration   # Layer 5: Integration
npm run test:navigation    # Layer 6: Navigation
npm run test:consistency   # Layer 7: Consistency

# Coverage report
npm run test:coverage

# Validate (lint + all tests)
npm run validate
```

## هيكل الاختبارات

```
src/__tests__/
├── utils/                          # Layer 1: Unit Tests
│   ├── userUtils.test.js           # 20 tests — getUserType, isAdmin, permissions
│   └── responseValidator.test.js   # 22 tests — portfolio, trades, settings validation
├── context/                        # Layer 3: State Tests
│   ├── ThemeContext.test.js         # 7 tests — provider, hook, theme values
│   └── TradingModeContext.test.js   # 16 tests — exports, state, dependencies
├── screens/                        # Layer 2: Component Tests
│   └── ScreenRendering.test.js     # 4 tests — Login, Register, Auth render
├── services/                       # Layer 4: API Tests
│   ├── DatabaseApiService.test.js  # 66 tests — all API methods, retry, camelCase
│   ├── ServerConfig.test.js        # 17 tests — endpoints, URLs, connection
│   ├── UnifiedConnectionService.test.js # 15 tests — USB, network, emulator
│   └── ApiPathConsistency.test.js  # 32 tests — no /user/user/, correct paths
├── integration/                    # Layer 5: Integration Tests
│   └── AppIntegration.test.js      # 33 tests — nav, context, services, build
├── navigation/                     # Layer 6: Navigation Tests
│   └── NavigationStructure.test.js # 15 tests — tabs, stacks, auth, guards
├── consistency/                    # Layer 7: Consistency Tests
│   └── UnifiedOperations.test.js   # 14 tests — single source, no dead imports
├── design/
│   └── DesignVerification.test.js  # emoji, gradient, animations, BrandIcon
└── functional-tests.js             # placeholder
```

## القواعد الذهبية

1. **لا PR بدون Tests** — كل ملف جديد يحتاج اختبار مقابل
2. **لا Deploy بدون اجتياز `npm run test:all`**
3. **كل Bug يحتاج اختبار regression يمنع تكراره**
4. **مصدر واحد للبيانات** — DatabaseApiService فقط (لا axios مباشر في الشاشات)
5. **لا imports لملفات محذوفة** — Layer 7 يكتشفها تلقائياً
6. **لا /user/user/ مكرر** — ApiPathConsistency يراقب ذلك

## إضافة اختبار جديد

### Unit Test (Layer 1)
```js
// src/__tests__/utils/myUtil.test.js
import { myFunction } from '../../utils/myUtil';

describe('myFunction', () => {
  test('handles normal input', () => {
    expect(myFunction('input')).toBe('expected');
  });
  test('handles edge cases', () => {
    expect(myFunction(null)).toBe('default');
  });
});
```

### API Test (Layer 4)
استخدم نمط DatabaseApiService.test.js: `jest.isolateModules` + mock `axios.create`

### Consistency Test (Layer 7)
استخدم `fs.readFileSync` لقراءة الكود المصدري والتحقق من القواعد
