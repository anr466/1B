/**
 * Login Screen - شاشة تسجيل الدخول
 * مع دعم حفظ بيانات الدخول والدخول التلقائي بالبصمة
 */

import React, { useState, useEffect, useRef } from 'react';
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    KeyboardAvoidingView,
    Platform,
    SafeAreaView,
    StatusBar,
    ScrollView,
    Keyboard,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { theme } from '../theme/theme';
import { useBackHandler } from '../utils/BackHandlerUtil';
import ToastService from '../services/ToastService';
import Icon from '../components/CustomIcons';
import BiometricAuth from '../services/BiometricService';
import TempStorageService from '../services/TempStorageService';
import SecureStorageService from '../services/SecureStorageService'; // ✅ للتخزين المشفر
import ModernButton from '../components/ModernButton';
import ModernCard from '../components/ModernCard';
import UnifiedBrandLogo from '../components/UnifiedBrandLogo';
import GlobalHeader from '../components/GlobalHeader';
import ModernInput from '../components/ModernInput';

const LoginScreen = ({ onLogin, onNavigateToRegister, onNavigateToForgotPassword }) => {
    const [identifier, setIdentifier] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    // const [showPassword, setShowPassword] = useState(false); // ✅ ModernInput handles this
    const [rememberMe, setRememberMe] = useState(false);
    const [biometricChecked, setBiometricChecked] = useState(false);
    const [keyboardVisible, setKeyboardVisible] = useState(false);

    // ✅ إصلاح Race Conditions
    const isMountedRef = useRef(true);

    // منع الرجوع
    useBackHandler(() => { });

    useEffect(() => {
        isMountedRef.current = true;
        initializeScreen();

        const keyboardDidShowListener = Keyboard.addListener(
            'keyboardDidShow',
            () => { if (isMountedRef.current) {setKeyboardVisible(true);} }
        );
        const keyboardDidHideListener = Keyboard.addListener(
            'keyboardDidHide',
            () => { if (isMountedRef.current) {setKeyboardVisible(false);} }
        );

        return () => {
            isMountedRef.current = false;
            keyboardDidShowListener.remove();
            keyboardDidHideListener.remove();
        };
    }, []);

    // تهيئة الشاشة
    const initializeScreen = async () => {
        await loadSavedCredentials();
        await tryAutoBiometricLogin();
    };

    // تحميل البيانات المحفوظة
    const loadSavedCredentials = async () => {
        if (!isMountedRef.current) {return;}
        try {
            const remember = await AsyncStorage.getItem('remember_me');
            if (remember === 'true' && isMountedRef.current) {
                setRememberMe(true);
                const savedId = await AsyncStorage.getItem('saved_identifier');
                if (savedId && isMountedRef.current) {
                    setIdentifier(savedId);
                }
            }
        } catch (error) {
            console.log('خطأ في تحميل البيانات:', error);
        }
    };

    // محاولة الدخول التلقائي بالبصمة
    // ⚠️ لا نطلب البصمة إذا تم طلبها في App.js أو لا يوجد اتصال
    const tryAutoBiometricLogin = async () => {
        if (biometricChecked || !isMountedRef.current) {return;}
        if (isMountedRef.current) {
            setBiometricChecked(true);
        }

        try {
            // ✅ فحص إذا تم محاولة البصمة في App.js
            const biometricAttempted = await AsyncStorage.getItem('biometric_attempted_this_session');
            if (biometricAttempted === 'true') {
                console.log('⚠️ تخطي البصمة - تم محاولتها في App.js');
                return;
            }

            // 1. فحص البصمة متاحة
            const bioResult = await BiometricAuth.initialize();
            if (!bioResult.available) {return;}

            // 2. فحص مستخدم مسجل
            const lastUserId = await TempStorageService.getItem('lastUserId');
            if (!lastUserId) {return;}

            // 3. فحص البصمة مفعلة
            const isRegistered = await BiometricAuth.isBiometricRegistered(lastUserId);
            if (!isRegistered) {return;}

            // 4. فحص "تذكرني" مفعل
            const remember = await AsyncStorage.getItem('remember_me');
            if (remember !== 'true') {return;}

            // 5. فحص كلمة المرور محفوظة (مشفرة)
            const savedPassword = await SecureStorageService.getSavedPassword(lastUserId);
            if (!savedPassword) {return;}

            console.log('🔐 محاولة الدخول التلقائي بالبصمة من LoginScreen...');
            setLoading(true);

            // ✅ تحديث flag لمنع التكرار
            await AsyncStorage.setItem('biometric_attempted_this_session', 'true');

            // التحقق من البصمة
            const verifyResult = await BiometricAuth.verifyBiometric(lastUserId);

            if (verifyResult.success && verifyResult.username) {
                console.log('✅ نجح التحقق - تسجيل الدخول...');
                if (onLogin) {
                    await onLogin(verifyResult.username, savedPassword, true);
                }
            } else {
                console.log('❌ فشل التحقق من البصمة');
                setLoading(false);
            }
        } catch (error) {
            console.log('خطأ في الدخول التلقائي:', error);
            setLoading(false);
        }
    };

    // تسجيل الدخول العادي
    const handleLogin = async () => {
        // ✅ رسائل خطأ محددة لكل حقل
        if (!identifier.trim() && !password.trim()) {
            ToastService.showError('الرجاء إدخال البريد الإلكتروني وكلمة المرور');
            return;
        }
        if (!identifier.trim()) {
            ToastService.showError('الرجاء إدخال البريد الإلكتروني أو اسم المستخدم');
            return;
        }
        if (!password.trim()) {
            ToastService.showError('الرجاء إدخال كلمة المرور');
            return;
        }

        setLoading(true);
        try {
            // حفظ البيانات إذا "تذكرني" مفعل
            if (rememberMe) {
                await AsyncStorage.setItem('remember_me', 'true');
                await AsyncStorage.setItem('saved_identifier', identifier.trim());
            } else {
                await AsyncStorage.removeItem('remember_me');
                await AsyncStorage.removeItem('saved_identifier');
            }

            if (onLogin) {
                // تمرير rememberMe للتحكم في حفظ كلمة المرور
                await onLogin(identifier.trim(), password, false, rememberMe);
            }
        } catch (error) {
            // ✅ الخطأ يُعالج في App.js handleLogin - لا نعرض رسالة هنا لتجنب التكرار
            console.log('LoginScreen catch - error passed to App.js');
            throw error; // تمرير الخطأ لـ App.js
        } finally {
            setLoading(false);
        }
    };

    return (
        <SafeAreaView style={styles.safeArea}>
            <StatusBar barStyle="light-content" backgroundColor={theme.colors.background} />

            {/* ✅ استخدام GlobalHeader الموحد */}
            <GlobalHeader
                title="تسجيل الدخول"
                showBack={false}
                isAdminUser={false}
            />

            <KeyboardAvoidingView
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                style={styles.container}
                keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 20}
            >
                <ScrollView
                    contentContainerStyle={styles.scrollContent}
                    showsVerticalScrollIndicator={false}
                    keyboardShouldPersistTaps="handled"
                >
                    {/* الشعار - يتقلص عند ظهور الكيبورد */}
                    {!keyboardVisible && (
                        <View style={styles.logoContainer}>
                            <UnifiedBrandLogo variant="auth" />

                            {/* شعار النظام */}
                            <View style={styles.systemMottoContainer}>
                                <Text style={styles.systemMottoText}>
                                    1B is not luck.{' '}
                                    <Text style={styles.systemMottoHighlight}>It's a system</Text>
                                </Text>
                                <View style={styles.systemMottoUnderline} />
                            </View>
                        </View>
                    )}

                    <ModernCard>
                        <View style={styles.form}>
                            {/* حقل الإيميل أو اليوزر */}
                            <ModernInput
                                label="الإيميل أو اسم المستخدم"
                                placeholder="أدخل الإيميل أو اسم المستخدم"
                                value={identifier}
                                onChangeText={setIdentifier}
                                keyboardType="email-address"
                                editable={!loading}
                                icon="email"
                                autoCapitalize="none"
                            />

                            {/* حقل كلمة المرور */}
                            <ModernInput
                                label="كلمة المرور"
                                placeholder="أدخل كلمة المرور"
                                value={password}
                                onChangeText={setPassword}
                                secureTextEntry={true}
                                editable={!loading}
                                icon="lock"
                            />

                            {/* خيار تذكرني */}
                            <View style={styles.rememberRow}>
                                <TouchableOpacity
                                    style={styles.rememberOption}
                                    onPress={() => setRememberMe(!rememberMe)}
                                    activeOpacity={0.7}
                                >
                                    <View style={[styles.checkbox, rememberMe && styles.checkboxChecked]}>
                                        {rememberMe && <Text style={styles.checkmark}>✓</Text>}
                                    </View>
                                    <Text style={styles.rememberText}>تذكرني</Text>
                                </TouchableOpacity>

                                <TouchableOpacity
                                    onPress={() => onNavigateToForgotPassword?.()}
                                    disabled={loading}
                                >
                                    <Text style={styles.forgotPasswordLink}>نسيت كلمة المرور؟</Text>
                                </TouchableOpacity>
                            </View>

                            {/* زر تسجيل الدخول */}
                            <ModernButton
                                title="تسجيل الدخول"
                                onPress={handleLogin}
                                loading={loading}
                                variant="primary"
                                size="large"
                                fullWidth
                                style={styles.loginButton}
                            />

                            {/* رابط إنشاء حساب */}
                            <TouchableOpacity
                                onPress={() => onNavigateToRegister?.()}
                                style={styles.registerContainer}
                            >
                                <Text style={styles.registerLink}>
                                    ليس لديك حساب؟ <Text style={styles.registerLinkBold}>إنشاء حساب</Text>
                                </Text>
                            </TouchableOpacity>
                        </View>
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
    scrollContent: {
        flexGrow: 1,
        justifyContent: 'center',
        paddingHorizontal: theme.spacing.lg,
        paddingBottom: theme.spacing.xl,
    },
    logoContainer: {
        alignItems: 'center',
        marginBottom: theme.spacing.xl,
        marginTop: theme.spacing.lg,
    },
    systemMottoContainer: {
        alignItems: 'center',
        marginTop: theme.spacing.md,
        paddingHorizontal: theme.spacing.lg,
    },
    systemMottoText: {
        fontSize: 15,
        fontWeight: '500',
        color: theme.colors.textSecondary,
        letterSpacing: 0.5,
        textAlign: 'center',
    },
    systemMottoHighlight: {
        color: theme.colors.primary,
        fontWeight: '700',
        letterSpacing: 0.8,
    },
    systemMottoUnderline: {
        width: 80,
        height: 2,
        backgroundColor: theme.colors.primary,
        marginTop: 8,
        borderRadius: 1,
        opacity: 0.6,
    },
    // L1: العنوان الرئيسي
    title: {
        ...theme.hierarchy.primary,
        color: theme.colors.primary,
        textAlign: 'center',
        marginBottom: 8,
    },
    logo: {
        marginBottom: 16,
    },
    // L2: العنوان الفرعي
    subtitle: {
        ...theme.hierarchy.secondary,
        fontWeight: '400',
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginBottom: 24,
    },
    form: {
        paddingTop: 8,
    },
    inputGroup: {
        marginBottom: 16,
    },
    // L4: التسميات
    label: {
        ...theme.hierarchy.caption,
        fontWeight: '500',
        color: theme.colors.text,
        marginBottom: 8,
    },
    input: {
        backgroundColor: theme.colors.backgroundSecondary,
        borderWidth: 1,
        borderColor: theme.colors.border,
        borderRadius: 10,
        paddingHorizontal: 14,
        paddingVertical: 12,
        color: theme.colors.text,
        fontSize: theme.typography.fontSize.base,
    },
    passwordContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.backgroundSecondary,
        borderWidth: 1,
        borderColor: theme.colors.border,
        borderRadius: 10,
        paddingHorizontal: 14,
    },
    passwordInput: {
        flex: 1,
        paddingVertical: 12,
        color: theme.colors.text,
        fontSize: theme.typography.fontSize.base,
    },
    rememberRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 20,
    },
    rememberOption: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    checkbox: {
        width: 22,
        height: 22,
        borderRadius: 6,
        borderWidth: 2,
        borderColor: theme.colors.border,
        alignItems: 'center',
        justifyContent: 'center',
        marginRight: 8,
    },
    checkboxChecked: {
        backgroundColor: theme.colors.primary,
        borderColor: theme.colors.primary,
    },
    checkmark: {
        color: '#FFF',
        fontSize: theme.typography.fontSize.sm,
        fontWeight: 'bold',
    },
    rememberText: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.text,
    },
    forgotPasswordLink: {
        color: theme.colors.primary,
        fontSize: theme.typography.fontSize.sm,
        fontWeight: '500',
    },
    loginButton: {
        marginTop: 4,
    },
    registerContainer: {
        marginTop: 20,
        alignItems: 'center',
    },
    registerLink: {
        textAlign: 'center',
        color: theme.colors.textSecondary,
        fontSize: theme.typography.fontSize.sm,
    },
    registerLinkBold: {
        color: theme.colors.primary,
        fontWeight: 'bold',
    },
});

export default LoginScreen;
