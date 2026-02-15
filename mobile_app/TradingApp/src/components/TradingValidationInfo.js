/**
 * Trading Validation Info Component
 * عرض معلومات التحقق من متطلبات التداول
 */

import React, { useState, useEffect } from 'react';
import {
    View,
    Text,
    StyleSheet,
    ActivityIndicator,
    Alert,
} from 'react-native';
import { theme } from '../theme/theme';
import ModernCard from './ModernCard';
import BrandIcon from './BrandIcons';
import DatabaseApiService from '../services/DatabaseApiService';

const TradingValidationInfo = ({ user, settings, isAdmin }) => {
    const [validationData, setValidationData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        loadValidationData();
    }, [user?.id, settings]);

    const loadValidationData = async () => {
        try {
            setLoading(true);

            // فحص قدرة المستخدم على التداول
            const response = await DatabaseApiService.validateTradingSettings(user?.id, settings);

            if (response?.success) {
                setValidationData(response.data);
            } else {
                setValidationData({
                    can_trade: false,
                    reason: 'فشل في فحص متطلبات التداول',
                    has_keys: false,
                    sufficient_balance: false,
                    current_positions: 0,
                    max_allowed_positions: settings?.max_positions || 5,
                });
            }
        } catch (error) {
            console.error('Trading validation error:', error);
            setValidationData({
                can_trade: false,
                reason: 'خطأ في التحقق من المتطلبات',
                has_keys: false,
                sufficient_balance: false,
                current_positions: 0,
                max_allowed_positions: settings?.max_positions || 5,
            });
        } finally {
            setLoading(false);
        }
    };

    const getValidationIcon = (isValid) => {
        return isValid ? 'check-circle' : 'x-circle';
    };

    const getValidationColor = (isValid) => {
        return isValid ? theme.colors.success : theme.colors.error;
    };

    if (loading) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="small" color={theme.colors.primary} />
                <Text style={styles.loadingText}>جاري التحقق من متطلبات التداول...</Text>
            </View>
        );
    }

    if (!validationData) {
        return null;
    }

    const {
        can_trade,
        reason,
        has_keys,
        sufficient_balance,
        current_positions,
        max_allowed_positions,
        available_balance,
        required_amount,
        validation_errors,
    } = validationData;

    return (
        <View style={styles.container}>
            <Text style={styles.sectionTitle}>متطلبات التداول</Text>

            {/* حالة التحقق العامة */}
            <View style={[styles.statusBox, {
                backgroundColor: can_trade ? theme.colors.success + '20' : theme.colors.error + '20',
                borderColor: can_trade ? theme.colors.success : theme.colors.error,
            }]}>
                <BrandIcon
                    name={getValidationIcon(can_trade)}
                    size={20}
                    color={getValidationColor(can_trade)}
                />
                <Text style={[styles.statusText, { color: getValidationColor(can_trade) }]}>
                    {can_trade ? '✅ جاهز للتداول' : '❌ غير جاهز للتداول'}
                </Text>
            </View>

            {/* تفاصيل التحقق */}
            <View style={styles.detailsContainer}>

                {/* 1. فحص مفاتيح Binance */}
                <View style={styles.detailRow}>
                    <BrandIcon
                        name={getValidationIcon(has_keys)}
                        size={16}
                        color={getValidationColor(has_keys)}
                    />
                    <Text style={styles.detailLabel}>مفاتيح Binance:</Text>
                    <Text style={[styles.detailValue, { color: getValidationColor(has_keys) }]}>
                        {has_keys ? 'مربوطة' : 'غير مربوطة'}
                    </Text>
                </View>

                {/* 2. فحص الرصيد */}
                <View style={styles.detailRow}>
                    <BrandIcon
                        name={getValidationIcon(sufficient_balance)}
                        size={16}
                        color={getValidationColor(sufficient_balance)}
                    />
                    <Text style={styles.detailLabel}>الرصيد الكافي:</Text>
                    <Text style={[styles.detailValue, { color: getValidationColor(sufficient_balance) }]}>
                        {sufficient_balance ? 'كافي' : 'غير كافي'}
                    </Text>
                </View>

                {/* 3. عدد الصفقات النشطة */}
                <View style={styles.detailRow}>
                    <BrandIcon
                        name={getValidationIcon(current_positions < max_allowed_positions)}
                        size={16}
                        color={getValidationColor(current_positions < max_allowed_positions)}
                    />
                    <Text style={styles.detailLabel}>الصفقات النشطة:</Text>
                    <Text style={styles.detailValue}>
                        {current_positions}/{max_allowed_positions}
                    </Text>
                </View>

                {/* 4. تفاصيل الرصيد */}
                {available_balance !== undefined && required_amount !== undefined && (
                    <View style={styles.balanceDetails}>
                        <Text style={styles.balanceLabel}>الرصيد المتاح:</Text>
                        <Text style={styles.balanceValue}>{available_balance?.toFixed(2)} USDT</Text>

                        <Text style={styles.balanceLabel}>المبلغ المطلوب:</Text>
                        <Text style={styles.balanceValue}>{required_amount?.toFixed(2)} USDT</Text>
                    </View>
                )}

                {/* 5. سبب عدم الجاهزية */}
                {!can_trade && reason && (
                    <View style={styles.reasonBox}>
                        <Text style={styles.reasonLabel}>السبب:</Text>
                        <Text style={styles.reasonText}>{reason}</Text>
                    </View>
                )}

                {/* 6. أخطاء التحقق */}
                {validation_errors && validation_errors.length > 0 && (
                    <View style={styles.errorsBox}>
                        <Text style={styles.errorsLabel}>أخطاء في الإعدادات:</Text>
                        {validation_errors.map((error, index) => (
                            <Text key={index} style={styles.errorText}>• {error}</Text>
                        ))}
                    </View>
                )}
            </View>

            {/* توضيحات إضافية */}
            <View style={styles.infoBox}>
                <Text style={styles.infoTitle}>ملاحظات مهمة:</Text>
                <Text style={styles.infoText}>
                    • يجب ربط مفاتيح Binance للتداول الحقيقي
                </Text>
                <Text style={styles.infoText}>
                    • النظام يستخدم الأقل بين المبلغ الثابت ونسبة رأس المال
                </Text>
                <Text style={styles.infoText}>
                    • وقف الخسارة وجني الأرباح يحددها النظام تلقائياً
                </Text>
                <Text style={styles.infoText}>
                    • لا يمكن فتح صفقات جديدة عند الوصول للحد الأقصى
                </Text>
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        marginTop: 16,
    },
    sectionTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 12,
    },
    loadingContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
    },
    loadingText: {
        marginLeft: 8,
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    statusBox: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 12,
        borderRadius: 8,
        borderWidth: 1,
        marginBottom: 16,
    },
    statusText: {
        fontSize: 14,
        fontWeight: '600',
        marginLeft: 8,
    },
    detailsContainer: {
        marginBottom: 16,
    },
    detailRow: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 8,
    },
    detailLabel: {
        fontSize: 14,
        color: theme.colors.text,
        marginLeft: 8,
        flex: 1,
    },
    detailValue: {
        fontSize: 14,
        fontWeight: '500',
    },
    balanceDetails: {
        marginTop: 12,
        padding: 12,
        backgroundColor: theme.colors.backgroundSecondary,
        borderRadius: 8,
    },
    balanceLabel: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        marginTop: 4,
    },
    balanceValue: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 8,
    },
    reasonBox: {
        marginTop: 12,
        padding: 12,
        backgroundColor: theme.colors.warning + '20',
        borderRadius: 8,
        borderWidth: 1,
        borderColor: theme.colors.warning,
    },
    reasonLabel: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.warning,
        marginBottom: 4,
    },
    reasonText: {
        fontSize: 14,
        color: theme.colors.text,
    },
    errorsBox: {
        marginTop: 12,
        padding: 12,
        backgroundColor: theme.colors.error + '20',
        borderRadius: 8,
        borderWidth: 1,
        borderColor: theme.colors.error,
    },
    errorsLabel: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.error,
        marginBottom: 4,
    },
    errorText: {
        fontSize: 12,
        color: theme.colors.text,
        marginBottom: 2,
    },
    infoBox: {
        marginTop: 12,
        padding: 12,
        backgroundColor: theme.colors.info + '20',
        borderRadius: 8,
        borderWidth: 1,
        borderColor: theme.colors.info,
    },
    infoTitle: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.info,
        marginBottom: 4,
    },
    infoText: {
        fontSize: 11,
        color: theme.colors.textSecondary,
        marginBottom: 2,
    },
});

export default TradingValidationInfo;
