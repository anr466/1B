/**
 * شاشة التحقق الموحدة للعمليات الحساسة
 * =====================================
 *
 * تُستخدم للتحقق من هوية المستخدم قبل تنفيذ العمليات الحساسة:
 * - تغيير كلمة المرور
 * - تغيير الإيميل
 * - تغيير الجوال
 * - تفعيل/إلغاء البصمة
 * - تغيير/حذف مفاتيح Binance
 */

import React, { useState, useEffect, useRef } from 'react';
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    SafeAreaView,
    StatusBar,
    KeyboardAvoidingView,
    Platform,
    ActivityIndicator,
    Alert,
} from 'react-native';
import { theme } from '../theme/theme';
import ModernCard from '../components/ModernCard';
import ModernButton from '../components/ModernButton';
import GlobalHeader from '../components/GlobalHeader';
import ToastService from '../services/ToastService';
import { useBackHandler } from '../utils/BackHandlerUtil';
import SecureActionsService, {
    SECURE_ACTIONS,
    VERIFICATION_METHODS,
    ACTION_NAMES,
} from '../services/SecureActionsService';
import OTPInput from './OTP/components/OTPInput';

const VerifyActionScreen = ({
    route,
    navigation,
    // أو يمكن تمرير البيانات مباشرة
    action: propAction,
    newValue: propNewValue,
    oldPassword: propOldPassword,
    onSuccess,
    onCancel,
}) => {
    // البيانات من route أو props
    const action = route?.params?.action || propAction;
    const newValue = route?.params?.newValue || propNewValue;
    const oldPassword = route?.params?.oldPassword || propOldPassword;
    const onSuccessCallback = route?.params?.onSuccess || onSuccess;
    const onCancelCallback = route?.params?.onCancel || onCancel;

    // الحالات
    const [step, setStep] = useState('select'); // select | verify
    const [loading, setLoading] = useState(false);
    const [verificationOptions, setVerificationOptions] = useState([]);
    const [selectedMethod, setSelectedMethod] = useState(null);
    const [maskedTarget, setMaskedTarget] = useState('');
    const [otp, setOtp] = useState(['', '', '', '', '', '']);
    const [countdown, setCountdown] = useState(0);
    const [canResend, setCanResend] = useState(false);

    const otpRef = useRef(null);

    // ✅ معالجة زر الرجوع
    useBackHandler(() => {
        handleCancel();
        return true; // منع الرجوع الافتراضي
    });

    // تحميل خيارات التحقق
    useEffect(() => {
        if (action) {
            loadVerificationOptions();
        }
    }, [action]);

    // العد التنازلي
    useEffect(() => {
        let timer;
        if (countdown > 0) {
            timer = setInterval(() => {
                setCountdown(prev => {
                    if (prev <= 1) {
                        setCanResend(true);
                        return 0;
                    }
                    return prev - 1;
                });
            }, 1000);
        }
        return () => clearInterval(timer);
    }, [countdown]);

    const loadVerificationOptions = async () => {
        setLoading(true);
        try {
            const result = await SecureActionsService.getVerificationOptions(action);

            if (result.success) {
                setVerificationOptions(result.options);

                // ✅ اختيار SMS تلقائياً كافتراضي، أو أول خيار متاح
                const smsOption = result.options.find(o => o.method === 'sms');
                if (smsOption) {
                    setSelectedMethod('sms');
                } else if (result.options.length > 0) {
                    setSelectedMethod(result.options[0].method);
                }
            } else {
                const errorMsg = result.error || 'فشل في تحميل خيارات التحقق';
                ToastService.showError(errorMsg);
                handleCancel();
            }
        } catch (error) {
            const errorMsg = error?.response?.data?.error || error?.message || 'خطأ في الاتصال';
            ToastService.showError(errorMsg);
            handleCancel();
        } finally {
            setLoading(false);
        }
    };

    const handleSelectMethod = (method) => {
        setSelectedMethod(method);
    };

    const handleRequestVerification = async () => {
        if (!selectedMethod) {
            ToastService.showWarning('اختر طريقة التحقق');
            return;
        }

        setLoading(true);
        try {
            const result = await SecureActionsService.requestVerification(
                action,
                selectedMethod,
                newValue,
                oldPassword
            );

            if (result.success) {
                setMaskedTarget(result.maskedTarget);
                setStep('verify');
                setCountdown(60);
                setCanResend(false);
                ToastService.showSuccess(result.message);
            } else {
                ToastService.showError(result.error);
            }
        } catch (error) {
            const errorMsg = error?.response?.data?.error || error?.message || 'خطأ في إرسال رمز التحقق';
            ToastService.showError(errorMsg);
        } finally {
            setLoading(false);
        }
    };

    const handleVerify = async (otpCode = null) => {
        const code = otpCode || otp.join('');

        if (code.length !== 6) {
            ToastService.showWarning('أدخل رمز التحقق كاملاً');
            return;
        }

        setLoading(true);
        try {
            const result = await SecureActionsService.verifyAndExecute(action, code, newValue);

            if (result.success) {
                ToastService.showSuccess(result.message);

                if (onSuccessCallback) {
                    onSuccessCallback(result);
                } else if (navigation?.goBack) {
                    navigation.goBack();
                }
            } else {
                ToastService.showError(result.error);
                // مسح OTP عند الخطأ مع اهتزاز
                otpRef.current?.shake();
                otpRef.current?.clear();
            }
        } catch (error) {
            const errorMsg = error?.response?.data?.error || error?.message || 'خطأ في التحقق';
            ToastService.showError(errorMsg);
        } finally {
            setLoading(false);
        }
    };

    const handleResend = async () => {
        if (!canResend) { return; }

        setLoading(true);
        try {
            const result = await SecureActionsService.requestVerification(
                action,
                selectedMethod,
                newValue,
                oldPassword
            );

            if (result.success) {
                setCountdown(60);
                setCanResend(false);
                setOtp(['', '', '', '', '', '']);
                ToastService.showSuccess('تم إعادة إرسال الرمز');
            } else {
                ToastService.showError(result.error);
            }
        } catch (error) {
            const errorMsg = error?.response?.data?.error || error?.message || 'خطأ في إعادة الإرسال';
            ToastService.showError(errorMsg);
        } finally {
            setLoading(false);
        }
    };

    const handleCancel = () => {
        // ✅ إذا كان المستخدم في مرحلة إدخال OTP وأدخل بعض الأرقام، تأكد من الإلغاء
        const hasPartialOtp = step === 'verify' && otp.some(d => d !== '');

        if (hasPartialOtp) {
            Alert.alert(
                'إلغاء العملية',
                'هل أنت متأكد من إلغاء عملية التحقق؟',
                [
                    { text: 'العودة', style: 'cancel' },
                    {
                        text: 'إلغاء',
                        style: 'destructive',
                        onPress: () => {
                            SecureActionsService.cancelVerification(action);
                            if (onCancelCallback) {
                                onCancelCallback();
                            } else if (navigation?.goBack) {
                                navigation.goBack();
                            }
                        },
                    },
                ]
            );
        } else {
            SecureActionsService.cancelVerification(action);
            if (onCancelCallback) {
                onCancelCallback();
            } else if (navigation?.goBack) {
                navigation.goBack();
            }
        }
    };

    const formatTime = (seconds) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const getActionName = () => {
        return ACTION_NAMES[action] || 'عملية';
    };

    // ==================== شاشة اختيار طريقة التحقق ====================
    const renderSelectStep = () => (
        <View style={styles.stepContainer}>
            <ModernCard>
                <View style={styles.cardContent}>
                    {/* العنوان */}
                    <Text style={styles.title}>التحقق من الهوية</Text>
                    <Text style={styles.subtitle}>
                        لإتمام عملية "{getActionName()}"، اختر طريقة التحقق
                    </Text>

                    {/* خيارات التحقق */}
                    <View style={styles.optionsContainer}>
                        {verificationOptions.map((option, index) => (
                            <TouchableOpacity
                                key={option.method}
                                style={[
                                    styles.optionCard,
                                    selectedMethod === option.method && styles.optionCardSelected,
                                ]}
                                onPress={() => handleSelectMethod(option.method)}
                                activeOpacity={0.7}
                            >
                                <View style={styles.optionIcon}>
                                    <Text style={styles.optionIconText}>
                                        {option.method === 'email' ? '📧' : '📱'}
                                    </Text>
                                </View>
                                <View style={styles.optionInfo}>
                                    <Text style={styles.optionLabel}>{option.label}</Text>
                                    <Text style={styles.optionTarget}>{option.masked_target}</Text>
                                </View>
                                <View style={[
                                    styles.optionRadio,
                                    selectedMethod === option.method && styles.optionRadioSelected,
                                ]}>
                                    {selectedMethod === option.method && (
                                        <View style={styles.optionRadioInner} />
                                    )}
                                </View>
                            </TouchableOpacity>
                        ))}
                    </View>

                    {/* زر المتابعة */}
                    <ModernButton
                        title="إرسال رمز التحقق"
                        onPress={handleRequestVerification}
                        loading={loading}
                        disabled={!selectedMethod || loading}
                        style={styles.continueButton}
                    />

                    {/* زر الإلغاء */}
                    <TouchableOpacity
                        style={styles.cancelButton}
                        onPress={handleCancel}
                    >
                        <Text style={styles.cancelButtonText}>إلغاء</Text>
                    </TouchableOpacity>
                </View>
            </ModernCard>
        </View>
    );

    // ==================== شاشة إدخال OTP ====================
    const renderVerifyStep = () => (
        <View style={styles.stepContainer}>
            <ModernCard>
                <View style={styles.cardContent}>
                    {/* العنوان */}
                    <Text style={styles.title}>أدخل رمز التحقق</Text>
                    <Text style={styles.subtitle}>
                        تم إرسال رمز مكون من 6 أرقام إلى{'\n'}
                        <Text style={styles.targetHighlight}>{maskedTarget}</Text>
                    </Text>

                    {/* حقول OTP */}
                    <OTPInput
                        ref={otpRef}
                        length={6}
                        value={otp}
                        onChange={setOtp}
                        onComplete={handleVerify}
                        disabled={loading}
                        autoFocus={true}
                        style={{ marginBottom: 24 }}
                    />

                    {/* العد التنازلي */}
                    <View style={styles.countdownContainer}>
                        {countdown > 0 ? (
                            <Text style={styles.countdownText}>
                                إعادة الإرسال بعد {formatTime(countdown)}
                            </Text>
                        ) : (
                            <TouchableOpacity onPress={handleResend} disabled={loading}>
                                <Text style={styles.resendText}>إعادة إرسال الرمز</Text>
                            </TouchableOpacity>
                        )}
                    </View>

                    {/* زر التحقق */}
                    <ModernButton
                        title="تأكيد"
                        onPress={() => handleVerify()}
                        loading={loading}
                        disabled={otp.some(d => !d) || loading}
                        style={styles.verifyButton}
                    />

                    {/* زر الرجوع */}
                    <TouchableOpacity
                        style={styles.backButton}
                        onPress={() => {
                            setStep('select');
                            setOtp(['', '', '', '', '', '']);
                        }}
                    >
                        <Text style={styles.backButtonText}>تغيير طريقة التحقق</Text>
                    </TouchableOpacity>
                </View>
            </ModernCard>
        </View>
    );

    // ==================== الشاشة الرئيسية ====================
    return (
        <SafeAreaView style={styles.container}>
            <StatusBar barStyle="light-content" backgroundColor={theme.colors.background} />

            <GlobalHeader
                title={getActionName()}
                showBack={true}
                onBack={handleCancel}
            />

            <KeyboardAvoidingView
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                style={styles.content}
            >
                {loading && step === 'select' && verificationOptions.length === 0 ? (
                    <View style={styles.loadingContainer}>
                        <ActivityIndicator size="large" color={theme.colors.primary} />
                        <Text style={styles.loadingText}>جاري التحميل...</Text>
                    </View>
                ) : (
                    step === 'select' ? renderSelectStep() : renderVerifyStep()
                )}
            </KeyboardAvoidingView>
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    content: {
        flex: 1,
        justifyContent: 'center',
        paddingHorizontal: 20,
    },
    loadingContainer: {
        alignItems: 'center',
        justifyContent: 'center',
    },
    loadingText: {
        color: theme.colors.textSecondary,
        marginTop: 12,
        fontSize: 14,
    },
    stepContainer: {
        width: '100%',
    },
    cardContent: {
        padding: 20,
    },
    title: {
        fontSize: 22,
        fontWeight: 'bold',
        color: theme.colors.text,
        textAlign: 'center',
        marginBottom: 8,
    },
    subtitle: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginBottom: 24,
        lineHeight: 22,
    },
    targetHighlight: {
        color: theme.colors.primary,
        fontWeight: '600',
    },
    optionsContainer: {
        marginBottom: 24,
    },
    optionCard: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
        borderWidth: 2,
        borderColor: 'transparent',
    },
    optionCardSelected: {
        borderColor: theme.colors.primary,
        backgroundColor: theme.colors.primary + '10',
    },
    optionIcon: {
        width: 44,
        height: 44,
        borderRadius: 22,
        backgroundColor: theme.colors.background,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 12,
    },
    optionIconText: {
        fontSize: 20,
    },
    optionInfo: {
        flex: 1,
    },
    optionLabel: {
        fontSize: 15,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 2,
    },
    optionTarget: {
        fontSize: 13,
        color: theme.colors.textSecondary,
    },
    optionRadio: {
        width: 22,
        height: 22,
        borderRadius: 11,
        borderWidth: 2,
        borderColor: theme.colors.border,
        alignItems: 'center',
        justifyContent: 'center',
    },
    optionRadioSelected: {
        borderColor: theme.colors.primary,
    },
    optionRadioInner: {
        width: 12,
        height: 12,
        borderRadius: 6,
        backgroundColor: theme.colors.primary,
    },
    continueButton: {
        marginBottom: 12,
    },
    cancelButton: {
        alignItems: 'center',
        padding: 12,
    },
    cancelButtonText: {
        color: theme.colors.textSecondary,
        fontSize: 14,
    },
    countdownContainer: {
        alignItems: 'center',
        marginBottom: 24,
    },
    countdownText: {
        color: theme.colors.textSecondary,
        fontSize: 14,
    },
    resendText: {
        color: theme.colors.primary,
        fontSize: 14,
        fontWeight: '600',
    },
    verifyButton: {
        marginBottom: 12,
    },
    backButton: {
        alignItems: 'center',
        padding: 12,
    },
    backButtonText: {
        color: theme.colors.textSecondary,
        fontSize: 14,
    },
});

export default VerifyActionScreen;
