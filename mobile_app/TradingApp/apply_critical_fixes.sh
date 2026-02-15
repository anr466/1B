#!/bin/bash

# 🔧 سكريبت تطبيق الإصلاحات الحرجة - Trading AI Bot
# يُطبّق الإصلاحات الثلاثة الحرجة بشكل تلقائي

set -e  # إيقاف عند أي خطأ

echo "🚀 بدء تطبيق الإصلاحات الحرجة..."
echo "========================================"

# الانتقال لمجلد التطبيق
cd "$(dirname "$0")"
APP_DIR=$(pwd)

echo ""
echo "📍 المسار الحالي: $APP_DIR"
echo ""

# ==================== الإصلاح 1: تثبيت SecureStorage ====================
echo "🔧 الإصلاح 1/3: تثبيت react-native-encrypted-storage"
echo "--------------------------------------------------------"

if grep -q '"react-native-encrypted-storage"' package.json; then
    echo "✅ المكتبة موجودة في package.json"
    
    if [ -d "node_modules/react-native-encrypted-storage" ]; then
        echo "⚠️  المكتبة مُثبّتة مسبقاً، سيتم إعادة التثبيت..."
        npm uninstall react-native-encrypted-storage
    fi
    
    echo "📦 تثبيت react-native-encrypted-storage..."
    npm install react-native-encrypted-storage
    
    # iOS Pod install
    if [ -d "ios" ]; then
        echo "🍎 تثبيت Pods لـ iOS..."
        cd ios
        pod install
        cd ..
    fi
    
    echo "✅ تم تثبيت SecureStorage بنجاح"
else
    echo "❌ المكتبة غير موجودة في package.json!"
    exit 1
fi

echo ""
echo "🧹 تنظيف الـ cache..."
npm run clean || echo "⚠️  تحذير: فشل تنظيف الـ cache"

echo ""
echo "✅ الإصلاح 1 مكتمل!"
echo ""

# ==================== الإصلاح 2: توحيد Navigation ====================
echo "🔧 الإصلاح 2/3: توحيد Navigation"
echo "--------------------------------------------------------"

# نسخ احتياطي لـ App.js
cp App.js App.js.backup
echo "💾 تم عمل نسخة احتياطية: App.js.backup"

# تحديث App.js
echo "📝 تحديث App.js..."
sed -i.tmp "s|import AppNavigator from './src/navigation/AppNavigator';|import EnhancedAppNavigator from './src/navigation/EnhancedAppNavigator';|g" App.js
sed -i.tmp 's/<AppNavigator/<EnhancedAppNavigator/g' App.js
sed -i.tmp 's|/AppNavigator>|/EnhancedAppNavigator>|g' App.js
rm -f App.js.tmp

echo "✅ تم تحديث App.js"

# إصلاح OTPNavigator
if [ -f "src/navigation/OTPNavigator.js" ]; then
    echo "📝 إصلاح OTPNavigator.js..."
    cp src/navigation/OTPNavigator.js src/navigation/OTPNavigator.js.backup
    
    sed -i.tmp "s|import { useTheme } from '../contexts/ThemeContext';|import { Theme } from '../theme/colors';|g" src/navigation/OTPNavigator.js
    sed -i.tmp 's|const { colors } = useTheme();|const colors = Theme.colors;|g' src/navigation/OTPNavigator.js
    rm -f src/navigation/OTPNavigator.js.tmp
    
    echo "✅ تم إصلاح OTPNavigator.js"
fi

# حذف AppNavigator القديم (بعد التأكد)
if [ -f "src/navigation/AppNavigator.js" ]; then
    echo "🗑️  نقل AppNavigator.js القديم للأرشيف..."
    mkdir -p archive/old_navigation
    mv src/navigation/AppNavigator.js archive/old_navigation/
    echo "✅ تم نقل AppNavigator القديم"
fi

echo ""
echo "✅ الإصلاح 2 مكتمل!"
echo ""

# ==================== الإصلاح 3: ربط OTP Flow ====================
echo "🔧 الإصلاح 3/3: ربط OTP Flow"
echo "--------------------------------------------------------"

echo "ℹ️  هذا الإصلاح يتطلب تعديلات يدوية في RegisterScreen.js"
echo ""
echo "يرجى إضافة الكود التالي في RegisterScreen.js بعد نجاح التسجيل:"
echo ""
echo "---------- الكود المطلوب ----------"
cat << 'EOF'

// في handleRegister() بعد const response = await DatabaseAPI.post(...)
if (response.success) {
  // إرسال OTP
  const otpResult = await OTPService.sendOTP(
    userData.email, 
    'registration'
  );
  
  if (otpResult.success) {
    // الانتقال لشاشة التحقق
    props.onNavigateToEmailVerification({
      email: userData.email,
      purpose: 'registration',
      userData: response.user
    });
  } else {
    Alert.alert('خطأ', 'فشل إرسال رمز التحقق');
  }
}
EOF
echo "------------------------------------"
echo ""

echo "⚠️  الإصلاح 3 يحتاج تطبيق يدوي"
echo ""

# ==================== النهاية ====================
echo ""
echo "========================================" 
echo "✅ تم تطبيق الإصلاحات بنجاح!"
echo "========================================" 
echo ""
echo "📋 الخطوات التالية:"
echo "1. راجع التغييرات في App.js"
echo "2. طبّق التعديل اليدوي في RegisterScreen.js"
echo "3. أعد بناء التطبيق:"
echo "   npm run android"
echo ""
echo "💾 النسخ الاحتياطية:"
echo "   - App.js.backup"
echo "   - src/navigation/OTPNavigator.js.backup"
echo "   - archive/old_navigation/AppNavigator.js"
echo ""
echo "🎉 انتهى!"
