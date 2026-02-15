/**
 * شاشة شروط الاستخدام
 */

import React from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  TouchableOpacity,
} from 'react-native';
import { theme } from '../theme/theme';
import ModernCard from '../components/ModernCard';
import { useBackHandler } from '../utils/BackHandlerUtil';
// ✅ GlobalHeader يأتي من Navigator

const TermsAndConditionsScreen = ({ onBack }) => {
  // معالجة زر الرجوع من الجهاز
  useBackHandler(() => {
    onBack && onBack();
  });

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={theme.colors.background} />
      {/* ✅ Header يأتي من Navigator */}

      <ScrollView style={styles.scrollContent} showsVerticalScrollIndicator={false}>
        <ModernCard>
          <View style={styles.section}>
            <Text style={styles.title}>شروط الاستخدام</Text>

            <Text style={styles.lastUpdated}>آخر تحديث: 2025-10-26</Text>

            <View style={styles.content}>
              <Text style={styles.heading}>1. قبول الشروط</Text>
              <Text style={styles.paragraph}>
                بالدخول إلى هذا التطبيق واستخدامه، فإنك توافق على الالتزام بجميع الشروط والأحكام المذكورة هنا.
              </Text>

              <Text style={styles.heading}>2. استخدام الخدمة</Text>
              <Text style={styles.paragraph}>
                يجب أن تكون مسؤولاً عن جميع الأنشطة التي تتم تحت حسابك. أنت توافق على عدم استخدام الخدمة لأي أغراض غير قانونية أو ضارة.
              </Text>

              <Text style={styles.heading}>3. حقوق الملكية الفكرية</Text>
              <Text style={styles.paragraph}>
                جميع المحتويات والميزات في التطبيق محمية بحقوق الملكية الفكرية. لا يُسمح بنسخ أو توزيع أي محتوى دون إذن كتابي.
              </Text>

              <Text style={styles.heading}>4. تحديد المسؤولية</Text>
              <Text style={styles.paragraph}>
                التطبيق يُقدم "كما هو" بدون أي ضمانات. نحن لا نتحمل مسؤولية أي خسائر مالية أو أضرار ناجمة عن استخدام التطبيق.
              </Text>

              <Text style={styles.heading}>5. المعاملات المالية</Text>
              <Text style={styles.paragraph}>
                التداول ينطوي على مخاطر عالية. أنت تتحمل كامل المسؤولية عن قراراتك الاستثمارية. نحن لا نقدم نصائح استثمارية.
              </Text>

              <Text style={styles.heading}>6. الخصوصية والبيانات</Text>
              <Text style={styles.paragraph}>
                بيانات المستخدم محمية وفقاً لسياسة الخصوصية. نحن نستخدم تشفير قوي لحماية معلوماتك.
              </Text>

              <Text style={styles.heading}>7. التعديلات على الشروط</Text>
              <Text style={styles.paragraph}>
                نحتفظ بالحق في تعديل هذه الشروط في أي وقت. سيتم إخطار المستخدمين بأي تغييرات جوهرية.
              </Text>

              <Text style={styles.heading}>8. الإنهاء</Text>
              <Text style={styles.paragraph}>
                نحتفظ بالحق في إنهاء الحسابات التي تنتهك هذه الشروط أو تشكل خطراً على الخدمة.
              </Text>

              <Text style={styles.heading}>9. القانون الحاكم</Text>
              <Text style={styles.paragraph}>
                تخضع هذه الشروط للقوانين السارية في المملكة العربية السعودية.
              </Text>

              <Text style={styles.heading}>10. التواصل معنا</Text>
              <Text style={styles.paragraph}>
                إذا كان لديك أي أسئلة حول هذه الشروط، يرجى التواصل معنا عبر البريد الإلكتروني: support@tradingbot.com
              </Text>
            </View>
          </View>
        </ModernCard>
      </ScrollView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  headerGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingTop: 24,
    paddingBottom: 16,
    paddingHorizontal: 16,
    borderBottomLeftRadius: 16,
    borderBottomRightRadius: 16,
    marginBottom: 12,
  },
  backButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: theme.colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  backButtonText: {
    fontSize: 20,
    color: theme.colors.text,
    fontWeight: '600',
  },
  headerTitle: {
    flex: 1,
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.colors.text,
    textAlign: 'center',
  },
  headerSpacer: {
    width: 40,
  },
  content: {
    flex: 1,
  },
  scrollContent: {
    flex: 1,
    paddingHorizontal: 16,
    paddingBottom: 16,
  },
  section: {},
  title: {
    fontSize: theme.typography.fontSize.xxl,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: theme.spacing.lg,
  },
  lastUpdated: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.lg,
  },
  heading: {
    fontSize: theme.typography.fontSize.base,
    fontWeight: '600',
    color: theme.colors.primary,
    marginTop: theme.spacing.lg,
    marginBottom: theme.spacing.md,
  },
  paragraph: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.text,
    lineHeight: 24,
    marginBottom: theme.spacing.md,
  },
});

export default TermsAndConditionsScreen;
