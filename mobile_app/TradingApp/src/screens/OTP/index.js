/**
 * فهرس شاشات OTP الموحدة
 * يصدر جميع شاشات ومكونات OTP للاستخدام السهل
 */

// الشاشات الرئيسية
export { default as OTPSentScreen } from './OTPSentScreen';
export { default as OTPVerificationScreen } from './OTPVerificationScreen';
export { default as OTPSuccessScreen } from './OTPSuccessScreen';

// المكونات المشتركة
export { default as OTPInput } from './components/OTPInput';
export { default as CountdownTimer } from './components/CountdownTimer';
export { default as ResendButton } from './components/ResendButton';
export {
  default as StatusMessage,
  SuccessMessage,
  ErrorMessage,
  WarningMessage,
  InfoMessage,
  MESSAGE_TYPES,
} from './components/StatusMessage';

// الخدمات
export { default as OTPService, OTP_OPERATION_TYPES } from '../../services/OTPService';
