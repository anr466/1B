/**
 * 🔐 شاشة المصادقة الموحدة - AuthScreen
 * تجمع بين شاشتي تسجيل الدخول والتسجيل
 * ✅ متوافقة مع الهوية البصرية الجديدة
 */

import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import LoginScreen from './LoginScreen';
import RegisterScreen from './RegisterScreen';
import { theme } from '../theme/theme';
import GlobalHeader from '../components/GlobalHeader';
import { useBackHandler } from '../utils/BackHandlerUtil';
import { SafeAreaView } from 'react-native-safe-area-context';

const AuthScreen = ({
    initialMode = 'login',
    onLogin,
    onRegister,
    onNavigateToForgotPassword,
    onNavigateToEmailVerification,
}) => {
    const [mode, setMode] = useState(initialMode);

    // التبديل بين تسجيل الدخول والتسجيل
    const handleNavigateToRegister = () => {
        setMode('register');
    };

    const handleNavigateToLogin = () => {
        setMode('login');
    };

    return (
        <View style={styles.container}>
            {mode === 'login' ? (
                <LoginScreen
                    onLogin={onLogin}
                    onNavigateToRegister={handleNavigateToRegister}
                    onNavigateToForgotPassword={onNavigateToForgotPassword}
                />
            ) : (
                <RegisterScreen
                    onRegister={onRegister}
                    onBackToLogin={handleNavigateToLogin}
                    onNavigateToEmailVerification={onNavigateToEmailVerification}
                />
            )}
        </View>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
});

export default AuthScreen;
