/**
 * التطبيق الرئيسي - 1B Trading App
 * نظام تداول ذكي مع مصادقة مزدوجة ونظام تنقل متكامل
 * مع إصلاح مشكلة AsyncStorage
 */

// ✅ تعطيل console.log في الإنتاج - يجب أن يكون أول استيراد
import './src/utils/ConsoleConfig';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  StatusBar,
  View,
  I18nManager,
  AppState as RNAppState,
} from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

// تفعيل RTL (العربية) عند بدء التطبيق
// ✅ تأكد من تفعيل RTL دائماً
I18nManager.forceRTL(true);
I18nManager.allowRTL(true);

// Screens
import SplashScreen from './src/screens/SplashScreen';
import AuthScreen from './src/screens/AuthScreen';
import ForgotPasswordScreen from './src/screens/ForgotPasswordScreen';
import EnhancedAppNavigator from './src/navigation/EnhancedAppNavigator';
import PermissionsScreen from './src/screens/PermissionsScreen'; // ✅ شاشة الصلاحيات

// Services - تم إصلاح مشكلة AsyncStorage
import DatabaseAPI from './src/services/DatabaseApiService';
import NotificationService, { setNavigationRef } from './src/services/NotificationService';
import TempStorageService from './src/services/TempStorageService';
import BiometricAuth from './src/services/BiometricService';
import AsyncStorage from '@react-native-async-storage/async-storage';
import SecureStorageService from './src/services/SecureStorageService'; // ✅ للتخزين المشفر
import PermissionsService from './src/services/PermissionsService'; // ✅ خدمة الصلاحيات

// Theme
import { theme as Theme } from './src/theme/theme';

// Toast Container & Alert
import ToastContainer from './src/components/Toast/ToastContainer';
import CustomAlert, { AlertService } from './src/components/CustomAlert';

// Error Boundary
import ErrorBoundary from './src/components/ErrorBoundary';
import Logger from './src/services/LoggerService';
import cacheService from './src/services/CacheService';

// Trading Mode Context
import { TradingModeProvider } from './src/context/TradingModeContext';
import { PortfolioProvider } from './src/context/PortfolioContext';
import { ThemeProvider } from './src/context/ThemeContext';

// Connection Status
import ConnectionStatusBar from './src/components/ConnectionStatusBar';

export default function App() {
  const [appState, setAppState] = useState({
    isLoading: true,
    isLoggedIn: false,
    currentScreen: 'splash', // splash, permissions, login, register, main
    user: null,
    isNewUser: false, // ✅ لتحديد إذا كان المستخدم جديد (تسجيل جديد) أو عائد (تسجيل دخول)
  });

  const [initializationComplete, setInitializationComplete] = useState(false);
  const [splashComplete, setSplashComplete] = useState(false);
  const [initializationResult, setInitializationResult] = useState(null);
  const [isProcessingTransition, setIsProcessingTransition] = useState(false);
  const [showPermissions, setShowPermissions] = useState(false); // ✅ لعرض شاشة الصلاحيات

  // useRef لتجنب memory leaks
  const isMountedRef = useRef(true);
  const navigationRef = useRef(null); // ✅ مرجع التنقل للإشعارات
  const appStateRef = useRef(RNAppState.currentState); // ✅ حالة التطبيق (background/foreground)

  useEffect(() => {
    initializeApp();

    // ✅ بدء التنظيف التلقائي للـ cache
    cacheService.startAutoCleanup();

    // ✅ الاستماع لـ event انتهاء الجلسة (401)
    const { DeviceEventEmitter } = require('react-native');
    const sessionExpiredListener = DeviceEventEmitter.addListener('SESSION_EXPIRED', () => {
      Logger.warn('Session expired - redirecting to login', 'App');
      if (isMountedRef.current) {
        setAppState({
          isLoading: false,
          isLoggedIn: false,
          currentScreen: 'login',
          user: null,
          isNewUser: false,
        });
      }
    });

    // ✅ الاستماع لتغييرات حالة التطبيق (background/foreground)
    const handleAppStateChange = async (nextAppState) => {
      const previousState = appStateRef.current;
      appStateRef.current = nextAppState;

      console.log(`📱 AppState: ${previousState} → ${nextAppState}`);

      // عند العودة من الخلفية للمقدمة
      if (previousState.match(/inactive|background/) && nextAppState === 'active') {
        console.log('🔄 التطبيق عاد للمقدمة - فحص الجلسة...');

        try {
          // فحص إذا كان المستخدم مسجل دخول
          const savedToken = await AsyncStorage.getItem('authToken');
          const savedLoginState = await TempStorageService.getItem('isLoggedIn');

          if (savedToken && savedLoginState === 'true') {
            // التحقق من صلاحية الجلسة
            const sessionValid = await DatabaseAPI.validateSession();

            if (!sessionValid) {
              console.log('❌ الجلسة انتهت أثناء الخلفية - إعادة تسجيل الدخول');
              // تنظيف البيانات
              await AsyncStorage.removeItem('authToken');
              await TempStorageService.removeItem('isLoggedIn');
              await TempStorageService.removeItem('userData');

              if (isMountedRef.current) {
                setAppState({
                  isLoading: false,
                  isLoggedIn: false,
                  currentScreen: 'login',
                  user: null,
                  isNewUser: false,
                });
              }
            } else {
              console.log('✅ الجلسة لا تزال صالحة');
              // ✅ إرسال حدث لإعادة تحميل البيانات في الشاشات الإدارية
              DeviceEventEmitter.emit('APP_RESUMED_FROM_BACKGROUND');
            }
          }
        } catch (error) {
          Logger.warn('AppState change handler error', 'App');
        }
      }
    };

    const appStateSubscription = RNAppState.addEventListener('change', handleAppStateChange);

    // Cleanup function
    return () => {
      isMountedRef.current = false;
      sessionExpiredListener.remove();
      appStateSubscription?.remove();
      // ✅ إيقاف التنظيف التلقائي للـ cache
      cacheService.stopAutoCleanup();
    };
  }, []);

  // التحكم في الانتقال بعد اكتمال كل من التهيئة و Splash Screen
  useEffect(() => {
    if (initializationComplete && splashComplete && isMountedRef.current) {
      proceedToNextScreen();
    }
  }, [initializationComplete, splashComplete]);

  const initializeApp = async () => {
    let userData = null;
    let isUserLoggedIn = false;

    try {
      console.log('🚀 بدء تهيئة التطبيق...');

      // 0. فحص إذا كان أول استخدام للتطبيق (لعرض شاشة الصلاحيات)
      try {
        const permissionsRequested = await PermissionsService.hasRequestedPermissions();
        if (!permissionsRequested) {
          console.log('🔐 أول استخدام - سيتم عرض شاشة الصلاحيات');
          setShowPermissions(true);
        } else {
          console.log('✅ الصلاحيات تم طلبها مسبقاً');
        }
      } catch (permError) {
        Logger.error('Permission check failed', permError, 'App.initializeApp');
      }

      // 1. تهيئة الاتصال بالخادم أولاً - ✅ إجباري
      console.log('🔗 تهيئة الاتصال بخادم قاعدة البيانات...');
      const connectionInitialized = await DatabaseAPI.initializeConnection();
      console.log('📡 حالة الاتصال:', connectionInitialized ? 'متصل' : 'غير متصل');

      // ✅ فحص حرج: إذا لم يكن هناك اتصال، لا نسمح بالدخول
      if (!connectionInitialized) {
        console.error('🔴 خطأ حرج: لا يوجد اتصال بالخادم');
        throw new Error('لا يوجد اتصال بالخادم. يرجى التحقق من الاتصال بالإنترنت والمحاولة مرة أخرى.');
      }

      // 2. تهيئة خدمة الإشعارات (اختيارية - لن توقف التطبيق إذا فشلت)
      let notificationInitialized = false;
      try {
        notificationInitialized = await NotificationService.initialize();
        console.log('Firebase Notifications:', notificationInitialized ? 'مفعل' : 'غير مفعل');
      } catch (notifError) {
        console.log('تحذير: فشل في تهيئة الإشعارات:', notifError);
        notificationInitialized = false;
      }

      // 3. قراءة بيانات المستخدم المحفوظة (بغض النظر عن حالة الجلسة)
      let savedLoginState = null;
      let savedUser = null;
      let savedToken = null;

      try {
        savedLoginState = await TempStorageService.getItem('isLoggedIn');
        savedUser = await TempStorageService.getItem('userData');
      } catch (tempStorageError) {
        console.warn('⚠️ خطأ في قراءة TempStorage:', tempStorageError?.message);
        savedLoginState = null;
        savedUser = null;
      }

      try {
        savedToken = await AsyncStorage.getItem('authToken');
      } catch (asyncStorageError) {
        console.warn('⚠️ خطأ في قراءة AsyncStorage:', asyncStorageError?.message);
        savedToken = null;
      }

      // 4. محاولة قراءة userData أولاً - ✅ مع التحقق من وجود token
      if (savedUser && savedToken) {
        try {
          userData = JSON.parse(savedUser);
          console.log('✅ تم قراءة بيانات المستخدم المحفوظة مع token');
        } catch (parseError) {
          console.warn('⚠️ خطأ في تحليل userData:', parseError?.message);
          userData = null;
        }
      } else if (savedUser && !savedToken) {
        // ✅ حالة أمان: userData موجودة بدون token - تنظيف البيانات القديمة
        console.log('🔴 userData موجودة بدون token - تنظيف البيانات القديمة');
        await TempStorageService.removeItem('userData');
        await TempStorageService.removeItem('isLoggedIn');
        savedLoginState = null;
        userData = null;
      }

      // 5. ✅ التحقق من البصمة أولاً (أعلى أولوية) قبل فحص Token
      // المعيار: Biometric → Token → Manual Login
      let biometricAvailable = false;
      let biometricRegistered = false;
      let biometricUserId = null;
      let biometricAttempted = false;

      try {
        const bioResult = await BiometricAuth.initialize();
        biometricAvailable = !!bioResult?.available;
        console.log(`📱 الحساس البيومتري: available=${biometricAvailable}`);

        // الحصول على userId من userData أو من lastUserId المحفوظ
        biometricUserId = userData?.id || userData?.user_id;

        if (!biometricUserId) {
          try {
            const savedLastUserId = await TempStorageService.getItem('lastUserId');
            if (savedLastUserId) {
              biometricUserId = savedLastUserId;
              console.log(`👤 userId من lastUserId المحفوظ: ${biometricUserId}`);
            }
          } catch (storageError) {
            console.warn('⚠️ خطأ في قراءة lastUserId:', storageError?.message);
          }
        } else {
          console.log(`👤 userId من userData: ${biometricUserId}`);
        }

        // فحص إذا كانت البصمة مسجلة
        if (biometricAvailable && biometricUserId) {
          try {
            biometricRegistered = await BiometricAuth.isBiometricRegistered(biometricUserId.toString());
            console.log(`🔐 حالة البصمة: registered=${biometricRegistered}`);
          } catch (bioRegError) {
            console.warn('⚠️ خطأ في فحص تسجيل البصمة:', bioRegError?.message);
            biometricRegistered = false;
          }
        }
      } catch (bioError) {
        console.warn('⚠️ خطأ في تهيئة البصمة:', bioError?.message);
        biometricAvailable = false;
        biometricRegistered = false;
      }

      // 6. ✅ إذا البصمة مفعلة → طلبها أولاً (حتى لو Token صالح)
      if (connectionInitialized && biometricAvailable && biometricRegistered && biometricUserId) {
        try {
          const rememberMe = await AsyncStorage.getItem('remember_me');
          const savedPassword = await SecureStorageService.getSavedPassword(biometricUserId);

          console.log(`🔍 فحص شروط البصمة: rememberMe=${rememberMe}, hasPassword=${!!savedPassword}`);

          if (rememberMe === 'true' && savedPassword) {
            console.log('🔐 طلب البصمة (أولوية أولى)...');
            biometricAttempted = true;

            const bioVerifyResult = await BiometricAuth.verifyBiometric(biometricUserId.toString());

            if (bioVerifyResult.success && bioVerifyResult.username) {
              console.log('✅ نجح التحقق من البصمة');
              console.log('🔑 تسجيل دخول بعد البصمة...');

              const loginResult = await DatabaseAPI.login(bioVerifyResult.username, savedPassword);

              if (loginResult.success && loginResult.user) {
                console.log('✅ تسجيل دخول ناجح بالبصمة');
                userData = loginResult.user;
                isUserLoggedIn = true;
                // ✅ مستخدم يدخل بالبصمة = مستخدم عائد (ليس جديد)
                // سيتم تعيين isNewUserFromDB = false لاحقاً

                await TempStorageService.setItem('userData', JSON.stringify(loginResult.user));
                await TempStorageService.setItem('isLoggedIn', 'true');

                // تسجيل FCM Token
                if (notificationInitialized && userData.id) {
                  try {
                    await NotificationService.registerTokenWithServer(userData.id, DatabaseAPI);
                    console.log('✅ تم تسجيل FCM Token');
                  } catch (fcmError) {
                    console.log('تحذير: فشل في تسجيل FCM Token:', fcmError);
                  }
                }
              } else {
                console.log('❌ فشل تسجيل الدخول بعد البصمة');
                isUserLoggedIn = false;
              }
            } else {
              console.log('❌ فشل/إلغاء التحقق من البصمة - التحقق من Token...');
              isUserLoggedIn = false;
            }
          }
        } catch (bioAutoError) {
          Logger.warn('Biometric auto-login failed', 'App.initializeApp');
          biometricAttempted = true;
          isUserLoggedIn = false;
        }
      }

      // 7. إذا لم تنجح البصمة أو غير مفعلة → فحص Token (أولوية ثانية)
      // ✅ المستخدم العائد (تسجيل دخول تلقائي أو بالبصمة) = ليس مستخدم جديد
      let isNewUserFromDB = false;

      if (!isUserLoggedIn && savedLoginState === 'true' && userData && connectionInitialized) {
        try {
          console.log('🔍 فحص Token (أولوية ثانية)...');
          const sessionValid = await DatabaseAPI.validateSession();

          if (sessionValid === true) {
            console.log('✅ Token صالح - تسجيل دخول تلقائي');
            isUserLoggedIn = true;
            // ✅ مستخدم عائد بـ Token صالح = ليس مستخدم جديد
            isNewUserFromDB = false;

            if (notificationInitialized && userData.id) {
              try {
                await NotificationService.registerTokenWithServer(userData.id, DatabaseAPI);
                console.log('✅ تم تسجيل FCM Token');
              } catch (fcmError) {
                console.log('تحذير: فشل في تسجيل FCM Token:', fcmError);
              }
            }
          } else {
            console.log('❌ Token غير صالح أو منتهي - تنظيف البيانات');
            // تنظيف شامل للبيانات
            await AsyncStorage.removeItem('authToken');
            await TempStorageService.removeItem('isLoggedIn');
            await TempStorageService.removeItem('userData');
            await TempStorageService.removeItem('lastUserId');
            savedToken = null;
            userData = null;
            isUserLoggedIn = false;
          }
        } catch (sessionError) {
          Logger.error('Token validation failed', sessionError, 'App.initializeApp');
          // تنظيف شامل عند الخطأ
          await AsyncStorage.removeItem('authToken');
          await TempStorageService.removeItem('isLoggedIn');
          await TempStorageService.removeItem('userData');
          await TempStorageService.removeItem('lastUserId');
          savedToken = null;
          userData = null;
          isUserLoggedIn = false;
        }
      }

      // ✅ حفظ flag لمنع تكرار طلب البصمة في LoginScreen
      await AsyncStorage.setItem('biometric_attempted_this_session', biometricAttempted ? 'true' : 'false');

      // 8. تحديد الشاشة التالية - ✅ يجب عرض login أولاً دائماً إذا لم يكن المستخدم مسجل دخول
      let nextScreen = 'login';  // ✅ الافتراضي: login (الأمان أولاً)

      // ✅ فحص شامل: إذا كان مسجل دخول بدون token، مسح البيانات
      if (isUserLoggedIn && userData && !savedToken) {
        console.warn('🔴 تنبيه أمني: مستخدم مسجل دخول بدون token - إجبار تسجيل دخول جديد');
        await AsyncStorage.removeItem('authToken');
        await TempStorageService.removeItem('isLoggedIn');
        await TempStorageService.removeItem('userData');
        await TempStorageService.removeItem('lastUserId');
        isUserLoggedIn = false;
        userData = null;
        savedToken = null;
      }

      // ✅ فحص نهائي صارم: يجب توفر الثلاثة معاً
      if (isUserLoggedIn && userData && savedToken) {
        // تحقق إضافي من صحة userData
        if (userData.id && (userData.username || userData.email)) {
          nextScreen = 'main';
          console.log('✅ الجلسة صالحة → عرض Main App');
        } else {
          console.error('❌ بيانات المستخدم غير كاملة - إجبار تسجيل دخول');
          await AsyncStorage.removeItem('authToken');
          await TempStorageService.removeItem('isLoggedIn');
          await TempStorageService.removeItem('userData');
          await TempStorageService.removeItem('lastUserId');
          isUserLoggedIn = false;
          userData = null;
          savedToken = null;
          nextScreen = 'login';
        }
      } else {
        nextScreen = 'login';  // ✅ إجباري: عرض login إذا لم يكن مسجل دخول
        console.log('❌ المستخدم غير مسجل دخول → عرض LoginScreen');
      }

      // 7. حفظ نتائج التهيئة
      const result = {
        success: true,
        connectionInitialized,
        notificationInitialized,
        isUserLoggedIn,
        userData,
        nextScreen,
        biometricAvailable,
        biometricRegistered,
        isNewUser: isNewUserFromDB, // ✅ إضافة isNewUser من قاعدة البيانات
        message: 'تم تهيئة التطبيق بنجاح'
      };

      console.log('✅ اكتملت تهيئة التطبيق:', result);

      if (isMountedRef.current) {
        setInitializationResult(result);
        setInitializationComplete(true);
      }

    } catch (error) {
      Logger.critical('App initialization failed', error, 'App.initializeApp');

      const result = {
        success: false,
        error: error.message,
        nextScreen: 'login',
        message: 'فشل في تهيئة التطبيق - سيتم المتابعة بالوضع الأساسي'
      };

      if (isMountedRef.current) {
        setInitializationResult(result);
        setInitializationComplete(true);
      }
    }
  };

  const proceedToNextScreen = useCallback(() => {
    if (isProcessingTransition || !initializationResult) return;

    setIsProcessingTransition(true);

    setTimeout(() => {
      if (isMountedRef.current) {
        const { isUserLoggedIn, userData, nextScreen, isNewUser } = initializationResult;

        // ✅ إجباري: إذا لم يكن المستخدم مسجل دخول، عرض login دائماً
        const screenToShow = isUserLoggedIn && userData ? nextScreen : 'login';

        console.log(`🔐 Proceeding to screen: ${screenToShow} (isLoggedIn=${isUserLoggedIn}, isNewUser=${isNewUser})`);

        setAppState({
          isLoading: false,
          isLoggedIn: isUserLoggedIn,
          currentScreen: screenToShow,  // ✅ يجب أن يكون 'login' إذا لم يكن مسجل دخول
          user: userData,
          isNewUser: isNewUser || false, // ✅ استخدام isNewUser من التهيئة
        });

        setIsProcessingTransition(false);
      }
    }, 300);
  }, [isProcessingTransition, initializationResult]);

  const handleSplashComplete = () => {
    console.log('🎬 Splash Screen اكتمل');
    if (isMountedRef.current) {
      setSplashComplete(true);
    }
  };

  const handleRegister = async (registrationData) => {
    try {
      console.log('📝 بدء عملية التسجيل:', registrationData.email);

      // ⚠️ تحذير: هذه الدالة لا يجب استدعاؤها بعد نجاح OTP
      // المستخدم يُنشأ في verify-registration-otp
      console.warn('⚠️ handleRegister تم استدعاؤه - هذا لا يجب أن يحدث بعد OTP!');

      // ✅ فحص إذا كان المستخدم مسجل بالفعل
      try {
        const userData = await TempStorageService.getItem('userData');
        const isLoggedIn = await TempStorageService.getItem('isLoggedIn');

        if (userData && isLoggedIn === 'true') {
          console.log('✅ المستخدم مسجل بالفعل - تجاهل استدعاء register');
          const user = JSON.parse(userData);

          if (isMountedRef.current) {
            setAppState({
              isLoading: false,
              isLoggedIn: true,
              currentScreen: 'main',
              user: user,
              isNewUser: true,
            });
          }
          return;
        }
      } catch (checkError) {
        console.log('فحص المستخدم المسجل:', checkError);
      }

      // استدعاء API التسجيل
      const result = await DatabaseAPI.register({
        username: registrationData.email.split('@')[0],
        email: registrationData.email,
        phone: registrationData.phone,
        password: registrationData.password,
        full_name: registrationData.fullName
      });

      if (result.success && result.user) {
        console.log('✅ نجح التسجيل:', result.user);

        // حفظ بيانات المستخدم
        await TempStorageService.setItem('userData', JSON.stringify(result.user));
        await TempStorageService.setItem('isLoggedIn', 'true');

        // حفظ lastUserId لاستخدامه في البصمة مستقبلاً
        const userId = result.user.id || result.user.user_id;
        if (userId) {
          try {
            await TempStorageService.setItem('lastUserId', userId.toString());
            console.log(`✅ تم حفظ lastUserId: ${userId}`);

            // ✅ حفظ كلمة المرور بشكل مشفر للدخول التلقائي بالبصمة
            await SecureStorageService.setSavedPassword(userId, registrationData.password);
            console.log('✅ تم حفظ كلمة المرور بشكل مشفر');
          } catch (error) {
            Logger.error('Failed to save user data', error, 'App.handleRegister');
          }
        }

        // تحديث الحالة - ✅ مستخدم جديد يحتاج Onboarding
        // ✅ حفظ onboarding_completed = false في قاعدة البيانات للمستخدم الجديد
        try {
          await DatabaseAPI.updateSettings(result.user.id, { onboarding_completed: false });
          console.log('✅ تم تعيين onboarding_completed = false للمستخدم الجديد');
        } catch (error) {
          console.warn('⚠️ خطأ في تحديث onboarding_completed:', error);
        }

        if (isMountedRef.current) {
          setAppState({
            isLoading: false,
            isLoggedIn: true,
            currentScreen: 'main',
            user: result.user,
            isNewUser: true, // ✅ مستخدم جديد - يحتاج Onboarding
          });
        }

        AlertService.success('نجح', 'تم إنشاء الحساب بنجاح! مرحباً بك');
        console.log('✅ تم الانتقال للشاشة الرئيسية - مستخدم جديد');
      } else {
        console.error('❌ فشل التسجيل:', result.message);
        AlertService.error('خطأ', result.message || 'فشل التسجيل');
      }
    } catch (error) {
      Logger.error('Registration failed', error, 'App.handleRegister');
      AlertService.error('خطأ', 'حدث خطأ أثناء التسجيل. يرجى المحاولة مرة أخرى');
    }
  };

  const handleLogin = async (username, password, isBiometricLogin = false, rememberMe = false) => {
    try {
      console.log(`🔐 بدء عملية تسجيل الدخول${isBiometricLogin ? ' بالبصمة' : ''}...`);
      console.log('📧 Username:', username);

      const result = await DatabaseAPI.login(username, password);

      if (result.success && result.user) {
        console.log('✅ نجح تسجيل الدخول:', result.user);
        console.log('🔍 user_type من API:', result.user.user_type || result.user.userType);

        // ✅ التأكد من وجود user_type في userData
        const userData = {
          ...result.user,
          user_type: result.user.user_type || result.user.userType || 'user',
        };

        // ✅ حفظ بيانات المستخدم في TempStorage
        await TempStorageService.setItem('userData', JSON.stringify(userData));
        await TempStorageService.setItem('isLoggedIn', 'true');

        // ✅ حفظ authToken في AsyncStorage و TempStorageService
        if (result.token) {
          await AsyncStorage.setItem('authToken', result.token);
          await TempStorageService.setItem('authToken', result.token);
          console.log('✅ تم حفظ authToken بنجاح');
        }

        // ✅ حفظ lastUserId لاستخدامه في البصمة مستقبلاً
        const userId = userData.id || userData.user_id;
        if (userId) {
          try {
            await TempStorageService.setItem('lastUserId', userId.toString());
            console.log(`✅ تم حفظ lastUserId: ${userId}`);

            // ✅ حفظ كلمة المرور فقط إذا اختار المستخدم "تذكرني" أو كان دخول بالبصمة
            const shouldRemember = rememberMe || isBiometricLogin;
            if (shouldRemember) {
              await SecureStorageService.setSavedPassword(userId, password);
              console.log('✅ تم حفظ كلمة المرور (تذكرني مفعل)');
            } else {
              // ✅ مسح كلمة المرور المحفوظة إذا لم يختر "تذكرني"
              await SecureStorageService.removeSavedPassword(userId);
              console.log('🔒 لم يتم حفظ كلمة المرور (تذكرني غير مفعل)');
            }
          } catch (error) {
            Logger.error('Failed to save user data', error, 'App.handleLogin');
          }
        }

        // ✅ مستخدم عائد - تحديث onboarding_completed = true
        try {
          await DatabaseAPI.updateSettings(userData.id, { onboarding_completed: true });
          console.log('✅ تم تعيين onboarding_completed = true للمستخدم العائد');
        } catch (error) {
          console.warn('⚠️ خطأ في تحديث onboarding_completed:', error);
        }

        if (isMountedRef.current) {
          setAppState({
            isLoading: false,
            isLoggedIn: true,
            currentScreen: 'main',
            user: userData,
            isNewUser: false,
          });
        }

        console.log(`✅ تم الانتقال للشاشة الرئيسية${isBiometricLogin ? ' بعد البصمة الناجحة' : ''} - مستخدم عائد`);
      } else {
        console.error('❌ فشل تسجيل الدخول:', result.message);
        AlertService.error('خطأ', result.message || 'فشل تسجيل الدخول');
      }
    } catch (error) {
      Logger.error('Login failed', error, 'App.handleLogin');

      // ✅ معالجة دقيقة للأخطاء مع رسائل واضحة
      let errorMessage = 'حدث خطأ أثناء تسجيل الدخول';

      if (error?.response?.data?.error) {
        // رسالة من الخادم (أولوية أولى)
        errorMessage = error.response.data.error;
      } else if (error?.response?.status === 401) {
        errorMessage = 'كلمة المرور غير صحيحة';
      } else if (error?.response?.status === 400) {
        errorMessage = 'اسم المستخدم أو البريد الإلكتروني غير صحيح';
      } else if (error?.response?.status === 403) {
        errorMessage = 'الحساب غير مفعل. يرجى التحقق من بريدك الإلكتروني';
      } else if (error?.response?.status === 404) {
        errorMessage = 'المستخدم غير موجود';
      } else if (error?.code === 'ECONNABORTED' || error?.message?.includes('timeout')) {
        errorMessage = 'انتهى وقت الانتظار. يرجى المحاولة مرة أخرى';
      } else if (error?.code === 'ERR_NETWORK' || error?.message?.includes('Network Error')) {
        errorMessage = 'فشل الاتصال بالخادم. تحقق من اتصالك بالإنترنت';
      } else if (error?.message) {
        errorMessage = error.message;
      }

      AlertService.error('خطأ', errorMessage);
    }
  };

  const handleLogout = async () => {
    console.log('👋 تسجيل الخروج...');

    try {
      // ✅ مسح البيانات المحلية بشكل شامل
      await TempStorageService.removeItem('isLoggedIn');
      await TempStorageService.removeItem('userData');
      await TempStorageService.removeItem('authToken');

      // ✅ مسح authToken من AsyncStorage أيضاً (مهم جداً!)
      await AsyncStorage.removeItem('authToken');
      await AsyncStorage.removeItem('userData');
      await AsyncStorage.removeItem('isLoggedIn');
      console.log('🔐 تم مسح authToken من AsyncStorage');

      // ✅ إصلاح: مسح flag البصمة للسماح بطلبها مجدداً في الجلسة القادمة
      await AsyncStorage.removeItem('biometric_attempted_this_session');
      console.log('🔐 تم مسح flag البصمة');

      // ✅ مسح TradingModeContext بشكل غير مباشر (سيتم تلقائياً عند تغيير الشاشة)

      // إعادة تعيين حالة التطبيق
      if (isMountedRef.current) {
        setAppState({
          isLoading: false,
          isLoggedIn: false,
          currentScreen: 'login',
          user: null,
          isNewUser: false,
        });
      }

      console.log('✅ تم تسجيل الخروج بنجاح');
    } catch (error) {
      Logger.error('Logout failed', error, 'App.handleLogout');
    }
  };

  const handleNavigateToRegister = () => {
    if (isMountedRef.current) {
      setAppState(prev => ({
        ...prev,
        currentScreen: 'register',
      }));
    }
  };

  const handleNavigateToLogin = () => {
    if (isMountedRef.current) {
      setAppState(prev => ({
        ...prev,
        currentScreen: 'login',
      }));
    }
  };

  const handleNavigateToForgotPassword = () => {
    if (isMountedRef.current) {
      setAppState(prev => ({
        ...prev,
        currentScreen: 'forgotPassword',
      }));
    }
  };

  // ✅ معالج اكتمال شاشة الصلاحيات
  const handlePermissionsComplete = (results) => {
    console.log('✅ اكتملت شاشة الصلاحيات:', results);
    setShowPermissions(false);
  };

  const renderCurrentScreen = () => {
    const { currentScreen, isLoading, isLoggedIn, user, isNewUser } = appState;

    // ✅ عرض شاشة الصلاحيات عند أول استخدام (بعد Splash)
    if (showPermissions && !isLoading && splashComplete) {
      return <PermissionsScreen onComplete={handlePermissionsComplete} />;
    }

    if (isLoading || !splashComplete) {
      return <SplashScreen onComplete={handleSplashComplete} />;
    }

    switch (currentScreen) {
      case 'login':
      case 'register':
        return (
          <AuthScreen
            initialMode={currentScreen}
            onLogin={handleLogin}
            onRegister={handleRegister}
            onNavigateToForgotPassword={handleNavigateToForgotPassword}
            onNavigateToEmailVerification={(navData) => {
              console.log('📧 Navigate to Email Verification:', navData);
              // ✅ حفظ بيانات OTP وتغيير الشاشة
              const targetScreen = navData.screen === 'OTPSent' ? 'otpSent' : 'otpVerification';
              if (isMountedRef.current) {
                setAppState(prev => ({
                  ...prev,
                  currentScreen: targetScreen,
                  otpParams: navData,
                }));
              }
            }}
          />
        );

      case 'forgotPassword':
        return (
          <ForgotPasswordScreen
            onBack={handleNavigateToLogin}
            onNavigateToOTP={(params) => {
              console.log('📧 Navigate to OTP for password reset:', params);
              const targetScreen = params.screen === 'OTPSent' ? 'otpSent' : 'otpVerification';
              if (isMountedRef.current) {
                setAppState(prev => ({
                  ...prev,
                  currentScreen: targetScreen,
                  otpParams: params,
                }));
              }
            }}
          />
        );

      case 'main':
        // ✅ تحقق أمني حرج: يجب أن يكون المستخدم مسجل دخول وله بيانات صحيحة وtoken صالح
        if (isLoggedIn && user && user.id) {
          console.log('✅ المستخدم مسجل دخول بشكل صحيح - عرض Dashboard');
          console.log(`📋 حالة المستخدم: isNewUser=${isNewUser}, userId=${user.id}, userType=${user.user_type || user.userType}`);

          return (
            <EnhancedAppNavigator
              user={user}
              onLogout={handleLogout}
              isNewUser={isNewUser}
            />
          );
        } else {
          // ❌ حالة أمان: إذا كان currentScreen=main لكن المستخدم غير مسجل، أرجع للـ login فوراً
          console.warn('🔴 تنبيه أمني: محاولة الوصول للـ Dashboard بدون تسجيل دخول صحيح!');
          console.warn(`   isLoggedIn=${isLoggedIn}, user=${user ? 'موجود' : 'غير موجود'}, userId=${user?.id || 'لا يوجد'}`);

          // ✅ إعادة تعيين الحالة للأمان بشكل صحيح
          if (isMountedRef.current) {
            setAppState({
              isLoading: false,
              isLoggedIn: false,
              currentScreen: 'login',
              user: null,
              isNewUser: false,
            });
          }

          // ✅ مسح جميع بيانات الجلسة بشكل آمن
          Promise.all([
            AsyncStorage.removeItem('authToken'),
            AsyncStorage.removeItem('userData'),
            AsyncStorage.removeItem('isLoggedIn'),
            TempStorageService.removeItem('authToken'),
            TempStorageService.removeItem('userData'),
            TempStorageService.removeItem('isLoggedIn'),
          ]).catch(err => console.warn('⚠️ خطأ في مسح البيانات:', err));

          return (
            <AuthScreen
              initialMode="login"
              onLogin={handleLogin}
              onNavigateToRegister={handleNavigateToRegister}
              onNavigateToLogin={handleNavigateToLogin}
            />
          );
        }

      case 'otpSent':
        // ✅ شاشة اختيار طريقة التحقق + إرسال OTP
        const OTPSentScreen = require('./src/screens/OTP/OTPSentScreen').default;
        return (
          <OTPSentScreen
            navigation={{
              setOptions: () => { },
              navigate: (screen, params) => {
                console.log('🔄 Navigation from OTPSent:', screen, params);
                if (screen === 'OTPVerification') {
                  setAppState(prev => ({
                    ...prev,
                    currentScreen: 'otpVerification',
                    otpParams: { ...prev.otpParams, params: params },
                  }));
                }
              },
              goBack: () => {
                const operationType = appState.otpParams?.params?.operationType;
                const targetScreen = operationType === 'reset_password' ? 'forgotPassword' : 'register';
                setAppState(prev => ({
                  ...prev,
                  currentScreen: targetScreen,
                  otpParams: null,
                }));
              },
            }}
            route={{ params: appState.otpParams?.params || {} }}
          />
        );

      case 'otpVerification':
        // ✅ شاشة التحقق من OTP المباشرة
        const OTPVerificationScreen = require('./src/screens/OTP/OTPVerificationScreen').default;
        return (
          <OTPVerificationScreen
            navigation={{
              setOptions: () => { },
              navigate: (screen, params) => {
                console.log('🔄 Navigation from OTP:', screen, params);
                if (screen === 'OTPSuccess') {
                  setAppState(prev => ({
                    ...prev,
                    currentScreen: 'otpSuccess',
                    otpParams: { ...prev.otpParams, successParams: params },
                  }));
                } else if (screen === 'NewPassword') {
                  setAppState(prev => ({
                    ...prev,
                    currentScreen: 'newPassword',
                    otpParams: { ...prev.otpParams, params: params },
                  }));
                } else if (screen === 'OTPSent') {
                  // ✅ العودة لشاشة الإرسال (انتهاء الصلاحية أو تجاوز المحاولات)
                  setAppState(prev => ({
                    ...prev,
                    currentScreen: 'otpSent',
                    otpParams: { ...prev.otpParams, params: params },
                  }));
                }
              },
              replace: (screen, params) => {
                console.log('🔄 Replace navigation from OTP:', screen, params);
                if (screen === 'OTPSuccess') {
                  setAppState(prev => ({
                    ...prev,
                    currentScreen: 'otpSuccess',
                    otpParams: { ...prev.otpParams, successParams: params },
                  }));
                }
              },
              goBack: () => {
                // ✅ العودة لشاشة اختيار طريقة التحقق (OTPSent) وليس للشاشة الأصلية
                setAppState(prev => ({
                  ...prev,
                  currentScreen: 'otpSent',
                }));
              },
            }}
            route={{ params: appState.otpParams?.params || {} }}
          />
        );

      case 'newPassword':
        // ✅ شاشة إدخال كلمة المرور الجديدة
        const NewPasswordScreen = require('./src/screens/NewPasswordScreen').default;
        return (
          <NewPasswordScreen
            navigation={{
              navigate: (screen, params) => {
                console.log('🔄 Navigation from NewPassword:', screen, params);
                if (screen === 'Login') {
                  if (isMountedRef.current) {
                    setAppState({
                      isLoading: false,
                      isLoggedIn: false,
                      currentScreen: 'login',
                      user: null,
                      isNewUser: false,
                      otpParams: null,
                    });
                  }
                }
              },
              reset: (options) => {
                console.log('🔄 Reset navigation from NewPassword:', options);
                // ✅ بعد إعادة تعيين كلمة المرور بنجاح مع auto-login → الذهاب للـ login
                // (الحالة الحقيقية تُعالج في handleLogin من App.js)
                if (isMountedRef.current) {
                  setAppState({
                    isLoading: false,
                    isLoggedIn: false,
                    currentScreen: 'login',
                    user: null,
                    isNewUser: false,
                    otpParams: null,
                  });
                }
              },
              goBack: () => {
                setAppState(prev => ({
                  ...prev,
                  currentScreen: 'otpVerification',
                }));
              },
            }}
            route={{ params: appState.otpParams?.params || {} }}
          />
        );

      case 'otpSuccess':
        // ✅ شاشة نجاح التحقق من OTP
        const OTPSuccessScreen = require('./src/screens/OTP/OTPSuccessScreen').default;
        const successParams = appState.otpParams?.successParams || {};
        const registrationData = appState.otpParams?.params?.registrationData;
        const operationType = appState.otpParams?.params?.operationType;

        // ✅ دالة للتعامل مع نجاح التسجيل (الحساب تم إنشاؤه بالفعل في verify-registration-otp)
        const handleRegistrationSuccess = async () => {
          try {
            // الحصول على بيانات المستخدم من successParams (تم إرجاعها من verify-registration-otp)
            const userId = successParams.additionalData?.userId;
            const accessToken = successParams.additionalData?.accessToken;
            const regData = successParams.registrationData || registrationData;
            const isComplete = successParams.additionalData?.registrationComplete;

            console.log('🔍 handleRegistrationSuccess - userId:', userId, 'accessToken:', !!accessToken, 'isComplete:', isComplete);

            if (userId && accessToken) {
              console.log('✅ التسجيل تم بنجاح - الانتقال للشاشة الرئيسية...');

              const userData = {
                id: userId,
                email: regData?.email || successParams.email,
                username: regData?.username || '',
                fullName: regData?.fullName || '',
                userType: 'user'
              };

              // البيانات تم حفظها بالفعل في OTPVerificationScreen
              // فقط نحدث حالة التطبيق

              // حفظ كلمة المرور للبصمة (إذا كانت متاحة)
              if (regData?.password) {
                try {
                  await SecureStorageService.setSavedPassword(userId, regData.password);
                  console.log('✅ تم حفظ كلمة المرور بشكل مشفر');
                } catch (e) {
                  console.warn('⚠️ فشل حفظ كلمة المرور:', e);
                }
              }

              // الانتقال للشاشة الرئيسية
              if (isMountedRef.current) {
                setAppState({
                  isLoading: false,
                  isLoggedIn: true,
                  currentScreen: 'main',
                  user: userData,
                  isNewUser: true,
                  otpParams: null,
                });
              }
              console.log('✅ تم الانتقال للشاشة الرئيسية - مستخدم جديد');
            } else {
              // ✅ محاولة قراءة البيانات من التخزين (تم حفظها في OTPVerificationScreen)
              console.log('⚠️ بيانات غير مكتملة في params، محاولة قراءة من التخزين...');
              try {
                const savedUserData = await TempStorageService.getItem('userData');
                const savedToken = await TempStorageService.getItem('accessToken');
                const savedIsLoggedIn = await TempStorageService.getItem('isLoggedIn');

                if (savedUserData && savedToken && savedIsLoggedIn === 'true') {
                  const userData = JSON.parse(savedUserData);
                  console.log('✅ تم استرجاع البيانات من التخزين - userId:', userData.id);

                  if (isMountedRef.current) {
                    setAppState({
                      isLoading: false,
                      isLoggedIn: true,
                      currentScreen: 'main',
                      user: userData,
                      isNewUser: true,
                      otpParams: null,
                    });
                  }
                  return;
                }
              } catch (readError) {
                console.error('❌ خطأ في قراءة البيانات من التخزين:', readError);
              }

              console.log('❌ فشل استرجاع البيانات، الانتقال لتسجيل الدخول');
              handleNavigateToLogin();
            }
          } catch (error) {
            console.error('❌ خطأ في معالجة نجاح التسجيل:', error);
            handleNavigateToLogin();
          }
        };

        return (
          <OTPSuccessScreen
            navigation={{
              setOptions: () => { },
              navigate: (screen, params) => {
                console.log('🔄 Navigation from OTPSuccess:', screen, params);
                console.log('🔍 operationType:', operationType, 'registrationData exists:', !!registrationData);

                // ✅ عملية التسجيل تعتمد فقط على operationType
                if (operationType === 'register') {
                  console.log('✅ عملية تسجيل - استدعاء handleRegistrationSuccess');
                  handleRegistrationSuccess();
                } else {
                  console.log('⚠️ عملية أخرى - الانتقال للدخول');
                  handleNavigateToLogin();
                }
              },
              reset: (options) => {
                console.log('🔄 Reset navigation from OTPSuccess:', options);
                console.log('🔍 operationType:', operationType, 'registrationData exists:', !!registrationData);

                // ✅ فحص operationType فقط - ليس registrationData
                if (operationType === 'register') {
                  console.log('✅ عملية تسجيل - استدعاء handleRegistrationSuccess');
                  handleRegistrationSuccess();
                } else {
                  console.log('⚠️ عملية أخرى - الانتقال للدخول');
                  handleNavigateToLogin();
                }
              },
            }}
            route={{
              params: {
                ...successParams,
                email: appState.otpParams?.params?.email,
                operationType: operationType,
              }
            }}
          />
        );

      default:
        return <SplashScreen onComplete={handleSplashComplete} />;
    }
  };

  return (
    <SafeAreaProvider>
      <ErrorBoundary
        onReset={() => {
          // إعادة تعيين حالة التطبيق عند الخطأ
          setAppState({
            isLoading: false,
            isLoggedIn: false,
            currentScreen: 'login',
            user: null,
          });
        }}
      >
        <ThemeProvider>
          <TradingModeProvider>
            <PortfolioProvider>
              <View style={{ flex: 1, backgroundColor: Theme.colors.background }}>
                <StatusBar
                  barStyle="light-content"
                  backgroundColor={Theme.colors.background}
                  translucent={false}
                />
                <NavigationContainer
                  ref={navigationRef}
                  onReady={() => {
                    // ✅ تمرير مرجع التنقل لخدمة الإشعارات
                    setNavigationRef(navigationRef.current);
                    console.log('✅ Navigation ready - تم تمرير مرجع التنقل للإشعارات');
                  }}
                >
                  {renderCurrentScreen()}
                </NavigationContainer>

                {/* ✅ شريط حالة الاتصال - معطل مؤقتاً لإصلاح مشكلة التهيئة */}
                {/* <ConnectionStatusBar /> */}

                <ToastContainer />
                <CustomAlert />
              </View>
            </PortfolioProvider>
          </TradingModeProvider>
        </ThemeProvider>
      </ErrorBoundary>
    </SafeAreaProvider>
  );
}
