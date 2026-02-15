/**
 * خدمة OTP موحدة - تدعم جميع عمليات التحقق
 * تتكامل مع DatabaseApiService وFirebase Auth
 * تدعم التحقق عبر الإيميل والرسائل النصية SMS
 *
 * ✅ Firebase Auth مُثبت ومُفعّل (v18.3.0)
 * ✅ SMS OTP يعمل عبر Firebase Phone Authentication
 * ✅ Email OTP يعمل عبر Backend (SimpleEmailOTPService)
 */

import DatabaseApiService from './DatabaseApiService';
import auth from '@react-native-firebase/auth';

// أنواع العمليات المدعومة
export const OTP_OPERATION_TYPES = {
  LOGIN: 'login',                 // تسجيل الدخول
  REGISTER: 'register',           // تسجيل مستخدم جديد
  CHANGE_EMAIL: 'change_email',   // تغيير الإيميل
  CHANGE_PASSWORD: 'change_password', // تغيير كلمة المرور
  RESET_PASSWORD: 'reset_password',    // نسيان كلمة المرور
};

// طرق التحقق
export const VERIFICATION_METHODS = {
  EMAIL: 'email',
  SMS: 'sms',
};

// رسائل مخصصة لكل عملية
const OPERATION_MESSAGES = {
  [OTP_OPERATION_TYPES.LOGIN]: {
    title: 'التحقق من الهوية',
    subtitle: 'تحقق من رمز الأمان المرسل إلى هاتفك',
    subtitlePhone: 'تحقق من رمز الأمان المرسل إلى هاتفك',
    sentMessage: 'تم إرسال رمز التحقق إلى هاتفك',
    sentMessagePhone: 'تم إرسال رمز التحقق إلى هاتفك',
    successMessage: 'تم التحقق بنجاح! مرحباً بك',
    buttonText: 'تسجيل الدخول',
    nextScreen: 'Dashboard',
  },
  [OTP_OPERATION_TYPES.REGISTER]: {
    title: 'تفعيل الحساب',
    subtitle: 'تحقق من إيميلك لتفعيل حسابك الجديد',
    subtitlePhone: 'تحقق من رقم هاتفك لتفعيل حسابك الجديد',
    sentMessage: 'تم إرسال رمز التفعيل إلى إيميلك',
    sentMessagePhone: 'تم إرسال رمز التفعيل إلى هاتفك',
    successMessage: 'تم تفعيل حسابك بنجاح! مرحباً بك في تطبيق التداول الذكي',
    buttonText: 'تفعيل الحساب',
    nextScreen: 'Dashboard',
  },
  [OTP_OPERATION_TYPES.CHANGE_EMAIL]: {
    title: 'تغيير الإيميل',
    subtitle: 'تحقق من إيميلك الجديد لتأكيد التغيير',
    sentMessage: 'تم إرسال رمز التحقق إلى الإيميل الجديد',
    successMessage: 'تم تغيير إيميلك بنجاح',
    buttonText: 'تأكيد الإيميل الجديد',
    nextScreen: 'Settings',
  },
  [OTP_OPERATION_TYPES.CHANGE_PASSWORD]: {
    title: 'تغيير كلمة المرور',
    subtitle: 'تحقق من هويتك لتغيير كلمة المرور',
    sentMessage: 'تم إرسال رمز التحقق إلى إيميلك',
    successMessage: 'تم تغيير كلمة المرور بنجاح',
    buttonText: 'تأكيد التغيير',
    nextScreen: 'NewPassword',
  },
  [OTP_OPERATION_TYPES.RESET_PASSWORD]: {
    title: 'إعادة تعيين كلمة المرور',
    subtitle: 'تحقق من إيميلك لإعادة تعيين كلمة مرور جديدة',
    sentMessage: 'تم إرسال رمز إعادة التعيين إلى إيميلك',
    successMessage: 'تم التحقق بنجاح، يمكنك الآن إنشاء كلمة مرور جديدة',
    buttonText: 'تأكيد الهوية',
    nextScreen: 'NewPassword',
  },
};

class OTPService {
  constructor() {
    this.databaseApi = DatabaseApiService;
    this.phoneConfirmation = null; // لحفظ confirmation من Firebase
  }

  /**
   * إرسال OTP حسب نوع العملية
   * @param {string} target - الإيميل أو رقم الهاتف
   * @param {string} operationType - نوع العملية (من OTP_OPERATION_TYPES)
   * @param {object} additionalData - بيانات إضافية حسب نوع العملية
   * @returns {Promise<{success: boolean, message: string, data?: any}>}
   */
  async sendOTP(target, operationType, additionalData = {}) {
    try {
      const isPhone = additionalData.isPhone || false;

      // التحقق من صحة المعاملات
      if (!target || !operationType) {
        return {
          success: false,
          message: isPhone ? 'رقم الهاتف ونوع العملية مطلوبان' : 'الإيميل ونوع العملية مطلوبان',
        };
      }

      // التحقق من صحة الإيميل أو الهاتف
      if (isPhone) {
        if (!this.validatePhone(target)) {
          return {
            success: false,
            message: 'صيغة رقم الهاتف غير صحيحة',
          };
        }
      } else {
        if (!this.validateEmail(target)) {
          return {
            success: false,
            message: 'صيغة الإيميل غير صحيحة',
          };
        }
      }

      // التحقق من نوع العملية
      if (!Object.values(OTP_OPERATION_TYPES).includes(operationType)) {
        return {
          success: false,
          message: 'نوع العملية غير مدعوم',
        };
      }

      let response;

      // إرسال OTP حسب الطريقة المختارة
      if (isPhone) {
        // إرسال SMS عبر Firebase
        response = await this._sendPhoneOTP(target, additionalData);
      } else {
        // إرسال OTP عبر الإيميل أو SMS
        switch (operationType) {
          case OTP_OPERATION_TYPES.LOGIN:
            response = await this._sendLoginOTP(target, additionalData);
            break;

          case OTP_OPERATION_TYPES.REGISTER:
            response = await this._sendRegisterOTP(target, additionalData);
            break;

          case OTP_OPERATION_TYPES.CHANGE_EMAIL:
            response = await this._sendChangeEmailOTP(target, additionalData);
            break;

          case OTP_OPERATION_TYPES.CHANGE_PASSWORD:
            response = await this._sendChangePasswordOTP(target, additionalData);
            break;

          case OTP_OPERATION_TYPES.RESET_PASSWORD:
            response = await this._sendResetPasswordOTP(target, additionalData);
            break;

          default:
            return {
              success: false,
              message: 'نوع العملية غير مدعوم',
            };
        }
      }

      return response;

    } catch (error) {
      console.error('خطأ في إرسال OTP:', error);
      return {
        success: false,
        message: 'حدث خطأ في إرسال رمز التحقق. يرجى المحاولة مرة أخرى',
      };
    }
  }

  /**
   * التحقق من OTP
   * @param {string} email - الإيميل
   * @param {string} code - رمز OTP
   * @param {string} operationType - نوع العملية
   * @param {object} additionalData - بيانات إضافية
   * @returns {Promise<{success: boolean, message: string, data?: any}>}
   */
  async verifyOTP(email, code, operationType, additionalData = {}) {
    try {
      // التحقق من المعاملات
      if (!email || !code || !operationType) {
        return {
          success: false,
          message: 'جميع البيانات مطلوبة للتحقق',
        };
      }

      // التحقق من طول الرمز
      if (code.length !== 6 || !/^\d{6}$/.test(code)) {
        return {
          success: false,
          message: 'رمز التحقق يجب أن يكون 6 أرقام',
        };
      }

      let response;

      // التحقق حسب نوع العملية
      switch (operationType) {
        case OTP_OPERATION_TYPES.LOGIN:
          response = await this._verifyLoginOTP(email, code, additionalData);
          break;

        case OTP_OPERATION_TYPES.REGISTER:
          response = await this._verifyRegisterOTP(email, code, additionalData);
          break;

        case OTP_OPERATION_TYPES.CHANGE_EMAIL:
          response = await this._verifyChangeEmailOTP(email, code, additionalData);
          break;

        case OTP_OPERATION_TYPES.CHANGE_PASSWORD:
          response = await this._verifyChangePasswordOTP(email, code, additionalData);
          break;

        case OTP_OPERATION_TYPES.RESET_PASSWORD:
          response = await this._verifyResetPasswordOTP(email, code, additionalData);
          break;

        default:
          return {
            success: false,
            message: 'نوع العملية غير مدعوم',
          };
      }

      return response;

    } catch (error) {
      console.error('خطأ في التحقق من OTP:', error);
      return {
        success: false,
        message: 'حدث خطأ في التحقق. يرجى المحاولة مرة أخرى',
      };
    }
  }

  /**
   * التحقق من OTP للهاتف عبر ID Token (للخادم)
   * @deprecated استخدم verifyPhoneOTP(code, additionalData) بدلاً منها
   */
  async verifyPhoneTokenWithServer(idToken, phoneNumber) {
    try {
      if (!idToken) {
        return {
          success: false,
          message: 'رمز المصادقة مطلوب',
        };
      }

      const response = await this.databaseApi.verifyPhoneToken(idToken, phoneNumber);

      if (response.success) {
        return {
          success: true,
          message: 'تم التحقق من الهاتف بنجاح',
          data: response,
        };
      }

      return {
        success: false,
        message: response.error || 'فشل التحقق من الهاتف',
      };

    } catch (error) {
      console.error('خطأ في التحقق من الهاتف:', error);
      return {
        success: false,
        message: 'حدث خطأ في التحقق. يرجى المحاولة مرة أخرى',
      };
    }
  }

  /**
   * إعادة إرسال OTP
   * @param {string} email - الإيميل
   * @param {string} operationType - نوع العملية
   * @param {object} additionalData - بيانات إضافية
   * @returns {Promise<{success: boolean, message: string}>}
   */
  async resendOTP(email, operationType, additionalData = {}) {
    try {
      // إعادة إرسال بنفس منطق الإرسال الأول
      const response = await this.sendOTP(email, operationType, additionalData);

      if (response.success) {
        return {
          success: true,
          message: 'تم إعادة إرسال رمز التحقق بنجاح',
        };
      }

      return response;

    } catch (error) {
      console.error('خطأ في إعادة إرسال OTP:', error);
      return {
        success: false,
        message: 'فشل في إعادة الإرسال. يرجى المحاولة مرة أخرى',
      };
    }
  }

  /**
   * ✅ إلغاء OTP نشط
   * @param {string} email - الإيميل
   * @param {string} operationType - نوع العملية
   * @returns {Promise<{success: boolean, message: string}>}
   */
  async cancelOTP(email, operationType) {
    try {
      // تحويل operationType إلى purpose
      const purposeMap = {
        'login': 'login',
        'register': 'registration',
        'reset_password': 'password_reset',
        'change_email': 'change_email',
        'change_password': 'change_password',
      };

      const purpose = purposeMap[operationType] || 'password_reset';

      const response = await this.databaseApi.cancelOTP(email, purpose);

      if (response.success) {
        return {
          success: true,
          message: 'تم إلغاء رمز التحقق بنجاح',
        };
      }

      return {
        success: false,
        message: response.error || 'فشل في إلغاء رمز التحقق',
      };

    } catch (error) {
      console.error('خطأ في إلغاء OTP:', error);
      return {
        success: false,
        message: 'حدث خطأ في الإلغاء',
      };
    }
  }

  /**
   * الحصول على رسائل العملية
   * @param {string} operationType - نوع العملية
   * @returns {object} رسائل العملية
   */
  getOperationMessages(operationType) {
    return OPERATION_MESSAGES[operationType] || OPERATION_MESSAGES[OTP_OPERATION_TYPES.REGISTER];
  }

  /**
   * التحقق من صحة الإيميل
   * @param {string} email - الإيميل
   * @returns {boolean}
   */
  validateEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  }

  /**
   * التحقق من صحة رقم الهاتف
   * @param {string} phone - رقم الهاتف
   * @returns {boolean}
   */
  validatePhone(phone) {
    if (!phone) { return false; }
    const cleanPhone = phone.replace(/[^0-9+]/g, '');
    // يجب أن يكون 10-15 رقم
    return /^(\+?[0-9]{10,15})$/.test(cleanPhone);
  }

  /**
   * تنسيق رقم الهاتف للإرسال
   * @param {string} phone - رقم الهاتف
   * @returns {string} رقم الهاتف بالتنسيق الدولي
   */
  formatPhoneNumber(phone) {
    if (!phone) { return phone; }
    let cleanPhone = phone.replace(/[^0-9+]/g, '');

    // إذا بدأ بـ 0، استبدله بـ +966 (السعودية)
    if (cleanPhone.startsWith('0')) {
      cleanPhone = '+966' + cleanPhone.substring(1);
    }
    // إذا لم يبدأ بـ +، أضف +966
    if (!cleanPhone.startsWith('+')) {
      cleanPhone = '+966' + cleanPhone;
    }

    return cleanPhone;
  }

  /**
   * إخفاء جزء من الإيميل للعرض
   * @param {string} email - الإيميل
   * @returns {string} الإيميل المخفي جزئياً
   */
  maskEmail(email) {
    if (!email || !this.validateEmail(email)) { return email; }

    const [localPart, domain] = email.split('@');
    if (localPart.length <= 2) { return email; }

    const maskedLocal = localPart[0] + '*'.repeat(localPart.length - 2) + localPart[localPart.length - 1];
    return `${maskedLocal}@${domain}`;
  }

  /**
   * إخفاء جزء من رقم الهاتف للعرض
   * @param {string} phone - رقم الهاتف
   * @returns {string} رقم الهاتف المخفي جزئياً
   */
  maskPhone(phone) {
    if (!phone) { return phone; }
    const cleanPhone = phone.replace(/[^0-9+]/g, '');
    if (cleanPhone.length < 6) { return phone; }

    // إظهار أول 4 أرقام وآخر 2
    const start = cleanPhone.substring(0, 4);
    const end = cleanPhone.substring(cleanPhone.length - 2);
    const middle = '*'.repeat(cleanPhone.length - 6);

    return `${start}${middle}${end}`;
  }

  // ==================== وظائف خاصة لكل نوع عملية ====================

  /**
   * إرسال OTP لتسجيل الدخول
   */
  async _sendLoginOTP(identifier, additionalData) {
    try {
      const method = additionalData.method || 'sms';
      const response = await this.databaseApi.sendLoginOTP(identifier, additionalData.password, method);

      if (response.success) {
        return {
          success: true,
          message: response.message || 'تم إرسال رمز التحقق',
          data: response,
        };
      }

      return {
        success: false,
        message: response.error || 'فشل في إرسال رمز التحقق',
      };

    } catch (error) {
      throw error;
    }
  }

  /**
   * إرسال OTP للتسجيل
   */
  async _sendRegisterOTP(email, additionalData) {
    try {
      const method = additionalData.method || 'sms';
      const phone = additionalData.phone || null;
      const response = await this.databaseApi.sendRegistrationOTP(email, method, phone);

      if (response.success) {
        return {
          success: true,
          message: response.message || 'تم إرسال رمز التفعيل',
          data: response,
        };
      }

      return {
        success: false,
        message: response.message || 'فشل في إرسال رمز التفعيل',
      };

    } catch (error) {
      throw error;
    }
  }

  /**
   * إرسال OTP لتغيير الإيميل
   */
  async _sendChangeEmailOTP(email, additionalData) {
    try {
      const response = await this.databaseApi.sendChangeEmailOTP(email, additionalData);
      return response;
    } catch (error) {
      throw error;
    }
  }

  /**
   * إرسال OTP لتغيير كلمة المرور
   */
  async _sendChangePasswordOTP(email, additionalData) {
    try {
      const response = await this.databaseApi.sendChangePasswordOTP(email, additionalData);
      return response;
    } catch (error) {
      throw error;
    }
  }

  /**
   * إرسال OTP لإعادة تعيين كلمة المرور
   */
  async _sendResetPasswordOTP(email, additionalData) {
    try {
      const method = additionalData.method || 'sms';
      const phone = additionalData.phone || null;
      const response = await this.databaseApi.sendResetPasswordOTP(email, { ...additionalData, method, phone });

      if (response.success) {
        return {
          success: true,
          message: response.message || 'تم إرسال رمز إعادة التعيين',
          data: response,
        };
      }

      return {
        success: false,
        message: response.message || response.error || 'فشل في إرسال رمز إعادة التعيين',
      };
    } catch (error) {
      throw error;
    }
  }

  /**
   * إرسال OTP عبر SMS (Firebase)
   * @param {string} phoneNumber - رقم الهاتف
   * @param {object} additionalData - بيانات إضافية
   * @returns {Promise<{success: boolean, message: string, data?: any}>}
   */
  async _sendPhoneOTP(phoneNumber, additionalData) {
    try {
      // تنسيق رقم الهاتف
      const formattedPhone = this.formatPhoneNumber(phoneNumber);
      console.log('📱 إرسال SMS عبر Firebase إلى:', formattedPhone);

      // ✅ إرسال SMS عبر Firebase Phone Authentication
      const confirmation = await auth().signInWithPhoneNumber(formattedPhone);

      // حفظ confirmation للتحقق لاحقاً
      this.phoneConfirmation = confirmation;

      return {
        success: true,
        message: 'تم إرسال رمز التحقق إلى هاتفك',
        data: {
          verificationId: confirmation.verificationId,
          phoneNumber: formattedPhone,
        },
      };

    } catch (error) {
      console.error('❌ خطأ في إرسال SMS:', error);

      // معالجة أخطاء Firebase المحددة
      let errorMessage = 'فشل في إرسال رمز التحقق';

      if (error.code === 'auth/invalid-phone-number') {
        errorMessage = 'رقم الهاتف غير صحيح';
      } else if (error.code === 'auth/too-many-requests') {
        errorMessage = 'تم تجاوز الحد الأقصى للمحاولات. يرجى المحاولة لاحقاً';
      } else if (error.code === 'auth/quota-exceeded') {
        errorMessage = 'تم تجاوز الحد اليومي للرسائل';
      }

      return {
        success: false,
        message: errorMessage,
      };
    }
  }

  /**
   * التحقق من OTP المرسل عبر SMS
   * @param {string} code - رمز التحقق
   * @param {object} additionalData - بيانات إضافية
   */
  async verifyPhoneOTP(code, additionalData = {}) {
    try {
      if (!this.phoneConfirmation) {
        return {
          success: false,
          message: 'لم يتم إرسال رمز التحقق. يرجى إعادة المحاولة',
        };
      }

      // التحقق من الرمز عبر Firebase
      const userCredential = await this.phoneConfirmation.confirm(code);

      if (userCredential && userCredential.user) {
        // الحصول على ID Token لإرساله للخادم
        const idToken = await userCredential.user.getIdToken();

        // إرسال Token للخادم للتحقق وإكمال التسجيل
        const response = await this.databaseApi.verifyPhoneToken(idToken, additionalData.phone);

        // مسح confirmation بعد النجاح
        this.phoneConfirmation = null;

        return {
          success: true,
          message: 'تم التحقق من رقم الهاتف بنجاح',
          data: {
            ...response,
            firebaseUser: userCredential.user,
          },
        };
      }

      return {
        success: false,
        message: 'فشل التحقق من الرمز',
      };

    } catch (error) {
      console.error('❌ خطأ في التحقق من SMS:', error);

      let errorMessage = 'رمز التحقق غير صحيح';

      if (error.code === 'auth/invalid-verification-code') {
        errorMessage = 'رمز التحقق غير صحيح';
      } else if (error.code === 'auth/code-expired') {
        errorMessage = 'انتهت صلاحية رمز التحقق. يرجى طلب رمز جديد';
      }

      return {
        success: false,
        message: errorMessage,
      };
    }
  }

  /**
   * التحقق من OTP لتسجيل الدخول
   */
  async _verifyLoginOTP(userId, code, additionalData) {
    try {
      const response = await this.databaseApi.verifyLoginOTP(userId, code);
      return response;
    } catch (error) {
      throw error;
    }
  }

  /**
   * التحقق من OTP للتسجيل
   */
  async _verifyRegisterOTP(email, code, additionalData) {
    try {
      const response = await this.databaseApi.verifyEmail(email, code, OTP_OPERATION_TYPES.REGISTER);
      return response;
    } catch (error) {
      throw error;
    }
  }

  /**
   * التحقق من OTP لتغيير الإيميل
   */
  async _verifyChangeEmailOTP(email, code, additionalData) {
    try {
      const response = await this.databaseApi.verifyChangeEmail(email, code, additionalData);
      return response;
    } catch (error) {
      throw error;
    }
  }

  /**
   * التحقق من OTP لتغيير كلمة المرور
   */
  async _verifyChangePasswordOTP(email, code, additionalData) {
    try {
      const response = await this.databaseApi.verifyChangePassword(email, code, additionalData);
      return response;
    } catch (error) {
      throw error;
    }
  }

  /**
   * التحقق من OTP لإعادة تعيين كلمة المرور
   */
  async _verifyResetPasswordOTP(email, code, additionalData) {
    try {
      const response = await this.databaseApi.verifyResetPassword(email, code, additionalData);
      return response;
    } catch (error) {
      throw error;
    }
  }
}

// إنشاء instance واحد للاستخدام
const otpService = new OTPService();

export default otpService;
export { OTPService };
