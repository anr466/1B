/**
 * مكون اختيار طريقة التحقق
 * يتيح للمستخدم الاختيار بين الإيميل والرسائل النصية
 */

import React from 'react';
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    Dimensions,
} from 'react-native';
import Icon from './CustomIcons';
import { theme } from '../theme/theme';

const { width } = Dimensions.get('window');

// أنواع التحقق
export const VERIFICATION_METHODS = {
    EMAIL: 'email',
    SMS: 'sms',
};

/**
 * مكون اختيار طريقة التحقق
 * @param {string} selectedMethod - الطريقة المختارة
 * @param {function} onSelect - دالة عند الاختيار
 * @param {boolean} disabled - تعطيل الاختيار
 */
const VerificationMethodSelector = ({
    selectedMethod = VERIFICATION_METHODS.SMS,
    onSelect,
    disabled = false,
    maskedPhone = null,
    maskedEmail = null,
    availableMethods = null, // null = both, or ['sms'], ['email'], ['sms','email']
}) => {
    const allMethods = [
        {
            id: VERIFICATION_METHODS.SMS,
            title: 'رسالة نصية SMS',
            description: maskedPhone ? `إرسال رمز التحقق إلى ${maskedPhone}` : 'إرسال رمز التحقق إلى هاتفك',
            icon: 'phone-iphone',
            recommended: true,
        },
        {
            id: VERIFICATION_METHODS.EMAIL,
            title: 'البريد الإلكتروني',
            description: maskedEmail ? `إرسال رمز التحقق إلى ${maskedEmail}` : 'إرسال رمز التحقق إلى إيميلك',
            icon: 'email',
            recommended: false,
        },
    ];

    const methods = availableMethods
        ? allMethods.filter(m => availableMethods.includes(m.id))
        : allMethods;

    return (
        <View style={styles.container}>
            <Text style={styles.title}>اختر طريقة التحقق</Text>
            <Text style={styles.subtitle}>
                كيف تريد استلام رمز التحقق؟
            </Text>

            <View style={styles.optionsContainer}>
                {methods.map((method) => {
                    const isSelected = selectedMethod === method.id;

                    return (
                        <TouchableOpacity
                            key={method.id}
                            style={[
                                styles.option,
                                isSelected && styles.optionSelected,
                                disabled && styles.optionDisabled,
                            ]}
                            onPress={() => !disabled && onSelect(method.id)}
                            activeOpacity={0.7}
                            disabled={disabled}
                        >
                            <View style={[
                                styles.iconContainer,
                                isSelected && styles.iconContainerSelected,
                            ]}>
                                <Icon
                                    name={method.icon}
                                    size={24}
                                    color={isSelected ? '#FFFFFF' : theme.colors.textSecondary}
                                />
                            </View>

                            <View style={styles.textContainer}>
                                <View style={styles.titleRow}>
                                    <Text style={[
                                        styles.optionTitle,
                                        isSelected && styles.optionTitleSelected,
                                    ]}>
                                        {method.title}
                                    </Text>
                                    {method.recommended && (
                                        <View style={styles.recommendedBadge}>
                                            <Text style={styles.recommendedText}>موصى به</Text>
                                        </View>
                                    )}
                                </View>
                                <Text style={styles.optionDescription}>
                                    {method.description}
                                </Text>
                            </View>

                            <View style={[
                                styles.radio,
                                isSelected && styles.radioSelected,
                            ]}>
                                {isSelected && <View style={styles.radioInner} />}
                            </View>
                        </TouchableOpacity>
                    );
                })}
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        marginVertical: 16,
    },
    title: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
        textAlign: 'right',
        marginBottom: 4,
    },
    subtitle: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        textAlign: 'right',
        marginBottom: 16,
    },
    optionsContainer: {
        gap: 12,
    },
    option: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        padding: 16,
        borderWidth: 2,
        borderColor: 'transparent',
    },
    optionSelected: {
        borderColor: theme.colors.primary,
        backgroundColor: theme.colors.primary + '10',
    },
    optionDisabled: {
        opacity: 0.5,
    },
    iconContainer: {
        width: 48,
        height: 48,
        borderRadius: 24,
        backgroundColor: theme.colors.background,
        justifyContent: 'center',
        alignItems: 'center',
        marginStart: 12,
    },
    iconContainerSelected: {
        backgroundColor: theme.colors.primary,
    },
    textContainer: {
        flex: 1,
        alignItems: 'flex-end',
    },
    titleRow: {
        flexDirection: 'row-reverse',
        alignItems: 'center',
        gap: 8,
    },
    recommendedBadge: {
        backgroundColor: theme.colors.success + '20',
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 8,
    },
    recommendedText: {
        fontSize: 11,
        color: theme.colors.success,
        fontWeight: '600',
    },
    optionTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 4,
    },
    optionTitleSelected: {
        color: theme.colors.primary,
    },
    optionDescription: {
        fontSize: 13,
        color: theme.colors.textSecondary,
    },
    radio: {
        width: 22,
        height: 22,
        borderRadius: 11,
        borderWidth: 2,
        borderColor: theme.colors.textSecondary,
        justifyContent: 'center',
        alignItems: 'center',
        marginEnd: 12,
    },
    radioSelected: {
        borderColor: theme.colors.primary,
    },
    radioInner: {
        width: 12,
        height: 12,
        borderRadius: 6,
        backgroundColor: theme.colors.primary,
    },
});

export default VerificationMethodSelector;
