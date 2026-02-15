/**
 * خدمة إدارة الصلاحيات
 * تطلب جميع الصلاحيات المطلوبة عند أول استخدام للتطبيق
 *
 * @version 1.0
 */

import { Platform, Alert, Linking } from 'react-native';
import { PermissionsAndroid } from 'react-native';
import messaging from '@react-native-firebase/messaging';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Logger from './LoggerService';

class PermissionsService {
  constructor() {
    this.permissionsRequested = false;
  }

  /**
   * فحص إذا تم طلب الصلاحيات من قبل
   */
  async hasRequestedPermissions() {
    try {
      const requested = await AsyncStorage.getItem('permissions_requested');
      return requested === 'true';
    } catch (error) {
      return false;
    }
  }

  /**
   * تعليم أن الصلاحيات تم طلبها
   */
  async markPermissionsRequested() {
    try {
      await AsyncStorage.setItem('permissions_requested', 'true');
    } catch (error) {
      Logger.error('خطأ في حفظ حالة الصلاحيات', 'PermissionsService', error);
    }
  }

  /**
   * طلب جميع الصلاحيات المطلوبة
   * يُستدعى عند أول تشغيل للتطبيق
   */
  async requestAllPermissions() {
    try {
      // فحص إذا تم طلب الصلاحيات من قبل
      const alreadyRequested = await this.hasRequestedPermissions();
      if (alreadyRequested) {
        console.log('✅ الصلاحيات تم طلبها مسبقاً');
        return { alreadyRequested: true };
      }

      console.log('🔐 بدء طلب الصلاحيات...');

      const results = {
        notifications: false,
        camera: false,
        photos: false,
        biometric: false,
      };

      // 1. طلب صلاحية الإشعارات
      results.notifications = await this.requestNotificationPermission();

      // 2. طلب صلاحية الكاميرا (Android فقط)
      if (Platform.OS === 'android') {
        results.camera = await this.requestCameraPermission();
        results.photos = await this.requestPhotosPermission();
      } else {
        // iOS - الصلاحيات تُطلب تلقائياً عند الاستخدام
        results.camera = true;
        results.photos = true;
      }

      // 3. البصمة لا تحتاج صلاحية خاصة (تُطلب عند الاستخدام)
      results.biometric = true;

      // تعليم أن الصلاحيات تم طلبها
      await this.markPermissionsRequested();

      console.log('✅ نتائج طلب الصلاحيات:', results);
      return results;
    } catch (error) {
      Logger.error('خطأ في طلب الصلاحيات', 'PermissionsService', error);
      return { error: error.message };
    }
  }

  /**
   * طلب صلاحية الإشعارات
   */
  async requestNotificationPermission() {
    try {
      if (Platform.OS === 'ios') {
        // iOS - طلب صلاحية الإشعارات
        const authStatus = await messaging().requestPermission();
        const enabled =
          authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
          authStatus === messaging.AuthorizationStatus.PROVISIONAL;

        console.log(`📱 صلاحية الإشعارات (iOS): ${enabled ? '✅' : '❌'}`);
        return enabled;
      } else {
        // Android 13+ يتطلب طلب صلاحية POST_NOTIFICATIONS
        if (Platform.Version >= 33) {
          const granted = await PermissionsAndroid.request(
            PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS,
            {
              title: 'صلاحية الإشعارات',
              message: 'يحتاج التطبيق إلى إذن لإرسال إشعارات التداول والتنبيهات المهمة',
              buttonPositive: 'موافق',
              buttonNegative: 'لاحقاً',
            }
          );
          const enabled = granted === PermissionsAndroid.RESULTS.GRANTED;
          console.log(`📱 صلاحية الإشعارات (Android): ${enabled ? '✅' : '❌'}`);
          return enabled;
        }
        // Android < 13 - الإشعارات مفعلة افتراضياً
        return true;
      }
    } catch (error) {
      Logger.error('خطأ في طلب صلاحية الإشعارات', 'PermissionsService', error);
      return false;
    }
  }

  /**
   * طلب صلاحية الكاميرا (Android)
   */
  async requestCameraPermission() {
    try {
      if (Platform.OS !== 'android') { return true; }

      const granted = await PermissionsAndroid.request(
        PermissionsAndroid.PERMISSIONS.CAMERA,
        {
          title: 'صلاحية الكاميرا',
          message: 'يحتاج التطبيق إلى إذن الكاميرا لالتقاط صورة الملف الشخصي',
          buttonPositive: 'موافق',
          buttonNegative: 'لاحقاً',
        }
      );

      const enabled = granted === PermissionsAndroid.RESULTS.GRANTED;
      console.log(`📷 صلاحية الكاميرا: ${enabled ? '✅' : '❌'}`);
      return enabled;
    } catch (error) {
      Logger.error('خطأ في طلب صلاحية الكاميرا', 'PermissionsService', error);
      return false;
    }
  }

  /**
   * طلب صلاحية الصور/المعرض (Android)
   */
  async requestPhotosPermission() {
    try {
      if (Platform.OS !== 'android') { return true; }

      // Android 13+ يستخدم READ_MEDIA_IMAGES
      // Android < 13 يستخدم READ_EXTERNAL_STORAGE
      const permission = Platform.Version >= 33
        ? PermissionsAndroid.PERMISSIONS.READ_MEDIA_IMAGES
        : PermissionsAndroid.PERMISSIONS.READ_EXTERNAL_STORAGE;

      const granted = await PermissionsAndroid.request(permission, {
        title: 'صلاحية الصور',
        message: 'يحتاج التطبيق إلى إذن الوصول للصور لاختيار صورة الملف الشخصي',
        buttonPositive: 'موافق',
        buttonNegative: 'لاحقاً',
      });

      const enabled = granted === PermissionsAndroid.RESULTS.GRANTED;
      console.log(`🖼️ صلاحية الصور: ${enabled ? '✅' : '❌'}`);
      return enabled;
    } catch (error) {
      Logger.error('خطأ في طلب صلاحية الصور', 'PermissionsService', error);
      return false;
    }
  }

  /**
   * فحص حالة صلاحية معينة
   */
  async checkPermission(permissionType) {
    try {
      if (Platform.OS !== 'android') {
        // iOS - نفترض أن الصلاحيات ممنوحة حتى يتم رفضها
        return true;
      }

      let permission;
      switch (permissionType) {
        case 'camera':
          permission = PermissionsAndroid.PERMISSIONS.CAMERA;
          break;
        case 'photos':
          permission = Platform.Version >= 33
            ? PermissionsAndroid.PERMISSIONS.READ_MEDIA_IMAGES
            : PermissionsAndroid.PERMISSIONS.READ_EXTERNAL_STORAGE;
          break;
        case 'notifications':
          if (Platform.Version >= 33) {
            permission = PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS;
          } else {
            return true; // مفعلة افتراضياً
          }
          break;
        default:
          return false;
      }

      const result = await PermissionsAndroid.check(permission);
      return result;
    } catch (error) {
      Logger.error('خطأ في فحص الصلاحية', 'PermissionsService', error);
      return false;
    }
  }

  /**
   * فتح إعدادات التطبيق لتفعيل الصلاحيات يدوياً
   */
  openAppSettings() {
    Alert.alert(
      'الصلاحيات مطلوبة',
      'بعض الميزات تتطلب صلاحيات إضافية. هل تريد فتح إعدادات التطبيق؟',
      [
        { text: 'إلغاء', style: 'cancel' },
        {
          text: 'فتح الإعدادات',
          onPress: () => Linking.openSettings(),
        },
      ]
    );
  }

  /**
   * عرض شاشة ترحيبية لطلب الصلاحيات
   * تُستخدم لعرض رسالة توضيحية قبل طلب الصلاحيات
   */
  async showPermissionsWelcome(onAccept, onDecline) {
    const alreadyRequested = await this.hasRequestedPermissions();
    if (alreadyRequested) {
      onAccept && onAccept();
      return;
    }

    Alert.alert(
      '🔐 صلاحيات التطبيق',
      'لتقديم أفضل تجربة، يحتاج التطبيق إلى الصلاحيات التالية:\n\n' +
      '📱 الإشعارات - لتنبيهك بالصفقات والأرباح\n' +
      '📷 الكاميرا - لالتقاط صورة الملف الشخصي\n' +
      '🖼️ الصور - لاختيار صورة من المعرض\n' +
      '🔐 البصمة - لتسجيل دخول سريع وآمن\n\n' +
      'يمكنك تغيير هذه الإعدادات لاحقاً من إعدادات الجهاز.',
      [
        {
          text: 'لاحقاً',
          style: 'cancel',
          onPress: () => {
            this.markPermissionsRequested();
            onDecline && onDecline();
          },
        },
        {
          text: 'موافق',
          onPress: async () => {
            await this.requestAllPermissions();
            onAccept && onAccept();
          },
        },
      ]
    );
  }

  /**
   * الحصول على ملخص حالة الصلاحيات
   */
  async getPermissionsStatus() {
    const status = {
      notifications: await this.checkPermission('notifications'),
      camera: await this.checkPermission('camera'),
      photos: await this.checkPermission('photos'),
      requested: await this.hasRequestedPermissions(),
    };
    return status;
  }
}

// إنشاء instance واحد
const permissionsService = new PermissionsService();
export default permissionsService;
