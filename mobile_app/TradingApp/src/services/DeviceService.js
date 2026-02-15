/**
 * خدمة إدارة الجهاز والأمان
 * تتعامل مع معلومات الجهاز والحماية
 */

import { Platform } from 'react-native';
import DeviceInfo from 'react-native-device-info';
import DatabaseApiService from './DatabaseApiService';
import TempStorageService from './TempStorageService';
import Logger from './LoggerService';

class DeviceService {
  constructor() {
    this.deviceInfo = null;
  }

  /**
   * الحصول على معلومات الجهاز
   */
  async getDeviceInfo() {
    if (this.deviceInfo) {
      return this.deviceInfo;
    }

    try {
      let deviceId = await TempStorageService.getItem('deviceId');
      if (!deviceId) {
        deviceId = `device_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        await TempStorageService.setItem('deviceId', deviceId);
      }

      this.deviceInfo = {
        deviceId,
        deviceName: await this._getDeviceName(),
        platform: Platform.OS,
        version: Platform.Version.toString(),
        model: await this._getDeviceModel(),
        brand: await this._getDeviceBrand(),
        systemVersion: await this._getSystemVersion(),
        buildNumber: await this._getBuildNumber(),
        bundleId: await this._getBundleId(),
        isEmulator: await this._isEmulator(),
        hasNotch: await this._hasNotch(),
        totalMemory: await this._getTotalMemory(),
        registeredAt: new Date().toISOString(),
      };

      return this.deviceInfo;
    } catch (error) {
      Logger.error('خطأ في الحصول على معلومات الجهاز', 'DeviceService', error);
      return {
        deviceId: `device_${Date.now()}`,
        deviceName: 'Unknown Device',
        platform: Platform.OS,
        version: Platform.Version.toString(),
        model: 'Unknown',
        brand: 'Unknown',
        systemVersion: 'Unknown',
        buildNumber: 'Unknown',
        bundleId: 'Unknown',
        isEmulator: false,
        hasNotch: false,
        totalMemory: 0,
        registeredAt: new Date().toISOString(),
      };
    }
  }

  /**
   * تسجيل الجهاز في قاعدة البيانات
   */
  async registerDevice(userId) {
    try {
      const deviceInfo = await this.getDeviceInfo();

      const result = await DatabaseApiService.registerDevice(userId, {
        ...deviceInfo,
        user_id: userId,
      });

      if (result.success) {
        await TempStorageService.setItem('deviceRegistered', 'true');
        await TempStorageService.setItem('deviceRegisteredAt', new Date().toISOString());
      }

      return result;
    } catch (error) {
      Logger.error('خطأ في تسجيل الجهاز', 'DeviceService', error);
      return {
        success: false,
        message: 'فشل في تسجيل الجهاز',
      };
    }
  }

  /**
   * فحص إذا كان الجهاز مسجل
   */
  async isDeviceRegistered() {
    try {
      const registered = await TempStorageService.getItem('deviceRegistered');
      return registered === 'true';
    } catch (error) {
      return false;
    }
  }

  /**
   * الحصول على معرف الجهاز الفريد
   */
  async getDeviceId() {
    const deviceInfo = await this.getDeviceInfo();
    return deviceInfo.deviceId;
  }

  /**
   * إنشاء بصمة أمان للجهاز
   */
  async createSecurityFingerprint() {
    try {
      const deviceInfo = await this.getDeviceInfo();

      const fingerprint = {
        deviceId: deviceInfo.deviceId,
        platform: deviceInfo.platform,
        model: deviceInfo.model,
        timestamp: Date.now(),
        hash: this._generateHash(deviceInfo),
      };

      await TempStorageService.setItem('securityFingerprint', JSON.stringify(fingerprint));
      return fingerprint;
    } catch (error) {
      Logger.error('خطأ في إنشاء بصمة الأمان', 'DeviceService', error);
      return null;
    }
  }

  /**
   * التحقق من بصمة الأمان
   */
  async verifySecurityFingerprint() {
    try {
      const storedFingerprint = await TempStorageService.getItem('securityFingerprint');
      if (!storedFingerprint) { return false; }

      const fingerprint = JSON.parse(storedFingerprint);
      const currentDeviceInfo = await this.getDeviceInfo();
      const currentHash = this._generateHash(currentDeviceInfo);

      return fingerprint.hash === currentHash;
    } catch (error) {
      Logger.error('خطأ في التحقق من بصمة الأمان', 'DeviceService', error);
      return false;
    }
  }

  /**
   * تنظيف بيانات الجهاز
   */
  async clearDeviceData() {
    try {
      await TempStorageService.multiRemove([
        'deviceId',
        'deviceRegistered',
        'deviceRegisteredAt',
        'securityFingerprint',
      ]);

      this.deviceInfo = null;
      return true;
    } catch (error) {
      Logger.error('خطأ في تنظيف بيانات الجهاز', 'DeviceService', error);
      return false;
    }
  }

  // ==================== الدوال المساعدة ====================

  /**
   * الحصول على اسم الجهاز
   */
  async _getDeviceName() {
    try {
      if (DeviceInfo) {
        return await DeviceInfo.getDeviceName();
      } else {
        return Platform.OS === 'ios' ? 'iPhone/iPad' : 'Android Device';
      }
    } catch (error) {
      return Platform.OS === 'ios' ? 'iPhone/iPad' : 'Android Device';
    }
  }

  /**
   * الحصول على موديل الجهاز
   */
  async _getDeviceModel() {
    try {
      if (DeviceInfo) {
        return await DeviceInfo.getModel();
      } else {
        return Platform.OS === 'ios' ? 'iOS Device' : 'Android Device';
      }
    } catch (error) {
      return 'Unknown';
    }
  }

  /**
   * فحص إذا كان الجهاز محاكي
   */
  async _isEmulator() {
    try {
      if (DeviceInfo) {
        return await DeviceInfo.isEmulator();
      } else {
        return false;
      }
    } catch (error) {
      return false;
    }
  }

  /**
   * الحصول على العلامة التجارية للجهاز
   */
  async _getDeviceBrand() {
    try {
      if (DeviceInfo) {
        return await DeviceInfo.getBrand();
      } else {
        return Platform.OS === 'ios' ? 'Apple' : 'Android';
      }
    } catch (error) {
      return 'Unknown';
    }
  }

  /**
   * الحصول على إصدار النظام
   */
  async _getSystemVersion() {
    try {
      if (DeviceInfo) {
        return await DeviceInfo.getSystemVersion();
      } else {
        return Platform.Version.toString();
      }
    } catch (error) {
      return Platform.Version.toString();
    }
  }

  /**
   * الحصول على رقم البناء
   */
  async _getBuildNumber() {
    try {
      if (DeviceInfo) {
        return await DeviceInfo.getBuildNumber();
      } else {
        return '1.0';
      }
    } catch (error) {
      return '1.0';
    }
  }

  /**
   * الحصول على Bundle ID
   */
  async _getBundleId() {
    try {
      if (DeviceInfo) {
        return await DeviceInfo.getBundleId();
      } else {
        return 'com.tradingapp';
      }
    } catch (error) {
      return 'com.tradingapp';
    }
  }

  /**
   * فحص إذا كان الجهاز يحتوي على notch
   */
  async _hasNotch() {
    try {
      if (DeviceInfo) {
        return await DeviceInfo.hasNotch();
      } else {
        return false;
      }
    } catch (error) {
      return false;
    }
  }

  /**
   * الحصول على إجمالي الذاكرة
   */
  async _getTotalMemory() {
    try {
      if (DeviceInfo) {
        return await DeviceInfo.getTotalMemory();
      } else {
        return 0;
      }
    } catch (error) {
      return 0;
    }
  }

  /**
   * إنشاء hash للجهاز
   */
  _generateHash(deviceInfo) {
    const data = `${deviceInfo.deviceId}_${deviceInfo.platform}_${deviceInfo.model}_${deviceInfo.brand}`;
    // إنشاء hash بسيط بدون مكتبات خارجية
    let hash = 0;
    for (let i = 0; i < data.length; i++) {
      const char = data.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash).toString(36).padStart(32, '0').substr(0, 32);
  }
}

// إنشاء instance واحد للاستخدام في التطبيق
const DeviceManager = new DeviceService();
export default DeviceManager;
