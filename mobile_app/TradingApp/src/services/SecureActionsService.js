/**
 * خدمة العمليات الآمنة - نظام التحقق الموحد
 * ============================================
 *
 * جميع العمليات الحساسة تتطلب تحقق OTP (SMS أو Email)
 *
 * التدفق:
 * 1. getVerificationOptions(action) - الحصول على خيارات التحقق المتاحة
 * 2. requestVerification(action, method, newValue) - طلب رمز التحقق
 * 3. verifyAndExecute(action, otp, newValue) - التحقق وتنفيذ العملية
 *
 * العمليات المدعومة:
 * - change_password: تغيير كلمة المرور (يتطلب كلمة المرور القديمة)
 * - change_email: تغيير الإيميل (التحقق من الجوال فقط)
 * - change_phone: تغيير الجوال (التحقق من الإيميل فقط)
 * - change_biometric: تفعيل/إلغاء البصمة
 * - change_binance_keys: تغيير مفاتيح Binance
 * - delete_binance_keys: حذف مفاتيح Binance
 */

import DatabaseApiService from './DatabaseApiService';

// أنواع العمليات
export const SECURE_ACTIONS = {
    CHANGE_PASSWORD: 'change_password',
    CHANGE_EMAIL: 'change_email',
    CHANGE_PHONE: 'change_phone',
    CHANGE_BIOMETRIC: 'change_biometric',
    CHANGE_BINANCE_KEYS: 'change_binance_keys',
    DELETE_BINANCE_KEYS: 'delete_binance_keys',
};

// طرق التحقق
export const VERIFICATION_METHODS = {
    EMAIL: 'email',
    SMS: 'sms',
};

// أسماء العمليات بالعربي
export const ACTION_NAMES = {
    [SECURE_ACTIONS.CHANGE_PASSWORD]: 'تغيير كلمة المرور',
    [SECURE_ACTIONS.CHANGE_EMAIL]: 'تغيير الإيميل',
    [SECURE_ACTIONS.CHANGE_PHONE]: 'تغيير رقم الجوال',
    [SECURE_ACTIONS.CHANGE_BIOMETRIC]: 'تغيير إعدادات البصمة',
    [SECURE_ACTIONS.CHANGE_BINANCE_KEYS]: 'تغيير مفاتيح Binance',
    [SECURE_ACTIONS.DELETE_BINANCE_KEYS]: 'حذف مفاتيح Binance',
};

class SecureActionsService {
    constructor() {
        // ✅ المسار بدون /user لأن interceptor يضيف /api/user تلقائياً
        this.baseUrl = '/secure';
        this.pendingAction = null; // العملية المعلقة حالياً
    }

    /**
     * الحصول على خيارات التحقق المتاحة لعملية معينة
     * @param {string} action - نوع العملية
     * @returns {Promise<{success: boolean, options: Array, requires_password: boolean}>}
     */
    async getVerificationOptions(action) {
        try {
            const response = await DatabaseApiService.apiClient.get(
                `${this.baseUrl}/get-verification-options/${action}`
            );

            if (response.data?.success) {
                return {
                    success: true,
                    action: response.data.action,
                    actionName: response.data.action_name,
                    requiresPassword: response.data.requires_password,
                    options: response.data.options || [],
                };
            }

            return {
                success: false,
                error: response.data?.error || 'فشل في جلب خيارات التحقق',
            };
        } catch (error) {
            console.error('[SecureActions] خطأ في getVerificationOptions:', error);
            return {
                success: false,
                error: error.response?.data?.error || 'خطأ في الاتصال بالخادم',
            };
        }
    }

    /**
     * طلب رمز التحقق
     * @param {string} action - نوع العملية
     * @param {string} method - طريقة التحقق (email/sms)
     * @param {any} newValue - القيمة الجديدة (اختياري)
     * @param {string} oldPassword - كلمة المرور القديمة (للعمليات التي تتطلبها)
     * @returns {Promise<{success: boolean, message: string, maskedTarget: string}>}
     */
    async requestVerification(action, method, newValue = null, oldPassword = null) {
        try {
            const payload = {
                action,
                method,
            };

            if (newValue !== null) {
                payload.new_value = newValue;
            }

            if (oldPassword) {
                payload.old_password = oldPassword;
            }

            const response = await DatabaseApiService.apiClient.post(
                `${this.baseUrl}/request-verification`,
                payload
            );

            if (response.data?.success) {
                // حفظ العملية المعلقة
                this.pendingAction = {
                    action,
                    method,
                    newValue,
                    maskedTarget: response.data.masked_target,
                    expiresIn: response.data.expires_in,
                    requestedAt: Date.now(),
                };

                return {
                    success: true,
                    message: response.data.message,
                    method: response.data.method,
                    maskedTarget: response.data.masked_target,
                    expiresIn: response.data.expires_in,
                    actionName: response.data.action_name,
                };
            }

            return {
                success: false,
                error: response.data?.error || 'فشل في إرسال رمز التحقق',
                allowedMethods: response.data?.allowed_methods,
            };
        } catch (error) {
            console.error('[SecureActions] خطأ في requestVerification:', error);
            return {
                success: false,
                error: error.response?.data?.error || 'خطأ في الاتصال بالخادم',
            };
        }
    }

    /**
     * التحقق من OTP وتنفيذ العملية
     * @param {string} action - نوع العملية
     * @param {string} otp - رمز التحقق
     * @param {any} newValue - القيمة الجديدة (اختياري إذا أُرسلت في requestVerification)
     * @returns {Promise<{success: boolean, message: string}>}
     */
    async verifyAndExecute(action, otp, newValue = null) {
        try {
            const payload = {
                action,
                otp,
            };

            if (newValue !== null) {
                payload.new_value = newValue;
            }

            const response = await DatabaseApiService.apiClient.post(
                `${this.baseUrl}/verify-and-execute`,
                payload
            );

            if (response.data?.success) {
                // مسح العملية المعلقة
                this.pendingAction = null;

                return {
                    success: true,
                    message: response.data.message,
                };
            }

            return {
                success: false,
                error: response.data?.error || 'فشل في تنفيذ العملية',
            };
        } catch (error) {
            console.error('[SecureActions] خطأ في verifyAndExecute:', error);
            return {
                success: false,
                error: error.response?.data?.error || 'خطأ في الاتصال بالخادم',
            };
        }
    }

    /**
     * إلغاء طلب تحقق معلق
     * @param {string} action - نوع العملية
     */
    async cancelVerification(action) {
        try {
            await DatabaseApiService.apiClient.delete(
                `${this.baseUrl}/cancel-verification/${action}`
            );

            if (this.pendingAction?.action === action) {
                this.pendingAction = null;
            }

            return { success: true };
        } catch (error) {
            console.error('[SecureActions] خطأ في cancelVerification:', error);
            return { success: false };
        }
    }

    /**
     * الحصول على العملية المعلقة حالياً
     */
    getPendingAction() {
        if (!this.pendingAction) { return null; }

        // التحقق من انتهاء الصلاحية
        const elapsed = (Date.now() - this.pendingAction.requestedAt) / 1000;
        if (elapsed > this.pendingAction.expiresIn) {
            this.pendingAction = null;
            return null;
        }

        return {
            ...this.pendingAction,
            remainingTime: Math.max(0, this.pendingAction.expiresIn - elapsed),
        };
    }

    /**
     * التحقق من أن العملية تتطلب كلمة المرور القديمة
     */
    requiresOldPassword(action) {
        return action === SECURE_ACTIONS.CHANGE_PASSWORD;
    }

    /**
     * الحصول على طرق التحقق المسموحة لعملية معينة
     */
    getAllowedMethods(action) {
        // ✅ جميع العمليات تدعم SMS و Email - SMS أولاً (الافتراضي)
        return [VERIFICATION_METHODS.SMS, VERIFICATION_METHODS.EMAIL];
    }

    /**
     * الحصول على اسم العملية بالعربي
     */
    getActionName(action) {
        return ACTION_NAMES[action] || action;
    }

    /**
     * الحصول على رسالة توضيحية للتحقق
     */
    getVerificationMessage(action, method) {
        const actionName = this.getActionName(action);
        const methodName = method === 'email' ? 'الإيميل' : 'الجوال';
        return `لإتمام عملية "${actionName}"، سيتم إرسال رمز تحقق إلى ${methodName} المسجل`;
    }
}

// إنشاء instance واحد
const secureActionsService = new SecureActionsService();

export default secureActionsService;
