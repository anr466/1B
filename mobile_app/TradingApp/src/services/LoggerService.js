/**
 * نظام تسجيل موحد للأخطاء والرسائل البرمجية
 *
 * الغرض:
 * - تسجيل جميع رسائل الكونسول البرمجية في ملف موحد
 * - رسائل الأخطاء البرمجية (للمطور) → تُسجل في الملف
 * - رسائل الأخطاء للمستخدم → تظهر في الواجهة فقط
 */

import RNFS from 'react-native-fs';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
// ✅ FIX: Lazy-load to break require cycle (LoggerService ↔ UnifiedConnectionService)
let _unifiedConnectionService = null;
function getUnifiedConnectionService() {
    if (!_unifiedConnectionService) {
        _unifiedConnectionService = require('./UnifiedConnectionService').default;
    }
    return _unifiedConnectionService;
}

class LoggerService {
    constructor() {
        this.logFilePath = `${RNFS.DocumentDirectoryPath}/app_logs.txt`;
        this.maxLogSize = 5 * 1024 * 1024; // 5MB
        this.isEnabled = true; // يمكن تعطيله في الإنتاج

        // ✅ إعدادات إرسال السجلات للخادم
        this.sendToServer = true; // تفعيل الإرسال للخادم
        this.logBuffer = []; // buffer لتجميع السجلات
        this.maxBufferSize = 10; // عدد السجلات قبل الإرسال
        this.flushInterval = 30000; // إرسال كل 30 ثانية
        this.userId = null;
        this.deviceInfo = null;

        // بدء timer للإرسال الدوري
        this._startFlushTimer();
        this._loadUserInfo();
    }

    /**
     * تحميل معلومات المستخدم
     */
    async _loadUserInfo() {
        try {
            const userId = await AsyncStorage.getItem('userId');
            const userType = await AsyncStorage.getItem('userType');

            // ✅ فقط استخدم userId إذا كان صالح ومُصرح
            if (userId && userId !== 'undefined' && userId !== 'null' && userType !== 'guest') {
                this.userId = userId;
            } else {
                this.userId = 'unknown';
            }

            // جمع معلومات الجهاز
            const { Platform, Dimensions } = require('react-native');
            this.deviceInfo = `${Platform.OS}/${Platform.Version}`;
        } catch (error) {
            this.userId = 'unknown';
        }
    }

    /**
     * بدء timer للإرسال الدوري
     */
    _startFlushTimer() {
        this.flushTimer = setInterval(() => {
            this._flushLogsToServer();
        }, this.flushInterval);
    }

    /**
     * إيقاف timer
     */
    _stopFlushTimer() {
        if (this.flushTimer) {
            clearInterval(this.flushTimer);
            this.flushTimer = null;
        }
    }

    /**
     * تسجيل رسالة معلوماتية (للمطور)
     */
    async info(message, context = '') {
        const logEntry = this._formatLog('INFO', message, context);
        await this._writeToFile(logEntry);
        await this._addToBuffer('INFO', message, context);
        if (__DEV__) {
            console.log(logEntry);
        }
    }

    /**
     * تسجيل رسالة تحذير (للمطور)
     */
    async warn(message, context = '') {
        const logEntry = this._formatLog('WARN', message, context);
        await this._writeToFile(logEntry);
        await this._addToBuffer('WARN', message, context);
        if (__DEV__) {
            console.warn(logEntry);
        }
    }

    /**
     * تسجيل خطأ برمجي (للمطور)
     */
    async error(message, error = null, context = '') {
        const errorDetails = error ? `\n${error.stack || error.message || error}` : '';
        const logEntry = this._formatLog('ERROR', message + errorDetails, context);
        await this._writeToFile(logEntry);
        await this._addToBuffer('ERROR', message + errorDetails, context, true); // إرسال فوري
        if (__DEV__) {
            console.error(logEntry);
        }
    }

    /**
     * تسجيل خطأ حرج (للمطور)
     */
    async critical(message, error = null, context = '') {
        const errorDetails = error ? `\n${error.stack || error.message || error}` : '';
        const logEntry = this._formatLog('CRITICAL', message + errorDetails, context);
        await this._writeToFile(logEntry);
        await this._addToBuffer('CRITICAL', message + errorDetails, context, true); // إرسال فوري
        console.error('🔴 CRITICAL:', logEntry);
    }

    /**
     * تسجيل رسالة debug (للمطور فقط)
     */
    async debug(message, context = '') {
        if (!__DEV__) { return; } // فقط في وضع التطوير
        const logEntry = this._formatLog('DEBUG', message, context);
        await this._writeToFile(logEntry);
        console.log(logEntry);
    }

    /**
     * تنسيق رسالة السجل
     */
    _formatLog(level, message, context) {
        const timestamp = new Date().toISOString();
        const contextStr = context ? ` [${context}]` : '';
        return `[${timestamp}] ${level}${contextStr}: ${message}`;
    }

    /**
     * كتابة السجل في الملف
     */
    async _writeToFile(logEntry) {
        if (!this.isEnabled) { return; }

        try {
            // التحقق من حجم الملف
            const fileExists = await RNFS.exists(this.logFilePath);
            if (fileExists) {
                const stats = await RNFS.stat(this.logFilePath);
                if (stats.size > this.maxLogSize) {
                    // إنشاء نسخة احتياطية وحذف الملف القديم
                    const backupPath = `${this.logFilePath}.old`;
                    await RNFS.moveFile(this.logFilePath, backupPath);
                }
            }

            // إضافة السجل للملف
            await RNFS.appendFile(this.logFilePath, logEntry + '\n', 'utf8');
        } catch (error) {
            // في حالة فشل الكتابة، نعرض في الكونسول فقط
            if (__DEV__) {
                console.error('Failed to write log:', error);
            }
        }
    }

    /**
     * قراءة السجلات (للمطور)
     */
    async readLogs() {
        try {
            const fileExists = await RNFS.exists(this.logFilePath);
            if (!fileExists) {
                return 'No logs available';
            }
            return await RNFS.readFile(this.logFilePath, 'utf8');
        } catch (error) {
            return `Error reading logs: ${error.message}`;
        }
    }

    /**
     * مسح السجلات
     */
    async clearLogs() {
        try {
            const fileExists = await RNFS.exists(this.logFilePath);
            if (fileExists) {
                await RNFS.unlink(this.logFilePath);
            }
            return true;
        } catch (error) {
            console.error('Failed to clear logs:', error);
            return false;
        }
    }

    /**
     * الحصول على مسار الملف
     */
    getLogFilePath() {
        return this.logFilePath;
    }

    /**
     * تفعيل/تعطيل التسجيل
     */
    setEnabled(enabled) {
        this.isEnabled = enabled;
    }

    /**
     * ✅ إضافة سجل إلى buffer
     */
    async _addToBuffer(level, message, context, immediate = false) {
        if (!this.sendToServer) { return; }

        const logEntry = {
            level,
            message,
            context,
            timestamp: new Date().toISOString(),
            userId: this.userId,
            device: this.deviceInfo,
        };

        this.logBuffer.push(logEntry);

        // إرسال فوري للأخطاء الحرجة
        if (immediate) {
            await this._flushLogsToServer();
        }
        // أو إرسال عند امتلاء الـ buffer
        else if (this.logBuffer.length >= this.maxBufferSize) {
            await this._flushLogsToServer();
        }
    }

    /**
     * ✅ إرسال السجلات المتراكمة للخادم
     */
    async _flushLogsToServer() {
        if (!this.sendToServer || this.logBuffer.length === 0) { return; }

        const logs = [...this.logBuffer];
        this.logBuffer = []; // تفريغ الـ buffer

        try {
            const baseURL = getUnifiedConnectionService().getBaseURL();

            await axios.post(`${baseURL}/api/client-logs/batch`, {
                logs,
            }, {
                timeout: 5000,
                headers: { 'Content-Type': 'application/json' },
            });

            // نجح الإرسال - لا حاجة لتسجيل
        } catch (error) {
            // فشل الإرسال - إعادة السجلات للـ buffer
            this.logBuffer = [...logs, ...this.logBuffer];

            // حذف السجلات القديمة جداً لتجنب امتلاء الذاكرة
            if (this.logBuffer.length > 100) {
                this.logBuffer = this.logBuffer.slice(-50);
            }
        }
    }

    /**
     * ✅ إرسال فوري للسجلات (للاستخدام عند إغلاق التطبيق)
     */
    async flush() {
        await this._flushLogsToServer();
    }

    /**
     * ✅ تفعيل/تعطيل الإرسال للخادم
     */
    setSendToServer(enabled) {
        this.sendToServer = enabled;
        if (!enabled) {
            this._stopFlushTimer();
        } else {
            this._startFlushTimer();
        }
    }

    /**
     * ✅ تنظيف الموارد
     */
    cleanup() {
        this._stopFlushTimer();
        this._flushLogsToServer(); // إرسال أي سجلات متبقية
    }
}

// تصدير instance واحد
export default new LoggerService();
