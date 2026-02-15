/**
 * Profit/Loss Indicator Component
 * مكون موحد لعرض الأرباح والخسائر بشكل واضح
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { theme } from '../theme/theme';
import Icon from './CustomIcons';

const ProfitLossIndicator = ({
    value,
    percentage,
    showIcon = true,
    showPercentage = true,
    size = 'medium', // small, medium, large
    style,
}) => {
    const isProfit = value >= 0;
    const color = isProfit ? theme.colors.success : theme.colors.error;
    const icon = isProfit ? 'trending-up' : 'trending-down';
    const arrow = isProfit ? '↑' : '↓';

    // تنسيق القيمة
    const formatValue = (val) => {
        const absVal = Math.abs(val);
        if (absVal >= 1000000) {
            return `${(absVal / 1000000).toFixed(2)}M`;
        }
        if (absVal >= 1000) {
            return `${(absVal / 1000).toFixed(2)}K`;
        }
        return absVal.toFixed(2);
    };

    const formatPercentage = (pct) => {
        return Math.abs(pct).toFixed(2);
    };

    // أحجام مختلفة
    const sizes = {
        small: {
            valueSize: 14,
            percentageSize: 12,
            iconSize: 16,
        },
        medium: {
            valueSize: 18,
            percentageSize: 14,
            iconSize: 20,
        },
        large: {
            valueSize: 24,
            percentageSize: 18,
            iconSize: 24,
        },
    };

    const currentSize = sizes[size] || sizes.medium;

    return (
        <View style={[styles.container, style]}>
            {showIcon && (
                <Icon
                    name={icon}
                    size={currentSize.iconSize}
                    color={color}
                    style={styles.icon}
                />
            )}
            <View style={styles.textContainer}>
                <Text style={[
                    styles.valueText,
                    { color, fontSize: currentSize.valueSize },
                ]}>
                    {isProfit ? '+' : '-'}${formatValue(value)}
                </Text>
                {showPercentage && percentage !== undefined && (
                    <Text style={[
                        styles.percentageText,
                        { color, fontSize: currentSize.percentageSize },
                    ]}>
                        {arrow} {formatPercentage(percentage)}%
                    </Text>
                )}
            </View>
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    icon: {
        marginStart: 4,
    },
    textContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 6,
    },
    valueText: {
        fontWeight: '700',
        fontFamily: 'monospace',
    },
    percentageText: {
        fontWeight: '600',
        opacity: 0.9,
    },
});

export default ProfitLossIndicator;
