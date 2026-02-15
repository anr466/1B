/**
 * New Password Screen - شاشة إدخال كلمة المرور الجديدة
 * بعد التحقق من OTP لاستعادة كلمة المرور
 */

import React, { useState } from 'react';
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    ActivityIndicator,
    KeyboardAvoidingView,
    Platform,
    SafeAreaView,
    StatusBar,
} from 'react-native';
import { theme } from '../theme/theme';
import ToastService from '../services/ToastService';
import DatabaseApiService from '../services/DatabaseApiService';
import ModernCard from '../components/ModernCard';
import ModernButton from '../components/ModernButton';
import ModernInput from '../components/ModernInput';
import Icon from '../components/CustomIcons';
import GlobalHeader from '../components/GlobalHeader';
import UnifiedBrandLogo from '../components/UnifiedBrandLogo';

const NewPasswordScreen = ({ navigation, route }) => {
    const { email, resetToken, verified } = route?.params || {};
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(false);

    const validatePassword = () => {
        if (!newPassword || !confirmPassword) {
            ToastService.showError('يرجى إدخال كلمة المرور وتأكيدها');
            return false;
        }

        if (newPassword.length < 8) {
            ToastService.showError('كلمة المرور يجب أن تكون 8 أحرف على الأقل');
            return false;
        }

        if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(newPassword)) {
            ToastService.showError('كلمة المرور يجب أن تحتوي على حروف كبيرة وصغيرة وأرقام');
            return false;
        }

        if (newPassword !== confirmPassword) {
            ToastService.showError('كلمة المرور وتأكيدها غير متطابقين');
            return false;
        }

        return true;
    };

    const handleResetPassword = async () => {
        if (!validatePassword()) {
            return;
        }

        if (!resetToken) {
            ToastService.showError('بيانات غير صحيحة. يرجى المحاولة مرة أخرى');
            return;
        }

        setLoading(true);
        try {
            // ✅ استدعاء API لإعادة تعيين كلمة المرور باستخدام Reset Token
            const response = await DatabaseApiService.resetPasswordWithToken(
                resetToken,
                newPassword
            );

            if (response.success) {
                ToastService.showSuccess('تم تغيير كلمة المرور بنجاح');

                // ✅ تسجيل دخول تلقائي إذا كان هناك access_token
                if (response.access_token || response.accessToken) {
                    const TempStorageService = require('../services/TempStorageService').default;
                    const AsyncStorage = require('@react-native-async-storage/async-storage').default;

                    try {
                        const accessToken = response.access_token || response.accessToken;
                        const refreshToken = response.refresh_token || response.refreshToken;
                        const userId = response.user_id;

                        // حفظ بيانات المستخدم
                        const userData = {
                            id: userId,
                            email: email,
                            user_type: 'user',
                        };

                        // حفظ في TempStorage و AsyncStorage
                        await Promise.all([
                            TempStorageService.setItem('authToken', accessToken),
                            TempStorageService.setItem('accessToken', accessToken),
                            TempStorageService.setItem('userData', JSON.stringify(userData)),
                            TempStorageService.setItem('isLoggedIn', 'true'),
                            AsyncStorage.setItem('authToken', accessToken),
                            AsyncStorage.setItem('userData', JSON.stringify(userData)),
                            AsyncStorage.setItem('isLoggedIn', 'true'),
                        ]);

                        if (refreshToken) {
                            await Promise.all([
                                TempStorageService.setItem('refreshToken', refreshToken),
                                AsyncStorage.setItem('refreshToken', refreshToken),
                            ]);
                        }

                        // الانتقال مباشرة للـ Dashboard
                        setTimeout(() => {
                            navigation.reset({
                                index: 0,
                                routes: [{ name: 'Dashboard' }],
                            });
                        }, 1500);
                    } catch (storageError) {
                        console.error('⚠️ خطأ في حفظ البيانات:', storageError);
                        // في حالة فشل الحفظ، العودة لشاشة تسجيل الدخول
                        setTimeout(() => {
                            navigation.navigate('Login');
                        }, 1500);
                    }
                } else {
                    // لا يوجد token للدخول التلقائي - العودة لشاشة تسجيل الدخول
                    setTimeout(() => {
                        navigation.navigate('Login');
                    }, 1500);
                }
            } else {
                ToastService.showError(response.message || 'فشل في تغيير كلمة المرور');
            }
        } catch (error) {
            console.error('[ERROR] خطأ في تغيير كلمة المرور:', error);
            ToastService.showError('حدث خطأ في تغيير كلمة المرور');
        } finally {
            setLoading(false);
        }
    };

    const getPasswordStrength = (password) => {
        if (!password) { return { strength: 0, text: '', color: theme.colors.textSecondary }; }

        let strength = 0;
        if (password.length >= 8) { strength++; }
        if (password.length >= 12) { strength++; }
        if (/[A-Z]/.test(password)) { strength++; }
        if (/[a-z]/.test(password)) { strength++; }
        if (/[0-9]/.test(password)) { strength++; }
        if (/[^A-Za-z0-9]/.test(password)) { strength++; }

        if (strength <= 2) { return { strength: 33, text: 'ضعيفة', color: theme.colors.error }; }
        if (strength <= 4) { return { strength: 66, text: 'متوسطة', color: theme.colors.warning }; }
        return { strength: 100, text: 'قوية', color: theme.colors.success };
    };

    const passwordStrength = getPasswordStrength(newPassword);

    return (
        <SafeAreaView style={styles.container}>
            <StatusBar barStyle="light-content" backgroundColor={theme.colors.background} />

            <GlobalHeader
                title="كلمة المرور الجديدة"
                showBack={true}
                onBack={() => navigation.goBack()}
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
                            <Icon name="lock" size={24} color={theme.colors.info} />
                            <Text style={styles.infoText}>
                                أدخل كلمة مرور جديدة قوية لحسابك
                            </Text>
                        </View>
                    </ModernCard>

                    {/* New Password Input */}
                    <View style={styles.form}>
                        <ModernInput
                            label="كلمة المرور الجديدة"
                            value={newPassword}
                            onChangeText={setNewPassword}
                            placeholder="أدخل كلمة المرور الجديدة"
                            icon="lock"
                            secureTextEntry={true}
                            editable={!loading}
                            autoCapitalize="none"
                        />

                        {/* Password Strength */}
                        {newPassword.length > 0 && (
                            <View style={styles.strengthContainer}>
                                <View style={styles.strengthBarContainer}>
                                    <View
                                        style={[
                                            styles.strengthBar,
                                            {
                                                width: `${passwordStrength.strength}%`,
                                                backgroundColor: passwordStrength.color,
                                            },
                                        ]}
                                    />
                                </View>
                                <Text style={[styles.strengthText, { color: passwordStrength.color }]}>
                                    {passwordStrength.text}
                                </Text>
                            </View>
                        )}
                    </View>

                    {/* Confirm Password Input */}
                    <View style={styles.form}>
                        <ModernInput
                            label="تأكيد كلمة المرور"
                            value={confirmPassword}
                            onChangeText={setConfirmPassword}
                            placeholder="أعد إدخال كلمة المرور"
                            icon="lock"
                            secureTextEntry={true}
                            editable={!loading}
                            autoCapitalize="none"
                            error={confirmPassword.length > 0 && newPassword !== confirmPassword ? 'كلمات المرور غير متطابقة' : null}
                            success={confirmPassword.length > 0 && newPassword === confirmPassword}
                            successText={confirmPassword.length > 0 && newPassword === confirmPassword ? 'كلمات المرور متطابقة' : null}
                        />
                    </View>

                    {/* Requirements */}
                    <ModernCard>
                        <View style={styles.requirementsContainer}>
                            <Text style={styles.requirementsTitle}>متطلبات كلمة المرور:</Text>
                            <View style={styles.requirement}>
                                <Icon
                                    name={newPassword.length >= 8 ? 'check' : 'circle'}
                                    size={14}
                                    color={newPassword.length >= 8 ? theme.colors.success : theme.colors.textSecondary}
                                />
                                <Text style={styles.requirementText}>8 أحرف على الأقل</Text>
                            </View>
                            <View style={styles.requirement}>
                                <Icon
                                    name={/[a-z]/.test(newPassword) ? 'check' : 'circle'}
                                    size={14}
                                    color={/[a-z]/.test(newPassword) ? theme.colors.success : theme.colors.textSecondary}
                                />
                                <Text style={styles.requirementText}>حرف صغير واحد على الأقل</Text>
                            </View>
                            <View style={styles.requirement}>
                                <Icon
                                    name={/[A-Z]/.test(newPassword) ? 'check' : 'circle'}
                                    size={14}
                                    color={/[A-Z]/.test(newPassword) ? theme.colors.success : theme.colors.textSecondary}
                                />
                                <Text style={styles.requirementText}>حرف كبير واحد على الأقل</Text>
                            </View>
                            <View style={styles.requirement}>
                                <Icon
                                    name={/[0-9]/.test(newPassword) ? 'check' : 'circle'}
                                    size={14}
                                    color={/[0-9]/.test(newPassword) ? theme.colors.success : theme.colors.textSecondary}
                                />
                                <Text style={styles.requirementText}>رقم واحد على الأقل</Text>
                            </View>
                        </View>
                    </ModernCard>
                </View>

                {/* Submit Button */}
                <View style={styles.buttonContainer}>
                    <ModernButton
                        title={loading ? 'جاري الحفظ...' : 'تغيير كلمة المرور'}
                        onPress={handleResetPassword}
                        disabled={loading || !newPassword || !confirmPassword || newPassword !== confirmPassword}
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
        marginTop: theme.spacing.lg,
    },
    strengthContainer: {
        marginTop: theme.spacing.sm,
    },
    strengthBarContainer: {
        height: 4,
        backgroundColor: theme.colors.border,
        borderRadius: 2,
        overflow: 'hidden',
    },
    strengthBar: {
        height: '100%',
        borderRadius: 2,
    },
    strengthText: {
        ...theme.hierarchy.tiny,
        marginTop: theme.spacing.xs,
    },
    requirementsContainer: {
        gap: theme.spacing.sm,
    },
    requirementsTitle: {
        ...theme.hierarchy.caption,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: theme.spacing.xs,
    },
    requirement: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing.sm,
    },
    requirementText: {
        ...theme.hierarchy.tiny,
        color: theme.colors.textSecondary,
    },
    buttonContainer: {
        padding: theme.spacing.lg,
        borderTopWidth: 0,
    },
});

export default NewPasswordScreen;
