import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import Icon from '../../../components/CustomIcons';
import { useTheme } from '../../../context/ThemeContext';

const { width } = Dimensions.get('window');

// أنواع الرسائل
export const MESSAGE_TYPES = {
  SUCCESS: 'success',
  ERROR: 'error',
  WARNING: 'warning',
  INFO: 'info',
};

/**
 * مكون عرض رسائل الحالة مع أيقونات
 * @param {string} type - نوع الرسالة (success, error, warning, info)
 * @param {string} message - نص الرسالة
 * @param {string} title - عنوان الرسالة (اختياري)
 * @param {boolean} visible - إظهار أو إخفاء الرسالة
 * @param {object} style - أنماط إضافية للحاوية
 * @param {object} textStyle - أنماط إضافية للنص
 */
const StatusMessage = ({
  type = MESSAGE_TYPES.INFO,
  message,
  title,
  visible = true,
  style = {},
  textStyle = {},
}) => {
  const { colors } = useTheme();

  if (!visible || !message) {return null;}

  // تحديد الأيقونة حسب نوع الرسالة
  const getIcon = () => {
    switch (type) {
      case MESSAGE_TYPES.SUCCESS:
        return 'check-circle';
      case MESSAGE_TYPES.ERROR:
        return 'error';
      case MESSAGE_TYPES.WARNING:
        return 'warning';
      case MESSAGE_TYPES.INFO:
      default:
        return 'info';
    }
  };

  // تحديد الألوان حسب نوع الرسالة
  const getColors = () => {
    switch (type) {
      case MESSAGE_TYPES.SUCCESS:
        return {
          background: colors.success + '15', // شفافية 15%
          border: colors.success,
          text: colors.success,
          icon: colors.success,
        };
      case MESSAGE_TYPES.ERROR:
        return {
          background: colors.error + '15',
          border: colors.error,
          text: colors.error,
          icon: colors.error,
        };
      case MESSAGE_TYPES.WARNING:
        return {
          background: colors.warning + '15',
          border: colors.warning,
          text: colors.warning,
          icon: colors.warning,
        };
      case MESSAGE_TYPES.INFO:
      default:
        return {
          background: colors.primary + '15',
          border: colors.primary,
          text: colors.text,
          icon: colors.primary,
        };
    }
  };

  const messageColors = getColors();

  const styles = StyleSheet.create({
    container: {
      backgroundColor: messageColors.background,
      borderLeftWidth: 4,
      borderLeftColor: messageColors.border,
      borderRadius: 8,
      padding: 12,
      marginVertical: 8,
      flexDirection: 'row',
      alignItems: 'flex-start',
      ...style,
    },
    iconContainer: {
      marginRight: 12,
      marginTop: 2,
    },
    textContainer: {
      flex: 1,
    },
    title: {
      fontSize: width * 0.04,
      fontWeight: 'bold',
      color: messageColors.text,
      marginBottom: title ? 4 : 0,
      textAlign: 'right',
    },
    message: {
      fontSize: width * 0.035,
      color: messageColors.text,
      lineHeight: 20,
      textAlign: 'right',
      ...textStyle,
    },
  });

  return (
    <View style={styles.container}>
      <View style={styles.iconContainer}>
        <Icon
          name={getIcon()}
          size={20}
          color={messageColors.icon}
        />
      </View>
      <View style={styles.textContainer}>
        {title && (
          <Text style={styles.title}>
            {title}
          </Text>
        )}
        <Text style={styles.message}>
          {message}
        </Text>
      </View>
    </View>
  );
};

// مكونات مخصصة لكل نوع رسالة
export const SuccessMessage = (props) => (
  <StatusMessage {...props} type={MESSAGE_TYPES.SUCCESS} />
);

export const ErrorMessage = (props) => (
  <StatusMessage {...props} type={MESSAGE_TYPES.ERROR} />
);

export const WarningMessage = (props) => (
  <StatusMessage {...props} type={MESSAGE_TYPES.WARNING} />
);

export const InfoMessage = (props) => (
  <StatusMessage {...props} type={MESSAGE_TYPES.INFO} />
);

export default StatusMessage;
