/**
 * Mini Portfolio Chart - نسخة مبسطة من شارت النمو
 * ✅ ارتفاع 180px فقط (بدلاً من 280px)
 * ✅ فترة واحدة فقط (7D)
 * ✅ بدون أزرار تبديل الفترات
 * ✅ بدون Grid Lines
 * ✅ خط بسيط وسريع
 * ✅ الهدف: نظرة سريعة - هل أنا صاعد/نازل؟
 */

import React, { useMemo, useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, Dimensions, ActivityIndicator, I18nManager } from 'react-native';
import Svg, { Path, Defs, LinearGradient, Stop } from 'react-native-svg';
import { theme } from '../../theme/theme';
import DatabaseApiService from '../../services/DatabaseApiService';

const isRTL = I18nManager.isRTL;

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const MiniPortfolioChart = React.memo(({
    userId,
    currentBalance = null,
    isAdmin = false,
    tradingMode = 'auto',
    width = SCREEN_WIDTH - 48,
    height = 180,
}) => {
    const [chartData, setChartData] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [growthPercentage, setGrowthPercentage] = useState(0);

    // جلب بيانات آخر 7 أيام فقط
    const loadChartData = useCallback(async () => {
        if (!userId) {return;}

        setIsLoading(true);
        try {
            const response = await DatabaseApiService.getPortfolioHistory(userId, 7, isAdmin, tradingMode);

            if (response?.success && response?.data) {
                const historyData = response.data;

                if (historyData.dates && historyData.balances && historyData.balances.length > 0) {
                    const formattedData = historyData.dates.map((date, index) => ({
                        value: historyData.balances[index] || 0,
                        date: date,
                    }));
                    setChartData(formattedData);

                    // حساب نسبة النمو
                    const firstValue = formattedData[0]?.value || 0;
                    const lastValue = formattedData[formattedData.length - 1]?.value || 0;
                    if (firstValue > 0) {
                        const growth = ((lastValue - firstValue) / firstValue) * 100;
                        setGrowthPercentage(growth);
                    }
                } else {
                    setChartData([]);
                    setGrowthPercentage(0);
                }
            } else {
                setChartData([]);
                setGrowthPercentage(0);
            }
        } catch (error) {
            console.error('[MiniChart] خطأ في جلب البيانات:', error);
            setChartData([]);
            setGrowthPercentage(0);
        } finally {
            setIsLoading(false);
        }
    }, [userId, isAdmin, tradingMode]);

    useEffect(() => {
        loadChartData();
    }, [loadChartData]);

    // إنشاء بيانات العرض
    const displayData = useMemo(() => {
        if (chartData && chartData.length > 0) {return chartData;}

        // بيانات افتراضية إذا لم تكن هناك بيانات
        if (currentBalance && currentBalance > 0) {
            return [
                { value: currentBalance, date: new Date().toISOString() },
                { value: currentBalance, date: new Date().toISOString() },
            ];
        }
        return [];
    }, [chartData, currentBalance]);

    // حساب القيم والمسارات
    const chartCalculations = useMemo(() => {
        if (displayData.length === 0) {
            return {
                path: '',
                gradientPath: '',
                minValue: 0,
                maxValue: 0,
                padding: { top: 20, right: 20, bottom: 20, left: 20 },
            };
        }

        const padding = { top: 20, right: 20, bottom: 20, left: 20 };
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;

        const values = displayData.map(d => d.value);
        const minValue = Math.min(...values);
        const maxValue = Math.max(...values);
        const valueRange = maxValue - minValue || 1;

        // حساب النقاط
        const points = displayData.map((item, index) => {
            const x = padding.left + (index / (displayData.length - 1 || 1)) * chartWidth;
            const normalizedValue = (item.value - minValue) / valueRange;
            const y = padding.top + chartHeight - (normalizedValue * chartHeight);
            return { x, y };
        });

        // إنشاء المسار الخطي (بدون منحنيات - أبسط)
        let path = `M ${points[0].x} ${points[0].y}`;
        for (let i = 1; i < points.length; i++) {
            path += ` L ${points[i].x} ${points[i].y}`;
        }

        // إنشاء مسار التدرج
        let gradientPath = path;
        gradientPath += ` L ${points[points.length - 1].x} ${height - padding.bottom}`;
        gradientPath += ` L ${points[0].x} ${height - padding.bottom}`;
        gradientPath += ' Z';

        return {
            path,
            gradientPath,
            minValue,
            maxValue,
            padding,
        };
    }, [displayData, width, height]);

    const isPositive = growthPercentage >= 0;
    // ✅ توحيد الألوان مع PortfolioDistributionChart
    const lineColor = isPositive ? theme.colors.primary : theme.colors.secondary;
    const gradientStart = isPositive ? `${theme.colors.primary}33` : `${theme.colors.secondary}33`;
    const gradientEnd = 'rgba(0, 0, 0, 0)';

    if (isLoading) {
        return (
            <View style={[styles.container, { height }]}>
                <ActivityIndicator size="small" color={theme.colors.primary} />
                <Text style={styles.loadingText}>جاري التحميل...</Text>
            </View>
        );
    }

    if (displayData.length === 0) {
        return (
            <View style={[styles.container, { height }]}>
                <Text style={styles.emptyText}>لا توجد بيانات</Text>
            </View>
        );
    }

    return (
        <View style={[styles.container, { height }]}>
            {/* الرصيد والنسبة */}
            <View style={styles.header}>
                <Text style={[styles.balance, { writingDirection: 'ltr' }]}>
                    ${currentBalance ? currentBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}
                </Text>
                <View style={styles.changeContainer}>
                    <Text style={[styles.changeText, { color: lineColor, writingDirection: 'ltr' }]}>
                        {isPositive ? '+' : ''}{growthPercentage.toFixed(2)}%
                    </Text>
                    <Text style={styles.changeLabel}>آخر 7 أيام</Text>
                </View>
            </View>

            {/* الرسم البياني */}
            <Svg width={width} height={height - 60}>
                <Defs>
                    <LinearGradient id="miniGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                        <Stop offset="0%" stopColor={gradientStart} stopOpacity="1" />
                        <Stop offset="100%" stopColor={gradientEnd} stopOpacity="1" />
                    </LinearGradient>
                </Defs>

                {/* منطقة التدرج */}
                <Path
                    d={chartCalculations.gradientPath}
                    fill="url(#miniGradient)"
                />

                {/* الخط */}
                <Path
                    d={chartCalculations.path}
                    stroke={lineColor}
                    strokeWidth="2"
                    fill="none"
                />
            </Svg>
        </View>
    );
});

const styles = StyleSheet.create({
    container: {
        backgroundColor: theme.colors.cardBackground,
        borderRadius: 16,
        padding: 16,
        justifyContent: 'center',
        alignItems: 'center',
    },
    header: {
        width: '100%',
        marginBottom: 8,
    },
    balance: {
        fontSize: 28,
        fontWeight: '700',
        color: theme.colors.text,
        textAlign: 'left',
    },
    changeContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 4,
    },
    changeText: {
        fontSize: 16,
        fontWeight: '600',
        marginEnd: 8,
    },
    changeLabel: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    loadingText: {
        marginTop: 8,
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    emptyText: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
});

export default MiniPortfolioChart;
