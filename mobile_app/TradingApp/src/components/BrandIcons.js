/**
 * 🎨 مكتبة الأيقونات المخصصة - 1B Trading
 * أيقونات SVG احترافية متناسقة مع الثيم
 * ✅ بدون مكتبات خارجية
 */

import React from 'react';
import { View, StyleSheet } from 'react-native';
import Svg, { Path, Circle, Rect, Defs, LinearGradient, Stop, Text as SvgText, G } from 'react-native-svg';
import { theme } from '../theme/theme';

// ألوان الأيقونات
const ICON_COLORS = {
    primary: theme.colors.primary,      // #8B5CF6
    gold: '#D4AF37',
    cyan: theme.colors.accent,          // #06B6D4
    success: theme.colors.success,      // #10B981
    error: theme.colors.error,          // #EF4444
    warning: theme.colors.warning,      // #F59E0B
    white: '#FFFFFF',
    gray: theme.colors.textSecondary,   // #9CA3AF
};

/**
 * مكون الأيقونة الرئيسي
 */
const BrandIcon = ({ name, size = 24, color = ICON_COLORS.white, style }) => {
    const icons = {
        // ═══════════════════════════════════════════════════════════
        // 🔔 أيقونة الإشعارات
        // ═══════════════════════════════════════════════════════════
        notification: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M12 2C10.9 2 10 2.9 10 4V4.29C7.03 5.17 5 7.9 5 11V17L3 19V20H21V19L19 17V11C19 7.9 16.97 5.17 14 4.29V4C14 2.9 13.1 2 12 2ZM12 22C13.1 22 14 21.1 14 20H10C10 21.1 10.9 22 12 22Z"
                    fill={color}
                />
                <Circle cx="18" cy="6" r="4" fill={ICON_COLORS.error} />
            </Svg>
        ),

        // 🔔 إشعارات بدون نقطة
        'notification-outline': (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M12 2C10.9 2 10 2.9 10 4V4.29C7.03 5.17 5 7.9 5 11V17L3 19V20H21V19L19 17V11C19 7.9 16.97 5.17 14 4.29V4C14 2.9 13.1 2 12 2ZM12 6C14.76 6 17 8.24 17 11V18H7V11C7 8.24 9.24 6 12 6ZM12 22C13.1 22 14 21.1 14 20H10C10 21.1 10.9 22 12 22Z"
                    fill={color}
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // ⚙️ أيقونة الإعدادات
        // ═══════════════════════════════════════════════════════════
        settings: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M12 15.5C13.93 15.5 15.5 13.93 15.5 12C15.5 10.07 13.93 8.5 12 8.5C10.07 8.5 8.5 10.07 8.5 12C8.5 13.93 10.07 15.5 12 15.5Z"
                    fill={color}
                />
                <Path
                    d="M19.43 12.98C19.47 12.66 19.5 12.34 19.5 12C19.5 11.66 19.47 11.34 19.43 11.02L21.54 9.37C21.73 9.22 21.78 8.95 21.66 8.73L19.66 5.27C19.54 5.05 19.27 4.97 19.05 5.05L16.56 6.05C16.04 5.65 15.48 5.32 14.87 5.07L14.49 2.42C14.46 2.18 14.25 2 14 2H10C9.75 2 9.54 2.18 9.51 2.42L9.13 5.07C8.52 5.32 7.96 5.66 7.44 6.05L4.95 5.05C4.72 4.96 4.46 5.05 4.34 5.27L2.34 8.73C2.21 8.95 2.27 9.22 2.46 9.37L4.57 11.02C4.53 11.34 4.5 11.67 4.5 12C4.5 12.33 4.53 12.66 4.57 12.98L2.46 14.63C2.27 14.78 2.21 15.05 2.34 15.27L4.34 18.73C4.46 18.95 4.73 19.03 4.95 18.95L7.44 17.95C7.96 18.35 8.52 18.68 9.13 18.93L9.51 21.58C9.54 21.82 9.75 22 10 22H14C14.25 22 14.46 21.82 14.49 21.58L14.87 18.93C15.48 18.68 16.04 18.34 16.56 17.95L19.05 18.95C19.28 19.04 19.54 18.95 19.66 18.73L21.66 15.27C21.78 15.05 21.73 14.78 21.54 14.63L19.43 12.98Z"
                    stroke={color}
                    strokeWidth="1.5"
                    fill="none"
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 👤 أيقونة المستخدم
        // ═══════════════════════════════════════════════════════════
        user: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Circle cx="12" cy="8" r="4" fill={color} />
                <Path
                    d="M12 14C8.13 14 5 16.13 5 19V21H19V19C19 16.13 15.87 14 12 14Z"
                    fill={color}
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 📊 أيقونة الرسم البياني
        // ═══════════════════════════════════════════════════════════
        chart: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Rect x="3" y="12" width="4" height="9" rx="1" fill={color} opacity="0.5" />
                <Rect x="10" y="8" width="4" height="13" rx="1" fill={color} opacity="0.7" />
                <Rect x="17" y="4" width="4" height="17" rx="1" fill={color} />
            </Svg>
        ),

        // 📈 خط الرسم البياني (المطلوب في NotificationsScreen)
        'chart-line': (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M3 12L9 6L13 10L21 2"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    fill="none"
                />
                <Circle cx="3" cy="12" r="2" fill={color} />
                <Circle cx="9" cy="6" r="2" fill={color} />
                <Circle cx="13" cy="10" r="2" fill={color} />
                <Circle cx="21" cy="2" r="2" fill={color} />
                <Path d="M3 20H21" stroke={color} strokeWidth="1" strokeLinecap="round" opacity="0.3" />
                <Path d="M3 16H21" stroke={color} strokeWidth="1" strokeLinecap="round" opacity="0.2" />
                <Path d="M3 8H21" stroke={color} strokeWidth="1" strokeLinecap="round" opacity="0.2" />
                <Path d="M3 4H21" stroke={color} strokeWidth="1" strokeLinecap="round" opacity="0.1" />
            </Svg>
        ),

        // 📈 صعود
        'trending-up': (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M16 6L18.29 8.29L13.41 13.17L9.41 9.17L2 16.59L3.41 18L9.41 12L13.41 16L19.71 9.71L22 12V6H16Z"
                    fill={ICON_COLORS.success}
                />
            </Svg>
        ),

        // 📉 هبوط
        'trending-down': (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M16 18L18.29 15.71L13.41 10.83L9.41 14.83L2 7.41L3.41 6L9.41 12L13.41 8L19.71 14.29L22 12V18H16Z"
                    fill={ICON_COLORS.error}
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 💼 أيقونة المحفظة
        // ═══════════════════════════════════════════════════════════
        wallet: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M21 7H3C2.45 7 2 7.45 2 8V19C2 19.55 2.45 20 3 20H21C21.55 20 22 19.55 22 19V8C22 7.45 21.55 7 21 7Z"
                    fill={color}
                    opacity="0.3"
                />
                <Path
                    d="M21 7V5C21 3.9 20.1 3 19 3H5C3.9 3 3 3.9 3 5V7"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                />
                <Circle cx="17" cy="13" r="2" fill={ICON_COLORS.gold} />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 🔒 أيقونة القفل
        // ═══════════════════════════════════════════════════════════
        lock: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Rect x="5" y="10" width="14" height="11" rx="2" fill={color} />
                <Path
                    d="M8 10V7C8 4.79 9.79 3 12 3C14.21 3 16 4.79 16 7V10"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                    fill="none"
                />
                <Circle cx="12" cy="15" r="1.5" fill={ICON_COLORS.gold} />
            </Svg>
        ),

        // 🔓 قفل مفتوح
        'lock-open': (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Rect x="5" y="10" width="14" height="11" rx="2" fill={color} />
                <Path
                    d="M8 10V7C8 4.79 9.79 3 12 3C13.5 3 14.77 3.8 15.5 5"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                    fill="none"
                />
                <Circle cx="12" cy="15" r="1.5" fill={ICON_COLORS.success} />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 👁️ أيقونة العين
        // ═══════════════════════════════════════════════════════════
        eye: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M12 4.5C7 4.5 2.73 7.61 1 12C2.73 16.39 7 19.5 12 19.5C17 19.5 21.27 16.39 23 12C21.27 7.61 17 4.5 12 4.5Z"
                    stroke={color}
                    strokeWidth="1.5"
                    fill="none"
                />
                <Circle cx="12" cy="12" r="3.5" fill={color} />
            </Svg>
        ),

        // 👁️‍🗨️ عين مغلقة
        'eye-off': (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M12 6.5C14.76 6.5 17 8.74 17 11.5C17 12.01 16.9 12.5 16.76 12.96L19.82 16.02C21.21 14.79 22.31 13.25 23 11.5C21.27 7.11 17 4 12 4C10.73 4 9.51 4.2 8.36 4.57L10.53 6.74C11 6.6 11.49 6.5 12 6.5Z"
                    fill={color}
                />
                <Path
                    d="M2 3.27L4.28 5.55L4.74 6.01C3.08 7.3 1.78 9.02 1 11C2.73 15.39 7 18.5 12 18.5C13.55 18.5 15.03 18.2 16.38 17.66L16.81 18.09L19.73 21L21 19.73L3.27 2L2 3.27ZM12 16.5C9.24 16.5 7 14.26 7 11.5C7 10.73 7.18 10 7.49 9.36L9.06 10.93C9.03 11.11 9 11.3 9 11.5C9 13.16 10.34 14.5 12 14.5C12.2 14.5 12.38 14.47 12.57 14.43L14.14 16C13.49 16.32 12.77 16.5 12 16.5Z"
                    fill={color}
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // ✉️ أيقونة البريد
        // ═══════════════════════════════════════════════════════════
        email: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Rect x="2" y="4" width="20" height="16" rx="2" fill={color} opacity="0.3" />
                <Path
                    d="M22 6L12 13L2 6"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // ← أيقونة السهم للخلف
        // ═══════════════════════════════════════════════════════════
        'arrow-back': (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M20 11H7.83L13.42 5.41L12 4L4 12L12 20L13.41 18.59L7.83 13H20V11Z"
                    fill={color}
                />
            </Svg>
        ),

        // → أيقونة السهم للأمام
        'arrow-forward': (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M4 13H16.17L10.58 18.59L12 20L20 12L12 4L10.59 5.41L16.17 11H4V13Z"
                    fill={color}
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // ✓ أيقونة الصح
        // ═══════════════════════════════════════════════════════════
        check: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M9 16.17L4.83 12L3.41 13.41L9 19L21 7L19.59 5.59L9 16.17Z"
                    fill={color}
                />
            </Svg>
        ),

        // ✓ دائرة مع صح
        'check-circle': (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Circle cx="12" cy="12" r="10" fill={ICON_COLORS.success} opacity="0.2" />
                <Circle cx="12" cy="12" r="10" stroke={ICON_COLORS.success} strokeWidth="1.5" fill="none" />
                <Path
                    d="M8 12L11 15L16 9"
                    stroke={ICON_COLORS.success}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // ✕ أيقونة الإغلاق
        // ═══════════════════════════════════════════════════════════
        close: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M19 6.41L17.59 5L12 10.59L6.41 5L5 6.41L10.59 12L5 17.59L6.41 19L12 13.41L17.59 19L19 17.59L13.41 12L19 6.41Z"
                    fill={color}
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 🔄 أيقونة التحديث
        // ═══════════════════════════════════════════════════════════
        refresh: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M17.65 6.35C16.2 4.9 14.21 4 12 4C7.58 4 4.01 7.58 4.01 12C4.01 16.42 7.58 20 12 20C15.73 20 18.84 17.45 19.73 14H17.65C16.83 16.33 14.61 18 12 18C8.69 18 6 15.31 6 12C6 8.69 8.69 6 12 6C13.66 6 15.14 6.69 16.22 7.78L13 11H20V4L17.65 6.35Z"
                    fill={color}
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // ⚠️ أيقونة التحذير
        // ═══════════════════════════════════════════════════════════
        warning: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M1 21H23L12 2L1 21Z"
                    fill={ICON_COLORS.warning}
                    opacity="0.2"
                />
                <Path
                    d="M1 21H23L12 2L1 21Z"
                    stroke={ICON_COLORS.warning}
                    strokeWidth="1.5"
                    strokeLinejoin="round"
                    fill="none"
                />
                <Path d="M12 9V13" stroke={ICON_COLORS.warning} strokeWidth="2" strokeLinecap="round" />
                <Circle cx="12" cy="17" r="1" fill={ICON_COLORS.warning} />
            </Svg>
        ),

        // ⚠️ مثلث تحذير (المطلوب في NotificationsScreen)
        'alert-triangle': (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M10.29 3.86L1.82 18C1.64 18.37 1.9 18.8 2.32 18.8H21.68C22.1 18.8 22.36 18.37 22.18 18L13.71 3.86C13.32 3.15 12.68 3.15 12.29 3.86L10.29 3.86Z"
                    fill={color}
                    opacity="0.2"
                />
                <Path
                    d="M10.29 3.86L1.82 18C1.64 18.37 1.9 18.8 2.32 18.8H21.68C22.1 18.8 22.36 18.37 22.18 18L13.71 3.86C13.32 3.15 12.68 3.15 12.29 3.86Z"
                    stroke={color}
                    strokeWidth="1.5"
                    strokeLinejoin="round"
                    fill="none"
                />
                <Path d="M12 9V13" stroke={color} strokeWidth="2" strokeLinecap="round" />
                <Circle cx="12" cy="17" r="1" fill={color} />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 🔑 أيقونة المفتاح
        // ═══════════════════════════════════════════════════════════
        key: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Circle cx="8" cy="10" r="5" stroke={color} strokeWidth="2" fill="none" />
                <Path
                    d="M12 10H21M21 10V14M17 10V13"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // ☰ أيقونة القائمة
        // ═══════════════════════════════════════════════════════════
        menu: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path d="M3 6H21" stroke={color} strokeWidth="2" strokeLinecap="round" />
                <Path d="M3 12H21" stroke={color} strokeWidth="2" strokeLinecap="round" />
                <Path d="M3 18H21" stroke={color} strokeWidth="2" strokeLinecap="round" />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 🔍 أيقونة البحث
        // ═══════════════════════════════════════════════════════════
        search: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Circle cx="11" cy="11" r="7" stroke={color} strokeWidth="2" fill="none" />
                <Path
                    d="M21 21L16.5 16.5"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // ➕ أيقونة الإضافة
        // ═══════════════════════════════════════════════════════════
        plus: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M12 5V19M5 12H19"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                />
            </Svg>
        ),

        // ➖ أيقونة الطرح
        minus: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M5 12H19"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 🏠 أيقونة الرئيسية
        // ═══════════════════════════════════════════════════════════
        home: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M3 12L12 3L21 12"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
                <Path
                    d="M5 10V19C5 19.55 5.45 20 6 20H9V14H15V20H18C18.55 20 19 19.55 19 19V10"
                    fill={color}
                    opacity="0.3"
                />
                <Path
                    d="M5 10V19C5 19.55 5.45 20 6 20H9V14H15V20H18C18.55 20 19 19.55 19 19V10"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 📱 أيقونة الهاتف
        // ═══════════════════════════════════════════════════════════
        phone: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M6.62 10.79C8.06 13.62 10.38 15.94 13.21 17.38L15.41 15.18C15.69 14.9 16.08 14.82 16.43 14.93C17.55 15.3 18.75 15.5 20 15.5C20.55 15.5 21 15.95 21 16.5V20C21 20.55 20.55 21 20 21C10.61 21 3 13.39 3 4C3 3.45 3.45 3 4 3H7.5C8.05 3 8.5 3.45 8.5 4C8.5 5.25 8.7 6.45 9.07 7.57C9.18 7.92 9.1 8.31 8.82 8.59L6.62 10.79Z"
                    fill={color}
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 🛡️ أيقونة الدرع/الأمان
        // ═══════════════════════════════════════════════════════════
        shield: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M12 2L4 5V11C4 16.55 7.84 21.74 12 23C16.16 21.74 20 16.55 20 11V5L12 2Z"
                    fill={color}
                    opacity="0.2"
                />
                <Path
                    d="M12 2L4 5V11C4 16.55 7.84 21.74 12 23C16.16 21.74 20 16.55 20 11V5L12 2Z"
                    stroke={color}
                    strokeWidth="1.5"
                    fill="none"
                />
                <Path
                    d="M9 12L11 14L15 10"
                    stroke={ICON_COLORS.success}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // ⭐ أيقونة النجمة
        // ═══════════════════════════════════════════════════════════
        star: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"
                    fill={ICON_COLORS.gold}
                />
            </Svg>
        ),

        // ⭐ نجمة فارغة
        'star-outline': (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"
                    stroke={color}
                    strokeWidth="1.5"
                    strokeLinejoin="round"
                    fill="none"
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 💳 أيقونة البطاقة
        // ═══════════════════════════════════════════════════════════
        card: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Rect x="2" y="4" width="20" height="16" rx="2" fill={color} opacity="0.2" />
                <Rect x="2" y="4" width="20" height="16" rx="2" stroke={color} strokeWidth="1.5" fill="none" />
                <Path d="M2 9H22" stroke={color} strokeWidth="1.5" />
                <Rect x="5" y="14" width="6" height="2" rx="1" fill={color} />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 🤖 أيقونة الروبوت/AI
        // ═══════════════════════════════════════════════════════════
        robot: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Rect x="4" y="6" width="16" height="14" rx="3" fill={color} opacity="0.2" />
                <Rect x="4" y="6" width="16" height="14" rx="3" stroke={color} strokeWidth="1.5" fill="none" />
                <Circle cx="9" cy="12" r="2" fill={ICON_COLORS.cyan} />
                <Circle cx="15" cy="12" r="2" fill={ICON_COLORS.cyan} />
                <Path d="M9 16H15" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
                <Path d="M12 2V6" stroke={color} strokeWidth="1.5" strokeLinecap="round" />
                <Circle cx="12" cy="2" r="1" fill={ICON_COLORS.gold} />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 📋 أيقونة القائمة/الصفقات
        // ═══════════════════════════════════════════════════════════
        list: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path d="M3 6H21" stroke={color} strokeWidth="2" strokeLinecap="round" />
                <Path d="M3 12H21" stroke={color} strokeWidth="2" strokeLinecap="round" />
                <Path d="M3 18H15" stroke={color} strokeWidth="2" strokeLinecap="round" />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 🎯 أيقونة الهدف
        // ═══════════════════════════════════════════════════════════
        target: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Circle cx="12" cy="12" r="9" stroke={color} strokeWidth="1.5" fill="none" />
                <Circle cx="12" cy="12" r="5" stroke={color} strokeWidth="1.5" fill="none" />
                <Circle cx="12" cy="12" r="2" fill={ICON_COLORS.error} />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 🔗 أيقونة الرابط
        // ═══════════════════════════════════════════════════════════
        link: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M10 13C10.87 13.87 12.13 13.87 13 13L17 9C17.87 8.13 17.87 6.87 17 6C16.13 5.13 14.87 5.13 14 6L13 7"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                />
                <Path
                    d="M14 11C13.13 10.13 11.87 10.13 11 11L7 15C6.13 15.87 6.13 17.13 7 18C7.87 18.87 9.13 18.87 10 18L11 17"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 📤 أيقونة الخروج
        // ═══════════════════════════════════════════════════════════
        logout: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M9 21H5C4.45 21 4 20.55 4 20V4C4 3.45 4.45 3 5 3H9"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                />
                <Path
                    d="M16 17L21 12L16 7"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
                <Path
                    d="M21 12H9"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 📥 أيقونة الدخول
        // ═══════════════════════════════════════════════════════════
        login: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M15 3H19C19.55 3 20 3.45 20 4V20C20 20.55 19.55 21 19 21H15"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                />
                <Path
                    d="M10 17L15 12L10 7"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
                <Path
                    d="M15 12H3"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 🔄 أيقونة التبديل
        // ═══════════════════════════════════════════════════════════
        swap: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M7 16L3 12L7 8"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
                <Path d="M3 12H15" stroke={color} strokeWidth="2" strokeLinecap="round" />
                <Path
                    d="M17 8L21 12L17 16"
                    stroke={color}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
                <Path d="M21 12H9" stroke={color} strokeWidth="2" strokeLinecap="round" />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // ℹ️ أيقونة المعلومات
        // ═══════════════════════════════════════════════════════════
        info: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Circle cx="12" cy="12" r="10" stroke={color} strokeWidth="1.5" fill="none" />
                <Path d="M12 16V12" stroke={color} strokeWidth="2" strokeLinecap="round" />
                <Circle cx="12" cy="8" r="1" fill={color} />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 📊 أيقونة لوحة التحكم
        // ═══════════════════════════════════════════════════════════
        dashboard: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Rect x="3" y="3" width="8" height="8" rx="2" fill={color} opacity="0.3" />
                <Rect x="3" y="3" width="8" height="8" rx="2" stroke={color} strokeWidth="1.5" fill="none" />
                <Rect x="13" y="3" width="8" height="5" rx="2" fill={color} opacity="0.3" />
                <Rect x="13" y="3" width="8" height="5" rx="2" stroke={color} strokeWidth="1.5" fill="none" />
                <Rect x="3" y="13" width="8" height="8" rx="2" fill={color} opacity="0.3" />
                <Rect x="3" y="13" width="8" height="8" rx="2" stroke={color} strokeWidth="1.5" fill="none" />
                <Rect x="13" y="10" width="8" height="11" rx="2" fill={color} opacity="0.3" />
                <Rect x="13" y="10" width="8" height="11" rx="2" stroke={color} strokeWidth="1.5" fill="none" />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 💰 أيقونة المحفظة البديلة
        // ═══════════════════════════════════════════════════════════
        'wallet-alt': (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Rect x="2" y="6" width="20" height="14" rx="2" fill={color} opacity="0.2" />
                <Rect x="2" y="6" width="20" height="14" rx="2" stroke={color} strokeWidth="1.5" />
                <Path d="M2 10H22" stroke={color} strokeWidth="1.5" />
                <Circle cx="17" cy="14" r="2" fill={color} />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 🕐 أيقونة السجل/التاريخ
        // ═══════════════════════════════════════════════════════════
        history: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Circle cx="12" cy="12" r="9" stroke={color} strokeWidth="1.5" fill="none" />
                <Path d="M12 7V12L15 15" stroke={color} strokeWidth="2" strokeLinecap="round" />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 🛡️ أيقونة الدرع/الأمان البديلة
        // ═══════════════════════════════════════════════════════════
        'shield-alt': (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M12 2L4 6V11C4 16.55 7.16 21.74 12 23C16.84 21.74 20 16.55 20 11V6L12 2Z"
                    fill={color}
                    opacity="0.2"
                />
                <Path
                    d="M12 2L4 6V11C4 16.55 7.16 21.74 12 23C16.84 21.74 20 16.55 20 11V6L12 2Z"
                    stroke={color}
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 📋 أيقونة القائمة البديلة
        // ═══════════════════════════════════════════════════════════
        'menu-alt': (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path d="M4 6H20" stroke={color} strokeWidth="2" strokeLinecap="round" />
                <Path d="M4 12H20" stroke={color} strokeWidth="2" strokeLinecap="round" />
                <Path d="M4 18H20" stroke={color} strokeWidth="2" strokeLinecap="round" />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 📝 أيقونة القائمة/السجل البديلة
        // ═══════════════════════════════════════════════════════════
        'list-alt': (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path d="M8 6H21" stroke={color} strokeWidth="2" strokeLinecap="round" />
                <Path d="M8 12H21" stroke={color} strokeWidth="2" strokeLinecap="round" />
                <Path d="M8 18H21" stroke={color} strokeWidth="2" strokeLinecap="round" />
                <Circle cx="4" cy="6" r="1.5" fill={color} />
                <Circle cx="4" cy="12" r="1.5" fill={color} />
                <Circle cx="4" cy="18" r="1.5" fill={color} />
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 🏷️ شعار 1B Trading - البساطة الأنيقة
        // ═══════════════════════════════════════════════════════════
        logo: (
            <Svg width={size} height={size} viewBox="0 0 200 200" fill="none">
                <Defs>
                    <LinearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <Stop offset="0%" stopColor="#8B5CF6" />
                        <Stop offset="100%" stopColor="#06B6D4" />
                    </LinearGradient>
                </Defs>
                <Rect x="30" y="30" width="140" height="140" rx="30" fill="url(#logoGrad)" />
                <SvgText x="75" y="130" fill="#FFFFFF" fontSize="80" fontWeight="bold" fontFamily="Arial">1</SvgText>
                <G>
                    <SvgText x="105" y="130" fill="#FFFFFF" fontSize="80" fontWeight="bold" fontFamily="Arial">B</SvgText>
                    <Path d="M115 75 L125 65 L135 70 L145 60" fill="none" stroke="#10B981" strokeWidth="4" strokeLinecap="round" />
                    <Circle cx="145" cy="60" r="5" fill="#10B981" />
                </G>
            </Svg>
        ),

        // 🏷️ شعار مصغر (للهيدر والتبويبات)
        'logo-mini': (
            <Svg width={size} height={size} viewBox="0 0 200 200" fill="none">
                <Defs>
                    <LinearGradient id="logoMiniGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                        <Stop offset="0%" stopColor="#8B5CF6" />
                        <Stop offset="100%" stopColor="#06B6D4" />
                    </LinearGradient>
                </Defs>
                <Rect x="30" y="30" width="140" height="140" rx="30" fill="url(#logoMiniGrad)" />
                <SvgText x="75" y="130" fill="#FFFFFF" fontSize="80" fontWeight="bold" fontFamily="Arial">1</SvgText>
                <SvgText x="115" y="130" fill="#FFFFFF" fontSize="80" fontWeight="bold" fontFamily="Arial">B</SvgText>
            </Svg>
        ),

        // 🏷️ شعار أحادي اللون
        'logo-mono': (
            <Svg width={size} height={size} viewBox="0 0 200 200" fill="none">
                <Rect x="30" y="30" width="140" height="140" rx="30" fill={color} />
                <SvgText x="75" y="130" fill="#FFFFFF" fontSize="80" fontWeight="bold" fontFamily="Arial">1</SvgText>
                <SvgText x="115" y="130" fill="#FFFFFF" fontSize="80" fontWeight="bold" fontFamily="Arial">B</SvgText>
            </Svg>
        ),

        // 🏷️ شعار خط فقط (Outline)
        'logo-outline': (
            <Svg width={size} height={size} viewBox="0 0 200 200" fill="none">
                <Rect x="30" y="30" width="140" height="140" rx="30" fill="none" stroke="#8B5CF6" strokeWidth="4" />
                <SvgText x="75" y="130" fill="#8B5CF6" fontSize="80" fontWeight="bold" fontFamily="Arial">1</SvgText>
                <SvgText x="115" y="130" fill="#06B6D4" fontSize="80" fontWeight="bold" fontFamily="Arial">B</SvgText>
            </Svg>
        ),

        // ═══════════════════════════════════════════════════════════
        // 🔔 أيقونة الجرس (بديل للإشعارات)
        // ═══════════════════════════════════════════════════════════
        bell: (
            <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                <Path
                    d="M18 8C18 6.4087 17.3679 4.88258 16.2426 3.75736C15.1174 2.63214 13.5913 2 12 2C10.4087 2 8.88258 2.63214 7.75736 3.75736C6.63214 4.88258 6 6.4087 6 8C6 15 3 17 3 17H21C21 17 18 15 18 8Z"
                    fill={color}
                    opacity="0.2"
                />
                <Path
                    d="M18 8C18 6.4087 17.3679 4.88258 16.2426 3.75736C15.1174 2.63214 13.5913 2 12 2C10.4087 2 8.88258 2.63214 7.75736 3.75736C6.63214 4.88258 6 6.4087 6 8C6 15 3 17 3 17H21C21 17 18 15 18 8Z"
                    stroke={color}
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
                <Path
                    d="M13.73 21C13.5542 21.3031 13.3019 21.5547 12.9982 21.7295C12.6946 21.9044 12.3504 21.9965 12 21.9965C11.6496 21.9965 11.3054 21.9044 11.0018 21.7295C10.6982 21.5547 10.4458 21.3031 10.27 21"
                    stroke={color}
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                />
            </Svg>
        ),

    };

    // إرجاع الأيقونة أو أيقونة افتراضية
    const icon = icons[name];

    if (!icon) {
        // أيقونة افتراضية (دائرة)
        return (
            <View style={[styles.container, style]}>
                <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
                    <Circle cx="12" cy="12" r="8" stroke={color} strokeWidth="1.5" fill="none" />
                </Svg>
            </View>
        );
    }

    return <View style={[styles.container, style]}>{icon}</View>;
};

const styles = StyleSheet.create({
    container: {
        alignItems: 'center',
        justifyContent: 'center',
    },
});

export default BrandIcon;
export { ICON_COLORS };
