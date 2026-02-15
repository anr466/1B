module.exports = {
  root: true,
  extends: '@react-native',
  env: {
    jest: true,  // تفعيل بيئة Jest للاختبارات
  },
  rules: {
    'prettier/prettier': 0,
    'react-native/no-inline-styles': 0,
    'react-hooks/exhaustive-deps': 'warn',
    'no-shadow': 'warn',
    'no-catch-shadow': 'off',
  },
};
