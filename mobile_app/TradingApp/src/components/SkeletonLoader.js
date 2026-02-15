/**
 * مكونات Skeleton Loader
 * ✅ تأثير shimmer متحرك
 * ✅ أشكال متعددة (مستطيل، دائرة، نص)
 * ✅ قابل للتخصيص
 */

import React, { useEffect, useRef } from 'react';
import { View, StyleSheet, Animated, Dimensions } from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { theme } from '../theme/theme';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

/**
 * مكون Skeleton الأساسي مع تأثير shimmer
 */
export const SkeletonBox = ({
    width = '100%',
    height = 20,
    borderRadius = 8,
    style,
}) => {
    const shimmerAnim = useRef(new Animated.Value(0)).current;

    useEffect(() => {
        const animation = Animated.loop(
            Animated.timing(shimmerAnim, {
                toValue: 1,
                duration: 1500,
                useNativeDriver: true,
            })
        );
        animation.start();
        return () => animation.stop();
    }, []);

    const translateX = shimmerAnim.interpolate({
        inputRange: [0, 1],
        outputRange: [-SCREEN_WIDTH, SCREEN_WIDTH],
    });

    return (
        <View
            style={[
                styles.skeletonBase,
                {
                    width,
                    height,
                    borderRadius,
                },
                style,
            ]}
        >
            <Animated.View
                style={[
                    styles.shimmer,
                    {
                        transform: [{ translateX }],
                    },
                ]}
            >
                <LinearGradient
                    colors={[
                        'transparent',
                        'rgba(255, 255, 255, 0.1)',
                        'transparent',
                    ]}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.gradient}
                />
            </Animated.View>
        </View>
    );
};

/**
 * Skeleton دائري (للصور الشخصية)
 */
export const SkeletonCircle = ({ size = 50, style }) => (
    <SkeletonBox
        width={size}
        height={size}
        borderRadius={size / 2}
        style={style}
    />
);

/**
 * Skeleton لسطر نص
 */
export const SkeletonText = ({ width = '80%', height = 14, style }) => (
    <SkeletonBox
        width={width}
        height={height}
        borderRadius={4}
        style={[{ marginVertical: 4 }, style]}
    />
);

/**
 * Skeleton لكارت
 */
export const SkeletonCard = ({ style }) => (
    <View style={[styles.card, style]}>
        <View style={styles.cardHeader}>
            <SkeletonCircle size={40} />
            <View style={styles.cardHeaderText}>
                <SkeletonText width="60%" />
                <SkeletonText width="40%" height={12} />
            </View>
        </View>
        <SkeletonText width="100%" />
        <SkeletonText width="90%" />
        <SkeletonText width="70%" />
    </View>
);

/**
 * Skeleton للوحة التحكم (Dashboard)
 */
export const DashboardSkeleton = () => (
    <View style={styles.dashboardContainer}>
        {/* Header */}
        <View style={styles.dashboardHeader}>
            <SkeletonBox width={120} height={24} />
            <SkeletonCircle size={40} />
        </View>

        {/* Balance Card */}
        <View style={styles.balanceCard}>
            <SkeletonText width="40%" height={14} />
            <SkeletonBox width="70%" height={36} style={{ marginVertical: 8 }} />
            <View style={styles.balanceRow}>
                <SkeletonBox width="45%" height={50} borderRadius={12} />
                <SkeletonBox width="45%" height={50} borderRadius={12} />
            </View>
        </View>

        {/* Stats Cards */}
        <View style={styles.statsRow}>
            <SkeletonBox width="48%" height={80} borderRadius={12} />
            <SkeletonBox width="48%" height={80} borderRadius={12} />
        </View>

        {/* Recent Trades */}
        <SkeletonText width="30%" height={18} style={{ marginTop: 16 }} />
        <SkeletonCard />
        <SkeletonCard />
    </View>
);

/**
 * Skeleton للمحفظة (Portfolio)
 */
export const PortfolioSkeleton = () => (
    <View style={styles.portfolioContainer}>
        {/* Total Value */}
        <View style={styles.totalCard}>
            <SkeletonText width="30%" height={14} />
            <SkeletonBox width="60%" height={32} style={{ marginVertical: 8 }} />
            <SkeletonBox width="40%" height={20} />
        </View>

        {/* Chart Placeholder */}
        <SkeletonBox width="100%" height={200} borderRadius={16} style={{ marginVertical: 16 }} />

        {/* Holdings List */}
        <SkeletonText width="25%" height={16} />
        {[1, 2, 3, 4].map((i) => (
            <View key={i} style={styles.holdingItem}>
                <SkeletonCircle size={40} />
                <View style={styles.holdingInfo}>
                    <SkeletonText width="50%" />
                    <SkeletonText width="30%" height={12} />
                </View>
                <View style={styles.holdingValue}>
                    <SkeletonText width={60} />
                    <SkeletonText width={40} height={12} />
                </View>
            </View>
        ))}
    </View>
);

/**
 * Skeleton لسجل التداول
 */
export const TradeHistorySkeleton = () => (
    <View style={styles.tradeHistoryContainer}>
        {/* Filters */}
        <View style={styles.filtersRow}>
            <SkeletonBox width="30%" height={36} borderRadius={18} />
            <SkeletonBox width="30%" height={36} borderRadius={18} />
            <SkeletonBox width="30%" height={36} borderRadius={18} />
        </View>

        {/* Stats Summary */}
        <View style={styles.statsSummary}>
            <SkeletonBox width="48%" height={70} borderRadius={12} />
            <SkeletonBox width="48%" height={70} borderRadius={12} />
        </View>

        {/* Trade Items */}
        {[1, 2, 3, 4, 5].map((i) => (
            <View key={i} style={styles.tradeItem}>
                <View style={styles.tradeItemLeft}>
                    <SkeletonText width={80} height={16} />
                    <SkeletonText width={60} height={12} />
                </View>
                <View style={styles.tradeItemRight}>
                    <SkeletonText width={70} height={16} />
                    <SkeletonText width={50} height={12} />
                </View>
            </View>
        ))}
    </View>
);

/**
 * Skeleton لإعدادات التداول
 */
export const TradingSettingsSkeleton = () => (
    <View style={styles.settingsContainer}>
        {/* Section Title */}
        <SkeletonText width="40%" height={18} style={{ marginBottom: 16 }} />

        {/* Settings Items */}
        {[1, 2, 3, 4].map((i) => (
            <View key={i} style={styles.settingItem}>
                <View style={styles.settingInfo}>
                    <SkeletonText width="50%" height={16} />
                    <SkeletonText width="70%" height={12} />
                </View>
                <SkeletonBox width={50} height={30} borderRadius={15} />
            </View>
        ))}

        {/* Slider Setting */}
        <View style={styles.sliderSetting}>
            <SkeletonText width="40%" height={16} />
            <SkeletonBox width="100%" height={40} borderRadius={8} style={{ marginTop: 8 }} />
        </View>
    </View>
);

/**
 * Skeleton للملف الشخصي
 */
export const ProfileSkeleton = () => (
    <View style={styles.profileContainer}>
        {/* Avatar */}
        <View style={styles.profileHeader}>
            <SkeletonCircle size={80} />
            <SkeletonText width={120} height={20} style={{ marginTop: 12 }} />
            <SkeletonText width={80} height={14} />
        </View>

        {/* Info Card */}
        <View style={styles.profileCard}>
            {[1, 2, 3].map((i) => (
                <View key={i} style={styles.profileItem}>
                    <SkeletonText width="30%" height={14} />
                    <SkeletonText width="50%" height={16} />
                </View>
            ))}
        </View>

        {/* Menu Items */}
        {[1, 2, 3].map((i) => (
            <SkeletonBox
                key={i}
                width="100%"
                height={56}
                borderRadius={12}
                style={{ marginBottom: 12 }}
            />
        ))}
    </View>
);

/**
 * Skeleton للوحة تحكم الأدمن
 */
export const AdminDashboardSkeleton = () => (
    <View style={styles.adminContainer}>
        {/* Global Status */}
        <SkeletonBox width="100%" height={80} borderRadius={16} style={{ marginBottom: 16 }} />

        {/* Trading Mode Card */}
        <View style={styles.adminCard}>
            <SkeletonText width="40%" height={18} />
            <SkeletonText width="60%" height={14} style={{ marginTop: 8 }} />
            <SkeletonBox width="100%" height={44} borderRadius={12} style={{ marginTop: 12 }} />
        </View>


        {/* Group B Card */}
        <View style={styles.adminCard}>
            <View style={styles.adminCardHeader}>
                <View style={{ flex: 1 }}>
                    <SkeletonText width="60%" height={18} />
                    <SkeletonText width="40%" height={12} style={{ marginTop: 4 }} />
                </View>
                <SkeletonBox width={70} height={28} borderRadius={14} />
            </View>
            <View style={styles.adminStatsRow}>
                <SkeletonBox width="48%" height={50} borderRadius={8} />
                <SkeletonBox width="48%" height={50} borderRadius={8} />
            </View>
        </View>

        {/* Quick Nav */}
        <View style={styles.adminCard}>
            <SkeletonText width="30%" height={18} />
            <View style={styles.adminButtonsRow}>
                <SkeletonBox width="48%" height={80} borderRadius={12} />
                <SkeletonBox width="48%" height={80} borderRadius={12} />
            </View>
        </View>
    </View>
);

const styles = StyleSheet.create({
    skeletonBase: {
        backgroundColor: theme.colors.border,
        overflow: 'hidden',
    },
    shimmer: {
        width: '100%',
        height: '100%',
        position: 'absolute',
    },
    gradient: {
        flex: 1,
        width: SCREEN_WIDTH,
    },
    card: {
        backgroundColor: theme.colors.card,
        borderRadius: 16,
        padding: 16,
        marginVertical: 8,
    },
    cardHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 12,
    },
    cardHeaderText: {
        flex: 1,
        marginStart: 12,
    },

    // Dashboard
    dashboardContainer: {
        padding: 16,
    },
    dashboardHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 20,
    },
    balanceCard: {
        backgroundColor: theme.colors.card,
        borderRadius: 16,
        padding: 20,
        marginBottom: 16,
    },
    balanceRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginTop: 12,
    },
    statsRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
    },

    // Portfolio
    portfolioContainer: {
        padding: 16,
    },
    totalCard: {
        backgroundColor: theme.colors.card,
        borderRadius: 16,
        padding: 20,
        alignItems: 'center',
    },
    holdingItem: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.card,
        borderRadius: 12,
        padding: 12,
        marginTop: 8,
    },
    holdingInfo: {
        flex: 1,
        marginStart: 12,
    },
    holdingValue: {
        alignItems: 'flex-end',
    },

    // Trade History
    tradeHistoryContainer: {
        padding: 16,
    },
    filtersRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginBottom: 16,
    },
    statsSummary: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginBottom: 16,
    },
    tradeItem: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        backgroundColor: theme.colors.card,
        borderRadius: 12,
        padding: 16,
        marginBottom: 8,
    },
    tradeItemLeft: {},
    tradeItemRight: {
        alignItems: 'flex-end',
    },

    // Settings
    settingsContainer: {
        padding: 16,
    },
    settingItem: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        backgroundColor: theme.colors.card,
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
    },
    settingInfo: {
        flex: 1,
    },
    sliderSetting: {
        backgroundColor: theme.colors.card,
        borderRadius: 12,
        padding: 16,
        marginTop: 8,
    },

    // Profile
    profileContainer: {
        padding: 16,
    },
    profileHeader: {
        alignItems: 'center',
        marginBottom: 24,
    },
    profileCard: {
        backgroundColor: theme.colors.card,
        borderRadius: 16,
        padding: 16,
        marginBottom: 16,
    },
    profileItem: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        paddingVertical: 12,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },

    // Admin Dashboard
    adminContainer: {
        padding: 16,
    },
    adminCard: {
        backgroundColor: theme.colors.card,
        borderRadius: 16,
        padding: 16,
        marginBottom: 16,
    },
    adminCardHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: 16,
    },
    adminStatsRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginBottom: 12,
    },
    adminButtonsRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginTop: 8,
    },
});

export default {
    SkeletonBox,
    SkeletonCircle,
    SkeletonText,
    SkeletonCard,
    DashboardSkeleton,
    PortfolioSkeleton,
    TradeHistorySkeleton,
    TradingSettingsSkeleton,
    ProfileSkeleton,
    AdminDashboardSkeleton,
};
