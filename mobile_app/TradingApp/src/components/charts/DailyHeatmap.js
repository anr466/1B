/**
 * Daily P&L Heatmap - خريطة حرارية للأرباح اليومية
 * ✅ تقويم ملون يعرض آخر 3-6 أشهر
 * ✅ كل مربع = يوم واحد
 * ✅ اللون = الربح/الخسارة
 * ✅ نقر على اليوم → صفقات ذلك اليوم
 * ✅ يكشف الأنماط الزمنية
 */

import React, { useMemo, useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, ScrollView, ActivityIndicator, Dimensions } from 'react-native';
import { theme } from '../../theme/theme';
import DatabaseApiService from '../../services/DatabaseApiService';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const DailyHeatmap = React.memo(({
    userId,
    isAdmin = false,
    tradingMode = 'auto',
    months = 3, // عدد الأشهر للعرض
    onDayPress = null, // callback عند الضغط على يوم
}) => {
    const [dailyData, setDailyData] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [selectedDay, setSelectedDay] = useState(null);

    // جلب البيانات اليومية
    const loadDailyData = useCallback(async () => {
        if (!userId) { return; }

        setIsLoading(true);
        try {
            const days = months * 30;
            const response = await DatabaseApiService.getDailyPnL(userId, days, isAdmin, tradingMode);

            if (response?.success && response?.data) {
                const items = Array.isArray(response.data) ? response.data : (response.data?.data || []);
                setDailyData(items);
            } else {
                setDailyData([]);
            }
        } catch (error) {
            console.error('[Heatmap] خطأ في جلب البيانات:', error);
            setDailyData([]);
        } finally {
            setIsLoading(false);
        }
    }, [userId, months, isAdmin, tradingMode]);

    useEffect(() => {
        loadDailyData();
    }, [loadDailyData]);

    // تنظيم البيانات حسب الأسابيع والأشهر
    const organizedData = useMemo(() => {
        if (dailyData.length === 0) { return []; }

        const today = new Date();
        const startDate = new Date();
        startDate.setDate(today.getDate() - (months * 30));

        const monthsData = [];
        const dataMap = new Map(dailyData.map(d => [d.date, d]));

        // إنشاء هيكل البيانات لكل شهر
        for (let m = 0; m < months; m++) {
            const monthDate = new Date(today);
            monthDate.setMonth(today.getMonth() - (months - 1 - m));
            monthDate.setDate(1);

            const monthName = monthDate.toLocaleDateString('ar-EG', { month: 'long', year: 'numeric' });
            const daysInMonth = new Date(monthDate.getFullYear(), monthDate.getMonth() + 1, 0).getDate();
            const firstDayOfWeek = monthDate.getDay(); // 0 = الأحد

            const weeks = [];
            let currentWeek = new Array(7).fill(null);

            // ملء الأيام
            for (let day = 1; day <= daysInMonth; day++) {
                const date = new Date(monthDate.getFullYear(), monthDate.getMonth(), day);
                const dateStr = date.toISOString().split('T')[0];
                const dayOfWeek = date.getDay();

                const dayData = dataMap.get(dateStr);
                currentWeek[dayOfWeek] = {
                    day,
                    date: dateStr,
                    pnl: dayData?.total_pnl || 0,
                    trades: dayData?.trades_count || 0,
                };

                // إذا كان آخر يوم في الأسبوع أو آخر يوم في الشهر
                if (dayOfWeek === 6 || day === daysInMonth) {
                    weeks.push([...currentWeek]);
                    currentWeek = new Array(7).fill(null);
                }
            }

            monthsData.push({
                name: monthName,
                weeks,
            });
        }

        return monthsData;
    }, [dailyData, months]);

    // تحديد اللون بناءً على الربح/الخسارة - ✅ متوافق مع الثيم
    const getColorForPnL = (pnl, trades) => {
        if (trades === 0) { return theme.colors.border; } // لا صفقات
        if (pnl > 50) { return theme.colors.successDark; } // ربح كبير - #059669
        if (pnl > 10) { return theme.colors.success; } // ربح متوسط - #10B981
        if (pnl > 0) { return theme.colors.successLight; } // ربح صغير - #34D399
        if (pnl > -10) { return theme.colors.errorLight; } // خسارة صغيرة - #F87171
        if (pnl > -50) { return theme.colors.error; } // خسارة متوسطة - #EF4444
        return theme.colors.errorDark; // خسارة كبيرة - #DC2626
    };

    const handleDayPress = (dayData) => {
        setSelectedDay(dayData);
        if (onDayPress) {
            onDayPress(dayData);
        }
    };

    if (isLoading) {
        return (
            <View style={styles.container}>
                <ActivityIndicator size="small" color={theme.colors.primary} />
                <Text style={styles.loadingText}>جاري التحميل...</Text>
            </View>
        );
    }

    if (organizedData.length === 0) {
        return (
            <View style={styles.container}>
                <Text style={styles.title}>الأرباح اليومية</Text>
                <Text style={styles.emptyText}>لا توجد بيانات</Text>
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <Text style={styles.title}>الأرباح اليومية - آخر {months} أشهر</Text>

            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.scrollView}>
                <View style={styles.heatmapContainer}>
                    {/* أسماء أيام الأسبوع */}
                    <View style={styles.weekDaysHeader}>
                        <Text style={styles.weekDayLabel}>أحد</Text>
                        <Text style={styles.weekDayLabel}>إثنين</Text>
                        <Text style={styles.weekDayLabel}>ثلاثاء</Text>
                        <Text style={styles.weekDayLabel}>أربعاء</Text>
                        <Text style={styles.weekDayLabel}>خميس</Text>
                        <Text style={styles.weekDayLabel}>جمعة</Text>
                        <Text style={styles.weekDayLabel}>سبت</Text>
                    </View>

                    {/* كل شهر */}
                    {organizedData.map((month, monthIndex) => (
                        <View key={monthIndex} style={styles.monthContainer}>
                            <Text style={styles.monthName}>{month.name}</Text>

                            {/* الأسابيع */}
                            {month.weeks.map((week, weekIndex) => (
                                <View key={weekIndex} style={styles.weekRow}>
                                    {week.map((day, dayIndex) => (
                                        <TouchableOpacity
                                            key={dayIndex}
                                            style={[
                                                styles.dayCell,
                                                {
                                                    backgroundColor: day
                                                        ? getColorForPnL(day.pnl, day.trades)
                                                        : 'transparent',
                                                },
                                                selectedDay?.date === day?.date && styles.selectedDay,
                                            ]}
                                            onPress={() => day && handleDayPress(day)}
                                            disabled={!day}
                                        >
                                            {day && (
                                                <Text style={styles.dayText}>{day.day}</Text>
                                            )}
                                        </TouchableOpacity>
                                    ))}
                                </View>
                            ))}
                        </View>
                    ))}
                </View>
            </ScrollView>

            {/* Legend - ✅ متوافق مع الثيم */}
            <View style={styles.legend}>
                <Text style={styles.legendTitle}>الدليل:</Text>
                <View style={styles.legendRow}>
                    <View style={styles.legendItem}>
                        <View style={[styles.legendBox, { backgroundColor: theme.colors.successDark }]} />
                        <Text style={styles.legendText}>ربح كبير</Text>
                    </View>
                    <View style={styles.legendItem}>
                        <View style={[styles.legendBox, { backgroundColor: theme.colors.successLight }]} />
                        <Text style={styles.legendText}>ربح صغير</Text>
                    </View>
                    <View style={styles.legendItem}>
                        <View style={[styles.legendBox, { backgroundColor: theme.colors.errorLight }]} />
                        <Text style={styles.legendText}>خسارة صغيرة</Text>
                    </View>
                    <View style={styles.legendItem}>
                        <View style={[styles.legendBox, { backgroundColor: theme.colors.errorDark }]} />
                        <Text style={styles.legendText}>خسارة كبيرة</Text>
                    </View>
                    <View style={styles.legendItem}>
                        <View style={[styles.legendBox, { backgroundColor: theme.colors.border }]} />
                        <Text style={styles.legendText}>لا صفقات</Text>
                    </View>
                </View>
            </View>

            {/* تفاصيل اليوم المحدد */}
            {selectedDay && (
                <View style={styles.selectedDayInfo}>
                    <Text style={styles.selectedDayDate}>
                        {new Date(selectedDay.date).toLocaleDateString('ar-EG', {
                            weekday: 'long',
                            year: 'numeric',
                            month: 'long',
                            day: 'numeric',
                        })}
                    </Text>
                    <View style={styles.selectedDayStats}>
                        <Text style={[
                            styles.selectedDayPnL,
                            { color: selectedDay.pnl >= 0 ? theme.colors.success : theme.colors.error },
                        ]}>
                            {selectedDay.pnl >= 0 ? '+' : ''}{selectedDay.pnl.toFixed(2)} USDT
                        </Text>
                        <Text style={styles.selectedDayTrades}>
                            {selectedDay.trades} صفقة
                        </Text>
                    </View>
                </View>
            )}
        </View>
    );
});

const styles = StyleSheet.create({
    container: {
        backgroundColor: theme.colors.cardBackground,
        borderRadius: 16,
        padding: 16,
    },
    title: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 16,
    },
    scrollView: {
        marginBottom: 16,
    },
    heatmapContainer: {
        minWidth: SCREEN_WIDTH - 64,
    },
    weekDaysHeader: {
        flexDirection: 'row',
        marginBottom: 8,
        justifyContent: 'space-around',
    },
    weekDayLabel: {
        fontSize: 10,
        color: theme.colors.textSecondary,
        width: 32,
        textAlign: 'center',
    },
    monthContainer: {
        marginBottom: 16,
    },
    monthName: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 8,
    },
    weekRow: {
        flexDirection: 'row',
        marginBottom: 4,
        justifyContent: 'space-around',
    },
    dayCell: {
        width: 32,
        height: 32,
        borderRadius: 4,
        alignItems: 'center',
        justifyContent: 'center',
        margin: 2,
    },
    selectedDay: {
        borderWidth: 2,
        borderColor: theme.colors.primary,
    },
    dayText: {
        fontSize: 10,
        color: theme.colors.text,
        fontWeight: '500',
    },
    legend: {
        marginTop: 8,
        paddingTop: 12,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
    },
    legendTitle: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.textSecondary,
        marginBottom: 8,
    },
    legendRow: {
        flexDirection: 'row',
        flexWrap: 'wrap',
    },
    legendItem: {
        flexDirection: 'row',
        alignItems: 'center',
        marginEnd: 12,
        marginBottom: 4,
    },
    legendBox: {
        width: 16,
        height: 16,
        borderRadius: 3,
        marginEnd: 4,
    },
    legendText: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    selectedDayInfo: {
        marginTop: 12,
        padding: 12,
        backgroundColor: theme.colors.background,
        borderRadius: 8,
    },
    selectedDayDate: {
        fontSize: 13,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 8,
    },
    selectedDayStats: {
        flexDirection: 'row',
        justifyContent: 'space-between',
    },
    selectedDayPnL: {
        fontSize: 18,
        fontWeight: '700',
    },
    selectedDayTrades: {
        fontSize: 14,
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
        textAlign: 'center',
        marginTop: 20,
    },
});

export default DailyHeatmap;
