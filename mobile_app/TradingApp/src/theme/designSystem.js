/**
 * 🎨 Design System - نظام التصميم الموحد
 * ✅ هوية بصرية احترافية ومتناسقة
 * ✅ 8-pt Grid System
 * ✅ Typography Scale
 * ✅ Color Tokens
 * ✅ Component Tokens
 */

import { Dimensions, Platform } from 'react-native';

const { width: SCREEN_WIDTH, height: SCREEN_HEIGHT } = Dimensions.get('window');

// ═══════════════════════════════════════════════════════════════
// 🎨 COLOR PALETTE - لوحة الألوان الموحدة
// ═══════════════════════════════════════════════════════════════

export const colors = {
    // ─── Brand Colors ───────────────────────────────────────────
    brand: {
        primary: '#8B5CF6',      // البنفسجي الرئيسي
        primaryDark: '#7C3AED',
        primaryLight: '#A78BFA',
        secondary: '#EC4899',    // الوردي
        accent: '#06B6D4',       // السماوي
    },

    // ─── Semantic Colors ────────────────────────────────────────
    semantic: {
        success: '#10B981',
        successLight: '#34D399',
        successDark: '#059669',
        warning: '#F59E0B',
        warningLight: '#FBBF24',
        warningDark: '#D97706',
        error: '#EF4444',
        errorLight: '#F87171',
        errorDark: '#DC2626',
        info: '#3B82F6',
    },

    // ─── Background Colors ──────────────────────────────────────
    background: {
        primary: '#0D0D12',      // الخلفية الرئيسية
        secondary: '#13131A',    // الخلفية الثانوية
        tertiary: '#1A1A24',     // الخلفية الثالثة
        card: '#1F1F2E',         // خلفية البطاقات
        elevated: '#252530',     // خلفية مرتفعة
    },

    // ─── Text Colors ────────────────────────────────────────────
    text: {
        primary: '#FFFFFF',      // النص الرئيسي
        secondary: '#A1A1AA',    // النص الثانوي (تباين 5.5:1)
        tertiary: '#71717A',     // النص الثالث
        disabled: '#52525B',     // النص المعطل
        inverse: '#0D0D12',      // النص المعكوس
    },

    // ─── Border Colors ──────────────────────────────────────────
    border: {
        default: '#2A2A3C',
        light: '#3D3D52',
        focus: '#8B5CF6',
    },

    // ─── Overlay Colors ─────────────────────────────────────────
    overlay: {
        light: 'rgba(255, 255, 255, 0.05)',
        medium: 'rgba(255, 255, 255, 0.10)',
        dark: 'rgba(0, 0, 0, 0.50)',
    },
};

// ═══════════════════════════════════════════════════════════════
// 📐 SPACING - نظام المسافات (8-pt Grid)
// ═══════════════════════════════════════════════════════════════

export const spacing = {
    none: 0,
    xxs: 2,
    xs: 4,
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
    xxl: 32,
    xxxl: 48,
    huge: 64,
};

// ═══════════════════════════════════════════════════════════════
// 🔤 TYPOGRAPHY - نظام الخطوط
// ═══════════════════════════════════════════════════════════════

export const typography = {
    // ─── Font Families ──────────────────────────────────────────
    fontFamily: {
        regular: Platform.select({ ios: 'System', android: 'Roboto' }),
        medium: Platform.select({ ios: 'System', android: 'Roboto-Medium' }),
        bold: Platform.select({ ios: 'System', android: 'Roboto-Bold' }),
    },

    // ─── Font Sizes (Modular Scale 1.25) ────────────────────────
    size: {
        xs: 11,      // التفاصيل الصغيرة
        sm: 13,      // النص الثانوي
        base: 15,    // النص الأساسي
        md: 17,      // النص المتوسط
        lg: 20,      // العناوين الصغيرة
        xl: 24,      // العناوين المتوسطة
        xxl: 30,     // العناوين الكبيرة
        hero: 38,    // الأرقام الرئيسية
    },

    // ─── Font Sizes Alias (للتوافق مع theme.js) ─────────────────
    fontSize: {
        xs: 11,
        sm: 13,
        base: 15,
        md: 17,
        lg: 20,
        xl: 24,
        xxl: 30,
        xxxl: 38,
    },

    // ─── Font Weights ───────────────────────────────────────────
    weight: {
        regular: '400',
        medium: '500',
        semibold: '600',
        bold: '700',
    },

    // ─── Line Heights ───────────────────────────────────────────
    lineHeight: {
        tight: 1.2,
        normal: 1.5,
        relaxed: 1.75,
    },

    // ─── Letter Spacing ─────────────────────────────────────────
    letterSpacing: {
        tight: -0.5,
        normal: 0,
        wide: 0.5,
    },
};

// ─── Typography Presets ─────────────────────────────────────────
export const textStyles = {
    // Hero - للأرقام الرئيسية (الرصيد)
    hero: {
        fontSize: 36,
        fontWeight: '700',
        letterSpacing: -0.5,
        color: '#FFFFFF',
    },
    // H1 - للعناوين الكبيرة
    h1: {
        fontSize: 28,
        fontWeight: '700',
        letterSpacing: -0.5,
        color: '#FFFFFF',
    },
    // H2 - للعناوين المتوسطة
    h2: {
        fontSize: 22,
        fontWeight: '600',
        color: '#FFFFFF',
    },
    // H3 - للعناوين الصغيرة
    h3: {
        fontSize: 18,
        fontWeight: '600',
        color: '#FFFFFF',
    },
    // Body - للنص الأساسي
    body: {
        fontSize: 15,
        fontWeight: '400',
        lineHeight: 22.5,
        color: '#FFFFFF',
    },
    // Body Small - للنص الثانوي
    bodySmall: {
        fontSize: 13,
        fontWeight: '400',
        lineHeight: 19.5,
        color: '#A1A1AA',
    },
    // Caption - للتفاصيل
    caption: {
        fontSize: 11,
        fontWeight: '400',
        color: '#71717A',
    },
    // Label - للتسميات
    label: {
        fontSize: 13,
        fontWeight: '500',
        color: '#A1A1AA',
        textTransform: 'uppercase',
        letterSpacing: 0.5,
    },
};

// ═══════════════════════════════════════════════════════════════
// 📦 COMPONENT TOKENS - رموز المكونات
// ═══════════════════════════════════════════════════════════════

export const components = {
    // ─── Card ───────────────────────────────────────────────────
    card: {
        borderRadius: 16,
        padding: 16,
        backgroundColor: '#1F1F2E',
        borderWidth: 1,
        borderColor: '#2A2A3C',
        shadow: {
            shadowColor: '#000000',
            shadowOffset: { width: 0, height: 4 },
            shadowOpacity: 0.15,
            shadowRadius: 12,
            elevation: 4,
        },
    },

    // ─── Button ─────────────────────────────────────────────────
    button: {
        primary: {
            height: 52,
            borderRadius: 14,
            backgroundColor: '#8B5CF6',
            paddingHorizontal: 24,
        },
        secondary: {
            height: 46,
            borderRadius: 12,
            backgroundColor: 'transparent',
            borderWidth: 1.5,
            borderColor: '#8B5CF6',
            paddingHorizontal: 16,
        },
        small: {
            height: 36,
            borderRadius: 8,
            paddingHorizontal: 12,
        },
    },

    // ─── Input ──────────────────────────────────────────────────
    input: {
        height: 52,
        borderRadius: 12,
        backgroundColor: '#13131A',
        borderWidth: 1,
        borderColor: '#2A2A3C',
        paddingHorizontal: 16,
        fontSize: 15,
    },

    // ─── Header ─────────────────────────────────────────────────
    header: {
        height: 56,
        paddingHorizontal: 16,
        backgroundColor: '#0D0D12',
        borderBottomWidth: 1,
        borderBottomColor: '#2A2A3C',
    },

    // ─── Tab Bar ────────────────────────────────────────────────
    tabBar: {
        height: 64,
        backgroundColor: '#13131A',
        borderTopWidth: 1,
        borderTopColor: '#2A2A3C',
    },

    // ─── Icon Button ────────────────────────────────────────────
    iconButton: {
        size: 44,
        borderRadius: 22,
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
    },

    // ─── Badge ──────────────────────────────────────────────────
    badge: {
        height: 24,
        minWidth: 24,
        borderRadius: 12,
        paddingHorizontal: 8,
    },

    // ─── Divider ────────────────────────────────────────────────
    divider: {
        height: 1,
        backgroundColor: '#2A2A3C',
        marginVertical: 12,
    },

    // ─── List Item ──────────────────────────────────────────────
    listItem: {
        height: 56,
        paddingHorizontal: 16,
        backgroundColor: '#1F1F2E',
    },
};

// ═══════════════════════════════════════════════════════════════
// 🎭 SHADOWS - الظلال
// ═══════════════════════════════════════════════════════════════

export const shadows = {
    none: {},
    sm: {
        shadowColor: '#000000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 2,
        elevation: 1,
    },
    md: {
        shadowColor: '#000000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.15,
        shadowRadius: 8,
        elevation: 4,
    },
    lg: {
        shadowColor: '#000000',
        shadowOffset: { width: 0, height: 8 },
        shadowOpacity: 0.2,
        shadowRadius: 16,
        elevation: 8,
    },
    glow: {
        shadowColor: '#8B5CF6',
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0.4,
        shadowRadius: 20,
        elevation: 0,
    },
};

// ═══════════════════════════════════════════════════════════════
// 📱 RESPONSIVE - الاستجابة
// ═══════════════════════════════════════════════════════════════

export const responsive = {
    screenWidth: SCREEN_WIDTH,
    screenHeight: SCREEN_HEIGHT,
    isSmallDevice: SCREEN_WIDTH < 375,
    isMediumDevice: SCREEN_WIDTH >= 375 && SCREEN_WIDTH < 414,
    isLargeDevice: SCREEN_WIDTH >= 414,

    // دالة لحساب القيم المتجاوبة
    scale: (size) => (SCREEN_WIDTH / 375) * size,
    verticalScale: (size) => (SCREEN_HEIGHT / 812) * size,
    moderateScale: (size, factor = 0.5) => size + (responsive.scale(size) - size) * factor,
};

// ═══════════════════════════════════════════════════════════════
// 🎨 GRADIENTS - التدرجات
// ═══════════════════════════════════════════════════════════════

export const gradients = {
    primary: ['#8B5CF6', '#EC4899'],
    secondary: ['#EC4899', '#F472B6'],
    accent: ['#06B6D4', '#8B5CF6'],
    success: ['#10B981', '#059669'],
    error: ['#EF4444', '#DC2626'],
    dark: ['#1A1A24', '#0D0D12'],
    card: ['#1F1F2E', '#13131A'],
};

// ═══════════════════════════════════════════════════════════════
// 🔧 UTILITIES - أدوات مساعدة
// ═══════════════════════════════════════════════════════════════

export const utils = {
    // إنشاء ظل مخصص
    createShadow: (color, opacity, radius, offset = { width: 0, height: 4 }) => ({
        shadowColor: color,
        shadowOffset: offset,
        shadowOpacity: opacity,
        shadowRadius: radius,
        elevation: Math.round(radius / 2),
    }),

    // إنشاء حد ملون
    createBorder: (color, width = 1) => ({
        borderWidth: width,
        borderColor: color,
    }),

    // الحصول على لون حسب الحالة
    getStatusColor: (status) => {
        switch (status) {
            case 'success': return '#10B981';
            case 'warning': return '#F59E0B';
            case 'error': return '#EF4444';
            case 'info': return '#3B82F6';
            default: return '#A1A1AA';
        }
    },

    // الحصول على لون الربح/الخسارة
    getPnLColor: (value) => {
        const numValue = parseFloat(value);
        if (numValue > 0) {return '#10B981';}
        if (numValue < 0) {return '#EF4444';}
        return '#A1A1AA';
    },
};

// ═══════════════════════════════════════════════════════════════
// 📤 EXPORT - التصدير الموحد
// ═══════════════════════════════════════════════════════════════

const designSystem = {
    colors,
    spacing,
    typography,
    textStyles,
    components,
    shadows,
    responsive,
    gradients,
    utils,
};

export default designSystem;
