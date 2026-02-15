/**
 * خدمة الإشعارات الفورية (Toast/Snackbar)
 * توفر ردود فعل فورية للمستخدم بعد كل إجراء
 */

class ToastService {
  constructor() {
    this.queue = [];
    this.listeners = {
      show: [],
      hide: [],
      hideAll: [],
    };
  }

  /**
   * تسجيل مستمع للأحداث
   */
  on(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event].push(callback);
    }
  }

  /**
   * إلغاء تسجيل مستمع
   */
  off(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter(cb => cb !== callback);
    }
  }

  /**
   * إطلاق حدث
   */
  emit(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(callback => callback(data));
    }
  }

  /**
   * عرض رسالة نجاح
   */
  success(message, duration = 3000) {
    this.show({
      type: 'success',
      message,
      duration,
    });
  }

  /**
   * عرض رسالة خطأ
   */
  error(message, duration = 3000) {
    this.show({
      type: 'error',
      message,
      duration,
    });
  }

  /**
   * عرض رسالة تحذير
   */
  warning(message, duration = 3000) {
    this.show({
      type: 'warning',
      message,
      duration,
    });
  }

  /**
   * عرض رسالة معلومات
   */
  info(message, duration = 3000) {
    this.show({
      type: 'info',
      message,
      duration,
    });
  }

  /**
   * عرض رسالة مخصصة
   */
  show(config) {
    // منع تكرار نفس الرسالة خلال ثانية واحدة
    const now = Date.now();
    const duplicateToast = this.queue.find(
      t => t.message === config.message && (now - t.timestamp) < 1000
    );
    if (duplicateToast) {
      return; // تجاهل الرسالة المكررة
    }

    // الحد الأقصى للرسائل المعروضة في نفس الوقت
    if (this.queue.length >= 3) {
      // إزالة أقدم رسالة
      const oldestToast = this.queue.shift();
      this.emit('hide', oldestToast.id);
    }

    const toast = {
      id: Date.now() + Math.random(),
      type: config.type || 'info',
      message: config.message,
      duration: config.duration || 3000,
      timestamp: Date.now(),
    };

    this.queue.push(toast);
    this.emit('show', toast);

    // إزالة تلقائية بعد المدة المحددة
    if (toast.duration > 0) {
      setTimeout(() => {
        this.hide(toast.id);
      }, toast.duration);
    }
  }

  /**
   * إخفاء رسالة محددة
   */
  hide(id) {
    this.queue = this.queue.filter(toast => toast.id !== id);
    this.emit('hide', id);
  }

  /**
   * إخفاء جميع الرسائل
   */
  hideAll() {
    this.queue = [];
    this.emit('hideAll');
  }

  /**
   * الحصول على الرسائل الحالية
   */
  getQueue() {
    return [...this.queue];
  }

  /**
   * ✅ الاشتراك في أحداث Toast (للتوافق مع ToastContainer)
   * @param {Function} callback - دالة تُستدعى عند عرض toast جديد
   * @returns {Function} - دالة لإلغاء الاشتراك
   */
  subscribe(callback) {
    this.on('show', callback);
    return () => this.off('show', callback);
  }

  // ═══════════════════════════════════════════════════════════════
  // ✅ دوال متوافقة مع FlashMessageService (للتوحيد)
  // ═══════════════════════════════════════════════════════════════

  /**
   * عرض رسالة نجاح (متوافق مع FlashMessageService)
   */
  showSuccess(message) {
    this.success(message);
  }

  /**
   * عرض رسالة خطأ (متوافق مع FlashMessageService)
   */
  showError(message) {
    this.error(message);
  }

  /**
   * عرض رسالة تحذير (متوافق مع FlashMessageService)
   */
  showWarning(message) {
    this.warning(message);
  }

  /**
   * عرض رسالة معلومات (متوافق مع FlashMessageService)
   */
  showInfo(message) {
    this.info(message);
  }
}

// إنشاء نسخة واحدة (Singleton)
const toastService = new ToastService();

export default toastService;
