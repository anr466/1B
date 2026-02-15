"""
✅ Input Validation - نظام التحقق من صحة البيانات المدخلة
يوفر schemas و validators لضمان سلامة البيانات في جميع العمليات
"""

import logging
from typing import Any, Dict, Optional, List, Union, Tuple
from decimal import Decimal
import re

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """خطأ في التحقق من صحة البيانات"""
    def __init__(self, field: str, message: str, value: Any = None):
        self.field = field
        self.message = message
        self.value = value
        super().__init__(f"{field}: {message}")


class ValidationResult:
    """نتيجة التحقق من صحة البيانات"""
    
    def __init__(self, is_valid: bool = True, errors: List[ValidationError] = None):
        self.is_valid = is_valid
        self.errors = errors or []
    
    def add_error(self, field: str, message: str, value: Any = None):
        """إضافة خطأ"""
        self.errors.append(ValidationError(field, message, value))
        self.is_valid = False
    
    def to_dict(self) -> Dict:
        """تحويل النتيجة إلى قاموس"""
        return {
            'is_valid': self.is_valid,
            'errors': [
                {
                    'field': e.field,
                    'message': e.message,
                    'value': str(e.value) if e.value is not None else None
                }
                for e in self.errors
            ]
        }


class Validator:
    """فئة أساسية للتحقق من صحة البيانات"""
    
    @staticmethod
    def validate_string(
        value: Any,
        field_name: str = "field",
        min_length: int = 0,
        max_length: int = None,
        pattern: str = None,
        required: bool = True
    ) -> Tuple[bool, str]:
        """
        التحقق من صحة النص
        
        Args:
            value: القيمة المراد التحقق منها
            field_name: اسم الحقل
            min_length: الحد الأدنى للطول
            max_length: الحد الأقصى للطول
            pattern: نمط regex للتحقق
            required: هل الحقل مطلوب
            
        Returns:
            (is_valid, error_message)
        """
        if value is None:
            if required:
                return False, f"{field_name} مطلوب"
            return True, ""
        
        if not isinstance(value, str):
            return False, f"{field_name} يجب أن يكون نصاً"
        
        if len(value) < min_length:
            return False, f"{field_name} يجب أن يكون على الأقل {min_length} أحرف"
        
        if max_length and len(value) > max_length:
            return False, f"{field_name} يجب ألا يتجاوز {max_length} أحرف"
        
        if pattern:
            if not re.match(pattern, value):
                return False, f"{field_name} لا يطابق النمط المطلوب"
        
        return True, ""
    
    @staticmethod
    def validate_number(
        value: Any,
        field_name: str = "field",
        min_value: float = None,
        max_value: float = None,
        required: bool = True,
        allow_zero: bool = True
    ) -> Tuple[bool, str]:
        """
        التحقق من صحة الأرقام
        
        Args:
            value: القيمة المراد التحقق منها
            field_name: اسم الحقل
            min_value: الحد الأدنى
            max_value: الحد الأقصى
            required: هل الحقل مطلوب
            allow_zero: هل يسمح بالصفر
            
        Returns:
            (is_valid, error_message)
        """
        if value is None:
            if required:
                return False, f"{field_name} مطلوب"
            return True, ""
        
        try:
            num_value = float(value)
        except (ValueError, TypeError):
            return False, f"{field_name} يجب أن يكون رقماً"
        
        if not allow_zero and num_value == 0:
            return False, f"{field_name} لا يمكن أن يكون صفراً"
        
        if min_value is not None and num_value < min_value:
            return False, f"{field_name} يجب أن يكون على الأقل {min_value}"
        
        if max_value is not None and num_value > max_value:
            return False, f"{field_name} يجب ألا يتجاوز {max_value}"
        
        return True, ""
    
    @staticmethod
    def validate_email(value: Any, field_name: str = "email") -> Tuple[bool, str]:
        """التحقق من صحة البريد الإلكتروني"""
        is_valid, error = Validator.validate_string(
            value,
            field_name,
            min_length=5,
            max_length=255,
            pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
        if not is_valid:
            return False, error
        return True, ""
    
    @staticmethod
    def validate_symbol(value: Any, field_name: str = "symbol") -> Tuple[bool, str]:
        """التحقق من صحة رمز العملة"""
        is_valid, error = Validator.validate_string(
            value,
            field_name,
            min_length=2,
            max_length=20,
            pattern=r'^[A-Z0-9]+$'
        )
        if not is_valid:
            return False, error
        return True, ""
    
    @staticmethod
    def validate_price(
        value: Any,
        field_name: str = "price",
        min_price: float = 0.00000001,
        max_price: float = 1_000_000
    ) -> Tuple[bool, str]:
        """التحقق من صحة السعر"""
        is_valid, error = Validator.validate_number(
            value,
            field_name,
            min_value=min_price,
            max_value=max_price,
            allow_zero=False
        )
        if not is_valid:
            return False, error
        return True, ""
    
    @staticmethod
    def validate_quantity(
        value: Any,
        field_name: str = "quantity",
        min_quantity: float = 0.00000001,
        max_quantity: float = 1_000_000_000
    ) -> Tuple[bool, str]:
        """التحقق من صحة الكمية"""
        is_valid, error = Validator.validate_number(
            value,
            field_name,
            min_value=min_quantity,
            max_value=max_quantity,
            allow_zero=False
        )
        if not is_valid:
            return False, error
        return True, ""
    
    @staticmethod
    def validate_percentage(
        value: Any,
        field_name: str = "percentage"
    ) -> Tuple[bool, str]:
        """التحقق من صحة النسبة المئوية"""
        is_valid, error = Validator.validate_number(
            value,
            field_name,
            min_value=0,
            max_value=100
        )
        if not is_valid:
            return False, error
        return True, ""
    
    @staticmethod
    def validate_choice(
        value: Any,
        choices: List[Any],
        field_name: str = "field"
    ) -> Tuple[bool, str]:
        """التحقق من أن القيمة من بين خيارات محددة"""
        if value not in choices:
            return False, f"{field_name} يجب أن يكون من {choices}"
        return True, ""
    
    @staticmethod
    def validate_list(
        value: Any,
        field_name: str = "list",
        min_items: int = 0,
        max_items: int = None,
        required: bool = True
    ) -> Tuple[bool, str]:
        """التحقق من صحة القائمة"""
        if value is None:
            if required:
                return False, f"{field_name} مطلوب"
            return True, ""
        
        if not isinstance(value, list):
            return False, f"{field_name} يجب أن تكون قائمة"
        
        if len(value) < min_items:
            return False, f"{field_name} يجب أن تحتوي على الأقل {min_items} عناصر"
        
        if max_items and len(value) > max_items:
            return False, f"{field_name} يجب ألا تحتوي على أكثر من {max_items} عناصر"
        
        return True, ""


class TradeValidator:
    """التحقق من صحة بيانات التداول"""
    
    @staticmethod
    def validate_buy_order(
        symbol: str,
        quantity: float,
        price: float,
        user_id: int = None
    ) -> ValidationResult:
        """التحقق من صحة أمر شراء"""
        result = ValidationResult()
        
        # التحقق من الرمز
        is_valid, error = Validator.validate_symbol(symbol)
        if not is_valid:
            result.add_error('symbol', error, symbol)
        
        # التحقق من الكمية
        is_valid, error = Validator.validate_quantity(quantity)
        if not is_valid:
            result.add_error('quantity', error, quantity)
        
        # التحقق من السعر
        is_valid, error = Validator.validate_price(price)
        if not is_valid:
            result.add_error('price', error, price)
        
        # التحقق من المستخدم
        if user_id is not None:
            if not isinstance(user_id, int) or user_id <= 0:
                result.add_error('user_id', 'معرف المستخدم يجب أن يكون رقماً موجباً', user_id)
        
        # التحقق من القيمة الإجمالية
        total_value = quantity * price
        if total_value < 1:
            result.add_error('total_value', 'قيمة الصفقة يجب أن تكون على الأقل 1 USDT', total_value)
        
        return result
    
    @staticmethod
    def validate_sell_order(
        symbol: str,
        quantity: float,
        price: float,
        user_id: int = None
    ) -> ValidationResult:
        """التحقق من صحة أمر بيع"""
        # نفس التحقق من أمر الشراء
        return TradeValidator.validate_buy_order(symbol, quantity, price, user_id)
    
    @staticmethod
    def validate_position(position: Dict) -> ValidationResult:
        """التحقق من صحة بيانات المركز"""
        result = ValidationResult()
        
        required_fields = ['symbol', 'entry_price', 'quantity', 'strategy', 'timeframe']
        for field in required_fields:
            if field not in position:
                result.add_error(field, f'{field} مطلوب')
        
        if 'symbol' in position:
            is_valid, error = Validator.validate_symbol(position['symbol'])
            if not is_valid:
                result.add_error('symbol', error, position['symbol'])
        
        if 'entry_price' in position:
            is_valid, error = Validator.validate_price(position['entry_price'])
            if not is_valid:
                result.add_error('entry_price', error, position['entry_price'])
        
        if 'quantity' in position:
            is_valid, error = Validator.validate_quantity(position['quantity'])
            if not is_valid:
                result.add_error('quantity', error, position['quantity'])
        
        return result


class APIValidator:
    """التحقق من صحة بيانات API"""
    
    @staticmethod
    def validate_api_key(api_key: str) -> Tuple[bool, str]:
        """التحقق من صحة مفتاح API"""
        is_valid, error = Validator.validate_string(
            api_key,
            'api_key',
            min_length=20,
            max_length=200
        )
        if not is_valid:
            return False, error
        return True, ""
    
    @staticmethod
    def validate_api_secret(api_secret: str) -> Tuple[bool, str]:
        """التحقق من صحة سر API"""
        is_valid, error = Validator.validate_string(
            api_secret,
            'api_secret',
            min_length=20,
            max_length=200
        )
        if not is_valid:
            return False, error
        return True, ""
    
    @staticmethod
    def validate_binance_keys(api_key: str, api_secret: str) -> ValidationResult:
        """التحقق من صحة مفاتيح Binance"""
        result = ValidationResult()
        
        is_valid, error = APIValidator.validate_api_key(api_key)
        if not is_valid:
            result.add_error('api_key', error, api_key)
        
        is_valid, error = APIValidator.validate_api_secret(api_secret)
        if not is_valid:
            result.add_error('api_secret', error, api_secret)
        
        return result


class StrategyValidator:
    """التحقق من صحة بيانات الاستراتيجية"""
    
    VALID_STRATEGIES = [
        'trend_following',
        'peak_valley_scalping',
        'momentum_breakout',
        'mean_reversion',
        'scalping_ema',
        'rsi_divergence',
        'volume_price_trend'
    ]
    
    VALID_TIMEFRAMES = [
        '1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'
    ]
    
    @staticmethod
    def validate_strategy_name(strategy_name: str) -> Tuple[bool, str]:
        """التحقق من اسم الاستراتيجية"""
        is_valid, error = Validator.validate_choice(
            strategy_name,
            StrategyValidator.VALID_STRATEGIES,
            'strategy_name'
        )
        if not is_valid:
            return False, error
        return True, ""
    
    @staticmethod
    def validate_timeframe(timeframe: str) -> Tuple[bool, str]:
        """التحقق من الإطار الزمني"""
        is_valid, error = Validator.validate_choice(
            timeframe,
            StrategyValidator.VALID_TIMEFRAMES,
            'timeframe'
        )
        if not is_valid:
            return False, error
        return True, ""
    
    @staticmethod
    def validate_strategy_params(
        strategy_name: str,
        timeframe: str,
        params: Dict = None
    ) -> ValidationResult:
        """التحقق من صحة معاملات الاستراتيجية"""
        result = ValidationResult()
        
        is_valid, error = StrategyValidator.validate_strategy_name(strategy_name)
        if not is_valid:
            result.add_error('strategy_name', error, strategy_name)
        
        is_valid, error = StrategyValidator.validate_timeframe(timeframe)
        if not is_valid:
            result.add_error('timeframe', error, timeframe)
        
        if params:
            if not isinstance(params, dict):
                result.add_error('params', 'المعاملات يجب أن تكون قاموساً', type(params))
        
        return result


class UserValidator:
    """التحقق من صحة بيانات المستخدم"""
    
    @staticmethod
    def validate_user_id(user_id: Any) -> Tuple[bool, str]:
        """التحقق من معرف المستخدم"""
        if not isinstance(user_id, int) or user_id <= 0:
            return False, "معرف المستخدم يجب أن يكون رقماً موجباً"
        return True, ""
    
    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """التحقق من اسم المستخدم"""
        is_valid, error = Validator.validate_string(
            username,
            'username',
            min_length=3,
            max_length=50,
            pattern=r'^[a-zA-Z0-9_-]+$'
        )
        if not is_valid:
            return False, error
        return True, ""
    
    @staticmethod
    def validate_password(password: str) -> Tuple[bool, str]:
        """التحقق من كلمة المرور"""
        is_valid, error = Validator.validate_string(
            password,
            'password',
            min_length=8,
            max_length=128
        )
        if not is_valid:
            return False, error
        
        # التحقق من قوة كلمة المرور
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        
        if not (has_upper and has_lower and has_digit):
            return False, "كلمة المرور يجب أن تحتوي على أحرف كبيرة وصغيرة وأرقام"
        
        return True, ""


def validate_input(
    data: Dict,
    schema: Dict[str, Dict]
) -> ValidationResult:
    """
    التحقق من صحة البيانات بناءً على schema
    
    Args:
        data: البيانات المراد التحقق منها
        schema: schema التحقق
        
    Returns:
        ValidationResult
    
    مثال:
        schema = {
            'symbol': {'type': 'string', 'required': True, 'pattern': r'^[A-Z0-9]+$'},
            'price': {'type': 'number', 'required': True, 'min': 0},
            'quantity': {'type': 'number', 'required': True, 'min': 0}
        }
        result = validate_input(data, schema)
    """
    result = ValidationResult()
    
    for field_name, field_schema in schema.items():
        value = data.get(field_name)
        field_type = field_schema.get('type')
        required = field_schema.get('required', True)
        
        # التحقق من المتطلبات
        if required and value is None:
            result.add_error(field_name, f'{field_name} مطلوب')
            continue
        
        if value is None:
            continue
        
        # التحقق من النوع
        if field_type == 'string':
            is_valid, error = Validator.validate_string(
                value,
                field_name,
                min_length=field_schema.get('min_length', 0),
                max_length=field_schema.get('max_length'),
                pattern=field_schema.get('pattern'),
                required=required
            )
            if not is_valid:
                result.add_error(field_name, error, value)
        
        elif field_type == 'number':
            is_valid, error = Validator.validate_number(
                value,
                field_name,
                min_value=field_schema.get('min'),
                max_value=field_schema.get('max'),
                required=required
            )
            if not is_valid:
                result.add_error(field_name, error, value)
        
        elif field_type == 'email':
            is_valid, error = Validator.validate_email(value, field_name)
            if not is_valid:
                result.add_error(field_name, error, value)
        
        elif field_type == 'list':
            is_valid, error = Validator.validate_list(
                value,
                field_name,
                min_items=field_schema.get('min_items', 0),
                max_items=field_schema.get('max_items'),
                required=required
            )
            if not is_valid:
                result.add_error(field_name, error, value)
    
    return result
