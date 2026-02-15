/**
 * ⚙️ إعدادات الخادم الموحدة
 * ملف مركزي واحد لجميع إعدادات الاتصال بالخادم
 *
 * يجمع وظائف:
 * - ConnectionConfig
 * - DynamicIPConfig
 * - UnifiedServerConfig
 * - AutoIPUpdateConfig
 * - env.config
 */

import { Platform, NativeModules } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

class ServerConfig {
    constructor() {
        // ============================================================
        // إعدادات الخادم الأساسية
        // ============================================================
        this.SERVER = {
            PORT: 3002,
            PROTOCOL: 'http',
            TIMEOUT: 10000,
            MAX_RETRIES: 3,
            RETRY_DELAY: 1000,
        };

        // ============================================================
        // نقاط النهاية (Endpoints)
        // ============================================================
        this.ENDPOINTS = {
            HEALTH: '/health',
            STATUS: '/api/system/status',

            AUTH: {
                LOGIN: '/api/auth/login',
                REGISTER: '/api/auth/register',
                LOGOUT: '/api/auth/logout',
                REFRESH: '/api/auth/refresh',
                SEND_OTP: '/api/auth/send-otp',
                VERIFY_EMAIL: '/api/auth/verify-email',
                FORGOT_PASSWORD: '/api/auth/forgot-password',
                RESET_PASSWORD: '/api/auth/reset-password',
                VALIDATE_SESSION: '/api/auth/validate-session',
            },

            USER: {
                PORTFOLIO: '/api/user/portfolio',
                STATS: '/api/user/stats',
                TRADES: '/api/user/trades',
                SETTINGS: '/api/user/settings',
                PROFILE: '/api/user/profile',
                BINANCE_KEYS: '/api/user/binance-keys',
                SUCCESSFUL_COINS: '/api/user/successful-coins',
            },

            ADMIN: {
                SYSTEM_STATUS: '/api/admin/system/status',
                SYSTEM_STATS: '/api/admin/system/stats',
                USERS: '/api/admin/users',
                ERRORS: '/api/admin/errors',
                TRADING_STATUS: '/api/admin/trading/status',
            },
        };

        // ============================================================
        // معلومات IP والاتصال
        // ============================================================
        this.ipConfig = {
            hostIP: null,
            deviceIP: null,
            lastUpdate: null,
            lastKnownIP: null,
        };

        this.connection = {
            method: null,
            baseURL: null,
            isConnected: false,
            lastChecked: null,
            error: null,
        };

        // ============================================================
        // مفاتيح التخزين
        // ============================================================
        this.STORAGE_KEYS = {
            HOST_IP: '@server_config_host_ip',
            LAST_KNOWN_IP: '@server_config_last_known_ip',
            LAST_UPDATE: '@server_config_last_update',
        };

        // ============================================================
        // إعدادات التطوير
        // ============================================================
        this.DEBUG = {
            LOG_REQUESTS: __DEV__ || false,
            LOG_RESPONSES: __DEV__ || false,
        };
    }

    // ============================================================
    // تهيئة النظام
    // ============================================================

    async initialize() {
        console.log('⚙️ [ServerConfig] Initializing...');

        try {
            // 1. تحميل آخر IP معروف
            await this._loadSavedIP();

            // 2. اكتشاف IP الحالي
            await this._detectCurrentIP();

            // 3. حفظ في التخزين
            await this._saveIP();

            console.log('✅ [ServerConfig] Initialized:', {
                hostIP: this.ipConfig.hostIP,
                baseURL: this.getBaseURL(),
            });

            return true;
        } catch (error) {
            console.error('❌ [ServerConfig] Failed to initialize:', error);
            return false;
        }
    }

    // ============================================================
    // إدارة IP
    // ============================================================

    async _loadSavedIP() {
        try {
            const savedIP = await AsyncStorage.getItem(this.STORAGE_KEYS.LAST_KNOWN_IP);
            if (savedIP) {
                this.ipConfig.lastKnownIP = savedIP;
                this.ipConfig.hostIP = savedIP;
                console.log('📂 [ServerConfig] Loaded saved IP:', savedIP);
            }
        } catch (error) {
            console.log('⚠️ [ServerConfig] Could not load saved IP');
        }
    }

    async _detectCurrentIP() {
        try {
            // 1. متغيرات البيئة
            const envIP = process.env.REACT_APP_HOST_IP ||
                process.env.BACKEND_HOST;

            if (envIP) {
                this.ipConfig.hostIP = envIP;
                console.log('✅ [ServerConfig] IP from environment:', envIP);
                return;
            }

            // 2. آخر IP معروف
            if (this.ipConfig.lastKnownIP) {
                this.ipConfig.hostIP = this.ipConfig.lastKnownIP;
                console.log('✅ [ServerConfig] Using last known IP:', this.ipConfig.lastKnownIP);
                return;
            }

            // 3. قيمة افتراضية (10.0.2.2 للمحاكي)
            this.ipConfig.hostIP = Platform.OS === 'android' ? '10.0.2.2' : 'localhost';
            console.log('⚠️ [ServerConfig] Using default:', this.ipConfig.hostIP);

        } catch (error) {
            console.error('❌ [ServerConfig] Error detecting IP:', error);
            this.ipConfig.hostIP = Platform.OS === 'android' ? '10.0.2.2' : 'localhost';
        }
    }

    async _saveIP() {
        try {
            if (this.ipConfig.hostIP) {
                await AsyncStorage.setItem(this.STORAGE_KEYS.LAST_KNOWN_IP, this.ipConfig.hostIP);
                await AsyncStorage.setItem(this.STORAGE_KEYS.LAST_UPDATE, new Date().toISOString());
                this.ipConfig.lastUpdate = new Date();
            }
        } catch (error) {
            console.error('❌ [ServerConfig] Error saving IP:', error);
        }
    }

    async setHostIP(ip) {
        try {
            this.ipConfig.hostIP = ip;
            this.ipConfig.lastKnownIP = ip;
            await this._saveIP();
            console.log('✅ [ServerConfig] Host IP set:', ip);
            return true;
        } catch (error) {
            console.error('❌ [ServerConfig] Error setting IP:', error);
            return false;
        }
    }

    // ============================================================
    // إدارة الاتصال
    // ============================================================

    getBaseURL() {
        if (this.connection.baseURL) {
            return this.connection.baseURL;
        }

        const host = this.ipConfig.hostIP || (Platform.OS === 'android' ? '10.0.2.2' : 'localhost');
        return `${this.SERVER.PROTOCOL}://${host}:${this.SERVER.PORT}`;
    }

    getEndpointURL(endpoint) {
        return `${this.getBaseURL()}${endpoint}`;
    }

    setConnection(method, baseURL) {
        this.connection = {
            method,
            baseURL,
            isConnected: true,
            lastChecked: new Date(),
            error: null,
        };
        console.log(`✅ [ServerConfig] Connected: ${method} → ${baseURL}`);
    }

    setConnectionError(error) {
        this.connection.error = error;
        this.connection.isConnected = false;
        this.connection.lastChecked = new Date();
        console.error('❌ [ServerConfig] Connection error:', error.message);
    }

    // ============================================================
    // طرق الاتصال الممكنة
    // ============================================================

    getPossibleURLs() {
        const urls = [];

        // 1. Port Forwarding (localhost) - الأفضل
        urls.push({
            method: 'port_forwarding',
            url: `http://localhost:${this.SERVER.PORT}`,
            priority: 1,
            description: 'USB Port Forwarding (ADB)',
        });

        // 2. الشبكة المحلية
        if (this.ipConfig.hostIP && this.ipConfig.hostIP !== 'localhost') {
            urls.push({
                method: 'local_network',
                url: `http://${this.ipConfig.hostIP}:${this.SERVER.PORT}`,
                priority: 2,
                description: `Local Network (${this.ipConfig.hostIP})`,
            });
        }

        // 3. Android Emulator
        if (Platform.OS === 'android') {
            urls.push({
                method: 'android_emulator',
                url: `http://10.0.2.2:${this.SERVER.PORT}`,
                priority: 3,
                description: 'Android Emulator',
            });
        }

        return urls;
    }

    // ============================================================
    // معلومات الحالة
    // ============================================================

    getConnectionInfo() {
        return {
            ...this.connection,
            hostIP: this.ipConfig.hostIP,
            port: this.SERVER.PORT,
            protocol: this.SERVER.PROTOCOL,
            possibleURLs: this.getPossibleURLs(),
        };
    }

    getConfig() {
        return {
            server: this.SERVER,
            endpoints: this.ENDPOINTS,
            ip: this.ipConfig,
            connection: this.connection,
            debug: this.DEBUG,
        };
    }

    // ============================================================
    // إعادة التعيين
    // ============================================================

    async reset() {
        try {
            await AsyncStorage.multiRemove([
                this.STORAGE_KEYS.HOST_IP,
                this.STORAGE_KEYS.LAST_KNOWN_IP,
                this.STORAGE_KEYS.LAST_UPDATE,
            ]);

            this.ipConfig = {
                hostIP: null,
                deviceIP: null,
                lastUpdate: null,
                lastKnownIP: null,
            };

            this.connection = {
                method: null,
                baseURL: null,
                isConnected: false,
                lastChecked: null,
                error: null,
            };

            console.log('✅ [ServerConfig] Reset complete');
            return true;
        } catch (error) {
            console.error('❌ [ServerConfig] Reset error:', error);
            return false;
        }
    }

    // ============================================================
    // طباعة الإعدادات
    // ============================================================

    printConfig() {
        console.log('═'.repeat(60));
        console.log('⚙️ Server Configuration');
        console.log('═'.repeat(60));
        console.log(`📡 Port: ${this.SERVER.PORT}`);
        console.log(`🔗 Protocol: ${this.SERVER.PROTOCOL}`);
        console.log(`🖥️ Host IP: ${this.ipConfig.hostIP || 'Not set'}`);
        console.log(`🌐 Base URL: ${this.getBaseURL()}`);
        console.log(`✅ Connected: ${this.connection.isConnected ? 'Yes' : 'No'}`);
        console.log('═'.repeat(60));
    }
}

// ✅ Singleton instance
const serverConfig = new ServerConfig();

export default serverConfig;
