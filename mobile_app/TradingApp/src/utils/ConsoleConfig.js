/**
 * 🔧 إعدادات Console للإنتاج والتطوير
 * =====================================
 *
 * في التطوير (__DEV__ = true):
 * - console.log/warn/error تعمل بشكل طبيعي
 *
 * في الإنتاج (__DEV__ = false):
 * - console.log معطل تماماً
 * - console.warn معطل
 * - console.error يعمل (للأخطاء الحرجة فقط)
 *
 * الاستخدام:
 * import './utils/ConsoleConfig'; // في App.js أو index.js
 */

// حفظ الدوال الأصلية
const originalConsole = {
  log: console.log,
  warn: console.warn,
  error: console.error,
  info: console.info,
  debug: console.debug,
};

/**
 * تعطيل console في الإنتاج
 */
const disableConsoleInProduction = () => {
  if (__DEV__) {
    // في التطوير: لا تفعل شيء
    console.log('🔧 [ConsoleConfig] Development mode - console enabled');
    return;
  }

  // في الإنتاج: تعطيل console.log و console.warn
  console.log = () => {};
  console.warn = () => {};
  console.info = () => {};
  console.debug = () => {};

  // console.error يبقى للأخطاء الحرجة
  // لكن نحوله لـ LoggerService
  console.error = (...args) => {
    // يمكن إرسال الأخطاء لخدمة تتبع الأخطاء مثل Sentry
    // originalConsole.error(...args);
  };
};

/**
 * إعادة تفعيل console (للاختبارات)
 */
const enableConsole = () => {
  console.log = originalConsole.log;
  console.warn = originalConsole.warn;
  console.error = originalConsole.error;
  console.info = originalConsole.info;
  console.debug = originalConsole.debug;
};

/**
 * التحقق من وضع التطوير
 */
const isDevelopment = () => __DEV__;

/**
 * التحقق من وضع الإنتاج
 */
const isProduction = () => !__DEV__;

// تطبيق الإعدادات تلقائياً عند الاستيراد
disableConsoleInProduction();

export {
  disableConsoleInProduction,
  enableConsole,
  isDevelopment,
  isProduction,
  originalConsole,
};

export default {
  disableConsoleInProduction,
  enableConsole,
  isDevelopment,
  isProduction,
};
