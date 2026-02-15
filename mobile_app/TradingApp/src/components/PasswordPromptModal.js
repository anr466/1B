/**
 * PasswordPromptModal - Modal لإدخال كلمة المرور
 * بديل لـ Alert.prompt الذي لا يعمل على Android
 */

import React, { useState, useRef, useEffect } from 'react';
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    Modal,
    KeyboardAvoidingView,
    Platform,
} from 'react-native';
import { theme } from '../theme/theme';
import ModernInput from './ModernInput';

const PasswordPromptModal = ({
    visible,
    title = '🔐 تأكيد الهوية',
    message = 'أدخل كلمة المرور للتأكيد:',
    placeholder = 'كلمة المرور',
    confirmText = 'تأكيد',
    cancelText = 'إلغاء',
    onConfirm,
    onCancel,
    confirmButtonStyle = 'destructive', // 'default' | 'destructive'
}) => {
    const [password, setPassword] = useState('');

    // reset password when visibility changes
    useEffect(() => {
        if (!visible) {
            setPassword('');
        }
    }, [visible]);

    const handleConfirm = () => {
        if (password.trim()) {
            onConfirm(password);
            setPassword(''); // إعادة تعيين
        }
    };

    const handleCancel = () => {
        setPassword(''); // إعادة تعيين
        onCancel();
    };

    return (
        <Modal
            visible={visible}
            transparent
            animationType="fade"
            onRequestClose={handleCancel}
        >
            <KeyboardAvoidingView
                style={styles.overlay}
                behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
            >
                <TouchableOpacity
                    style={styles.backdrop}
                    activeOpacity={1}
                    onPress={handleCancel}
                />

                <View style={styles.modalContent}>
                    {/* Header */}
                    <View style={styles.header}>
                        <Text style={styles.title}>{title}</Text>
                        {message ? (
                            <Text style={styles.message}>{message}</Text>
                        ) : null}
                    </View>

                    {/* Input */}
                    <ModernInput
                        value={password}
                        onChangeText={setPassword}
                        placeholder={placeholder}
                        secureTextEntry={true}
                        autoFocus={true}
                        autoCapitalize="none"
                        returnKeyType="done"
                        onSubmitEditing={handleConfirm}
                        icon="lock"
                        containerStyle={{ marginBottom: 20 }}
                    />

                    {/* Buttons */}
                    <View style={styles.buttons}>
                        <TouchableOpacity
                            style={[styles.button, styles.cancelButton]}
                            onPress={handleCancel}
                            activeOpacity={0.7}
                        >
                            <Text style={styles.cancelButtonText}>
                                {cancelText}
                            </Text>
                        </TouchableOpacity>

                        <TouchableOpacity
                            style={[
                                styles.button,
                                confirmButtonStyle === 'destructive'
                                    ? styles.destructiveButton
                                    : styles.confirmButton,
                            ]}
                            onPress={handleConfirm}
                            activeOpacity={0.7}
                            disabled={!password.trim()}
                        >
                            <Text
                                style={[
                                    confirmButtonStyle === 'destructive'
                                        ? styles.destructiveButtonText
                                        : styles.confirmButtonText,
                                    !password.trim() && styles.disabledButtonText,
                                ]}
                            >
                                {confirmText}
                            </Text>
                        </TouchableOpacity>
                    </View>
                </View>
            </KeyboardAvoidingView>
        </Modal>
    );
};

const styles = StyleSheet.create({
    overlay: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    backdrop: {
        ...StyleSheet.absoluteFillObject,
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
    },
    modalContent: {
        width: '85%',
        maxWidth: 400,
        backgroundColor: theme.colors.surface,
        borderRadius: 16,
        padding: 24,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
        elevation: 8,
    },
    header: {
        marginBottom: 20,
    },
    title: {
        fontSize: 20,
        fontWeight: '700',
        color: theme.colors.text,
        textAlign: 'center',
        marginBottom: 8,
    },
    message: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        lineHeight: 20,
    },
    input: {
        backgroundColor: theme.colors.background,
        borderRadius: 8,
        paddingHorizontal: 16,
        paddingVertical: 12,
        fontSize: 16,
        color: theme.colors.text,
        textAlign: 'right',
        borderWidth: 1,
        borderColor: theme.colors.border || '#333',
        marginBottom: 20,
    },
    buttons: {
        flexDirection: 'row',
        gap: 12,
    },
    button: {
        flex: 1,
        paddingVertical: 12,
        borderRadius: 8,
        alignItems: 'center',
    },
    cancelButton: {
        backgroundColor: theme.colors.background,
        borderWidth: 1,
        borderColor: theme.colors.border || '#333',
    },
    cancelButtonText: {
        fontSize: 16,
        fontWeight: '600',
        color: theme.colors.textSecondary,
    },
    confirmButton: {
        backgroundColor: theme.colors.primary,
    },
    confirmButtonText: {
        fontSize: 16,
        fontWeight: '600',
        color: '#FFF',
    },
    destructiveButton: {
        backgroundColor: theme.colors.error || '#EF4444',
    },
    destructiveButtonText: {
        fontSize: 16,
        fontWeight: '600',
        color: '#FFF',
    },
    disabledButtonText: {
        opacity: 0.5,
    },
});

export default PasswordPromptModal;
