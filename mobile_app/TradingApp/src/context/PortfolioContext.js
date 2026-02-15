/**
 * Portfolio Context - إدارة بيانات المحفظة المركزية
 * ✅ يمنع تكرار استدعاءات API
 * ✅ Cache ذكي مع TTL
 * ✅ تحديث تلقائي كل 30 ثانية
 * ✅ مشاركة البيانات بين جميع الشاشات
 */

import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import DatabaseApiService from '../services/DatabaseApiService';
import Logger from '../services/LoggerService';
import { DeviceEventEmitter } from 'react-native';
import { isAdmin as checkIsAdmin, getSafeTradingMode } from '../utils/userUtils';
import { useTradingModeContext } from './TradingModeContext';

const PortfolioContext = createContext();

// Cache TTL بالمللي ثانية (60 ثانية)
const CACHE_TTL = 60000;

export const PortfolioProvider = ({ children }) => {
    // بيانات المستخدم
    const [userId, setUserId] = useState(null);
    const [isAdmin, setIsAdmin] = useState(false);

    // بيانات المحفظة - ✅ بدون بيانات افتراضية
    const [portfolio, setPortfolio] = useState(null);
    const [demoPortfolio, setDemoPortfolio] = useState(null);
    const [realPortfolio, setRealPortfolio] = useState(null);

    // حالة التحميل
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    // Cache timestamps
    const lastFetchRef = useRef({
        portfolio: 0,
        demo: 0,
        real: 0,
    });

    // ✅ FIX: Use refs for state accessed inside useCallback to prevent infinite loops
    const portfolioRef = useRef(null);
    const demoPortfolioRef = useRef(null);
    const realPortfolioRef = useRef(null);
    const fetchingRef = useRef(false);

    // استخدام TradingModeContext للحصول على الوضع الحالي
    const { getCurrentViewMode, refreshCounter } = useTradingModeContext();

    // تحميل بيانات المستخدم - فقط إذا كان token موجود
    const loadUserData = useCallback(async () => {
        try {
            const token = await AsyncStorage.getItem('authToken');
            if (!token) {
                setUserId(null);
                setIsAdmin(false);
                return null;
            }

            const userData = await AsyncStorage.getItem('userData');
            if (userData) {
                let user;
                try {
                    user = JSON.parse(userData);
                } catch (parseError) {
                    console.error('[PortfolioContext] فشل تحليل بيانات المستخدم:', parseError);
                    // ✅ محاولة مسح البيانات التالفة
                    try {
                        await AsyncStorage.removeItem('userData');
                    } catch (removeError) {
                        console.error('[PortfolioContext] فشل مسح البيانات التالفة:', removeError);
                    }
                    return null;
                }
                setUserId(user.id);
                // ✅ استخدام دالة isAdmin الموحدة
                setIsAdmin(checkIsAdmin(user));
                return user;
            }
        } catch (userError) {
            console.error('[PortfolioContext] Error loading user data:', userError);
        }
        return null;
    }, []);

    // فحص صلاحية Cache
    const isCacheValid = useCallback((type) => {
        const now = Date.now();
        return (now - lastFetchRef.current[type]) < CACHE_TTL;
    }, []);

    // ✅ FIX: Keep refs in sync with state
    useEffect(() => { portfolioRef.current = portfolio; }, [portfolio]);
    useEffect(() => { demoPortfolioRef.current = demoPortfolio; }, [demoPortfolio]);
    useEffect(() => { realPortfolioRef.current = realPortfolio; }, [realPortfolio]);

    // جلب المحفظة الرئيسية
    const fetchPortfolio = useCallback(async (forceRefresh = false) => {
        if (!userId) { return null; }

        if (!forceRefresh && isCacheValid('portfolio') && portfolioRef.current) {
            return portfolioRef.current;
        }

        try {
            setIsLoading(true);
            setError(null);

            // ✅ استخدام دالة getSafeTradingMode الموحدة
            let currentMode = getSafeTradingMode(getCurrentViewMode?.(), isAdmin);

            const response = await DatabaseApiService.getPortfolio(userId, currentMode);

            if (response?.success && response?.data) {
                setPortfolio(response.data);
                lastFetchRef.current.portfolio = Date.now();
                return response.data;
            }
        } catch (err) {
            console.error('[PortfolioContext] Error fetching portfolio:', err);
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
        return null;
    }, [userId, isCacheValid, getCurrentViewMode, isAdmin]);

    // جلب محفظة Demo
    const fetchDemoPortfolio = useCallback(async (forceRefresh = false) => {
        if (!userId || !isAdmin) { return null; }

        if (!forceRefresh && isCacheValid('demo') && demoPortfolioRef.current) {
            return demoPortfolioRef.current;
        }

        try {
            const response = await DatabaseApiService.getPortfolio(userId, 'demo');
            if (response?.success && response?.data) {
                setDemoPortfolio(response.data);
                lastFetchRef.current.demo = Date.now();
                return response.data;
            }
        } catch (err) {
            console.error('[PortfolioContext] Error fetching demo portfolio:', err);
        }
        return null;
    }, [userId, isAdmin, isCacheValid]);

    // جلب محفظة Real
    const fetchRealPortfolio = useCallback(async (forceRefresh = false) => {
        if (!userId || !isAdmin) { return null; }

        if (!forceRefresh && isCacheValid('real') && realPortfolioRef.current) {
            return realPortfolioRef.current;
        }

        try {
            const response = await DatabaseApiService.getPortfolio(userId, 'real');
            if (response?.success && response?.data) {
                setRealPortfolio(response.data);
                lastFetchRef.current.real = Date.now();
                return response.data;
            }
        } catch (err) {
            console.error('[PortfolioContext] Error fetching real portfolio:', err);
        }
        return null;
    }, [userId, isAdmin, isCacheValid]);

    // جلب جميع المحافظ (للأدمن)
    // ✅ FIX: Added fetchingRef guard to prevent concurrent fetches
    const fetchAllPortfolios = useCallback(async (forceRefresh = false) => {
        if (!userId) { return; }
        if (fetchingRef.current) { return; }
        fetchingRef.current = true;

        setIsLoading(true);
        try {
            // جلب المحفظة الرئيسية
            await fetchPortfolio(forceRefresh);

            // للأدمن: جلب Demo و Real
            if (isAdmin) {
                await Promise.all([
                    fetchDemoPortfolio(forceRefresh),
                    fetchRealPortfolio(forceRefresh),
                ]);
            }
        } finally {
            setIsLoading(false);
            fetchingRef.current = false;
        }
    }, [userId, isAdmin, fetchPortfolio, fetchDemoPortfolio, fetchRealPortfolio]);

    const refreshPortfolios = useCallback(async () => {
        lastFetchRef.current = { portfolio: 0, demo: 0, real: 0 };
        await fetchAllPortfolios(true);
    }, [fetchAllPortfolios]);

    // ✅ FIX: Listen for cache invalidation events from backend
    useEffect(() => {
        const { DeviceEventEmitter } = require('react-native');
        const subscription = DeviceEventEmitter.addListener('CACHE_INVALIDATE', (key) => {
            if (key === 'portfolio' || key === 'stats' || key === 'admin_dashboard') {
                // Force refresh on next fetch
                lastFetchRef.current.portfolio = 0;
                lastFetchRef.current.demo = 0;
                lastFetchRef.current.real = 0;

                // Auto-refresh if user is viewing
                if (userId) {
                    fetchAllPortfolios(true);
                }
            }
        });

        return () => subscription.remove();
    }, [userId, fetchAllPortfolios]);

    // تحميل البيانات عند البداية - ✅ FIX: run only once on mount
    useEffect(() => {
        loadUserData().then(user => {
            if (user) {
                fetchAllPortfolios(true);
            }
        });
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // ✅ الاستماع لـ refreshCounter من TradingModeContext (Central Auto-Refresh)
    // بدلاً من interval خاص - يتم التحكم مركزياً من TradingModeContext
    useEffect(() => {
        if (refreshCounter > 0 && userId) {
            refreshPortfolios();
        }
    }, [refreshCounter, userId, refreshPortfolios]);

    // تحديث userId عند تغيير المستخدم
    const updateUser = useCallback(async (newUserId, newIsAdmin = false) => {
        setUserId(newUserId);
        setIsAdmin(newIsAdmin);
        // مسح Cache عند تغيير المستخدم
        lastFetchRef.current = { portfolio: 0, demo: 0, real: 0 };
        setPortfolio(null);
        setDemoPortfolio(null);
        setRealPortfolio(null);
    }, []);

    const value = {
        // البيانات
        portfolio,
        demoPortfolio,
        realPortfolio,
        isLoading,
        error,
        userId,
        isAdmin,

        // الدوال
        fetchPortfolio,
        fetchDemoPortfolio,
        fetchRealPortfolio,
        fetchAllPortfolios,
        refreshPortfolios,
        updateUser,

        // معلومات Cache
        isCacheValid,
        lastFetch: lastFetchRef.current,
    };

    return (
        <PortfolioContext.Provider value={value}>
            {children}
        </PortfolioContext.Provider>
    );
};

// Hook للاستخدام
export const usePortfolioContext = () => {
    const context = useContext(PortfolioContext);
    if (!context) {
        throw new Error('usePortfolioContext must be used within a PortfolioProvider');
    }
    return context;
};

export default PortfolioContext;
