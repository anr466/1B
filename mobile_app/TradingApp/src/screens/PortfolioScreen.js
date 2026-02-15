/**
 * Portfolio Screen - شاشة المحفظة المحسّنة
 * ✅ رسم بياني لنمو المحفظة
 * ✅ Empty State محسّن مع زر ربط Binance
 * ✅ تصميم نظيف ومركز
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
    View,
    Text,
    ScrollView,
    StyleSheet,
    TouchableOpacity,
    RefreshControl,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useNavigation } from '@react-navigation/native';
import { theme } from '../theme/theme';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing, typography, components, shadows } from '../theme/designSystem';
import { useBackHandlerWithConfirmation } from '../utils/BackHandlerUtil';
import ToastService from '../services/ToastService';
import ModernCard from '../components/ModernCard';
import { useTradingModeContext } from '../context/TradingModeContext';
import { usePortfolioContext } from '../context/PortfolioContext';
import { PortfolioSkeleton } from '../components/SkeletonLoader';
import { useIsAdmin } from '../hooks/useIsAdmin';
import AdminModeBanner from '../components/AdminModeBanner';
// ✅ AdminModeSwitcher تم نقله إلى GlobalHeader
import PortfolioChart from '../components/charts/PortfolioChart';
import PortfolioDistributionChart from '../components/charts/PortfolioDistributionChart';
import BrandIcon from '../components/BrandIcons';

const PortfolioScreen = ({ user: propUser }) => {
    const navigation = useNavigation();
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [userId, setUserId] = useState(propUser?.id || null);

    // ✅ إصلاح Race Conditions - منع تحديث State على unmounted component
    const isMountedRef = useRef(true);

    // ✅ استخدام PortfolioContext
    const {
        portfolio,
        fetchPortfolio,
    } = usePortfolioContext();

    // ✅ استخدام Hook موحد لفحص الأدمن (يجب أن يكون قبل استخدامه)
    const isAdmin = useIsAdmin(propUser);

    // ✅ استخدام TradingModeContext
    const {
        tradingMode,
        refreshCounter,
        getCurrentViewMode,
    } = useTradingModeContext();

    // ✅ تحديد نوع البيانات (حقيقي/وهمي)
    const isDemoData = tradingMode === 'demo' || isAdmin;

    const currentViewMode = getCurrentViewMode();

    useBackHandlerWithConfirmation(true);

    // ✅ Cleanup عند unmount
    useEffect(() => {
        isMountedRef.current = true;
        return () => {
            isMountedRef.current = false;
        };
    }, []);

    // ✅ FIX: Debounced refresh to prevent duplicate API calls
    const lastRefreshTimeRef = useRef(0);
    const DEBOUNCE_DELAY = 1000; // 1 second

    // ✅ loadPortfolioData مع useCallback و debouncing
    const loadPortfolioData = useCallback(async () => {
        if (!isMountedRef.current) { return; }

        // ✅ Prevent duplicate calls within 1 second
        const now = Date.now();
        if (now - lastRefreshTimeRef.current < DEBOUNCE_DELAY) {
            console.log('[PortfolioScreen] Debounced - skipping duplicate refresh');
            return;
        }
        lastRefreshTimeRef.current = now;

        try {
            if (isMountedRef.current) {
                setLoading(true);
            }

            let currentUserId = userId || propUser?.id;

            if (!currentUserId) {
                const userData = await AsyncStorage.getItem('userData');
                if (userData) {
                    try {
                        const parsedUser = JSON.parse(userData);
                        currentUserId = parsedUser.id;
                        if (isMountedRef.current) {
                            setUserId(currentUserId);
                        }
                    } catch (parseError) {
                        console.error('[ERROR] خطأ في تحليل بيانات المستخدم:', parseError);
                    }
                }
            }

            if (!isMountedRef.current) { return; }

            await fetchPortfolio();
        } catch (error) {
            console.error('[ERROR] فشل تحميل بيانات المحفظة:', error);

            if (isMountedRef.current) {
                let errorMessage = 'فشل تحميل بيانات المحفظة';
                if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
                    errorMessage = '⏱️ انتهى وقت الانتظار\n\nتحقق من الاتصال وحاول مرة أخرى';
                } else if (error?.code === 'ERR_NETWORK' || error?.message?.includes('Network Error')) {
                    errorMessage = '❌ لا يوجد اتصال بالإنترنت\n\nتحقق من اتصالك وحاول مرة أخرى';
                } else if (error?.response?.status === 401) {
                    errorMessage = '❌ انتهت صلاحية الجلسة\n\nسيتم إعادة تسجيل الدخول...';
                } else {
                    errorMessage = `❌ خطأ في جلب المحفظة\n\n${error?.message || 'حاول مرة أخرى'}`;
                }

                ToastService.showError(errorMessage);
            }
        } finally {
            if (isMountedRef.current) {
                setLoading(false);
            }
        }
    }, [userId, propUser, fetchPortfolio]);

    useEffect(() => {
        if (propUser?.id) {
            setUserId(propUser.id);
        }
        loadPortfolioData();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [propUser?.id]); // ✅ فقط عند تغيير user ID

    useEffect(() => {
        if (refreshCounter > 0) {
            // ✅ تأخير عشوائي لمنع الطلبات المتزامنة (429 Rate Limit)
            const delay = Math.random() * 500 + 300; // 300-800ms
            const timer = setTimeout(() => {
                loadPortfolioData();
            }, delay);
            return () => clearTimeout(timer);
        }
    }, [refreshCounter, loadPortfolioData]);

    const onRefresh = useCallback(async () => {
        if (!isMountedRef.current) { return; }
        if (isMountedRef.current) {
            setRefreshing(true);
        }
        await loadPortfolioData();
        if (isMountedRef.current) {
            setRefreshing(false);
        }
    }, [loadPortfolioData]);

    // Loading State
    if (loading) {
        return (
            <View style={styles.container}>
                <PortfolioSkeleton />
            </View>
        );
    }

    // ✅ Empty State محسّن
    if (!portfolio) {
        return (
            <View style={styles.container}>
                <ScrollView
                    contentContainerStyle={styles.emptyStateContainer}
                    refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.primary} />}
                >
                    <View style={styles.emptyStateContent}>
                        <Text style={styles.emptyStateIcon}>💼</Text>
                        <Text style={styles.emptyStateTitle}>محفظتك فارغة</Text>
                        <Text style={styles.emptyStateDescription}>
                            لبدء التداول الآلي وعرض بيانات محفظتك، تحتاج لربط حسابك على Binance.
                        </Text>

                        <TouchableOpacity
                            style={styles.connectButton}
                            onPress={() => navigation.navigate('Trading', { screen: 'BinanceKeys' })}
                            activeOpacity={0.8}
                        >
                            <Text style={styles.connectButtonText}>🔗 ربط حساب Binance</Text>
                        </TouchableOpacity>

                        <TouchableOpacity
                            style={styles.refreshButton}
                            onPress={onRefresh}
                            activeOpacity={0.7}
                        >
                            <Text style={styles.refreshButtonText}>🔄 تحديث</Text>
                        </TouchableOpacity>
                    </View >
                </ScrollView >
            </View >
        );
    }

    // حساب قيم الرسم البياني - ✅ بيانات حقيقية فقط من API (بدون بيانات افتراضية)
    const chartBalance = (() => {
        const val = parseFloat(String(portfolio?.totalBalance || '').replace(/[^0-9.-]/g, ''));
        return !isNaN(val) && val > 0 ? val : null;
    })();

    const chartInitialBalance = (() => {
        const val = parseFloat(String(portfolio?.initialBalance || '').replace(/[^0-9.-]/g, ''));
        return !isNaN(val) && val > 0 ? val : null;
    })();

    return (
        <View style={styles.container}>
            {/* ✅ Banner تحذيري للأدمن - مع تمرير وضع التداول */}
            {isAdmin && <AdminModeBanner tradingMode={tradingMode} />}

            <ScrollView
                contentContainerStyle={styles.scrollContent}
                refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={theme.colors.primary} />}
            >
                {/* ═══════════════ الرسم البياني (يعرض الرصيد داخله) ═══════════════ */}
                <View style={styles.chartContainer}>
                    <PortfolioChart
                        userId={userId}
                        currentBalance={chartBalance}
                        initialBalance={chartInitialBalance}
                        isAdmin={isAdmin}
                        tradingMode={tradingMode}
                    />
                </View>

                {/* ═══════════════ رسم بياني توزيع الأصول ═══════════════ */}
                {userId && (
                    <View style={styles.chartContainer}>
                        <PortfolioDistributionChart
                            userId={userId}
                            isAdmin={isAdmin}
                            tradingMode={tradingMode}
                        />
                    </View>
                )}

                {/* ═══════════════ توزيع الرصيد ═══════════════ */}
                <ModernCard style={styles.card}>
                    <View style={styles.cardHeader}>
                        <BrandIcon name="pie-chart" size={20} color={colors.brand.primary} />
                        <Text style={styles.cardTitle}>توزيع الرصيد</Text>
                    </View>

                    <View style={styles.balanceRow}>
                        <View style={styles.balanceItem}>
                            <View style={[styles.indicator, { backgroundColor: theme.colors.success }]} />
                            <Text style={styles.balanceLabel}>الرصيد المتاح</Text>
                        </View>
                        <Text style={styles.balanceValue}>{portfolio?.availableBalance || '0.00'}</Text>
                    </View>

                    <View style={styles.divider} />

                    <View style={styles.balanceRow}>
                        <View style={styles.balanceItem}>
                            <View style={[styles.indicator, { backgroundColor: theme.colors.warning }]} />
                            <Text style={styles.balanceLabel}>المبلغ المستثمر</Text>
                        </View>
                        <Text style={styles.balanceValue}>{portfolio?.investedBalance || portfolio?.investedAmount || '0.00'}</Text>
                    </View>
                </ModernCard>

                {/* ═══════════════ الأداء ═══════════════ */}
                <ModernCard style={styles.card}>
                    <View style={styles.cardHeader}>
                        <BrandIcon name="trending-up" size={20} color={colors.brand.primary} />
                        <Text style={styles.cardTitle}>الأداء</Text>
                    </View>

                    <View style={styles.performanceGrid}>
                        <View style={styles.performanceItem}>
                            <Text style={styles.performanceLabel}>الربح/الخسارة</Text>
                            <Text style={[
                                styles.performanceValue,
                                { color: String(portfolio?.totalPnL || '').includes('-') ? theme.colors.error : theme.colors.success },
                            ]}>
                                {portfolio?.totalPnL || '+0.00'}
                            </Text>
                        </View>

                        <View style={styles.performanceDivider} />

                        <View style={styles.performanceItem}>
                            <Text style={styles.performanceLabel}>النسبة المئوية</Text>
                            <Text style={[
                                styles.performanceValue,
                                { color: String(portfolio?.totalPnLPercentage || portfolio?.dailyPnLPercentage || '').includes('-') ? theme.colors.error : theme.colors.success },
                            ]}>
                                {portfolio?.totalPnLPercentage || portfolio?.dailyPnLPercentage || '+0.0'}%
                            </Text>
                        </View>
                    </View>
                </ModernCard>

                {/* ═══════════════ معلومات المحفظة ═══════════════ */}
                <ModernCard variant="outlined" style={styles.card}>
                    <View style={styles.cardHeader}>
                        <BrandIcon name="info" size={20} color={colors.brand.primary} />
                        <Text style={styles.cardTitle}>معلومات المحفظة</Text>
                    </View>

                    <View style={styles.infoRow}>
                        <Text style={styles.infoLabel}>حالة الاتصال</Text>
                        <Text style={styles.infoValue}>
                            {portfolio?.hasKeys === true
                                ? '✅ مفاتيح Binance موجودة'
                                : portfolio?.hasKeys === false
                                    ? '❌ لا توجد مفاتيح Binance'
                                    : '⏳ جاري التحقق...'
                            }
                        </Text>
                    </View>

                    <View style={styles.infoRow}>
                        <Text style={styles.infoLabel}>العملة</Text>
                        <Text style={styles.infoValue}>
                            {portfolio?.currency || 'USDT'}
                        </Text>
                    </View>

                    <View style={styles.infoRow}>
                        <Text style={styles.infoLabel}>آخر تحديث</Text>
                        <Text style={styles.infoValue}>
                            {portfolio?.lastUpdate
                                ? new Date(portfolio.lastUpdate).toLocaleString('ar-SA', {
                                    hour: '2-digit',
                                    minute: '2-digit',
                                    day: 'numeric',
                                    month: 'short',
                                })
                                : 'الآن'}
                        </Text>
                    </View>
                </ModernCard>

                <View style={{ height: 30 }} />
            </ScrollView>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    scrollContent: {
        paddingHorizontal: 16,
        paddingTop: 8,
    },
    // Hero Card
    heroCard: {
        marginBottom: 16,
    },
    heroHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
    },
    heroLabel: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    modeBadge: {
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 12,
    },
    modeBadgeText: {
        fontSize: 12,
        fontWeight: '600',
    },
    heroBalance: {
        fontSize: 32,
        fontWeight: '700',
        color: theme.colors.text,
        marginBottom: 8,
    },
    currency: {
        fontSize: 18,
        fontWeight: '400',
        color: theme.colors.textSecondary,
    },
    pnlRow: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    pnlValue: {
        fontSize: 16,
        fontWeight: '600',
        marginEnd: 8,
    },
    pnlPercent: {
        fontSize: 14,
    },
    // Chart
    chartContainer: {
        marginBottom: 16,
    },
    // Cards
    card: {
        marginBottom: 16,
    },
    // Card Header with Icon
    cardHeader: {
        flexDirection: 'row-reverse',
        alignItems: 'center',
        gap: spacing.xs,
        marginBottom: 16,
    },
    // L2 (مهم - عنوان البطاقة)
    cardTitle: {
        ...theme.hierarchy.secondary,
        color: theme.colors.text,
    },
    // Balance Distribution
    balanceRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 12,
    },
    balanceItem: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    indicator: {
        width: 8,
        height: 8,
        borderRadius: 4,
        marginEnd: spacing.sm,
    },
    // L4 (ثانوي)
    balanceLabel: {
        ...theme.hierarchy.caption,
        color: theme.colors.textSecondary,
    },
    // L3 (عادي)
    balanceValue: {
        ...theme.hierarchy.body,
        fontWeight: '600',
        color: theme.colors.text,
    },
    divider: {
        height: 1,
        backgroundColor: colors.border.default,
    },
    // Performance
    performanceGrid: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    performanceItem: {
        flex: 1,
        alignItems: 'center',
    },
    performanceDivider: {
        width: 1,
        height: 40,
        backgroundColor: colors.border.default,
    },
    // L5 (تفاصيل)
    performanceLabel: {
        ...theme.hierarchy.tiny,
        color: theme.colors.textSecondary,
        marginBottom: 4,
    },
    // L2 (مهم - الأداء)
    performanceValue: {
        ...theme.hierarchy.secondary,
    },
    // Info
    infoRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        paddingVertical: spacing.sm,
        borderBottomWidth: 1,
        borderBottomColor: colors.border.default,
    },
    // L4 (ثانوي)
    infoLabel: {
        ...theme.hierarchy.caption,
        color: theme.colors.textSecondary,
    },
    infoValue: {
        fontSize: 14,
        color: theme.colors.text,
        fontWeight: '500',
    },
    // Empty State
    emptyStateContainer: {
        flexGrow: 1,
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: 32,
    },
    emptyStateContent: {
        alignItems: 'center',
        width: '100%',
    },
    emptyStateIcon: {
        fontSize: 72,
        marginBottom: 20,
    },
    emptyStateTitle: {
        fontSize: 22,
        fontWeight: '700',
        color: theme.colors.text,
        marginBottom: 12,
        textAlign: 'center',
    },
    emptyStateDescription: {
        fontSize: 15,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        lineHeight: 24,
        marginBottom: 32,
    },
    connectButton: {
        backgroundColor: colors.brand.primary,
        paddingVertical: spacing.md,
        paddingHorizontal: spacing.xxl,
        borderRadius: components.button.primary.borderRadius,
        marginBottom: spacing.lg,
        width: '100%',
        ...shadows.sm,
    },
    connectButtonText: {
        color: colors.text.primary,
        fontSize: typography.size.md,
        fontWeight: typography.weight.bold,
        textAlign: 'center',
    },
    refreshButton: {
        paddingVertical: 12,
        paddingHorizontal: 24,
    },
    refreshButtonText: {
        color: theme.colors.textSecondary,
        fontSize: 14,
    },
    // ✅ Styles لبانر الوضع
    modeBanner: {
        marginHorizontal: spacing.md,
        marginBottom: spacing.md,
        borderRadius: 8,
        paddingVertical: spacing.sm,
        paddingHorizontal: spacing.md,
        borderWidth: 1,
        borderColor: 'rgba(255, 255, 255, 0.1)',
    },
    modeBannerContent: {
        flexDirection: 'row-reverse',
        alignItems: 'center',
        justifyContent: 'center',
        gap: spacing.sm,
    },
    modeBannerText: {
        fontSize: typography.size.sm,
        fontWeight: '600',
        textAlign: 'center',
    },
    // ✅ Style لشارة توضيح نوع البيانات
    dataTypeBadge: {
        fontSize: typography.size.xs,
        fontWeight: '500',
        color: '#666666',  // ✅ لون رمادي للبيانات الوهمية
        backgroundColor: 'rgba(128, 128, 128, 0.1)',  // ✅ خلفية شفافة
        paddingHorizontal: spacing.xs,
        paddingVertical: 2,
        borderRadius: 4,
        marginLeft: spacing.xs,
    },
    // ✅ Style لشارة توضيح مصدر البيانات
    dataSourceBadge: {
        fontSize: typography.size.xxs,
        fontWeight: '400',
        color: '#888888',
        backgroundColor: 'rgba(128, 128, 128, 0.05)',
        paddingHorizontal: spacing.xs,
        paddingVertical: 1,
        borderRadius: 2,
        marginLeft: spacing.xs,
    },
});

export default PortfolioScreen;
