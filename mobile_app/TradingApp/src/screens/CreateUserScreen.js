/**
 * ➕ شاشة إنشاء مستخدم جديد - Create User Screen
 * ✅ نموذج إنشاء مستخدم مع اختيار النوع (admin/regular/support)
 * ✅ تحقق من صحة البيانات قبل الإرسال
 * ✅ تصميم متناسق مع Theme الموحد
 */

import React, { useState, useCallback } from 'react';
import {
    View,
    Text,
    StyleSheet,
    ScrollView,
    KeyboardAvoidingView,
    Platform,
    TouchableOpacity,
} from 'react-native';
import { theme } from '../theme/theme';
import { colors, spacing, typography } from '../theme/designSystem';
import ModernCard from '../components/ModernCard';
import ModernButton from '../components/ModernButton';
import ModernInput from '../components/ModernInput';
import BrandIcon from '../components/BrandIcons';
import DatabaseApiService from '../services/DatabaseApiService';
import ToastService from '../services/ToastService';

const USER_TYPES = [
    {
        value: 'regular',
        label: 'مستخدم عادي',
        description: 'مستخدم يمكنه التداول ومتابعة محفظته',
        icon: 'user',
        color: colors.brand.primary,
    },
    {
        value: 'admin',
        label: 'مدير / دعم فني',
        description: 'صلاحيات كاملة: إدارة النظام والمستخدمين والدعم الفني',
        icon: 'shield',
        color: colors.semantic.error,
    },
];

const CreateUserScreen = ({ navigation }) => {
    const [form, setForm] = useState({
        username: '',
        email: '',
        password: '',
        confirmPassword: '',
        full_name: '',
        phone: '',
        user_type: 'regular',
    });
    const [errors, setErrors] = useState({});
    const [loading, setLoading] = useState(false);

    const updateField = (field, value) => {
        setForm(prev => ({ ...prev, [field]: value }));
        // مسح الخطأ عند الكتابة
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: null }));
        }
    };

    const validate = useCallback(() => {
        const newErrors = {};

        // اسم المستخدم
        if (!form.username.trim()) {
            newErrors.username = 'اسم المستخدم مطلوب';
        } else if (form.username.length < 3) {
            newErrors.username = 'يجب أن يكون 3 أحرف على الأقل';
        } else if (!/^[a-zA-Z0-9_]+$/.test(form.username)) {
            newErrors.username = 'يُسمح فقط بالأحرف الإنجليزية والأرقام و _';
        }

        // البريد الإلكتروني
        if (!form.email.trim()) {
            newErrors.email = 'البريد الإلكتروني مطلوب';
        } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
            newErrors.email = 'بريد إلكتروني غير صحيح';
        }

        // كلمة المرور
        if (!form.password) {
            newErrors.password = 'كلمة المرور مطلوبة';
        } else if (form.password.length < 8) {
            newErrors.password = 'يجب أن تكون 8 أحرف على الأقل';
        } else if (!/[A-Z]/.test(form.password)) {
            newErrors.password = 'يجب أن تحتوي على حرف كبير';
        } else if (!/[a-z]/.test(form.password)) {
            newErrors.password = 'يجب أن تحتوي على حرف صغير';
        } else if (!/\d/.test(form.password)) {
            newErrors.password = 'يجب أن تحتوي على رقم';
        }

        // تأكيد كلمة المرور
        if (form.password !== form.confirmPassword) {
            newErrors.confirmPassword = 'كلمة المرور غير متطابقة';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    }, [form]);

    const handleCreate = useCallback(async () => {
        if (!validate()) return;

        try {
            setLoading(true);
            const response = await DatabaseApiService.request('/admin/users/create', 'POST', {
                username: form.username.trim(),
                email: form.email.trim().toLowerCase(),
                password: form.password,
                full_name: form.full_name.trim(),
                phone: form.phone.trim(),
                user_type: form.user_type,
            });

            if (response?.success) {
                ToastService.showSuccess(`تم إنشاء المستخدم "${form.username}" بنجاح`);
                navigation.goBack();
            } else {
                const errorMsg = response?.error || 'فشل إنشاء المستخدم';
                if (errorMsg.includes('موجود بالفعل')) {
                    setErrors({ username: 'الاسم أو الإيميل مسجل بالفعل', email: 'الاسم أو الإيميل مسجل بالفعل' });
                }
                ToastService.showError(errorMsg);
            }
        } catch (error) {
            ToastService.showError('حدث خطأ أثناء إنشاء المستخدم');
        } finally {
            setLoading(false);
        }
    }, [form, validate, navigation]);

    return (
        <View style={styles.container}>
            <KeyboardAvoidingView
                style={{ flex: 1 }}
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            >
                <ScrollView
                    contentContainerStyle={styles.scrollContent}
                    keyboardShouldPersistTaps="handled"
                >
                    {/* معلومات أساسية */}
                    <ModernCard style={styles.card}>
                        <Text style={styles.sectionTitle}>المعلومات الأساسية</Text>

                        <ModernInput
                            label="اسم المستخدم *"
                            value={form.username}
                            onChangeText={(v) => updateField('username', v)}
                            placeholder="مثال: ahmed_ali"
                            autoCapitalize="none"
                            autoCorrect={false}
                            error={errors.username}
                        />

                        <ModernInput
                            label="البريد الإلكتروني *"
                            value={form.email}
                            onChangeText={(v) => updateField('email', v)}
                            placeholder="example@email.com"
                            autoCapitalize="none"
                            autoCorrect={false}
                            keyboardType="email-address"
                            error={errors.email}
                        />

                        <ModernInput
                            label="الاسم الكامل"
                            value={form.full_name}
                            onChangeText={(v) => updateField('full_name', v)}
                            placeholder="أحمد علي"
                        />

                        <ModernInput
                            label="رقم الهاتف"
                            value={form.phone}
                            onChangeText={(v) => updateField('phone', v)}
                            placeholder="+966XXXXXXXXX"
                            keyboardType="phone-pad"
                        />
                    </ModernCard>

                    {/* كلمة المرور */}
                    <ModernCard style={styles.card}>
                        <Text style={styles.sectionTitle}>كلمة المرور</Text>

                        <ModernInput
                            label="كلمة المرور *"
                            value={form.password}
                            onChangeText={(v) => updateField('password', v)}
                            placeholder="8 أحرف على الأقل"
                            secureTextEntry
                            error={errors.password}
                        />

                        <ModernInput
                            label="تأكيد كلمة المرور *"
                            value={form.confirmPassword}
                            onChangeText={(v) => updateField('confirmPassword', v)}
                            placeholder="أعد كتابة كلمة المرور"
                            secureTextEntry
                            error={errors.confirmPassword}
                        />

                        <View style={styles.passwordHints}>
                            <PasswordHint label="8 أحرف على الأقل" met={form.password.length >= 8} />
                            <PasswordHint label="حرف كبير (A-Z)" met={/[A-Z]/.test(form.password)} />
                            <PasswordHint label="حرف صغير (a-z)" met={/[a-z]/.test(form.password)} />
                            <PasswordHint label="رقم (0-9)" met={/\d/.test(form.password)} />
                        </View>
                    </ModernCard>

                    {/* نوع المستخدم */}
                    <ModernCard style={styles.card}>
                        <Text style={styles.sectionTitle}>نوع الحساب</Text>

                        {USER_TYPES.map((type) => (
                            <TouchableOpacity
                                key={type.value}
                                style={[
                                    styles.typeOption,
                                    form.user_type === type.value && styles.typeOptionSelected,
                                    form.user_type === type.value && { borderColor: type.color },
                                ]}
                                onPress={() => updateField('user_type', type.value)}
                                activeOpacity={0.7}
                            >
                                <View style={[styles.typeIconCircle, { backgroundColor: type.color + '15' }]}>
                                    <BrandIcon name={type.icon} size={20} color={type.color} />
                                </View>
                                <View style={styles.typeInfo}>
                                    <Text style={[styles.typeLabel, form.user_type === type.value && { color: type.color }]}>
                                        {type.label}
                                    </Text>
                                    <Text style={styles.typeDesc}>{type.description}</Text>
                                </View>
                                <View style={[
                                    styles.typeRadio,
                                    form.user_type === type.value && { borderColor: type.color },
                                ]}>
                                    {form.user_type === type.value && (
                                        <View style={[styles.typeRadioInner, { backgroundColor: type.color }]} />
                                    )}
                                </View>
                            </TouchableOpacity>
                        ))}
                    </ModernCard>

                    {/* زر الإنشاء */}
                    <ModernButton
                        title={loading ? 'جاري الإنشاء...' : '✅ إنشاء المستخدم'}
                        onPress={handleCreate}
                        variant="success"
                        size="large"
                        fullWidth
                        loading={loading}
                        disabled={loading}
                        style={styles.createButton}
                    />

                    <View style={{ height: 40 }} />
                </ScrollView>
            </KeyboardAvoidingView>
        </View>
    );
};

// مكون تلميح كلمة المرور
const PasswordHint = ({ label, met }) => (
    <View style={styles.hintRow}>
        <BrandIcon
            name={met ? 'check-circle' : 'circle'}
            size={14}
            color={met ? colors.semantic.success : colors.text.tertiary}
        />
        <Text style={[styles.hintText, met && { color: colors.semantic.success }]}>{label}</Text>
    </View>
);

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    scrollContent: {
        padding: spacing.md,
    },
    card: {
        marginBottom: spacing.md,
    },
    sectionTitle: {
        ...typography.h4,
        color: colors.text.primary,
        fontWeight: '600',
        marginBottom: spacing.md,
    },

    // تلميحات كلمة المرور
    passwordHints: {
        marginTop: spacing.sm,
        backgroundColor: colors.background.elevated,
        borderRadius: 8,
        padding: spacing.sm,
    },
    hintRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
        marginBottom: 4,
    },
    hintText: {
        ...typography.caption,
        color: colors.text.tertiary,
    },

    // اختيار نوع المستخدم
    typeOption: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: spacing.sm,
        borderRadius: 12,
        borderWidth: 2,
        borderColor: colors.border.default,
        marginBottom: spacing.sm,
        gap: spacing.sm,
    },
    typeOptionSelected: {
        backgroundColor: colors.background.elevated,
    },
    typeIconCircle: {
        width: 40,
        height: 40,
        borderRadius: 20,
        justifyContent: 'center',
        alignItems: 'center',
    },
    typeInfo: {
        flex: 1,
    },
    typeLabel: {
        ...typography.body1,
        color: colors.text.primary,
        fontWeight: '600',
    },
    typeDesc: {
        ...typography.caption,
        color: colors.text.secondary,
        marginTop: 2,
    },
    typeRadio: {
        width: 20,
        height: 20,
        borderRadius: 10,
        borderWidth: 2,
        borderColor: colors.border.default,
        justifyContent: 'center',
        alignItems: 'center',
    },
    typeRadioInner: {
        width: 10,
        height: 10,
        borderRadius: 5,
    },

    createButton: {
        marginTop: spacing.sm,
    },
});

export default CreateUserScreen;
