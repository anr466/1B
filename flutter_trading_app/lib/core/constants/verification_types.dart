/// Verification flow types and metadata
class VerificationFlowType {
  static const String registration = 'registration';
  static const String forgotPassword = 'forgot_password';
  static const String changePassword = 'change_password';
  static const String changeEmail = 'change_email';
  static const String changeBiometric = 'change_biometric';
  static const String changePhone = 'change_phone';
  static const String loginOtp = 'login_otp';
}

/// Verification method options
class VerificationMethod {
  static const String email = 'email';
  static const String sms = 'sms';
  static const String biometric = 'biometric';
}

/// Flow metadata for unified OTP verification
class VerificationFlowMetadata {
  final String type;
  final String title;
  final List<String> steps;
  final String? subtitle;
  final String defaultMethod;

  const VerificationFlowMetadata({
    required this.type,
    required this.title,
    required this.steps,
    this.subtitle,
    this.defaultMethod = VerificationMethod.email,
  });

  static const registration = VerificationFlowMetadata(
    type: VerificationFlowType.registration,
    title: 'إنشاء حساب جديد',
    steps: ['البيانات الأساسية', 'رمز التحقق'],
  );

  static const forgotPassword = VerificationFlowMetadata(
    type: VerificationFlowType.forgotPassword,
    title: 'استعادة كلمة المرور',
    steps: ['إدخال البريد', 'رمز التحقق', 'كلمة المرور الجديدة'],
  );

  static const changePassword = VerificationFlowMetadata(
    type: VerificationFlowType.changePassword,
    title: 'تغيير كلمة المرور',
    steps: ['التحقق من الهوية', 'رمز التحقق', 'كلمة المرور الجديدة'],
  );

  static const changeEmail = VerificationFlowMetadata(
    type: VerificationFlowType.changeEmail,
    title: 'تغيير البريد الإلكتروني',
    steps: ['إدخال البريد الجديد', 'رمز التحقق', 'تحديث البريد'],
  );

  static const changeBiometric = VerificationFlowMetadata(
    type: VerificationFlowType.changeBiometric,
    title: 'تفعيل البصمة',
    steps: ['التحقق بالبصمة', 'رمز التحقق', 'إتمام التفعيل'],
  );

  static const changePhone = VerificationFlowMetadata(
    type: VerificationFlowType.changePhone,
    title: 'تغيير رقم الجوال',
    steps: ['إدخال الرقم الجديد', 'رمز التحقق', 'تأكيد التحديث'],
  );

  Map<String, dynamic> toExtra({Map<String, dynamic>? additionalData}) {
    return {
      'type': type,
      'flow_title': title,
      'flow_steps': steps,
      'verification_method': defaultMethod,
      if (subtitle != null) 'subtitle': subtitle,
      ...?additionalData,
    };
  }
}
