/**
 * AppStateManager - مدير حالة التطبيق المركزي
 * ===============================================
 * يُنظم العمليات ويضمن تزامن الحالات وتحديث البيانات
 *
 * المسؤوليات:
 * 1. تنظيم العمليات (Operations Coordination)
 * 2. مزامنة الحالات بين الشاشات (State Sync)
 * 3. إدارة جلب البيانات (Data Fetching)
 * 4. معالجة الأخطاء المرئية (User-Visible Errors)
 */

import { DeviceEventEmitter } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import DatabaseApiService from './DatabaseApiService';
import ToastService from './ToastService';
import { isAdmin } from '../utils/userUtils';

// أحداث التزامن
export const AppEvents = {
    // حالة النظام
    SYSTEM_STATUS_CHANGED: 'SYSTEM_STATUS_CHANGED',
    TRADING_MODE_CHANGED: 'TRADING_MODE_CHANGED',
    CONNECTION_STATUS_CHANGED: 'CONNECTION_STATUS_CHANGED',

    // البيانات
    PORTFOLIO_UPDATED: 'PORTFOLIO_UPDATED',
    SETTINGS_UPDATED: 'SETTINGS_UPDATED',
    STATS_UPDATED: 'STATS_UPDATED',
    POSITIONS_UPDATED: 'POSITIONS_UPDATED',

    // العمليات
    OPERATION_STARTED: 'OPERATION_STARTED',
    OPERATION_COMPLETED: 'OPERATION_COMPLETED',
    OPERATION_FAILED: 'OPERATION_FAILED',

    // التحديث
    FORCE_REFRESH: 'FORCE_REFRESH',
    CACHE_INVALIDATE: 'CACHE_INVALIDATE',
};

// رسائل الأخطاء المرئية للمستخدم
const UserErrorMessages = {
    NETWORK_ERROR: '❌ لا يوجد اتصال بالإنترنت\nتحقق من اتصالك وحاول مرة أخرى',
    TIMEOUT_ERROR: '⏱️ انتهى وقت الانتظار\nالخادم بطيء - حاول مرة أخرى',
    SERVER_ERROR: '⚠️ خطأ في الخادم\nيرجى المحاولة لاحقاً',
    AUTH_ERROR: '🔐 انتهت صلاحية الجلسة\nيرجى إعادة تسجيل الدخول',
    VALIDATION_ERROR: '⚠️ بيانات غير صحيحة\nتحقق من المدخلات',
    UNKNOWN_ERROR: '❌ حدث خطأ غير متوقع\nحاول مرة أخرى',

    // عمليات محددة
    START_SYSTEM_FAILED: '❌ فشل تشغيل النظام\nتحقق من الاتصال وحاول مرة أخرى',
    STOP_SYSTEM_FAILED: '❌ فشل إيقاف النظام\nقد تحتاج لإعادة المحاولة',
    SAVE_SETTINGS_FAILED: '❌ فشل حفظ الإعدادات\nتحقق من الاتصال',
    LOAD_DATA_FAILED: '⚠️ فشل تحميل البيانات\nاسحب للتحديث',
};

class AppStateManager {
    constructor() {
        // حالة التطبيق المركزية
        this._state = {
            isConnected: true,
            systemStatus: {
                is_running: false,
                status: 'stopped',
                lastUpdate: null,
            },
            tradingMode: 'demo',
            isAdmin: false,
            userId: null,

            // العمليات الجارية
            pendingOperations: new Set(),

            // Cache للبيانات
            cache: {
                portfolio: { data: null, timestamp: 0 },
                settings: { data: null, timestamp: 0 },
                stats: { data: null, timestamp: 0 },
                positions: { data: null, timestamp: 0 },
            },
        };

        // مدة صلاحية Cache (30 ثانية)
        this.CACHE_TTL = 30000;

        // مستمعين للأحداث
        this._listeners = {};
    }

    // ═══════════════════════════════════════════════════════════════
    // 1. إدارة الحالة المركزية
    // ═══════════════════════════════════════════════════════════════

    /**
     * تهيئة المستخدم
     */
    async initializeUser(user) {
        if (!user) { return; }

        this._state.userId = user.id;
        this._state.isAdmin = isAdmin(user);

        // تحميل البيانات الأولية
        await this.loadInitialData();
    }

    /**
     * تحميل البيانات الأولية
     */
    async loadInitialData() {
        if (!this._state.userId) { return; }

        try {
            // جلب البيانات بالتوازي
            const [settingsRes, portfolioRes] = await Promise.all([
                this.fetchSettings(true),
                this.fetchPortfolio(true),
            ]);

            // إشعار الشاشات بالبيانات الجديدة
            this.emit(AppEvents.SETTINGS_UPDATED, settingsRes);
            this.emit(AppEvents.PORTFOLIO_UPDATED, portfolioRes);

        } catch (error) {
            console.error('[AppStateManager] Error loading initial data:', error);
        }
    }

    /**
     * تحديث حالة الاتصال
     */
    updateConnectionStatus(isConnected) {
        if (this._state.isConnected !== isConnected) {
            this._state.isConnected = isConnected;
            this.emit(AppEvents.CONNECTION_STATUS_CHANGED, { isConnected });

            if (!isConnected) {
                ToastService.warning('⚠️ فقد الاتصال بالخادم');
            } else {
                ToastService.success('✅ تم استعادة الاتصال');
                // تحديث البيانات عند استعادة الاتصال
                this.forceRefreshAll();
            }
        }
    }

    /**
     * تحديث حالة النظام
     */
    updateSystemStatus(status) {
        const oldStatus = this._state.systemStatus.is_running;

        this._state.systemStatus = {
            ...this._state.systemStatus,
            ...status,
            lastUpdate: Date.now(),
        };

        // إذا تغيرت الحالة، أشعر جميع الشاشات
        if (oldStatus !== status.is_running) {
            this.emit(AppEvents.SYSTEM_STATUS_CHANGED, this._state.systemStatus);
        }
    }

    /**
     * تحديث وضع التداول
     */
    updateTradingMode(mode) {
        if (this._state.tradingMode !== mode) {
            this._state.tradingMode = mode;
            this.emit(AppEvents.TRADING_MODE_CHANGED, { mode });

            // مسح Cache عند تغيير الوضع
            this.invalidateCache();
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // 2. إدارة العمليات
    // ═══════════════════════════════════════════════════════════════

    /**
     * بدء عملية
     */
    startOperation(operationId) {
        this._state.pendingOperations.add(operationId);
        this.emit(AppEvents.OPERATION_STARTED, { operationId });
    }

    /**
     * إنهاء عملية بنجاح
     */
    completeOperation(operationId, result) {
        this._state.pendingOperations.delete(operationId);
        this.emit(AppEvents.OPERATION_COMPLETED, { operationId, result });
    }

    /**
     * فشل عملية
     */
    failOperation(operationId, error) {
        this._state.pendingOperations.delete(operationId);
        this.emit(AppEvents.OPERATION_FAILED, { operationId, error });

        // عرض رسالة خطأ واضحة للمستخدم
        const userMessage = this.getUserErrorMessage(error);
        ToastService.error(userMessage);
    }

    /**
     * هل توجد عملية جارية
     */
    isOperationPending(operationId) {
        return this._state.pendingOperations.has(operationId);
    }

    // ═══════════════════════════════════════════════════════════════
    // 3. جلب البيانات مع Cache
    // ═══════════════════════════════════════════════════════════════

    /**
     * جلب المحفظة
     */
    async fetchPortfolio(forceRefresh = false) {
        const cacheKey = 'portfolio';

        // استخدام Cache إذا كان صالحاً
        if (!forceRefresh && this.isCacheValid(cacheKey)) {
            return this._state.cache[cacheKey].data;
        }

        try {
            const mode = this._state.isAdmin ? this._state.tradingMode : null;
            const response = await DatabaseApiService.getPortfolio(this._state.userId, mode);

            if (response?.success && response?.data) {
                this.updateCache(cacheKey, response.data);
                return response.data;
            }
        } catch (error) {
            console.error('[AppStateManager] fetchPortfolio error:', error);
            throw error;
        }

        return null;
    }

    /**
     * جلب الإعدادات
     */
    async fetchSettings(forceRefresh = false) {
        const cacheKey = 'settings';

        if (!forceRefresh && this.isCacheValid(cacheKey)) {
            return this._state.cache[cacheKey].data;
        }

        try {
            const mode = this._state.isAdmin ? this._state.tradingMode : null;
            const response = await DatabaseApiService.getSettings(this._state.userId, mode);

            if (response?.success && response?.data) {
                this.updateCache(cacheKey, response.data);
                return response.data;
            }
        } catch (error) {
            console.error('[AppStateManager] fetchSettings error:', error);
            throw error;
        }

        return null;
    }

    /**
     * جلب الإحصائيات
     */
    async fetchStats(forceRefresh = false) {
        const cacheKey = 'stats';

        if (!forceRefresh && this.isCacheValid(cacheKey)) {
            return this._state.cache[cacheKey].data;
        }

        try {
            const mode = this._state.isAdmin ? this._state.tradingMode : null;
            const response = await DatabaseApiService.getStats(this._state.userId, mode);

            if (response?.success && response?.data) {
                this.updateCache(cacheKey, response.data);
                return response.data;
            }
        } catch (error) {
            console.error('[AppStateManager] fetchStats error:', error);
            throw error;
        }

        return null;
    }

    /**
     * جلب الصفقات النشطة
     */
    async fetchPositions(forceRefresh = false) {
        const cacheKey = 'positions';

        if (!forceRefresh && this.isCacheValid(cacheKey)) {
            return this._state.cache[cacheKey].data;
        }

        try {
            const mode = this._state.isAdmin ? this._state.tradingMode : null;
            const response = await DatabaseApiService.getActivePositions(this._state.userId, mode);

            if (response?.success && response?.data) {
                this.updateCache(cacheKey, response.data);
                return response.data;
            }
        } catch (error) {
            console.error('[AppStateManager] fetchPositions error:', error);
            throw error;
        }

        return null;
    }

    // ═══════════════════════════════════════════════════════════════
    // 4. إدارة Cache
    // ═══════════════════════════════════════════════════════════════

    isCacheValid(key) {
        const cache = this._state.cache[key];
        if (!cache || !cache.data) { return false; }
        return (Date.now() - cache.timestamp) < this.CACHE_TTL;
    }

    updateCache(key, data) {
        this._state.cache[key] = {
            data,
            timestamp: Date.now(),
        };
    }

    invalidateCache(key = null) {
        if (key) {
            this._state.cache[key] = { data: null, timestamp: 0 };
        } else {
            // مسح كل Cache
            Object.keys(this._state.cache).forEach(k => {
                this._state.cache[k] = { data: null, timestamp: 0 };
            });
        }
        this.emit(AppEvents.CACHE_INVALIDATE, { key });
    }

    // ═══════════════════════════════════════════════════════════════
    // 5. تحديث إجباري
    // ═══════════════════════════════════════════════════════════════

    /**
     * تحديث جميع البيانات
     */
    async forceRefreshAll() {
        this.invalidateCache();
        this.emit(AppEvents.FORCE_REFRESH, {});

        try {
            await Promise.all([
                this.fetchPortfolio(true),
                this.fetchSettings(true),
                this.fetchStats(true),
                this.fetchPositions(true),
            ]);
        } catch (error) {
            console.error('[AppStateManager] forceRefreshAll error:', error);
        }
    }

    // ═══════════════════════════════════════════════════════════════
    // 6. معالجة الأخطاء
    // ═══════════════════════════════════════════════════════════════

    /**
     * تحويل الخطأ لرسالة مفهومة للمستخدم
     */
    getUserErrorMessage(error) {
        if (!error) { return UserErrorMessages.UNKNOWN_ERROR; }

        // خطأ شبكة
        if (error?.code === 'ERR_NETWORK' || error?.message?.includes('Network Error')) {
            return UserErrorMessages.NETWORK_ERROR;
        }

        // انتهاء الوقت
        if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
            return UserErrorMessages.TIMEOUT_ERROR;
        }

        // خطأ مصادقة
        if (error?.response?.status === 401) {
            return UserErrorMessages.AUTH_ERROR;
        }

        // خطأ في الخادم
        if (error?.response?.status >= 500) {
            return UserErrorMessages.SERVER_ERROR;
        }

        // خطأ تحقق
        if (error?.response?.status === 400 || error?.response?.status === 422) {
            return error?.response?.data?.error || UserErrorMessages.VALIDATION_ERROR;
        }

        // رسالة من الخادم
        if (error?.response?.data?.error) {
            return error.response.data.error;
        }

        return UserErrorMessages.UNKNOWN_ERROR;
    }

    // ═══════════════════════════════════════════════════════════════
    // 7. نظام الأحداث
    // ═══════════════════════════════════════════════════════════════

    /**
     * الاشتراك في حدث
     */
    on(event, callback) {
        if (!this._listeners[event]) {
            this._listeners[event] = [];
        }
        this._listeners[event].push(callback);

        // إرجاع دالة إلغاء الاشتراك
        return () => this.off(event, callback);
    }

    /**
     * إلغاء الاشتراك
     */
    off(event, callback) {
        if (this._listeners[event]) {
            this._listeners[event] = this._listeners[event].filter(cb => cb !== callback);
        }
    }

    /**
     * إطلاق حدث
     */
    emit(event, data) {
        // إطلاق للمستمعين المحليين
        if (this._listeners[event]) {
            this._listeners[event].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`[AppStateManager] Error in ${event} listener:`, error);
                }
            });
        }

        // إطلاق عبر DeviceEventEmitter للتوافق
        DeviceEventEmitter.emit(event, data);
    }

    // ═══════════════════════════════════════════════════════════════
    // 8. Getters
    // ═══════════════════════════════════════════════════════════════

    get isConnected() { return this._state.isConnected; }
    get systemStatus() { return this._state.systemStatus; }
    get tradingMode() { return this._state.tradingMode; }
    get isAdmin() { return this._state.isAdmin; }
    get userId() { return this._state.userId; }
    get hasPendingOperations() { return this._state.pendingOperations.size > 0; }

    /**
     * مسح البيانات عند تسجيل الخروج
     */
    clearUserData() {
        this._state.userId = null;
        this._state.isAdmin = false;
        this._state.tradingMode = 'demo';
        this.invalidateCache();
    }
}

// Singleton instance
export const appStateManager = new AppStateManager();
export default appStateManager;
