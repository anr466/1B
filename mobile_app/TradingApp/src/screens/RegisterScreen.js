import React, { useState, useEffect, useRef } from 'react';
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    ScrollView,
    KeyboardAvoidingView,
    Platform,
    SafeAreaView,
    StatusBar,
    Keyboard,
    ActivityIndicator,
} from 'react-native';
import { theme } from '../theme/theme';
import ModernButton from '../components/ModernButton';
import ModernCard from '../components/ModernCard';
import ModernInput from '../components/ModernInput';
import Icon from '../components/CustomIcons';
import OTPService, { OTP_OPERATION_TYPES } from '../services/OTPService';
import DeviceManager from '../services/DeviceService';
import VerificationMethodSelector, { VERIFICATION_METHODS } from '../components/VerificationMethodSelector';
import BiometricAuth from '../services/BiometricService';
import { useBackHandler, handleGoBack, handlePreventGoBack } from '../utils/BackHandlerUtil';
import ToastService from '../services/ToastService';
import UnifiedBrandLogo from '../components/UnifiedBrandLogo';
import GlobalHeader from '../components/GlobalHeader';
import { AlertService } from '../components/CustomAlert';
import DatabaseApiService from '../services/DatabaseApiService';

const REGISTRATION_DRAFT_KEY = 'registration_draft';

const RegisterScreen = ({ onRegister, onBackToLogin, onNavigateToEmailVerification }) => {
    const [formData, setFormData] = useState({
        fullName: '',
        username: '',
        email: '',
        phone: '',
        password: '',
        confirmPassword: '',
        agreeToTerms: false,
    });
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [loading, setLoading] = useState(false);
    const [deviceInfo, setDeviceInfo] = useState(null);
    const [verificationMethod, setVerificationMethod] = useState(VERIFICATION_METHODS.SMS);
    const [keyboardVisible, setKeyboardVisible] = useState(false);
    const [draftLoaded, setDraftLoaded] = useState(false);
    const [errors, setErrors] = useState({});

    // ✅ حالات التحقق الفوري من التوفر (3 حقول أساسية)
    const [availability, setAvailability] = useState({
        email: { checking: false, available: null, message: '' },
        username: { checking: false, available: null, message: '' },
        phone: { checking: false, available: null, message: '' },
    });
    const checkTimeoutRef = useRef({ email: null, username: null, phone: null });
    const requestIdRef = useRef({ email: 0, username: 0, phone: 0 }); // ✅ لمنع Race Condition

    const isMountedRef = useRef(true);

    useBackHandler(() => {
        onBackToLogin && onBackToLogin();
    });

    useEffect(() => {
        isMountedRef.current = true;

        const loadDraft = async () => {
            try {
                const AsyncStorage = require('@react-native-async-storage/async-storage').default;
                const draft = await AsyncStorage.getItem(REGISTRATION_DRAFT_KEY);
                if (draft && isMountedRef.current) {
                    const parsedDraft = JSON.parse(draft);
                    setFormData(prev => ({
                        ...prev,
                        fullName: parsedDraft.fullName || '',
                        username: parsedDraft.username || '',
                        email: parsedDraft.email || '',
                        phone: parsedDraft.phone || '',
                    }));
                    setDraftLoaded(true);
                    console.log('[INFO] تم تحميل مسودة التسجيل');
                }
            } catch (error) {
                console.warn('[WARNING] فشل تحميل مسودة التسجيل:', error);
            }
        };

        loadDraft();
        initializeDeviceInfo();

        const keyboardDidShowListener = Keyboard.addListener(
            'keyboardDidShow',
            () => isMountedRef.current && setKeyboardVisible(true)
        );
        const keyboardDidHideListener = Keyboard.addListener(
            'keyboardDidHide',
            () => isMountedRef.current && setKeyboardVisible(false)
        );

        return () => {
            isMountedRef.current = false;
            if (checkTimeoutRef.current.email) {
                clearTimeout(checkTimeoutRef.current.email);
            }
            if (checkTimeoutRef.current.username) {
                clearTimeout(checkTimeoutRef.current.username);
            }
            keyboardDidShowListener.remove();
            keyboardDidHideListener.remove();
        };
    }, []);

    useEffect(() => {
        const saveDraft = async () => {
            if (!draftLoaded) { return; }
            try {
                const AsyncStorage = require('@react-native-async-storage/async-storage').default;
                const draftData = {
                    fullName: formData.fullName,
                    username: formData.username,
                    email: formData.email,
                    phone: formData.phone,
                };
                await AsyncStorage.setItem(REGISTRATION_DRAFT_KEY, JSON.stringify(draftData));
            } catch (error) {
                console.warn('[WARNING] فشل حفظ مسودة التسجيل:', error);
            }
        };

        const timer = setTimeout(saveDraft, 1000);
        return () => clearTimeout(timer);
    }, [formData.fullName, formData.email, formData.phone, draftLoaded]);

    const initializeDeviceInfo = async () => {
        if (!isMountedRef.current) { return; }
        try {
            const info = await DeviceManager.getDeviceInfo();
            if (isMountedRef.current) {
                setDeviceInfo(info);
            }
            console.log('[SUCCESS] تم جلب معلومات الجهاز:', info);
        } catch (error) {
            console.error('[ERROR] خطأ في جلب معلومات الجهاز:', error);
        }
    };

    const getPasswordStrength = (password) => {
        if (!password) { return { level: 0, text: '', color: theme.colors.textSecondary }; }

        let score = 0;
        if (password.length >= 8) { score++; }
        if (password.length >= 12) { score++; }
        if (/[a-z]/.test(password)) { score++; }
        if (/[A-Z]/.test(password)) { score++; }
        if (/\d/.test(password)) { score++; }
        if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) { score++; }

        if (score <= 2) { return { level: 1, text: 'ضعيفة', color: theme.colors.error }; }
        if (score <= 4) { return { level: 2, text: 'متوسطة', color: theme.colors.warning }; }
        return { level: 3, text: 'قوية', color: theme.colors.success };
    };

    const passwordStrength = getPasswordStrength(formData.password);

    const validateForm = () => {
        const newErrors = {};

        if (!formData.fullName.trim()) {
            newErrors.fullName = 'الاسم الكامل مطلوب';
        } else if (formData.fullName.trim().length < 3) {
            newErrors.fullName = 'الاسم يجب أن يكون 3 أحرف على الأقل';
        }

        if (!formData.username.trim()) {
            newErrors.username = 'اسم المستخدم مطلوب';
        } else if (formData.username.trim().length < 3) {
            newErrors.username = 'اسم المستخدم يجب أن يكون 3 أحرف على الأقل';
        } else if (!/^[a-zA-Z0-9_]+$/.test(formData.username)) {
            newErrors.username = 'اسم المستخدم يجب أن يحتوي على حروف وأرقام فقط';
        }

        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!formData.email.trim()) {
            newErrors.email = 'البريد الإلكتروني مطلوب';
        } else if (!emailRegex.test(formData.email)) {
            newErrors.email = 'البريد الإلكتروني غير صحيح';
        }

        const phoneRegex = /^[0-9]{10,15}$/;
        if (!formData.phone.trim()) {
            newErrors.phone = 'رقم الهاتف مطلوب';
        } else if (!phoneRegex.test(formData.phone.replace(/[^0-9]/g, ''))) {
            newErrors.phone = 'رقم الهاتف غير صحيح';
        }

        if (!formData.password) {
            newErrors.password = 'كلمة المرور مطلوبة';
        } else if (formData.password.length < 8) {
            newErrors.password = 'كلمة المرور يجب أن تكون 8 أحرف على الأقل';
        } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password)) {
            newErrors.password = 'كلمة المرور يجب أن تحتوي على حروف كبيرة وصغيرة وأرقام';
        }

        if (!formData.confirmPassword) {
            newErrors.confirmPassword = 'تأكيد كلمة المرور مطلوب';
        } else if (formData.password !== formData.confirmPassword) {
            newErrors.confirmPassword = 'كلمات المرور غير متطابقة';
        }

        if (!formData.agreeToTerms) {
            newErrors.agreeToTerms = 'يجب الموافقة على الشروط والأحكام';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleRegister = async () => {
        if (!isMountedRef.current) { return; }
        if (!validateForm()) {
            // ✅ لا إشعارات منبثقة - الأخطاء تظهر أسفل الحقول
            return;
        }

        const isPhoneVerification = verificationMethod === VERIFICATION_METHODS.SMS;
        const targetDisplay = isPhoneVerification
            ? formData.phone.replace(/(\d{3})\d{4}(\d{3})/, '$1****$2')
            : formData.email.replace(/(.{2})(.*)(@.*)/, '$1***$3');

        AlertService.confirm(
            '📧 تأكيد إرسال رمز التحقق',
            `سيتم إرسال رمز التحقق إلى:\n\n${targetDisplay}\n\nتأكد من صحة ${isPhoneVerification ? 'رقم الهاتف' : 'البريد الإلكتروني'} قبل المتابعة.`,
            () => proceedWithRegistration(isPhoneVerification),
            () => { }
        );
    };

    const proceedWithRegistration = async (isPhoneVerification) => {
        setLoading(true);
        try {
            const username = formData.username.trim().toLowerCase();

            // ✅ التحقق تم بالفعل في النموذج - لا حاجة للتحقق مرة أخرى
            // ✅ التحقق من توفر البيانات الثلاثة
            if (availability.email.available !== true ||
                availability.username.available !== true ||
                availability.phone.available !== true) {
                setLoading(false);
                // ✅ لا إشعارات منبثقة - الرسائل تظهر أسفل الحقول
                return;
            }

            if (deviceInfo) {
                try {
                    const isRegistered = await DeviceManager.isDeviceRegistered();
                    if (!isRegistered) {
                        const deviceRegistrationResult = await DeviceManager.registerDevice();
                        if (!deviceRegistrationResult.success) {
                            console.warn('[WARNING] فشل في تسجيل الجهاز:', deviceRegistrationResult.message);
                        }
                    }
                } catch (deviceError) {
                    console.warn('[WARNING] خطأ في تسجيل الجهاز:', deviceError);
                }
            }

            // ✅ مسح المسودة قبل الانتقال
            try {
                const AsyncStorage = require('@react-native-async-storage/async-storage').default;
                await AsyncStorage.removeItem(REGISTRATION_DRAFT_KEY);
                console.log('[INFO] تم مسح مسودة التسجيل');
            } catch (clearError) {
                console.warn('[WARNING] فشل مسح مسودة التسجيل:', clearError);
            }

            // ✅ الانتقال لشاشة اختيار طريقة التحقق (OTPSentScreen) بدلاً من إرسال OTP مباشرة
            if (onNavigateToEmailVerification) {
                onNavigateToEmailVerification({
                    screen: 'OTPSent',
                    params: {
                        email: formData.email,
                        phoneNumber: formData.phone,
                        isPhone: isPhoneVerification,
                        operationType: OTP_OPERATION_TYPES.REGISTER,
                        registrationData: {
                            fullName: formData.fullName,
                            username: username,
                            email: formData.email,
                            phone: formData.phone,
                            password: formData.password,
                            verificationMethod: verificationMethod,
                        },
                        maskedEmail: OTPService.maskEmail(formData.email),
                    },
                });
            } else {
                setLoading(false);
                console.error('[ERROR] خطأ في التنقل');
            }
        } catch (error) {
            console.error('خطأ في التسجيل:', error);

            let errorMessage = 'حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.';

            if (error?.response?.data?.error) {
                errorMessage = error.response.data.error;
            } else if (error?.response?.status === 400) {
                errorMessage = 'يرجى التحقق من البيانات المدخلة';
            } else if (error?.response?.status === 409) {
                errorMessage = 'البريد الإلكتروني مسجل بالفعل';
            } else if (error?.code === 'ERR_NETWORK') {
                errorMessage = 'لا يوجد اتصال بالإنترنت';
            } else if (error?.message) {
                errorMessage = error.message;
            }

            // ✅ عرض الخطأ أسفل زر التسجيل
            setErrors(prev => ({ ...prev, submit: errorMessage }));
        } finally {
            setLoading(false);
        }
    };

    // ✅ التحقق الفوري من توفر البريد الإلكتروني (مع حماية Race Condition)
    const checkEmailAvailability = async (email) => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!email || !emailRegex.test(email)) {
            setAvailability(prev => ({
                ...prev,
                email: { checking: false, available: null, message: '' },
            }));
            return;
        }

        // ✅ زيادة request ID لمنع Race Condition
        const currentRequestId = ++requestIdRef.current.email;

        setAvailability(prev => ({
            ...prev,
            email: { checking: true, available: null, message: 'جاري التحقق...' },
        }));

        try {
            const result = await DatabaseApiService.checkAvailability(email, null);
            // ✅ تجاهل النتيجة إذا كان هناك طلب أحدث
            if (isMountedRef.current && currentRequestId === requestIdRef.current.email) {
                const isAvailable = result.emailAvailable ?? result.email_available;
                setAvailability(prev => ({
                    ...prev,
                    email: {
                        checking: false,
                        available: isAvailable,
                        message: isAvailable ? '✅ البريد الإلكتروني متاح' : '❌ البريد مسجل مسبقاً',
                    },
                }));
            }
        } catch (error) {
            console.error('خطأ في التحقق من البريد:', error);
            // ✅ تجاهل الخطأ إذا كان هناك طلب أحدث
            if (isMountedRef.current && currentRequestId === requestIdRef.current.email) {
                let errorMsg = '⚠️ فشل التحقق - تحقق من الاتصال';
                if (error?.response?.status === 429) {
                    errorMsg = '⏱️ الرجاء الانتظار قبل المحاولة مرة أخرى';
                } else if (error?.code === 'ERR_NETWORK') {
                    errorMsg = '🔌 لا يوجد اتصال بالإنترنت';
                }
                setAvailability(prev => ({
                    ...prev,
                    email: { checking: false, available: null, message: errorMsg },
                }));
            }
        }
    };

    // ✅ التحقق الفوري من توفر اسم المستخدم (مع حماية Race Condition)
    const checkUsernameAvailability = async (username) => {
        if (!username || username.length < 3 || !/^[a-zA-Z0-9_]+$/.test(username)) {
            setAvailability(prev => ({
                ...prev,
                username: { checking: false, available: null, message: '' },
            }));
            return;
        }

        // ✅ زيادة request ID لمنع Race Condition
        const currentRequestId = ++requestIdRef.current.username;

        setAvailability(prev => ({
            ...prev,
            username: { checking: true, available: null, message: 'جاري التحقق...' },
        }));

        try {
            const result = await DatabaseApiService.checkAvailability(null, username);
            // ✅ تجاهل النتيجة إذا كان هناك طلب أحدث
            if (isMountedRef.current && currentRequestId === requestIdRef.current.username) {
                const isAvailable = result.usernameAvailable ?? result.username_available;
                setAvailability(prev => ({
                    ...prev,
                    username: {
                        checking: false,
                        available: isAvailable,
                        message: isAvailable ? '✅ اسم المستخدم متاح' : '❌ اسم المستخدم محجوز',
                    },
                }));
            }
        } catch (error) {
            console.error('خطأ في التحقق من اسم المستخدم:', error);
            // ✅ تجاهل الخطأ إذا كان هناك طلب أحدث
            if (isMountedRef.current && currentRequestId === requestIdRef.current.username) {
                let errorMsg = '⚠️ فشل التحقق - تحقق من الاتصال';
                if (error?.response?.status === 429) {
                    errorMsg = '⏱️ الرجاء الانتظار قبل المحاولة مرة أخرى';
                } else if (error?.code === 'ERR_NETWORK') {
                    errorMsg = '🔌 لا يوجد اتصال بالإنترنت';
                }
                setAvailability(prev => ({
                    ...prev,
                    username: { checking: false, available: null, message: errorMsg },
                }));
            }
        }
    };

    // ✅ التحقق الفوري من توفر رقم الجوال (مع حماية Race Condition)
    const checkPhoneAvailability = async (phone) => {
        const phoneRegex = /^[0-9]{10,15}$/;
        const cleanPhone = phone.replace(/[^0-9]/g, '');

        if (!cleanPhone || !phoneRegex.test(cleanPhone)) {
            setAvailability(prev => ({
                ...prev,
                phone: { checking: false, available: null, message: '' },
            }));
            return;
        }

        // ✅ زيادة request ID لمنع Race Condition
        const currentRequestId = ++requestIdRef.current.phone;

        setAvailability(prev => ({
            ...prev,
            phone: { checking: true, available: null, message: 'جاري التحقق...' },
        }));

        try {
            const result = await DatabaseApiService.checkAvailability(null, null, cleanPhone);
            // ✅ تجاهل النتيجة إذا كان هناك طلب أحدث
            if (isMountedRef.current && currentRequestId === requestIdRef.current.phone) {
                const isAvailable = result.phoneAvailable ?? result.phone_available;
                setAvailability(prev => ({
                    ...prev,
                    phone: {
                        checking: false,
                        available: isAvailable,
                        message: isAvailable ? '✅ رقم الجوال متاح' : '❌ رقم الجوال مسجل مسبقاً',
                    },
                }));
            }
        } catch (error) {
            console.error('خطأ في التحقق من رقم الجوال:', error);
            // ✅ تجاهل الخطأ إذا كان هناك طلب أحدث
            if (isMountedRef.current && currentRequestId === requestIdRef.current.phone) {
                let errorMsg = '⚠️ فشل التحقق - تحقق من الاتصال';
                if (error?.response?.status === 429) {
                    errorMsg = '⏱️ الرجاء الانتظار قبل المحاولة مرة أخرى';
                } else if (error?.code === 'ERR_NETWORK') {
                    errorMsg = '🔌 لا يوجد اتصال بالإنترنت';
                }
                setAvailability(prev => ({
                    ...prev,
                    phone: { checking: false, available: null, message: errorMsg },
                }));
            }
        }
    };

    const updateFormData = (field, value) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: null }));
        }

        // ✅ التحقق الفوري مع تأخير (debounce)
        if (field === 'email') {
            // ✅ تحويل لـ lowercase تلقائياً
            const normalizedEmail = value.toLowerCase();
            setFormData(prev => ({ ...prev, email: normalizedEmail }));

            if (checkTimeoutRef.current.email) {
                clearTimeout(checkTimeoutRef.current.email);
            }
            checkTimeoutRef.current.email = setTimeout(() => {
                checkEmailAvailability(normalizedEmail);
            }, 800);
            return; // ✅ منع التحديث المزدوج
        }

        if (field === 'username') {
            // ✅ تحويل لـ lowercase تلقائياً
            const normalizedUsername = value.toLowerCase().replace(/[^a-z0-9_]/g, '');
            setFormData(prev => ({ ...prev, username: normalizedUsername }));

            if (checkTimeoutRef.current.username) {
                clearTimeout(checkTimeoutRef.current.username);
            }
            checkTimeoutRef.current.username = setTimeout(() => {
                checkUsernameAvailability(normalizedUsername);
            }, 800);
            return; // ✅ منع التحديث المزدوج
        }

        if (field === 'phone') {
            // ✅ تنظيف رقم الجوال من الرموز غير الأرقام
            if (checkTimeoutRef.current.phone) {
                clearTimeout(checkTimeoutRef.current.phone);
            }
            checkTimeoutRef.current.phone = setTimeout(() => {
                checkPhoneAvailability(value);
            }, 800);
        }
    };

    // ✅ التحقق من أن جميع البيانات صالحة ومتاحة
    const isFormValid = () => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        const phoneRegex = /^[0-9]{10,15}$/;

        return (
            formData.fullName.trim().length >= 3 &&
            formData.username.trim().length >= 3 &&
            /^[a-zA-Z0-9_]+$/.test(formData.username) &&
            emailRegex.test(formData.email) &&
            phoneRegex.test(formData.phone.replace(/[^0-9]/g, '')) &&
            formData.password.length >= 8 &&
            /(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(formData.password) &&
            formData.password === formData.confirmPassword &&
            formData.agreeToTerms &&
            availability.email.available === true &&
            availability.username.available === true &&
            availability.phone.available === true
        );
    };

    return (
        <SafeAreaView style={styles.safeArea}>
            <StatusBar barStyle="light-content" backgroundColor={theme.colors.background} />

            <GlobalHeader
                title="إنشاء حساب جديد"
                showBack={true}
                onBack={onBackToLogin}
                isAdminUser={false}
            />

            <KeyboardAvoidingView
                style={styles.container}
                behavior={Platform.OS === 'ios' ? 'padding' : undefined}
                enabled={Platform.OS === 'ios'}
            >
                <ScrollView
                    style={styles.scrollView}
                    contentContainerStyle={styles.scrollContent}
                    showsVerticalScrollIndicator={false}
                    keyboardShouldPersistTaps="handled"
                    nestedScrollEnabled={true}
                    removeClippedSubviews={false}
                >
                    {!keyboardVisible && (
                        <View style={styles.logoContainer} />
                    )}

                    <ModernCard style={styles.formCard}>
                        {/* الاسم الكامل */}
                        <ModernInput
                            label="الاسم الكامل"
                            value={formData.fullName}
                            onChangeText={(value) => updateFormData('fullName', value)}
                            placeholder="أحمد محمد"
                            icon="person"
                            error={errors.fullName}
                        />

                        {/* اسم المستخدم */}
                        <ModernInput
                            label="اسم المستخدم"
                            value={formData.username}
                            onChangeText={(value) => updateFormData('username', value.toLowerCase())}
                            placeholder="ahmed_123"
                            icon="at-sign"
                            autoCapitalize="none"
                            error={errors.username || (availability.username.message && !availability.username.available ? availability.username.message : null)}
                            success={availability.username.available === true}
                            successText={availability.username.available === true ? availability.username.message : null}
                            loading={availability.username.checking}
                        />

                        {/* البريد الإلكتروني */}
                        <ModernInput
                            label="البريد الإلكتروني"
                            value={formData.email}
                            onChangeText={(value) => updateFormData('email', value)}
                            placeholder="example@email.com"
                            icon="email"
                            keyboardType="email-address"
                            autoCapitalize="none"
                            error={errors.email || (availability.email.message && !availability.email.available ? availability.email.message : null)}
                            success={availability.email.available === true}
                            successText={availability.email.available === true ? availability.email.message : null}
                            loading={availability.email.checking}
                        />

                        {/* رقم الهاتف */}
                        <ModernInput
                            label="رقم الهاتف"
                            value={formData.phone}
                            onChangeText={(value) => updateFormData('phone', value)}
                            placeholder="05xxxxxxxx"
                            icon="phone"
                            keyboardType="phone-pad"
                            error={errors.phone || (availability.phone.message && !availability.phone.available ? availability.phone.message : null)}
                            success={availability.phone.available === true}
                            successText={availability.phone.available === true ? availability.phone.message : null}
                            loading={availability.phone.checking}
                        />

                        {/* كلمة المرور */}
                        <ModernInput
                            label="كلمة المرور"
                            value={formData.password}
                            onChangeText={(value) => updateFormData('password', value)}
                            placeholder="أدخل كلمة المرور"
                            icon="lock"
                            secureTextEntry={true}
                            error={errors.password}
                            helperText={passwordStrength.text ? `قوة كلمة المرور: ${passwordStrength.text}` : null}
                        />

                        {/* تأكيد كلمة المرور */}
                        <ModernInput
                            label="تأكيد كلمة المرور"
                            value={formData.confirmPassword}
                            onChangeText={(value) => updateFormData('confirmPassword', value)}
                            placeholder="أعد إدخال كلمة المرور"
                            icon="lock"
                            secureTextEntry={true}
                            error={errors.confirmPassword}
                        />

                        {/* اختيار طريقة التحقق */}
                        <VerificationMethodSelector
                            selectedMethod={verificationMethod}
                            onSelect={setVerificationMethod}
                        />

                        {/* الشروط والأحكام */}
                        <TouchableOpacity
                            style={styles.termsRow}
                            onPress={() => updateFormData('agreeToTerms', !formData.agreeToTerms)}
                            activeOpacity={0.7}
                        >
                            <View style={[styles.checkbox, formData.agreeToTerms && styles.checkboxChecked]}>
                                {formData.agreeToTerms && <Text style={styles.checkmark}>✓</Text>}
                            </View>
                            <Text style={styles.termsText}>
                                أوافق على <Text style={styles.linkText}>الشروط والأحكام</Text> و <Text style={styles.linkText}>سياسة الخصوصية</Text>
                            </Text>
                        </TouchableOpacity>
                        {errors.agreeToTerms && <Text style={styles.errorText}>{errors.agreeToTerms}</Text>}

                        {/* زر التسجيل */}
                        <ModernButton
                            title="إنشاء حساب جديد"
                            onPress={handleRegister}
                            loading={loading}
                            variant="primary"
                            size="large"
                            fullWidth
                            style={styles.registerButton}
                        />

                        {errors.submit && <Text style={styles.submitErrorText}>{errors.submit}</Text>}

                        {/* رابط تسجيل الدخول */}
                        <TouchableOpacity
                            onPress={onBackToLogin}
                            style={styles.loginLinkContainer}
                        >
                            <Text style={styles.loginLink}>
                                لديك حساب بالفعل؟ <Text style={styles.loginLinkBold}>تسجيل الدخول</Text>
                            </Text>
                        </TouchableOpacity>
                    </ModernCard>
                </ScrollView>
            </KeyboardAvoidingView>
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    safeArea: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    scrollView: {
        flex: 1,
    },
    scrollContent: {
        flexGrow: 1,
        padding: 16,
    },
    logoContainer: {
        alignItems: 'center',
        marginTop: theme.spacing.md,
        marginBottom: theme.spacing.lg,
    },
    formCard: {
        marginBottom: 16,
    },
    inputGroup: {
        marginBottom: 16,
    },
    label: {
        ...theme.hierarchy.caption,
        fontWeight: '500',
        color: theme.colors.text,
        marginBottom: 4,
        textAlign: 'right',
    },
    helperText: {
        fontSize: theme.typography.fontSize.xs,
        color: theme.colors.textSecondary,
        marginBottom: theme.spacing.sm,
        textAlign: 'right',
        fontStyle: 'italic',
    },
    inputContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.surface,
        borderRadius: theme.borderRadius.lg,
        borderWidth: 1,
        borderColor: theme.colors.border,
        paddingHorizontal: theme.spacing.md,
        height: 50,
    },
    inputError: {
        borderColor: theme.colors.error,
    },
    inputSuccess: {
        borderColor: theme.colors.success,
    },
    inputIcon: {
        marginLeft: 8,
    },
    statusIcon: {
        marginRight: 8,
    },
    availabilityText: {
        fontSize: theme.typography.fontSize.xs,
        marginTop: 4,
        textAlign: 'right',
    },
    registerButtonDisabled: {
        opacity: 0.6,
    },
    eyeIcon: {
        padding: 4,
    },
    errorText: {
        fontSize: theme.typography.fontSize.xs,
        color: theme.colors.error,
        marginTop: 4,
        textAlign: 'right',
    },
    passwordStrengthContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 8,
        gap: 8,
    },
    strengthBars: {
        flexDirection: 'row',
        flex: 1,
        gap: 4,
    },
    strengthBar: {
        flex: 1,
        height: 4,
        borderRadius: 2,
    },
    strengthText: {
        fontSize: theme.typography.fontSize.xs,
        fontWeight: '600',
        minWidth: 50,
        textAlign: 'left',
    },
    checkboxContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 16,
    },
    checkbox: {
        width: 20,
        height: 20,
        borderRadius: 4,
        borderWidth: 2,
        borderColor: theme.colors.border,
        marginLeft: theme.spacing.sm,
        alignItems: 'center',
        justifyContent: 'center',
    },
    checkboxChecked: {
        backgroundColor: theme.colors.primary,
        borderColor: theme.colors.primary,
    },
    checkboxText: {
        flex: 1,
        fontSize: theme.typography.fontSize.xs,
        color: theme.colors.textSecondary,
        textAlign: 'right',
        lineHeight: 20,
    },
    linkText: {
        color: theme.colors.primary,
        textDecorationLine: 'underline',
    },
    registerButton: {
        marginTop: 12,
    },
    loginSection: {
        alignItems: 'center',
        paddingVertical: 16,
    },
    loginText: {
        fontSize: theme.typography.fontSize.base,
        color: theme.colors.textSecondary,
        textAlign: 'center',
    },
    loginLink: {
        color: theme.colors.primary,
        fontWeight: '600',
        textDecorationLine: 'underline',
    },
});

export default RegisterScreen;
