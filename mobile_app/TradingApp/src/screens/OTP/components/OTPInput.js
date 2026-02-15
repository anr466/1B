import React, { useRef, useEffect, forwardRef, useImperativeHandle } from 'react';
import {
  View,
  TextInput,
  StyleSheet,
  Dimensions,
  Animated,
  I18nManager,
} from 'react-native';
import { useTheme } from '../../../context/ThemeContext';

const { width } = Dimensions.get('window');

/**
 * مكون إدخال OTP محسن مع تأثيرات بصرية
 * @param {number} length - عدد خانات OTP (افتراضي: 6)
 * @param {array} value - قيم OTP الحالية
 * @param {function} onChange - دالة تغيير القيم
 * @param {function} onComplete - دالة عند اكتمال الإدخال
 * @param {boolean} disabled - حالة التعطيل
 * @param {boolean} autoFocus - التركيز التلقائي على أول حقل
 * @param {boolean} hasError - إظهار حالة خطأ
 * @param {object} style - أنماط إضافية للحاوية
 */
const OTPInput = forwardRef(({
  length = 6,
  value = [],
  onChange,
  onComplete,
  disabled = false,
  autoFocus = false,
  hasError = false,
  style = {},
}, ref) => {
  const { colors } = useTheme();
  const inputRefs = useRef([]);
  const animatedValues = useRef(Array(length).fill(0).map(() => new Animated.Value(1))).current;

  // تعريض وظائف للمكون الأب
  useImperativeHandle(ref, () => ({
    focus: () => {
      inputRefs.current[0]?.focus();
    },
    clear: () => {
      const newValue = Array(length).fill('');
      onChange(newValue);
      inputRefs.current[0]?.focus();
    },
    shake: () => {
      // تأثير اهتزاز عند الخطأ
      const shakeAnimation = Animated.sequence([
        Animated.timing(animatedValues[0], { toValue: 1.1, duration: 100, useNativeDriver: true }),
        Animated.timing(animatedValues[0], { toValue: 0.9, duration: 100, useNativeDriver: true }),
        Animated.timing(animatedValues[0], { toValue: 1.1, duration: 100, useNativeDriver: true }),
        Animated.timing(animatedValues[0], { toValue: 1, duration: 100, useNativeDriver: true }),
      ]);

      shakeAnimation.start();
    },
  }));

  useEffect(() => {
    if (autoFocus && inputRefs.current[0]) {
      setTimeout(() => inputRefs.current[0].focus(), 100);
    }
  }, [autoFocus]);

  // استخدام ref لتتبع آخر قيمة مكتملة لمنع الاستدعاء المتكرر
  const lastCompletedValue = useRef('');

  useEffect(() => {
    const currentValue = value.join('');
    // استدعاء onComplete فقط إذا اكتمل الرمز ولم يُستدعى من قبل بنفس القيمة
    if (currentValue.length === length && onComplete && currentValue !== lastCompletedValue.current) {
      lastCompletedValue.current = currentValue;
      onComplete(currentValue);
    }
    // إعادة تعيين عند مسح الرمز
    if (currentValue.length === 0) {
      lastCompletedValue.current = '';
    }
  }, [value, length, onComplete]);

  // تأثير بصري عند التركيز
  const handleFocus = (index) => {
    Animated.spring(animatedValues[index], {
      toValue: 1.05,
      useNativeDriver: true,
    }).start();
  };

  // إزالة التأثير عند فقدان التركيز
  const handleBlur = (index) => {
    Animated.spring(animatedValues[index], {
      toValue: 1,
      useNativeDriver: true,
    }).start();
  };

  const handleChange = (text, index) => {
    if (text.length > 1) { return; } // منع إدخال أكثر من رقم واحد

    const newValue = [...value];
    newValue[index] = text;
    onChange(newValue);

    // الانتقال للحقل التالي تلقائياً
    if (text && index < length - 1) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyPress = (key, index) => {
    if (key === 'Backspace' && !value[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  // تحديد لون الحدود حسب الحالة
  const getBorderColor = (index) => {
    if (hasError) { return colors.error; }
    if (value[index]) { return colors.success; }
    return colors.border;
  };

  // تحديد لون الخلفية حسب الحالة
  const getBackgroundColor = (index) => {
    if (hasError) { return colors.error + '10'; }
    if (value[index]) { return colors.success + '10'; }
    return colors.surface;
  };

  // ✅ حساب الـ index الفعلي في بيئة RTL
  const getActualIndex = (visualIndex) => {
    // في RTL، نعكس الترتيب المرئي ليتطابق مع الترتيب المنطقي
    return I18nManager.isRTL ? (length - 1 - visualIndex) : visualIndex;
  };

  const styles = StyleSheet.create({
    container: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      alignItems: 'center',
      direction: 'ltr',
      ...style,
    },
    inputContainer: {
      width: width * 0.12,
      height: width * 0.12,
      marginHorizontal: 4,
    },
    input: {
      width: '100%',
      height: '100%',
      backgroundColor: colors.surface,
      borderRadius: 12,
      textAlign: 'center',
      fontSize: width * 0.05,
      fontWeight: 'bold',
      color: colors.text,
      borderWidth: 2,
    },
    inputFilled: {
      backgroundColor: colors.primary + '10',
      borderColor: colors.primary,
    },
    inputError: {
      backgroundColor: colors.error + '10',
      borderColor: colors.error,
    },
    inputDisabled: {
      backgroundColor: colors.border + '30',
      color: colors.textSecondary,
    },
  });

  return (
    <View style={styles.container}>
      {Array(length).fill(0).map((_, visualIndex) => {
        const index = visualIndex; // الترتيب المنطقي = الترتيب المرئي (LTR)
        return (
          <Animated.View
            key={index}
            style={[
              styles.inputContainer,
              { transform: [{ scale: animatedValues[index] }] },
            ]}
          >
            <TextInput
              ref={inputRef => inputRefs.current[index] = inputRef}
              style={[
                styles.input,
                {
                  borderColor: getBorderColor(index),
                  backgroundColor: getBackgroundColor(index),
                },
                value[index] && styles.inputFilled,
                hasError && styles.inputError,
                disabled && styles.inputDisabled,
              ]}
              value={value[index] || ''}
              onChangeText={(text) => handleChange(text, index)}
              onKeyPress={({ nativeEvent }) => handleKeyPress(nativeEvent.key, index)}
              onFocus={() => handleFocus(index)}
              onBlur={() => handleBlur(index)}
              keyboardType="numeric"
              maxLength={1}
              selectTextOnFocus
              editable={!disabled}
              autoCorrect={false}
              autoCapitalize="none"
              returnKeyType={index === length - 1 ? 'done' : 'next'}
              textContentType="oneTimeCode"
              writingDirection="ltr"
              accessibilityLabel={`رقم التحقق ${index + 1} من ${length}`}
              accessibilityHint="أدخل رقم واحد"
              accessibilityState={{ disabled }}
            />
          </Animated.View>
        );
      })}
    </View>
  );
});

export default OTPInput;
