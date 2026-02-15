/**
 * User Utilities - دوال مساعدة للمستخدم
 * توحيد التعامل مع بيانات المستخدم وتجنب التناقضات
 */

/**
 * الحصول على نوع المستخدم بشكل موحد
 * يدعم كلا من user_type و userType للتوافق
 */
export const getUserType = (user) => {
  if (!user) return 'user';
  return user.user_type || user.userType || 'user';
};

/**
 * التحقق إذا كان المستخدم أدمن
 * استخدام دالة موحدة لتجنب التناقضات
 */
export const isAdmin = (user) => {
  return getUserType(user) === 'admin';
};

/**
 * الحصول على الوضع الآمن للتداول
 * الأدمن دائماً في وضع demo للسلامة
 */
export const getSafeTradingMode = (mode, isAdminUser) => {
  if (isAdminUser) return 'demo'; // الأدمن دائماً demo للسلامة
  return mode || 'real';
};

/**
 * التحقق من القيم الفارغة بشكل موحد
 */
export const isEmpty = (value) => {
  return value === null || value === undefined;
};

/**
 * التحقق من القيم الفارغة أو غير صالحة
 */
export const isInvalid = (value) => {
  return isEmpty(value) || value === '' || Number.isNaN(value);
};

/**
 * الحصول على معرف المستخدم بشكل آمن
 */
export const getUserId = (user) => {
  return user?.id || user?.userId || null;
};

/**
 * تنسيق اسم المستخدم بشكل موحد
 */
export const getUserName = (user) => {
  return user?.fullName || user?.full_name || user?.name || 'مستخدم';
};

/**
 * التحقق من صلاحيات المستخدم
 */
export const hasPermission = (user, permission) => {
  const userType = getUserType(user);
  
  switch (permission) {
    case 'admin':
      return userType === 'admin';
    case 'trading':
      return userType === 'user' || userType === 'admin';
    case 'demo_only':
      return userType === 'admin';
    case 'real_trading':
      return userType === 'user';
    default:
      return false;
  }
};
