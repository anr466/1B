/**
 * مكون حقل الإدخال الحديث الموحد
 * ✅ تصميم متسق مع ModernCard و ModernButton
 * ✅ يدعم الأيقونات، التحقق، الحالات المختلفة (Error, Success)
 * ✅ دعم كامل لـ RTL
 */

import React, { useState } from 'react';
import {
    View,
    TextInput,
    Text,
    StyleSheet,
    TouchableOpacity,
    I18nManager,
    ActivityIndicator,
} from 'react-native';
import { theme } from '../theme/theme';
import Icon from './CustomIcons';

const isRTL = I18nManager.isRTL;

const ModernInput = ({
    label,
    value,
    onChangeText,
    placeholder,
    icon,
    secureTextEntry,
    error,
    success,
    successText, // ✅ إضافة خاصية لرسالة النجاح
    loading, // حالة التحقق (مثلاً التحقق من توفر الاسم)
    keyboardType = 'default',
    autoCapitalize = 'none',
    editable = true,
    helperText,
    rightAction, // مكون إضافي على اليمين (مثل زر إظهار كلمة المرور)
    containerStyle,
    ...props // ✅ تمرير باقي الخصائص
}) => {
    const [isFocused, setIsFocused] = useState(false);
    const [isPasswordVisible, setIsPasswordVisible] = useState(!secureTextEntry);

    // تحديد لون الحدود بناءً على الحالة
    const getBorderColor = () => {
        if (error) { return theme.colors.error; }
        if (success) { return theme.colors.success; }
        if (isFocused) { return theme.colors.primary; }
        return theme.colors.border;
    };

    // تحديد أيقونة الحالة
    const renderStatusIcon = () => {
        if (loading) { return <ActivityIndicator size="small" color={theme.colors.primary} />; }
        if (error) { return <Icon name="close" size={20} color={theme.colors.error} />; }
        if (success) { return <Icon name="check-circle" size={20} color={theme.colors.success} />; }
        return null;
    };

    return (
        <View style={[styles.container, containerStyle]}>
            {label && <Text style={styles.label}>{label}</Text>}

            <View style={[
                styles.inputWrapper,
                { borderColor: getBorderColor() },
                !editable && styles.disabledWrapper,
            ]}>
                {/* الأيقونة الرئيسية */}
                {icon && (
                    <View style={styles.iconContainer}>
                        <Icon
                            name={icon}
                            size={20}
                            color={isFocused ? theme.colors.primary : theme.colors.textSecondary}
                        />
                    </View>
                )}

                <TextInput
                    style={[styles.input, !editable && styles.disabledInput]}
                    value={value}
                    onChangeText={onChangeText}
                    placeholder={placeholder}
                    placeholderTextColor={theme.colors.textTertiary}
                    secureTextEntry={secureTextEntry && !isPasswordVisible}
                    keyboardType={keyboardType}
                    autoCapitalize={autoCapitalize}
                    editable={editable}
                    onFocus={() => setIsFocused(true)}
                    onBlur={() => setIsFocused(false)}
                    textAlign={isRTL ? 'right' : 'left'}
                    accessibilityLabel={label || placeholder}
                    accessibilityState={{ disabled: !editable }}
                    accessibilityHint={error || helperText || undefined}
                    {...props}
                />

                {/* الأزرار الجانبية أو حالة الحقل */}
                <View style={styles.rightContainer}>
                    {/* زر إظهار/إخفاء كلمة المرور */}
                    {secureTextEntry && (
                        <TouchableOpacity
                            onPress={() => setIsPasswordVisible(!isPasswordVisible)}
                            style={styles.actionButton}
                            accessibilityRole="button"
                            accessibilityLabel={isPasswordVisible ? 'إخفاء كلمة المرور' : 'إظهار كلمة المرور'}
                        >
                            <Icon
                                name={isPasswordVisible ? 'eye-off' : 'eye'}
                                size={20}
                                color={theme.colors.textSecondary}
                            />
                        </TouchableOpacity>
                    )}

                    {/* إجراء مخصص أو أيقونة الحالة */}
                    {rightAction || renderStatusIcon()}
                </View>
            </View>

            {/* رسائل الخطأ أو المساعدة */}
            {error ? (
                <Text style={styles.errorText}>{error}</Text>
            ) : successText ? (
                <Text style={styles.successText}>{successText}</Text>
            ) : helperText ? (
                <Text style={styles.helperText}>{helperText}</Text>
            ) : null}
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        marginBottom: 16,
    },
    label: {
        fontSize: theme.typography.fontSize.sm,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 8,
        textAlign: 'left',
    },
    inputWrapper: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.backgroundSecondary,
        borderWidth: 1,
        borderRadius: 12,
        height: 50,
        paddingHorizontal: 12,
    },
    disabledWrapper: {
        opacity: 0.6,
        backgroundColor: theme.colors.backgroundTertiary,
    },
    iconContainer: {
        marginEnd: 10,
    },
    input: {
        flex: 1,
        color: theme.colors.text,
        fontSize: theme.typography.fontSize.base,
        height: '100%',
        textAlign: isRTL ? 'right' : 'left',
    },
    disabledInput: {
        color: theme.colors.textSecondary,
    },
    rightContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        marginStart: 8,
    },
    actionButton: {
        padding: 4,
    },
    errorText: {
        color: theme.colors.error,
        fontSize: theme.typography.fontSize.xs,
        marginTop: 4,
        textAlign: 'left',
    },
    successText: {
        color: theme.colors.success,
        fontSize: theme.typography.fontSize.xs,
        marginTop: 4,
        textAlign: 'left',
    },
    helperText: {
        color: theme.colors.textSecondary,
        fontSize: theme.typography.fontSize.xs,
        marginTop: 4,
        textAlign: 'left',
    },
});

export default ModernInput;
