/**
 * Trading Settings Screen - شاشة إعدادات التداول
 * إدارة إعدادات التداول الأساسية
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
    View,
    Text,
    ScrollView,
    StyleSheet,
    Switch,
    TouchableOpacity,
    ActivityIndicator,
    Alert,
    Animated,
} from 'react-native';
import CustomSlider from '../components/CustomSlider';
import AsyncStorage from '@react-native-async-storage/async-storage';
import DatabaseApiService from '../services/DatabaseApiService';
import { theme } from '../theme/theme';
import ToastService from '../services/ToastService';
import ModernCard from '../components/ModernCard';
import Icon from '../components/CustomIcons';
import useIsAdmin from '../hooks/useIsAdmin';
import { useTradingModeContext } from '../context/TradingModeContext';
import AdminModeBanner from '../components/AdminModeBanner';
import { TradingSettingsSkeleton } from '../components/SkeletonLoader';
import { HelpIcon, LabelWithTooltip } from '../components/Tooltip';
import TradingValidationInfo from '../components/TradingValidationInfo';
import { hapticLight, hapticSuccess, hapticSelection, hapticWarning, hapticError, hapticMedium } from '../utils/HapticFeedback';
import { useBackHandler } from '../utils/BackHandlerUtil';
import { SafeAreaView } from 'react-native-safe-area-context';
import { AlertService } from '../components/CustomAlert';

// ✅ تم تبسيط الشاشة - فقط مبلغ الصفقة وعدد الصفقات المتزامنة

const TradingSettingsScreen = ({ navigation, user, onBack }) => {
    const isAdmin = useIsAdmin(user);
    const {
        tradingMode,
        refreshCounter,
        getModeText,
        getModeColor,
        isAdmin: contextIsAdmin,
        getCurrentViewMode,
    } = useTradingModeContext();

    const currentViewMode = getCurrentViewMode();

    const [settings, setSettings] = useState({
        position_size_percentage: 12.0,  // نسبة من الرصيد (5-20%)
        max_positions: 5,
        trading_enabled: false,
    });
    const [togglingTrading, setTogglingTrading] = useState(false);

    const [portfolioBalance, setPortfolioBalance] = useState(0); // رصيد المحفظة لحساب حجم الصفقة

    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [hasChanges, setHasChanges] = useState(false);
    const [originalSettings, setOriginalSettings] = useState(null);
    const [showAdvanced, setShowAdvanced] = useState(false);

    const isMountedRef = useRef(true);

    useEffect(() => {
        isMountedRef.current = true;
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
                () => onBack && onBack(),
                () => { }
            );
            return true; // منع الرجوع الافتراضي
        }
        onBack && onBack();
        return true;
    });

    const loadSettings = useCallback(async () => {
        if (!isMountedRef.current) { return; }

        try {
            if (isMountedRef.current) {
                setLoading(true);
            }

            if (!user?.id) {
                if (isMountedRef.current) {
                    setOriginalSettings(settings);
                    setLoading(false);
                }
                return;
            }

            const cachedSettings = await AsyncStorage.getItem(`trading_settings_${user.id}`);
            if (cachedSettings && isMountedRef.current) {
                try {
                    const parsed = JSON.parse(cachedSettings);
                    setSettings(parsed);
                    setOriginalSettings(parsed);
                } catch (parseError) {
                    console.warn('[CRASH_PREVENTION] فشل تحليل إعدادات التداول المخزنة:', parseError);
                    // استمر بدون الإعدادات المخزنة - سيتم جلبها من الخادم
                }
            }

            const authToken = await AsyncStorage.getItem('authToken');
            if (!authToken) {
                if (isMountedRef.current) {
                    setLoading(false);
                }
                return;
            }

            if (!isMountedRef.current) { return; }

            await DatabaseApiService.initialize();

            if (!isMountedRef.current) { return; }

            const apiData = await DatabaseApiService.getSettings(
                user.id,
                isAdmin ? currentViewMode : null
            );

            if (!isMountedRef.current) { return; }

            if (apiData?.success && apiData?.data) {
                const apiSettings = apiData.data;
                const newSettings = {
                    position_size_percentage: apiSettings.positionSizePercentage || apiSettings.position_size_percentage || 12.0,
                    max_positions: apiSettings.maxConcurrentTrades || apiSettings.max_positions || 5,
                    trading_enabled: apiSettings.tradingEnabled ?? apiSettings.trading_enabled ?? false,
                };
                // 📊 جلب رصيد المحفظة لعرض حجم الصفقة المتوقع
                try {
                    const portfolioData = await DatabaseApiService.getPortfolio(user.id);
                    if (portfolioData?.success && portfolioData?.data) {
                        setPortfolioBalance(portfolioData.data.available_balance || portfolioData.data.balance || 0);
                    }
                } catch (err) {
                    console.log('Could not fetch portfolio balance');
                }
                if (isMountedRef.current) {
                    setSettings(newSettings);
                    setOriginalSettings(newSettings);
                    await AsyncStorage.setItem(
                        `trading_settings_${user.id}`,
                        JSON.stringify(newSettings)
                    );
                }
            }
        } catch (error) {
            console.error('[ERROR] خطأ في تحميل الإعدادات:', error);
        } finally {
            if (isMountedRef.current) {
                setLoading(false);
            }
        }
    }, [user, currentViewMode, isAdmin]);

    useEffect(() => {
        loadSettings();
    }, [loadSettings]);

    useEffect(() => {
        if (refreshCounter > 0) {
            const delay = Math.random() * 500 + 500;
            const timer = setTimeout(() => {
                loadSettings();
            }, delay);
            return () => clearTimeout(timer);
        }
    }, [refreshCounter, loadSettings]);

    const saveSettings = useCallback(async () => {
        if (!isMountedRef.current) { return; }

        try {
            if (isMountedRef.current) {
                setSaving(true);
            }
            hapticMedium();

            const apiSettings = {
                positionSizePercentage: settings.position_size_percentage,
                maxConcurrentTrades: settings.max_positions,
                tradingEnabled: settings.trading_enabled, // يرسل الحالة الحالية بدون تغيير
            };

            const response = await DatabaseApiService.updateSettings(user?.id, apiSettings);

            if (!isMountedRef.current) { return; }

            if (response?.success) {
                await AsyncStorage.setItem(
                    `trading_settings_${user?.id}`,
                    JSON.stringify(settings)
                );
                if (isMountedRef.current) {
                    setOriginalSettings(settings);
                    setHasChanges(false);
                    ToastService.showSuccess('تم حفظ الإعدادات بنجاح\n\n⏱️ سيتم تطبيقها في الدورة القادمة (~60 ثانية)');
                    hapticSuccess();
                }
            } else {
                if (isMountedRef.current) {
                    ToastService.showError(response?.message || 'فشل حفظ الإعدادات');
                    hapticError();
                }
            }
        } catch (error) {
            console.error('[ERROR] خطأ في حفظ الإعدادات:', error);
            if (isMountedRef.current) {
                let errorMessage = 'فشل حفظ الإعدادات';
                if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
                    errorMessage = 'انتهى وقت الانتظار. يرجى المحاولة مرة أخرى';
                } else if (error?.code === 'ERR_NETWORK' || error?.message?.includes('Network Error')) {
                    errorMessage = 'فشل الاتصال بالخادم. تحقق من اتصالك بالإنترنت';
                }
                ToastService.showError(errorMessage);
                hapticError();
            }
        } finally {
            if (isMountedRef.current) {
                setSaving(false);
            }
        }
    }, [user, settings]);

    const handleSettingChange = useCallback((key, value) => {
        setSettings(prev => ({ ...prev, [key]: value }));
        setHasChanges(true);
        hapticLight();
    }, []);

    const handleReset = useCallback(() => {
        if (originalSettings) {
            setSettings(originalSettings);
            setHasChanges(false);
            hapticSelection();
        }
    }, [originalSettings]);

    // ✅ تفعيل/تعطيل التداول — منفصل عن حفظ الإعدادات
    // الباكند يتحقق من: الإعدادات محفوظة + الرصيد + Binance keys
    const toggleTrading = useCallback(async (newValue) => {
        if (!isMountedRef.current || togglingTrading) return;

        // عند التفعيل: تأكيد من المستخدم
        if (newValue) {
            AlertService.confirm(
                'تفعيل التداول',
                'هل تريد السماح للنظام بالتداول باستخدام إعداداتك الحالية؟\n\n• نسبة الصفقة: ' + settings.position_size_percentage + '%\n• أقصى صفقات: ' + settings.max_positions,
                async () => {
                    await _executeToggle(true);
                },
                () => { } // إلغاء
            );
        } else {
            // عند التعطيل: تنفيذ مباشر
            await _executeToggle(false);
        }
    }, [settings, togglingTrading]);

    const _executeToggle = useCallback(async (enable) => {
        if (!isMountedRef.current) return;
        try {
            setTogglingTrading(true);
            hapticMedium();

            const apiSettings = {
                positionSizePercentage: settings.position_size_percentage,
                maxConcurrentTrades: settings.max_positions,
                tradingEnabled: enable,
            };

            const response = await DatabaseApiService.updateSettings(user?.id, apiSettings);

            if (!isMountedRef.current) return;

            if (response?.success) {
                const newSettings = { ...settings, trading_enabled: enable };
                setSettings(newSettings);
                setOriginalSettings(newSettings);
                await AsyncStorage.setItem(
                    `trading_settings_${user?.id}`,
                    JSON.stringify(newSettings)
                );
                if (enable) {
                    ToastService.showSuccess('✅ تم تفعيل التداول\nالنظام سيبدأ التداول في الدورة القادمة (~60 ثانية)');
                    hapticSuccess();
                } else {
                    ToastService.showInfo('⏸ تم تعطيل التداول\nلن يتم فتح صفقات جديدة. الصفقات المفتوحة ستستمر في المراقبة.');
                    hapticSelection();
                }
            } else {
                // الباكند رفض التفعيل (رصيد غير كافي / لا مفاتيح Binance / إلخ)
                const errorMsg = response?.message || response?.error || 'فشل تفعيل التداول';
                ToastService.showError(errorMsg);
                hapticError();
            }
        } catch (error) {
            console.error('[ERROR] خطأ في تبديل التداول:', error);
            if (isMountedRef.current) {
                const errData = error?.response?.data;
                const errorMsg = errData?.message || errData?.error || 'فشل تبديل حالة التداول';
                ToastService.showError(errorMsg);
                hapticError();
            }
        } finally {
            if (isMountedRef.current) {
                setTogglingTrading(false);
            }
        }
    }, [user, settings]);

    if (loading) {
        return (
            <SafeAreaView style={styles.container} edges={['top']}>
                <TradingSettingsSkeleton />
            </SafeAreaView>
        );
    }

    return (
        <SafeAreaView style={styles.container} edges={['top']}>
            <ScrollView
                style={styles.scrollView}
                contentContainerStyle={styles.scrollContent}
                showsVerticalScrollIndicator={false}
            >
                {/* ✅ بانر وضع التداول للأدمن */}
                {isAdmin && currentViewMode === 'demo' && (
                    <AdminModeBanner style={{ marginHorizontal: 0, marginBottom: 16 }} />
                )}

                {/* ✅ بانر تحذير للتداول الحقيقي */}
                {currentViewMode === 'real' && (
                    <ModernCard variant="warning" style={styles.card}>
                        <View style={styles.infoBannerHeader}>
                            <Icon name="alert-triangle" size={24} color={theme.colors.warning} />
                            <Text style={[styles.infoBannerTitle, { color: theme.colors.warning }]}>
                                ⚠️ تداول حقيقي
                            </Text>
                        </View>
                        <Text style={styles.infoBannerText}>
                            هذه الإعدادات تؤثر على أموالك الحقيقية
                        </Text>
                    </ModernCard>
                )}

                {/* ✅ نسبة حجم الصفقة من الرصيد */}
                <ModernCard style={styles.card}>
                    <View style={styles.settingHeader}>
                        <Icon name="percent" size={22} color={theme.colors.primary} />
                        <Text style={styles.settingTitle}>نسبة حجم الصفقة</Text>
                    </View>
                    <Text style={styles.settingDescription}>
                        نسبة الرصيد المخصصة لكل صفقة من رصيدك المتاح
                    </Text>
                    <View style={styles.valueDisplay}>
                        <Text style={styles.valueText}>{settings.position_size_percentage}</Text>
                        <Text style={styles.valueUnit}>%</Text>
                    </View>
                    <CustomSlider
                        value={settings.position_size_percentage}
                        onValueChange={(val) => handleSettingChange('position_size_percentage', val)}
                        minimumValue={5}
                        maximumValue={20}
                        step={1}
                        unit="%"
                    />
                    {portfolioBalance > 0 && (
                        <Text style={styles.calculationText}>
                            📊 حجم الصفقة = {portfolioBalance.toFixed(0)} USDT × {settings.position_size_percentage}% = {(portfolioBalance * settings.position_size_percentage / 100).toFixed(0)} USDT
                        </Text>
                    )}
                    <Text style={styles.helperText}>
                        💡 مثال: رصيد 1000 USDT × 10% = حجم صفقة 100 USDT
                    </Text>
                </ModernCard>

                {/* ✅ عدد الصفقات المتزامنة */}
                <ModernCard style={styles.card}>
                    <View style={styles.settingHeader}>
                        <Icon name="layers" size={22} color={theme.colors.primary} />
                        <Text style={styles.settingTitle}>عدد الصفقات المتزامنة</Text>
                    </View>
                    <Text style={styles.settingDescription}>
                        الحد الأقصى للصفقات المفتوحة في نفس الوقت
                    </Text>
                    <View style={styles.valueDisplay}>
                        <Text style={styles.valueText}>{settings.max_positions}</Text>
                        <Text style={styles.valueUnit}>صفقة</Text>
                    </View>
                    <CustomSlider
                        value={settings.max_positions}
                        onValueChange={(val) => handleSettingChange('max_positions', Math.round(val))}
                        minimumValue={1}
                        maximumValue={10}
                        step={1}
                        unit=""
                    />
                </ModernCard>

                {/* ═════ تفعيل/تعطيل التداول ═════ */}
                <ModernCard style={[styles.card, hasChanges && { opacity: 0.5 }]}>
                    <View style={styles.settingHeader}>
                        <Icon name={settings.trading_enabled ? 'toggle-right' : 'toggle-left'} size={22} color={settings.trading_enabled ? theme.colors.success : theme.colors.textSecondary} />
                        <Text style={styles.settingTitle}>تفعيل التداول</Text>
                    </View>
                    <Text style={styles.settingDescription}>
                        {'السماح للنظام بالتداول باستخدام إعداداتك المحفوظة'}
                    </Text>
                    <View style={styles.switchRow}>
                        <View style={styles.switchLabelContainer}>
                            <Text style={{ fontSize: 15, fontWeight: '600', color: settings.trading_enabled ? theme.colors.success : theme.colors.text }}>
                                {settings.trading_enabled ? 'التداول مفعل' : 'التداول معطل'}
                            </Text>
                            {hasChanges && (
                                <Text style={{ fontSize: 12, color: theme.colors.warning, marginTop: 4 }}>
                                    احفظ الإعدادات أولاً قبل تغيير حالة التداول
                                </Text>
                            )}
                        </View>
                        {togglingTrading ? (
                            <ActivityIndicator size="small" color={theme.colors.primary} />
                        ) : (
                            <Switch
                                value={settings.trading_enabled}
                                onValueChange={toggleTrading}
                                disabled={hasChanges || togglingTrading}
                                trackColor={{ false: theme.colors.border, true: theme.colors.success + '60' }}
                                thumbColor={settings.trading_enabled ? theme.colors.success : theme.colors.textSecondary}
                            />
                        )}
                    </View>
                </ModernCard>

                {hasChanges && (
                    <View style={styles.actionButtons}>
                        <TouchableOpacity
                            style={[styles.button, styles.resetButton]}
                            onPress={handleReset}
                            activeOpacity={0.8}
                        >
                            <Icon name="refresh" size={18} color={theme.colors.text} />
                            <Text style={styles.resetButtonText}>إعادة تعيين</Text>
                        </TouchableOpacity>

                        <TouchableOpacity
                            style={[
                                styles.button,
                                styles.saveButton,
                                { opacity: saving ? 0.6 : 1 }
                            ]}
                            onPress={saveSettings}
                            disabled={saving}
                            activeOpacity={0.8}
                        >
                            {saving ? (
                                <ActivityIndicator size="small" color={theme.colors.background} />
                            ) : (
                                <>
                                    <Icon name="check" size={18} color={theme.colors.background} />
                                    <Text style={styles.saveButtonText}>حفظ التغييرات</Text>
                                </>
                            )}
                        </TouchableOpacity>
                    </View>
                )}
            </ScrollView>
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    scrollView: {
        flex: 1,
    },
    scrollContent: {
        padding: 16,
        paddingBottom: 32,
    },
    card: {
        marginBottom: 16,
    },
    advancedButton: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 12,
        marginVertical: 8,
    },
    advancedButtonText: {
        color: theme.colors.primary,
        fontSize: 14,
        fontWeight: '600',
        marginStart: 8,
    },
    actionButtons: {
        flexDirection: 'row',
        gap: 12,
        marginTop: 24,
    },
    button: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 14,
        borderRadius: 12,
        gap: 8,
    },
    resetButton: {
        backgroundColor: theme.colors.card,
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    resetButtonText: {
        color: theme.colors.text,
        fontSize: 15,
        fontWeight: '600',
    },
    saveButton: {
        backgroundColor: theme.colors.primary,
    },
    saveButtonText: {
        color: theme.colors.background,
        fontSize: 15,
        fontWeight: '600',
    },
    switchRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    switchLabelContainer: {
        flex: 1,
        marginEnd: 12,
    },
    infoBanner: {
        backgroundColor: theme.colors.info + '15',
        borderLeftWidth: 4,
        borderLeftColor: theme.colors.info,
    },
    infoBannerHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 8,
    },
    infoBannerTitle: {
        fontSize: 16,
        fontWeight: '700',
        color: theme.colors.text,
        marginStart: 8,
    },
    infoBannerText: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        lineHeight: 20,
    },
    settingHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 8,
        gap: 10,
    },
    settingTitle: {
        fontSize: 18,
        fontWeight: '700',
        color: theme.colors.text,
    },
    settingDescription: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        marginBottom: 16,
    },
    valueDisplay: {
        flexDirection: 'row',
        alignItems: 'baseline',
        justifyContent: 'center',
        marginBottom: 12,
        gap: 6,
    },
    valueText: {
        fontSize: 36,
        fontWeight: '700',
        color: theme.colors.primary,
    },
    valueUnit: {
        fontSize: 16,
        fontWeight: '500',
        color: theme.colors.textSecondary,
    },
    calculationText: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.primary,
        textAlign: 'center',
        marginTop: 12,
        marginBottom: 4,
        backgroundColor: theme.colors.primary + '10',
        padding: 10,
        borderRadius: 8,
    },
    helperText: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginTop: 8,
        marginBottom: 4,
    },
    adaptiveInfoText: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.success,
        textAlign: 'center',
        marginTop: 8,
        marginBottom: 4,
    },
});

export default TradingSettingsScreen;
