/**
 * 📊 بطاقة الصفقات النشطة - Active Positions Card
 * ✅ تعرض الصفقات المفتوحة مع مؤشرات الربح/الخسارة
 * ✅ تدعم Admin (demo/real) و User (real only)
 * ✅ تصميم متناسق مع Theme الموحد
 * ✅ عرض: العملة + الاستراتيجية + المدة + نسبة الربح + قرب TP/SL
 */

import React, { useMemo } from 'react';
import {
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    ActivityIndicator,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { theme } from '../theme/theme';
import { colors, spacing, typography } from '../theme/designSystem';
import BrandIcon from './BrandIcons';

// حساب مدة الصفقة من تاريخ الفتح
const getPositionDuration = (createdAt) => {
    if (!createdAt) return '—';
    const now = new Date();
    const opened = new Date(createdAt);
    const diffMs = now - opened;
    if (isNaN(diffMs) || diffMs < 0) return '—';

    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 60) return `${diffMins} د`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours} س ${diffMins % 60} د`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays} يوم ${diffHours % 24} س`;
    return `${diffDays} يوم`;
};

// حساب قرب السعر من TP أو SL
const getTpSlProximity = (position) => {
    const entry = parseFloat(position.entry_price);
    const current = parseFloat(position.current_price || position.entry_price);
    const tp = parseFloat(position.take_profit);
    const sl = parseFloat(position.stop_loss);
    const isBuy = position.position_type === 'BUY';

    if (!tp || !sl || isNaN(tp) || isNaN(sl) || isNaN(current)) {
        return { label: '—', color: colors.text.tertiary, icon: 'minus', percent: 0 };
    }

    // المسافة من السعر الحالي إلى TP و SL
    const distToTp = Math.abs(tp - current);
    const distToSl = Math.abs(sl - current);
    const totalRange = Math.abs(tp - sl);

    if (totalRange === 0) {
        return { label: '—', color: colors.text.tertiary, icon: 'minus', percent: 0 };
    }

    // نسبة القرب من TP (0% = عند SL، 100% = عند TP)
    const tpProximityPct = Math.round((1 - distToTp / totalRange) * 100);

    if (distToTp < distToSl) {
        return {
            label: 'أقرب للهدف',
            color: colors.semantic.success,
            icon: 'trending-up',
            percent: Math.min(Math.max(tpProximityPct, 0), 100),
            closerTo: 'tp',
        };
    } else {
        return {
            label: 'أقرب للوقف',
            color: colors.semantic.error,
            icon: 'trending-down',
            percent: Math.min(Math.max(tpProximityPct, 0), 100),
            closerTo: 'sl',
        };
    }
};

const ActivePositionsCard = ({ positions = [], summary = {}, loading = false, onRefresh }) => {
    const navigation = useNavigation();

    // إذا كان Loading
    if (loading) {
        return (
            <View style={styles.card}>
                <View style={styles.header}>
                    <BrandIcon name="activity" size={20} color={colors.brand.primary} />
                    <Text style={styles.title}>الصفقات المفتوحة</Text>
                </View>
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="small" color={colors.brand.primary} />
                    <Text style={styles.loadingText}>جاري التحميل...</Text>
                </View>
            </View>
        );
    }

    // إذا لم توجد صفقات
    if (!positions || positions.length === 0) {
        return (
            <View style={styles.card}>
                <View style={styles.header}>
                    <BrandIcon name="activity" size={20} color={colors.brand.primary} />
                    <Text style={styles.title}>الصفقات المفتوحة</Text>
                </View>
                <View style={styles.emptyContainer}>
                    <View style={styles.emptyIconContainer}>
                        <BrandIcon name="inbox" size={48} color={colors.text.tertiary} />
                    </View>
                    <Text style={styles.emptyText}>لا توجد صفقات مفتوحة حالياً</Text>
                    <Text style={styles.emptySubtext}>ستظهر صفقاتك المفتوحة هنا عندما يفتح النظام صفقة جديدة</Text>
                </View>
            </View>
        );
    }

    // عرض الصفقات
    return (
        <View style={styles.card}>
            {/* Header */}
            <View style={styles.header}>
                <View style={styles.headerLeft}>
                    <BrandIcon name="activity" size={20} color={colors.brand.primary} />
                    <Text style={styles.title}>الصفقات المفتوحة</Text>
                    <View style={styles.badge}>
                        <Text style={styles.badgeText}>{summary.total_positions || positions.length}</Text>
                    </View>
                </View>
                {onRefresh && (
                    <TouchableOpacity
                        style={styles.refreshBtn}
                        onPress={onRefresh}
                        hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                    >
                        <BrandIcon name="refresh" size={18} color={colors.brand.primary} />
                    </TouchableOpacity>
                )}
            </View>

            {/* Summary Stats */}
            <View style={styles.summaryContainer}>
                <View style={styles.summaryItem}>
                    <Text style={styles.summaryLabel}>القيمة الإجمالية</Text>
                    <Text style={styles.summaryValue}>
                        ${(summary.total_value || 0).toFixed(2)}
                    </Text>
                </View>
                <View style={styles.summaryDivider} />
                <View style={styles.summaryItem}>
                    <Text style={styles.summaryLabel}>الربح/الخسارة</Text>
                    <Text
                        style={[
                            styles.summaryValue,
                            (summary.total_pnl || 0) >= 0 ? styles.profitText : styles.lossText,
                        ]}
                    >
                        {(summary.total_pnl || 0) >= 0 ? '+' : ''}
                        ${(summary.total_pnl || 0).toFixed(2)}
                    </Text>
                </View>
                <View style={styles.summaryDivider} />
                <View style={styles.summaryItem}>
                    <Text style={styles.summaryLabel}>رابحة/خاسرة</Text>
                    <Text style={styles.summaryValue}>
                        <Text style={styles.profitText}>{summary.profitable_count || 0}</Text>
                        /
                        <Text style={styles.lossText}>{summary.losing_count || 0}</Text>
                    </Text>
                </View>
            </View>

            {/* Positions Vertical List */}
            {positions.slice(0, 5).map((position, index) => (
                <PositionItem key={position.id || index} position={position} isLast={index === Math.min(positions.length, 5) - 1} />
            ))}

            {/* Footer */}
            {positions.length > 5 && (
                <TouchableOpacity
                    style={styles.footer}
                    onPress={() => navigation.navigate('Trading')}
                >
                    <Text style={styles.footerText}>
                        عرض جميع الصفقات ({positions.length})
                    </Text>
                    <BrandIcon name="arrow-left" size={16} color={colors.brand.primary} />
                </TouchableOpacity>
            )}
        </View>
    );
};

// مكون عنصر الصفقة — عرض عمودي تفصيلي
const PositionItem = ({ position, isLast }) => {
    const isProfitable = position.is_profitable || (position.current_pnl || 0) > 0;
    const pnlPercentage = position.current_pnl_percentage || 0;

    // حساب مدة الصفقة
    const duration = useMemo(() => getPositionDuration(position.created_at), [position.created_at]);

    // حساب قرب TP/SL
    const proximity = useMemo(() => getTpSlProximity(position), [
        position.current_price,
        position.take_profit,
        position.stop_loss,
        position.entry_price,
        position.position_type,
    ]);

    // ✅ تحديد حالة ML وأيقونتها
    const mlStatus = position.ml_status || 'none';
    const getMlIcon = () => {
        switch (mlStatus) {
            case 'approved_winning':
                return { icon: 'brain', color: colors.semantic.success };
            case 'approved_new':
                return { icon: 'sparkles', color: colors.brand.primary };
            default:
                return null;
        }
    };
    const mlInfo = getMlIcon();

    return (
        <View style={[styles.positionItem, !isLast && styles.positionItemBorder]}>
            {/* الصف الأول: العملة + النوع + نسبة الربح */}
            <View style={styles.positionRow1}>
                <View style={styles.symbolSection}>
                    <Text style={styles.positionSymbol}>{position.symbol || '—'}</Text>
                    {mlInfo && (
                        <View style={[styles.mlBadge, { backgroundColor: mlInfo.color + '20' }]}>
                            <BrandIcon name={mlInfo.icon} size={10} color={mlInfo.color} />
                        </View>
                    )}
                    <View style={[styles.typeBadge, position.position_type === 'BUY' ? styles.buyBadge : styles.sellBadge]}>
                        <Text style={[styles.typeText, { color: position.position_type === 'BUY' ? colors.semantic.success : colors.semantic.error }]}>
                            {position.position_type === 'BUY' ? 'شراء' : 'بيع'}
                        </Text>
                    </View>
                </View>
                <View style={styles.pnlSection}>
                    <BrandIcon
                        name={isProfitable ? 'trending-up' : 'trending-down'}
                        size={14}
                        color={isProfitable ? colors.semantic.success : colors.semantic.error}
                    />
                    <Text style={[styles.pnlPercent, isProfitable ? styles.profitText : styles.lossText]}>
                        {pnlPercentage >= 0 ? '+' : ''}{pnlPercentage.toFixed(2)}%
                    </Text>
                    <Text style={styles.pnlAmount}>
                        ({(position.current_pnl || 0) >= 0 ? '+' : ''}${(position.current_pnl || 0).toFixed(2)})
                    </Text>
                </View>
            </View>

            {/* الصف الثاني: الاستراتيجية + المدة */}
            <View style={styles.positionRow2}>
                <View style={styles.strategySection}>
                    <BrandIcon name="chart" size={12} color={colors.text.tertiary} />
                    <Text style={styles.strategyText}>{position.strategy || 'استراتيجية آلية'}</Text>
                </View>
                <View style={styles.durationSection}>
                    <BrandIcon name="clock" size={12} color={colors.text.tertiary} />
                    <Text style={styles.durationText}>{duration}</Text>
                </View>
            </View>

            {/* الصف الثالث: شريط القرب من TP/SL */}
            {(position.take_profit && position.stop_loss) ? (
                <View style={styles.proximityContainer}>
                    <View style={styles.proximityLabels}>
                        <Text style={[styles.proximityLabel, { color: colors.semantic.error }]}>SL</Text>
                        <View style={styles.proximityInfo}>
                            <BrandIcon name={proximity.icon} size={12} color={proximity.color} />
                            <Text style={[styles.proximityText, { color: proximity.color }]}>
                                {proximity.label}
                            </Text>
                        </View>
                        <Text style={[styles.proximityLabel, { color: colors.semantic.success }]}>TP</Text>
                    </View>
                    <View style={styles.proximityBar}>
                        {/* خلفية الشريط */}
                        <View style={styles.proximityBarBg} />
                        {/* مؤشر الموقع الحالي */}
                        <View
                            style={[
                                styles.proximityMarker,
                                {
                                    left: `${Math.min(Math.max(proximity.percent, 2), 98)}%`,
                                    backgroundColor: proximity.color,
                                },
                            ]}
                        />
                        {/* تدرج لوني من SL (أحمر) إلى TP (أخضر) */}
                        <View style={[styles.proximityFillSl, { width: `${100 - proximity.percent}%` }]} />
                        <View style={[styles.proximityFillTp, { width: `${proximity.percent}%` }]} />
                    </View>
                    <View style={styles.proximityPrices}>
                        <Text style={styles.proximityPrice}>${parseFloat(position.stop_loss).toFixed(2)}</Text>
                        <Text style={[styles.proximityPrice, { fontWeight: '600', color: colors.text.primary }]}>
                            ${parseFloat(position.current_price || position.entry_price).toFixed(2)}
                        </Text>
                        <Text style={styles.proximityPrice}>${parseFloat(position.take_profit).toFixed(2)}</Text>
                    </View>
                </View>
            ) : null}
        </View>
    );
};

const styles = StyleSheet.create({
    card: {
        backgroundColor: colors.background.card,
        borderRadius: 16,
        padding: spacing.md,
        marginBottom: spacing.md,
        ...theme.shadows.medium,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: spacing.md,
    },
    headerLeft: {
        flexDirection: 'row-reverse',
        alignItems: 'center',
        gap: spacing.xs,
    },
    title: {
        ...typography.h3,
        color: colors.text.primary,
        fontWeight: '600',
    },
    badge: {
        backgroundColor: colors.brand.primary + '20',
        borderRadius: 12,
        paddingHorizontal: spacing.xs,
        paddingVertical: 2,
        minWidth: 24,
        alignItems: 'center',
    },
    badgeText: {
        ...typography.caption,
        color: colors.brand.primary,
        fontWeight: '600',
    },
    refreshBtn: {
        padding: 6,
        borderRadius: 8,
        backgroundColor: colors.brand.primary + '10',
    },
    summaryContainer: {
        flexDirection: 'row',
        justifyContent: 'space-around',
        backgroundColor: colors.background.elevated,
        borderRadius: 12,
        padding: spacing.sm,
        marginBottom: spacing.md,
    },
    summaryItem: {
        alignItems: 'center',
        flex: 1,
    },
    summaryLabel: {
        ...typography.caption,
        color: colors.text.secondary,
        marginBottom: 4,
    },
    summaryValue: {
        ...typography.body1,
        color: colors.text.primary,
        fontWeight: '600',
    },
    summaryDivider: {
        width: 1,
        backgroundColor: colors.border.default,
        marginHorizontal: spacing.xs,
    },
    profitText: {
        color: colors.semantic.success,
    },
    lossText: {
        color: colors.semantic.error,
    },

    // ═══════════════ Position Item (Vertical) ═══════════════
    positionItem: {
        paddingVertical: spacing.sm,
    },
    positionItemBorder: {
        borderBottomWidth: 1,
        borderBottomColor: colors.border.default + '60',
    },

    // الصف 1: العملة + نسبة الربح
    positionRow1: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 6,
    },
    symbolSection: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
    },
    positionSymbol: {
        ...typography.body1,
        color: colors.text.primary,
        fontWeight: '700',
        fontSize: 15,
    },
    mlBadge: {
        borderRadius: 6,
        padding: 3,
    },
    typeBadge: {
        borderRadius: 4,
        paddingHorizontal: 6,
        paddingVertical: 1,
    },
    buyBadge: {
        backgroundColor: colors.semantic.success + '15',
    },
    sellBadge: {
        backgroundColor: colors.semantic.error + '15',
    },
    typeText: {
        fontSize: 10,
        fontWeight: '600',
    },
    pnlSection: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
    },
    pnlPercent: {
        ...typography.body2,
        fontWeight: '700',
    },
    pnlAmount: {
        ...typography.caption,
        color: colors.text.tertiary,
        fontSize: 10,
    },

    // الصف 2: الاستراتيجية + المدة
    positionRow2: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 8,
    },
    strategySection: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        backgroundColor: colors.background.elevated,
        borderRadius: 6,
        paddingHorizontal: 8,
        paddingVertical: 3,
    },
    strategyText: {
        ...typography.caption,
        color: colors.text.secondary,
        fontSize: 11,
    },
    durationSection: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        backgroundColor: colors.background.elevated,
        borderRadius: 6,
        paddingHorizontal: 8,
        paddingVertical: 3,
    },
    durationText: {
        ...typography.caption,
        color: colors.text.secondary,
        fontSize: 11,
    },

    // الصف 3: شريط القرب TP/SL
    proximityContainer: {
        marginTop: 2,
    },
    proximityLabels: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 4,
    },
    proximityLabel: {
        fontSize: 10,
        fontWeight: '700',
    },
    proximityInfo: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 3,
    },
    proximityText: {
        fontSize: 10,
        fontWeight: '600',
    },
    proximityBar: {
        height: 6,
        borderRadius: 3,
        backgroundColor: colors.background.elevated,
        overflow: 'hidden',
        position: 'relative',
        flexDirection: 'row',
    },
    proximityBarBg: {
        ...StyleSheet.absoluteFillObject,
        backgroundColor: colors.background.elevated,
    },
    proximityFillSl: {
        height: '100%',
        backgroundColor: colors.semantic.error + '20',
    },
    proximityFillTp: {
        height: '100%',
        backgroundColor: colors.semantic.success + '20',
    },
    proximityMarker: {
        position: 'absolute',
        top: -2,
        width: 10,
        height: 10,
        borderRadius: 5,
        marginLeft: -5,
        zIndex: 2,
        borderWidth: 2,
        borderColor: colors.background.card,
    },
    proximityPrices: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginTop: 3,
    },
    proximityPrice: {
        fontSize: 9,
        color: colors.text.tertiary,
    },

    footer: {
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 4,
        marginTop: spacing.sm,
        paddingTop: spacing.sm,
        borderTopWidth: 1,
        borderTopColor: colors.border.default,
    },
    footerText: {
        ...typography.body2,
        color: colors.brand.primary,
        fontWeight: '500',
    },
    loadingContainer: {
        flexDirection: 'row',
        justifyContent: 'center',
        alignItems: 'center',
        gap: spacing.xs,
        paddingVertical: spacing.lg,
    },
    loadingText: {
        ...typography.body2,
        color: colors.text.secondary,
    },
    emptyContainer: {
        alignItems: 'center',
        paddingVertical: spacing.xl,
    },
    emptyIconContainer: {
        marginBottom: spacing.sm,
    },
    emptyText: {
        ...typography.body1,
        color: colors.text.secondary,
        marginTop: spacing.sm,
        marginBottom: spacing.xs,
    },
    emptySubtext: {
        ...typography.caption,
        color: colors.text.tertiary,
        textAlign: 'center',
    },
});

export default ActivePositionsCard;
