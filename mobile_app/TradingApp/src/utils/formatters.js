/**
 * Formatting Utilities
 * دوال موحدة لتنسيق الأرقام والعملات والتواريخ
 */

/**
 * تنسيق الأرقام بشكل موحد
 * @param {number} value - القيمة المراد تنسيقها
 * @param {number} decimals - عدد الخانات العشرية (افتراضي: 2)
 * @returns {string} - القيمة المنسقة
 */
export const formatNumber = (value, decimals = 2) => {
    if (value === null || value === undefined || isNaN(value)) {
        return '0.00';
    }

    const num = parseFloat(value);

    // للأرقام الكبيرة جداً
    if (Math.abs(num) >= 1000000) {
        return `${(num / 1000000).toFixed(decimals)}M`;
    }

    // للأرقام الكبيرة
    if (Math.abs(num) >= 1000) {
        return `${(num / 1000).toFixed(decimals)}K`;
    }

    // للأرقام العادية
    return num.toFixed(decimals);
};

/**
 * تنسيق المبلغ بالدولار
 * @param {number} value - المبلغ
 * @param {boolean} showSign - إظهار علامة + للأرقام الموجبة
 * @returns {string} - المبلغ المنسق
 */
export const formatCurrency = (value, showSign = false) => {
    if (value === null || value === undefined || isNaN(value)) {
        return '$0.00';
    }

    const num = parseFloat(value);
    const formatted = formatNumber(Math.abs(num), 2);
    const sign = num >= 0 ? (showSign ? '+' : '') : '-';

    return `${sign}$${formatted}`;
};

/**
 * تنسيق النسبة المئوية
 * @param {number} value - النسبة
 * @param {boolean} showSign - إظهار علامة + للأرقام الموجبة
 * @returns {string} - النسبة المنسقة
 */
export const formatPercentage = (value, showSign = false) => {
    if (value === null || value === undefined || isNaN(value)) {
        return '0.00%';
    }

    const num = parseFloat(value);
    const sign = num >= 0 ? (showSign ? '+' : '') : '';

    return `${sign}${Math.abs(num).toFixed(2)}%`;
};

/**
 * تنسيق التاريخ والوقت
 * @param {string|Date} date - التاريخ
 * @param {string} format - التنسيق (short, medium, long)
 * @returns {string} - التاريخ المنسق
 */
export const formatDate = (date, format = 'medium') => {
    if (!date) {return '-';}

    const d = new Date(date);

    if (isNaN(d.getTime())) {return '-';}

    const options = {
        short: {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
        },
        medium: {
            year: 'numeric',
            month: 'short',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        },
        long: {
            year: 'numeric',
            month: 'long',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
        },
    };

    return d.toLocaleString('ar-SA', options[format] || options.medium);
};

/**
 * تنسيق الوقت النسبي (منذ X)
 * @param {string|Date} date - التاريخ
 * @returns {string} - الوقت النسبي
 */
export const formatTimeAgo = (date) => {
    if (!date) {return '-';}

    const d = new Date(date);
    if (isNaN(d.getTime())) {return '-';}

    const now = new Date();
    const diffMs = now - d;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffSec < 60) {return 'الآن';}
    if (diffMin < 60) {return `منذ ${diffMin} دقيقة`;}
    if (diffHour < 24) {return `منذ ${diffHour} ساعة`;}
    if (diffDay < 7) {return `منذ ${diffDay} يوم`;}
    if (diffDay < 30) {return `منذ ${Math.floor(diffDay / 7)} أسبوع`;}
    if (diffDay < 365) {return `منذ ${Math.floor(diffDay / 30)} شهر`;}
    return `منذ ${Math.floor(diffDay / 365)} سنة`;
};

/**
 * تنسيق رمز العملة
 * @param {string} symbol - رمز العملة
 * @returns {string} - الرمز المنسق
 */
export const formatCoinSymbol = (symbol) => {
    if (!symbol) {return '';}
    return symbol.toUpperCase().replace('USDT', '');
};

/**
 * تنسيق الكمية (Quantity)
 * @param {number} quantity - الكمية
 * @param {number} decimals - عدد الخانات العشرية
 * @returns {string} - الكمية المنسقة
 */
export const formatQuantity = (quantity, decimals = 8) => {
    if (quantity === null || quantity === undefined || isNaN(quantity)) {
        return '0';
    }

    const num = parseFloat(quantity);

    // إزالة الأصفار غير الضرورية
    return num.toFixed(decimals).replace(/\.?0+$/, '');
};

/**
 * الحصول على لون حسب القيمة (ربح/خسارة)
 * @param {number} value - القيمة
 * @param {object} colors - ألوان theme
 * @returns {string} - اللون
 */
export const getValueColor = (value, colors) => {
    if (value > 0) {return colors.success;}
    if (value < 0) {return colors.error;}
    return colors.textSecondary;
};

/**
 * الحصول على أيقونة الاتجاه
 * @param {number} value - القيمة
 * @returns {string} - اسم الأيقونة
 */
export const getTrendIcon = (value) => {
    if (value > 0) {return 'trending-up';}
    if (value < 0) {return 'trending-down';}
    return 'minus';
};

/**
 * الحصول على سهم الاتجاه
 * @param {number} value - القيمة
 * @returns {string} - السهم
 */
export const getTrendArrow = (value) => {
    if (value > 0) {return '↑';}
    if (value < 0) {return '↓';}
    return '→';
};

export default {
    formatNumber,
    formatCurrency,
    formatPercentage,
    formatDate,
    formatTimeAgo,
    formatCoinSymbol,
    formatQuantity,
    getValueColor,
    getTrendIcon,
    getTrendArrow,
};
