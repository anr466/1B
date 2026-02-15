/**
 * Win/Loss Pie Chart - شارت دائري لمعدل النجاح
 * ✅ يعرض نسبة الصفقات الرابحة vs الخاسرة
 * ✅ تصميم Donut (دائرة مجوفة)
 * ✅ ألوان واضحة (أخضر/أحمر)
 * ✅ معدل النجاح في المركز
 * ✅ تفاعلي - نقر على القسم يعرض التفاصيل
 */

import React, { useMemo, useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, TouchableOpacity, I18nManager } from 'react-native';
import Svg, { G, Path, Circle, Text as SvgText } from 'react-native-svg';
import { theme } from '../../theme/theme';
import DatabaseApiService from '../../services/DatabaseApiService';

const isRTL = I18nManager.isRTL;

const WinLossPieChart = React.memo(({
    userId,
    isAdmin = false,
    tradingMode = 'auto',
    size = 160,
    innerRadius = 0.6, // نسبة الفراغ الداخلي (60%)
}) => {
    const [stats, setStats] = useState(null);
    const [isLoading, setIsLoading] = useState(false);

    // جلب إحصائيات الصفقات
    const loadStats = useCallback(async () => {
        if (!userId) { return; }

        setIsLoading(true);
        try {
            const response = await DatabaseApiService.getUserStats(userId);

            if (response?.success && response?.data) {
                setStats(response.data);
            } else {
                setStats(null);
            }
        } catch (error) {
            console.error('[WinLossPie] خطأ في جلب الإحصائيات:', error);
            setStats(null);
        } finally {
            setIsLoading(false);
        }
    }, [userId]);

    useEffect(() => {
        loadStats();
    }, [loadStats]);

    // حساب البيانات
    const chartData = useMemo(() => {
        if (!stats) {
            return {
                winCount: 0,
                loseCount: 0,
                winRate: 0,
                totalTrades: 0,
            };
        }

        // ✅ FIX: دعم كلا التنسيقين (camelCase من API و snake_case)
        const winCount = stats.winningTrades || stats.winning_trades || 0;
        const loseCount = stats.losingTrades || stats.losing_trades || 0;
        const totalTrades = winCount + loseCount;
        const winRate = totalTrades > 0 ? (winCount / totalTrades) * 100 : 0;

        return {
            winCount,
            loseCount,
            winRate,
            totalTrades,
        };
    }, [stats]);

    // إنشاء مسارات الدائرة
    const pieSlices = useMemo(() => {
        if (chartData.totalTrades === 0) {
            return [];
        }

        const { winCount, loseCount, totalTrades } = chartData;
        const radius = size / 2;
        const innerR = radius * innerRadius;

        // نسبة كل قسم
        const winPercentage = (winCount / totalTrades) * 100;
        const losePercentage = (loseCount / totalTrades) * 100;

        // زوايا
        const winAngle = (winPercentage / 100) * 360;
        const loseAngle = (losePercentage / 100) * 360;

        // دالة لإنشاء مسار القوس
        const createArc = (startAngle, endAngle, outerRadius, innerR) => {
            const start = polarToCartesian(radius, radius, outerRadius, endAngle);
            const end = polarToCartesian(radius, radius, outerRadius, startAngle);
            const largeArc = endAngle - startAngle <= 180 ? '0' : '1';

            const innerStart = polarToCartesian(radius, radius, innerR, endAngle);
            const innerEnd = polarToCartesian(radius, radius, innerR, startAngle);

            const d = [
                'M', start.x, start.y,
                'A', outerRadius, outerRadius, 0, largeArc, 0, end.x, end.y,
                'L', innerEnd.x, innerEnd.y,
                'A', innerR, innerR, 0, largeArc, 1, innerStart.x, innerStart.y,
                'Z',
            ].join(' ');

            return d;
        };

        const slices = [];

        // قسم الرابحة (بنفسجي - موحد)
        if (winCount > 0) {
            slices.push({
                path: createArc(0, winAngle, radius, innerR),
                color: theme.colors.primary,
                label: 'رابحة',
                count: winCount,
                percentage: winPercentage,
            });
        }

        // قسم الخاسرة (وردي - موحد)
        if (loseCount > 0) {
            slices.push({
                path: createArc(winAngle, 360, radius, innerR),
                color: theme.colors.secondary,
                label: 'خاسرة',
                count: loseCount,
                percentage: losePercentage,
            });
        }

        return slices;
    }, [chartData, size, innerRadius]);

    // تحويل من إحداثيات قطبية إلى ديكارتية
    const polarToCartesian = (centerX, centerY, radius, angleInDegrees) => {
        const angleInRadians = ((angleInDegrees - 90) * Math.PI) / 180;
        return {
            x: centerX + radius * Math.cos(angleInRadians),
            y: centerY + radius * Math.sin(angleInRadians),
        };
    };

    if (isLoading) {
        return (
            <View style={[styles.container, { width: size, height: size }]}>
                <ActivityIndicator size="small" color={theme.colors.primary} />
            </View>
        );
    }

    if (chartData.totalTrades === 0) {
        return (
            <View style={[styles.container, { width: size, height: size }]}>
                <View style={styles.emptyCircle}>
                    <Text style={styles.emptyText}>لا توجد صفقات</Text>
                </View>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <Text style={styles.title}>معدل النجاح</Text>

            {/* الرسم البياني */}
            <View style={styles.chartContainer}>
                <Svg width={size} height={size}>
                    <G>
                        {pieSlices.map((slice, index) => (
                            <Path
                                key={index}
                                d={slice.path}
                                fill={slice.color}
                            />
                        ))}
                    </G>
                </Svg>

                {/* النسبة في المركز */}
                <View style={styles.centerLabel}>
                    <Text style={[styles.winRateText, { writingDirection: 'ltr' }]}>
                        {chartData.winRate.toFixed(0)}%
                    </Text>
                    <Text style={styles.centerSubtext}>معدل النجاح</Text>
                </View>
            </View>

            {/* التفاصيل */}
            <View style={styles.legend}>
                <View style={styles.legendItem}>
                    <View style={[styles.legendDot, { backgroundColor: theme.colors.primary }]} />
                    <Text style={[styles.legendText, { writingDirection: 'ltr' }]}>
                        رابحة: {chartData.winCount} ({chartData.winRate.toFixed(1)}%)
                    </Text>
                </View>
                <View style={styles.legendItem}>
                    <View style={[styles.legendDot, { backgroundColor: theme.colors.secondary }]} />
                    <Text style={[styles.legendText, { writingDirection: 'ltr' }]}>
                        خاسرة: {chartData.loseCount} ({(100 - chartData.winRate).toFixed(1)}%)
                    </Text>
                </View>
            </View>
        </View>
    );
});

const styles = StyleSheet.create({
    container: {
        backgroundColor: theme.colors.cardBackground,
        borderRadius: 16,
        padding: 16,
        alignItems: 'center',
    },
    title: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 16,
    },
    chartContainer: {
        position: 'relative',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 16,
    },
    centerLabel: {
        position: 'absolute',
        alignItems: 'center',
        justifyContent: 'center',
    },
    winRateText: {
        fontSize: 32,
        fontWeight: '700',
        color: theme.colors.text,
    },
    centerSubtext: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        marginTop: 4,
    },
    legend: {
        width: '100%',
    },
    legendItem: {
        flexDirection: 'row',
        alignItems: 'center',
        marginVertical: 6,
    },
    legendDot: {
        width: 12,
        height: 12,
        borderRadius: 6,
        marginEnd: 8,
    },
    legendText: {
        fontSize: 14,
        color: theme.colors.text,
    },
    emptyCircle: {
        width: '100%',
        height: '100%',
        borderRadius: 1000,
        borderWidth: 2,
        borderColor: theme.colors.border,
        borderStyle: 'dashed',
        alignItems: 'center',
        justifyContent: 'center',
    },
    emptyText: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
});

export default WinLossPieChart;
