/**
 * خدمة تخزين آمنة ومشفرة
 * تستخدم react-native-encrypted-storage للبيانات الحساسة
 * وتدعم Keychain (iOS) و Keystore (Android)
 *
 * @security AES-256 encryption
 * @compliance OWASP MASVS V2: Data Storage and Privacy
 */

import EncryptedStorage from 'react-native-encrypted-storage';
import { Platform } from 'react-native';

class SecureStorageService {
  constructor() {
    this.isAvailable = false;
    this.initialized = false;
  }

  /**
   * تهيئة الخدمة والتحقق من التوفر
   */
  async initialize() {
    if (this.initialized) {
      return this.isAvailable;
    }

    try {
      // اختبار التخزين الآمن
      await EncryptedStorage.setItem('@test_key', 'test_value');
      await EncryptedStorage.removeItem('@test_key');

      this.isAvailable = true;
      this.initialized = true;
      return true;
    } catch (error) {
      this.isAvailable = false;
      this.initialized = true;
      return false;
    }
  }

  /**
   * حفظ بيانات حساسة مشفرة
   * @param {string} key - المفتاح
   * @param {string|object} value - القيمة (ستُشفّر تلقائياً)
   */
  async setSecureItem(key, value) {
    try {
      await this.initialize();

      if (!this.isAvailable) {
        throw new Error('SecureStorage غير متاح');
      }

      const stringValue = typeof value === 'string' ? value : JSON.stringify(value);

      await EncryptedStorage.setItem(key, stringValue);
      return true;
    } catch (error) {
      throw error;
    }
  }

  /**
   * استرجاع بيانات مشفرة
   */
  async getSecureItem(key) {
    try {
      await this.initialize();

      if (!this.isAvailable) {
        return null;
      }

      return await EncryptedStorage.getItem(key);
    } catch (error) {
      return null;
    }
  }

  /**
   * حذف عنصر مشفر
   */
  async removeSecureItem(key) {
    try {
      await this.initialize();

      if (!this.isAvailable) {
        return false;
      }

      await EncryptedStorage.removeItem(key);
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * مسح جميع البيانات المشفرة
   */
  async clearSecureStorage() {
    try {
      await this.initialize();

      if (!this.isAvailable) {
        return false;
      }

      await EncryptedStorage.clear();
      return true;
    } catch (error) {
      return false;
    }
  }

  /**
   * حفظ token مشفر (JWT)
   */
  async setAuthToken(token) {
    return await this.setSecureItem('@auth_token', token);
  }

  /**
   * استرجاع token مشفر
   */
  async getAuthToken() {
    return await this.getSecureItem('@auth_token');
  }

  /**
   * حفظ بيانات المستخدم مشفرة
   */
  async setUserData(userData) {
    return await this.setSecureItem('@user_data', userData);
  }

  /**
   * استرجاع بيانات المستخدم
   */
  async getUserData() {
    const data = await this.getSecureItem('@user_data');
    if (!data) {return null;}
    try {
      return JSON.parse(data);
    } catch (parseError) {
      return null;
    }
  }

  /**
   * حفظ مفاتيح Binance مشفرة
   */
  async setBinanceKeys(userId, apiKey, secretKey) {
    const keys = {
      userId,
      apiKey,
      secretKey,
      savedAt: Date.now(),
    };
    return await this.setSecureItem(`@binance_keys_${userId}`, keys);
  }

  /**
   * استرجاع مفاتيح Binance
   */
  async getBinanceKeys(userId) {
    const data = await this.getSecureItem(`@binance_keys_${userId}`);
    if (!data) {return null;}
    try {
      return JSON.parse(data);
    } catch (parseError) {
      return null;
    }
  }

  /**
   * 🔐 حفظ كلمة المرور للدخول التلقائي بالبصمة (مشفرة)
   */
  async setSavedPassword(userId, password) {
    return await this.setSecureItem(`@saved_password_${userId}`, password);
  }

  /**
   * 🔓 استرجاع كلمة المرور المحفوظة
   */
  async getSavedPassword(userId) {
    return await this.getSecureItem(`@saved_password_${userId}`);
  }

  /**
   * 🗑️ حذف كلمة المرور المحفوظة
   */
  async removeSavedPassword(userId) {
    return await this.removeSecureItem(`@saved_password_${userId}`);
  }

  /**
   * حفظ بيانات البصمة بشكل آمن
   */
  async setBiometricData(userId, biometricData) {
    return await this.setSecureItem(`@biometric_${userId}`, biometricData);
  }

  /**
   * استرجاع بيانات البصمة
   */
  async getBiometricData(userId) {
    const data = await this.getSecureItem(`@biometric_${userId}`);
    if (!data) {return null;}
    try {
      return JSON.parse(data);
    } catch (parseError) {
      return null;
    }
  }

  /**
   * فحص حالة التخزين الآمن
   */
  getSecurityStatus() {
    return {
      available: this.isAvailable,
      platform: Platform.OS,
      storage: Platform.OS === 'ios' ? 'iOS Keychain' : 'Android Keystore',
      encryption: 'AES-256',
      initialized: this.initialized,
    };
  }
}

// إنشاء instance واحد
const secureStorageService = new SecureStorageService();

export default secureStorageService;
