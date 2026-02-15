/**
 * أيقونات أوضاع التداول المصممة
 * أيقونات احترافية مخصصة لـ Demo و Real
 * تصميم SVG بسيط وفعال
 */

import React from 'react';
import { View, StyleSheet } from 'react-native';
import Svg, { Circle, Path, Line, Rect } from 'react-native-svg';

/**
 * أيقونة الوضع الوهمي (Demo)
 * تمثل المحاكاة والاختبار
 */
export const DemoModeIcon = ({ size = 32, color = '#3B82F6' }) => {
    return (
        <View style={[styles.iconContainer, { width: size, height: size }]}>
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                {/* الدائرة الخارجية */}
                <Circle cx="12" cy="12" r="10" stroke={color} strokeWidth="1.5" />

                {/* السهم الدوار (يشير للدوران/المحاكاة) */}
                <Path
                    d="M12 4C7.58 4 4 7.58 4 12C4 16.42 7.58 20 12 20"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                    fill="none"
                />

                {/* رأس السهم */}
                <Path
                    d="M14 6L12 4L13 7"
                    fill={color}
                    stroke={color}
                    strokeWidth="1"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />

                {/* النقطة في المركز */}
                <Circle cx="12" cy="12" r="2" fill={color} />
            </Svg>
        </View>
    );
};

/**
 * أيقونة الوضع الحقيقي (Real)
 * تمثل التداول الحقيقي والخطورة
 */
export const RealModeIcon = ({ size = 32, color = '#10B981' }) => {
    return (
        <View style={[styles.iconContainer, { width: size, height: size }]}>
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                {/* المثلث الخارجي (تحذير) */}
                <Path
                    d="M12 2L22 20H2L12 2Z"
                    stroke={color}
                    strokeWidth="1.5"
                    fill="none"
                />

                {/* النقطة في المركز (خطر) */}
                <Circle cx="12" cy="15" r="1.5" fill={color} />

                {/* الخط العمودي (تحذير) */}
                <Line
                    x1="12"
                    y1="8"
                    x2="12"
                    y2="12"
                    stroke={color}
                    strokeWidth="1.5"
                    strokeLinecap="round"
                />
            </Svg>
        </View>
    );
};

/**
 * أيقونة التبديل بين الأوضاع
 * تمثل الانتقال من وضع لآخر
 */
export const ToggleModeIcon = ({ size = 32, color = '#F59E0B' }) => {
    return (
        <View style={[styles.iconContainer, { width: size, height: size }]}>
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                {/* الخط الأفقي */}
                <Line
                    x1="2"
                    y1="12"
                    x2="22"
                    y2="12"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                />

                {/* السهم الأيسر */}
                <Path
                    d="M6 8L2 12L6 16"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                />

                {/* السهم الأيمن */}
                <Path
                    d="M18 8L22 12L18 16"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                />
            </Svg>
        </View>
    );
};

/**
 * أيقونة المحفظة الوهمية
 * تمثل المحفظة التجريبية
 */
export const DemoPortfolioIcon = ({ size = 32, color = '#3B82F6' }) => {
    return (
        <View style={[styles.iconContainer, { width: size, height: size }]}>
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                {/* المحفظة */}
                <Rect x="3" y="6" width="18" height="14" rx="2" stroke={color} strokeWidth="1.5" />

                {/* الخط العلوي */}
                <Line x1="3" y1="10" x2="21" y2="10" stroke={color} strokeWidth="1.5" />

                {/* الدائرة (رمز الاختبار) */}
                <Circle cx="17" cy="15" r="2" fill={color} />

                {/* النقطتان (رمز المحاكاة) */}
                <Circle cx="7" cy="15" r="1" fill={color} />
                <Circle cx="11" cy="15" r="1" fill={color} />
            </Svg>
        </View>
    );
};

/**
 * أيقونة المحفظة الحقيقية
 * تمثل المحفظة الحقيقية مع Binance
 */
export const RealPortfolioIcon = ({ size = 32, color = '#10B981' }) => {
    return (
        <View style={[styles.iconContainer, { width: size, height: size }]}>
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                {/* المحفظة */}
                <Rect x="3" y="6" width="18" height="14" rx="2" stroke={color} strokeWidth="1.5" />

                {/* الخط العلوي */}
                <Line x1="3" y1="10" x2="21" y2="10" stroke={color} strokeWidth="1.5" />

                {/* علامة الصح (النجاح) */}
                <Path
                    d="M7 15L9 17L13 13"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                />

                {/* النقطة (الحقيقية) */}
                <Circle cx="17" cy="15" r="2" fill={color} />
            </Svg>
        </View>
    );
};

/**
 * أيقونة البيانات الوهمية
 * تمثل البيانات التجريبية
 */
export const DemoDataIcon = ({ size = 32, color = '#3B82F6' }) => {
    return (
        <View style={[styles.iconContainer, { width: size, height: size }]}>
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                {/* الرسم البياني */}
                <Rect x="2" y="4" width="20" height="16" rx="1" stroke={color} strokeWidth="1.5" />

                {/* الأعمدة (بيانات) */}
                <Line x1="6" y1="14" x2="6" y2="18" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
                <Line x1="10" y1="10" x2="10" y2="18" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
                <Line x1="14" y1="12" x2="14" y2="18" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
                <Line x1="18" y1="8" x2="18" y2="18" stroke={color} strokeWidth="1.5" strokeLinecap="round" />

                {/* علامة الاختبار (X) */}
                <Path
                    d="M8 6L10 8M10 6L8 8"
                    stroke={color}
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
            </Svg>
        </View>
    );
};

/**
 * أيقونة البيانات الحقيقية
 * تمثل بيانات Binance الحقيقية
 */
export const RealDataIcon = ({ size = 32, color = '#10B981' }) => {
    return (
        <View style={[styles.iconContainer, { width: size, height: size }]}>
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                {/* الرسم البياني */}
                <Rect x="2" y="4" width="20" height="16" rx="1" stroke={color} strokeWidth="1.5" />

                {/* الأعمدة (بيانات صاعدة) */}
                <Line x1="6" y1="14" x2="6" y2="18" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
                <Line x1="10" y1="10" x2="10" y2="18" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
                <Line x1="14" y1="8" x2="14" y2="18" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
                <Line x1="18" y1="6" x2="18" y2="18" stroke={color} strokeWidth="1.5" strokeLinecap="round" />

                {/* علامة الصح (النجاح) */}
                <Path
                    d="M8 6L9 7L11 5"
                    stroke={color}
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                />
            </Svg>
        </View>
    );
};

/**
 * أيقونة التحذير
 * تمثل التحذير من التداول الحقيقي
 */
export const WarningIcon = ({ size = 32, color = '#F59E0B' }) => {
    return (
        <View style={[styles.iconContainer, { width: size, height: size }]}>
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                {/* المثلث */}
                <Path
                    d="M12 2L22 20H2L12 2Z"
                    stroke={color}
                    strokeWidth="1.5"
                    fill="none"
                />

                {/* النقطة */}
                <Circle cx="12" cy="15" r="1.5" fill={color} />

                {/* الخط */}
                <Line
                    x1="12"
                    y1="8"
                    x2="12"
                    y2="12"
                    stroke={color}
                    strokeWidth="1.5"
                    strokeLinecap="round"
                />
            </Svg>
        </View>
    );
};

/**
 * أيقونة النجاح
 * تمثل النجاح والتأكيد
 */
export const SuccessIcon = ({ size = 32, color = '#10B981' }) => {
    return (
        <View style={[styles.iconContainer, { width: size, height: size }]}>
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                {/* الدائرة */}
                <Circle cx="12" cy="12" r="10" stroke={color} strokeWidth="1.5" />

                {/* علامة الصح */}
                <Path
                    d="M8 12L11 15L16 9"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                />
            </Svg>
        </View>
    );
};

const styles = StyleSheet.create({
    iconContainer: {
        justifyContent: 'center',
        alignItems: 'center',
    },
});

export default {
    DemoModeIcon,
    RealModeIcon,
    ToggleModeIcon,
    DemoPortfolioIcon,
    RealPortfolioIcon,
    DemoDataIcon,
    RealDataIcon,
    WarningIcon,
    SuccessIcon,
};
