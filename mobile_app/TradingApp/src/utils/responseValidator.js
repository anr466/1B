/**
 * Response Validator - التحقق من صحة responses من Backend
 * يمنع app crashes بسبب بيانات غير متوقعة
 */

import Logger from './Logger';

/**
 * التحقق من Portfolio Response
 */
export const validatePortfolioResponse = (data) => {
    if (!data || typeof data !== 'object') {
        Logger.error('Invalid portfolio response: not an object', data);
        return {
            valid: false,
            data: getDefaultPortfolio(),
            error: 'Invalid response format'
        };
    }

    // التحقق من الحقول الإلزامية
    const required = ['totalBalance', 'availableBalance'];
    const missing = required.filter(field => !(field in data));
    
    if (missing.length > 0) {
        Logger.warn('Portfolio response missing fields:', missing);
        return {
            valid: false,
            data: { ...getDefaultPortfolio(), ...data },
            error: `Missing fields: ${missing.join(', ')}`
        };
    }

    // التحقق من أنواع البيانات
    const numericFields = ['totalBalance', 'availableBalance', 'investedBalance'];
    for (const field of numericFields) {
        if (data[field] && typeof data[field] === 'string') {
            // تحويل string إلى number
            data[field] = parseFloat(data[field].replace(/,/g, '')) || 0;
        }
    }

    return {
        valid: true,
        data: { ...getDefaultPortfolio(), ...data }
    };
};

/**
 * التحقق من Trades Response
 */
export const validateTradesResponse = (data) => {
    if (!Array.isArray(data)) {
        Logger.error('Invalid trades response: not an array', data);
        return {
            valid: false,
            data: [],
            error: 'Expected array of trades'
        };
    }

    // التحقق من كل trade
    const validTrades = data.filter(trade => {
        if (!trade || typeof trade !== 'object') return false;
        
        const required = ['id', 'symbol', 'entryPrice', 'quantity'];
        const hasRequired = required.every(field => field in trade);
        
        if (!hasRequired) {
            Logger.warn('Trade missing required fields:', trade);
        }
        
        return hasRequired;
    });

    return {
        valid: true,
        data: validTrades,
        filtered: data.length - validTrades.length
    };
};

/**
 * التحقق من System Status Response
 */
export const validateSystemStatusResponse = (data) => {
    if (!data || typeof data !== 'object') {
        Logger.error('Invalid system status response', data);
        return {
            valid: false,
            data: getDefaultSystemStatus(),
            error: 'Invalid response format'
        };
    }

    // التحقق من الحقول الأساسية
    const defaults = getDefaultSystemStatus();
    const validated = { ...defaults, ...data };

    // التأكد من أن trading_state قيمة صحيحة
    const validStates = ['STOPPED', 'STARTING', 'RUNNING', 'STOPPING', 'ERROR'];
    if (!validStates.includes(validated.trading_state)) {
        Logger.warn('Invalid trading_state:', validated.trading_state);
        validated.trading_state = 'STOPPED';
    }

    return {
        valid: true,
        data: validated
    };
};

/**
 * التحقق من Settings Response
 */
export const validateSettingsResponse = (data) => {
    if (!data || typeof data !== 'object') {
        Logger.error('Invalid settings response', data);
        return {
            valid: false,
            data: getDefaultSettings(),
            error: 'Invalid response format'
        };
    }

    return {
        valid: true,
        data: { ...getDefaultSettings(), ...data }
    };
};

/**
 * Generic Response Validator
 */
export const validateResponse = (data, schema) => {
    if (!data || typeof data !== 'object') {
        return {
            valid: false,
            data: schema.default || {},
            error: 'Invalid response format'
        };
    }

    // التحقق من الحقول المطلوبة
    if (schema.required) {
        const missing = schema.required.filter(field => !(field in data));
        if (missing.length > 0) {
            Logger.warn('Response missing required fields:', missing);
            return {
                valid: false,
                data: { ...(schema.default || {}), ...data },
                error: `Missing: ${missing.join(', ')}`
            };
        }
    }

    // التحقق من الأنواع
    if (schema.types) {
        for (const [field, expectedType] of Object.entries(schema.types)) {
            if (field in data && typeof data[field] !== expectedType) {
                Logger.warn(`Field ${field} has wrong type:`, typeof data[field], 'expected:', expectedType);
                
                // محاولة التحويل
                if (expectedType === 'number' && typeof data[field] === 'string') {
                    data[field] = parseFloat(data[field]) || 0;
                } else if (expectedType === 'boolean') {
                    data[field] = Boolean(data[field]);
                }
            }
        }
    }

    return {
        valid: true,
        data: { ...(schema.default || {}), ...data }
    };
};

// ============================================================================
// Default Values
// ============================================================================

const getDefaultPortfolio = () => ({
    totalBalance: '0.00',
    availableBalance: '0.00',
    investedBalance: '0.00',
    totalProfitLoss: '+0.00',
    totalProfitLossPercentage: '+0.00',
    dailyPnL: '+0.00',
    dailyPnLPercentage: '+0.00',
    currency: 'USD',
    hasKeys: false,
    error: false
});

const getDefaultSystemStatus = () => ({
    trading_state: 'STOPPED',
    is_running: false,
    message: 'النظام متوقف',
    uptime: 0,
    session_id: null,
    mode: 'PAPER'
});

const getDefaultSettings = () => ({
    trading_enabled: false,
    trading_mode: 'demo',
    max_positions: 3,
    risk_per_trade: 2.0,
    daily_loss_limit: 5.0
});

export default {
    validatePortfolioResponse,
    validateTradesResponse,
    validateSystemStatusResponse,
    validateSettingsResponse,
    validateResponse
};
