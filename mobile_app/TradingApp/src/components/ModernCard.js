/**
 * مكون الكارت الحديث
 * ✅ تصميم جديد مستوحى من Stakent
 * ✅ ألوان بنفسجية أنيقة
 * ✅ دعم كامل لـ RTL
 */

import React from 'react';
import { View, StyleSheet, I18nManager } from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { theme as Theme } from '../theme/theme';

const isRTL = I18nManager.isRTL;

const ModernCard = ({
  children,
  variant = 'default',
  noPadding = false,
  style = {},
  gradient = false,
}) => {
  const getCardStyle = () => {
    const baseStyle = [styles.card];

    // إضافة نمط النوع
    baseStyle.push(styles[`variant_${variant}`]);

    // إضافة أو إزالة الحشو
    if (!noPadding) {
      baseStyle.push(styles.withPadding);
    }

    // إضافة الأنماط المخصصة
    baseStyle.push(style);

    return baseStyle;
  };

  if (gradient) {
    return (
      <LinearGradient
        colors={Theme.colors.gradientCard}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={[styles.card, styles.gradientCard, !noPadding && styles.withPadding, style]}
      >
        {children}
      </LinearGradient>
    );
  }

  return (
    <View style={getCardStyle()}>
      {children}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    borderRadius: 16,
    marginVertical: 8,
    overflow: 'hidden',
  },

  // أنواع الكروت
  variant_default: {
    backgroundColor: Theme.colors.card,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    shadowColor: '#000000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 4,
  },
  variant_elevated: {
    backgroundColor: Theme.colors.surface,
    borderWidth: 1,
    borderColor: Theme.colors.border,
    shadowColor: Theme.colors.primary,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.15,
    shadowRadius: 16,
    elevation: 8,
  },
  variant_outlined: {
    backgroundColor: Theme.colors.background,
    borderWidth: 1.5,
    borderColor: Theme.colors.border,
  },
  variant_transparent: {
    backgroundColor: 'transparent',
  },
  variant_glass: {
    backgroundColor: Theme.colors.card + 'CC',
    borderWidth: 1,
    borderColor: Theme.colors.border,
    backdropFilter: 'blur(10px)',
  },
  variant_success: {
    backgroundColor: Theme.colors.card,
    borderWidth: 1,
    borderColor: Theme.colors.success + '40',
    // RTL: الحد الملون على اليمين
    ...(isRTL ? {
      borderRightWidth: 4,
      borderRightColor: Theme.colors.success,
    } : {
      borderLeftWidth: 4,
      borderLeftColor: Theme.colors.success,
    }),
  },
  variant_warning: {
    backgroundColor: Theme.colors.card,
    borderWidth: 1,
    borderColor: Theme.colors.warning + '40',
    ...(isRTL ? {
      borderRightWidth: 4,
      borderRightColor: Theme.colors.warning,
    } : {
      borderLeftWidth: 4,
      borderLeftColor: Theme.colors.warning,
    }),
  },
  variant_error: {
    backgroundColor: Theme.colors.card,
    borderWidth: 1,
    borderColor: Theme.colors.error + '40',
    ...(isRTL ? {
      borderRightWidth: 4,
      borderRightColor: Theme.colors.error,
    } : {
      borderLeftWidth: 4,
      borderLeftColor: Theme.colors.error,
    }),
  },
  variant_info: {
    backgroundColor: Theme.colors.card,
    borderWidth: 1,
    borderColor: Theme.colors.info + '40',
    ...(isRTL ? {
      borderRightWidth: 4,
      borderRightColor: Theme.colors.info,
    } : {
      borderLeftWidth: 4,
      borderLeftColor: Theme.colors.info,
    }),
  },
  variant_primary: {
    backgroundColor: Theme.colors.card,
    borderWidth: 1,
    borderColor: Theme.colors.primary + '40',
    ...(isRTL ? {
      borderRightWidth: 4,
      borderRightColor: Theme.colors.primary,
    } : {
      borderLeftWidth: 4,
      borderLeftColor: Theme.colors.primary,
    }),
  },

  // كارت متدرج
  gradientCard: {
    borderWidth: 1,
    borderColor: Theme.colors.border,
  },

  // الحشو
  withPadding: {
    padding: 20,
  },
});

export default ModernCard;
