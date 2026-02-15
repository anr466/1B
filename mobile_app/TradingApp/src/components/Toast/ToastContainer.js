/**
 * 🍞 Toast Container - حاوية رسائل التنبيه
 * تعرض رسائل التنبيه المؤقتة (Toast Messages)
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
    View,
    Text,
    StyleSheet,
    Animated,
    Dimensions,
} from 'react-native';
import { theme } from '../../theme/theme';
import ToastService from '../../services/ToastService';

const { width } = Dimensions.get('window');

// أنواع التنبيهات
const TOAST_TYPES = {
    success: {
        backgroundColor: 'rgba(16, 185, 129, 0.95)',
        icon: '✓',
    },
    error: {
        backgroundColor: 'rgba(239, 68, 68, 0.95)',
        icon: '✕',
    },
    warning: {
        backgroundColor: 'rgba(245, 158, 11, 0.95)',
        icon: '⚠',
    },
    info: {
        backgroundColor: 'rgba(139, 92, 246, 0.95)',
        icon: 'ℹ',
    },
};

const Toast = ({ message, type = 'info', onHide }) => {
    const [fadeAnim] = useState(new Animated.Value(0));
    const [translateY] = useState(new Animated.Value(-50));

    useEffect(() => {
        // ظهور
        Animated.parallel([
            Animated.timing(fadeAnim, {
                toValue: 1,
                duration: 300,
                useNativeDriver: true,
            }),
            Animated.spring(translateY, {
                toValue: 0,
                tension: 50,
                friction: 8,
                useNativeDriver: true,
            }),
        ]).start();

        // اختفاء بعد 3 ثواني
        const timer = setTimeout(() => {
            Animated.parallel([
                Animated.timing(fadeAnim, {
                    toValue: 0,
                    duration: 200,
                    useNativeDriver: true,
                }),
                Animated.timing(translateY, {
                    toValue: -50,
                    duration: 200,
                    useNativeDriver: true,
                }),
            ]).start(() => {
                if (onHide) {onHide();}
            });
        }, 3000);

        return () => clearTimeout(timer);
    }, []);

    const toastStyle = TOAST_TYPES[type] || TOAST_TYPES.info;

    return (
        <Animated.View
            style={[
                styles.toast,
                { backgroundColor: toastStyle.backgroundColor },
                {
                    opacity: fadeAnim,
                    transform: [{ translateY }],
                },
            ]}
        >
            <Text style={styles.icon}>{toastStyle.icon}</Text>
            <Text style={styles.message}>{message}</Text>
        </Animated.View>
    );
};

const ToastContainer = () => {
    const [toasts, setToasts] = useState([]);

    useEffect(() => {
        // الاشتراك في خدمة التنبيهات
        const unsubscribe = ToastService.subscribe((toast) => {
            const id = Date.now();
            setToasts((prev) => [...prev, { ...toast, id }]);
        });

        return () => {
            if (unsubscribe) {unsubscribe();}
        };
    }, []);

    const handleHide = useCallback((id) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    if (toasts.length === 0) {return null;}

    return (
        <View style={styles.container} pointerEvents="box-none">
            {toasts.map((toast) => (
                <Toast
                    key={toast.id}
                    message={toast.message}
                    type={toast.type}
                    onHide={() => handleHide(toast.id)}
                />
            ))}
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        position: 'absolute',
        top: 60,
        left: 0,
        right: 0,
        alignItems: 'center',
        zIndex: 9999,
    },
    toast: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 12,
        paddingHorizontal: 20,
        borderRadius: 12,
        marginBottom: 8,
        maxWidth: width - 40,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
        elevation: 8,
    },
    icon: {
        fontSize: 18,
        marginEnd: 10,
        color: '#FFFFFF',
    },
    message: {
        fontSize: 14,
        fontWeight: '500',
        color: '#FFFFFF',
        flex: 1,
    },
});

export default ToastContainer;
