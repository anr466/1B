/**
 * مكون الزر الحديث الاحترافي
 * ✅ تصميم جديد مستوحى من Stakent
 * ✅ تدرجات بنفسجية أنيقة
 * ✅ دعم كامل لـ RTL
 */

import React from 'react';
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
  View,
  I18nManager,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { theme as Theme } from '../theme/theme';
import Icon from './CustomIcons';
import { hapticLight } from '../utils/HapticFeedback';

const isRTL = I18nManager.isRTL;

const ModernButton = ({
  title,
  onPress,
  variant = 'primary',
  size = 'medium',
  fullWidth = false,
  disabled = false,
  loading = false,
  icon = null,
  style = {},
}) => {
  const getButtonStyle = () => {
    const baseStyle = [styles.button];

    // إضافة نمط الحجم
    baseStyle.push(styles[`size_${size}`]);

    // إضافة نمط النوع
    baseStyle.push(styles[`variant_${variant}`]);

    // إضافة العرض الكامل
    if (fullWidth) {
      baseStyle.push(styles.fullWidth);
    }

    // إضافة حالة التعطيل
    if (disabled || loading) {
      baseStyle.push(styles.disabled);
    }

    // إضافة الأنماط المخصصة
    baseStyle.push(style);

    return baseStyle;
  };

  const getTextStyle = () => {
    const baseStyle = [styles.text];

    // إضافة نمط النص حسب النوع
    baseStyle.push(styles[`text_${variant}`]);

    // إضافة نمط النص حسب الحجم
    baseStyle.push(styles[`textSize_${size}`]);

    return baseStyle;
  };

  const useGradient = ['primary', 'success', 'error'].includes(variant);

  // ✅ دالة الضغط مع الاهتزاز
  const handlePress = () => {
    hapticLight(); // اهتزاز خفيف عند الضغط
    onPress && onPress();
  };

  return (
    <TouchableOpacity
      style={[getButtonStyle(), !useGradient && styles.solidButton]}
      onPress={handlePress}
      disabled={disabled || loading}
      activeOpacity={0.85}
      accessibilityRole="button"
      accessibilityLabel={title}
      accessibilityState={{ disabled: disabled || loading, busy: loading }}
    >
      {useGradient ? (
        <LinearGradient
          colors={Theme.colors[`gradient${variant.charAt(0).toUpperCase() + variant.slice(1)}`] || Theme.colors.gradientPrimary}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 0 }}
          style={styles.gradientContainer}
        >
          <View style={styles.content}>
            {loading ? (
              <ActivityIndicator
                size="small"
                color="#FFFFFF"
                style={styles.loader}
              />
            ) : (
              <>
                {icon && (
                  typeof icon === 'string' ? (
                    <Icon
                      name={icon}
                      size={size === 'small' ? 16 : size === 'large' ? 24 : 20}
                      color="#FFFFFF"
                      style={styles.iconStyle}
                    />
                  ) : (
                    <View style={styles.iconStyle}>{icon}</View>
                  )
                )}
                <Text style={getTextStyle()}>{title}</Text>
              </>
            )}
          </View>
        </LinearGradient>
      ) : (
        <View style={styles.content}>
          {loading ? (
            <ActivityIndicator
              size="small"
              color={variant === 'ghost' ? Theme.colors.primary : '#FFFFFF'}
              style={styles.loader}
            />
          ) : (
            <>
              {icon && (
                typeof icon === 'string' ? (
                  <Icon
                    name={icon}
                    size={size === 'small' ? 16 : size === 'large' ? 24 : 20}
                    color={variant === 'ghost' ? Theme.colors.primary : '#FFFFFF'}
                    style={styles.iconStyle}
                  />
                ) : (
                  <View style={styles.iconStyle}>{icon}</View>
                )
              )}
              <Text style={getTextStyle()}>{title}</Text>
            </>
          )}
        </View>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  button: {
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
    overflow: 'hidden',
    shadowColor: '#000000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.25, shadowRadius: 3.84, elevation: 5,
  },
  solidButton: {
    // For non-gradient buttons
  },
  gradientContainer: {
    width: '100%',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
  },

  // أحجام الأزرار - ✅ محسّن لـ Touch Target (44px minimum)
  size_small: {
    paddingVertical: 10,
    paddingHorizontal: 14,
    minHeight: 44,    // ✅ كان 36
  },
  size_medium: {
    paddingVertical: 12,
    paddingHorizontal: 16,
    minHeight: 48,    // ✅ كان 44
  },
  size_large: {
    paddingVertical: 16,
    paddingHorizontal: 24,
    minHeight: 56,    // ✅ كان 52
  },

  // أنواع الأزرار
  variant_primary: {
    // Gradient handled separately
  },
  variant_secondary: {
    backgroundColor: Theme.colors.surface,
    borderWidth: 1.5,
    borderColor: Theme.colors.primary + '40',
  },
  variant_success: {
    // Gradient handled separately
  },
  variant_error: {
    // Gradient handled separately
  },
  variant_warning: {
    backgroundColor: Theme.colors.warning,
  },
  variant_ghost: {
    backgroundColor: 'transparent',
    borderWidth: 1.5,
    borderColor: Theme.colors.primary + '40',
  },
  variant_outline: {
    backgroundColor: 'transparent',
    borderWidth: 2,
    borderColor: Theme.colors.primary,
  },

  // أنماط النصوص
  text: {
    fontWeight: '700',
    textAlign: 'center',
    letterSpacing: 0.5,
  },
  text_primary: {
    color: '#FFFFFF',
  },
  text_secondary: {
    color: Theme.colors.text,
  },
  text_success: {
    color: '#FFFFFF',
  },
  text_error: {
    color: '#FFFFFF',
  },
  text_warning: {
    color: '#FFFFFF',
  },
  text_ghost: {
    color: Theme.colors.primary,
  },
  text_outline: {
    color: Theme.colors.primary,
  },

  // أحجام النصوص - ✅ متوافق مع buttonHierarchy
  textSize_small: {
    fontSize: Theme.buttonHierarchy.tertiary.fontSize,  // 14
  },
  textSize_medium: {
    fontSize: Theme.buttonHierarchy.secondary.fontSize, // 15
  },
  textSize_large: {
    fontSize: Theme.buttonHierarchy.primary.fontSize,   // 17
  },

  // أنماط إضافية
  fullWidth: {
    width: '100%',
  },
  disabled: {
    opacity: 0.5,
  },
  content: {
    flexDirection: isRTL ? 'row-reverse' : 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconStyle: {
    // RTL: الأيقونة على اليمين
    marginEnd: 8,
  },
  loader: {
    marginEnd: 8,
  },
});

export default ModernButton;
