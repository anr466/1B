/**
 * 🌐 خدمة الاتصال الموحدة
 * تتعامل مع جميع طرق الاتصال تلقائياً بدون تعارضات
 *
 * الميزات:
 * ✅ تجربة جميع الطرق تلقائياً
 * ✅ اختيار الأفضل منها
 * ✅ إعادة محاولة عند الفشل
 * ✅ تخزين مؤقت للنتيجة الناجحة
 * ✅ تحديث IP ديناميكي
 * ✅ استخدام إعدادات موحدة
 */

import serverConfig from '../config/ServerConfig';
import Logger from './LoggerService';

class UnifiedConnectionService {
  constructor() {
    this.isInitializing = false;
    this.initializationPromise = null;
    this.retryCount = 0;
    this.maxRetries = 3;
  }

  /**
   * 🚀 تهيئة الاتصال الموحدة
   */
  async initialize() {
    // ✅ منع التهيئة المتعددة
    if (this.isInitializing) {
      return this.initializationPromise;
    }

    this.isInitializing = true;
    this.initializationPromise = this._performInitialization();

    try {
      const result = await this.initializationPromise;
      this.isInitializing = false;
      return result;
    } catch (error) {
      this.isInitializing = false;
      throw error;
    }
  }

  /**
   * 🔄 تنفيذ التهيئة الفعلي
   */
  async _performInitialization() {
    console.log('🔄 Starting Unified Connection Initialization...');

    // ✅ الأولوية 1: Port Forwarding (USB) - الأفضل والأسرع
    // عند توصيل الجهاز عبر USB مع adb reverse، localhost يعمل مباشرة
    console.log('📍 Attempt 1: USB Port Forwarding (localhost:3002)');
    const portForwardingURL = 'http://localhost:3002';
    if (await this._testConnection(portForwardingURL)) {
      serverConfig.setConnection('usb_port_forwarding', portForwardingURL);
      console.log('✅ Connected via USB Port Forwarding');
      return {
        success: true,
        method: 'usb_port_forwarding',
        baseURL: portForwardingURL,
      };
    }

    // 🔄 تحديث IPs ديناميكياً
    console.log('🔄 Checking server config...');
    await serverConfig.initialize();
    const config = serverConfig.getConfig();
    console.log('📡 Current Config:', config.ip);

    // 2️⃣ محاولة الشبكة المحلية (WiFi)
    const backendURL = serverConfig.getBaseURL();
    console.log(`📍 Attempt 2: Local Network (${backendURL})`);
    if (await this._testConnection(backendURL)) {
      serverConfig.setConnection('local_network', backendURL);
      console.log('✅ Connected via Local Network');
      return {
        success: true,
        method: 'local_network',
        baseURL: backendURL,
      };
    }

    // 3️⃣ محاولة 10.0.2.2 (Android Emulator)
    console.log('📍 Attempt 3: Android Emulator (10.0.2.2:3002)');
    const emulatorURL = 'http://10.0.2.2:3002';
    if (await this._testConnection(emulatorURL)) {
      serverConfig.setConnection('android_emulator', emulatorURL);
      console.log('✅ Connected via Android Emulator');
      return {
        success: true,
        method: 'android_emulator',
        baseURL: emulatorURL,
      };
    }

    // 4️⃣ محاولة ngrok (للاختبار البعيد)
    console.log('📍 Attempt 4: ngrok Tunnel');
    const ngrokURL = await this._detectNgrokURL();
    if (ngrokURL && await this._testConnection(ngrokURL)) {
      serverConfig.setConnection('ngrok', ngrokURL);
      console.log('✅ Connected via ngrok');
      return {
        success: true,
        method: 'ngrok',
        baseURL: ngrokURL,
      };
    }

    // ❌ فشل جميع الطرق - لا fallback تلقائي
    Logger.error('All connection methods failed', 'UnifiedConnectionService');
    Logger.error('Troubleshooting:', 'UnifiedConnectionService');
    Logger.error('   1. تأكد من تشغيل Backend Server', 'UnifiedConnectionService');
    Logger.error('   2. للمحاكي: adb reverse tcp:3002 tcp:3002', 'UnifiedConnectionService');
    Logger.error('   3. للأجهزة: تأكد من نفس الشبكة WiFi', 'UnifiedConnectionService');

    serverConfig.setConnectionError(new Error('No connection method succeeded'));

    return {
      success: false,
      error: 'Cannot connect to server',
      message: 'Please ensure the backend server is running',
      troubleshooting: [
        'Check if backend is running on port 3002',
        'For emulator: Run adb reverse tcp:3002 tcp:3002',
        'For WiFi: Ensure same network connection',
      ],
    };
  }

  /**
   * 🧪 اختبار الاتصال بـ URL معين
   */
  async _testConnection(url, timeout = 2000) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(`${url}/api/system/status`, {
        method: 'GET',
        signal: controller.signal,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        console.log(`✅ Connection successful: ${url}`);
        return true;
      } else {
        console.log(`⚠️ Connection returned status ${response.status}: ${url}`);
        return false;
      }
    } catch (error) {
      console.log(`❌ Connection failed: ${url} - ${error.message}`);
      return false;
    }
  }

  /**
   * 🔍 الكشف عن ngrok URL
   */
  async _detectNgrokURL() {
    try {
      // محاولة الحصول على ngrok URL من API المحلي
      const response = await fetch('http://localhost:4040/api/tunnels', {
        timeout: 2000,
      });

      if (response.ok) {
        const data = await response.json();
        if (data.tunnels && data.tunnels.length > 0) {
          const ngrokURL = data.tunnels[0].public_url;
          console.log(`✅ Found ngrok URL: ${ngrokURL}`);
          return ngrokURL;
        }
      }
    } catch (error) {
      console.log('ℹ️ ngrok not available:', error.message);
    }
    return null;
  }

  /**
   * 🔗 الحصول على Base URL
   */
  getBaseURL() {
    return serverConfig.getBaseURL();
  }

  /**
   * 📊 الحصول على حالة الاتصال
   */
  getStatus() {
    return serverConfig.getConnectionInfo();
  }

  /**
   * 🔄 إعادة محاولة الاتصال
   */
  async retry() {
    if (this.retryCount < this.maxRetries) {
      this.retryCount++;
      console.log(`🔄 Retrying connection (${this.retryCount}/${this.maxRetries})...`);
      serverConfig.reset();
      return await this.initialize();
    } else {
      throw new Error('Max retries exceeded');
    }
  }

  /**
   * 🔄 إعادة تعيين
   */
  reset() {
    this.retryCount = 0;
    serverConfig.reset();
    console.log('🔄 Connection Service Reset');
  }
}

// ✅ Instance واحد مشترك
export const unifiedConnectionService = new UnifiedConnectionService();

export default unifiedConnectionService;
