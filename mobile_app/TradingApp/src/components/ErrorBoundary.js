/**
 * 🛡️ Error Boundary - معالج الأخطاء العام
 * يلتقط الأخطاء غير المتوقعة ويعرض شاشة بديلة
 */

import React, { Component } from 'react';
import {
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    SafeAreaView,
} from 'react-native';
import { theme } from '../theme/theme';

class ErrorBoundary extends Component {
    constructor(props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null,
        };
    }

    static getDerivedStateFromError(error) {
        return { hasError: true, error };
    }

    componentDidCatch(error, errorInfo) {
        console.error('❌ ErrorBoundary caught an error:', error, errorInfo);
        this.setState({ errorInfo });
    }

    handleReset = () => {
        this.setState({ hasError: false, error: null, errorInfo: null });
        if (this.props.onReset) {
            this.props.onReset();
        }
    };

    render() {
        if (this.state.hasError) {
            return (
                <SafeAreaView style={styles.container}>
                    <View style={styles.content}>
                        <Text style={styles.emoji}>😕</Text>
                        <Text style={styles.title}>حدث خطأ غير متوقع</Text>
                        <Text style={styles.message}>
                            نعتذر عن هذا الخطأ. يرجى المحاولة مرة أخرى.
                        </Text>

                        {__DEV__ && this.state.error && (
                            <View style={styles.errorDetails}>
                                <Text style={styles.errorText}>
                                    {this.state.error.toString()}
                                </Text>
                            </View>
                        )}

                        <TouchableOpacity
                            style={styles.button}
                            onPress={this.handleReset}
                        >
                            <Text style={styles.buttonText}>إعادة المحاولة</Text>
                        </TouchableOpacity>
                    </View>
                </SafeAreaView>
            );
        }

        return this.props.children;
    }
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    content: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 24,
    },
    emoji: {
        fontSize: 64,
        marginBottom: 20,
    },
    title: {
        fontSize: 24,
        fontWeight: '700',
        color: theme.colors.text,
        marginBottom: 12,
        textAlign: 'center',
    },
    message: {
        fontSize: 16,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        marginBottom: 24,
        lineHeight: 24,
    },
    errorDetails: {
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        borderRadius: 12,
        padding: 16,
        marginBottom: 24,
        maxWidth: '100%',
    },
    errorText: {
        fontSize: 12,
        color: '#EF4444',
        fontFamily: 'monospace',
    },
    button: {
        backgroundColor: theme.colors.primary,
        paddingVertical: 14,
        paddingHorizontal: 32,
        borderRadius: 12,
    },
    buttonText: {
        fontSize: 16,
        fontWeight: '600',
        color: '#FFFFFF',
    },
});

export default ErrorBoundary;
