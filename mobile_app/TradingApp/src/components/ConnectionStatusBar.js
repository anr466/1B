/**
 * 📡 Connection Status Bar - شريط حالة الاتصال
 * ✅ يستخدم TradingModeContext المركزي لحالة الاتصال
 */

import React, { useState, useEffect, useRef } from 'react';
import {
    View,
    Text,
    StyleSheet,
    Animated,
} from 'react-native';
import { theme } from '../theme/theme';
import { useTradingModeContext } from '../context/TradingModeContext';

const ConnectionStatusBar = () => {
    // ✅ استخدام حالة الاتصال من Context المركزي
    const { isConnected } = useTradingModeContext();

    const [showBar, setShowBar] = useState(false);
    const [fadeAnim] = useState(new Animated.Value(0));
    const prevConnectedRef = useRef(isConnected);

    // ✅ مراقبة تغيّر حالة الاتصال من Context
    useEffect(() => {
        const prevConnected = prevConnectedRef.current;
        prevConnectedRef.current = isConnected;

        // تغيّرت الحالة
        if (prevConnected !== isConnected) {
            if (!isConnected) {
                // فقد الاتصال - إظهار الشريط
                setShowBar(true);
                Animated.timing(fadeAnim, {
                    toValue: 1,
                    duration: 300,
                    useNativeDriver: true,
                }).start();
            } else {
                // استعادة الاتصال - إخفاء بعد 2 ثانية
                setTimeout(() => {
                    Animated.timing(fadeAnim, {
                        toValue: 0,
                        duration: 300,
                        useNativeDriver: true,
                    }).start(() => setShowBar(false));
                }, 2000);
            }
        }
    }, [isConnected, fadeAnim]);

    if (!showBar) {return null;}

    return (
        <Animated.View
            style={[
                styles.container,
                { opacity: fadeAnim },
                isConnected ? styles.connected : styles.disconnected,
            ]}
        >
            <View style={styles.dot} />
            <Text style={styles.text}>
                {isConnected ? 'تم استعادة الاتصال' : 'لا يوجد اتصال بالخادم'}
            </Text>
        </Animated.View>
    );
};

const styles = StyleSheet.create({
    container: {
        position: 'absolute',
        bottom: 90,
        left: 20,
        right: 20,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        paddingVertical: 10,
        paddingHorizontal: 16,
        borderRadius: 10,
        zIndex: 999,
    },
    connected: {
        backgroundColor: 'rgba(16, 185, 129, 0.9)',
    },
    disconnected: {
        backgroundColor: 'rgba(239, 68, 68, 0.9)',
    },
    dot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: '#FFFFFF',
        marginEnd: 8,
    },
    text: {
        fontSize: 14,
        fontWeight: '500',
        color: '#FFFFFF',
    },
});

export default ConnectionStatusBar;
