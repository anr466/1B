/**
 * شاشة سياسة الخصوصية
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

const PrivacyPolicyScreen = ({ onBack }) => {
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
            <Text style={styles.title}>سياسة الخصوصية</Text>

            <Text style={styles.lastUpdated}>آخر تحديث: 2025-10-26</Text>

            <View style={styles.content}>
              <Text style={styles.heading}>1. مقدمة</Text>
              <Text style={styles.paragraph}>
                نحن نقدر خصوصيتك ونلتزم بحماية بيانات المستخدمين. تشرح هذه السياسة كيفية جمع واستخدام وحماية معلوماتك.
              </Text>

              <Text style={styles.heading}>2. البيانات التي نجمعها</Text>
              <Text style={styles.paragraph}>
                نجمع المعلومات التالية:
                {'\n'}• معلومات الحساب (الاسم، البريد الإلكتروني، رقم الهاتف)
                {'\n'}• بيانات التداول والمحفظة
                {'\n'}• معلومات الجهاز والموقع
                {'\n'}• سجلات الاستخدام والنشاط
              </Text>

              <Text style={styles.heading}>3. كيفية استخدام البيانات</Text>
              <Text style={styles.paragraph}>
                نستخدم بيانات المستخدم لـ:
                {'\n'}• توفير وتحسين الخدمات
                {'\n'}• المصادقة والأمان
                {'\n'}• التواصل معك بشأن الحسابات والتحديثات
                {'\n'}• تحليل الاستخدام وتحسين الأداء
              </Text>

              <Text style={styles.heading}>4. حماية البيانات</Text>
              <Text style={styles.paragraph}>
                نستخدم تشفير AES-256 لحماية بيانات المستخدمين. جميع الاتصالات محمية بـ HTTPS/SSL.
              </Text>

              <Text style={styles.heading}>5. مشاركة البيانات</Text>
              <Text style={styles.paragraph}>
                لا نشارك بيانات المستخدمين مع أطراف ثالثة دون موافقة صريحة، باستثناء:
                {'\n'}• مزودي الخدمات الضروريين
                {'\n'}• الامتثال للقوانين واللوائح
                {'\n'}• حماية الحقوق والأمان
              </Text>

              <Text style={styles.heading}>6. حقوق المستخدم</Text>
              <Text style={styles.paragraph}>
                لديك الحق في:
                {'\n'}• الوصول إلى بيانات حسابك
                {'\n'}• تصحيح المعلومات غير الدقيقة
                {'\n'}• حذف حسابك وبيانات المستخدم
                {'\n'}• الاعتراض على معالجة البيانات
              </Text>

              <Text style={styles.heading}>7. ملفات تعريف الارتباط</Text>
              <Text style={styles.paragraph}>
                يستخدم التطبيق ملفات تعريف الارتباط لتحسين تجربة المستخدم والحفاظ على الجلسات.
              </Text>

              <Text style={styles.heading}>8. الروابط الخارجية</Text>
              <Text style={styles.paragraph}>
                قد يحتوي التطبيق على روابط لمواقع خارجية. نحن لا نتحمل مسؤولية سياسات الخصوصية الخاصة بها.
              </Text>

              <Text style={styles.heading}>9. تحديثات السياسة</Text>
              <Text style={styles.paragraph}>
                قد نحدث هذه السياسة من وقت لآخر. سيتم إخطارك بأي تغييرات جوهرية.
              </Text>

              <Text style={styles.heading}>10. التواصل معنا</Text>
              <Text style={styles.paragraph}>
                إذا كان لديك أسئلة حول سياسة الخصوصية، يرجى التواصل معنا:
                {'\n'}البريد الإلكتروني: privacy@tradingbot.com
                {'\n'}الهاتف: +966 XX XXX XXXX
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

export default PrivacyPolicyScreen;
