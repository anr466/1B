/**
 * 🎨 الشعار الموحد للتطبيق - 1B Trading
 * المصدر الوحيد للشعار - يضمن التوحيد في جميع الشاشات
 * ✅ شعار "البساطة الأنيقة" المعتمد (SVG)
 */

import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import Svg, { Path, Circle, Rect, Defs, LinearGradient, Stop, Text as SvgText, G } from 'react-native-svg';
import { theme } from '../theme/theme';

// ✅ ألوان مستمدة من الثيم الحالي - متوافقة مع theme.js
export const BRAND_COLORS = {
    // الألوان الأساسية للعلامة التجارية
    gold: '#D4AF37',                    // الذهبي الرئيسي
    goldLight: '#FCD34D',
    goldDark: '#B45309',

    // من الثيم
    purple: theme.colors.primary,       // #8B5CF6
    purpleLight: theme.colors.primaryLight, // #A78BFA
    purpleDark: theme.colors.primaryDark,   // #7C3AED

    // ألوان إضافية
    cyan: theme.colors.accent,          // #06B6D4
    background: theme.colors.background, // #0D0D12
    text: theme.colors.text,            // #FFFFFF
    textSecondary: theme.colors.textSecondary, // #9CA3AF
};

// 🎨 مكون الشعار SVG الجديد
const LogoSVG = ({ size = 100, withChart = true }) => (
    <Svg width={size} height={size} viewBox="0 0 200 200" fill="none">
        <Defs>
            <LinearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <Stop offset="0%" stopColor="#8B5CF6" />
                <Stop offset="100%" stopColor="#06B6D4" />
            </LinearGradient>
        </Defs>
        {/* الخلفية المستديرة */}
        <Rect x="30" y="30" width="140" height="140" rx="30" fill="url(#logoGradient)" />
        {/* الرقم 1 */}
        <SvgText x="75" y="130" fill="#FFFFFF" fontSize="80" fontWeight="bold" fontFamily="Arial">1</SvgText>
        {/* الحرف B مع خط البيان */}
        <G>
            <SvgText x="105" y="130" fill="#FFFFFF" fontSize="80" fontWeight="bold" fontFamily="Arial">B</SvgText>
            {withChart && (
                <>
                    <Path d="M115 75 L125 65 L135 70 L145 60" fill="none" stroke="#10B981" strokeWidth="4" strokeLinecap="round" />
                    <Circle cx="145" cy="60" r="5" fill="#10B981" />
                </>
            )}
        </G>
    </Svg>
);

const UnifiedBrandLogo = ({
    variant = 'header',
    size,
    showText = false,
    textOnly = false,  // عرض النص فقط بدون الصورة
    onPress,
    style,
}) => {
    // أحجام مختلفة حسب مكان الاستخدام
    const sizes = {
        splash: { logo: 180, fontSize: 32, textMargin: 15 },   // شاشة البداية
        auth: { logo: 120, fontSize: 24, textMargin: 12 },     // شاشات المصادقة
        header: { logo: 36, fontSize: 16, textMargin: 8 },     // الهيدر
        profile: { logo: 45, fontSize: 14, textMargin: 8 },    // صفحة الملف الشخصي
        icon: { logo: 50, fontSize: 0, textMargin: 0 },        // أيقونة فقط
        mini: { logo: 28, fontSize: 12, textMargin: 6 },       // صغير جداً
    };

    const s = sizes[variant] || sizes.header;
    const logoSize = size || s.logo;

    // حساب حجم الخط بناءً على الحجم
    const fontSize = s.fontSize || Math.max(12, logoSize * 0.4);
    const textMargin = s.textMargin || 8;

    const content = (
        <View style={[styles.container, style]}>
            {/* الشعار SVG */}
            {!textOnly && (
                <View style={styles.logoContainer}>
                    <LogoSVG size={logoSize} withChart={variant === 'splash' || variant === 'auth'} />
                </View>
            )}

            {/* النص */}
            {showText && (
                <View style={[styles.textContainer, { marginLeft: textOnly ? 0 : textMargin }]}>
                    <Text style={[styles.brandText, { fontSize }]}>
                        <Text style={styles.gold}>1</Text>
                        <Text style={styles.purple}>B</Text>
                    </Text>
                    {variant === 'splash' && (
                        <Text style={[styles.subText, { fontSize: fontSize * 0.5 }]}>
                            Trading
                        </Text>
                    )}
                </View>
            )}
        </View>
    );

    if (onPress) {
        return <TouchableOpacity onPress={onPress} activeOpacity={0.8}>{content}</TouchableOpacity>;
    }
    return content;
};

const styles = StyleSheet.create({
    container: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
    },
    logoContainer: {
        alignItems: 'center',
        justifyContent: 'center',
    },
    textContainer: {
        alignItems: 'flex-start',
    },
    brandText: {
        fontWeight: '900',
        letterSpacing: 1,
    },
    gold: {
        color: BRAND_COLORS.gold,
        textShadowColor: 'rgba(212, 175, 55, 0.3)',
        textShadowOffset: { width: 0, height: 1 },
        textShadowRadius: 4,
    },
    purple: {
        color: BRAND_COLORS.purple,
        textShadowColor: 'rgba(139, 92, 246, 0.3)',
        textShadowOffset: { width: 0, height: 1 },
        textShadowRadius: 4,
    },
    subText: {
        color: BRAND_COLORS.textSecondary,
        fontWeight: '500',
        letterSpacing: 2,
        marginTop: -2,
    },
});

export default UnifiedBrandLogo;
