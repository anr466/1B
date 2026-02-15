/**
 * Notification Settings Screen - شاشة إعدادات الإشعارات
 * إدارة تفضيلات الإشعارات التفصيلية
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
    View,
    Text,
    ScrollView,
    StyleSheet,
    Switch,
    ActivityIndicator,
    StatusBar,
    TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import DatabaseApiService from '../services/DatabaseApiService';
import { theme } from '../theme/theme';
import ToastService from '../services/ToastService';
import { useBackHandler } from '../utils/BackHandlerUtil';
import { AlertService } from '../components/CustomAlert';
// ✅ GlobalHeader يأتي من Navigator
import ModernCard from '../components/ModernCard';
import ModernButton from '../components/ModernButton';
import Icon from '../components/CustomIcons';

const ImprovedNotificationSettingsScreen = ({ navigation, user }) => {
    const [settings, setSettings] = useState({
        tradeNotifications: true,
        priceAlerts: true,
        errorNotifications: true,
        dailySummary: true,
        pushEnabled: true,

        // إعدادات تفصيلية جديدة
        notifyNewDeal: true,
        notifyDealProfit: true,
        notifyDealLoss: true,
        notifyDailyProfit: true,
        notifyDailyLoss: true,
        notifyLowBalance: true,

        // إعدادات متقدمة جديدة
        notifySystemStatus: true,
        notifyMaintenance: false,
        notifySecurityAlerts: true,
        quietHoursEnabled: false,
        quietHoursStart: '22:00',
        quietHoursEnd: '08:00',
        notifyLargeProfit: true,
        notifyLargeLoss: true,
        profitThreshold: 50, // دولار
        lossThreshold: 25, // دولار
        weeklySummary: true,
        monthlyReport: true,
    });

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [hasChanges, setHasChanges] = useState(false);
    const [originalSettings, setOriginalSettings] = useState(null);

    // ✅ إصلاح Race Conditions
    const isMountedRef = useRef(true);

    useEffect(() => {
        isMountedRef.current = true;
        loadSettings();
        return () => {
            isMountedRef.current = false;
        };
    }, []);

    // ✅ معالجة زر الرجوع - تأكيد إذا كانت هناك تغييرات غير محفوظة
    useBackHandler(() => {
        if (hasChanges) {
            AlertService.confirm(
                'تنبيه',
                'لديك تغييرات غير محفوظة. هل تريد المغادرة بدون حفظ؟',
                () => navigation.goBack(),
                () => { }
            );
            return true;
        }
        navigation.goBack();
        return true;
    });

    const loadSettings = useCallback(async () => {
        if (!user?.id || !isMountedRef.current) { return; }

        try {
            if (isMountedRef.current) {
                setLoading(true);
            }

            // تهيئة خدمة قاعدة البيانات
            await DatabaseApiService.initialize();

            const notificationData = await DatabaseApiService.getNotificationSettings(user.id);
            if (notificationData?.success && notificationData?.data) {
                setSettings(notificationData.data);
                setOriginalSettings(notificationData.data);
                setHasChanges(false);
            }
        } catch (error) {
            console.error('[ERROR] خطأ في تحميل الإعدادات:', error);
            // لا نعرض خطأ للمستخدم، نستخدم القيم الافتراضية
        } finally {
            if (isMountedRef.current) {
                setLoading(false);
            }
        }
    }, [user]);

    const handleSaveSettings = async () => {
        if (!user?.id) { return; }

        try {
            setSaving(true);
            const response = await DatabaseApiService.updateNotificationSettings(user.id, settings);

            if (response?.success) {
                setOriginalSettings(settings);
                setHasChanges(false);
                ToastService.showSuccess('تم حفظ تفضيلات الإشعارات بنجاح');
                setTimeout(() => navigation?.goBack(), 1000);
            } else {
                ToastService.showError('فشل حفظ الإعدادات');
            }
        } catch (error) {
            console.error('[ERROR] خطأ في حفظ الإعدادات:', error);

            let errorMessage = 'فشل حفظ إعدادات الإشعارات';
            if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
                errorMessage = 'انتهى وقت الانتظار. يرجى المحاولة مرة أخرى';
            } else if (error?.code === 'ERR_NETWORK' || error?.message?.includes('Network Error')) {
                errorMessage = 'فشل الاتصال بالخادم. تحقق من اتصالك بالإنترنت';
            }

            ToastService.showError(errorMessage);
        } finally {
            setSaving(false);
        }
    };

    const updateSetting = (key, value) => {
        setSettings(prev => ({ ...prev, [key]: value }));
        setHasChanges(true);
    };

    if (loading) {
        return (
            <SafeAreaView style={styles.container}>
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color={theme.colors.primary} />
                </View>
            </SafeAreaView>
        );
    }

    return (
        <View style={styles.container}>
            <ScrollView contentContainerStyle={styles.scrollContent}>
                {/* قسم التحكم الرئيسي */}
                <ModernCard>
                    <Text style={styles.sectionHeader}>التحكم الرئيسي</Text>

                    <View style={styles.settingRow}>
                        <View style={styles.settingLabel}>
                            <Icon name="bell" size={24} color={theme.colors.primary} />
                            <View style={styles.labelText}>
                                <Text style={styles.settingTitle}>تفعيل الإشعارات</Text>
                                <Text style={styles.settingSubtitle}>تفعيل/تعطيل جميع الإشعارات</Text>
                            </View>
                        </View>
                        <Switch
                            value={settings.pushEnabled}
                            onValueChange={(val) => updateSetting('pushEnabled', val)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                            thumbColor={settings.pushEnabled ? theme.colors.success : theme.colors.textSecondary}
                        />
                    </View>
                </ModernCard>

                {/* قسم الصفقات */}
                <ModernCard>
                    <Text style={styles.sectionHeader}>إشعارات الصفقات</Text>

                    <View style={styles.settingRow}>
                        <View style={styles.settingLabel}>
                            <Icon name="plus-circle" size={24} color={theme.colors.info} />
                            <View style={styles.labelText}>
                                <Text style={styles.settingTitle}>صفقة جديدة</Text>
                                <Text style={styles.settingSubtitle}>عندما يفتح البوت صفقة جديدة</Text>
                            </View>
                        </View>
                        <Switch
                            value={settings.notifyNewDeal}
                            onValueChange={(val) => updateSetting('notifyNewDeal', val)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                            thumbColor={settings.notifyNewDeal ? theme.colors.success : theme.colors.textSecondary}
                            disabled={!settings.pushEnabled}
                        />
                    </View>

                    <View style={styles.divider} />

                    <View style={styles.settingRow}>
                        <View style={styles.settingLabel}>
                            <Icon name="trending-up" size={24} color={theme.colors.success} />
                            <View style={styles.labelText}>
                                <Text style={styles.settingTitle}>إغلاق بربح</Text>
                                <Text style={styles.settingSubtitle}>عند إغلاق صفقة بربح</Text>
                            </View>
                        </View>
                        <Switch
                            value={settings.notifyDealProfit}
                            onValueChange={(val) => updateSetting('notifyDealProfit', val)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                            thumbColor={settings.notifyDealProfit ? theme.colors.success : theme.colors.textSecondary}
                            disabled={!settings.pushEnabled}
                        />
                    </View>

                    <View style={styles.divider} />

                    <View style={styles.settingRow}>
                        <View style={styles.settingLabel}>
                            <Icon name="trending-down" size={24} color={theme.colors.error} />
                            <View style={styles.labelText}>
                                <Text style={styles.settingTitle}>إغلاق بخسارة</Text>
                                <Text style={styles.settingSubtitle}>عند إغلاق صفقة بخسارة أو وقف خسارة</Text>
                            </View>
                        </View>
                        <Switch
                            value={settings.notifyDealLoss}
                            onValueChange={(val) => updateSetting('notifyDealLoss', val)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                            thumbColor={settings.notifyDealLoss ? theme.colors.success : theme.colors.textSecondary}
                            disabled={!settings.pushEnabled}
                        />
                    </View>
                </ModernCard>

                {/* قسم المحفظة والملخصات */}
                <ModernCard>
                    <Text style={styles.sectionHeader}>المحفظة والتقارير</Text>

                    <View style={styles.settingRow}>
                        <View style={styles.settingLabel}>
                            <Icon name="dollar-sign" size={24} color={theme.colors.warning} />
                            <View style={styles.labelText}>
                                <Text style={styles.settingTitle}>انخفاض الرصيد</Text>
                                <Text style={styles.settingSubtitle}>تنبيه عند انخفاض الرصيد المتاح</Text>
                            </View>
                        </View>
                        <Switch
                            value={settings.notifyLowBalance}
                            onValueChange={(val) => updateSetting('notifyLowBalance', val)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                            thumbColor={settings.notifyLowBalance ? theme.colors.success : theme.colors.textSecondary}
                            disabled={!settings.pushEnabled}
                        />
                    </View>

                    <View style={styles.divider} />

                    <View style={styles.settingRow}>
                        <View style={styles.settingLabel}>
                            <Icon name="bar-chart-2" size={24} color={theme.colors.success} />
                            <View style={styles.labelText}>
                                <Text style={styles.settingTitle}>تقرير أرباح يومي</Text>
                                <Text style={styles.settingSubtitle}>ملخص يومي في حالة الربح</Text>
                            </View>
                        </View>
                        <Switch
                            value={settings.notifyDailyProfit}
                            onValueChange={(val) => updateSetting('notifyDailyProfit', val)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                            thumbColor={settings.notifyDailyProfit ? theme.colors.success : theme.colors.textSecondary}
                            disabled={!settings.pushEnabled}
                        />
                    </View>

                    <View style={styles.divider} />

                    <View style={styles.settingRow}>
                        <View style={styles.settingLabel}>
                            <Icon name="activity" size={24} color={theme.colors.textSecondary} />
                            <View style={styles.labelText}>
                                <Text style={styles.settingTitle}>تقرير خسائر يومي</Text>
                                <Text style={styles.settingSubtitle}>ملخص يومي في حالة الخسارة</Text>
                            </View>
                        </View>
                        <Switch
                            value={settings.notifyDailyLoss}
                            onValueChange={(val) => updateSetting('notifyDailyLoss', val)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                            thumbColor={settings.notifyDailyLoss ? theme.colors.success : theme.colors.textSecondary}
                            disabled={!settings.pushEnabled}
                        />
                    </View>
                </ModernCard>

                {/* قسم النظام والأمان */}
                <ModernCard>
                    <Text style={styles.sectionHeader}>النظام والأمان</Text>

                    <View style={styles.settingRow}>
                        <View style={styles.settingLabel}>
                            <Icon name="shield" size={24} color={theme.colors.warning} />
                            <View style={styles.labelText}>
                                <Text style={styles.settingTitle}>تنبيهات الأمان</Text>
                                <Text style={styles.settingSubtitle}>تغيير كلمة المرور، تسجيل دخول مشبوه</Text>
                            </View>
                        </View>
                        <Switch
                            value={settings.notifySecurityAlerts}
                            onValueChange={(val) => updateSetting('notifySecurityAlerts', val)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                            thumbColor={settings.notifySecurityAlerts ? theme.colors.success : theme.colors.textSecondary}
                            disabled={!settings.pushEnabled}
                        />
                    </View>

                    <View style={styles.divider} />

                    <View style={styles.settingRow}>
                        <View style={styles.settingLabel}>
                            <Icon name="settings" size={24} color={theme.colors.info} />
                            <View style={styles.labelText}>
                                <Text style={styles.settingTitle}>حالة النظام</Text>
                                <Text style={styles.settingSubtitle}>تحديثات حالة النظام والصيانة</Text>
                            </View>
                        </View>
                        <Switch
                            value={settings.notifySystemStatus}
                            onValueChange={(val) => updateSetting('notifySystemStatus', val)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                            thumbColor={settings.notifySystemStatus ? theme.colors.success : theme.colors.textSecondary}
                            disabled={!settings.pushEnabled}
                        />
                    </View>

                    <View style={styles.divider} />

                    <View style={styles.settingRow}>
                        <View style={styles.settingLabel}>
                            <Icon name="tool" size={24} color={theme.colors.secondary} />
                            <View style={styles.labelText}>
                                <Text style={styles.settingTitle}>إشعارات الصيانة</Text>
                                <Text style={styles.settingSubtitle}>تنبيهات الصيانة والتحديثات</Text>
                            </View>
                        </View>
                        <Switch
                            value={settings.notifyMaintenance}
                            onValueChange={(val) => updateSetting('notifyMaintenance', val)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                            thumbColor={settings.notifyMaintenance ? theme.colors.success : theme.colors.textSecondary}
                            disabled={!settings.pushEnabled}
                        />
                    </View>
                </ModernCard>

                {/* قسم التقارير الدورية */}
                <ModernCard>
                    <Text style={styles.sectionHeader}>التقارير الدورية</Text>

                    <View style={styles.settingRow}>
                        <View style={styles.settingLabel}>
                            <Icon name="calendar" size={24} color={theme.colors.primary} />
                            <View style={styles.labelText}>
                                <Text style={styles.settingTitle}>التقرير الأسبوعي</Text>
                                <Text style={styles.settingSubtitle}>ملخص أداء أسبوعي كل يوم أحد</Text>
                            </View>
                        </View>
                        <Switch
                            value={settings.weeklySummary}
                            onValueChange={(val) => updateSetting('weeklySummary', val)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                            thumbColor={settings.weeklySummary ? theme.colors.success : theme.colors.textSecondary}
                            disabled={!settings.pushEnabled}
                        />
                    </View>

                    <View style={styles.divider} />

                    <View style={styles.settingRow}>
                        <View style={styles.settingLabel}>
                            <Icon name="file-text" size={24} color={theme.colors.secondary} />
                            <View style={styles.labelText}>
                                <Text style={styles.settingTitle}>التقرير الشهري</Text>
                                <Text style={styles.settingSubtitle}>تقرير مفصل في نهاية كل شهر</Text>
                            </View>
                        </View>
                        <Switch
                            value={settings.monthlyReport}
                            onValueChange={(val) => updateSetting('monthlyReport', val)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                            thumbColor={settings.monthlyReport ? theme.colors.success : theme.colors.textSecondary}
                            disabled={!settings.pushEnabled}
                        />
                    </View>
                </ModernCard>

                {/* قسم الإعدادات المتقدمة */}
                <ModernCard>
                    <Text style={styles.sectionHeader}>الإعدادات المتقدمة</Text>

                    <View style={styles.settingRow}>
                        <View style={styles.settingLabel}>
                            <Icon name="moon" size={24} color={theme.colors.textSecondary} />
                            <View style={styles.labelText}>
                                <Text style={styles.settingTitle}>الساعات الهادئة</Text>
                                <Text style={styles.settingSubtitle}>تعطيل الإشعارات خلال فترة محددة</Text>
                            </View>
                        </View>
                        <Switch
                            value={settings.quietHoursEnabled}
                            onValueChange={(val) => updateSetting('quietHoursEnabled', val)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                            thumbColor={settings.quietHoursEnabled ? theme.colors.success : theme.colors.textSecondary}
                            disabled={!settings.pushEnabled}
                        />
                    </View>

                    {settings.quietHoursEnabled && (
                        <>
                            <View style={styles.divider} />
                            <View style={styles.timeSettings}>
                                <Text style={styles.timeLabel}>من: {settings.quietHoursStart}</Text>
                                <Text style={styles.timeLabel}>إلى: {settings.quietHoursEnd}</Text>
                            </View>
                        </>
                    )}

                    <View style={styles.divider} />

                    <View style={styles.settingRow}>
                        <View style={styles.settingLabel}>
                            <Icon name="trending-up" size={24} color={theme.colors.success} />
                            <View style={styles.labelText}>
                                <Text style={styles.settingTitle}>تنبيهات الأرباح الكبيرة</Text>
                                <Text style={styles.settingSubtitle}>إشعار عند تجاوز حد معين</Text>
                            </View>
                        </View>
                        <Switch
                            value={settings.notifyLargeProfit}
                            onValueChange={(val) => updateSetting('notifyLargeProfit', val)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                            thumbColor={settings.notifyLargeProfit ? theme.colors.success : theme.colors.textSecondary}
                            disabled={!settings.pushEnabled}
                        />
                    </View>

                    <View style={styles.divider} />

                    <View style={styles.settingRow}>
                        <View style={styles.settingLabel}>
                            <Icon name="trending-down" size={24} color={theme.colors.error} />
                            <View style={styles.labelText}>
                                <Text style={styles.settingTitle}>تنبيهات الخسائر الكبيرة</Text>
                                <Text style={styles.settingSubtitle}>إشعار عند تجاوز حد معين</Text>
                            </View>
                        </View>
                        <Switch
                            value={settings.notifyLargeLoss}
                            onValueChange={(val) => updateSetting('notifyLargeLoss', val)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary }}
                            thumbColor={settings.notifyLargeLoss ? theme.colors.success : theme.colors.textSecondary}
                            disabled={!settings.pushEnabled}
                        />
                    </View>

                    {(settings.notifyLargeProfit || settings.notifyLargeLoss) && (
                        <>
                            <View style={styles.divider} />
                            <View style={styles.thresholdSettings}>
                                <Text style={styles.thresholdLabel}>
                                    حد الربح: ${settings.profitThreshold}
                                </Text>
                                <Text style={styles.thresholdLabel}>
                                    حد الخسارة: ${settings.lossThreshold}
                                </Text>
                            </View>
                        </>
                    )}
                </ModernCard>
                <TouchableOpacity
                    style={[styles.saveButton, saving && styles.saveButtonDisabled]}
                    onPress={handleSaveSettings}
                    disabled={saving}
                    activeOpacity={0.8}
                >
                    <Text style={styles.saveButtonText}>
                        {saving ? 'جاري الحفظ...' : 'حفظ التغييرات'}
                    </Text>
                </TouchableOpacity>
            </ScrollView>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    scrollContent: {
        padding: theme.spacing.lg,
        paddingBottom: theme.spacing.xl,
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    // L2: عنوان القسم
    sectionHeader: {
        ...theme.hierarchy.secondary,
        color: theme.colors.primary,
        marginBottom: theme.spacing.md,
        textAlign: 'left',
    },
    settingRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: theme.spacing.sm,
    },
    settingLabel: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: theme.spacing.md,
        flex: 1,
    },
    labelText: {
        flex: 1,
    },
    // L3: عنوان الإعداد
    settingTitle: {
        ...theme.hierarchy.body,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 4,
    },
    // L5: وصف الإعداد
    settingSubtitle: {
        ...theme.hierarchy.tiny,
        color: theme.colors.textSecondary,
    },
    divider: {
        height: 1,
        backgroundColor: theme.colors.border,
        marginVertical: theme.spacing.md,
        opacity: 0.5,
    },
    saveButton: {
        backgroundColor: theme.colors.primary,
        paddingVertical: 14,
        paddingHorizontal: 24,
        borderRadius: 12,
        alignItems: 'center',
        marginTop: theme.spacing.lg,
    },
    saveButtonDisabled: {
        opacity: 0.6,
    },
    saveButtonText: {
        color: theme.colors.text,
        fontSize: 16,
        fontWeight: '600',
    },
});

export default ImprovedNotificationSettingsScreen;
