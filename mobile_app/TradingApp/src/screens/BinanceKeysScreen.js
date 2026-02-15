/**
 * شاشة إدارة مفاتيح Binance
 * للشروحات التفصيلية، انظر إلى دليل الاستخدام (📖)
 * للمستخدمين العاديين: تفعيل التداول الحقيقي عبر Binance API
 */

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  SafeAreaView,
  StatusBar,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  TouchableOpacity,
  RefreshControl,
} from 'react-native';
import { theme } from '../theme/theme';
import ModernButton from '../components/ModernButton';
import ModernCard from '../components/ModernCard';
import ModernInput from '../components/ModernInput';
import DatabaseApiService from '../services/DatabaseApiService';
import ToastService from '../services/ToastService';
import { useIsAdmin } from '../hooks/useIsAdmin';
import AdminModeBanner from '../components/AdminModeBanner';
import { validateBinanceKeys, maskKey } from '../utils/binanceKeyValidator';
import { AlertService } from '../components/CustomAlert';
import { useBackHandler } from '../utils/BackHandlerUtil';
import SecureActionsService, { SECURE_ACTIONS } from '../services/SecureActionsService';
import Icon from '../components/CustomIcons';
import { useTradingModeContext } from '../context/TradingModeContext';
import { useNavigation } from '@react-navigation/native';
// ✅ GlobalHeader يأتي من Navigator

const BinanceKeysScreen = ({ user, onBack }) => {
  // استخدام Hook في أعلى المكون فقط
  const isAdmin = useIsAdmin(user);
  const navigation = useNavigation();

  // ✅ استخدام Context لتحديث حالة المفاتيح وجلب trading_mode
  const { updateKeysStatus, tradingMode } = useTradingModeContext();

  const [binanceKeys, setBinanceKeys] = useState({
    apiKey: '',
    secretKey: '',
    isConfigured: false,
    tradingMode: 'virtual', // virtual or real
    keyId: null, // معرف المفتاح من قاعدة البيانات
  });

  const [isLoading, setIsLoading] = useState(false);
  const [showKeys, setShowKeys] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [securityInfo, setSecurityInfo] = useState(null);
  const [showGuide, setShowGuide] = useState(false);

  useEffect(() => {
    let isMounted = true;

    const initialize = async () => {
      if (isMounted) {
        await loadBinanceKeys();
      }
    };

    initialize();

    return () => {
      isMounted = false;
    };
  }, []);

  // ✅ معالجة زر الرجوع - تأكيد إذا كانت هناك مفاتيح غير محفوظة
  useBackHandler(() => {
    if (hasUnsavedChanges) {
      AlertService.confirm(
        'تنبيه',
        'لديك مفاتيح غير محفوظة. هل تريد المغادرة بدون حفظ؟',
        () => onBack && onBack(),
        () => { }
      );
      return true;
    }
    onBack && onBack();
    return true;
  });

  // ✅ Pull-to-refresh
  const onRefresh = async () => {
    setRefreshing(true);
    await loadBinanceKeys();
    setRefreshing(false);
  };

  const loadBinanceKeys = async () => {
    setIsLoading(true);
    try {
      if (!user?.id) {
        console.error('[ERROR] معرف المستخدم غير متوفر في شاشة مفاتيح Binance');
        setIsLoading(false);
        return;
      }

      // التحقق من الاتصال أولاً
      const isConnected = await DatabaseApiService.checkConnection();
      if (!isConnected) {
        console.warn('[WARNING]️ لا يوجد اتصال بالخادم في شاشة مفاتيح Binance');
        setIsLoading(false);
        return;
      }

      const response = await DatabaseApiService.getBinanceKeys(user.id);
      if (response.success) {
        const hasKeys = response.data.hasKeys || response.data.isConfigured;
        setBinanceKeys({
          apiKey: response.data.apiKey || '',
          secretKey: '', // لا يُرجع من الخادم للأمان
          isConfigured: hasKeys,
          keyId: response.data.keyId || null,
          tradingMode: tradingMode || (isAdmin ? 'real' : (hasKeys ? 'real' : 'not_configured')),
        });
      }
    } catch (error) {
      console.error('خطأ في تحميل مفاتيح Binance:', error);
      // عرض رسالة خطأ واضحة للمستخدم
      let errorMessage = 'فشل تحميل مفاتيح Binance';
      if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
        errorMessage = 'انتهى وقت الانتظار. يرجى المحاولة مرة أخرى';
      } else if (error?.code === 'ERR_NETWORK' || error?.message?.includes('Network Error')) {
        errorMessage = 'فشل الاتصال بالخادم. تحقق من اتصالك بالإنترنت';
      }
      ToastService.showError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleTestKeys = async () => {
    // التحقق من صحة الصيغة أولاً
    const validation = validateBinanceKeys(binanceKeys.apiKey, binanceKeys.secretKey);

    if (!validation.valid) {
      AlertService.error('خطأ في التحقق', validation.errors.join('\n'));
      return;
    }

    // التحقق الفعلي من Binance API
    try {
      setIsLoading(true);
      ToastService.showInfo('⏳ جاري التحقق من المفاتيح مع Binance...');

      const result = await DatabaseApiService.validateBinanceKeys(
        binanceKeys.apiKey,
        binanceKeys.secretKey
      );

      if (result?.success && result?.valid) {
        const canTrade = result.can_trade ? '✅ يمكن التداول' : '⚠️ لا يمكن التداول';
        const balanceInfo = result.balances_count ? `\n📊 عدد الأصول: ${result.balances_count}` : '';

        // ===== فحص الأمان التفصيلي =====
        const security = result.security;
        let securityInfo = '';

        if (security) {
          setSecurityInfo(security);

          const scoreEmoji = security.score >= 70 ? '🟢' : security.score >= 40 ? '🟡' : '🔴';
          securityInfo = `\n\n${scoreEmoji} درجة الأمان: ${security.score}/100`;

          if (security.withdrawals_enabled) {
            securityInfo += '\n\n🚨 تحذير حرج: صلاحية السحب مفعّلة!\nيجب تعطيلها فوراً من إعدادات API في Binance';
          }

          if (!security.ip_restricted) {
            securityInfo += '\n\n⚠️ المفتاح غير مقيّد بعنوان IP\nننصح بتقييده بعنوان IP السيرفر';
          }

          if (security.is_safe) {
            securityInfo += '\n\n✅ المفتاح آمن — يمكنك حفظه';
          }
        }

        AlertService.success(
          '✅ المفاتيح صحيحة!',
          `تم التحقق من المفاتيح بنجاح مع Binance\n\n${canTrade}${balanceInfo}${securityInfo}`
        );
      } else {
        const errorMsg = result?.error || result?.message || 'المفاتيح غير صحيحة';
        AlertService.error(
          '❌ فشل التحقق',
          `لم يتم التحقق من المفاتيح مع Binance\n\n${errorMsg}\n\n💡 تحقق من صحة المفاتيح من حسابك على Binance`
        );
      }
    } catch (error) {
      console.error('[ERROR] خطأ في التحقق من المفاتيح:', error);
      AlertService.error(
        'خطأ في الاتصال',
        'فشل الاتصال بالخادم\n\nتحقق من الاتصال بالإنترنت وحاول مرة أخرى'
      );
    } finally {
      setIsLoading(false);
    }
  };

  // حفظ المفاتيح - مع التحقق من الهوية
  const handleSaveKeys = async () => {
    if (!binanceKeys.apiKey.trim() || !binanceKeys.secretKey.trim()) {
      ToastService.showError('يرجى إدخال جميع المفاتيح المطلوبة');
      return;
    }

    // التحقق من صحة المفاتيح أولاً
    const validation = validateBinanceKeys(binanceKeys.apiKey, binanceKeys.secretKey);
    if (!validation.valid) {
      AlertService.error('خطأ في التحقق', validation.errors.join('\n'));
      return;
    }

    // ✅ تحذير حرج للمستخدم العادي قبل حفظ المفاتيح
    if (!isAdmin) {
      AlertService.confirm(
        '⚠️ تحذير مهم جداً',
        'بعد حفظ هذه المفاتيح:\n\n✅ النظام سيبدأ التداول فوراً\n✅ بأموالك الحقيقية من Binance\n✅ خسائر/أرباح حقيقية 100%\n✅ النظام يعمل 24/7 تلقائياً\n\nهل تريد بدء التداول الحقيقي؟',
        () => {
          // المتابعة للتحقق
          proceedToVerification();
        },
        () => {
          ToastService.showInfo('تم الإلغاء - لم يتم حفظ المفاتيح');
        },
        'نعم، ابدأ التداول',
        'لا، إلغاء'
      );
      return;
    }

    // للأدمن: المتابعة مباشرة
    proceedToVerification();
  };

  // دالة منفصلة للتحقق والحفظ
  const proceedToVerification = () => {
    AlertService.confirm(
      'حفظ مفاتيح Binance',
      'سيتم إرسال رمز تحقق للتأكيد.\n\nهل تريد المتابعة؟',
      () => {
        navigation?.navigate('VerifyAction', {
          action: SECURE_ACTIONS.CHANGE_BINANCE_KEYS,
          newValue: {
            api_key: binanceKeys.apiKey,
            secret_key: binanceKeys.secretKey,
          },
          onSuccess: async (result) => {
            // إعادة تحميل المفاتيح
            await loadBinanceKeys();
            // تحديث حالة المفاتيح في Context
            updateKeysStatus(true);

            // رسالة تعكس الوضع الفعلي + خطوات الجاهزية
            let successMessage;
            if (isAdmin) {
              // للأدمن: الرسالة تعتمد على trading_mode
              if (tradingMode === 'demo') {
                successMessage = 'تم حفظ مفاتيح Binance للعرض.\n\nالتداول يبقى وهمي (Demo Mode).';
              } else if (tradingMode === 'real') {
                successMessage = 'تم حفظ مفاتيح Binance بنجاح.\n\n⚠️ أنت في وضع التداول الحقيقي\nالنظام الخلفي سيتداول بأموال حقيقية!';
              } else { // auto
                successMessage = 'تم حفظ مفاتيح Binance بنجاح.\n\n✅ الوضع التلقائي: النظام الخلفي سيتداول حقيقياً.';
              }
            } else {
              // للمستخدم العادي - توحيد: حفظ + تفعيل تلقائي
              try {
                // تفعيل التداول تلقائياً
                await DatabaseApiService.updateSettings(user.id, {
                  trading_enabled: true,
                });

                successMessage = '✅ تم تفعيل التداول الحقيقي!\n\n🎯 ماذا حدث الآن؟\n\n1️⃣ المفاتيح محفوظة ومشفرة ✅\n2️⃣ التداول الحقيقي مُفعّل ✅\n3️⃣ النظام سيبدأ خلال 60 ثانية ⏱️\n\n💡 النظام الآن:\n• يفحص السوق كل 60 ثانية\n• يفتح صفقات عند وجود فرص\n• يغلق تلقائياً عند شروط الإغلاق\n\n⚙️ يمكنك ضبط الإعدادات من Trading Settings\n📊 تابع النتائج من Dashboard';
              } catch (error) {
                console.error('فشل تفعيل التداول تلقائياً:', error);
                successMessage = '✅ تم حفظ المفاتيح!\n\n⚠️ يرجى تفعيل التداول من Trading Settings';
              }
            }

            AlertService.success('🎉 جاهز للتداول', successMessage);
          },
          onCancel: () => {
            // لا شيء
          },
        });
      },
      () => { }
    );
  };

  // حذف المفاتيح - مع التحقق من الهوية
  const handleDeleteKeys = () => {
    if (!binanceKeys.keyId) {
      ToastService.showError('لا يوجد مفتاح للحذف');
      return;
    }

    AlertService.warning(
      'تحذير - حذف مفاتيح Binance',
      'سيتم إرسال رمز تحقق للتأكيد.\n\nهل تريد المتابعة؟',
      [
        { text: 'إلغاء', style: 'cancel' },
        {
          text: 'نعم، تابع',
          style: 'destructive',
          onPress: () => {
            navigation?.navigate('VerifyAction', {
              action: SECURE_ACTIONS.DELETE_BINANCE_KEYS,
              newValue: null,
              onSuccess: async (result) => {
                setBinanceKeys({
                  apiKey: '',
                  secretKey: '',
                  isConfigured: false,
                  tradingMode: 'not_configured',
                  keyId: null,
                });
                updateKeysStatus(false);

                // رسالة تعكس الوضع الفعلي
                AlertService.success('نجح ✅', 'تم حذف مفاتيح Binance.\n\n⚠️ التداول يتطلب ربط مفاتيح Binance.');
              },
              onCancel: () => {
                // لا شيء
              },
            });
          },
        },
      ]
    );
  };

  const getTradingModeText = (mode) => {
    if (mode === 'real') { return 'تداول حقيقي'; }
    if (mode === 'demo' && isAdmin) { return 'تداول وهمي (أدمن)'; }
    return 'يرجى ربط مفاتيح Binance';
  };

  const getTradingModeColor = (mode) => {
    if (mode === 'real') { return theme.colors.success; }
    if (mode === 'demo' && isAdmin) { return theme.colors.info; }
    return theme.colors.error; // أحمر لأن الربط إلزامي
  };

  if (isLoading && !binanceKeys.isConfigured) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor={theme.colors.background} />
      {/* ✅ Banner تحذيري للأدمن */}
      {isAdmin && <AdminModeBanner />}

      {/* ✅ Header يأتي من Navigator - لا حاجة لتكراره هنا */}

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView
          style={styles.content}
          showsVerticalScrollIndicator={false}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={onRefresh}
              tintColor={theme.colors.primary}
            />
          }
        >
          {/* حالة التداول الحالية */}
          <ModernCard variant="elevated">
            <View style={styles.statusSection}>
              <Text style={styles.sectionTitle}>حالة التداول الحالية</Text>
              <View style={styles.statusContainer}>
                <View style={[styles.statusIndicator, { backgroundColor: getTradingModeColor(binanceKeys.tradingMode) }]} />
                <Text style={[styles.statusText, { color: getTradingModeColor(binanceKeys.tradingMode) }]}>
                  {getTradingModeText(binanceKeys.tradingMode)}
                </Text>
              </View>
              <Text style={styles.statusDescription}>
                {binanceKeys.tradingMode === 'real'
                  ? 'التداول يتم باستخدام أموال حقيقية عبر Binance API'
                  : binanceKeys.tradingMode === 'demo' && isAdmin
                    ? 'محفظة اختبارية - أموال وهمية للتعلم والاختبار'
                    : '❌ ربط مفاتيح Binance إلزامي للتداول. أضف مفاتيحك الآن.'
                }
              </Text>
            </View>
          </ModernCard>

          {/* إدارة المفاتيح */}
          <ModernCard>
            <View style={styles.keysSection}>
              <Text style={styles.sectionTitle}>مفاتيح Binance</Text>

              <ModernInput
                label="API Key"
                value={binanceKeys.apiKey}
                onChangeText={(text) => {
                  setBinanceKeys(prev => ({ ...prev, apiKey: text }));
                  setHasUnsavedChanges(true);
                }}
                placeholder="أدخل API Key"
                secureTextEntry={!showKeys}
                editable={!binanceKeys.isConfigured}
              />

              <ModernInput
                label="Secret Key"
                value={binanceKeys.secretKey}
                onChangeText={(text) => {
                  setBinanceKeys(prev => ({ ...prev, secretKey: text }));
                  setHasUnsavedChanges(true);
                }}
                placeholder="أدخل Secret Key"
                secureTextEntry={!showKeys}
                editable={!binanceKeys.isConfigured}
              />

              <TouchableOpacity
                style={styles.showKeysButton}
                onPress={() => setShowKeys(!showKeys)}
              >
                <View style={styles.showKeysContent}>
                  <Icon name={showKeys ? "eye-off" : "eye"} size={16} color={theme.colors.primary} />
                  <Text style={styles.showKeysText}>
                    {showKeys ? 'إخفاء المفاتيح' : 'إظهار المفاتيح'}
                  </Text>
                </View>
              </TouchableOpacity>
            </View>
          </ModernCard>

          {/* الإجراءات */}
          <ModernCard>
            <View style={styles.actionsSection}>
              <Text style={styles.sectionTitle}>الإجراءات</Text>

              {!binanceKeys.isConfigured ? (
                <>
                  <ModernButton
                    title="✅ اختبار المفاتيح"
                    onPress={handleTestKeys}
                    variant="info"
                    size="medium"
                    fullWidth={true}
                    style={styles.testButton}
                  />

                  <ModernButton
                    title="💾 حفظ وتفعيل التداول الحقيقي"
                    onPress={handleSaveKeys}
                    variant="success"
                    size="medium"
                    fullWidth={true}
                    loading={isLoading}
                  />
                </>
              ) : (
                <>
                  <ModernButton
                    title="تحديث المفاتيح"
                    onPress={() => {
                      setBinanceKeys(prev => ({ ...prev, isConfigured: false }));
                      setHasUnsavedChanges(false);
                    }}
                    variant="primary"
                    size="medium"
                    fullWidth={true}
                  />

                  <ModernButton
                    title={isAdmin ? 'حذف المفاتيح' : 'حذف المفاتيح (لن تتمكن من التداول)'}
                    onPress={handleDeleteKeys}
                    variant="error"
                    size="medium"
                    fullWidth={true}
                    loading={isLoading}
                  />
                </>
              )}
            </View>
          </ModernCard>

          {/* ===== نتيجة فحص الأمان ===== */}
          {securityInfo && (
            <ModernCard variant={securityInfo.is_safe ? 'elevated' : 'warning'}>
              <View style={styles.securitySection}>
                <Text style={styles.sectionTitle}>
                  {securityInfo.is_safe ? '🛡️ تقييم أمان المفتاح' : '⚠️ تقييم أمان المفتاح'}
                </Text>

                <View style={styles.securityScoreContainer}>
                  <Text style={[styles.securityScore, {
                    color: securityInfo.score >= 70 ? theme.colors.success
                      : securityInfo.score >= 40 ? theme.colors.warning
                        : theme.colors.error
                  }]}>
                    {securityInfo.score}/100
                  </Text>
                </View>

                <View style={styles.securityChecks}>
                  <View style={styles.securityCheckRow}>
                    <Text style={styles.securityCheckIcon}>
                      {!securityInfo.withdrawals_enabled ? '✅' : '🚨'}
                    </Text>
                    <Text style={[styles.securityCheckText,
                    securityInfo.withdrawals_enabled && { color: theme.colors.error, fontWeight: 'bold' }
                    ]}>
                      {!securityInfo.withdrawals_enabled
                        ? 'السحب معطّل — أموالك محمية'
                        : 'السحب مفعّل! عطّله فوراً من Binance'}
                    </Text>
                  </View>

                  <View style={styles.securityCheckRow}>
                    <Text style={styles.securityCheckIcon}>
                      {securityInfo.ip_restricted ? '✅' : '⚠️'}
                    </Text>
                    <Text style={styles.securityCheckText}>
                      {securityInfo.ip_restricted
                        ? 'مقيّد بعنوان IP — لا يعمل من جهاز آخر'
                        : 'غير مقيّد بـ IP — ننصح بتقييده'}
                    </Text>
                  </View>

                  <View style={styles.securityCheckRow}>
                    <Text style={styles.securityCheckIcon}>
                      {securityInfo.spot_enabled ? '✅' : '❌'}
                    </Text>
                    <Text style={styles.securityCheckText}>
                      {securityInfo.spot_enabled
                        ? 'التداول الفوري مفعّل'
                        : 'التداول غير مفعّل — فعّله من Binance'}
                    </Text>
                  </View>
                </View>
              </View>
            </ModernCard>
          )}

          {/* ===== دليل إنشاء مفتاح آمن ===== */}
          <ModernCard>
            <TouchableOpacity
              style={styles.guideToggle}
              onPress={() => setShowGuide(!showGuide)}
            >
              <View style={styles.guideTitleRow}>
                <Icon name="info" size={18} color={theme.colors.primary} />
                <Text style={styles.guideToggleText}>
                  كيف أنشئ مفتاح API آمن؟
                </Text>
              </View>
              <Icon
                name={showGuide ? "chevron-up" : "chevron-down"}
                size={18}
                color={theme.colors.textSecondary}
              />
            </TouchableOpacity>

            {showGuide && (
              <View style={styles.guideContent}>
                <Text style={styles.guideStep}>
                  {'1️⃣  افتح Binance → الملف الشخصي → API Management'}
                </Text>
                <Text style={styles.guideStep}>
                  {'2️⃣  اضغط Create API → اختر System Generated'}
                </Text>
                <Text style={styles.guideStep}>
                  {'3️⃣  الصلاحيات — فعّل فقط:'}
                </Text>
                <Text style={styles.guideSubStep}>
                  {'     ✅ Enable Spot & Margin Trading'}
                </Text>
                <Text style={styles.guideSubStep}>
                  {'     ❌ لا تفعّل Enable Withdrawals أبداً'}
                </Text>
                <Text style={styles.guideStep}>
                  {'4️⃣  تقييد IP — اضغط Restrict access to trusted IPs only'}
                </Text>
                <Text style={styles.guideSubStep}>
                  {'     🔒 أضف عنوان IP السيرفر فقط'}
                </Text>
                <Text style={styles.guideStep}>
                  {'5️⃣  انسخ API Key و Secret Key والصقهما هنا'}
                </Text>

                <View style={styles.guideTrustBox}>
                  <Text style={styles.guideTrustTitle}>🛡️ لماذا هذا آمن؟</Text>
                  <Text style={styles.guideTrustText}>
                    {'• بدون صلاحية سحب = لا أحد يستطيع سحب أموالك\n'}
                    {'• تقييد IP = المفتاح لا يعمل إلا من السيرفر\n'}
                    {'• حتى لو سُرق المفتاح = لا ضرر ممكن\n'}
                    {'• يمكنك حذف المفتاح من Binance في أي وقت'}
                  </Text>
                </View>
              </View>
            )}
          </ModernCard>

          {/* معلومات مهمة */}
          <ModernCard variant="warning">
            <View style={styles.warningSection}>
              <View style={styles.warningTitleContainer}>
                <Icon
                  name="warning"
                  size={18}
                  color={theme.colors.warning}
                />
                <Text style={styles.warningTitle}>حماية أموالك</Text>
              </View>
              <Text style={styles.warningText}>
                • المفتاح بدون صلاحية سحب = لا أحد يسحب أموالك{'\n'}
                • تقييد IP = المفتاح لا يعمل من أي جهاز آخر{'\n'}
                • يمكنك إلغاء المفتاح من Binance في أي لحظة{'\n'}
                • المفتاح السري مشفّر ولا يظهر بعد الحفظ{'\n'}
                • النظام يستخدم المفتاح للتداول فقط — لا سحب{'\n'}
              </Text>
            </View>
          </ModernCard>

          <View style={styles.bottomSpacing} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingVertical: 16,
    borderBottomLeftRadius: 16,
    borderBottomRightRadius: 16,
    marginBottom: 12,
  },
  backButton: {
    padding: 8,
    marginEnd: 12,
  },
  backButtonText: {
    fontSize: 24,
    color: theme.colors.primary,
    fontWeight: 'bold',
  },
  // L2: عنوان الصفحة
  headerTitle: {
    ...theme.hierarchy.secondary,
    color: theme.colors.text,
    flex: 1,
    textAlign: 'center',
  },
  headerSpacer: {
    width: 40,
  },
  content: {
    flex: 1,
    padding: 16,
  },
  statusSection: {
    alignItems: 'center',
  },
  // L2: عنوان القسم
  sectionTitle: {
    ...theme.hierarchy.secondary,
    color: theme.colors.text,
    marginBottom: theme.spacing.md,
    textAlign: 'center',
  },
  statusContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  statusIndicator: {
    width: 12,
    height: 12,
    borderRadius: 6,
    marginEnd: 8,
  },
  statusText: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  statusDescription: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
  },
  keysSection: {
    marginBottom: 12,
  },
  inputContainer: {
    marginBottom: 12,
  },
  // L4: التسميات
  inputLabel: {
    ...theme.hierarchy.caption,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: 4,
  },
  showKeysButton: {
    alignSelf: 'center',
    padding: 8,
  },
  showKeysContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  showKeysText: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.primary,
    fontWeight: '600',
  },
  actionsSection: {
    gap: 12,
  },
  warningSection: {
    padding: 12,
  },
  warningTitleContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  warningTitle: {
    fontSize: theme.typography.fontSize.base,
    fontWeight: 'bold',
    color: theme.colors.warning,
  },
  warningText: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.textSecondary,
    lineHeight: 20,
  },
  bottomSpacing: {
    height: 24,
  },
  testButton: {
    marginBottom: 12,
  },
  // ===== Security Score Section =====
  securitySection: {
    alignItems: 'center',
    padding: 8,
  },
  securityScoreContainer: {
    marginVertical: 12,
  },
  securityScore: {
    fontSize: 36,
    fontWeight: 'bold',
    textAlign: 'center',
  },
  securityChecks: {
    width: '100%',
    gap: 10,
  },
  securityCheckRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 4,
  },
  securityCheckIcon: {
    fontSize: 18,
    width: 24,
    textAlign: 'center',
  },
  securityCheckText: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text,
    flex: 1,
    lineHeight: 20,
  },
  // ===== Guide Section =====
  guideToggle: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 4,
  },
  guideTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  guideToggleText: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.primary,
    fontWeight: '600',
  },
  guideContent: {
    marginTop: 12,
    gap: 8,
  },
  guideStep: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text,
    lineHeight: 22,
    fontWeight: '600',
  },
  guideSubStep: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.textSecondary,
    lineHeight: 22,
    paddingStart: 8,
  },
  guideTrustBox: {
    backgroundColor: theme.colors.success + '15',
    borderRadius: 12,
    padding: 14,
    marginTop: 8,
    borderWidth: 1,
    borderColor: theme.colors.success + '30',
  },
  guideTrustTitle: {
    fontSize: theme.typography.fontSize.base,
    fontWeight: 'bold',
    color: theme.colors.success,
    marginBottom: 8,
    textAlign: 'center',
  },
  guideTrustText: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.text,
    lineHeight: 22,
  },
});

export default BinanceKeysScreen;
