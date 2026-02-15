/**
 * Admin Errors Screen
 * سجل الأخطاء الحرجة والمشاكل في النظام
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
    View,
    Text,
    FlatList,
    RefreshControl,
    StyleSheet,
    ActivityIndicator,
    StatusBar,
} from 'react-native';
import { theme } from '../theme/theme';
import DatabaseApiService from '../services/DatabaseApiService';
import { useBackHandler } from '../utils/BackHandlerUtil';
import Icon from '../components/CustomIcons';
// ✅ GlobalHeader يأتي من Navigator
import errorHandler from '../services/UnifiedErrorHandler'; // ✅ سجل الأخطاء الموحد

const AdminErrorsScreen = () => {
    const [loading, setLoading] = useState(false);
    const [refreshing, setRefreshing] = useState(false);
    const [errors, setErrors] = useState([]);
    const [errorStats, setErrorStats] = useState({
        total: 0,
        unresolved: 0,
        critical: 0,
        by_source: {},
        by_level: {},
    });

    const fetchErrors = useCallback(async () => {
        try {
            setLoading(true);

            // ✅ جلب أخطاء التطبيق المحلية من UnifiedErrorHandler
            const localStats = errorHandler.getStats();

            // Fetch errors from backend and stats concurrently
            const [errorsResponse, statsResponse] = await Promise.all([
                DatabaseApiService.getBackgroundErrors(50),
                DatabaseApiService.getBackgroundErrorStats(),
            ]);

            if (errorsResponse && errorsResponse.success) {
                setErrors(errorsResponse.data?.errors || errorsResponse.errors || []);
            }

            if (statsResponse && statsResponse.success) {
                const stats = statsResponse.data?.stats || statsResponse.stats || {};
                setErrorStats({
                    total: (stats.total || 0) + localStats.total,
                    unresolved: stats.unresolved || 0,
                    critical: stats.critical || 0,
                    by_source: stats.by_source || {},
                    by_level: stats.by_level || {},
                    // ✅ إضافة إحصائيات التطبيق
                    mobile_total: localStats.total,
                    mobile_by_severity: localStats.bySeverity,
                });
            }
        } catch (error) {
            // ✅ استخدام معالج الأخطاء الموحد - لا يظهر للمستخدم (خطأ نظام)
            errorHandler.handleSystemError('MINOR_API_ERROR', 'فشل تحميل الأخطاء');
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    }, []);

    useEffect(() => {
        let isMounted = true;

        const fetchData = async () => {
            if (isMounted) {
                await fetchErrors();
            }
        };

        fetchData();

        return () => {
            isMounted = false;
        };
    }, [fetchErrors]);

    // معالجة زر الرجوع من الجهاز
    useBackHandler(() => {
        // لا نفعل شيء - منع الرجوع فقط
    });

    const renderError = ({ item, index }) => {
        const severityColor = getSeverityColor(item.severity);
        const severityLabel = getSeverityLabel(item.severity);

        return (
            <View style={[styles.errorCard, { borderLeftColor: severityColor }]}>
                <View style={styles.errorHeader}>
                    <View style={styles.errorHeaderLeft}>
                        <Text style={styles.errorType}>{item.type || 'System Error'}</Text>
                        <View
                            style={[
                                styles.severityBadge,
                                { backgroundColor: severityColor + '20', borderColor: severityColor },
                            ]}
                        >
                            <Text style={[styles.severityText, { color: severityColor }]}>
                                {severityLabel}
                            </Text>
                        </View>
                    </View>
                    <Text style={styles.errorTime}>{item.time || item.timestamp}</Text>
                </View>

                <Text style={styles.errorMessage}>{item.message || item.error}</Text>

                {item.details && (
                    <Text style={styles.errorDetails} numberOfLines={2}>
                        {item.details}
                    </Text>
                )}
            </View>
        );
    };

    const renderEmpty = () => (
        <View style={styles.emptyContainer}>
            <Icon
                name="check"
                size={60}
                color={theme.colors.success}
            />
            <Text style={styles.emptyTitle}>لا توجد أخطاء!</Text>
            <Text style={styles.emptyMessage}>النظام يعمل بشكل ممتاز</Text>
        </View>
    );

    return (
        <View style={styles.container}>
            <StatusBar barStyle="light-content" backgroundColor={theme.colors.background} />
            {/* ✅ Header يأتي من Navigator */}

            {/* Stats Section */}
            <View style={styles.statsSection}>
                <View style={styles.statsContainer}>
                    <StatItem
                        label="إجمالي 24 ساعة"
                        value={errorStats.total || 0}
                        color={theme.colors.textSecondary}
                    />
                    <StatItem
                        label="حرجة"
                        value={errorStats.critical || 0}
                        color={theme.colors.error}
                    />
                    <StatItem
                        label="غير محلولة"
                        value={errorStats.unresolved || 0}
                        color={theme.colors.warning}
                    />
                </View>
            </View>

            <FlatList
                data={errors}
                renderItem={renderError}
                keyExtractor={(item, index) => `error-${index}`}
                ListEmptyComponent={!loading && renderEmpty()}
                contentContainerStyle={styles.listContent}
                refreshControl={
                    <RefreshControl
                        refreshing={refreshing}
                        onRefresh={() => {
                            setRefreshing(true);
                            fetchErrors();
                        }}
                        tintColor={theme.colors.primary}
                    />
                }
            />

            {loading && !refreshing && (
                <View style={styles.loadingOverlay}>
                    <ActivityIndicator size="large" color={theme.colors.primary} />
                </View>
            )}
        </View>
    );
};

// مكون إحصائية صغير
const StatItem = ({ label, value, color }) => (
    <View style={styles.statItem}>
        <Text style={[styles.statValue, { color }]}>{value}</Text>
        <Text style={styles.statLabel}>{label}</Text>
    </View>
);

// دوال مساعدة
const getSeverityColor = (severity) => {
    switch (severity?.toLowerCase()) {
        case 'critical':
            return theme.colors.error;
        case 'high':
            return theme.colors.warning;
        case 'medium':
            return theme.colors.info;
        case 'low':
            return theme.colors.success;
        default:
            return theme.colors.textSecondary;
    }
};

const getSeverityLabel = (severity) => {
    switch (severity?.toLowerCase()) {
        case 'critical':
            return 'حرج';
        case 'high':
            return 'عالي';
        case 'medium':
            return 'متوسط';
        case 'low':
            return 'منخفض';
        default:
            return 'غير محدد';
    }
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    statsSection: {
        paddingHorizontal: theme.spacing.lg,
        paddingVertical: theme.spacing.md,
    },
    listContent: {
        padding: theme.spacing.lg,
    },
    statsContainer: {
        flexDirection: 'row',
        backgroundColor: theme.colors.surface,
        borderRadius: theme.borderRadius.lg,
        padding: theme.spacing.lg,
        gap: theme.spacing.lg,
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    statItem: {
        flex: 1,
        alignItems: 'center',
    },
    statValue: {
        fontSize: 20,
        fontWeight: '700',
        marginBottom: 4,
    },
    statLabel: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        textAlign: 'center',
    },
    errorCard: {
        backgroundColor: theme.colors.surface,
        borderRadius: theme.borderRadius.lg,
        padding: theme.spacing.lg,
        marginBottom: theme.spacing.md,
        borderLeftWidth: 4,
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    errorHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 8,
    },
    errorHeaderLeft: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    errorType: {
        fontSize: theme.typography.fontSize.base,
        fontWeight: '600',
        color: theme.colors.text,
    },
    severityBadge: {
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 4,
        borderWidth: 1,
    },
    severityText: {
        fontSize: 12,
        fontWeight: '600',
    },
    errorTime: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        marginLeft: 8,
    },
    errorMessage: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.textSecondary,
        lineHeight: 20,
        marginBottom: 4,
    },
    errorDetails: {
        fontSize: 12,
        color: theme.colors.textTertiary,
        fontStyle: 'italic',
    },
    emptyContainer: {
        alignItems: 'center',
        justifyContent: 'center',
        paddingVertical: theme.spacing.xxxl,
    },
    emptyIcon: {
        fontSize: 64,
        marginBottom: 16,
    },
    emptyTitle: {
        fontSize: theme.typography.fontSize.lg,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: theme.spacing.sm,
    },
    emptyMessage: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.textSecondary,
    },
    loadingOverlay: {
        ...StyleSheet.absoluteFillObject,
        backgroundColor: 'rgba(15, 17, 24, 0.7)',
        justifyContent: 'center',
        alignItems: 'center',
    },
});

export default AdminErrorsScreen;
