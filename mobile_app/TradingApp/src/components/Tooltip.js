/**
 * مكون Tooltip للمساعدة
 * ✅ يظهر عند الضغط على أيقونة المساعدة
 * ✅ تصميم أنيق متوافق مع الثيم
 * ✅ يختفي تلقائياً أو بالضغط
 */

import React, { useState, useRef, useEffect } from 'react';
import {
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    Modal,
    Animated,
    Dimensions,
    TouchableWithoutFeedback,
} from 'react-native';
import { theme } from '../theme/theme';
import Icon from './CustomIcons';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

/**
 * محتوى Tooltips للإعدادات المختلفة
 */
export const TooltipContent = {
    // نظام التداول الآلي
    autoTradingSystem: {
        title: '🤖 نظام تداول آلي 100%',
        description: 'هذا نظام تداول آلي بالكامل. النظام يتداول تلقائياً كل 60 ثانية - أنت فقط تراقب النتائج.',
        sections: [
            {
                label: '✅ أنت تفعل:',
                items: ['تسجيل الدخول', 'ربط مفاتيح Binance', 'مراقبة النتائج'],
            },
            {
                label: '🤖 النظام يفعل (تلقائياً):',
                items: ['اختيار العملات كل 12 ساعة', 'فتح صفقات كل 60 ثانية', 'إغلاق الصفقات تلقائياً', 'تحديث المحفظة'],
            },
            {
                label: '❌ لا يمكنك:',
                items: ['فتح صفقات يدوياً', 'إغلاق صفقات يدوياً', 'تغيير شروط الإغلاق'],
            },
        ],
        example: 'البيانات المعروضة حقيقية من Binance - محدثة تلقائياً كل 60 ثانية',
    },

    // إعدادات التداول
    stopLoss: {
        title: 'وقف الخسارة (Stop Loss)',
        description: 'النسبة المئوية للخسارة التي سيتم عندها إغلاق الصفقة تلقائياً لحماية رأس المال.',
        example: 'مثال: إذا اشتريت بـ 100$ ووضعت 5%، سيتم البيع إذا انخفضت القيمة إلى 95$.',
        recommended: '3% - 7%',
    },
    takeProfit: {
        title: 'جني الأرباح (Take Profit)',
        description: 'النسبة المئوية للربح التي سيتم عندها إغلاق الصفقة تلقائياً لتأمين الأرباح.',
        example: 'مثال: إذا اشتريت بـ 100$ ووضعت 10%، سيتم البيع عند وصول القيمة إلى 110$.',
        recommended: '5% - 15%',
    },
    tradeAmount: {
        title: 'مبلغ الصفقة',
        description: 'المبلغ الذي سيتم استخدامه في كل صفقة. يمكن أن يكون مبلغ ثابت أو نسبة من الرصيد.',
        example: 'مثال: 50$ لكل صفقة أو 5% من إجمالي الرصيد.',
        recommended: '1% - 5% من الرصيد',
    },
    maxOpenTrades: {
        title: 'الحد الأقصى للصفقات المفتوحة',
        description: 'عدد الصفقات التي يمكن أن تكون مفتوحة في نفس الوقت. يساعد في إدارة المخاطر.',
        example: 'مثال: 3 صفقات مفتوحة كحد أقصى.',
        recommended: '3 - 5 صفقات',
    },
    tradingPairs: {
        title: 'أزواج التداول',
        description: 'العملات الرقمية التي سيتم التداول عليها. اختر الأزواج ذات السيولة العالية.',
        example: 'مثال: BTC/USDT, ETH/USDT',
        recommended: 'أزواج USDT الرئيسية',
    },
    autoTrading: {
        title: 'التداول التلقائي',
        description: 'عند التفعيل، سيقوم النظام بتنفيذ الصفقات تلقائياً بناءً على إشارات الذكاء الاصطناعي.',
        example: 'يعمل 24/7 دون تدخل منك.',
        recommended: 'فعّل بعد اختبار الإعدادات',
    },

    // Binance Keys
    apiKey: {
        title: 'مفتاح API',
        description: 'مفتاح الوصول لحسابك في Binance. يُستخدم للاتصال بحسابك وتنفيذ الصفقات.',
        example: 'احصل عليه من: Binance > API Management > Create API',
        recommended: 'فعّل صلاحيات التداول فقط',
    },
    secretKey: {
        title: 'المفتاح السري',
        description: 'المفتاح السري المرتبط بـ API Key. يُستخدم للتوقيع على الطلبات.',
        example: 'يظهر مرة واحدة فقط عند الإنشاء - احفظه بأمان!',
        recommended: 'لا تشاركه مع أي شخص',
    },

    // المحفظة
    totalBalance: {
        title: 'إجمالي الرصيد',
        description: 'القيمة الإجمالية لجميع أصولك بالدولار الأمريكي.',
        example: 'يشمل: الرصيد المتاح + قيمة الصفقات المفتوحة',
    },
    pnl: {
        title: 'الربح والخسارة (P&L)',
        description: 'إجمالي الأرباح أو الخسائر من جميع صفقاتك.',
        example: 'الأخضر = ربح، الأحمر = خسارة',
    },
};

/**
 * مكون أيقونة المساعدة
 */
export const HelpIcon = ({ tooltipKey, size = 18, style }) => {
    const [visible, setVisible] = useState(false);
    const content = TooltipContent[tooltipKey];

    if (!content) {return null;}

    return (
        <>
            <TouchableOpacity
                style={[styles.helpIcon, style]}
                onPress={() => setVisible(true)}
                hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
            >
                <Icon name="help-circle" size={size} color={theme.colors.textSecondary} />
            </TouchableOpacity>

            <TooltipModal
                visible={visible}
                onClose={() => setVisible(false)}
                content={content}
            />
        </>
    );
};

/**
 * Modal لعرض Tooltip
 */
const TooltipModal = ({ visible, onClose, content }) => {
    const scaleAnim = useRef(new Animated.Value(0)).current;
    const opacityAnim = useRef(new Animated.Value(0)).current;

    useEffect(() => {
        if (visible) {
            Animated.parallel([
                Animated.spring(scaleAnim, {
                    toValue: 1,
                    tension: 50,
                    friction: 7,
                    useNativeDriver: true,
                }),
                Animated.timing(opacityAnim, {
                    toValue: 1,
                    duration: 200,
                    useNativeDriver: true,
                }),
            ]).start();
        } else {
            Animated.parallel([
                Animated.timing(scaleAnim, {
                    toValue: 0,
                    duration: 150,
                    useNativeDriver: true,
                }),
                Animated.timing(opacityAnim, {
                    toValue: 0,
                    duration: 150,
                    useNativeDriver: true,
                }),
            ]).start();
        }
    }, [visible]);

    if (!content) {return null;}

    return (
        <Modal
            visible={visible}
            transparent
            animationType="none"
            onRequestClose={onClose}
        >
            <TouchableWithoutFeedback onPress={onClose}>
                <View style={styles.modalOverlay}>
                    <TouchableWithoutFeedback>
                        <Animated.View
                            style={[
                                styles.tooltipContainer,
                                {
                                    opacity: opacityAnim,
                                    transform: [{ scale: scaleAnim }],
                                },
                            ]}
                        >
                            {/* Header */}
                            <View style={styles.tooltipHeader}>
                                <Icon name="information-circle" size={24} color={theme.colors.primary} />
                                <Text style={styles.tooltipTitle}>{content.title}</Text>
                            </View>

                            {/* Description */}
                            <Text style={styles.tooltipDescription}>
                                {content.description}
                            </Text>

                            {/* Sections (للنظام الآلي) */}
                            {content.sections && content.sections.map((section, idx) => (
                                <View key={idx} style={styles.sectionBox}>
                                    <Text style={styles.sectionLabel}>{section.label}</Text>
                                    {section.items.map((item, itemIdx) => (
                                        <Text key={itemIdx} style={styles.sectionItem}>
                                            • {item}
                                        </Text>
                                    ))}
                                </View>
                            ))}

                            {/* Example */}
                            {content.example && (
                                <View style={styles.exampleBox}>
                                    <Text style={styles.exampleLabel}>💡 ملاحظة:</Text>
                                    <Text style={styles.exampleText}>{content.example}</Text>
                                </View>
                            )}

                            {/* Recommended */}
                            {content.recommended && (
                                <View style={styles.recommendedBox}>
                                    <Text style={styles.recommendedLabel}>📊 الموصى به:</Text>
                                    <Text style={styles.recommendedText}>{content.recommended}</Text>
                                </View>
                            )}

                            {/* Close Button */}
                            <TouchableOpacity
                                style={styles.closeButton}
                                onPress={onClose}
                            >
                                <Text style={styles.closeButtonText}>فهمت ✓</Text>
                            </TouchableOpacity>
                        </Animated.View>
                    </TouchableWithoutFeedback>
                </View>
            </TouchableWithoutFeedback>
        </Modal>
    );
};

/**
 * مكون Label مع Tooltip
 */
export const LabelWithTooltip = ({ label, tooltipKey, required = false, style }) => (
    <View style={[styles.labelContainer, style]}>
        <Text style={styles.label}>
            {label}
            {required && <Text style={styles.required}> *</Text>}
        </Text>
        <HelpIcon tooltipKey={tooltipKey} />
    </View>
);

const styles = StyleSheet.create({
    helpIcon: {
        padding: 4,
    },
    modalOverlay: {
        flex: 1,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 24,
    },
    tooltipContainer: {
        backgroundColor: theme.colors.card,
        borderRadius: 20,
        padding: 24,
        maxWidth: SCREEN_WIDTH - 48,
        width: '100%',
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    tooltipHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 16,
        gap: 10,
    },
    tooltipTitle: {
        fontSize: theme.typography.fontSize.lg,
        fontWeight: 'bold',
        color: theme.colors.text,
        flex: 1,
    },
    tooltipDescription: {
        fontSize: theme.typography.fontSize.base,
        color: theme.colors.textSecondary,
        lineHeight: 24,
        marginBottom: 16,
    },
    exampleBox: {
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        padding: 12,
        marginBottom: 12,
    },
    exampleLabel: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.primary,
        fontWeight: '600',
        marginBottom: 4,
    },
    exampleText: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.text,
        lineHeight: 20,
    },
    recommendedBox: {
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        borderRadius: 12,
        padding: 12,
        marginBottom: 16,
        borderWidth: 1,
        borderColor: 'rgba(16, 185, 129, 0.3)',
    },
    recommendedLabel: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.success,
        fontWeight: '600',
        marginBottom: 4,
    },
    recommendedText: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.text,
    },
    sectionBox: {
        backgroundColor: theme.colors.surface,
        borderRadius: 12,
        padding: 12,
        marginBottom: 12,
        borderLeftWidth: 3,
        borderLeftColor: theme.colors.primary,
    },
    sectionLabel: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.primary,
        fontWeight: '700',
        marginBottom: 8,
    },
    sectionItem: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.text,
        lineHeight: 20,
        marginBottom: 4,
    },
    closeButton: {
        backgroundColor: theme.colors.primary,
        borderRadius: 12,
        paddingVertical: 14,
        alignItems: 'center',
    },
    closeButtonText: {
        color: '#FFF',
        fontSize: theme.typography.fontSize.base,
        fontWeight: '600',
    },
    labelContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
    },
    label: {
        fontSize: theme.typography.fontSize.sm,
        color: theme.colors.text,
        fontWeight: '600',
    },
    required: {
        color: theme.colors.error,
    },
});

export default {
    HelpIcon,
    TooltipModal,
    LabelWithTooltip,
    TooltipContent,
};
