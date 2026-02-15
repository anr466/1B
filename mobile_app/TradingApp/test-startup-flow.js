/**
 * 🧪 محاكاة فعلية لـ App Startup Flow
 * يحاكي تمامًا ما يحدث عند فتح التطبيق
 */

const axios = require('axios');

// ═══════════════════════════════════════════════════════════
// إعدادات
// ═══════════════════════════════════════════════════════════

const SERVER_URL = 'http://localhost:3002';
const TEST_USER = {
    username: 'admin',
    password: 'admin'
};

// ═══════════════════════════════════════════════════════════
// محاكاة AsyncStorage
// ═══════════════════════════════════════════════════════════

const mockStorage = {
    data: {},

    async getItem(key) {
        return this.data[key] || null;
    },

    async setItem(key, value) {
        this.data[key] = value;
    },

    async removeItem(key) {
        delete this.data[key];
    },

    async multiRemove(keys) {
        keys.forEach(key => delete this.data[key]);
    },

    clear() {
        this.data = {};
    },

    print() {
        console.log('📦 AsyncStorage:', Object.keys(this.data));
        Object.entries(this.data).forEach(([key, value]) => {
            const preview = typeof value === 'string' && value.length > 50
                ? value.substring(0, 50) + '...'
                : value;
            console.log(`  - ${key}: ${preview}`);
        });
    }
};

// ═══════════════════════════════════════════════════════════
// المساعدات
// ═══════════════════════════════════════════════════════════

function log(emoji, message, data = null) {
    console.log(`${emoji} ${message}`);
    if (data) {
        console.log(JSON.stringify(data, null, 2));
    }
}

function separator() {
    console.log('═'.repeat(70));
}

async function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ═══════════════════════════════════════════════════════════
// API Calls
// ═══════════════════════════════════════════════════════════

async function testConnection() {
    try {
        const response = await axios.get(`${SERVER_URL}/api/system/status`, {
            timeout: 5000
        });
        return {
            success: true,
            data: response.data
        };
    } catch (error) {
        return {
            success: false,
            error: error.message
        };
    }
}

async function login(username, password) {
    try {
        const response = await axios.post(`${SERVER_URL}/api/auth/login`, {
            username,
            password
        }, {
            headers: { 'Content-Type': 'application/json' }
        });
        return {
            success: true,
            data: response.data
        };
    } catch (error) {
        return {
            success: false,
            error: error.response?.data?.error || error.message
        };
    }
}

async function validateSession(token) {
    try {
        const response = await axios.get(`${SERVER_URL}/api/auth/validate-session`, {
            headers: {
                'Authorization': `Bearer ${token}`
            },
            timeout: 5000
        });
        return {
            success: true,
            data: response.data
        };
    } catch (error) {
        return {
            success: false,
            error: error.response?.data?.message || error.message
        };
    }
}

async function registerFCMToken(token, fcmToken) {
    try {
        const response = await axios.post(`${SERVER_URL}/api/user/fcm-token`, {
            fcm_token: fcmToken,
            platform: 'android'
        }, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        });
        return {
            success: true,
            data: response.data
        };
    } catch (error) {
        return {
            success: false,
            error: error.response?.data?.error || error.message
        };
    }
}

// ═══════════════════════════════════════════════════════════
// محاكاة initializeApp()
// ═══════════════════════════════════════════════════════════

async function initializeApp() {
    separator();
    log('🚀', 'بدء تهيئة التطبيق...');
    separator();

    let userData = null;
    let isUserLoggedIn = false;
    let nextScreen = 'login';

    try {
        // Phase 1: فحص الاتصال
        log('🔗', 'Phase 1: تهيئة الاتصال بالخادم...');
        const connectionResult = await testConnection();

        if (!connectionResult.success) {
            throw new Error(`فشل الاتصال: ${connectionResult.error}`);
        }

        log('✅', 'الاتصال ناجح', connectionResult.data);
        await delay(500);

        // Phase 2: قراءة البيانات المحفوظة
        log('📂', 'Phase 2: قراءة البيانات المحفوظة...');
        const savedToken = await mockStorage.getItem('authToken');
        const savedUser = await mockStorage.getItem('userData');
        const savedLoginState = await mockStorage.getItem('isLoggedIn');

        log('📦', `البيانات المحفوظة: token=${!!savedToken}, user=${!!savedUser}, isLoggedIn=${savedLoginState}`);

        if (savedUser && savedToken) {
            try {
                userData = JSON.parse(savedUser);
                log('✅', 'تم قراءة بيانات المستخدم المحفوظة');
            } catch (e) {
                log('❌', 'خطأ في تحليل userData');
                userData = null;
            }
        }
        await delay(500);

        // Phase 3: التحقق من Token (إذا وجد)
        if (savedToken && userData && savedLoginState === 'true') {
            log('🔍', 'Phase 3: التحقق من صلاحية Token...');
            const sessionResult = await validateSession(savedToken);

            if (sessionResult.success && sessionResult.data.success) {
                log('✅', 'الجلسة صالحة', sessionResult.data);
                isUserLoggedIn = true;
                nextScreen = 'main';

                // Phase 4: تسجيل FCM Token
                log('🔔', 'Phase 4: تسجيل FCM Token...');
                const fcmResult = await registerFCMToken(savedToken, 'test_fcm_token_startup');
                if (fcmResult.success) {
                    log('✅', 'تم تسجيل FCM Token', fcmResult.data);
                } else {
                    log('⚠️', 'فشل تسجيل FCM Token (اختياري)', fcmResult.error);
                }
            } else {
                log('❌', 'الجلسة منتهية - تنظيف البيانات');
                await mockStorage.multiRemove(['authToken', 'userData', 'isLoggedIn']);
                isUserLoggedIn = false;
                nextScreen = 'login';
            }
        } else {
            log('ℹ️', 'لا توجد بيانات محفوظة - عرض Login');
            nextScreen = 'login';
        }

        await delay(500);

        // النتيجة النهائية
        separator();
        log('✅', 'اكتملت تهيئة التطبيق بنجاح');
        separator();

        return {
            success: true,
            isUserLoggedIn,
            userData,
            nextScreen,
            message: 'تم تهيئة التطبيق بنجاح'
        };

    } catch (error) {
        separator();
        log('❌', 'فشلت تهيئة التطبيق', error.message);
        separator();

        return {
            success: false,
            error: error.message,
            nextScreen: 'login',
            message: 'فشل في تهيئة التطبيق'
        };
    }
}

// ═══════════════════════════════════════════════════════════
// السيناريوهات
// ═══════════════════════════════════════════════════════════

async function scenario1_FirstLaunch() {
    console.log('\n\n');
    separator();
    log('🎬', 'السيناريو 1: مستخدم جديد (First Launch)');
    separator();

    // تنظيف Storage
    mockStorage.clear();

    const result = await initializeApp();

    separator();
    log('📊', 'النتيجة النهائية:');
    console.log('  - nextScreen:', result.nextScreen);
    console.log('  - isUserLoggedIn:', result.isUserLoggedIn);
    console.log('  - userData:', result.userData ? 'موجود' : 'غير موجود');
    separator();

    if (result.nextScreen === 'login' && !result.isUserLoggedIn) {
        log('✅', 'السيناريو 1: ناجح - تم توجيه المستخدم لـ Login');
        return true;
    } else {
        log('❌', 'السيناريو 1: فشل - النتيجة غير متوقعة');
        return false;
    }
}

async function scenario2_LoginAndSaveSession() {
    console.log('\n\n');
    separator();
    log('🎬', 'السيناريو 2: تسجيل الدخول وحفظ الجلسة');
    separator();

    // تنظيف Storage
    mockStorage.clear();

    // محاكاة Login
    log('🔑', 'محاولة تسجيل الدخول...');
    const loginResult = await login(TEST_USER.username, TEST_USER.password);

    if (!loginResult.success) {
        log('❌', 'فشل تسجيل الدخول', loginResult.error);
        return false;
    }

    log('✅', 'نجح تسجيل الدخول');

    // حفظ في Storage (كما يفعل التطبيق)
    await mockStorage.setItem('authToken', loginResult.data.token);
    await mockStorage.setItem('userData', JSON.stringify(loginResult.data.user));
    await mockStorage.setItem('isLoggedIn', 'true');

    log('💾', 'تم حفظ البيانات في Storage');
    mockStorage.print();

    await delay(1000);

    // الآن محاكاة فتح التطبيق مرة أخرى
    log('🔄', 'محاكاة إعادة فتح التطبيق...');
    const result = await initializeApp();

    separator();
    log('📊', 'النتيجة النهائية:');
    console.log('  - nextScreen:', result.nextScreen);
    console.log('  - isUserLoggedIn:', result.isUserLoggedIn);
    console.log('  - userData:', result.userData ? 'موجود' : 'غير موجود');
    separator();

    if (result.nextScreen === 'main' && result.isUserLoggedIn) {
        log('✅', 'السيناريو 2: ناجح - تم توجيه المستخدم لـ Main');
        return true;
    } else {
        log('❌', 'السيناريو 2: فشل - النتيجة غير متوقعة');
        return false;
    }
}

async function scenario3_ExpiredToken() {
    console.log('\n\n');
    separator();
    log('🎬', 'السيناريو 3: Token منتهي');
    separator();

    // إعداد Storage مع token منتهي
    mockStorage.clear();
    await mockStorage.setItem('authToken', 'expired_or_invalid_token_12345');
    await mockStorage.setItem('userData', JSON.stringify({
        id: 999,
        username: 'test',
        email: 'test@test.com'
    }));
    await mockStorage.setItem('isLoggedIn', 'true');

    log('💾', 'تم إعداد Storage مع token منتهي');
    mockStorage.print();

    await delay(500);

    const result = await initializeApp();

    separator();
    log('📊', 'النتيجة النهائية:');
    console.log('  - nextScreen:', result.nextScreen);
    console.log('  - isUserLoggedIn:', result.isUserLoggedIn);
    console.log('  - userData:', result.userData ? 'موجود' : 'غير موجود');
    separator();

    // التحقق من تنظيف Storage
    const tokenAfter = await mockStorage.getItem('authToken');
    const userDataAfter = await mockStorage.getItem('userData');

    if (result.nextScreen === 'login' && !result.isUserLoggedIn && !tokenAfter && !userDataAfter) {
        log('✅', 'السيناريو 3: ناجح - تم تنظيف البيانات والتوجيه لـ Login');
        return true;
    } else {
        log('❌', 'السيناريو 3: فشل - النتيجة غير متوقعة');
        return false;
    }
}

// ═══════════════════════════════════════════════════════════
// التنفيذ الرئيسي
// ═══════════════════════════════════════════════════════════

async function main() {
    console.log('\n');
    separator();
    log('🧪', 'بدء اختبار App Startup Flow الفعلي');
    separator();

    const results = {
        scenario1: false,
        scenario2: false,
        scenario3: false
    };

    try {
        // السيناريو 1
        results.scenario1 = await scenario1_FirstLaunch();
        await delay(2000);

        // السيناريو 2
        results.scenario2 = await scenario2_LoginAndSaveSession();
        await delay(2000);

        // السيناريو 3
        results.scenario3 = await scenario3_ExpiredToken();

    } catch (error) {
        log('❌', 'خطأ في التنفيذ', error.message);
    }

    // النتائج النهائية
    console.log('\n\n');
    separator();
    log('📊', 'النتائج النهائية');
    separator();
    console.log('السيناريو 1 (First Launch):', results.scenario1 ? '✅ ناجح' : '❌ فاشل');
    console.log('السيناريو 2 (Login & Resume):', results.scenario2 ? '✅ ناجح' : '❌ فاشل');
    console.log('السيناريو 3 (Expired Token):', results.scenario3 ? '✅ ناجح' : '❌ فاشل');
    separator();

    const allPassed = results.scenario1 && results.scenario2 && results.scenario3;

    if (allPassed) {
        log('🎉', 'جميع السيناريوهات نجحت - التطبيق يعمل بشكل صحيح!');
    } else {
        log('⚠️', 'بعض السيناريوهات فشلت - يحتاج مراجعة');
    }

    separator();

    process.exit(allPassed ? 0 : 1);
}

// تشغيل
main().catch(error => {
    console.error('💥 خطأ حرج:', error);
    process.exit(1);
});
