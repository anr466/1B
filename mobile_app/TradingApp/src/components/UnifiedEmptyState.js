/**
 * 📭 مكون الحالة الفارغة الموحد - Unified Empty State
 * ✅ تصميم موحد لجميع حالات عدم وجود بيانات
 * ✅ دعم الأيقونات المخصصة
 * ✅ دعم الإجراءات (Action Buttons)
 * ✅ دعم RTL كامل
 */

import React from 'react';
import {
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    I18nManager,
} from 'react-native';
import { theme } from '../theme/theme';
import BrandIcon from './BrandIcons';

const isRTL = I18nManager.isRTL;

/**
 * أنماط الحالة الفارغة المتاحة
 */
const EMPTY_STATE_STYLES = {
    default: 'default',
    search: 'search',
    error: 'error',
    loading: 'loading',
    success: 'success',
};

/**
 * الأيقونات الافتراضية لكل نمط
 */
const DEFAULT_ICONS = {
    default: 'inbox',
    search: 'search',
    error: 'alert-circle',
    loading: 'loader',
    success: 'check-circle',
};

const UnifiedEmptyState = ({
    style = {},
    variant = 'default',
    icon = null,
    title,
    description = null,
    actionLabel = null,
    onAction = null,
    actionLoading = false,
    testID = 'empty-state',
}) => {
    const getIconName = icon || DEFAULT_ICONS[variant] || DEFAULT_ICONS.default;

    const handleAction = () => {
        if (onAction && !actionLoading) {
            onAction();
        }
    };

    return (
        <View
            style={[styles.container, style]}
            testID={testID}
        >
            {/* الأيقونة */}
            <View style={styles.iconContainer}>
                {variant === 'loading' ? (
                    <View style={styles.loadingIcon}>
                        <BrandIcon
                            name={getIconName}
                            size={48}
                            color={theme.colors.primary}
                        />
                    </View>
                ) : (
                    <BrandIcon
                        name={getIconName}
                        size={48}
                        color={theme.colors.textTertiary}
                    />
                )}
            </View>

            {/* العنوان */}
            <Text style={styles.title} testID={`${testID}-title`}>
                {title}
            </Text>

            {/* الوصف */}
            {description && (
                <Text style={styles.description} testID={`${testID}-description`}>
                    {description}
                </Text>
            )}

            {/* زر الإجراء */}
            {actionLabel && onAction && (
                <TouchableOpacity
                    style={[
                        styles.actionButton,
                        actionLoading && styles.actionButtonLoading,
                    ]}
                    onPress={handleAction}
                    disabled={actionLoading}
                    testID={`${testID}-action`}
                    activeOpacity={0.7}
                >
                    <BrandIcon
                        name={actionLoading ? 'loader' : 'plus'}
                        size={18}
                        color={theme.colors.background}
                        style={actionLoading && styles.spinningIcon}
                    />
                    <Text style={styles.actionButtonText}>
                        {actionLoading ? 'جاري التحميل...' : actionLabel}
                    </Text>
                </TouchableOpacity>
            )}
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        alignItems: 'center',
        justifyContent: 'center',
        paddingVertical: theme.spacing.xxl,
        paddingHorizontal: theme.spacing.lg,
    },
    iconContainer: {
        marginBottom: theme.spacing.md,
    },
    loadingIcon: {
        transform: [{ rotate: isRTL ? '90deg' : '0deg' }],
    },
    spinningIcon: {
        transform: [{ rotate: '360deg' }],
    },
    title: {
        ...theme.hierarchy.secondary,
        color: theme.colors.text,
        textAlign: 'center',
        marginBottom: theme.spacing.sm,
    },
    description: {
        fontSize: theme.typography.fontSize.base,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        lineHeight: 22,
    },
    actionButton: {
        flexDirection: isRTL ? 'row-reverse' : 'row',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: theme.colors.primary,
        paddingVertical: theme.spacing.sm + 4,
        paddingHorizontal: theme.spacing.lg,
        borderRadius: 12,
        marginTop: theme.spacing.lg,
        minWidth: 140,
        minHeight: 44,
    },
    actionButtonLoading: {
        opacity: 0.7,
    },
    actionButtonText: {
        color: theme.colors.background,
        fontSize: theme.typography.fontSize.base,
        fontWeight: '600',
        marginStart: theme.spacing.xs,
    },
});

// تصدير الثوابت
UnifiedEmptyState.Styles = EMPTY_STATE_STYLES;
UnifiedEmptyState.DefaultIcons = DEFAULT_ICONS;

export default UnifiedEmptyState;
