import React, { useState } from 'react';
import { TouchableOpacity, Text, ActivityIndicator, StyleSheet, Dimensions } from 'react-native';
import { useTheme } from '../../../context/ThemeContext';
import { theme } from '../../../theme/theme';

const { width } = Dimensions.get('window');

/**
 * مكون زر إعادة الإرسال مع عداد تنازلي
 * @param {function} onPress - دالة إعادة الإرسال
 * @param {boolean} disabled - حالة تعطيل الزر
 * @param {number} cooldownTime - وقت الانتظار بالثواني (افتراضي: 60)
 * @param {boolean} loading - حالة التحميل
 * @param {object} style - أنماط إضافية للزر
 * @param {object} textStyle - أنماط إضافية للنص
 */
const ResendButton = ({
  onPress,
  disabled = false,
  cooldownTime = 60,
  loading = false,
  style = {},
  textStyle = {},
}) => {
  const { colors } = useTheme();
  const [countdown, setCountdown] = useState(0);
  const [isLoading, setIsLoading] = useState(loading);

  // بدء العداد التنازلي
  const startCooldown = () => {
    setCountdown(cooldownTime);

    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  // معالجة الضغط على الزر
  const handlePress = async () => {
    if (disabled || countdown > 0 || isLoading) { return; }

    setIsLoading(true);

    try {
      if (onPress) {
        await onPress();
      }
      // بدء العداد التنازلي بعد الإرسال الناجح
      startCooldown();
    } catch (error) {
      console.error('خطأ في إعادة الإرسال:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // تحديد حالة تعطيل الزر
  const isDisabled = disabled || countdown > 0 || isLoading;

  // تحديد نص الزر
  const getButtonText = () => {
    if (isLoading) { return ''; }
    if (countdown > 0) { return `إعادة الإرسال (${countdown}s)`; }
    return 'إعادة الإرسال';
  };

  // تحديد لون الزر
  const getButtonColor = () => {
    if (isDisabled) { return colors.border; }
    return colors.primary;
  };

  // تحديد لون النص
  const getTextColor = () => {
    if (isDisabled) { return colors.textSecondary; }
    return colors.surface;
  };

  const styles = StyleSheet.create({
    button: {
      backgroundColor: getButtonColor(),
      borderRadius: 12,
      paddingVertical: 12,
      paddingHorizontal: 20,
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: 48,
      minWidth: width * 0.4,
      flexDirection: 'row',
      ...style,
    },
    buttonText: {
      color: getTextColor(),
      fontSize: width * 0.04,
      fontWeight: '600',
      textAlign: 'center',
      ...textStyle,
    },
    loadingContainer: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
    },
  });

  return (
    <TouchableOpacity
      style={styles.button}
      onPress={handlePress}
      disabled={isDisabled}
      activeOpacity={isDisabled ? 1 : theme.opacity.hover}
    >
      {isLoading ? (
        <ActivityIndicator
          color={colors.surface}
          size="small"
        />
      ) : (
        <Text style={styles.buttonText}>
          {getButtonText()}
        </Text>
      )}
    </TouchableOpacity>
  );
};

export default ResendButton;
