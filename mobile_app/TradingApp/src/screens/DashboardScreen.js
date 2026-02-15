/**
 * Dashboard Screen - شاشة لوحة التحكم
 * Main dashboard showing portfolio and trading overview
 */

import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
    View,
    Text,
    ScrollView,
    StyleSheet,
    ActivityIndicator,
    RefreshControl,
    I18nManager,
    TouchableOpacity,
    Image,
    Dimensions,
} from 'react-native';
// ActivityIndicator موجود بالفعل
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useNavigation } from '@react-navigation/native';
import DatabaseApiService from '../services/DatabaseApiService';
import { theme } from '../theme/theme';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing, typography, textStyles, components, shadows } from '../theme/designSystem';
import { useBackHandlerWithConfirmation } from '../utils/BackHandlerUtil';
import ToastService from '../services/ToastService';
import { DemoModeIcon, RealModeIcon } from '../components/TradingModeIcons';
import ModernCard from '../components/ModernCard';
import PortfolioChart from '../components/charts/PortfolioChart';
import WinLossPieChart from '../components/charts/WinLossPieChart';
import ActivePositionsCard from '../components/ActivePositionsCard';
import MonitoredCoinsCard from '../components/MonitoredCoinsCard';
import { useTradingModeContext } from '../context/TradingModeContext';
import { usePortfolioContext } from '../context/PortfolioContext';
import UnifiedBrandLogo from '../components/UnifiedBrandLogo';
import GlobalHeader from '../components/GlobalHeader';
import BrandIcon from '../components/BrandIcons';
import { DashboardSkeleton } from '../components/SkeletonLoader';
import { hapticLight, hapticSuccess, hapticWarning } from '../utils/HapticFeedback';
import { AlertService } from '../components/CustomAlert';
import Logger from '../services/LoggerService';
import { useIsAdmin } from '../hooks/useIsAdmin';
import AdminModeBanner from '../components/AdminModeBanner';
import { appStateManager, AppEvents } from '../services/AppStateManager';
// ✅ AdminModeSwitcher تم نقله إلى GlobalHeader

const isRTL = I18nManager.isRTL;
const { width: SCREEN_WIDTH } = Dimensions.get('window');

const DashboardScreen = ({ user: propUser }) => {
    const navigation = useNavigation();
    const [user, setUser] = useState(propUser || null);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [lastUpdated, setLastUpdated] = useState(new Date());
    const [hasKeys, setHasKeys] = useState(null); // ✅ null حتى جلب البيانات الحقيقية - لا افتراضات
    const [activePositions, setActivePositions] = useState([]);
    const [positionsSummary, setPositionsSummary] = useState({});
    const [positionsLoading, setPositionsLoading] = useState(false);
    const [monitoredCoins, setMonitoredCoins] = useState([]);
    const [coinsLoading, setCoinsLoading] = useState(false);

    // ✅ إصلاح Race Conditions - منع تحديث State على unmounted component
    const isMountedRef = useRef(true);

    // ✅ Cleanup عند unmount
    useEffect(() => {
        isMountedRef.current = true;
        return () => {
            isMountedRef.current = false;
        };
    }, []);

    // ✅ حالة النظام الفعلية (للانعكاس الصحيح)
    const [systemStatus, setSystemStatus] = useState({
        is_running: false,
        group_b_active: false,
    });

    // ✅ استخدام PortfolioContext بدلاً من state محلي
    const {
        portfolio,
        demoPortfolio,
        realPortfolio,
        isLoading: portfolioLoading,
        fetchAllPortfolios,
        refreshPortfolios,
        updateUser: updatePortfolioUser,
    } = usePortfolioContext();

    // ✅ للأدمن: ملخص المحفظتين من Context
    const adminPortfolios = {
        demo: demoPortfolio,
        real: realPortfolio,
    };

    // ✅ استخدام Context الموحد لوضع التداول
    const {
        tradingMode,
        getModeText,
        getModeColor,
        refreshCounter,
        initializeUser,
        isAdmin: contextIsAdmin,
        getCurrentViewMode,
        adminViewMode,
        changeTradingMode,
        isLoading: modeLoading,
        hasBinanceKeys,
    } = useTradingModeContext();

    const [switching, setSwitching] = useState(false);

    // ✅ الوضع الفعلي للعرض (للأدمن يمكن أن يختلف عن tradingMode)
    const currentViewMode = getCurrentViewMode();

    // ✅ معالجة زر الرجوع من الجهاز - عرض Dialog تأكيد قبل الخروج
    useBackHandlerWithConfirmation(true);

    useEffect(() => {
        // استخدام user من props أو من AsyncStorage
        if (propUser) {
            setUser(propUser);
            initializeUser(propUser);
            const isAdminUser = propUser.user_type === 'admin';
            updatePortfolioUser(propUser.id, isAdminUser);
            loadDashboardData();
        }
    }, [propUser]);

    // ✅ FIX: Debounced refresh to prevent continuous updates
    const lastRefreshTimeRef = useRef(0);
    const REFRESH_DEBOUNCE_MS = 10000; // 10 seconds minimum between refreshes

    // ✅ إعادة تحميل البيانات عند تغيير وضع التداول (مع debounce لمنع التحديث المتكرر)
    useEffect(() => {
        if (refreshCounter > 0 && user) {
            const now = Date.now();
            // ✅ منع التحديث إذا كان آخر تحديث قبل أقل من 10 ثواني
            if (now - lastRefreshTimeRef.current < REFRESH_DEBOUNCE_MS) {
                console.log('[Dashboard] Skipping refresh - too soon since last refresh');
                return;
            }
            lastRefreshTimeRef.current = now;

            // ✅ تأخير عشوائي لمنع الطلبات المتزامنة (429 Rate Limit)
            const delay = Math.random() * 500 + 200; // 200-700ms
            const timer = setTimeout(() => {
                loadDashboardData();
            }, delay);
            return () => clearTimeout(timer);
        }
    }, [refreshCounter, user]);

    // ✅ الاستماع لتغييرات حالة النظام (مرة واحدة فقط عند mount)
    useEffect(() => {
        // الاستماع لتغيير حالة النظام (من AdminDashboard)
        const unsubSystemStatus = appStateManager.on(AppEvents.SYSTEM_STATUS_CHANGED, (status) => {
            if (isMountedRef.current) {
                setSystemStatus({
                    is_running: status.is_running || false,
                    group_b_active: status.group_b_active || false,
                });
            }
        });

        return () => {
            unsubSystemStatus();
        };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []); // ✅ فقط عند mount - لا نحتاج dependencies لأن الـ listener يستخدم isMountedRef

    // ✅ Live Dashboard: تحديث الصفقات يتم عبر refreshCounter من TradingModeContext
    // تم إزالة interval منفصل - التحديث مركزي الآن

    const loadDashboardData = useCallback(async () => {
        // ✅ فحص isMounted قبل البدء
        if (!isMountedRef.current) { return; }

        try {
            setLoading(true);

            // استخدام user من props أو من AsyncStorage
            let currentUser = user || propUser;

            if (!currentUser) {
                const userData = await AsyncStorage.getItem('userData');
                if (!userData) {
                    if (isMountedRef.current) {
                        ToastService.showInfo('لم يتم العثور على بيانات المستخدم');
                        setLoading(false);
                    }
                    return;
                }
                try {
                    currentUser = JSON.parse(userData);
                } catch (parseError) {
                    Logger.error('فشل تحليل بيانات المستخدم', 'DashboardScreen', parseError);
                    if (isMountedRef.current) {
                        ToastService.showError('بيانات المستخدم تالفة، يرجى تسجيل الدخول مرة أخرى');
                        setLoading(false);
                    }
                    return;
                }
            }

            // ✅ فحص isMounted بعد كل عملية async
            if (!isMountedRef.current) { return; }

            // تهيئة خدمة قاعدة البيانات
            await DatabaseApiService.initialize();

            if (!isMountedRef.current) { return; }

            // ✅ جلب الملف الشخصي (يجب أن يسبق باقي الطلبات لتحديث بيانات المستخدم)
            try {
                const profileData = await DatabaseApiService.getProfile(currentUser.id);
                if (isMountedRef.current && profileData?.success && profileData?.data) {
                    currentUser = { ...currentUser, ...profileData.data };
                }
            } catch (e) {
                console.warn('[WARNING] فشل جلب الملف الشخصي');
            }

            if (!isMountedRef.current) { return; }
            setUser(currentUser);

            // ✅ جلب بيانات متعددة بالتوازي لتسريع التحميل
            const userIsAdmin = currentUser?.user_type === 'admin';
            const parallelPromises = [
                fetchAllPortfolios().catch(() => null),
                DatabaseApiService.getStats(
                    currentUser.id,
                    userIsAdmin ? currentViewMode : null
                ).catch(() => null),
                loadActivePositions(currentUser).catch(() => null),
            ];

            // ✅ جلب حالة النظام — فقط للأدمن (endpoint يتطلب صلاحية أدمن)
            if (userIsAdmin) {
                parallelPromises.push(
                    DatabaseApiService.getBackgroundSystemStatus?.()?.catch(() => null)
                );
                parallelPromises.push(
                    DatabaseApiService.getMonitoredCoins?.()?.catch(() => null)
                );
            }

            const [portfolioData, statsData, , sysResponse, coinsResponse] = await Promise.all(parallelPromises);

            if (!isMountedRef.current) { return; }

            // تحديث hasKeys من portfolio (بيانات حقيقية فقط)
            if (portfolioData && portfolioData.hasKeys !== undefined) {
                setHasKeys(portfolioData.hasKeys === true);
            } else {
                setHasKeys(null);
            }

            // تحديث الإحصائيات
            if (statsData?.success && statsData?.data) {
                setStats(statsData.data);
            } else {
                if (statsData?.errorCode === 401) {
                    console.warn('[WARNING] انتهت صلاحية الجلسة - يرجى إعادة تسجيل الدخول');
                }
                setStats(null);
            }

            // تحديث العملات المُراقبة (للأدمن فقط)
            if (userIsAdmin && coinsResponse?.success) {
                setMonitoredCoins(coinsResponse.coins || []);
            }

            // تحديث حالة النظام (للأدمن فقط)
            if (userIsAdmin && sysResponse?.success) {
                const sysData = sysResponse.data || sysResponse;
                setSystemStatus({
                    is_running: sysData.is_running || false,
                    group_b_active: sysData.group_b_active || false,
                });
                appStateManager.updateSystemStatus({
                    is_running: sysData.is_running || false,
                    status: sysData.status || 'stopped',
                });
            }

            if (isMountedRef.current) {
                setLastUpdated(new Date());
            }
        } catch (error) {
            Logger.error('خطأ في تحميل بيانات لوحة التحكم', 'DashboardScreen', error);
            if (isMountedRef.current) {
                ToastService.showInfo('فشل تحميل البيانات');
            }
        } finally {
            if (isMountedRef.current) {
                setLoading(false);
            }
        }
    }, [user, propUser, fetchAllPortfolios, currentViewMode]);

    const loadActivePositions = useCallback(async (currentUser) => {
        // ✅ فحص isMounted قبل البدء
        if (!isMountedRef.current) { return; }

        try {
            if (!currentUser || !currentUser.id) {
                console.warn('[WARNING] لا يوجد مستخدم أو معرف مستخدم');
                if (isMountedRef.current) {
                    setActivePositions([]);
                    setPositionsSummary({});
                }
                return;
            }

            setPositionsLoading(true);
            const userIsAdmin = currentUser?.user_type === 'admin';
            const mode = userIsAdmin ? currentViewMode : null;
            const positionsData = await DatabaseApiService.getActivePositions(currentUser.id, mode);

            if (!isMountedRef.current) { return; }

            if (positionsData?.success && positionsData?.data) {
                setActivePositions(positionsData.data.positions || []);
                setPositionsSummary(positionsData.data.summary || {});
            } else {
                setActivePositions([]);
                setPositionsSummary({});
            }
        } catch (error) {
            Logger.error('خطأ في جلب الصفقات النشطة', 'DashboardScreen', error);
            if (isMountedRef.current) {
                setActivePositions([]);
                setPositionsSummary({});
            }
        } finally {
            if (isMountedRef.current) {
                setPositionsLoading(false);
            }
        }
    }, [currentViewMode]);

    const onRefresh = useCallback(async () => {
        if (!isMountedRef.current) { return; }
        setRefreshing(true);
        await loadDashboardData();
        if (isMountedRef.current) {
            setRefreshing(false);
        }
    }, [loadDashboardData]);

    // فحص إذا كان المستخدم أدمن - ✅ استخدام Hook موحد
    const isAdmin = useIsAdmin(user);
    const modeColor = getModeColor?.() || '#4A90E2';

    // ✅ دالة تنفيذ التبديل
    const executeToggle = useCallback(async (newMode) => {
        setSwitching(true);
        hapticLight();
        try {
            const result = await changeTradingMode(newMode);
            if (result?.success) {
                hapticSuccess();
                ToastService.showSuccess(`تم التبديل إلى ${newMode === 'demo' ? 'التجريبي' : 'الحقيقي'}`);
            } else {
                hapticWarning();
                ToastService.showError(result?.error || 'فشل التبديل');
            }
        } catch (error) {
            hapticWarning();
            ToastService.showError('حدث خطأ');
        } finally {
            setSwitching(false);
        }
    }, [changeTradingMode]);

    // ✅ دالة تبديل الوضع للأدمن
    const handleToggleMode = useCallback(async () => {
        if (!isAdmin || switching || modeLoading) { return; }

        const newMode = currentViewMode === 'demo' ? 'real' : 'demo';

        if (newMode === 'real') {
            if (!hasBinanceKeys) {
                hapticWarning();
                ToastService.showWarning('يجب إضافة مفاتيح Binance أولاً');
                return;
            }

            AlertService.confirm(
                '⚠️ تحذير هام',
                'أنت على وشك التبديل للتداول الحقيقي.\n\nجميع الصفقات ستكون حقيقية.',
                async () => { await executeToggle(newMode); },
                () => { },
                'تأكيد',
                'إلغاء'
            );
        } else {
            await executeToggle(newMode);
        }
    }, [isAdmin, switching, modeLoading, currentViewMode, hasBinanceKeys, executeToggle]);

    // تثبيت قيم الشارت لتجنب إعادة الحساب المستمرة - ✅ بيانات حقيقية فقط (بدون بيانات افتراضية)
    const chartBalance = useMemo(() => {
        const balance = parseFloat(portfolio?.totalBalance);
        return !isNaN(balance) ? balance : null;
    }, [portfolio?.totalBalance]);

    const chartInitialBalance = useMemo(() => {
        const balance = parseFloat(portfolio?.initialBalance);
        return !isNaN(balance) ? balance : null;
    }, [portfolio?.initialBalance]);

    // ✅ عرض Skeleton Loader بدلاً من ActivityIndicator
    if (loading) {
        return (
            <View style={styles.container}>
                <DashboardSkeleton />
            </View>
        );
    }

    return (
        <View style={styles.container}>
            {/* ✅ استخدام GlobalHeader الموحد */}
            <GlobalHeader
                title="1B Trading"
                subtitle={`مرحباً، ${user?.name || user?.username || 'متداول'}`}
                showLogo={true}
                isAdminUser={isAdmin}
                rightAction={
                    <View style={{ flexDirection: isRTL ? 'row-reverse' : 'row', alignItems: 'center', gap: 8 }}>
                        <TouchableOpacity
                            style={styles.notificationBtn}
                            onPress={() => { hapticLight(); navigation.navigate('Notifications'); }}
                            activeOpacity={0.7}
                        >
                            <BrandIcon name="notification" size={24} color={theme.colors.text} />
                        </TouchableOpacity>
                        <TouchableOpacity
                            style={styles.settingsBtn}
                            onPress={() => { hapticLight(); navigation.navigate('Profile'); }}
                            activeOpacity={0.7}
                        >
                            <BrandIcon name="settings" size={22} color={theme.colors.textSecondary} />
                        </TouchableOpacity>
                    </View>
                }
            />

            {/* ✅ Banner تحذيري للأدمن فقط - مع تمرير وضع التداول */}
            {isAdmin && <AdminModeBanner tradingMode={tradingMode} />}

            <ScrollView
                contentContainerStyle={styles.scrollContent}
                refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.primary} />}
            >
                {/* 1️⃣ بطاقة الرصيد + شارت المحفظة */}
                <ModernCard style={styles.heroCard}>
                    <View style={styles.balanceSection}>
                        <Text style={styles.balanceLabel}>الرصيد الإجمالي</Text>
                        <Text style={styles.balanceValue}>
                            {chartBalance !== null ? chartBalance.toFixed(2) : '⏳ جاري التحقق...'} <Text style={styles.currency}>USDT</Text>
                        </Text>
                        {chartInitialBalance && chartBalance && (
                            <Text style={[styles.pnlBadge, {
                                color: chartBalance >= chartInitialBalance ? theme.colors.success : theme.colors.error,
                            }]}>
                                {chartBalance >= chartInitialBalance ? '▲' : '▼'} {((chartBalance - chartInitialBalance) / chartInitialBalance * 100).toFixed(2)}%
                            </Text>
                        )}
                    </View>

                    {/* ✅ الشارت الرئيسي - رسم بياني تفاعلي لمعدل النمو */}
                    <View style={styles.chartInCard}>
                        <PortfolioChart
                            userId={user?.id}
                            initialBalance={chartInitialBalance}
                            currentBalance={chartBalance}
                            isAdmin={isAdmin}
                            tradingMode={currentViewMode}
                            width={SCREEN_WIDTH - 64}
                            height={220}
                            showGrid={false}
                            showLabels={true}
                        />
                    </View>
                </ModernCard>

                {/* 2️⃣ الصفقات النشطة - بطاقة رئيسية */}
                {user && (
                    <ActivePositionsCard
                        positions={activePositions}
                        summary={positionsSummary}
                        loading={positionsLoading}
                        onRefresh={() => loadActivePositions(user)}
                    />
                )}

                {/* 3️⃣ العملات المُراقبة — للأدمن فقط */}
                {isAdmin && (
                    <MonitoredCoinsCard
                        coins={monitoredCoins}
                        loading={coinsLoading}
                    />
                )}

                {/* 4️⃣ الإحصائيات الأساسية - معدل النجاح والربح */}
                <ModernCard style={styles.statsCard}>
                    <Text style={styles.sectionTitle}>الأداء العام</Text>
                    {parseInt(stats?.totalTrades || 0) === 0 ? (
                        <View style={styles.noTradesContainer}>
                            <BrandIcon name="chart" size={32} color={theme.colors.textSecondary} />
                            <Text style={styles.noTradesText}>لا توجد صفقات بعد</Text>
                            <Text style={styles.noTradesHint}>
                                النظام يعمل آلياً وسيبدأ التداول عند توفر فرص مناسبة.
                                يمكنك مراجعة إعدادات التداول من قائمة الإعدادات.
                            </Text>
                        </View>
                    ) : (
                        <View style={styles.quickStatsRow}>
                            <View style={styles.quickStatItem}>
                                <Text style={[
                                    styles.quickStatValue,
                                    { color: parseFloat(stats?.totalProfit || 0) >= 0 ? theme.colors.success : theme.colors.error },
                                ]}>
                                    ${stats?.totalProfit || '0.00'}
                                </Text>
                                <Text style={styles.quickStatLabel}>إجمالي الربح</Text>
                            </View>
                            <View style={styles.quickStatDivider} />
                            <View style={styles.quickStatItem}>
                                <Text style={[styles.quickStatValue, { color: parseFloat(stats?.winRate || 0) >= 50 ? theme.colors.success : theme.colors.warning }]}>
                                    {stats?.winRate || '0'}%
                                </Text>
                                <Text style={styles.quickStatLabel}>معدل النجاح</Text>
                            </View>
                        </View>
                    )}
                </ModernCard>

                {/* ℹ️ قسم المساعدة الموحد - بدلاً من التشتيت في كل مكان */}
                <ModernCard variant="outlined" style={styles.helpCard}>
                    <View style={styles.helpHeader}>
                        <BrandIcon name="help" size={20} color={theme.colors.primary} />
                        <Text style={styles.helpTitle}>مساعدة ومعلومات</Text>
                    </View>
                    <Text style={styles.helpText}>
                        النظام يعمل آلياً لتحليل السوق وفتح الصفقات المناسبة.
                        يمكنك مراجعة الإعدادات والتاريخ من قائمة التنقل.
                    </Text>
                    <View style={styles.helpActions}>
                        <TouchableOpacity
                            style={styles.helpButton}
                            onPress={() => { hapticLight(); navigation.navigate('Trading'); }}
                        >
                            <BrandIcon name="settings" size={16} color={theme.colors.primary} />
                            <Text style={styles.helpButtonText}>الإعدادات</Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                            style={styles.helpButton}
                            onPress={() => { hapticLight(); navigation.navigate('History'); }}
                        >
                            <BrandIcon name="history" size={16} color={theme.colors.primary} />
                            <Text style={styles.helpButtonText}>سجل التداول</Text>
                        </TouchableOpacity>
                    </View>
                </ModernCard>

                <View style={{ height: 20 }} />
            </ScrollView>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    // ✅ Loading State Styles
    loadingContainer: {
        flex: 1,
        backgroundColor: theme.colors.background,
        justifyContent: 'center',
        alignItems: 'center',
    },
    loadingText: {
        marginTop: theme.spacing.md,
        fontSize: theme.typography.fontSize.base,
        color: theme.colors.textSecondary,
    },
    notificationBtn: {
        width: 44,      // ✅ Touch Target محسّن
        height: 44,
        borderRadius: 22,
        backgroundColor: 'rgba(139, 92, 246, 0.1)',
        alignItems: 'center',
        justifyContent: 'center',
    },
    settingsBtn: {
        width: 44,      // ✅ Touch Target محسّن (كان 36)
        height: 44,
        borderRadius: 22,
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
        alignItems: 'center',
        justifyContent: 'center',
    },
    scrollContent: {
        paddingBottom: theme.spacing.xl,
        paddingHorizontal: theme.spacing.md,
    },
    // ✅ Hero Card - بطاقة الرصيد الرئيسية
    heroCard: {
        marginBottom: theme.spacing.md,
    },
    modeBar: {
        flexDirection: isRTL ? 'row-reverse' : 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: theme.spacing.md,
    },
    lastUpdate: {
        fontSize: theme.typography.fontSize.xs,
        color: theme.colors.textSecondary,
    },
    modeIndicator: {
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 12,
        borderWidth: 1,
        backgroundColor: 'rgba(0,0,0,0.3)',
    },
    modeText: {
        fontSize: 12,
        fontWeight: 'bold',
    },
    adminBanner: {
        marginBottom: theme.spacing.md,
    },
    adminWarningContent: {
        flexDirection: isRTL ? 'row-reverse' : 'row',
        alignItems: 'center',
    },
    iconContainer: {
        marginEnd: theme.spacing.md,
        padding: 8,
        backgroundColor: 'rgba(0,0,0,0.2)',
        borderRadius: theme.borderRadius.full,
    },
    textContainer: {
        flex: 1,
    },
    adminWarningTitle: {
        fontSize: theme.typography.fontSize.md,
        fontWeight: theme.typography.fontWeight.bold,
        marginBottom: 2,
    },
    adminWarningText: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.textSecondary,
    },
    chartContainer: {
        marginBottom: theme.spacing.md,
    },
    // ✅ Section Titles - L2 (مهم)
    sectionTitle: {
        ...theme.hierarchy.secondary,
        color: theme.colors.text,
        textAlign: isRTL ? 'right' : 'left',
        marginBottom: theme.spacing.md,
    },
    statsCard: {
        marginBottom: theme.spacing.md,
    },
    // بطاقة العملات المؤهلة
    coinsCard: {
        marginBottom: theme.spacing.md,
    },
    coinsSectionHeader: {
        flexDirection: 'row-reverse',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: theme.spacing.sm,
    },
    coinsCount: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.primary,
        fontWeight: '600',
    },
    coinsRow: {
        flexDirection: 'row-reverse',
        flexWrap: 'wrap',
        gap: 8,
    },
    coinBadge: {
        backgroundColor: theme.colors.primary + '20',
        borderRadius: 8,
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderWidth: 1,
        borderColor: theme.colors.primary + '40',
    },
    coinSymbol: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.primary,
        fontWeight: '600',
    },
    // عرض تفصيلي للعملات
    coinDetailRow: {
        flexDirection: 'row-reverse',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border + '30',
    },
    coinMainInfo: {
        flexDirection: 'row-reverse',
        alignItems: 'center',
        gap: 10,
    },
    coinIcon: {
        width: 32,
        height: 32,
        borderRadius: 16,
        backgroundColor: theme.colors.primary + '20',
    },
    coinIconFallback: {
        width: 36,
        height: 36,
        borderRadius: 18,
        backgroundColor: theme.colors.primary,
        justifyContent: 'center',
        alignItems: 'center',
    },
    coinIconText: {
        fontSize: 16,
        fontWeight: '700',
        color: '#FFFFFF',
    },
    coinRankBadge: {
        width: 28,
        height: 28,
        borderRadius: 14,
        backgroundColor: theme.colors.primary + '30',
        justifyContent: 'center',
        alignItems: 'center',
        borderWidth: 1,
        borderColor: theme.colors.primary,
    },
    coinRankText: {
        fontSize: 14,
        fontWeight: '700',
        color: theme.colors.primary,
    },
    coinSymbolLarge: {
        fontSize: theme.typography.fontSize.lg,
        fontWeight: '700',
        color: theme.colors.text,
    },
    coinScoreBadge: {
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 6,
    },
    coinScoreText: {
        fontSize: theme.typography.fontSize.sm,
        fontWeight: '700',
    },
    coinStats: {
        flexDirection: 'row-reverse',
        gap: 16,
    },
    coinStatItem: {
        alignItems: 'center',
    },
    coinStatValue: {
        fontSize: theme.typography.fontSize.md,
        fontWeight: '600',
        color: theme.colors.text,
    },
    coinStatLabel: {
        fontSize: theme.typography.fontSize.xs,
        color: theme.colors.textSecondary,
        marginTop: 2,
    },
    cardTitle: {
        fontSize: theme.typography.fontSize.lg,
        fontWeight: theme.typography.fontWeight.bold,
        color: theme.colors.primary,
        marginBottom: theme.spacing.md,
        textAlign: 'right',
    },
    portfolioContent: {
        gap: theme.spacing.md,
    },
    balanceSection: {
        alignItems: 'center',
        paddingVertical: theme.spacing.sm,
    },
    // L4 (ثانوي)
    balanceLabel: {
        ...theme.hierarchy.caption,
        color: theme.colors.textSecondary,
        marginBottom: theme.spacing.xs,
    },
    // L1 (حرج - الرصيد الرئيسي)
    balanceValue: {
        ...theme.hierarchy.hero,
        color: theme.colors.white,
        textShadowColor: theme.colors.primary,
        textShadowOffset: { width: 0, height: 0 },
        textShadowRadius: 10,
    },
    currency: {
        fontSize: theme.typography.fontSize.lg,
        color: theme.colors.primary,
    },
    divider: {
        height: 1,
        backgroundColor: theme.colors.border,
        marginVertical: theme.spacing.xs,
    },
    statsRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
    },
    statItem: {
        alignItems: 'center',
        flex: 1,
    },
    // L5 (تفاصيل)
    statLabel: {
        ...theme.hierarchy.tiny,
        color: theme.colors.textSecondary,
        marginBottom: 4,
    },
    // L3 (عادي)
    statValue: {
        ...theme.hierarchy.body,
        fontWeight: '600',
        color: theme.colors.text,
    },
    statsGrid: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: theme.spacing.md,
    },
    gridItem: {
        width: '48%',
        backgroundColor: theme.colors.background,
        borderRadius: theme.borderRadius.md,
        padding: theme.spacing.md,
        alignItems: 'center',
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    gridLabel: {
        fontSize: theme.typography.fontSize.xs,
        color: theme.colors.textSecondary,
        marginBottom: theme.spacing.sm,
    },
    gridValue: {
        fontSize: theme.typography.fontSize.lg,
        fontWeight: theme.typography.fontWeight.bold,
        color: theme.colors.text,
    },
    pnlContent: {
        flexDirection: 'row',
        justifyContent: 'space-around',
    },
    pnlItem: {
        alignItems: 'center',
    },
    pnlLabel: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.textSecondary,
        marginBottom: theme.spacing.sm,
    },
    pnlValue: {
        fontSize: theme.typography.fontSize.xl,
        fontWeight: theme.typography.fontWeight.bold,
    },
    // 🔑 Styles للبطاقة التوجيهية
    setupCard: {
        marginBottom: theme.spacing.md,
    },
    setupCardContent: {
        flexDirection: isRTL ? 'row-reverse' : 'row',
        alignItems: 'flex-start',
        marginBottom: theme.spacing.md,
    },
    setupIconContainer: {
        width: 48,
        height: 48,
        borderRadius: 24,
        backgroundColor: colors.semantic.warning + '20',
        alignItems: 'center',
        justifyContent: 'center',
        marginEnd: theme.spacing.md,
    },
    setupIcon: {
        fontSize: 24,
    },
    setupTextContainer: {
        flex: 1,
    },
    setupTitle: {
        fontSize: typography.size.lg,
        fontWeight: typography.weight.bold,
        color: colors.semantic.warning,
        marginBottom: theme.spacing.xs,
        textAlign: isRTL ? 'right' : 'left',
    },
    setupDescription: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.textSecondary,
        lineHeight: 20,
        textAlign: isRTL ? 'right' : 'left',
    },
    setupSteps: {
        backgroundColor: 'rgba(0, 0, 0, 0.2)',
        borderRadius: theme.borderRadius.md,
        padding: theme.spacing.md,
        marginBottom: theme.spacing.md,
    },
    setupStep: {
        flexDirection: isRTL ? 'row-reverse' : 'row',
        alignItems: 'center',
        marginBottom: theme.spacing.sm,
    },
    stepNumber: {
        width: 24,
        height: 24,
        borderRadius: 12,
        backgroundColor: theme.colors.warning,
        color: theme.colors.background,
        fontSize: 14,
        fontWeight: 'bold',
        textAlign: 'center',
        lineHeight: 24,
        marginEnd: theme.spacing.sm,
    },
    stepText: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.text,
        flex: 1,
        textAlign: isRTL ? 'right' : 'left',
    },
    setupButton: {
        backgroundColor: colors.brand.primary,
        borderRadius: theme.borderRadius.md,
        paddingVertical: theme.spacing.md,
        flexDirection: 'row-reverse',
        alignItems: 'center',
        justifyContent: 'center',
        gap: theme.spacing.xs,
        marginBottom: theme.spacing.sm,
        ...shadows.sm,
    },
    setupButtonText: {
        fontSize: typography.size.md,
        fontWeight: typography.weight.bold,
        color: colors.text.inverse,
    },
    setupNote: {
        fontSize: theme.typography.fontSize.xs,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        fontStyle: 'italic',
    },
    // ✅ Styles جديدة للتصميم المبسط
    mainBalanceCard: {
        alignItems: 'center',
        paddingVertical: theme.spacing.md,
    },
    pnlBadge: {
        fontSize: theme.typography.fontSize.sm,
        fontWeight: '600',
        marginTop: theme.spacing.xs,
    },
    quickStatsRow: {
        flexDirection: 'row-reverse',
        justifyContent: 'space-around',
        alignItems: 'center',
        paddingVertical: theme.spacing.sm,
    },
    quickStatItem: {
        alignItems: 'center',
        flex: 1,
    },
    quickStatValue: {
        fontSize: theme.typography.fontSize.xl,
        fontWeight: theme.typography.fontWeight.bold,
        color: theme.colors.text,
    },
    quickStatLabel: {
        fontSize: theme.typography.fontSize.xs,
        color: theme.colors.textSecondary,
        marginTop: 2,
    },
    quickStatDivider: {
        width: 1,
        height: 30,
        backgroundColor: theme.colors.border,
    },
    // ✅ Styles لملخص المحفظتين للأدمن
    adminPortfoliosCard: {
        marginBottom: theme.spacing.md,
    },
    portfoliosSummary: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        gap: 12,
    },
    portfolioSummaryItem: {
        flex: 1,
        backgroundColor: theme.colors.background,
        borderRadius: 12,
        padding: 16,
        alignItems: 'center',
        borderWidth: 2,
    },
    portfolioSummaryIcon: {
        fontSize: 28,
        marginBottom: 8,
    },
    portfolioSummaryLabel: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.textSecondary,
        fontWeight: '600',
        marginBottom: 4,
    },
    portfolioSummaryValue: {
        fontSize: theme.typography.fontSize.lg,
        fontWeight: 'bold',
        color: theme.colors.text,
        marginBottom: 4,
    },
    portfolioSummaryPnL: {
        fontSize: theme.typography.fontSize.sm,
        fontWeight: '600',
    },
    // ✅ الشارت داخل بطاقة الرصيد
    chartInCard: {
        marginTop: theme.spacing.md,
        paddingTop: theme.spacing.md,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border + '20',
    },
    // ✅ بانر وضع التداول
    modeBanner: {
        marginHorizontal: 0,
        marginBottom: theme.spacing.md,
        borderRadius: theme.borderRadius.md,
        paddingVertical: theme.spacing.sm,
        paddingHorizontal: theme.spacing.md,
        borderWidth: 1,
        borderColor: 'rgba(255, 255, 255, 0.1)',
    },
    modeBannerContent: {
        flexDirection: 'row-reverse',
        alignItems: 'center',
        justifyContent: 'center',
        gap: theme.spacing.sm,
    },
    modeBannerText: {
        fontSize: theme.typography.fontSize.sm,
        fontWeight: '600',
        textAlign: 'center',
    },
    // ✅ Styles للعملات قيد المراقبة
    coinsHint: {
        fontSize: theme.typography.fontSize.xs,
    },
    // ✅ شارة توضيحية لنوع البيانات
    dataTypeBadge: {
        fontSize: theme.typography.fontSize.xs,
        color: theme.colors.textSecondary,
        backgroundColor: theme.colors.background + '20',
        paddingHorizontal: theme.spacing.xs,
        paddingVertical: 2,
        borderRadius: theme.borderRadius.sm,
        marginTop: 4,
        textAlign: 'center',
    },
    // ✅ Styles للتحذير الواضح في Dashboard
    dashboardWarningCard: {
        marginHorizontal: theme.spacing.md,
        marginBottom: theme.spacing.md,
        borderRadius: theme.borderRadius.md,
        paddingVertical: theme.spacing.md,
        paddingHorizontal: theme.spacing.md,
        borderWidth: 2,
        borderColor: theme.colors.warning,
        backgroundColor: theme.colors.warning + '10',
    },
    warningHeader: {
        flexDirection: 'row-reverse',
        alignItems: 'center',
        justifyContent: 'flex-start',
        marginBottom: theme.spacing.sm,
        gap: theme.spacing.sm,
    },
    warningTitle: {
        fontSize: theme.typography.fontSize.base,
        fontWeight: '700',
        color: theme.colors.warning,
    },
    warningText: {
        fontSize: theme.typography.fontSize.sm,
        fontWeight: '500',
        color: theme.colors.text,
        lineHeight: 20,
        textAlign: 'right',
    },
    // ✅ Style لشارة توضيح مصدر البيانات
    dataSourceBadge: {
        fontSize: theme.typography.fontSize.xs,
        color: theme.colors.textSecondary,
        backgroundColor: 'rgba(128, 128, 128, 0.1)',
        paddingHorizontal: theme.spacing.xs,
        paddingVertical: 2,
        borderRadius: theme.borderRadius.sm,
        marginTop: 4,
        textAlign: 'center',
    },
    // ✅ Styles لحالة النظام
    systemStatusCard: {
        marginHorizontal: theme.spacing.md,
        marginBottom: theme.spacing.md,
    },
    systemStatusRow: {
        flexDirection: 'row-reverse',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        gap: theme.spacing.md,
    },
    systemStatusItem: {
        flex: 1,
        alignItems: 'center',
    },
    systemStatusHeader: {
        flexDirection: 'row-reverse',
        alignItems: 'center',
        marginBottom: theme.spacing.sm,
        gap: theme.spacing.xs,
    },
    systemStatusTitle: {
        fontSize: theme.typography.fontSize.sm,
        fontWeight: '600',
        color: theme.colors.text,
        textAlign: 'center',
    },
    systemStatusValue: {
        fontSize: theme.typography.fontSize.xs,
        fontWeight: '500',
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginBottom: theme.spacing.xs,
    },
    systemStatusDescription: {
        fontSize: theme.typography.fontSize.xxs,
        color: theme.colors.textSecondary,
        lineHeight: 16,
        textAlign: 'center',
    },
    systemStatusDivider: {
        width: 1,
        height: 60,
        backgroundColor: theme.colors.border,
        marginHorizontal: theme.spacing.sm,
    },
    systemStatusFooter: {
        marginTop: theme.spacing.md,
        paddingTop: theme.spacing.sm,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
    },
    systemStatusLastUpdate: {
        fontSize: theme.typography.fontSize.xxs,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginBottom: theme.spacing.xs,
    },
    systemStatusNote: {
        fontSize: theme.typography.fontSize.xs,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        fontStyle: 'italic',
        lineHeight: 18,
    },
    noTradesHint: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        lineHeight: 20,
        marginTop: 8,
    },
    emptyCoinsContainer: {
        alignItems: 'center',
        paddingVertical: 32,
    },
    emptyCoinsText: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
        marginTop: 16,
        textAlign: 'center',
    },
    emptyCoinsHint: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        lineHeight: 20,
        marginTop: 8,
        paddingHorizontal: 16,
    },
    coinsCount: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        marginBottom: 8,
    },
    // ✅ Styles لحالة عدم وجود صفقات
    noTradesContainer: {
        alignItems: 'center',
        paddingVertical: theme.spacing.lg,
    },
    noTradesText: {
        fontSize: theme.typography.fontSize.base,
        color: theme.colors.text,
        marginTop: theme.spacing.sm,
        fontWeight: '600',
    },
    noTradesHint: {
        fontSize: theme.typography.fontSize.xs,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginTop: theme.spacing.xs,
        paddingHorizontal: theme.spacing.md,
    },
    // ✅ قسم المساعدة الموحد
    helpCard: {
        marginBottom: theme.spacing.md,
    },
    helpHeader: {
        flexDirection: 'row-reverse',
        alignItems: 'center',
        marginBottom: theme.spacing.sm,
        gap: theme.spacing.sm,
    },
    helpTitle: {
        fontSize: theme.typography.fontSize.md,
        fontWeight: '600',
        color: theme.colors.primary,
        textAlign: 'right',
    },
    helpText: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.textSecondary,
        textAlign: 'right',
        lineHeight: 20,
        marginBottom: theme.spacing.md,
    },
    helpActions: {
        flexDirection: 'row-reverse',
        justifyContent: 'space-around',
        gap: theme.spacing.sm,
    },
    helpButton: {
        flexDirection: 'row-reverse',
        alignItems: 'center',
        backgroundColor: theme.colors.primary + '10',
        paddingHorizontal: theme.spacing.md,
        paddingVertical: theme.spacing.sm,
        borderRadius: theme.borderRadius.md,
        gap: theme.spacing.xs,
    },
    helpButtonText: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.primary,
        fontWeight: '600',
    },
});

export default DashboardScreen;
