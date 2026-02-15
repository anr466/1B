import React, { useState } from 'react';
import {
    View,
    ScrollView,
    Text,
    TouchableOpacity,
    StyleSheet,
    Dimensions,
    SafeAreaView,
} from 'react-native';
import BrandIcon from '../components/BrandIcons';
import ModernInput from '../components/ModernInput';
import { theme } from '../theme/theme';

const { width } = Dimensions.get('window');

const UsageGuideScreen = ({ navigation }) => {
    const [activeSection, setActiveSection] = useState('getting-started');
    const [searchQuery, setSearchQuery] = useState('');
    const [expandedItems, setExpandedItems] = useState({});

    const toggleExpand = (id) => {
        setExpandedItems(prev => ({
            ...prev,
            [id]: !prev[id],
        }));
    };

    const sections = {
        'getting-started': {
            title: '🚀 البداية السريعة',
            icon: 'rocket',
            items: [
                {
                    id: 'gs-1',
                    title: 'الخطوة 1: التسجيل',
                    content: [
                        { label: 'ماذا تفعل:', value: 'أدخل بريدك وكلمة مرورك' },
                        { label: 'لماذا:', value: 'لإنشاء حسابك الآمن' },
                        { label: 'ماذا سيحدث:', value: 'ستدخل إلى لوحة التحكم' },
                    ],
                },
                {
                    id: 'gs-2',
                    title: 'الخطوة 2: ربط Binance (اختياري)',
                    content: [
                        { label: 'ماذا تفعل:', value: 'أضف مفاتيح Binance API' },
                        { label: 'لماذا:', value: 'لتفعيل التداول الحقيقي' },
                        { label: 'ماذا سيحدث:', value: 'النظام سيتداول بأموالك الحقيقية' },
                        { label: '⚠️ تحذير:', value: 'قد تخسر أموالك' },
                    ],
                },
                {
                    id: 'gs-3',
                    title: 'الخطوة 3: تفعيل التداول',
                    content: [
                        { label: 'ماذا تفعل:', value: 'اضغط على "تفعيل التداول"' },
                        { label: 'لماذا:', value: 'لبدء النظام الآلي' },
                        { label: 'ماذا سيحدث:', value: 'النظام سيبدأ بفتح صفقات تلقائياً' },
                    ],
                },
            ],
        },
        'trading-settings': {
            title: '⚙️ إعدادات التداول',
            icon: 'settings',
            items: [
                {
                    id: 'ts-1',
                    title: 'Max Positions - الحد الأقصى للصفقات',
                    content: [
                        { label: 'ماذا:', value: 'عدد الصفقات المفتوحة معاً' },
                        { label: 'لماذا:', value: 'تقليل المخاطر' },
                        { label: 'ماذا يحدث:', value: 'إذا وصلت للحد، لن يفتح صفقات جديدة' },
                        { label: 'الحد:', value: '1 - 5' },
                        { label: 'مثال:', value: 'إذا جعلتها 2، سيفتح صفقة واحدة فقط معاً' },
                    ],
                },
                {
                    id: 'ts-2',
                    title: 'Stop Loss - وقف الخسارة',
                    content: [
                        { label: 'ماذا:', value: 'نسبة الخسارة التي يغلق عندها النظام' },
                        { label: 'لماذا:', value: 'حماية أموالك من الخسائر الكبيرة' },
                        { label: 'ماذا يحدث:', value: 'عند انخفاض السعر بهذه النسبة، يغلق الصفقة تلقائياً' },
                        { label: 'الحد:', value: '1% - 10%' },
                        { label: 'مثال:', value: 'اشتريت بـ 100$، إذا جعلتها 5%، سيبيع عند 95$' },
                    ],
                },
                {
                    id: 'ts-3',
                    title: 'Take Profit - جني الأرباح',
                    content: [
                        { label: 'ماذا:', value: 'نسبة الربح التي يغلق عندها النظام' },
                        { label: 'لماذا:', value: 'تأمين الأرباح' },
                        { label: 'ماذا يحدث:', value: 'عند ارتفاع السعر بهذه النسبة، يغلق الصفقة تلقائياً' },
                        { label: 'الحد:', value: '2% - 20%' },
                        { label: 'مثال:', value: 'اشتريت بـ 100$، إذا جعلتها 10%، سيبيع عند 110$' },
                    ],
                },
                {
                    id: 'ts-4',
                    title: 'Trading Enabled - تفعيل التداول',
                    content: [
                        { label: 'ماذا:', value: 'تشغيل أو إيقاف النظام الآلي' },
                        { label: 'لماذا:', value: 'التحكم في متى يتداول النظام' },
                        { label: 'ماذا يحدث:', value: 'إذا أطفأته، النظام لن يفتح صفقات جديدة' },
                        { label: 'ملاحظة:', value: 'الصفقات المفتوحة ستبقى مفتوحة' },
                    ],
                },
            ],
        },
        'binance-keys': {
            title: '🔑 مفاتيح Binance',
            icon: 'key',
            items: [
                {
                    id: 'bk-1',
                    title: '👤 للمستخدم العادي: Real Mode فقط',
                    content: [
                        { label: 'ماذا:', value: 'تداول حقيقي بأموالك الفعلية' },
                        { label: 'لماذا:', value: 'النظام يحتاج مفاتيح حقيقية للتداول' },
                        { label: 'ماذا يحدث:', value: 'النظام يتداول بأموالك الحقيقية من Binance' },
                        { label: 'المخاطر:', value: '⚠️ قد تخسر أموالك' },
                        { label: 'ملاحظة:', value: 'لا يمكنك اختيار Demo Mode - هذا للأدمن فقط' },
                    ],
                },
                {
                    id: 'bk-2',
                    title: '👨‍💼 للأدمن فقط: Demo Mode متاح',
                    content: [
                        { label: 'ماذا:', value: 'تداول وهمي للممارسة والاختبار' },
                        { label: 'لماذا:', value: 'اختبار النظام بدون مخاطر' },
                        { label: 'ماذا يحدث:', value: 'النظام يتداول بأموال افتراضية (1000 USDT)' },
                        { label: 'المخاطر:', value: 'لا توجد' },
                        { label: 'الفائدة:', value: 'تعلم واختبار بدون خسائر' },
                    ],
                },
                {
                    id: 'bk-3',
                    title: 'كيفية إضافة مفاتيح Binance',
                    content: [
                        { label: '1️⃣', value: 'اذهب إلى Binance > API Management' },
                        { label: '2️⃣', value: 'أنشئ API Key جديد' },
                        { label: '3️⃣', value: 'انسخ المفتاح والسر' },
                        { label: '4️⃣', value: 'الصقهما في التطبيق' },
                        { label: '⚠️ تحذير:', value: 'لا تشارك هذه المفاتيح مع أحد' },
                        { label: '⚠️ مهم:', value: 'بدون مفاتيح = لا يمكنك التداول' },
                    ],
                },
            ],
        },
        'portfolio': {
            title: '📊 المحفظة والأرباح',
            icon: 'pie-chart',
            items: [
                {
                    id: 'pf-1',
                    title: 'الرصيد الكلي',
                    content: [
                        { label: 'ماذا يعني:', value: 'إجمالي أموالك في الحساب' },
                        { label: 'من أين:', value: 'حسابك الفعلي في Binance (Real) أو محاكاة (Demo)' },
                        { label: 'متى يتحدث:', value: 'كل 60 ثانية تلقائياً' },
                        { label: 'يتضمن:', value: 'الأموال الأصلية + الأرباح - الخسائر' },
                    ],
                },
                {
                    id: 'pf-2',
                    title: 'الأرباح اليومية',
                    content: [
                        { label: 'ماذا يعني:', value: 'أرباحك منذ بداية اليوم' },
                        { label: 'كيف تُحسب:', value: 'من الصفقات المغلقة بنجاح اليوم' },
                        { label: 'متى يتحدث:', value: 'كل 60 ثانية تلقائياً' },
                        { label: 'ملاحظة:', value: 'تُعاد للصفر في منتصف الليل' },
                    ],
                },
                {
                    id: 'pf-3',
                    title: 'الأرباح الكلية',
                    content: [
                        { label: 'ماذا يعني:', value: 'كم ربحت منذ البداية' },
                        { label: 'كيف تُحسب:', value: 'من جميع الصفقات الناجحة' },
                        { label: 'متى يتحدث:', value: 'كل 60 ثانية تلقائياً' },
                        { label: 'ملاحظة:', value: 'لا تُعاد للصفر أبداً' },
                    ],
                },
            ],
        },
        'notifications': {
            title: '🔔 الإشعارات',
            icon: 'notifications',
            items: [
                {
                    id: 'notif-1',
                    title: '"تم فتح صفقة BTCUSDT"',
                    content: [
                        { label: 'ماذا تعني:', value: 'النظام فتح صفقة شراء على Bitcoin' },
                        { label: 'ماذا يفعل النظام:', value: 'يراقب السعر ويغلقها عند تحقق الشروط' },
                        { label: 'ماذا تفعل أنت:', value: 'لا شيء (النظام يتحكم تلقائياً)' },
                    ],
                },
                {
                    id: 'notif-2',
                    title: '"ربح +50 USDT"',
                    content: [
                        { label: 'ماذا تعني:', value: 'صفقة أغلقت برابح 50 دولار' },
                        { label: 'ماذا يفعل النظام:', value: 'أضاف الربح إلى رصيدك' },
                        { label: 'ماذا تفعل أنت:', value: 'لا شيء (النظام يتحكم تلقائياً)' },
                    ],
                },
                {
                    id: 'notif-3',
                    title: '"حد الخسارة اليومي تم الوصول إليه"',
                    content: [
                        { label: 'ماذا تعني:', value: 'خسرت أكثر من الحد المسموح اليوم' },
                        { label: 'ماذا يفعل النظام:', value: 'توقف عن فتح صفقات جديدة' },
                        { label: 'ماذا تفعل أنت:', value: 'انتظر حتى غداً أو غيّر الإعدادات' },
                    ],
                },
            ],
        },
        'faq': {
            title: '❓ الأسئلة الشائعة',
            icon: 'help-circle',
            items: [
                {
                    id: 'faq-1',
                    title: 'س: هل يمكنني فتح صفقة يدوياً؟',
                    content: [
                        { label: 'الإجابة:', value: 'لا، النظام آلي 100%. لا توجد صفقات يدوية.' },
                    ],
                },
                {
                    id: 'faq-2',
                    title: 'س: هل يمكنني إيقاف التداول؟',
                    content: [
                        { label: 'الإجابة:', value: 'نعم، اذهب إلى Settings وأطفئ "Trading Enabled"' },
                    ],
                },
                {
                    id: 'faq-3',
                    title: 'س: ماذا لو خسرت أموالي؟',
                    content: [
                        { label: 'الإجابة:', value: 'هناك حد خسارة يومي يحمي أموالك من الخسائر الكبيرة' },
                    ],
                },
                {
                    id: 'faq-4',
                    title: 'س: كم مرة يتحدث الرصيد؟',
                    content: [
                        { label: 'الإجابة:', value: 'كل 60 ثانية تلقائياً' },
                    ],
                },
                {
                    id: 'faq-5',
                    title: 'س: هل البيانات حقيقية؟',
                    content: [
                        { label: 'في Real Mode:', value: 'نعم، بيانات حقيقية من Binance' },
                        { label: 'في Demo Mode:', value: 'لا، بيانات وهمية للممارسة' },
                    ],
                },
            ],
        },
    };

    const currentSection = sections[activeSection];

    return (
        <SafeAreaView style={styles.container}>
            <View style={styles.header}>
                <TouchableOpacity onPress={() => navigation.goBack()}>
                    <BrandIcon name="arrow-back" size={24} color="#fff" />
                </TouchableOpacity>
                <Text style={styles.headerTitle}>📖 دليل الاستخدام</Text>
                <View style={{ width: 24 }} />
            </View>

            {/* Search Bar */}
            <ModernInput
                value={searchQuery}
                onChangeText={setSearchQuery}
                placeholder="ابحث عن..."
                icon="search"
                containerStyle={{ marginHorizontal: 16, marginTop: 12 }}
            />

            <ScrollView style={styles.content} showsVerticalScrollIndicator={false}>
                {/* Sections Navigation */}
                <View style={styles.sectionsNav}>
                    {Object.entries(sections).map(([key, section]) => (
                        <TouchableOpacity
                            key={key}
                            style={[
                                styles.sectionButton,
                                activeSection === key && styles.sectionButtonActive,
                            ]}
                            onPress={() => setActiveSection(key)}
                        >
                            <Text style={[
                                styles.sectionButtonText,
                                activeSection === key && styles.sectionButtonTextActive,
                            ]}>
                                {section.title}
                            </Text>
                        </TouchableOpacity>
                    ))}
                </View>

                {/* Current Section Content */}
                <View style={styles.sectionContent}>
                    <Text style={styles.sectionTitle}>{currentSection.title}</Text>

                    {currentSection.items.map((item) => (
                        <View key={item.id} style={styles.itemContainer}>
                            <TouchableOpacity
                                style={styles.itemHeader}
                                onPress={() => toggleExpand(item.id)}
                            >
                                <Text style={styles.itemTitle}>{item.title}</Text>
                                <BrandIcon
                                    name={expandedItems[item.id] ? 'chevron-up' : 'chevron-down'}
                                    size={20}
                                    color="#4CAF50"
                                />
                            </TouchableOpacity>

                            {expandedItems[item.id] && (
                                <View style={styles.itemContent}>
                                    {item.content.map((line, idx) => (
                                        <View key={idx} style={styles.contentLine}>
                                            <Text style={styles.contentLabel}>{line.label}</Text>
                                            <Text style={styles.contentValue}>{line.value}</Text>
                                        </View>
                                    ))}
                                </View>
                            )}
                        </View>
                    ))}
                </View>

                <View style={{ height: 30 }} />
            </ScrollView>
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.background,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingVertical: 12,
        backgroundColor: theme.colors.surface,
        borderBottomWidth: 1,
        borderBottomColor: theme.colors.border,
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: theme.colors.text,
    },
    searchContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        marginHorizontal: 16,
        marginVertical: 12,
        paddingHorizontal: 12,
        backgroundColor: theme.colors.surface,
        borderRadius: 8,
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    searchInput: {
        flex: 1,
        marginLeft: 8,
        color: theme.colors.text,
        fontSize: 14,
        paddingVertical: 8,
    },
    content: {
        flex: 1,
        paddingHorizontal: 16,
    },
    sectionsNav: {
        marginVertical: 12,
    },
    sectionButton: {
        paddingHorizontal: 12,
        paddingVertical: 8,
        marginRight: 8,
        marginBottom: 8,
        backgroundColor: theme.colors.surface,
        borderRadius: 6,
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    sectionButtonActive: {
        backgroundColor: theme.colors.success,
        borderColor: theme.colors.success,
    },
    sectionButtonText: {
        fontSize: 12,
        color: theme.colors.textSecondary,
        fontWeight: '500',
    },
    sectionButtonTextActive: {
        color: theme.colors.text,
    },
    sectionContent: {
        marginVertical: 12,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: '700',
        color: theme.colors.success,
        marginBottom: 16,
    },
    itemContainer: {
        marginBottom: 12,
        backgroundColor: theme.colors.surface,
        borderRadius: 8,
        borderWidth: 1,
        borderColor: theme.colors.border,
        overflow: 'hidden',
    },
    itemHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 12,
        paddingVertical: 12,
    },
    itemTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: theme.colors.text,
        flex: 1,
    },
    itemContent: {
        paddingHorizontal: 12,
        paddingVertical: 12,
        backgroundColor: theme.colors.background,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
    },
    contentLine: {
        marginBottom: 8,
    },
    contentLabel: {
        fontSize: 12,
        fontWeight: '600',
        color: theme.colors.success,
        marginBottom: 2,
    },
    contentValue: {
        fontSize: 13,
        color: theme.colors.textSecondary,
        lineHeight: 18,
    },
});

export default UsageGuideScreen;
