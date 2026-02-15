/**
 * نظام Cache ذكي لتحسين الأداء
 * ✅ إنتاج: بدون console.logs
 * ✅ آمن: لا يكشف البيانات
 * ✅ مستقر: TTL ذكي وتنظيف تلقائي
 */

class CacheService {
  constructor() {
    this.cache = new Map();
    this.cleanupInterval = null;

    // TTL (Time To Live) بالميلي ثانية
    this.ttl = {
      portfolio: 10000,           // 10 ثواني
      stats: 30000,               // 30 ثانية
      successfulCoins: 300000,    // 5 دقائق
      trades: 60000,              // دقيقة واحدة
      settings: 600000,           // 10 دقائق
      binanceKeys: 600000,        // 10 دقائق
      profile: 300000,            // 5 دقائق
      notifications: 60000,       // دقيقة واحدة
    };

    this.stats = {
      hits: 0,
      misses: 0,
      sets: 0,
      invalidations: 0,
    };
  }

  /**
   * الحصول على بيانات من Cache
   *
   * @param {string} key - المفتاح (مثل: coins_123, portfolio_123)
   * @param {string} type - نوع البيانات (portfolio, stats, successfulCoins, etc.)
   * @returns {any|null} البيانات إذا كانت موجودة وصالحة، null خلاف ذلك
   */
  get(key, type) {
    const item = this.cache.get(key);

    if (!item) {
      this.stats.misses++;
      return null;
    }

    const ttl = this.ttl[type] || 60000;
    const age = Date.now() - item.timestamp;

    if (age < ttl) {
      this.stats.hits++;
      return item.data;
    } else {
      this.cache.delete(key);
      this.stats.misses++;
      return null;
    }
  }

  /**
   * حفظ بيانات في Cache
   *
   * @param {string} key - المفتاح
   * @param {any} data - البيانات
   * @param {string} type - نوع البيانات
   */
  set(key, data, type) {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      type,
    });
    this.stats.sets++;
  }

  /**
   * إبطال (حذف) بيانات من Cache
   *
   * مفيد عند تحديث البيانات في Server
   *
   * @param {string} key - المفتاح
   */
  invalidate(key) {
    if (this.cache.has(key)) {
      this.cache.delete(key);
      this.stats.invalidations++;
      return true;
    }
    return false;
  }

  /**
   * إبطال جميع بيانات مستخدم معين
   *
   * @param {number} userId - معرف المستخدم
   */
  invalidateUser(userId) {
    let count = 0;

    this.cache.forEach((value, key) => {
      if (key.includes(`_${userId}`)) {
        this.cache.delete(key);
        count++;
      }
    });

    if (count > 0) {
      this.stats.invalidations += count;
    }
    return count;
  }

  /**
   * حذف جميع البيانات المنتهية الصلاحية
   *
   * @returns {number} عدد العناصر المحذوفة
   */
  clearExpired() {
    let count = 0;
    const now = Date.now();

    this.cache.forEach((value, key) => {
      const ttl = this.ttl[value.type] || 60000;
      const age = now - value.timestamp;

      if (age >= ttl) {
        this.cache.delete(key);
        count++;
      }
    });

    return count;
  }

  /**
   * مسح جميع بيانات Cache
   */
  clearAll() {
    this.cache.clear();
    this.stats = { hits: 0, misses: 0, sets: 0, invalidations: 0 };
  }

  /**
   * الحصول على إحصائيات Cache
   *
   * @returns {object} إحصائيات الاستخدام
   */
  getStats() {
    const total = this.stats.hits + this.stats.misses;
    const hitRate = total > 0 ? ((this.stats.hits / total) * 100).toFixed(1) : 0;

    return {
      entries: this.cache.size,
      hits: this.stats.hits,
      misses: this.stats.misses,
      hitRate: `${hitRate}%`,
      sets: this.stats.sets,
      invalidations: this.stats.invalidations,
    };
  }

  /**
   * الحصول على حجم Cache
   *
   * @returns {number} عدد العناصر
   */
  size() {
    return this.cache.size;
  }

  /**
   * فحص إذا كان المفتاح موجود (بغض النظر عن الصلاحية)
   *
   * @param {string} key - المفتاح
   * @returns {boolean}
   */
  has(key) {
    return this.cache.has(key);
  }

  /**
   * ✅ بدء التنظيف التلقائي
   */
  startAutoCleanup() {
    if (this.cleanupInterval) {return;}

    this.cleanupInterval = setInterval(() => {
      this.clearExpired();
    }, 300000);
  }

  /**
   * ✅ إيقاف التنظيف التلقائي
   */
  stopAutoCleanup() {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
  }
}

// Instance واحدة للاستخدام في جميع أنحاء التطبيق
const cacheService = new CacheService();

// ✅ لا يتم بدء التنظيف التلقائي هنا
// سيتم بدءه من App.js عند mount

export default cacheService;
