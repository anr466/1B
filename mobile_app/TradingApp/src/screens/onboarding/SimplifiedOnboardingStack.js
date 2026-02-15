/**
 * نظام Onboarding مبسّط - 3 شاشات فقط
 * ✅ شاشة 1: مرحباً + كيف يعمل (مدمجة)
 * ✅ شاشة 2: ربط Binance
 * ✅ شاشة 3: تفعيل التداول + البصمة
 */

import React, { useState, useEffect } from 'react';
import {
    View,
    Text,
    StyleSheet,
    SafeAreaView,
    StatusBar,
    ScrollView,
    TouchableOpacity,
    Switch,
    Alert,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { useNavigation } from '@react-navigation/native';
import { theme } from '../../theme/theme';
import ModernButton from '../../components/ModernButton';
import ModernCard from '../../components/ModernCard';
import ModernInput from '../../components/ModernInput';
import SecureStorageService from '../../services/SecureStorageService';
import DatabaseApiService from '../../services/DatabaseApiService';
import ToastService from '../../services/ToastService';
import BiometricService from '../../services/BiometricService';
import Icon from '../../components/CustomIcons';

const SimplifiedOnboardingStack = ({ onComplete, user }) => {
    const navigation = useNavigation();
    const [currentStep, setCurrentStep] = useState(0);
    const [isLoading, setIsLoading] = useState(false);

    // بيانات Binance
    const [apiKey, setApiKey] = useState('');
    const [secretKey, setSecretKey] = useState('');

    // إعدادات التداول
    const [enableBiometric, setEnableBiometric] = useState(false);
    const [biometricAvailable, setBiometricAvailable] = useState(false);

    const totalSteps = 3;

    useEffect(() => {
        checkBiometricAvailability();
    }, []);

    const checkBiometricAvailability = async () => {
        try {
            const available = await BiometricService.isBiometricAvailable();
            setBiometricAvailable(available);
        } catch (e) {
            setBiometricAvailable(false);
        }
    };

    const handleNext = () => {
        if (currentStep < totalSteps - 1) {
            setCurrentStep(currentStep + 1);
        }
    };

    const handleBack = () => {
        if (currentStep > 0) {
            setCurrentStep(currentStep - 1);
        }
    };

    const handleSkipBinance = () => {
        Alert.alert(
            '⏭️ تخطي ربط Binance',
            'إذا تخطيت الآن:\n\n' +
            '• لن تتمكن من التداول الحقيقي\n' +
            '• يمكنك الربط لاحقاً من الإعدادات\n' +
            '• ستظل تستطيع استكشاف التطبيق\n\n' +
            'ملاحظة: بدون ربط Binance، لا يمكن للنظام التداول بأموال حقيقية.',
            [
                { text: 'إلغاء', style: 'cancel' },
                {
                    text: 'فهمت، تخطي',
                    onPress: () => {
                        ToastService.showInfo('يمكنك ربط Binance لاحقاً من الإعدادات');
                        handleNext();
                    },
                    style: 'default',
                },
            ]
        );
    };

    const handleSaveBinanceKeys = async () => {
        if (!apiKey.trim() || !secretKey.trim()) {
            ToastService.showWarning('يرجى إدخال المفاتيح');
            return;
        }

        // تأكيد من المستخدم
        Alert.alert(
            '🔐 تأكيد حفظ المفاتيح',
            'بعد حفظ المفاتيح:\n\n' +
            '✅ النظام سيتمكن من التداول تلقائياً\n' +
            '✅ ستُحفظ المفاتيح مشفرة بـ AES-256\n' +
            '✅ يمكنك حذفها في أي وقت من الإعدادات\n\n' +
            '⚠️ تذكير: التداول ينطوي على مخاطر',
            [
                { text: 'إلغاء', style: 'cancel' },
                {
                    text: 'فهمت، احفظ',
                    onPress: async () => {
                        setIsLoading(true);
                        try {
                            const response = await DatabaseApiService.saveBinanceKeys(apiKey, secretKey);
                            if (response?.success) {
                                ToastService.showSuccess('✅ تم حفظ المفاتيح وتشفيرها بنجاح');
                                Alert.alert(
                                    '🎉 تم الربط بنجاح!',
                                    'الآن يمكن للنظام التداول تلقائياً بأموالك الحقيقية من Binance.\n\nتأكد من مراقبة أداء النظام بانتظام.',
                                    [{ text: 'فهمت', onPress: handleNext }]
                                );
                            } else {
                                ToastService.showError(response?.error || 'فشل حفظ المفاتيح');
                            }
                        } catch (e) {
                            const errorMsg = e?.response?.data?.error || e?.message || 'فشل الاتصال بالخادم';
                            ToastService.showError(errorMsg);
                        } finally {
                            setIsLoading(false);
                        }
                    },
                },
            ]
        );
    };

    const handleComplete = async () => {
        setIsLoading(true);
        try {
            // تفعيل البصمة إذا اختارها المستخدم
            if (enableBiometric && biometricAvailable) {
                await BiometricService.enableBiometric(user?.id);
            }

            // حفظ حالة إكمال Onboarding
            await SecureStorageService.setSecureItem(`onboarding_completed_${user?.id}`, 'true');

            ToastService.showSuccess('مرحباً بك! 🎉');

            if (onComplete) {
                onComplete();
            }
        } catch (e) {
            const errorMsg = e?.response?.data?.error || e?.message || 'حدث خطأ غير متوقع';
            ToastService.showError(errorMsg);
        } finally {
            setIsLoading(false);
        }
    };

    // ═══════════════════════════════════════════════════════════════
    // شاشة 1: مرحباً + كيف يعمل
    // ═══════════════════════════════════════════════════════════════
    const renderWelcomeScreen = () => (
        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
            {/* الترحيب */}
            <LinearGradient
                colors={theme.colors.gradientPrimary}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={styles.heroBox}
            >
                <Text style={styles.heroIcon}>📈</Text>
                <Text style={styles.heroTitle}>1B Trading</Text>
                <Text style={styles.heroSubtitle}>التداول الآلي الذكي</Text>
            </LinearGradient>

            {/* ✅ شرح واضح للنظام الآلي */}
            <ModernCard variant="info" style={styles.autoTradingCard}>
                <Text style={styles.autoTradingTitle}>🤖 ماذا يعني "تداول آلي"؟</Text>
                <Text style={styles.autoTradingText}>
                    هذا النظام يتداول <Text style={styles.boldText}>بدلاً منك 24/7</Text>{'\n'}
                    {'\n'}
                    <Text style={styles.boldText}>أنت لا تتداول يدوياً!</Text>{'\n'}
                    {'\n'}
                    • أنت تضيف مفاتيح Binance{'\n'}
                    • النظام يبدأ التداول تلقائياً{'\n'}
                    • أنت تضبط الإعدادات فقط{'\n'}
                    • النظام يتداول 24/7 بدونك{'\n'}
                    • أنت تراقب النتائج فقط
                </Text>
            </ModernCard>

            {/* كيف يعمل */}
            <Text style={styles.sectionTitle}>خطوات البداية</Text>

            <View style={styles.stepsContainer}>
                {[
                    { icon: '🔑', title: 'ربط Binance', desc: 'اربط حسابك بأمان' },
                    { icon: '⚙️', title: 'الإعدادات', desc: 'حدد المخاطر المقبولة' },
                    { icon: '🤖', title: 'تداول آلي', desc: 'النظام يتداول 24/7' },
                    { icon: '📊', title: 'راقب', desc: 'تابع الأرباح والأداء' },
                ].map((step, i) => (
                    <View key={i} style={styles.stepItem}>
                        <View style={styles.stepNumber}>
                            <Text style={styles.stepNumberText}>{i + 1}</Text>
                        </View>
                        <Text style={styles.stepIcon}>{step.icon}</Text>
                        <View style={styles.stepTextBox}>
                            <Text style={styles.stepTitle}>{step.title}</Text>
                            <Text style={styles.stepDesc}>{step.desc}</Text>
                        </View>
                    </View>
                ))}
            </View>

            {/* رابط إلى دليل الاستخدام */}
            <TouchableOpacity
                style={styles.helpLinkCard}
                onPress={() => {
                    // ✅ الانتقال إلى Usage Guide
                    if (navigation) {
                        navigation.navigate('UsageGuide');
                    }
                }}
            >
                <Text style={styles.helpLinkIcon}>📖</Text>
                <View style={styles.helpLinkContent}>
                    <Text style={styles.helpLinkTitle}>دليل الاستخدام الشامل</Text>
                    <Text style={styles.helpLinkDesc}>شروحات تفصيلية لكل وظيفة</Text>
                </View>
                <Text style={styles.helpLinkArrow}>›</Text>
            </TouchableOpacity>

            {/* المميزات */}
            <ModernCard style={styles.featuresCard}>
                <Text style={styles.featuresTitle}>✨ المميزات</Text>
                {[
                    'تداول آلي 24/7 بدون تدخل',
                    'ذكاء اصطناعي للتحليل',
                    'إدارة مخاطر متقدمة',
                    'إشعارات فورية',
                ].map((f, i) => (
                    <View key={i} style={styles.featureRow}>
                        <Text style={styles.featureCheck}>✓</Text>
                        <Text style={styles.featureText}>{f}</Text>
                    </View>
                ))}
            </ModernCard>

            <ModernButton
                title="ابدأ الآن"
                onPress={handleNext}
                variant="primary"
                size="large"
                fullWidth
                style={styles.mainButton}
            />
        </ScrollView>
    );

    // ═══════════════════════════════════════════════════════════════
    // شاشة 2: ربط Binance
    // ═══════════════════════════════════════════════════════════════
    const renderBinanceScreen = () => (
        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
            <View style={styles.headerBox}>
                <Text style={styles.headerIcon}>🔑</Text>
                <Text style={styles.headerTitle}>ربط حساب Binance</Text>
                <Text style={styles.headerSubtitle}>
                    للتداول الحقيقي، تحتاج لربط حسابك على Binance
                </Text>
            </View>

            {/* شرح مفصل */}
            <ModernCard variant="info" style={styles.infoCard}>
                <Text style={styles.infoTitle}>📌 فكرة التطبيق:</Text>
                <Text style={styles.infoText}>
                    • التطبيق نظام تداول آلي 100%{'\n'}
                    • أنت لا تتداول يدوياً - النظام يتداول تلقائياً{'\n'}
                    • دورك: المراقبة وتحديد الإعدادات فقط{'\n'}
                    • النظام يعمل 24/7 بدون تدخل منك
                </Text>
            </ModernCard>

            {/* الأمان والخصوصية */}
            <ModernCard variant="success" style={styles.securityCard}>
                <Text style={styles.securityTitle}>🔒 الأمان والخصوصية:</Text>
                <Text style={styles.securityText}>
                    ✅ التطبيق لا يستطيع الوصول لمحفظتك{'\n'}
                    ✅ التطبيق لا يستطيع سحب أموالك{'\n'}
                    ✅ المفاتيح مشفرة بـ AES-256{'\n'}
                    ✅ نحتاج صلاحية التداول فقط (Spot Trading)
                </Text>
            </ModernCard>

            {/* الصلاحيات المطلوبة */}
            <ModernCard variant="outlined" style={styles.permissionsCard}>
                <Text style={styles.permissionsTitle}>⚙️ الصلاحيات المطلوبة:</Text>
                <View style={styles.permissionItem}>
                    <Text style={styles.permissionCheck}>✅</Text>
                    <Text style={styles.permissionText}>Enable Spot & Margin Trading</Text>
                </View>
                <View style={styles.permissionItem}>
                    <Text style={styles.permissionCross}>❌</Text>
                    <Text style={styles.permissionText}>Enable Withdrawals (غير مطلوب)</Text>
                </View>
                <View style={styles.permissionItem}>
                    <Text style={styles.permissionCross}>❌</Text>
                    <Text style={styles.permissionText}>Enable Futures (غير مطلوب)</Text>
                </View>
            </ModernCard>

            {/* تعليمات مفصلة */}
            <ModernCard variant="outlined" style={styles.instructionsCard}>
                <Text style={styles.instructionsTitle}>📋 خطوات الحصول على المفاتيح:</Text>
                <Text style={styles.instructionsText}>
                    1️⃣ افتح Binance → حسابي → API Management{'\n'}
                    2️⃣ اضغط "Create API"{'\n'}
                    3️⃣ اختر "System generated" API Key{'\n'}
                    4️⃣ أدخل اسماً (مثل: Trading Bot){'\n'}
                    5️⃣ فعّل: "Enable Spot & Margin Trading" فقط{'\n'}
                    6️⃣ تأكد من عدم تفعيل "Enable Withdrawals"{'\n'}
                    7️⃣ انسخ API Key و Secret Key هنا{'\n'}
                    8️⃣ احتفظ بهما في مكان آمن
                </Text>
            </ModernCard>

            <ModernCard style={styles.inputCard}>
                <ModernInput
                    label="API Key"
                    value={apiKey}
                    onChangeText={setApiKey}
                    placeholder="أدخل API Key"
                    autoCapitalize="none"
                    autoCorrect={false}
                    icon="key"
                />

                <ModernInput
                    label="Secret Key"
                    value={secretKey}
                    onChangeText={setSecretKey}
                    placeholder="أدخل Secret Key"
                    autoCapitalize="none"
                    autoCorrect={false}
                    secureTextEntry={true}
                    icon="lock"
                />
            </ModernCard>

            <View style={styles.buttonRow}>
                <TouchableOpacity style={styles.skipButton} onPress={handleSkipBinance}>
                    <Text style={styles.skipButtonText}>تخطي</Text>
                </TouchableOpacity>

                <ModernButton
                    title={isLoading ? 'جاري الحفظ...' : 'حفظ المفاتيح'}
                    onPress={handleSaveBinanceKeys}
                    variant="primary"
                    size="medium"
                    disabled={isLoading}
                    style={{ flex: 1, marginLeft: 12 }}
                />
            </View>

            <TouchableOpacity style={styles.backButton} onPress={handleBack}>
                <Text style={styles.backButtonText}>← رجوع</Text>
            </TouchableOpacity>
        </ScrollView>
    );

    // ═══════════════════════════════════════════════════════════════
    // شاشة 3: تفعيل + البصمة
    // ═══════════════════════════════════════════════════════════════
    const renderActivateScreen = () => (
        <ScrollView contentContainerStyle={styles.scrollContent} showsVerticalScrollIndicator={false}>
            <View style={styles.headerBox}>
                <Text style={styles.headerIcon}>🚀</Text>
                <Text style={styles.headerTitle}>أنت جاهز!</Text>
                <Text style={styles.headerSubtitle}>
                    خطوة أخيرة قبل البدء
                </Text>
            </View>

            {/* البصمة */}
            {biometricAvailable && (
                <ModernCard style={styles.optionCard}>
                    <View style={styles.optionRow}>
                        <View style={styles.optionInfo}>
                            <Text style={styles.optionIcon}>👆</Text>
                            <View>
                                <Text style={styles.optionTitle}>تسجيل الدخول بالبصمة</Text>
                                <Text style={styles.optionDesc}>دخول سريع وآمن</Text>
                            </View>
                        </View>
                        <Switch
                            value={enableBiometric}
                            onValueChange={setEnableBiometric}
                            trackColor={{ false: theme.colors.border, true: theme.colors.primary + '80' }}
                            thumbColor={enableBiometric ? theme.colors.primary : theme.colors.textSecondary}
                        />
                    </View>
                </ModernCard>
            )}

            {/* ملخص */}
            <ModernCard variant="success" style={styles.summaryCard}>
                <Text style={styles.summaryTitle}>✅ ملخص الإعداد</Text>
                <View style={styles.summaryRow}>
                    <Text style={styles.summaryLabel}>الحساب:</Text>
                    <Text style={styles.summaryValue}>{user?.email || 'مسجل'}</Text>
                </View>
                <View style={styles.summaryRow}>
                    <Text style={styles.summaryLabel}>Binance:</Text>
                    <Text style={styles.summaryValue}>{apiKey ? '✅ مربوط' : '⏭️ تم التخطي'}</Text>
                </View>
                <View style={styles.summaryRow}>
                    <Text style={styles.summaryLabel}>البصمة:</Text>
                    <Text style={styles.summaryValue}>{enableBiometric ? '✅ مفعّلة' : '❌ معطّلة'}</Text>
                </View>
            </ModernCard>

            {/* تنبيه */}
            <ModernCard variant="warning" style={styles.warningCard}>
                <Text style={styles.warningText}>
                    ⚠️ التداول ينطوي على مخاطر. لا تستثمر أكثر مما يمكنك تحمل خسارته.
                </Text>
            </ModernCard>

            <ModernButton
                title={isLoading ? 'جاري التفعيل...' : '🎉 ابدأ التداول'}
                onPress={handleComplete}
                variant="success"
                size="large"
                fullWidth
                disabled={isLoading}
                style={styles.mainButton}
            />

            <TouchableOpacity style={styles.backButton} onPress={handleBack}>
                <Text style={styles.backButtonText}>← رجوع</Text>
            </TouchableOpacity>
        </ScrollView>
    );

    // ═══════════════════════════════════════════════════════════════
    // Render
    // ═══════════════════════════════════════════════════════════════
    const renderCurrentScreen = () => {
        switch (currentStep) {
            case 0: return renderWelcomeScreen();
            case 1: return renderBinanceScreen();
            case 2: return renderActivateScreen();
            default: return renderWelcomeScreen();
        }
    };

    return (
        <SafeAreaView style={styles.container}>
            <StatusBar barStyle="light-content" backgroundColor={theme.colors.background} />

            {/* Progress Bar */}
            <View style={styles.progressContainer}>
                {[0, 1, 2].map((step) => (
                    <View
                        key={step}
                        style={[
                            styles.progressDot,
                            currentStep >= step && styles.progressDotActive,
                        ]}
                    />
                ))}
            </View>

            {renderCurrentScreen()}
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    scrollContent: {
        paddingHorizontal: 20,
        paddingBottom: 40,
    },
    // Progress
    progressContainer: {
        flexDirection: 'row',
        justifyContent: 'center',
        paddingVertical: 16,
        gap: 8,
    },
    progressDot: {
        width: 10,
        height: 10,
        borderRadius: 5,
        backgroundColor: theme.colors.border,
    },
    progressDotActive: {
        backgroundColor: theme.colors.primary,
        width: 30,
    },
    // Hero
    heroBox: {
        alignItems: 'center',
        paddingVertical: 40,
        borderRadius: 20,
        marginBottom: 24,
    },
    heroIcon: {
        fontSize: 60,
        marginBottom: 12,
    },
    heroTitle: {
        fontSize: 28,
        fontWeight: '700',
        color: '#FFF',
    },
    heroSubtitle: {
        fontSize: 16,
        color: 'rgba(255,255,255,0.8)',
        marginTop: 4,
    },
    // Section
    sectionTitle: {
        fontSize: 20,
        fontWeight: '700',
        color: theme.colors.text,
        marginBottom: 16,
        textAlign: 'center',
    },
    // Steps
    stepsContainer: {
        marginBottom: 24,
    },
    stepItem: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.surface,
        padding: 16,
        borderRadius: 12,
        marginBottom: 12,
    },
    stepNumber: {
        width: 28,
        height: 28,
        borderRadius: 14,
        backgroundColor: theme.colors.primary,
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 12,
    },
    stepNumberText: {
        color: '#FFF',
        fontWeight: '700',
        fontSize: 14,
    },
    stepIcon: {
        fontSize: 24,
        marginRight: 12,
    },
    stepTextBox: {
        flex: 1,
    },
    stepTitle: {
        fontSize: 15,
        fontWeight: '600',
        color: theme.colors.text,
    },
    stepDesc: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        marginTop: 2,
    },
    // Features
    featuresCard: {
        marginBottom: 24,
    },
    featuresTitle: {
        fontSize: 16,
        fontWeight: '700',
        color: theme.colors.text,
        marginBottom: 12,
    },
    featureRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 8,
    },
    featureCheck: {
        color: theme.colors.success,
        fontSize: 16,
        marginRight: 10,
        fontWeight: '700',
    },
    featureText: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    // Help Link
    helpLinkCard: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: theme.colors.surface,
        padding: 16,
        borderRadius: 12,
        marginBottom: 24,
        borderWidth: 1,
        borderColor: theme.colors.primary + '40',
    },
    helpLinkIcon: {
        fontSize: 28,
        marginRight: 12,
    },
    helpLinkContent: {
        flex: 1,
    },
    helpLinkTitle: {
        fontSize: 15,
        fontWeight: '600',
        color: theme.colors.primary,
    },
    helpLinkDesc: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        marginTop: 2,
    },
    helpLinkArrow: {
        fontSize: 20,
        color: theme.colors.primary,
        marginLeft: 8,
    },
    // Header
    headerBox: {
        alignItems: 'center',
        paddingVertical: 32,
    },
    headerIcon: {
        fontSize: 56,
        marginBottom: 16,
    },
    headerTitle: {
        fontSize: 24,
        fontWeight: '700',
        color: theme.colors.text,
        marginBottom: 8,
    },
    headerSubtitle: {
        fontSize: 15,
        color: theme.colors.textSecondary,
        textAlign: 'center',
        lineHeight: 22,
    },
    // Input
    inputCard: {
        marginBottom: 16,
    },
    inputLabel: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 8,
    },
    input: {
        backgroundColor: theme.colors.surface,
        borderRadius: 10,
        paddingHorizontal: 16,
        paddingVertical: 14,
        fontSize: 15,
        color: theme.colors.text,
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    secretInputRow: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    eyeButton: {
        padding: 14,
        marginLeft: 8,
    },
    eyeIcon: {
        fontSize: 20,
    },
    // Instructions
    instructionsCard: {
        marginBottom: 24,
    },
    instructionsTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.text,
        marginBottom: 8,
    },
    instructionsText: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        lineHeight: 22,
    },
    // Buttons
    buttonRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 16,
    },
    skipButton: {
        paddingVertical: 14,
        paddingHorizontal: 20,
    },
    skipButtonText: {
        color: theme.colors.textSecondary,
        fontSize: 15,
    },
    backButton: {
        alignItems: 'center',
        paddingVertical: 12,
    },
    backButtonText: {
        color: theme.colors.textSecondary,
        fontSize: 14,
    },
    mainButton: {
        marginTop: 8,
    },
    // Options
    optionCard: {
        marginBottom: 16,
    },
    optionRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    optionInfo: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    optionIcon: {
        fontSize: 32,
        marginRight: 12,
    },
    optionTitle: {
        fontSize: 15,
        fontWeight: '600',
        color: theme.colors.text,
    },
    optionDesc: {
        fontSize: 13,
        color: theme.colors.textSecondary,
    },
    // Summary
    summaryCard: {
        marginBottom: 16,
    },
    summaryTitle: {
        fontSize: 16,
        fontWeight: '700',
        color: theme.colors.text,
        marginBottom: 12,
    },
    summaryRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        paddingVertical: 8,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    summaryLabel: {
        fontSize: 14,
        color: theme.colors.textSecondary,
    },
    summaryValue: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.text,
    },
    // Auto Trading Card
    autoTradingCard: {
        backgroundColor: theme.colors.info + '15',
        borderLeftWidth: 4,
        borderLeftColor: theme.colors.info,
        marginBottom: 24,
    },
    autoTradingTitle: {
        fontSize: 16,
        fontWeight: '700',
        color: theme.colors.text,
        marginBottom: 12,
    },
    autoTradingText: {
        fontSize: 14,
        color: theme.colors.textSecondary,
        lineHeight: 22,
    },
    boldText: {
        color: theme.colors.text,
        fontWeight: '500',
    },
    // Warning
    warningCard: {
        marginBottom: 24,
    },
    warningText: {
        fontSize: 13,
        color: theme.colors.warning,
        textAlign: 'center',
        lineHeight: 20,
    },
});

export default SimplifiedOnboardingStack;
