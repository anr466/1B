/**
 * Admin Dashboard - لوحة تحكم الأدمن المُبسطة
 * ============================================
 * ✅ تحكم موحد في النظام الخلفي (Group B + ML)
 * ✅ عرض حالة الأنظمة الفرعية (للمراقبة فقط)
 * ✅ سجل الأخطاء الحقيقي من Backend
 * ✅ إعادة ضبط Demo
 *
 * ⚠️ ملاحظة مهمة:
 * - النظام الخلفي واحد يدير كل شيء
 * - لا يوجد تحكم منفصل في Group B
 * - الأنظمة الفرعية للعرض فقط
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
    View,
    Text,
    ScrollView,
    TouchableOpacity,
    RefreshControl,
    StyleSheet,
    DeviceEventEmitter,
    ActivityIndicator,
} from 'react-native';
import { theme } from '../theme/theme';
import ModernCard from '../components/ModernCard';
import { useBackHandler } from '../utils/BackHandlerUtil';
import ToastService from '../services/ToastService';
import DatabaseApiService from '../services/DatabaseApiService';
import { AlertService } from '../components/CustomAlert';
import { useTradingModeContext } from '../context/TradingModeContext';
import { appStateManager, AppEvents } from '../services/AppStateManager';
import { AdminDashboardSkeleton } from '../components/SkeletonLoader';
import { hapticWarning, hapticError, hapticSuccess } from '../utils/HapticFeedback';
import { useIsAdmin } from '../hooks/useIsAdmin';

const AdminDashboard = ({ onBack, navigation, user }) => {
    // ==================== التحقق من الصلاحيات ====================
    const isAdmin = useIsAdmin(user);

    const {
        isConnected: contextIsConnected,
        updateConnectionStatus,
    } = useTradingModeContext();

    // ==================== State ====================
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [lastUpdated, setLastUpdated] = useState(null);
    const isMountedRef = useRef(true);
    const isServerConnected = contextIsConnected;

    // ✅ حالة نظام التداول — المصدر الوحيد للحقيقة هو Backend
    // trading_state: STOPPED | STARTING | RUNNING | STOPPING | ERROR
    const [tradingState, setTradingState] = useState({
        trading_state: 'STOPPED',
        trading_state_label: 'متوقف',
        session_id: null,
        mode: 'PAPER',
        open_positions: 0,
        pid: null,
        uptime: 0,
        uptime_formatted: null,
        started_at: null,
        message: '',
        subsystems: {},
    });

    // ✅ حالة الأنظمة الفرعية (للعرض فقط)
    const [subsystems, setSubsystems] = useState({
        groupB: { active_trades: 0, monitored_coins: 0, last_cycle: null },
        ml: { is_ready: false, progress_pct: 0, total_samples: 0, required_samples: 500 },
    });

    // ✅ حالة نظام التعلم التكيّفي
    const [learningStatus, setLearningStatus] = useState({
        verdict: null,          // LEARNING_EFFECTIVE | MARGINAL | HARMFUL | NEUTRAL
        accuracy: 0,
        baseline: 0,
        lift: 0,
        trend: 'unknown',      // improving | stable | declining
        totalTrades: 0,
        withIndicators: 0,
        winRate: 0,
        avgPnl: 0,
        blockedSymbols: 0,
        validatedAt: null,
    });

    // ✅ سجل الأخطاء
    const [errors, setErrors] = useState({
        count: 0,
        critical_count: 0,
        recent: [],
    });

    // ✅ حالة التحميل للأزرار (فقط resetDemo و userManagement — النظام يستخدم trading_state)
    const [actionLoading, setActionLoading] = useState({
        resetDemo: false,
        userManagement: false,
    });

    // ✅ بيانات المستخدمين
    const [users, setUsers] = useState({
        count: 0,
        active: 0,
        list: [],
    });

    useBackHandler(() => { onBack && onBack(); });

    // ==================== جلب حالة التداول (State Machine) ====================
    const fetchTradingState = useCallback(async () => {
        if (!isMountedRef.current || !isAdmin) { return; }
        try {
            const response = await DatabaseApiService.getTradingState?.();
            if (isMountedRef.current && response) {
                setTradingState({
                    trading_state: response.trading_state || 'STOPPED',
                    trading_state_label: response.trading_state_label || 'متوقف',
                    session_id: response.session_id || null,
                    mode: response.mode || 'PAPER',
                    open_positions: response.open_positions || 0,
                    pid: response.pid || null,
                    uptime: response.uptime || 0,
                    uptime_formatted: response.uptime_formatted || null,
                    started_at: response.started_at || null,
                    message: response.message || '',
                    subsystems: response.subsystems || {},
                });

                const groupBState = response.subsystems?.group_b || {};
                setSubsystems(prev => ({
                    ...prev,
                    groupB: {
                        active_trades: groupBState.active_trades || response.open_positions || 0,
                        monitored_coins: groupBState.total_cycles || 0,
                        last_cycle: groupBState.last_activity || null,
                    },
                }));

                updateConnectionStatus(true);
                // Sync with appStateManager
                appStateManager.updateSystemStatus({
                    is_running: response.trading_state === 'RUNNING',
                    status: (response.trading_state || 'STOPPED').toLowerCase(),
                });
            }
        } catch (e) {
            console.log('[AdminDashboard] Trading state error:', e.message);
            updateConnectionStatus(false);
        }
    }, [isAdmin, updateConnectionStatus]);

    // ==================== جلب البيانات الإضافية ====================
    const fetchAllData = useCallback(async (silent = false) => {
        if (!isMountedRef.current || !isAdmin) { return; }

        try {
            if (!silent) { setLoading(true); }

            // 1️⃣ جلب حالة التداول (State Machine - المصدر الوحيد للحقيقة)
            await fetchTradingState();

            // 2️⃣ جلب حالة الأنظمة الفرعية (للعرض فقط)
            try {
                const mlResponse = await DatabaseApiService.getSystemMLStatus?.('demo');
                if (isMountedRef.current && mlResponse?.success) {
                    setSubsystems(prev => ({
                        ...prev,
                        ml: {
                            is_ready: mlResponse.ml?.is_ready || false,
                            progress_pct: mlResponse.ml?.progress_pct || 0,
                            total_samples: mlResponse.ml?.total_samples || 0,
                            required_samples: mlResponse.ml?.required_samples || 500,
                        },
                        groupB: {
                            ...prev.groupB,
                            active_trades: mlResponse.active_positions?.length || 0,
                        },
                    }));
                }
            } catch (e) {
                console.log('[AdminDashboard] ML status error:', e.message);
            }

            // 3️⃣ جلب الأخطاء
            try {
                const errorsRes = await DatabaseApiService.getBackgroundErrors?.(5);
                if (isMountedRef.current && errorsRes?.success) {
                    setErrors({
                        count: errorsRes.count || 0,
                        critical_count: errorsRes.errors?.filter(e => e.level === 'critical')?.length || 0,
                        recent: errorsRes.errors?.slice(0, 3) || [],
                    });
                }
            } catch (e) {
                console.log('[AdminDashboard] Errors fetch error:', e.message);
            }

            // 4️⃣ جلب بيانات المستخدمين
            try {
                const usersRes = await DatabaseApiService.getAllUsers();
                if (isMountedRef.current && usersRes?.success) {
                    const usersData = usersRes.users || [];
                    setUsers({
                        count: usersRes.total || usersData.length,
                        active: usersData.filter(u => u.is_active).length,
                        list: usersData.slice(0, 10), // عرض أول 10 مستخدمين فقط
                    });
                }
            } catch (e) {
                console.log('[AdminDashboard] Users fetch error:', e.message);
            }

            // 5️⃣ جلب حالة نظام التعلم التكيّفي
            try {
                const learningRes = await DatabaseApiService.getLearningStatus?.();
                if (isMountedRef.current && learningRes?.success) {
                    const lv = learningRes.last_validation;
                    const lr = learningRes.learning || {};
                    setLearningStatus({
                        verdict: lv?.verdict || null,
                        accuracy: lv?.accuracy || 0,
                        baseline: lv?.baseline || 0,
                        lift: lv?.lift || 0,
                        trend: learningRes.trend || 'unknown',
                        totalTrades: lr.total_trades || 0,
                        withIndicators: lr.trades_with_indicators || 0,
                        winRate: lr.overall_win_rate || 0,
                        avgPnl: lr.avg_pnl_pct || 0,
                        blockedSymbols: lr.blocked_symbols || 0,
                        validatedAt: lv?.validated_at || null,
                    });
                }
            } catch (e) {
                console.log('[AdminDashboard] Learning status error:', e.message);
            }

            if (isMountedRef.current) {
                setLastUpdated(new Date());
            }

        } catch (err) {
            if (isMountedRef.current) {
                hapticError();
                updateConnectionStatus(false);
            }
        } finally {
            if (isMountedRef.current) {
                setLoading(false);
                setRefreshing(false);
            }
        }
    }, [isAdmin, updateConnectionStatus, fetchTradingState]);

    // ==================== Effects ====================
    useEffect(() => {
        if (!isAdmin) {
            ToastService.showError('الوصول مرفوض - هذه الصفحة للأدمن فقط');
            navigation?.navigate('Dashboard');
        }
    }, [isAdmin, navigation]);

    useEffect(() => {
        isMountedRef.current = true;
        if (!isAdmin) { return; }

        fetchAllData();

        // ✅ Polling حالة التداول كل 5 ثواني (سريع لأنه endpoint خفيف)
        const tradingStateInterval = setInterval(() => {
            if (isMountedRef.current) { fetchTradingState(); }
        }, 5000);

        // Polling البيانات الإضافية كل 15 ثانية
        const dataInterval = setInterval(() => {
            if (isMountedRef.current) { fetchAllData(true); }
        }, 15000);

        const resumeListener = DeviceEventEmitter.addListener('APP_RESUMED_FROM_BACKGROUND', () => {
            if (isMountedRef.current) { fetchTradingState(); fetchAllData(true); }
        });

        return () => {
            isMountedRef.current = false;
            clearInterval(tradingStateInterval);
            clearInterval(dataInterval);
            resumeListener.remove();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [isAdmin]); // ✅ فقط عند تغيير صلاحيات الأدمن

    // ==================== Actions (State Machine Driven) ====================

    /**
     * تشغيل/إيقاف النظام — يستخدم State Machine API
     * ❌ لا يوجد Optimistic Update
     * ✅ الأزرار معطلة أثناء STARTING/STOPPING
     * ✅ الحالة تتحدث عبر Polling من الخادم فقط
     */
    const handleStartSystem = async () => {
        if (tradingState.trading_state !== 'STOPPED' && tradingState.trading_state !== 'ERROR') { return; }
        if (!isServerConnected) { ToastService.showError('لا يوجد اتصال بالخادم'); return; }
        AlertService.warning(
            'تشغيل نظام التداول',
            '✅ سيتم تشغيل نظام التداول بالكامل:\n• المجموعة B (التداول الآلي)\n• نظام التعلم الآلي\n\nهل تريد المتابعة؟',
            [
                { text: 'إلغاء', style: 'cancel' },
                {
                    text: 'تشغيل',
                    onPress: async () => {
                        console.log('[StateMachine] Start requested');
                        const result = await DatabaseApiService.startTradingSystem?.('PAPER');
                        console.log('[StateMachine] Start result:', result?.trading_state);

                        if (isMountedRef.current && result) {
                            setTradingState(prev => ({ ...prev, ...result }));
                            if (result.trading_state === 'RUNNING') {
                                hapticSuccess();
                                ToastService.showSuccess(`✅ تم تشغيل النظام (PID: ${result.pid})`);
                            } else if (result.trading_state === 'STARTING') {
                                ToastService.showInfo('⏳ جاري تشغيل النظام...');
                            } else if (result.trading_state === 'ERROR') {
                                hapticError();
                                ToastService.showError(result.message || 'فشل التشغيل');
                            }
                        }
                    },
                },
            ]
        );
    };

    const handleStopSystem = async () => {
        if (tradingState.trading_state !== 'RUNNING') { return; }
        if (!isServerConnected) { ToastService.showError('لا يوجد اتصال بالخادم'); return; }

        const posWarning = tradingState.open_positions > 0
            ? `\n\n⚠️ يوجد ${tradingState.open_positions} صفقة مفتوحة تحتاج مراقبة يدوية`
            : '';

        AlertService.warning(
            'إيقاف نظام التداول',
            `⚠️ سيتم إيقاف نظام التداول بالكامل.${posWarning}\n\nهل أنت متأكد؟`,
            [
                { text: 'إلغاء', style: 'cancel' },
                {
                    text: 'إيقاف',
                    style: 'destructive',
                    onPress: async () => {
                        console.log('[StateMachine] Stop requested');
                        const result = await DatabaseApiService.stopTradingSystem?.();
                        console.log('[StateMachine] Stop result:', result?.trading_state);

                        if (isMountedRef.current && result) {
                            setTradingState(prev => ({ ...prev, ...result }));
                            if (result.trading_state === 'STOPPED') {
                                hapticSuccess();
                                ToastService.showSuccess('✅ تم إيقاف النظام بنجاح');
                            } else if (result.trading_state === 'STOPPING') {
                                ToastService.showInfo('⏳ جاري إيقاف النظام...');
                            }
                        }
                    },
                },
            ]
        );
    };

    // ✅ إيقاف الطوارئ — State Machine
    const handleEmergencyStop = async () => {
        AlertService.warning(
            '🚨 إيقاف الطوارئ',
            'سيتم إيقاف النظام بالقوة فوراً!\n\n⚠️ هذا الإجراء لا يمكن التراجع عنه.',
            [
                { text: 'إلغاء', style: 'cancel' },
                {
                    text: '🚨 إيقاف فوري',
                    style: 'destructive',
                    onPress: async () => {
                        const result = await DatabaseApiService.emergencyStopTradingSystem?.();
                        if (isMountedRef.current && result) {
                            setTradingState(prev => ({ ...prev, ...result }));
                            hapticWarning();
                            ToastService.showSuccess('🚨 تم إيقاف الطوارئ');
                        }
                    },
                },
            ]
        );
    };

    // ✅ إعادة تعيين من حالة ERROR
    const handleResetError = async () => {
        const result = await DatabaseApiService.resetTradingError?.();
        if (isMountedRef.current && result) {
            setTradingState(prev => ({ ...prev, ...result }));
            if (result.trading_state === 'STOPPED') {
                ToastService.showSuccess('✅ تم إعادة التعيين');
            }
        }
    };

    // ✅ إعادة ضبط Demo
    const handleResetDemo = async () => {
        // منع الضغط المتكرر
        if (actionLoading.resetDemo) { return; }

        AlertService.warning(
            '🔄 إعادة ضبط الحساب التجريبي',
            'سيتم حذف جميع الصفقات وإعادة الرصيد إلى $1,000.\n\nهل أنت متأكد؟',
            [
                { text: 'إلغاء', style: 'cancel' },
                {
                    text: 'إعادة ضبط',
                    style: 'destructive',
                    onPress: async () => {
                        try {
                            setActionLoading(prev => ({ ...prev, resetDemo: true }));
                            const response = await DatabaseApiService.resetDemoAccount?.();

                            if (response?.success) {
                                hapticSuccess();
                                ToastService.showSuccess('تم إعادة ضبط الحساب بنجاح');
                                await fetchAllData(true);
                            } else {
                                hapticError();
                                ToastService.showError(response?.error || 'فشل إعادة الضبط');
                            }
                        } catch (e) {
                            hapticError();
                            ToastService.showError('فشل الاتصال');
                        } finally {
                            setActionLoading(prev => ({ ...prev, resetDemo: false }));
                        }
                    },
                },
            ]
        );
    };

    // ==================== Helpers ====================
    const formatSecondsAgo = (seconds) => {
        if (seconds === null || seconds === undefined) { return 'غير متاح'; }
        if (seconds < 60) { return `منذ ${seconds} ثانية`; }
        const minutes = Math.floor(seconds / 60);
        if (minutes < 60) { return `منذ ${minutes} دقيقة`; }
        const hours = Math.floor(minutes / 60);
        if (hours < 24) { return `منذ ${hours} ساعة`; }
        const days = Math.floor(hours / 24);
        return `منذ ${days} يوم`;
    };

    const formatUptime = (seconds) => {
        if (!seconds || seconds === 0) { return 'غير متاح'; }
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        if (days > 0) { return `${days} يوم ${hours} ساعة`; }
        if (hours > 0) { return `${hours} ساعة ${minutes} دقيقة`; }
        if (minutes > 0) { return `${minutes} دقيقة`; }
        return `${seconds} ثانية`;
    };

    const formatTime = (dateString) => {
        if (!dateString) { return 'غير متاح'; }
        try {
            return new Date(dateString).toLocaleTimeString('ar-SA');
        } catch {
            return 'غير متاح';
        }
    };

    const renderStatItem = (label, value, color = theme.colors.text) => (
        <View style={styles.statItem}>
            <Text style={styles.statLabel}>{label}</Text>
            <Text style={[styles.statValue, { color }]}>{value}</Text>
        </View>
    );

    // ==================== Render ====================
    if (!isAdmin) { return null; }
    if (loading && !refreshing) { return <View style={styles.container}><AdminDashboardSkeleton /></View>; }

    // ✅ حالات مشتقة من trading_state (المصدر الوحيد)
    const ts = tradingState.trading_state;
    const isSystemRunning = ts === 'RUNNING';
    const isTransitioning = ts === 'STARTING' || ts === 'STOPPING';
    const isError = ts === 'ERROR';
    const canStart = ts === 'STOPPED' || ts === 'ERROR';
    const canStop = ts === 'RUNNING';
    const mlProgress = subsystems.ml.progress_pct || 0;

    return (
        <View style={styles.container}>
            <ScrollView
                style={styles.content}
                refreshControl={
                    <RefreshControl
                        refreshing={refreshing}
                        onRefresh={() => { setRefreshing(true); fetchAllData(); }}
                        tintColor={theme.colors.primary}
                    />
                }
                showsVerticalScrollIndicator={false}
            >
                {/* ═══════════════ شريط الحالة الموحد ═══════════════ */}
                <View style={styles.statusBar}>
                    <View style={styles.statusBarItem}>
                        <View style={[styles.statusDot, { backgroundColor: isServerConnected ? theme.colors.success : theme.colors.error }]} />
                        <Text style={styles.statusBarLabel}>الخادم:</Text>
                        <Text style={[styles.statusBarValue, { color: isServerConnected ? theme.colors.success : theme.colors.error }]}>
                            {isServerConnected ? 'متصل' : 'غير متصل'}
                        </Text>
                    </View>
                    <View style={styles.statusBarDivider} />
                    <View style={styles.statusBarItem}>
                        <View style={[styles.statusDot, { backgroundColor: isSystemRunning ? theme.colors.success : theme.colors.error }]} />
                        <Text style={styles.statusBarLabel}>النظام:</Text>
                        <Text style={[styles.statusBarValue, { color: isSystemRunning ? theme.colors.success : theme.colors.error }]}>
                            {isSystemRunning ? 'يعمل' : 'متوقف'}
                        </Text>
                    </View>
                    {lastUpdated && (
                        <>
                            <View style={styles.statusBarDivider} />
                            <Text style={styles.lastUpdateText}>{lastUpdated.toLocaleTimeString('ar-SA')}</Text>
                        </>
                    )}
                </View>

                {/* تحذير عدم الاتصال */}
                {!isServerConnected && (
                    <ModernCard variant="warning" style={styles.card}>
                        <Text style={styles.warningTitle}>⚠️ فقد الاتصال بالخادم</Text>
                        <Text style={styles.warningText}>البيانات المعروضة قد تكون قديمة</Text>
                        <TouchableOpacity style={styles.retryButton} onPress={() => fetchAllData()}>
                            <Text style={styles.retryButtonText}>🔄 إعادة الاتصال</Text>
                        </TouchableOpacity>
                    </ModernCard>
                )}

                {/* ═══════════════ 1. نظام التداول (State Machine) ═══════════════ */}
                <ModernCard style={styles.card}>
                    <View style={styles.cardHeader}>
                        <Text style={styles.cardTitle}>🖥️ نظام التداول</Text>
                        {/* شارة الحالة — تعكس trading_state من الخادم فقط */}
                        <View style={[styles.statusBadge, {
                            backgroundColor: (
                                isSystemRunning ? theme.colors.success :
                                    isTransitioning ? theme.colors.warning :
                                        isError ? theme.colors.error :
                                            theme.colors.error
                            ) + '20',
                        }]}>
                            {isTransitioning ? (
                                <ActivityIndicator size={10} color={theme.colors.warning} style={{ marginRight: 6 }} />
                            ) : (
                                <View style={[styles.statusDot, {
                                    backgroundColor: isSystemRunning ? theme.colors.success :
                                        isError ? theme.colors.error : theme.colors.error
                                }]} />
                            )}
                            <Text style={[styles.statusText, {
                                color: isSystemRunning ? theme.colors.success :
                                    isTransitioning ? theme.colors.warning :
                                        isError ? theme.colors.error : theme.colors.error,
                            }]}>
                                {tradingState.trading_state_label || tradingState.trading_state}
                            </Text>
                        </View>
                    </View>

                    <Text style={styles.systemDescription}>
                        يتحكم في: المجموعة B (التداول الآلي) + التعلم الآلي
                    </Text>

                    <View style={styles.statsRow}>
                        {renderStatItem(
                            'الحالة',
                            tradingState.trading_state_label || ts,
                            isSystemRunning ? theme.colors.success :
                                isTransitioning ? theme.colors.warning :
                                    isError ? theme.colors.error : theme.colors.error
                        )}
                        {isSystemRunning && renderStatItem('مدة التشغيل', tradingState.uptime_formatted || formatUptime(tradingState.uptime), theme.colors.info)}
                        {tradingState.pid && isSystemRunning && renderStatItem('PID', tradingState.pid, theme.colors.textSecondary)}
                    </View>

                    {/* ===== Live Monitoring ===== */}
                    {isSystemRunning && tradingState.subsystems?.heartbeat && (
                        <View style={styles.liveMonitoringContainer}>
                            <Text style={styles.liveMonitoringTitle}>💓 المراقبة الحية</Text>
                            <View style={[styles.heartbeatRow, {
                                backgroundColor: (
                                    tradingState.subsystems.heartbeat.status === 'healthy' ? theme.colors.success :
                                        tradingState.subsystems.heartbeat.status === 'warning' ? theme.colors.warning :
                                            theme.colors.error
                                ) + '10'
                            }]}>
                                <Text style={styles.heartbeatIcon}>
                                    {tradingState.subsystems.heartbeat.status === 'healthy' ? '💚' :
                                        tradingState.subsystems.heartbeat.status === 'warning' ? '💛' : '💔'}
                                </Text>
                                <View style={{ flex: 1 }}>
                                    <Text style={styles.heartbeatLabel}>آخر نبضة</Text>
                                    <Text style={[styles.heartbeatValue, {
                                        color: tradingState.subsystems.heartbeat.status === 'healthy' ? theme.colors.success :
                                            tradingState.subsystems.heartbeat.status === 'warning' ? theme.colors.warning : theme.colors.error
                                    }]}>
                                        {formatSecondsAgo(tradingState.subsystems.heartbeat.seconds_ago)}
                                    </Text>
                                </View>
                            </View>

                            {tradingState.subsystems?.group_b && (
                                <View style={styles.activityGrid}>
                                    <View style={styles.activityCard}>
                                        <Text style={styles.activityIcon}>💹</Text>
                                        <Text style={styles.activityLabel}>Group B</Text>
                                        <Text style={[styles.activityTime, {
                                            color: tradingState.subsystems.group_b.status === 'active' ? theme.colors.success : theme.colors.textSecondary
                                        }]}>
                                            {formatSecondsAgo(tradingState.subsystems.group_b.seconds_ago)}
                                        </Text>
                                        <Text style={styles.activityCycles}>🔄 {tradingState.subsystems.group_b.total_cycles || 0} دورة</Text>
                                    </View>
                                </View>
                            )}
                        </View>
                    )}

                    {/* شريط تقدم أثناء الانتقال */}
                    {isTransitioning && (
                        <View style={styles.progressIndicator}>
                            <ActivityIndicator size="small" color={theme.colors.warning} />
                            <Text style={styles.progressText}>
                                {ts === 'STOPPING' ? 'جاري إيقاف النظام...' : 'جاري تشغيل النظام...'}
                            </Text>
                        </View>
                    )}

                    {/* رسالة الخطأ */}
                    {isError && (
                        <View style={[styles.progressIndicator, { backgroundColor: theme.colors.error + '15' }]}>
                            <Text style={[styles.progressText, { color: theme.colors.error }]}>
                                ❌ {tradingState.message || 'حدث خطأ في النظام'}
                            </Text>
                        </View>
                    )}

                    {/* ✅ أزرار مبنية على trading_state */}
                    <View style={styles.buttonRow}>
                        {/* زر التشغيل — يظهر فقط عند STOPPED أو ERROR */}
                        {canStart && (
                            <TouchableOpacity
                                style={[styles.toggleButton, {
                                    backgroundColor: theme.colors.success,
                                    opacity: !isServerConnected ? 0.6 : 1,
                                    flex: 1,
                                }]}
                                onPress={handleStartSystem}
                                disabled={!isServerConnected}
                            >
                                <Text style={styles.toggleButtonText}>
                                    {isError ? '🔄 إعادة التشغيل' : '▶️ تشغيل النظام'}
                                </Text>
                            </TouchableOpacity>
                        )}

                        {/* إعادة تعيين في حالة ERROR */}
                        {isError && (
                            <TouchableOpacity
                                style={[styles.emergencyButton, { backgroundColor: theme.colors.warning, marginLeft: 8 }]}
                                onPress={handleResetError}
                            >
                                <Text style={styles.emergencyButtonText}>🔄</Text>
                            </TouchableOpacity>
                        )}

                        {/* زر الإيقاف — يظهر فقط عند RUNNING */}
                        {canStop && (
                            <TouchableOpacity
                                style={[styles.toggleButton, {
                                    backgroundColor: theme.colors.error,
                                    opacity: !isServerConnected ? 0.6 : 1,
                                    flex: 1,
                                    marginRight: 8,
                                }]}
                                onPress={handleStopSystem}
                                disabled={!isServerConnected}
                            >
                                <Text style={styles.toggleButtonText}>⏹ إيقاف النظام</Text>
                            </TouchableOpacity>
                        )}

                        {/* زر الطوارئ — يظهر فقط عند RUNNING */}
                        {canStop && (
                            <TouchableOpacity
                                style={[styles.emergencyButton, { opacity: !isServerConnected ? 0.5 : 1 }]}
                                onPress={handleEmergencyStop}
                                disabled={!isServerConnected}
                            >
                                <Text style={styles.emergencyButtonText}>🚨</Text>
                            </TouchableOpacity>
                        )}

                        {/* أزرار معطلة أثناء STARTING/STOPPING */}
                        {isTransitioning && (
                            <View style={[styles.toggleButton, { backgroundColor: theme.colors.warning, flex: 1, opacity: 0.6 }]}>
                                <View style={styles.buttonContent}>
                                    <ActivityIndicator color="#FFF" size="small" />
                                    <Text style={[styles.toggleButtonText, { marginLeft: 8 }]}>
                                        {tradingState.trading_state_label}
                                    </Text>
                                </View>
                            </View>
                        )}
                    </View>

                    {/* الصفقات النشطة تُعرض في شاشات التداول وليس هنا */}
                </ModernCard>

                {/* ═══════════════ 2. حالة الأنظمة الفرعية (تعكس حالة النظام) ═══════════════ */}
                <ModernCard style={[styles.card, !isSystemRunning && styles.cardDisabled]}>
                    <View style={styles.cardHeader}>
                        <Text style={styles.cardTitle}>📊 الأنظمة الفرعية</Text>
                        <View style={[styles.statusBadge, {
                            backgroundColor: isSystemRunning ? theme.colors.success + '20' : theme.colors.error + '20',
                        }]}>
                            <View style={[styles.statusDot, { backgroundColor: isSystemRunning ? theme.colors.success : theme.colors.error }]} />
                            <Text style={[styles.statusText, { color: isSystemRunning ? theme.colors.success : theme.colors.error }]}>
                                {isSystemRunning ? 'نشط' : 'متوقف'}
                            </Text>
                        </View>
                    </View>

                    {/* Group B */}
                    <View style={[styles.subsystemRow, !isSystemRunning && styles.subsystemDisabled]}>
                        <View style={styles.subsystemInfo}>
                            <Text style={[styles.subsystemIcon, !isSystemRunning && styles.iconDisabled]}>💹</Text>
                            <View>
                                <Text style={[styles.subsystemName, !isSystemRunning && styles.textDisabled]}>المجموعة B</Text>
                                <Text style={styles.subsystemDesc}>
                                    {isSystemRunning ? 'التداول الآلي (كل 60 ثانية)' : '⏸ متوقف'}
                                </Text>
                            </View>
                        </View>
                        <View style={styles.subsystemStats}>
                            <Text style={[styles.subsystemStatValue, !isSystemRunning && styles.valueDisabled]}>
                                {isSystemRunning ? subsystems.groupB.active_trades : '-'}
                            </Text>
                            <Text style={styles.subsystemStatLabel}>صفقة نشطة</Text>
                        </View>
                    </View>

                    {/* ML */}
                    <View style={[styles.subsystemRow, { borderBottomWidth: 0 }, !isSystemRunning && styles.subsystemDisabled]}>
                        <View style={styles.subsystemInfo}>
                            <Text style={[styles.subsystemIcon, !isSystemRunning && styles.iconDisabled]}>🧠</Text>
                            <View>
                                <Text style={[styles.subsystemName, !isSystemRunning && styles.textDisabled]}>التعلم الآلي</Text>
                                <Text style={styles.subsystemDesc}>
                                    {!isSystemRunning ? '⏸ متوقف' : (subsystems.ml.is_ready ? '✅ جاهز' : `${mlProgress.toFixed(0)}% تقدم`)}
                                </Text>
                            </View>
                        </View>
                        <View style={styles.subsystemStats}>
                            <Text style={[styles.subsystemStatValue, !isSystemRunning && styles.valueDisabled]}>
                                {isSystemRunning ? subsystems.ml.total_samples : '-'}
                            </Text>
                            <Text style={styles.subsystemStatLabel}>/ {subsystems.ml.required_samples}</Text>
                        </View>
                    </View>

                    {/* ML Progress Bar */}
                    <View style={styles.mlProgressContainer}>
                        <View style={styles.progressBar}>
                            <View style={[styles.progressFill, {
                                width: isSystemRunning ? `${mlProgress}%` : '0%',
                                backgroundColor: !isSystemRunning ? theme.colors.border : (subsystems.ml.is_ready ? theme.colors.success : theme.colors.info),
                            }]} />
                        </View>
                    </View>

                    {/* رسالة حالة النظام */}
                    {!isSystemRunning && (
                        <View style={styles.systemStoppedMessage}>
                            <Text style={styles.systemStoppedText}>⚠️ شغّل النظام لتفعيل الأنظمة الفرعية</Text>
                        </View>
                    )}
                </ModernCard>

                {/* ═══════════════ 3. مؤشر نظام التعلم ═══════════════ */}
                <ModernCard style={styles.card}>
                    <View style={styles.cardHeader}>
                        <Text style={styles.cardTitle}>📈 نظام التعلم التكيّفي</Text>
                        <View style={[styles.statusBadge, {
                            backgroundColor: (
                                learningStatus.verdict === 'LEARNING_EFFECTIVE' ? theme.colors.success :
                                    learningStatus.verdict === 'LEARNING_MARGINAL' ? theme.colors.warning :
                                        learningStatus.verdict === 'LEARNING_HARMFUL' ? theme.colors.error :
                                            learningStatus.verdict === 'LEARNING_NEUTRAL' ? theme.colors.info :
                                                theme.colors.textSecondary
                            ) + '20',
                        }]}>
                            <Text style={[styles.statusText, {
                                color: learningStatus.verdict === 'LEARNING_EFFECTIVE' ? theme.colors.success :
                                    learningStatus.verdict === 'LEARNING_MARGINAL' ? theme.colors.warning :
                                        learningStatus.verdict === 'LEARNING_HARMFUL' ? theme.colors.error :
                                            learningStatus.verdict === 'LEARNING_NEUTRAL' ? theme.colors.info :
                                                theme.colors.textSecondary,
                            }]}>
                                {learningStatus.verdict === 'LEARNING_EFFECTIVE' ? '✅ فعّال' :
                                    learningStatus.verdict === 'LEARNING_MARGINAL' ? '⚠️ هامشي' :
                                        learningStatus.verdict === 'LEARNING_HARMFUL' ? '🔴 ضار' :
                                            learningStatus.verdict === 'LEARNING_NEUTRAL' ? '➖ محايد' :
                                                learningStatus.verdict === 'INSUFFICIENT_DATA' ? '⏳ بيانات قليلة' :
                                                    '⏳ ينتظر'}
                            </Text>
                        </View>
                    </View>

                    {/* مؤشر الاتجاه البصري */}
                    <View style={[styles.learningIndicator, {
                        backgroundColor: (
                            learningStatus.verdict === 'LEARNING_EFFECTIVE' ? theme.colors.success :
                                learningStatus.verdict === 'LEARNING_HARMFUL' ? theme.colors.error :
                                    learningStatus.verdict ? theme.colors.warning :
                                        theme.colors.textSecondary
                        ) + '10',
                        borderLeftColor: learningStatus.verdict === 'LEARNING_EFFECTIVE' ? theme.colors.success :
                            learningStatus.verdict === 'LEARNING_HARMFUL' ? theme.colors.error :
                                learningStatus.verdict ? theme.colors.warning :
                                    theme.colors.border,
                    }]}>
                        <Text style={styles.learningIndicatorIcon}>
                            {learningStatus.trend === 'improving' ? '📈' :
                                learningStatus.trend === 'declining' ? '📉' : '📊'}
                        </Text>
                        <View style={{ flex: 1 }}>
                            <Text style={styles.learningIndicatorTitle}>
                                {learningStatus.verdict === 'LEARNING_EFFECTIVE'
                                    ? 'التعلم يحسّن النتائج'
                                    : learningStatus.verdict === 'LEARNING_HARMFUL'
                                        ? 'التعلم يحتاج مراجعة!'
                                        : learningStatus.verdict === 'LEARNING_MARGINAL'
                                            ? 'تحسن طفيف'
                                            : learningStatus.totalTrades > 0
                                                ? 'يجمع بيانات...'
                                                : 'ينتظر بيانات'}
                            </Text>
                            {learningStatus.verdict && (
                                <Text style={styles.learningIndicatorDetail}>
                                    دقة {(learningStatus.accuracy * 100).toFixed(0)}% vs عشوائي {(learningStatus.baseline * 100).toFixed(0)}% ({learningStatus.lift > 0 ? '+' : ''}{(learningStatus.lift * 100).toFixed(0)}%)
                                </Text>
                            )}
                        </View>
                    </View>

                    {/* إحصائيات التعلم */}
                    <View style={styles.statsRow}>
                        {renderStatItem('صفقات مسجّلة', learningStatus.totalTrades, theme.colors.primary)}
                        {renderStatItem('مع مؤشرات', learningStatus.withIndicators, learningStatus.withIndicators > 0 ? theme.colors.success : theme.colors.textSecondary)}
                        {renderStatItem('نسبة الفوز', learningStatus.winRate > 0 ? `${(learningStatus.winRate * 100).toFixed(0)}%` : '-',
                            learningStatus.winRate >= 0.5 ? theme.colors.success : learningStatus.winRate > 0 ? theme.colors.warning : theme.colors.textSecondary)}
                    </View>

                    <View style={styles.statsRow}>
                        {renderStatItem('متوسط الربح', learningStatus.avgPnl !== 0 ? `${learningStatus.avgPnl > 0 ? '+' : ''}${learningStatus.avgPnl}%` : '-',
                            learningStatus.avgPnl > 0 ? theme.colors.success : learningStatus.avgPnl < 0 ? theme.colors.error : theme.colors.textSecondary)}
                        {renderStatItem('عملات محظورة', learningStatus.blockedSymbols,
                            learningStatus.blockedSymbols > 0 ? theme.colors.warning : theme.colors.textSecondary)}
                        {renderStatItem('الاتجاه',
                            learningStatus.trend === 'improving' ? 'تحسّن' :
                                learningStatus.trend === 'declining' ? 'تراجع' : 'مستقر',
                            learningStatus.trend === 'improving' ? theme.colors.success :
                                learningStatus.trend === 'declining' ? theme.colors.error : theme.colors.textSecondary)}
                    </View>
                </ModernCard>

                {/* ═══════════════ 4. سجل الأخطاء ═══════════════ */}
                <ModernCard style={styles.card}>
                    <View style={styles.cardHeader}>
                        <Text style={styles.cardTitle}>🚨 سجل الأخطاء</Text>
                        <View style={[styles.statusBadge, {
                            backgroundColor: errors.count > 0
                                ? (errors.critical_count > 0 ? theme.colors.error : theme.colors.warning) + '20'
                                : theme.colors.success + '20',
                        }]}>
                            <Text style={[styles.statusText, {
                                color: errors.count > 0
                                    ? (errors.critical_count > 0 ? theme.colors.error : theme.colors.warning)
                                    : theme.colors.success,
                            }]}>
                                {errors.count > 0 ? `${errors.count} خطأ` : '✅ لا أخطاء'}
                            </Text>
                        </View>
                    </View>

                    {errors.recent.length > 0 ? (
                        errors.recent.map((err, index) => (
                            <View key={err.id || `error-${index}-${err.created_at}`} style={styles.errorItem}>
                                <View style={styles.errorHeader}>
                                    <Text style={[styles.errorLevel, {
                                        color: err.level === 'critical' ? theme.colors.error : theme.colors.warning,
                                    }]}>
                                        {err.level === 'critical' ? '🔴' : '🟡'} {err.source || 'النظام'}
                                    </Text>
                                    <Text style={styles.errorTime}>{formatTime(err.created_at)}</Text>
                                </View>
                                <Text style={styles.errorMessage} numberOfLines={2}>{err.message}</Text>
                            </View>
                        ))
                    ) : (
                        <Text style={styles.emptyText}>✅ لا توجد أخطاء حديثة</Text>
                    )}

                    {errors.count > 3 && (
                        <TouchableOpacity
                            style={styles.viewAllButton}
                            onPress={() => navigation?.navigate('AdminErrors')}
                        >
                            <Text style={styles.viewAllText}>عرض الكل ({errors.count})</Text>
                        </TouchableOpacity>
                    )}
                </ModernCard>

                {/* ═══════════════ 4. إعادة ضبط Demo ═══════════════ */}
                <ModernCard style={styles.card}>
                    <View style={styles.cardHeader}>
                        <Text style={styles.cardTitle}>🔄 إعادة ضبط Demo</Text>
                    </View>
                    <Text style={styles.resetDescription}>
                        سيتم حذف جميع الصفقات وإعادة الرصيد إلى $1,000
                    </Text>
                    <TouchableOpacity
                        style={[styles.resetButton, { opacity: (!isServerConnected || actionLoading.resetDemo) ? 0.5 : 1 }]}
                        onPress={handleResetDemo}
                        disabled={!isServerConnected || actionLoading.resetDemo}
                    >
                        {actionLoading.resetDemo ? (
                            <ActivityIndicator color={theme.colors.error} size="small" />
                        ) : (
                            <Text style={styles.resetButtonText}>🔄 إعادة ضبط الحساب التجريبي</Text>
                        )}
                    </TouchableOpacity>
                </ModernCard>

                {/* ═══════════════ 5. إدارة المستخدمين ═══════════════ */}
                <ModernCard style={styles.card}>
                    <View style={styles.cardHeader}>
                        <Text style={styles.cardTitle}>👥 إدارة المستخدمين</Text>
                        <View style={[styles.statusBadge, {
                            backgroundColor: users.count > 0 ? theme.colors.success + '20' : theme.colors.warning + '20',
                        }]}>
                            <Text style={[styles.statusText, {
                                color: users.count > 0 ? theme.colors.success : theme.colors.warning,
                            }]}>
                                {users.count} مستخدم
                            </Text>
                        </View>
                    </View>

                    <View style={styles.statsRow}>
                        {renderStatItem('إجمالي المستخدمين', users.count, theme.colors.primary)}
                        {renderStatItem('المستخدمون النشطون', users.active, theme.colors.success)}
                        {renderStatItem('المستخدمون غير النشطين', users.count - users.active, theme.colors.warning)}
                    </View>

                    {/* قائمة المستخدمين */}
                    {users.list.length > 0 && (
                        <View style={styles.usersList}>
                            {users.list.map((user, index) => (
                                <View key={user.id || `user-${index}`} style={styles.userItem}>
                                    <View style={styles.userInfo}>
                                        <Text style={styles.userName}>
                                            {user.username} {user.user_type === 'admin' && '👑'}
                                        </Text>
                                        <Text style={styles.userEmail}>{user.email}</Text>
                                    </View>
                                    <View style={styles.userStatus}>
                                        <View style={[styles.userStatusDot, {
                                            backgroundColor: user.is_active ? theme.colors.success : theme.colors.error,
                                        }]} />
                                        <Text style={[styles.userStatusText, {
                                            color: user.is_active ? theme.colors.success : theme.colors.error,
                                        }]}>
                                            {user.is_active ? 'نشط' : 'غير نشط'}
                                        </Text>
                                    </View>
                                </View>
                            ))}
                        </View>
                    )}

                    {/* أزرار الإدارة */}
                    <View style={styles.buttonRow}>
                        <TouchableOpacity
                            style={[styles.managementButton, {
                                backgroundColor: theme.colors.primary,
                                opacity: (!isServerConnected || actionLoading.userManagement) ? 0.5 : 1,
                                flex: 1,
                                marginRight: 8,
                            }]}
                            onPress={() => navigation?.navigate('UserManagement')}
                            disabled={!isServerConnected || actionLoading.userManagement}
                        >
                            <Text style={[styles.managementButtonText, { color: '#FFF' }]}>
                                👥 إدارة المستخدمين
                            </Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                            style={[styles.managementButton, {
                                backgroundColor: theme.colors.success,
                                opacity: (!isServerConnected || actionLoading.userManagement) ? 0.5 : 1,
                                flex: 1,
                            }]}
                            onPress={() => navigation?.navigate('CreateUser')}
                            disabled={!isServerConnected || actionLoading.userManagement}
                        >
                            <Text style={[styles.managementButtonText, { color: '#FFF' }]}>
                                ➕ إضافة مستخدم
                            </Text>
                        </TouchableOpacity>
                    </View>
                </ModernCard>

                <View style={{ height: 40 }} />
            </ScrollView>
        </View>
    );
};

// ==================== Styles ====================
const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: theme.colors.background },
    content: { flex: 1, paddingHorizontal: 16, paddingTop: 16 },
    card: { marginBottom: 16 },
    cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
    cardTitle: { ...theme.hierarchy.secondary, fontSize: 16, color: theme.colors.text },

    // شريط الحالة الموحد
    statusBar: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.surface,
        paddingHorizontal: 16,
        paddingVertical: 12,
        borderRadius: 10,
        marginBottom: 16,
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    statusBarItem: { flexDirection: 'row', alignItems: 'center' },
    statusBarLabel: { fontSize: 12, color: theme.colors.textSecondary, marginRight: 4 },
    statusBarValue: { fontSize: 12, fontWeight: '700' },
    statusBarDivider: { width: 1, height: 16, backgroundColor: theme.colors.border, marginHorizontal: 12 },

    // حالات
    statusBadge: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 10, paddingVertical: 5, borderRadius: 12 },
    statusDot: { width: 8, height: 8, borderRadius: 4, marginRight: 6 },
    statusText: { fontSize: 12, fontWeight: '600' },

    // وصف النظام
    systemDescription: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginBottom: 12,
        backgroundColor: theme.colors.info + '10',
        padding: 8,
        borderRadius: 6,
    },

    // الإحصائيات
    statsRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 },
    statItem: { alignItems: 'center', flex: 1 },
    statLabel: { ...theme.hierarchy.tiny, color: theme.colors.textSecondary, marginBottom: 4 },
    statValue: { ...theme.hierarchy.body, fontWeight: '700' },

    // الأزرار
    toggleButton: { paddingVertical: 14, borderRadius: 10, alignItems: 'center', justifyContent: 'center', minHeight: 48 },
    toggleButtonText: { color: '#FFF', fontSize: 15, fontWeight: '700' },
    buttonRow: { flexDirection: 'row', alignItems: 'center', marginTop: 12 },
    buttonContent: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center' },
    emergencyButton: { backgroundColor: theme.colors.error, paddingVertical: 14, paddingHorizontal: 18, borderRadius: 10, alignItems: 'center', justifyContent: 'center', minHeight: 48 },
    emergencyButtonText: { fontSize: 20 },

    // مؤشر التقدم أثناء التنفيذ
    progressIndicator: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: theme.colors.warning + '15',
        padding: 10,
        borderRadius: 8,
        marginBottom: 12,
    },
    progressText: {
        fontSize: 13,
        color: theme.colors.warning,
        marginLeft: 10,
        fontWeight: '600',
    },

    // Live Monitoring Styles
    liveMonitoringContainer: {
        marginTop: 16,
        padding: 12,
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    liveMonitoringTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 12,
    },
    heartbeatRow: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 12,
        borderRadius: 8,
        marginBottom: 12,
    },
    heartbeatIcon: {
        fontSize: 24,
        marginRight: 12,
    },
    heartbeatLabel: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        marginBottom: 2,
    },
    heartbeatValue: {
        fontSize: 14,
        fontWeight: '600',
    },
    activityGrid: {
        flexDirection: 'row',
        gap: 8,
    },
    activityCard: {
        flex: 1,
        backgroundColor: theme.colors.background,
        padding: 10,
        borderRadius: 8,
        borderWidth: 1,
        borderColor: theme.colors.border,
        alignItems: 'center',
    },
    activityIcon: {
        fontSize: 20,
        marginBottom: 4,
    },
    activityLabel: {
        fontSize: 11,
        color: theme.colors.textSecondary,
        marginBottom: 4,
    },
    activityTime: {
        fontSize: 12,
        fontWeight: '600',
        marginBottom: 4,
    },
    activityCycles: {
        fontSize: 10,
        color: theme.colors.textSecondary,
    },

    // للعرض فقط
    viewOnlyBadge: {
        fontSize: 10,
        color: theme.colors.textSecondary,
        backgroundColor: theme.colors.border + '50',
        paddingHorizontal: 8,
        paddingVertical: 3,
        borderRadius: 8,
    },

    // الأنظمة الفرعية
    subsystemRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border + '50',
    },
    subsystemInfo: { flexDirection: 'row', alignItems: 'center', flex: 1 },
    subsystemIcon: { fontSize: 24, marginRight: 12 },
    subsystemName: { fontSize: 14, fontWeight: '600', color: theme.colors.text },
    subsystemDesc: { fontSize: 11, color: theme.colors.textSecondary, marginTop: 2 },
    subsystemStats: { alignItems: 'flex-end' },
    subsystemStatValue: { fontSize: 18, fontWeight: '700', color: theme.colors.primary },
    subsystemStatLabel: { fontSize: 10, color: theme.colors.textSecondary },

    // ML Progress
    mlProgressContainer: { marginTop: 8 },
    progressBar: { height: 8, backgroundColor: theme.colors.surface, borderRadius: 4, overflow: 'hidden' },
    progressFill: { height: '100%', borderRadius: 4 },

    // الأخطاء
    errorItem: {
        backgroundColor: theme.colors.surface,
        padding: 10,
        borderRadius: 8,
        marginBottom: 8,
    },
    errorHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
    errorLevel: { fontSize: 12, fontWeight: '600' },
    errorTime: { fontSize: 10, color: theme.colors.textSecondary },
    errorMessage: { fontSize: 12, color: theme.colors.text, lineHeight: 18 },
    viewAllButton: {
        alignItems: 'center',
        paddingVertical: 10,
        marginTop: 4,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border + '50',
    },
    viewAllText: { fontSize: 13, color: theme.colors.primary, fontWeight: '600' },

    // إعادة الضبط
    resetDescription: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginBottom: 12,
    },
    resetButton: {
        paddingVertical: 12,
        borderRadius: 8,
        borderWidth: 1,
        borderColor: theme.colors.error,
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 44,
    },
    resetButtonText: { color: theme.colors.error, fontSize: 14, fontWeight: '600' },

    // تحذيرات
    warningTitle: { fontSize: 15, fontWeight: '700', color: theme.colors.warning, marginBottom: 6 },
    warningText: { fontSize: 13, color: theme.colors.textSecondary, marginBottom: 12 },
    retryButton: { backgroundColor: theme.colors.warning + '20', paddingVertical: 10, paddingHorizontal: 16, borderRadius: 8, alignItems: 'center' },
    retryButtonText: { color: theme.colors.warning, fontSize: 14, fontWeight: '600' },

    // عام
    emptyText: { fontSize: 13, color: theme.colors.textSecondary, textAlign: 'center', paddingVertical: 16 },
    lastUpdateText: { fontSize: 11, color: theme.colors.textSecondary },

    // إدارة المستخدمين
    usersList: { marginTop: 12 },
    userItem: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 10,
        paddingHorizontal: 12,
        backgroundColor: theme.colors.surface,
        borderRadius: 8,
        marginBottom: 8,
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    userInfo: { flex: 1 },
    userName: { fontSize: 14, fontWeight: '600', color: theme.colors.text },
    userEmail: { fontSize: 12, color: theme.colors.textSecondary, marginTop: 2 },
    userStatus: { flexDirection: 'row', alignItems: 'center' },
    userStatusDot: { width: 8, height: 8, borderRadius: 4, marginRight: 6 },
    userStatusText: { fontSize: 12, fontWeight: '600' },
    managementButton: {
        paddingVertical: 12,
        borderRadius: 8,
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 44,
    },
    managementButtonText: { fontSize: 14, fontWeight: '600' },

    // مؤشر نظام التعلم
    learningIndicator: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 12,
        borderRadius: 8,
        borderLeftWidth: 4,
        marginBottom: 12,
    },
    learningIndicatorIcon: {
        fontSize: 24,
        marginRight: 12,
    },
    learningIndicatorTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 2,
    },
    learningIndicatorDetail: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
});

export default AdminDashboard;
