import React, { useState, useEffect } from 'react';
import { Text, StyleSheet } from 'react-native';
import { useTheme } from '../../../context/ThemeContext';

/**
 * مكون العداد التنازلي لـ OTP
 * @param {number} initialTime - الوقت الأولي بالثواني (افتراضي: 300 = 5 دقائق)
 * @param {function} onComplete - دالة يتم استدعاؤها عند انتهاء العداد
 * @param {object} style - أنماط إضافية
 */
const CountdownTimer = ({
  initialTime = 300,
  onComplete,
  style = {},
  textStyle = {},
}) => {
  const { colors } = useTheme();
  const [timeLeft, setTimeLeft] = useState(initialTime);
  const [isActive, setIsActive] = useState(true);

  useEffect(() => {
    let interval = null;

    if (isActive && timeLeft > 0) {
      interval = setInterval(() => {
        setTimeLeft(time => {
          if (time <= 1) {
            setIsActive(false);
            if (onComplete) {
              onComplete();
            }
            return 0;
          }
          return time - 1;
        });
      }, 1000);
    } else if (timeLeft === 0) {
      setIsActive(false);
    }

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [isActive, timeLeft, onComplete]);

  // إعادة تشغيل العداد
  const restart = (newTime = initialTime) => {
    setTimeLeft(newTime);
    setIsActive(true);
  };

  // إيقاف العداد
  const stop = () => {
    setIsActive(false);
  };

  // تحويل الثواني إلى تنسيق mm:ss
  const formatTime = (seconds) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  // تحديد لون النص حسب الوقت المتبقي
  const getTextColor = () => {
    if (timeLeft <= 30) {return colors.error;}     // أحمر في آخر 30 ثانية
    if (timeLeft <= 60) {return colors.warning;}  // برتقالي في آخر دقيقة
    return colors.textSecondary;                 // لون عادي
  };

  const styles = StyleSheet.create({
    timerText: {
      fontSize: 16,
      fontWeight: '600',
      color: getTextColor(),
      textAlign: 'center',
      fontFamily: 'monospace', // خط ثابت العرض للأرقام
      ...textStyle,
    },
  });

  // عرض الرسالة المناسبة
  const getDisplayText = () => {
    if (timeLeft === 0) {
      return 'انتهت صلاحية الرمز';
    }

    if (timeLeft <= 60) {
      return `${timeLeft} ثانية متبقية`;
    }

    return `صالح لمدة ${formatTime(timeLeft)}`;
  };

  return (
    <Text style={[styles.timerText, style]}>
      {getDisplayText()}
    </Text>
  );
};

// تصدير المكون مع وظائف إضافية
CountdownTimer.restart = (ref, newTime) => {
  if (ref && ref.current) {
    ref.current.restart(newTime);
  }
};

CountdownTimer.stop = (ref) => {
  if (ref && ref.current) {
    ref.current.stop();
  }
};

export default CountdownTimer;
