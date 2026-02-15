/**
 * 🎨 شعار 1B Trading - البساطة الأنيقة
 * الشعار الرسمي المعتمد للتطبيق
 *
 * الاستخدام:
 * import { Logo, LogoMini, LogoMono, LogoOutline } from '../assets/logo/Logo';
 * <Logo size={100} />
 * <LogoMini size={40} />
 */

import React from 'react';
import { View } from 'react-native';
import Svg, {
    Path,
    Circle,
    Rect,
    Defs,
    LinearGradient,
    Stop,
    Text as SvgText,
    G,
} from 'react-native-svg';

// ألوان الهوية البصرية
const BRAND_COLORS = {
    primary: '#8B5CF6',      // البنفسجي الرئيسي
    secondary: '#06B6D4',    // السماوي
    success: '#10B981',      // الأخضر (ربح)
    error: '#EF4444',        // الأحمر (خسارة)
    warning: '#F59E0B',      // الذهبي
    white: '#FFFFFF',
    dark: '#0F0F23',
};

/**
 * الشعار الرئيسي الكامل
 * يتضمن التدرج اللوني وخط البيان الصاعد
 */
export const Logo = ({ size = 100, style }) => (
    <View style={style}>
        <Svg width={size} height={size} viewBox="0 0 200 200" fill="none">
            <Defs>
                <LinearGradient id="logoGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <Stop offset="0%" stopColor={BRAND_COLORS.primary} />
                    <Stop offset="100%" stopColor={BRAND_COLORS.secondary} />
                </LinearGradient>
            </Defs>
            {/* الخلفية المستديرة */}
            <Rect x="30" y="30" width="140" height="140" rx="30" fill="url(#logoGradient)" />
            {/* الرقم 1 */}
            <SvgText
                x="75"
                y="130"
                fill={BRAND_COLORS.white}
                fontSize="80"
                fontWeight="bold"
                fontFamily="Arial"
            >
                1
            </SvgText>
            {/* الحرف B مع خط البيان */}
            <G>
                <SvgText
                    x="105"
                    y="130"
                    fill={BRAND_COLORS.white}
                    fontSize="80"
                    fontWeight="bold"
                    fontFamily="Arial"
                >
                    B
                </SvgText>
                {/* خط البيان الصاعد */}
                <Path
                    d="M115 75 L125 65 L135 70 L145 60"
                    fill="none"
                    stroke={BRAND_COLORS.success}
                    strokeWidth="4"
                    strokeLinecap="round"
                />
                {/* نقطة النهاية */}
                <Circle cx="145" cy="60" r="5" fill={BRAND_COLORS.success} />
            </G>
        </Svg>
    </View>
);

/**
 * الشعار المصغر
 * للاستخدام في الهيدر والتبويبات
 */
export const LogoMini = ({ size = 40, style }) => (
    <View style={style}>
        <Svg width={size} height={size} viewBox="0 0 200 200" fill="none">
            <Defs>
                <LinearGradient id="logoMiniGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                    <Stop offset="0%" stopColor={BRAND_COLORS.primary} />
                    <Stop offset="100%" stopColor={BRAND_COLORS.secondary} />
                </LinearGradient>
            </Defs>
            <Rect x="30" y="30" width="140" height="140" rx="30" fill="url(#logoMiniGradient)" />
            <SvgText x="75" y="130" fill={BRAND_COLORS.white} fontSize="80" fontWeight="bold" fontFamily="Arial">1</SvgText>
            <SvgText x="115" y="130" fill={BRAND_COLORS.white} fontSize="80" fontWeight="bold" fontFamily="Arial">B</SvgText>
        </Svg>
    </View>
);

/**
 * الشعار أحادي اللون
 * للاستخدام على خلفيات ملونة
 */
export const LogoMono = ({ size = 100, color = BRAND_COLORS.primary, style }) => (
    <View style={style}>
        <Svg width={size} height={size} viewBox="0 0 200 200" fill="none">
            <Rect x="30" y="30" width="140" height="140" rx="30" fill={color} />
            <SvgText x="75" y="130" fill={BRAND_COLORS.white} fontSize="80" fontWeight="bold" fontFamily="Arial">1</SvgText>
            <SvgText x="115" y="130" fill={BRAND_COLORS.white} fontSize="80" fontWeight="bold" fontFamily="Arial">B</SvgText>
        </Svg>
    </View>
);

/**
 * الشعار بخط فقط (Outline)
 * للاستخدام على خلفيات داكنة
 */
export const LogoOutline = ({ size = 100, style }) => (
    <View style={style}>
        <Svg width={size} height={size} viewBox="0 0 200 200" fill="none">
            <Rect x="30" y="30" width="140" height="140" rx="30" fill="none" stroke={BRAND_COLORS.primary} strokeWidth="4" />
            <SvgText x="75" y="130" fill={BRAND_COLORS.primary} fontSize="80" fontWeight="bold" fontFamily="Arial">1</SvgText>
            <SvgText x="115" y="130" fill={BRAND_COLORS.secondary} fontSize="80" fontWeight="bold" fontFamily="Arial">B</SvgText>
        </Svg>
    </View>
);

/**
 * الشعار الأبيض
 * للاستخدام على خلفيات ملونة أو صور
 */
export const LogoWhite = ({ size = 100, style }) => (
    <View style={style}>
        <Svg width={size} height={size} viewBox="0 0 200 200" fill="none">
            <Rect x="30" y="30" width="140" height="140" rx="30" fill={BRAND_COLORS.white} opacity="0.2" />
            <Rect x="30" y="30" width="140" height="140" rx="30" fill="none" stroke={BRAND_COLORS.white} strokeWidth="3" />
            <SvgText x="75" y="130" fill={BRAND_COLORS.white} fontSize="80" fontWeight="bold" fontFamily="Arial">1</SvgText>
            <SvgText x="115" y="130" fill={BRAND_COLORS.white} fontSize="80" fontWeight="bold" fontFamily="Arial">B</SvgText>
        </Svg>
    </View>
);

// تصدير الألوان للاستخدام في أماكن أخرى
export { BRAND_COLORS };

// تصدير افتراضي
export default Logo;
