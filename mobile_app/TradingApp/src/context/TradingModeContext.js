/**
 * Trading Mode Context - إدارة وضع التداول المركزية
 * ✅ ينعكس على جميع الشاشات فوراً
 * ✅ يدعم الأدمن والمستخدم العادي
 * ✅ يُحدث البيانات عند تغيير الوضع
 * ✅ الأدمن يمكنه التبديل بين Demo/Real مع انعكاس كامل
 */

import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { AppState as RNAppState } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import DatabaseApiService from '../services/DatabaseApiService';
import Logger from '../services/LoggerService';
import { isAdmin as checkIsAdmin, getSafeTradingMode } from '../utils/userUtils';

const TradingModeContext = createContext();

export const TradingModeProvider = ({ children }) => {
    // بيانات المستخدم
    const [userId, setUserId] = useState(null);
    const [isAdmin, setIsAdmin] = useState(false);

    // وضع التداول
    const [tradingMode, setTradingMode] = useState('auto');
    const [hasBinanceKeys, setHasBinanceKeys] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    // ✅ حالة الاتصال المركزية - موحدة لجميع الشاشات
    const [isConnected, setIsConnected] = useState(true);
    const [lastConnectionCheck, setLastConnectionCheck] = useState(null);

    // عداد التحديث - يُستخدم لإجبار الشاشات على إعادة جلب البيانات
    const [refreshCounter, setRefreshCounter] = useState(0);

    // ✅ وضع العرض للأدمن (منفصل عن tradingMode الفعلي)
    // هذا يحدد أي بيانات تُعرض للأدمن دون تغيير الوضع الفعلي للتداول
    const [adminViewMode, setAdminViewMode] = useState(null); // null = يتبع tradingMode

    // ✅ مرجع لحالة التطبيق (background/foreground)
    const appStateRef = useRef(RNAppState.currentState);

    // ✅ Central Auto-Refresh Interval (واحد فقط للتطبيق كله)
    const centralRefreshRef = useRef(null);
    const CENTRAL_REFRESH_INTERVAL = 60000; // 60 ثانية - تحديث أقل توتراً

    // تحميل بيانات المستخدم من AsyncStorage
    const loadUserData = useCallback(async () => {
        try {
            const userData = await AsyncStorage.getItem('userData');
            if (userData) {
                let user;
                try {
                    user = JSON.parse(userData);
                } catch (parseError) {
                    console.error('[TradingModeContext] فشل تحليل بيانات المستخدم:', parseError);
                    // ✅ محاولة مسح البيانات التالفة
                    try {
                        await AsyncStorage.removeItem('userData');
                    } catch (removeError) {
                        console.error('[TradingModeContext] فشل مسح البيانات التالفة:', removeError);
                    }
                    return null;
                }
                setUserId(user.id);
                // ✅ استخدام دالة isAdmin الموحدة
                setIsAdmin(checkIsAdmin(user));
                return user;
            }
        } catch (error) {
            console.error('[TradingModeContext] Error loading user data:', error);
        }
        return null;
    }, []);

    // جلب وضع التداول من API
    const fetchTradingMode = useCallback(async (uid = null) => {
        const targetUserId = uid || userId;
        if (!targetUserId) return;

        // ✅ التحقق من وجود token قبل استدعاء API
        const token = await AsyncStorage.getItem('authToken');
        if (!token) return;

        setIsLoading(true);
        try {
            // ✅ التأكد من تهيئة الخدمة أولاً
            await DatabaseApiService.initialize();

            const response = await DatabaseApiService.getSettings(targetUserId);

            if (response?.success || response?.data) {
                const data = response.data || response;
                const mode = data.tradingMode || data.trading_mode || 'auto';
                const hasKeys = data.hasBinanceKeys || data.has_binance_keys || false;

                setTradingMode(mode);
                setHasBinanceKeys(hasKeys);
            }
        } catch (error) {
            console.error('[TradingModeContext] Error fetching trading mode:', error);
        } finally {
            setIsLoading(false);
        }
    }, [userId]);

    const changeTradingMode = useCallback(async (newMode) => {
        if (!userId || !isAdmin) {
            return { success: false, error: 'غير مصرح' };
        }

        // التحقق من المفاتيح إذا كان الوضع real
        if (newMode === 'real' && !hasBinanceKeys) {
            return { success: false, error: 'يجب إضافة مفاتيح Binance أولاً' };
        }

        setIsLoading(true);
        try {
            const response = await DatabaseApiService.updateTradingMode(userId, newMode);

            if (response?.success) {
                setTradingMode(newMode);
                setAdminViewMode(newMode);
                setRefreshCounter(prev => prev + 1);
                return { success: true };
            } else {
                return { success: false, error: response?.error || 'فشل التحديث' };
            }
        } catch (error) {
            console.error('[TradingModeContext] Error changing trading mode:', error);
            return { success: false, error: error.message };
        } finally {
            setIsLoading(false);
        }
    }, [userId, isAdmin, hasBinanceKeys]);

    const switchAdminViewMode = useCallback((mode) => {
        if (!isAdmin) return;

        setAdminViewMode(mode);
        setRefreshCounter(prev => prev + 1);
    }, [isAdmin]);

    // تحديث حالة المفاتيح
    const updateKeysStatus = useCallback((hasKeys) => {
        setHasBinanceKeys(hasKeys);
    }, []);

    // ✅ فحص الاتصال المركزي
    const checkConnection = useCallback(async () => {
        try {
            // ✅ استخدام checkConnection الموجودة في DatabaseApiService
            const connected = await DatabaseApiService.checkConnection();

            setIsConnected(connected);
            setLastConnectionCheck(new Date());

            return connected;
        } catch (error) {
            setIsConnected(false);
            setLastConnectionCheck(new Date());
            return false;
        }
    }, []);

    // ✅ تحديث حالة الاتصال يدوياً (من الشاشات)
    const updateConnectionStatus = useCallback((connected) => {
        setIsConnected(connected);
        setLastConnectionCheck(new Date());
    }, []);

    const initializeUser = useCallback(async (user) => {
        if (user) {
            setUserId(user.id);
            const isAdminUser = checkIsAdmin(user);
            setIsAdmin(isAdminUser);

            // ✅ إضافة تأخير صغير للتأكد من أن PortfolioContext جاهز
            setTimeout(() => {
                fetchTradingMode(user.id);
            }, 100);
        }
    }, [fetchTradingMode]);

    const clearUserData = useCallback(async () => {
        setUserId(null);
        setIsAdmin(false);
        setTradingMode('auto');
        setHasBinanceKeys(false);
        setRefreshCounter(0);
        setAdminViewMode(null);

        // مسح كامل من AsyncStorage
        try {
            // ✅ جلب userId قبل المسح لحذف trading_settings
            const userData = await AsyncStorage.getItem('userData');
            let userIdToRemove = null;
            if (userData) {
                try {
                    const user = JSON.parse(userData);
                    userIdToRemove = user.id;
                } catch (e) { }
            }

            // ✅ قائمة المفاتيح الأساسية
            const keysToRemove = [
                'authToken',
                'refreshToken',
                'userData',
                'lastUserId',
                'isLoggedIn'
            ];

            // ✅ إضافة trading_settings إذا كان userId موجود
            if (userIdToRemove) {
                keysToRemove.push(`trading_settings_${userIdToRemove}`);
            }

            await AsyncStorage.multiRemove(keysToRemove);
        } catch (error) {
            // صامت
        }
    }, []);

    // دوال مساعدة للعرض
    const getModeText = useCallback(() => {
        if (tradingMode === 'real') return '✅ حقيقي (Real)';
        if (tradingMode === 'demo') return '🔄 وهمي (Demo)';
        return '🔄 تلقائي (Auto)';
    }, [tradingMode]);

    const getModeDescription = useCallback(() => {
        if (tradingMode === 'real') {
            return 'البيانات والصفقات حقيقية من Binance';
        }
        if (tradingMode === 'demo') {
            return 'محفظة اختبارية - أموال وهمية للتعلم';
        }
        return hasBinanceKeys ? 'تداول حقيقي (تلقائي)' : 'يرجى ربط مفاتيح Binance';
    }, [tradingMode, hasBinanceKeys]);

    const getModeColor = useCallback(() => {
        if (tradingMode === 'real') return '#10B981'; // أخضر
        if (tradingMode === 'demo') return '#3B82F6'; // أزرق للأدمن
        return hasBinanceKeys ? '#10B981' : '#EF4444'; // أحمر إذا لا توجد مفاتيح
    }, [tradingMode, hasBinanceKeys]);

    // تحديد الوضع الفعلي (للاستخدام في API calls)
    // ✅ الأدمن يختار محفظة واحدة فقط (Demo أو Real)
    const getEffectiveMode = useCallback(() => {
        if (isAdmin) {
            // ✅ الأدمن: يختار محفظة واحدة فقط
            if (tradingMode === 'auto') {
                return hasBinanceKeys ? 'real' : 'demo';
            }
            // ✅ استخدام دالة getSafeTradingMode للأمان
            return getSafeTradingMode(tradingMode, true); // isAdmin = true
        }
        // المستخدم العادي: real فقط (لا يظهر له أبداً Demo)
        return 'real';
    }, [isAdmin, tradingMode, hasBinanceKeys]);

    // ✅ الحصول على وضع العرض الحالي (يُستخدم في جلب البيانات)
    // ✅ إخفاء كامل لـ Demo من المستخدمين العاديين
    const getCurrentViewMode = useCallback(() => {
        if (isAdmin) {
            // الأدمن: يرى وضعه الفعلي
            if (adminViewMode) {
                return adminViewMode;
            }
            if (tradingMode === 'auto') {
                return hasBinanceKeys ? 'real' : 'demo';
            }
            return tradingMode;
        }
        // المستخدم العادي: دائماً real فقط
        // لا يظهر أبداً 'demo' للمستخدمين العاديين
        return 'real';
    }, [isAdmin, adminViewMode, tradingMode, hasBinanceKeys]);

    // تحميل البيانات عند بدء التطبيق
    useEffect(() => {
        loadUserData().then(user => {
            if (user) {
                fetchTradingMode(user.id);
            }
        });
    }, [loadUserData, fetchTradingMode]);

    // ✅ Central Auto-Refresh - interval واحد مركزي لكل التطبيق
    useEffect(() => {
        const startCentralRefresh = async () => {
            // إيقاف أي interval سابق
            if (centralRefreshRef.current) {
                clearInterval(centralRefreshRef.current);
                centralRefreshRef.current = null;
            }

            // لا نبدأ إلا إذا كان المستخدم مسجل دخول
            const token = await AsyncStorage.getItem('authToken');
            if (!userId || !token) return;

            centralRefreshRef.current = setInterval(async () => {
                const currentToken = await AsyncStorage.getItem('authToken');
                if (!currentToken || !userId) {
                    if (centralRefreshRef.current) {
                        clearInterval(centralRefreshRef.current);
                        centralRefreshRef.current = null;
                    }
                    return;
                }
                // ✅ زيادة عداد التحديث - جميع الشاشات تستمع لهذا
                setRefreshCounter(prev => prev + 1);
            }, CENTRAL_REFRESH_INTERVAL);
        };

        startCentralRefresh();

        return () => {
            if (centralRefreshRef.current) {
                clearInterval(centralRefreshRef.current);
                centralRefreshRef.current = null;
            }
        };
    }, [userId]);

    // ✅ الاستماع لتغييرات حالة التطبيق (background/foreground)
    useEffect(() => {
        const handleAppStateChange = async (nextAppState) => {
            const previousState = appStateRef.current;
            appStateRef.current = nextAppState;

            // عند العودة من الخلفية للمقدمة - تحديث البيانات
            if (previousState.match(/inactive|background/) && nextAppState === 'active') {
                if (userId) {
                    fetchTradingMode(userId);
                    setRefreshCounter(prev => prev + 1);
                }
            }
        };

        const appStateSubscription = RNAppState.addEventListener('change', handleAppStateChange);

        return () => {
            appStateSubscription?.remove();
        };
    }, [userId, fetchTradingMode]);

    const value = {
        // البيانات
        userId,
        isAdmin,
        tradingMode,
        hasBinanceKeys,
        isLoading,
        refreshCounter,
        adminViewMode,

        // ✅ حالة الاتصال المركزية
        isConnected,
        lastConnectionCheck,

        // الدوال
        initializeUser,
        fetchTradingMode,
        changeTradingMode,
        switchAdminViewMode,
        getCurrentViewMode,
        updateKeysStatus,
        clearUserData,

        // ✅ دوال الاتصال
        checkConnection,
        updateConnectionStatus,

        // دوال العرض
        getModeText,
        getModeDescription,
        getModeColor,
        getEffectiveMode,
    };

    return (
        <TradingModeContext.Provider value={value}>
            {children}
        </TradingModeContext.Provider>
    );
};

// Hook للوصول إلى TradingModeContext
export const useTradingModeContext = () => {
    const context = useContext(TradingModeContext);
    if (!context) {
        throw new Error('useTradingModeContext must be used within TradingModeProvider');
    }
    return context;
};

export default TradingModeContext;
