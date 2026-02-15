/**
 * شاشة الملف الشخصي - مبسطة ومنظمة
 */

import React, { useState, useEffect } from 'react';
import {
    View,
    Text,
    TouchableOpacity,
    ScrollView,
    StyleSheet,
    Switch,
    Alert,
    KeyboardAvoidingView,
    Platform,
    RefreshControl,
} from 'react-native';
import { theme } from '../theme/theme';
import { colors, spacing, typography, components, shadows } from '../theme/designSystem';
import ModernCard from '../components/ModernCard';
import ModernInput from '../components/ModernInput';
import BiometricAuth from '../services/BiometricService';
import DatabaseApiService from '../services/DatabaseApiService';
import { useIsAdmin } from '../hooks/useIsAdmin';
import AdminModeBanner from '../components/AdminModeBanner';
import FingerprintIcon from '../components/FingerprintIcon';
import { useBackHandler } from '../utils/BackHandlerUtil';
import ToastService from '../services/ToastService';
import { useTradingModeContext } from '../context/TradingModeContext';
import SecureActionsService, { SECURE_ACTIONS } from '../services/SecureActionsService';
import GlobalHeader from '../components/GlobalHeader';
import { SafeAreaView } from 'react-native-safe-area-context';
import PasswordPromptModal from '../components/PasswordPromptModal';

const ProfileScreen = ({ user, onBack, onLogout, navigation }) => {
    const isAdmin = useIsAdmin(user);
    const { clearUserData, tradingMode } = useTradingModeContext();

    const [userInfo, setUserInfo] = useState({
        username: user?.username || 'المستخدم',
        name: user?.name || '',
        email: user?.email || '',
        phone_number: user?.phone_number || user?.phoneNumber || '',
        joinDate: user?.created_at || new Date().toISOString(),
    });

    const [biometricSettings, setBiometricSettings] = useState({
        available: false,
        enabled: false,
        biometryType: null,
    });

    const [editMode, setEditMode] = useState(null); // 'name' | 'email' | 'password' | 'phone_number' | null
    const [editValue, setEditValue] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [showVerification, setShowVerification] = useState(false);
    const [pendingAction, setPendingAction] = useState(null);
    const [refreshing, setRefreshing] = useState(false);
    const [showPasswordModal, setShowPasswordModal] = useState(false);

    useBackHandler(() => {
        if (editMode) {
            setEditMode(null);
            return;
        }
        onBack && onBack();
    });

    useEffect(() => {
        let isMounted = true;

        const initialize = async () => {
            if (isMounted) {
                await loadUserProfile();
                await initializeBiometric();
            }
        };

        initialize();

        return () => {
            isMounted = false;
        };
    }, []);

    const initializeBiometric = async () => {
        try {
            const result = await BiometricAuth.initialize();
            const isRegistered = await BiometricAuth.isBiometricRegistered(user?.id || 'current_user');
            setBiometricSettings({
                available: result.available,
                enabled: isRegistered,
                biometryType: result.biometryType,
            });
        } catch (error) {
            console.error('[ERROR] خطأ في تهيئة البصمة:', error);
        }
    };

    const loadUserProfile = async (isRefresh = false) => {
        try {
            if (isRefresh) { setRefreshing(true); }
            if (!user?.id) { return; }
            const response = await DatabaseApiService.getProfile(user.id);
            if (response?.success && response?.data) {
                const d = response.data;
                setUserInfo(prev => ({
                    ...prev,
                    ...d,
                    phone_number: d.phone_number || d.phoneNumber || prev.phone_number || '',
                }));
            }
        } catch (error) {
            console.error('[ERROR] خطأ في تحميل الملف الشخصي:', error);
        } finally {
            if (isRefresh) { setRefreshing(false); }
        }
    };

    // ✅ Pull-to-refresh
    const onRefresh = () => {
        loadUserProfile(true);
    };

    // تبديل البصمة - مع التحقق من الهوية
    const handleToggleBiometric = async (enabled) => {
        if (!biometricSettings.available) {
            ToastService.showInfo('البصمة غير متاحة على هذا الجهاز');
            return;
        }

        const action = enabled ? 'تفعيل' : 'إلغاء';

        Alert.alert(
            `${action} البصمة`,
            `هل تريد ${action} تسجيل الدخول بالبصمة؟\nسيتم إرسال رمز تحقق للتأكيد.`,
            [
                { text: 'إلغاء', style: 'cancel' },
                {
                    text: 'متابعة',
                    onPress: () => {
                        // الانتقال لشاشة التحقق
                        navigation?.navigate('VerifyAction', {
                            action: SECURE_ACTIONS.CHANGE_BIOMETRIC,
                            newValue: enabled ? 'enable' : 'disable',
                            onSuccess: async (result) => {
                                // تنفيذ تغيير البصمة بعد التحقق
                                const userId = user?.id || 'current_user';

                                if (enabled) {
                                    const username = user?.username || userInfo.username;
                                    const bioResult = await BiometricAuth.registerBiometric(userId.toString(), username);
                                    if (bioResult.success) {
                                        setBiometricSettings(prev => ({ ...prev, enabled: true }));
                                        ToastService.showSuccess('تم تفعيل البصمة');
                                    } else {
                                        ToastService.showError(bioResult.message || 'فشل تفعيل البصمة');
                                    }
                                } else {
                                    const bioResult = await BiometricAuth.removeBiometric(userId);
                                    if (bioResult.success) {
                                        setBiometricSettings(prev => ({ ...prev, enabled: false }));
                                        ToastService.showSuccess('تم إلغاء البصمة');
                                    }
                                }
                            },
                            onCancel: () => {
                                // لا شيء
                            },
                        });
                    },
                },
            ]
        );
    };

    // بدء التعديل
    const startEdit = async (field) => {
        // ✅ الاسم الكامل: تعديل مباشر بدون OTP
        if (field === 'name') {
            setEditValue(userInfo[field] || '');
            setEditMode(field);
            return;
        }

        // ✅ باقي الحقول: تحتاج تحقق OTP
        let action;
        switch (field) {
            case 'email':
                action = SECURE_ACTIONS.CHANGE_EMAIL;
                break;
            case 'password':
                action = SECURE_ACTIONS.CHANGE_PASSWORD;
                break;
            case 'phone_number':
                action = SECURE_ACTIONS.CHANGE_PHONE;
                break;
            default:
                return;
        }

        // حفظ العملية المعلقة
        setPendingAction({ field, action });

        if (field === 'password') {
            setEditValue('');
        } else {
            setEditValue(userInfo[field] || '');
        }
        setEditMode(field);
    };

    // حفظ التعديل
    const saveEdit = async () => {
        // ✅ الاسم الكامل: حفظ مباشر بدون OTP
        if (editMode === 'name') {
            // ✅ Validation للاسم
            const trimmedName = editValue.trim();
            if (!trimmedName || trimmedName.length < 2) {
                ToastService.showError('الاسم يجب أن يكون حرفين على الأقل');
                return;
            }
            if (trimmedName.length > 50) {
                ToastService.showError('الاسم طويل جداً (50 حرف كحد أقصى)');
                return;
            }

            setIsLoading(true);
            try {
                const response = await DatabaseApiService.updateProfile(user.id, {
                    name: trimmedName,
                });

                if (response?.success) {
                    setUserInfo(prev => ({ ...prev, name: trimmedName }));
                    setEditMode(null);
                    ToastService.showSuccess('تم تحديث الاسم بنجاح');
                    // ✅ Refresh من Backend للتأكد من التطابق
                    await loadUserProfile(true);
                } else {
                    ToastService.showError(response?.error || 'فشل تحديث الاسم');
                }
            } catch (error) {
                console.error('[ProfileScreen] خطأ في تحديث الاسم:', error);
                ToastService.showError('حدث خطأ أثناء تحديث الاسم');
            } finally {
                setIsLoading(false);
            }
            return;
        }

        // ✅ باقي الحقول: تحتاج تحقق OTP
        if (!editValue.trim()) {
            ToastService.showError('الحقل مطلوب');
            return;
        }

        // ✅ التحقق من صيغة الإيميل
        if (editMode === 'email' && editValue.trim()) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(editValue.trim())) {
                ToastService.showError('صيغة البريد الإلكتروني غير صحيحة');
                return;
            }
        }

        // ✅ التحقق من قوة كلمة المرور
        if (editMode === 'password') {
            if (editValue.length < 8) {
                ToastService.showError('كلمة المرور يجب أن تكون 8 أحرف على الأقل');
                return;
            }
            if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(editValue)) {
                ToastService.showError('كلمة المرور يجب أن تحتوي على حروف كبيرة وصغيرة وأرقام');
                return;
            }
        }

        // ✅ التحقق من صيغة رقم الهاتف
        if (editMode === 'phone_number' && editValue.trim()) {
            const phoneRegex = /^[\d\s\-\+\(\)]{8,20}$/;
            if (!phoneRegex.test(editValue.trim())) {
                ToastService.showError('رقم الهاتف غير صحيح');
                return;
            }
        }

        // الانتقال لشاشة التحقق
        if (pendingAction) {
            navigation?.navigate('VerifyAction', {
                action: pendingAction.action,
                newValue: editValue.trim(),
                onSuccess: (result) => {
                    // تحديث البيانات المحلية
                    if (editMode !== 'password') {
                        setUserInfo(prev => ({ ...prev, [editMode]: editValue.trim() }));
                    }
                    setEditMode(null);
                    setPendingAction(null);
                    loadUserProfile(true);
                },
                onCancel: () => {
                    // ✅ معالجة الإلغاء: إعادة تعيين الحالة
                    setEditMode(null);
                    setPendingAction(null);
                    ToastService.showInfo('تم إلغاء العملية');
                },
            });
        }
    };

    // تسجيل الخروج مع Double Confirmation
    const handleLogout = () => {
        Alert.alert(
            'تسجيل الخروج',
            'هل تريد تسجيل الخروج من التطبيق؟',
            [
                { text: 'إلغاء', style: 'cancel' },
                {
                    text: 'تأكيد',
                    style: 'destructive',
                    onPress: () => {
                        // ✅ Double Confirmation
                        Alert.alert(
                            'تأكيد نهائي',
                            'هل أنت متأكد من تسجيل الخروج؟ سيتم مسح جميع البيانات المحلية.',
                            [
                                { text: 'إلغاء', style: 'cancel' },
                                {
                                    text: 'نعم، خروج',
                                    style: 'destructive',
                                    onPress: async () => {
                                        // ✅ إصلاح: مسح بيانات TradingModeContext عند تسجيل الخروج
                                        await clearUserData();
                                        onLogout();
                                    },
                                },
                            ]
                        );
                    },
                },
            ]
        );
    };

    // حذف الحساب مع Double Confirmation
    const handleDeleteAccount = () => {
        // التحقق من أنه ليس الأدمن
        if (isAdmin) {
            Alert.alert('تنبيه', 'لا يمكن حذف حساب المدير');
            return;
        }

        // المرحلة 1: تأكيد أولي
        Alert.alert(
            '⚠️ حذف الحساب',
            'هل أنت متأكد من رغبتك في حذف حسابك نهائياً؟\n\nسيتم حذف جميع بياناتك بما في ذلك:\n• المحفظة والأرصدة\n• سجل الصفقات\n• الإعدادات\n• مفاتيح Binance\n\n⚠️ هذا الإجراء لا يمكن التراجع عنه!',
            [
                { text: 'إلغاء', style: 'cancel' },
                {
                    text: 'متابعة',
                    style: 'destructive',
                    onPress: () => {
                        // ✅ Double Confirmation
                        Alert.alert(
                            'تأكيد نهائي - خطوة أخيرة',
                            '⚠️ هذه هي فرصتك الأخيرة للإلغاء.\n\nهل أنت متأكد 100% من حذف حسابك؟\n\nلن تتمكن من استرداد أي من بياناتك.',
                            [
                                { text: 'إلغاء', style: 'cancel' },
                                {
                                    text: 'نعم، احذف نهائياً',
                                    style: 'destructive',
                                    onPress: () => promptPasswordForDelete(),
                                },
                            ]
                        );
                    },
                },
            ]
        );
    };

    // طلب كلمة المرور للحذف
    const promptPasswordForDelete = () => {
        setShowPasswordModal(true);
    };

    // تنفيذ الحذف
    const confirmDeleteAccount = async (password) => {
        if (!password || password.length < 4) {
            Alert.alert('خطأ', 'كلمة المرور مطلوبة');
            return;
        }

        setIsLoading(true);
        try {
            const result = await DatabaseApiService.deleteAccount(password, 'DELETE');

            if (result.success) {
                Alert.alert(
                    '✅ تم الحذف',
                    result.message || 'تم حذف حسابك بنجاح',
                    [
                        {
                            text: 'موافق',
                            onPress: () => {
                                // تسجيل الخروج وإعادة التوجيه
                                onLogout && onLogout();
                            },
                        },
                    ]
                );
            } else {
                Alert.alert('خطأ', result.error || 'فشل حذف الحساب');
            }
        } catch (error) {
            console.error('[ERROR] خطأ في حذف الحساب:', error);
            Alert.alert('خطأ', 'حدث خطأ أثناء حذف الحساب');
        } finally {
            setIsLoading(false);
        }
    };

    const formatDate = (dateString) => {
        try {
            return new Date(dateString).toLocaleDateString('ar-SA', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
            });
        } catch {
            return '-';
        }
    };


    return (
        <SafeAreaView style={styles.container}>
            {/* ✅ Banner تحذيري للأدمن - مع تمرير وضع التداول */}
            {isAdmin && <AdminModeBanner tradingMode={tradingMode} />}

            {/* ✅ Header يُعرض من Navigator - لا نحتاج GlobalHeader هنا */}

            <KeyboardAvoidingView
                style={styles.flex}
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
                keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 20}
            >
                <ScrollView
                    style={styles.content}
                    showsVerticalScrollIndicator={false}
                    keyboardShouldPersistTaps="handled"
                    keyboardDismissMode="on-drag"
                    refreshControl={
                        <RefreshControl
                            refreshing={refreshing}
                            onRefresh={onRefresh}
                            tintColor={theme.colors.primary}
                        />
                    }
                >
                    {/* رأس الصفحة - بسيط بدون صورة */}
                    <View style={styles.headerSimple}>
                        <Text style={styles.welcomeText}>مرحباً،</Text>
                        <Text style={styles.usernameTitle}>
                            {userInfo.name || userInfo.username}
                        </Text>
                        <View style={styles.accountBadge}>
                            <Text style={styles.accountBadgeText}>
                                {isAdmin ? 'مدير النظام' : 'حساب تداول'}
                            </Text>
                        </View>
                    </View>

                    {/* ═══════════════ 1. المعلومات الشخصية ═══════════════ */}
                    <View style={styles.sectionContainer}>
                        <Text style={styles.sectionHeader}>المعلومات الشخصية</Text>

                        <View style={styles.groupedCard}>
                            {/* الاسم الكامل */}
                            <View style={styles.groupedItem}>
                                <Text style={styles.groupedLabel}>الاسم</Text>
                                {editMode === 'name' ? (
                                    <View style={styles.editContainer}>
                                        <ModernInput
                                            value={editValue}
                                            onChangeText={setEditValue}
                                            placeholder="أدخل اسمك"
                                            autoFocus
                                            containerStyle={{ marginBottom: 8 }}
                                        />
                                        <View style={styles.editButtonsRow}>
                                            <TouchableOpacity style={styles.confirmBtn} onPress={saveEdit}>
                                                <Text style={styles.confirmBtnText}>حفظ</Text>
                                            </TouchableOpacity>
                                            <TouchableOpacity style={styles.cancelEditBtn} onPress={() => setEditMode(null)}>
                                                <Text style={styles.cancelEditBtnText}>إلغاء</Text>
                                            </TouchableOpacity>
                                        </View>
                                    </View>
                                ) : (
                                    <TouchableOpacity style={styles.groupedValueRow} onPress={() => startEdit('name')}>
                                        <Text style={styles.groupedValue}>{userInfo.name || 'إضافة اسم'}</Text>
                                        <Text style={styles.chevron}>‹</Text>
                                    </TouchableOpacity>
                                )}
                            </View>

                            <View style={styles.groupedDivider} />

                            {/* البريد الإلكتروني */}
                            <View style={styles.groupedItem}>
                                <Text style={styles.groupedLabel}>البريد الإلكتروني</Text>
                                {editMode === 'email' ? (
                                    <View style={styles.editContainer}>
                                        <ModernInput
                                            value={editValue}
                                            onChangeText={setEditValue}
                                            placeholder="البريد الإلكتروني"
                                            keyboardType="email-address"
                                            autoCapitalize="none"
                                            autoFocus
                                            containerStyle={{ marginBottom: 8 }}
                                        />
                                        <View style={styles.editButtonsRow}>
                                            <TouchableOpacity style={styles.confirmBtn} onPress={saveEdit}>
                                                <Text style={styles.confirmBtnText}>حفظ</Text>
                                            </TouchableOpacity>
                                            <TouchableOpacity style={styles.cancelEditBtn} onPress={() => setEditMode(null)}>
                                                <Text style={styles.cancelEditBtnText}>إلغاء</Text>
                                            </TouchableOpacity>
                                        </View>
                                    </View>
                                ) : (
                                    <TouchableOpacity style={styles.groupedValueRow} onPress={() => startEdit('email')}>
                                        <Text style={styles.groupedValue}>{userInfo.email || '-'}</Text>
                                        <Text style={styles.chevron}>‹</Text>
                                    </TouchableOpacity>
                                )}
                            </View>

                            <View style={styles.groupedDivider} />

                            {/* رقم الهاتف */}
                            <View style={styles.groupedItem}>
                                <Text style={styles.groupedLabel}>رقم الهاتف</Text>
                                {editMode === 'phone_number' ? (
                                    <View style={styles.editContainer}>
                                        <ModernInput
                                            value={editValue}
                                            onChangeText={setEditValue}
                                            placeholder="رقم الهاتف"
                                            keyboardType="phone-pad"
                                            autoFocus
                                            containerStyle={{ marginBottom: 8 }}
                                        />
                                        <View style={styles.editButtonsRow}>
                                            <TouchableOpacity style={styles.confirmBtn} onPress={saveEdit}>
                                                <Text style={styles.confirmBtnText}>حفظ</Text>
                                            </TouchableOpacity>
                                            <TouchableOpacity style={styles.cancelEditBtn} onPress={() => setEditMode(null)}>
                                                <Text style={styles.cancelEditBtnText}>إلغاء</Text>
                                            </TouchableOpacity>
                                        </View>
                                    </View>
                                ) : (
                                    <TouchableOpacity style={styles.groupedValueRow} onPress={() => startEdit('phone_number')}>
                                        <Text style={styles.groupedValue}>{userInfo.phone_number || 'إضافة رقم'}</Text>
                                        <Text style={styles.chevron}>‹</Text>
                                    </TouchableOpacity>
                                )}
                            </View>
                        </View>
                    </View>

                    {/* ═══════════════ 2. الأمان والخصوصية ═══════════════ */}
                    <View style={styles.sectionContainer}>
                        <Text style={styles.sectionHeader}>الأمان والخصوصية</Text>

                        <View style={styles.groupedCard}>
                            {/* كلمة المرور */}
                            <View style={styles.groupedItem}>
                                <Text style={styles.groupedLabel}>كلمة المرور</Text>
                                {editMode === 'password' ? (
                                    <View style={styles.editContainer}>
                                        <ModernInput
                                            value={editValue}
                                            onChangeText={setEditValue}
                                            placeholder="كلمة المرور الجديدة"
                                            secureTextEntry={true}
                                            autoFocus={true}
                                            icon="lock"
                                            containerStyle={{ marginBottom: 8 }}
                                        />
                                        <View style={styles.editButtonsRow}>
                                            <TouchableOpacity style={styles.confirmBtn} onPress={saveEdit}>
                                                <Text style={styles.confirmBtnText}>حفظ</Text>
                                            </TouchableOpacity>
                                            <TouchableOpacity style={styles.cancelEditBtn} onPress={() => setEditMode(null)}>
                                                <Text style={styles.cancelEditBtnText}>إلغاء</Text>
                                            </TouchableOpacity>
                                        </View>
                                    </View>
                                ) : (
                                    <TouchableOpacity style={styles.groupedValueRow} onPress={() => startEdit('password')}>
                                        <Text style={styles.groupedValue}>••••••••</Text>
                                        <Text style={styles.chevron}>‹</Text>
                                    </TouchableOpacity>
                                )}
                            </View>

                            {/* البصمة / Face ID */}
                            <View style={styles.groupedDivider} />
                            <View style={styles.groupedItem}>
                                <View style={styles.groupedLabelRow}>
                                    <FingerprintIcon size={18} color={biometricSettings.available ? theme.colors.primary : theme.colors.textTertiary} />
                                    <View>
                                        <Text style={[styles.groupedLabel, { marginRight: 8 }, !biometricSettings.available && { color: theme.colors.textTertiary }]}>
                                            {biometricSettings.biometryType === 'FaceID' ? 'Face ID' : 'تسجيل الدخول بالبصمة'}
                                        </Text>
                                        {!biometricSettings.available && (
                                            <Text style={styles.biometricHint}>غير متاح على هذا الجهاز</Text>
                                        )}
                                    </View>
                                </View>
                                <Switch
                                    value={biometricSettings.enabled}
                                    onValueChange={handleToggleBiometric}
                                    trackColor={{ false: '#333', true: theme.colors.primary }}
                                    thumbColor="#FFF"
                                    disabled={!biometricSettings.available}
                                />
                            </View>
                        </View>
                    </View>

                    {/* ═══════════════ 3. معلومات الحساب ═══════════════ */}
                    <View style={styles.sectionContainer}>
                        <Text style={styles.sectionHeader}>معلومات الحساب</Text>

                        <View style={styles.groupedCard}>
                            {/* اسم المستخدم */}
                            <View style={styles.groupedItem}>
                                <Text style={styles.groupedLabel}>اسم المستخدم</Text>
                                <Text style={styles.groupedValueStatic}>@{userInfo.username}</Text>
                            </View>

                            <View style={styles.groupedDivider} />

                            {/* تاريخ الانضمام */}
                            <View style={styles.groupedItem}>
                                <Text style={styles.groupedLabel}>تاريخ الانضمام</Text>
                                <Text style={styles.groupedValueStatic}>{formatDate(userInfo.joinDate)}</Text>
                            </View>
                        </View>
                    </View>

                    {/* ═══════════════ 4. الإعدادات ═══════════════ */}
                    <View style={styles.sectionContainer}>
                        <Text style={styles.sectionHeader}>الإعدادات</Text>

                        <View style={styles.groupedCard}>
                            <TouchableOpacity
                                style={styles.groupedItemTouchable}
                                onPress={() => navigation?.navigate('NotificationSettings')}
                                activeOpacity={0.7}
                            >
                                <View style={styles.groupedLabelRow}>
                                    <Text style={styles.settingsIcon}>🔔</Text>
                                    <Text style={styles.groupedLabel}>الإشعارات</Text>
                                </View>
                                <Text style={styles.chevron}>‹</Text>
                            </TouchableOpacity>
                        </View>
                    </View>

                    {/* ═══════════════ 5. حول التطبيق ═══════════════ */}
                    <View style={styles.sectionContainer}>
                        <Text style={styles.sectionHeader}>حول التطبيق</Text>

                        <View style={styles.groupedCard}>
                            {/* 📖 دليل الاستخدام - الأهم */}
                            <TouchableOpacity
                                style={styles.groupedItemTouchable}
                                onPress={() => navigation?.navigate('UsageGuide')}
                                activeOpacity={0.7}
                            >
                                <View style={styles.groupedLabelRow}>
                                    <Text style={styles.settingsIcon}>📖</Text>
                                    <Text style={styles.groupedLabel}>دليل الاستخدام</Text>
                                </View>
                                <Text style={styles.chevron}>‹</Text>
                            </TouchableOpacity>

                            <View style={styles.groupedDivider} />

                            {/* شروط الاستخدام */}
                            <TouchableOpacity
                                style={styles.groupedItemTouchable}
                                onPress={() => navigation?.navigate('TermsAndConditions')}
                                activeOpacity={0.7}
                            >
                                <Text style={styles.groupedLabel}>شروط الاستخدام</Text>
                                <Text style={styles.chevron}>‹</Text>
                            </TouchableOpacity>

                            <View style={styles.groupedDivider} />

                            {/* سياسة الخصوصية */}
                            <TouchableOpacity
                                style={styles.groupedItemTouchable}
                                onPress={() => navigation?.navigate('PrivacyPolicy')}
                                activeOpacity={0.7}
                            >
                                <Text style={styles.groupedLabel}>سياسة الخصوصية</Text>
                                <Text style={styles.chevron}>‹</Text>
                            </TouchableOpacity>

                            <View style={styles.groupedDivider} />

                            {/* الإصدار */}
                            <View style={styles.groupedItem}>
                                <Text style={styles.groupedLabel}>الإصدار</Text>
                                <Text style={styles.groupedValueStatic}>{require('../../package.json').version}</Text>
                            </View>
                        </View>
                    </View>

                    {/* تسجيل الخروج */}
                    <TouchableOpacity
                        style={styles.logoutBtn}
                        onPress={handleLogout}
                        activeOpacity={0.8}
                    >
                        <Text style={styles.logoutText}>🚪 تسجيل الخروج</Text>
                    </TouchableOpacity>

                    {/* حذف الحساب - للمستخدمين العاديين فقط */}
                    {!isAdmin && (
                        <TouchableOpacity
                            style={styles.deleteAccountBtn}
                            onPress={handleDeleteAccount}
                            activeOpacity={0.8}
                            disabled={isLoading}
                        >
                            <Text style={styles.deleteAccountText}>
                                {isLoading ? '⏳ جاري الحذف...' : '🗑️ حذف الحساب نهائياً'}
                            </Text>
                        </TouchableOpacity>
                    )}

                    <View style={{ height: 40 }} />
                </ScrollView>
            </KeyboardAvoidingView>

            {/* Modal إدخال كلمة المرور للحذف */}
            <PasswordPromptModal
                visible={showPasswordModal}
                title="🔐 تأكيد الهوية"
                message="أدخل كلمة المرور لتأكيد حذف الحساب نهائياً:"
                placeholder="كلمة المرور"
                confirmText="حذف نهائياً"
                cancelText="إلغاء"
                confirmButtonStyle="destructive"
                onConfirm={(password) => {
                    setShowPasswordModal(false);
                    confirmDeleteAccount(password);
                }}
                onCancel={() => setShowPasswordModal(false)}
            />
        </SafeAreaView >
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
        paddingHorizontal: 16,
    },
    // التصميم الجديد - رأس بسيط
    headerSimple: {
        paddingTop: 24,
        paddingBottom: 20,
        alignItems: 'flex-end',
    },
    welcomeText: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        marginBottom: 4,
    },
    usernameTitle: {
        fontSize: 28,
        fontWeight: '700',
        color: theme.colors.text,
        marginBottom: 12,
    },
    accountBadge: {
        backgroundColor: theme.colors.primary + '20',
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 16,
    },
    accountBadgeText: {
        fontSize: 12,
        color: theme.colors.primary,
        fontWeight: '600',
    },
    // أقسام المحتوى
    sectionContainer: {
        marginBottom: 24,
    },
    sectionHeader: {
        fontSize: 13,
        fontWeight: '600',
        color: theme.colors.textSecondary,
        marginBottom: 12,
        textAlign: 'right',
        textTransform: 'uppercase',
        letterSpacing: 0.5,
    },
    // بطاقات المعلومات
    infoCard: {
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        paddingHorizontal: 16,
        paddingVertical: 14,
        marginBottom: 8,
    },
    infoCardRow: {
        flexDirection: 'column',
    },
    infoCardLabel: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        marginBottom: 6,
        textAlign: 'right',
    },
    infoCardValue: {
        fontSize: 16,
        color: theme.colors.text,
        fontWeight: '500',
        textAlign: 'right',
    },
    valueRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    editLink: {
        fontSize: 14,
        color: theme.colors.primary,
        fontWeight: '500',
    },
    // نموذج التعديل المحسن
    editContainer: {
        marginTop: 8,
    },
    modernInput: {
        backgroundColor: theme.colors.background,
        borderRadius: 8,
        paddingHorizontal: 14,
        paddingVertical: 12,
        fontSize: 16,
        color: theme.colors.text,
        textAlign: 'right',
        borderWidth: 1,
        borderColor: theme.colors.primary,
    },
    editButtonsRow: {
        flexDirection: 'row',
        justifyContent: 'flex-start',
        gap: 10,
        marginTop: 12,
    },
    confirmBtn: {
        backgroundColor: theme.colors.primary,
        paddingHorizontal: 20,
        paddingVertical: 10,
        borderRadius: 8,
    },
    confirmBtnText: {
        color: '#FFF',
        fontSize: 14,
        fontWeight: '600',
    },
    cancelEditBtn: {
        backgroundColor: theme.colors.surface,
        paddingHorizontal: 20,
        paddingVertical: 10,
        borderRadius: 8,
        borderWidth: 1,
        borderColor: colors.border.default,
    },
    cancelEditBtnText: {
        color: theme.colors.textSecondary,
        fontSize: 14,
        fontWeight: '500',
    },
    // البطاقات المجمعة (iOS Style)
    groupedCard: {
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        overflow: 'hidden',
    },
    groupedItem: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 16,
        paddingVertical: 14,
        minHeight: 50,
    },
    groupedItemTouchable: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 16,
        paddingVertical: 14,
        minHeight: 50,
    },
    groupedLabel: {
        fontSize: 16,
        color: theme.colors.text,
    },
    groupedLabelRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    groupedValue: {
        fontSize: 16,
        color: theme.colors.textSecondary,
    },
    groupedValueRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
    },
    groupedValueStatic: {
        fontSize: 16,
        color: theme.colors.textSecondary,
    },
    groupedDivider: {
        height: 1,
        backgroundColor: colors.border.default,
        marginLeft: 16,
    },
    chevron: {
        fontSize: 20,
        color: theme.colors.textTertiary,
        fontWeight: '300',
    },
    settingsIcon: {
        fontSize: 18,
        marginLeft: 8,
    },
    biometricHint: {
        fontSize: 12,
        color: theme.colors.textTertiary,
        marginRight: 8,
        marginTop: 2,
    },
    logoutBtn: {
        backgroundColor: colors.semantic.error + '15',
        borderWidth: 1,
        borderColor: colors.semantic.error,
        padding: spacing.md,
        borderRadius: components.card.borderRadius,
        alignItems: 'center',
        marginTop: spacing.xl,
    },
    logoutText: {
        fontSize: typography.size.base,
        fontWeight: typography.weight.semibold,
        color: colors.semantic.error,
    },
    deleteAccountBtn: {
        backgroundColor: colors.semantic.errorDark + '20',
        borderWidth: 1,
        borderColor: colors.semantic.errorDark,
        padding: spacing.md,
        borderRadius: components.card.borderRadius,
        alignItems: 'center',
        marginTop: spacing.md,
    },
    deleteAccountText: {
        fontSize: typography.size.sm,
        fontWeight: typography.weight.medium,
        color: colors.semantic.errorDark,
    },
    // Modal Styles
    modalOverlay: {
        flex: 1,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        justifyContent: 'flex-end',
    },
    imageModalContent: {
        backgroundColor: theme.colors.card,
        borderTopLeftRadius: 24,
        borderTopRightRadius: 24,
        padding: 24,
        paddingBottom: 40,
    },
    imageModalTitle: {
        fontSize: 18,
        fontWeight: '700',
        color: theme.colors.text,
        textAlign: 'center',
        marginBottom: 24,
    },
    imageOption: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
    },
    removeOption: {
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
    },
    imageOptionIcon: {
        fontSize: 24,
        marginRight: 16,
    },
    imageOptionText: {
        fontSize: theme.typography.fontSize.base,
        color: theme.colors.text,
        fontWeight: '500',
    },
    imageModalClose: {
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        padding: 16,
        marginTop: 8,
    },
    imageModalCloseText: {
        fontSize: theme.typography.fontSize.base,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        fontWeight: '600',
    },
});

export default ProfileScreen;
