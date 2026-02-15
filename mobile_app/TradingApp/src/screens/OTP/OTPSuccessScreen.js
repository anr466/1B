import React, { useEffect, useState, useRef } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Dimensions,
  Animated,
  BackHandler,
  SafeAreaView,
  StatusBar,
  ActivityIndicator,
} from 'react-native';
import Icon from '../../components/CustomIcons';
import { useTheme } from '../../context/ThemeContext';
import OTPService from '../../services/OTPService';
import { theme } from '../../theme/theme';
import UnifiedBrandLogo from '../../components/UnifiedBrandLogo';
import ModernButton from '../../components/ModernButton';

const { width, height } = Dimensions.get('window');

/**
 * شاشة النجاح بعد التحقق من OTP
 * @param {object} navigation - التنقل
 * @param {object} route - معاملات الشاشة
 */
const OTPSuccessScreen = ({ navigation, route }) => {
  const { colors } = useTheme();
  const {
    email,
    operationType,
    additionalData = {},
    message,
    nextScreen = 'Dashboard',
    autoRedirect = true,
    redirectDelay = 3000,
  } = route.params || {};

  // الحالات المحلية
  const [countdown, setCountdown] = useState(Math.floor(redirectDelay / 1000));
  const [isRedirecting, setIsRedirecting] = useState(false);

  // تأثيرات الحركة - ✅ استخدام useRef لمنع إعادة الإنشاء
  const scaleValue = useRef(new Animated.Value(0)).current;
  const fadeValue = useRef(new Animated.Value(0)).current;
  const progressValue = useRef(new Animated.Value(0)).current;

  // الحصول على رسائل العملية
  const operationMessages = OTPService.getOperationMessages(operationType);

  useEffect(() => {
    // تشغيل تأثير الظهور
    startAnimations();

    // تحديث عنوان الشاشة
    navigation.setOptions({
      title: 'تم بنجاح',
      headerLeft: null, // إخفاء زر العودة
    });

    // منع العودة بزر الأندرويد
    const backHandler = BackHandler.addEventListener('hardwareBackPress', () => true);

    // بدء العداد التنازلي للتوجيه التلقائي
    if (autoRedirect) {
      startCountdown();
    }

    return () => {
      backHandler.remove();
    };
  }, []);

  // تشغيل تأثيرات الحركة
  const startAnimations = () => {
    Animated.parallel([
      Animated.spring(scaleValue, {
        toValue: 1,
        tension: 50,
        friction: 7,
        useNativeDriver: true,
      }),
      Animated.timing(fadeValue, {
        toValue: 1,
        duration: 800,
        useNativeDriver: true,
      }),
    ]).start();
  };

  // بدء العداد التنازلي مع شريط التقدم
  const startCountdown = () => {
    // ✅ تحريك شريط التقدم
    Animated.timing(progressValue, {
      toValue: 1,
      duration: redirectDelay,
      useNativeDriver: false,
    }).start();

    const timer = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          clearInterval(timer);
          handleRedirect();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  // التوجيه للشاشة التالية
  const handleRedirect = async () => {
    if (isRedirecting) { return; }

    setIsRedirecting(true);

    // تحديد الشاشة التالية حسب نوع العملية
    switch (operationType) {
      case 'register':
        // ✅ المستخدم الجديد يذهب إلى الشاشة الرئيسية التي ستعرض Onboarding تلقائياً
        // لأن onboarding_completed لم يُحفظ بعد
        navigation.reset({
          index: 0,
          routes: [{ name: 'Dashboard' }],
        });
        break;

      case 'change_email':
        navigation.reset({
          index: 0,
          routes: [
            { name: 'Dashboard' },
            { name: 'Settings' },
          ],
        });
        break;

      case 'change_password':
        // تسجيل خروج تلقائي بعد تغيير كلمة المرور
        navigation.reset({
          index: 0,
          routes: [{ name: 'Login' }],
        });
        break;

      case 'reset_password':
        navigation.reset({
          index: 0,
          routes: [{ name: 'Login' }],
        });
        break;

      default:
        navigation.reset({
          index: 0,
          routes: [{ name: nextScreen || 'Dashboard' }],
        });
    }
  };

  // التوجيه الفوري
  const handleContinue = () => {
    handleRedirect();
  };

  // الحصول على الرسالة المناسبة
  const getSuccessMessage = () => {
    if (message) { return message; }

    switch (operationType) {
      case 'register':
        return 'تم إنشاء حسابك بنجاح! مرحباً بك في 1B Trading';
      case 'change_email':
        return `تم تغيير إيميلك بنجاح إلى ${additionalData.newEmail || email}`;
      case 'change_password':
        return 'تم تغيير كلمة المرور بنجاح. يرجى تسجيل الدخول مرة أخرى';
      case 'reset_password':
        return 'تم إعادة تعيين كلمة المرور بنجاح. يمكنك الآن تسجيل الدخول';
      default:
        return operationMessages.successMessage || 'تم التحقق بنجاح!';
    }
  };

  // الحصول على النص التوضيحي
  const getSubtitle = () => {
    switch (operationType) {
      case 'register':
        return 'سنوجهك الآن لإعداد حسابك خطوة بخطوة';
      case 'change_email':
        return 'تم تحديث عنوان إيميلك في حسابك';
      case 'change_password':
        return 'من أجل الأمان، يرجى تسجيل الدخول بكلمة المرور الجديدة';
      case 'reset_password':
        return 'يمكنك الآن تسجيل الدخول بكلمة المرور الجديدة';
      default:
        return 'تم إكمال العملية بنجاح';
    }
  };

  // الحصول على نص الزر
  const getButtonText = () => {
    switch (operationType) {
      case 'register':
        return 'ابدأ الإعداد';
      case 'change_email':
        return 'العودة للإعدادات';
      case 'change_password':
      case 'reset_password':
        return 'تسجيل الدخول';
      default:
        return 'المتابعة';
    }
  };

  // الحصول على أيقونة النجاح
  const getSuccessIcon = () => {
    switch (operationType) {
      case 'register':
        return 'person-add';
      case 'change_email':
        return 'email';
      case 'change_password':
      case 'reset_password':
        return 'lock';
      default:
        return 'check-circle';
    }
  };

  const styles = StyleSheet.create({
    safeArea: {
      flex: 1,
      backgroundColor: theme.colors.background,
    },
    container: {
      flex: 1,
      backgroundColor: colors.background,
      justifyContent: 'center',
      alignItems: 'center',
      padding: width * 0.05,
    },
    animatedContainer: {
      alignItems: 'center',
    },
    iconContainer: {
      width: width * 0.3,
      height: width * 0.3,
      borderRadius: width * 0.15,
      backgroundColor: colors.success + '20',
      justifyContent: 'center',
      alignItems: 'center',
      marginBottom: 30,
      elevation: 5,
      shadowColor: colors.success,
      shadowOffset: { width: 0, height: 4 },
      shadowOpacity: 0.3,
      shadowRadius: 8,
    },
    successIcon: {
      marginBottom: 10,
    },
    checkIcon: {
      position: 'absolute',
      bottom: -5,
      right: -5,
      backgroundColor: colors.success,
      borderRadius: 15,
      width: 30,
      height: 30,
      justifyContent: 'center',
      alignItems: 'center',
    },
    title: {
      fontSize: width * 0.07,
      fontWeight: 'bold',
      color: colors.text,
      textAlign: 'center',
      marginBottom: 15,
    },
    subtitle: {
      fontSize: width * 0.04,
      color: colors.textSecondary,
      textAlign: 'center',
      lineHeight: 24,
      marginBottom: 30,
    },
    messageContainer: {
      width: '100%',
      marginBottom: 30,
    },
    continueButton: {
      backgroundColor: colors.success,
      borderRadius: 12,
      paddingVertical: 16,
      paddingHorizontal: 32,
      minWidth: width * 0.6,
      alignItems: 'center',
      elevation: 3,
      shadowColor: colors.success,
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.3,
      shadowRadius: 4,
    },
    continueButtonText: {
      color: colors.surface,
      fontSize: width * 0.045,
      fontWeight: 'bold',
    },
    countdownContainer: {
      marginTop: 20,
      alignItems: 'center',
    },
    countdownText: {
      fontSize: width * 0.035,
      color: colors.textSecondary,
      textAlign: 'center',
      marginLeft: 10,
    },
    logoContainer: {
      position: 'absolute',
      top: 40,
      alignItems: 'center',
      width: '100%',
    },
    successText: {
      fontSize: width * 0.04,
      color: colors.textSecondary,
      textAlign: 'center',
      lineHeight: 24,
      marginBottom: 40,
      paddingHorizontal: 20,
    },
    progressContainer: {
      width: '80%',
      alignItems: 'center',
      marginTop: 20,
    },
    progressBar: {
      width: '100%',
      height: 6,
      backgroundColor: colors.border,
      borderRadius: 3,
      overflow: 'hidden',
    },
    progressFill: {
      height: '100%',
      backgroundColor: colors.success,
      borderRadius: 3,
    },
    redirectInfo: {
      flexDirection: 'row',
      alignItems: 'center',
      marginTop: 15,
    },
  });

  // ✅ عرض شريط التقدم
  const progressWidth = progressValue.interpolate({
    inputRange: [0, 1],
    outputRange: ['0%', '100%'],
  });

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="light-content" backgroundColor={theme.colors.background} />
      <View style={styles.container}>
        {/* ✅ شعار التطبيق */}
        <View style={styles.logoContainer}>
          <UnifiedBrandLogo variant="compact" />
        </View>

        <Animated.View
          style={[
            styles.animatedContainer,
            {
              transform: [{ scale: scaleValue }],
              opacity: fadeValue,
            },
          ]}
        >
          {/* أيقونة النجاح */}
          <View style={styles.iconContainer}>
            <Icon
              name="check-circle"
              size={width * 0.2}
              color={colors.success}
            />
          </View>

          {/* العنوان */}
          <Text style={styles.title}>
            {operationType === 'register' ? 'مرحباً بك!' : 'تم بنجاح!'}
          </Text>

          {/* رسالة النجاح */}
          <Text style={styles.successText}>
            {getSuccessMessage()}
          </Text>

          {/* ✅ شريط التقدم + زر احتياطي */}
          {autoRedirect && countdown > 0 && (
            <View style={styles.progressContainer}>
              <View style={styles.progressBar}>
                <Animated.View
                  style={[
                    styles.progressFill,
                    { width: progressWidth },
                  ]}
                />
              </View>
              <View style={styles.redirectInfo}>
                <ActivityIndicator size="small" color={colors.success} />
                <Text style={styles.countdownText}>
                  جاري التوجيه... {countdown} ثانية
                </Text>
              </View>
            </View>
          )}

          {/* ✅ زر احتياطي يظهر عند انتهاء العد التنازلي */}
          {countdown <= 0 && !isRedirecting && (
            <ModernButton
              title={getButtonText()}
              onPress={handleContinue}
              variant="primary"
              size="large"
              style={{ marginTop: 20, minWidth: width * 0.6 }}
            />
          )}
        </Animated.View>
      </View>
    </SafeAreaView>
  );
};

export default OTPSuccessScreen;
