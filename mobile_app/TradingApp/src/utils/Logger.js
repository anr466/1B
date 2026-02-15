/**
 * Logger Utility
 * نظام تسجيل موحد للتطبيق
 */

const isDevelopment = __DEV__;

class Logger {
  static log(message, ...args) {
    if (isDevelopment) {
      console.log(`[LOG] ${message}`, ...args);
    }
  }

  static info(message, ...args) {
    if (isDevelopment) {
      console.info(`[INFO] ${message}`, ...args);
    }
  }

  static warn(message, ...args) {
    if (isDevelopment) {
      console.warn(`[WARN] ${message}`, ...args);
    }
  }

  static error(message, ...args) {
    console.error(`[ERROR] ${message}`, ...args);
  }

  static debug(message, ...args) {
    if (isDevelopment) {
      console.debug(`[DEBUG] ${message}`, ...args);
    }
  }
}

export default Logger;
