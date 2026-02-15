import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Alert,
  BackHandler,
  SafeAreaView,
  StatusBar,
} from 'react-native';
// ✅ Firebase Auth مُثبت - OTPService يتولى التحقق من SMS
import Icon from '../../components/CustomIcons';
import { useTheme } from '../../context/ThemeContext';
import OTPInput from './components/OTPInput';
import CountdownTimer from './components/CountdownTimer';
import ResendButton from './components/ResendButton';
import StatusMessage, { ErrorMessage, SuccessMessage } from './components/StatusMessage';
import OTPService from '../../services/OTPService';
import { theme } from '../../theme/theme';
import UnifiedBrandLogo from '../../components/UnifiedBrandLogo';
import ModernButton from '../../components/ModernButton';
import GlobalHeader from '../../components/GlobalHeader';

const { width, height } = Dimensions.get('window');

/**
 * شاشة إدخال OTP الموحدة - تدعم الإيميل و SMS (Firebase)
 * @param {object} navigation - التنقل
 * @param {object} route - معاملات الشاشة
 */
const OTPVerificationScreen = ({ navigation, route }) => {
  const { colors } = useTheme();
  const {
    email,
    phoneNumber,
    isPhone = false,
    operationType,
    additionalData = {},
    registrationData = {},
    maskedEmail,
    fromScreen = 'OTPSent',
  } = route.params || {};

  // الحالات المحلية
  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [isLoading, setIsLoading] = useState(false);
  const [attempts, setAttempts] = useState(0);
  const [hasError, setHasError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [successMessage, setSuccessMessage] = useState('');

  // Firebase Phone Auth State
  const [confirm, setConfirm] = useState(null);

  // المراجع
  const otpInputRef = useRef();
  const maxAttempts = 3;

  // الحصول على رسائل العملية
  const operationMessages = OTPService.getOperationMessages(operationType);

  useEffect(() => {
    // تحديث عنوان الشاشة
    navigation.setOptions({
      title: operationMessages.title || 'التحقق من الرمز',
    });

    // معالجة زر العودة في Android
    const backHandler = BackHandler.addEventListener('hardwareBackPress', handleBackPress);

    return () => {
      backHandler.remove();
    };
  }, [navigation, operationMessages]);

  // ✅ معالجة زر العودة - إلغاء OTP عند الخروج
  const handleBackPress = async () => {
    try {
      // إلغاء OTP النشط في Backend
      if (email && !isPhone) {
        await OTPService.cancelOTP(email, operationType);
      }
    } catch (error) {
      // Silent failure - لا نعيق المستخدم
      console.warn('Failed to cancel OTP on back:', error);
    }

    // الانتقال
    if (fromScreen === 'OTPSent') {
      navigation.goBack();
    } else {
      navigation.navigate('OTPSent', {
        email,
        phoneNumber,
        isPhone,
        operationType,
        additionalData,
        maskedEmail,
      });
    }
    return true;
  };

  // مسح الرسائل
  const clearMessages = () => {
    setHasError(false);
    setErrorMessage('');
    setSuccessMessage('');
  };

  // عرض رسالة خطأ
  const showError = (message) => {
    setHasError(true);
    setErrorMessage(message);
    setSuccessMessage('');

    // اهتزاز مكون OTP
    if (otpInputRef.current) {
      otpInputRef.current.shake();
    }
  };

  // عرض رسالة نجاح
  const showSuccess = (message) => {
    setHasError(false);
    setErrorMessage('');
    setSuccessMessage(message);
  };

  // تغيير قيم OTP
  const handleOtpChange = (newOtp) => {
    setOtp(newOtp);
    clearMessages();
  };

  // اكتمال إدخال OTP
  const handleOtpComplete = (otpCode) => {
    // منع الاستدعاء المتكرر أثناء التحميل
    if (isLoading) { return; }
    if (otpCode.length === 6) {
      verifyOTP(otpCode);
    }
  };

  // التحقق من OTP
  const verifyOTP = async (otpCode = null) => {
    const codeToVerify = otpCode || otp.join('');

    if (codeToVerify.length !== 6) {
      showError('يرجى إدخال رمز التحقق كاملاً (6 أرقام)');
      return;
    }

    if (!/^\d{6}$/.test(codeToVerify)) {
      showError('رمز التحقق يجب أن يحتوي على أرقام فقط');
      return;
    }

    setIsLoading(true);
    clearMessages();

    try {
      let result;

      // ✅ إذا كان تسجيل جديد: استخدم endpoint الجديد (سواء بريد أو SMS)
      const isRegistration = operationType === 'register' || operationType === 'REGISTER';
      if (isRegistration && registrationData && Object.keys(registrationData).length > 0) {
        // 🆕 التحقق من OTP وإنشاء الحساب
        const DatabaseApiService = require('../../services/DatabaseApiService').default;

        if (isPhone) {
          // 📱 التسجيل عبر SMS - التحقق من Firebase أولاً ثم إنشاء الحساب
          try {
            const phoneResult = await OTPService.verifyPhoneOTP(codeToVerify, {
              ...additionalData,
              ...registrationData,
            });

            if (phoneResult.success) {
              // Firebase تحقق بنجاح - الآن أنشئ الحساب في الخادم
              result = await DatabaseApiService.registerWithPhone({
                phone: registrationData.phone,
                username: registrationData.username,
                password: registrationData.password,
                fullName: registrationData.fullName,
                email: registrationData.email, // اختياري
                firebaseToken: phoneResult.data?.idToken,
              });
            } else {
              result = phoneResult;
            }
          } catch (phoneError) {
            console.error('خطأ في التحقق من SMS:', phoneError);
            result = { success: false, message: 'فشل التحقق من رقم الهاتف' };
          }
        } else {
          // 📧 التسجيل عبر البريد
          result = await DatabaseApiService.verifyRegistrationOTP({
            email: registrationData.email,
            otp_code: codeToVerify,
            username: registrationData.username,
            password: registrationData.password,
            phone: registrationData.phone,
            fullName: registrationData.fullName,
          });
        }
      } else {
        // التحقق لعمليات أخرى (تسجيل دخول، تغيير كلمة مرور، إلخ)
        if (isPhone) {
          // 📱 التحقق عبر SMS (Firebase)
          result = await OTPService.verifyPhoneOTP(codeToVerify, additionalData);
        } else {
          // 📧 التحقق عبر الإيميل
          result = await OTPService.verifyOTP(
            email,
            codeToVerify,
            operationType,
            additionalData
          );
        }
      }

      if (result.success) {
        showSuccess(result.message || operationMessages.successMessage);

        // ✅ إذا كان تسجيل جديد: حفظ الـ token وتسجيل الدخول تلقائياً
        const token = result.accessToken || result.access_token;
        const userId = result.userId || result.user_id;

        if (isRegistration && token && userId) {
          const TempStorageService = require('../../services/TempStorageService').default;

          // ✅ دالة حفظ مع Retry Logic (3 محاولات)
          const saveWithRetry = async (key, value, maxRetries = 3) => {
            for (let attempt = 1; attempt <= maxRetries; attempt++) {
              try {
                await TempStorageService.setItem(key, value);
                return true;
              } catch (err) {
                console.warn(`⚠️ محاولة ${attempt}/${maxRetries} لحفظ ${key} فشلت:`, err);
                if (attempt < maxRetries) {
                  await new Promise(resolve => setTimeout(resolve, 200 * attempt));
                }
              }
            }
            return false;
          };

          try {
            // حفظ بيانات المستخدم
            const userData = {
              id: userId,
              email: registrationData.email,
              username: registrationData.username,
              fullName: registrationData.fullName,
              user_type: 'user',
            };

            // ✅ حفظ بالترتيب مع Retry
            const saveResults = await Promise.all([
              saveWithRetry('userData', JSON.stringify(userData)),
              saveWithRetry('accessToken', token),
              saveWithRetry('isLoggedIn', 'true'),
              saveWithRetry('lastUserId', userId.toString()),
            ]);

            if (result.refreshToken || result.refresh_token) {
              await saveWithRetry('refreshToken', result.refreshToken || result.refresh_token);
            }

            // ✅ التحقق من نجاح الحفظ الأساسي
            const criticalSaveSuccess = saveResults[0] && saveResults[1] && saveResults[2];

            if (criticalSaveSuccess) {
              console.log('✅ تم حفظ بيانات المستخدم بعد التسجيل - userId:', userId);
            } else {
              console.warn('⚠️ بعض البيانات لم تُحفظ بشكل كامل:', saveResults);
            }

            // ✅ الانتقال مباشرة لشاشة النجاح مع البيانات الكاملة
            setTimeout(() => {
              navigation.replace('OTPSuccess', {
                email,
                phoneNumber,
                isPhone,
                operationType,
                additionalData: {
                  ...additionalData,
                  accessToken: token,
                  userId: userId,
                  registrationComplete: true,
                  storageSaveSuccess: criticalSaveSuccess,
                },
                registrationData: registrationData,
                message: result.message || operationMessages.successMessage,
                nextScreen: 'Dashboard',
              });
            }, 1500);

          } catch (saveError) {
            console.error('❌ خطأ حرج في حفظ بيانات المستخدم:', saveError);
            // ✅ حتى لو فشل الحفظ، ننتقل لشاشة النجاح مع البيانات في params
            setTimeout(() => {
              navigation.replace('OTPSuccess', {
                email,
                operationType,
                additionalData: {
                  accessToken: token,
                  userId: userId,
                  storageSaveSuccess: false,
                },
                registrationData: registrationData,
                message: result.message || operationMessages.successMessage,
                nextScreen: 'Dashboard',
              });
            }, 1500);
          }
        } else if (operationType === 'reset_password') {
          // ✅ استعادة كلمة المرور - التحقق من OTP والحصول على Reset Token
          const DatabaseApiService = require('../../services/DatabaseApiService').default;
          const verifyResult = await DatabaseApiService.verifyResetOTP(email, codeToVerify);

          if (verifyResult.success && verifyResult.reset_token) {
            showSuccess(verifyResult.message || 'تم التحقق بنجاح');
            setTimeout(() => {
              navigation.navigate('NewPassword', {
                email: email,
                resetToken: verifyResult.reset_token,
                verified: true,
              });
            }, 1000);
          } else {
            showError(verifyResult.message || 'فشل التحقق من الرمز');
            setOtp(['', '', '', '', '', '']);
          }
        } else {
          // عمليات أخرى (ليست تسجيل أو استعادة كلمة مرور)
          setTimeout(() => {
            navigation.replace('OTPSuccess', {
              email,
              phoneNumber,
              isPhone,
              operationType,
              additionalData: {
                ...additionalData,
                accessToken: token,
                userId: userId,
              },
              message: result.message || operationMessages.successMessage,
              nextScreen: operationMessages.nextScreen,
            });
          }, 1500);
        }

      } else {
        // ✅ استخدام remaining_attempts من Backend إذا متاح
        const serverRemaining = result.remaining_attempts;
        const isMaxExceeded = result.code === 'MAX_ATTEMPTS_EXCEEDED' || serverRemaining === 0;

        if (isMaxExceeded) {
          showError('تجاوزت الحد الأقصى (5 محاولات). اضغط "إعادة إرسال" أسفل الشاشة للحصول على رمز جديد.');

          // مسح OTP وتعطيل الإدخال مؤقتاً
          setOtp(['', '', '', '', '', '']);

          // العودة لشاشة الإرسال بعد 3 ثوان
          setTimeout(() => {
            navigation.navigate('OTPSent', {
              email,
              phoneNumber,
              isPhone,
              operationType,
              additionalData,
              maskedEmail,
            });
          }, 3000);

        } else {
          // ✅ عرض رسالة الخطأ التفصيلية من Backend
          const errorMsg = result.message || 'رمز التحقق غير صحيح';
          showError(errorMsg);

          // مسح OTP للمحاولة التالية
          setOtp(['', '', '', '', '', '']);

          // التركيز على أول حقل
          setTimeout(() => {
            if (otpInputRef.current) {
              otpInputRef.current.focus();
            }
          }, 500);
        }
      }

    } catch (error) {
      console.error('خطأ في التحقق من OTP:', error);
      showError('حدث خطأ في التحقق. يرجى المحاولة مرة أخرى.');
    } finally {
      setIsLoading(false);
    }
  };

  // إعادة إرسال OTP
  const handleResend = async () => {
    try {
      // ✅ Firebase Auth غير مثبت - استخدام الإيميل فقط
      // إعادة إرسال للإيميل
      const result = await OTPService.resendOTP(email, operationType, additionalData);
      if (!result.success) { throw new Error(result.message); }

      // إعادة تعيين المحاولات والرسائل
      setAttempts(0);
      clearMessages();
      setOtp(['', '', '', '', '', '']);

      showSuccess('تم إعادة إرسال رمز التحقق بنجاح');

      // التركيز على أول حقل
      setTimeout(() => {
        if (otpInputRef.current) {
          otpInputRef.current.focus();
        }
      }, 1000);

    } catch (error) {
      console.error('خطأ في إعادة الإرسال:', error);
      showError(error.message || 'حدث خطأ في إعادة الإرسال. يرجى المحاولة مرة أخرى.');
    }
  };

  // مسح OTP
  const clearOTP = () => {
    setOtp(['', '', '', '', '', '']);
    clearMessages();
    setAttempts(0);

    if (otpInputRef.current) {
      otpInputRef.current.clear();
    }
  };

  // انتهاء صلاحية الرمز
  const handleTimerComplete = () => {
    showError('انتهت صلاحية رمز التحقق. يرجى طلب رمز جديد.');

    setTimeout(() => {
      navigation.navigate('OTPSent', {
        email,
        phoneNumber,
        isPhone,
        operationType,
        additionalData,
        maskedEmail,
      });
    }, 2000);
  };

  const styles = StyleSheet.create({
    safeArea: {
      flex: 1,
      backgroundColor: theme.colors.background,
    },
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
    scrollContainer: {
      flexGrow: 1,
      justifyContent: 'center',
      padding: width * 0.05,
    },
    header: {
      alignItems: 'center',
      marginBottom: height * 0.04,
    },
    iconContainer: {
      width: width * 0.2,
      height: width * 0.2,
      borderRadius: width * 0.1,
      backgroundColor: colors.primary + '20',
      justifyContent: 'center',
      alignItems: 'center',
      marginBottom: 20,
    },
    title: {
      fontSize: width * 0.06,
      fontWeight: 'bold',
      color: colors.text,
      textAlign: 'center',
      marginBottom: 10,
    },
    subtitle: {
      fontSize: width * 0.04,
      color: colors.textSecondary,
      textAlign: 'center',
      lineHeight: 22,
    },
    emailContainer: {
      backgroundColor: colors.surface,
      borderRadius: 12,
      padding: 12,
      marginVertical: 20,
      alignItems: 'center',
    },
    emailLabel: {
      fontSize: width * 0.035,
      color: colors.textSecondary,
      marginBottom: 4,
    },
    emailText: {
      fontSize: width * 0.04,
      fontWeight: '600',
      color: colors.text,
      fontFamily: 'monospace',
    },
    otpContainer: {
      alignItems: 'center',
      marginVertical: 20,
    },
    otpLabel: {
      fontSize: width * 0.04,
      fontWeight: '600',
      color: colors.text,
      marginBottom: 16,
      textAlign: 'center',
    },
    timerContainer: {
      alignItems: 'center',
      marginTop: 16,
    },
    verifyButton: {
      backgroundColor: colors.primary,
      borderRadius: 12,
      padding: 16,
      alignItems: 'center',
      marginTop: 20,
    },
    verifyButtonDisabled: {
      backgroundColor: colors.border,
    },
    verifyButtonText: {
      color: colors.surface,
      fontSize: width * 0.045,
      fontWeight: 'bold',
    },
    actionsContainer: {
      marginTop: 20,
      alignItems: 'center',
    },
    clearButton: {
      padding: 12,
      marginTop: 10,
    },
    clearButtonText: {
      color: colors.textSecondary,
      fontSize: width * 0.035,
      textDecorationLine: 'underline',
    },
    resendContainer: {
      alignItems: 'center',
      marginTop: 30,
      paddingTop: 20,
      borderTopWidth: 1,
      borderTopColor: colors.border,
    },
    resendLabel: {
      fontSize: width * 0.035,
      color: colors.textSecondary,
      marginBottom: 12,
      textAlign: 'center',
    },
    attemptsContainer: {
      alignItems: 'center',
      marginTop: 10,
    },
    attemptsText: {
      fontSize: width * 0.03,
      color: colors.textSecondary,
    },
    backButton: {
      position: 'absolute',
      top: Platform.OS === 'ios' ? 50 : 20,
      right: 20,
      width: 40,
      height: 40,
      borderRadius: 20,
      backgroundColor: colors.surface,
      justifyContent: 'center',
      alignItems: 'center',
      elevation: 2,
      shadowColor: '#000',
      shadowOffset: { width: 0, height: 2 },
      shadowOpacity: 0.1,
      shadowRadius: 4,
    },
    messagesContainer: {
      marginVertical: 10,
    },
    logoContainer: {
      alignItems: 'center',
      marginBottom: 20,
    },
    progressStepsContainer: {
      flexDirection: 'row',
      justifyContent: 'center',
      alignItems: 'center',
      marginBottom: 30,
      paddingHorizontal: 20,
    },
    stepWrapper: {
      alignItems: 'center',
      flexDirection: 'row',
    },
    stepCircle: {
      width: 28,
      height: 28,
      borderRadius: 14,
      backgroundColor: colors.border,
      justifyContent: 'center',
      alignItems: 'center',
    },
    stepCompleted: {
      backgroundColor: colors.success,
    },
    stepActive: {
      backgroundColor: colors.primary,
      borderWidth: 2,
      borderColor: colors.primary + '50',
    },
    stepNumber: {
      fontSize: 12,
      fontWeight: 'bold',
      color: colors.textSecondary,
    },
    stepNumberActive: {
      color: '#fff',
    },
    stepLabel: {
      fontSize: 11,
      color: colors.textSecondary,
      marginLeft: 4,
      marginRight: 8,
    },
    stepLabelActive: {
      color: colors.primary,
      fontWeight: 'bold',
    },
    stepLine: {
      width: 30,
      height: 2,
      backgroundColor: colors.border,
      marginHorizontal: 4,
    },
    stepLineCompleted: {
      backgroundColor: colors.success,
    },
  });

  // ✅ شريط تقدم التسجيل (للتسجيل فقط)
  const isRegistration = operationType === 'register';
  const registrationSteps = [
    { id: 1, label: 'البيانات', completed: true },
    { id: 2, label: 'التحقق', completed: false, active: true },
    { id: 3, label: 'الانتهاء', completed: false },
  ];

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="light-content" backgroundColor={theme.colors.background} />

      <GlobalHeader
        title={operationMessages.title || 'التحقق من الرمز'}
        showBack={true}
        onBack={handleBackPress}
      />

      <KeyboardAvoidingView
        style={styles.container}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContainer}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          {/* ✅ شعار التطبيق */}
          <View style={styles.logoContainer}>
            <UnifiedBrandLogo variant="compact" />
          </View>

          {/* ✅ شريط تقدم التسجيل */}
          {isRegistration && (
            <View style={styles.progressStepsContainer}>
              {registrationSteps.map((step, index) => (
                <View key={step.id} style={styles.stepWrapper}>
                  <View style={[
                    styles.stepCircle,
                    step.completed && styles.stepCompleted,
                    step.active && styles.stepActive,
                  ]}>
                    {step.completed ? (
                      <Icon name="check" size={14} color="#fff" />
                    ) : (
                      <Text style={[
                        styles.stepNumber,
                        step.active && styles.stepNumberActive,
                      ]}>{step.id}</Text>
                    )}
                  </View>
                  <Text style={[
                    styles.stepLabel,
                    step.active && styles.stepLabelActive,
                  ]}>{step.label}</Text>
                  {index < registrationSteps.length - 1 && (
                    <View style={[
                      styles.stepLine,
                      step.completed && styles.stepLineCompleted,
                    ]} />
                  )}
                </View>
              ))}
            </View>
          )}

          {/* الرأس */}
          <View style={styles.header}>
            <View style={styles.iconContainer}>
              <Icon
                name={isPhone ? 'phone-iphone' : 'email'}
                size={width * 0.1}
                color={colors.primary}
              />
            </View>
            <Text style={styles.title}>
              {operationMessages.title}
            </Text>
            <Text style={styles.subtitle}>
              {isPhone ? 'أدخل رمز التحقق المرسل إلى هاتفك' : 'أدخل رمز التحقق المرسل إلى إيميلك'}
            </Text>
          </View>

          {/* عرض الإيميل أو الهاتف */}
          <View style={styles.emailContainer}>
            <Text style={styles.emailLabel}>
              {isPhone ? 'رقم الهاتف:' : 'الإيميل:'}
            </Text>
            <Text style={styles.emailText}>
              {isPhone ? phoneNumber : (maskedEmail || OTPService.maskEmail(email))}
            </Text>
          </View>

          {/* رسائل الحالة */}
          <View style={styles.messagesContainer}>
            {errorMessage && (
              <ErrorMessage
                message={errorMessage}
                visible={!!errorMessage}
              />
            )}
            {successMessage && (
              <SuccessMessage
                message={successMessage}
                visible={!!successMessage}
              />
            )}
          </View>

          {/* إدخال OTP */}
          <View style={styles.otpContainer}>
            <Text style={styles.otpLabel}>
              رمز التحقق
            </Text>

            <OTPInput
              ref={otpInputRef}
              length={6}
              value={otp}
              onChange={handleOtpChange}
              onComplete={handleOtpComplete}
              disabled={isLoading || attempts >= maxAttempts}
              autoFocus={true}
              hasError={hasError}
            />

            {/* العداد التنازلي */}
            <View style={styles.timerContainer}>
              <CountdownTimer
                initialTime={300} // 5 دقائق
                onComplete={handleTimerComplete}
              />
            </View>
          </View>

          {/* عرض عدد المحاولات */}
          {attempts > 0 && (
            <View style={styles.attemptsContainer}>
              <Text style={styles.attemptsText}>
                المحاولة {attempts} من {maxAttempts}
              </Text>
            </View>
          )}

          {/* إعادة الإرسال */}
          <View style={styles.resendContainer}>
            <Text style={styles.resendLabel}>
              لم يصل الرمز أو انتهت صلاحيته؟
            </Text>
            <ResendButton
              onPress={handleResend}
              cooldownTime={60}
            />
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

export default OTPVerificationScreen;
