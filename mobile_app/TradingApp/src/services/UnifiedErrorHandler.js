/**
 * Unified Error Handler - Placeholder
 * تم استبداله بـ ApiErrorHandler
 * هذا ملف مؤقت للتوافق حتى يتم تحديث جميع الاستيرادات
 */

import Logger from './LoggerService';
import ToastService from './ToastService';

class UnifiedErrorHandler {
    constructor() {
        this.errorLog = [];
    }

    handle(error, options = {}) {
        const context = options.context || 'Unknown';
        const message = error?.message || error;

        if (options.logToConsole !== false) {
            Logger.error(`[${context}] ${message}`);
        }

        if (options.showToast && ToastService) {
            const userMsg = options.userMessage || message || 'حدث خطأ';
            try {
                ToastService.showError(userMsg);
            } catch (e) {
                // Toast service unavailable — silent fallback
            }
        }

        return { success: false, error };
    }

    handleSmart(error, options = {}) {
        const context = options.context || 'Unknown';
        Logger.error(`[${context}]`, error?.message || error);
        return { success: false, error: error?.message || 'Unknown error' };
    }

    handleSystemError(code, message) {
        Logger.error(`[${code}] ${message}`);
    }

    handleUserError(code, message = '') {
        Logger.warn(`[USER_ERROR:${code}] ${message}`);
    }

    getErrorLog() {
        return [];
    }

    getStats() {
        return {
            total: 0,
            bySeverity: {},
        };
    }
}

const errorHandler = new UnifiedErrorHandler();
export default errorHandler;
