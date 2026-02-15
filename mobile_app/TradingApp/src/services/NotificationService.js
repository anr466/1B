/**
 * خدمة الإشعارات باستخدام Firebase Cloud Messaging
 * تدير إرسال واستقبال الإشعارات للتطبيق
 * ✅ مع دعم Deep Linking للتنقل من الإشعارات
 */

import { Alert } from 'react-native';
import messaging from '@react-native-firebase/messaging';
import TempStorageService from './TempStorageService';
import Logger from './LoggerService';

// ✅ مرجع التنقل للوصول من خارج React Components
let navigationRef = null;

class NotificationService {
  constructor() {
    this.fcmToken = null;
    this.isInitialized = false;
    this.pendingNotification = null; // إشعار معلق للتنقل بعد تحميل التطبيق
  }

  /**
   * ✅ تعيين مرجع التنقل (يُستدعى من App.js)
   */
  setNavigationRef(ref) {
    navigationRef = ref;
    // إذا كان هناك إشعار معلق، نفذ التنقل الآن
    if (this.pendingNotification) {
      this.handleNotificationAction(this.pendingNotification);
      this.pendingNotification = null;
    }
  }

  /**
   * تهيئة خدمة الإشعارات
   */
  async initialize() {
    try {
      // طلب الإذن للإشعارات
      const authStatus = await messaging().requestPermission();
      const enabled =
        authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
        authStatus === messaging.AuthorizationStatus.PROVISIONAL;

      if (!enabled) {
        // console.log removed for production
        return false;
      }

      // الحصول على FCM Token
      this.fcmToken = await messaging().getToken();
      // console.log removed for production
      // حفظ التوكن محلياً
      await TempStorageService.setItem('fcmToken', this.fcmToken);

      // إعداد معالجات الإشعارات
      this.setupMessageHandlers();

      this.isInitialized = true;
      return true;
    } catch (error) {
      Logger.error('خطأ في تهيئة خدمة الإشعارات', 'NotificationService', error);
      return false;
    }
  }

  /**
   * إعداد معالجات الإشعارات
   */
  setupMessageHandlers() {
    if (!messaging) {
      return;
    }
    // معالج الإشعارات عند فتح التطبيق
    messaging().onMessage(async remoteMessage => {
      // console.log removed for production
      // عرض الإشعار كـ Alert
      if (remoteMessage.notification) {
        Alert.alert(
          remoteMessage.notification.title || 'إشعار جديد',
          remoteMessage.notification.body || '',
          [
            { text: 'موافق', style: 'default' },
          ]
        );
      }

      // حفظ الإشعار في قاعدة البيانات المحلية
      await this.saveNotificationLocally(remoteMessage);
    });

    // معالج الإشعارات عند النقر عليها (التطبيق مغلق)
    messaging().onNotificationOpenedApp(remoteMessage => {
      // console.log removed for production
      this.handleNotificationAction(remoteMessage);
    });

    // معالج الإشعارات عند فتح التطبيق لأول مرة من إشعار
    messaging()
      .getInitialNotification()
      .then(remoteMessage => {
        if (remoteMessage) {
          // console.log removed for production
          this.handleNotificationAction(remoteMessage);
        }
      });

    // معالج تحديث التوكن
    messaging().onTokenRefresh(token => {
      // console.log removed for production
      this.fcmToken = token;
      TempStorageService.setItem('fcmToken', token);
      // يمكن إرسال التوكن الجديد للخادم هنا
    });
  }

  /**
   * ✅ معالجة إجراءات الإشعارات مع Deep Linking
   */
  handleNotificationAction(remoteMessage) {
    if (!remoteMessage?.data) {
      // console.log removed for production
      return;
    }

    const { type, action, tradeId, userId, screen } = remoteMessage.data;
    // console.log removed for production
    // إذا لم يكن التنقل جاهزاً، احفظ الإشعار للتنفيذ لاحقاً
    if (!navigationRef?.isReady?.()) {
      // console.log removed for production
      this.pendingNotification = remoteMessage;
      return;
    }

    // تحديد الشاشة المستهدفة
    let targetScreen = screen || 'Dashboard';
    let params = {};

    switch (type) {
      case 'trade_signal':
      case 'trade_opened':
        targetScreen = 'Dashboard';
        params = { highlightTrades: true };
        // console.log removed for production
        break;

      case 'trade_completed':
      case 'trade_closed':
      case 'trade_closed_profit':
      case 'trade_closed_loss':
        targetScreen = 'TradeHistory';
        params = { tradeId };
        // console.log removed for production
        break;

      case 'portfolio_update':
      case 'balance_update':
        targetScreen = 'Portfolio';
        // console.log removed for production
        break;

      case 'daily_loss_limit':
      case 'balance_low':
      case 'system_alert':
      case 'alert':
        targetScreen = 'Notifications';
        // console.log removed for production
        break;

      case 'settings':
        targetScreen = 'Settings';
        // console.log removed for production
        break;

      default:
        // console.log removed for production
        targetScreen = 'Dashboard';
    }

    // تنفيذ التنقل
    try {
      navigationRef.navigate(targetScreen, params);
      // console.log removed for production
    } catch (navError) {
      Logger.error('خطأ في التنقل', 'NotificationService', navError);
      // محاولة التنقل للشاشة الرئيسية كخطة بديلة
      try {
        navigationRef.navigate('Dashboard');
      } catch (e) {
        Logger.error('فشل التنقل البديل', 'NotificationService', e);
      }
    }
  }

  /**
   * حفظ الإشعار محلياً
   */
  async saveNotificationLocally(remoteMessage) {
    try {
      const notification = {
        id: Date.now().toString(),
        title: remoteMessage.notification?.title || '',
        body: remoteMessage.notification?.body || '',
        data: remoteMessage.data || {},
        receivedAt: new Date().toISOString(),
        read: false,
      };

      // جلب الإشعارات المحفوظة
      const savedNotifications = await TempStorageService.getItem('notifications');
      let notifications = [];
      if (savedNotifications) {
        try {
          notifications = JSON.parse(savedNotifications);
        } catch (parseError) {
          Logger.warn('فشل تحليل الإشعارات المحفوظة', 'NotificationService', parseError);
          notifications = [];
        }
      }

      // إضافة الإشعار الجديد
      notifications.unshift(notification);

      // الاحتفاظ بآخر 50 إشعار فقط
      if (notifications.length > 50) {
        notifications.splice(50);
      }

      // حفظ الإشعارات المحدثة
      await TempStorageService.setItem('notifications', JSON.stringify(notifications));
    } catch (error) {
      Logger.error('خطأ في حفظ الإشعار محلياً', 'NotificationService', error);
    }
  }

  /**
   * الحصول على الإشعارات المحفوظة محلياً
   */
  async getLocalNotifications() {
    try {
      const savedNotifications = await TempStorageService.getItem('notifications');
      return savedNotifications ? JSON.parse(savedNotifications) : [];
    } catch (error) {
      Logger.error('خطأ في جلب الإشعارات المحلية', 'NotificationService', error);
      return [];
    }
  }

  /**
   * تحديد إشعار كمقروء
   */
  async markNotificationAsRead(notificationId) {
    try {
      const savedNotifications = await TempStorageService.getItem('notifications');
      let notifications = [];
      if (savedNotifications) {
        try {
          notifications = JSON.parse(savedNotifications);
        } catch (parseError) {
          Logger.warn('فشل تحليل الإشعارات في markAsRead', 'NotificationService', parseError);
          return false;
        }
      }

      const updatedNotifications = notifications.map(notification =>
        notification.id === notificationId
          ? { ...notification, read: true }
          : notification
      );

      await TempStorageService.setItem('notifications', JSON.stringify(updatedNotifications));
      return true;
    } catch (error) {
      Logger.error('خطأ في تحديد الإشعار كمقروء', 'NotificationService', error);
      return false;
    }
  }

  /**
   * مسح جميع الإشعارات
   */
  async clearAllNotifications() {
    try {
      await TempStorageService.removeItem('notifications');
      return true;
    } catch (error) {
      Logger.error('خطأ في مسح الإشعارات', 'NotificationService', error);
      return false;
    }
  }

  /**
   * الحصول على FCM Token
   */
  async getFCMToken() {
    if (!messaging) {
      Logger.warn('لا يمكن الحصول على FCM Token بدون Firebase messaging', 'NotificationService');
      return null;
    }
    if (this.fcmToken) {
      return this.fcmToken;
    }

    try {
      const token = await TempStorageService.getItem('fcmToken');
      if (token) {
        this.fcmToken = token;
        return token;
      }

      // إذا لم يكن محفوظ، احصل على واحد جديد
      const newToken = await messaging().getToken();
      this.fcmToken = newToken;
      await TempStorageService.setItem('fcmToken', newToken);
      return newToken;
    } catch (error) {
      Logger.error('خطأ في الحصول على FCM Token', 'NotificationService', error);
      return null;
    }
  }

  /**
   * تسجيل التوكن مع الخادم
   */
  async registerTokenWithServer(userId, databaseApiService) {
    try {
      const token = await this.getFCMToken();
      if (!token) {
        Logger.error('لا يوجد FCM Token للتسجيل', 'NotificationService');
        return false;
      }

      // إرسال التوكن للخادم (لا نحتاج userId لأن الـ token يحدد المستخدم)
      const response = await databaseApiService.registerFCMToken(token);
      return response?.success || false;
    } catch (error) {
      Logger.error('خطأ في تسجيل التوكن مع الخادم', 'NotificationService', error);
      return false;
    }
  }

  /**
   * إلغاء تسجيل التوكن من الخادم
   */
  async unregisterTokenFromServer(userId, databaseApiService) {
    try {
      const token = await this.getFCMToken();
      if (!token) {
        return true; // لا يوجد توكن للإلغاء
      }

      // إلغاء التسجيل من الخادم
      const response = await databaseApiService.unregisterFCMToken(userId, token);
      return response.success;
    } catch (error) {
      Logger.error('خطأ في إلغاء تسجيل التوكن', 'NotificationService', error);
      return false;
    }
  }

  /**
   * فحص حالة الإذن للإشعارات
   */
  async checkPermissionStatus() {
    try {
      if (!messaging) {
        return false;
      }
      const authStatus = await messaging().hasPermission();
      return authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
        authStatus === messaging.AuthorizationStatus.PROVISIONAL;
    } catch (error) {
      Logger.error('خطأ في فحص إذن الإشعارات', 'NotificationService', error);
      return false;
    }
  }

  /**
   * طلب الإذن للإشعارات مرة أخرى
   */
  async requestPermission() {
    try {
      if (!messaging) {
        return false;
      }
      const authStatus = await messaging().requestPermission();
      return authStatus === messaging.AuthorizationStatus.AUTHORIZED ||
        authStatus === messaging.AuthorizationStatus.PROVISIONAL;
    } catch (error) {
      Logger.error('خطأ في طلب إذن الإشعارات', 'NotificationService', error);
      return false;
    }
  }
}

// ✅ إنشاء instance واحد
const notificationService = new NotificationService();

// ✅ تصدير الدالة للوصول من App.js
export const setNavigationRef = (ref) => notificationService.setNavigationRef(ref);

export default notificationService;
