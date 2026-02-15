/**
 * 📊 مخطط توزيع الصفقات - Trade Distribution Chart
 * ✅ يعرض تنوع الصفقات وتوزيعها حسب الربح والخسارة
 * ✅ يدعم الفلاتر (الفترة، النتيجة، المفضلة)
 * ✅ تصميم متناسق مع Theme الموحد
 */

import React, { useMemo } from 'react';
import { View, Text, StyleSheet, I18nManager } from 'react-native';
import { PieChart } from 'react-native-chart-kit';
import { theme } from '../../theme/theme';
import { colors, spacing, typography } from '../../theme/designSystem';
import ModernCard from '../ModernCard';
import BrandIcon from '../BrandIcons';

const isRTL = I18nManager.isRTL;

const TradeDistributionChart = ({
    trades = [],
    title = 'توزيع الصفقات',
    showLegend = true,
    chartWidth = 220,
    style = {},
}) => {
    // ✅ حساب توزيع الصفقات
    const distribution = useMemo(() => {
        if (!trades || trades.length === 0) {
            return {
                winning: 0,
                losing: 0,
                breakeven: 0,
                total: 0,
                winningPercent: 0,
                losingPercent: 0,
                breakevenPercent: 0,
            };
        }

        let winning = 0;
        let losing = 0;
        let breakeven = 0;

        trades.forEach(trade => {
            const profit = parseFloat(trade.profit_loss || trade.profitLoss || 0);
            if (profit > 0) {
                winning++;
            } else if (profit < 0) {
                losing++;
            } else {
                breakeven++;
            }
        });

        const total = trades.length;
        return {
            winning,
            losing,
            breakeven,
            total,
            winningPercent: total > 0 ? Math.round((winning / total) * 100) : 0,
            losingPercent: total > 0 ? Math.round((losing / total) * 100) : 0,
            breakevenPercent: total > 0 ? Math.round((breakeven / total) * 100) : 0,
        };
    }, [trades]);

    // ✅ بيانات الرسم البياني
    const chartData = useMemo(() => {
        const data = [];

        if (distribution.winning > 0) {
            data.push({
                name: 'رابحة',
                count: distribution.winning,
                percentage: distribution.winningPercent,
                color: colors.semantic.success,
                legendFontColor: colors.text,
            });
        }

        if (distribution.losing > 0) {
            data.push({
                name: 'خاسرة',
                count: distribution.losing,
                percentage: distribution.losingPercent,
                color: colors.semantic.error,
                legendFontColor: colors.text,
            });
        }

        if (distribution.breakeven > 0) {
            data.push({
                name: 'تعادل',
                count: distribution.breakeven,
                percentage: distribution.breakevenPercent,
                color: colors.text.tertiary,
                legendFontColor: colors.text,
            });
        }

        return data.length > 0 ? data : [
            {
                name: 'لا توجد صفقات',
                count: 0,
                percentage: 0,
                color: colors.text.tertiary,
                legendFontColor: colors.text,
            }
        ];
    }, [distribution]);

    // ✅ حساب إجمالي الربح/الخسارة
    const totalProfit = useMemo(() => {
        return trades.reduce((sum, trade) => {
            return sum + parseFloat(trade.profit_loss || trade.profitLoss || 0);
        }, 0);
    }, [trades]);

    // ✅ حساب متوسط الربح
    const averageProfit = useMemo(() => {
        if (trades.length === 0) return 0;
        return totalProfit / trades.length;
    }, [trades, totalProfit]);

    // ✅ تنسيق الأرقام
    const formatNumber = (num) => {
        if (Math.abs(num) >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toFixed(2);
    };

    // ✅ إذا لم توجد صفقات
    if (trades.length === 0) {
        return (
            <ModernCard style={[style, styles.container]}>
                <View style={styles.header}>
                    <BrandIcon name="pie-chart" size={22} color={colors.brand.primary} />
                    <Text style={styles.title}>{title}</Text>
                </View>
                <View style={styles.emptyContainer}>
                    <BrandIcon name="pie-chart" size={48} color={colors.text.tertiary} />
                    <Text style={styles.emptyText}>لا توجد بيانات كافية</Text>
                    <Text style={styles.emptySubtext}>
                        سيظهر المخطط عند وجود صفقات
                    </Text>
                </View>
            </ModernCard>
        );
    }

    return (
        <ModernCard style={[style, styles.container]}>
            {/* العنوان */}
            <View style={styles.header}>
                <BrandIcon name="pie-chart" size={22} color={colors.brand.primary} />
                <Text style={styles.title}>{title}</Text>
            </View>

            {/* الرسم البياني */}
            <View style={styles.chartContainer}>
                <PieChart
                    data={chartData.map(item => ({
                        name: item.name,
                        population: item.count,
                        color: item.color,
                        legendFontColor: item.legendFontColor,
                        legendFontSize: 12,
                    }))}
                    width={chartWidth}
                    height={chartWidth}
                    chartConfig={{
                        backgroundColor: 'transparent',
                        decimalPlaces: 0,
                        color: (opacity = 1) => `rgba(139, 92, 246, ${opacity})`,
                        labelColor: () => colors.text,
                        style: {
                            borderRadius: 16,
                        },
                        propsForDots: {
                            r: '6',
                            strokeWidth: '2',
                            stroke: colors.brand.primary,
                        },
                    }}
                    center={[chartWidth / 4, chartWidth / 4]}
                    absolute={false}
                    hasLegend={false}
                    style={styles.pieChart}
                />

                {/* النسبة المئوية في المنتصف */}
                <View style={styles.centerLabel}>
                    <Text style={styles.centerPercent}>
                        {distribution.winningPercent}%
                    </Text>
                    <Text style={styles.centerLabelText}>نجاح</Text>
                </View>
            </View>

            {/* مفتاح الرموز */}
            {showLegend && (
                <View style={styles.legend}>
                    {chartData.map((item, index) => (
                        <View key={index} style={styles.legendItem}>
                            <View style={[styles.legendDot, { backgroundColor: item.color }]} />
                            <Text style={styles.legendText}>{item.name}</Text>
                            <Text style={styles.legendCount}>({item.count})</Text>
                            <Text style={[styles.legendPercent, { color: item.color }]}>
                                {item.percentage}%
                            </Text>
                        </View>
                    ))}
                </View>
            )}

            {/* الإحصائيات السريعة */}
            <View style={styles.statsRow}>
                <View style={styles.statItem}>
                    <Text style={styles.statLabel}>إجمالي الصفقات</Text>
                    <Text style={styles.statValue}>{distribution.total}</Text>
                </View>
                <View style={styles.statDivider} />
                <View style={styles.statItem}>
                    <Text style={styles.statLabel}>صافي الربح</Text>
                    <Text style={[
                        styles.statValue,
                        totalProfit >= 0 ? styles.profitText : styles.lossText
                    ]}>
                        {totalProfit >= 0 ? '+' : ''}{formatNumber(totalProfit)} USDT
                    </Text>
                </View>
                <View style={styles.statDivider} />
                <View style={styles.statItem}>
                    <Text style={styles.statLabel}>متوسط الصفقة</Text>
                    <Text style={[
                        styles.statValue,
                        averageProfit >= 0 ? styles.profitText : styles.lossText
                    ]}>
                        {averageProfit >= 0 ? '+' : ''}{formatNumber(averageProfit)} USDT
                    </Text>
                </View>
            </View>
        </ModernCard>
    );
};

const styles = StyleSheet.create({
    container: {
        padding: spacing.lg,
    },
    header: {
        flexDirection: isRTL ? 'row-reverse' : 'row',
        alignItems: 'center',
        marginBottom: spacing.md,
    },
    title: {
        ...typography.secondary,
        color: colors.text,
        marginStart: spacing.sm,
    },
    chartContainer: {
        alignItems: 'center',
        justifyContent: 'center',
        position: 'relative',
    },
    pieChart: {
        borderRadius: 16,
    },
    centerLabel: {
        position: 'absolute',
        top: '35%',
        left: '38%',
        alignItems: 'center',
    },
    centerPercent: {
        ...typography.primary,
        fontSize: 24,
        fontWeight: '700',
        color: colors.brand.primary,
    },
    centerLabelText: {
        ...typography.tiny,
        color: colors.text.secondary,
    },
    emptyContainer: {
        alignItems: 'center',
        paddingVertical: spacing.xxl,
    },
    emptyText: {
        ...typography.secondary,
        color: colors.text,
        marginTop: spacing.md,
    },
    emptySubtext: {
        ...typography.sm,
        color: colors.text.secondary,
        marginTop: spacing.sm,
        textAlign: 'center',
    },
    legend: {
        flexDirection: isRTL ? 'row-reverse' : 'row',
        justifyContent: 'center',
        flexWrap: 'wrap',
        marginTop: spacing.md,
        gap: spacing.md,
    },
    legendItem: {
        flexDirection: isRTL ? 'row-reverse' : 'row',
        alignItems: 'center',
    },
    legendDot: {
        width: 10,
        height: 10,
        borderRadius: 5,
        marginEnd: spacing.xs,
    },
    legendText: {
        ...typography.sm,
        color: colors.text,
    },
    legendCount: {
        ...typography.sm,
        color: colors.text.secondary,
        marginStart: spacing.xs,
    },
    legendPercent: {
        ...typography.sm,
        fontWeight: '600',
        marginStart: spacing.xs,
    },
    statsRow: {
        flexDirection: isRTL ? 'row-reverse' : 'row',
        justifyContent: 'space-between',
        marginTop: spacing.lg,
        paddingTop: spacing.md,
        borderTopWidth: 1,
        borderTopColor: colors.border.default,
    },
    statItem: {
        flex: 1,
        alignItems: 'center',
    },
    statDivider: {
        width: 1,
        backgroundColor: colors.border.default,
        marginHorizontal: spacing.sm,
    },
    statLabel: {
        ...typography.tiny,
        color: colors.text.secondary,
        marginBottom: spacing.xs,
    },
    statValue: {
        ...typography.secondary,
        fontWeight: '600',
        color: colors.text,
    },
    profitText: {
        color: colors.semantic.success,
    },
    lossText: {
        color: colors.semantic.error,
    },
});

export default TradeDistributionChart;
