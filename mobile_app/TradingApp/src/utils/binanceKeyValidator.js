/**
 * Binance Key Validator
 * يتحقق من صحة مفاتيح Binance API
 */

/**
 * التحقق من صيغة API Key
 * @param {string} apiKey - مفتاح API
 * @returns {boolean} true إذا كانت الصيغة صحيحة
 */
export const validateApiKeyFormat = (apiKey) => {
  if (!apiKey || typeof apiKey !== 'string') {
    return false;
  }

  // مفاتيح Binance عادة تكون 64 حرف أو أكثر
  // وتحتوي على أحرف وأرقام فقط
  const apiKeyRegex = /^[a-zA-Z0-9]{20,}$/;
  return apiKeyRegex.test(apiKey.trim());
};

/**
 * التحقق من صيغة Secret Key
 * @param {string} secretKey - مفتاح السر
 * @returns {boolean} true إذا كانت الصيغة صحيحة
 */
export const validateSecretKeyFormat = (secretKey) => {
  if (!secretKey || typeof secretKey !== 'string') {
    return false;
  }

  // مفاتيح السر عادة تكون 64 حرف أو أكثر
  // وتحتوي على أحرف وأرقام فقط
  const secretKeyRegex = /^[a-zA-Z0-9]{20,}$/;
  return secretKeyRegex.test(secretKey.trim());
};

/**
 * التحقق الشامل من المفاتيح
 * @param {string} apiKey - مفتاح API
 * @param {string} secretKey - مفتاح السر
 * @returns {Object} {valid: boolean, errors: string[]}
 */
export const validateBinanceKeys = (apiKey, secretKey) => {
  const errors = [];

  // التحقق من عدم ترك الحقول فارغة
  if (!apiKey || !apiKey.trim()) {
    errors.push('مفتاح API مطلوب');
  }

  if (!secretKey || !secretKey.trim()) {
    errors.push('مفتاح السر مطلوب');
  }

  // التحقق من الصيغة
  if (apiKey && !validateApiKeyFormat(apiKey)) {
    errors.push('صيغة مفتاح API غير صحيحة');
  }

  if (secretKey && !validateSecretKeyFormat(secretKey)) {
    errors.push('صيغة مفتاح السر غير صحيحة');
  }

  // التحقق من عدم تطابق المفاتيح
  if (apiKey && secretKey && apiKey === secretKey) {
    errors.push('مفتاح API ومفتاح السر لا يجب أن يكونا متطابقين');
  }

  return {
    valid: errors.length === 0,
    errors: errors,
  };
};

/**
 * إخفاء جزء من المفتاح للعرض الآمن
 * @param {string} key - المفتاح الكامل
 * @param {number} visibleChars - عدد الأحرف المرئية من النهاية
 * @returns {string} المفتاح المخفي
 */
export const maskKey = (key, visibleChars = 4) => {
  if (!key || key.length <= visibleChars) {
    return '****';
  }

  const hiddenLength = key.length - visibleChars;
  const hidden = '*'.repeat(hiddenLength);
  const visible = key.slice(-visibleChars);

  return `${hidden}${visible}`;
};

/**
 * الحصول على رسالة خطأ موحدة
 * @param {Object} validationResult - نتيجة التحقق
 * @returns {string} رسالة الخطأ الموحدة
 */
export const getValidationErrorMessage = (validationResult) => {
  if (validationResult.valid) {
    return 'المفاتيح صحيحة ✅';
  }

  if (validationResult.errors.length === 1) {
    return validationResult.errors[0];
  }

  return `${validationResult.errors.length} أخطاء:\n${validationResult.errors.join('\n')}`;
};

export default {
  validateApiKeyFormat,
  validateSecretKeyFormat,
  validateBinanceKeys,
  maskKey,
  getValidationErrorMessage,
};
