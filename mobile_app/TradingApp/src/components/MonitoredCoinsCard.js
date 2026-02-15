/**
 * 🪙 بطاقة العملات المُراقبة - Monitored Coins Card
 * تعرض العملات التي يراقبها النظام مرتبة بالأداء
 * كل عملة تظهر: الترتيب + الرمز + WR + متوسط الربح + الحالة
 */

import React from 'react';
import {
    View,
    Text,
    StyleSheet,
} from 'react-native';
import { theme } from '../theme/theme';
import ModernCard from './ModernCard';

const STATUS_CONFIG = {
    strong: { label: 'قوي', color: theme.colors.success, icon: '🟢' },
    normal: { label: 'عادي', color: theme.colors.info, icon: '🔵' },
    weak: { label: 'ضعيف', color: theme.colors.warning, icon: '🟡' },
    blocked: { label: 'محظور', color: theme.colors.error, icon: '🔴' },
    waiting: { label: 'ينتظر', color: theme.colors.textSecondary, icon: '⏳' },
};

const CoinRow = ({ coin, index }) => {
    const cfg = STATUS_CONFIG[coin.status] || STATUS_CONFIG.waiting;
    const wrColor = coin.win_rate >= 0.55 ? theme.colors.success
        : coin.win_rate >= 0.40 ? theme.colors.info
        : coin.win_rate > 0 ? theme.colors.warning
        : theme.colors.textSecondary;
    const pnlColor = coin.avg_pnl_pct > 0 ? theme.colors.success
        : coin.avg_pnl_pct < 0 ? theme.colors.error
        : theme.colors.textSecondary;

    return (
        <View style={[styles.coinRow, index > 0 && styles.coinRowBorder]}>
            {/* الترتيب + الرمز */}
            <View style={styles.coinLeft}>
                <Text style={styles.coinRank}>#{coin.rank}</Text>
                <View>
                    <Text style={styles.coinSymbol}>{coin.symbol.replace('USDT', '')}</Text>
                    <Text style={styles.coinTrades}>
                        {coin.total_trades > 0 ? `${coin.total_trades} صفقة` : 'لا صفقات'}
                    </Text>
                </View>
            </View>

            {/* WR + متوسط الربح */}
            <View style={styles.coinCenter}>
                {coin.total_trades > 0 ? (
                    <>
                        <Text style={[styles.coinWR, { color: wrColor }]}>
                            {(coin.win_rate * 100).toFixed(0)}%
                        </Text>
                        <Text style={[styles.coinPnl, { color: pnlColor }]}>
                            {coin.avg_pnl_pct > 0 ? '+' : ''}{coin.avg_pnl_pct}%
                        </Text>
                    </>
                ) : (
                    <Text style={styles.coinNoData}>—</Text>
                )}
            </View>

            {/* الحالة + صفقة نشطة */}
            <View style={styles.coinRight}>
                <View style={[styles.statusBadge, { backgroundColor: cfg.color + '18' }]}>
                    <Text style={[styles.statusText, { color: cfg.color }]}>
                        {cfg.icon} {cfg.label}
                    </Text>
                </View>
                {coin.active_positions > 0 && (
                    <Text style={styles.activeBadge}>📍 مفتوحة</Text>
                )}
            </View>
        </View>
    );
};

const MonitoredCoinsCard = ({ coins = [], loading = false }) => {
    if (loading) {
        return (
            <ModernCard style={styles.card}>
                <Text style={styles.cardTitle}>🪙 العملات المُراقبة</Text>
                <Text style={styles.loadingText}>جاري التحميل...</Text>
            </ModernCard>
        );
    }

    if (!coins || coins.length === 0) {
        return (
            <ModernCard style={styles.card}>
                <Text style={styles.cardTitle}>🪙 العملات المُراقبة</Text>
                <Text style={styles.emptyText}>لا توجد عملات مُراقبة حالياً</Text>
            </ModernCard>
        );
    }

    const activeCount = coins.filter(c => c.active_positions > 0).length;
    const strongCount = coins.filter(c => c.status === 'strong').length;

    return (
        <ModernCard style={styles.card}>
            {/* العنوان + ملخص */}
            <View style={styles.header}>
                <Text style={styles.cardTitle}>🪙 العملات المُراقبة</Text>
                <Text style={styles.headerSummary}>
                    {coins.length} عملة{strongCount > 0 ? ` · ${strongCount} قوية` : ''}{activeCount > 0 ? ` · ${activeCount} مفتوحة` : ''}
                </Text>
            </View>

            {/* رأس الجدول */}
            <View style={styles.tableHeader}>
                <Text style={[styles.thText, { flex: 1.2 }]}>العملة</Text>
                <Text style={[styles.thText, { flex: 0.8, textAlign: 'center' }]}>WR / الربح</Text>
                <Text style={[styles.thText, { flex: 0.8, textAlign: 'left' }]}>الحالة</Text>
            </View>

            {/* القائمة */}
            {coins.map((coin, index) => (
                <CoinRow key={coin.symbol} coin={coin} index={index} />
            ))}
        </ModernCard>
    );
};

const styles = StyleSheet.create({
    card: {
        marginBottom: 16,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
    },
    cardTitle: {
        fontSize: 16,
        fontWeight: '700',
        color: theme.colors.text,
    },
    headerSummary: {
        fontSize: 12,
        color: theme.colors.textSecondary,
    },
    tableHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingBottom: 8,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
        marginBottom: 4,
    },
    thText: {
        fontSize: 11,
        color: theme.colors.textSecondary,
        fontWeight: '600',
    },
    coinRow: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 10,
    },
    coinRowBorder: {
        borderTopWidth: StyleSheet.hairlineWidth,
        borderTopColor: theme.colors.border,
    },
    coinLeft: {
        flex: 1.2,
        flexDirection: 'row',
        alignItems: 'center',
    },
    coinRank: {
        fontSize: 12,
        fontWeight: '700',
        color: theme.colors.textSecondary,
        width: 28,
    },
    coinSymbol: {
        fontSize: 14,
        fontWeight: '700',
        color: theme.colors.text,
    },
    coinTrades: {
        fontSize: 11,
        color: theme.colors.textSecondary,
        marginTop: 1,
    },
    coinCenter: {
        flex: 0.8,
        alignItems: 'center',
    },
    coinWR: {
        fontSize: 14,
        fontWeight: '700',
    },
    coinPnl: {
        fontSize: 11,
        marginTop: 1,
    },
    coinNoData: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    coinRight: {
        flex: 0.8,
        alignItems: 'flex-start',
    },
    statusBadge: {
        paddingHorizontal: 8,
        paddingVertical: 3,
        borderRadius: 10,
    },
    statusText: {
        fontSize: 11,
        fontWeight: '600',
    },
    activeBadge: {
        fontSize: 10,
        color: theme.colors.primary,
        marginTop: 3,
    },
    loadingText: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        paddingVertical: 20,
    },
    emptyText: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        paddingVertical: 20,
    },
});

export default MonitoredCoinsCard;
