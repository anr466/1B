import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Dimensions,
  ScrollView,
  Linking,
  Platform,
  SafeAreaView,
  StatusBar,
  ActivityIndicator,
} from 'react-native';
import Icon from '../../components/CustomIcons';
import { useTheme } from '../../context/ThemeContext';
import { InfoMessage } from './components/StatusMessage';
import ResendButton from './components/ResendButton';
import OTPService from '../../services/OTPService';
import ToastService from '../../services/ToastService';
import { theme } from '../../theme/theme';
import VerificationMethodSelector, { VERIFICATION_METHODS } from '../../components/VerificationMethodSelector';
import ModernButton from '../../components/ModernButton';
import GlobalHeader from '../../components/GlobalHeader';

const { width, height } = Dimensions.get('window');

/**
 * شاشة اختيار طريقة التحقق + تأكيد إرسال OTP
 * ✅ خطوتين: 1) اختيار SMS/Email  2) تأكيد الإرسال والانتقال لإدخال الرمز
 */
const OTPSentScreen = ({ navigation, route }) => {
  const { colors } = useTheme();
  const {
    email,
    phoneNumber,
    isPhone: initialIsPhone = false,
    operationType,
    additionalData = {},
    maskedEmail: initialMaskedEmail,
    registrationData = {},
    // ✅ إذا كان OTP أُرسل مسبقاً (من شاشة سابقة)، ننتقل مباشرة للخطوة 2
    otpAlreadySent = false,
    sentMethod = null,
    sentMaskedTarget = null,
  } = route.params || {};

  // ✅ الحالات
  const [step, setStep] = useState(otpAlreadySent ? 'sent' : 'select'); // select | sending | sent
  const [selectedMethod, setSelectedMethod] = useState(
    initialIsPhone ? VERIFICATION_METHODS.SMS
      : (phoneNumber ? VERIFICATION_METHODS.SMS : VERIFICATION_METHODS.EMAIL)
  );
  const [isLoading, setIsLoading] = useState(false);
  const [isPhone, setIsPhone] = useState(initialIsPhone);
  const [maskedTarget, setMaskedTarget] = useState(
    sentMaskedTarget || initialMaskedEmail || ''
  );

  // الحصول على رسائل العملية
  const operationMessages = OTPService.getOperationMessages(operationType);

  useEffect(() => {
    navigation.setOptions({
      title: step === 'select' ? 'طريقة التحقق' : (operationMessages.title || 'تأكيد الإرسال'),
    });
  }, [navigation, operationMessages, step]);

  // ✅ هل لدينا رقم هاتف حقيقي (وليس placeholder)؟
  const hasRealPhone = phoneNumber && phoneNumber !== 'phone_from_backend';

  // ✅ إرسال OTP بالطريقة المختارة
  const handleSendOTP = async () => {
    setIsLoading(true);
    try {
      const isSms = selectedMethod === VERIFICATION_METHODS.SMS;

      // ✅ إذا SMS مع رقم حقيقي → Firebase. إذا SMS بدون رقم حقيقي → Backend يرسل SMS
      const useFirebaseSms = isSms && hasRealPhone;
      const target = useFirebaseSms ? phoneNumber : email;

      if (!target) {
        ToastService.showError(isSms ? 'رقم الهاتف غير متوفر' : 'البريد الإلكتروني غير متوفر');
        setIsLoading(false);
        return;
      }

      const result = await OTPService.sendOTP(target, operationType, {
        ...additionalData,
        ...registrationData,
        isPhone: useFirebaseSms, // ✅ Firebase فقط مع رقم حقيقي
        method: selectedMethod,  // ✅ Backend يعرف الطريقة المطلوبة
        phone: hasRealPhone ? phoneNumber : null,
        email: email,
      });

      if (result.success) {
        setIsPhone(isSms);
        setMaskedTarget(
          result.data?.masked_target
          || result.masked_target
          || (isSms && hasRealPhone ? OTPService.maskPhone(phoneNumber) : null)
          || additionalData.maskedPhone
          || (email ? OTPService.maskEmail(email) : '')
        );
        setStep('sent');
        ToastService.showSuccess(result.message || 'تم إرسال رمز التحقق');
      } else {
        ToastService.showError(result.message || 'فشل في إرسال رمز التحقق');
      }
    } catch (error) {
      console.error('خطأ في إرسال OTP:', error);
      ToastService.showError('حدث خطأ في إرسال رمز التحقق');
    } finally {
      setIsLoading(false);
    }
  };

  // فتح تطبيق الإيميل
  const openEmailApp = () => {
    const emailApps = {
      ios: ['message://', 'googlegmail://', 'ms-outlook://', 'ymail://'],
      android: ['mailto:', 'googlegmail://', 'ms-outlook://'],
    };
    const apps = Platform.OS === 'ios' ? emailApps.ios : emailApps.android;
    const tryOpenApp = (index = 0) => {
      if (index >= apps.length) {
        Linking.openURL(`mailto:${email}`);
        return;
      }
      Linking.canOpenURL(apps[index])
        .then(supported => supported ? Linking.openURL(apps[index]) : tryOpenApp(index + 1))
        .catch(() => tryOpenApp(index + 1));
    };
    tryOpenApp();
  };

  // إعادة إرسال OTP
  const handleResend = async () => {
    try {
      const target = isPhone ? phoneNumber : email;
      const result = await OTPService.resendOTP(target, operationType, {
        ...additionalData,
        isPhone,
        method: selectedMethod,
        phone: phoneNumber,
        email: email,
      });
      if (result.success) {
        ToastService.showSuccess('تم إعادة إرسال الرمز بنجاح');
      } else {
        ToastService.showError(result.message || 'فشل في إعادة الإرسال');
      }
    } catch (error) {
      console.error('خطأ في إعادة الإرسال:', error);
    }
  };

  // الانتقال إلى شاشة إدخال OTP
  const goToVerification = () => {
    navigation.navigate('OTPVerification', {
      email,
      phoneNumber,
      isPhone,
      operationType,
      additionalData: { ...additionalData, method: selectedMethod },
      maskedEmail: maskedTarget,
      registrationData,
    });
  };

  // العودة
  const goBack = () => {
    if (step === 'sent') {
      setStep('select');
    } else {
      navigation.goBack();
    }
  };

  // ✅ تحديد الطرق المتاحة
  const availableMethods = [];
  if (phoneNumber) { availableMethods.push('sms'); }
  if (email) { availableMethods.push('email'); }

  const styles = StyleSheet.create({
    safeArea: { flex: 1, backgroundColor: theme.colors.background },
    container: { flex: 1, backgroundColor: colors.background },
    scrollContainer: { flexGrow: 1, justifyContent: 'center', padding: width * 0.05 },
    header: { alignItems: 'center', marginBottom: height * 0.03 },
    iconContainer: {
      width: width * 0.2, height: width * 0.2, borderRadius: width * 0.1,
      backgroundColor: colors.primary + '20', justifyContent: 'center', alignItems: 'center', marginBottom: 16,
    },
    title: { fontSize: width * 0.055, fontWeight: 'bold', color: colors.text, textAlign: 'center', marginBottom: 8 },
    subtitle: { fontSize: width * 0.038, color: colors.textSecondary, textAlign: 'center', lineHeight: 22 },
    targetContainer: {
      backgroundColor: colors.surface, borderRadius: 12, padding: 16, marginVertical: 16,
      borderLeftWidth: 4, borderLeftColor: colors.primary,
    },
    targetLabel: { fontSize: width * 0.035, color: colors.textSecondary, marginBottom: 4, textAlign: 'center' },
    targetText: { fontSize: width * 0.042, fontWeight: 'bold', color: colors.text, textAlign: 'center', fontFamily: 'monospace' },
    actionsContainer: { marginTop: 16 },
    primaryButton: { backgroundColor: colors.primary, borderRadius: 12, padding: 16, alignItems: 'center', marginBottom: 12 },
    primaryButtonDisabled: { backgroundColor: colors.border },
    primaryButtonText: { color: '#FFFFFF', fontSize: width * 0.042, fontWeight: 'bold' },
    secondaryButton: {
      backgroundColor: colors.surface, borderRadius: 12, padding: 16, alignItems: 'center',
      marginBottom: 12, borderWidth: 1, borderColor: colors.border,
    },
    secondaryButtonText: { color: colors.text, fontSize: width * 0.038, fontWeight: '600' },
    resendContainer: { alignItems: 'center', marginTop: 20 },
    resendLabel: { fontSize: width * 0.035, color: colors.textSecondary, marginBottom: 12, textAlign: 'center' },
    backButton: {
      position: 'absolute', top: Platform.OS === 'ios' ? 50 : 20, right: 20,
      width: 40, height: 40, borderRadius: 20, backgroundColor: colors.surface,
      justifyContent: 'center', alignItems: 'center', elevation: 2, zIndex: 10,
      shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.1, shadowRadius: 4,
    },
    infoContainer: { marginTop: 16 },
    changeMethodButton: { alignItems: 'center', padding: 12, marginTop: 8 },
    changeMethodText: { color: colors.primary, fontSize: width * 0.035, fontWeight: '600' },
  });

  // ==================== خطوة 1: اختيار طريقة التحقق ====================
  const renderSelectStep = () => (
    <>
      <View style={styles.header}>
        <View style={styles.iconContainer}>
          <Icon name="verified-user" size={width * 0.09} color={colors.primary} />
        </View>
        <Text style={styles.title}>{operationMessages.title || 'التحقق من الهوية'}</Text>
        <Text style={styles.subtitle}>اختر الطريقة المفضلة لاستلام رمز التحقق</Text>
      </View>

      <VerificationMethodSelector
        selectedMethod={selectedMethod}
        onSelect={setSelectedMethod}
        disabled={isLoading}
        maskedPhone={
          additionalData.maskedPhone
          || (phoneNumber && phoneNumber !== 'phone_from_backend' ? OTPService.maskPhone(phoneNumber) : null)
        }
        maskedEmail={additionalData.maskedEmail || (email ? OTPService.maskEmail(email) : null)}
        availableMethods={availableMethods.length > 0 ? availableMethods : null}
      />

      <View style={styles.actionsContainer}>
        <ModernButton
          title="إرسال رمز التحقق"
          onPress={handleSendOTP}
          loading={isLoading}
          disabled={isLoading}
          variant="primary"
          size="large"
          fullWidth={true}
        />
      </View>
    </>
  );

  // ==================== خطوة 2: تأكيد الإرسال ====================
  const renderSentStep = () => {
    const sentMessage = isPhone
      ? (operationMessages.sentMessagePhone || 'تم إرسال رمز التحقق إلى هاتفك')
      : (operationMessages.sentMessage || 'تم إرسال رمز التحقق إلى إيميلك');

    return (
      <>
        <View style={styles.header}>
          <View style={styles.iconContainer}>
            <Icon
              name={isPhone ? 'phone-iphone' : 'mark-email-read'}
              size={width * 0.09}
              color={colors.primary}
            />
          </View>
          <Text style={styles.title}>{operationMessages.title}</Text>
          <Text style={styles.subtitle}>{sentMessage}</Text>
        </View>

        <View style={styles.targetContainer}>
          <Text style={styles.targetLabel}>تم الإرسال إلى:</Text>
          <Text style={styles.targetText}>{maskedTarget}</Text>
        </View>

        <View style={styles.actionsContainer}>
          <ModernButton
            title="المتابعة إلى إدخال الرمز"
            onPress={goToVerification}
            variant="primary"
            size="large"
            fullWidth={true}
          />

          {!isPhone && (
            <ModernButton
              title="فتح تطبيق الإيميل"
              onPress={openEmailApp}
              variant="secondary"
              size="large"
              fullWidth={true}
              style={{ marginTop: 12 }}
            />
          )}
        </View>

        <View style={styles.resendContainer}>
          <Text style={styles.resendLabel}>لم يصل الرمز؟</Text>
          <ResendButton onPress={handleResend} cooldownTime={60} />
        </View>

        <TouchableOpacity style={styles.changeMethodButton} onPress={() => setStep('select')}>
          <Text style={styles.changeMethodText}>تغيير طريقة التحقق</Text>
        </TouchableOpacity>

        <View style={styles.infoContainer}>
          <InfoMessage
            message={isPhone
              ? 'تأكد من أن رقم الهاتف صحيح وأن الهاتف متصل بالشبكة'
              : 'إذا لم تجد الرسالة في صندوق الوارد، تحقق من مجلد الرسائل غير المرغوب فيها (Spam)'
            }
          />
          <InfoMessage message="الرمز صالح لمدة 5 دقائق فقط" />
        </View>
      </>
    );
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar barStyle="light-content" backgroundColor={theme.colors.background} />

      <GlobalHeader
        title={operationMessages.title || 'التحقق من الهوية'}
        showBack={true}
        onBack={goBack}
      />

      <View style={styles.container}>
        <ScrollView
          contentContainerStyle={styles.scrollContainer}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          {step === 'select' ? renderSelectStep() : renderSentStep()}
        </ScrollView>
      </View>
    </SafeAreaView>
  );
};

export default OTPSentScreen;
