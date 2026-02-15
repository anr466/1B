/**
 * 📜 شاشة سجل الصفقات النهائية - نظيفة ومركزة
 *
 * الوظائف فقط:
 * 1. عرض سجل الصفقات المغلقة (read-only)
 * 2. الفلاتر (تاريخ، عملة، نتيجة)
 * 3. الإحصائيات التاريخية
 * 4. تفاصيل كل صفقة
 *
 * ممنوع:
 * ❌ الصفقات النشطة (في شاشة التداول)
 * ❌ فتح/إغلاق صفقات (Backend فقط)
 */

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  RefreshControl,
  SafeAreaView,
  StatusBar,
  ActivityIndicator,
  TouchableOpacity,
  TextInput,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import { theme } from '../theme/theme';
import ModernCard from '../components/ModernCard';
import ModernInput from '../components/ModernInput';
import Icon from '../components/CustomIcons';
import DatabaseApiService from '../services/DatabaseApiService';
import { DemoModeIcon, RealModeIcon, WarningIcon } from '../components/TradingModeIcons';
import { useBackHandlerWithConfirmation } from '../utils/BackHandlerUtil';
import BrandIcon from '../components/BrandIcons';
import DailyHeatmap from '../components/charts/DailyHeatmap';
import TradeDistributionChart from '../components/charts/TradeDistributionChart';
import UnifiedEmptyState from '../components/UnifiedEmptyState';

// أيقونات سجل الصفقات
const StatsChartIcon = ({ size = 24, color = theme.colors.text }) => <BrandIcon name="chart" size={size} color={color} />;
const FilterIcon = ({ size = 24, color = theme.colors.text }) => <BrandIcon name="menu" size={size} color={color} />;
const ProfitIcon = ({ size = 24, color = theme.colors.success }) => <BrandIcon name="trending-up" size={size} color={color} />;
const LossIcon = ({ size = 24, color = theme.colors.error }) => <BrandIcon name="trending-down" size={size} color={color} />;
const TotalIcon = ({ size = 24, color = theme.colors.text }) => <BrandIcon name="list" size={size} color={color} />;
const SuccessIcon = ({ size = 24, color = theme.colors.success }) => <BrandIcon name="check-circle" size={size} color={color} />;
import { useTradingModeContext } from '../context/TradingModeContext';
import { TradeHistorySkeleton } from '../components/SkeletonLoader';
import ToastService from '../services/ToastService';
import errorHandler from '../services/UnifiedErrorHandler';
import { useIsAdmin } from '../hooks/useIsAdmin';
import AdminModeBanner from '../components/AdminModeBanner';
// ✅ AdminModeSwitcher تم نقله إلى GlobalHeader

const TradeHistoryScreen = ({ user }) => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // ✅ إصلاح Race Conditions
  const isMountedRef = useRef(true);

  // ✅ استخدام Context الموحد لوضع التداول
  const {
    tradingMode,
    getModeText,
    getModeColor,
    refreshCounter,
    getCurrentViewMode,
  } = useTradingModeContext();

  // ✅ استخدام Hook موحد لفحص الأدمن
  const isAdmin = useIsAdmin(user);

  // ✅ تحديد نوع البيانات (حقيقي/وهمي)
  const isDemoData = tradingMode === 'demo' || isAdmin;

  // ✅ الوضع الفعلي للعرض
  const currentViewMode = getCurrentViewMode();

  // الفلاتر
  const [filters, setFilters] = useState({
    period: 'week', // week | month | all
    coin: 'all',
    result: 'all', // all | profit | loss
  });

  // ✅ حالة البحث
  const [searchQuery, setSearchQuery] = useState('');
  const [showSearch, setShowSearch] = useState(false);

  // البيانات
  const [stats, setStats] = useState({
    totalTrades: 0,
    winningTrades: 0,
    losingTrades: 0,
    winRate: '0.0',  // ✅ توحيد الاسم مع Dashboard (successRate → winRate)
    totalProfit: '0.00',
    averageProfit: '0.00',
    bestTrade: '0.00',
    worstTrade: '0.00',
  });

  const [trades, setTrades] = useState([]);

  // ✅ حالة المفضلة
  const [favorites, setFavorites] = useState({}); // { tradeId: true/false }

  // ✅ فلترة الصفقات مع البحث
  const filteredTrades = useMemo(() => {
    let result = trades;

    // ✅ تطبيق البحث على اسم العملة
    if (searchQuery.trim()) {
      const query = searchQuery.trim().toLowerCase();
      result = result.filter(trade =>
        (trade.symbol || '').toLowerCase().includes(query) ||
        (trade.coin || '').toLowerCase().includes(query) ||
        (trade.strategy || '').toLowerCase().includes(query)
      );
    }

    return result;
  }, [trades, searchQuery]);

  // ✅ معالجة زر الرجوع من الجهاز - عرض Dialog تأكيد قبل الخروج
  useBackHandlerWithConfirmation(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.period, filters.coin, filters.result]); // ✅ فقط عند تغيير الفلاتر الفعلية

  // ✅ إعادة تحميل البيانات عند تغيير وضع التداول (مع debounce لمنع 429)
  useEffect(() => {
    if (refreshCounter > 0) {
      // ✅ تأخير عشوائي لمنع الطلبات المتزامنة (429 Rate Limit)
      const delay = Math.random() * 500 + 400; // 400-900ms
      const timer = setTimeout(() => {
        loadData();
      }, delay);
      return () => clearTimeout(timer);
    }
  }, [refreshCounter]);

  const loadData = useCallback(async (isRefresh = false) => {
    if (!isMountedRef.current) { return; }

    if (isRefresh) {
      if (isMountedRef.current) { setRefreshing(true); }
    } else {
      if (isMountedRef.current) { setLoading(true); }
    }

    try {
      await Promise.all([
        loadStats(),
        loadTrades(),
      ]);
    } catch (error) {
      // ✅ استخدام UnifiedErrorHandler بدلاً من console.error
      errorHandler.handle(error, {
        context: 'TradeHistory:loadData',
        showToast: true,
        userMessage: 'فشل تحميل سجل الصفقات',
      });
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
        setRefreshing(false);
      }
    }
  }, [filters, currentViewMode, user]);

  const loadStats = useCallback(async () => {
    if (!isMountedRef.current) { return; }
    try {
      if (!user?.id) { return; }

      // ✅ تمرير الوضع للأدمن
      const response = await DatabaseApiService.getStats(
        user.id,
        isAdmin ? currentViewMode : null
      );

      if (response.success && isMountedRef.current) {
        const data = response.data;
        setStats({
          totalTrades: data.totalTrades || 0,
          winningTrades: data.winningTrades || 0,
          losingTrades: data.losingTrades || 0,
          winRate: data.winRate || data.successRate || '0.0',  // ✅ دعم كلا الاسمين للتوافق العكسي
          totalProfit: data.totalProfit || '0.00',
          averageProfit: data.averageProfit || '0.00',
          bestTrade: data.bestTrade || '0.00',
          worstTrade: data.worstTrade || '0.00',
        });
      }
    } catch (error) {
      // ✅ معالجة صامتة - الإحصائيات غير حرجة
      errorHandler.handle(error, {
        context: 'TradeHistory:loadStats',
        showToast: false,
        logToConsole: true,
      });
    }
  }, [user, currentViewMode]);

  const loadTrades = useCallback(async () => {
    if (!isMountedRef.current) { return; }
    try {
      if (!user?.id) { return; }

      // ✅ تمرير الوضع للأدمن
      const response = await DatabaseApiService.getTrades(
        user.id,
        isAdmin ? currentViewMode : null
      );

      if (response.success && isMountedRef.current) {
        // التأكد من أن response.data هو array
        const tradesData = Array.isArray(response.data)
          ? response.data
          : (response.data?.trades || []);

        // فلترة الصفقات المغلقة فقط
        let closedTrades = tradesData.filter(trade =>
          trade.status === 'closed' || trade.status === 'completed'
        );

        // ✅ تطبيق فلتر الفترة الزمنية
        if (filters.period !== 'all') {
          const now = new Date();
          const periodDays = filters.period === 'week' ? 7 : 30;
          const cutoffDate = new Date(now.getTime() - periodDays * 24 * 60 * 60 * 1000);
          closedTrades = closedTrades.filter(trade => {
            const tradeDate = new Date(trade.closed_at || trade.created_at);
            return tradeDate >= cutoffDate;
          });
        }

        // ✅ تطبيق فلتر النتيجة (رابحة/خاسرة)
        if (filters.result !== 'all') {
          closedTrades = closedTrades.filter(trade => {
            const profit = parseFloat(trade.profit_loss || 0);
            return filters.result === 'profit' ? profit > 0 : profit < 0;
          });
        }

        setTrades(closedTrades);
      }
    } catch (error) {
      // ✅ معالجة واضحة - الصفقات مهمة
      errorHandler.handle(error, {
        context: 'TradeHistory:loadTrades',
        showToast: true,
        userMessage: 'فشل تحميل الصفقات',
      });
    }
  }, [user, filters, currentViewMode]);

  const getProfitColor = (value) => {
    const numValue = parseFloat(value.toString().replace(/[+$,%]/g, ''));
    if (numValue > 0) { return theme.colors.success; }
    if (numValue < 0) { return theme.colors.error; }
    return theme.colors.textSecondary;
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('ar-SA', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const handleRefresh = useCallback(() => {
    if (isMountedRef.current) {
      loadData(true);
    }
  }, [loadData]);

  // ✅ تبديل المفضلة
  const toggleFavorite = useCallback(async (trade) => {
    const tradeId = trade.id;
    const currentStatus = favorites[tradeId] || trade.is_favorite || false;
    const newStatus = !currentStatus;

    try {
      const response = await DatabaseApiService.toggleTradeFavorite(tradeId, currentStatus);
      if (response.success) {
        setFavorites(prev => ({
          ...prev,
          [tradeId]: newStatus
        }));
        ToastService.showSuccess(
          newStatus ? 'تمت الإضافة للمفضلة' : 'تمت الإزالة من المفضلة'
        );
      } else {
        ToastService.showError(response.error || 'فشل تحديث المفضلة');
      }
    } catch (error) {
      ToastService.showError('حدث خطأ');
    }
  }, [favorites]);

  const FilterButton = ({ label, value, currentValue, onPress }) => (
    <TouchableOpacity
      style={[
        styles.filterButton,
        currentValue === value && styles.filterButtonActive,
      ]}
      onPress={onPress}
    >
      <Text style={[
        styles.filterButtonText,
        currentValue === value && styles.filterButtonTextActive,
      ]}>
        {label}
      </Text>
    </TouchableOpacity>
  );

  // ✅ عرض Skeleton Loader بدلاً من ActivityIndicator
  if (loading) {
    return (
      <View style={styles.container}>
        <TradeHistorySkeleton />
      </View>
    );
  }

  const modeColor = getModeColor?.() || '#4A90E2';

  return (
    <View style={styles.container}>
      {/* ✅ Banner تحذيري للأدمن */}
      {isAdmin && <AdminModeBanner />}

      {/* ✅ وضع التداول يظهر الآن في Header العام */}

      <ScrollView
        style={styles.content}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={handleRefresh}
            tintColor={modeColor}
          />
        }
      >
        {/* تحذير التداول الحقيقي - يظهر فقط عند وجود صفقات */}
        {tradingMode === 'real' && trades.length > 0 && (
          <View style={[styles.realTradingWarning, { backgroundColor: theme.colors.warning + '20', borderLeftColor: theme.colors.warning }]}>
            <View style={styles.warningIconContainer}>
              <WarningIcon size={24} color={theme.colors.warning} />
            </View>
            <Text style={[styles.warningText, { color: theme.colors.warning }]}>
              هذه الصفقات حقيقية من Binance
            </Text>
          </View>
        )}

        {/* Daily Heatmap - خريطة الأرباح اليومية */}
        {user && (
          <DailyHeatmap
            userId={user.id}
            isAdmin={isAdmin}
            tradingMode={tradingMode}
            months={3}
          />
        )}

        {/* ✅ Trade Distribution Chart - توزيع الصفقات */}
        {user && trades.length > 0 && (
          <TradeDistributionChart
            trades={trades}
            title="توزيع الصفقات"
            showLegend={true}
            chartWidth={200}
          />
        )}

        {/* ✅ شريط البحث */}
        {showSearch && (
          <ModernInput
            placeholder="ابحث بالاسم أو العملة أو الاستراتيجية..."
            value={searchQuery}
            onChangeText={setSearchQuery}
            icon="search"
            containerStyle={styles.searchInput}
            rightAction={
              <TouchableOpacity
                onPress={() => {
                  setSearchQuery('');
                  setShowSearch(false);
                }}
                style={styles.clearSearchButton}
              >
                <BrandIcon name="x" size={20} color={theme.colors.textSecondary} />
              </TouchableOpacity>
            }
          />
        )}

        {/* 1. الفلاتر */}
        <ModernCard style={styles.card}>
          <View style={styles.sectionHeader}>
            <View style={{ flexDirection: 'row', alignItems: 'center', flex: 1 }}>
              <FilterIcon size={22} color={theme.colors.primary} />
              <Text style={styles.sectionTitle}>الفلاتر</Text>
            </View>
            <TouchableOpacity
              style={styles.searchToggleButton}
              onPress={() => setShowSearch(!showSearch)}
              testID="toggle-search"
            >
              <BrandIcon
                name={showSearch ? 'x' : 'search'}
                size={20}
                color={showSearch ? theme.colors.error : theme.colors.primary}
              />
            </TouchableOpacity>
          </View>

          <Text style={styles.filterLabel}>الفترة الزمنية</Text>
          <View style={styles.filterButtons}>
            <FilterButton
              label="أسبوع"
              value="week"
              currentValue={filters.period}
              onPress={() => setFilters({ ...filters, period: 'week' })}
            />
            <FilterButton
              label="شهر"
              value="month"
              currentValue={filters.period}
              onPress={() => setFilters({ ...filters, period: 'month' })}
            />
            <FilterButton
              label="الكل"
              value="all"
              currentValue={filters.period}
              onPress={() => setFilters({ ...filters, period: 'all' })}
            />
          </View>

          <Text style={styles.filterLabel}>النتيجة</Text>
          <View style={styles.filterButtons}>
            <FilterButton
              label="الكل"
              value="all"
              currentValue={filters.result}
              onPress={() => setFilters({ ...filters, result: 'all' })}
            />
            <FilterButton
              label="رابحة"
              value="profit"
              currentValue={filters.result}
              onPress={() => setFilters({ ...filters, result: 'profit' })}
            />
            <FilterButton
              label="خاسرة"
              value="loss"
              currentValue={filters.result}
              onPress={() => setFilters({ ...filters, result: 'loss' })}
            />
          </View>
        </ModernCard>

        {/* 2. إحصائيات الصفقات - بيانات فريدة غير موجودة في Dashboard */}
        <ModernCard style={styles.card}>
          <View style={styles.sectionHeader}>
            <StatsChartIcon size={22} color={theme.colors.primary} />
            <Text style={styles.sectionTitle}>تفاصيل الصفقات</Text>
            {/* ✅ شارة توضيحية لنوع البيانات */}
            <Text style={styles.dataTypeBadge}>
              ({isDemoData ? '📊 بيانات تجريبية' : '💰 بيانات حقيقية'})
            </Text>
          </View>

          {/* توزيع الصفقات (رابحة/خاسرة) - فريد لهذه الشاشة */}
          <View style={styles.statsGrid}>
            <View style={styles.statBox}>
              <ProfitIcon size={32} color={theme.colors.success} />
              <Text style={[styles.statValue, { color: theme.colors.success }]}>
                {stats.winningTrades}
              </Text>
              <Text style={styles.statLabel}>رابحة</Text>
            </View>
            <View style={styles.statBox}>
              <LossIcon size={32} color={theme.colors.error} />
              <Text style={[styles.statValue, { color: theme.colors.error }]}>
                {stats.losingTrades}
              </Text>
              <Text style={styles.statLabel}>خاسرة</Text>
            </View>
          </View>

          {/* تفاصيل الأداء - فريدة لهذه الشاشة */}
          <View style={styles.additionalStats}>
            <View style={styles.additionalStatRow}>
              <Text style={styles.additionalStatLabel}>متوسط الربح للصفقة</Text>
              <Text style={[styles.additionalStatValue, { color: getProfitColor(stats.averageProfit) }]}>
                ${stats.averageProfit}
              </Text>
              {/* ✅ شارة توضيح مصدر البيانات */}
              <Text style={styles.dataSourceBadge}>
                من: {isDemoData ? '📊 قاعدة البيانات التجريبية' : '💰 Binance API'}
              </Text>
            </View>
            <View style={styles.additionalStatRow}>
              <Text style={styles.additionalStatLabel}>أفضل صفقة</Text>
              <Text style={[styles.additionalStatValue, { color: theme.colors.success }]}>
                +${stats.bestTrade}
              </Text>
              {/* ✅ شارة توضيح مصدر البيانات */}
              <Text style={styles.dataSourceBadge}>
                من: {isDemoData ? '📊 قاعدة البيانات التجريبية' : '💰 Binance API'}
              </Text>
            </View>
            <View style={styles.additionalStatRow}>
              <Text style={styles.additionalStatLabel}>أسوأ صفقة</Text>
              <Text style={[styles.additionalStatValue, { color: theme.colors.error }]}>
                -${Math.abs(parseFloat(stats.worstTrade))}</Text>
              {/* ✅ شارة توضيح مصدر البيانات */}
              <Text style={styles.dataSourceBadge}>
                من: {isDemoData ? '📊 قاعدة البيانات التجريبية' : '💰 Binance API'}
              </Text>
            </View>
          </View>
        </ModernCard>

        {/* 3. قائمة الصفقات */}
        <ModernCard style={styles.card}>
          <View style={styles.sectionHeader}>
            <Icon name="list" size={20} color={theme.colors.primary} />
            <Text style={styles.sectionTitle}>
              قائمة الصفقات ({filteredTrades.length})
              {searchQuery.trim() && (
                <Text style={styles.searchResultsCount}>
                  {' '}(نتيجة البحث)
                </Text>
              )}
            </Text>
          </View>

          {filteredTrades.length === 0 ? (
            <UnifiedEmptyState
              variant={searchQuery.trim() ? 'search' : 'default'}
              title={searchQuery.trim() ? 'لا توجد نتائج' : 'لا توجد صفقات مغلقة'}
              description={
                searchQuery.trim()
                  ? `لا توجد صفقات تطابق \"${searchQuery}\"`
                  : 'جرّب:\n• تغيير الفترة الزمنية\n• التحقق من الصفقات النشطة'
              }
              actionLabel={searchQuery.trim() ? 'مسح البحث' : null}
              onAction={() => {
                if (searchQuery.trim()) {
                  setSearchQuery('');
                }
              }}
              testID="trades-empty-state"
            />
          ) : (
            filteredTrades.map((trade, index) => (
              <View key={trade.id || `trade-${index}-${trade.created_at}`} style={styles.tradeCard}>
                <View style={styles.tradeHeader}>
                  <View style={styles.tradeSymbol}>
                    <Text style={styles.tradeSymbolText}>{trade.symbol || trade.coin}</Text>
                    <Text style={styles.tradeStrategy}>{trade.strategy || 'استراتيجية آلية'}</Text>
                  </View>
                  <View style={styles.tradeHeaderRight}>
                    <TouchableOpacity
                      style={styles.favoriteButton}
                      onPress={() => toggleFavorite(trade)}
                      testID={`favorite-${trade.id}`}
                    >
                      <BrandIcon
                        name={favorites[trade.id] || trade.is_favorite ? 'star-filled' : 'star'}
                        size={22}
                        color={favorites[trade.id] || trade.is_favorite ? theme.colors.warning : theme.colors.textSecondary}
                      />
                    </TouchableOpacity>
                    <View style={[
                      styles.tradeBadge,
                      {
                        backgroundColor: parseFloat(trade.profit_loss || trade.profitLoss || 0) > 0
                          ? theme.colors.success + '20'
                          : theme.colors.error + '20',
                      },
                    ]}>
                      <Text style={[
                        styles.tradeBadgeText,
                        {
                          color: parseFloat(trade.profit_loss || trade.profitLoss || 0) > 0
                            ? theme.colors.success
                            : theme.colors.error,
                        },
                      ]}>
                        {parseFloat(trade.profit_loss || trade.profitLoss || 0) > 0 ? 'ربح' : 'خسارة'}
                      </Text>
                    </View>
                  </View>
                </View>

                <View style={styles.tradeDetails}>
                  <View style={styles.tradeDetailRow}>
                    <Text style={styles.tradeDetailLabel}>التاريخ</Text>
                    <Text style={styles.tradeDetailValue}>
                      {formatDate(trade.exit_time || trade.entry_time || trade.created_at)}
                    </Text>
                  </View>
                  <View style={styles.tradeDetailRow}>
                    <Text style={styles.tradeDetailLabel}>الدخول</Text>
                    <Text style={styles.tradeDetailValue}>${trade.entry_price || '0.00'}</Text>
                  </View>
                  <View style={styles.tradeDetailRow}>
                    <Text style={styles.tradeDetailLabel}>الخروج</Text>
                    <Text style={styles.tradeDetailValue}>${trade.exit_price || '0.00'}</Text>
                  </View>
                </View>

                <View style={styles.tradeProfitRow}>
                  <Text style={styles.tradeProfitLabel}>الربح/الخسارة</Text>
                  <View style={styles.tradeProfitValues}>
                    <Text style={[
                      styles.tradeProfitAmount,
                      { color: getProfitColor(trade.profit_loss || trade.profitLoss || 0) },
                    ]}>
                      ${trade.profit_loss || trade.profitLoss || '0.00'}
                    </Text>
                    <Text style={[
                      styles.tradeProfitPercentage,
                      { color: getProfitColor(trade.profit_loss_pct || trade.profitLossPercentage || 0) },
                    ]}>
                      ({trade.profit_loss_pct || trade.profitLossPercentage || '0.0'}%)
                    </Text>
                  </View>
                </View>
              </View>
            ))
          )}
        </ModernCard>

        <View style={styles.bottomSpacing} />
      </ScrollView>
    </View>
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
  loadingText: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.lg,
  },
  headerGradient: {
    paddingTop: 24,
    paddingBottom: 16,
    paddingHorizontal: 16,
    borderBottomLeftRadius: 16,
    borderBottomRightRadius: 16,
    marginBottom: 12,
  },
  headerContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-start',
  },
  headerText: {
    marginRight: 12,
  },
  // L1 (رئيسي - عنوان الشاشة)
  headerTitle: {
    ...theme.hierarchy.primary,
    color: theme.colors.text,
  },
  modeSubtitle: {
    fontSize: 12,
    marginTop: 4,
    fontWeight: '600',
  },
  content: {
    flex: 1,
    paddingHorizontal: 16,
  },
  card: {
    marginBottom: 16,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 16,
  },
  // L2 (مهم - عنوان القسم)
  sectionTitle: {
    ...theme.hierarchy.secondary,
    color: theme.colors.text,
    marginRight: theme.spacing.sm,
  },
  // Filters
  filterLabel: {
    fontSize: theme.typography.fontSize.sm,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: theme.spacing.sm,
    marginTop: theme.spacing.md,
  },
  filterButtons: {
    flexDirection: 'row',
    gap: 8,
    marginBottom: 8,
  },
  filterButton: {
    flex: 1,
    paddingVertical: 10,
    paddingHorizontal: theme.spacing.lg,
    borderRadius: theme.borderRadius.md,
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.border,
    alignItems: 'center',
  },
  filterButtonActive: {
    backgroundColor: theme.colors.primary,
    borderColor: theme.colors.primary,
  },
  filterButtonText: {
    fontSize: theme.typography.fontSize.sm,
    fontWeight: '600',
    color: theme.colors.textSecondary,
  },
  filterButtonTextActive: {
    color: theme.colors.white,
  },
  // Stats
  statsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    marginBottom: 16,
  },
  statBox: {
    width: '50%',
    alignItems: 'center',
    paddingVertical: 16,
    gap: 8,
  },
  // L1 (رئيسي - الإحصائيات)
  statValue: {
    ...theme.hierarchy.primary,
    color: theme.colors.text,
    marginTop: 4,
  },
  // L4 (ثانوي)
  statLabel: {
    ...theme.hierarchy.caption,
    color: theme.colors.textSecondary,
  },
  totalProfitCard: {
    alignItems: 'center',
    paddingVertical: 20,
    paddingHorizontal: 16,
    borderRadius: 12,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: theme.colors.primary + '30',
  },
  // L4 (ثانوي)
  totalProfitLabel: {
    ...theme.hierarchy.caption,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.sm,
  },
  // L1 (حرج - إجمالي الربح)
  totalProfitValue: {
    ...theme.hierarchy.hero,
  },
  additionalStats: {
    borderTopWidth: 1,
    borderTopColor: theme.colors.border,
    paddingTop: theme.spacing.lg,
  },
  additionalStatRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 8,
  },
  additionalStatLabel: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.textSecondary,
  },
  additionalStatValue: {
    fontSize: theme.typography.fontSize.sm,
    fontWeight: '600',
  },
  // Search & Filters
  searchInput: {
    marginBottom: theme.spacing.md,
  },
  clearSearchButton: {
    padding: 4,
  },
  searchToggleButton: {
    padding: 8,
    marginStart: theme.spacing.sm,
  },
  searchResultsCount: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.textSecondary,
    fontWeight: '400',
  },
  // Trade List
  emptyList: {
    alignItems: 'center',
    paddingVertical: 40,
  },
  emptyText: {
    fontSize: theme.typography.fontSize.base,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.lg,
    fontWeight: '600',
  },
  emptySubtext: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.textSecondary,
    marginTop: theme.spacing.md,
    textAlign: 'center',
    lineHeight: 20,
  },
  tradeCard: {
    padding: theme.spacing.lg,
    backgroundColor: theme.colors.surface,
    borderRadius: theme.borderRadius.lg,
    marginBottom: theme.spacing.md,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  tradeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 12,
  },
  tradeHeaderRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  favoriteButton: {
    padding: 4,
    minWidth: 36,
    minHeight: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  tradeSymbol: {
    flex: 1,
  },
  // L2 (مهم - اسم العملة)
  tradeSymbolText: {
    ...theme.hierarchy.secondary,
    color: theme.colors.text,
    marginBottom: 4,
  },
  // L5 (تفاصيل)
  tradeStrategy: {
    ...theme.hierarchy.tiny,
    color: theme.colors.textSecondary,
  },
  tradeBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 6,
  },
  tradeBadgeText: {
    fontSize: 12,
    fontWeight: '700',
  },
  tradeDetails: {
    marginBottom: 12,
  },
  tradeDetailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 6,
  },
  tradeDetailLabel: {
    fontSize: theme.typography.fontSize.sm,
    color: theme.colors.textSecondary,
  },
  tradeDetailValue: {
    fontSize: theme.typography.fontSize.sm,
    fontWeight: '600',
    color: theme.colors.text,
  },
  tradeProfitRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: theme.spacing.md,
    borderTopWidth: 1,
    borderTopColor: theme.colors.border,
  },
  tradeProfitLabel: {
    fontSize: theme.typography.fontSize.sm,
    fontWeight: '600',
    color: theme.colors.text,
  },
  tradeProfitValues: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  tradeProfitAmount: {
    fontSize: 18,
    fontWeight: '700',
  },
  tradeProfitPercentage: {
    fontSize: theme.typography.fontSize.sm,
    fontWeight: '600',
  },
  bottomSpacing: {
    height: 40,
  },
  realTradingWarning: {
    flexDirection: 'row',
    alignItems: 'center',
    borderLeftWidth: 4,
    padding: 12,
    marginHorizontal: 16,
    marginVertical: 12,
    borderRadius: 8,
  },
  warningIconContainer: {
    marginRight: 8,
  },
  warningText: {
    fontWeight: '600',
    flex: 1,
  },
  // ✅ Style لشارة توضيح نوع البيانات
  dataTypeBadge: {
    fontSize: 12,
    fontWeight: '500',
    color: '#666666',  // ✅ لون رمادي للبيانات الوهمية
    backgroundColor: 'rgba(128, 128, 128, 0.1)',  // ✅ خلفية شفافة
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 4,
    marginLeft: 8,
  },
  // ✅ Style لشارة توضيح مصدر البيانات
  dataSourceBadge: {
    fontSize: 10,
    fontWeight: '400',
    color: '#888888',
    backgroundColor: 'rgba(128, 128, 128, 0.05)',
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: 2,
    marginLeft: 6,
  },
});

export default TradeHistoryScreen;
