/**
 * مكون الرسم البياني الدائري لتوزيع المحفظة
 * ✅ رسم بياني دائري تفاعلي
 * ✅ يعرض توزيع الأصول (BTC, ETH, USDT, etc.)
 * ✅ متوافق مع الثيم الجديد
 * ✅ مرتبط بالبيانات الفعلية من API
 */

import React, { useMemo, useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, Dimensions, TouchableOpacity, ScrollView, I18nManager } from 'react-native';
import Svg, { Circle, Path, Text as SvgText, Defs, LinearGradient, Stop } from 'react-native-svg';
import { theme } from '../../theme/theme';
import DatabaseApiService from '../../services/DatabaseApiService';

const isRTL = I18nManager.isRTL;

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// الألوان المتعددة للأصول
const ASSET_COLORS = [
    theme.colors.primary,      // بنفسجي
    theme.colors.secondary,    // وردي
    theme.colors.accent,       // سماوي
    theme.colors.success,      // أخضر
    theme.colors.warning,      // برتقالي
    theme.colors.error,        // أحمر
    '#FF6B9D',                 // وردي فاتح
    '#4ECDC4',                 // تركواز
];

const PortfolioDistributionChart = React.memo(({
    userId,
    isAdmin = false,
    tradingMode = 'auto',
    width = SCREEN_WIDTH - 48,
    height = 300,
}) => {
    const [chartData, setChartData] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [selectedAsset, setSelectedAsset] = useState(null);

    // جلب بيانات المحفظة من API
    const loadChartData = useCallback(async () => {
        if (!userId) {return;}

        setIsLoading(true);
        try {
            // جلب البيانات من API
            const response = await DatabaseApiService.getPortfolio(userId, null, false);

            if (response?.success && response?.data) {
                const portfolioData = response.data;

                // تحويل البيانات لصيغة الشارت
                if (portfolioData.assets && Array.isArray(portfolioData.assets)) {
                    const formattedData = portfolioData.assets
                        .filter(asset => asset.balance > 0)
                        .map((asset, index) => ({
                            symbol: asset.symbol || 'Unknown',
                            balance: asset.balance || 0,
                            value: asset.value || 0,
                            percentage: 0, // سيتم حسابه لاحقاً
                            color: ASSET_COLORS[index % ASSET_COLORS.length],
                        }));

                    // حساب النسب المئوية
                    const totalValue = formattedData.reduce((sum, asset) => sum + asset.value, 0);
                    formattedData.forEach(asset => {
                        asset.percentage = totalValue > 0 ? ((asset.value / totalValue) * 100).toFixed(1) : 0;
                    });

                    setChartData(formattedData);
                } else {
                    setChartData([]);
                }
            } else {
                setChartData([]);
            }
        } catch (error) {
            console.error('خطأ في جلب بيانات المحفظة:', error);
            setChartData([]);
        } finally {
            setIsLoading(false);
        }
    }, [userId]);

    // تحميل البيانات عند تحميل المكون
    useEffect(() => {
        loadChartData();
    }, [loadChartData]);

    // حساب مسارات الدائرة
    const chartCalculations = useMemo(() => {
        if (chartData.length === 0) {
            return { paths: [], centerX: width / 2, centerY: height / 2, radius: 0 };
        }

        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.min(width, height) / 2 - 40;

        const paths = [];
        let currentAngle = -Math.PI / 2; // ابدأ من الأعلى

        chartData.forEach((asset, index) => {
            const sliceAngle = (asset.percentage / 100) * 2 * Math.PI;
            const startAngle = currentAngle;
            const endAngle = currentAngle + sliceAngle;

            // حساب نقاط الدائرة
            const x1 = centerX + radius * Math.cos(startAngle);
            const y1 = centerY + radius * Math.sin(startAngle);
            const x2 = centerX + radius * Math.cos(endAngle);
            const y2 = centerY + radius * Math.sin(endAngle);

            // حساب نقطة المنتصف للنص
            const midAngle = startAngle + sliceAngle / 2;
            const labelRadius = radius * 0.65;
            const labelX = centerX + labelRadius * Math.cos(midAngle);
            const labelY = centerY + labelRadius * Math.sin(midAngle);

            // إنشاء مسار القطاع
            const largeArc = sliceAngle > Math.PI ? 1 : 0;
            const path = `M ${centerX} ${centerY} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`;

            paths.push({
                path,
                color: asset.color,
                labelX,
                labelY,
                percentage: asset.percentage,
                symbol: asset.symbol,
                index,
            });

            currentAngle = endAngle;
        });

        return { paths, centerX, centerY, radius };
    }, [chartData, width, height]);

    const { paths, centerX, centerY, radius } = chartCalculations;

    // حساب الإحصائيات
    const stats = useMemo(() => {
        const totalValue = chartData.reduce((sum, asset) => sum + asset.value, 0);
        const topAsset = chartData.length > 0 ? chartData[0] : null;

        return { totalValue, topAsset, assetCount: chartData.length };
    }, [chartData]);

    if (isLoading) {
        return (
            <View style={styles.container}>
                <Text style={styles.loadingText}>جاري تحميل البيانات...</Text>
            </View>
        );
    }

    if (chartData.length === 0) {
        return (
            <View style={styles.container}>
                <Text style={styles.emptyText}>لا توجد أصول في المحفظة</Text>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            {/* معلومات المحفظة */}
            <View style={styles.infoContainer}>
                <Text style={styles.totalLabel}>إجمالي القيمة</Text>
                <Text style={[styles.totalValue, { writingDirection: 'ltr' }]}>
                    ${stats.totalValue.toFixed(2)}
                </Text>
                <Text style={[styles.assetCountText, { writingDirection: 'ltr' }]}>
                    {stats.assetCount} أصول
                </Text>
            </View>

            {/* الرسم البياني الدائري */}
            <View style={styles.chartContainer}>
                <Svg width={width} height={height}>
                    {/* الأقطاع */}
                    {paths.map((pathData, index) => (
                        <Path
                            key={`slice-${index}`}
                            d={pathData.path}
                            fill={pathData.color}
                            opacity={selectedAsset === null || selectedAsset === index ? 1 : 0.3}
                        />
                    ))}

                    {/* تسميات النسب المئوية */}
                    {paths.map((pathData, index) => (
                        pathData.percentage > 5 && (
                            <SvgText
                                key={`label-${index}`}
                                x={pathData.labelX}
                                y={pathData.labelY}
                                textAnchor="middle"
                                fontSize="12"
                                fontWeight="600"
                                fill={theme.colors.white}
                            >
                                {pathData.percentage}%
                            </SvgText>
                        )
                    ))}
                </Svg>
            </View>

            {/* قائمة الأصول */}
            <ScrollView style={styles.legendContainer} showsVerticalScrollIndicator={false}>
                {chartData.map((asset, index) => (
                    <TouchableOpacity
                        key={`asset-${index}`}
                        style={[
                            styles.legendItem,
                            selectedAsset === index && styles.legendItemActive,
                        ]}
                        onPress={() => setSelectedAsset(selectedAsset === index ? null : index)}
                    >
                        <View style={[styles.legendColor, { backgroundColor: asset.color }]} />
                        <View style={styles.legendInfo}>
                            <Text style={styles.legendSymbol}>{asset.symbol}</Text>
                            <Text style={[styles.legendBalance, { writingDirection: 'ltr' }]}>
                                {asset.balance.toFixed(8)} {asset.symbol}
                            </Text>
                        </View>
                        <View style={styles.legendValue}>
                            <Text style={[styles.legendPercentage, { writingDirection: 'ltr' }]}>{asset.percentage}%</Text>
                            <Text style={[styles.legendPrice, { writingDirection: 'ltr' }]}>${asset.value.toFixed(2)}</Text>
                        </View>
                    </TouchableOpacity>
                ))}
            </ScrollView>
        </View>
    );
});

PortfolioDistributionChart.displayName = 'PortfolioDistributionChart';

const styles = StyleSheet.create({
    container: {
        backgroundColor: theme.colors.card,
        borderRadius: 16,
        padding: 16,
        marginVertical: 8,
    },
    infoContainer: {
        alignItems: 'center',
        marginBottom: 16,
        paddingBottom: 16,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    totalLabel: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        marginBottom: 4,
    },
    totalValue: {
        fontSize: 24,
        fontWeight: '700',
        color: theme.colors.text,
        marginBottom: 4,
    },
    assetCountText: {
        fontSize: 12,
        color: theme.colors.textTertiary,
    },
    chartContainer: {
        alignItems: 'center',
        justifyContent: 'center',
        marginVertical: 16,
    },
    legendContainer: {
        maxHeight: 200,
    },
    legendItem: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 8,
        paddingHorizontal: 8,
        borderRadius: 8,
        marginBottom: 4,
    },
    legendItemActive: {
        backgroundColor: theme.colors.primary + '20',
    },
    legendColor: {
        width: 12,
        height: 12,
        borderRadius: 2,
        marginEnd: 8,
    },
    legendInfo: {
        flex: 1,
    },
    legendSymbol: {
        fontSize: 13,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 2,
    },
    legendBalance: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    legendValue: {
        alignItems: 'flex-end',
    },
    legendPercentage: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 2,
    },
    legendPrice: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    loadingText: {
        textAlign: 'center',
        color: theme.colors.textSecondary,
        paddingVertical: 20,
    },
    emptyText: {
        textAlign: 'center',
        color: theme.colors.textSecondary,
        paddingVertical: 20,
    },
});

export default PortfolioDistributionChart;
