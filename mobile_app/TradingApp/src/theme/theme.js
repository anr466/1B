/**
 * Theme Configuration - إعدادات التصميم والألوان
 * Dark theme with modern colors for Trading AI Bot
 * ✅ مستوحى من تصميم Stakent - بنفسجي أنيق
 */

export const theme = {
    // ==================== Colors ====================
    colors: {
        // Primary Colors - بنفسجي أنيق
        primary: '#8B5CF6',      // Purple Violet
        primaryDark: '#7C3AED',
        primaryLight: '#A78BFA',

        // Secondary Colors - وردي
        secondary: '#EC4899',    // Pink
        secondaryDark: '#DB2777',
        secondaryLight: '#F472B6',

        // Accent Color - سماوي
        accent: '#06B6D4',       // Cyan
        accentDark: '#0891B2',
        accentLight: '#22D3EE',

        // Success Colors - أخضر
        success: '#10B981',
        successDark: '#059669',
        successLight: '#34D399',

        // Warning Colors - برتقالي
        warning: '#F59E0B',
        warningDark: '#D97706',
        warningLight: '#FBBF24',

        // Error Colors - أحمر
        error: '#EF4444',
        errorDark: '#DC2626',
        errorLight: '#F87171',

        // Background Colors - أسود داكن
        background: '#0D0D12',   // Dark Background
        backgroundSecondary: '#13131A',
        backgroundTertiary: '#1A1A24',
        surface: '#1A1A24',      // Card Surface
        card: '#1F1F2E',         // Card Background

        // Text Colors - ✅ محسّن للتباين (WCAG AA)
        text: '#FFFFFF',
        textSecondary: '#A1A1AA',    // تباين 5.5:1 ✅
        textTertiary: '#8B8B96',     // تباين 4.5:1 ✅ (كان #6B7280)

        // Info Color
        info: '#3B82F6',         // Blue

        // Border Colors
        border: '#2A2A3C',
        borderLight: '#3D3D52',

        // Special Colors
        transparent: 'transparent',
        white: '#FFFFFF',
        black: '#000000',

        // Chart Colors - ألوان الرسوم البيانية
        chartLine: '#8B5CF6',
        chartGradientStart: '#8B5CF6',
        chartGradientEnd: '#8B5CF600',
        chartGrid: '#2A2A3C',

        // Gradients (Arrays of colors)
        gradientPrimary: ['#8B5CF6', '#EC4899'],     // Purple -> Pink
        gradientSecondary: ['#EC4899', '#F472B6'],   // Pink -> Light Pink
        gradientSuccess: ['#10B981', '#059669'],
        gradientError: ['#EF4444', '#DC2626'],
        gradientWarning: ['#F59E0B', '#D97706'],
        gradientAccent: ['#06B6D4', '#8B5CF6'],      // Cyan -> Purple
        gradientDark: ['#1A1A24', '#0D0D12'],
        gradientCard: ['#1F1F2E', '#13131A'],
    },

    // ==================== Brand Colors ====================
    brand: {
        primary: '#8B5CF6',      // Purple
        secondary: '#EC4899',    // Pink
        accent: '#06B6D4',       // Cyan
        success: '#10B981',      // Green
        background: '#0D0D12',   // Dark Background
        cardBg: '#1A1A24',       // Card Background
    },

    // ==================== Spacing ====================
    spacing: {
        xs: 4,
        sm: 8,
        md: 12,
        lg: 16,
        xl: 24,
        xxl: 32,
        xxxl: 48,
    },

    // ==================== Opacity ====================
    opacity: {
        disabled: 0.6,      // للعناصر المعطلة (buttons, inputs)
        hover: 0.8,         // للتفاعل (TouchableOpacity activeOpacity)
        secondary: 0.7,     // للعناصر الثانوية
        muted: 0.5,         // للعناصر الخافتة
        overlay: 0.4,       // للخلفيات الشفافة
    },

    // ==================== Typography ====================
    typography: {
        // Font Families
        fontFamily: {
            regular: 'System',
            medium: 'System',
            bold: 'System',
        },

        // Font Sizes - ✅ محسنة للقراءة
        fontSize: {
            xs: 11,      // L5: تفاصيل صغيرة (timestamps, hints)
            sm: 13,      // L4: ثانوي (labels, captions)
            base: 15,    // L3: عادي (body text)
            md: 16,      // L3: عادي+
            lg: 18,      // L2: مهم (section titles)
            xl: 22,      // L2: مهم+ (card titles)
            xxl: 28,     // L1: رئيسي (balances)
            xxxl: 36,    // L1: حرج (main balance)
        },

        // Font Weights
        fontWeight: {
            light: '300',
            regular: '400',
            medium: '500',
            semibold: '600',
            bold: '700',
            heavy: '800',
        },

        // Line Heights
        lineHeight: {
            tight: 1.2,
            normal: 1.5,
            relaxed: 1.75,
        },
    },

    // ==================== Visual Hierarchy (التسلسل الهرمي البصري) ====================
    // استخدم هذه الأنماط الجاهزة لضمان التناسق
    hierarchy: {
        // L1: العناصر الحرجة (الرصيد الرئيسي، أزرار الإجراء الرئيسية)
        hero: {
            fontSize: 36,
            fontWeight: '700',
            letterSpacing: -0.5,
        },
        // L1: العناصر الرئيسية (الأرقام المهمة، العناوين الكبيرة)
        primary: {
            fontSize: 28,
            fontWeight: '700',
            letterSpacing: -0.3,
        },
        // L2: العناصر المهمة (عناوين الأقسام، أسماء البطاقات)
        secondary: {
            fontSize: 18,
            fontWeight: '600',
            letterSpacing: 0,
        },
        // L3: المحتوى العادي (نص البطاقات، القيم)
        body: {
            fontSize: 15,
            fontWeight: '400',
            letterSpacing: 0.1,
        },
        // L4: العناصر الثانوية (التسميات، الوصف)
        caption: {
            fontSize: 13,
            fontWeight: '400',
            letterSpacing: 0.2,
        },
        // L5: التفاصيل الصغيرة (التواريخ، الملاحظات)
        tiny: {
            fontSize: 11,
            fontWeight: '300',
            letterSpacing: 0.3,
        },
    },

    // ==================== Button Hierarchy (تسلسل الأزرار) ====================
    buttonHierarchy: {
        // الزر الرئيسي (إجراء واحد مهم في الشاشة)
        primary: {
            minHeight: 52,
            fontSize: 17,
            fontWeight: '700',
            borderRadius: 14,
        },
        // الزر الثانوي (إجراءات إضافية)
        secondary: {
            minHeight: 46,
            fontSize: 15,
            fontWeight: '600',
            borderRadius: 12,
        },
        // الزر الصغير (إجراءات فرعية)
        tertiary: {
            minHeight: 40,
            fontSize: 14,
            fontWeight: '500',
            borderRadius: 10,
        },
        // رابط/نص قابل للنقر
        link: {
            fontSize: 14,
            fontWeight: '500',
        },
    },

    // ==================== Border Radius ====================
    borderRadius: {
        none: 0,
        sm: 4,
        md: 8,
        lg: 12,
        xl: 16,
        full: 999,
    },

    // ==================== Shadows ====================
    shadows: {
        sm: {
            shadowColor: '#000000',
            shadowOffset: { width: 0, height: 1 },
            shadowOpacity: 0.18,
            shadowRadius: 1.0,
            elevation: 1,
        },
        md: {
            shadowColor: '#000000',
            shadowOffset: { width: 0, height: 2 },
            shadowOpacity: 0.25,
            shadowRadius: 3.84,
            elevation: 5,
        },
        lg: {
            shadowColor: '#000000',
            shadowOffset: { width: 0, height: 4 },
            shadowOpacity: 0.3,
            shadowRadius: 4.65,
            elevation: 8,
        },
        xl: {
            shadowColor: '#000000',
            shadowOffset: { width: 0, height: 10 },
            shadowOpacity: 0.37,
            shadowRadius: 7.49,
            elevation: 12,
        },
    },

    // ==================== Responsive ====================
    responsive: {
        small: 320,
        medium: 375,
        large: 414,
        xlarge: 768,
    },

    // ==================== Opacity ====================
    opacity: {
        disabled: 0.6,      // للعناصر المعطلة
        hover: 0.8,         // للتفاعل
        secondary: 0.7,     // للعناصر الثانوية
        muted: 0.5,        // للعناصر الخافتة
    },
};

// ==================== Dark Mode ====================
export const darkMode = {
    ...theme,
    colors: {
        ...theme.colors,
        background: '#0A0E27',
        backgroundSecondary: '#1A1F3A',
        backgroundTertiary: '#252D4A',
        text: '#FFFFFF',
        textSecondary: '#B0B8D4',
    },
};

// ==================== Light Mode ====================
export const lightMode = {
    ...theme,
    colors: {
        ...theme.colors,
        background: '#FFFFFF',
        backgroundSecondary: '#F5F7FA',
        backgroundTertiary: '#EBEEF5',
        text: '#1A1F3A',
        textSecondary: '#5A6277',
        border: '#D5DDE8',
        borderLight: '#E5EBF5',
    },
};

export default theme;
