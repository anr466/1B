/**
 * خدمة المصادقة البيومترية - محسّنة
 * تتعامل مع بصمة الإصبع والوجه على Android و iOS
 * @version 2.0 - تم إصلاح جميع المشاكل
 */

import { Alert, Platform } from 'react-native';
import ReactNativeBiometrics, { BiometryTypes } from 'react-native-biometrics';
import TempStorageService from './TempStorageService';
import SecureStorageService from './SecureStorageService';

class BiometricService {
  constructor() {
    // إنشاء instance صحيح من المكتبة
    this.rnBiometrics = new ReactNativeBiometrics({ allowDeviceCredentials: true });
    this.isInitialized = false;
    this._available = false;
    this.biometryType = null;
  }

  /**
   * تهيئة الخدمة وفحص التوفر
   */
  async initialize() {
    try {
      // console.log removed for production
      // استدعاء من خلال الـ instance
      const { available, biometryType } = await this.rnBiometrics.isSensorAvailable();

      this.isInitialized = true;
      this._available = available;
      this.biometryType = biometryType;

      // console.log removed for production
      return {
        available,
        biometryType,
        supportedTypes: this._getSupportedTypes(biometryType),
        error: null,
      };
    } catch (error) {
      console.error('❌ خطأ في تهيئة البيومترية:', error);
      this.isInitialized = true; // نعلّمها كـ initialized حتى لو فشلت
      this._available = false;

      return {
        available: false,
        biometryType: null,
        error: error.message,
      };
    }
  }

  /**
   * فحص إذا كانت البيومترية متاحة
   */
  async isAvailable() {
    if (!this.isInitialized) {
      const result = await this.initialize();
      return result.available;
    }
    return this._available;
  }

  /**
   * Alias لـ isAvailable للتوافق مع الكود القديم
   */
  async isBiometricAvailable() {
    return await this.isAvailable();
  }

  /**
   * Alias لـ registerBiometric للتوافق مع الكود القديم
   */
  async enableBiometric(userId, username = null) {
    return await this.registerBiometric(userId, username);
  }

  /**
   * الحصول على نوع البيومترية المتاحة
   */
  getBiometryType() {
    return this.biometryType;
  }

  /**
   * تسجيل البيومترية للمستخدم
   */
  async registerBiometric(userId, username) {
    try {
      // console.log removed for production
      const available = await this.isAvailable();
      if (!available) {
        throw new Error('البيومترية غير متاحة على هذا الجهاز');
      }

      // إنشاء مفاتيح جديدة
      const { publicKey } = await this.rnBiometrics.createKeys();
      // console.log removed for production
      // طلب المصادقة لتأكيد التسجيل
      const payload = `register_${userId}_${Date.now()}`;
      const { success, signature } = await this.rnBiometrics.createSignature({
        promptMessage: 'تسجيل البصمة',
        payload: payload,
      });

      if (!success) {
        throw new Error('فشل تأكيد البصمة');
      }

      // console.log removed for production
      // حفظ معلومات البصمة في التخزين المشفر
      const biometricData = {
        userId,
        username,
        publicKey,
        registered: true,
        registeredAt: new Date().toISOString(),
      };

      await SecureStorageService.setBiometricData(userId, biometricData);

      // تخزين آخر معرف مستخدم لإظهار شاشة البصمة عند الإقلاع القادم
      try {
        await TempStorageService.setItem('lastUserId', userId.toString());
        // console.log removed for production
      } catch (error) {
        console.error('❌ خطأ في حفظ lastUserId:', error);
      }

      return {
        success: true,
        message: 'تم تسجيل البيومترية بنجاح',
        publicKey,
      };
    } catch (error) {
      console.error('❌ خطأ في تسجيل البيومترية:', error);
      return {
        success: false,
        message: error.message || 'فشل في تسجيل البيومترية',
      };
    }
  }

  /**
   * التحقق من البيومترية
   */
  async verifyBiometric(userId) {
    try {
      const available = await this.isAvailable();
      if (!available) {
        return {
          success: false,
          message: 'البيومترية غير متاحة',
        };
      }

      const isRegistered = await this.isBiometricRegistered(userId);
      if (!isRegistered) {
        return {
          success: false,
          message: 'البيومترية غير مسجلة لهذا المستخدم',
        };
      }

      // طلب المصادقة
      const payload = `verify_${userId}_${Date.now()}`;
      const { success, signature } = await this.rnBiometrics.createSignature({
        promptMessage: 'تسجيل الدخول بالبصمة',
        payload: payload,
      });

      if (success) {
        // الحصول على اسم المستخدم المحفوظ
        const username = await this.getBiometricUsername(userId);

        // حفظ معرف المستخدم الأخير
        try {
          await TempStorageService.setItem('lastUserId', userId.toString());
          // console.log removed for production
        } catch (error) {
          console.error('❌ خطأ في حفظ lastUserId:', error);
        }

        return {
          success: true,
          username,
          message: 'تم التحقق بنجاح',
        };
      } else {
        return {
          success: false,
          message: 'فشل التحقق من البصمة',
        };
      }
    } catch (error) {
      console.error('❌ خطأ في التحقق البيومتري:', error);
      return {
        success: false,
        message: error.message || 'فشل التحقق',
      };
    }
  }

  /**
   * فحص إذا كانت البيومترية مسجلة للمستخدم
   */
  async isBiometricRegistered(userId) {
    try {
      const biometricData = await SecureStorageService.getBiometricData(userId);
      if (biometricData) {
        return biometricData.registered === true;
      }
      return false;
    } catch (error) {
      console.error('خطأ في فحص تسجيل البيومترية:', error);
      return false;
    }
  }

  /**
   * الحصول على اسم المستخدم المحفوظ مع البيومترية
   */
  async getBiometricUsername(userId) {
    try {
      const biometricData = await SecureStorageService.getBiometricData(userId);
      if (biometricData) {
        return biometricData.username;
      }
      return null;
    } catch (error) {
      console.error('خطأ في الحصول على اسم المستخدم:', error);
      return null;
    }
  }

  /**
   * حذف البيومترية المسجلة
   */
  async removeBiometric(userId) {
    try {
      await this.rnBiometrics.deleteKeys();
      await SecureStorageService.removeSecureItem(`@biometric_${userId}`);
      // console.log removed for production
      return {
        success: true,
        message: 'تم حذف البيومترية بنجاح',
      };
    } catch (error) {
      console.error('❌ خطأ في حذف البيومترية:', error);
      return {
        success: false,
        message: 'فشل في حذف البيومترية',
      };
    }
  }

  /**
   * عرض حوار تفعيل البيومترية
   */
  async promptEnableBiometric(userId, onSuccess, onCancel) {
    Alert.alert(
      'تفعيل المصادقة البيومترية',
      `هل تريد تفعيل ${this._getBiometryDisplayName()} لتسجيل الدخول السريع؟`,
      [
        {
          text: 'لاحقاً',
          style: 'cancel',
          onPress: onCancel,
        },
        {
          text: 'تفعيل',
          onPress: async () => {
            const result = await this.registerBiometric(userId);
            if (result.success) {
              Alert.alert('نجح', result.message);
              if (onSuccess) {onSuccess();}
            } else {
              Alert.alert('خطأ', result.message);
              if (onCancel) {onCancel();}
            }
          },
        },
      ]
    );
  }

  // ==================== الدوال المساعدة ====================

  /**
   * الحصول على معرف الجهاز
   */
  async _getDeviceId() {
    try {
      let deviceId = await TempStorageService.getItem('deviceId');
      if (!deviceId) {
        deviceId = `device_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        await TempStorageService.setItem('deviceId', deviceId);
      }
      return deviceId;
    } catch (error) {
      return `device_${Date.now()}`;
    }
  }

  /**
   * تحويل نوع البيومترية إلى نص
   */
  _mapBiometryType(biometryType) {
    switch (biometryType) {
      case 'TouchID':
        return 'fingerprint';
      case 'FaceID':
        return 'face';
      case 'Biometrics':
        return 'fingerprint'; // افتراضي للأندرويد
      default:
        return 'fingerprint';
    }
  }

  /**
   * الحصول على اسم البيومترية للعرض
   */
  _getBiometryDisplayName() {
    switch (this.biometryType) {
      case 'TouchID':
        return 'بصمة الإصبع';
      case 'FaceID':
        return 'التعرف على الوجه';
      case 'Biometrics':
        return 'البصمة البيومترية';
      default:
        return 'المصادقة البيومترية';
    }
  }

  /**
   * الحصول على الأنواع المدعومة
   */
  _getSupportedTypes(biometryType) {
    const types = [];
    if (biometryType === 'TouchID') {
      types.push('TouchID');
    }
    if (biometryType === 'FaceID') {
      types.push('FaceID');
    }
    if (biometryType === 'Biometrics') {
      types.push('Fingerprint');
    }
    return types;
  }
}

// إنشاء instance واحد للاستخدام في التطبيق
const BiometricAuth = new BiometricService();
export default BiometricAuth;
