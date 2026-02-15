/**
 * 📊 شاشة معلومات مصادر البيانات - DataSourcesInfoScreen
 * توضيح مصادر البيانات المعروضة في التطبيق
 */

import React from 'react';
import {
    View,
    Text,
    ScrollView,
    StyleSheet,
} from 'react-native';
import { theme } from '../theme/theme';
import { SafeAreaView } from 'react-native-safe-area-context';
import ModernCard from '../components/ModernCard';
import BrandIcon from '../components/BrandIcons';
import { useTradingModeContext } from '../context/TradingModeContext';
import { useIsAdmin } from '../hooks/useIsAdmin';

const DataSourcesInfoScreen = ({ navigation, user, onBack }) => {
    // ✅ تحديد نوع البيانات (حقيقي/وهمي)
    const { tradingMode } = useTradingModeContext();
    const isAdmin = useIsAdmin(user);
    const isDemoData = tradingMode === 'demo' || isAdmin;

    const handleBack = () => {
        onBack ? onBack() : navigation?.goBack();
    };

    return (
        <SafeAreaView style={styles.container}>
            <ScrollView contentContainerStyle={styles.scrollContent}>
                {/* ✅ Header */}
                <View style={styles.header}>
                    <BrandIcon name="information-circle" size={32} color={theme.colors.primary} />
                    <Text style={styles.headerTitle}>مصادر البيانات</Text>
                </View>

                {/* ✅ توضيح البيانات التجريبية */}
                <ModernCard variant="info" style={styles.card}>
                    <View style={styles.cardHeader}>
                        <BrandIcon name="database" size={24} color={theme.colors.info} />
                        <Text style={styles.cardTitle}>📊 البيانات التجريبية</Text>
                    </View>
                    <View style={styles.cardContent}>
                        <Text style={styles.sectionText}>
                            • مصدر البيانات: قاعدة البيانات المحلية{'\n'}
                            • نوع البيانات: وهمية للاختبار{'\n'}
                            • الغرض: عرض واجهة التطبيق فقط{'\n'}
                            • التحديث: يدوي من النظام الخلفي{'\n'}
                            • الحالة: {isDemoData ? 'مفعلة' : 'غير مفعلة'}
                        </Text>
                    </View>
                </ModernCard>

                {/* ✅ توضيح البيانات الحقيقية */}
                <ModernCard variant="success" style={styles.card}>
                    <View style={styles.cardHeader}>
                        <BrandIcon name="trending-up" size={24} color={theme.colors.success} />
                        <Text style={styles.cardTitle}>💰 البيانات الحقيقية</Text>
                    </View>
                    <View style={styles.cardContent}>
                        <Text style={styles.sectionText}>
                            • مصدر البيانات: Binance API{'\n'}
                            • نوع البيانات: حقيقية من السوق{'\n'}
                            • الغرض: تداول حقيقي بأموال حقيقية{'\n'}
                            • التحديث: كل 60 ثانية تلقائياً{'\n'}
                            • الحالة: {isDemoData ? 'غير مفعلة' : 'مفعلة'}
                        </Text>
                    </View>
                </ModernCard>

                {/* ✅ مصادر البيانات المختلفة */}
                <ModernCard style={styles.card}>
                    <View style={styles.cardHeader}>
                        <BrandIcon name="chart" size={24} color={theme.colors.primary} />
                        <Text style={styles.cardTitle}>📋 مصادر البيانات المختلفة</Text>
                    </View>
                    <View style={styles.cardContent}>
                        <View style={styles.sourceRow}>
                            <Text style={styles.sourceLabel}>Dashboard:</Text>
                            <Text style={styles.sourceValue}>
                                {isDemoData ? '📊 قاعدة البيانات التجريبية' : '💰 Binance API'}
                            </Text>
                        </View>
                        <View style={styles.sourceRow}>
                            <Text style={styles.sourceLabel}>Portfolio:</Text>
                            <Text style={styles.sourceValue}>
                                {isDemoData ? '📊 قاعدة البيانات التجريبية' : '💰 Binance API'}
                            </Text>
                        </View>
                        <View style={styles.sourceRow}>
                            <Text style={styles.sourceLabel}>Trade History:</Text>
                            <Text style={styles.sourceValue}>
                                {isDemoData ? '📊 قاعدة البيانات التجريبية' : '💰 Binance API'}
                            </Text>
                        </View>
                        <View style={styles.sourceRow}>
                            <Text style={styles.sourceLabel}>Notifications:</Text>
                            <Text style={styles.sourceValue}>
                                {isDemoData ? '📊 قاعدة البيانات التجريبية' : '💰 Binance API'}
                            </Text>
                        </View>
                    </View>
                </ModernCard>

                {/* ✅ توضيح Group B */}
                <ModernCard variant="warning" style={styles.card}>
                    <View style={styles.cardHeader}>
                        <BrandIcon name="settings" size={24} color={theme.colors.warning} />
                        <Text style={styles.cardTitle}>🤖 نظام التداول</Text>
                    </View>
                    <View style={styles.cardContent}>
                        <View style={styles.systemRow}>
                            <Text style={styles.systemTitle}>Group B System:</Text>
                            <Text style={styles.systemDescription}>
                                • فتح وإغلاق الصفقات{'\n'}
                                • إدارة الصفقات النشطة{'\n'}
                                • كل 60 ثانية{'\n'}
                                • البيانات: {isDemoData ? 'تجريبية' : 'حقيقية'}
                            </Text>
                        </View>
                    </View>
                </ModernCard>

                {/* ✅ تحذير مهم */}
                <ModernCard variant="error" style={styles.card}>
                    <View style={styles.cardHeader}>
                        <BrandIcon name="exclamation-triangle" size={24} color={theme.colors.error} />
                        <Text style={styles.cardTitle}>⚠️ تحذير مهم</Text>
                    </View>
                    <View style={styles.cardContent}>
                        <Text style={styles.warningText}>
                            {isAdmin
                                ? '🔴 أنت في وضع الأدمن - جميع البيانات تجريبية للاختبار فقط'
                                : (tradingMode === 'demo'
                                    ? '📊 أنت في وضع التداول التجريبي - البيانات وهمية للاختبار'
                                    : '💡 أنت في وضع التداول الحقيقي - البيانات حقيقية من Binance')
                            }
                        </Text>
                        <Text style={styles.warningSubtext}>
                            تأكد من فهم طبيعة البيانات المعروضة قبل اتخاذ أي قرارات تداول.
                        </Text>
                    </View>
                </ModernCard>

                {/* ✅ معلومات تقنية */}
                <ModernCard style={styles.card}>
                    <View style={styles.cardHeader}>
                        <BrandIcon name="code" size={24} color={theme.colors.textSecondary} />
                        <Text style={styles.cardTitle}>⚙️ معلومات تقنية</Text>
                    </View>
                    <View style={styles.cardContent}>
                        <View style={styles.techRow}>
                            <Text style={styles.techLabel}>وضع التداول:</Text>
                            <Text style={styles.techValue}>
                                {tradingMode === 'demo' ? 'Demo Mode' : 'Real Mode'}
                            </Text>
                        </View>
                        <View style={styles.techRow}>
                            <Text style={styles.techLabel}>نوع المستخدم:</Text>
                            <Text style={styles.techValue}>
                                {isAdmin ? 'Admin' : 'User'}
                            </Text>
                        </View>
                        <View style={styles.techRow}>
                            <Text style={styles.techLabel}>آخر تحديث:</Text>
                            <Text style={styles.techValue}>
                                {new Date().toLocaleString('ar-SA')}
                            </Text>
                        </View>
                    </View>
                </ModernCard>
            </ScrollView>
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    scrollContent: {
        padding: theme.spacing.md,
        gap: theme.spacing.md,
    },
    header: {
        flexDirection: 'row-reverse',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: theme.spacing.lg,
        gap: theme.spacing.sm,
    },
    headerTitle: {
        fontSize: theme.typography.fontSize.xl,
        fontWeight: '700',
        color: theme.colors.text,
        textAlign: 'center',
    },
    card: {
        marginBottom: theme.spacing.md,
    },
    cardHeader: {
        flexDirection: 'row-reverse',
        alignItems: 'center',
        marginBottom: theme.spacing.md,
        gap: theme.spacing.sm,
    },
    cardTitle: {
        fontSize: theme.typography.fontSize.lg,
        fontWeight: '600',
        color: theme.colors.text,
        textAlign: 'right',
    },
    cardContent: {
        gap: theme.spacing.sm,
    },
    sectionText: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.text,
        lineHeight: 22,
        textAlign: 'right',
    },
    sourceRow: {
        flexDirection: 'row-reverse',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: theme.spacing.sm,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    sourceLabel: {
        fontSize: theme.typography.fontSize.sm,
        fontWeight: '600',
        color: theme.colors.text,
    },
    sourceValue: {
        fontSize: theme.typography.fontSize.xs,
        color: theme.colors.textSecondary,
        textAlign: 'left',
    },
    systemRow: {
        marginBottom: theme.spacing.md,
        paddingBottom: theme.spacing.md,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    systemTitle: {
        fontSize: theme.typography.fontSize.base,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: theme.spacing.xs,
        textAlign: 'right',
    },
    systemDescription: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.textSecondary,
        lineHeight: 20,
        textAlign: 'right',
    },
    warningText: {
        fontSize: theme.typography.fontSize.sm,
        fontWeight: '600',
        color: theme.colors.error,
        lineHeight: 22,
        textAlign: 'right',
        marginBottom: theme.spacing.sm,
    },
    warningSubtext: {
        fontSize: theme.typography.fontSize.xs,
        color: theme.colors.textSecondary,
        lineHeight: 18,
        textAlign: 'right',
        fontStyle: 'italic',
    },
    techRow: {
        flexDirection: 'row-reverse',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: theme.spacing.xs,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    techLabel: {
        fontSize: theme.typography.fontSize.sm,
        fontWeight: '500',
        color: theme.colors.text,
    },
    techValue: {
        fontSize: theme.typography.fontSize.xs,
        color: theme.colors.textSecondary,
        textAlign: 'left',
    },
});

export default DataSourcesInfoScreen;
