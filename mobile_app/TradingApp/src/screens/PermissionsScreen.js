/**
 * 🔐 شاشة طلب الصلاحيات - PermissionsScreen
 * تُعرض عند أول استخدام للتطبيق لطلب الصلاحيات المطلوبة
 * ✅ متوافقة مع الهوية البصرية الجديدة
 */

import React, { useState } from 'react';
import {
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    ScrollView,
    StatusBar,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, { Path, Circle, Rect, Defs, LinearGradient as SvgLinearGradient, Stop, Text as SvgText, G } from 'react-native-svg';
import LinearGradient from 'react-native-linear-gradient';
import { theme } from '../theme/theme';
import PermissionsService from '../services/PermissionsService';
import ToastService from '../services/ToastService';
import GlobalHeader from '../components/GlobalHeader';
import { useBackHandler } from '../utils/BackHandlerUtil';
import BrandIcon from '../components/BrandIcons';

// ✅ استخدام ألوان الهوية البصرية من theme الموحد
const BRAND_COLORS = {
    primary: theme.colors.primary,
    secondary: theme.colors.accent,
    success: theme.colors.success,
    background: theme.colors.background,
};

// الشعار المصغر
const LogoMini = ({ size = 80 }) => (
    <Svg width={size} height={size} viewBox="0 0 200 200" fill="none">
        <Defs>
            <SvgLinearGradient id="permLogoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <Stop offset="0%" stopColor={BRAND_COLORS.primary} />
                <Stop offset="100%" stopColor={BRAND_COLORS.secondary} />
            </SvgLinearGradient>
        </Defs>
        <Rect x="30" y="30" width="140" height="140" rx="30" fill="url(#permLogoGrad)" />
        <SvgText x="75" y="130" fill="#FFFFFF" fontSize="80" fontWeight="bold" fontFamily="Arial">1</SvgText>
        <SvgText x="115" y="130" fill="#FFFFFF" fontSize="80" fontWeight="bold" fontFamily="Arial">B</SvgText>
    </Svg>
);

// عنصر صلاحية
const PermissionItem = ({ icon, title, description, status }) => (
    <View style={styles.permissionItem}>
        <View style={styles.permissionIcon}>
            <BrandIcon name={icon} size={28} color={BRAND_COLORS.primary} />
        </View>
        <View style={styles.permissionContent}>
            <Text style={styles.permissionTitle}>{title}</Text>
            <Text style={styles.permissionDescription}>{description}</Text>
        </View>
        <View style={[styles.permissionStatus, status === 'granted' && styles.permissionGranted]}>
            <BrandIcon
                name={status === 'granted' ? 'check-circle' : 'info'}
                size={20}
                color={status === 'granted' ? BRAND_COLORS.success : '#666'}
            />
        </View>
    </View>
);

const PermissionsScreen = ({ onComplete }) => {
    const [loading, setLoading] = useState(false);
    const [permissions, setPermissions] = useState({
        notifications: 'pending',
        camera: 'pending',
        storage: 'pending',
    });

    const handleRequestPermissions = async () => {
        setLoading(true);
        try {
            const results = await PermissionsService.requestAllPermissions();

            setPermissions({
                notifications: results.notifications ? 'granted' : 'denied',
                camera: results.camera ? 'granted' : 'denied',
                storage: results.storage ? 'granted' : 'denied',
            });

            // تأخير قصير لعرض النتائج
            setTimeout(() => {
                onComplete(results);
            }, 1000);
        } catch (error) {
            console.error('خطأ في طلب الصلاحيات:', error);
            onComplete({});
        } finally {
            setLoading(false);
        }
    };

    const handleSkip = async () => {
        await PermissionsService.markPermissionsRequested();
        onComplete({});
    };

    return (
        <SafeAreaView style={styles.container}>
            <StatusBar barStyle="light-content" backgroundColor={BRAND_COLORS.background} />

            <ScrollView
                contentContainerStyle={styles.scrollContent}
                showsVerticalScrollIndicator={false}
            >
                {/* الشعار */}
                <View style={styles.logoContainer}>
                    <LogoMini size={100} />
                </View>

                {/* العنوان */}
                <Text style={styles.title}>مرحباً بك في 1B Trading</Text>
                <Text style={styles.subtitle}>
                    نحتاج بعض الصلاحيات لتقديم أفضل تجربة لك
                </Text>

                {/* قائمة الصلاحيات */}
                <View style={styles.permissionsList}>
                    <PermissionItem
                        icon="notification"
                        title="الإشعارات"
                        description="لإعلامك بالصفقات والتحديثات المهمة"
                        status={permissions.notifications}
                    />
                    <PermissionItem
                        icon="shield"
                        title="الأمان"
                        description="لحماية حسابك باستخدام البصمة"
                        status={permissions.camera}
                    />
                    <PermissionItem
                        icon="settings"
                        title="التخزين"
                        description="لحفظ إعداداتك وبياناتك محلياً"
                        status={permissions.storage}
                    />
                </View>

                {/* الأزرار */}
                <View style={styles.buttonsContainer}>
                    <TouchableOpacity
                        style={[styles.primaryButton, loading && styles.buttonDisabled]}
                        onPress={handleRequestPermissions}
                        disabled={loading}
                    >
                        <LinearGradient
                            colors={[BRAND_COLORS.primary, BRAND_COLORS.secondary]}
                            start={{ x: 0, y: 0 }}
                            end={{ x: 1, y: 0 }}
                            style={styles.buttonGradient}
                        >
                            <Text style={styles.primaryButtonText}>
                                {loading ? 'جاري الطلب...' : 'السماح بالصلاحيات'}
                            </Text>
                        </LinearGradient>
                    </TouchableOpacity>

                    <TouchableOpacity
                        style={styles.skipButton}
                        onPress={handleSkip}
                        disabled={loading}
                    >
                        <Text style={styles.skipButtonText}>تخطي الآن</Text>
                    </TouchableOpacity>
                </View>

                {/* ملاحظة */}
                <Text style={styles.note}>
                    يمكنك تغيير هذه الإعدادات لاحقاً من إعدادات الجهاز
                </Text>
            </ScrollView>
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: BRAND_COLORS.background,
    },
    scrollContent: {
        flexGrow: 1,
        paddingHorizontal: 24,
        paddingVertical: 40,
        alignItems: 'center',
    },
    logoContainer: {
        marginBottom: 30,
        alignItems: 'center',
    },
    title: {
        fontSize: 26,
        fontWeight: '800',
        color: '#FFFFFF',
        textAlign: 'center',
        marginBottom: 12,
    },
    subtitle: {
        fontSize: 16,
        color: '#A0A0B0',
        textAlign: 'center',
        marginBottom: 40,
        lineHeight: 24,
    },
    permissionsList: {
        width: '100%',
        marginBottom: 40,
    },
    permissionItem: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#1A1A2E',
        borderRadius: 16,
        padding: 16,
        marginBottom: 12,
        borderWidth: 1,
        borderColor: 'rgba(139, 92, 246, 0.2)',
    },
    permissionIcon: {
        width: 50,
        height: 50,
        borderRadius: 25,
        backgroundColor: 'rgba(139, 92, 246, 0.15)',
        alignItems: 'center',
        justifyContent: 'center',
        marginEnd: 16,
    },
    permissionContent: {
        flex: 1,
    },
    permissionTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#FFFFFF',
        marginBottom: 4,
    },
    permissionDescription: {
        fontSize: 13,
        color: '#A0A0B0',
    },
    permissionStatus: {
        width: 36,
        height: 36,
        borderRadius: 18,
        backgroundColor: 'rgba(255, 255, 255, 0.05)',
        alignItems: 'center',
        justifyContent: 'center',
    },
    permissionGranted: {
        backgroundColor: 'rgba(16, 185, 129, 0.15)',
    },
    buttonsContainer: {
        width: '100%',
        marginBottom: 20,
    },
    primaryButton: {
        borderRadius: 16,
        overflow: 'hidden',
        marginBottom: 12,
    },
    buttonGradient: {
        paddingVertical: 16,
        alignItems: 'center',
    },
    buttonDisabled: {
        opacity: 0.7,
    },
    primaryButtonText: {
        fontSize: 18,
        fontWeight: '700',
        color: '#FFFFFF',
    },
    skipButton: {
        paddingVertical: 14,
        alignItems: 'center',
    },
    skipButtonText: {
        fontSize: 16,
        color: '#A0A0B0',
    },
    note: {
        fontSize: 13,
        color: '#666',
        textAlign: 'center',
        marginTop: 10,
    },
});

export default PermissionsScreen;
