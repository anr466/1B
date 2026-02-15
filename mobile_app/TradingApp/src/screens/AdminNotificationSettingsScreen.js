/**
 * شاشة إعدادات إشعارات الأدمن
 * ✅ Telegram Bot
 * ✅ Webhook
 * ✅ Email
 * ✅ اختبار الإشعارات
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
    View,
    Text,
    StyleSheet,
    ScrollView,
    Switch,
    TouchableOpacity,
    ActivityIndicator,
    Alert,
    RefreshControl,
} from 'react-native';
import { theme } from '../theme/theme';
import ModernCard from '../components/ModernCard';
import ModernButton from '../components/ModernButton';
import ModernInput from '../components/ModernInput';
import DatabaseApiService from '../services/DatabaseApiService';
import ToastService from '../services/ToastService';
import { useBackHandler } from '../utils/BackHandlerUtil';
// ✅ GlobalHeader يأتي من Navigator

const AdminNotificationSettingsScreen = () => {
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [testing, setTesting] = useState(false);
    const [refreshing, setRefreshing] = useState(false);

    // الإعدادات
    const [settings, setSettings] = useState({
        telegram_enabled: false,
        telegram_bot_token: '',
        telegram_chat_id: '',
        email_enabled: false,
        admin_email: '',
        webhook_enabled: false,
        webhook_url: '',
        push_enabled: true,
        notify_on_error: true,
        notify_on_trade: true,
        notify_on_warning: true,
    });

    const [unreadCount, setUnreadCount] = useState(0);

    // ✅ إصلاح Race Conditions
    const isMountedRef = useRef(true);

    useEffect(() => {
        isMountedRef.current = true;
        loadSettings();
        return () => {
            isMountedRef.current = false;
        };
    }, []);

    const loadSettings = useCallback(async () => {
        if (!isMountedRef.current) {return;}
        try {
            if (isMountedRef.current) {
                setLoading(true);
            }
            const response = await DatabaseApiService.request('/admin/notification-settings', 'GET');

            if (response?.success && response.data) {
                setSettings(prev => ({
                    ...prev,
                    ...response.data,
                }));
                setUnreadCount(response.data.unread_count || 0);
            }
        } catch (error) {
            const errorMsg = error?.response?.data?.error || error?.message || 'فشل تحميل الإعدادات';
            ToastService.showError(errorMsg);
        } finally {
            if (isMountedRef.current) {
                setLoading(false);
            }
        }
    }, []);

    const onRefresh = useCallback(async () => {
        if (!isMountedRef.current) {return;}
        if (isMountedRef.current) {
            setRefreshing(true);
        }
        await loadSettings();
        if (isMountedRef.current) {
            setRefreshing(false);
        }
    }, [loadSettings]);

    const saveSettings = async () => {
        try {
            setSaving(true);
            const response = await DatabaseApiService.request('/admin/notification-settings', 'PUT', settings);

            if (response?.success) {
                ToastService.showSuccess('تم حفظ الإعدادات');
            } else {
                ToastService.showError(response?.message || 'فشل الحفظ');
            }
        } catch (error) {
            const errorMsg = error?.response?.data?.error || error?.message || 'فشل حفظ الإعدادات';
            ToastService.showError(errorMsg);
        } finally {
            setSaving(false);
        }
    };

    const testNotification = async () => {
        try {
            setTesting(true);
            const response = await DatabaseApiService.request('/admin/notification-settings/test', 'POST');

            if (response?.success) {
                ToastService.showSuccess('تم إرسال الإشعار الاختباري');
            } else {
                ToastService.showError(response?.message || 'فشل الإرسال');
            }
        } catch (error) {
            const errorMsg = error?.response?.data?.error || error?.message || 'فشل إرسال الإشعار';
            ToastService.showError(errorMsg);
        } finally {
            setTesting(false);
        }
    };

    const updateSetting = (key, value) => {
        setSettings(prev => ({ ...prev, [key]: value }));
    };

    if (loading) {
        return (
            <View style={styles.loadingContainer}>
                <ActivityIndicator size="large" color={theme.colors.primary} />
            </View>
        );
    }

    return (
        <View style={styles.container}>
            <ScrollView
                contentContainerStyle={styles.scrollContent}
                refreshControl={
                    <RefreshControl
                        refreshing={refreshing}
                        onRefresh={onRefresh}
                        tintColor={theme.colors.primary}
                    />
                }
            >
                {/* عداد الإشعارات */}
                {unreadCount > 0 && (
                    <ModernCard variant="warning" style={styles.alertCard}>
                        <Text style={styles.alertText}>
                            📬 لديك {unreadCount} إشعار غير مقروء
                        </Text>
                    </ModernCard>
                )}

                {/* ═══════════════ Telegram ═══════════════ */}
                <ModernCard style={styles.card}>
                    <View style={styles.cardHeader}>
                        <Text style={styles.cardIcon}>📱</Text>
                        <Text style={styles.cardTitle}>Telegram Bot</Text>
                        <Switch
                            value={settings.telegram_enabled}
                            onValueChange={(v) => updateSetting('telegram_enabled', v)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary + '80' }}
                            thumbColor={settings.telegram_enabled ? theme.colors.primary : theme.colors.textSecondary}
                        />
                    </View>

                    {settings.telegram_enabled && (
                        <View style={styles.inputsContainer}>
                            <ModernInput
                                label="Bot Token"
                                value={settings.telegram_bot_token}
                                onChangeText={(v) => updateSetting('telegram_bot_token', v)}
                                placeholder="123456789:ABCdefGHI..."
                                autoCapitalize="none"
                                autoCorrect={false}
                            />

                            <ModernInput
                                label="Chat ID"
                                value={settings.telegram_chat_id}
                                onChangeText={(v) => updateSetting('telegram_chat_id', v)}
                                placeholder="-1001234567890"
                                keyboardType="numeric"
                                helperText="💡 أنشئ Bot من @BotFather واحصل على Chat ID من @userinfobot"
                            />
                        </View>
                    )}
                </ModernCard>

                {/* ═══════════════ Webhook ═══════════════ */}
                <ModernCard style={styles.card}>
                    <View style={styles.cardHeader}>
                        <Text style={styles.cardIcon}>🔗</Text>
                        <Text style={styles.cardTitle}>Webhook</Text>
                        <Switch
                            value={settings.webhook_enabled}
                            onValueChange={(v) => updateSetting('webhook_enabled', v)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary + '80' }}
                            thumbColor={settings.webhook_enabled ? theme.colors.primary : theme.colors.textSecondary}
                        />
                    </View>

                    {settings.webhook_enabled && (
                        <View style={styles.inputsContainer}>
                            <ModernInput
                                label="Webhook URL"
                                value={settings.webhook_url}
                                onChangeText={(v) => updateSetting('webhook_url', v)}
                                placeholder="https://your-server.com/webhook"
                                autoCapitalize="none"
                                autoCorrect={false}
                                keyboardType="url"
                                helperText="💡 سيتم إرسال POST request مع JSON payload"
                            />
                        </View>
                    )}
                </ModernCard>

                {/* ═══════════════ Email ═══════════════ */}
                <ModernCard style={styles.card}>
                    <View style={styles.cardHeader}>
                        <Text style={styles.cardIcon}>📧</Text>
                        <Text style={styles.cardTitle}>Email</Text>
                        <Switch
                            value={settings.email_enabled}
                            onValueChange={(v) => updateSetting('email_enabled', v)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary + '80' }}
                            thumbColor={settings.email_enabled ? theme.colors.primary : theme.colors.textSecondary}
                        />
                    </View>

                    {settings.email_enabled && (
                        <View style={styles.inputsContainer}>
                            <ModernInput
                                label="البريد الإلكتروني"
                                value={settings.admin_email}
                                onChangeText={(v) => updateSetting('admin_email', v)}
                                placeholder="admin@example.com"
                                autoCapitalize="none"
                                autoCorrect={false}
                                keyboardType="email-address"
                                helperText="⚠️ يتطلب إعداد SMTP على الخادم"
                            />
                        </View>
                    )}
                </ModernCard>

                {/* ═══════════════ أنواع الإشعارات ═══════════════ */}
                <ModernCard style={styles.card}>
                    <Text style={styles.sectionTitle}>📋 أنواع الإشعارات</Text>

                    <View style={styles.toggleRow}>
                        <View style={styles.toggleInfo}>
                            <Text style={styles.toggleIcon}>🚨</Text>
                            <Text style={styles.toggleLabel}>الأخطاء الحرجة</Text>
                        </View>
                        <Switch
                            value={settings.notify_on_error}
                            onValueChange={(v) => updateSetting('notify_on_error', v)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.error + '80' }}
                            thumbColor={settings.notify_on_error ? theme.colors.error : theme.colors.textSecondary}
                        />
                    </View>

                    <View style={styles.toggleRow}>
                        <View style={styles.toggleInfo}>
                            <Text style={styles.toggleIcon}>⚠️</Text>
                            <Text style={styles.toggleLabel}>التحذيرات</Text>
                        </View>
                        <Switch
                            value={settings.notify_on_warning}
                            onValueChange={(v) => updateSetting('notify_on_warning', v)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.warning + '80' }}
                            thumbColor={settings.notify_on_warning ? theme.colors.warning : theme.colors.textSecondary}
                        />
                    </View>

                    <View style={styles.toggleRow}>
                        <View style={styles.toggleInfo}>
                            <Text style={styles.toggleIcon}>💰</Text>
                            <Text style={styles.toggleLabel}>الصفقات</Text>
                        </View>
                        <Switch
                            value={settings.notify_on_trade}
                            onValueChange={(v) => updateSetting('notify_on_trade', v)}
                            trackColor={{ false: theme.colors.border, true: theme.colors.success + '80' }}
                            thumbColor={settings.notify_on_trade ? theme.colors.success : theme.colors.textSecondary}
                        />
                    </View>
                </ModernCard>

                {/* ═══════════════ الأزرار ═══════════════ */}
                <View style={styles.buttonsContainer}>
                    <ModernButton
                        title={saving ? 'جاري الحفظ...' : '💾 حفظ الإعدادات'}
                        onPress={saveSettings}
                        variant="primary"
                        size="large"
                        fullWidth
                        disabled={saving}
                    />

                    <ModernButton
                        title={testing ? 'جاري الإرسال...' : '🧪 اختبار الإشعارات'}
                        onPress={testNotification}
                        variant="outline"
                        size="medium"
                        fullWidth
                        disabled={testing}
                        style={{ marginTop: 12 }}
                    />
                </View>

                <View style={{ height: 40 }} />
            </ScrollView>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: theme.colors.background,
    },
    scrollContent: {
        padding: 16,
    },
    alertCard: {
        marginBottom: 16,
    },
    alertText: {
        fontSize: 14,
        color: theme.colors.warning,
        textAlign: 'center',
    },
    card: {
        marginBottom: 16,
    },
    cardHeader: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    cardIcon: {
        fontSize: 24,
        marginRight: 12,
    },
    cardTitle: {
        flex: 1,
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
    },
    inputsContainer: {
        marginTop: 16,
        paddingTop: 16,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
    },
    sectionTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 16,
    },
    toggleRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    toggleInfo: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    toggleIcon: {
        fontSize: 20,
        marginRight: 12,
    },
    toggleLabel: {
        fontSize: 14,
        color: theme.colors.text,
    },
    buttonsContainer: {
        marginTop: 8,
    },
});

export default AdminNotificationSettingsScreen;
