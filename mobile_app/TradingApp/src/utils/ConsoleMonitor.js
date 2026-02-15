/**
 * 🛡️ Console Monitor - مراقب أخطاء Console
 * يلتقط ويراقب جميع أخطاء JavaScript و React
 */

import { Platform } from 'react-native';

class ConsoleMonitor {
    static init() {
        if (__DEV__) {
            console.log('🔍 Console Monitor initialized');

            // مراقبة أخطاء JavaScript
            const originalError = console.error;
            console.error = (...args) => {
                originalError.apply(console, args);

                const errorMessage = args.join(' ');
                if (this.isReactError(errorMessage)) {
                    this.logReactError(errorMessage);
                }
            };

            // مراقبة تحذيرات React
            const originalWarn = console.warn;
            console.warn = (...args) => {
                originalWarn.apply(console, args);

                const warningMessage = args.join(' ');
                if (this.isReactWarning(warningMessage)) {
                    this.logReactWarning(warningMessage);
                }
            };

            // مراقبة أخطاء الشبكة
            const originalLog = console.log;
            console.log = (...args) => {
                const logMessage = args.join(' ');
                if (this.isNetworkError(logMessage)) {
                    this.logNetworkError(logMessage);
                }
                originalLog.apply(console, args);
            };
        }
    }

    static isReactError(message) {
        return message.includes('Warning:') ||
            message.includes('Error:') ||
            message.includes('undefined is not an object') ||
            message.includes('Cannot read property') ||
            message.includes('TypeError') ||
            message.includes('ReferenceError');
    }

    static isReactWarning(message) {
        return message.includes('Warning:') ||
            message.includes('Each child should have a unique "key" prop') ||
            message.includes('Can not perform a React state update') ||
            message.includes('React state update during render');
    }

    static isNetworkError(message) {
        return message.includes('Network Error') ||
            message.includes('fetch failed') ||
            message.includes('Request failed') ||
            message.includes('Timeout');
    }

    static logReactError(error) {
        console.group('🚨 React Error Detected');
        console.log('Error:', error);
        console.log('Time:', new Date().toLocaleTimeString('ar-SA'));
        console.log('Platform:', Platform?.OS || 'Unknown');
        console.log('Screen:', this.getCurrentScreen());
        console.groupEnd();
    }

    static logReactWarning(warning) {
        console.group('⚠️ React Warning Detected');
        console.log('Warning:', warning);
        console.log('Time:', new Date().toLocaleTimeString('ar-SA'));
        console.log('Platform:', Platform.OS);
        console.groupEnd();
    }

    static logNetworkError(error) {
        console.group('🌐 Network Error Detected');
        console.log('Error:', error);
        console.log('Time:', new Date().toLocaleTimeString('ar-SA'));
        console.log('Platform:', Platform.OS);
        console.groupEnd();
    }

    static getCurrentScreen() {
        try {
            // محاولة تحديد الشاشة الحالية من navigation state
            return global.currentScreen || 'Unknown Screen';
        } catch {
            return 'Unknown Screen';
        }
    }

    // دالة لفحص الأخطاء في مكون معين
    static inspectComponent(componentName, props, state) {
        console.group(`🔍 Inspecting ${componentName}`);

        console.log('Props:', props);
        console.log('State:', state);

        // فحص Props غير المعرّفة
        Object.keys(props || {}).forEach(key => {
            if (props[key] === undefined) {
                console.warn(`⚠️ Undefined prop: ${key} in ${componentName}`);
            }
        });

        // فحص State الفاسد
        Object.keys(state || {}).forEach(key => {
            if (state[key] === null || state[key] === undefined) {
                console.warn(`⚠️ Invalid state: ${key} = ${state[key]} in ${componentName}`);
            }
        });

        console.groupEnd();
    }

    // دالة لمراقبة API calls
    static monitorAPI(apiName, startTime) {
        const endTime = global.performance?.now?.() || Date.now();
        const duration = endTime - startTime;

        if (duration > 2000) { // أكثر من ثانيتين
            console.warn(`🐌 Slow API call detected: ${apiName} took ${duration.toFixed(2)}ms`);
        } else {
            console.log(`✅ API call successful: ${apiName} took ${duration.toFixed(2)}ms`);
        }
    }
}

export default ConsoleMonitor;
