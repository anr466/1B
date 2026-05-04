/// UX Messages — رسائل موحّدة وواضحة للمستخدم
class UxMessages {
  UxMessages._();

  static const String success = 'تمت العملية بنجاح';
  static const String error = 'تعذر إتمام العملية، حاول مرة أخرى';

  static const String otpSent = 'تم إرسال رمز التحقق بنجاح';

  static const String networkError = 'فشل الاتصال بالخادم، تحقق من الإنترنت';
  static const String sessionExpired = 'انتهت الجلسة، يرجى تسجيل الدخول مجدداً';
  static const String unauthorized = 'غير مصرح، يرجى تسجيل الدخول';

  static const String tradingToggleError = 'تعذر تحديث حالة التداول';
  static const String modeSwitchError = 'تعذر التبديل بين الأوضاع';

  static const String biometricFailed = 'فشل التحقق من البصمة';
  static const String biometricNotAvailable = 'المصادقة بالبصمة غير متاحة';

  static const String apiKeysSaveError = 'تعذر حفظ مفاتيح API';
  static const String apiKeysValidateError = 'فشل التحقق من المفاتيح';
}
