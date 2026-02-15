/**
 * خدمة الاستجابة اللمسية (Haptic Feedback)
 * ✅ اهتزاز خفيف عند التفاعل
 * ✅ أنواع مختلفة للأحداث المختلفة
 * ✅ يعمل بصمت إذا لم يكن مدعوماً
 */

import { Platform, Vibration } from 'react-native';

// محاولة استيراد react-native-haptic-feedback إذا كان متاحاً
let ReactNativeHapticFeedback = null;
try {
    ReactNativeHapticFeedback = require('react-native-haptic-feedback').default;
} catch (e) {
    // المكتبة غير مثبتة - سنستخدم Vibration كبديل
}

/**
 * أنواع الاستجابة اللمسية
 */
export const HapticTypes = {
    // خفيف - للضغط على الأزرار العادية
    LIGHT: 'impactLight',
    // متوسط - للسحب والإفلات
    MEDIUM: 'impactMedium',
    // قوي - للتأكيدات المهمة
    HEAVY: 'impactHeavy',
    // نجاح - عند إتمام عملية بنجاح
    SUCCESS: 'notificationSuccess',
    // تحذير - عند وجود تحذير
    WARNING: 'notificationWarning',
    // خطأ - عند حدوث خطأ
    ERROR: 'notificationError',
    // اختيار - عند تبديل Switch أو اختيار عنصر
    SELECTION: 'selection',
};

/**
 * خيارات الاهتزاز
 */
const hapticOptions = {
    enableVibrateFallback: true,
    ignoreAndroidSystemSettings: false,
};

/**
 * تشغيل الاستجابة اللمسية
 */
export const triggerHaptic = (type = HapticTypes.LIGHT) => {
    try {
        if (ReactNativeHapticFeedback) {
            // استخدام المكتبة المتقدمة
            ReactNativeHapticFeedback.trigger(type, hapticOptions);
        } else {
            // استخدام Vibration كبديل
            const duration = getVibrationDuration(type);
            if (duration > 0) {
                Vibration.vibrate(duration);
            }
        }
    } catch (error) {
        // صامت - لا نريد أن يفشل التطبيق بسبب الاهتزاز
        console.debug('[Haptic] غير متاح:', error.message);
    }
};

/**
 * تحديد مدة الاهتزاز للبديل
 */
const getVibrationDuration = (type) => {
    switch (type) {
        case HapticTypes.LIGHT:
        case HapticTypes.SELECTION:
            return 10;
        case HapticTypes.MEDIUM:
            return 20;
        case HapticTypes.HEAVY:
            return 30;
        case HapticTypes.SUCCESS:
            return 15;
        case HapticTypes.WARNING:
            return 25;
        case HapticTypes.ERROR:
            return 40;
        default:
            return 10;
    }
};

/**
 * اهتزاز خفيف للضغط على الأزرار
 */
export const hapticLight = () => triggerHaptic(HapticTypes.LIGHT);

/**
 * اهتزاز متوسط
 */
export const hapticMedium = () => triggerHaptic(HapticTypes.MEDIUM);

/**
 * اهتزاز قوي
 */
export const hapticHeavy = () => triggerHaptic(HapticTypes.HEAVY);

/**
 * اهتزاز نجاح
 */
export const hapticSuccess = () => triggerHaptic(HapticTypes.SUCCESS);

/**
 * اهتزاز تحذير
 */
export const hapticWarning = () => triggerHaptic(HapticTypes.WARNING);

/**
 * اهتزاز خطأ
 */
export const hapticError = () => triggerHaptic(HapticTypes.ERROR);

/**
 * اهتزاز اختيار (للـ Switch و Picker)
 */
export const hapticSelection = () => triggerHaptic(HapticTypes.SELECTION);

/**
 * تعطيل/تفعيل الاهتزاز (للإعدادات)
 */
let isHapticEnabled = true;

export const setHapticEnabled = (enabled) => {
    isHapticEnabled = enabled;
};

export const isHapticAvailable = () => {
    return ReactNativeHapticFeedback !== null || Platform.OS !== 'web';
};

/**
 * دالة مساعدة لإضافة الاهتزاز لأي onPress
 */
export const withHaptic = (onPress, hapticType = HapticTypes.LIGHT) => {
    return () => {
        triggerHaptic(hapticType);
        onPress && onPress();
    };
};

/**
 * دالة مساعدة لإضافة الاهتزاز مع تمرير المعاملات
 */
export const withHapticArgs = (onPress, hapticType = HapticTypes.LIGHT) => {
    return (...args) => {
        triggerHaptic(hapticType);
        onPress && onPress(...args);
    };
};

export default {
    triggerHaptic,
    hapticLight,
    hapticMedium,
    hapticHeavy,
    hapticSuccess,
    hapticWarning,
    hapticError,
    hapticSelection,
    setHapticEnabled,
    isHapticAvailable,
    HapticTypes,
    withHaptic,
    withHapticArgs,
};
