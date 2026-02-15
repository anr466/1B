/**
 * أداة معالجة زر الرجوع الموحدة
 * توفر نمط موحد لمعالجة زر الرجوع من الجهاز في جميع الشاشات
 */

import { BackHandler, Alert } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import { useCallback } from 'react';

/**
 * Hook موحد لمعالجة زر الرجوع
 * @param {Function} onBackPress - الدالة التي تُستدعى عند الضغط على زر الرجوع
 * @param {boolean} enabled - تفعيل/تعطيل المعالجة (افتراضي: true)
 */
export const useBackHandler = (onBackPress, enabled = true) => {
    useFocusEffect(
        useCallback(() => {
            if (!enabled) {return;}

            const subscription = BackHandler.addEventListener(
                'hardwareBackPress',
                () => {
                    if (onBackPress) {
                        onBackPress();
                        return true; // منع السلوك الافتراضي
                    }
                    return false; // السماح بالسلوك الافتراضي
                }
            );

            return () => subscription.remove();
        }, [onBackPress, enabled])
    );
};

/**
 * معالج موحد للرجوع من الشاشات العادية
 * @param {Object} navigation - كائن الملاحة
 */
export const handleGoBack = (navigation) => {
    if (navigation?.canGoBack?.()) {
        navigation.goBack();
        return true;
    }
    return false;
};

/**
 * معالج موحد لمنع الرجوع من شاشات معينة
 * @param {Object} navigation - كائن الملاحة
 * @param {string} targetScreen - الشاشة المراد الذهاب إليها
 */
export const handlePreventGoBack = (navigation, targetScreen = 'Dashboard') => {
    if (navigation?.replace) {
        navigation.replace(targetScreen);
        return true;
    }
    return false;
};

/**
 * معالج موحد للخروج من التطبيق
 */
export const handleExitApp = () => {
    BackHandler.exitApp();
};

/**
 * ✅ عرض Dialog تأكيد قبل الخروج من التطبيق
 * يُستخدم في الشاشات الرئيسية (Dashboard, Portfolio, etc.)
 */
export const showExitConfirmation = () => {
    Alert.alert(
        'الخروج من التطبيق',
        'هل تريد الخروج من التطبيق؟',
        [
            {
                text: 'إلغاء',
                style: 'cancel',
            },
            {
                text: 'خروج',
                style: 'destructive',
                onPress: () => BackHandler.exitApp(),
            },
        ],
        { cancelable: true }
    );
};

/**
 * ✅ Hook محسن لمعالجة زر الرجوع مع Dialog تأكيد
 * @param {boolean} showConfirmation - عرض Dialog تأكيد قبل الخروج
 */
export const useBackHandlerWithConfirmation = (showConfirmation = true) => {
    useFocusEffect(
        useCallback(() => {
            const subscription = BackHandler.addEventListener(
                'hardwareBackPress',
                () => {
                    if (showConfirmation) {
                        showExitConfirmation();
                        return true; // منع السلوك الافتراضي
                    }
                    return false;
                }
            );

            return () => subscription.remove();
        }, [showConfirmation])
    );
};

export default {
    useBackHandler,
    handleGoBack,
    handlePreventGoBack,
    handleExitApp,
    showExitConfirmation,
    useBackHandlerWithConfirmation,
};
