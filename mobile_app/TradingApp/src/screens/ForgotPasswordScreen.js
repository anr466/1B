/**
 * Forgot Password Screen - شاشة نسيان كلمة المرور
 * طلب إعادة تعيين كلمة المرور
 */

import React, { useState, useRef, useEffect } from 'react';
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    KeyboardAvoidingView,
    Platform,
    SafeAreaView,
    StatusBar,
} from 'react-native';
import { theme } from '../theme/theme';
import ToastService from '../services/ToastService';
import OTPService, { OTP_OPERATION_TYPES } from '../services/OTPService';
import ModernCard from '../components/ModernCard';
import ModernButton from '../components/ModernButton';
import ModernInput from '../components/ModernInput';
import Icon from '../components/CustomIcons';
import GlobalHeader from '../components/GlobalHeader';
import UnifiedBrandLogo from '../components/UnifiedBrandLogo';
import DatabaseApiService from '../services/DatabaseApiService';

const ForgotPasswordScreen = ({ navigation, onNavigateToOTP, onBack }) => {
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [checkingEmail, setCheckingEmail] = useState(false);
    const [emailExists, setEmailExists] = useState(null);
    const checkTimeoutRef = useRef(null);

    // التحقق من وجود الإيميل مع debounce
    const checkEmailExists = async (emailToCheck) => {
        // مسح أي تحقق سابق
        if (checkTimeoutRef.current) {
            clearTimeout(checkTimeoutRef.current);
        }

        if (!emailToCheck || emailToCheck.length < 3) {
            setEmailExists(null);
            return;
        }

        if (!OTPService.validateEmail(emailToCheck)) {
            setEmailExists(null);
            return;
        }

        // انتظار 500ms قبل التحقق
        checkTimeoutRef.current = setTimeout(async () => {
            setCheckingEmail(true);
            try {
                const response = await DatabaseApiService.checkAvailability(emailToCheck, null, null);
                console.log('📧 Check email response:', response);

                // إذا كان emailAvailable = true يعني الإيميل متاح للتسجيل (غير موجود)
                // إذا كان emailAvailable = false يعني الإيميل مستخدم (موجود)
                const isAvailable = response.emailAvailable === true || response.email_available === true;
                const exists = !isAvailable; // عكس المتاح = موجود

                console.log('📧 Email exists:', exists);
                setEmailExists(exists);
            } catch (error) {
                console.error('❌ خطأ في التحقق من الإيميل:', error);
                setEmailExists(null);
            } finally {
                setCheckingEmail(false);
            }
        }, 500);
    };

    // تنظيف عند unmount
    useEffect(() => {
        return () => {
            if (checkTimeoutRef.current) {
                clearTimeout(checkTimeoutRef.current);
            }
        };
    }, []);

    const handleSendReset = async () => {
        if (!email.trim()) {
            ToastService.showInfo('يرجى إدخال بريدك الإلكتروني');
            return;
        }

        if (!OTPService.validateEmail(email)) {
            ToastService.showInfo('صيغة البريد الإلكتروني غير صحيحة');
            return;
        }

        // التحقق من وجود الإيميل
        if (emailExists === false) {
            ToastService.showError('هذا البريد الإلكتروني غير مسجل');
            return;
        }

        setLoading(true);
        try {
            // ✅ جلب طرق التحقق المتاحة (SMS/Email) من الخادم
            const methodsResult = await DatabaseApiService.getVerificationMethods(email);
            const maskedPhone = methodsResult?.masked_phone || null;
            const maskedEmail = methodsResult?.masked_email || OTPService.maskEmail(email);
            // ✅ استخراج رقم الهاتف المخفي (لعرضه فقط - لا نحتاج الرقم الحقيقي)
            const hasPhone = methodsResult?.options?.some(o => o.method === 'sms') || false;

            // ✅ الانتقال لشاشة اختيار طريقة التحقق بدلاً من إرسال OTP مباشرة
            if (onNavigateToOTP) {
                onNavigateToOTP({
                    screen: 'OTPSent',
                    params: {
                        email,
                        phoneNumber: hasPhone ? 'phone_from_backend' : null,
                        operationType: OTP_OPERATION_TYPES.RESET_PASSWORD,
                        maskedEmail: maskedEmail,
                        additionalData: {
                            maskedPhone: maskedPhone,
                            maskedEmail: maskedEmail,
                        },
                    },
                });
            }
        } catch (error) {
            console.error('[ERROR] خطأ في إرسال رمز إعادة التعيين:', error);

            let errorMessage = 'حدث خطأ في إرسال رمز إعادة التعيين';
            if (error?.response?.data?.error) {
                errorMessage = error.response.data.error;
            } else if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
                errorMessage = 'انتهى وقت الانتظار. يرجى المحاولة مرة أخرى';
            } else if (error?.code === 'ERR_NETWORK' || error?.message?.includes('Network Error')) {
                errorMessage = 'فشل الاتصال بالخادم. تحقق من اتصالك بالإنترنت';
            }

            ToastService.showError(errorMessage);
        } finally {
            setLoading(false);
        }
    };

    return (
        <SafeAreaView style={styles.container}>
            <StatusBar barStyle="light-content" backgroundColor={theme.colors.background} />

            <GlobalHeader
                title="استعادة كلمة المرور"
                showBack={true}
                onBack={onBack}
            />

            <KeyboardAvoidingView
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                style={styles.flex}
            >
                <View style={styles.content}>
                    {/* Logo */}
                    <View style={styles.logoContainer}>
                        <UnifiedBrandLogo size={80} />
                    </View>
                    {/* Info Card */}
                    <ModernCard variant="info">
                        <View style={styles.infoContent}>
                            <Icon name="info" size={24} color={theme.colors.info} />
                            <Text style={styles.infoText}>
                                أدخل بريدك الإلكتروني وسنرسل لك رمز إعادة تعيين كلمة المرور
                            </Text>
                        </View>
                    </ModernCard>

                    {/* Email Input */}
                    <View style={styles.form}>
                        <ModernInput
                            label="البريد الإلكتروني"
                            value={email}
                            onChangeText={(text) => {
                                setEmail(text);
                                checkEmailExists(text);
                            }}
                            placeholder="أدخل بريدك الإلكتروني"
                            icon="email"
                            keyboardType="email-address"
                            autoCapitalize="none"
                            editable={!loading}
                            loading={checkingEmail}
                            success={!checkingEmail && emailExists === true}
                            error={!checkingEmail && emailExists === false ? 'هذا البريد الإلكتروني غير مسجل' : null}
                        />
                    </View>

                    {/* Security Info */}
                    <ModernCard>
                        <View style={styles.securityInfo}>
                            <Icon name="shield" size={20} color={theme.colors.success} />
                            <Text style={styles.securityText}>
                                سنتحقق من هويتك عبر رمز OTP قبل السماح بتغيير كلمة المرور
                            </Text>
                        </View>
                    </ModernCard>
                </View>

                {/* Send Button */}
                <View style={styles.buttonContainer}>
                    <ModernButton
                        title={loading ? 'جاري الإرسال...' : 'إرسال رمز إعادة التعيين'}
                        onPress={handleSendReset}
                        disabled={loading || checkingEmail || emailExists === false}
                        variant="primary"
                        size="large"
                        fullWidth={true}
                    />
                </View>
            </KeyboardAvoidingView>
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    flex: {
        flex: 1,
    },
    content: {
        flex: 1,
        padding: theme.spacing.lg,
        justifyContent: 'flex-start',
    },
    logoContainer: {
        alignItems: 'center',
        marginBottom: theme.spacing.xl,
    },
    infoContent: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing.md,
    },
    infoText: {
        flex: 1,
        ...theme.hierarchy.caption,
        color: theme.colors.textSecondary,
        lineHeight: 20,
    },
    form: {
        marginVertical: theme.spacing.xl,
    },
    securityInfo: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing.md,
    },
    securityText: {
        flex: 1,
        ...theme.hierarchy.tiny,
        color: theme.colors.textSecondary,
        lineHeight: 18,
    },
    buttonContainer: {
        padding: theme.spacing.lg,
        borderTopWidth: 0,
    },
});

export default ForgotPasswordScreen;
