/**
 * useAppState - Hook لاستخدام AppStateManager في الشاشات
 * ========================================================
 * يوفر واجهة سهلة للوصول لحالة التطبيق المركزية
 */

import { useState, useEffect, useCallback } from 'react';
import { appStateManager, AppEvents } from '../services/AppStateManager';

/**
 * Hook للاستماع لحالة الاتصال
 */
export const useConnectionStatus = () => {
    const [isConnected, setIsConnected] = useState(appStateManager.isConnected);

    useEffect(() => {
        const unsubscribe = appStateManager.on(AppEvents.CONNECTION_STATUS_CHANGED, (data) => {
            setIsConnected(data.isConnected);
        });

        return unsubscribe;
    }, []);

    return isConnected;
};

/**
 * Hook للاستماع لحالة النظام
 */
export const useSystemStatus = () => {
    const [systemStatus, setSystemStatus] = useState(appStateManager.systemStatus);

    useEffect(() => {
        const unsubscribe = appStateManager.on(AppEvents.SYSTEM_STATUS_CHANGED, (data) => {
            setSystemStatus(data);
        });

        return unsubscribe;
    }, []);

    return systemStatus;
};

/**
 * Hook للاستماع لوضع التداول
 */
export const useTradingMode = () => {
    const [tradingMode, setTradingMode] = useState(appStateManager.tradingMode);

    useEffect(() => {
        const unsubscribe = appStateManager.on(AppEvents.TRADING_MODE_CHANGED, (data) => {
            setTradingMode(data.mode);
        });

        return unsubscribe;
    }, []);

    return tradingMode;
};

/**
 * Hook لجلب البيانات مع إدارة الحالة
 */
export const useDataFetch = (fetchFunction, dependencies = []) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [refreshing, setRefreshing] = useState(false);

    const fetch = useCallback(async (forceRefresh = false) => {
        try {
            if (forceRefresh) {
                setRefreshing(true);
            } else {
                setLoading(true);
            }
            setError(null);

            const result = await fetchFunction(forceRefresh);
            setData(result);

        } catch (err) {
            setError(appStateManager.getUserErrorMessage(err));
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, [fetchFunction]);

    // جلب البيانات عند التحميل
    useEffect(() => {
        fetch(false);
    }, dependencies);

    // الاستماع لأحداث التحديث
    useEffect(() => {
        const unsubscribe = appStateManager.on(AppEvents.FORCE_REFRESH, () => {
            fetch(true);
        });

        return unsubscribe;
    }, [fetch]);

    const refresh = useCallback(() => fetch(true), [fetch]);

    return { data, loading, error, refreshing, refresh };
};

/**
 * Hook للمحفظة
 */
export const usePortfolio = () => {
    const { data, loading, error, refreshing, refresh } = useDataFetch(
        (forceRefresh) => appStateManager.fetchPortfolio(forceRefresh),
        [appStateManager.userId, appStateManager.tradingMode]
    );

    // الاستماع لتحديثات المحفظة
    useEffect(() => {
        const unsubscribe = appStateManager.on(AppEvents.PORTFOLIO_UPDATED, (newData) => {
            // البيانات ستتحدث تلقائياً من خلال useDataFetch
        });

        return unsubscribe;
    }, []);

    return { portfolio: data, loading, error, refreshing, refresh };
};

/**
 * Hook للإعدادات
 */
export const useSettings = () => {
    const { data, loading, error, refreshing, refresh } = useDataFetch(
        (forceRefresh) => appStateManager.fetchSettings(forceRefresh),
        [appStateManager.userId, appStateManager.tradingMode]
    );

    return { settings: data, loading, error, refreshing, refresh };
};

/**
 * Hook للإحصائيات
 */
export const useStats = () => {
    const { data, loading, error, refreshing, refresh } = useDataFetch(
        (forceRefresh) => appStateManager.fetchStats(forceRefresh),
        [appStateManager.userId, appStateManager.tradingMode]
    );

    return { stats: data, loading, error, refreshing, refresh };
};

/**
 * Hook للصفقات النشطة
 */
export const useActivePositions = () => {
    const { data, loading, error, refreshing, refresh } = useDataFetch(
        (forceRefresh) => appStateManager.fetchPositions(forceRefresh),
        [appStateManager.userId, appStateManager.tradingMode]
    );

    return { positions: data, loading, error, refreshing, refresh };
};

/**
 * Hook لإدارة العمليات
 */
export const useOperation = (operationId) => {
    const [isPending, setIsPending] = useState(appStateManager.isOperationPending(operationId));

    useEffect(() => {
        const onStarted = (data) => {
            if (data.operationId === operationId) {
                setIsPending(true);
            }
        };

        const onCompleted = (data) => {
            if (data.operationId === operationId) {
                setIsPending(false);
            }
        };

        const onFailed = (data) => {
            if (data.operationId === operationId) {
                setIsPending(false);
            }
        };

        const unsub1 = appStateManager.on(AppEvents.OPERATION_STARTED, onStarted);
        const unsub2 = appStateManager.on(AppEvents.OPERATION_COMPLETED, onCompleted);
        const unsub3 = appStateManager.on(AppEvents.OPERATION_FAILED, onFailed);

        return () => {
            unsub1();
            unsub2();
            unsub3();
        };
    }, [operationId]);

    const startOperation = useCallback(() => {
        appStateManager.startOperation(operationId);
    }, [operationId]);

    const completeOperation = useCallback((result) => {
        appStateManager.completeOperation(operationId, result);
    }, [operationId]);

    const failOperation = useCallback((error) => {
        appStateManager.failOperation(operationId, error);
    }, [operationId]);

    return { isPending, startOperation, completeOperation, failOperation };
};

/**
 * Hook شامل لحالة التطبيق
 */
export const useAppState = () => {
    const isConnected = useConnectionStatus();
    const systemStatus = useSystemStatus();
    const tradingMode = useTradingMode();

    return {
        isConnected,
        systemStatus,
        tradingMode,
        isAdmin: appStateManager.isAdmin,
        userId: appStateManager.userId,

        // دوال
        forceRefresh: () => appStateManager.forceRefreshAll(),
        invalidateCache: (key) => appStateManager.invalidateCache(key),
        updateConnectionStatus: (status) => appStateManager.updateConnectionStatus(status),
        updateSystemStatus: (status) => appStateManager.updateSystemStatus(status),
        updateTradingMode: (mode) => appStateManager.updateTradingMode(mode),
    };
};

export default useAppState;
