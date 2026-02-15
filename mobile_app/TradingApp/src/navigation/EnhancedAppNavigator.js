/**
 * نظام التنقل المحسن والموحد
 * يدعم التنقل الهرمي والتبويبات مع تصميم موحد
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { View, StyleSheet, NavigationContainer } from 'react-native';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import { isAdmin } from '../utils/userUtils';
import GlobalHeader from '../components/GlobalHeader';
import { theme } from '../theme/theme';

// استيراد الأيقونات المخصصة
import BrandIcon from '../components/BrandIcons';

// أيقونات التبويبات
const DashboardIcon = ({ color, size }) => <BrandIcon name="dashboard" size={size} color={color} />;
const WalletIcon = ({ color, size }) => <BrandIcon name="wallet" size={size} color={color} />;
const ChartIcon = ({ color, size }) => <BrandIcon name="chart" size={size} color={color} />;
const HistoryIcon = ({ color, size }) => <BrandIcon name="history" size={size} color={color} />;
const ProfileIcon = ({ color, size }) => <BrandIcon name="user" size={size} color={color} />;
const AdminIcon = ({ color, size }) => <BrandIcon name="shield" size={size} color={color} />;

// استيراد الشاشات الموجودة
import DashboardScreen from '../screens/DashboardScreen';
import PortfolioScreen from '../screens/PortfolioScreen';
import TradingSettingsScreen from '../screens/TradingSettingsScreen';
import TradeHistoryScreen from '../screens/TradeHistoryScreen';
import ProfileScreen from '../screens/ProfileScreen';
import BinanceKeysScreen from '../screens/BinanceKeysScreen';
import UsageGuideScreen from '../screens/UsageGuideScreen';

// استيراد شاشات Settings
import ImprovedNotificationSettingsScreen from '../screens/ImprovedNotificationSettingsScreen';
import TermsAndConditionsScreen from '../screens/TermsAndConditionsScreen';
import PrivacyPolicyScreen from '../screens/PrivacyPolicyScreen';

// استيراد شاشات Admin
import AdminDashboardScreen from '../screens/AdminDashboard';
import AdminErrorsScreen from '../screens/AdminErrorsScreen';
import AdminNotificationSettingsScreen from '../screens/AdminNotificationSettingsScreen';
import UserManagementScreen from '../screens/UserManagementScreen';
import CreateUserScreen from '../screens/CreateUserScreen';
// ✅ تم دمج AdminTradingControlScreen في AdminDashboard

// استيراد Onboarding
import SimplifiedOnboardingStack from '../screens/onboarding/SimplifiedOnboardingStack';
import SecureStorageService from '../services/SecureStorageService';

// استيراد شاشة التحقق الموحدة
import VerifyActionScreen from '../screens/VerifyActionScreen';

// استيراد شاشة الإشعارات
import NotificationsScreen from '../screens/NotificationsScreen';

const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

// ✅ استخدام useIsAdmin Hook الموحد بدلاً من دالة مكررة

// خيارات البنر الموحد الجديد
const getGlobalHeaderOptions = (title, user, showNotification = false) => ({
  header: (props) => (
    <GlobalHeader
      {...props}
      title={title}
      showBack={props.navigation.canGoBack()}
      isAdminUser={isAdmin(user)}
      showNotification={showNotification}
      onNotificationPress={() => props.navigation.navigate('Notifications')}
    />
  ),
  headerShown: true,
  cardStyle: { backgroundColor: '#0F111A' },
});

// مكون أيقونة احترافي مع أيقونات مخصصة
const TabIcon = ({ IconComponent, color, size }) => (
  <View style={styles.tabIconContainer}>
    <IconComponent
      color={color}
      size={size}
    />
  </View>
);

// Stack Navigator لكل تبويب
const DashboardStack = ({ user, onLogout }) => (
  <Stack.Navigator
    screenOptions={{
      headerShown: false, // Dashboard لديه Header مخصص
      cardStyle: { backgroundColor: '#0F111A' },
      cardStyleInterpolator: ({ current, layouts }) => ({
        cardStyle: {
          transform: [
            {
              translateX: current.progress.interpolate({
                inputRange: [0, 1],
                outputRange: [layouts.screen.width, 0],
              }),
            },
          ],
        },
      }),
    }}
  >
    <Stack.Screen name="DashboardMain">
      {(props) => (
        <DashboardScreen
          {...props}
          user={user}
          onNavigate={(screen) => props.navigation.navigate(screen)}
          onLogout={onLogout}
        />
      )}
    </Stack.Screen>

    {/* شاشة الإشعارات */}
    <Stack.Screen
      name="Notifications"
      options={getGlobalHeaderOptions('الإشعارات')}
    >
      {(props) => (
        <NotificationsScreen
          {...props}
          user={user}
          onBack={() => props.navigation.goBack()}
        />
      )}
    </Stack.Screen>
  </Stack.Navigator>
);

const PortfolioStack = ({ user }) => (
  <Stack.Navigator
    screenOptions={getGlobalHeaderOptions('المحفظة', user, true)}
  >
    <Stack.Screen
      name="PortfolioMain"
    >
      {(props) => (
        <PortfolioScreen
          {...props}
          user={user}
          navigation={props.navigation}
        />
      )}
    </Stack.Screen>
    {/* ✅ تم نقل BinanceKeys إلى TradingStack فقط لتجنب التكرار */}
  </Stack.Navigator>
);

const TradingStack = ({ user }) => (
  <Stack.Navigator
    screenOptions={getGlobalHeaderOptions('إعدادات التداول', user, true)}
  >
    <Stack.Screen
      name="TradingMain"
    >
      {(props) => (
        <TradingSettingsScreen
          {...props}
          user={user}
          onBack={() => props.navigation.goBack()}
        />
      )}
    </Stack.Screen>

    <Stack.Screen
      name="BinanceKeys"
      options={getGlobalHeaderOptions('مفاتيح Binance', user)}
    >
      {(props) => (
        <BinanceKeysScreen
          {...props}
          user={user}
          onBack={() => props.navigation.goBack()}
          navigation={props.navigation}
        />
      )}
    </Stack.Screen>

    {/* ✅ شاشة التحقق — مطلوبة لحفظ/حذف مفاتيح Binance */}
    <Stack.Screen
      name="VerifyAction"
      options={{ headerShown: false }}
    >
      {(props) => (
        <VerifyActionScreen
          {...props}
          user={user}
          navigation={props.navigation}
        />
      )}
    </Stack.Screen>
  </Stack.Navigator>
);

const HistoryStack = ({ user }) => (
  <Stack.Navigator
    screenOptions={getGlobalHeaderOptions('سجل الصفقات', user, true)}
  >
    <Stack.Screen
      name="HistoryMain"
    >
      {(props) => (
        <TradeHistoryScreen
          {...props}
          user={user}
          onBack={() => props.navigation.goBack()}
        />
      )}
    </Stack.Screen>
  </Stack.Navigator>
);

const ProfileStack = ({ user, onLogout }) => (
  <Stack.Navigator
    screenOptions={getGlobalHeaderOptions('الملف الشخصي', user, true)}
  >
    <Stack.Screen
      name="ProfileMain"
    >
      {(props) => (
        <ProfileScreen
          {...props}
          user={user}
          onBack={() => props.navigation.goBack()}
          onLogout={onLogout}
          navigation={props.navigation}
        />
      )}
    </Stack.Screen>

    {/* شاشات الإعدادات */}
    <Stack.Screen
      name="NotificationSettings"
      options={getGlobalHeaderOptions('إعدادات الإشعارات', user)}
    >
      {(props) => (
        <ImprovedNotificationSettingsScreen
          {...props}
          user={user}
          navigation={props.navigation}
        />
      )}
    </Stack.Screen>

    <Stack.Screen
      name="TermsAndConditions"
      options={getGlobalHeaderOptions('الشروط والأحكام', user)}
    >
      {(props) => (
        <TermsAndConditionsScreen
          {...props}
          navigation={props.navigation}
          onBack={() => props.navigation.goBack()}
        />
      )}
    </Stack.Screen>

    <Stack.Screen
      name="PrivacyPolicy"
      options={getGlobalHeaderOptions('سياسة الخصوصية', user)}
    >
      {(props) => (
        <PrivacyPolicyScreen
          {...props}
          navigation={props.navigation}
          onBack={() => props.navigation.goBack()}
        />
      )}
    </Stack.Screen>

    {/* ✅ شاشة التحقق من الهوية */}
    <Stack.Screen
      name="VerifyAction"
      options={{ headerShown: false }}
    >
      {(props) => (
        <VerifyActionScreen
          {...props}
          user={user}
          navigation={props.navigation}
        />
      )}
    </Stack.Screen>

    {/* ✅ شاشة دليل الاستخدام - متاحة من ProfileStack */}
    <Stack.Screen
      name="UsageGuide"
      options={getGlobalHeaderOptions('📖 دليل الاستخدام', user)}
    >
      {(props) => (
        <UsageGuideScreen
          {...props}
          user={user}
        />
      )}
    </Stack.Screen>
  </Stack.Navigator>
);

// Admin Stack - يظهر فقط للأدمن
const AdminStack = ({ user }) => (
  <Stack.Navigator
    screenOptions={getGlobalHeaderOptions('لوحة الإدارة', user, true)}
  >
    <Stack.Screen
      name="AdminDashboard"
    >
      {(props) => (
        <AdminDashboardScreen
          {...props}
          user={user}
        />
      )}
    </Stack.Screen>

    <Stack.Screen
      name="AdminErrors"
      options={getGlobalHeaderOptions('سجل الأخطاء')}
      component={AdminErrorsScreen}
    />
    <Stack.Screen
      name="AdminNotificationSettings"
      options={getGlobalHeaderOptions('إعدادات الإشعارات')}
      component={AdminNotificationSettingsScreen}
    />
    <Stack.Screen
      name="UserManagement"
      options={getGlobalHeaderOptions('إدارة المستخدمين')}
    >
      {(props) => (
        <UserManagementScreen
          {...props}
          navigation={props.navigation}
        />
      )}
    </Stack.Screen>
    <Stack.Screen
      name="CreateUser"
      options={getGlobalHeaderOptions('إضافة مستخدم')}
    >
      {(props) => (
        <CreateUserScreen
          {...props}
          navigation={props.navigation}
        />
      )}
    </Stack.Screen>
    {/* ✅ تم دمج AdminTrading في AdminDashboard */}
  </Stack.Navigator>
);

// التنقل الرئيسي المحسن
const EnhancedAppNavigator = ({ user, onLogout, isNewUser = false }) => {
  const [showOnboarding, setShowOnboarding] = React.useState(null);

  // ✅ التحقق من حالة Onboarding - يظهر فقط للمستخدم الجديد
  React.useEffect(() => {
    const checkOnboarding = async () => {
      try {
        // ✅ إذا كان المستخدم عائد (ليس جديد) - لا نعرض Onboarding أبداً
        if (!isNewUser) {
          console.log('👤 مستخدم عائد - تخطي Onboarding');
          setShowOnboarding(false);
          return;
        }

        // ✅ إذا كان مستخدم جديد - نتحقق إذا أكمل Onboarding من قبل
        const completed = await SecureStorageService.getSecureItem(
          `onboarding_completed_${user?.id}`
        );

        if (completed === 'true') {
          console.log('✅ المستخدم أكمل Onboarding سابقاً');
          setShowOnboarding(false);
        } else {
          console.log('🆕 مستخدم جديد - عرض Onboarding');
          setShowOnboarding(true);
        }
      } catch (error) {
        console.error('خطأ في قراءة حالة Onboarding:', error);
        // في حالة الخطأ - لا نعرض Onboarding للمستخدم العائد
        setShowOnboarding(isNewUser);
      }
    };

    if (user?.id) {
      checkOnboarding();
    }
  }, [user?.id, isNewUser]);

  // ✅ فحص إذا كان المستخدم أدمن - استخدام دالة isAdmin
  const isAdminUser = isAdmin(user);

  // ✅ فحص حرج: التأكد من وجود بيانات المستخدم
  if (!user || !user.id) {
    console.error('🔴 خطأ حرج: بيانات المستخدم غير موجودة في Navigator');
    return null;
  }

  // طباعة للتشخيص
  console.log('🔍 [Navigator] User Object:', JSON.stringify(user));
  console.log('🔍 [Navigator] isAdmin:', isAdminUser);
  console.log('🔍 [Navigator] isNewUser:', isNewUser);
  console.log('🔍 [Navigator] showOnboarding:', showOnboarding);

  // ✅ إذا كان مستخدم جديد ولم يكمل Onboarding - عرض Onboarding
  if (showOnboarding === true) {
    return (
      <SimplifiedOnboardingStack
        user={user}
        onComplete={() => {
          setShowOnboarding(false);
        }}
      />
    );
  }

  // إذا كانت حالة Onboarding غير محددة بعد، عدم عرض أي شيء
  if (showOnboarding === null) {
    return null;
  }

  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: '#161925',
          borderTopColor: '#2A3250',
          borderTopWidth: 1,
          paddingBottom: 10,
          paddingTop: 10,
          height: 75,
          elevation: 8,
          shadowColor: '#000',
          shadowOffset: { width: 0, height: -2 },
          shadowOpacity: 0.1,
          shadowRadius: 4,
        },
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: theme.colors.textSecondary,
        tabBarShowLabel: true,
        tabBarLabelStyle: {
          fontSize: 10,
          fontWeight: '500',
          marginTop: 4,
        },
        tabBarIconStyle: {
          marginBottom: 0,
        },
      }}
    >
      <Tab.Screen
        name="Dashboard"
        options={{
          tabBarLabel: 'الرئيسية',
          tabBarIcon: ({ size, focused }) => (
            <TabIcon
              IconComponent={DashboardIcon}
              color={focused ? theme.colors.primary : theme.colors.textSecondary}
              size={size}
            />
          ),
        }}
      >
        {(props) => <DashboardStack {...props} user={user} onLogout={onLogout} />}
      </Tab.Screen>

      <Tab.Screen
        name="Portfolio"
        options={{
          tabBarLabel: 'المحفظة',
          tabBarIcon: ({ size, focused }) => (
            <TabIcon
              IconComponent={WalletIcon}
              color={focused ? theme.colors.primary : theme.colors.textSecondary}
              size={size}
            />
          ),
        }}
      >
        {(props) => <PortfolioStack {...props} user={user} />}
      </Tab.Screen>

      <Tab.Screen
        name="Trading"
        options={{
          tabBarLabel: 'التداول',
          tabBarIcon: ({ size, focused }) => (
            <TabIcon
              IconComponent={ChartIcon}
              color={focused ? theme.colors.primary : theme.colors.textSecondary}
              size={size}
            />
          ),
        }}
      >
        {(props) => <TradingStack {...props} user={user} />}
      </Tab.Screen>

      <Tab.Screen
        name="History"
        options={{
          tabBarLabel: 'السجل',
          tabBarIcon: ({ size, focused }) => (
            <TabIcon
              IconComponent={HistoryIcon}
              color={focused ? theme.colors.primary : theme.colors.textSecondary}
              size={size}
            />
          ),
        }}
      >
        {(props) => <HistoryStack {...props} user={user} />}
      </Tab.Screen>

      {/* Admin Tab - يظهر فقط للأدمن */}
      {isAdminUser && (
        <Tab.Screen
          name="Admin"
          options={{
            tabBarLabel: 'الإدارة',
            tabBarIcon: ({ size, focused }) => (
              <TabIcon
                IconComponent={AdminIcon}
                color={focused ? theme.colors.primary : theme.colors.textSecondary}
                size={size}
              />
            ),
          }}
        >
          {(props) => <AdminStack {...props} user={user} />}
        </Tab.Screen>
      )}

      <Tab.Screen
        name="Profile"
        options={{
          tabBarLabel: 'الملف الشخصي',
          tabBarIcon: ({ size, focused }) => (
            <TabIcon
              IconComponent={ProfileIcon}
              color={focused ? theme.colors.primary : theme.colors.textSecondary}
              size={size}
            />
          ),
        }}
      >
        {(props) => <ProfileStack {...props} user={user} onLogout={onLogout} />}
      </Tab.Screen>
    </Tab.Navigator>
  );
};

const styles = StyleSheet.create({
  // أنماط التابات المحسنة
  tabIconContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 4,
  },
  tabIndicator: {
    position: 'absolute',
    bottom: -10,
    width: 40,
    height: 3,
    borderRadius: 2,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#161925',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#2A3250',
  },
  headerTitle: {
    color: theme.colors.primary,
    fontSize: 18,
    fontWeight: '600',
    flex: 1,
    textAlign: 'center',
  },
  headerButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#1E2235',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerButtonText: {
    color: theme.colors.primary,
    fontSize: 18,
    fontWeight: '600',
  },
});

export default EnhancedAppNavigator;
