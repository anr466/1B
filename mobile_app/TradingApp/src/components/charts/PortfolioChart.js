/**
 * مكون الرسم البياني للمحفظة
 * ✅ رسم بياني خطي تفاعلي مع تدرج
 * ✅ متوافق مع الثيم الجديد
 * ✅ مرتبط بالبيانات الفعلية من سجل الصفقات والمحفظة
 * ✅ يفرق بين الأدمن (demo/real) والمستخدم العادي
 * ⚠️ الرسم البياني يبقى LTR (من اليسار لليمين) لأن هذا هو المعيار العالمي للرسوم البيانية
 */

import React, { useMemo, useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, Dimensions, TouchableOpacity } from 'react-native';
import Svg, { Path, Defs, LinearGradient, Stop, Circle, Line, Text as SvgText } from 'react-native-svg';
import { theme } from '../../theme/theme';
import DatabaseApiService from '../../services/DatabaseApiService';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// فترات زمنية متاحة
const TIME_PERIODS = [
    { key: '24H', label: '24 ساعة', days: 1 },
    { key: '7D', label: '7 أيام', days: 7 },
    { key: '1M', label: 'شهر', days: 30 },
    { key: '3M', label: '3 أشهر', days: 90 },
    { key: '1Y', label: 'سنة', days: 365 },
];

// قيم افتراضية ثابتة خارج المكون - ✅ بدون بيانات افتراضية
const DEFAULT_DATA = [];
const DEFAULT_GRADIENT = [theme.colors.chartGradientStart, theme.colors.chartGradientEnd];

const PortfolioChart = React.memo(({
    userId,
    initialBalance = null,  // ✅ بدون قيمة افتراضية
    currentBalance = null,  // ✅ بدون قيمة افتراضية
    isAdmin = false,
    tradingMode = 'auto',
    width = SCREEN_WIDTH - 48,
    height = 200,
    showGrid = true,
    showLabels = true,
    lineColor = theme.colors.primary,
    gradientColors = DEFAULT_GRADIENT,
}) => {
    const [selectedPeriod, setSelectedPeriod] = useState('1M');
    const [chartData, setChartData] = useState([]);
    const [isLoading, setIsLoading] = useState(false);

    // جلب بيانات الشارت من API
    const loadChartData = useCallback(async () => {
        if (!userId) {return;}

        setIsLoading(true);
        try {
            const period = TIME_PERIODS.find(p => p.key === selectedPeriod);
            const days = period?.days || 30;

            // جلب البيانات من API - يفرق بين الأدمن والمستخدم العادي
            const response = await DatabaseApiService.getPortfolioHistory(userId, days, isAdmin, tradingMode);

            if (response?.success && response?.data) {
                const historyData = response.data;

                // تحويل البيانات لصيغة الشارت
                if (historyData.dates && historyData.balances) {
                    const formattedData = historyData.dates.map((date, index) => ({
                        value: historyData.balances[index] || 0,
                        label: formatDateLabel(date, selectedPeriod),
                        date: date,
                    }));
                    setChartData(formattedData);
                } else {
                    setChartData([]);
                }
            } else {
                setChartData([]);
            }
        } catch (error) {
            console.error('خطأ في جلب بيانات الشارت:', error);
            setChartData([]);
        } finally {
            setIsLoading(false);
        }
    }, [userId, selectedPeriod, isAdmin, tradingMode]);

    // تحميل البيانات عند تغيير الفترة أو المستخدم
    useEffect(() => {
        loadChartData();
    }, [loadChartData]);

    // تنسيق تسمية التاريخ
    const formatDateLabel = (dateStr, period) => {
        const date = new Date(dateStr);
        if (period === '24H') {
            return date.getHours() + ':00';
        } else if (period === '7D' || period === '1M') {
            return date.getDate() + '/' + (date.getMonth() + 1);
        } else {
            return (date.getMonth() + 1) + '/' + date.getFullYear().toString().slice(-2);
        }
    };

    // إنشاء بيانات العرض - استخدام البيانات الحقيقية أو توليد بيانات مبنية على الرصيد الحالي
    const displayData = useMemo(() => {
        // إذا كانت هناك بيانات حقيقية من API
        if (chartData && chartData.length > 0) {return chartData;}

        // ✅ إذا لا توجد بيانات حقيقية، نعرض خط مستقيم عند الرصيد الحالي (بدون بيانات وهمية)
        const period = TIME_PERIODS.find(p => p.key === selectedPeriod);
        const days = period?.days || 30;
        const points = Math.min(days, 10);
        const balance = currentBalance || initialBalance || 0;

        // خط مستقيم عند الرصيد الحالي (0% تغيير)
        const flatData = [];
        for (let i = 0; i < points; i++) {
            const date = new Date();
            date.setDate(date.getDate() - (points - 1 - i));
            flatData.push({
                value: balance,
                label: formatDateLabel(date.toISOString(), selectedPeriod),
                date: date.toISOString(),
            });
        }
        return flatData;
    }, [selectedPeriod, currentBalance, initialBalance, chartData]);

    // حساب القيم والمسارات في useMemo واحد
    const chartCalculations = useMemo(() => {
        const values = displayData.map(d => d.value);
        // ✅ معالجة آمنة عندما تكون البيانات فارغة
        const minValue = values.length > 0 ? Math.min(...values) * 0.95 : 0;
        const maxValue = values.length > 0 ? Math.max(...values) * 1.05 : 100;
        const range = maxValue - minValue || 1;

        const padding = { top: 20, right: 20, bottom: 40, left: 50 };
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;

        const getX = (index) => padding.left + (index / (displayData.length - 1 || 1)) * chartWidth;
        const getY = (value) => padding.top + chartHeight - ((value - minValue) / range) * chartHeight;

        // إنشاء مسار الخط
        let linePath = '';
        if (displayData.length >= 2) {
            linePath = `M ${getX(0)} ${getY(displayData[0].value)}`;
            for (let i = 1; i < displayData.length; i++) {
                const x = getX(i);
                const y = getY(displayData[i].value);
                const prevX = getX(i - 1);
                const prevY = getY(displayData[i - 1].value);
                const cpX = (prevX + x) / 2;
                linePath += ` C ${cpX} ${prevY}, ${cpX} ${y}, ${x} ${y}`;
            }
        }

        // مسار التدرج
        let areaPath = '';
        if (displayData.length >= 2) {
            areaPath = linePath;
            areaPath += ` L ${getX(displayData.length - 1)} ${padding.top + chartHeight}`;
            areaPath += ` L ${padding.left} ${padding.top + chartHeight}`;
            areaPath += ' Z';
        }

        // خطوط الشبكة
        const gridLines = [];
        const numLines = 4;
        for (let i = 0; i <= numLines; i++) {
            const y = padding.top + (i / numLines) * chartHeight;
            const value = maxValue - (i / numLines) * range;
            gridLines.push({ y, value });
        }

        // نقاط البيانات
        const dataPoints = displayData.map((point, index) => ({
            x: getX(index),
            y: getY(point.value),
            isLast: index === displayData.length - 1,
            label: point.label,
            showLabel: index % Math.ceil(displayData.length / 5) === 0,
        }));

        return {
            linePath,
            areaPath,
            gridLines,
            dataPoints,
            padding,
            chartWidth,
            chartHeight,
            minValue,
            maxValue,
            range,
        };
    }, [displayData, width, height]);

    const { linePath, areaPath, gridLines, dataPoints, padding, chartHeight } = chartCalculations;

    // حساب التغيير - ✅ بيانات حقيقية فقط (بدون بيانات افتراضية)
    const firstValue = displayData[0]?.value || null;
    const lastValue = displayData[displayData.length - 1]?.value || currentBalance || null;
    const change = (firstValue !== null && lastValue !== null) ? (lastValue - firstValue) : null;
    const changePercent = (firstValue !== null && firstValue > 0 && change !== null) ? ((change / firstValue) * 100).toFixed(2) : null;
    const isPositive = change !== null ? change >= 0 : null;

    // ✅ عرض رسالة إذا لم تكن هناك بيانات حقيقية
    if (!lastValue || !changePercent) {
        return (
            <View style={styles.container}>
                <View style={styles.emptyStateContainer}>
                    <Text style={styles.emptyStateText}>لا توجد بيانات متاحة</Text>
                    <Text style={styles.emptyStateSubText}>قم بتسجيل الدخول أو إجراء صفقات لعرض البيانات</Text>
                </View>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            {/* معلومات التغيير */}
            <View style={styles.infoContainer}>
                <View>
                    <Text style={styles.currentValue}>
                        ${lastValue.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </Text>
                    <Text style={styles.periodLabel}>
                        {TIME_PERIODS.find(p => p.key === selectedPeriod)?.label || 'شهر'}
                    </Text>
                </View>
                <View style={[styles.changeContainer, { backgroundColor: isPositive ? theme.colors.success + '20' : theme.colors.error + '20' }]}>
                    <Text style={[styles.changeText, { color: isPositive ? theme.colors.success : theme.colors.error }]}>
                        {isPositive ? '+' : ''}{changePercent}%
                    </Text>
                </View>
            </View>

            {/* الرسم البياني */}
            <Svg width={width} height={height}>
                <Defs>
                    <LinearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                        <Stop offset="0%" stopColor={gradientColors[0]} stopOpacity="0.4" />
                        <Stop offset="100%" stopColor={gradientColors[1]} stopOpacity="0" />
                    </LinearGradient>
                    <LinearGradient id="lineGradient" x1="0" y1="0" x2="1" y2="0">
                        <Stop offset="0%" stopColor={theme.colors.primary} />
                        <Stop offset="100%" stopColor={theme.colors.secondary} />
                    </LinearGradient>
                </Defs>

                {/* خطوط الشبكة */}
                {showGrid && gridLines.map((line, index) => (
                    <React.Fragment key={index}>
                        <Line
                            x1={padding.left}
                            y1={line.y}
                            x2={width - padding.right}
                            y2={line.y}
                            stroke={theme.colors.chartGrid}
                            strokeWidth="1"
                            strokeDasharray="4,4"
                            opacity="0.5"
                        />
                        {showLabels && (
                            <SvgText
                                x={padding.left - 8}
                                y={line.y + 4}
                                fill={theme.colors.textSecondary}
                                fontSize="10"
                                textAnchor="end"
                            >
                                ${(line.value / 1000).toFixed(1)}k
                            </SvgText>
                        )}
                    </React.Fragment>
                ))}

                {/* منطقة التدرج */}
                <Path
                    d={areaPath}
                    fill="url(#areaGradient)"
                />

                {/* الخط الرئيسي */}
                <Path
                    d={linePath}
                    stroke="url(#lineGradient)"
                    strokeWidth="3"
                    fill="none"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />

                {/* نقاط البيانات */}
                {dataPoints.map((point, index) => (
                    <Circle
                        key={index}
                        cx={point.x}
                        cy={point.y}
                        r={point.isLast ? 6 : 4}
                        fill={point.isLast ? theme.colors.primary : theme.colors.background}
                        stroke={theme.colors.primary}
                        strokeWidth="2"
                    />
                ))}

                {/* تسميات المحور السيني */}
                {showLabels && dataPoints.map((point, index) => (
                    point.showLabel && (
                        <SvgText
                            key={`label-${index}`}
                            x={point.x}
                            y={height - 10}
                            fill={theme.colors.textSecondary}
                            fontSize="10"
                            textAnchor="middle"
                        >
                            {point.label}
                        </SvgText>
                    )
                ))}
            </Svg>

            {/* فترات زمنية - تفاعلية */}
            <View style={styles.periodContainer}>
                {TIME_PERIODS.map((period) => (
                    <TouchableOpacity
                        key={period.key}
                        style={[
                            styles.periodButton,
                            selectedPeriod === period.key && styles.periodButtonActive,
                        ]}
                        onPress={() => setSelectedPeriod(period.key)}
                        activeOpacity={0.7}
                    >
                        <Text style={[
                            styles.periodText,
                            selectedPeriod === period.key && styles.periodTextActive,
                        ]}>
                            {period.key}
                        </Text>
                    </TouchableOpacity>
                ))}
            </View>
        </View>
    );
});

const styles = StyleSheet.create({
    container: {
        backgroundColor: theme.colors.card,
        borderRadius: 16,
        padding: 16,
        marginVertical: 8,
    },
    infoContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 16,
    },
    currentValue: {
        fontSize: 28,
        fontWeight: '700',
        color: theme.colors.text,
    },
    periodLabel: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        marginTop: 4,
    },
    loadingOverlay: {
        position: 'absolute',
        top: 60,
        right: 16,
        zIndex: 10,
    },
    changeContainer: {
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 20,
    },
    changeText: {
        fontSize: 14,
        fontWeight: '600',
    },
    periodContainer: {
        flexDirection: 'row',
        justifyContent: 'space-around',
        marginTop: 16,
        paddingTop: 16,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
    },
    periodButton: {
        paddingHorizontal: 16,
        paddingVertical: 8,
        borderRadius: 20,
    },
    emptyStateContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        paddingVertical: 40,
    },
    emptyStateText: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 8,
    },
    emptyStateSubText: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        textAlign: 'center',
    },
    periodButtonActive: {
        backgroundColor: theme.colors.primary + '20',
    },
    periodText: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.textSecondary,
    },
    periodTextActive: {
        color: theme.colors.primary,
    },
});

export default PortfolioChart;
