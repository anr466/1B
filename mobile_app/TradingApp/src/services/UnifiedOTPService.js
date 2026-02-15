/**
 * 🔐 Unified OTP Service - خدمة موحدة لجميع عمليات OTP
 * =========================================================
 * 
 * خدمة شاملة لجميع تدفقات OTP في التطبيق:
 * - Login OTP
 * - Registration OTP
 * - Password Reset OTP
 * - Email Verification OTP
 * - Change Password OTP
 * 
 * Features:
 * - إرسال OTP موحد
 * - التحقق من OTP موحد
 * - إعادة إرسال OTP موحد
 * - إلغاء OTP موحد
 * - Error handling موحد
 * - Validation موحد
 * - Timer management موحد
 */

import DatabaseApiService from './DatabaseApiService';
import Logger from '../utils/Logger';

class UnifiedOTPService {
    constructor() {
        this.apiService = new DatabaseApiService();

        // OTP purposes
        this.PURPOSES = {
            LOGIN: 'login',
            REGISTRATION: 'registration',
            PASSWORD_RESET: 'password_reset',
            EMAIL_VERIFICATION: 'email_verification',
            CHANGE_PASSWORD: 'change_password'
        };

        // Error codes
        this.ERROR_CODES = {
            INVALID_CODE: 'OTP_INVALID',
            EXPIRED: 'OTP_EXPIRED',
            TOO_MANY_ATTEMPTS: 'OTP_TOO_MANY_ATTEMPTS',
            RATE_LIMITED: 'OTP_RATE_LIMITED',
            SERVICE_UNAVAILABLE: 'OTP_SERVICE_UNAVAILABLE',
            NOT_FOUND: 'OTP_NOT_FOUND'
        };

        // Error messages (Arabic)
        this.ERROR_MESSAGES = {
            [this.ERROR_CODES.INVALID_CODE]: 'رمز التحقق غير صحيح',
            [this.ERROR_CODES.EXPIRED]: 'انتهت صلاحية رمز التحقق',
            [this.ERROR_CODES.TOO_MANY_ATTEMPTS]: 'تم تجاوز عدد المحاولات المسموح بها',
            [this.ERROR_CODES.RATE_LIMITED]: 'يرجى الانتظار قبل طلب رمز جديد',
            [this.ERROR_CODES.SERVICE_UNAVAILABLE]: 'خدمة OTP غير متاحة حالياً',
            [this.ERROR_CODES.NOT_FOUND]: 'لم يتم العثور على رمز تحقق نشط'
        };
    }

    /**
     * إرسال OTP موحد
     * 
     * @param {string} identifier - email أو phone number
     * @param {string} purpose - نوع العملية (login, registration, etc.)
     * @param {string} method - طريقة الإرسال (sms أو email) - الافتراضي: sms
     * @param {object} additionalData - بيانات إضافية (مثل password للـ login)
     * @returns {Promise<object>} response
     */
    async sendOTP(identifier, purpose, method = 'sms', additionalData = {}) {
        try {
            Logger.info(`Sending OTP for ${purpose} to ${identifier} via ${method}`);

            // Validate inputs
            if (!identifier || !purpose) {
                return {
                    success: false,
                    error: 'المعرف ونوع العملية مطلوبان',
                    error_code: 'INVALID_INPUT'
                };
            }

            // Route to appropriate endpoint based on purpose
            let response;

            switch (purpose) {
                case this.PURPOSES.LOGIN:
                    response = await this.apiService.sendLoginOTP(
                        identifier,
                        additionalData.password,
                        method
                    );
                    break;

                case this.PURPOSES.REGISTRATION:
                    response = await this.apiService.sendRegistrationOTP(
                        identifier,
                        method,
                        additionalData.phone
                    );
                    break;

                case this.PURPOSES.PASSWORD_RESET:
                    response = await this.apiService.sendResetPasswordOTP(
                        identifier,
                        additionalData
                    );
                    break;

                case this.PURPOSES.EMAIL_VERIFICATION:
                    response = await this.apiService.resendVerificationEmail(identifier);
                    break;

                default:
                    return {
                        success: false,
                        error: 'نوع العملية غير صحيح',
                        error_code: 'INVALID_PURPOSE'
                    };
            }

            // Normalize response
            return this._normalizeResponse(response);

        } catch (error) {
            Logger.error('Send OTP failed', error);
            return {
                success: false,
                error: 'خطأ في إرسال رمز التحقق',
                error_code: 'INTERNAL_ERROR'
            };
        }
    }

    /**
     * التحقق من OTP موحد
     * 
     * @param {string} identifier - email أو phone number
     * @param {string} otpCode - رمز التحقق
     * @param {string} purpose - نوع العملية
     * @param {object} additionalData - بيانات إضافية
     * @returns {Promise<object>} response
     */
    async verifyOTP(identifier, otpCode, purpose, additionalData = {}) {
        try {
            Logger.info(`Verifying OTP for ${purpose}`);

            // Validate inputs
            if (!identifier || !otpCode || !purpose) {
                return {
                    success: false,
                    verified: false,
                    error: 'جميع الحقول مطلوبة',
                    error_code: 'INVALID_INPUT'
                };
            }

            // Validate OTP format (6 digits)
            if (!/^\d{6}$/.test(otpCode)) {
                return {
                    success: false,
                    verified: false,
                    error: 'رمز التحقق يجب أن يكون 6 أرقام',
                    error_code: this.ERROR_CODES.INVALID_CODE
                };
            }

            // Route to appropriate endpoint
            let response;

            switch (purpose) {
                case this.PURPOSES.LOGIN:
                    response = await this.apiService.verifyLoginOTP(
                        additionalData.userId,
                        otpCode
                    );
                    break;

                case this.PURPOSES.REGISTRATION:
                    response = await this.apiService.verifyRegistrationOTP({
                        email: identifier,
                        otp_code: otpCode,
                        ...additionalData
                    });
                    break;

                case this.PURPOSES.PASSWORD_RESET:
                    response = await this.apiService.verifyResetOTP(
                        identifier,
                        otpCode
                    );
                    break;

                case this.PURPOSES.EMAIL_VERIFICATION:
                    response = await this.apiService.verifyEmail(
                        identifier,
                        otpCode,
                        'register'
                    );
                    break;

                default:
                    return {
                        success: false,
                        verified: false,
                        error: 'نوع العملية غير صحيح',
                        error_code: 'INVALID_PURPOSE'
                    };
            }

            // Normalize response
            return this._normalizeVerifyResponse(response);

        } catch (error) {
            Logger.error('Verify OTP failed', error);
            return {
                success: false,
                verified: false,
                error: 'خطأ في التحقق من الرمز',
                error_code: 'INTERNAL_ERROR'
            };
        }
    }

    /**
     * إعادة إرسال OTP موحد
     * 
     * @param {string} identifier - email أو phone number
     * @param {string} purpose - نوع العملية
     * @param {string} method - طريقة الإرسال (الافتراضي: sms)
     * @param {object} additionalData - بيانات إضافية
     * @returns {Promise<object>} response
     */
    async resendOTP(identifier, purpose, method = 'sms', additionalData = {}) {
        try {
            Logger.info(`Resending OTP for ${purpose}`);

            // Route to appropriate endpoint
            let response;

            switch (purpose) {
                case this.PURPOSES.LOGIN:
                    response = await this.apiService.resendLoginOTP(
                        additionalData.userId
                    );
                    break;

                case this.PURPOSES.REGISTRATION:
                case this.PURPOSES.PASSWORD_RESET:
                case this.PURPOSES.EMAIL_VERIFICATION:
                    // For these, we just send a new OTP
                    response = await this.sendOTP(identifier, purpose, method, additionalData);
                    break;

                default:
                    return {
                        success: false,
                        error: 'نوع العملية غير صحيح',
                        error_code: 'INVALID_PURPOSE'
                    };
            }

            return this._normalizeResponse(response);

        } catch (error) {
            Logger.error('Resend OTP failed', error);
            return {
                success: false,
                error: 'خطأ في إعادة إرسال رمز التحقق',
                error_code: 'INTERNAL_ERROR'
            };
        }
    }

    /**
     * إلغاء OTP نشط
     * 
     * @param {string} identifier - email أو phone number
     * @param {string} purpose - نوع العملية
     * @returns {Promise<object>} response
     */
    async cancelOTP(identifier, purpose) {
        try {
            Logger.info(`Cancelling OTP for ${purpose}`);

            const response = await this.apiService.cancelOTP(identifier, purpose);

            return {
                success: response.success || false,
                message: response.message || 'تم إلغاء رمز التحقق'
            };

        } catch (error) {
            Logger.error('Cancel OTP failed', error);
            return {
                success: false,
                error: 'خطأ في إلغاء رمز التحقق'
            };
        }
    }

    /**
     * الحصول على رسالة خطأ مفهومة
     * 
     * @param {string} errorCode - كود الخطأ
     * @param {string} defaultMessage - رسالة افتراضية
     * @returns {string} error message
     */
    getErrorMessage(errorCode, defaultMessage = 'حدث خطأ') {
        return this.ERROR_MESSAGES[errorCode] || defaultMessage;
    }

    /**
     * توحيد response format
     * @private
     */
    _normalizeResponse(response) {
        if (!response) {
            return {
                success: false,
                error: 'لم يتم استلام استجابة',
                error_code: 'NO_RESPONSE'
            };
        }

        return {
            success: response.success || false,
            message: response.message || response.error || '',
            data: response.data || {
                masked_target: response.masked_target || '',
                expires_in: response.expires_in || 300,
                can_resend_after: response.can_resend_after || 60,
                methods_available: response.methods_available || ['email']
            },
            error: response.error || null,
            error_code: response.error_code || null,
            wait_seconds: response.wait_seconds || null
        };
    }

    /**
     * توحيد verify response format
     * @private
     */
    _normalizeVerifyResponse(response) {
        if (!response) {
            return {
                success: false,
                verified: false,
                error: 'لم يتم استلام استجابة',
                error_code: 'NO_RESPONSE'
            };
        }

        return {
            success: response.success || false,
            verified: response.verified || response.success || false,
            message: response.message || '',
            data: response.data || response.user || null,
            error: response.error || null,
            error_code: response.error_code || null,
            attempts_remaining: response.attempts_remaining || null
        };
    }

    /**
     * Validate OTP code format
     * 
     * @param {string} otpCode - رمز التحقق
     * @returns {object} {valid: boolean, error: string}
     */
    validateOTPFormat(otpCode) {
        if (!otpCode) {
            return {
                valid: false,
                error: 'رمز التحقق مطلوب'
            };
        }

        if (!/^\d{6}$/.test(otpCode)) {
            return {
                valid: false,
                error: 'رمز التحقق يجب أن يكون 6 أرقام'
            };
        }

        return {
            valid: true,
            error: null
        };
    }
}

// Export singleton instance
export default new UnifiedOTPService();
