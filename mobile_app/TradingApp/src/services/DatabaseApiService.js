/**
 * 🌐 خدمة قاعدة البيانات الموحدة
 * ✅ موحدة مع UnifiedConnectionService
 * ✅ تحديث ديناميكي للمسارات
 * ✅ معالجة أخطاء شاملة
 */

import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import unifiedConnectionService from './UnifiedConnectionService';
import errorHandler from './UnifiedErrorHandler';
import TempStorageService from './TempStorageService';
import Logger from './LoggerService';
import ResponseValidator from '../utils/responseValidator';

class DatabaseApiService {
    constructor() {
        this.apiClient = null;
        this.isInitialized = false;
        this.initializationPromise = null;
        this.maxRetries = 3;
        this.retryDelay = 1000; // ms
        this._sessionExpiredHandled = false; // ✅ FIX: flag لمنع حذف الـ token المتكرر
    }

    async _retryWithBackoff(fn, retries = this.maxRetries) {
        try {
            return await fn();
        } catch (error) {
            if (retries > 0 && this._isRetryableError(error)) {
                Logger.warn(`Retrying request (${this.maxRetries - retries + 1}/${this.maxRetries})`, 'DatabaseApiService');
                await new Promise(resolve => setTimeout(resolve, this.retryDelay));
                return this._retryWithBackoff(fn, retries - 1);
            }
            throw error;
        }
    }

    _isRetryableError(error) {
        if (!error.response) {
            return true; // Network errors
        }
        const status = error.response.status;
        // ✅ FIX: Do NOT retry 429 - it means "slow down", retrying amplifies the problem
        return status === 408 || status === 500 || status === 502 || status === 503 || status === 504;
    }

    async initialize() {
        if (this.isInitialized) {
            return true;
        }

        if (this.initializationPromise) {
            return this.initializationPromise;
        }

        this.initializationPromise = this._performInitialization();
        return this.initializationPromise;
    }

    async _performInitialization() {
        try {
            // console.log removed for production
            await unifiedConnectionService.initialize();
            // console.log removed for production
            const baseURL = unifiedConnectionService.getBaseURL();
            // console.log removed for production
            this.apiClient = axios.create({
                baseURL: `${baseURL}/api/user`,
                timeout: 15000,  // زيادة timeout إلى 15 ثانية
                headers: {
                    'Content-Type': 'application/json',
                    'Connection': 'keep-alive',  // connection reuse
                },
                maxRedirects: 5,
                maxContentLength: 50 * 1024 * 1024,  // 50MB
            });

            this._setupInterceptors();

            this.isInitialized = true;
            // console.log removed for production
            return true;
        } catch (error) {
            Logger.error('Failed to initialize DatabaseApiService', 'DatabaseApiService', error);
            this.isInitialized = false;
            throw error;
        }
    }

    /**
     * تحويل camelCase إلى snake_case
     * ✅ يُستخدم عند إرسال البيانات للـ Backend
     * مثال: { userId: 1, userName: "test" } → { user_id: 1, user_name: "test" }
     *
     * @param {*} obj - الكائن أو المصفوفة المراد تحويلها
     * @returns {*} الكائن المحول
     */
    _camelToSnake(obj) {
        if (Array.isArray(obj)) {
            return obj.map(item => this._camelToSnake(item));
        }
        if (obj !== null && typeof obj === 'object') {
            const newObj = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    const snakeKey = key.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
                    newObj[snakeKey] = this._camelToSnake(obj[key]);
                }
            }
            return newObj;
        }
        return obj;
    }

    /**
     * تحويل snake_case إلى camelCase
     * ✅ يُستخدم عند استقبال البيانات من الـ Backend
     * مثال: { user_id: 1, user_name: "test" } → { userId: 1, userName: "test" }
     *
     * @param {*} obj - الكائن أو المصفوفة المراد تحويلها
     * @returns {*} الكائن المحول
     */
    _snakeToCamel(obj) {
        if (Array.isArray(obj)) {
            return obj.map(item => this._snakeToCamel(item));
        }
        if (obj !== null && typeof obj === 'object') {
            const newObj = {};
            for (const key in obj) {
                if (obj.hasOwnProperty(key)) {
                    const camelKey = key.replace(/_([a-z])/g, (match, letter) => letter.toUpperCase());
                    newObj[camelKey] = this._snakeToCamel(obj[key]);
                }
            }
            return newObj;
        }
        return obj;
    }

    _setupInterceptors() {
        this.apiClient.interceptors.request.use(
            async (config) => {
                const serverURL = unifiedConnectionService.getBaseURL();
                // ✅ استثناء مسارات المصادقة من /api/user
                const authPaths = ['/auth/login', '/auth/register', '/auth/check-availability', '/auth/send-registration-otp', '/auth/verify-registration-otp', '/auth/forgot-password', '/auth/reset-password', '/auth/verify-email', '/auth/resend-verification', '/auth/delete-account', '/auth/verify-phone-token'];
                const isAuthPath = authPaths.some(path => config.url?.includes(path));
                // ✅ مسارات الأدمن تستخدم /api/admin
                const isAdminPath = config.url?.startsWith('/admin/');

                if (serverURL) {
                    if (isAuthPath) {
                        // مسارات المصادقة تستخدم /api/auth مباشرة
                        config.baseURL = `${serverURL}/api`;
                    } else if (isAdminPath) {
                        // مسارات الأدمن تستخدم /api مباشرة
                        config.baseURL = `${serverURL}/api`;
                    } else if (!config.baseURL?.includes('/api/user')) {
                        config.baseURL = `${serverURL}/api/user`;
                    }
                }

                let token = await AsyncStorage.getItem('authToken');

                if (!token) {
                    try {
                        token = await TempStorageService.getItem('authToken');
                    } catch (e) {
                        // console.log removed for production
                    }
                }

                if (token) {
                    config.headers.Authorization = `Bearer ${token}`;
                    // console.log removed for production
                } else if (!isAuthPath) {
                    Logger.warn('No authorization token found', 'DatabaseApiService');
                }

                if (config.data && typeof config.data === 'object') {
                    config.data = this._camelToSnake(config.data);
                }

                // Request logging disabled in production
                return config;
            },
            (error) => {
                Logger.error('Request error', error, 'DatabaseApiService');
                return Promise.reject(error);
            }
        );

        this.apiClient.interceptors.response.use(
            (response) => {
                // ✅ FIX: Handle cache invalidation from backend
                const cacheInvalidateHeader = response.headers?.['x-cache-invalidate'];
                if (cacheInvalidateHeader && typeof cacheInvalidateHeader === 'string') {
                    const cacheKeys = cacheInvalidateHeader.split(',');
                    Logger.info(`🗑️ Cache invalidation requested: ${cacheKeys.join(', ')}`, 'DatabaseApiService');

                    // Send event to PortfolioContext
                    const { DeviceEventEmitter } = require('react-native');
                    cacheKeys.forEach(key => {
                        DeviceEventEmitter.emit('CACHE_INVALIDATE', key.trim());
                    });
                }

                // console.log removed for production
                if (response.data && typeof response.data === 'object') {
                    response.data = this._snakeToCamel(response.data);
                }

                return response;
            },
            async (error) => {
                errorHandler.handleSmart(error, {
                    context: `API:${error.config?.url || 'unknown'}`,
                });

                // ✅ FIX: منع حذف الـ token المتكرر باستخدام flag
                if (error.response?.status === 401 && !this._sessionExpiredHandled) {
                    this._sessionExpiredHandled = true;
                    await AsyncStorage.removeItem('authToken');
                    await AsyncStorage.removeItem('userData');
                    await AsyncStorage.removeItem('isLoggedIn');
                    // ✅ إرسال event لإعادة توجيه المستخدم لشاشة تسجيل الدخول
                    const { DeviceEventEmitter } = require('react-native');
                    DeviceEventEmitter.emit('SESSION_EXPIRED');
                    Logger.warn('Session expired - token removed', 'DatabaseApiService');
                    // إعادة تعيين الـ flag بعد 5 ثواني للسماح بمعالجة جديدة
                    setTimeout(() => { this._sessionExpiredHandled = false; }, 5000);
                }

                // ✅ معالجة خطأ 429 (Too Many Requests) - بشكل صامت
                if (error.response?.status === 429) {
                    Logger.warn('Rate limit exceeded - will retry later', 'DatabaseApiService');
                    // لا نعرض رسالة للمستخدم - النظام سيعيد المحاولة تلقائياً
                }

                // ✅ معالجة خطأ 409 (Conflict) - بشكل صامت
                if (error.response?.status === 409) {
                    Logger.info('Resource conflict - operation already in progress', 'DatabaseApiService');
                    // لا نعرض رسالة للمستخدم - العملية تعمل بالفعل
                }

                // ✅ معالجة خطأ 500 (Server Error) - بشكل صامت
                if (error.response?.status === 500) {
                    Logger.error('Server error occurred', error, 'DatabaseApiService');
                    // لا نعرض رسالة للمستخدم - خطأ داخلي في الخادم
                }

                // ✅ FIX #3: Network error recovery with proper error propagation
                if (error.code === 'ECONNABORTED' || error.message === 'Network Error') {
                    try {
                        await unifiedConnectionService.retry();
                        errorHandler.handleSystemError('AUTO_RECONNECT', 'تم إعادة الاتصال');
                    } catch (retryError) {
                        Logger.error('Network retry failed', retryError, 'DatabaseApiService');
                        errorHandler.handleUserError('NO_INTERNET');
                        // Ensure error is logged and propagated
                        return Promise.reject(retryError);
                    }
                }

                return Promise.reject(error);
            }
        );
    }

    async initializeConnection() {
        try {
            const result = await this.initialize();
            if (result) {
                const serverURL = unifiedConnectionService.getBaseURL();
                await axios.get(`${serverURL}/api/system/status`);
                // console.log removed for production
                return true;
            }
            return false;
        } catch (error) {
            Logger.error('Connection test failed', 'DatabaseApiService', error);
            return false;
        }
    }

    /**
     * فحص الاتصال بالخادم
     * @returns {Promise<boolean>} true إذا كان الاتصال ناجحاً
     */
    async checkConnection() {
        try {
            await this.initialize();
            const serverURL = unifiedConnectionService.getBaseURL();
            const response = await axios.get(`${serverURL}/api/system/status`, {
                timeout: 5000,
            });
            return response.status === 200;
        } catch (error) {
            Logger.warn('Connection check failed', 'DatabaseApiService');
            return false;
        }
    }

    async login(identifier, password) {
        try {
            await this.initialize();
            const isEmail = identifier.includes('@');
            const payload = isEmail
                ? { email: identifier, password }
                : { username: identifier, password };

            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/login', payload)
            );

            if (response.data?.token) {
                try {
                    await AsyncStorage.setItem('authToken', response.data.token);
                    await TempStorageService.setItem('authToken', response.data.token);
                    // console.log removed for production
                } catch (storageError) {
                    Logger.warn('Failed to save token', 'DatabaseApiService');
                }
            }
            return response.data;
        } catch (error) {
            Logger.error('Login failed', error, 'DatabaseApiService.login');
            // ✅ تمرير الخطأ كما هو للسماح للشاشة بمعالجته بدقة
            // لا نعدل رسالة الخطأ هنا - نتركها للشاشة
            throw error;
        }
    }

    async checkAvailability(email, username, phone) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/check-availability', { email, username, phone })
            );
            return response.data;
        } catch (error) {
            Logger.error('Check availability failed', 'DatabaseApiService', error);
            throw error;
        }
    }

    async sendRegistrationOTP(email, method = 'sms', phone = null) {
        try {
            await this.initialize();
            const payload = { email, method };
            if (phone) { payload.phone = phone; }
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/send-registration-otp', payload)
            );
            return response.data;
        } catch (error) {
            Logger.error('Send registration OTP failed', 'DatabaseApiService', error);
            // ✅ معالجة خطأ cooldown
            if (error?.response?.status === 429) {
                return {
                    success: false,
                    message: error?.response?.data?.error || 'يرجى الانتظار قبل طلب رمز جديد',
                    code: 'COOLDOWN',
                };
            }
            // ✅ معالجة خطأ البريد مسجل مسبقاً
            if (error?.response?.status === 409) {
                return {
                    success: false,
                    message: 'البريد الإلكتروني مسجل مسبقاً',
                    code: 'EMAIL_EXISTS',
                };
            }
            return {
                success: false,
                message: error?.response?.data?.error || 'فشل في إرسال رمز التحقق',
            };
        }
    }

    async verifyRegistrationOTP(data) {
        try {
            await this.initialize();
            const requestData = {
                email: data.email,
                otp_code: data.otp_code,
                username: data.username?.toLowerCase(), // ✅ توحيد lowercase
                password: data.password,
                phone: data.phone,
                fullName: data.fullName,
            };
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/verify-registration-otp', requestData)
            );
            return response.data;
        } catch (error) {
            Logger.error('Verify registration OTP failed', 'DatabaseApiService', error);
            // ✅ معالجة أخطاء محددة
            const errorData = error?.response?.data || {};
            return {
                success: false,
                message: errorData.error || 'فشل التحقق من الرمز',
                remaining_attempts: errorData.remaining_attempts,
                code: errorData.code,
            };
        }
    }

    /**
     * التسجيل عبر رقم الهاتف (بعد التحقق من Firebase)
     * @param {object} data - بيانات التسجيل
     */
    async registerWithPhone(data) {
        try {
            await this.initialize();
            const requestData = {
                phone: data.phone,
                username: data.username,
                password: data.password,
                fullName: data.fullName,
                email: data.email || null,
                firebaseToken: data.firebaseToken,
                verificationMethod: 'sms',
            };
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/register-with-phone', requestData)
            );
            return response.data;
        } catch (error) {
            Logger.error('Register with phone failed', 'DatabaseApiService', error);
            return {
                success: false,
                message: error?.response?.data?.error || 'فشل التسجيل عبر الهاتف',
            };
        }
    }

    async register(data, username, password) {
        try {
            await this.initialize();
            let requestData;
            if (typeof data === 'object' && data !== null) {
                requestData = {
                    email: data.email,
                    username: data.username || data.email?.split('@')[0],
                    password: data.password,
                    full_name: data.full_name || data.fullName,
                    phone: data.phone,
                    verificationMethod: data.verificationMethod || 'email',
                };
            } else {
                requestData = {
                    email: data,
                    username,
                    password,
                    verificationMethod: 'email',
                };
            }

            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/register', requestData)
            );
            return response.data;
        } catch (error) {
            Logger.error('Registration failed', 'DatabaseApiService', error);
            errorHandler.handleUserError('INVALID_INPUT', 'فشل التسجيل: ' + error?.message);
            throw error;
        }
    }

    async getActivePositions(userId, mode = null) {
        try {
            await this.initialize();
            const url = mode
                ? `/active-positions/${userId}?mode=${mode}`
                : `/active-positions/${userId}`;
            // console.log removed for production
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(url)
            );

            if (response.data && response.data.success) {
                return response.data;
            }
            return {
                success: false,
                error: 'فشل في جلب الصفقات النشطة',
                data: {
                    positions: [],
                    summary: {
                        total_positions: 0,
                        total_value: 0,
                        total_pnl: 0,
                        profitable_count: 0,
                        losing_count: 0,
                    },
                },
            };
        } catch (error) {
            Logger.warn('Get active positions failed', 'DatabaseApiService');
            errorHandler.handleSystemError('MINOR_API_ERROR', 'فشل جلب الصفقات النشطة');
            return {
                success: false,
                error: 'حدث خطأ أثناء جلب الصفقات النشطة',
                data: {
                    positions: [],
                    summary: {
                        total_positions: 0,
                        total_value: 0,
                        total_pnl: 0,
                        profitable_count: 0,
                        losing_count: 0,
                    },
                },
            };
        }
    }

    async getProfile(userId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(`/profile/${userId}`)
            );
            return response.data;
        } catch (error) {
            Logger.error('Get profile failed', 'DatabaseApiService', error);
            errorHandler.handleSystemError('MINOR_API_ERROR', 'فشل جلب الملف الشخصي');
            return { success: false, error: error?.message };
        }
    }

    async updateProfile(userId, profileData) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.put(`/profile/${userId}`, profileData)
            );
            return response.data;
        } catch (error) {
            Logger.error('Update profile failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    async getSettings(userId, mode = null) {
        try {
            await this.initialize();
            const url = mode ? `/settings/${userId}?mode=${mode}` : `/settings/${userId}`;
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(url)
            );
            return response.data;
        } catch (error) {
            Logger.error('Get settings failed', 'DatabaseApiService', error);
            errorHandler.handleSystemError('MINOR_API_ERROR', 'فشل جلب الإعدادات');
            return { success: false, error: error?.message };
        }
    }

    async updateSettings(userId, settings) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.put(`/settings/${userId}`, settings)
            );
            return response.data;
        } catch (error) {
            Logger.error('Update settings failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    // ✅ دالة جلب المحفظة مع validation شامل
    async getPortfolio(userId, mode = 'demo') {
        try {
            // ✅ التحقق من صحة المعاملات
            if (!userId) {
                Logger.error('getPortfolio: userId is required', 'DatabaseApiService');
                return {
                    success: false,
                    error: 'userId مطلوب',
                    data: null,
                };
            }

            // ✅ التحقق من صحة mode - استخدام demo كافتراضي بدون تحذير
            const validModes = ['demo', 'real', 'auto'];
            if (!mode || !validModes.includes(mode)) {
                mode = 'demo';
            }

            await this.initialize();
            const url = `/portfolio/${userId}?mode=${mode}`;
            // console.log removed for production
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(url)
            );

            // ✅ التحقق من صحة الاستجابة مع validation
            if (response?.data?.success && response?.data?.data) {
                const validation = ResponseValidator.validatePortfolioResponse(response.data.data);
                if (!validation.valid) {
                    Logger.warn('Portfolio response validation failed:', validation.error);
                }
                return {
                    ...response.data,
                    data: validation.data
                };
            }

            Logger.warn('getPortfolio: Invalid response structure', 'DatabaseApiService');
            return {
                success: false,
                error: 'بيانات المحفظة غير صحيحة',
                data: {
                    balance: 0,
                    initial_balance: 0,
                    total_profit: 0,
                    win_rate: 0,
                    total_trades: 0,
                    mode: mode,
                },
            };
        } catch (error) {
            Logger.error('Get portfolio failed', 'DatabaseApiService', error);
            errorHandler.handleSystemError('MINOR_API_ERROR', 'فشل جلب المحفظة');

            // ✅ إرجاع بيانات افتراضية آمنة
            return {
                success: false,
                error: error?.message || 'حدث خطأ أثناء جلب المحفظة',
                data: {
                    balance: 0,
                    initial_balance: 0,
                    total_profit: 0,
                    win_rate: 0,
                    total_trades: 0,
                    mode: mode,
                },
            };
        }
    }

    // ❌ DELETED: getUserSettings() - استخدم getSettings() بدلاً منها
    // ❌ DELETED: updateUserSettings() - استخدم updateSettings() بدلاً منها
    // السبب: تكرار 100% - نفس API endpoint، نفس الوظيفة، نفس المعاملات

    async getQualifiedCoins(userId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(`/successful-coins/${userId}`)
            );
            return response.data;
        } catch (error) {
            Logger.error('Get qualified coins failed', 'DatabaseApiService', error);
            errorHandler.handleSystemError('MINOR_API_ERROR', 'فشل جلب العملات المؤهلة');
            return { success: false, data: { coins: [] } };
        }
    }

    // ❌ DELETED: getTradingSettings() - DUPLICATE of getSettings(userId)
    // ❌ DELETED: updateTradingSettings() - DUPLICATE of updateSettings(userId, settings)
    // Reason: Non-uniform duplicate - same functionality in /settings/<user_id>

    // ❌ REMOVED: changePassword() — deprecated, use sendChangePasswordOTP() + verifyChangePassword()
    // ❌ REMOVED: getTradeStats() — duplicate of getStats() (same endpoint /stats/{userId})

    async getStats(userId, mode = null) {
        try {
            await this.initialize();
            const url = mode ? `/stats/${userId}?mode=${mode}` : `/stats/${userId}`;
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(url)
            );
            return response.data;
        } catch (error) {
            Logger.error('Get stats failed', 'DatabaseApiService', error);
            // ✅ إرجاع كود الخطأ الحقيقي للسماح بمعالجة دقيقة
            const errorCode = error?.response?.status;
            return {
                success: false,
                errorCode: errorCode,
                errorMessage: errorCode === 401 ? 'SESSION_EXPIRED' : 'FETCH_ERROR',
                data: {
                    totalTrades: 0,
                    winningTrades: 0,
                    losingTrades: 0,
                    closedTrades: 0,
                    activeTrades: 0,
                    winRate: '0%',  // ✅ توحيد الاسم مع Dashboard (successRate → winRate)
                    totalProfit: 0,
                    averageProfit: 0,
                    bestTrade: 0,
                },
            };
        }
    }

    async getPortfolioHistory(userId, days = 30, isAdmin = false, tradingMode = 'auto') {
        try {
            await this.initialize();
            // ✅ FIX: إضافة دعم isAdmin و tradingMode - API يستخدم 'mode' وليس 'trading_mode'
            let url = `/portfolio-growth/${userId}?days=${days}`;
            if (isAdmin && tradingMode) {
                url += `&mode=${tradingMode}`;
            }

            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(url)
            );
            return response.data;
        } catch (error) {
            Logger.error('Get portfolio history failed', 'DatabaseApiService', error);
            return { success: false, data: { dates: [], balances: [] } };
        }
    }

    async getTrades(userId, limitOrMode = 50) {
        try {
            await this.initialize();
            let limit = 50;
            let mode = null;

            if (typeof limitOrMode === 'string') {
                mode = limitOrMode;
            } else if (typeof limitOrMode === 'number') {
                limit = limitOrMode;
            }

            let url = `/trades/${userId}?limit=${limit}`;
            if (mode) {
                url += `&mode=${mode}`;
            }

            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(url)
            );
            return response.data;
        } catch (error) {
            Logger.error('Get trades failed', 'DatabaseApiService', error);
            return { success: false, data: { trades: [] } };
        }
    }

    async validateSession() {
        try {
            await this.initialize();
            const serverURL = unifiedConnectionService.getBaseURL();
            const token = await AsyncStorage.getItem('authToken');

            // التحقق من وجود Token أولاً
            if (!token) {
                Logger.error('No saved token', 'DatabaseApiService');
                return false;
            }

            const response = await axios.get(`${serverURL}/api/auth/validate-session`, {
                headers: { Authorization: `Bearer ${token}` },
                timeout: 5000,
            });

            // التحقق من نجاح الاستجابة
            if (response.data && response.data.success === true) {
                return true;
            } else {
                Logger.warn('Invalid session', 'DatabaseApiService');
                // حذف Token غير الصالح
                await AsyncStorage.removeItem('authToken');
                await TempStorageService.removeItem('isLoggedIn');
                await TempStorageService.removeItem('userData');
                return false;
            }
        } catch (error) {
            Logger.error('Validate session failed', 'DatabaseApiService', error);
            try {
                await AsyncStorage.removeItem('authToken');
                await TempStorageService.removeItem('isLoggedIn');
                await TempStorageService.removeItem('userData');
            } catch (cleanupError) {
                Logger.error('Cleanup failed', 'DatabaseApiService', cleanupError);
            }
            return false;
        }
    }

    async sendLoginOTP(identifier, password, method = 'sms') {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/login/send-otp', {
                    identifier: identifier,
                    password: password,
                    method: method,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('Send login OTP failed', 'DatabaseApiService', error);

            let errorMessage = 'فشل إرسال رمز التحقق';
            let retryAllowed = true;

            if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
                errorMessage = 'انتهى وقت الانتظار. يرجى المحاولة مرة أخرى';
            } else if (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
                errorMessage = 'فشل الاتصال. تحقق من اتصالك بالإنترنت';
            } else if (error?.response?.data?.error) {
                errorMessage = error.response.data.error;
                retryAllowed = error.response.data.retry_allowed !== false;
            }

            return {
                success: false,
                error: errorMessage,
                retry_allowed: retryAllowed,
            };
        }
    }

    async verifyLoginOTP(userId, otpCode) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/login/verify-otp', {
                    user_id: userId,
                    otp_code: otpCode,
                }, {
                    timeout: 10000,
                })
            );

            if (response.data.success && response.data.token) {
                await AsyncStorage.setItem('authToken', response.data.token);
            }

            return response.data;
        } catch (error) {
            Logger.error('Verify login OTP failed', 'DatabaseApiService', error);

            let errorMessage = 'فشل التحقق من الرمز';

            if (error.code === 'ECONNABORTED' || error.message?.includes('timeout')) {
                errorMessage = 'انتهى وقت الانتظار. يرجى المحاولة مرة أخرى';
            } else if (error.code === 'ERR_NETWORK' || error.message?.includes('Network Error')) {
                errorMessage = 'فشل الاتصال. تحقق من اتصالك بالإنترنت';
            } else if (error?.response?.data?.error) {
                errorMessage = error.response.data.error;
            }

            return {
                success: false,
                error: errorMessage,
            };
        }
    }

    async resendLoginOTP(userId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/login/resend-otp', {
                    user_id: userId,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('Resend login OTP failed', 'DatabaseApiService', error);
            return {
                success: false,
                error: error?.response?.data?.error || error?.message || 'فشل إعادة إرسال الرمز',
            };
        }
    }

    async getBinanceKeys(userId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(`/binance-keys/${userId}`)
            );
            return response.data;
        } catch (error) {
            Logger.error('Get Binance keys failed', 'DatabaseApiService', error);
            return { success: false, data: { keys: [] } };
        }
    }

    async saveBinanceKeys(apiKey, apiSecret) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/binance-keys', {
                    api_key: apiKey,
                    api_secret: apiSecret,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('Save Binance keys failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    async deleteBinanceKey(keyId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.delete(`/binance-keys/${keyId}`)
            );
            return response.data;
        } catch (error) {
            Logger.error('Delete Binance key failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    async validateBinanceKeys(apiKey, apiSecret) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/binance-keys/validate', {
                    api_key: apiKey,
                    api_secret: apiSecret,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('Validate Binance keys failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    async getNotifications(userId, page = 1, limit = 20) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(`/user/notifications/${userId}?page=${page}&limit=${limit}`)
            );
            return response.data;
        } catch (error) {
            Logger.error('Get notifications failed', 'DatabaseApiService', error);
            return { success: false, data: { notifications: [] } };
        }
    }

    async markNotificationRead(notificationId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.put(`/user/notifications/${notificationId}/read`)
            );
            return response.data;
        } catch (error) {
            Logger.error('Mark notification read failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    async markAllNotificationsRead(userId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post(`/user/notifications/${userId}/mark-all-read`)
            );
            return response.data;
        } catch (error) {
            Logger.error('Mark all notifications read failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    // ❌ REMOVED: getNotificationSettings/updateNotificationSettings (old path /notification-settings/{userId})
    // ✅ الإصدار الصحيح في الأسفل يستخدم /notifications/settings

    async getOnboardingStatus(userId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(`/onboarding/status/${userId}`)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get onboarding status failed:', error?.message);
            return { success: false, data: { completed: false, steps: [] } };
        }
    }

    async getNextOnboardingStep(userId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(`/onboarding/next-step/${userId}`)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get next onboarding step failed:', error?.message);
            return { success: false, data: { step: null } };
        }
    }

    async dismissOnboardingStep(userId, stepId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post(`/onboarding/dismiss/${userId}`, {
                    step_id: stepId,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Dismiss onboarding step failed:', error?.message);
            return { success: false, error: error?.message };
        }
    }

    async registerDevice(deviceInfo) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/device', deviceInfo)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Register device failed:', error?.message);
            return { success: false, error: error?.message };
        }
    }

    async getTradingMode(userId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(`/settings/trading-mode/${userId}`)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get trading mode failed:', error?.message);
            return { success: false, data: { mode: 'auto' } };
        }
    }

    async updateTradingMode(userId, mode) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.put(`/settings/trading-mode/${userId}`, {
                    mode: mode,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Update trading mode failed:', error?.message);
            return { success: false, error: error?.message };
        }
    }

    async resetAccountData(userId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post(`/reset-data/${userId}`)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Reset account data failed:', error?.message);
            return { success: false, error: error?.message };
        }
    }

    async getAdminDemoPortfolioGrowth(adminId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(`/admin/demo-portfolio-growth/${adminId}`)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get admin demo portfolio growth failed:', error?.message);
            return { success: false, data: { dates: [], balances: [] } };
        }
    }

    async verifyBiometric(biometricData) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/biometric/verify', biometricData)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Verify biometric failed:', error?.message);
            return { success: false, error: error?.message };
        }
    }

    async registerFCMToken(token) {
        try {
            await this.initialize();
            const serverURL = unifiedConnectionService.getBaseURL();
            const authToken = await AsyncStorage.getItem('authToken');
            const response = await this._retryWithBackoff(() =>
                axios.post(`${serverURL}/api/notifications/fcm-token`, {
                    fcm_token: token,
                    platform: 'android',
                    user_id: null,
                }, {
                    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
                    timeout: 10000,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Register FCM token failed:', error?.message);
            return { success: false, error: error?.message };
        }
    }

    async unregisterFCMToken(userId, token) {
        try {
            await this.initialize();
            const serverURL = unifiedConnectionService.getBaseURL();
            const authToken = await AsyncStorage.getItem('authToken');
            const response = await this._retryWithBackoff(() =>
                axios.delete(`${serverURL}/api/notifications/fcm-token`, {
                    data: { user_id: userId, fcm_token: token },
                    headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
                    timeout: 10000,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Unregister FCM token failed:', error?.message);
            return { success: false, error: error?.message };
        }
    }

    // ==================== ML Learning System (Hybrid) ====================

    /**
     * الحصول على تقدم التعلم - للمؤشر في لوحة الأدمن
     */
    async getMLLearningProgressSimple() {
        try {
            await this.initialize();
            // ✅ FIX: استخدام المسار الصحيح مع token
            const serverURL = unifiedConnectionService.getBaseURL();
            const token = await AsyncStorage.getItem('authToken');
            const response = await this._retryWithBackoff(() =>
                axios.get(`${serverURL}/api/admin/ml/status`, {
                    timeout: 10000,
                    headers: token ? { Authorization: `Bearer ${token}` } : {},
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get ML learning progress failed:', error?.message);
            return {
                success: false,
                progress: {
                    percentage: 0,
                    phase: 'initial',
                    is_ready: false,
                    real_trades: 0,
                },
            };
        }
    }

    /**
     * الحصول على حالة ML الكاملة
     */
    async getMLFullStatus() {
        try {
            await this.initialize();
            const serverURL = unifiedConnectionService.getBaseURL();
            const token = await AsyncStorage.getItem('authToken');
            const response = await this._retryWithBackoff(() =>
                axios.get(`${serverURL}/api/ml/status`, {
                    timeout: 10000,
                    headers: token ? { Authorization: `Bearer ${token}` } : {},
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get ML full status failed:', error?.message);
            return { success: false };
        }
    }

    /**
     * الحصول على جميع الأنماط
     */
    async getMLPatterns() {
        try {
            await this.initialize();
            const serverURL = unifiedConnectionService.getBaseURL();
            const token = await AsyncStorage.getItem('authToken');
            const response = await this._retryWithBackoff(() =>
                axios.get(`${serverURL}/api/ml/patterns`, {
                    timeout: 10000,
                    headers: token ? { Authorization: `Bearer ${token}` } : {},
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get ML patterns failed:', error?.message);
            return { success: false, patterns: [] };
        }
    }

    /**
     * حالة نظام التعلم التكيّفي (مؤشر الأدمن)
     */
    async getLearningStatus() {
        try {
            await this.initialize();
            const serverURL = unifiedConnectionService.getBaseURL();
            const token = await AsyncStorage.getItem('authToken');

            const response = await axios.get(`${serverURL}/api/ml/learning-status`, {
                timeout: 10000,
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });

            return response.data;
        } catch (error) {
            Logger.error('❌ Get learning status failed:', error?.message);
            return {
                success: false,
                learning: { total_trades: 0, trades_with_indicators: 0, overall_win_rate: 0, avg_pnl_pct: 0, blocked_symbols: 0 },
                last_validation: null,
                trend: 'unknown',
            };
        }
    }

    /**
     * العملات المُراقبة مرتبة بالأداء
     */
    async getMonitoredCoins() {
        try {
            await this.initialize();
            const serverURL = unifiedConnectionService.getBaseURL();
            const token = await AsyncStorage.getItem('authToken');

            const response = await axios.get(`${serverURL}/api/ml/monitored-coins`, {
                timeout: 10000,
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });

            return response.data;
        } catch (error) {
            Logger.error('❌ Get monitored coins failed:', error?.message);
            return { success: false, coins: [] };
        }
    }

    /**
     * ✅ FIX: الحصول على حالة النظام الشاملة مع دعم Demo/Real mode
     */
    async getSystemMLStatus(tradingMode = 'demo') {
        try {
            await this.initialize();
            const serverURL = unifiedConnectionService.getBaseURL();
            const token = await AsyncStorage.getItem('authToken');

            // ✅ FIX: إرسال mode parameter للحصول على البيانات الصحيحة
            const response = await axios.get(`${serverURL}/api/admin/system/ml-status`, {
                params: { mode: tradingMode },
                timeout: 10000,
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });

            if (response.data?.success) {
                return response.data;
            }

            // Fallback للبيانات الافتراضية
            return {
                success: false,
                ml: {
                    enabled: false,
                    is_ready: false,
                    total_samples: 0,
                    required_samples: 200,
                    progress_pct: 0,
                    accuracy: 0,
                    precision: 0,
                    recall: 0,
                    f1_score: 0,
                },
                portfolio: { balance: 0, total_trades: 0, winning_trades: 0, win_rate: 0 },
                trading: { enabled: false, mode: 'demo', active_coins: 0, active_positions: 0 },
                patterns: { total_patterns: 0, live_trades: 0 },
            };
        } catch (error) {
            Logger.error('❌ Get ML status failed:', error?.message);
            return {
                success: false,
                ml: {
                    enabled: false,
                    is_ready: false,
                    total_samples: 0,
                    required_samples: 200,
                    progress_pct: 0,
                    accuracy: 0,
                    precision: 0,
                    recall: 0,
                    f1_score: 0,
                },
                portfolio: { balance: 0, total_trades: 0, winning_trades: 0, win_rate: 0 },
                trading: { enabled: false, mode: 'demo', active_coins: 0, active_positions: 0 },
                patterns: { total_patterns: 0, live_trades: 0 },
            };
        }
    }

    async getMLProgress() {
        try {
            await this.initialize();
            const response = await this.apiClient.get('/admin/ml/progress');
            return response.data;
        } catch (error) {
            Logger.error('❌ Get ML progress failed:', error.message);
            return {
                success: false,
                data: {
                    training_progress: {
                        total_samples: 0,
                        min_required: 50,
                        readiness_required: 200,
                        progress_percent: 0,
                        status: 'training',
                    },
                    model_metrics: {
                        accuracy: 0,
                        precision: 0,
                        recall: 0,
                        f1_score: 0,
                        is_ready: false,
                    },
                },
            };
        }
    }

    async getMLQualityMetrics() {
        try {
            await this.initialize();
            const response = await this.apiClient.get('/admin/ml/quality-metrics');
            return response.data;
        } catch (error) {
            Logger.error('❌ Get ML quality metrics failed:', error.message);
            return {
                success: false,
                data: {
                    data_quality: {
                        total_trades_validated: 0,
                        valid_trades: 0,
                        invalid_trades: 0,
                        validity_rate: '0.0%',
                    },
                    model_quality: {
                        total_models_validated: 0,
                        valid_models: 0,
                        validity_rate: '0.0%',
                    },
                    signal_quality: {
                        total_signals_validated: 0,
                        valid_signals: 0,
                        validity_rate: '0.0%',
                    },
                },
            };
        }
    }

    // ✅ CLEANED: Removed deprecated startGroupB/stopGroupB/getGroupBStatus methods
    // Use startTradingSystem/stopTradingSystem/getTradingState (State Machine) instead

    async resetDemoAccount() {
        try {
            await this.initialize();
            // ✅ FIX: استخدام المسار الكامل لأن الـ endpoint في /api/admin وليس /api/user
            const serverURL = unifiedConnectionService.getBaseURL();
            const token = await AsyncStorage.getItem('authToken');
            const response = await axios.post(`${serverURL}/api/admin/demo/reset`, {}, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
            });
            return response.data;
        } catch (error) {
            Logger.warn('Reset demo account failed', 'DatabaseApiService');
            return { success: false, error: error.message };
        }
    }

    // ✅ حذف الحساب - للتوافق مع ProfileScreen
    async deleteAccount(password, confirmText) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.delete('/auth/delete-account', {
                    data: { password, confirmation: confirmText },
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Delete account failed:', error?.message);
            return { success: false, error: error?.response?.data?.error || error?.message || 'فشل حذف الحساب' };
        }
    }

    // ✅ جلب أخطاء الخلفية - للتوافق مع AdminErrorsScreen
    async getBackgroundErrors(limit = 50) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(`/admin/errors?limit=${limit}`)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get background errors failed:', error?.message);
            return { success: false, data: { errors: [] } };
        }
    }

    // ✅ جلب إحصائيات أخطاء الخلفية - للتوافق مع AdminErrorsScreen
    async getBackgroundErrorStats() {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get('/admin/errors/stats')
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get background error stats failed:', error?.message);
            return { success: false, data: { total: 0, today: 0, critical: 0 } };
        }
    }

    // ==================== دوال التحكم في النظام الخلفي ====================

    /**
     * ✅ جلب حالة النظام الخلفي الفعلية - استخدام Unified API
     */
    async getBackgroundSystemStatus() {
        try {
            // ✅ فحص الصلاحيات قبل استدعاء API
            const userType = await AsyncStorage.getItem('userType');
            if (!userType || userType !== 'admin') {
                Logger.warn('❌ غير مسموح - فقط الأدمن يمكنه الوصول لحالة النظام');
                return { success: false, is_running: false, error: 'Unauthorized - Admin only' };
            }

            await this.initialize();
            const serverURL = unifiedConnectionService.getBaseURL();
            const token = await AsyncStorage.getItem('authToken');

            if (!token) {
                return { success: false, is_running: false, error: 'No authentication token' };
            }

            // ✅ استخدام endpoint موحد
            const response = await axios.get(`${serverURL}/api/admin/system/status`, {
                headers: { Authorization: `Bearer ${token}` },
                timeout: 5000,
            });
            return response.data;
        } catch (error) {
            Logger.error('❌ Get background system status failed:', error?.message);
            return { success: false, is_running: false, error: error?.message };
        }
    }

    /**
     * @deprecated استخدم startTradingSystem() بدلاً منه — Backend يرجع 410 Gone
     */
    async startBackgroundSystem() {
        console.warn('⚠️ [DEPRECATED] startBackgroundSystem() → use startTradingSystem()');
        return this.startTradingSystem();
    }

    /**
     * @deprecated استخدم stopTradingSystem() بدلاً منه — Backend يرجع 410 Gone
     */
    async stopBackgroundSystem() {
        console.warn('⚠️ [DEPRECATED] stopBackgroundSystem() → use stopTradingSystem()');
        return this.stopTradingSystem();
    }

    /**
     * @deprecated استخدم emergencyStopTradingSystem() بدلاً منه — Backend يرجع 410 Gone
     */
    async emergencyStopBackgroundSystem() {
        console.warn('⚠️ [DEPRECATED] emergencyStopBackgroundSystem() → use emergencyStopTradingSystem()');
        return this.emergencyStopTradingSystem();
    }

    // ==================== Trading State Machine API (المصدر الوحيد للحقيقة) ====================

    /**
     * 📊 جلب حالة نظام التداول - State Machine API
     * 
     * Returns: { trading_state, session_id, mode, open_positions, pid, uptime, subsystems }
     * trading_state: STOPPED | STARTING | RUNNING | STOPPING | ERROR
     */
    async getTradingState() {
        try {
            await this.initialize();
            const serverURL = unifiedConnectionService.getBaseURL();
            const token = await AsyncStorage.getItem('authToken');
            const response = await axios.get(`${serverURL}/api/admin/trading/state`, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
                timeout: 5000,
            });
            return response.data;
        } catch (error) {
            Logger.error('❌ getTradingState failed:', error?.message);
            return { success: false, trading_state: 'ERROR', message: error?.message || 'فشل جلب الحالة' };
        }
    }

    /**
     * 🚀 تشغيل نظام التداول - State Machine API
     * 
     * NEVER returns 409. Always returns current state.
     * If already running → returns RUNNING state silently.
     */
    async startTradingSystem(mode = 'PAPER') {
        try {
            await this.initialize();
            const serverURL = unifiedConnectionService.getBaseURL();
            const token = await AsyncStorage.getItem('authToken');
            console.log('🚀 [StateMachine] Starting trading system...');
            const response = await axios.post(`${serverURL}/api/admin/trading/start`, { mode }, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
                timeout: 15000,
            });
            console.log('✅ [StateMachine] Response:', response.data?.trading_state);
            return response.data;
        } catch (error) {
            Logger.error('❌ startTradingSystem failed:', error?.message);
            return { success: false, trading_state: 'ERROR', message: error?.message || 'فشل تشغيل النظام' };
        }
    }

    /**
     * ⏹️ إيقاف نظام التداول - State Machine API
     * 
     * NEVER returns error for normal states.
     * If already stopped → returns STOPPED state silently.
     */
    async stopTradingSystem() {
        try {
            await this.initialize();
            const serverURL = unifiedConnectionService.getBaseURL();
            const token = await AsyncStorage.getItem('authToken');
            console.log('⏹️ [StateMachine] Stopping trading system...');
            const response = await axios.post(`${serverURL}/api/admin/trading/stop`, {}, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
                timeout: 15000,
            });
            console.log('✅ [StateMachine] Response:', response.data?.trading_state);
            return response.data;
        } catch (error) {
            Logger.error('❌ stopTradingSystem failed:', error?.message);
            return { success: false, trading_state: 'ERROR', message: error?.message || 'فشل إيقاف النظام' };
        }
    }

    /**
     * 🚨 إيقاف طوارئ - State Machine API
     */
    async emergencyStopTradingSystem() {
        try {
            await this.initialize();
            const serverURL = unifiedConnectionService.getBaseURL();
            const token = await AsyncStorage.getItem('authToken');
            console.log('🚨 [StateMachine] Emergency stop...');
            const response = await axios.post(`${serverURL}/api/admin/trading/emergency-stop`, {}, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
                timeout: 10000,
            });
            return response.data;
        } catch (error) {
            Logger.error('❌ emergencyStopTradingSystem failed:', error?.message);
            return { success: false, trading_state: 'ERROR', message: error?.message || 'فشل إيقاف الطوارئ' };
        }
    }

    /**
     * 🔄 إعادة تعيين من حالة خطأ - State Machine API
     */
    async resetTradingError() {
        try {
            await this.initialize();
            const serverURL = unifiedConnectionService.getBaseURL();
            const token = await AsyncStorage.getItem('authToken');
            const response = await axios.post(`${serverURL}/api/admin/trading/reset-error`, {}, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
                timeout: 5000,
            });
            return response.data;
        } catch (error) {
            Logger.error('❌ resetTradingError failed:', error?.message);
            return { success: false, trading_state: 'ERROR', message: error?.message };
        }
    }

    // ==================== Legacy Unified System API (deprecated → State Machine) ====================

    // ✅ REMOVED: Deprecated startSystem() and stopSystem() methods
    // Use startTradingSystem() and stopTradingSystem() directly

    // ✅ REMOVED: Deprecated getSystemStatus() method
    // Use getTradingState() directly

    // ❌ REMOVED: startBackgroundSystemFast/stopBackgroundSystemFast/getBackgroundSystemStatusFast
    // — deprecated wrappers, use startSystem()/stopSystem()/getSystemStatus() directly

    // ✅ دالة request عامة - للتوافق مع AdminNotificationSettingsScreen
    async request(endpoint, method = 'GET', data = null) {
        try {
            await this.initialize();
            const config = { method: method.toLowerCase() };
            if (data && ['post', 'put', 'patch'].includes(config.method)) {
                config.data = data;
            }
            const response = await this._retryWithBackoff(() =>
                this.apiClient.request({ url: endpoint, ...config })
            );
            return response.data;
        } catch (error) {
            Logger.error(`❌ Request ${method} ${endpoint} failed:`, error?.message);
            return { success: false, error: error?.message };
        }
    }

    // ==================== دوال OTP للتحقق ====================

    /**
     * التحقق من الإيميل بعد التسجيل
     * @param {string} email - الإيميل
     * @param {string} otp - رمز التحقق
     * @param {string} operationType - نوع العملية
     */
    async verifyEmail(email, otp, operationType = 'register') {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/verify-email', {
                    email,
                    otp,
                    operation_type: operationType,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Verify email failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل التحقق من الإيميل' };
        }
    }

    /**
     * ✅ إلغاء OTP نشط
     * @param {string} email - الإيميل
     * @param {string} purpose - الغرض (password_reset, login, registration, etc.)
     */
    async cancelOTP(email, purpose = 'password_reset') {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/cancel-otp', {
                    email: email.toLowerCase().trim(),
                    purpose: purpose,
                })
            );

            // ✅ التحقق من الاستجابة
            if (response?.data) {
                return response.data;
            }

            // ✅ إذا لم تكن هناك استجابة واضحة، نعتبرها نجاح
            return { success: true, message: 'تم إلغاء رمز التحقق' };
        } catch (error) {
            Logger.error('❌ Cancel OTP failed:', error.message);

            // ✅ إذا كان الخطأ 404 (لا يوجد OTP نشط)، نعتبرها نجاح
            if (error.response?.status === 404) {
                return { success: true, message: 'لا يوجد رمز تحقق نشط' };
            }

            return {
                success: false,
                error: error.response?.data?.error || 'فشل إلغاء رمز التحقق',
            };
        }
    }

    /**
     * ✅ جلب طرق التحقق المتاحة لإيميل (قبل المصادقة)
     * @param {string} email - الإيميل
     * @returns {Promise<{success: boolean, options: Array, masked_phone: string, masked_email: string}>}
     */
    async getVerificationMethods(email) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/get-verification-methods', { email })
            );
            return response.data;
        } catch (error) {
            Logger.error('Get verification methods failed', 'DatabaseApiService', error);
            return { success: false, options: [], error: error?.response?.data?.error || 'فشل جلب طرق التحقق' };
        }
    }

    /**
     * إرسال OTP لاستعادة كلمة المرور
     * @param {string} email - الإيميل
     */
    async sendResetPasswordOTP(email, additionalData = {}) {
        try {
            await this.initialize();
            const payload = { email };
            if (additionalData.method) { payload.method = additionalData.method; }
            if (additionalData.phone) { payload.phone = additionalData.phone; }
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/forgot-password', payload)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Send reset password OTP failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل إرسال رمز استعادة كلمة المرور' };
        }
    }

    /**
     * التحقق من OTP لاستعادة كلمة المرور والحصول على Reset Token
     * @param {string} email - الإيميل
     * @param {string} otp - رمز التحقق
     */
    async verifyResetOTP(email, otp) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/verify-reset-otp', {
                    email,
                    otp,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Verify reset OTP failed:', error?.message);
            const errorData = error?.response?.data || {};
            return {
                success: false,
                message: errorData.error || 'فشل التحقق من رمز OTP',
                remaining_attempts: errorData.remaining_attempts || 0,
            };
        }
    }

    /**
     * إعادة تعيين كلمة المرور باستخدام Reset Token
     * @param {string} resetToken - رمز إعادة التعيين
     * @param {string} newPassword - كلمة المرور الجديدة
     */
    async resetPasswordWithToken(resetToken, newPassword) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/reset-password', {
                    reset_token: resetToken,
                    new_password: newPassword,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Reset password with token failed:', error?.message);
            return {
                success: false,
                message: error?.response?.data?.error || 'فشل إعادة تعيين كلمة المرور',
            };
        }
    }

    /**
     * @deprecated استخدم verifyResetOTP ثم resetPasswordWithToken
     * التحقق وإعادة تعيين كلمة المرور (طريقة قديمة)
     */
    async verifyResetPassword(email, otp, additionalData = {}) {
        try {
            // الطريقة الجديدة: خطوتين منفصلتين
            const verifyResult = await this.verifyResetOTP(email, otp);
            if (!verifyResult.success) {
                return verifyResult;
            }

            const resetToken = verifyResult.reset_token;
            const newPassword = additionalData.newPassword || additionalData.new_password;

            if (!newPassword) {
                return { success: false, message: 'كلمة المرور الجديدة مطلوبة' };
            }

            return await this.resetPasswordWithToken(resetToken, newPassword);
        } catch (error) {
            Logger.error('❌ Verify reset password failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل إعادة تعيين كلمة المرور' };
        }
    }

    /**
     * إرسال OTP لتغيير الإيميل
     * @param {string} newEmail - الإيميل الجديد
     * @param {object} additionalData - بيانات إضافية
     */
    async sendChangeEmailOTP(newEmail, additionalData = {}) {
        try {
            await this.initialize();
            const userId = additionalData.userId || additionalData.user_id;
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/send-change-email-otp', {
                    new_email: newEmail,
                    user_id: userId,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Send change email OTP failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل إرسال رمز تغيير الإيميل' };
        }
    }

    /**
     * التحقق وتغيير الإيميل
     * @param {string} newEmail - الإيميل الجديد
     * @param {string} otp - رمز التحقق
     * @param {object} additionalData - بيانات إضافية
     */
    async verifyChangeEmail(newEmail, otp, additionalData = {}) {
        try {
            await this.initialize();
            const userId = additionalData.userId || additionalData.user_id;
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/verify-change-email-otp', {
                    new_email: newEmail,
                    otp,
                    user_id: userId,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Verify change email failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل تغيير الإيميل' };
        }
    }

    /**
     * إرسال OTP لتغيير كلمة المرور
     * @param {string} email - الإيميل
     * @param {object} additionalData - بيانات إضافية (تحتوي على old_password)
     */
    async sendChangePasswordOTP(email, additionalData = {}) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/send-change-password-otp', {
                    email,
                    old_password: additionalData.oldPassword || additionalData.old_password,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Send change password OTP failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل إرسال رمز تغيير كلمة المرور' };
        }
    }

    /**
     * التحقق وتغيير كلمة المرور
     * @param {string} email - الإيميل
     * @param {string} otp - رمز التحقق
     * @param {object} additionalData - بيانات إضافية (تحتوي على new_password)
     */
    async verifyChangePassword(email, otp, additionalData = {}) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/verify-change-password-otp', {
                    email,
                    otp,
                    new_password: additionalData.newPassword || additionalData.new_password,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Verify change password failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل تغيير كلمة المرور' };
        }
    }

    /**
     * التحقق من رمز الهاتف (Firebase)
     * @param {string} idToken - رمز Firebase
     * @param {string} phoneNumber - رقم الهاتف
     */
    async verifyPhoneToken(idToken, phoneNumber) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/verify-phone-token', {
                    idToken,
                    phoneNumber,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Verify phone token failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل التحقق من الهاتف' };
        }
    }

    /**
     * جلب إحصائيات المستخدم (للـ Pie Chart)
     * @param {number} userId - معرف المستخدم
     */
    async getUserStats(userId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(`/stats/${userId}`)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get user stats failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل جلب الإحصائيات' };
        }
    }

    /**
     * جلب الأرباح/الخسائر اليومية (للـ Heatmap)
     * @param {number} userId - معرف المستخدم
     * @param {number} days - عدد الأيام
     * @param {boolean} isAdmin - هل المستخدم أدمن
     * @param {string} tradingMode - وضع التداول
     */
    async getDailyPnL(userId, days = 90, isAdmin = false, tradingMode = 'auto') {
        try {
            await this.initialize();
            let url = `/daily-pnl/${userId}?days=${days}`;

            if (isAdmin) {
                url += `&is_admin=true&trading_mode=${tradingMode}`;
            }

            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(url)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get daily PnL failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل جلب البيانات اليومية' };
        }
    }

    // ============================================================
    // ML Learning API (Smart Incremental Learning System)
    // ============================================================

    /**
     * الحصول على تقدم التعلم لمستخدم
     */
    async getMLLearningProgress(userId = null) {
        try {
            await this.initialize();

            // إذا لم يتم تحديد userId، استخدم المستخدم الحالي
            if (!userId) {
                const userStr = await AsyncStorage.getItem('userData');
                if (userStr) {
                    try {
                        const user = JSON.parse(userStr);
                        userId = user.id;
                    } catch (parseError) {
                        Logger.error('فشل تحليل بيانات المستخدم في getMLLearningProgress', 'DatabaseApiService', parseError);
                    }
                }
            }

            // ✅ FIX: تأكد من وجود userId قبل الطلب
            if (!userId) {
                return {
                    success: false,
                    message: 'لا يوجد مستخدم مسجل دخول',
                    data: { total_signals_processed: 0, learning_stage: 'initial' },
                };
            }

            // ✅ FIX: استخدام المسار الكامل لأن ML endpoint ليس تحت /api/user
            const serverURL = unifiedConnectionService.getBaseURL();
            const token = await AsyncStorage.getItem('authToken');
            const response = await this._retryWithBackoff(() =>
                axios.get(`${serverURL}/api/ml/learning/progress/${userId}`, {
                    headers: token ? { Authorization: `Bearer ${token}` } : {},
                    timeout: 10000,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get ML learning progress failed:', error?.message);
            return {
                success: false,
                message: error?.response?.data?.error || 'فشل جلب تقدم التعلم',
                data: {
                    total_signals_processed: 0,
                    total_combinations: 0,
                    learned_combinations: 0,
                    overall_win_rate: 0,
                    learning_stage: 'initial',
                    system_readiness: 0,
                },
            };
        }
    }

    /**
     * الحصول على صحة نظام التعلم
     */
    async getMLLearningHealth(userId = null) {
        try {
            await this.initialize();

            const params = userId ? `?user_id=${userId}` : '';
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(`/ml/learning/health${params}`)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get ML learning health failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل جلب صحة التعلم' };
        }
    }

    /**
     * الحصول على ملخص التعلم الشامل
     */
    async getMLLearningSummary(userId = null) {
        try {
            await this.initialize();

            const params = userId ? `?user_id=${userId}` : '';
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(`/ml/learning/stats/summary${params}`)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get ML learning summary failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل جلب ملخص التعلم' };
        }
    }

    /**
     * تشغيل فحص صحة يدوي
     */
    async triggerMLHealthCheck(userId) {
        try {
            await this.initialize();

            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/ml/learning/run-health-check', { user_id: userId })
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Trigger ML health check failed:', error);
            return { success: false, message: error?.response?.data?.error || 'فشل تشغيل فحص الصحة' };
        }
    }

    /**
     * ✅ التحقق من متطلبات التداول وفحص الإعدادات
     */
    async validateTradingSettings(userId, settings) {
        try {
            await this.initialize();
            const serverURL = unifiedConnectionService.getBaseURL();
            const token = await AsyncStorage.getItem('authToken');

            const response = await axios.post(`${serverURL}/api/user/settings/${userId}/validate`, {
                settings: settings,
            }, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
                timeout: 10000,
            });

            return response.data;
        } catch (error) {
            Logger.error('❌ Validate trading settings failed:', error);
            return {
                success: false,
                message: error?.response?.data?.error || 'فشل التحقق من متطلبات التداول',
                data: {
                    can_trade: false,
                    reason: 'خطأ في التحقق من المتطلبات',
                    has_keys: false,
                    sufficient_balance: false,
                    current_positions: 0,
                    max_allowed_positions: settings?.max_positions || 5,
                },
            };
        }
    }
    // =========================================================================
    // 🛡️ ADMIN API METHODS
    // =========================================================================

    // ✅ دالة موحدة للأخطاء العامة
    async getAdminErrors(filters = {}) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get('/admin/errors', { params: filters })
            );
            return response.data;
        } catch (error) {
            Logger.error('Get admin errors failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    async getAdminCriticalErrors(params = {}) {
        try {
            const errorsResponse = await this.getBackgroundErrors(params.limit || 100);
            if (!errorsResponse?.success) {
                return errorsResponse;
            }

            const allErrors = errorsResponse.errors || errorsResponse.data?.errors || [];
            const criticalErrors = allErrors.filter(e => e?.level === 'critical' || e?.severity === 'critical');

            return {
                success: true,
                errors: criticalErrors,
                count: criticalErrors.length,
            };
        } catch (error) {
            Logger.error('Get critical errors failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    // ✅ Group B APIs - تمت إزالة التكرار (المسارات الصحيحة في الأعلى)

    // ✅ إحصائيات النظام
    async getSystemStats() {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get('/admin/system/stats')
            );
            return response.data;
        } catch (error) {
            Logger.error('Get System Stats failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    // ✅ إحصائيات المستخدمين
    async getUsersStats() {
        try {
            const usersResponse = await this.getAllUsers();
            if (!usersResponse?.success) {
                return usersResponse;
            }

            const users = usersResponse.users || usersResponse.data?.users || [];
            const stats = usersResponse.stats || usersResponse.data?.stats || {
                total_users: users.length,
                active_users: users.filter(u => u?.is_active).length,
                admin_users: users.filter(u => u?.user_type === 'admin').length,
            };

            return {
                success: true,
                data: stats,
            };
        } catch (error) {
            Logger.error('Get Users Stats failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    // ✅ إحصائيات التداول
    async getTradingStats() {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get('/admin/trades/stats')
            );
            return response.data;
        } catch (error) {
            Logger.error('Get Trading Stats failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    // ✅ إحصائيات المحفظة (Admin)
    async getPortfolioStats() {
        try {
            const status = await this.getSystemMLStatus('demo');
            if (!status?.success) {
                return { success: false, error: status?.error || 'فشل جلب إحصائيات المحفظة' };
            }

            return {
                success: true,
                data: status.portfolio || {},
            };
        } catch (error) {
            Logger.error('Get Portfolio Stats failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    // ✅ إدارة إعدادات النظام
    async updateSystemSettings(settings) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.patch('/admin/config', settings)
            );
            return response.data;
        } catch (error) {
            Logger.error('Update System Settings failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    async getSystemSettings() {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get('/admin/config')
            );
            return response.data;
        } catch (error) {
            Logger.error('Get System Settings failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    // ✅ إدارة الإشعارات (Admin) - تمت إزالة التكرار مع getNotificationSettings/updateNotificationSettings
    async getAdminNotificationSettings() {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get('/admin/notification-settings')
            );
            return response.data;
        } catch (error) {
            Logger.error('Get Admin Notification Settings failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    async updateAdminNotificationSettings(settings) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.put('/admin/notification-settings', settings)
            );
            return response.data;
        } catch (error) {
            Logger.error('Update Admin Notification Settings failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    // ✅ إدارة النظام - restartSystem (uses direct axios with correct URL)
    async restartSystem() {
        try {
            const stopResult = await this.stopTradingSystem();
            if (!stopResult?.success && stopResult?.trading_state !== 'STOPPED') {
                return {
                    success: false,
                    error: stopResult?.message || 'فشل إيقاف النظام قبل إعادة التشغيل',
                };
            }

            const startResult = await this.startTradingSystem('PAPER');
            return startResult;
        } catch (error) {
            Logger.error('Restart System failed', 'DatabaseApiService', error);
            return { success: false, error: error?.message };
        }
    }

    // ✅ Notifications - إدارة الإشعارات
    async getNotifications(userId, page = 1, limit = 20) {
        try {
            // ✅ فحص صحة userId
            if (!userId || userId === 'unknown' || userId === 'guest') {
                Logger.warn('❌ معرف المستخدم غير صالح للإشعارات');
                return { success: false, data: { notifications: [], total: 0, unread: 0 } };
            }

            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                axios.get(`${unifiedConnectionService.getBaseURL()}/api/user/notifications/${userId}`, {
                    headers: this._getHeaders(),
                    params: { page, limit },
                    timeout: 10000,
                })
            );
            return response.data;
        } catch (error) {
            Logger.error('Get Notifications failed', 'DatabaseApiService', error);
            return { success: false, data: { notifications: [], total: 0, unread: 0 } };
        }
    }

    async getFavoriteTrades(userId, mode = null) {
        try {
            await this.initialize();
            const url = mode
                ? `/trades/favorites/${userId}?mode=${mode}`
                : `/trades/favorites/${userId}`;
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(url)
            );
            return response.data;
        } catch (error) {
            Logger.error('Get favorite trades failed', 'DatabaseApiService', error);
            return { success: false, data: { trades: [] } };
        }
    }

    async getTradesWithDistribution(userId, mode = null) {
        try {
            await this.initialize();
            const url = mode
                ? `/trades/distribution/${userId}?mode=${mode}`
                : `/trades/distribution/${userId}`;
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(url)
            );
            return response.data;
        } catch (error) {
            Logger.error('Get trades distribution failed', 'DatabaseApiService', error);
            return { success: false, data: { distribution: {}, totalTrades: 0 } };
        }
    }

    // =========================================================================
    // 🔔 USER NOTIFICATION SETTINGS APIs
    // =========================================================================

    /**
     * جلب إعدادات الإشعارات للمستخدم
     * @param {number} userId - معرف المستخدم
     */
    async getNotificationSettings(userId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(`/notifications/settings`)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get user notification settings failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل جلب إعدادات الإشعارات' };
        }
    }

    /**
     * حفظ إعدادات الإشعارات للمستخدم
     * @param {number} userId - معرف المستخدم
     * @param {object} settings - إعدادات الإشعارات
     */
    async updateNotificationSettings(userId, settings) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.put(`/notifications/settings`, settings)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Update user notification settings failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل حفظ إعدادات الإشعارات' };
        }
    }

    // =========================================================================
    // 👥 USER MANAGEMENT APIs (Admin)
    // =========================================================================

    /**
     * جلب جميع المستخدمين (Admin)
     */
    async getAllUsers() {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get('/admin/users/all')
            );
            const payload = response.data || {};
            const users = payload.users || payload.data?.users || [];
            const stats = payload.stats || payload.data?.stats || null;

            return {
                ...payload,
                users,
                stats,
                total: payload.total || stats?.total_users || users.length,
            };
        } catch (error) {
            Logger.error('❌ Get all users failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل جلب قائمة المستخدمين' };
        }
    }

    /**
     * جلب تفاصيل مستخدم معين (Admin)
     * @param {number} userId - معرف المستخدم
     */
    async getUserDetails(userId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get(`/admin/users/${userId}`)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get user details failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل جلب تفاصيل المستخدم' };
        }
    }

    /**
     * إنشاء مستخدم جديد (Admin)
     * @param {object} userData - بيانات المستخدم الجديد
     */
    async createUser(userData) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/admin/users/create', userData)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Create user failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل إنشاء المستخدم' };
        }
    }

    /**
     * تحديث بيانات مستخدم (Admin)
     * @param {number} userId - معرف المستخدم
     * @param {object} userData - البيانات المحدثة
     */
    async updateUser(userId, userData) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.put(`/admin/users/${userId}/update`, userData)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Update user failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل تحديث المستخدم' };
        }
    }

    /**
     * تعطيل مستخدم (Admin)
     * @param {number} userId - معرف المستخدم
     */
    async deleteUser(userId) {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.delete(`/admin/users/${userId}/delete`)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Delete user failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل تعطيل المستخدم' };
        }
    }

    // =========================================================================
    // 🔍 AVAILABILITY CHECKING APIs
    // =========================================================================

    /**
     * التحقق من توفر البريد الإلكتروني أو اسم المستخدم أو رقم الهاتف
     * @param {string} email - البريد الإلكتروني (اختياري)
     * @param {string} username - اسم المستخدم (اختياري)
     * @param {string} phone - رقم الهاتف (اختياري)
     */
    async checkAvailability(email = null, username = null, phone = null) {
        try {
            await this.initialize();
            const params = {};
            if (email) params.email = email;
            if (username) params.username = username;
            if (phone) params.phone = phone;

            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/auth/check-availability', params)
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Check availability failed:', error?.message);
            return {
                success: false,
                message: error?.response?.data?.error || 'فشل التحقق من التوفر',
                emailAvailable: null,
                usernameAvailable: null,
                phoneAvailable: null
            };
        }
    }

    // =========================================================================
    // 💾 CACHE & OFFLINE SUPPORT APIs
    // =========================================================================

    /**
     * جلب حالة الـ Cache
     */
    async getCacheStatus() {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get('/cache/status')
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get cache status failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل جلب حالة الـ Cache' };
        }
    }

    /**
     * مسح الـ Cache
     */
    async clearCache() {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.post('/cache/clear')
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Clear cache failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل مسح الـ Cache' };
        }
    }

    /**
     * جلب حالة التكامل
     */
    async getIntegrationStatus() {
        try {
            await this.initialize();
            const response = await this._retryWithBackoff(() =>
                this.apiClient.get('/integration/status')
            );
            return response.data;
        } catch (error) {
            Logger.error('❌ Get integration status failed:', error?.message);
            return { success: false, message: error?.response?.data?.error || 'فشل جلب حالة التكامل' };
        }
    }
}

// ✅ Singleton Instance
const databaseApiService = new DatabaseApiService();
export default databaseApiService;
