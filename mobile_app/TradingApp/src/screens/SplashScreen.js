/**
 * 🚀 شاشة البداية المتحركة الذكية - Smart Animated Splash Screen
 * ✅ تأثيرات متحركة احترافية
 * ✅ جزيئات متطايرة (Particles)
 * ✅ موجات متحركة (Waves)
 * ✅ دوائر نابضة (Pulsing Rings)
 * ✅ شعار متحرك مع توهج
 */

import React, { useEffect, useState, useRef } from 'react';
import { View, Text, StyleSheet, Animated, Dimensions, StatusBar, Easing } from 'react-native';
import Svg, { Path, Circle, Rect, Defs, LinearGradient as SvgGradient, Stop, Text as SvgText, G } from 'react-native-svg';
import LinearGradient from 'react-native-linear-gradient';
import ToastService from '../services/ToastService';
import GlobalHeader from '../components/GlobalHeader';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useBackHandler } from '../utils/BackHandlerUtil';
import { theme } from '../theme/theme';

// استخدام ألوان الهوية البصرية من theme الموحد
const BRAND_COLORS = {
  primary: theme.colors.primary,
  secondary: theme.colors.accent,
  success: theme.colors.success,
  gold: theme.colors.warning,
  background: theme.colors.background,
  surface: theme.colors.surface,
};

const { width, height } = Dimensions.get('window');

// ==================== مكون الجزيئات المتطايرة ====================
const AnimatedParticle = ({ delay, startX, startY, size, color }) => {
  const translateY = useRef(new Animated.Value(0)).current;
  const translateX = useRef(new Animated.Value(0)).current;
  const opacity = useRef(new Animated.Value(0)).current;
  const scale = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const animate = () => {
      // إعادة تعيين
      translateY.setValue(0);
      translateX.setValue(0);
      opacity.setValue(0);
      scale.setValue(0);

      Animated.sequence([
        Animated.delay(delay),
        Animated.parallel([
          // حركة للأعلى
          Animated.timing(translateY, {
            toValue: -height * 0.4,
            duration: 3000,
            easing: Easing.out(Easing.quad),
            useNativeDriver: true,
          }),
          // حركة جانبية عشوائية
          Animated.timing(translateX, {
            toValue: (Math.random() - 0.5) * 100,
            duration: 3000,
            useNativeDriver: true,
          }),
          // الظهور والاختفاء
          Animated.sequence([
            Animated.timing(opacity, {
              toValue: 0.8,
              duration: 500,
              useNativeDriver: true,
            }),
            Animated.delay(1500),
            Animated.timing(opacity, {
              toValue: 0,
              duration: 1000,
              useNativeDriver: true,
            }),
          ]),
          // التكبير والتصغير
          Animated.sequence([
            Animated.spring(scale, {
              toValue: 1,
              tension: 50,
              friction: 5,
              useNativeDriver: true,
            }),
            Animated.timing(scale, {
              toValue: 0.3,
              duration: 2000,
              useNativeDriver: true,
            }),
          ]),
        ]),
      ]).start(() => animate());
    };

    animate();
  }, []);

  return (
    <Animated.View
      style={[
        styles.particle,
        {
          left: startX,
          top: startY,
          width: size,
          height: size,
          borderRadius: size / 2,
          backgroundColor: color,
          opacity,
          transform: [{ translateY }, { translateX }, { scale }],
        },
      ]}
    />
  );
};

// ==================== مكون الدوائر النابضة ====================
const PulsingRing = ({ size, delay, color }) => {
  const scale = useRef(new Animated.Value(0.8)).current;
  const opacity = useRef(new Animated.Value(0.6)).current;

  useEffect(() => {
    const animate = () => {
      scale.setValue(0.8);
      opacity.setValue(0.6);

      Animated.sequence([
        Animated.delay(delay),
        Animated.parallel([
          Animated.timing(scale, {
            toValue: 1.5,
            duration: 2000,
            easing: Easing.out(Easing.quad),
            useNativeDriver: true,
          }),
          Animated.timing(opacity, {
            toValue: 0,
            duration: 2000,
            useNativeDriver: true,
          }),
        ]),
      ]).start(() => animate());
    };

    animate();
  }, []);

  return (
    <Animated.View
      style={[
        styles.pulsingRing,
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          borderColor: color,
          opacity,
          transform: [{ scale }],
        },
      ]}
    />
  );
};

const SplashScreen = ({ onComplete }) => {
  // الحركات الأساسية
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.5)).current;
  const progressAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;
  const glowAnim = useRef(new Animated.Value(0)).current;
  const logoSlideAnim = useRef(new Animated.Value(-50)).current;
  const textSlideAnim = useRef(new Animated.Value(50)).current;
  const featureOpacity = useRef(new Animated.Value(0)).current;
  const featureScale = useRef(new Animated.Value(0.8)).current;

  const [loadingStep, setLoadingStep] = useState(0);
  const [currentFeature, setCurrentFeature] = useState(0);
  const [showParticles, setShowParticles] = useState(true);

  // خطوات التحميل الذكية
  const loadingSteps = [
    '🔄 جاري التهيئة...',
    '🔐 فحص الأمان...',
    '📡 الاتصال بالخادم...',
    '✅ جاهز!',
  ];

  // العبارات المتحركة الاحترافية
  const features = [
    '🚀 تحليل ذكي للسوق',
    '📊 استراتيجيات متقدمة',
    '🛡️ تداول آمن وموثوق',
    '💰 إدارة ذكية للمخاطر',
    '⚡ تنفيذ فوري للصفقات',
    '🎯 نتائج مثبتة',
  ];

  // بيانات الجزيئات
  const particles = Array.from({ length: 15 }, (_, i) => ({
    id: i,
    delay: Math.random() * 2000,
    startX: Math.random() * width,
    startY: height * 0.6 + Math.random() * height * 0.3,
    size: 4 + Math.random() * 8,
    color: [BRAND_COLORS.primary, BRAND_COLORS.secondary, BRAND_COLORS.success, BRAND_COLORS.gold][Math.floor(Math.random() * 4)],
  }));

  // منع الرجوع من هذه الشاشة
  useBackHandler(() => {
    // لا نفعل شيء - منع الرجوع فقط
  });

  useEffect(() => {
    // ==================== تأثيرات الحركة المتقدمة ====================

    // 1. تأثير التوهج المتكرر
    const glowLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(glowAnim, {
          toValue: 1,
          duration: 1500,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(glowAnim, {
          toValue: 0,
          duration: 1500,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ])
    );

    // 2. تأثير النبض للشعار
    const pulseLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.08,
          duration: 1200,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1200,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ])
    );

    // 3. تأثير الدوران البطيء (للخلفية)
    const rotateLoop = Animated.loop(
      Animated.timing(rotateAnim, {
        toValue: 1,
        duration: 20000,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    );

    // 4. ظهور الشعار مع انزلاق من الأعلى
    const logoEntrance = Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 600,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.spring(scaleAnim, {
        toValue: 1,
        tension: 50,
        friction: 7,
        useNativeDriver: true,
      }),
      Animated.timing(logoSlideAnim, {
        toValue: 0,
        duration: 800,
        easing: Easing.out(Easing.back(1.5)),
        useNativeDriver: true,
      }),
      Animated.timing(textSlideAnim, {
        toValue: 0,
        duration: 800,
        delay: 200,
        easing: Easing.out(Easing.back(1.5)),
        useNativeDriver: true,
      }),
    ]);

    // بدء جميع التأثيرات
    logoEntrance.start();
    glowLoop.start();
    pulseLoop.start();
    rotateLoop.start();

    // 5. تقدم شريط التحميل مع تسارع
    Animated.timing(progressAnim, {
      toValue: 1,
      duration: 2500,
      easing: Easing.bezier(0.25, 0.1, 0.25, 1),
      useNativeDriver: false,
    }).start();

    // 6. تغيير خطوات التحميل بشكل متزامن
    const stepInterval = setInterval(() => {
      setLoadingStep(prev => {
        if (prev < loadingSteps.length - 1) {
          return prev + 1;
        }
        return prev;
      });
    }, 600);

    // 7. تأثيرات العبارات المتحركة
    const featureTimer = setTimeout(() => {
      const animateFeature = () => {
        Animated.sequence([
          // ظهور مع تأثير bounce
          Animated.parallel([
            Animated.timing(featureOpacity, {
              toValue: 1,
              duration: 300,
              useNativeDriver: true,
            }),
            Animated.spring(featureScale, {
              toValue: 1,
              tension: 80,
              friction: 6,
              useNativeDriver: true,
            }),
          ]),
          // انتظار
          Animated.delay(800),
          // اختفاء سلس
          Animated.parallel([
            Animated.timing(featureOpacity, {
              toValue: 0,
              duration: 250,
              useNativeDriver: true,
            }),
            Animated.timing(featureScale, {
              toValue: 0.6,
              duration: 250,
              useNativeDriver: true,
            }),
          ]),
        ]).start(() => {
          setCurrentFeature(prev => (prev + 1) % features.length);
          animateFeature();
        });
      };

      animateFeature();
    }, 800);

    // 8. الانتقال للشاشة التالية - ✅ تقليل التوقيت لتحسين تجربة المستخدم
    const timer = setTimeout(() => {
      // تأثير الخروج
      Animated.parallel([
        Animated.timing(fadeAnim, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true,
        }),
        Animated.timing(scaleAnim, {
          toValue: 1.1,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start(() => {
        // ✅ الانتقال للشاشة التالية
        if (onComplete) {
          onComplete();
        }
      });
    }, 1800);

    return () => {
      clearInterval(stepInterval);
      clearTimeout(timer);
      clearTimeout(featureTimer);
      glowLoop.stop();
      pulseLoop.stop();
      rotateLoop.stop();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // حساب الدوران
  const spin = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" backgroundColor="#0a0a2e" translucent />

      {/* خلفية متدرجة احترافية */}
      <LinearGradient
        colors={['#0D0D12', '#1A1A2E', '#0F0F23', '#0D0D12']}
        style={StyleSheet.absoluteFill}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
      />

      {/* ==================== الجزيئات المتطايرة ==================== */}
      {showParticles && particles.map(particle => (
        <AnimatedParticle key={particle.id} {...particle} />
      ))}

      {/* ==================== الخلفية الدوارة ==================== */}
      <Animated.View
        style={[
          styles.rotatingBackground,
          { transform: [{ rotate: spin }] },
        ]}
      >
        <View style={styles.bgCircle1} />
        <View style={styles.bgCircle2} />
        <View style={styles.bgCircle3} />
      </Animated.View>

      {/* ==================== الدوائر النابضة ==================== */}
      <View style={styles.pulsingRingsContainer}>
        <PulsingRing size={200} delay={0} color={BRAND_COLORS.primary} />
        <PulsingRing size={200} delay={500} color={BRAND_COLORS.secondary} />
        <PulsingRing size={200} delay={1000} color={BRAND_COLORS.success} />
      </View>

      {/* ==================== المحتوى الرئيسي ==================== */}
      <View style={styles.content}>
        <Animated.View
          style={[
            styles.textContainer,
            {
              opacity: fadeAnim,
              transform: [
                { scale: scaleAnim },
                { scale: pulseAnim },
                { translateY: logoSlideAnim },
              ],
            },
          ]}
        >
          {/* تأثير التوهج خلف الشعار */}
          <Animated.View
            style={[
              styles.glowEffect,
              {
                opacity: glowAnim.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0.3, 0.8],
                }),
                transform: [
                  {
                    scale: glowAnim.interpolate({
                      inputRange: [0, 1],
                      outputRange: [1, 1.3],
                    }),
                  },
                ],
              },
            ]}
          />

          {/* 🎨 الشعار المتحرك */}
          <View style={styles.logoWrapper}>
            <Svg width={180} height={180} viewBox="0 0 200 200" fill="none">
              <Defs>
                <SvgGradient id="splashLogoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <Stop offset="0%" stopColor={BRAND_COLORS.primary} />
                  <Stop offset="50%" stopColor="#A78BFA" />
                  <Stop offset="100%" stopColor={BRAND_COLORS.secondary} />
                </SvgGradient>
                <SvgGradient id="chartGrad" x1="0%" y1="100%" x2="100%" y2="0%">
                  <Stop offset="0%" stopColor={BRAND_COLORS.success} />
                  <Stop offset="100%" stopColor="#34D399" />
                </SvgGradient>
              </Defs>
              {/* الخلفية المستديرة مع ظل */}
              <Rect x="25" y="25" width="150" height="150" rx="35" fill="url(#splashLogoGrad)" />
              {/* الرقم 1 */}
              <SvgText x="70" y="135" fill="#FFFFFF" fontSize="85" fontWeight="bold" fontFamily="Arial">1</SvgText>
              {/* الحرف B */}
              <G>
                <SvgText x="100" y="135" fill="#FFFFFF" fontSize="85" fontWeight="bold" fontFamily="Arial">B</SvgText>
                {/* خط البيان الصاعد المتحرك */}
                <Path
                  d="M110 80 L122 68 L134 74 L146 58 L158 50"
                  fill="none"
                  stroke="url(#chartGrad)"
                  strokeWidth="5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <Circle cx="158" cy="50" r="7" fill={BRAND_COLORS.success} />
                {/* نقاط إضافية على الخط */}
                <Circle cx="122" cy="68" r="4" fill="#34D399" opacity="0.8" />
                <Circle cx="134" cy="74" r="4" fill="#34D399" opacity="0.6" />
                <Circle cx="146" cy="58" r="4" fill="#34D399" opacity="0.8" />
              </G>
            </Svg>
          </View>
        </Animated.View>

        {/* اسم التطبيق مع انزلاق */}
        <Animated.View
          style={{
            opacity: fadeAnim,
            transform: [{ translateY: textSlideAnim }],
          }}
        >
          <Text style={styles.appName}>1B Trading</Text>
          <Text style={styles.tagline}>تداول ذكي • أرباح مستمرة</Text>
        </Animated.View>
      </View>

      {/* قسم التحميل السفلي */}
      <View style={styles.loadingSection}>
        {/* نص التحميل الديناميكي أو العبارات المتحركة */}
        <Animated.View style={{ opacity: fadeAnim, minHeight: 24 }}>
          {loadingStep < loadingSteps.length ? (
            <Text style={styles.loadingText}>{loadingSteps[loadingStep]}</Text>
          ) : (
            // العبارات المتحركة بعد انتهاء خطوات التحميل
            <Animated.View
              style={[
                styles.featureDisplayContainer,
                {
                  opacity: featureOpacity,
                  transform: [{ scale: featureScale }],
                },
              ]}
            >
              <Text style={styles.featureDisplayText}>
                {features[currentFeature]}
              </Text>
            </Animated.View>
          )}
        </Animated.View>

        {/* شريط التقدم المحسّن */}
        <View style={styles.progressContainer}>
          <View style={styles.progressTrack}>
            <Animated.View
              style={[
                styles.progressBar,
                {
                  width: progressAnim.interpolate({
                    inputRange: [0, 1],
                    outputRange: ['0%', '100%'],
                  }),
                },
              ]}
            >
              <LinearGradient
                colors={[BRAND_COLORS.primary, BRAND_COLORS.secondary, BRAND_COLORS.success]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.progressGradient}
              />
            </Animated.View>
          </View>
        </View>

        {/* نسخة التطبيق */}
        <Text style={styles.version}>النسخة 1.0.0</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0D0D12',
    overflow: 'hidden',
  },

  // ==================== الجزيئات ====================
  particle: {
    position: 'absolute',
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 6,
    elevation: 5,
  },

  // ==================== الخلفية الدوارة ====================
  rotatingBackground: {
    position: 'absolute',
    width: width * 2,
    height: width * 2,
    left: -width / 2,
    top: height / 2 - width,
    justifyContent: 'center',
    alignItems: 'center',
  },
  bgCircle1: {
    position: 'absolute',
    width: width * 1.5,
    height: width * 1.5,
    borderRadius: width * 0.75,
    borderWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.08)',
  },
  bgCircle2: {
    position: 'absolute',
    width: width * 1.2,
    height: width * 1.2,
    borderRadius: width * 0.6,
    borderWidth: 1,
    borderColor: 'rgba(6, 182, 212, 0.06)',
  },
  bgCircle3: {
    position: 'absolute',
    width: width * 0.9,
    height: width * 0.9,
    borderRadius: width * 0.45,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.05)',
  },

  // ==================== الدوائر النابضة ====================
  pulsingRingsContainer: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    justifyContent: 'center',
    alignItems: 'center',
  },
  pulsingRing: {
    position: 'absolute',
    borderWidth: 2,
  },

  // ==================== تأثير التوهج ====================
  glowEffect: {
    position: 'absolute',
    width: 220,
    height: 220,
    borderRadius: 110,
    backgroundColor: 'rgba(139, 92, 246, 0.15)',
  },

  // ==================== الشعار ====================
  logoWrapper: {
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 15 },
    shadowOpacity: 0.5,
    shadowRadius: 30,
    elevation: 15,
  },

  // ==================== المحتوى ====================
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
    zIndex: 10,
  },
  textContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 30,
  },
  // قسم التحميل
  loadingSection: {
    paddingHorizontal: 32,
    paddingBottom: 60,
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#8B5CF6',
    marginBottom: 20,
    textAlign: 'center',
    letterSpacing: 0.5,
  },
  featureDisplayContainer: {
    marginBottom: 20,
    alignItems: 'center',
  },
  featureDisplayText: {
    fontSize: 18,
    fontWeight: '800',
    color: '#10B981',
    textAlign: 'center',
    letterSpacing: 1.5,
    textShadowColor: 'rgba(16, 185, 129, 0.5)',
    textShadowOffset: { width: 0, height: 3 },
    textShadowRadius: 6,
  },
  // شريط التقدم
  progressContainer: {
    width: '100%',
    marginBottom: 24,
  },
  progressTrack: {
    width: '100%',
    height: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: 3,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: 'rgba(139, 92, 246, 0.15)',
  },
  progressBar: {
    height: '100%',
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.6,
    shadowRadius: 8,
    elevation: 4,
  },
  progressGradient: {
    flex: 1,
    width: '100%',
    height: '100%',
  },
  version: {
    fontSize: 13,
    fontWeight: '500',
    color: 'rgba(255, 255, 255, 0.45)',
    letterSpacing: 0.5,
  },
  tagline: {
    fontSize: 17,
    fontWeight: '600',
    color: 'rgba(255, 255, 255, 0.75)',
    marginTop: 12,
    letterSpacing: 3,
    textAlign: 'center',
  },
  appName: {
    fontSize: 32,
    fontWeight: '900',
    color: '#FFFFFF',
    letterSpacing: 4,
    textAlign: 'center',
    textShadowColor: 'rgba(139, 92, 246, 0.6)',
    textShadowOffset: { width: 0, height: 4 },
    textShadowRadius: 15,
  },
});

export default SplashScreen;
