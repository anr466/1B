import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, I18nManager, ActivityIndicator, Modal, Animated } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import LinearGradient from 'react-native-linear-gradient';
import { theme } from '../theme/theme';
import { useNavigation } from '@react-navigation/native';
import BrandIcon from './BrandIcons';
import UnifiedBrandLogo from './UnifiedBrandLogo';
import { useTradingModeContext } from '../context/TradingModeContext';
import { hapticLight, hapticWarning, hapticSuccess } from '../utils/HapticFeedback';
import { AlertService } from './CustomAlert';
import ToastService from '../services/ToastService';
import { TooltipContent } from './Tooltip';
import Logger from '../services/LoggerService';

// أيقونات مخصصة للـ Header
const ArrowLeftIcon = ({ size = 24, color = '#FFFFFF' }) => <BrandIcon name="arrow-back" size={size} color={color} />;
const ArrowRightIcon = ({ size = 24, color = '#FFFFFF' }) => <BrandIcon name="arrow-forward" size={size} color={color} />;
const NotificationIcon = ({ size = 24, color = '#FFFFFF' }) => <BrandIcon name="notification" size={size} color={color} />;

const isRTL = I18nManager.isRTL;

/**
 * البنر العلوي الموحد (Global Header)
 * ✅ تصميم جديد مستوحى من Stakent
 * ✅ تدرج بنفسجي أنيق
 */
const GlobalHeader = ({
    title,
    showBack = false,
    onBack,
    rightAction,
    showNotification = false,
    onNotificationPress,
    subtitle,
    variant = 'default', // 'default' | 'transparent' | 'gradient'
    showLogo = true,
    isAdminUser = false, // ✅ يمكن تمريره كـ prop
}) => {
    const insets = useSafeAreaInsets();
    const navigation = useNavigation();

    // ✅ وضع التداول للأدمن (يظهر في Header)
    const { isAdmin: contextIsAdmin, getCurrentViewMode, getModeColor, changeTradingMode, isLoading: modeLoading, hasBinanceKeys, tradingMode, userId } = useTradingModeContext();

    // ✅ استخدام isAdmin من Context فقط (مصدر واحد للحقيقة)
    const isAdmin = contextIsAdmin;
    const currentMode = getCurrentViewMode?.() || tradingMode || 'demo';
    const modeColor = getModeColor?.() || '#F59E0B';
    const [switching, setSwitching] = useState(false);
    const [showAutoTooltip, setShowAutoTooltip] = useState(false);
    const scaleAnim = React.useRef(new Animated.Value(0)).current;

    // ✅ فحص: يجب أن يكون المستخدم مسجل دخول لعرض الشارة
    const isUserLoggedIn = userId !== null && userId !== undefined;

    // ✅ تصحيح: تأكد من أن isAdmin محدث
    Logger.debug(`GlobalHeader - isAdmin: ${isAdmin}, mode: ${currentMode}, isLoggedIn: ${isUserLoggedIn}`, 'GlobalHeader');

    // ✅ Tooltip animation
    React.useEffect(() => {
        if (showAutoTooltip) {
            Animated.spring(scaleAnim, {
                toValue: 1,
                tension: 50,
                friction: 7,
                useNativeDriver: true,
            }).start();
        } else {
            Animated.timing(scaleAnim, {
                toValue: 0,
                duration: 150,
                useNativeDriver: true,
            }).start();
        }
    }, [showAutoTooltip]);

    // ✅ دالة تبديل الوضع للأدمن
    const handleToggleMode = async () => {
        console.log(`[GlobalHeader] handleToggleMode: isAdmin=${isAdmin}, switching=${switching}, modeLoading=${modeLoading}, currentMode=${currentMode}`);

        if (!isAdmin || switching || modeLoading) {
            console.log(`[GlobalHeader] Blocked: isAdmin=${isAdmin}, switching=${switching}, modeLoading=${modeLoading}`);
            return;
        }

        const newMode = currentMode === 'demo' ? 'real' : 'demo';
        console.log(`[GlobalHeader] Switching from ${currentMode} to ${newMode}`);

        // تحذير عند التبديل للوضع الحقيقي
        if (newMode === 'real') {
            if (!hasBinanceKeys) {
                hapticWarning();
                ToastService.showWarning('يجب إضافة مفاتيح Binance أولاً');
                return;
            }

            AlertService.confirm(
                '⚠️ تحذير هام',
                'أنت على وشك التبديل للتداول الحقيقي.\n\nجميع الصفقات ستكون حقيقية وقد تؤدي لخسائر مالية.',
                async () => {
                    await executeToggle(newMode);
                },
                () => { },
                'تأكيد التبديل',
                'إلغاء'
            );
        } else {
            await executeToggle(newMode);
        }
    };

    const executeToggle = async (newMode) => {
        console.log(`[GlobalHeader] executeToggle called with newMode=${newMode}`);
        setSwitching(true);
        hapticLight();
        try {
            console.log(`[GlobalHeader] Calling changeTradingMode(${newMode})...`);
            const result = await changeTradingMode(newMode);
            console.log('[GlobalHeader] changeTradingMode result:', JSON.stringify(result));

            if (result?.success) {
                console.log('[GlobalHeader] Toggle successful!');
                hapticSuccess();
                ToastService.showSuccess(`تم التبديل إلى الوضع ${newMode === 'demo' ? 'التجريبي' : 'الحقيقي'}`);
            } else {
                hapticWarning();
                ToastService.showError(result?.error || 'فشل التبديل');
            }
        } catch (error) {
            hapticWarning();

            let errorMessage = 'فشل التبديل بين الأوضاع';
            if (error?.response?.data?.error) {
                errorMessage = error.response.data.error;
            } else if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
                errorMessage = 'انتهى وقت الانتظار. يرجى المحاولة مرة أخرى';
            } else if (error?.code === 'ERR_NETWORK' || error?.message?.includes('Network Error')) {
                errorMessage = 'فشل الاتصال بالخادم. تحقق من اتصالك بالإنترنت';
            }

            ToastService.showError(errorMessage);
        } finally {
            setSwitching(false);
        }
    };

    return (
        <View style={[styles.container, { paddingTop: insets.top }]}>
            {/* خط التدرج العلوي */}
            <LinearGradient
                colors={theme.colors.gradientPrimary}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.gradientLine}
            />

            <View style={styles.content}>
                {/* زر الرجوع أو الشعار - RTL: يظهر على اليمين */}
                <View style={isRTL ? styles.rightContainer : styles.leftContainer}>
                    {showBack ? (
                        <TouchableOpacity
                            onPress={() => { hapticLight(); onBack ? onBack() : navigation.goBack(); }}
                            style={styles.backButton}
                            activeOpacity={0.7}
                        >
                            {/* في RTL: السهم يشير لليمين للرجوع */}
                            {isRTL ? (
                                <ArrowRightIcon size={24} color={theme.colors.text} />
                            ) : (
                                <ArrowLeftIcon size={24} color={theme.colors.text} />
                            )}
                        </TouchableOpacity>
                    ) : showLogo ? (
                        <UnifiedBrandLogo variant="header" size={36} />
                    ) : <View style={{ width: 40 }} />}
                </View>

                {/* العنوان + وضع التداول للأدمن + شارة AUTO */}
                <View style={styles.centerContainer}>
                    <View style={styles.titleRow}>
                        <Text style={styles.title} numberOfLines={1}>
                            {title || '1B Trading'}
                        </Text>

                        {/* ✅ شارة وضع التداول للأدمن - فقط بعد تسجيل الدخول */}
                        {isAdmin && isUserLoggedIn && userId && (
                            <TouchableOpacity
                                onPress={handleToggleMode}
                                disabled={switching || modeLoading}
                                activeOpacity={0.7}
                                style={[styles.modeBadgeLarge, {
                                    backgroundColor: currentMode === 'demo' ? '#F59E0B' : '#10B981',
                                    borderColor: currentMode === 'demo' ? '#F59E0B' : '#10B981',
                                }]}
                            >
                                {switching ? (
                                    <ActivityIndicator size="small" color="#FFFFFF" />
                                ) : (
                                    <View style={styles.modeBadgeContent}>
                                        <Text style={styles.modeBadgeTextLarge}>
                                            {currentMode === 'demo' ? '🔴 تجريبي' : '🟢 حقيقي'}
                                        </Text>
                                        <BrandIcon name="swap" size={14} color="#FFFFFF" />
                                    </View>
                                )}
                            </TouchableOpacity>
                        )}
                    </View>
                    {subtitle && (
                        <Text style={styles.subtitle} numberOfLines={1}>
                            {subtitle}
                        </Text>
                    )}
                </View>

                {/* الإجراء الأيمن - RTL: يظهر على اليسار */}
                <View style={isRTL ? styles.leftContainer : styles.rightContainer}>
                    {rightAction ? rightAction : showNotification ? (
                        <TouchableOpacity
                            onPress={() => { hapticLight(); onNotificationPress && onNotificationPress(); }}
                            style={styles.iconButton}
                            activeOpacity={0.7}
                        >
                            <NotificationIcon size={24} color={theme.colors.textSecondary} />
                        </TouchableOpacity>
                    ) : null}
                </View>
            </View>

            {/* خط فاصل سفلي */}
            <View style={styles.bottomBorder} />

            {/* ✅ Tooltip للنظام الآلي */}
            <Modal
                visible={showAutoTooltip}
                transparent
                animationType="none"
                onRequestClose={() => setShowAutoTooltip(false)}
            >
                <TouchableOpacity
                    style={styles.tooltipOverlay}
                    activeOpacity={1}
                    onPress={() => setShowAutoTooltip(false)}
                >
                    <Animated.View
                        style={[
                            styles.tooltipBox,
                            {
                                transform: [{ scale: scaleAnim }],
                            },
                        ]}
                    >
                        <Text style={styles.tooltipTitle}>🤖 نظام تداول آلي 100%</Text>
                        <Text style={styles.tooltipDescription}>
                            النظام يتداول تلقائياً كل 60 ثانية - أنت فقط تراقب النتائج
                        </Text>

                        <View style={styles.tooltipSection}>
                            <Text style={styles.tooltipSectionLabel}>✅ أنت تفعل:</Text>
                            <Text style={styles.tooltipItem}>• تسجيل الدخول</Text>
                            <Text style={styles.tooltipItem}>• ربط مفاتيح Binance</Text>
                            <Text style={styles.tooltipItem}>• مراقبة النتائج</Text>
                        </View>

                        <View style={styles.tooltipSection}>
                            <Text style={styles.tooltipSectionLabel}>🤖 النظام يفعل (تلقائياً):</Text>
                            <Text style={styles.tooltipItem}>• اختيار العملات كل 12 ساعة</Text>
                            <Text style={styles.tooltipItem}>• فتح صفقات كل 60 ثانية</Text>
                            <Text style={styles.tooltipItem}>• إغلاق الصفقات تلقائياً</Text>
                            <Text style={styles.tooltipItem}>• تحديث المحفظة</Text>
                        </View>

                        <View style={styles.tooltipNote}>
                            <Text style={styles.tooltipNoteText}>
                                💡 البيانات المعروضة حقيقية من Binance - محدثة تلقائياً كل 60 ثانية
                            </Text>
                        </View>

                        <TouchableOpacity
                            style={styles.tooltipButton}
                            onPress={() => setShowAutoTooltip(false)}
                        >
                            <Text style={styles.tooltipButtonText}>فهمت ✓</Text>
                        </TouchableOpacity>
                    </Animated.View>
                </TouchableOpacity>
            </Modal>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        backgroundColor: theme.colors.background,
        zIndex: 100,
    },
    gradientLine: {
        height: 3,
        width: '100%',
    },
    content: {
        height: 60,
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 16,
        justifyContent: 'space-between',
    },
    leftContainer: {
        width: 48,
        alignItems: 'flex-start',
        justifyContent: 'center',
    },
    centerContainer: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
    },
    titleRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
    },
    modeBadge: {
        paddingHorizontal: 8,
        paddingVertical: 3,
        borderRadius: 10,
        borderWidth: 1,
    },
    modeBadgeText: {
        fontSize: 10,
        fontWeight: '600',
    },
    modeBadgeLarge: {
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 12,
        borderWidth: 2,
        marginStart: 8,
    },
    modeBadgeTextLarge: {
        fontSize: 13,
        fontWeight: '700',
        color: '#FFFFFF',
    },
    modeBadgeContent: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    rightContainer: {
        width: 48,
        alignItems: 'flex-end',
        justifyContent: 'center',
    },
    title: {
        color: theme.colors.text,
        fontSize: 18,
        fontWeight: '700',
        letterSpacing: 0.3,
    },
    subtitle: {
        color: theme.colors.textSecondary,
        fontSize: 12,
        marginTop: 2,
    },
    backButton: {
        width: 44,      // ✅ Touch Target محسّن
        height: 44,
        borderRadius: 12,
        backgroundColor: theme.colors.surface,
        alignItems: 'center',
        justifyContent: 'center',
    },
    iconButton: {
        width: 44,      // ✅ Touch Target محسّن
        height: 44,
        borderRadius: 12,
        backgroundColor: theme.colors.surface,
        alignItems: 'center',
        justifyContent: 'center',
    },
    bottomBorder: {
        height: 1,
        backgroundColor: theme.colors.border,
        opacity: 0.5,
    },
    autoBadge: {
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 8,
        backgroundColor: theme.colors.primary + '15',
        borderWidth: 1,
        borderColor: theme.colors.primary + '30',
    },
    autoBadgeText: {
        fontSize: 10,
        fontWeight: '700',
        color: theme.colors.primary,
    },
    tooltipOverlay: {
        flex: 1,
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 24,
    },
    tooltipBox: {
        backgroundColor: theme.colors.card,
        borderRadius: 16,
        padding: 20,
        width: '100%',
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    tooltipTitle: {
        fontSize: 16,
        fontWeight: '700',
        color: theme.colors.text,
        marginBottom: 12,
    },
    tooltipDescription: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        lineHeight: 20,
        marginBottom: 16,
    },
    tooltipSection: {
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        padding: 12,
        marginBottom: 12,
        borderLeftWidth: 3,
        borderLeftColor: theme.colors.primary,
    },
    tooltipSectionLabel: {
        fontSize: 12,
        fontWeight: '700',
        color: theme.colors.primary,
        marginBottom: 8,
    },
    tooltipItem: {
        fontSize: 12,
        color: theme.colors.text,
        lineHeight: 18,
        marginBottom: 4,
    },
    tooltipNote: {
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        borderRadius: 12,
        padding: 12,
        marginBottom: 16,
        borderWidth: 1,
        borderColor: 'rgba(16, 185, 129, 0.3)',
    },
    tooltipNoteText: {
        fontSize: 12,
        color: theme.colors.text,
        lineHeight: 18,
    },
    tooltipButton: {
        backgroundColor: theme.colors.primary,
        borderRadius: 12,
        paddingVertical: 12,
        alignItems: 'center',
    },
    tooltipButtonText: {
        color: '#FFF',
        fontSize: 14,
        fontWeight: '600',
    },
});

export default GlobalHeader;
